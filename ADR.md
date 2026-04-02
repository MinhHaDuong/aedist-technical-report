# Architecture Decision Records — aedist-bench

## ADR-1: Deux repos (code+bench fusionnés, rapport séparé)

**Décidé** : 2026-02-16

Fusionner `aedist-feasibility-demonstrator` et `aedist-bench` dans un repo unique `aedist`. Le rapport LaTeX (`aedist-technical-report`) reste un repo séparé et pointe vers `aedist/` comme sous-dossier.

**Justification** : Un seul package Python installable, pas de duplication du code de normalisation/matching. Le rapport a un cycle de build différent (tectonic + BibTeX).

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

**Justification** : Les LLMs produisent quasi-systématiquement au niveau central. C'est aussi le niveau pertinent pour la modélisation énergie (PyPSA). La règle d'agrégation (strip "Unit N", somme des capacités par nom+statut) est documentée dans `HDM_aggregate.py`.
