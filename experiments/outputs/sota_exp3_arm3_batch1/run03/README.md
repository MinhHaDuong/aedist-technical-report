# Overview

This directory was patched on 2026-05-25 after a classifier rerun for Exp3 Arm3 (Anthropic).

# Summary

- Original artifact state: `classification = no_report` in `anthropic.json` and `summary.json`.
- Rerun command (with project `.env` loaded) classified `run03/anthropic.md` as `report`.
- The local artifacts were updated in place to match the rerun verdict.

# Notes

- Rerun context: `uv run` with `OPENROUTER_API_KEY` from project `.env`.
- This patch changed classification labels only; model output text and cost fields were kept as recorded.
- Related directory patched in the same operation: `run04`.
