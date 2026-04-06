"""Tests for aedist.compare_converters — PDF converter benchmarking."""

from pathlib import Path

from aedist.compare_converters import (
    analyze_backend,
    count_html_tables,
    count_table_rows,
    count_tables,
    format_latex,
    format_summary,
    vietnamese_sample_check,
)

SAMPLE_MD = """\
# Title

Some text.

| Name | Capacity | Province |
|------|----------|----------|
| Phả Lại | 600 MW | Hải Dương |
| Vĩnh Tân | 1200 MW | Bình Thuận |

More text about nhà máy điện lực.

| Fuel | công suất |
|------|-----------|
| Coal | 31055 MW |
"""

SAMPLE_HTML = """\
<table>
<tr><th>Name</th></tr>
<tr><td>Quyết định test</td></tr>
</table>
<table>
<tr><td>tỉnh something</td></tr>
</table>
"""


def test_count_tables():
    assert count_tables(SAMPLE_MD) == 2


def test_count_table_rows():
    # 2 header + 2 separator + 3 data = 7 pipe lines per table style
    rows = count_table_rows(SAMPLE_MD)
    assert rows >= 6  # headers + data rows


def test_count_tables_empty():
    assert count_tables("No tables here.\nJust text.") == 0


def test_count_html_tables():
    assert count_html_tables(SAMPLE_HTML) == 2


def test_count_html_tables_none():
    assert count_html_tables(SAMPLE_MD) == 0


def test_vietnamese_check_all_present():
    text = "Quyết định về điện lực, công suất nhà máy tỉnh Hà Nội"
    result = vietnamese_sample_check(text)
    assert all(result.values())


def test_vietnamese_check_partial():
    text = "Some English text with điện mentioned"
    result = vietnamese_sample_check(text)
    assert result["điện lực"]
    assert not result["công suất"]


def test_analyze_backend(tmp_path):
    md_file = tmp_path / "test.md"
    md_file.write_text(SAMPLE_MD, encoding="utf-8")
    result = analyze_backend(md_file)
    assert result["md_tables"] == 2
    assert result["md_table_rows"] >= 6
    assert result["lines"] > 0
    assert result["size_kb"] > 0


def test_format_summary():
    results = {
        "grobid": {
            "lines": 100,
            "md_tables": 0,
            "md_table_rows": 0,
            "html_tables": 5,
            "vietnamese_score": 4,
            "vietnamese_max": 5,
            "size_kb": 50,
        },
        "marker": {
            "lines": 200,
            "md_tables": 10,
            "md_table_rows": 100,
            "html_tables": 0,
            "vietnamese_score": 5,
            "vietnamese_max": 5,
            "size_kb": 150,
        },
    }
    text = format_summary(results, "test-doc")
    assert "grobid" in text
    assert "marker" in text
    assert "test-doc" in text


def test_format_latex():
    results = {
        "marker": {
            "lines": 200,
            "md_tables": 10,
            "md_table_rows": 100,
            "html_tables": 0,
            "vietnamese_score": 5,
            "vietnamese_max": 5,
            "size_kb": 150,
        },
    }
    tex = format_latex(results, "test-doc")
    assert r"\begin{tabular}" in tex
    assert "marker" in tex
    assert r"\bottomrule" in tex


def test_format_latex_merges_md_and_html_tables():
    """LaTeX table column merges markdown + HTML table counts (PR #167 review)."""
    results = {
        "mistral-ocr": {
            "lines": 100,
            "md_tables": 0,
            "md_table_rows": 0,
            "html_tables": 15,
            "vietnamese_score": 5,
            "vietnamese_max": 5,
            "size_kb": 67,
        },
    }
    tex = format_latex(results, "test-doc")
    # Should show 15 (0 md + 15 html), not 0
    assert "& 15 &" in tex


def test_module_has_argparse():
    source = Path("src/aedist/compare_converters.py").read_text()
    assert "ArgumentParser" in source
