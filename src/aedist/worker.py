"""Worker classes with lease semantics for the job board.

Workers poll for pending jobs, acquire exclusive leases via atomic file
renames, execute the query pipeline, and write results to done/ or failed/.

Subclasses:
    PadmeWorker  — local Ollama (GPU)
    OpenRouterWorker — OpenRouter cloud API
"""

import logging
import re
import signal
import traceback
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from .harness import (
    compute_cost,
    load_models,
    make_client,
    model_metadata,
    output_path,
    query_single_turn,
    save_json,
    should_skip,
)
from .schema import (
    JobSpec,
    LeaseInfo,
    MethodParams,
    ResourceUse,
    RunRecord,
)

log = logging.getLogger(__name__)

_PENDING_RE = re.compile(r"^(\d{3})-(.+)\.yaml$")


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

    # -- execution (abstract) --------------------------------------------------

    def execute(self, job: JobSpec) -> dict:
        """Subclasses override to call appropriate query pipeline based on job.mode."""
        raise NotImplementedError

    # -- completion ------------------------------------------------------------

    def complete(self, job: JobSpec, result: dict) -> RunRecord:
        """Move the running file to done/ and return a RunRecord."""
        src = self._find_running_file(job)
        dst = self.jobs_root / "done" / f"{job.job_id}.yaml"
        src.rename(dst)

        record = RunRecord(
            method=job.mode,
            method_params=MethodParams(model=job.model_filter or "unknown"),
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
        self.acquire(job)

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
    Ollama endpoint.
    """

    def __init__(
        self,
        jobs_root: Path = Path("jobs"),
        base_url: str = OLLAMA_BASE_URL,
    ) -> None:
        super().__init__(worker_id="padme", jobs_root=jobs_root)
        self.base_url = base_url

    def execute(self, job: JobSpec) -> dict:
        """Run a single query against Ollama.

        Each job targets exactly one model (via model_filter) and one run
        (repeat=1).  The manager handles fan-out.
        """
        client = make_client(self.base_url)
        prompt = Path(job.prompt).read_text().strip()
        models = load_models(job.models_file)
        output_dir = Path(job.output_dir)

        if job.model_filter:
            models = [m for m in models if job.model_filter in m["id"]]
        if not models:
            raise ValueError(f"No model matched filter {job.model_filter!r}")
        model_entry = models[0]
        model_id = model_entry["id"]

        if should_skip(output_dir, model_id, 1, "padme"):
            log.info("Skip %s (cached)", model_id)
            return {"wall_seconds": 0, "cost_usd": 0, "tokens_in": 0,
                    "tokens_out": 0, "result_file": None}

        log.info("Querying %s ...", model_id)
        result = query_single_turn(
            client, model_id, [{"role": "user", "content": prompt}],
        )

        usage = result.get("usage") or {}
        cost = compute_cost(usage, model_entry)

        filepath = output_path(output_dir, model_id, 1, "padme")
        save_json(
            filepath,
            {
                "model": model_id,
                "date": date.today().isoformat(),
                "run": 1,
                "prompt": prompt,
                "response": result["content"],
                "finish_reason": result["finish_reason"],
                "usage": usage,
                "wall_seconds": result["wall_seconds"],
                "cost_usd": cost,
                "model_metadata": model_metadata(model_entry),
            },
        )

        return {
            "wall_seconds": result["wall_seconds"],
            "cost_usd": cost,
            "tokens_in": usage.get("prompt_tokens", 0),
            "tokens_out": usage.get("completion_tokens", 0),
            "result_file": str(filepath),
        }


# ---------------------------------------------------------------------------
# OpenRouterWorker — cloud API with parallel execution
# ---------------------------------------------------------------------------

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterWorker(Worker):
    """Worker for execution via OpenRouter cloud API.

    Each job is a single (model, run) pair — the manager handles fan-out.
    """

    def __init__(self, jobs_root: Path = Path("jobs")) -> None:
        super().__init__(worker_id="openrouter", jobs_root=jobs_root)

    def execute(self, job: JobSpec) -> dict:
        """Run a single query via OpenRouter."""
        client = make_client()
        prompt = Path(job.prompt).read_text().strip()
        models = load_models(job.models_file)
        output_dir = Path(job.output_dir)

        if job.model_filter:
            models = [m for m in models if job.model_filter in m["id"]]
        if not models:
            raise ValueError(f"No model matched filter {job.model_filter!r}")
        model_entry = models[0]
        model_id = model_entry["id"]

        if should_skip(output_dir, model_id, 1):
            log.info("Skip %s (cached)", model_id)
            return {"wall_seconds": 0, "cost_usd": 0, "tokens_in": 0,
                    "tokens_out": 0, "result_file": None}

        log.info("Querying %s ...", model_id)
        result = query_single_turn(
            client, model_id, [{"role": "user", "content": prompt}],
        )

        usage = result.get("usage") or {}
        cost = compute_cost(usage, model_entry)

        filepath = output_path(output_dir, model_id, 1)
        save_json(
            filepath,
            {
                "model": model_id,
                "date": date.today().isoformat(),
                "run": 1,
                "prompt": prompt,
                "response": result["content"],
                "finish_reason": result["finish_reason"],
                "usage": usage,
                "wall_seconds": result["wall_seconds"],
                "cost_usd": cost,
                "model_metadata": model_metadata(model_entry),
            },
        )

        return {
            "wall_seconds": result["wall_seconds"],
            "cost_usd": cost,
            "tokens_in": usage.get("prompt_tokens", 0),
            "tokens_out": usage.get("completion_tokens", 0),
            "result_file": str(filepath),
        }


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
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously, polling for jobs (never exits)",
    )
    parser.add_argument(
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
