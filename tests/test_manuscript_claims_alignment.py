"""Ticket 0568 — claims/findings alignment guards.

Conditional guard (S1): IF the abstract claims that only one of the four
frontier agents improved over the memory-only query, THEN the §exp2 body
must carry the per-agent memory-vs-web comparison explicitly — one
paragraph naming all four agents, anchored to the memory/parametric
baseline, with the four before-to-after value pairs. Conditional polarity
per the 0557 test-polarity rule: nothing pins the abstract's authorial
wording; weakening the abstract dissolves the obligation (the guard then
skips).

Mechanical checks (values re-derived from committed artifacts by an
independent parse, per the 0557 polarity rule):

- the cross-experiment per-agent comparison the abstract rests on is
  re-derived from ``exp1_cross_eval.csv`` (same-lab flagship, parametric
  arm) and ``tab_exp2_2x2.csv`` (naive, no-documents arm): exactly one
  agent improves at the manuscript's 2-dp rounding;
- the §exp2 multi-turn (no-documents) deltas support "degraded for three
  of the four agents": exactly three of four naive→optimised deltas are
  negative, and the body quotes each pair at 2 dp;
- the §exp1 good-model F1 floor/ceiling literals match the
  ``plot_exp1_reliability`` gate re-applied to ``exp1_cross_eval.csv``.
"""

import csv
import re
import statistics
from pathlib import Path

import pytest
from manuscript_source import body_raw, normalized, raw, strip_comments

from aedist.plot_exp1_reliability import N_REPS, is_good_run, load_rows

pytestmark = pytest.mark.adherence

REPO_ROOT = Path(__file__).resolve().parent.parent
XEVAL_CSV = REPO_ROOT / "experiments" / "derived" / "exp1_cross_eval.csv"
CSV_2X2 = REPO_ROOT / "experiments" / "derived" / "tab_exp2_2x2.csv"

# The Exp2 agents and the same lab's flagship in the Exp1 parametric sweep.
FLAGSHIPS = {
    "anthropic": "claude-opus-4.6",
    "openai": "gpt-5.5",
    "mistral": "mistral-large-2512",
    "qwen": "qwen3.7-max",
}
AGENT_NAMES = ("Anthropic", "OpenAI", "Mistral", "Qwen")

# The abstract's coverage-story claim, in any of its phrasings. Structural
# trigger only — the guard never requires this wording to be present.
_ONLY_ONE_RE = re.compile(r"[Oo]nly one of (?:them|the four)")
# A before-to-after value pair as the manuscript quotes them: "0.41 to 0.49".
_PAIR_RE = re.compile(r"0\.\d{2} to 0\.\d{2}")


def _abstract() -> str:
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", raw(), re.DOTALL)
    assert m, "no abstract environment in main.tex"
    return normalized(m.group(1))


def _exp2_paragraphs() -> list[str]:
    """Blank-line-delimited paragraphs of §exp2, each normalized."""
    text = strip_comments(body_raw())
    start = text.find("\\label{sec:exp2}")
    assert start != -1, "no \\label{sec:exp2} in main.tex body"
    nxt = re.search(r"\\section\*?\{", text[start:])
    sec = text[start : start + nxt.start()] if nxt else text[start:]
    return [normalized(p) for p in re.split(r"\n\s*\n", sec) if p.strip()]


def _exp2_text() -> str:
    return " ".join(_exp2_paragraphs())


def _exp1_flagship_means() -> dict[str, float]:
    """Per-agent mean parametric F1 of the same lab's flagship (independent parse)."""
    if not XEVAL_CSV.exists():
        pytest.skip(f"{XEVAL_CSV} not generated")
    by_model: dict[str, list[float]] = {m: [] for m in FLAGSHIPS.values()}
    for r in csv.DictReader(XEVAL_CSV.open(encoding="utf-8")):
        if r["arm"] == "parametric" and r["model"] in by_model:
            by_model[r["model"]].append(float(r["accuracy_f1"]))
    return {agent: statistics.mean(by_model[m]) for agent, m in FLAGSHIPS.items()}


def _exp2_f1(arm: str) -> dict[str, float]:
    """Per-agent mean F1 for one no-documents arm of the 2x2 CSV."""
    if not CSV_2X2.exists():
        pytest.skip(f"{CSV_2X2} not generated")
    rows = list(csv.DictReader(CSV_2X2.open(encoding="utf-8")))
    out = {r["agent"]: float(r["f1_mean"]) for r in rows if r["arm"] == arm and r["docs"] == "no"}
    assert set(out) == set(FLAGSHIPS), f"2x2 CSV {arm}/no rows incomplete: {sorted(out)}"
    return out


def test_artifacts_support_only_one_agent_improving_over_memory():
    """Exactly one agent's naive-arm F1 beats its lab's Exp1 flagship at 2 dp —
    the data support for the abstract's coverage story, re-derived."""
    exp1 = _exp1_flagship_means()
    naive = _exp2_f1("naive")
    improved = [a for a in FLAGSHIPS if round(naive[a], 2) > round(exp1[a], 2)]
    assert len(improved) == 1, (
        f"abstract coverage story expects exactly one improving agent, "
        f"artifacts give {improved or 'none'}"
    )


def test_abstract_only_one_claim_backed_by_exp2_per_agent_comparison():
    """S1 conditional guard: the abstract's only-one-of-four claim obliges the
    §exp2 body to carry the per-agent comparison (four agent names + the
    memory/parametric anchor + the four re-derived value pairs in one
    paragraph)."""
    if not _ONLY_ONE_RE.search(_abstract()):
        pytest.skip("abstract no longer makes the only-one-of-four claim")
    anchor_re = re.compile(r"memory|parametric|\\ref\{sec:exp1\}", re.IGNORECASE)
    candidates = [
        p
        for p in _exp2_paragraphs()
        if all(name in p for name in AGENT_NAMES)
        and anchor_re.search(p)
        and len(_PAIR_RE.findall(p)) >= len(AGENT_NAMES)
    ]
    assert candidates, (
        "abstract claims only one of the four agents improved over the "
        "memory-only query, but no §exp2 paragraph carries the per-agent "
        "comparison (all four agent names, a memory/parametric baseline "
        "anchor, and four before-to-after value pairs)"
    )
    # The quoted pairs are the artifact-derived ones, at 2-dp rounding.
    exp1, naive = _exp1_flagship_means(), _exp2_f1("naive")
    para = candidates[0]
    for agent, name in zip(("anthropic", "openai", "mistral", "qwen"), AGENT_NAMES, strict=True):
        pair = f"{round(exp1[agent], 2):.2f} to {round(naive[agent], 2):.2f}"
        assert pair in para, f"{name} memory-vs-web pair {pair!r} missing from the comparison"


def test_exp2_multiturn_deltas_match_artifact_and_three_of_four_decline():
    """The multi-turn (no-documents) story: exactly three of four agents
    decline naive→optimised, and §exp2 quotes each re-derived pair."""
    naive, opt = _exp2_f1("naive"), _exp2_f1("optimised")
    declined = [a for a in FLAGSHIPS if round(opt[a], 2) < round(naive[a], 2)]
    assert len(declined) == 3, (
        f"'degraded for three of the four agents' expects 3 declines, "
        f"artifacts give {sorted(declined)}"
    )
    sec = _exp2_text()
    for agent in FLAGSHIPS:
        pair = f"{round(naive[agent], 2):.2f} to {round(opt[agent], 2):.2f}"
        assert pair in sec, f"{agent} naive→optimised pair {pair!r} missing from §exp2"


def test_exp1_good_model_f1_range_matches_gate():
    """The §exp1 'F1 means of X--Y' literal for the nine good models matches
    the reliability gate re-applied to the cross-eval artifact."""
    if not XEVAL_CSV.exists():
        pytest.skip(f"{XEVAL_CSV} not generated")
    good_f1: dict[str, list[float]] = {}
    counts: dict[str, int] = {}
    for row in load_rows(XEVAL_CSV):
        model = row["model"].strip()
        counts.setdefault(model, 0)
        if is_good_run(row):
            counts[model] += 1
            good_f1.setdefault(model, []).append(float(row["accuracy_f1"]))
    means = [
        statistics.mean(good_f1[m])
        for m, n in counts.items()
        if n >= N_REPS - 1  # the nine models with four or five good runs
    ]
    assert len(means) == 9, f"expected nine good models, gate gives {len(means)}"
    literal = f"{min(means):.2f}–{max(means):.2f}"  # normalized() folds -- to –
    text = strip_comments(body_raw())
    start = text.find("\\label{sec:exp1}")
    assert start != -1
    nxt = re.search(r"\\section\*?\{", text[start:])
    sec1 = normalized(text[start : start + nxt.start()] if nxt else text[start:])
    assert literal in sec1, (
        f"§exp1 good-model F1 range should read {literal!r} "
        f"(re-derived from {XEVAL_CSV.name} under the reliability gate)"
    )
