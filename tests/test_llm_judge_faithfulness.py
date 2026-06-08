"""Tests for the cached LLM-judge faithfulness scorer (ticket 0470).

All tests mock _call_api — no live API calls are made.
"""

import json

import pytest

from aedist.llm_judge_faithfulness import (
    DEFAULT_JUDGE_MODEL,
    PROMPT_VERSION,
    FaithfulnessJudge,
    Verdict,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _canned_api(raw: str):
    """Return a fake _call_api that always returns ``raw`` text."""

    def _fake(*, doc, plant, attr, claim):
        return raw

    return _fake


def _boom(*, doc, plant, attr, claim):
    """Fake _call_api that must never be called."""
    raise AssertionError("_call_api must not be called on a cache hit")


# ── Cache-hit test (the canonical test from the ticket spec) ──────────────────


class TestCacheHitSkipsApi:
    """Cache hit must not call the API."""

    def test_cache_hit_skips_api(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "verdicts.jsonl"
        judge = FaithfulnessJudge(cache=cache_path)

        # Inject fake _call_api so the first call doesn't hit the network
        monkeypatch.setattr(judge, "_call_api", _canned_api("supported — the document states 440 MW."))

        # First call: cache miss → fake API call #1
        v1 = judge.verdict(
            "Decision 1195/QD-TTg states Pha Lai has 440 MW coal capacity.",
            plant="Pha Lai",
            attr="capacity",
            claim="440",
        )
        assert v1.supported in (True, False)
        assert not v1.cache_hit

        # Swap to bomb — any API call now would raise
        monkeypatch.setattr(judge, "_call_api", _boom)

        # Second call: same key → cache hit, no API call
        v2 = judge.verdict(
            "Decision 1195/QD-TTg states Pha Lai has 440 MW coal capacity.",
            plant="Pha Lai",
            attr="capacity",
            claim="440",
        )
        assert v2.supported in (True, False)
        assert v2.cache_hit


# ── Verdict parsing ───────────────────────────────────────────────────────────


class TestParseRaw:
    """_parse_raw extracts the label and explanation from model output."""

    def test_supported_verdict(self):
        label, expl = FaithfulnessJudge._parse_raw("supported — the document states 440 MW.")
        assert label == "supported"
        assert "440" in expl

    def test_contradicted_verdict(self):
        label, _ = FaithfulnessJudge._parse_raw("contradicted. The document says 500 MW.")
        assert label == "contradicted"

    def test_not_mentioned(self):
        label, _ = FaithfulnessJudge._parse_raw("not_mentioned The document is silent on this.")
        assert label == "not_mentioned"

    def test_unknown_becomes_error(self):
        label, raw = FaithfulnessJudge._parse_raw("I don't know.")
        assert label == "error"

    def test_case_insensitive(self):
        label, _ = FaithfulnessJudge._parse_raw("SUPPORTED — value confirmed.")
        assert label == "supported"


# ── Verdict dataclass ─────────────────────────────────────────────────────────


class TestVerdictSemantics:
    """Verdict.supported follows the three-way semantics."""

    def test_supported_true(self, tmp_path, monkeypatch):
        judge = FaithfulnessJudge(cache=tmp_path / "v.jsonl")
        monkeypatch.setattr(judge, "_call_api", _canned_api("supported — confirmed."))
        v = judge.verdict("doc text", plant="P", attr="fuel", claim="coal")
        assert v.supported is True
        assert v.verdict_label == "supported"

    def test_contradicted_false(self, tmp_path, monkeypatch):
        judge = FaithfulnessJudge(cache=tmp_path / "v.jsonl")
        monkeypatch.setattr(judge, "_call_api", _canned_api("contradicted — doc says gas."))
        v = judge.verdict("doc text", plant="P", attr="fuel", claim="coal")
        assert v.supported is False
        assert v.verdict_label == "contradicted"

    def test_not_mentioned_false(self, tmp_path, monkeypatch):
        judge = FaithfulnessJudge(cache=tmp_path / "v.jsonl")
        monkeypatch.setattr(judge, "_call_api", _canned_api("not_mentioned No fuel info."))
        v = judge.verdict("doc text", plant="P", attr="fuel", claim="coal")
        assert v.supported is False
        assert v.verdict_label == "not_mentioned"

    def test_api_error_returns_none(self, tmp_path, monkeypatch):
        judge = FaithfulnessJudge(cache=tmp_path / "v.jsonl")

        def _raise(**kwargs):
            raise RuntimeError("network failure")

        monkeypatch.setattr(judge, "_call_api", _raise)
        v = judge.verdict("doc text", plant="P", attr="fuel", claim="coal")
        assert v.supported is None
        assert v.verdict_label == "error"


# ── Cache persistence ─────────────────────────────────────────────────────────


class TestCachePersistence:
    """Cache survives process restart (new FaithfulnessJudge reads existing file)."""

    def test_written_verdicts_survive_reload(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "v.jsonl"
        judge1 = FaithfulnessJudge(cache=cache_path)
        monkeypatch.setattr(judge1, "_call_api", _canned_api("supported — confirmed."))

        judge1.verdict("doc A", plant="P", attr="capacity", claim="600")

        # New judge instance loads the cache
        judge2 = FaithfulnessJudge(cache=cache_path)
        monkeypatch.setattr(judge2, "_call_api", _boom)  # must not be called

        v = judge2.verdict("doc A", plant="P", attr="capacity", claim="600")
        assert v.cache_hit
        assert v.supported is True

    def test_cache_file_is_valid_jsonl(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "v.jsonl"
        judge = FaithfulnessJudge(cache=cache_path)
        monkeypatch.setattr(judge, "_call_api", _canned_api("supported — yes."))

        judge.verdict("doc B", plant="Q", attr="status", claim="operating")

        lines = [ln for ln in cache_path.read_text().splitlines() if ln.strip()]
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["plant"] == "Q"
        assert entry["attr"] == "status"
        assert entry["verdict_label"] == "supported"
        assert entry["model"] == DEFAULT_JUDGE_MODEL
        assert entry["prompt_version"] == PROMPT_VERSION


# ── Cache key includes model + prompt_version ─────────────────────────────────


class TestCacheKeyInvalidation:
    """Changing model or prompt_version bypasses cached verdicts."""

    def test_different_model_is_cache_miss(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "v.jsonl"

        judge_a = FaithfulnessJudge(cache=cache_path, model="openai/gpt-4o-mini")
        call_count = {"n": 0}

        def _count(**kwargs):
            call_count["n"] += 1
            return "supported — by model A."

        monkeypatch.setattr(judge_a, "_call_api", _count)
        judge_a.verdict("doc C", plant="R", attr="fuel", claim="gas")
        assert call_count["n"] == 1

        judge_b = FaithfulnessJudge(cache=cache_path, model="anthropic/claude-3-haiku")
        call_count2 = {"n": 0}

        def _count2(**kwargs):
            call_count2["n"] += 1
            return "supported — by model B."

        monkeypatch.setattr(judge_b, "_call_api", _count2)
        judge_b.verdict("doc C", plant="R", attr="fuel", claim="gas")
        assert call_count2["n"] == 1, "different model should be a cache miss"


# ── faithfulness_score scalar ─────────────────────────────────────────────────


class TestFaithfulnessScore:
    """faithfulness_score reduces a list of verdicts to a float | None."""

    def test_all_supported(self):
        verdicts = [
            Verdict(supported=True, raw="supported", verdict_label="supported"),
            Verdict(supported=True, raw="supported", verdict_label="supported"),
        ]
        judge = FaithfulnessJudge()
        assert judge.faithfulness_score(verdicts) == 1.0

    def test_mixed_verdicts(self):
        verdicts = [
            Verdict(supported=True, raw="supported", verdict_label="supported"),
            Verdict(supported=False, raw="contradicted", verdict_label="contradicted"),
            Verdict(supported=False, raw="not_mentioned", verdict_label="not_mentioned"),
        ]
        judge = FaithfulnessJudge()
        score = judge.faithfulness_score(verdicts)
        assert score == pytest.approx(1 / 3, abs=1e-4)

    def test_empty_list_returns_none(self):
        """ADR-7 / f1=None semantics: no verdicts = None, not 0.0."""
        judge = FaithfulnessJudge()
        assert judge.faithfulness_score([]) is None

    def test_all_errors_returns_none(self):
        """All-error verdicts carry no information → None."""
        verdicts = [
            Verdict(supported=None, raw="err", verdict_label="error"),
            Verdict(supported=None, raw="err", verdict_label="error"),
        ]
        judge = FaithfulnessJudge()
        assert judge.faithfulness_score(verdicts) is None

    def test_errors_excluded_from_denominator(self):
        """Error verdicts are excluded from the denominator."""
        verdicts = [
            Verdict(supported=True, raw="supported", verdict_label="supported"),
            Verdict(supported=None, raw="err", verdict_label="error"),
        ]
        judge = FaithfulnessJudge()
        assert judge.faithfulness_score(verdicts) == 1.0


# ── measurements.py wiring (ADR-7) ───────────────────────────────────────────


class TestMeasurementsWiring:
    """faithfulness_score is projected from justification into the metrics dict."""

    def _make_record(self, justification: dict | None):

        from aedist.schema import Method, MethodParams, ResultSummary, RunRecord

        return RunRecord(
            method=Method.RAG,
            method_params=MethodParams(model="test/model"),
            result_summary=ResultSummary(tp=1, fp=0, fn=0, f1=1.0),
            justification=justification,
        )

    def test_faithfulness_score_present_when_in_justification(self):
        from aedist.measurements import records_to_metrics

        record = self._make_record({"faithfulness_score": 0.75})
        metrics = records_to_metrics([record])
        assert len(metrics) == 1
        assert metrics[0]["faithfulness_score"] == pytest.approx(0.75)

    def test_faithfulness_score_absent_when_null(self):
        """None value is omitted (same as other omit-when-absent fields)."""
        from aedist.measurements import records_to_metrics

        record = self._make_record({"faithfulness_score": None})
        metrics = records_to_metrics([record])
        assert "faithfulness_score" not in metrics[0]

    def test_faithfulness_score_absent_when_no_justification(self):
        """No justification → key not present in metrics dict."""
        from aedist.measurements import records_to_metrics

        record = self._make_record(None)
        metrics = records_to_metrics([record])
        assert "faithfulness_score" not in metrics[0]

    def test_existing_verification_scalars_unaffected(self):
        """Adding faithfulness_score does not disturb existing justification keys."""
        from aedist.measurements import records_to_metrics

        record = self._make_record(
            {
                "verification_mode": "strict",
                "mean_evidence_score": 3.5,
                "faithfulness_score": 0.9,
            }
        )
        metrics = records_to_metrics([record])
        m = metrics[0]
        assert m["verification_mode"] == "strict"
        assert m["mean_evidence_score"] == pytest.approx(3.5)
        assert m["faithfulness_score"] == pytest.approx(0.9)
