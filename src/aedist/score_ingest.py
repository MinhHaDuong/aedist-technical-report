"""Run-ingestion helpers for mechanical scoring.

Resolves Exp2 run outputs from `(arm, model, run)` metadata, extracts the best
plant table from the paired markdown report, and returns canonical row dicts for
downstream scoring.
"""

import csv
import enum
import io
import json
from dataclasses import dataclass
from pathlib import Path

from .extract import _extract_pipe_tables, parse_and_canonicalize, score_csv_like_block

_DEFAULT_NAIVE_DIR = Path("experiments/outputs/sota_exp3_arm1_batch1")
_DEFAULT_OPTIMISED_DIR = Path("experiments/outputs/sota_exp2_brerun1")


class IngestionErrorKind(enum.Enum):
    UNKNOWN_ARM = "unknown_arm"
    RUN_NOT_FOUND = "run_not_found"
    AMBIGUOUS_RUN = "ambiguous_run"
    MISSING_MARKDOWN = "missing_markdown"
    INVALID_ENCODING = "invalid_encoding"
    NO_TABLE = "no_table"
    PARSE_FAILED = "parse_failed"
    INVALID_PARITY_ROW = "invalid_parity_row"


@dataclass
class RunLocator:
    arm: str
    model: str
    run: int


@dataclass
class ResolvedRunPaths:
    json_path: Path
    markdown_path: Path


@dataclass
class IngestedRun:
    locator: RunLocator
    json_path: Path
    markdown_path: Path
    rows: list[dict[str, str]]


@dataclass
class ParityDiagnostic:
    locator: RunLocator
    expected_rows: int
    observed_rows: int
    matches: bool
    message: str


class IngestionError(RuntimeError):
    def __init__(self, kind: IngestionErrorKind, locator: RunLocator, detail: str):
        self.kind = kind
        self.locator = locator
        self.detail = detail
        super().__init__(f"{kind.value}: {detail}")


def _arm_dir(arm: str, naive_dir: Path, optimised_dir: Path) -> Path:
    if arm == "naive":
        return naive_dir
    if arm == "optimised":
        return optimised_dir
    raise IngestionError(
        IngestionErrorKind.UNKNOWN_ARM,
        RunLocator(arm=arm, model="", run=0),
        f"unknown arm '{arm}'",
    )


def resolve_run_paths(
    locator: RunLocator,
    *,
    naive_dir: Path = _DEFAULT_NAIVE_DIR,
    optimised_dir: Path = _DEFAULT_OPTIMISED_DIR,
) -> ResolvedRunPaths:
    arm_dir = _arm_dir(locator.arm, naive_dir, optimised_dir)
    pattern = f"*_run{locator.run:02d}.json"
    matches: list[Path] = []
    for json_path in sorted(arm_dir.glob(pattern)):
        meta = json.loads(json_path.read_text(encoding="utf-8"))
        if meta.get("model") == locator.model:
            matches.append(json_path)

    if not matches:
        raise IngestionError(
            IngestionErrorKind.RUN_NOT_FOUND,
            locator,
            f"no {locator.arm} run found for model={locator.model!r} run={locator.run}",
        )
    if len(matches) > 1:
        raise IngestionError(
            IngestionErrorKind.AMBIGUOUS_RUN,
            locator,
            f"multiple run files matched: {[path.name for path in matches]}",
        )

    json_path = matches[0]
    markdown_path = json_path.with_suffix(".md")
    if not markdown_path.exists():
        raise IngestionError(
            IngestionErrorKind.MISSING_MARKDOWN,
            locator,
            f"missing markdown report {markdown_path.name}",
        )
    return ResolvedRunPaths(json_path=json_path, markdown_path=markdown_path)


def ingest_run(
    locator: RunLocator,
    *,
    naive_dir: Path = _DEFAULT_NAIVE_DIR,
    optimised_dir: Path = _DEFAULT_OPTIMISED_DIR,
) -> IngestedRun:
    resolved = resolve_run_paths(locator, naive_dir=naive_dir, optimised_dir=optimised_dir)
    try:
        text = resolved.markdown_path.read_text(encoding="utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise IngestionError(
            IngestionErrorKind.INVALID_ENCODING,
            locator,
            f"invalid UTF-8 in markdown report {resolved.markdown_path.name}",
        ) from exc
    candidates = _extract_pipe_tables(text)
    if not candidates:
        raise IngestionError(
            IngestionErrorKind.NO_TABLE,
            locator,
            f"no markdown pipe tables found in {resolved.markdown_path.name}",
        )

    best = max(candidates, key=score_csv_like_block)
    try:
        canonical_csv = parse_and_canonicalize(best)
    except Exception as exc:
        raise IngestionError(
            IngestionErrorKind.PARSE_FAILED,
            locator,
            f"failed to canonicalize {resolved.markdown_path.name}: {exc}",
        ) from exc

    rows = list(csv.DictReader(io.StringIO(canonical_csv)))
    return IngestedRun(
        locator=locator,
        json_path=resolved.json_path,
        markdown_path=resolved.markdown_path,
        rows=rows,
    )


def check_inventory_row_parity(
    locator: RunLocator,
    expected_rows: int,
    *,
    naive_dir: Path = _DEFAULT_NAIVE_DIR,
    optimised_dir: Path = _DEFAULT_OPTIMISED_DIR,
) -> ParityDiagnostic:
    ingested = ingest_run(locator, naive_dir=naive_dir, optimised_dir=optimised_dir)
    observed_rows = len(ingested.rows)
    matches = observed_rows == expected_rows
    if matches:
        message = (
            f"row parity OK for {locator.arm}/{locator.model}/run{locator.run:02d}: "
            f"expected={expected_rows} observed={observed_rows}"
        )
    else:
        message = (
            f"row parity mismatch for {locator.arm}/{locator.model}/run{locator.run:02d}: "
            f"expected={expected_rows} observed={observed_rows}"
        )
    return ParityDiagnostic(
        locator=locator,
        expected_rows=expected_rows,
        observed_rows=observed_rows,
        matches=matches,
        message=message,
    )


def check_inventory_row_parity_row(
    row: dict[str, str],
    *,
    naive_dir: Path = _DEFAULT_NAIVE_DIR,
    optimised_dir: Path = _DEFAULT_OPTIMISED_DIR,
) -> ParityDiagnostic:
    required = {"arm", "model", "run", "inventory_rows"}
    missing = sorted(k for k in required if not row.get(k))
    if missing:
        raise IngestionError(
            IngestionErrorKind.INVALID_PARITY_ROW,
            RunLocator(arm=row.get("arm", ""), model=row.get("model", ""), run=0),
            f"missing required parity fields: {missing}",
        )

    run_raw = row["run"].strip()
    expected_raw = row["inventory_rows"].strip()
    try:
        run = int(run_raw)
    except ValueError as exc:
        raise IngestionError(
            IngestionErrorKind.INVALID_PARITY_ROW,
            RunLocator(arm=row["arm"], model=row["model"], run=0),
            f"invalid run value {run_raw!r}; expected integer",
        ) from exc

    try:
        expected_rows = int(expected_raw)
    except ValueError as exc:
        raise IngestionError(
            IngestionErrorKind.INVALID_PARITY_ROW,
            RunLocator(arm=row["arm"], model=row["model"], run=run),
            f"invalid inventory_rows value {expected_raw!r}; expected integer",
        ) from exc

    locator = RunLocator(
        arm=row["arm"],
        model=row["model"],
        run=run,
    )
    return check_inventory_row_parity(
        locator,
        expected_rows,
        naive_dir=naive_dir,
        optimised_dir=optimised_dir,
    )


def _diagnostic_from_error(err: IngestionError) -> ParityDiagnostic:
    locator = err.locator
    return ParityDiagnostic(
        locator=RunLocator(
            arm=locator.arm or "<invalid>",
            model=locator.model or "<invalid>",
            run=locator.run,
        ),
        expected_rows=0,
        observed_rows=0,
        matches=False,
        message=f"{err.kind.value}: {err.detail}",
    )


def check_inventory_row_parity_csv(
    csv_path: Path,
    *,
    naive_dir: Path = _DEFAULT_NAIVE_DIR,
    optimised_dir: Path = _DEFAULT_OPTIMISED_DIR,
) -> list[ParityDiagnostic]:
    diagnostics: list[ParityDiagnostic] = []
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                diagnostics.append(
                    check_inventory_row_parity_row(
                        row,
                        naive_dir=naive_dir,
                        optimised_dir=optimised_dir,
                    )
                )
            except IngestionError as err:
                diagnostics.append(_diagnostic_from_error(err))
    return diagnostics
