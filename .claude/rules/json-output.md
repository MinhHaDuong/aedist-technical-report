---
paths:
  - "**/*.py"
---

# JSON output

All single-object JSON files written by this project end with exactly one trailing newline (`\n`).

**Applies to:** `*.json` output files — `json.dump()` + `f.write("\n")`, and `.write_text(json.dumps(...) + "\n")`, and `.write_text(model.model_dump_json(...) + "\n")`.

**Does not apply to:** JSONL writers (`to_jsonl_line() + "\n"` per record, no extra newline after the last line), or in-memory `json.dumps()` that is not written to a file.

**Why:** Newline-only diffs (`No newline at end of file`) are non-semantic but noisy in reviews and audits. Verified by `tests/test_json_eof_newline.py` (`@pytest.mark.adherence`).
