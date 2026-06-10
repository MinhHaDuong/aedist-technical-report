"""Ticket 0515 — §6 arm-1D equalization claim guarded against the 2×2 artifact.

The reopened ticket reframed the earlier (cut) "RAG rescues cheaper models"
idea: judged on the *delta* arm0→arm1D rather than absolute F1, the data shows
*equalization*. With documents in single-shot mode (arm 1D), the weakest agents
rise toward the cohort — three of four converge near ~0.61 — while a strong
model (OpenAI) keeps headroom. The cohort spread narrows.

Each number in the §6 equalization sentence is re-derived here from the
committed ``experiments/derived/tab_exp2_2x2.csv`` by an independent parse, at
the manuscript's 2-decimal rounding, then asserted present in main.md. The
guard is the CSV re-derivation, not the literal-phrasing absence: "rescues
cheaper models" was already removed by ticket 0512, so this test adds the claim
rather than swapping it.
"""

import csv
from pathlib import Path

import pytest

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_MD = REPO_ROOT / "slides" / "manuscript" / "main.md"
CSV_2X2 = REPO_ROOT / "experiments" / "derived" / "tab_exp2_2x2.csv"


def _md() -> str:
    if not MAIN_MD.exists():
        pytest.skip("main.md not found")
    return MAIN_MD.read_text(encoding="utf-8")


def _section6(md: str) -> str:
    start = md.index("## 6. Experiment 2")
    end = md.index("## 7.", start)
    return md[start:end]


def _f1_by_arm() -> tuple[dict[str, float], dict[str, float]]:
    """Return (naive_f1, arm3_f1) keyed by agent, from the committed 2×2 CSV."""
    rows = list(csv.DictReader(CSV_2X2.open(encoding="utf-8")))
    naive = {r["agent"]: float(r["f1_mean"]) for r in rows if r["arm"] == "naive"}
    arm3 = {r["agent"]: float(r["f1_mean"]) for r in rows if r["arm"] == "arm3"}
    assert naive and arm3, "2×2 CSV missing naive or arm3 rows"
    return naive, arm3


def test_section6_equalization_numbers_match_artifact():
    md = _md()
    sec = _section6(md)
    naive, arm3 = _f1_by_arm()

    # The two weakest naive agents (qwen, mistral) and their arm-1D recovery.
    # Numbers cited at the manuscript's 2-dp rounding (matching Table 1).
    qwen_naive, qwen_1d = round(naive["qwen"], 2), round(arm3["qwen"], 2)
    mistral_naive, mistral_1d = round(naive["mistral"], 2), round(arm3["mistral"], 2)
    assert f"{qwen_naive:.2f}".rstrip("0").rstrip(".") in sec or f"{qwen_naive:.2f}" in sec
    # Explicit pair literals: "0.37 to 0.62" (qwen), "0.49 to 0.59" (mistral).
    assert f"{qwen_naive:.2f}" in sec, f"qwen naive {qwen_naive:.2f} missing from §6"
    assert f"{qwen_1d:.2f}" in sec, f"qwen 1D {qwen_1d:.2f} missing from §6"
    assert f"{mistral_naive:.2f}" in sec, f"mistral naive {mistral_naive:.2f} missing from §6"
    assert f"{mistral_1d:.2f}" in sec, f"mistral 1D {mistral_1d:.2f} missing from §6"

    # Spread (max-min) narrows naive -> 1D.
    naive_spread = round(max(naive.values()) - min(naive.values()), 2)
    arm3_spread = round(max(arm3.values()) - min(arm3.values()), 2)
    assert naive_spread > arm3_spread, "spread does not narrow — equalization not in data"
    assert f"{naive_spread:.2f}" in sec, f"naive spread {naive_spread:.2f} missing from §6"
    assert f"{arm3_spread:.2f}" in sec, f"1D spread {arm3_spread:.2f} missing from §6"


def test_section6_equalization_is_scoped_to_single_shot_docs():
    """Multi-turn+docs (arm4) hurts (e.g. Anthropic 0.61->0.38), so the claim
    must name the single-shot/documents (1D) condition, not 'docs' in general."""
    sec = _section6(_md())
    lowered = sec.lower()
    assert "equalis" in lowered or "converg" in lowered, "no equalization framing in §6"
    assert "1d" in lowered or "single-shot" in lowered, "equalization not scoped to 1D"


def test_data_supports_equalization_weak_models_gain_most():
    """Independent check that the artifact actually supports the claim: the two
    weakest naive agents post the largest arm0->arm1D deltas."""
    naive, arm3 = _f1_by_arm()
    deltas = {a: arm3[a] - naive[a] for a in naive}
    weakest_two = sorted(naive, key=naive.get)[:2]
    strongest_two = sorted(naive, key=naive.get)[-2:]
    # qwen and mistral are the weakest naive performers.
    assert set(weakest_two) == {"qwen", "mistral"}
    min_weak_delta = min(deltas[a] for a in weakest_two)
    # The smallest weak-model gain exceeds the smallest strong-model gain.
    assert min_weak_delta > min(deltas[a] for a in strongest_two)
