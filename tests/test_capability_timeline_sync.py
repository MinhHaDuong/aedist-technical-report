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
