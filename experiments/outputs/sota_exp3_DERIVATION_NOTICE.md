# EXP3 Snapshot (Raw/JSON Only)

Date: 2026-05-25

This commit intentionally snapshots EXP3 outputs as raw provider payloads and JSON metadata only.

Rules:
- No EXP3 `.md` artifacts are included at snapshot step 1.
- Canonical evidence for provenance/scoring is in raw provider payloads and JSON files.
- Narrative markdown must be regenerated ex post from raw payloads via a dedicated extractor.
