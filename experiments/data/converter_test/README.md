# PDF Converter Test: Decision 1509/QĐ-BCT

**Date**: 2026-04-05
**Document**: Decision 1509/QĐ-BCT (Revised PDP8 Implementation Plan, 30 May 2025)
**Source**: thuvienphapluat.vn → Zotero (UGF63EJ4)
**Pages**: 173 (scanned Vietnamese, complex table layouts)

## Results

### GROBID (localhost:8070)
- **Output**: 4960 lines of markdown
- **Text extraction**: Good — Vietnamese diacritics preserved
- **Table extraction**: Poor — tables collapsed into flat text, no row/column structure
- **Verdict**: Usable for body text, not for table extraction

### Gemma 4 26B (Ollama vision)
- **Test**: Single page (page 15, LNG thermal power table)
- **Table recognition**: Good — correctly identifies columns (TT, Dự án, Công suất, Năm vận hành, Ghi chú)
- **Vietnamese OCR**: Good — reads diacritics and numbers accurately
- **Issue**: Output lands in `thinking` field, not `content` (reasoning model behavior)
- **Speed**: ~60s per page (173 pages ≈ 3 hours)
- **Verdict**: Best table quality, but slow and needs thinking-field extraction

### Not tested (need container setup)
- Marker (#83)
- MinerU (#84)

## Conclusion

For Decision 1509 annexes (thermal power plant tables):
- GROBID alone is insufficient — tables lose structure
- Vision model (Gemma 4) produces usable tables but needs:
  1. Thinking-field content extraction (not just `content`)
  2. Page-range selection for efficiency (only annex pages, not all 173)
- Hybrid approach recommended: GROBID for text + vision for table pages
