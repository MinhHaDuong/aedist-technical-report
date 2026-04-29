# Writing rules — AEDIST

## General structure

**No heading above a one-paragraph subsection.** If a subsection is a single paragraph, drop the heading and let the paragraph stand flat in its parent section.

**Epistemic humility on absence claims.** Use "to our knowledge" or "we did not find" — never "nobody has done" or "no prior work exists."

**Forward-reference, don't link outward.** When a concept is developed later in the same document, point the reader there ("see §3.3") rather than linking to an external working document.

## Related Work sections

**Strict citation budget.** Prefer 10–15 citations for a short Related Work; cut aggressively, record dropped candidates in a companion due-diligence note, not the paper.

**Per-paragraph mix:** one field-defining anchor (often older) + one recent survey + two-to-three recent frontier works (≤2 years old). Not all tiers are required in every paragraph, but this is the default.

**Gap paragraph at end.** The gap statement is its own paragraph, never shares space with topical coverage. Language: "to our knowledge" / "we did not find."

**Cite closely-related projects unconditionally.** Work a reader of this paper would obviously know (e.g., PyPSA-VN, powerplantmatching for an AEDIST-style paper) must be cited even if not strictly required by the argument.

**No in-repo documents in the bibliography.** `docs/*.md`, internal planning notes, and uncommitted artefacts never appear in the paper's references.

## LaTeX macro includes (tectonic)

For ≤3 new macro values, write inline in the slide or append to the existing `macros.tex` — do **not** create a new `\InputIfFileExists{inputs/generated/new_file}{}{}` include. Tectonic resolves filenames against its online bundle first and can silently load the wrong file, causing cryptic "Missing \begin{document}" errors.

**Why:** Agent 0117 burned 20 min on this. Fix was 2 lines inline. Only create a new include file if a script regenerates it on every build run.
