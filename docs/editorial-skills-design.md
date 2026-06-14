# Editorial skills — design note

Status: Imagine/Plan (2026-06-14). Captures the agreed design before any
skill is built. Supersedes the 2022-style "embed + retrieve-k + few-shot
mimic" framing recorded earlier in STATE.

## Motivation

Reading-2 of the AEDIST manuscript surfaced three recurring prose-quality
defects that no CI guard can pin (they are *positive* quality judgments, not
lexically stable — see the polarity rule, ticket 0557):

1. **Scaffolding leak** — instructions and construction-diary residue
   surviving into published prose ("test before blasting", dated decisions,
   imperatives-as-prose).
2. **Voice drift** — LLMisms / dry-academism replacing the author's voice.
3. **Caption altitude** — figure captions pitched above body reading level or
   merely restating the text.

These belong in reusable review-time **IDH skills** (user-level,
`~/.claude/skills/`, so they serve all the author's texts), not in CI.

## One mechanism, three retrieval pools

All three are the same move, parameterized by which exemplar pool feeds it:

> **classify the target's register → select class-matched, sole-authored,
> quality-vetted exemplars → assign the blog as contrast-or-model by class →
> reason an explicit characterization (sharpened by a contrast class) →
> critique-and-realign the target with explained edits.**

| Skill | Exemplar pool | Contrast class |
|-------|---------------|----------------|
| voiceprint | the author's prose **in the target's publication class** | email register; blog (when target is formal) |
| descaffold | clean published prose (the "after") | scaffolded/diary prose (the "before") |
| caption-altitude | good captions at the right reading level | over-pitched / body-restating captions |

## Why not the 2022 version

"Embed the corpus, retrieve k paragraphs, few-shot mimic" pattern-matches
surface n-grams; it does not *understand* the voice, and it is hostage to a
vector index. The 2026 version spends the model's reasoning instead:

- **Long context over retrieval.** Put 3–6 *whole* class-matched articles in
  context. A strong model internalizes a voice from full pieces far better
  than from k detached paragraphs (rhetorical moves, argument rhythm, how the
  author hedges, where the prose goes terse).
- **Reasoned characterization is the artifact.** The model reasons out an
  explicit voice characterization per run — generated fresh, not a stored
  profile to ratify. No vector store, no readability-scorer machinery, no
  standing "voiceprint artifact" file.
- **Contrast is signal, not noise.** Hand the model the author's article prose
  *and* the email/blog register and ask it to articulate the discriminating
  axes. The thing we were trying to filter out sharpens the model's model.
- **Realign by reasoned critique, not mimicry.** The model diffs the target
  against its own characterization and rewrites with *explained* edits ("this
  nominalization is dry-academism; he'd use a verb"), optionally in a short
  self-critique loop. Auditable, not a black-box rephrase.
- **World knowledge where it is safe.** What counts as an LLMism, French
  academic-register norms, what reads above grade level — general knowledge the
  model already has. The corpus is *only* for author-specific voice; never lean
  on training priors for "what the author sounds like" (hallucination risk).

## Register is the load-bearing variable

Voice is class-conditional. The publication list is stratified and each class
has its own voice:

- Exemplar source = `~/CNRS/papiers/published/{Peer reviewed, Reports,
  Inproceedings, Non-peer reviewed, Books}/` — the author's actual articles,
  already filed by class. **Step zero: classify the target, then draw
  exemplars only from the matching class.** AEDIST (English arXiv preprint) →
  Peer-reviewed + Reports strata, never the popular register.
- **The blog role-flips by target class.** banhhanoi.art / co2capture are
  *contrast* when the target is formal (a report/paper), *model* when the
  target is itself a blog post.

## Corpus discipline (the email-imbalance lesson)

Do **not** mine the `chemin-de-voix` `voix-auteur-{en,fr}` chunkstore. It is a
disk-wide harvest (manifest 2026-04-27) contaminated with non-author content:
external RePEc working papers, others' job dossiers, course material, and 3500+
email docs. Volume-weighted sampling there learns the email register and brands
the article voice as drift. The `published/` tree is the clean, class-stratified
substitute — there is no retrieval problem to solve once you read from it.

## Two provenance gates before any exemplar is used

- **Authorship.** Verify the author is the voice. Co-authored papers blend
  voices (e.g. `Keith.ea-2006…` is Keith-led — not his voice); prefer
  sole/lead-authored pieces. Never feed a co-author's paragraphs as "his
  voice."
- **Intrinsic quality.** Vet each exemplar first. A rushed or dated piece
  teaches the wrong target. Exemplars are *curated*, not merely *retrieved*.

The real upfront work is a one-time **curated, authorship-clean exemplar
shortlist per class** — not per-run retrieval.

## MVP plan

Each skill's first cut is an agent prompt implementing the mechanism above on a
real target paragraph, with exemplars selected live from the `published/` tree.
No vector store, no scorer. Apply to `slides/manuscript/main.tex` (English) to
see how it works, then decide what to harden into a `SKILL.md`. The
`/review-pr-prose` panel is the eventual host for the lenses; an
`editorial-brief.md` entry records each standing decision (review-time, not CI).

## Corrected objective (post-MVP, 2026-06-14) — the skill REDUCES

The skill is a **prose fixer for tone, style, and complexity**, and every
operation moves *down*. The author's voice is the destination register; the
operations are reductive — split, plain-verb, de-confetti, shorten. "Realign to
voice" must never be read as "make more academic / more elaborate." Two live
MVP runs pinned the failure modes on both sides:

- **Run 1 (wrong test, wrong direction).** Target was a paragraph the author
  wrote himself (`main.tex:106`) — a circular test: the input already was the
  target, so there was no signal. Worse, the rewrite *climbed* — added an
  em-dash (an LLM tell), lengthened sentences, raised clause depth. The model
  conflated "formal academic voice" with "more complex."
- **Run 2 (right test, overshoot).** Round-trip with ground truth: take the
  author's plain original → bloat it into LLM-prose (226 words, 37.7
  words/sentence, 2 em-dashes, 9 LLMisms) → fix it. The fixer reduced correctly
  (117 words, 11.7 words/sentence, 0 em-dashes, 0 LLMisms, facts preserved) —
  but **overshot below the author's own ~18 words/sentence into a choppy,
  staccato rhythm that is not his either.**

### Test design: round-trip with the author's own prose as answer key

A voice/style fixer cannot be validated on the author's already-good prose
(circular, no signal). The valid experiment: **bloat a known-plain author
paragraph into LLM-prose, fix it, and score the fix against the original.** The
author's own writing is the ground truth precisely because he wrote it.

### Calibration rule 1 — descaffold whitelist

First-person scientific narration is **in-register**, not scaffolding: "we
observed that", "we tested", "we found", "we measured" are the courteous prose
form of `Results:` / `Methods:` headers. Do NOT strip them. The real descaffold
target is *construction / process-diary* leak — narration of how the **writing
or engineering** was managed ("test before blasting", dated build decisions,
instructions-as-prose, harness/operator travelogue). Discriminator: reports a
scientific action or finding → keep; narrates the authoring process → cut.

### Calibration rule 2 — complexity target is a BAND, not a floor of zero

"Reduce complexity" needs a target, and the exemplars set it. The author's
measured sentence-length distribution and hedge density *are* the destination
band (his ~18 words/sentence here). Don't climb (run 1), don't minimize past
him (run 2) — land in his band. This turns the corpus from a vague "voice"
notion into a concrete, measurable calibration, and it is the same per-class
n≥3 sole-authored shortlist the authorship gate already requires.

### Reduction guards (concrete, checkable per run)

Output words ≤ input words; mean sentence length within the author's band (not
merely lower); em-dash count 0; count of LLMism-list words 0; every number and
claim preserved verbatim; **no new summary verdicts invented** (run 1's engine
smuggled a "does little better" clause — realign can fabricate claims; guard
against it).

### Contrast is conditional (correcting the table above)

For a formal target the useful contrast is the **email / agent-speak / LLMism**
register; the food/personal blog is too distant to sharpen a technical abstract
(confirmed empirically — it changed nothing in run 1). The blog earns its keep
only when the target is near its register (the role-flip).

### What the MVPs settled

- **Authorship gate works and is essential** — it correctly rejected
  co-authored AdaPation (Dumas-led) and Kopf-2007, exactly as designed. But it
  starved voiceprint to n=1; the curated per-class shortlist is the
  precondition, not a nicety.
- **Ship descaffold first** — it stands alone (lexically stable signatures,
  high precision, no corpus dependency). **voiceprint runs after descaffold**,
  on already-clean prose, so its marginal value is visible — and needs the n≥3
  shortlist + the complexity band before it is trustworthy.
- On scaffold-heavy prose the two skills overlap ~70%; the genuinely
  voiceprint-only moves are small (the don't-over-correct boundary). Test
  voiceprint on prose with no scaffolding leak to see it stand on its own.

## Parked state (2026-06-14)

Design parked for a fresh restart from first principles. Durable artifacts on
this branch:
- this design note (`docs/editorial-skills-design.md`);
- the verbatim session transcript (`docs/editorial-skills-transcript.md`) —
  both the spec session and the MVP session, user↔assistant dialogue preserved.

The two MVP agent prompts and their full outputs live in the transcript. No
skill files were written; no manuscript prose was changed.
