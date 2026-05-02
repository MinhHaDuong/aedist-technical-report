# Argument audit — frontier LLM panel

*Audit of `docs/argument.md` by 6 frontier models, 2026-05-01.*

## Audit protocol

**Prompt:** Each model received `argument.md` (342 lines) as user input with
a system prompt asking four questions: (a) strongest internal inconsistency,
(b) weakest empirical claim, (c) most likely methodological objection from a
peer reviewer, (d) one claim to drop if forced. Models were asked to quote
specific phrases from the document. Temperature: 0.3, max_tokens: 2048.

**Panel:**

| Model | Provider | Tokens (in/out) | Wall time |
|-------|----------|-----------------|-----------|
| DeepSeek V3.2 | DeepSeek | 4273/399 | 31.4s |
| GPT-5.4 | OpenAI | 4282/452 | 8.2s |
| Claude Opus 4.6 | Anthropic | 4736/603 | 13.7s |
| Gemini 3 Flash | Google | 4410/347 | 3.7s |
| Mistral Large 3 | Mistral | 4381/356 | 6.9s |
| Qwen3 Max Thinking | Alibaba | 4356/327 | 10.8s |

All via OpenRouter. Raw responses: `docs/audit-responses/`.

## Consensus findings

### 1. Deep-research saturation hypothesis contradicts current data (6/6)

**Unanimous.** Every model flagged the contradiction between the narrative
claim that deep research "caps both data quality and answer quality" /
"F1 → 1" and the empirical caveat showing best deep-research F1 = 0.557,
mean ≈ 0.35, three models at 0.000. GPT-5.4 called it a "desk-reject-level
credibility problem." This was raised under (a) by all six and under (d) by
four (DeepSeek, GPT-5.4, Mistral, Qwen).

**Resolution:** The document already marks this as "a hypothesis the present
data does not corroborate." The prose should be restructured so the
saturation claim is clearly framed as a hypothesis to test, not as the
narrative's conclusion. The Part 2 arc should end with the current ceiling
(decomposed RAG, F1 = 0.988) and present deep research as an open question
contingent on evaluator fixes and further runs. *Considered and accepted.*

### 2. F1 metric bundles distinct quality dimensions (4/6)

DeepSeek, GPT-5.4, Claude Opus, Qwen all noted that using a single F1
metric to measure both data quality (Coverage, Freshness) and answer quality
(Articulation, Coherence) makes it impossible to attribute gains to
individual limits. Claude Opus specifically noted the deep-research step
"bundles two deltas" and the intermediate cell (ticket 0144) doesn't yet
exist to disentangle them.

**Resolution:** The document already acknowledges this bundling explicitly.
The paper should: (1) state upfront that F1 is a composite and cannot
isolate individual limits, (2) use the four-limits framework as a
conceptual decomposition, not a causal claim, (3) note that the
intermediate cell (ticket 0144) is needed for clean attribution.
*Considered and accepted.*

### 3. "Stage 5 forced" is weak causal inference (3/6)

DeepSeek, GPT-5.4, and Gemini objected to the claim that deep research is
"forced once 3 and 4 are present" / "a near-mechanical join" — arguing this
is product-release correlation from four labs, not a demonstrated technical
necessity.

**Resolution:** Weaken to observational language: "every lab shipped deep
research within 2–7 months" → "we observed that..." without the causal
"forced" / "near-mechanical" framing. The DAG remains as a structural
hypothesis, not a proven mechanism. *Considered and accepted.*

### 4. Evaluator artifact is a confounding variable (2/6)

GPT-5.4 and Gemini noted that if the extraction pipeline chokes on
`prompt_complete`'s structured-document format, the F1 drops may reflect
measurement failure rather than model or method failure, undermining the
entire comparison.

**Resolution:** This is already the leading diagnosis (interpretation 1 in
the empirical caveat). The paper must resolve this empirically before
asserting any deep-research F1 claim. Until then, the caveat stays
prominent. *Considered and accepted — diagnosis is priority 2 in STATE.md.*

## Distinct findings (1/6 each)

### 5. qwen3.5:9b n=1 result is too weak to draw conclusions (Claude Opus)

The n=1 F1=0.984 from a 9B local model "cannot support" the inference
that "you may not need a deep-research stack at this task at all."

**Resolution:** Already flagged for confirmation (priority 3 in STATE.md).
Language should be strictly conditional until repeats confirm. *Considered
and accepted.*

### 6. Strict sequential ordering of limits is unsupported (Claude Opus)

The "each is the next bottleneck once the previous one is relaxed"
framing is too strong given admitted stage overlaps and per-lab inversions.

**Resolution:** Weaken to "approximate ordering" or "historical sequence"
rather than strict bottleneck chain. The DAG already shows parallel
branches (3 ∥ 4); the prose should match. *Considered and accepted.*

### 7. Weak/internal coherence operationalization may be too narrow (Mistral)

For energy infrastructure statistics, external consistency (cross-document
validation) may matter more than internal self-consistency.

**Resolution:** The 2×2 coherence matrix already acknowledges strong/external
coherence and marks it out of scope. The paper should note that this scoping
decision is a limitation, not an oversight. *Considered and rejected as
out-of-scope for the current paper — but flagged for future work.*

### 8. "Linearity is a convenience" contradicts the ladder (Gemini)

Calling linearity "a convenience simplification" while then building a
sequential 7-stage ladder creates conceptual friction.

**Resolution:** Rephrase to clarify the ladder is a partial order (DAG),
not a total linear order. The "convenience" sentence should reference the
DAG structure explicitly. *Considered and accepted.*

## Summary table

| # | Finding | Consensus | Disposition |
|---|---------|-----------|-------------|
| 1 | Deep-research saturation contradicts data | 6/6 | Accepted: reframe as hypothesis |
| 2 | F1 bundles distinct quality dimensions | 4/6 | Accepted: state limitation upfront |
| 3 | "Stage 5 forced" is weak causal claim | 3/6 | Accepted: weaken to observational |
| 4 | Evaluator artifact confounds comparison | 2/6 | Accepted: resolve empirically first |
| 5 | qwen3.5:9b n=1 too weak | 1/6 | Accepted: conditional language |
| 6 | Sequential ordering too strict | 1/6 | Accepted: weaken to partial order |
| 7 | Weak coherence too narrow | 1/6 | Rejected: acknowledged limitation |
| 8 | "Linearity" vs ladder friction | 1/6 | Accepted: rephrase |
