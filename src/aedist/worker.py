"""Worker classes with lease semantics for the job board.

Worker.execute() dispatches on job.mode, routing each job to the correct
query pipeline (single-turn, RAG, multiturn, web, decomposed).  Subclasses
override only make_client() to target different endpoints (Ollama vs
OpenRouter).  All dispatch logic lives in the base class.
"""

import logging
import os
import re
import signal
import traceback
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from .harness import (
    BudgetTracker,
    assemble_prompt,
    build_api_kwargs,
    compute_cost,
    load_models,
    make_client,
    model_metadata,
    output_path,
    query_single_turn,
    save_json,
    should_skip,
)
from .query_fusion import run_fusion
from .query_livesearch import run_web_searches
from .query_multiturn import run_conversation
from .query_per_fuel import query_decomposed
from .query_rag import load_corpus
from .schema import (
    JobSpec,
    LeaseInfo,
    Method,
    MethodParams,
    ResourceUse,
    RunRecord,
)

log = logging.getLogger(__name__)

_PENDING_RE = re.compile(r"^(\d{3})-(.+)\.yaml$")

# Translate legacy dispatch modes to emitted method vocabulary (ticket 0120).
# method = <base>[+<modifier>...]
# base: direct | rag | rag_livesearch
# modifiers: +multiturn | +verification
# prompt_version in method_params: extract | complete | scenarios | cited |
#   followups | per_fuel | base | composite | +aspect | -aspect | dspy
_MODE_TO_METHOD: dict[Method, Method] = {
    Method.SINGLE: Method.DIRECT,
    Method.FRONTIER: Method.DIRECT,
    Method.SOURCED: Method.RAG,
    Method.RAG: Method.RAG,
    Method.DECOMPOSED: Method.RAG,
    Method.WEB: Method.RAG_LIVESEARCH,
    Method.MULTITURN: Method.DIRECT_MULTITURN,
    Method.VERIFICATION: Method.RAG_VERIFICATION,
    Method.FUSION: Method.FUSION,
}

# Prompt modules whose directory presence signals sign-notation (ticket 0121).
# When output_dir ends with /ablation/{aspect}, emit "+{aspect}".
# When output_dir ends with /ablation/no_{aspect}, emit "-{aspect}".
_ABLATION_MODULES = frozenset(
    [
        "persona",
        "overview",
        "citation_columns",
        "sourcing_ground",
        "narratives",
        "bibliography",
        "statistics",
    ]
)


def _derive_ablation_prompt_version(output_dir: Path) -> str | None:
    """Return sign-notation prompt_version for ablation/plus/minus sweeps.

    Maps output directory names under outputs/ablation/ to prompt_version:
      ablation/base          -> None  (no special version; caller uses dir name)
      ablation/{aspect}      -> "+{aspect}"  (sweep_ablation_plus_*)
      ablation/no_{aspect}   -> "-{aspect}"  (sweep_ablation_minus_*)

    Returns None if the directory is not an ablation plus/minus dir.
    """
    parts = output_dir.parts
    # Look for .../ablation/{leaf} pattern
    if len(parts) < 2 or parts[-2] != "ablation":
        return None
    leaf = parts[-1]
    if leaf.startswith("no_"):
        aspect = leaf[3:]
        if aspect in _ABLATION_MODULES:
            return f"-{aspect}"
    elif leaf in _ABLATION_MODULES:
        return f"+{leaf}"
    return None


class Worker:
    """Base worker that implements the poll-acquire-execute-complete lifecycle."""

    def __init__(self, worker_id: str, jobs_root: Path = Path("jobs")) -> None:
        self.worker_id = worker_id
        self.jobs_root = jobs_root
        for subdir in ("pending", "running", "done", "failed"):
            (self.jobs_root / subdir).mkdir(parents=True, exist_ok=True)

    # -- polling ---------------------------------------------------------------

    def poll(self) -> JobSpec | None:
        """Scan pending/ for the highest-priority job.

        Returns the highest-priority JobSpec, or None if the queue is empty.
        Priority is sorted descending (higher number first); ties broken
        by job_id lexicographically (FIFO within same priority).
        """
        pending_dir = self.jobs_root / "pending"
        candidates: list[tuple[int, str, Path]] = []
        for path in pending_dir.glob("*.yaml"):
            m = _PENDING_RE.match(path.name)
            if m:
                priority = int(m.group(1))
                job_id = m.group(2)
                candidates.append((priority, job_id, path))
        if not candidates:
            return None
        # Sort: highest priority first, then job_id ascending (FIFO)
        candidates.sort(key=lambda t: (-t[0], t[1]))
        best = candidates[0]
        text = best[2].read_text()
        return JobSpec.from_yaml(text)

    # -- lease acquisition -----------------------------------------------------

    def acquire(self, job: JobSpec) -> LeaseInfo:
        """Atomically move a pending job to running/ with a lease timestamp.

        Uses Path.rename() for POSIX atomicity.
        """
        now = datetime.now(UTC)
        expiry = now + timedelta(seconds=job.timeout_seconds)
        expiry_str = expiry.strftime("%Y%m%dT%H%M%SZ")
        src = self._find_pending_file(job)
        dst = self.jobs_root / "running" / f"{job.job_id}-lease-{expiry_str}.yaml"
        src.rename(dst)
        return LeaseInfo(
            job_id=job.job_id,
            worker_id=self.worker_id,
            start_time=now,
            expiry_time=expiry,
        )

    # -- client factory (override in subclasses) --------------------------------

    def make_client(self):
        """Create an OpenAI-compatible client. Subclasses override for their endpoint."""
        return make_client()

    # -- mode dispatch ----------------------------------------------------------

    def execute(self, job: JobSpec) -> dict:
        """Dispatch to the correct query pipeline based on job.mode.

        Raises ValueError for unrecognized modes. Raises NotImplementedError
        for modes that require external orchestration (verification).
        """
        client = self.make_client()
        if job.prompt_modules is not None:
            modules_dir = (
                Path(job.modules_dir) if job.modules_dir else Path("experiments/prompts/modules")
            )
            prompt = assemble_prompt(modules_dir, job.prompt_modules)
        else:
            prompt = Path(job.prompt).read_text().strip()
        models = load_models(job.models_file)
        output_dir = Path(job.output_dir)

        if job.model_filter:
            models = [m for m in models if job.model_filter in m["id"]]
        if not models:
            raise ValueError(f"No model matched filter {job.model_filter!r}")
        model_entry = models[0]
        model_id = model_entry["id"]
        run = job.run_number
        api_kwargs = build_api_kwargs(
            model_entry,
            temperature=job.temperature,
            enable_web_search=job.web_search,
            no_think=job.no_think,
        )

        pool_label = self.worker_id
        if should_skip(output_dir, model_id, run, pool_label):
            log.info("Skip %s run %d (cached)", model_id, run)
            return {
                "wall_seconds": 0,
                "cost_usd": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "result_file": None,
            }

        mode = job.mode
        if mode in (Method.SINGLE, Method.FRONTIER, Method.SOURCED):
            return self._execute_single(
                client,
                model_id,
                model_entry,
                prompt,
                output_dir,
                run,
                pool_label,
                api_kwargs=api_kwargs,
            )
        elif mode == Method.RAG:
            return self._execute_rag(
                client,
                model_id,
                model_entry,
                prompt,
                output_dir,
                run,
                pool_label,
                job,
                api_kwargs=api_kwargs,
            )
        elif mode == Method.MULTITURN:
            return self._execute_multiturn(
                client,
                model_id,
                model_entry,
                prompt,
                output_dir,
                run,
                pool_label,
                job,
                api_kwargs=api_kwargs,
            )
        elif mode == Method.WEB:
            return self._execute_web(
                client,
                model_id,
                model_entry,
                prompt,
                output_dir,
                run,
                pool_label,
                api_kwargs=api_kwargs,
            )
        elif mode == Method.DECOMPOSED:
            return self._execute_decomposed(
                client,
                model_id,
                model_entry,
                prompt,
                output_dir,
                run,
                pool_label,
                job,
                api_kwargs=api_kwargs,
            )
        elif mode == Method.FUSION:
            return self._execute_fusion(job)
        elif mode == Method.VERIFICATION:
            raise NotImplementedError(  # noqa: hygiene — documented design choice
                "verification mode requires external orchestration "
                "(use query_verification.py directly)"
            )
        else:
            raise ValueError(f"Unsupported mode: {mode!r}")

    # -- per-mode handlers -----------------------------------------------------

    @staticmethod
    def _build_result(result: dict, cost: float, filepath: Path) -> dict:
        """Build the standard return dict from a query_single_turn result."""
        usage = result.get("usage") or {}
        return {
            "wall_seconds": result["wall_seconds"],
            "cost_usd": cost,
            "tokens_in": usage.get("prompt_tokens", 0),
            "tokens_out": usage.get("completion_tokens", 0),
            "result_file": str(filepath),
        }

    def _query_and_save(
        self,
        client,
        model_id,
        model_entry,
        messages,
        output_dir,
        run,
        pool_label,
        extra_fields=None,
        api_kwargs=None,
    ):
        """Run query_single_turn, save JSON, return standard result dict.

        Common path for single, RAG, and web modes that all use
        query_single_turn with different message lists.
        """
        result = query_single_turn(client, model_id, messages, **(api_kwargs or {}))
        usage = result.get("usage") or {}
        cost = compute_cost(usage, model_entry)

        filepath = output_path(output_dir, model_id, run, pool_label)
        record = {
            "model": model_id,
            "date": date.today().isoformat(),
            "run": run,
            "response": result["content"],
            "finish_reason": result["finish_reason"],
            "usage": usage,
            "wall_seconds": result["wall_seconds"],
            "cost_usd": cost,
            "temperature": (api_kwargs or {}).get("temperature"),
            "model_metadata": model_metadata(model_entry),
        }
        if extra_fields:
            record.update(extra_fields)
        save_json(filepath, record)
        return self._build_result(result, cost, filepath)

    def _execute_single(
        self, client, model_id, model_entry, prompt, output_dir, run, pool_label, api_kwargs=None
    ):
        """Execute a single-turn query."""
        log.info("Querying %s run %d ...", model_id, run)
        messages = [{"role": "user", "content": prompt}]
        return self._query_and_save(
            client,
            model_id,
            model_entry,
            messages,
            output_dir,
            run,
            pool_label,
            extra_fields={"prompt": prompt},
            api_kwargs=api_kwargs,
        )

    def _execute_rag(
        self,
        client,
        model_id,
        model_entry,
        prompt,
        output_dir,
        run,
        pool_label,
        job,
        api_kwargs=None,
    ):
        """Execute a RAG query: corpus as system context + prompt as user."""
        corpus_dir = Path(job.corpus) if job.corpus else None
        if not corpus_dir or not corpus_dir.exists():
            raise ValueError(f"RAG mode requires a valid corpus directory, got {job.corpus!r}")

        try:
            corpus_text, corpus_files = load_corpus(corpus_dir)
        except SystemExit as exc:
            raise RuntimeError(f"RAG corpus load failed for {corpus_dir}: {exc}") from exc
        messages = [
            {"role": "system", "content": corpus_text},
            {"role": "user", "content": prompt},
        ]

        log.info("Querying %s run %d (RAG %s)...", model_id, run, job.strategy or "wholesale")
        return self._query_and_save(
            client,
            model_id,
            model_entry,
            messages,
            output_dir,
            run,
            pool_label,
            extra_fields={
                "prompt": prompt,
                "strategy": job.strategy or "wholesale",
                "corpus_files": corpus_files,
            },
            api_kwargs=api_kwargs,
        )

    def _execute_multiturn(
        self,
        client,
        model_id,
        model_entry,
        prompt,
        output_dir,
        run,
        pool_label,
        job,
        api_kwargs=None,
    ):
        """Execute a multi-turn conversation."""
        followups_path = Path(job.followups) if job.followups else None
        if not followups_path or not followups_path.exists():
            raise ValueError(
                f"Multiturn mode requires a valid followups file, got {job.followups!r}"
            )

        followups = [
            line.strip() for line in followups_path.read_text().splitlines() if line.strip()
        ]
        budget = BudgetTracker(job.budget_usd)

        log.info("Querying %s run %d (multiturn, %d followups)...", model_id, run, len(followups))
        conv = run_conversation(
            client,
            model_id,
            prompt,
            followups,
            model_entry,
            budget,
            **(api_kwargs or {}),
        )
        if conv is None:
            raise RuntimeError(f"Multiturn conversation failed for {model_id} run {run}")

        filepath = output_path(output_dir, model_id, run, pool_label)
        save_json(
            filepath,
            {
                "model": model_id,
                "run": run,
                "date": date.today().isoformat(),
                "temperature": (api_kwargs or {}).get("temperature"),
                "model_metadata": model_metadata(model_entry),
                **conv,
            },
        )
        return {
            "wall_seconds": conv.get("total_wall_seconds", 0),
            "cost_usd": conv.get("total_cost_usd", 0),
            "tokens_in": 0,
            "tokens_out": 0,
            "result_file": str(filepath),
        }

    def _execute_web(
        self,
        client,
        model_id,
        model_entry,
        prompt,
        output_dir,
        run,
        pool_label,
        api_kwargs=None,
    ):
        """Execute a web-augmented query."""
        tavily_key = os.environ.get("TAVILY_API_KEY", "")
        if not tavily_key:
            raise RuntimeError(
                "TAVILY_API_KEY is not set — web mode cannot produce valid results "
                "without search context"
            )
        web_context, search_log = run_web_searches(tavily_key)

        messages = [
            {
                "role": "system",
                "content": (
                    "Use the following web search results as context "
                    "to answer the user's question.\n\n" + web_context
                ),
            },
            {"role": "user", "content": prompt},
        ]

        log.info("Querying %s run %d (web-augmented)...", model_id, run)
        return self._query_and_save(
            client,
            model_id,
            model_entry,
            messages,
            output_dir,
            run,
            pool_label,
            extra_fields={"prompt": prompt, "web_searches": search_log},
            api_kwargs=api_kwargs,
        )

    def _execute_decomposed(
        self,
        client,
        model_id,
        model_entry,
        prompt,
        output_dir,
        run,
        pool_label,
        job,
        api_kwargs=None,
    ):
        """Execute decomposed sub-queries by fuel type."""
        corpus_dir = Path(job.corpus) if job.corpus else None
        if not corpus_dir or not corpus_dir.exists():
            raise ValueError(
                f"Decomposed mode requires a valid corpus directory, got {job.corpus!r}"
            )

        try:
            corpus_text, corpus_files = load_corpus(corpus_dir)
        except SystemExit as exc:
            raise RuntimeError(f"Decomposed corpus load failed for {corpus_dir}: {exc}") from exc
        budget = BudgetTracker(job.budget_usd)

        log.info("Querying %s run %d (decomposed RAG)...", model_id, run)
        decomposed = query_decomposed(
            client,
            model_id,
            corpus_text,
            budget,
            model_entry,
            **(api_kwargs or {}),
        )
        if decomposed is None:
            raise RuntimeError(f"Decomposed query failed for {model_id} run {run}")

        filepath = output_path(output_dir, model_id, run, pool_label)
        save_json(
            filepath,
            {
                "model": model_id,
                "run": run,
                "date": date.today().isoformat(),
                "strategy": "decomposed",
                "corpus_files": corpus_files,
                "prompt": prompt,
                "response": decomposed.get("merged_csv", ""),
                "finish_reason": "merged",
                "usage": decomposed.get("total_usage", {}),
                "wall_seconds": decomposed.get("total_wall_seconds", 0),
                "cost_usd": decomposed.get("total_cost_usd", 0),
                "temperature": (api_kwargs or {}).get("temperature"),
                "model_metadata": model_metadata(model_entry),
                "n_merged_plants": decomposed.get("n_merged_plants", 0),
            },
        )
        return {
            "wall_seconds": decomposed.get("total_wall_seconds", 0),
            "cost_usd": decomposed.get("total_cost_usd", 0),
            "tokens_in": decomposed.get("total_usage", {}).get("prompt_tokens", 0),
            "tokens_out": decomposed.get("total_usage", {}).get("completion_tokens", 0),
            "result_file": str(filepath),
        }

    @staticmethod
    def _execute_fusion(job: JobSpec) -> dict:
        """Execute the fusion pipeline for one sweep configuration.

        Fusion is dispatch-different from other modes: it takes a single model
        string (not a models.yaml file) and does not iterate over a model
        registry.  Results are written to derived/fusion_proto/ by
        run_fusion(), not to the standard outputs/ tree.
        """
        corpus_dir = Path(job.corpus) if job.corpus else None
        if not corpus_dir or not corpus_dir.exists():
            raise ValueError(f"Fusion mode requires a valid corpus directory, got {job.corpus!r}")

        model = job.model_filter or "openai/gpt-4o-mini"
        output_dir = Path(job.output_dir)

        # Fusion-specific params live in job.extra (populated from sweep config
        # fields that JobSpec doesn't have dedicated slots for).
        extra = job.method_params.extra or {}
        fusion_mode = extra.get("fusion_mode", "compare")
        fmt = extra.get("format", "md")
        fragments = extra.get("fragments")
        seed = extra.get("seed")
        provider = extra.get("provider")

        log.info(
            "Executing fusion sweep model=%s fusion_mode=%s format=%s", model, fusion_mode, fmt
        )
        summary = run_fusion(
            model=model,
            corpus_dir=corpus_dir,
            output_dir=output_dir,
            fusion_mode=fusion_mode,
            fmt=fmt,
            fragments=fragments,
            seed=seed,
            provider=provider,
        )

        return {
            "wall_seconds": summary.get("wall_seconds", 0),
            "cost_usd": 0,  # fusion uses make_client() directly; cost not tracked here
            "tokens_in": 0,
            "tokens_out": 0,
            "result_file": str(output_dir / "fusion_summary.json"),
        }

    # -- completion ------------------------------------------------------------

    def complete(self, job: JobSpec, result: dict) -> RunRecord:
        """Move the running file to done/ and return a RunRecord."""
        src = self._find_running_file(job)
        dst = self.jobs_root / "done" / f"{job.job_id}.yaml"
        src.rename(dst)

        # Translate dispatch mode to emitted method vocabulary.
        emitted_method = _MODE_TO_METHOD.get(job.mode, job.mode)
        # Derive sign-notation prompt_version for ablation plus/minus sweeps
        # (ticket 0121/0122): sweep_ablation_plus_* → "+{aspect}",
        # sweep_ablation_minus_* → "-{aspect}".
        ablation_pv = _derive_ablation_prompt_version(Path(job.output_dir))
        method_params = MethodParams(model=job.model_filter or "unknown")
        if ablation_pv is not None:
            method_params.prompt_version = ablation_pv
        record = RunRecord(
            method=emitted_method,
            method_params=method_params,
            resource_use=ResourceUse(
                wall_s=result.get("wall_seconds"),
                cost_usd=result.get("cost_usd"),
                tokens_in=result.get("tokens_in"),
                tokens_out=result.get("tokens_out"),
            ),
            result_file=result.get("result_file"),
        )
        return record

    # -- failure ---------------------------------------------------------------

    def fail(self, job: JobSpec, error: Exception) -> None:
        """Move the running file to failed/ and write an error log."""
        src = self._find_running_file(job)
        dst = self.jobs_root / "failed" / f"{job.job_id}.yaml"
        src.rename(dst)
        error_file = self.jobs_root / "failed" / f"{job.job_id}.error.txt"
        error_file.write_text(
            "".join(traceback.format_exception(type(error), error, error.__traceback__))
            or str(error)
        )

    # -- convenience -----------------------------------------------------------

    def run_one(self) -> RunRecord | None:
        """Poll, acquire, execute, and complete/fail a single job.

        Returns a RunRecord on success, or None if no job was available.
        Uses signal.alarm for timeout enforcement (POSIX-only).
        """
        job = self.poll()
        if job is None:
            return None
        try:
            self.acquire(job)
        except FileNotFoundError:
            # Lost race: another worker grabbed this job first. Retry.
            return self.run_one()

        def _timeout_handler(signum: int, frame: object) -> None:
            raise TimeoutError(f"Job {job.job_id} exceeded timeout of {job.timeout_seconds}s")

        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        try:
            signal.alarm(job.timeout_seconds)
            result = self.execute(job)
            signal.alarm(0)
            return self.complete(job, result)
        except Exception as exc:
            signal.alarm(0)
            self.fail(job, exc)
            return None
        finally:
            signal.signal(signal.SIGALRM, old_handler)

    # -- helpers ---------------------------------------------------------------

    def _find_pending_file(self, job: JobSpec) -> Path:
        """Find the pending file for a given job."""
        matches = list(self.jobs_root.glob(f"pending/*-{job.job_id}.yaml"))
        if not matches:
            msg = f"No pending file found for job {job.job_id}"
            raise FileNotFoundError(msg)
        return matches[0]

    def _find_running_file(self, job: JobSpec) -> Path:
        """Find the running file for a given job."""
        matches = list(self.jobs_root.glob(f"running/{job.job_id}-lease-*.yaml"))
        if not matches:
            msg = f"No running file found for job {job.job_id}"
            raise FileNotFoundError(msg)
        return matches[0]


# ---------------------------------------------------------------------------
# PadmeWorker — local GPU execution via Ollama
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = "http://localhost:11434/v1"


class PadmeWorker(Worker):
    """Worker for local GPU execution via Ollama.

    Executes jobs sequentially (one model at a time) using the local
    Ollama endpoint.  Dispatch logic is inherited from Worker.execute().
    """

    def __init__(
        self,
        jobs_root: Path = Path("jobs"),
        base_url: str = OLLAMA_BASE_URL,
    ) -> None:
        super().__init__(worker_id="padme", jobs_root=jobs_root)
        self.base_url = base_url

    def make_client(self):
        """Create an OpenAI-compatible client for Ollama."""
        return make_client(self.base_url)


# ---------------------------------------------------------------------------
# OpenRouterWorker — cloud API with parallel execution
# ---------------------------------------------------------------------------

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterWorker(Worker):
    """Worker for execution via OpenRouter cloud API.

    Each job is a single (model, run) pair — the manager handles fan-out.
    Dispatch logic is inherited from Worker.execute().
    """

    def __init__(self, jobs_root: Path = Path("jobs")) -> None:
        super().__init__(worker_id="", jobs_root=jobs_root)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv=None):
    """Run a worker from the command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Run an AEDIST worker")
    parser.add_argument(
        "pool",
        choices=["padme", "openrouter"],
        help="Worker pool to run",
    )
    parser.add_argument(
        "--jobs-root",
        type=Path,
        default=Path("jobs"),
        help="Root directory for job board (default: jobs/)",
    )
    parser.add_argument(
        "--base-url",
        default=OLLAMA_BASE_URL,
        help=f"Ollama API base URL (default: {OLLAMA_BASE_URL})",
    )
    run_mode = parser.add_mutually_exclusive_group()
    run_mode.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously, polling for jobs (never exits)",
    )
    run_mode.add_argument(
        "--drain",
        action="store_true",
        help="Process all pending jobs then exit when queue is empty",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    workers = {
        "padme": lambda: PadmeWorker(jobs_root=args.jobs_root, base_url=args.base_url),
        "openrouter": lambda: OpenRouterWorker(jobs_root=args.jobs_root),
    }
    worker = workers[args.pool]()

    if args.loop:
        import time

        while True:
            record = worker.run_one()
            if record is None:
                time.sleep(5)
    elif args.drain:
        while True:
            record = worker.run_one()
            if record is None:
                log.info("Queue drained, exiting.")
                break
            log.info("Completed job, method=%s", record.method)
    else:
        record = worker.run_one()
        if record is None:
            log.info("No pending jobs.")
        else:
            log.info("Completed job, method=%s", record.method)
