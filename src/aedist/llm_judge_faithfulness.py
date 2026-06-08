"""Cached LLM-judge source-faithfulness scorer (ticket 0470).

For each (document, plant, attribute, claimed-value) tuple, asks an LLM:
"Does document X say plant P has attribute A = claimed value?"

Verdicts are cached in a JSONL file keyed by
(document_id, plant, attribute, claimed_value, judge_model, prompt_version).
Re-runs read the cache; only novel (plant, claim) tuples hit the API.

Relationship to deterministic baseline (ticket 0201 / score_provenance.py):
  - The deterministic scorer (score_provenance.py) is the fast first pass:
    string/number lookup — does the cited source contain value V for plant P.
  - This LLM judge is the upgrade layer: catches paraphrase, unit-restated,
    and table-layout cases the deterministic check misses.
  - The deterministic baseline is NOT replaced; it remains the cheap first pass.

ADR-7: ``faithfulness_score`` is wired into ``records_to_metrics()`` via the
``justification`` dict so it sits alongside the deterministic provenance score
in the complete scientific record.

Note: Action 4 from the ticket spec ("test one before blasting" — one real
verdict per attribute before any batch) is a validation step for the first live
deployment; it is deferred under the no-API constraint of this ticket.

Usage::

    judge = FaithfulnessJudge()
    verdict = judge.verdict(
        doc="Decision 1195/QD-TTg says Pha Lai has 440 MW coal capacity.",
        plant="Pha Lai",
        attr="capacity",
        claim="440",
    )
    print(verdict.supported, verdict.explanation)
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ── Prompt ────────────────────────────────────────────────────────────────────

PROMPT_VERSION = "v1"
DEFAULT_JUDGE_MODEL = "openai/gpt-4o-mini"

_SYSTEM_PROMPT = (
    "You are an evidence auditor for a power-plant database. "
    "You answer only 'supported', 'contradicted', or 'not_mentioned'."
)

_USER_TEMPLATE = (
    "Document:\n{doc}\n\n"
    "Claim: Plant '{plant}' has {attr} = {claim}.\n\n"
    "Does the document support, contradict, or not mention this claim? "
    "Reply with exactly one word: supported / contradicted / not_mentioned. "
    "Then add a short explanation (one sentence)."
)

_VALID_VERDICTS = frozenset({"supported", "contradicted", "not_mentioned"})


# ── Data structures ───────────────────────────────────────────────────────────


@dataclass
class Verdict:
    """One faithfulness verdict from the LLM judge."""

    supported: bool | None  # True=supported, False=contradicted/not_mentioned, None=error
    raw: str  # raw text from the model
    verdict_label: str  # 'supported' | 'contradicted' | 'not_mentioned' | 'error'
    explanation: str = ""
    cache_hit: bool = False
    model: str = DEFAULT_JUDGE_MODEL
    prompt_version: str = PROMPT_VERSION


@dataclass
class FaithfulnessJudge:
    """LLM judge that scores whether a document supports a factual claim.

    All verdicts are written to a JSONL cache keyed by
    (document_id, plant, attribute, claimed_value, judge_model, prompt_version).

    Parameters
    ----------
    cache:
        Path to the JSONL verdict cache file.  Created on first write if it
        does not exist.  Pass ``None`` to disable caching (every call hits the
        API, useful in tests that mock _call_api).
    model:
        Judge model identifier (OpenRouter / OpenAI format).
    prompt_version:
        Prompt template version string.  Changing this invalidates existing
        cache entries because they are keyed by model + prompt_version.
    """

    cache: Path | None = None
    model: str = DEFAULT_JUDGE_MODEL
    prompt_version: str = PROMPT_VERSION
    _cache_data: dict = field(default_factory=dict, repr=False, init=False)

    def __post_init__(self) -> None:
        if self.cache is not None:
            self._load_cache()

    # ── Cache I/O ─────────────────────────────────────────────────────────────

    def _load_cache(self) -> None:
        """Load verdict cache from disk (JSONL, one JSON object per line)."""
        if self.cache is None or not self.cache.exists():
            return
        with open(self.cache, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    key = entry.get("key")
                    if key:
                        self._cache_data[key] = entry
                except json.JSONDecodeError:
                    log.warning("Skipping malformed cache line: %s", line[:80])

    def _save_to_cache(self, key: str, entry: dict) -> None:
        """Append one verdict entry to the JSONL cache file."""
        if self.cache is None:
            return
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    @staticmethod
    def _make_key(doc_id: str, plant: str, attr: str, claim: str, model: str, pv: str) -> str:
        """Deterministic cache key from the 6-tuple."""
        raw = json.dumps(
            {"doc_id": doc_id, "plant": plant, "attr": attr, "claim": claim, "model": model, "pv": pv},
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    # ── API seam ──────────────────────────────────────────────────────────────

    def _call_api(self, *, doc: str, plant: str, attr: str, claim: str) -> str:
        """Send one verdict request to the configured judge model.

        Returns the model's raw text response.  This method is the sole
        network boundary — mock it in tests to avoid live API calls.

        Raises
        ------
        RuntimeError
            When the API call fails (network, auth, rate limit).  Callers
            catch this and record verdict_label='error'.
        """
        try:
            import openai  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError("openai package not installed; run `uv add openai`") from exc

        client = openai.OpenAI()  # reads OPENAI_API_KEY from env
        user_msg = _USER_TEMPLATE.format(doc=doc, plant=plant, attr=attr, claim=claim)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=128,
            temperature=0.0,
        )
        return response.choices[0].message.content or ""

    # ── Public API ────────────────────────────────────────────────────────────

    @staticmethod
    def _doc_id(doc: str) -> str:
        """Stable document identifier (SHA-256 prefix of the document text)."""
        return hashlib.sha256(doc.encode()).hexdigest()[:16]

    @staticmethod
    def _parse_raw(raw: str) -> tuple[str, str]:
        """Parse model output into (verdict_label, explanation).

        The model is instructed to start with one of
        'supported' / 'contradicted' / 'not_mentioned'.
        """
        text = raw.strip()
        lower = text.lower()
        for label in ("supported", "contradicted", "not_mentioned"):
            if lower.startswith(label):
                explanation = text[len(label):].lstrip(". \t\n")
                return label, explanation
        # Fallback: scan for keyword anywhere in first line
        first_line = lower.split("\n")[0]
        for label in ("supported", "contradicted", "not_mentioned"):
            if label in first_line:
                return label, text
        return "error", text

    def verdict(
        self,
        doc: str,
        *,
        plant: str,
        attr: str,
        claim: str,
    ) -> Verdict:
        """Return the faithfulness verdict for one (document, plant, attr, claim) tuple.

        If the key is already in the cache, returns the cached verdict without
        calling the API.  On a cache miss, calls ``_call_api``, parses the
        response, writes to cache, and returns the verdict.

        Parameters
        ----------
        doc:
            The document text (or excerpt) to judge.
        plant:
            Plant name as it appears in the extraction.
        attr:
            Attribute being checked: 'fuel', 'capacity', or 'status'.
        claim:
            The claimed value (e.g. "440" for capacity, "coal" for fuel).

        Returns
        -------
        Verdict
            supported=True when label is 'supported', False otherwise.
            supported=None on API / parse errors.
        """
        doc_id = self._doc_id(doc)
        key = self._make_key(doc_id, plant, attr, claim, self.model, self.prompt_version)

        # ── Cache hit ─────────────────────────────────────────────────────────
        if key in self._cache_data:
            entry = self._cache_data[key]
            label = entry.get("verdict_label", "error")
            return Verdict(
                supported=(True if label == "supported" else (None if label == "error" else False)),
                raw=entry.get("raw", ""),
                verdict_label=label,
                explanation=entry.get("explanation", ""),
                cache_hit=True,
                model=entry.get("model", self.model),
                prompt_version=entry.get("prompt_version", self.prompt_version),
            )

        # ── Cache miss → API call ─────────────────────────────────────────────
        try:
            raw = self._call_api(doc=doc, plant=plant, attr=attr, claim=claim)
            label, explanation = self._parse_raw(raw)
        except Exception as exc:
            log.warning("LLM judge API call failed for %s/%s/%s: %s", plant, attr, claim, exc)
            raw = str(exc)
            label = "error"
            explanation = raw

        supported: bool | None
        if label == "supported":
            supported = True
        elif label == "error":
            supported = None
        else:
            supported = False

        entry: dict[str, Any] = {
            "key": key,
            "doc_id": doc_id,
            "plant": plant,
            "attr": attr,
            "claim": claim,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "verdict_label": label,
            "raw": raw,
            "explanation": explanation,
        }
        self._cache_data[key] = entry
        self._save_to_cache(key, entry)

        return Verdict(
            supported=supported,
            raw=raw,
            verdict_label=label,
            explanation=explanation,
            cache_hit=False,
            model=self.model,
            prompt_version=self.prompt_version,
        )

    def faithfulness_score(
        self,
        verdicts: list[Verdict],
    ) -> float | None:
        """Compute per-run faithfulness scalar from a list of verdicts.

        Returns the fraction of verdicts that are 'supported', or None when
        the verdict list is empty or contains only errors (ADR-7: None means
        no verdicts cached yet, not a score of 0.0).
        """
        valid = [v for v in verdicts if v.verdict_label != "error"]
        if not valid:
            return None
        return round(sum(1 for v in valid if v.supported is True) / len(valid), 4)
