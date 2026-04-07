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

### MinerU v3.0.8 (localhost:8010, opendatalab official image, GPU)
- **Container**: `podman run --device nvidia.com/gpu=all` (not `--gpus all` — CDI syntax required for podman)
- **Pipeline backend** (`parse_method=auto`, `lang_list=latin`):
  - **Output**: 556 lines, 791 KB, **62 HTML tables**, 2994 rows
  - **Body text**: Vietnamese diacritics fully preserved
  - **Table cells**: Diacritics stripped ("Quảng Ninh" → "Qung Ninh", "Dự án" → "D án")
  - **Speed**: 5m45s for 173 pages
- **Hybrid-auto-engine** (VLM + pipeline, `MinerU2.5-2509-1.2B` Qwen2-VL):
  - Works on small files (30 tables from PDP8 in 1m35s)
  - OOM on 173-page Decision 1509 (pipeline model ~8.6GB + vLLM needs 50% GPU = exceeds 16GB A4000)
  - Chinese characters leak into Vietnamese tables (VLM is CN/EN trained)
- **`parse_method=txt`**: Identical output to `auto` — MinerU detects text layer automatically
- **Cost**: $0 (local, GPU)
- **Verdict**: 62 tables (vs Marker's 170), good body text, but table cells lose diacritics

## Benchmark Summary (2026-04-07, updated)

| Backend | Tables | Rows | Size KB | Speed | Diacritics |
|---------|--------|------|---------|-------|------------|
| Marker (local, GPU) | 170 | 4038 | 1630 | 45s | full |
| Mistral OCR (direct) | 169 | 3011 | 547 | 30s | full |
| MinerU v3 (pipeline) | 62 | 2994 | 791 | 5m45s | body only |
| GROBID (local) | 45 | 0 | 388 | 20s | full |
| Mistral OCR (plugin) | 15 | 0 | 67 | ~10 min | full |
| Cloudflare AI | 14 | 0 | 57 | ~8 min | full |

Note: "Tables" counts all detected tables (markdown `|---|` for Marker, HTML `<table>` for others).
"Diacritics": full = Vietnamese diacritics preserved everywhere; body only = body text OK but table cells stripped.

## Conclusion

**Marker and Mistral OCR (direct) are the top two converters**:
- Marker: 170 markdown tables, 4038 rows, 1.6 MB — local, free, GPU-accelerated, full diacritics
- Mistral OCR (direct): 169 HTML tables, 3011 rows, 548 KB — cloud API, $0.35, richer structure (rowspan/colspan)
- MinerU v3.0.8: 62 tables, 2994 rows — free, GPU-accelerated, but table cells lose Vietnamese diacritics. Hybrid-auto-engine (VLM) crashes on large documents due to GPU memory competition
- GROBID: good body text (full diacritics) but flattens table structure
- LLM-bottlenecked approaches (Mistral OCR plugin, Cloudflare AI): limited to 14-15 tables by output window

Recommended pipeline: **Marker (local, free) or Mistral OCR direct (cloud, $0.35)** for table-heavy scanned Vietnamese PDFs. Both deliver ~170 tables from 173 pages with preserved diacritics. Choose based on whether local GPU or cloud API is preferred.
