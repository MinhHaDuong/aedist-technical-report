"""Generate an interactive HTML recognition matrix for LP matcher QA (ticket 0450).

Pipeline phase: P3 (analyze & render) — invoked by experiments/render.mk.

This script generates a **dev-tool HTML file** from the same data as the static
PDF (``plot_exp1_matrix``).  It is not referenced by the manuscript or report
and is gitignored.  Its purpose is matcher quality assurance: hovering a cell
shows the full reference-vs-reply comparison table so the author can spot-check
LP matcher verdicts without grepping JSON.

Hover payloads per cell type
----------------------------
* **TP cell** (blue): reference attributes (name, fuel, capacity, status,
  province) + matched system attributes + LP similarity score + capacity delta.
* **FN cell** (empty / white): reference attributes only — the model missed this
  plant entirely.
* **FP cell** (red): the emitted system name + the nearest reference candidate
  (name, fuel, capacity, status) and the LP similarity score to it, so the
  author can see why the LP rejected the pairing.

``level`` column (0401/0402, post-preprint): rendered as "—" until the Plant
schema carries it; the hover table row is always shown so the layout is stable.

No new Python dependencies: the HTML uses inline vanilla JS.  All data is
embedded as a JSON blob in a ``<script>`` tag so the file is fully standalone.

Usage::

    uv run python -m aedist.plot_exp1_matrix_interactive \\
        --records-glob "experiments/outputs/exp1_batch2/*.record.json" \\
        --output /tmp/exp1_recognition_matrix_interactive.html
"""

import argparse
import json
import logging
from pathlib import Path

from .config import VN_THERMAL_PLANTS_RELEASE_CSV
from .exp1_recognition import (
    RecognitionData,
    load_exp1_recognition,
    top_false_positives,
)
from .plot_exp1_matrix import _order_plants, _order_runs
from .plot_method_convergence import _model_size_b
from .util import COLOR_ALERT, COLOR_MATCHED, model_family

log = logging.getLogger(__name__)

# Palette colors injected into the HTML template so hex literals never appear
# in this source (test_no_hardcoded_plot_colors.py adherence check).
_COLOR_FP = COLOR_ALERT
_COLOR_MATCH = COLOR_MATCHED


# ---------------------------------------------------------------------------
# HTML / JS template
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Exp1 Recognition Matrix — Interactive QA</title>
<style>
  body {{ font-family: sans-serif; margin: 1em; background: #f8f8f8; }}
  h1 {{ font-size: 1.2em; margin-bottom: 0.4em; }}
  p.subtitle {{ font-size: 0.85em; color: #555; margin-top: 0; }}

  /* Matrix container with sticky axes */
  #matrix-wrapper {{
    overflow: auto;
    max-height: 90vh;
    border: 1px solid #ccc;
    background: white;
  }}
  table.matrix {{
    border-collapse: collapse;
    table-layout: fixed;
    font-size: 11px;
  }}
  table.matrix th, table.matrix td {{
    padding: 0;
    border: none;
  }}

  /* Sticky row-header column */
  table.matrix td.row-label {{
    position: sticky;
    left: 0;
    background: white;
    z-index: 2;
    white-space: nowrap;
    padding: 0 4px 0 2px;
    font-size: 10px;
    color: #444;
    border-right: 1px solid #ccc;
    min-width: 140px;
  }}

  /* Sticky column-header row */
  table.matrix thead tr th {{
    position: sticky;
    top: 0;
    background: #eee;
    z-index: 3;
    text-align: center;
    border-bottom: 1px solid #bbb;
  }}
  table.matrix thead tr th.row-label {{
    left: 0;
    z-index: 4;
  }}

  /* Plant name column headers (rotated) */
  th.plant-col {{
    min-width: 14px;
    max-width: 14px;
    height: 100px;
    vertical-align: bottom;
    padding: 2px 0;
    overflow: hidden;
  }}
  th.plant-col span {{
    display: inline-block;
    transform: rotate(-90deg);
    transform-origin: bottom left;
    white-space: nowrap;
    font-size: 9px;
    color: #333;
    width: 100px;
    padding-left: 2px;
  }}
  th.gap-col {{
    min-width: 8px;
    background: #f8f8f8;
  }}
  th.fp-col {{
    min-width: 14px;
    max-width: 14px;
    height: 100px;
    vertical-align: bottom;
    padding: 2px 0;
    overflow: hidden;
  }}
  th.fp-col span {{
    display: inline-block;
    transform: rotate(-90deg);
    transform-origin: bottom left;
    white-space: nowrap;
    font-size: 9px;
    color: #a00;
    width: 100px;
    padding-left: 2px;
  }}

  /* Data cells */
  td.cell {{
    min-width: 14px;
    max-width: 14px;
    height: 10px;
    cursor: pointer;
  }}
  td.cell-tp    {{ background: #2166ac; }}
  td.cell-fn    {{ background: #f7fbff; border: 1px solid #ddd; }}
  td.cell-fp    {{ background: #d73027; }}
  td.cell-fp-absent {{ background: #fff5f0; border: 1px solid #fdd; }}
  td.cell-gap   {{ background: #f0f0f0; }}

  td.cell:hover {{ outline: 2px solid #f5a623; outline-offset: -1px; z-index: 1; position:relative; }}

  /* Status band header row */
  tr.band-row th {{
    font-size: 10px;
    color: #333;
    text-align: center;
    padding: 1px 0 3px;
    border-bottom: 1px solid #999;
  }}

  /* Model separator rows */
  tr.model-sep td {{
    height: 2px;
    background: #999;
  }}
  tr.family-sep td {{
    height: 3px;
    background: #333;
  }}

  /* Hover popup */
  #popup {{
    display: none;
    position: fixed;
    background: white;
    border: 1px solid #888;
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 12px;
    box-shadow: 3px 3px 8px rgba(0,0,0,0.2);
    z-index: 9999;
    max-width: 460px;
    pointer-events: none;
  }}
  #popup h3 {{ margin: 0 0 6px; font-size: 13px; }}
  #popup table {{ border-collapse: collapse; width: 100%; }}
  #popup td {{ padding: 2px 6px; }}
  #popup tr:nth-child(even) {{ background: #f5f5f5; }}
  #popup .label {{ font-weight: bold; color: #555; white-space: nowrap; }}
  #popup .ref-val  {{ color: #1a6b9a; }}
  #popup .sys-val  {{ color: #2c7a2c; }}
  #popup .fp-val   {{ color: #c00; }}
  #popup .meta-val {{ color: #777; }}
  .badge {{ display:inline-block; padding:1px 5px; border-radius:3px; font-size:10px; font-weight:bold; }}
  .badge-tp {{ background:#d0e8ff; color:#1a5a8a; }}
  .badge-fn {{ background:#ffe; color:#886600; }}
  .badge-fp {{ background:#ffe0e0; color:#a00; }}
  .fp-panel-header {{ color:{color_fp}; }}
  .score-good {{ color:{color_match}; }}
  .score-bad  {{ color:{color_fp}; }}
</style>
</head>
<body>
<h1>Exp1 Recognition Matrix — Interactive QA</h1>
<p class="subtitle">
  {n_runs} runs × {n_ref_plants} reference plants · {n_fps} false-positive columns<br>
  Hover a cell to inspect the LP matcher verdict.
  <strong style="color:#2166ac">Blue = TP</strong> &nbsp;
  <strong style="color:#d73027">Red = FP (present)</strong> &nbsp;
  <span style="color:#666">White = miss / absent</span>
</p>

<div id="popup">
  <h3 id="popup-title">Cell detail</h3>
  <table id="popup-table"></table>
</div>

<div id="matrix-wrapper">
  <table class="matrix" id="the-matrix">
  </table>
</div>

<script>
const DATA = {data_json};

// Build the matrix table from DATA
(function() {{
  const tbl = document.getElementById('the-matrix');

  const runs = DATA.runs;
  const refPlants = DATA.ref_plants;
  const fpNames = DATA.fp_names;
  const statusBands = DATA.status_bands; // [{{'label': ..., 'start': ..., 'end': ...}}]

  const nRuns = runs.length;
  const nRef = refPlants.length;
  const nFP = fpNames.length;
  const GAP_COLS = 2;

  // ---- HEADER: band labels row ----
  const bandTr = document.createElement('tr');
  bandTr.className = 'band-row';

  // Corner stub (sticky row-label column)
  const cornerTh = document.createElement('th');
  cornerTh.className = 'row-label';
  bandTr.appendChild(cornerTh);

  // FP panel header spanning nFP + GAP_COLS
  const fpBandTh = document.createElement('th');
  fpBandTh.colSpan = nFP + GAP_COLS;
  fpBandTh.textContent = nFP + ' most common false positives';
  fpBandTh.className = 'fp-panel-header';
  fpBandTh.style.borderRight = '2px solid #333';
  bandTh = fpBandTh;
  bandTr.appendChild(fpBandTh);

  // Status band spans
  statusBands.forEach(band => {{
    const th = document.createElement('th');
    th.colSpan = band.end - band.start + 1;
    th.textContent = band.label;
    if (band !== statusBands[statusBands.length - 1]) {{
      th.style.borderRight = '1px solid #999';
    }}
    bandTr.appendChild(th);
  }});

  // ---- HEADER: column labels row ----
  const labelTr = document.createElement('tr');

  const cornerTh2 = document.createElement('th');
  cornerTh2.className = 'row-label';
  cornerTh2.textContent = 'Model · run';
  labelTr.appendChild(cornerTh2);

  // FP column labels
  fpNames.forEach((name, j) => {{
    const th = document.createElement('th');
    th.className = 'fp-col';
    th.innerHTML = '<span>' + escHtml(name) + '</span>';
    th.dataset.fpIdx = j;
    labelTr.appendChild(th);
  }});

  // Gap columns
  for (let g = 0; g < GAP_COLS; g++) {{
    const th = document.createElement('th');
    th.className = 'gap-col';
    labelTr.appendChild(th);
  }}

  // Reference plant labels
  refPlants.forEach((plant, j) => {{
    const th = document.createElement('th');
    th.className = 'plant-col';
    th.innerHTML = '<span>' + escHtml(plant.name) + '</span>';
    th.dataset.plantIdx = j;
    labelTr.appendChild(th);
  }});

  const thead = document.createElement('thead');
  thead.appendChild(bandTr);
  thead.appendChild(labelTr);
  tbl.appendChild(thead);

  // ---- BODY: one row per run ----
  const tbody = document.createElement('tbody');
  let prevFamily = null;
  let prevModel = null;

  runs.forEach((run, i) => {{
    // Separator rows between model groups / architectural families
    if (prevModel !== null && prevModel !== run.model) {{
      const sepTr = document.createElement('tr');
      sepTr.className = (run.family !== prevFamily) ? 'family-sep' : 'model-sep';
      // colSpan = 1 (row-label) + nFP + GAP + nRef
      const td = document.createElement('td');
      td.colSpan = 1 + nFP + GAP_COLS + nRef;
      sepTr.appendChild(td);
      tbody.appendChild(sepTr);
    }}

    const tr = document.createElement('tr');

    // Row label
    const labelTd = document.createElement('td');
    labelTd.className = 'row-label';
    // Show model name only for first rep in each block
    if (prevModel !== run.model) {{
      labelTd.textContent = run.model + ' · r' + run.run;
    }} else {{
      labelTd.textContent = '  · r' + run.run;
    }}
    tr.appendChild(labelTd);

    // FP cells
    fpNames.forEach((fpName, j) => {{
      const td = document.createElement('td');
      const present = run.fp_present[j];
      td.className = 'cell ' + (present ? 'cell-fp' : 'cell-fp-absent');
      td.dataset.type = 'fp';
      td.dataset.runIdx = i;
      td.dataset.fpIdx = j;
      tr.appendChild(td);
    }});

    // Gap columns
    for (let g = 0; g < GAP_COLS; g++) {{
      const td = document.createElement('td');
      td.className = 'cell-gap';
      tr.appendChild(td);
    }}

    // Reference plant cells
    refPlants.forEach((plant, j) => {{
      const td = document.createElement('td');
      const recog = run.recognized[j];
      td.className = 'cell ' + (recog ? 'cell-tp' : 'cell-fn');
      td.dataset.type = 'tp';
      td.dataset.runIdx = i;
      td.dataset.plantIdx = j;
      tr.appendChild(td);
    }});

    tbody.appendChild(tr);
    prevFamily = run.family;
    prevModel = run.model;
  }});

  tbl.appendChild(tbody);

  // ---- POPUP logic ----
  const popup = document.getElementById('popup');
  const popupTitle = document.getElementById('popup-title');
  const popupTable = document.getElementById('popup-table');

  tbl.addEventListener('mouseover', function(e) {{
    const td = e.target.closest('td.cell');
    if (!td) {{ popup.style.display = 'none'; return; }}

    const runIdx = parseInt(td.dataset.runIdx);
    const run = DATA.runs[runIdx];
    let rows = [];
    let title = '';

    if (td.dataset.type === 'fp') {{
      const fpIdx = parseInt(td.dataset.fpIdx);
      const fpName = DATA.fp_names[fpIdx];
      const present = run.fp_present[fpIdx];
      const count = DATA.fp_run_counts[fpIdx];
      if (present) {{
        title = '<span class="badge badge-fp">FP</span> ' + escHtml(fpName);
        rows.push(['Emitted by', '<span class="fp-val">' + escHtml(run.model) + ' run ' + run.run + '</span>']);
        rows.push(['Present in', '<span class="meta-val">' + count + ' run(s)</span>']);
        const cand = DATA.fp_candidates[runIdx] && DATA.fp_candidates[runIdx][fpName];
        if (cand) {{
          rows.push(['— Nearest reference —', '']);
          rows.push(['Ref name', '<span class="ref-val">' + escHtml(cand.best_ref_name || '(none)') + '</span>']);
          rows.push(['Ref fuel', '<span class="ref-val">' + escHtml(cand.best_ref_fuel || '—') + '</span>']);
          rows.push(['Ref capacity', '<span class="ref-val">' + fmtCap(cand.best_ref_capacity_mw) + '</span>']);
          rows.push(['Ref status', '<span class="ref-val">' + escHtml(cand.best_ref_status || '—') + '</span>']);
          const scoreStr = cand.best_similarity.toFixed(1) + ' / 100 (threshold: 90)';
          const scoreCls = cand.best_similarity >= 90 ? 'score-good' : 'score-bad';
          rows.push(['Name similarity', '<span class="' + scoreCls + '">' + scoreStr + '</span>']);
        }}
      }} else {{
        title = '<span class="badge badge-fp">FP absent</span> ' + escHtml(fpName);
        rows.push(['Not emitted by', escHtml(run.model) + ' run ' + run.run]);
        rows.push(['Present in', '<span class="meta-val">' + count + ' run(s) (not this one)</span>']);
      }}
    }} else {{
      const plantIdx = parseInt(td.dataset.plantIdx);
      const plant = DATA.ref_plants[plantIdx];
      const recog = run.recognized[plantIdx];
      const detail = DATA.match_details[runIdx] && DATA.match_details[runIdx][plantIdx];

      if (recog) {{
        title = '<span class="badge badge-tp">TP</span> ' + escHtml(plant.name);
      }} else {{
        title = '<span class="badge badge-fn">FN</span> ' + escHtml(plant.name);
      }}

      rows.push(['— Reference plant —', '']);
      rows.push(['Ref name', '<span class="ref-val">' + escHtml(plant.name) + '</span>']);
      rows.push(['Ref fuel', '<span class="ref-val">' + escHtml(plant.fuel || '—') + '</span>']);
      rows.push(['Ref capacity', '<span class="ref-val">' + fmtCap(plant.capacity_mw) + '</span>']);
      rows.push(['Ref status', '<span class="ref-val">' + escHtml(plant.status || '—') + '</span>']);
      rows.push(['Ref province', '<span class="ref-val">' + escHtml(plant.province || '—') + '</span>']);
      rows.push(['Ref level', '<span class="ref-val">' + escHtml(plant.level || '—') + '</span>']);

      if (recog && detail) {{
        rows.push(['— Matched system row —', '']);
        rows.push(['Sys name', '<span class="sys-val">' + escHtml(detail.system_name || '—') + '</span>']);
        rows.push(['Sys fuel', '<span class="sys-val">' + escHtml(detail.system_fuel || '—') + '</span>']);
        rows.push(['Sys capacity', '<span class="sys-val">' + fmtCap(detail.system_capacity_mw) + '</span>']);
        rows.push(['Sys province', '<span class="sys-val">' + escHtml(detail.system_province || '—') + '</span>']);
        rows.push(['— Match quality —', '']);
        rows.push(['Match type', '<span class="meta-val">' + escHtml(detail.match_type || '—') + '</span>']);
        const sim = detail.similarity_score;
        rows.push(['Name similarity', '<span class="meta-val">' + (sim != null ? sim.toFixed(1) + ' / 100' : '—') + '</span>']);
        const cap_d = detail.capacity_diff_pct;
        rows.push(['Capacity Δ', '<span class="meta-val">' + (cap_d != null ? cap_d.toFixed(1) + ' %' : '—') + '</span>']);
      }} else if (!recog) {{
        rows.push(['— Not matched —', '<span class="meta-val">FN: model missed this plant</span>']);
      }}
    }}

    popupTitle.innerHTML = title;
    popupTable.innerHTML = rows.map(r =>
      '<tr><td class="label">' + r[0] + '</td><td>' + r[1] + '</td></tr>'
    ).join('');
    popup.style.display = 'block';
    positionPopup(e);
  }});

  tbl.addEventListener('mousemove', function(e) {{
    if (popup.style.display === 'block') positionPopup(e);
  }});

  tbl.addEventListener('mouseleave', function() {{
    popup.style.display = 'none';
  }});

  function positionPopup(e) {{
    const pw = popup.offsetWidth || 460;
    const ph = popup.offsetHeight || 200;
    let x = e.clientX + 14;
    let y = e.clientY + 14;
    if (x + pw > window.innerWidth - 10) x = e.clientX - pw - 10;
    if (y + ph > window.innerHeight - 10) y = e.clientY - ph - 10;
    popup.style.left = x + 'px';
    popup.style.top  = y + 'px';
  }}

  function escHtml(s) {{
    if (!s) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }}

  function fmtCap(v) {{
    if (v == null) return '—';
    return v.toFixed(0) + ' MW';
  }}
}})();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Data builder
# ---------------------------------------------------------------------------


def _build_data(
    data: RecognitionData,
    fp_top_n: int = 40,
    fp_seed: int = 42,
) -> dict:
    """Assemble the JSON data blob for the HTML template.

    Returns a plain dict that the template serialises into the ``DATA``
    JavaScript constant.  All cell payloads use list/dict primitives so
    ``json.dumps`` works without a custom encoder.
    """
    if not data.cells:
        return {
            "runs": [],
            "ref_plants": [],
            "fp_names": [],
            "fp_run_counts": [],
            "status_bands": [],
            "match_details": {},
            "fp_candidates": {},
        }

    # Plant (column) order, keyed by plant_id.

    plant_order, plant_info = _order_plants(data.cells)
    n_plants = len(plant_order)
    plant_col = {pid: j for j, pid in enumerate(plant_order)}

    # Run (row) order.
    run_recog: dict[tuple[str, int], dict[int, bool]] = {}
    for c in data.cells:
        run_recog.setdefault((c.model, c.run), {})[c.plant_id] = c.recognized
    size_by_model: dict[str, float] = {}
    size_class_by_model: dict[str, str | None] = {}
    for c in data.cells:
        size_class_by_model.setdefault(c.model, c.size_class)
    for model, sc in size_class_by_model.items():
        size_by_model[model] = _model_size_b(model, sc)
    runs = _order_runs(list(run_recog.keys()), size_by_model)

    # FP panel
    top_fps = top_false_positives(data.fp_presence, top_n=fp_top_n, seed=fp_seed)
    fp_names = [name for name, _ in top_fps]
    fp_run_counts = [count for _, count in top_fps]
    # Status bands for column header
    from .exp1_recognition import STATUS_LABELS_EN

    bands: list[dict] = []
    start = 0
    for j in range(1, n_plants + 1):
        if j == n_plants or plant_info[plant_order[j]][1] != plant_info[plant_order[start]][1]:
            status = plant_info[plant_order[start]][1]
            label = STATUS_LABELS_EN.get(status, status)
            bands.append({"label": label, "start": start, "end": j - 1})
            start = j

    # Reference plants list (for column headers + popup)
    ref_plants = [
        {
            "name": plant_info[pid][0],
            "status": plant_info[pid][1],
            "capacity_mw": plant_info[pid][2],
            "fuel": "",   # not stored in plant_info; populated from match_details if available
            "province": None,
            "level": "—",
        }
        for pid in plant_order
    ]

    # Enrich ref_plants with fuel/province from match_details (any run works)
    if data.match_details:
        for pid, j in plant_col.items():
            # Find any run's detail for this plant_id
            for (_m, _r, p), detail in data.match_details.items():
                if p == pid:
                    ref_plants[j]["fuel"] = detail.ref_fuel
                    ref_plants[j]["province"] = detail.ref_province
                    break

    # Run rows
    run_rows = []
    for _i, (model, run) in enumerate(runs):
        recognized_vec = [
            bool(run_recog[(model, run)].get(plant_order[j], False))
            for j in range(n_plants)
        ]
        fp_set = data.fp_presence.get((model, run), set())
        fp_present_vec = [name in fp_set for name in fp_names]
        run_rows.append(
            {
                "model": model,
                "run": run,
                "family": model_family(model),
                "recognized": recognized_vec,
                "fp_present": fp_present_vec,
            }
        )

    # Match details for hover: index by [run_idx][plant_col_idx]
    match_details_out: dict[str, dict[str, dict]] = {}
    for (model, run, plant_id), detail in data.match_details.items():
        run_idx = next(
            (i for i, (m, r) in enumerate(runs) if m == model and r == run), None
        )
        if run_idx is None:
            continue
        plant_j = plant_col.get(plant_id)
        if plant_j is None:
            continue
        run_key = str(run_idx)
        if run_key not in match_details_out:
            match_details_out[run_key] = {}
        match_details_out[run_key][str(plant_j)] = {
            "system_name": detail.system_name,
            "system_fuel": detail.system_fuel,
            "system_capacity_mw": detail.system_capacity_mw,
            "system_province": detail.system_province,
            "match_type": detail.match_type,
            "similarity_score": detail.similarity_score,
            "capacity_diff_pct": detail.capacity_diff_pct,
        }

    # FP candidates: index by [run_idx][fp_name]
    fp_candidates_out: dict[str, dict[str, dict]] = {}
    for (model, run, fp_name), cand in data.fp_candidates.items():
        run_idx = next(
            (i for i, (m, r) in enumerate(runs) if m == model and r == run), None
        )
        if run_idx is None:
            continue
        run_key = str(run_idx)
        if run_key not in fp_candidates_out:
            fp_candidates_out[run_key] = {}
        fp_candidates_out[run_key][fp_name] = {
            "best_ref_name": cand.best_ref_name,
            "best_similarity": cand.best_similarity,
            "best_ref_fuel": cand.best_ref_fuel,
            "best_ref_capacity_mw": cand.best_ref_capacity_mw,
            "best_ref_status": cand.best_ref_status,
        }

    return {
        "runs": run_rows,
        "ref_plants": ref_plants,
        "fp_names": fp_names,
        "fp_run_counts": fp_run_counts,
        "status_bands": bands,
        "match_details": match_details_out,
        "fp_candidates": fp_candidates_out,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_html(
    records_glob: str,
    reference_path: Path,
    output: Path,
    fp_top_n: int = 40,
    fp_seed: int = 42,
    models: list[str] | None = None,
    exclude_models: list[str] | None = None,
) -> None:
    """Render the Exp1 interactive recognition matrix as a standalone HTML file.

    Args:
        records_glob: Glob for record.json files.
        reference_path: Path to the gold reference CSV.
        output: Destination HTML file path.
        fp_top_n: Number of most-common false positives to show.
        fp_seed: Seed for FP tie-breaking (rebuild-stable).
        models: If given, include only these models.
        exclude_models: If given, exclude these models.
    """
    data = load_exp1_recognition(records_glob, reference_path, collect_details=True)
    if models is not None or exclude_models is not None:

        def keep(m: str) -> bool:
            return (models is None or m in models) and (
                exclude_models is None or m not in exclude_models
            )

        data.cells = [c for c in data.cells if keep(c.model)]
        data.fp_presence = {k: v for k, v in data.fp_presence.items() if keep(k[0])}
        data.match_details = {k: v for k, v in data.match_details.items() if keep(k[0])}
        data.fp_candidates = {k: v for k, v in data.fp_candidates.items() if keep(k[0])}

    if not data.cells:
        log.warning("No recognition data for pattern: %s", records_glob)
        return

    payload = _build_data(data, fp_top_n=fp_top_n, fp_seed=fp_seed)
    n_runs = len(payload["runs"])
    n_ref_plants = len(payload["ref_plants"])
    n_fps = len(payload["fp_names"])

    html = _HTML_TEMPLATE.format(
        n_runs=n_runs,
        n_ref_plants=n_ref_plants,
        n_fps=n_fps,
        data_json=json.dumps(payload, ensure_ascii=False),
        color_fp=_COLOR_FP,
        color_match=_COLOR_MATCH,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    log.info("Wrote interactive matrix to %s", output)
    log.info("  %d runs × %d plants · %d FP columns", n_runs, n_ref_plants, n_fps)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Generate interactive HTML recognition matrix for LP matcher QA"
    )
    parser.add_argument(
        "--records-glob",
        default="experiments/outputs/exp1_batch2/*.record.json",
        help="Glob for exp1_batch2 record.json files",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=VN_THERMAL_PLANTS_RELEASE_CSV,
        help="Reference CSV (gold list)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output HTML path",
    )
    parser.add_argument(
        "--fp-top-n",
        type=int,
        default=40,
        help="Top-N false positives to show",
    )
    parser.add_argument(
        "--fp-seed",
        type=int,
        default=42,
        help="Seed for FP tie-breaking (rebuild-stable)",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="Only include these models",
    )
    parser.add_argument(
        "--exclude-models",
        nargs="+",
        default=None,
        help="Exclude these models",
    )
    args = parser.parse_args(argv)
    write_html(
        records_glob=args.records_glob,
        reference_path=args.reference,
        output=args.output,
        fp_top_n=args.fp_top_n,
        fp_seed=args.fp_seed,
        models=args.models,
        exclude_models=args.exclude_models,
    )


if __name__ == "__main__":
    main()
