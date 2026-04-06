# Web Portal Access Test: Vietnamese Government Sources

**Date**: 2026-04-06
**Tool**: Tavily Search API
**Prerequisite**: TAVILY_API_KEY deployed (#95)

## Results

### 1. thuvienphapluat.vn (Legal text portal)
- **Search**: Finds Decision 1509/QĐ-BCT correctly
- **Content**: 10,469 chars raw content retrieved
- **MW data**: Yes — content mentions power capacity figures
- **Verdict**: ✅ Accessible, content extractable

### 2. evn.com.vn (EVN corporate site)
- **Search**: Finds Annual Report 2024-2025 page
- **Content**: 6,531 chars but mostly navigation/download links
- **MW data**: No — the actual report is a PDF download, not inline text
- **Verdict**: ⚠️ Search finds the page, but data is in PDF (needs download + RAG)

### 3. moit.gov.vn (Ministry of Industry and Trade)
- **Search**: Finds PDP8 review meeting article
- **Content**: 8,118 chars of news article text
- **MW data**: No — articles describe policy, don't contain data tables
- **Verdict**: ⚠️ News/policy articles accessible, but tabular data is in PDF annexes

## Summary

| Source | Searchable | Content extractable | Table data inline |
|--------|-----------|--------------------|--------------------|
| thuvienphapluat.vn | ✅ | ✅ (10K chars) | Partial (MW mentioned) |
| evn.com.vn | ✅ | ⚠️ (links only) | No (PDF download) |
| moit.gov.vn | ✅ | ✅ (articles) | No (data in PDF annexes) |

## Conclusion

**Web search finds Vietnamese government sources but cannot extract tabular data directly.** The actual data tables (power plant lists, capacity figures) are in PDF annexes, not in HTML pages.

Pipeline implication: Web-augmented queries give context (policy decisions, dates, summaries) but not the structured data needed for the benchmark. The **RAG pipeline with PDF conversion** (GROBID/Marker) remains essential for table extraction.

This explains why sweep2-web scored lower than sweep2-rag: web search adds policy context but not the specific plant-level data the task requires.
