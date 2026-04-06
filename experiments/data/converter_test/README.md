# PDF Converter Test: Decision 1509/QĐ-BCT

**Date**: 2026-04-06
**Document**: Decision 1509/QĐ-BCT (Revised PDP8 Implementation Plan, 30 May 2025)
**Source**: thuvienphapluat.vn → Zotero (UGF63EJ4)
**Pages**: 173 (scanned Vietnamese, complex table layouts)

## Results

### GROBID (localhost:8070)
- **Output**: 4960 lines of markdown
- **Text extraction**: Good — Vietnamese diacritics preserved
- **Table extraction**: Poor — tables collapsed into flat text, no row/column structure
- **Verdict**: Usable for body text, not for table extraction

### Marker (localhost:8001, savatar101/marker-api:0.3, GPU)
- **Output**: 4745 lines, 1.6 MB, **170 markdown tables**
- **Text extraction**: Good — Vietnamese text with some OCR errors (diacritics: "Quyét Đinh" → "Quyết Định")
- **Table extraction**: Excellent — proper markdown table format with `|` columns and `---` separators
- **Speed**: Full 173-page document processed in one API call
- **Verdict**: Best overall for table-heavy Vietnamese documents

### Gemma 4 26B (Ollama vision)
- **Test**: Single page (page 15, LNG thermal power table)
- **Table recognition**: Good — correctly identifies columns (TT, Dự án, Công suất, Năm vận hành, Ghi chú)
- **Vietnamese OCR**: Good — reads diacritics and numbers accurately
- **Issue**: Output lands in `thinking` field, not `content` (reasoning model behavior)
- **Speed**: ~60s per page (173 pages ≈ 3 hours)
- **Verdict**: Good table quality, but too slow for full documents

### OpenRouter / Mistral OCR ($2/1000 pages via file-parser plugin)
- **Output**: 1954 lines, 67 KB, **15 HTML tables**
- **Text extraction**: Good — Vietnamese diacritics preserved
- **Table extraction**: Moderate — proper HTML table structure with `<th>`/`<td>`, but only 15 tables (vs Marker's 170)
- **Limitation**: Output capped by LLM token limit (65K) — the parsed document is too large for the model to reproduce fully
- **Speed**: ~10 minutes for 173 pages (OCR + LLM generation)
- **Cost**: ~$0.35 (OCR) + LLM tokens
- **Verdict**: Good table quality per table, but incomplete coverage due to output length constraints

### OpenRouter / Cloudflare AI (free, text-only via file-parser plugin)
- **Output**: 1609 lines, 57 KB, **14 HTML tables**
- **Text extraction**: Moderate — extracted text despite being a scanned document (likely has a hidden text layer)
- **Table extraction**: Similar to Mistral OCR (14 vs 15 HTML tables)
- **Speed**: ~8 minutes for 173 pages
- **Cost**: Free (Cloudflare) + LLM tokens
- **Verdict**: Surprisingly comparable to Mistral OCR on this document; same output length constraint

### MinerU (not tested — container image not yet pulled)

## Benchmark Summary (2026-04-06)

```
Backend       Lines  Tables   Rows  HTML  Viet  Size KB
------------------------------------------------------------
cloudflare-ai   1609       0      0    14 5/  5      57
grobid         4961       0      0    45 5/  5     388
marker         4745     170   4038     0 5/  5    1630
mistral-ocr    1954       0      0    15 5/  5      67
```

Note: "Tables" counts markdown `|---|` tables, "HTML" counts `<table>` blocks.
Marker uses markdown tables; GROBID and OpenRouter backends use HTML tables.

## Conclusion

**Marker remains the clear winner** for this document type:
- 170 extracted tables vs 14-15 (OpenRouter) vs 45 (GROBID) — best table coverage by far
- Full document in one call, complete output (1.6 MB vs 57-67 KB)
- The OpenRouter backends are limited by the LLM output window — even with Mistral OCR's good per-table quality, only ~8% of the document's tables are captured
- GROBID extracts the most raw text (4961 lines) but flattens table structure

Recommended pipeline: **Marker for table-heavy scanned PDFs**. OpenRouter/Mistral OCR could be useful for small documents where per-table quality matters and the output fits in one LLM call.
