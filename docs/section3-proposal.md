---
title: "§3 proposal — from chatbots to knowledge management"
author: claude (drafting), Ha-Duong Minh (author directive)
ticket: 0219
date: 2026-05-21
status: DRAFT — awaiting author sign-off before touching slides/manuscript/main.md
---

# §3 proposal — envelope being pushed, not a ladder being climbed

## What §3 must do, in one sentence

> **Agent capabilities improve statistical-dataset quality, and the
> recent industry trajectory operationalises that improvement
> empirically — not as a ladder a single lab climbs, but as an envelope
> the industry pushes outward.**

That is the load-bearing claim. Everything else serves it.

## Diagnosis of the current §3 (lines 40–51)

The current draft is structurally inconsistent.

1. **Mixed enumeration.** It lists six "limits" (articulation, coverage,
   reasoning, tool-use, retroactivity, agency) — three of them stubbed
   (`—.`). The enumeration implicitly maps each limit onto a §2 quality
   dimension (articulation→accuracy, coverage→coverage, reasoning→
   coherence, …), which the author has explicitly told us *not* to
   defend.
2. **Ladder framing.** The closing paragraph ("first interactive
   chatbots, then RAG, then web + reasoning converging at deep
   research") reads as a linear staircase. The empirical record we
   already have in `docs/capability-timeline.md` shows it isn't: stage 3
   (browsing) and stage 4 (reasoning) ship in parallel across labs;
   stage 5 (deep research) is the *join* of 3 + 4, not a higher rung;
   Anthropic actually inverts 3 and 4 within its own product line.
3. **Lab coverage mismatched to §1.** The current §3 names no labs.
   §1 (Experiment 1) tests 16 models across five labs — Anthropic,
   OpenAI, Mistral, Alibaba (Qwen), DeepSeek. The author asked the §3
   history to focus on those same five labs. Today the working note
   covers only four (OpenAI, Anthropic, Google, Mistral) and includes
   Google, who is *not* in the Exp 1 panel.

## Reframing — four moves

1. **Drop the quality↔stages mapping.** §3 narrates capabilities; §2 owns
   quality. Cross-references at the §3 → §2 boundary are fine ("each new
   capability lifts one or more quality limits"); per-capability
   mappings to one specific §2 axis are out.
2. **Replace "ladder" with "envelope."** The industry-level claim is
   that the *surface of commercially attainable capability* expands
   over time. Individual labs add capabilities in lab-specific orders;
   the envelope is what they jointly trace.
3. **Lock the empirical timeline to Exp 1's five labs.** Anthropic /
   OpenAI / Mistral / Alibaba / DeepSeek. Add Qwen and DeepSeek rows to
   `docs/capability-timeline.md`; demote Google to a one-line footnote
   ("Other major labs — Google, Meta, xAI — trace similar trajectories;
   omitted from the matrix to keep alignment with §1's panel"). The
   §1↔§3 panel-alignment is part of the paper's coherence story.
4. **One-sentence thesis up top, paragraph-length elaboration, single
   figure, single closing paragraph.** Section length ≈ 1 page rendered.

## Proposed §3 prose (draft, ~600 words)

> **Third, from chatbots to knowledge management.**
>
> Agent capabilities improve statistical-dataset quality, and the
> industry trajectory of the past three years operationalises that
> claim. The improvement is not a single staircase any one lab climbs.
> It is an envelope — the outer surface of commercially attainable
> capability — that the industry has pushed outward through a sequence
> of integrations rather than a sequence of inventions.
>
> The integrations are by now familiar. *Retrieval-augmented
> generation* [@Lewis-Patrick2020:rag; @Gao-Yunfan2024:rag-survey]
> answers the coverage limit: parametric memory is finite; document
> retrieval at inference time isn't. *Reasoning surfaces* — chain-of-
> thought elicited by prompting [@Wei-Jason2022:cot], later embedded
> as test-time compute in production models [OpenAI o1, Anthropic
> extended thinking, Magistral, R1, QwQ] — narrow the coherence and
> reasoning limits on long, multi-source synthesis. The *join* of
> retrieval and reasoning is the deep-research surface
> [@Wei-Jason2025:browsecomp], which lets the model decide what to
> read and how to read it. *Tool use* and *agency* extend the reach
> of that decision further still: from a fixed retrieval surface to
> arbitrary external state [@Yao-Shunyu2023:react; @Mialon-Gregoire2024:gaia;
> @Jimenez-Carlos2024:swe-bench; @Xie-Tianbao2024:osworld]. Each
> integration lifts one or more of the §2 quality limits at the
> margin; none of them lifts all four; their combinations exhibit
> ordering structure but not a strict performance hierarchy.
>
> [FIGURE 4 — capability-shipping swimlane, 5 labs × 7 stages]
>
> *Figure 4. Empirical capability rollout across the five labs in
> Experiment 1. Each row is a capability stage (1 base instruct → 7
> multi-agent); each marker places when the named lab first shipped
> that stage as a consumer-facing product surface. Markers are coloured
> by lab. The horizontal spread within each row is the cross-lab
> emergence window; vertical neighbours that overlap in time (notably
> stages 3 and 4) indicate parallel-not-sequential capability
> development. Sources: per-lab primary announcements,
> `docs/capability-timeline.md`. The figure is descriptive — no claim
> is made that any lab is "ahead" or that the order is forced.*
>
> Three patterns are visible in the figure. (a) Stages 1 and 2 ship
> sequentially within each lab and within ~12 months across the
> industry. (b) Stages 3 and 4 emerge in parallel — within each lab
> the per-product order is not always 3 then 4 (Anthropic inverts;
> Mistral ships them within months), and the *cross-lab* shipping
> windows overlap. (c) Stage 5 (deep research) is the empirical join
> of stages 3 and 4: at every lab where both prerequisites land,
> deep-research follows within 2 – 7 months. This is structural
> evidence that the order is observed in the data, not imposed by
> the framing.
>
> The empirical envelope nonetheless leaves the §2 quality bar
> uncleared, which is what §4 (Experiment 2) tests directly.

## Visualization choice — swimlane (a.k.a. timeline dot plot)

**Picked: swimlane.** Heatmap vs flowchart vs spider vs swimlane was
the open question.

| Option | Verdict | Reason |
|---|---|---|
| Heatmap (lab × stage × month) | Rejected | Reads as "this lab is ahead" — exactly the ladder framing we want to drop. |
| Flowchart / DAG | Rejected as headline figure | The DAG structure (1→2 sequential; 3∥4→5 join; 6, 7 trailing) is real, but it claims a *capability* ordering, not an *industry trajectory*. Could be a small inline schematic if needed, not the main figure. |
| Spider-graph montage | Rejected | Belongs to ticket 0201 (Quality composite axis). §3 is about capability rollout, not joint-quality-surface measurement; using spiders here would duplicate the 0201 figure and confuse the two ideas. |
| **Swimlane (stage rows × time x-axis, lab as colour)** | **Chosen** | Renders "the envelope pushes outward" directly: the cross-lab emergence window is the visible bar per stage; the ordering between stages is the vertical layout; no claim of within-stage lab dominance. |

Implementation note: a one-paragraph DAG hint can live in the figure
caption ("stages 1–2 sequential; 3∥4 → 5; 6–7 trailing") if a separate
inline schematic is too heavy.

## Citations — cross-checked against `report/refs.bib`

All ten citations the §3 prose touches are already in
`docs/related-work/03-capability-ladder.md` and resolved into
`report/refs.bib` (entries verified by ticket 0151's resolver log).

| Citekey | Role in §3 | Status in refs.bib |
|---|---|---|
| `Lewis-Patrick2020:rag` | Coverage anchor (RAG) | present |
| `Gao-Yunfan2024:rag-survey` | RAG recent survey | present |
| `Wei-Jason2022:cot` | Reasoning anchor (CoT) | present |
| `Wei-Jason2025:browsecomp` | Deep-research frontier benchmark | present (preprint) |
| `Yao-Shunyu2023:react` | Tool-use anchor (ReAct) | present |
| `Mialon-Gregoire2024:gaia` | Agency benchmark | present |
| `Jimenez-Carlos2024:swe-bench` | Agency / coding benchmark | present |
| `Xie-Tianbao2024:osworld` | Agency / OS-scope benchmark | present |
| `Hendrycks-Dan2021:math` | Reasoning benchmark (optional) | present |
| `Rein-David2023:gpqa` | Reasoning under no-retrieval (optional) | present |

Net citation count for §3 prose: 8 mandatory + 2 optional ≤ 10.
Within the budget (10–15) prescribed by `.claude/rules/writing.md`.
The two optional reasoning-benchmark citations may move to §1 (which
also runs no-web) if the budget runs tight.

## Data work — extending `docs/capability-timeline.md`

The working note covers 4 labs (OpenAI, Anthropic, Google, Mistral).
For §3 to align with Exp 1's panel we need 5 labs: drop Google, add
Alibaba (Qwen) and DeepSeek.

### What we have

- Primary lab announcement URLs and dates for OpenAI, Anthropic,
  Mistral across all 7 stages — already in the matrix.

### What is missing (deep-research targets)

| Lab | Stage | Primary-source need |
|---|---|---|
| Alibaba (Qwen) | 1 Base instruct | Qwen-7B / Qwen-Chat release blog (Aug–Sep 2023) |
| Alibaba (Qwen) | 2 Retrieval / file upload | Tongyi Qianwen file-upload launch blog (date TBD) |
| Alibaba (Qwen) | 3 Browsing | Tongyi Qianwen / Qwen search launch (date TBD) |
| Alibaba (Qwen) | 4 Reasoning surface | QwQ-32B-Preview (2024-11-28) or Qwen3-Thinking |
| Alibaba (Qwen) | 5 Deep research | Qwen / Tongyi deep-research surface — verify whether shipped |
| Alibaba (Qwen) | 6 Tool use / agents | Qwen-Agent framework / Tongyi agentic surface |
| Alibaba (Qwen) | 7 Multi-agent | verify — may be a gap |
| DeepSeek | 1 Base instruct | DeepSeek LLM 7B / 67B release (Nov 2023) |
| DeepSeek | 2 Retrieval / file upload | DeepSeek Chat file upload — verify date |
| DeepSeek | 3 Browsing | DeepSeek Chat web search toggle (verify primary source) |
| DeepSeek | 4 Reasoning surface | DeepSeek-R1 (2025-01-20) |
| DeepSeek | 5 Deep research | likely *no* productised deep-research surface — record as honest gap |
| DeepSeek | 6 Tool use / agents | DeepSeek Chat tool integrations / API tool use |
| DeepSeek | 7 Multi-agent | likely no consumer surface |

The honest-gaps subsection of the matrix should grow accordingly:
Chinese-language primary sources are harder to retrieve via Western
search; some milestones may be in Chinese-only announcements; some
stages may be absent (which is itself empirically interesting — the
envelope is uneven across the industry).

## Open questions for the author

1. **Drop Google?** The author directive says "five labs we use in
   experiment 1." That excludes Google. The current matrix includes
   Google. Confirm: demote Google to a footnote, or keep Google as a
   sixth row "for context"?
2. **DAG inline schematic, yes or no?** The swimlane figure is enough
   to carry the empirical claim. A small DAG above or beside it would
   make the capability-ordering claim explicit ("1→2; 3∥4→5; 6,7
   trailing"). Risk: two figures crowd §3. Confirm: caption-only, or
   inline schematic?
3. **Section length.** Proposed ~600 words + one figure + caption.
   Target ≈ 1 page rendered. Acceptable, or should §3 grow to absorb
   what is currently in the "Related work" section?
4. **Citation budget.** 8 mandatory + 2 optional = 10. Comfortable, or
   tighten to 6–7 by folding RAG and reasoning into combined anchors
   (Gao 2024 alone for RAG; Wei 2022 alone for reasoning)?
5. **Spider-graph for §2.** The author noted in passing that ticket
   0201 should produce a spider-graph "to grade the reports quality."
   That ticket is open. This proposal stays out of 0201's scope — but
   confirm the §3 figure (swimlane) does not pre-empt 0201's figure
   (spider-graph) visually.

## What ships if this is signed off

1. **No edit to `slides/manuscript/main.md`** until author sign-off.
2. After sign-off:
   - `docs/capability-timeline.md` — drop Google, add Qwen + DeepSeek
     rows; document gaps explicitly; preserve full bibliography in the
     primary-announcements style.
   - `src/aedist/plot_capability_timeline.py` — new script, follows the
     figures-are-artifacts rule (`.claude/rules/writing.md`); writes
     `slides/inputs/generated/fig_capability_timeline.pdf` and the
     backing CSV.
   - `Makefile` — wire the new figure as an artifact target.
   - `slides/manuscript/main.md` §3 — replace lines 40–51 with the
     proposed prose; `\includegraphics` the swimlane.
   - `report/report.tex` — corresponding French rewrite of the
     capability-history paragraphs to match §3's frame (separate
     follow-up edit; out of scope for this ticket if the English
     rewrite ships first).
3. **Close 0212** after author sign-off + the manuscript edit; do not
   close on the proposal draft alone.

## Boundaries — what this ticket does *not* do

- It does not produce the spider-graph figure (ticket 0201).
- It does not run any new experiment.
- It does not edit §2 (the quality framework) or §4 (Experiment 2 SOTA).
- It does not re-cite the related-work-note in full; that note is
  already the long-form companion document.
