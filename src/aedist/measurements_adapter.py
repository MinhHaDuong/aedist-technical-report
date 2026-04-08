"""Adapter between RunRecord (measurements.jsonl) and reporting dict format.

Reporting scripts consume list[dict] with keys like label, f1, coverage, etc.
RunRecord stores the same data in a structured schema. This module bridges
the two representations so pure reporting functions stay untouched.
"""

from pathlib import Path

from .schema import (
    Method,
    MethodParams,
    ResourceUse,
    ResultSummary,
    RunRecord,
)
from .tabulate_utils import strip_label


def records_to_metrics(records: list[RunRecord]) -> list[dict]:
    """Convert RunRecord rows to reporting dict format.

    Produces dicts with the keys that reporting scripts consume:
    label, f1, coverage, precision, n_reference, n_system,
    n_matched, n_missed, n_hallucinated, fuel_accuracy,
    status_accuracy, province_accuracy.

    Also includes cost_usd and wall_s for summarize_sweep / plot_pareto.
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

        # Reconstruct label from prompt_version + result_file stem
        prompt_version = r.method_params.prompt_version or ""
        stem = Path(r.result_file).stem if r.result_file else r.run_id
        label = f"{prompt_version}/{stem}" if prompt_version else stem

        d: dict = {
            "label": label,
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

        # Include resource data for cost/latency consumers
        if r.resource_use.cost_usd is not None:
            d["cost_usd"] = r.resource_use.cost_usd
        if r.resource_use.wall_s is not None:
            d["wall_seconds"] = r.resource_use.wall_s

        result.append(d)
    return result


def metrics_to_records(
    metrics: list[dict],
    method: Method = Method.SINGLE,
) -> list[RunRecord]:
    """Convert reporting dicts to RunRecord rows.

    This is the inverse of records_to_metrics, used for migration
    and round-trip testing. Fields not present in the metrics dict
    (e.g. timestamps, tokens) get defaults.
    """
    records = []
    for entry in metrics:
        label = entry["label"]
        # Parse label into prompt_version and stem
        if "/" in label:
            prompt_version, stem = label.rsplit("/", 1)
        else:
            prompt_version, stem = "", label

        # Infer method from prompt_version
        m = method
        if "multiturn" in prompt_version:
            m = Method.MULTITURN
        elif "decomposed" in prompt_version:
            m = Method.DECOMPOSED
        elif "rag" in prompt_version:
            m = Method.RAG
        elif "web" in prompt_version:
            m = Method.WEB

        tp = entry.get("n_matched", 0)
        fn = entry.get("n_missed", 0)
        fp = entry.get("n_hallucinated", 0)
        n_plants = entry.get("n_system", tp + fp)

        records.append(
            RunRecord(
                method=m,
                method_params=MethodParams(
                    model=strip_label(label),
                    prompt_version=prompt_version or None,
                ),
                resource_use=ResourceUse(
                    cost_usd=entry.get("cost_usd"),
                    wall_s=entry.get("wall_seconds"),
                ),
                result_file=f"{label}.csv",
                result_summary=ResultSummary(
                    n_plants=n_plants,
                    tp=tp,
                    fp=fp,
                    fn=fn,
                    f1=entry.get("f1"),
                    fuel_accuracy=entry.get("fuel_accuracy"),
                    status_accuracy=entry.get("status_accuracy"),
                    province_accuracy=entry.get("province_accuracy"),
                ),
            )
        )
    return records


def load_metrics_from_measurements(path: str | Path) -> list[dict]:
    """Load measurements.jsonl and convert to reporting dict format."""
    records = RunRecord.load_jsonl(path)
    return records_to_metrics(records)
