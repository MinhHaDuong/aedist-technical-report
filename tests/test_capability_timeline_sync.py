import csv
import re
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
CSV_PATH = REPO / "data" / "capability_timeline.csv"
MD_PATH = REPO / "docs" / "capability-timeline.md"

# (lab, stage) pairs where the CSV date is approximate and the prose
# intentionally shows only month/year rather than the full ISO date.
APPROXIMATE_DATE_PAIRS = {
    ("OpenAI", "8"),  # 2025-03-01 shown as "2025-03" (day unverifiable)
}


@pytest.mark.adherence
def test_csv_dates_present_in_prose():
    """Every non-absent date in capability_timeline.csv must appear verbatim
    in docs/capability-timeline.md (the prose matrix).  This catches silent
    drift when one file is updated without the other."""
    md_text = MD_PATH.read_text()
    mismatches = []

    with CSV_PATH.open() as f:
        for row in csv.DictReader(f):
            lab = row["lab"]
            stage = row["stage"]
            date = row["date"].strip()
            if not date or date.lower() == "absent":
                continue
            if (lab, stage) in APPROXIMATE_DATE_PAIRS:
                # Check month prefix only (YYYY-MM)
                month_prefix = date[:7]
                pattern = re.escape(month_prefix)
            else:
                pattern = re.escape(date)
            if not re.search(pattern, md_text):
                mismatches.append(f"{lab} stage {stage}: date '{date}' not found in prose")

    assert not mismatches, "CSV dates missing from docs/capability-timeline.md:\n" + "\n".join(
        f"  {m}" for m in mismatches
    )


@pytest.mark.adherence
def test_stage_numbers_match_csv():
    """Every **N. label** header in the prose matrix must match the CSV's
    (stage, stage_name) pair.  Catches numbering drift between the figure
    y-axis and the docs.  Ratified 2026-06-03: CSV chronological order is
    canonical."""
    csv_stages: dict[int, str] = {}
    with CSV_PATH.open() as f:
        for row in csv.DictReader(f):
            n = int(row["stage"])
            csv_stages[n] = row["stage_name"]

    md_text = MD_PATH.read_text()
    prose_headers = re.findall(r"\*\*(\d+)\.\s+([^*]+?)\*\*", md_text)
    assert prose_headers, "no **N. label** headers found in the prose matrix"

    mismatches = []
    for num_str, label in prose_headers:
        num = int(num_str)
        label_clean = label.strip().rstrip("—").strip()
        csv_name = csv_stages.get(num)
        if csv_name is None:
            mismatches.append(f"prose has stage {num} ({label_clean}) but CSV has no stage {num}")
        elif not csv_name.startswith(label_clean) and not label_clean.startswith(csv_name):
            mismatches.append(f"stage {num}: prose='{label_clean}' vs CSV='{csv_name}'")

    assert not mismatches, (
        "Prose matrix headers do not match CSV stage numbering "
        "(canonical = CSV chronological order):\n" + "\n".join(f"  {m}" for m in mismatches)
    )


@pytest.mark.adherence
def test_no_inline_stage_numbers_outside_blockquote():
    """Inline 'stage N' references outside the historical blockquote must not
    carry the argument — the PR decouples prose from numbers.  Any surviving
    'stage N' (case-insensitive) outside the blockquote is drift risk.

    Allowed zones:
    - Lines starting with '>' (the historical edit-note blockquote)
    - **N. label** bold headers (already covered by test_stage_numbers_match_csv)
    """
    md_text = MD_PATH.read_text()
    violations = []
    for i, line in enumerate(md_text.splitlines(), 1):
        if line.lstrip().startswith(">"):
            continue
        stripped = line.lstrip("| ")
        if stripped.startswith("**") and re.match(r"\*\*\d+\.", stripped):
            continue
        hits = re.findall(r"[Ss]tages?[\s-]+\d+", line)
        if hits:
            violations.append(f"  line {i}: {hits} — {line.strip()[:80]}")

    assert not violations, (
        "Inline stage-number references found outside the blockquote.\n"
        "Use capability names instead of stage numbers in prose:\n" + "\n".join(violations)
    )
