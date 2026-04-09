"""Tests for aedist.compare_converters — PDF converter benchmarking."""

from pathlib import Path

from aedist.compare_converters import (
    analyze_backend,
    count_html_table_rows,
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

SAMPLE_HTML_INLINE = (
    '<table><tr><td>A</td></tr><tr><td>B</td></tr>'
    '<tr><td>C</td></tr></table>'
)


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


def test_count_html_table_rows():
    assert count_html_table_rows(SAMPLE_HTML) == 3


def test_count_html_table_rows_inline():
    """Inline HTML (MinerU-style) where multiple <tr> tags share one line."""
    assert count_html_table_rows(SAMPLE_HTML_INLINE) == 3


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
    assert result["total_tables"] == 2
    assert result["total_rows"] >= 6
    assert result["html_tables"] == 0
    assert result["html_table_rows"] == 0
    assert result["lines"] > 0
    assert result["size_kb"] > 0


def test_analyze_backend_html(tmp_path):
    md_file = tmp_path / "test.md"
    md_file.write_text(SAMPLE_HTML, encoding="utf-8")
    result = analyze_backend(md_file)
    assert result["html_tables"] == 2
    assert result["html_table_rows"] == 3
    assert result["total_tables"] == 2
    assert result["total_rows"] == 3


def test_format_summary():
    results = {
        "grobid": {
            "total_tables": 5,
            "total_rows": 0,
            "vietnamese_score": 4,
            "vietnamese_max": 5,
            "size_kb": 50,
        },
        "marker": {
            "total_tables": 10,
            "total_rows": 100,
            "vietnamese_score": 5,
            "vietnamese_max": 5,
            "size_kb": 150,
        },
    }
    text = format_summary(results, "test-doc")
    assert "grobid" in text
    assert "marker" in text
    assert "test-doc" in text


def _data_rows(tex):
    """Extract data rows (between midrule and bottomrule) from a tabular."""
    rows = []
    in_data = False
    for line in tex.splitlines():
        stripped = line.strip()
        if r"\midrule" in stripped:
            in_data = True
            continue
        if r"\bottomrule" in stripped:
            break
        if in_data and "&" in stripped:
            cells = [c.strip().rstrip("\\").strip() for c in stripped.split("&")]
            rows.append(cells)
    return rows


def test_format_latex_without_meta():
    results = {
        "marker": {
            "total_tables": 170,
            "total_rows": 4038,
            "vietnamese_score": 5,
            "vietnamese_max": 5,
            "size_kb": 1630,
        },
    }
    tex = format_latex(results)
    rows = _data_rows(tex)
    assert len(rows) == 1
    # Columns: Backend, Tableaux, Lignes, Taille, Temps, Diacritiques
    assert rows[0][0] == "marker"
    assert rows[0][1] == "170"
    assert "4" in rows[0][2] and "038" in rows[0][2]  # 4\,038
    assert rows[0][4] == "--"  # no timing without meta
    assert rows[0][5] == "5/5"


def test_format_latex_with_meta():
    results = {
        "marker": {
            "total_tables": 170,
            "total_rows": 4038,
            "vietnamese_score": 5,
            "vietnamese_max": 5,
            "size_kb": 1630,
        },
    }
    meta = {
        "marker": {
            "display_name": "Marker (local, GPU)",
            "timing_s": 45,
            "diacritics": "complets",
        },
    }
    tex = format_latex(results, meta)
    rows = _data_rows(tex)
    assert len(rows) == 1
    assert rows[0][0] == "Marker (local, GPU)"
    assert rows[0][1] == "170"
    assert rows[0][4] == "45"
    assert rows[0][5] == "complets"


def test_format_latex_rows_na():
    """Backends with rows_na=true show '--' instead of row count."""
    results = {
        "grobid": {
            "total_tables": 45,
            "total_rows": 0,
            "vietnamese_score": 5,
            "vietnamese_max": 5,
            "size_kb": 388,
        },
    }
    meta = {
        "grobid": {
            "display_name": "GROBID (local)",
            "timing_s": 20,
            "diacritics": "complets",
            "rows_na": True,
        },
    }
    tex = format_latex(results, meta)
    rows = _data_rows(tex)
    assert len(rows) == 1
    assert rows[0][0] == "GROBID (local)"
    assert rows[0][1] == "45"
    assert rows[0][2] == "--"  # rows_na suppresses row count
    assert rows[0][4] == "20"


def test_format_latex_thousands_separator():
    """Large numbers get LaTeX thin-space separators."""
    results = {
        "marker": {
            "total_tables": 170,
            "total_rows": 4038,
            "vietnamese_score": 5,
            "vietnamese_max": 5,
            "size_kb": 1630,
        },
    }
    tex = format_latex(results)
    assert r"4\,038" in tex
    assert r"1\,630" in tex


def test_module_has_argparse():
    source = Path("src/aedist/compare_converters.py").read_text()
    assert "ArgumentParser" in source
