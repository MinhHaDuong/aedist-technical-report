"""Compare legacy Exp2 CSV intermediates against mart-derived views.

Pipeline phase: P2 (score & consolidate) — invoked by experiments/derived/score.mk.

Tolerance policy:
- row counts must match exactly
- column sets must match exactly
- numeric cells compare within max($1e-3$, $0.001 x max(1, |a|, |b|))
- non-numeric cells compare exactly after trimming whitespace
"""

import argparse
import csv
import logging
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class ParityResult:
    name: str
    ok: bool
    message: str


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _as_float(text: str) -> float | None:
    value = text.strip()
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _compare_cells(left: str, right: str) -> bool:
    left_value = _as_float(left)
    right_value = _as_float(right)
    if left_value is None or right_value is None:
        return left.strip() == right.strip()
    scale = max(1.0, abs(left_value), abs(right_value))
    return abs(left_value - right_value) <= max(1e-3, 1e-3 * scale)


def _compare_csvs(left: Path, right: Path, key_fields: list[str], name: str) -> ParityResult:
    left_rows = _load_csv(left)
    right_rows = _load_csv(right)

    if len(left_rows) != len(right_rows):
        return ParityResult(
            name, False, f"row-count mismatch: {len(left_rows)} != {len(right_rows)}"
        )

    if not left_rows and not right_rows:
        return ParityResult(name, True, "empty")

    left_fields = set(left_rows[0].keys())
    right_fields = set(right_rows[0].keys())
    if left_fields != right_fields:
        return ParityResult(
            name, False, f"column-set mismatch: {sorted(left_fields)} != {sorted(right_fields)}"
        )

    left_rows = sorted(left_rows, key=lambda row: tuple(row[field] for field in key_fields))
    right_rows = sorted(right_rows, key=lambda row: tuple(row[field] for field in key_fields))

    for index, (left_row, right_row) in enumerate(
        zip(left_rows, right_rows, strict=True), start=1
    ):
        for field in left_fields:
            if not _compare_cells(left_row[field], right_row[field]):
                return ParityResult(
                    name,
                    False,
                    f"mismatch at row {index} field {field!r}: {left_row[field]!r} != {right_row[field]!r}",
                )

    return ParityResult(name, True, "ok")


def check_parity(left_dir: Path, right_dir: Path) -> list[ParityResult]:
    specs = [
        (
            "tab_exp2_arms_runs",
            "tab_exp2_arms_runs.csv",
            "tab_exp2_arms_runs_view.csv",
            ["agent", "arm", "model", "run"],
        ),
        (
            "tab_exp2_bib_quality",
            "tab_exp2_bib_quality.csv",
            "tab_exp2_bib_quality_view.csv",
            ["agent", "arm", "run"],
        ),
        (
            "exp2_turn_trajectory",
            "exp2_turn_trajectory.csv",
            "exp2_turn_trajectory_view.csv",
            ["agent", "arm", "run", "turn"],
        ),
        (
            "sota_cross_eval",
            "sota_cross_eval.csv",
            "sota_cross_eval_view.csv",
            ["arm", "model", "run"],
        ),
    ]

    results: list[ParityResult] = []
    for name, left_name, right_name, key_fields in specs:
        left_path = left_dir / left_name
        right_path = right_dir / right_name
        if not left_path.exists():
            results.append(ParityResult(name, False, f"missing left file: {left_path}"))
            continue
        if not right_path.exists():
            results.append(ParityResult(name, False, f"missing right file: {right_path}"))
            continue
        results.append(_compare_csvs(left_path, right_path, key_fields, name))
    return results


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Compare legacy Exp2 CSV intermediates against mart views"
    )
    parser.add_argument(
        "--left-dir", required=True, help="Directory with legacy CSV intermediates"
    )
    parser.add_argument("--right-dir", required=True, help="Directory with mart-derived view CSVs")
    args = parser.parse_args(argv)

    results = check_parity(Path(args.left_dir), Path(args.right_dir))
    failures = [result for result in results if not result.ok]
    for result in results:
        log.info("%s: %s", result.name, result.message)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
