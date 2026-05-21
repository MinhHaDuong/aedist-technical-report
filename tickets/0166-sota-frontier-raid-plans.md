# Raid Phase 3 plans — SOTA frontier API experiment (0166 umbrella)

Generated 2026-05-14 by six parallel Plan agents, then revised on user
decision to expand from 3 to 4 SOTA agents (added 0173 Qwen for CN/
Chinese-corpus diversity; dropped the 0173 Kimi placeholder). Phase 5
implementers read the section matching their ticket. Wave order:
0172 → 0167 / 0168 / 0169 / 0173 parallel → 0170 / 0171 parallel.

---

## 0172 — RunRecord schema extension (Wave 1)

### Actions
1. `src/aedist/schema.py:155-162` (`ResourceUse`): add `cost_breakdown: dict|None`, `thinking_tokens: int|None`.
2. `src/aedist/schema.py:180-211` (`RunRecord`): add optional `agent_family`, `agent_mode`, `synopsis_sha`, `designed_prompt_sha`, `web_search_calls: list[dict]|None`, `citations: list[dict]|None`, `parsed_table_path`, `finish_reason`, `retry_count`, `error`, `reasoning_summary`, `tool_calls_cost_usd` (the last for 0169 connector fees).
3. `src/aedist/measurements.py:74-157` (`records_to_metrics`): project each new field when present. Lists → counts (`n_web_search_calls`, `n_citations`); keep raw lists in the record.
4. `ADR.md:95-101` — extend ADR-7 table; add an "Agent runs" row covering the new fields. No new `measurements_schema.md`.
5. Tests: `tests/test_measurements_agent_fields.py` (new).

### First failing test (non-tautological)
`test_records_to_metrics_projects_web_search_count_from_list_length` — construct a `RunRecord` with `web_search_calls=[a,b,c]` (len 3) and `citations=[x,y]` (len 2); assert `m["n_web_search_calls"] == 3` and `m["n_citations"] == 2`. Asymmetric lengths catch both the "copy-pasted len(citations) into both" bug and the "forgot len()" bug.

### Contract surface for adapters
- `agent_family` literals: `anthropic-direct | openai-direct | mistral-direct | qwen-direct`
- `agent_mode` literals: `phase_a_design | phase_b_run | phase_c_score | smoke | probe`
- `web_search_calls` entry: `{"query": str, "urls_returned": list[str]}`
- `citations` entry: `{"url": str, "snippet": str|None, "supports_claim": bool|None}`
- `cost_breakdown` keys (omit-on-absent): `input | output | cache | reasoning`
- `parsed_table_path` is repo-relative.

### Backward-compat fixture
`measurements.jsonl` line 32, `run_id="61326a1572ec"` — real production record, non-empty `extra` (provider DeepSeek, MoE, etc.), no agent fields. Inline JSON literal in test to keep hermetic.

**Estimated diff: ~185 LOC.**

---

## 0167 — Anthropic adapter (Wave 2)

### Actions
1. New `src/aedist/query_anthropic.py`. Reuse from `harness`: `BudgetTracker`, `output_path`, `save_json`, `compute_cost` (extended), `load_models`, `select_models`.
2. `_load_key()` — reads `~/.config/keys/anthropic.env`.
3. `assemble_request(user_message, model, *, max_tokens=4096, max_uses=5)` — returns `messages.create` kwargs. Uses `tools=[{"type":"web_search_20250305","name":"web_search","max_uses":max_uses}]`, `thinking={"type":"adaptive","display":"summarized"}`, `tool_choice={"type":"auto"}`. **This is the protocol surface.**
4. `dispatch(payload, model, *, dry_run, output_dir, run, agent_mode, budget)` — 0170-facing entry point.
5. `_parse_anthropic_response(resp)` — walks `resp.content`: text blocks → narrative; `server_tool_use` → `web_search_calls`; `web_search_tool_result` → `citations`; `thinking` → `thinking_tokens` + `reasoning_summary`.
6. `_compute_anthropic_cost(usage, model, n_searches)` — token cost + `n_searches * $0.010`.
7. `experiments/models.yaml` entry: `family: anthropic-direct`, `route: anthropic-direct`, model `claude-opus-4-7`, price card incl. `price_per_web_search: 0.010`.
8. Tests: `tests/test_adapter_anthropic.py` with fixture response.

### First failing test
`test_parse_response_extracts_citations_and_search_calls` — feed a fixture `Message`-shaped dict with one thinking block, one `server_tool_use`, one `web_search_tool_result`, one text block, plus `usage.server_tool_use.web_search_requests=1`. Assert `len(parsed["web_search_calls"]) == 1`, `parsed["citations"][0]["url"]` contains the fixture domain, `parsed["text"].startswith("Vietnam operates")`. Verifies parsing effect, not request-kwargs tautology.

### Smoke budget (≤$0.50 cap, expected ~$0.19)
Model `claude-opus-4-7`, prompt `"List 3 coal power plants in Vietnam with one citation each, ≤200 words"`, `max_tokens=600`, `max_uses=3`. Worst case: 200 in × $15 + 600 + ~1500 thinking out × $75 + 3 × $0.010 = ~$0.19.

---

## 0168 — OpenAI Responses adapter (Wave 2)

### Actions
1. New `src/aedist/adapter_openai_responses.py`. Sibling to `harness.py:425-449`, not a graft (Responses API output is a heterogeneous `output[]`; flattening into `query_single_turn`'s shape would corrupt 23 callers).
2. `build_request(prompt, *, model, max_output_tokens, reasoning_effort="high")` → kwargs for `client.responses.create(model, input=prompt, tools=[{"type":"web_search"}], reasoning={"effort":"high"}, max_output_tokens)`.
3. `parse_response(resp, price_card)` — walks `resp.output[]`: `reasoning` items → `reasoning_summary` + `thinking_tokens`; `web_search_call` items → `web_search_calls` + `citations`; `message` items → narrative. Cost from `usage.input_tokens`, `usage.output_tokens`, `usage.output_tokens_details.reasoning_tokens`.
4. `run(prompt, *, dry_run)` — top-level entry, returns `RunRecord`.
5. `experiments/models.yaml` entry: `family: openai-direct`, `route: openai-responses`, model `gpt-5.5`.
6. Pre-call cap = `max_output_tokens` guard, not fabricated dollar estimate; verify post-call from `usage`.
7. Tests: `tests/test_adapter_openai_responses.py`.

### First failing test
`test_parse_canned_response_yields_runrecord_with_citations_and_reasoning` — feed a `SimpleNamespace` mimicking `responses.create` output: `[reasoning_item(summary="..."), web_search_call_item(action={"query":"vietnam coal"}, results=[{"url":"..."}]), message_item(content=[{"type":"output_text","text":"Body..."}])]` with `usage` populated. Assert `record.agent_family=="openai-direct"`, `len(record.citations)>=1`, `record.reasoning_summary` non-empty, `record.web_search_calls[0]["query"]=="vietnam coal"`, `record.resource_use.cost_usd` matches fixture arithmetic.

### Smoke budget (≤$0.50 cap, expected ~$0.28)
Model `gpt-5.5`, same prompt, `max_output_tokens=2000`, `reasoning={"effort":"high"}`. Worst case: 50 in + 2000 out + ≤8000 reasoning + 3 × web_search ≈ $0.28.

---

## 0169 — Mistral adapter (Wave 2)

### Actions
1. New `src/aedist/adapter_mistral.py` (in `src/aedist/`, not `experiments/`, to match peer adapter idiom and import conventions).
2. SDK: `mistralai`. `client.beta.agents.create(model="mistral-large-2512", tools=[{"type":"web_search"}])` + `client.beta.conversations.start(agent_id, inputs=[...])`. SDK over raw HTTP because Agents has nontrivial tool-call aggregation.
3. **Persistent agent_id strategy** — create-once, cache by SHA(config) in `experiments/derived/mistral_agent_ids.json`. Cleaner audit trail.
4. Same protocol surface as 0167/0168 (`build_payload`, `parse_response`, `run`).
5. `--probe` mode separate from `--smoke`.
6. **`tool_calls_cost_usd` separate from `cost_usd`** — connector fees do not blend into token cost.
7. `experiments/models.yaml` entry: `family: mistral-direct`, `model_id: mistral-large-2512`.
8. Tests: `tests/test_adapter_mistral.py` + fixture under `tests/fixtures/mistral_agent_response.json`.

### First failing test
`test_parse_response_populates_tool_calls_cost_and_citations` — feed fixture response. Assert `record.resource_use.cost_usd ≈ 0.0123` (token-only), `record.tool_calls_cost_usd ≈ 0.030` (3 connector calls × fixture price), `len(record.citations) >= 1`, `record.web_search_calls` non-empty.

### Pricing probe (Imagine ESCALATE → resolution)
Single `--probe` call, ≤$0.50 cap. Prompt: `"What is the current power generation capacity of Phú Mỹ 2.2 power plant? Cite one source."` (forces exactly 1 web_search). Inspect, in order: top-level `usage.billed_units / connector_calls / tool_call_count`; per-`tool_calls[*]` `cost`/`billing`/`units`; response headers `x-mistral-billing-*`; manual console invoice check.

**Outcomes**: (a) billed-units visible → record `price_per_websearch_call_usd` in models.yaml + driver docstring, proceed to live smoke under remaining budget. (b) opaque → halt 0169 at probe; defer to 0173 Kimi path. Per user 2026-05-14: keep both paths planned; pick at Phase B time.

### Smoke budget
≤$0.50 total across probe + smoke. If probe converts (returns cited answer with ≥1 web_search call), it IS the smoke — save to `experiments/outputs/sota_smoke/mistral_probe_<run_id>.json`.

---

## 0173 — Qwen3-Max via DashScope (Wave 2, parallel)

### Actions
1. New `src/aedist/adapter_qwen_dashscope.py`. Same protocol surface as 0167/0168/0169 (`build_request`, `parse_response`, `run`). Constants `AGENT_FAMILY="qwen-direct"`, `DEFAULT_MODEL="qwen3-max-2026-01-23"`, `API_DOCS_VERIFIED="2026-05-14"`.
2. SDK: `dashscope` Python SDK (default). OpenAI-compatible endpoint `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` exists but historically lags on tool-call fidelity — keep dashscope SDK unless smoke reveals friction.
3. Request shape (per Alibaba docs, verified 2026-05-14):
   ```python
   dashscope.Generation.call(
       model="qwen3-max-2026-01-23",
       messages=[{"role": "user", "content": prompt}],
       tools=[{"type": "web_search"}],
       enable_thinking=True,
       result_format="message",
       max_tokens=...,
   )
   ```
4. `experiments/models.yaml` entry: `family: qwen-direct`, `route: dashscope`, price card incl. `price_per_web_search_call_usd ≈ 0.010` (international) or `0.00057` (mainland) — confirm at registration. Surface `tool_calls_cost_usd` separately (same field as 0169 connector fees, already in 0172 schema).
5. Pre-call cap = `max_tokens` guard + estimated n_searches; post-call verify from `usage`.
6. API key precondition: user adds `~/.config/keys/dashscope.env` with `DASHSCOPE_API_KEY=...` (Alibaba Cloud Model Studio signup + KYC required, one-time).
7. Tests: `tests/test_adapter_qwen_dashscope.py` + `tests/fixtures/qwen_dashscope_response.json`.

### First failing test (asymmetric, non-tautological)
`test_parse_response_extracts_thinking_searches_and_citations` — fixture with 3 web_search hits resolving to 5 distinct URLs (asymmetric counts catch dedup/len-misuse bugs). Assert `len(record.web_search_calls)==3`, `len(record.citations)==5`, `record.reasoning_summary` non-empty, `record.agent_family=="qwen-direct"`, cost arithmetic against fixture price card matches.

### Smoke budget (≤$0.50, expected ~$0.10)
Same canonical prompt as 0167/0168/0169. `max_tokens=800`, `enable_thinking=True`, `tools=[{"type":"web_search"}]`. Worst case: 50 in × $0.002/Ktok + 800 out × $0.020/Ktok + 1500 thinking × $0.020/Ktok + 3 × $0.010 = ~$0.08–$0.10.

### Caveats
- Thinking + web_search compose on `qwen3-max-*` per docs; do NOT generalize to other Qwen families without re-verifying.
- International vs mainland endpoint matters for both price and latency; default international.

---

## 0170 — Phase A reflexive prompt design harness (Wave 3)

### Actions
1. New `experiments/prompts/phase_a_meta_prompt.txt` — template with `{baseline}` / `{quality_bar}` / `{task_and_envelope}` placeholders.
2. New `extract_synopsis_section(md_path, heading)` helper in `src/aedist/util.py` — ≤10 lines, regex-based section extraction.
3. New `experiments/sota/phase_a_prompt_design.py`:
   - argparse: `--adapter {anthropic,openai,mistral,qwen}`, `--dry-run/--live`, `--output-dir`, `--baseline`, `--synopsis`, `--template`.
   - `assemble_meta_prompt(baseline, synopsis, template)` → string (uses `str.format_map`).
   - `compute_shas(baseline_text, quality_bar_text, meta_prompt_text)` → `{baseline_sha, synopsis_section_sha, meta_prompt_sha}` (sha256 hex); plus `synopsis_git_sha` via `git log -1 --format=%H -- docs/synopsis.md`.
   - `load_adapter(name)` — dict registry of 0167/0168/0169(/0173) modules.
   - `validate_envelope(parsed)` — fails loudly on missing/wrong-typed keys; failures land under `<agent>/<ts>.failed.json` with raw payload.
4. New `experiments/outputs/sota_phase_a/README.md` documenting the output layout.
5. Tests: `tests/test_phase_a_harness.py`.

### First failing test (non-tautological)
`test_assemble_meta_prompt_round_trip_sha` — assemble the meta-prompt against real files; assert that the recomputed SHA matches `compute_shas[meta_prompt_sha]`, AND that the assembled string contains `prompt_complete.txt`'s actual contents, AND that synopsis §2 anchors ("Accuracy", "Temporality") appear. Round-trip integrity, not literal-vs-literal.

### JSON envelope
```json
{
  "prompt": "<non-empty str>",
  "settings": {"model": "...", "temperature": 0..2, "max_tokens": int,
               "tools": [...], "thinking": {...} | null},
  "rationale": "<non-empty str>"
}
```

### Output schema (`experiments/outputs/sota_phase_a/<agent>/<ts>.json`)
Top-level keys: `agent`, `agent_family`, `timestamp`, `phase="phase_a_design"`, `baseline_path/sha`, `synopsis_path/section_sha/git_sha`, `meta_prompt_sha`, `request_payload`, `raw_response`, `parsed={prompt, settings, rationale}`, `designed_prompt_sha = sha256(parsed.prompt)`, `run_record`, `cost_usd`, `wall_clock_s`. Phase B reads `parsed.prompt` and `designed_prompt_sha`.

---

## 0171 — Phase C cross-eval rubric + scoring (Wave 3)

### Actions
1. New `experiments/sota/phase_c_rubric.md` — canonical rubric with anchored 0-3 descriptors for Coherence, Provenance-resolves-and-supports, Temporality (see anchors below); Accuracy is mechanical-only, derived from `metrics.compute_metrics` and binned 0-3.
2. New `experiments/sota/phase_c_score.py`:
   - `mechanical_prepass(subject_record)` — uses `parsed_table_path`, calls `load_plants_csv` (`evaluate.py:81`) on reference + system, then `reconcile.reconcile` (`reconcile.py:187` — canonical entry, NOT `matching/lp.py`), then `compute_metrics` (`metrics.py:51`). Returns `BenchmarkMetrics` projection.
   - `bin_f1(f1)` — thresholds 0.15 / 0.35 / 0.60 for 0/1/2/3.
   - `build_prompt(subject_md, rubric, mechanical_priors)` — embeds rubric verbatim + sealed "Known mechanical results" block + subject markdown. Forbids judge from re-scoring Accuracy.
   - `verify_quoted_spans(judge_json, subject_md)` — `fold(s) = re.sub(r"\s+"," ",s.lower()).strip()`; substring match; **hard failure** on miss (no re-prompt; row written with `_status="schema_reject"`).
   - `write_row(row, csv_path)` — append to `experiments/derived/sota_cross_eval.csv`.
3. Tests: `tests/test_phase_c_rubric.py`.

### First failing test (directional + extremal)
`test_mechanical_prepass_separates_known_good_from_known_bad` — fixture A = copy of `data/reference/vietnam_thermal_v1.csv` (perfect), fixture B = 3 fabricated junk rows. Assert `dim_accuracy(A) == 3 and dim_accuracy(B) == 0`. Discrimination check, not type-system check.

### Rubric anchors (sketch)

**Coherence (LLM)**: 0 contradictions/duplicates or implausible units/geo; 1 one class of defect; 2 internally consistent + ≤2 borderline cases; 3 clean.

**Provenance-resolves (LLM)**: 0 no citations or bare URLs; 1 ≥50% cited but spot-checks fail or aggregators only; 2 ≥80% cited, spot-checks pass, mix OK; 3 ≥95% cited, primary sources, ≥30% double-sourced.

**Temporality (LLM)**: 0 no dates / no status; 1 status no dates or <50% dated; 2 status taxonomy + ≥70% dated; 3 every row dated + canonical status taxonomy + single freshness date stated.

**Accuracy (mechanical)**: f1 bins as above; also write continuous `accuracy_f1` to CSV.

### Quoted-span verification
`fold(quoted_span) ∈ fold(subject_md)`; hard-fail on miss (not re-prompt) — keeps measurement honest, surfaces ungroundable judges as auditable rejects, stays under $5 cap.

### Dependencies note
Hard upstream is **0172** (for `parsed_table_path`), even though Blocked-by points at 0167. 0167 supplies an evaluator; 0172 supplies the field `mechanical_prepass` reads.
