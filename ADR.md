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

**Justification** : Les LLMs produisent quasi-systématiquement au niveau central. C'est aussi le niveau pertinent pour la modélisation énergie (PyPSA). La règle d'agrégation (strip "Unit N", somme des capacités par nom+statut) est documentée dans `HDM_aggregate.py`.

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
