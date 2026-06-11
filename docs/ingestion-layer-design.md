# AEDIST — Ingestion Layer Design

*HDM with Claude*
*2026-05-28*

**Scope:** the extraction stage between *source discovery & fetching* and *chunking into storage*.
**Status:** design summary (rev. 2 — Docling spine) · **Working language:** EN · **Storage model:** Maildir-style filesystem queue + DVC stages

---

## 1. Purpose and boundaries

This layer turns **fetched raw documents** into **normalized, provenance-tagged, validated text+structure** that the chunker can consume. It does not discover or download sources (upstream), and it does not chunk, embed, or index (downstream).

```
[ discovery + fetch ] → ╔════════════ INGESTION LAYER ════════════╗ → [ chunk → embed → store ]
  OpenAlex / HAL          Docling standard pipeline as spine:                (out of scope here)
  EVN / PVN reports         triage → layout → OCR → tables →
  Quyết định 768/QĐ-TTg     reading order → normalize → validate → emit
```

**Input contract (from fetch):** a raw artifact on disk (PDF / image / Office / HTML), plus a minimal fetch record (source URI, retrieval timestamp, declared MIME, upstream identifier).

**Output contract (to chunker):** a normalized document record derived from a `DoclingDocument` (see §7) — canonical Markdown, per-block provenance, language tags, TableFormer cell-graphs, extraction method, and confidence/validation flags.

---

## 2. Design principles (ranked)

1. **Verifiable numeric fidelity over fluency.** AEDIST extracts energy statistics (capacities, COD years, output). A confidently wrong digit is worse than a flagged gap. Every figure must trace to a deterministic layer with a confidence signal, never to an unvalidated generative output.
2. **Deterministic source of truth.** Authoritative text comes from the Docling *standard* pipeline (deterministic layout + OCR + TableFormer). Any VLM output is a *hypothesis* validated against that layer, not ground truth.
3. **Orchestrate, don't hand-roll.** Docling is the spine: it already provides triage, layout, OCR, reading order, and table structure behind one `DoclingDocument` model. We own configuration, validation, and queue/state — not the document-understanding plumbing.
4. **Self-hosted, sovereign, permissive.** Everything runs locally on Padme. Docling and Granite-Docling are Apache-2.0; the default path keeps Vietnamese government sources off third-party infrastructure. Cloud OCR is an optional, measured escalation (EU provider only).
5. **Reproducible.** Each stage is a DVC step with pinned tool/model versions and content-addressed I/O. The single non-deterministic step (VLM) is fenced and recorded with model digest + params.
6. **Triage before OCR.** Never OCR a page that already carries a clean text layer.

---

## 3. Pipeline — Docling standard pipeline as spine

The spine is `DocumentConverter` configured with the **standard** (non-VLM) pipeline. Stages below map to Docling components; AEDIST adds only triage policy, OCR-backend selection, the numeric gate, and emission.

### 3.1 Triage / classify
- **Born-digital vs scanned:** rely on Docling's text-cell extraction; score coverage and garbage ratio per page. Clean text layer → OCR is skipped for that page.
- **Language:** detect VN / FR / EN at document and block level (drives OCR-backend language config and VLM routing).
- **Type hint:** decree / report / scholarly PDF / table-heavy — sets the extraction profile and validation strictness.

### 3.2 Layout + reading order
Docling **Heron** layout model (RT-DETR, DocLayNet-trained) classifies page elements (heading, paragraph, table, figure, caption) and resolves reading order across multi-column pages. No AEDIST code.

### 3.3 OCR backend — a *benchmarked configuration choice*
The OCR engine is a pluggable Docling backend, selected by benchmark on a representative VN/FR/EN sample, not a competing orchestrator.

| Backend | Status | VN support | Notes |
|---|---|---|---|
| **EasyOCR** (Docling default) | candidate | 80+ langs incl. `vi` | strong baseline, GPU on A4000 |
| **Tesseract** (`vie`/`fra`/`eng`) | candidate | yes, diacritics mediocre | CPU; fallback |
| **RapidOCR** | candidate | yes | ONNX, fast |
| **Surya** | *external comparator* | strong | not a native Docling backend; bench separately to see if a quality gap justifies a custom integration |
| **Mistral OCR 3** (EU API) | *escalation* | 99%+ multilingual | cloud; for pages the local backend mangles |
| **ABBYY FineReader Engine** | *reserve* | 200+ langs | on-prem, commercial; only if a measured table gap justifies licensing |

Decision rule: pick the best-scoring *local* backend as default; route low-confidence pages to Mistral; hold Surya/ABBYY as comparators, not production dependencies.

### 3.4 Table structure
**TableFormer V2** converts detected table regions into machine-readable cell-graphs (handles missing borderlines, empty cells, spans, hierarchical headers). This is the component that makes EVN/PVN capacity tables usable, and it feeds the table sidecar in §7 directly.

### 3.5 Normalize
- Unicode **NFC** with explicit VN diacritic-correctness checks (composed forms; common OCR confusions logged).
- Canonical Markdown via `DoclingDocument.export_to_markdown()`; tables exported both as Markdown *and* as the TableFormer cell-graph (JSON) so figures are never trapped in rendered text.
- Hyphenation/whitespace repair; column de-interleaving driven by Heron reading order.

### 3.6 Validate (numeric gate)
- Cross-check every extracted figure against the deterministic OCR/TableFormer layer (string + cell-position match).
- Range/unit sanity checks (plausible capacity bounds; MW vs GW consistency).
- VLM-vs-deterministic discrepancy → block **flagged, not dropped**, routed to human curation (Emma's curation pattern reused).

### 3.7 Emit
Serialize the normalized record (§7) to the queue's `done/` state for the chunker.

> **VLM pipeline — deliberately *not* the default.** Docling can run a single-pass VLM (Granite-Docling-258M, DocTags). It is faster and avoids multi-stage OCR error accumulation, but a single-pass VLM can emit a confidently wrong figure. It is therefore confined to the §6 hypothesis role over already-extracted pages, never the source of truth for numbers.

---

## 4. State and queue model (Maildir-inspired)

Atomic, rename-based transitions on the filesystem:

```
fetched/      raw artifact + fetch record (entry point)
triaged/      classification verdict attached
converting/   in-flight, claimed by a worker (Docling running)
converted/    DoclingDocument + table cell-graphs produced
review/       numeric/structuring discrepancy — awaits human curation
done/         normalized record ready for chunker
failed/       unrecoverable; reason recorded
```

Rename = commit (POSIX-atomic within one filesystem); a crash leaves a document in a recoverable in-flight state. Worker idempotency keyed on content hash → safe re-runs.

---

## 5. DVC stage layout

| Stage | Deps | Outs | Determinism |
|---|---|---|---|
| `triage` | raw artifacts | classification table | deterministic |
| `convert` | triaged docs; Docling + backend + Heron + TableFormer versions | `DoclingDocument` + cell-graphs | deterministic (versions pinned; Mistral model id recorded if escalated) |
| `structure_vlm` *(optional)* | convert outs | candidate structured fields | **non-deterministic** (Granite-Docling / local Qwen; digest + params, temp=0) |
| `normalize` | convert (+ structure_vlm) | canonical MD + table JSON | deterministic |
| `validate` | normalize + convert | validated record + flags | deterministic |

Pin: Docling release, OCR-backend version, Heron layout model, TableFormer V2, Mistral OCR model id (`mistral-ocr-2512`), local VLM digest. `structure_vlm` is the only non-reproducible link and is fenced as optional.

---

## 6. Backend selection, escalation, and validation policy

- **OCR backend selection** is an upfront benchmark (EasyOCR vs Tesseract vs RapidOCR on a labeled VN/FR/EN sample; Surya as external reference). Winner becomes the pinned default.
- **Escalation:** default backend → Mistral OCR triggers on per-page confidence below threshold *or* failed TableFormer parse. Logged with reason; never silent. ABBYY considered only if a measured table-accuracy gap persists.
- **VLM outputs are never authoritative.** Structured fields are accepted only when they reconcile with the deterministic layer. Numeric mismatch, unit ambiguity, or low OCR confidence on the underlying cell → `review/`.
- **Human-in-the-loop** is the terminal arbiter for flagged figures, not a model judge.

---

## 7. Output record schema (handed to chunker)

Derived from `DoclingDocument`; AEDIST adds provenance, language, validation, and DVC linkage.

```jsonc
{
  "doc_id": "sha256:…",                 // content-addressed
  "source": { "uri": "...", "fetched_at": "...", "upstream_id": "Quyết định 768/QĐ-TTg" },
  "language": "vi",                      // doc-level; blocks may override
  "conversion": {
    "spine": "docling/standard",
    "ocr_backend": "easyocr | tesseract | rapidocr | mistral_ocr",
    "layout_model": "heron",
    "table_model": "tableformer_v2",
    "docling_version": "...",
    "page_count": 42
  },
  "blocks": [
    {
      "type": "paragraph | heading | table | figure | caption",
      "text_md": "...",                  // from DoclingDocument export
      "lang": "vi",
      "provenance": { "page": 7, "bbox": [x0,y0,x1,y1] },
      "confidence": 0.97,
      "table": { "cellgraph_path": "…json", "csv_path": "…csv", "validated": true }  // tables only
    }
  ],
  "flags": ["numeric_review:p12_t1"],    // empty when clean
  "dvc_rev": "…"
}
```

The chunker must preserve `provenance`, `lang`, and the table `cellgraph_path`/`csv_path` through to storage, so retrieval can cite page-level sources and read figures from the machine-readable cell-graph rather than re-parsing rendered Markdown.

---

## 8. Open decisions

1. **Chunk-boundary signal:** emit typed Docling blocks and let the chunker decide boundaries (keeps layers decoupled), vs. pre-mark semantic boundaries here. *Leaning:* typed blocks only — `DoclingDocument` structure already carries enough for a structure-aware chunker (and Docling's LangChain/LlamaIndex hooks expect this).
2. **VLM placement:** run `structure_vlm` in-ingestion for tables only (numeric validation while bboxes/cell-graphs are in hand) vs. defer to retrieval time. *Leaning:* in-ingestion, tables only.
3. **Table representation to storage:** TableFormer cell-graph JSON (faithful: spans, hierarchical headers) vs. flattened CSV (simple, lossy). *Leaning:* keep both — JSON authoritative, CSV convenience. Confirm against how the energy schema ingests capacities.
4. **OCR-backend default:** pending the §6 benchmark on the VN/FR/EN sample. Decide whether a Surya quality gap (if any) justifies a custom non-native integration vs. staying within Docling's supported backends.
5. **Review backlog SLA:** acceptable `review/` volume before it blocks downstream, and whether `done/` may ship with unresolved low-severity flags.
