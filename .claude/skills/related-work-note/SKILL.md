---
name: related-work-note
description: Produce an author's due-diligence note for a single cited paragraph of a manuscript — relevance, history-of-science context, cited works (detailed), related-but-not-cited (justified), methods, author-verification checklist, formal bibliography with DOI/URL. Deep-researched; fresh each invocation.
disable-model-invocation: false
user-invocable: true
argument-hint: [paragraph-topic] [output-path]
---

# Related-work due-diligence note

**Purpose.** Academic authorship obliges the author to *know* each
cited work, not merely list it. This skill produces a companion
document that sits alongside a single manuscript paragraph and gives
the author everything needed to defend the paragraph under peer
review — what each cited work did, why it was chosen, what the
alternatives were and why they were dropped, what the field's lineage
is, and how the note itself was assembled.

**Scope.** One invocation = one paragraph = one note file. A section
with N paragraphs needs N invocations. Re-run the skill freshly on
every invocation; do not recycle an older note as a cache. The
Methods section records the invocation date as the freshness cutoff,
so a stale reuse would make the note lie.

## Inputs

The caller must provide:

1. **Paragraph topic or claim** — a phrase or sentence describing the
   paragraph's thesis. Example: *"LLM evaluation targets QA and
   reasoning, not structured statistical-table production."*
2. **Target manuscript path** — repository-relative path to the
   manuscript being written. Example:
   `publications/journal-article/paper_benchmark_merged.md`.
3. **Section identifier** — the section and paragraph number within
   the manuscript. Example: *"§2 Related Work, paragraph 1"*.
4. **Output path** — where the note file should be written. Example:
   `publications/journal-article/notes/02_related_work/01_llm_benchmarks.md`.
5. *(Optional)* **Citation budget** — the maximum number of citations
   the paragraph will use. If supplied, the skill still proposes more
   in "Related but not cited"; the operator cuts down later.

If the caller provides these inline, use them. If any is missing, ask
the caller once before proceeding.

## Procedure

### 1. Read the manuscript context

Read the target manuscript (at minimum the section the paragraph sits
in, ideally also the abstract and introduction) so the note is
tailored to *this* paper's argument, not the general field.

### 2. Deep-research the paragraph topic

Run web and scholar searches to surface:

- **Seminal works** — field-defining references, often older
  (pre-2015). Example: Lewis et al. 2020 for RAG; BERT 2019 for
  transformer-era IE.
- **Review / survey papers** — to let the author drill down later.
  Prefer recent surveys (≤3 years old) with strong citation counts.
- **Recent frontier works** — 2024–2026 results. Preprints allowed
  when no peer-reviewed equivalent exists; flag them as such.
- **Superseded or widely-critiqued works** — so "related but not
  cited" is informed, not arbitrary.

Log every search in the Methods section: the query, the tool, the
date, and the approximate result count that was usable.

### 3. Check the operator's existing bibliography

Before minting new BibTeX keys, check whether the reference already
exists in the project. Scan `report/refs.bib` (if present) and the
operator's Zotero library (see `memory/reference_zotero.md` for
access details). If a match exists, reuse the key. If not, mint a
new key matching the library's style, and note in the bibliography
that the entry is new.

### 4. Draft the note

Use the Output Template (next section) verbatim. Every section is
mandatory — including the Author Verification Checklist. The skill
rejects its own output if:

- any of the seven sections is missing,
- any cited-work entry lacks one of the four required fields,
- any non-cited entry lacks a justification,
- any bibliography entry lacks both DOI and stable URL, or
- the Methods section omits the preprint-acceptability note or the
  freshness cutoff.

### 5. Write the output file

Write the note to the caller-specified path. Do not modify
`report/refs.bib` or any other project file — the skill's output is
a single markdown note.

### 6. Report back

Summarise to the caller in ≤100 words: the path of the produced
note, the number of cited works, the number of "related but not
cited" entries, and any decision points the author should revisit
(e.g., "Gao et al. 2024 RAG survey was dropped in favor of Wang et
al. 2025 — the author may want to reconsider if coverage matters
more than freshness").

## Output template

Emit this markdown structure, filling each section with the results
of steps 1–3.

```markdown
---
title: {paragraph topic — imperative noun phrase}
author: Claude prompted by Ha-Duong Minh
date: {YYYY-MM-DD — the invocation date}
paper: {manuscript path as provided}
section: {section identifier as provided, e.g., "§2 Related Work, paragraph 1"}
---

## Relevance

One paragraph. Why this note exists for this paragraph of this paper:
what claim the paragraph makes, what a referee could legitimately
probe, why each cited work is load-bearing. Do not repeat the
paragraph's text — state the intellectual stakes.

## History of science context

200–400 words. The lineage of the sub-field the paragraph sits in:
the problem's origin, the main paradigm shifts (named with
approximate dates), the current state. The goal is for the author to
position the cited works against the field, not the other way around.
Avoid speculation; if a claim is contested, say so.

## Cited works — detailed

For each work the paragraph cites, produce a block with exactly
these four fields:

### {Author Year — short title}

- **Reference.** Author, year, venue, DOI/URL.
- **What the work did.** Method, data, main result — 2 to 4
  sentences.
- **Why this paragraph cites it.** The specific claim the paragraph
  uses this work to support. One sentence.
- **Limitations or critiques the author should know.** Known
  weaknesses, superseding work, replication failures, or
  community-level debates. One or two sentences.

Repeat for every cited work.

## Related but not cited — justified

For each plausible alternative that an informed reader would expect
to see but that is not cited, provide:

### {Author Year — short title}

One or two sentences: what the work is, and why it was not cited
(superseded by X, off-topic, redundant with Y, weaker evidence,
proprietary/closed, not yet peer-reviewed, too narrow, too broad,
etc.).

Aim for at least two entries. A thin "not cited" list is a red flag
that the search was shallow.

## Methods

How this note was written (the LLM-side record):

- **Searches run.** For each: query, tool (Tavily / Semantic Scholar
  / arXiv / Google Scholar / operator's Zotero library), date,
  approximate useful result count.
- **Databases consulted.** Named explicitly.
- **Freshness cutoff.** "Deep research includes results published
  through {invocation date}." No earlier cutoff — the skill is
  re-run on every consumer invocation to keep this honest.
- **Preprint policy.** arXiv preprints are cited when no
  peer-reviewed equivalent exists; each such entry is flagged in
  the bibliography. Preferred when covering 2024–2026 frontier.
- **LLM-assist disclosure.** This note was drafted by Claude from
  retrieved sources. Cited facts must be verified against the
  primary source by the author before publication.

## Author verification checklist

What the author must still do before the paragraph is defensible.
This is distinct from the LLM-side Methods disclosure above.

- [ ] Opened and read each cited primary source (not just its
      abstract).
- [ ] Confirmed the claim-to-citation mapping for every sentence of
      the paragraph.
- [ ] Checked that any preprint flagged in Methods is still the best
      available citation (peer-reviewed version may now exist).
- [ ] Agreed with the "Related but not cited" justifications — or
      overridden them deliberately.
- [ ] Confirmed no in-repo working document is cited in place of a
      primary source.

## Bibliography

Alphabetical by first author, BibTeX-compatible. Every entry carries
a DOI (when available) **and** a stable URL. Entries flagged
`[preprint]` in the key comment when they are not yet peer-reviewed.

```bibtex
@article{AuthorYEAR,
  author = {Author, A. and Author, B.},
  title  = {{Full title}},
  year   = {YEAR},
  journal = {Venue},
  doi    = {10.xxxx/yyyy},
  url    = {https://stable-url/},
}

% ... more entries ...
```
```

## Notes on style

- Write the note in English.
- Cite author-year in the prose; use the BibTeX key in the
  Bibliography section.
- Use present tense for claims ("Lewis et al. show that…"), past
  tense for methods ("they trained…"), third person throughout.
- Do not cite in-repo working documents (drafts, planning notes,
  other tickets). The paper's related work must stand on external
  published sources and forward references to the paper's own later
  sections.
- Keep the note self-contained: a reader should not need access to
  anything else in the repo to judge the cited works.

## Failure modes to avoid

- Drafting a note with fewer than two "Related but not cited"
  entries. If the search was shallow, say so and stop; do not pad.
- Citing a survey when a specific primary result is what the
  paragraph actually needs, or vice versa.
- Minting a new BibTeX key when the operator's library already has
  the reference under a different key. Always check first.
- Omitting the preprint-acceptability note or the freshness cutoff
  from Methods.
- Padding the bibliography. 15 well-justified citations beats 30
  noisy ones; fewer is fine if the paragraph's claim is narrow.
