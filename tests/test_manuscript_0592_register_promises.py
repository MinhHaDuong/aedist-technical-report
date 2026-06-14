"""Ticket 0592 — final global sweep guards: lab-journal register, forward
promises, noise phrases, leaked generation instructions.

The reading-2 wave (children of tracker 0578) converted the manuscript from
a construction-diary register to a technical-report register and stripped the
forward-promise, noise, and instruction-cruft defect classes. This file is the
regression ratchet so those classes stay shut.

Per the CI polarity rule (`.claude/rules/writing.md`, ticket 0557) every check
here is a *negative* guard — a forbidden phrasing or a fixed noise literal —
or a structural scope. No positive authorial wording is pinned: a legitimate
rewrite must never turn one of these red.

The no-companion-paper-promise phrasings are already guarded by
`test_manuscript_0512_structure.py::test_no_companion_paper_promise_in_body`
(brief entry no-companion-paper-promise); this file covers the *other*
forward-promise registers (deferral / planning / "future work will") plus the
noise and instruction-cruft classes, without duplicating that set.
"""

import re

import pytest
from manuscript_source import body, body_raw, normalized

pytestmark = pytest.mark.adherence


def _body_excluding_abstract() -> str:
    """Normalized body with the ``abstract`` environment removed.

    The abstract's brief-pinned summary register (entry
    frontier-result-abstract) legitimately uses first-person summary verbs
    ("We find…", "We then tested…") to compress the whole study; the
    lab-journal guard scopes to the running text, where process chronology
    is the defect.
    """
    raw = re.sub(
        r"\\begin\{abstract\}.*?\\end\{abstract\}", " ", body_raw(), flags=re.DOTALL
    )
    return normalized(raw)


# --- Forward promises (finding 25) -----------------------------------------
# Promises are deleted, not hedged: forward-looking material is framed as
# programme in the Future research section (sec:future), never as a commitment
# to do specific work outside this paper.
_PROMISE_PATTERNS = [
    r"post-conference",
    r"\bpost-arxiv\b",
    r"deferred \(post-",
    r"deferred to [\w\- ]*analysis",
    r"\bfuture work will\b",
    r"\bwe plan to\b",
    r"\bwe will (?:report|defer|run|present|evaluate|measure)\b",
    r"\bwill be reported (?:in a |elsewhere)",
    r"\bwe defer (?:more|further) \w+ (?:with|to)\b",
    r"\bwe intend to\b",
]


@pytest.mark.parametrize("pattern", _PROMISE_PATTERNS)
def test_no_forward_promise(pattern):
    m = re.search(pattern, body(), re.IGNORECASE)
    assert m is None, (
        f"forward-promise phrasing {m.group(0)!r} in the manuscript body — "
        "promises are deleted, not hedged; frame forward-looking work as "
        "programme in sec:future (ticket 0592, finding 25)"
    )


# --- Noise / throat-clearing literals (finding 38) -------------------------
# Author-flagged empty filler. These were folded into substantive sentences or
# deleted; the literals must not return.
_NOISE_LITERALS = [
    "now scored for all runs",
    "minimum attainable p",
]


@pytest.mark.parametrize("phrase", _NOISE_LITERALS)
def test_no_noise_phrase(phrase):
    assert phrase.lower() not in body().lower(), (
        f"author-flagged noise phrase {phrase!r} returned to the manuscript "
        "body (ticket 0592, finding 38)"
    )


# --- Lab-journal register (finding 26 / class 17) --------------------------
# This is a technical report, not a lab journal: state results and methods,
# not the chronology of running them. The defect signature is a session-log
# process connective opening a clause in the running text (the brief-pinned
# abstract summary register is excluded — see _body_excluding_abstract).
_LAB_JOURNAL_CONNECTIVES = [
    r"\bwe then ran\b",
    r"\bwe next ran\b",
    r"\bwe proceeded to\b",
    r"\bwe decided to\b",
    r"\bwe set out to\b",
    r"\bwe began by\b",
    r"\bwe started by\b",
    r"\bhaving (?:run|finished|completed)\b",
    r"\bonce we had (?:run|finished|the results)\b",
    r"\bafter that,? we\b",
]


@pytest.mark.parametrize("pattern", _LAB_JOURNAL_CONNECTIVES)
def test_no_lab_journal_register(pattern):
    m = re.search(pattern, _body_excluding_abstract(), re.IGNORECASE)
    assert m is None, (
        f"lab-journal process narration {m.group(0)!r} in the running text — "
        "this is a technical report: state the method/result, not the "
        "chronology of doing it (ticket 0592, finding 26)"
    )


# --- AI-English doublets (class 33) ----------------------------------------
# Adverb/intensifier near-synonym pairs ("solidly and firmly" class). These
# are vacuous emphasis, not the meaningful contrast pairs the prose does use
# (e.g. "internally and externally", two distinct coherence axes), which are
# not matched here.
_DOUBLET_PATTERNS = [
    r"\bsolidly and firmly\b",
    r"\bclearly and explicitly\b",
    r"\bfully and completely\b",
    r"\bsimply and easily\b",
    r"\bcarefully and thoroughly\b",
    r"\baccurately and precisely\b",
    r"\bcomprehensive and complete\b",
]


@pytest.mark.parametrize("pattern", _DOUBLET_PATTERNS)
def test_no_ai_english_doublet(pattern):
    m = re.search(pattern, body(), re.IGNORECASE)
    assert m is None, (
        f"AI-English synonym doublet {m.group(0)!r} in the manuscript body — "
        "vacuous emphasis; keep one term (ticket 0592, class 33)"
    )
