# Status Vocabulary Map — AEDIST

Committed 2026-06-08 as part of ticket 0454 (Imagine-phase inventory).
Covers the four vocabularies the project uses for plant lifecycle status.

---

## 1. Reference master (`data/reference/vietnam_thermal_plants_v2_classified.csv`)

9-class ordinal ladder (col 5 `status`):

| Ordinal | Label            | Count (v2.1, 173 plants) | Notes |
|---------|-----------------|--------------------------|-------|
| 0       | exploring       | 2                        | Pre-announcement |
| 1       | announced       | 20                       | |
| 2       | proposed        | 42                       | |
| 3       | added to PDP    | 15                       | Vietnam-specific: national lifecycle gate (PDP inclusion) |
| 4       | permitted       | 5                        | |
| 5       | construction    | 10                       | |
| 6       | operating       | 56                       | |
| 9       | cancelled       | 20                       | |
| 10      | retired         | 2                        | |

*Header row + 3 malformed rows account for the CSV's 177 non-blank lines.*

---

## 2. Exp1 prompt (`experiments/prompts/prompt_complete.txt`, line 35)

8-class GEM-style vocabulary, capitalised as instruction text:

`Announced / Pre-permit / Permitted / Construction / Operating / Shelved / Cancelled / Retired`

---

## 3. GEM standard (Global Energy Monitor)

De-facto interchange vocabulary; relevant for downstream comparability
(GEM reconciliation tickets 0428/0429):

`announced`, `pre-construction`, `permitted`, `construction`, `operating`,
`mothballed`, `cancelled`, `retired`, `shelved`

*GEM "pre-construction" ≈ prompt "Pre-permit"; GEM "mothballed" ≈ prompt "Shelved".*

---

## 4. Analysis / display vocabulary

### 4a. Canonical enum (`src/aedist/schema.py`, `PlantStatus`)

```
PROPOSED, PLANNED, CONSTRUCTING, OPERATIONAL, CANCELLED, RETIRED, UNKNOWN
```

### 4b. Reference-to-canonical projection (`src/aedist/evaluate.py`, `_STATUS_ORDINAL_PROJECTION`)

Author-ratified v1-compat mapping (ordinal → PlantStatus):

| Reference ordinal(s) | Label(s)                   | → PlantStatus  |
|----------------------|---------------------------|----------------|
| 0, 1, 2              | exploring, announced, proposed | PROPOSED   |
| 3, 4                 | added to PDP, permitted    | PLANNED        |
| 5                    | construction               | CONSTRUCTING   |
| 6                    | operating                  | OPERATIONAL    |
| 9                    | cancelled                  | CANCELLED      |
| 10                   | retired                    | RETIRED        |

`_STATUS_MAP` also accepts bare model-output strings:
`operational/operating → OPERATIONAL`, `planned → PLANNED`,
`proposed/announced → PROPOSED`, `constructing/construction/under construction → CONSTRUCTING`,
`cancelled/canceled/shelved → CANCELLED`, `retired → RETIRED`.

### 4c. Display order (`src/aedist/exp1_recognition.py`, `STATUS_ORDER`)

```python
["proposed", "planned", "constructing", "operational", "retired", "cancelled"]
```

### 4d. Display labels (`src/aedist/exp1_recognition.py`)

| PlantStatus key | FR label (`STATUS_LABELS`) | EN label (`STATUS_LABELS_EN`) |
|-----------------|---------------------------|-------------------------------|
| proposed        | En projet                 | Proposed                      |
| planned         | Planifiée                 | Planned                       |
| constructing    | En construction           | Under construction            |
| operational     | Opérationnelle            | Operational                   |
| cancelled       | Annulée                   | Cancelled                     |
| retired         | Retirée                   | Retired                       |

---

## 5. Coherence checker (`src/aedist/score_mechanical.py`, `_ALLOWED_STATUSES`)

Accepted model-output status strings for coherence scoring (sixth place
the vocabulary lives). Superset of GEM canonical + common synonyms:

```
# GEM canonical
announced, pre-permit, pre-permit development, permitted,
construction, operating, shelved, cancelled, retired
# Accepted synonyms
operational, under construction, approved, planned,
suspended, commissioning, decommissioned
```

---

## 6. Cleaner normalisation (`src/aedist/cleaner/config.json`, `status_substitutions`)

The cleaner strips the leading ordinal prefix via `^\d+\s*(.+)$` → `\1`,
then passes through: `operating`, `retired`, `cancelled`, `construction`,
`pre-permit`, `permitted`, `announced`, `exploring`, `pre-construction`,
`shelved`. The result lands in the `status_clean` column used by
`reconcile.py` for the per-row `status_match` attribute metric.

---

## Cross-vocabulary mapping

| Reference ordinal | Reference label  | Prompt term   | GEM term         | Analysis bucket (PlantStatus) | FR display label | EN display label    |
|-------------------|-----------------|---------------|-----------------|-------------------------------|-----------------|---------------------|
| 0                 | exploring        | —             | —               | PROPOSED                      | En projet        | Proposed            |
| 1                 | announced        | Announced     | announced       | PROPOSED                      | En projet        | Proposed            |
| 2                 | proposed         | —             | —               | PROPOSED                      | En projet        | Proposed            |
| 3                 | added to PDP     | —             | — (VN-specific) | PLANNED                       | Planifiée        | Planned             |
| 4                 | permitted        | Permitted     | permitted       | PLANNED                       | Planifiée        | Planned             |
| 5                 | construction     | Construction  | construction    | CONSTRUCTING                  | En construction  | Under construction  |
| 6                 | operating        | Operating     | operating       | OPERATIONAL                   | Opérationnelle   | Operational         |
| 9                 | cancelled        | Cancelled     | cancelled       | CANCELLED                     | Annulée          | Cancelled           |
| 10                | retired          | Retired       | retired         | RETIRED                       | Retirée          | Retired             |
| —                 | —                | Pre-permit    | pre-construction| (→ PLANNED via _STATUS_MAP)   | Planifiée        | Planned             |
| —                 | —                | Shelved       | shelved/mothballed | (→ CANCELLED via _STATUS_MAP) | Annulée       | Cancelled           |

**Open questions (for author decision, criterion 2):**
- Should analysis stay at 6-bucket v1-compat, or align on GEM granularity?
  Changing re-touches `_STATUS_ORDINAL_PROJECTION`, the difficulty table,
  and all quoted recognition-by-status numbers. Post-preprint work at earliest.
- Should display labels switch to GEM English terms (e.g. "Pre-construction"
  instead of "Planned"), given the preprint is in English?
- Does "3 added to PDP" (Vietnam-specific gate) deserve a distinct analysis bucket?

---

## Consumer inventory

| Consumer | File | Vocabulary used | Impact of granularity change |
|----------|------|-----------------|------------------------------|
| Reference parser | `evaluate.py:project_status()` | ordinal → PlantStatus | Mapping table must be updated |
| LP matcher input | `evaluate.py:plants_from_csv()` | ordinal via `project_status` | Same |
| Coherence scorer | `score_mechanical.py:_ALLOWED_STATUSES` | GEM + synonyms | Add/remove terms |
| Cleaner normalise | `cleaner/config.json:status_substitutions` | GEM base terms | Add new terms if reference changes |
| Reconcile `status_match` | `reconcile.py:_lookup_attrs()` | `status_clean` (cleaner output) | Cleaner change propagates |
| Recognition matrix (FR) | `plot_exp1_matrix.py` + `STATUS_LABELS` | 6-bucket + FR labels | Relabel or add bands |
| Recognition matrix (EN) | `plot_exp1_matrix.py` + `STATUS_LABELS_EN` | 6-bucket + EN labels | Relabel or add bands |
| Recognition matrix portrait | `plot_exp1_matrix_portrait.py` + `STATUS_LABELS_EN` | 6-bucket + EN labels | Relabel or add bands |
| Recognition matrix interactive | `plot_exp1_matrix_interactive.py` + `STATUS_LABELS_EN` | 6-bucket + EN labels | Relabel or add bands |
| Status difficulty table | `tabulate_status_difficulty.py` + `STATUS_LABELS` | 6-bucket + FR labels | Row count and labels change |
| `status_match` metric | `metrics.py:wrong_status` | PlantStatus equality | No direct change |
| Reconciliation table | `tabulate_reconciliation.py` | `status_match` boolean | No direct change |
| Prompt (model instruction) | `experiments/prompts/prompt_complete.txt` | 8-class GEM-style | Would need rewording if reference changes |
