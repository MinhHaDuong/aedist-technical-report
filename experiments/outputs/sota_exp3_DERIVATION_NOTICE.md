# EXP3 Snapshot (Raw, JSON, and Derived Ledgers)

Date: 2026-05-25

This notice defines the provenance policy for EXP3 artifacts under `sota_exp3_*`.

Rules:
- Canonical evidence for provenance/scoring is in raw provider payloads and raw prompts.
- Runtime JSON metadata (for example `*_phase_a.json`, `*_turn_*.record.json`) is derived from raw payloads and is kept for reproducibility.
- Run ledger `summary.json` is derived and represents the latest run state for that run directory.
- Timestamped `summary_*.md` files are derived append-only audit snapshots and must be kept in git.
- `summary_*.md` snapshots are not canonical scientific evidence, but are required for audit recovery when `summary.json` is overwritten by reruns.
- Narrative markdown reports can be regenerated ex post from raw payloads via a dedicated extractor.
