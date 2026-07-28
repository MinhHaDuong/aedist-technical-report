# Alignement : repos existants ↔ aedist-bench

## 1. Cartographie des repos existants

### `aedist-feasibility-demonstrator/` (code)

| Composant | Fichier(s) | Fonction | État |
|---|---|---|---|
| **Query LLM** | `src/query.py` | Interroge N modèles via OpenRouter, sauve JSON (prompt + réponse + usage) | ✅ Fonctionnel |
| **Modèles** | `src/models.yaml` | Registre de 15 modèles (Claude, GPT-4o, DeepSeek, Llama, Qwen, Grok, etc.) | ✅ Complet |
| **Prompt** | `src/prompts/prompt1.txt` | Prompt simple (single-shot CSV) | ✅ Prompt 1 seul ; prompt 2 et relances absents du repo |
| **Convert→LaTeX** | `src/convert.py` | Compte les lignes CSV dans les réponses, génère macros + tables LaTeX | ✅ Partiel : données relances/RAG hardcodées |
| **Nettoyage** | `compare/PowerPlantDataframeCleaner/` | Normalise noms, provinces, fuels, capacités, statuts via config JSON | ✅ Robuste, config-driven |
| **Matching LP** | `compare/Matching/lp.py` | MILP (PuLP) : fuzzy names + capacité → assignement optimal | ✅ Sophistiqué |
| **Matching phased** | `compare/Matching/phased.py` | Alternative : exact → fuzzy en 2 passes | ✅ Non utilisé (commenté) |
| **Réconciliation** | `compare/reconcile.py` | Orchestre : load CSV → clean → group by (province, fuel) → match → CSV résultat | ✅ Fonctionnel |
| **Référence** | `compare/input/HDM.csv` | 251 lignes (unités), 5 colonnes | ✅ Niveau unité |
| **Référence agrégée** | `compare/input/HDM_aggregated.csv` | 164 lignes (centrales), 6 colonnes | ✅ Niveau central |
| **Outputs LLM** | `compare/input/Claude_*.csv` | 4 fichiers : concise, normal, RAG18, relance | ✅ Claude seul |
| **GEM** | `compare/input/GEM.csv` + `GEM_aggregated.csv` | 308/153 lignes, Global Energy Monitor | ✅ Comparateur externe |
| **PDF→MD** | `pdfOCR2md/pdfOCR2md.py` | Pipeline PDF → OCR → Markdown | ✅ Prototype |

### `aedist-technical-report/` (rapport)

| Composant | Fichier(s) | Fonction | État |
|---|---|---|---|
| **Rapport** | `report.tex` | ~1600 lignes LaTeX, 9 chapitres | ✅ Complet mais à restructurer (cf TODO.md) |
| **Biblio** | `refs.bib` | Références | ✅ |
| **Build** | `Makefile` | `make query`, `make tables`, `make` (tectonic) | ✅ |
| **Inputs** | `inputs/` | Zotero list, energy stats knowledge | ✅ |
| **TODO** | `TODO.md` | Plan de révision détaillé | ✅ Aligné avec notre discussion |

**Lien report→code** : Le Makefile du rapport invoque `aedist/src/query.py` et `aedist/src/convert.py` — il attend le repo code comme sous-dossier `aedist/`.

---

## 2. Matrice d'alignement : existant ↔ aedist-bench

| Fonction aedist-bench | Existant dans les repos | Écart | Action |
|---|---|---|---|
| **Schema Pydantic** (`schema.py`) | Implicite dans les colonnes CSV + `config.json` | Le code existant n'a pas de schéma formel ; les colonnes sont {name, province, fuel, capacity, status} | **Créer** le schéma Pydantic comme couche au-dessus du cleaner existant |
| **Normalisation** (`normalize.py`) | `PowerPlantDataframeCleaner` (config-driven, diacritics strip, regex) | Le cleaner existant est plus complet (config JSON extensible, roman→arabic). Notre `normalize.py` est plus simple. | **Adopter** le cleaner existant comme backend, wrapper Pydantic par-dessus |
| **Matching** (`match.py`) | `Matching/lp.py` (MILP optimal) + `Matching/phased.py` (greedy 2-pass) | Notre match.py est un greedy 2-pass similaire à `phased.py`. Le LP est strictement supérieur (optimal global). | **Adopter** `lp.py` comme matcher par défaut, garder greedy comme fallback rapide |
| **Métriques** (`metrics.py`) | Compteurs dans `reconcile.py` (matched/fuzzy/only_in_file1/file2) | Les métriques existantes sont des comptes bruts. Il manque : coverage/precision/F1, fuel/status accuracy, taxonomie d'erreurs. | **Étendre** : ajouter le calcul de métriques formelles sur les résultats existants |
| **Runner CLI** (`runner.py`) | `reconcile.py` (argparse file1 file2) | Le runner existant compare 2 fichiers quelconques. Le nôtre évalue un système vs référence fixe. | **Adapter** : spécialiser pour l'usage benchmark (référence = HDM, système = output LLM) |
| **Référence dataset** | `HDM.csv` (251 unités) + `HDM_aggregated.csv` (164 centrales) | Le dataset existe mais : (a) pas versionné formellement, (b) pas de COD, (c) statuts codés "3 permitted" pas "planned" | **Nettoyer** HDM_aggregated → `vietnam_thermal_v1.csv` avec schéma canonique |
| **Outputs LLM** | 4 fichiers Claude uniquement | Manquent : GPT-4o, DeepSeek, o3-mini, Llama, RAG configs | **Compléter** via `query.py` (prompt 1 déjà automatisé) + collecter manuellement les runs RAG |
| **Prompts** | `prompt1.txt` seul | Manquent : prompt2 (structuré), prompt relance | **Ajouter** au repo |
| **LaTeX generation** | `convert.py` → macros + tables | Données relances/RAG hardcodées avec TODO pour automation | **Connecter** aux métriques de aedist-bench une fois calculées |
| **Groupement province×fuel** | `reconcile.py` groupe par (province, fuel) avant matching | Notre bench ne groupe pas — matching global | **Décision** : le groupement est-il souhaitable ? Avantage : réduit les faux positifs cross-province. Inconvénient : rate les erreurs de province. |

---

## 3. Décisions architecturales

### 3.1 Mono-repo vs multi-repo

**État actuel** : 2 repos séparés, le rapport inclut le code comme sous-dossier.

**Options** :

| Option | Pro | Contra |
|---|---|---|
| A. Garder 2 repos, ajouter `aedist-bench` comme 3e | Séparation des responsabilités | 3 repos à synchroniser |
| B. Fusionner code + bench dans un repo, rapport séparé | Un seul repo pour tout le code Python | Rapport continue à pointer vers sous-dossier |
| **C. Mono-repo : rapport + code + bench** | Tout ensemble, Makefile simplifié | Repo plus gros mais cohérent |

**Recommandation** : **Option B** — fusionner `aedist-feasibility-demonstrator` et `aedist-bench` dans un seul repo `aedist`. Le rapport reste séparé (il a sa propre logique de build LaTeX) et pointe vers le repo code.

### 3.2 Réutiliser vs réécrire le matching

**Recommandation** : Réutiliser `lp.py` (MILP). C'est une contribution technique du projet — le matching optimal par programmation linéaire est plus rigoureux que le greedy et publiable. Ajouter les métriques formelles (coverage, precision, F1) par-dessus.

**Adaptation nécessaire** : `lp.py` attend des DataFrames avec colonnes `name_clean`, `capacity_clean`. Il faut :
1. Un adaptateur Pydantic `list[Plant]` → DataFrame avec colonnes attendues
2. Un adaptateur retour DataFrame résultats → `list[ReconciliationEntry]`

### 3.3 Granularité : unité vs centrale

**État actuel** : HDM.csv est au niveau unité (251 lignes), HDM_aggregated au niveau centrale (164). Les outputs LLM sont au niveau central.

**Recommandation** : Le benchmark opère au **niveau central** (cohérent avec ce que les LLMs produisent). Garder HDM_aggregated comme référence. Documenter la règle d'agrégation (strip "Unit N" suffix, sum capacities within same plant+status).

### 3.4 Groupement province×fuel

**Le code existant** groupe par (province, fuel) avant matching — ce qui empêche de matcher "Vĩnh Tân" si le LLM met la mauvaise province.

**Recommandation** : Le benchmark ne doit **pas** grouper. Le matching global (sur tout le dataset) est plus fidèle à la tâche réelle. Les erreurs de province/fuel sont capturées séparément dans les métriques d'attributs.

---

## 4. Plan de migration concret

### Phase 1 : Consolider le dataset de référence

```
HDM_aggregated.csv  →  data/reference/vietnam_thermal_v1.csv
```

- Renommer colonnes → schéma canonique (Name→name, Capacity→capacity_mwe, etc.)
- Normaliser statuts : "5 operating"→"operational", "9 cancelled"→"cancelled", etc.
- Ajouter COD là où disponible (source : rapport chap. 5)
- Versionner (git tag v1.0)

### Phase 2 : Adapter le matching existant

```python
# Nouveau fichier : src/aedist_bench/match_lp.py
# Wrapper autour de compare/Matching/lp.py

def reconcile_lp(reference: list[Plant], system: list[Plant], ...) -> list[ReconciliationEntry]:
    """Adapte lp.reconcile() pour l'interface Pydantic du benchmark."""
    ref_df = plants_to_dataframe(reference)   # → colonnes name, name_clean, capacity_clean
    sys_df = plants_to_dataframe(system)
    result_df = lp.reconcile(ref_df, sys_df)
    return dataframe_to_entries(result_df)     # → list[ReconciliationEntry]
```

- Réutiliser `PowerPlantDataframeCleaner` pour la normalisation
- Réutiliser `lp.py` pour le matching
- Supprimer le groupement province×fuel (matching global)
- Ajouter `metrics.py` par-dessus

### Phase 3 : Collecter les outputs manquants

| Configuration | Source | Fichier cible |
|---|---|---|
| LLM direct (prompt 1) × 15 modèles | `query.py` via OpenRouter | `outputs/llm_direct/{model}.csv` |
| LLM multi-turn (prompt 2 + relances) | Manuellement (les relances ne sont pas automatisables via API simple) | `outputs/llm_multiturn/{model}_prompt2_relance{n}.csv` |
| RAG curated | Manuellement (requires doc injection) | `outputs/rag_curated/{model}.csv` |
| RAG extended | Manuellement | `outputs/rag_extended/{model}.csv` |

### Phase 4 : Générer les résultats pour le papier

```bash
# Évaluer chaque output
for f in outputs/**/*.csv; do
    aedist-bench evaluate "$f" --format json >> results/summary/all_metrics.json
done

# Générer les tables LaTeX pour le rapport
aedist-bench report --output paper/tables/
```

### Phase 5 : Aligner le rapport

Le `TODO.md` du rapport est déjà aligné avec cette stratégie. Changements clés :
- Chap 2+3 fusionnés → référencer les métriques du benchmark
- `convert.py` → remplacer les données hardcodées par lecture de `results/summary/`
- Conclusion → couper le grant proposal, garder les findings

---

## 5. Fichiers à déplacer / renommer

| Source | Destination dans aedist-bench | Action |
|---|---|---|
| `compare/input/HDM_aggregated.csv` | `data/reference/vietnam_thermal_v1.csv` | Nettoyer + renommer colonnes |
| `compare/input/HDM.csv` | `data/reference/vietnam_thermal_units_v1.csv` | Garder comme référence unités |
| `compare/input/GEM_aggregated.csv` | `data/reference/gem_thermal.csv` | Comparateur externe |
| `compare/input/Claude_*.csv` | `outputs/llm_*/claude_sonnet_*.csv` | Renommer par configuration |
| `compare/Matching/lp.py` | `src/aedist_bench/match_lp.py` | Adapter interface |
| `compare/PowerPlantDataframeCleaner/` | `src/aedist_bench/cleaner/` | Réutiliser tel quel |
| `compare/PowerPlantDataframeCleaner/config.json` | `src/aedist_bench/cleaner/config.json` | Idem |
| `src/query.py` | `src/aedist_bench/query.py` | Réutiliser |
| `src/models.yaml` | `models.yaml` | Réutiliser |
| `src/prompts/prompt1.txt` | `prompts/prompt_1_singleshot.txt` | Renommer |
