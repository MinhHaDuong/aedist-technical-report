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

### MinerU (localhost:8010, jianjungki/mineru-api:gpu, GPU)
- **Output**: 695 lines, 50K chars, **0 markdown tables**
- **Text extraction**: Good — Vietnamese diacritics preserved, document structure detected
- **Table extraction**: Poor — tables not converted to markdown format
- **Speed**: Fast (single API call)
- **Verdict**: Good for text, fails on tables for this document type

## Conclusion

**Marker is the clear winner** for this document type:

| Backend | Tables | Table rows | Lines | Size |
|---------|--------|-----------|-------|------|
| **Marker** | **170** | **4038** | 4745 | 1.6 MB |
| GROBID | 0 | 0 | 4961 | 388 KB |
| MinerU | 0 | 0 | 695 | 58 KB |
| Gemma 4 vision | good/page | — | — | ~60s/page |

- Marker is the only converter that preserves table structure at scale
- Full document in one call vs page-by-page (vision)
- Minor OCR errors on Vietnamese diacritics (fixable in post-processing)

Recommended pipeline: **Marker for table-heavy scanned PDFs**, GROBID as fallback for text-only documents.
