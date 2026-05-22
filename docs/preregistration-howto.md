# Pre-registration howto

A procedural guide for publicly pre-registering the AEDIST experimental analysis plans before data collection completes. Specific to Exp 2 (Doc 05 §3.5.1) but the recipe applies to Exp 1 and Exp 3 as well.

## What pre-registration is

A pre-registration is a **timestamped, publicly accessible commitment to a specific analysis plan, made before the analysis is run.** It says: "given the data we will collect, we will compute these specific tests in this specific order with these specific exclusion criteria, and report the result whatever it shows." The point is to make it harder to silently change the analysis after seeing the data (p-hacking, garden-of-forking-paths) and easier for reviewers to evaluate the experimental integrity.

It is NOT a commitment to publish. NOT a contract with anyone. NOT binding in any legal sense. It is a credibility signal: *"this analysis plan was specified before the data was seen, here's the timestamp."*

## When to register

**Before** any of:
- The live batch dispatches (ideally)
- The data is analysed
- Any descriptive statistics are computed on the full dataset
- Any visualisation of the full dataset is generated

Registration **after** data collection but **before** analysis is still meaningful (and common in field-research settings where data collection is unavoidable). What you cannot do is register a plan that already conditions on results you've seen.

For Exp 2: the §3.5.1 table should be registered before Phase B-0 dispatches or, at the latest, before Phase B-full dispatches. The pilot probe (2026-05-22 N=1 naive arm) is exploratory by definition and predates the formal pre-registration; that's fine and worth disclosing.

## Where to register

**Recommended: Open Science Framework (OSF)**, https://osf.io

OSF gives:
- Free, indefinite hosting
- Timestamped registrations with DOIs
- Standard registration forms (OSF Preregistration, AsPredicted-on-OSF, Registered Reports)
- Public access (no login required to view)
- Optional embargo (up to 4 years) if you want to register privately first
- Versioning + amendment tracking

Alternative: **AsPredicted** (https://aspredicted.org) — 8-question template, simpler but less detailed. Used in psychology/behavioural sciences.

For a methodology paper at an economics-of-AI / CS venue, OSF is the strong default.

## What to register for Exp 2

The pre-registration record should include:

1. **Title and authors.** AEDIST authors, paper title (current working title: *"A four-dimensional quality bar for structured statistical-inventory generation by LLMs"*).
2. **Hypotheses.** Copy the six rows of Doc 05 §3.5.1 verbatim.
3. **Sampling plan.** N=5 per agent per arm, 4 agents × 2 arms = 40 sessions total. Rationale: cost differential to N=3 is ~$2 batch-wide and to N=10 is ~$20 batch-wide; N=5 is sufficient for non-parametric tests on large effects with adequate power (see §3.5).
4. **Variables and measurements.** F1 (precision/recall vs. reference dataset, LP-matched), per-row provenance rate, Wikipedia citation count per session, per-agent bounce rate. Exact definitions in Doc 05 §3.7 + §3.8.
5. **Exclusion criteria.** Verbatim from §3.5.1 "Exclusion criteria" subsection.
6. **Analysis plan.** Verbatim from §3.5.1 table. Bonferroni correction for H1–H3 at α=0.0167. Wilson CIs for proportions. Bootstrap CIs for ranks/correlations.
7. **What is exploratory.** Pairwise comparisons (unless Friedman is significant). Parametric tests if attempted. Cross-dimension correlations within an agent. Anything not in the §3.5.1 table.
8. **Reference dataset epistemic status.** A pointer to Doc 05 §3.3 (the reference is a methodological artifact, not ground truth).
9. **Commit SHA of the protocol at registration time.** This locks the protocol text the registration refers to.

## How to register on OSF — step by step

1. **Create an OSF account** at https://osf.io if you don't have one. Use an academic / professional email.

2. **Create a new project.** Dashboard → "Create new project". Title: *"AEDIST Exp 2 — Four-frontier deep-research benchmark on Vietnam thermal inventory"*. Public visibility on by default; private with embargo if you prefer.

3. **Add the protocol as a component or upload as files.**
   - Easier: upload the six protocol docs (`protocol_01_ask.md` through `protocol_06_validation_round_1.md`) plus `protocol_07_naive_prompt.md` to the project's Files tab. Use a single commit SHA — git tag the commit `exp2-prereg-v1` so the docs are reproducible.
   - Alternative: link to the GitHub repo at the specific commit (e.g., `https://github.com/MinhHaDuong/aedist-technical-report/tree/<sha>/experiments/sota/`).

4. **Click "Registrations" in the project sidebar → "Add new"**.

5. **Pick a registration form.**
   - **OSF Preregistration** (recommended for methodology papers): detailed 12-section form covering hypotheses, design, sampling, analysis.
   - **AsPredicted** (simpler, 8 questions): faster to fill, less detailed.
   - **Registered Reports** (if a journal supports it): the analysis plan is reviewed *before* data collection by the target journal.

6. **Fill in the form.** Use the §3.5.1 table content + items 1–9 above. Most fields accept free-text or markdown. Be specific:
   - For "Hypotheses": list H1–H6 verbatim from §3.5.1
   - For "Analysis plan": copy the table, plus the exclusion criteria, plus the multiple-comparison correction
   - For "Sample size justification": cite the §3.5 power discussion (N=5 differential vs N=3 cost; N=5 non-parametric power adequate for large effects)
   - For "Exploratory analyses": list explicitly what will be marked exploratory

7. **Submit.** OSF stamps it immediately. You get a DOI like `10.17605/OSF.IO/XXXXX`. The registration is public and immutable from this point.

8. **(Optional) Embargo.** If you want the registration timestamped but kept private until the paper publishes, set an embargo (up to 4 years). The DOI is still issued and verifiable; only the content is hidden.

## How to handle amendments

If you need to update the analysis plan after registration (e.g., a new hypothesis surfaces, a test changes):

1. **Create an "Update" to the registration on OSF.** It becomes a new version with a new timestamp; the original is preserved.
2. **In the manuscript, disclose the amendment** with the date and rationale. Example: *"After registering the analysis plan on YYYY-MM-DD (OSF DOI 10.17605/...), we observed that hypothesis H3 required a clarification on what constitutes a 'paired turn-pair'; we registered an amendment on YYYY-MM-DD (OSF DOI 10.17605/...) before running the test."*
3. **Never silently change the original.** The original timestamp is the credibility anchor.

## How to cite in the paper

In the §4 methodology section, include something like:

> "The analysis plan was pre-registered on the Open Science Framework on YYYY-MM-DD (DOI 10.17605/OSF.IO/XXXXX) before any data was analysed. Hypotheses H1–H6 in §4.X are tested per the registered plan; any analysis not in the registration is marked as exploratory."

The DOI is the citation. Include it in the references section as well.

## Common pitfalls

1. **Registering after the analysis runs.** This is the cardinal sin. If you've seen the data, the registration is no longer pre. It can still be useful (registering future steps) but should be clearly labelled "delayed registration" with the rationale.

2. **Over-specifying.** A registration that lists every imaginable test risks being a fishing license. Keep H1–H6 as the headline; everything else is exploratory.

3. **Under-specifying.** "We will run statistical tests on F1 scores" is too vague. The §3.5.1 table is specific enough.

4. **Forgetting to disclose exploratory analyses in the paper.** If you ran something not in the registration, label it as such. The credibility of the pre-registered tests is preserved by being clear about what was and wasn't pre-registered.

5. **Citing the wrong commit SHA.** The §3.5.1 text the registration refers to is the version at the registration time. If you edit §3.5.1 later, the registration still points at the old text (that's the point). Use a git tag (`exp2-prereg-v1`) for permanence.

## Mapping to the existing protocol

| §3.5.1 element | OSF form field | Source in this repo |
|---|---|---|
| H1–H6 table | "Hypotheses" + "Analysis plan" | `experiments/sota/protocol_05_experiment.md` §3.5.1 |
| Sample size | "Sampling plan" | §3.5 (N=5 rationale) |
| Exclusion criteria | "Exclusions" | §3.5.1 |
| Reference dataset status | "Variables" / context | §3.3 |
| Phase C rubric | "Variables" / measurement | §3.7 + ticket 0171 |
| Mechanical metrics | "Variables" / measurement | §3.8.4 |

Copy these contents into the OSF form fields. The form will accept Markdown; the rendering is reasonable.

## Time budget

- Account creation + project setup: 10 minutes
- Filling in the form (first time): 30–45 minutes
- Submitting: 1 minute
- Review by yourself before submit: 15 minutes

Total: ~1 hour to first registration. Subsequent experiments take 30 minutes if the template is reused.

## Decision: register Exp 2 now or after Phase B-0?

**Recommended: register before Phase B-0 dispatches.**

The Phase B-0 N=1 gate is operational (does each adapter work?), not statistical. The registered analysis plan applies to the full N=5 batch, of which B-0 is the first replication. Registering before B-0 means the analysis is timestamped before any production data exists.

If you prefer to register after Phase B-0 but before Phase B-full, that's defensible too — Phase B-0 is sub-N statistical-power, so it's effectively pilot data. Disclose in the registration that "1 of 5 reps per agent had already been collected at registration time, intended as an operational smoke; the registered analysis applies to the full 5-rep batch."

The strongest credibility comes from registering before any data lands.
