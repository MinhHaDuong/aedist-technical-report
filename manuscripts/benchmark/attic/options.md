Voici trois façons (assez différentes) de vous y prendre pour **coder un benchmark de système agentique de statistique économique**, en restant aligné avec vos critères de stats (exhaustivité, cohérence, provenance, mise à jour temporelle) et vos métriques (coverage/precision/justification).  

## Approche 1 — “Benchmark d’abord” (pipeline d’évaluation robuste, agents en boîte noire)

Idée : vous construisez un **harness d’évaluation** impeccable et reproductible, et vous branchez dedans n’importe quel système (LLM direct, multi-tour, RAG, agentique), traité comme une boîte noire qui produit une table.

Briques à coder

* **Schéma canonique** (pydantic) : Plant(name, fuel, status, cod_date, province, capacity_mwe, + provenance fields).
* **Normalisation** : nettoyage unités, dates, alias de noms, mapping statuts (planned/under construction/operational/retired/cancelled), etc.
* **Matching à la référence** :

  * exact + fuzzy sur noms,
  * tolérance sur capacités (ex. +/- x%),
  * règles “plant vs unit vs project”.
* **Métriques** : coverage (recall), precision, justification rate (sur échantillon) + typologie d’erreurs (hallucination, mauvais fuel/statut, double comptage). 
* **Outputs** : tables de réconciliation + tableaux de synthèse + artefacts reproductibles (CSV/Parquet + rapport).

Ce que ça vous donne

* Vous pouvez comparer proprement : génération directe vs multi-turn vs RAG vs agentique, et mesurer le trade-off coverage/precision que vous avez déjà observé. 
* C’est la voie la plus “science expérimentale” : stable, CI-friendly, portable.

Technos suggérées (Python)

* `pydantic`, `pandas`, `rapidfuzz`, `duckdb` (ou sqlite) ; packaging `uv`, qualité `ruff`.
* Un runner type `invoke`/`typer` + GitHub Actions pour rejouer les expériences.

## Approche 2 — “Agentique instrumenté” (benchmark = évaluer un processus, pas juste une table)

Idée : vous ne benchmarkez pas seulement le résultat final, mais **la chaîne de production** (découverte de sources → extraction → résolution d’entités → consolidation → table), avec logs et états inspectables.

Briques à coder

* **Interface Agent** (contrat) : `run(task, state) -> {table, evidence_graph, logs}`.
* **State store** (persistant) : tout ce que l’agent “sait” (entités déjà vues, hypothèses, conflits, décisions).
* **Trace/provenance obligatoire** : chaque cellule de table doit pointer vers un ou plusieurs “supports” (quote + doc_id + date + score confiance). 
* **Nouvelles métriques de benchmark** (en plus de precision/recall) :

  * **provenance completeness** : % de cellules sourcées,
  * **conflict handling** : capacité à conserver versions contradictoires (temporellement datées) sans écraser,
  * **update ability** : après ajout d’un document plus récent, mesure de la révision correcte (diff attendu).
* **Test d’“auditabilité”** : rejouer l’agent sur le même corpus => mêmes sorties (ou variance explicitée).

Ce que ça vous donne

* Vous testez exactement ce que vous proposez dans votre architecture “stateful, agentic, graph-based” : accumulation, révision, cohérence temporelle, validation humaine tôt dans le pipeline. 

Technos suggérées

* Stockage : SQLite/DuckDB au début, puis éventuellement graph (Neo4j / RDF / TypeDB) si utile.
* “Evidence graph” minimal : nodes = (doc, claim, entity, attribute, time), edges = “supports/contradicts/updates”.

## Approche 3 — “Benchmark par scénarios de corpus” (document-driven, avec tests d’update et de dérive)

Idée : vous fabriquez un **mini-monde contrôlé** de documents (ou un corpus réel figé), et vous évaluez l’agent sur des scénarios : ajout d’un plan révisé, retrait d’un projet, changement de COD, renommage, etc. C’est idéal pour tester la mise à jour et la cohérence temporelle.

Briques à coder

* **Corpus packagé** (versionné) :

  * `corpus/v1/` (baseline),
  * `corpus/v2/` (+ nouveaux docs),
  * `corpus/v3/` (docs contradictoires, corrections).
* **Truth au fil du temps** : référence `gold_v1`, `gold_v2`, `gold_v3` (pas une seule “vérité”).
* **Runner de scénarios** :

  * exécute l’agent sur v1 → score,
  * puis “ingère delta” v2 → score d’update,
  * puis v3 → score de résolution de conflits.
* **Métriques dédiées update** :

  * exactitude des deltas (changements attendus vs observés),
  * stabilité des invariants (ce qui ne devait pas bouger ne bouge pas),
  * coût (tokens/temps) par amélioration de coverage.

Ce que ça vous donne

* Un benchmark qui répond directement à votre exigence “statistiques = objet accumulatif et révisable” plutôt que génération one-shot. 
* Une façon très convaincante de montrer pourquoi les systèmes stateless (RAG QA) plafonnent sur la maintenance de tables. 

Si vous voulez choisir vite

* Vous voulez publier/itérer vite et comparer des systèmes hétérogènes : **Approche 1**.
* Vous voulez tester “agentique + mémoire + provenance” comme contribution centrale : **Approche 2**.
* Vous voulez démontrer la supériorité sur la **mise à jour** et la **cohérence temporelle** : **Approche 3** (souvent la plus persuasive en papier).

Si vous me dites quel niveau d’agentique vous visez (simple multi-outils vs graphe + état persistant), je peux vous proposer un squelette de repo (arborescence, modèles Pydantic, format des logs, et un runner de scénarios) directement calé sur vos métriques coverage/precision/justification + temporal update.

