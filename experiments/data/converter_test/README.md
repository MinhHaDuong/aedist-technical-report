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

### Mistral OCR direct (/v1/ocr API, $2/1000 pages, no LLM)
- **Output**: 1307 lines, 548 KB, **169 HTML tables**
- **Text extraction**: Good — Vietnamese diacritics preserved
- **Table extraction**: Excellent — proper HTML tables with `rowspan`, `colspan`, `<th>`, matching Marker's 170 tables
- **Key advantage**: Direct OCR endpoint, no LLM bottleneck — returns ALL pages and ALL tables
- **Speed**: ~30 seconds for 173 pages (pure OCR, no generation)
- **Cost**: ~$0.35 (173 pages at $2/1000)
- **Verdict**: Matches Marker on table count with richer HTML structure (rowspan/colspan)

### MinerU v3.0.8 (localhost:8010, pipeline backend, lang=latin, GPU)
- **Output**: 564 lines, 812 KB, **62 HTML tables**
- **Text extraction**: Moderate — body text extracted but diacritics inconsistent (~60% correct)
- **Table extraction**: Partial — 62 HTML tables with rowspan/colspan (vs Marker's 170)
- **Vietnamese OCR**: Mixed — "Dự án" sometimes correct, sometimes "D án" or "Đ án"
- **Speed**: ~20s for 173 pages (8.3 pages/s) — fastest converter tested
- **Cost**: $0 (local, GPU)
- **Verdict**: Very fast, free, but misses 64% of tables and has unreliable diacritics

## Benchmark Summary (2026-04-06)

```
Backend              Lines  Tables  Rows  HTML  Viet  Size KB
--------------------------------------------------------------
Backend              Lines  Tables  Rows  HTML  Viet  Size KB  Speed
--------------------------------------------------------------  --------
cloudflare-ai         1609       0     0    14 5/  5      57   ~8 min
grobid                4961       0     0    45 5/  5     388   fast
marker                4745     170  4038     0 5/  5    1630   ~min
mineru v3 (pipeline)   564       0     0    62 3/  5     812   ~20s
mistral-ocr (plugin)  1954       0     0    15 5/  5      67   ~10 min
mistral-ocr (direct)  1307       0     0   169 5/  5     547   ~30s
```

Note: "Tables" counts markdown `|---|` tables, "HTML" counts `<table>` blocks.
Marker uses markdown tables; other backends use HTML tables.
MinerU Viet 3/5: diacritics present but inconsistent (~60% correct).

## Conclusion

**Marker and Mistral OCR (direct) are the top two converters**:
- Marker: 170 markdown tables, 1.6 MB — local, free, GPU-accelerated
- Mistral OCR (direct): 169 HTML tables, 548 KB — cloud API, $0.35, richer structure (rowspan/colspan)
- The OpenRouter file-parser plugin approach (mistral-ocr via LLM) only captured 15 tables — the LLM output window is the bottleneck, not OCR quality
- MinerU v3.x: fastest (20s) and free, but only 62/170 tables and inconsistent diacritics
- GROBID extracts the most raw text (4961 lines) but flattens table structure

Recommended pipeline: **Marker (local, free) or Mistral OCR direct (cloud, $0.35)** for table-heavy scanned PDFs. Both deliver ~170 tables from 173 pages. Choose based on whether local GPU or cloud API is preferred.
