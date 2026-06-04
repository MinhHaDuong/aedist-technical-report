"""Build the Exp2 mart JSONL artifact from immutable run outputs.

Pipeline phase: P2 (score & consolidate) — invoked by experiments/derived/score.mk.
"""

import argparse
import csv
import hashlib
import json
import logging
import re
from pathlib import Path

from .exp2_mart import (
    AccuracyMetrics,
    ArtifactPointer,
    CoherenceMetrics,
    Exp2ProbeMartRecord,
    Exp2RunMartRecord,
    Exp2ScoreMartRecord,
    FieldCompletenessMetrics,
    MetricValue,
    ProbeSummary,
    ProvenanceMetrics,
    RunSummary,
    ScoreSummary,
    TemporalityMetrics,
)
from .extract import count_best_table_rows
from .score_ingest import IngestionError, IngestionErrorKind, RunLocator, ingest_run

log = logging.getLogger(__name__)

_DEFAULT_NAIVE_DIR = Path("experiments/outputs/sota_exp2_naive_arm")
_DEFAULT_OPTIMISED_DIR = Path("experiments/outputs/sota_exp2_brerun1")
_DEFAULT_ARM3_DIR = Path("experiments/derived/arm3_flat")
_DEFAULT_ARM4_DIR = Path("experiments/derived/arm4_flat")
_DEFAULT_CROSS_EVAL = Path("experiments/derived/sota_cross_eval.csv")

# Single-turn arms emit one turn; multi-turn arms leave turns unset unless the
# run metadata records it explicitly.
_SINGLE_TURN_ARMS = {"naive", "arm3"}
_DEFAULT_OUTPUT = Path("report/inputs/generated/exp2_mart.jsonl")
_RUN_RE = re.compile(r"^([a-z]+)_run(\d+)\.json$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pointer(path: Path, repo_root: Path) -> ArtifactPointer:
    relative_path = path.relative_to(repo_root)
    return ArtifactPointer(path=relative_path.as_posix(), sha256=_sha256(path))


def _resolve_repo_path(repo_root: Path, value: Path | None, default: Path) -> Path:
    candidate = default if value is None else value
    return candidate if candidate.is_absolute() else repo_root / candidate


def _record_id(arm: str, model: str, run: int, suffix: str = "") -> str:
    safe_model = model.replace("/", "_")
    base = f"exp2/{arm}/{safe_model}/run{run:02d}"
    return f"{base}/{suffix}" if suffix else base


def _metric(value: str | None, annotation: str | None) -> MetricValue:
    token = (value or "").strip()
    parsed = float(token) if token else None
    return MetricValue(value=parsed, annotation=(annotation or "").strip())


def _score_summary(row: dict[str, str]) -> ScoreSummary:
    return ScoreSummary(
        n_rows=int(row["n_rows"]),
        accuracy=AccuracyMetrics(
            coverage=_metric(
                row.get("accuracy_coverage"), row.get("accuracy_coverage_annotation")
            ),
            precision=_metric(
                row.get("accuracy_precision"), row.get("accuracy_precision_annotation")
            ),
            f1=_metric(row.get("accuracy_f1"), row.get("accuracy_f1_annotation")),
            fuel=_metric(row.get("accuracy_fuel"), row.get("accuracy_fuel_annotation")),
            status=_metric(row.get("accuracy_status"), row.get("accuracy_status_annotation")),
            province=_metric(
                row.get("accuracy_province"), row.get("accuracy_province_annotation")
            ),
        ),
        coherence=CoherenceMetrics(
            vocab_adherence=_metric(
                row.get("coherence_vocab_adherence"),
                row.get("coherence_vocab_adherence_annotation"),
            ),
            status_vocab_adherence=_metric(
                row.get("coherence_status_vocab_adherence"),
                row.get("coherence_status_vocab_adherence_annotation"),
            ),
            capacity_nonnegative=_metric(
                row.get("coherence_capacity_nonnegative"),
                row.get("coherence_capacity_nonnegative_annotation"),
            ),
        ),
        provenance=ProvenanceMetrics(
            source_presence=_metric(
                row.get("provenance_source_presence"),
                row.get("provenance_source_presence_annotation"),
            ),
            high_conf_dual_source=_metric(
                row.get("provenance_high_conf_dual_source"),
                row.get("provenance_high_conf_dual_source_annotation"),
            ),
        ),
        temporality=TemporalityMetrics(
            asof_presence=_metric(
                row.get("temporality_asof_presence"),
                row.get("temporality_asof_presence_annotation"),
            ),
            plausible_range=_metric(
                row.get("temporality_plausible_range"),
                row.get("temporality_plausible_range_annotation"),
            ),
        ),
        field_completeness=FieldCompletenessMetrics(
            core=_metric(
                row.get("field_completeness_core"), row.get("field_completeness_core_annotation")
            ),
            capacity=_metric(
                row.get("field_completeness_capacity"),
                row.get("field_completeness_capacity_annotation"),
            ),
        ),
    )


def _load_score_rows(
    csv_path: Path,
) -> tuple[
    dict[tuple[str, str, int], dict[str, str]],
    dict[tuple[str, int], list[dict[str, str]]],
    dict[tuple[str, str, int], list[dict[str, str]]],
]:
    rows: dict[tuple[str, str, int], dict[str, str]] = {}
    rows_by_arm_run: dict[tuple[str, int], list[dict[str, str]]] = {}
    rows_by_arm_agent_run: dict[tuple[str, str, int], list[dict[str, str]]] = {}

    def infer_agent(model: str) -> str | None:
        token = model.lower()
        if "claude" in token or "anthropic" in token:
            return "anthropic"
        if "gpt" in token or "openai" in token:
            return "openai"
        if "mistral" in token:
            return "mistral"
        if "qwen" in token:
            return "qwen"
        return None

    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            key = (row["arm"], row["model"], int(row["run"]))
            rows[key] = row
            rows_by_arm_run.setdefault((row["arm"], int(row["run"])), []).append(row)
            agent = infer_agent(row["model"])
            if agent is not None:
                rows_by_arm_agent_run.setdefault((row["arm"], agent, int(row["run"])), []).append(
                    row
                )
    return rows, rows_by_arm_run, rows_by_arm_agent_run


def _resolve_score_row(
    arm: str,
    agent: str,
    model: str,
    run: int,
    score_rows: dict[tuple[str, str, int], dict[str, str]],
    rows_by_arm_agent_run: dict[tuple[str, str, int], list[dict[str, str]]],
) -> dict[str, str] | None:
    exact = score_rows.get((arm, model, run))
    if exact is not None:
        return exact

    by_agent = rows_by_arm_agent_run.get((arm, agent, run), [])
    if len(by_agent) == 1:
        return by_agent[0]
    return None


def _build_run_records(
    arm_dir: Path,
    arm: str,
    *,
    repo_root: Path,
    naive_dir: Path,
    optimised_dir: Path,
    arm3_dir: Path,
    arm4_dir: Path,
) -> list[Exp2RunMartRecord]:
    records: list[Exp2RunMartRecord] = []
    for json_path in sorted(arm_dir.glob("*.json")):
        match = _RUN_RE.match(json_path.name)
        if not match:
            continue
        agent, run_raw = match.groups()
        run = int(run_raw)
        meta = json.loads(json_path.read_text(encoding="utf-8"))
        # Some run summaries carry model=null (extraction-side artifact); fall
        # back to the agent name so the record stays valid and is still grouped
        # with its arm. The mechanical scorer skips these (no model to resolve),
        # so they appear as run records without a paired score record.
        model = meta.get("model") or agent
        locator = RunLocator(arm=arm, model=model, run=run)
        md_path = json_path.with_suffix(".md")
        md_text = md_path.read_text(encoding="utf-8", errors="replace")
        legacy_n_rows = count_best_table_rows(md_text)

        try:
            ingest_run(
                locator,
                naive_dir=naive_dir,
                optimised_dir=optimised_dir,
                arm3_dir=arm3_dir,
                arm4_dir=arm4_dir,
            )
        except IngestionError as exc:
            # Some runs have empty or non-canonical markdown tables, or carry an
            # unresolvable model field. Fall back to the legacy row counter used
            # by tabulate_exp2_arms_runs.
            if exc.kind in {
                IngestionErrorKind.NO_TABLE,
                IngestionErrorKind.PARSE_FAILED,
                IngestionErrorKind.RUN_NOT_FOUND,
                IngestionErrorKind.AMBIGUOUS_RUN,
            }:
                pass
            else:
                raise

        records.append(
            Exp2RunMartRecord(
                record_id=_record_id(arm, model, run),
                arm=arm,
                agent=agent,
                model=model,
                run=run,
                prompt_version=meta.get("prompt_version"),
                run_summary=RunSummary(
                    n_rows=legacy_n_rows,
                    classification=meta.get("classification"),
                    turns=meta.get("turns", 1 if arm in _SINGLE_TURN_ARMS else None),
                    tokens_out=meta.get("tokens_out"),
                    wall_s=meta.get("wall_s"),
                    cost_usd=meta.get("cost_usd", meta.get("total_cost_usd")),
                    classifier_cost_usd=meta.get("classifier_cost_usd"),
                    narrative_chars=meta.get("narrative_chars"),
                ),
                result_file=_pointer(json_path, repo_root),
                parsed_table_file=_pointer(md_path, repo_root),
            )
        )
    return records


def _build_probe_records(
    arm_dir: Path,
    arm: str,
    *,
    repo_root: Path,
) -> list[Exp2ProbeMartRecord]:
    records: list[Exp2ProbeMartRecord] = []
    probes_dir = arm_dir / "probes"
    if not probes_dir.exists():
        return records

    for run_dir in sorted(p for p in probes_dir.iterdir() if p.is_dir()):
        match = re.match(r"^([a-z]+)_run(\d+)$", run_dir.name)
        if not match:
            continue
        agent, run_raw = match.groups()
        run = int(run_raw)
        run_json_path = arm_dir / f"{agent}_run{run:02d}.json"
        if not run_json_path.exists():
            continue
        meta = json.loads(run_json_path.read_text(encoding="utf-8"))

        for raw_path in sorted(run_dir.glob(f"{agent}_turn_*.raw.json")):
            turn_match = re.search(r"_turn_(\d+)\.raw\.json$", raw_path.name)
            if turn_match is None:
                continue
            turn = int(turn_match.group(1))
            cls_path = raw_path.with_name(
                raw_path.name.replace(".raw.json", ".classification.json")
            )
            probe_label = None
            if cls_path.exists():
                cls_payload = json.loads(cls_path.read_text(encoding="utf-8"))
                probe_label = cls_payload.get("class")

            records.append(
                Exp2ProbeMartRecord(
                    record_id=_record_id(arm, meta.get("model", agent), run, f"turn{turn:02d}"),
                    parent_record_id=_record_id(arm, meta.get("model", agent), run),
                    arm=arm,
                    agent=agent,
                    model=meta.get("model", ""),
                    run=run,
                    prompt_version=meta.get("prompt_version"),
                    probe_summary=ProbeSummary(turn=turn, probe_label=probe_label),
                    probe_file=_pointer(raw_path, repo_root),
                )
            )

    return records


def build_exp2_mart(
    naive_dir: Path | None = None,
    optimised_dir: Path | None = None,
    cross_eval_csv: Path | None = None,
    repo_root: Path | None = None,
    arm3_dir: Path | None = None,
    arm4_dir: Path | None = None,
) -> list[Exp2RunMartRecord | Exp2ScoreMartRecord]:
    repo_root = (repo_root or Path.cwd()).resolve()
    naive_dir = _resolve_repo_path(repo_root, naive_dir, _DEFAULT_NAIVE_DIR)
    optimised_dir = _resolve_repo_path(repo_root, optimised_dir, _DEFAULT_OPTIMISED_DIR)
    arm3_dir = _resolve_repo_path(repo_root, arm3_dir, _DEFAULT_ARM3_DIR)
    arm4_dir = _resolve_repo_path(repo_root, arm4_dir, _DEFAULT_ARM4_DIR)
    cross_eval_csv = _resolve_repo_path(repo_root, cross_eval_csv, _DEFAULT_CROSS_EVAL)
    score_rows, _rows_by_arm_run, rows_by_arm_agent_run = _load_score_rows(cross_eval_csv)
    records: list[Exp2RunMartRecord | Exp2ScoreMartRecord] = []

    for arm, arm_dir in (
        ("naive", naive_dir),
        ("optimised", optimised_dir),
        ("arm3", arm3_dir),
        ("arm4", arm4_dir),
    ):
        for run_record in _build_run_records(
            arm_dir,
            arm,
            repo_root=repo_root,
            naive_dir=naive_dir,
            optimised_dir=optimised_dir,
            arm3_dir=arm3_dir,
            arm4_dir=arm4_dir,
        ):
            records.append(run_record)
            score_row = _resolve_score_row(
                run_record.arm,
                run_record.agent,
                run_record.model,
                run_record.run,
                score_rows,
                rows_by_arm_agent_run,
            )
            if score_row is None:
                continue
            records.append(
                Exp2ScoreMartRecord(
                    record_id=_record_id(
                        run_record.arm, run_record.model, run_record.run, "score"
                    ),
                    parent_record_id=run_record.record_id,
                    arm=run_record.arm,
                    agent=run_record.agent,
                    model=run_record.model,
                    run=run_record.run,
                    prompt_version=score_row.get("prompt_version") or run_record.prompt_version,
                    score_summary=_score_summary(score_row),
                    result_file=run_record.result_file,
                    parsed_table_file=run_record.parsed_table_file,
                )
            )
        records.extend(_build_probe_records(arm_dir, arm, repo_root=repo_root))

    records.sort(key=lambda record: (record.arm, record.model, record.run, record.record_kind))
    return records


def write_exp2_mart(
    output: Path,
    naive_dir: Path | None = None,
    optimised_dir: Path | None = None,
    cross_eval_csv: Path | None = None,
    repo_root: Path | None = None,
    arm3_dir: Path | None = None,
    arm4_dir: Path | None = None,
) -> list[Exp2RunMartRecord | Exp2ScoreMartRecord]:
    records = build_exp2_mart(
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
        cross_eval_csv=cross_eval_csv,
        repo_root=repo_root,
        arm3_dir=arm3_dir,
        arm4_dir=arm4_dir,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record.model_dump_json())
            handle.write("\n")
    return records


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Build the Exp2 mart JSONL artifact")
    parser.add_argument("--output")
    parser.add_argument("--naive-dir")
    parser.add_argument("--optimised-dir")
    parser.add_argument("--arm3-dir")
    parser.add_argument("--arm4-dir")
    parser.add_argument("--cross-eval-csv")
    parser.add_argument("--repo-root")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path.cwd().resolve()
    output = _resolve_repo_path(
        repo_root, Path(args.output) if args.output else None, _DEFAULT_OUTPUT
    )
    naive_dir = _resolve_repo_path(
        repo_root, Path(args.naive_dir) if args.naive_dir else None, _DEFAULT_NAIVE_DIR
    )
    optimised_dir = _resolve_repo_path(
        repo_root,
        Path(args.optimised_dir) if args.optimised_dir else None,
        _DEFAULT_OPTIMISED_DIR,
    )
    arm3_dir = _resolve_repo_path(
        repo_root, Path(args.arm3_dir) if args.arm3_dir else None, _DEFAULT_ARM3_DIR
    )
    arm4_dir = _resolve_repo_path(
        repo_root, Path(args.arm4_dir) if args.arm4_dir else None, _DEFAULT_ARM4_DIR
    )
    cross_eval_csv = _resolve_repo_path(
        repo_root,
        Path(args.cross_eval_csv) if args.cross_eval_csv else None,
        _DEFAULT_CROSS_EVAL,
    )

    records = write_exp2_mart(
        output,
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
        cross_eval_csv=cross_eval_csv,
        repo_root=repo_root,
        arm3_dir=arm3_dir,
        arm4_dir=arm4_dir,
    )
    log.info("Wrote %d mart records to %s", len(records), output)


if __name__ == "__main__":
    main()
