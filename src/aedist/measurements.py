"""Measurements loader — sole read interface for benchmark results (ADR-7).

All reporting scripts import ``load()`` or ``load_metrics()`` instead of
reading files directly.  The path to the measurements cache is read from
``experiments.toml [paths]``.

Data flow::

    Raw JSON  →  RunRecord / measurements.jsonl  →  metrics dict  →  figures / tables
    (worker)     (complete record, JSONL)            (flat dict)      (column projections)

The metrics dict returned by ``records_to_metrics()`` is the **complete
scientific record**: all experimental conditions and all result metrics.
Figures and tables are projections that select the columns they need.
Bookkeeping fields (run_id, timestamp, result_file, validation) are excluded.

Usage::

    from aedist.measurements import load, load_metrics

    records = load()                        # list[RunRecord], all methods
    records = load(method="rag")            # filtered by method
    metrics = load_metrics()                # list[dict], complete scientific record
"""

import tomllib
from pathlib import Path

from .schema import Method, RunRecord

# Model slug suffixes that are post-hoc aggregations, not individual runs.
# Shared by all reporting modules that filter measurements.
SYNTHETIC_SUFFIXES = ("-union", "-consolidated", "-filtered", "_filtered", "-unverified")

_REPO_ROOT = Path(__file__).parent.parent.parent
_EXPERIMENTS_TOML = _REPO_ROOT / "experiments" / "experiments.toml"


def _load_paths() -> dict[str, str]:
    """Read [paths] section from experiments.toml."""
    with open(_EXPERIMENTS_TOML, "rb") as f:
        config = tomllib.load(f)
    return config.get("paths", {})


def _resolve(rel_path: str) -> Path:
    """Resolve a path relative to the repo root."""
    return _REPO_ROOT / rel_path


def load(method: Method | str | None = None) -> list[RunRecord]:
    """Load measurements, optionally filtered by method.

    Reads the cache file declared in ``experiments.toml [paths].measurements``.
    Returns an empty list if the file does not exist yet
    (run ``make -f experiments/derived/score.mk measurements.jsonl``).
    """
    paths = _load_paths()
    measurements_path = _resolve(paths.get("measurements", "measurements.jsonl"))
    if not measurements_path.exists():
        return []
    records = RunRecord.load_jsonl(measurements_path)
    if method:
        m = Method(method)
        records = [r for r in records if r.method == m]
    return records


def measurements_path() -> Path:
    """Return the resolved path to the measurements file."""
    paths = _load_paths()
    return _resolve(paths.get("measurements", "measurements.jsonl"))


def records_to_metrics(records: list[RunRecord]) -> list[dict]:
    """Convert RunRecord rows to the complete scientific record (ADR-7).

    Returns one dict per run containing all experimental conditions and result
    metrics.  Figures and tables project onto whatever columns they need.

    Condition fields: model, method, prompt_version, temperature, no_think,
    web_search (effective), seed, max_tokens, num_ctx, provider_order.
    Diagnostic fields: tokens_in, tokens_out, finish_reason.
    Result fields: f1, coverage, precision, n_matched, n_missed,
    n_hallucinated, fuel_accuracy, status_accuracy, province_accuracy.
    Resource fields: cost_usd, wall_seconds.

    Fields backed by ticket 0139 (seed, max_tokens, num_ctx, provider_order,
    web_search effective, finish_reason) are included when present in the
    record; absent otherwise.  Bookkeeping fields (run_id, timestamp,
    result_file, validation) are excluded.

    Agent-mode fields (ticket 0172, umbrella 0166): agent_family,
    agent_mode, synopsis_sha, designed_prompt_sha, n_web_search_calls,
    n_citations, parsed_table_path, finish_reason, retry_count, error,
    reasoning_summary, thinking_tokens, cost_breakdown, tool_calls_cost_usd
    are surfaced when the underlying RunRecord field is non-None. Lists
    are projected as counts; the raw lists stay in the RunRecord.

    Reference identity (ticket 0431): ``reference`` — the release filename of
    the dataset tp/fp/fn were scored against — is projected when present
    (omit-when-absent for legacy rows).

    Verification scalars from ``justification`` (source-grounding pipeline):
    verification_mode, mean_evidence_score, verification_cost_usd are
    projected when the justification dict carries them (omit-when-absent).
    Nested structures (score_distribution, filtered_metrics) and the
    adapter's {"output_text": ...} narrative shape are not projected; they
    remain in the RunRecord.
    """
    result = []
    for r in records:
        s = r.result_summary
        tp = s.tp or 0
        fp = s.fp or 0
        fn = s.fn or 0

        n_reference = tp + fn
        n_system = tp + fp

        coverage = round(tp / n_reference, 4) if n_reference > 0 else 0.0
        precision = round(tp / n_system, 4) if n_system > 0 else 0.0

        prompt_version = r.method_params.prompt_version or ""
        stem = Path(r.result_file).stem if r.result_file else r.run_id
        label = f"{prompt_version}/{stem}" if prompt_version else stem

        extra = r.method_params.extra or {}

        d: dict = {
            # --- identity ---
            "label": label,
            "model": r.method_params.model,
            "method": r.method,
            "prompt_version": r.method_params.prompt_version,
            # --- controlled conditions ---
            "temperature": r.method_params.temperature,
            "no_think": extra.get("no_think", False),
            # --- results ---
            "coverage": coverage,
            "precision": precision,
            "f1": s.f1 if s.f1 is not None else 0.0,
            "n_reference": n_reference,
            "n_system": n_system,
            "n_matched": tp,
            "n_missed": fn,
            "n_hallucinated": fp,
            "fuel_accuracy": s.fuel_accuracy,
            "status_accuracy": s.status_accuracy,
            "province_accuracy": s.province_accuracy,
        }

        # --- resources ---
        if r.resource_use.cost_usd is not None:
            d["cost_usd"] = r.resource_use.cost_usd
        if r.resource_use.wall_s is not None:
            d["wall_seconds"] = r.resource_use.wall_s
        # --- diagnostic (always include when present) ---
        if r.resource_use.tokens_in is not None:
            d["tokens_in"] = r.resource_use.tokens_in
        if r.resource_use.tokens_out is not None:
            d["tokens_out"] = r.resource_use.tokens_out
        # --- 0139 fields: included once RunRecord carries them ---
        # max_tokens lives on the typed MethodParams slot — evaluate.py
        # routes it there (evaluate.py:233), so read it directly. Reading
        # only from ``extra`` would silently drop the value (ADR-7 trap).
        if r.method_params.max_tokens is not None:
            d["max_tokens"] = r.method_params.max_tokens
        for key in (
            "seed",
            "num_ctx",
            "provider_order",
            "web_search",
            "finish_reason",
        ):
            if key in extra:
                d[key] = extra[key]

        # --- 0175 fields: per-sweep system instruction + per-model reasoning_effort ---
        # Surfaced so figures and tables can confirm the baseline regime
        # (no_websearch system message, minimal reasoning on gpt-oss / qwen3-max)
        # without re-reading raw JSON. Both omit-when-absent.
        if "system_instruction" in extra:
            d["system_instruction"] = extra["system_instruction"]
        if "reasoning_effort" in extra:
            d["reasoning_effort"] = extra["reasoning_effort"]

        # --- agent-mode fields (ticket 0172) -----------------------------
        # Scalars: omit-when-None to match the existing pattern above.
        # Lists: surface as counts so reporting can pivot without re-loading
        # the raw record; the raw lists stay in the RunRecord itself.
        if r.agent_family is not None:
            d["agent_family"] = r.agent_family
        if r.agent_mode is not None:
            d["agent_mode"] = r.agent_mode
        if r.synopsis_sha is not None:
            d["synopsis_sha"] = r.synopsis_sha
        if r.designed_prompt_sha is not None:
            d["designed_prompt_sha"] = r.designed_prompt_sha
        if r.web_search_calls is not None:
            d["n_web_search_calls"] = len(r.web_search_calls)
        if r.citations is not None:
            d["n_citations"] = len(r.citations)
        if r.parsed_table_path is not None:
            d["parsed_table_path"] = r.parsed_table_path
        # finish_reason is also written from extra above (0139 path); the
        # first-class field takes precedence when present.
        if r.finish_reason is not None:
            d["finish_reason"] = r.finish_reason
        if r.retry_count is not None:
            d["retry_count"] = r.retry_count
        if r.error is not None:
            d["error"] = r.error
        # --- 0431: reference dataset the scores were computed against -------
        # Omit-when-None (0139 precedent): legacy rows lack it. When v2 is
        # adopted (0413) tp/fp/fn change and this field is what distinguishes
        # pre- from post-adoption rows in the metrics dict (ADR-7).
        if r.reference is not None:
            d["reference"] = r.reference
        if r.reasoning_summary is not None:
            d["reasoning_summary"] = r.reasoning_summary
        if r.tool_calls_cost_usd is not None:
            d["tool_calls_cost_usd"] = r.tool_calls_cost_usd
        if r.resource_use.thinking_tokens is not None:
            d["thinking_tokens"] = r.resource_use.thinking_tokens
        if r.resource_use.cost_breakdown is not None:
            d["cost_breakdown"] = r.resource_use.cost_breakdown

        # --- verification scalars from justification (source-grounding) ------
        # justification is a free-form dict whose verification-mode shape
        # (query_verification.py) carries scientific scalars. Project those so
        # ADR-7 holds without re-reading raw JSON; omit-when-absent. Nested
        # structures (score_distribution, filtered_metrics) and the adapter's
        # {"output_text": ...} narrative shape stay in the RunRecord.
        if isinstance(r.justification, dict):
            for src_key, out_key in (
                ("verification_mode", "verification_mode"),
                ("mean_evidence_score", "mean_evidence_score"),
                ("verification_cost_usd", "verification_cost_usd"),
                # 0470: LLM-judge faithfulness scalar (upgrade of deterministic baseline)
                # None = no verdicts cached yet (see f1=None semantics); 0.0 would mislead.
                ("faithfulness_score", "faithfulness_score"),
            ):
                if r.justification.get(src_key) is not None:
                    d[out_key] = r.justification[src_key]

        result.append(d)
    return result


def load_metrics(method: Method | str | None = None) -> list[dict]:
    """Load measurements and convert to reporting dict format.

    Convenience wrapper: ``load()`` + ``records_to_metrics()``.
    """
    return records_to_metrics(load(method))
