"""Build CSV views from the Exp2 mart JSONL artifact."""

import argparse
import csv
import json
import logging
import re
from pathlib import Path

from .extract_exp2_bib import parse_md

log = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = Path("report/inputs/generated")

_ARMS_RUNS_FIELDS = [
    "arm",
    "agent",
    "model",
    "run",
    "classification",
    "narrative_chars",
    "inventory_rows",
    "n_matched",
    "cost_usd",
    "wall_s",
    "turns",
]

_N_REFERENCE_PLANTS = 163

_BIB_FIELDS = [
    "agent",
    "arm",
    "run",
    "n_rows",
    "src1_empty",
    "src1_notfound",
    "src1_present",
    "src1_valid",
    "src1_primary",
    "src2_empty",
    "src2_notfound",
    "src2_present",
    "src2_valid",
    "src2_primary",
    "notes_empty",
    "notes_notfound",
    "notes_present",
    "bib_entries",
    "bib_valid",
    "bib_primary",
    "citation_style",
]

_TURN_FIELDS = ["agent", "arm", "run", "turn", "rows", "cls"]

_SCORE_VIEW_FIELDS = [
    "arm",
    "model",
    "run",
    "prompt_version",
    "n_rows",
    "accuracy_coverage",
    "accuracy_coverage_annotation",
    "accuracy_precision",
    "accuracy_precision_annotation",
    "accuracy_f1",
    "accuracy_f1_annotation",
    "accuracy_fuel",
    "accuracy_fuel_annotation",
    "accuracy_status",
    "accuracy_status_annotation",
    "accuracy_province",
    "accuracy_province_annotation",
    "coherence_vocab_adherence",
    "coherence_vocab_adherence_annotation",
    "coherence_status_vocab_adherence",
    "coherence_status_vocab_adherence_annotation",
    "coherence_capacity_nonnegative",
    "coherence_capacity_nonnegative_annotation",
    "provenance_source_presence",
    "provenance_source_presence_annotation",
    "provenance_high_conf_dual_source",
    "provenance_high_conf_dual_source_annotation",
    "temporality_asof_presence",
    "temporality_asof_presence_annotation",
    "temporality_plausible_range",
    "temporality_plausible_range_annotation",
    "field_completeness_core",
    "field_completeness_core_annotation",
    "field_completeness_capacity",
    "field_completeness_capacity_annotation",
]


def _load_mart_records(mart_path: Path) -> list[dict]:
    records = []
    for line in mart_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(json.loads(line))
    return records


def _fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.4f}"


def _agent_from_artifact_path(path: str) -> str:
    artifact = Path(path)
    for token in (artifact.name, artifact.parent.name):
        match = re.match(r"^([a-z]+)_run\d+", token)
        if match:
            return match.group(1)
    return ""


def _record_key(record: dict) -> tuple[str, str, int]:
    return (record["arm"], record["model"], int(record["run"]))


def _read_pointer(repo_root: Path, pointer: dict[str, str]) -> Path:
    return repo_root / pointer["path"]


def _extract_text(raw: dict) -> str:
    if "content" in raw and isinstance(raw["content"], list):
        return " ".join(
            block.get("text", "") for block in raw["content"] if block.get("type") == "text"
        )
    if isinstance(raw.get("output"), dict) and "choices" in raw["output"]:
        return raw["output"]["choices"][0]["message"].get("content", "")
    if isinstance(raw.get("output"), list):
        parts = []
        for item in raw["output"]:
            content = item.get("content")
            if not isinstance(content, list):
                continue
            parts.extend(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "output_text"
            )
        return " ".join(part for part in parts if part)
    if isinstance(raw.get("outputs"), list):
        for item in reversed(raw["outputs"]):
            if item.get("type") == "message.output":
                content = item.get("content", "")
                if isinstance(content, list):
                    return " ".join(
                        block.get("text", "") for block in content if isinstance(block, dict)
                    )
                return str(content)
    return ""


def _count_rows_from_probe(repo_root: Path, probe_pointer: dict[str, str]) -> int:
    raw_path = _read_pointer(repo_root, probe_pointer)
    text = _extract_text(json.loads(raw_path.read_text(encoding="utf-8")))
    from .extract import count_best_table_rows

    return count_best_table_rows(text)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_exp2_mart_views(mart_path: Path, repo_root: Path | None = None) -> dict[str, list[dict]]:
    repo_root = repo_root or Path.cwd()
    records = _load_mart_records(mart_path)

    runs = [record for record in records if record.get("record_kind") == "run"]
    probes = [record for record in records if record.get("record_kind") == "probe"]
    scores = [record for record in records if record.get("record_kind") == "score"]

    run_rows: list[dict] = []
    bib_rows: list[dict] = []
    turn_rows: list[dict] = []

    coverage_by_run: dict[tuple[str, str, int], float] = {}
    for s in scores:
        cov = s.get("score_summary", {}).get("accuracy", {}).get("coverage", {}).get("value")
        if cov is not None:
            coverage_by_run[(s["arm"], s["model"], s["run"])] = cov

    for record in runs:
        agent = _agent_from_artifact_path(record["result_file"]["path"])
        cov = coverage_by_run.get((record["arm"], record["model"], record["run"]))
        n_matched = round(cov * _N_REFERENCE_PLANTS) if cov is not None else None
        run_rows.append(
            {
                "arm": record["arm"],
                "agent": agent,
                "model": record["model"],
                "run": record["run"],
                "classification": record["run_summary"].get("classification", ""),
                "narrative_chars": record["run_summary"].get("narrative_chars", 0),
                "inventory_rows": record["run_summary"].get("n_rows", 0),
                "n_matched": n_matched,
                "cost_usd": record["run_summary"].get("cost_usd", 0.0),
                "wall_s": record["run_summary"].get("wall_s", 0.0),
                "turns": record["run_summary"].get("turns", 1),
            }
        )

        bib_metrics = parse_md(_read_pointer(repo_root, record["parsed_table_file"]))
        bib_rows.append(
            {"agent": agent, "arm": record["arm"], "run": record["run"], **bib_metrics}
        )

    for record in probes:
        agent = _agent_from_artifact_path(record["probe_file"]["path"])
        turn_rows.append(
            {
                "agent": agent,
                "arm": record["arm"],
                "run": record["run"],
                "turn": record["probe_summary"]["turn"],
                "rows": _count_rows_from_probe(repo_root, record["probe_file"]),
                "cls": record["probe_summary"].get("probe_label") or "no_report",
            }
        )

    score_rows: list[dict] = []
    for record in scores:
        summary = record["score_summary"]
        score_rows.append(
            {
                "arm": record["arm"],
                "model": record["model"],
                "run": str(record["run"]),
                "prompt_version": record.get("prompt_version", ""),
                "n_rows": str(summary["n_rows"]),
                "accuracy_coverage": _fmt(summary["accuracy"]["coverage"].get("value")),
                "accuracy_coverage_annotation": summary["accuracy"]["coverage"].get(
                    "annotation", ""
                ),
                "accuracy_precision": _fmt(summary["accuracy"]["precision"].get("value")),
                "accuracy_precision_annotation": summary["accuracy"]["precision"].get(
                    "annotation", ""
                ),
                "accuracy_f1": _fmt(summary["accuracy"]["f1"].get("value")),
                "accuracy_f1_annotation": summary["accuracy"]["f1"].get("annotation", ""),
                "accuracy_fuel": _fmt(summary["accuracy"]["fuel"].get("value")),
                "accuracy_fuel_annotation": summary["accuracy"]["fuel"].get("annotation", ""),
                "accuracy_status": _fmt(summary["accuracy"]["status"].get("value")),
                "accuracy_status_annotation": summary["accuracy"]["status"].get("annotation", ""),
                "accuracy_province": _fmt(summary["accuracy"]["province"].get("value")),
                "accuracy_province_annotation": summary["accuracy"]["province"].get(
                    "annotation", ""
                ),
                "coherence_vocab_adherence": _fmt(
                    summary["coherence"]["vocab_adherence"].get("value")
                ),
                "coherence_vocab_adherence_annotation": summary["coherence"][
                    "vocab_adherence"
                ].get("annotation", ""),
                # Defensive .get on the two newer coherence fields: marts written
                # before the status_vocab_adherence/capacity_nonnegative split lack
                # these keys. Tolerate their absence (empty cell) rather than
                # KeyError, so the view builds against pre-schema committed marts
                # until they are regenerated with full data. See ticket below.
                "coherence_status_vocab_adherence": _fmt(
                    summary["coherence"].get("status_vocab_adherence", {}).get("value")
                ),
                "coherence_status_vocab_adherence_annotation": summary["coherence"]
                .get("status_vocab_adherence", {})
                .get("annotation", ""),
                "coherence_capacity_nonnegative": _fmt(
                    summary["coherence"].get("capacity_nonnegative", {}).get("value")
                ),
                "coherence_capacity_nonnegative_annotation": summary["coherence"]
                .get("capacity_nonnegative", {})
                .get("annotation", ""),
                "provenance_source_presence": _fmt(
                    summary["provenance"]["source_presence"].get("value")
                ),
                "provenance_source_presence_annotation": summary["provenance"][
                    "source_presence"
                ].get("annotation", ""),
                "provenance_high_conf_dual_source": _fmt(
                    summary["provenance"]["high_conf_dual_source"].get("value")
                ),
                "provenance_high_conf_dual_source_annotation": summary["provenance"][
                    "high_conf_dual_source"
                ].get("annotation", ""),
                "temporality_asof_presence": _fmt(
                    summary["temporality"]["asof_presence"].get("value")
                ),
                "temporality_asof_presence_annotation": summary["temporality"][
                    "asof_presence"
                ].get("annotation", ""),
                "temporality_plausible_range": _fmt(
                    summary["temporality"]["plausible_range"].get("value")
                ),
                "temporality_plausible_range_annotation": summary["temporality"][
                    "plausible_range"
                ].get("annotation", ""),
                "field_completeness_core": _fmt(
                    summary["field_completeness"]["core"].get("value")
                ),
                "field_completeness_core_annotation": summary["field_completeness"]["core"].get(
                    "annotation", ""
                ),
                "field_completeness_capacity": _fmt(
                    summary["field_completeness"]["capacity"].get("value")
                ),
                "field_completeness_capacity_annotation": summary["field_completeness"][
                    "capacity"
                ].get("annotation", ""),
            }
        )

    run_rows.sort(key=lambda row: (row["arm"], row["agent"], row["run"]))
    bib_rows.sort(key=lambda row: (row["arm"], row["agent"], row["run"]))
    turn_rows.sort(key=lambda row: (row["arm"], row["agent"], row["run"], row["turn"]))
    score_rows.sort(key=lambda row: (row["arm"], row["model"], int(row["run"])))

    return {
        "tab_exp2_arms_runs_view.csv": run_rows,
        "tab_exp2_bib_quality_view.csv": bib_rows,
        "exp2_turn_trajectory_view.csv": turn_rows,
        "sota_cross_eval_view.csv": score_rows,
    }


def write_exp2_mart_views(
    mart_path: Path, output_dir: Path, repo_root: Path | None = None
) -> dict[str, Path]:
    views = build_exp2_mart_views(mart_path, repo_root=repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "tab_exp2_arms_runs_view.csv": output_dir / "tab_exp2_arms_runs_view.csv",
        "tab_exp2_bib_quality_view.csv": output_dir / "tab_exp2_bib_quality_view.csv",
        "exp2_turn_trajectory_view.csv": output_dir / "exp2_turn_trajectory_view.csv",
        "sota_cross_eval_view.csv": output_dir / "sota_cross_eval_view.csv",
    }

    for filename, path in outputs.items():
        rows = views[filename]
        fieldnames = (
            _ARMS_RUNS_FIELDS
            if filename == "tab_exp2_arms_runs_view.csv"
            else (
                _BIB_FIELDS
                if filename == "tab_exp2_bib_quality_view.csv"
                else (
                    _TURN_FIELDS
                    if filename == "exp2_turn_trajectory_view.csv"
                    else _SCORE_VIEW_FIELDS
                )
            )
        )
        _write_csv(path, fieldnames, rows)
        log.info("Wrote %d rows to %s", len(rows), path)
    return outputs


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Build CSV views from the Exp2 mart JSONL")
    parser.add_argument("--mart-jsonl", required=True)
    parser.add_argument("--output-dir", default=str(_DEFAULT_OUTPUT_DIR))
    parser.add_argument("--repo-root", default=str(Path.cwd()))
    args = parser.parse_args(argv)

    write_exp2_mart_views(
        Path(args.mart_jsonl),
        Path(args.output_dir),
        repo_root=Path(args.repo_root),
    )


if __name__ == "__main__":
    main()
