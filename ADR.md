# Architecture Decision Records — aedist-bench

## ADR-1: Deux repos → Monorepo

**Décidé** : 2026-02-16, **supercédé** : 2026-04-02

~~Deux repos séparés (code dans `aedist`, rapport dans `aedist-technical-report`).~~

Monorepo unique. Le repo `aedist` est archivé sur GitHub. Code, tests, expériences, rapport et slides dans un seul repo. Les cycles de build différents sont gérés par des sous-Makefiles.

---

## ADR-2: Matching MILP (lp.py) comme algorithme par défaut

**Décidé** : 2026-02-16

Adopter `Matching/lp.py` (assignement MILP via PuLP/CBC) comme matcher principal. Le greedy 2-pass reste disponible comme fallback.

**Justification** : Résultat globalement optimal (pas de sensibilité à l'ordre de parcours). Performant sur cette taille (~164 × ~100). Publiable comme contribution méthodologique.

---

## ADR-3: Matching global (pas de groupement province×fuel)

**Décidé** : 2026-02-16

Le benchmark effectue le matching sur l'ensemble du dataset, sans grouper par (province, fuel). Les erreurs de province ou de fuel sont capturées dans les métriques d'attributs.

**Justification** : On veut distinguer "le LLM connaît la centrale mais se trompe de province" (1 erreur d'attribut) de "le LLM ne connaît pas la centrale" (1 omission). Le matching global donne une image plus fine.

**Note opérationnelle** : Pour la vérification manuelle, la table de réconciliation inclut province et fuel en colonnes. On peut toujours trier/filtrer par province+fuel pour faciliter la relecture — c'est indispensable en pratique. Un flag `--group-by-province` peut être ajouté au runner pour ce cas d'usage.

---

## ADR-4: Granularité au niveau central (pas unité)

**Décidé** : 2026-02-16

Le benchmark opère au niveau **centrale** (plant). La référence est `HDM_aggregated.csv` (164 entrées), pas `HDM.csv` (251 unités).

**Justification** : Les LLMs produisent quasi-systématiquement au niveau central. C'est aussi le niveau pertinent pour la modélisation énergie (PyPSA).

**Mise à jour (ticket 0416, 2026-06-05)** : la règle d'agrégation originale (strip "Unit N", somme par nom+statut, dans `HDM_aggregate.py`) inventait l'identité de centrale à partir du nom — interdit. Le pipeline v2 (`aggregate_units.py`) groupe sur la colonne d'adresse `Plant` (le parentage est une donnée, jamais une inférence de nom) et somme les capacités par centrale. `HDM_aggregate.py` / `HDM_aggregated.csv` sont supprimés.

---

## ADR-5: Un ticket de vérification = un trait × une cible = un script

**Décidé** : 2026-04-17

Les tickets de vérification sont organisés par (trait, cible), où *trait* est une propriété vérifiable du pipeline ou de sa sortie (source-grounding, cohérence, incrémentalité, résolution de conflits, décroissance d'escalation, etc.) et *cible* ∈ {table, méthode, système}. Chaque ticket livre **un unique script** exécutable qui évalue ce trait et produit un rapport. L'ensemble des scripts constitue la batterie de vérification automatique.

**Justification** :
- TDD pour méthodes — chaque ticket démontre une propriété, pas seulement un livrable de code.
- Composabilité — la batterie tourne automatiquement (cf. healthcheck matinal, check "tests green").
- Lisibilité — un ticket = une colonne dans la matrice (trait × cible) = une page de preuve.
- Évite les tickets fourre-tout qui mélangent plusieurs propriétés.

**Conséquence opérationnelle** : les scripts vivent dans `scripts/verify/` (un fichier par ticket, nommé d'après le trait et la cible). Tickets de référence : 0097 (source-grounding × table, 3 phases), 0101–0104 (incrémentalité, décroissance d'escalation, cohérence, résolution de conflits).

---

## ADR-6: Mémoire HITL = cahier annoté du statisticien, pas table de substitutions

**Décidé** : 2026-04-17

Les règles de la mémoire ratifiée par HITL (alias, unité/format, terme local à la source, synonyme d'attribut) sont écrites au format **annoté** : chaque règle porte un contexte, une justification, des cas limites et une piste d'audit. Ce ne sont pas de simples paires `motif → substitution` à consommer mécaniquement.

**Justification** :
- Un statisticien humain reprenant le projet doit pouvoir lire la mémoire et comprendre **pourquoi** chaque règle existe, pas seulement ce qu'elle fait.
- Les cas limites (diacritiques, conventions de séparateurs de milliers multilingues, hiérarchies institutionnelles, ambiguïtés brut/net) méritent un flag explicite, pas une substitution silencieuse.
- L'audit externe (relecture méthodologique, due diligence) repose sur la lisibilité des décisions humaines encodées dans la mémoire.

**Conséquence opérationnelle** : chaque règle YAML dans `data/memory/` porte au minimum les champs `pattern`, `replacement`, `rationale`, `edge_cases`, `ratified_by`, `evidence` (passage source + document + ligne/page). Le code de vérification lit `pattern` et `replacement` ; les humains lisent tout le reste. La règle est d'abord une **note de terrain**, secondairement une substitution.

---

## ADR-7: The metrics dict is the complete scientific record

**Decided**: 2026-04-30

`records_to_metrics()` in `measurements.py` produces one dict per run. That
dict must contain **all fields a scientist needs to understand experimental
conditions and interpret results**. Figures and tables are projections that
select the columns they need. The dict is not defined by what the paper
currently shows.

**Three layers in the data flow:**

```
Raw JSON          →  RunRecord / measurements.jsonl  →  metrics dict  →  figures / tables
(worker writes)      (complete record, JSONL)            (flat dict)      (column projections)
```

**What belongs in the metrics dict (conditions + results):**

| Category | Fields |
|----------|--------|
| Model identity | `model`, `method`, `prompt_version` |
| Controlled conditions | `temperature`, `seed`, `max_tokens`, `num_ctx`, `no_think`, `web_search` (effective), `provider_order` |
| Diagnostic | `tokens_in`, `tokens_out`, `finish_reason` |
| Results | `f1`, `coverage`, `precision`, `n_matched`, `n_missed`, `n_hallucinated`, `fuel_accuracy`, `status_accuracy`, `province_accuracy` |
| Resources | `cost_usd`, `wall_seconds` |
| Agent runs (0172) | `agent_family`, `agent_mode`, `synopsis_sha`, `designed_prompt_sha`, `n_web_search_calls`, `n_citations`, `parsed_table_path`, `retry_count`, `error`, `reasoning_summary`, `thinking_tokens`, `cost_breakdown`, `tool_calls_cost_usd` |

**What does not belong:** bookkeeping fields (`run_id`, `timestamp`,
`result_file`, `validation`). These are in `RunRecord` for system purposes;
they are not scientific data.

**Justification:**

`measurements.jsonl` is declared the single source of truth (MASTERPLAN §4).
That claim is only meaningful if the metrics dict is complete. A lossy
projection forces analysts to re-read raw JSON files to answer diagnostic
questions ("did this run hit the context limit?", "was seed set?"). The
complete record makes such questions answerable without leaving the table.

Figures and tables are already projections — they select the columns they
display. Making the source richer does not change them.

**Operational consequences:**

- `records_to_metrics()` is expanded to include all condition and diagnostic
  fields listed above. Scripts that read metrics dicts ignore unused columns.
- New fields in `RunRecord` (from ticket 0139: `seed`, `provider_order`,
  `max_tokens`, `num_ctx`, `web_search` effective; `finish_reason`) are
  surfaced in the metrics dict on the same schedule.
- `records_to_metrics()` docstring is updated to state this contract
  explicitly.
- Ticket 0172 (SOTA frontier-API experiment, umbrella 0166): agent-mode
  fields are surfaced as a single row in the table above. Schema additions
  are strictly optional — the 330 pre-existing `measurements.jsonl` records
  parse unchanged. `web_search_calls` and `citations` are projected as
  counts (`n_web_search_calls`, `n_citations`); the raw lists remain in
  the `RunRecord` for forensic re-reading. `tool_calls_cost_usd` is kept
  distinct from `cost_usd` so connector / web-search fees do not blend
  with token economics.
