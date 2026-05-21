# Capability rollouts at the five major LLM labs

*Working note for the AEDIST technical report. Documents the empirical
chronology of capability stages (base instruct -> retrieval -> browsing /
reasoning -> deep research -> tool / agent use -> multi-agent) at the
five labs covered by Experiment 1's panel: Anthropic, OpenAI, Mistral,
Alibaba (Qwen), and DeepSeek. Google / DeepMind is retained as a
footnote (see [Note on Google / DeepMind](#note-on-google--deepmind))
because Gemini is not in Experiment 1's panel but its rollout cadence
is informative for cross-referencing.*

> **Status note (ticket 0218, 2026-05-21).** This note has been
> rewritten to the five-lab panel after Qwen and DeepSeek primary
> sources landed. The machine-readable source of truth for the §3
> figure is `data/capability_timeline.csv`. Three Qwen cells and three
> DeepSeek cells are recorded as `absent` (no productised consumer
> surface) with cutoff 2026-05-21; see "Honest gaps and divergences".

## Hypothesis

The seven capability stages we track are not a strict chain. The claim:

- **Stages 1 -> 2 are sequential** (instruct LLM, then retrieval / file
  upload).
- **Stages 3 and 4 emerged in parallel** (browsing / web tools AND
  reasoning model surfaces both shipped as products in 2024).
- **Stage 5 (deep research) is the join of 3 + 4** — multi-step web
  retrieval driven by a reasoning model, with citations.
- **Stages 6 -> 7 follow** (general tool use / computer use, then
  multi-agent coordination).

The "ladder" is therefore a small DAG, not a chain, with a fork between
1-2 and 5, and a merge at 5. The hypothesis is industry-level: at any
single lab, stage 3 (browsing) was usually shipped well before stage 4
(reasoning), but the *industry-level emergence window* of stage 4 (late
2024) overlaps the steady-state availability of stage 3 across labs, so
stage 5 became reachable for all four labs within a six-month window.

## Capability stages (schema)

1. **Base instruct LLM** — text-only, single-turn, parametric memory.
2. **Retrieval / RAG / file upload** — documents at inference time.
3. **Browsing / web search** — live external retrieval as a product.
4. **Reasoning / chain-of-thought as a product surface** — visible
   thinking, test-time compute exposed to users.
5. **Deep research** — multi-step web + reasoning, long-running, citations.
6. **General tool use / computer use / coding agents** — autonomous
   action over a tool surface (we record the *agentic surface* form, not
   the bare function-calling API; the API form is noted in the
   bibliography for context).
7. **Multi-agent coordination** — agent teams, sub-agent dispatch,
   orchestrator-worker patterns.

## Matrix: stage x lab

The matrix below is the five-lab panel that backs Experiment 1. The
machine-readable source of truth is `data/capability_timeline.csv`;
the rows here mirror that file. Cells marked *absent* are not "we
could not find a source" but verified gaps: no productised consumer
surface as of the 2026-05-21 cutoff. Google / DeepMind is recorded in
a footnote (see below) because Gemini is not in the Experiment 1
panel.

| Stage | OpenAI | Anthropic | Mistral | Alibaba (Qwen) | DeepSeek |
|---|---|---|---|---|---|
| **1. Base instruct LLM** | 2022-11-30 ChatGPT [(blog)][1] | 2023-03-14 Claude [(blog)][8] | 2023-09-27 Mistral 7B Instruct [(blog)][22] | 2023-08-03 Qwen-7B (Tongyi Qianwen) [(blog)][28] | 2023-11-29 DeepSeek LLM 7B/67B [(blog)][33] |
| **2. Retrieval / file upload** | 2023-10-30 ChatGPT All-Tools (PDF / file analysis) [(coverage)][6] | 2024-06-25 Projects (file upload to Claude.ai) [(blog)][9] | 2025-02-06 Le Chat (document upload) [(blog)][23] | 2023-10-31 Tongyi ZoneWit document upload (Apsara 2023) [(blog)][29] | 2025-01-15 DeepSeek App launch with file upload [(news)][34] |
| **3. Browsing / web search** | 2023-05-12 Browse with Bing (Plus rollout) [(plugin post)][2] | 2025-03-20 Claude web search [(blog)][10] | 2025-02-06 Le Chat web search [(blog)][23] | absent (no first-party source verifiable at cutoff) | 2024-12-10 Internet Search on chat.deepseek.com [(news)][35] |
| **4. Reasoning surface** | 2024-09-12 o1-preview [(blog)][3] | 2025-02-24 Claude 3.7 extended thinking [(blog)][11] | 2025-06-10 Magistral [(blog)][24] | 2024-11-28 QwQ-32B-Preview [(blog)][30] | 2025-01-20 DeepSeek-R1 [(blog)][37] |
| **5. Deep research** | 2025-02-02 Deep Research [(blog)][4] | 2025-04-15 Research [(blog)][12] | 2025-07-17 Le Chat dives deep [(blog)][25] | 2025-05-13 Deep Research on Qwen Chat [(X)][31] | absent |
| **6. Computer use / coding agent** | 2025-01-23 Operator (CUA) [(blog)][5] | 2024-10-22 Computer use beta [(blog)][13] / 2025-02-24 Claude Code [(blog)][11] | 2025-05-27 Agents API [(blog)][26] | 2024-04-07 Qwen-Agent v0.0.1 (developer framework) [(release)][32] | 2024-07-25 Function Calling API [(updates)][36] |
| **7. Multi-agent coordination** | 2024-10 Swarm (experimental) -> 2025-03 Agents SDK [(blog)][7] | 2025-06-13 multi-agent Research system + Claude Code subagents [(eng blog)][21] | 2025-05-27 Agents API multi-agent orchestration [(blog)][26] | absent | absent |

## Parallel branches: where the chain becomes a DAG

The matrix shows three reasons the linear "ladder" framing breaks down.

**Stage 3 || stage 4 at the industry level.** Browsing (stage 3) shipped
two years before the reasoning surface (stage 4) at OpenAI (May 2023 vs
Sept 2024) and at Google (Bard 2023 search grounding vs Dec 2024 Flash
Thinking). Per-lab at those two labs, the *per-product* sequence is the
expected 1 -> 2 -> 3 -> 4 -> 5. But Anthropic shipped its reasoning
surface (extended thinking, 2025-02-24) *before* its consumer web search
(2025-03-20) — a per-product inversion of 3 and 4 that would be
impossible if 3 strictly preceded 4. Mistral shipped both within weeks
in 2025, with web search (Feb) before reasoning (June). Across the four
labs, the *industry-level emergence window* for stage 4
(Sept 2024 - June 2025) is so compressed that, for any given calendar
month in that window, some labs are in stage 3 and others in stage 4
with similar maturity. Treating 3 and 4 as parallel branches of the
DAG matches the cross-lab data — and Anthropic's per-lab inversion —
better than treating them as sequential.

**Stage 5 = stage 3 join stage 4.** Deep research products are not new
capabilities but compositions: each lab ships deep research within
2-7 months of having both a reasoning surface and a web tool. OpenAI:
Sept 2024 (o1) + May 2023 (Bing) -> Feb 2025 deep research (5 months
after o1). Google: Dec 2024 (Flash Thinking) + 2023 (search) -> Dec
2024 deep research (same week as Flash Thinking, on Gemini 1.5 Pro).
Mistral: June 2025 (Magistral) + Feb 2025 (Le Chat search) -> July 2025
deep research (5 weeks after Magistral). The composition is *forced*:
the moment a lab has both prerequisites, the deep-research product
follows quickly. This is the strongest evidence that stage 5 is a
join, not a separate capability that the lab "decides" to build.

**Stage 6 splits between research-preview and API form.** The "general
tool use" cell is awkward because each lab has at least two distinct
surfaces: the bare function-calling / tool-use API (OpenAI 2023-06-13,
Anthropic via tool-use API 2024, Google via Gemini API 2024, Mistral
function calling 2024) and the agentic consumer surface (Operator,
Computer Use beta, Project Mariner, Agents API). We record the agentic
surface in the matrix because that is the product form; the API form is
typically a precondition rather than the capability itself.

## Honest gaps and divergences

- **Mistral has the most compressed timeline.** All six product-stage
  cells (1-6) ship between Sept 2023 and July 2025, ~22 months. By
  contrast OpenAI's stage 1 to stage 5 spans 27 months and Anthropic's
  spans 25 months. Mistral arrived later and shipped the stack faster
  because the scaffold (RAG patterns, web search APIs, reasoning
  RL recipes) was already public by 2025.
- **Stage 7 is fuzzy and we did not pin sharp dates.** "Multi-agent
  coordination" as a *product surface* (vs a paper / experimental
  framework) is still emerging. OpenAI's Swarm (Oct 2024) was
  explicitly experimental and not for production; the Agents SDK
  (March 2025) is the real shipped surface. Anthropic's multi-agent
  Research system was disclosed in a June 2025 engineering blog post,
  but the consumer-facing Research feature predates that. Google's
  Project Mariner expanded to "10 tasks at a time" at I/O 2025 (May
  2025) [(blog)][27], which is the closest thing to a multi-agent
  consumer surface. Mistral's Agents API (May 2025) advertises
  orchestration but the multi-agent semantics are not yet a separate
  product. Reading the matrix row honestly: stage 7 is an industry
  trajectory, not a clean product line.
- **Mistral stage 2 (file upload) is late.** Le Chat got document
  upload in Feb 2025, well after Mistral 7B Instruct shipped in Sept
  2023. The API supported function calling and external retrieval
  patterns earlier, but the *consumer-facing* file upload — which is
  what stage 2 is — arrived in 2025.
- **OpenAI stage 2 boundary is fuzzy.** ChatGPT plugins (March 2023)
  included a retrieval plugin and a browsing plugin; we treat the
  October 2023 "All Tools" rollout (PDF analysis + Code Interpreter +
  uploads, no plugin needed) as the stage-2 milestone because that is
  when retrieval became a default consumer surface. The plugin era
  has since been deprecated.
- **No primary OpenAI blog post for the May 2023 Browse-with-Bing
  rollout.** The plugin post [(1)][2] is the closest primary source;
  the rollout date itself is in OpenAI help-center release notes.
  Listed as 2023-05-12 with caveat.
- **Anthropic API web search vs consumer web search.** Consumer web
  search shipped 2025-03-20; API web search shipped 2025-05-07
  separately (mentioned in the same blog rollup [(10)][10]). We
  record the consumer date as the stage-3 milestone.
- **Alibaba (Qwen) has the broadest agentic developer surface but
  three absent consumer cells.** Qwen-7B (Aug 2023) and the
  Tongyi-branded consumer surface arrived early; Qwen-Agent v0.0.1
  shipped as a developer framework on PyPI / GitHub in April 2024
  [(release)][32], well before most peer labs put an agentic surface
  in front of consumers. The remaining absences are deliberate: stage
  3 (browsing / web search as a consumer Tongyi feature) has no
  primary first-party source we could verify by cutoff; tertiary
  reports point to a tongyi.ai deep-search launch circa 2024-08 but
  the lab itself does not blog it. Stage 7 (multi-agent consumer
  product) is absent because Qwen-Agent remains a developer framework
  — there is no QwenChat-side multi-agent product. Stage 5 (Deep
  Research on Qwen Chat, 2025-05-13) is the only cell sourced from a
  lab X / Twitter post rather than a long-form blog [(X)][31]; the
  ticket method allows X posts from the official lab handle as a
  primary source.
- **DeepSeek has the most compressed stack of any focus lab.** All
  five productised stages (1, 2, 3, 4, 6) ship between Nov 2023
  (DeepSeek LLM 67B) and Jan 2025 (DeepSeek App + R1) — 14 months,
  faster than Mistral's 22-month run. The same pattern that made
  Mistral fast applies in stronger form: by 2024-2025 the scaffolds
  (RAG patterns, web-search integrations, reasoning RL recipes, tool /
  function calling) were public, so a focused lab could ship a stack
  by composition. Stages 5 (deep research consumer product) and 7
  (multi-agent consumer product) are absent: DeepSeek's API surface
  supports the building blocks but the chat.deepseek.com consumer
  product does not have a deep-research mode or a multi-agent
  consumer feature as of the cutoff.

### Note on Google / DeepMind

Gemini is not in Experiment 1's five-lab panel, so it is not in the
matrix above; the historical record is preserved here for cross-lab
context. Stage 1: 2023-03-21 Bard [(blog)][14] / 2023-12-06 Gemini 1.0
[(blog)][16]. Stage 2: 2023-07-12 NotebookLM [(blog)][15]. Stage 3:
search-grounded since Bard 2023; 2024-12-11 Gemini 2.0 native tool use
[(blog)][17]. Stage 4: 2024-12 Gemini 2.0 Flash Thinking Experimental
[(blog)][18]. Stage 5: 2024-12-11 Gemini Deep Research [(blog)][19].
Stage 6: 2024-12-11 Project Mariner [(blog)][17] / 2025-10 Gemini 2.5
Computer Use [(blog)][20]. Stage 7: 2025-05-20 Project Mariner
multi-task agent system (I/O 2025) [(blog)][27].

## Bibliography

Primary lab announcements only. URLs as published; redirects from
`anthropic.com/news/...` to `claude.com/blog/...` are noted where
encountered.

[1]: https://openai.com/index/chatgpt/ "Introducing ChatGPT (OpenAI, 2022-11-30)"
[2]: https://openai.com/index/chatgpt-plugins/ "ChatGPT plugins (OpenAI, 2023-03-23; browsing / retrieval plugins. Browse with Bing rollout to Plus users 2023-05-12 per release notes.)"
[3]: https://openai.com/index/learning-to-reason-with-llms/ "Learning to Reason with LLMs / o1-preview (OpenAI, 2024-09-12)"
[4]: https://openai.com/index/introducing-deep-research/ "Introducing deep research (OpenAI, 2025-02-02)"
[5]: https://openai.com/index/introducing-operator/ "Introducing Operator (OpenAI, 2025-01-23)"
[6]: https://openai.com/index/function-calling-and-other-api-updates/ "Function calling and other API updates (OpenAI, 2023-06-13). Note: stage-2 milestone for OpenAI is the 2023-10-30 ChatGPT All-Tools rollout (PDF / file analysis without plugin); covered in ChatGPT release notes, no standalone blog post."
[7]: https://openai.com/index/new-tools-for-building-agents/ "New tools for building agents / Agents SDK (OpenAI, 2025-03). Swarm (Oct 2024) was experimental; the Agents SDK is the production successor. Primary page returned 403 to our automated fetch; date narrowed to month from OpenAI press coverage and developer-community thread."
[8]: https://www.anthropic.com/news/introducing-claude "Introducing Claude (Anthropic, 2023-03-14)"
[9]: https://www.anthropic.com/news/projects "Collaborate with Claude on Projects (Anthropic, 2024-06-25). File upload to Claude.ai for Pro / Team."
[10]: https://www.anthropic.com/news/web-search "Claude can now search the web (Anthropic, 2025-03-20). Redirects to claude.com/blog/web-search."
[11]: https://www.anthropic.com/news/claude-3-7-sonnet "Claude 3.7 Sonnet and Claude Code (Anthropic, 2025-02-24). Combines reasoning surface (extended thinking) and Claude Code coding-agent launch."
[12]: https://www.anthropic.com/news/research "Claude takes research to new places (Anthropic, 2025-04-15). Redirects to claude.com/blog/research."
[13]: https://www.anthropic.com/news/3-5-models-and-computer-use "Introducing computer use, a new Claude 3.5 Sonnet, and Claude 3.5 Haiku (Anthropic, 2024-10-22)."
[14]: https://blog.google/technology/ai/try-bard/ "Try Bard from Google (Google, 2023-03-21)."
[15]: https://blog.google/technology/ai/notebooklm-google-ai/ "NotebookLM (Google, 2023-07-12). Source-grounded retrieval over user-uploaded documents — Google's stage-2 product."
[16]: https://blog.google/technology/ai/google-gemini-ai/ "Introducing Gemini (Google, 2023-12-06)."
[17]: https://blog.google/technology/google-deepmind/google-gemini-ai-update-december-2024/ "Gemini 2.0 announcement (Google, 2024-12-11). Includes Project Mariner, Deep Research, native tool use."
[18]: https://blog.google/feed/gemini-app-experimental-models/ "Gemini 2.0 Flash Thinking Experimental in Gemini app (Google, 2024-12). The blog.google primary page does not stamp a precise day; cross-source coverage (siliconangle, 9to5google) reports 2024-12-19. Matrix uses 2024-12 to stay on a primary-source date."
[19]: https://blog.google/products/gemini/google-gemini-deep-research/ "Try Deep Research in Gemini (Google, 2024-12-11)."
[20]: https://blog.google/technology/google-deepmind/gemini-computer-use-model/ "Gemini 2.5 Computer Use model (Google, 2025-10)."
[21]: https://www.anthropic.com/engineering/multi-agent-research-system "How we built our multi-agent research system (Anthropic Engineering, 2025-06-13). Documents the orchestrator-worker architecture behind the Research feature."
[22]: https://mistral.ai/news/announcing-mistral-7b "Mistral 7B (Mistral, 2023-09-27)."
[23]: https://mistral.ai/news/all-new-le-chat "The all new le Chat (Mistral, 2025-02-06). Web search and document upload in one launch."
[24]: https://mistral.ai/news/magistral "Magistral (Mistral, 2025-06-10). First reasoning model from Mistral."
[25]: https://mistral.ai/news/le-chat-dives-deep "Le Chat dives deep (Mistral, 2025-07-17). Deep Research preview."
[26]: https://mistral.ai/news/agents-api "Build AI agents with the Mistral Agents API (Mistral, 2025-05-27)."
[27]: https://blog.google/innovation-and-ai/models-and-research/google-deepmind/gemini-universal-ai-assistant/ "Gemini as a universal AI assistant (Google I/O 2025, 2025-05-20). Project Mariner expanded to 10 simultaneous tasks; closest consumer surface to multi-agent."
[28]: https://qwenlm.github.io/blog/qwen-7b/ "Qwen-7B (Alibaba, 2023-08-03). First open-weight release of the Tongyi Qianwen series."
[29]: https://www.alibabacloud.com/blog/600550 "Tongyi ZoneWit document upload at Apsara 2023 (Alibaba Cloud, 2023-10-31). Consumer document-analysis surface on Tongyi Qianwen."
[30]: https://qwenlm.github.io/blog/qwq-32b-preview/ "QwQ-32B-Preview (Alibaba, 2024-11-28). First reasoning-surface model from the Qwen team."
[31]: https://x.com/Alibaba_Qwen/status/1922307096886051025 "Deep Research live on Qwen Chat (Alibaba_Qwen on X, 2025-05-13). Lab X post is the primary source; no long-form blog at the time of cutoff."
[32]: https://github.com/QwenLM/Qwen-Agent/releases "Qwen-Agent v0.0.1 (QwenLM on GitHub / PyPI, 2024-04-07). Developer-facing agent framework; predates most peer-lab consumer agents but is not itself a consumer surface."
[33]: https://api-docs.deepseek.com/news/news1129 "DeepSeek LLM 7B / 67B announcement (DeepSeek, 2023-11-29)."
[34]: https://api-docs.deepseek.com/news/news250115 "DeepSeek App launch with file upload and text extraction (DeepSeek, 2025-01-15)."
[35]: https://api-docs.deepseek.com/news/news1210 "V2.5-1210: Internet Search live on chat.deepseek.com (DeepSeek, 2024-12-10)."
[36]: https://api-docs.deepseek.com/updates "DeepSeek Function Calling API (DeepSeek, 2024-07-25). Stage-6 milestone for DeepSeek; the consumer chat surface does not currently expose a separate agent product."
[37]: https://api-docs.deepseek.com/news/news250120 "DeepSeek-R1 (DeepSeek, 2025-01-20)."
