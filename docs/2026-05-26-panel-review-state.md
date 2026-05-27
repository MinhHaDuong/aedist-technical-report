# Panel de révision slides Econom'IA 2026 — état sauvegardé

Session : 2026-05-26 (tour 1) — 2026-05-27 (tour 2)
Tour : 2 terminé (slides livrées relues — triage showstoppers avant talk du soir)

## Experts et IDs agents (pour reprise via SendMessage)

| Expert | Rôle | Agent ID |
|--------|------|----------|
| Dr. Sophie Lefèbvre | Verbatim/HCI — fidélité ticket ↔ intention | `a76c1cbbbfa8ddc0c` |
| Pr. Antoine Maurel | Contenu scientifique — cohérence des claims | `a2a24ca7289ae29e6` |
| Dr. Isabelle Charpentier | Communication/narration — structure du talk | `acdcfa91bf043e7f2` |
| Dr. Lucas Moreau | Dataviz/Figures — faisabilité technique | `a7d0982c459574736` |

**Note de validité :** Les agent IDs sont valables tant que la session harness les retient. Si la reprise échoue, relancer 4 nouveaux agents avec les mêmes prompts (sauvegardés dans le commit de cette session, voir PR #573).

## Matériel de référence
- Slides source : `slides/slides.tex`
- Verbatim session : `tickets/2026-05-26-slides-review-verbatim.md`
- Tickets : `tickets/0324-*.erg` à `tickets/0343-*.erg`

## Commentaires bruts (Tour 1)

### Sophie Lefèbvre — 12 commentaires (Verbatim/HCI)
- **C-1** : T-0324 exit criterion "Dr. Minh" → doit être "Dr. Minh Ha-Duong" *(corrigé)*
- **C-2** : T-0324 titre — 1 critère retenu sur 3 (manque résultat principal + take-home) *(corrigé)*
- **C-3** : T-0325 "au fer alignée à droite" perdu → préciser `\raggedleft` *(corrigé)*
- **C-4** : T-0335 "sans réduire" absent + T-0330 ne mentionne pas la contrainte dimensionnelle
- **C-5** : T-0329 sur-spécification (verbatim avait "ou" = choix ouvert)
- **C-6** : T-0332 sur-spécification de la représentation de variance *(précisée)*
- **C-7** : T-0327 réserves diapo 11 non spécifiées → tâche ouverte non solvable *(résolu via Q-1)*
- **C-8** : NOUVEAU ticket manquant — sweep global 1W/5W → 1D/5D *(créé 0337)*
- **C-9** : T-0326 liste des 4 dimensions figée sans instruction "vérifier dans le manuscrit"
- **C-10** : NOUVEAU ticket manquant — séquence finale des slides *(créé 0341)*
- **C-11** : T-0328 suppression silencieuse de "Anthropic trop cher" sans note *(résolu via Q-2)*
- **C-12** : T-0330 fix appliqué avant confirmation du diagnostic *(corrigé)*

### Antoine Maurel — 10 commentaires (Contenu scientifique)
- **AM-1** : T-0326 déplacement "Qualité de la méthode" brise le fil cause→résultat
- **AM-2** : T-0326+T-0329 incohérence 4 dimensions vs 5e dimension *(résolu via Q-3 : Fit for purpose post-hoc)*
- **AM-3** : T-0329 Quality dimensions en anglais sans cadrage "voici ce qu'on a demandé" *(décision auteur Q-4 : verbatim brut)*
- **AM-4** : T-0328 réordonnancement affaiblit "RAG FTW" comme message central
- **AM-5** : T-0332 convention FP en rouge sous zéro non explicitée pour économistes
- **AM-6** : T-0333 175+ = erreur données, pas bug affichage — investigation requise *(créé 0336)*
- **AM-7** : T-0327 "5 claws" remplace garantie méthodologique (reproductibilité hash) *(corrigé)*
- **AM-8** : T-0331 suppression DeepSeek sans justification documentée
- **AM-9** : NOUVEAU ticket — unification métrique (F1 vs count vs coverage) Exp1↔Exp2 *(créé 0343)*
- **AM-10** : NOUVEAU ticket — justification sélection 4 modèles SOTA pour Exp2 *(créé 0342)*

### Isabelle Charpentier — 10 commentaires (Communication/narration)
- **IC-1** : Quality dimensions en anglais → fracture linguistique sans préparation *(décision auteur : verbatim brut)*
- **IC-2** : Déplacement "Qualité de la méthode" brise cause→résultat pour public non-IA
- **IC-3** : Diapo 16 remonte tôt — callback "Beyond RAG" nécessaire plus loin
- **IC-4** : NOUVEAU ticket — définir RAG pour public économiste *(créé 0340)*
- **IC-5** : "KG" dans punchline non décodable pour économistes francophones *(résolu Q-5 : développer)*
- **IC-6** : Message 4 "pas encore" = conclusion, doit être distingué visuellement
- **IC-7** : Section "Discussion" nécessite phrase-parapluie d'entrée
- **IC-8** : NOUVEAU ticket — transition slide Exp1→Exp2 *(créé 0339)*
- **IC-9** : Slide structure prompt trop technique pour économistes → diagramme préférable
- **IC-10** : Tension "Beyond RAG" (titre) vs "pas encore" (conclusion) à assumer explicitement

### Lucas Moreau — 11 commentaires (Dataviz/Figures)
- **LM-1** : BLOQUANT T-0330 diagnostic incomplet — cause = ratio figsize 16:9, pas centrage *(corrigé)*
- **LM-2** : T-0330 pas de test automatique de ratio d'aspect
- **LM-3** : T-0331 "colonne à côté" ambigu pour plot polaire *(corrigé : par-subplot)*
- **LM-4** : T-0331 labels français non ancrés (hardcodé Python, pas de config YAML) *(corrigé)*
- **LM-5** : T-0332 "couleur du modèle" ne cite pas `model_family_color()` explicitement *(corrigé)*
- **LM-6** : BLOQUANT T-0332 n_matched absent → barres rouges impossibles *(créé 0336)*
- **LM-7** : BLOQUANT T-0333 n_rows ≠ n_matched → 175+ est erreur sémantique *(créé 0336)*
- **LM-8** : BLOQUANT T-0333 hallucinations sur scatter non définies formellement *(corrigé)*
- **LM-9** : T-0332 style variance non standard sans dimensions *(corrigé)*
- **LM-10** : T-0335 à absorber dans T-0330 pour éviter conflit merge *(note ajoutée)*
- **LM-11** : NOUVEAU ticket — constantes `SLIDE_FIGSIZE_WIDE/HALF` dans util.py *(créé 0338)*

## Synthèse (Tour 1)

### Bloquants (3)
- **B-1** : Données manquantes Exp2 (n_matched pour FP) → bloque 0332 et 0333 *(créé 0336)*
- **B-2** : Bug décalage = ratio figsize, pas centrage → 0330 précisé
- **B-3** : Ordre final slides non coordonné T-0326+T-0329 → créé 0341

### Corrections sur tickets existants (9 items appliqués)
Voir corrections marquées *(corrigé)* ci-dessus.

### Nouveaux tickets (8 créés)
- 0336 : data n_matched investigation (bloqueur)
- 0337 : sweep 1W/5W → 1D/5D global
- 0338 : figsize constants util.py
- 0339 : slide transition Exp1→Exp2
- 0340 : définir RAG pour économistes
- 0341 : séquence finale slides
- 0342 : justification sélection modèles Exp2
- 0343 : unification métrique

### Questions auteur (5/5 résolues)
- **Q-1** : Réserves diapo 11 → sourcées Doc 06 + round 2 reviews
- **Q-2** : « Anthropic trop cher » → suppression intentionnelle (discuté sur figure, prix non stable)
- **Q-3** : 5e dimension → « Fit for purpose », opérationnelle, exemple PyPSA
- **Q-4** : Quality dimensions slide → verbatim brut, pas de chapeau français
- **Q-5** : « KG » → développer en « Knowledge Graphs »

## Pour le 2e tour

**Objectif** : soumettre la synthèse aux 4 agents pour validation et nouveaux commentaires sur les corrections appliquées.

**Méthode** :
1. Réutiliser les agent IDs via `SendMessage(to: <id>, content: <synthèse + tickets mis à jour>)`
2. Si les IDs sont expirés, relancer 4 nouveaux agents avec les mêmes prompts (sauvegardés dans le commit)
3. Demander à chaque expert : (a) valider sa propre liste après corrections, (b) examiner les nouveaux tickets, (c) signaler les nouveaux écarts

**Items à valider en priorité** :
- T-0330 fix figsize ratio (LM-1)
- T-0336 data investigation (B-1, AM-6, LM-6/7/8)
- T-0341 séquence finale (B-3, C-10)
- Questions auteur Q-3, Q-4, Q-5 satisfont-elles les experts ?

**Items non-traités du tour 1 à reprendre** :
- C-4 « sans réduire » dans 0330/0335
- C-9 vérification 4 dimensions dans manuscrit
- AM-1, IC-2 déplacement Qualité méthode — décision à valider
- AM-4 affaiblissement "RAG FTW"
- AM-5 convention FP en rouge à expliciter
- AM-8 justification suppression DeepSeek
- IC-3 callback "Beyond RAG"
- IC-6 distinction visuelle message 4
- IC-7 phrase-parapluie section Discussion
- IC-9 diapo structure prompt trop technique
- IC-10 tension "Beyond RAG" vs "pas encore"
- LM-2 test automatique ratio aspect

---

# Tour 2 — 2026-05-27 (relecture des slides LIVRÉES, triage showstoppers)

**Contexte** : le tour 1 a été exécuté (tickets 0324-0343 fermés, slides effectivement modifiées). Le tour 2 relit `slides.tex` livré + figures régénérées, avec pour mission de prioriser ce qui DOIT être corrigé avant le talk du soir (Econom'IA 2026, 27 mai).

## Experts et IDs agents — Tour 2 (pour reprise via SendMessage)

| Expert | Rôle | Agent ID (tour 2) |
|--------|------|-------------------|
| Dr. Sophie Lefèbvre | Verbatim/HCI — fidélité intention ↔ livraison | `a215a9bc10ae22e31` |
| Pr. Antoine Maurel | Contenu scientifique — cohérence des claims | `ac0042adc8fc4fb3d` |
| Dr. Isabelle Charpentier | Communication/narration — structure du talk | `a8e5b6302d62f16d8` |
| Dr. Lucas Moreau | Dataviz/Figures — lisibilité & justesse | `ae6da8abafe51c5c6` |

## Commentaires bruts (Tour 2)

### Sophie Lefèbvre (Verbatim/HCI)
- **SHOWSTOPPER** : slide « deux modes » (`slides.tex:129-156`) — données non corroborées (Haiku « 15 centrales sur 5 runs », GPT OSS « récursion Trung Nam 1..83 ») introuvables dans report/logs, et slide absente du verbatim → vérifier ou retirer.
- **SHOWSTOPPER** : spider Claude (`fig_spider_exp1_claude`) — verbatim demandait les 3 Claude superposés (Haiku+Sonnet+Opus) ; livré = Opus seul → régénérer en overlay ou assumer.
- **SHOWSTOPPER (C-9)** : taxonomie des dimensions incohérente sur 3 supports — 4 axes prompt (Accuracy/Coherence/Provenance/Temporality) ≠ corps `:227` (…/Adéquation) ≠ annexe `:470` + spider (…/Contenu) ; province/fuel/status mal classés dans le spider.
- **MAJEUR** : msg-clé `:436` « aide certains modèles » vs verbatim dicté « nécessaire » — affaiblissement (cf. AM-4).
- **MAJEUR** : DAG Makefile cassé — `fig_spider_exp1_claude`, `fig_spider_exp1_families`, `fig_exp2_coverage`, `fig_exp2_cost` prérequis de `slides.pdf` sans recette (scripts `plot_quality_spider_exp1.py`, `plot_exp2_arms_split.py` jamais invoqués). Compile car PDF sur disque ; viole l'invariant DAG. Post-talk.
- **MAJEUR (C-4)** : slides Cost Exp1 (« sans réduire ») absentes de `slides.tex` — confirmer suppression intentionnelle.
- **MINEUR** : multipanel familles conforme (pas de DeepSeek) ; overlay « Récalcitrant » barré = sur-interprétation cohérente.

### Antoine Maurel (Contenu scientifique)
- **SHOWSTOPPER** : annexe grille 5 axes (`:470`) ≠ frame principale 5 axes (`:227`) — « Contenu » vs « Adéquation ».
- **SHOWSTOPPER** : asymétrie 4 axes demandés au modèle / 5 axes notés non signalée (`:238`) — ajouter « 5e mesuré post-hoc » (Q-3).
- **SHOWSTOPPER** : tension titre « Beyond RAG » / msg 2 « RAG dominant » / clôture « pas encore vérifié » non assumée.
- **SHOWSTOPPER** : msg-clé 1 « Multi-tour inutile » (`:433`) trop fort — contredit par son sous-titre et la donnée (1/4 modèles s'améliore, −0.078 F1).
- **MAJEUR (AM-8)** : absence DeepSeek non explicitée (juge non évalué, légitime mais à dire sur la frame design).
- **MAJEUR (AM-5)** : convention FP rouge sous zéro sans clé de lecture textuelle avant les figures.
- **MAJEUR (AM-1/AM-4)** : ordre cause→résultat dilue « RAG FTW » ; formulation « la méthode domine le modèle » plus faible que « RAG = intervention dominante ».
- **MINEUR** : `:99` `$>30 MWe$` sans `\,` ; `:106` borne 20 min en dur vs macro. Chiffres Exp1 (163, plages, 6.21$) cohérents avec `macros_p1_base`.

### Isabelle Charpentier (Communication/narration)
- **SHOWSTOPPER (IC-10)** : tension « Beyond RAG » vs « pas encore vérifié » non assumée → verdict confus ; ajouter une ligne-pont en conclusion.
- **SHOWSTOPPER (IC-4/0340)** : RAG jamais défini avant 1er emploi (timeline `:274`, design `:285`) ; ticket 0340 marqué créé mais définition absente du `.tex`.
- **SHOWSTOPPER** : « LP » et « faux positif » (`:388`) non glosés pour économistes.
- **SHOWSTOPPER (IC-7)** : section Discussion ouvre sur « Limites » sans phrase-parapluie → sape la crédibilité.
- **MAJEUR (IC-6)** : message 4 « pas encore » noyé dans la liste numérotée → le sortir en pleine page.
- **MAJEUR (IC-3)** : pas de callback « Beyond RAG » sur « Directions futures ».
- **MAJEUR (IC-9)** : slide structure prompt épurée mais toujours 3 colonnes de texte (diagramme préférable) — acceptable faute de temps.
- **MINEUR** : titre design Exp2 franglais ; punchline « turtles all the way down » non décodable FR ; citation d'ouverture EN ; titres-slides à 3 phrases.

### Lucas Moreau (Dataviz/Figures)
- **État bloquants 0336 (LM-6/7/8) : RÉSOLUS** — plus de « 175+ » (certainty plafonne ~130) ; FP/hallucinations bien en rouge dans les négatifs ; « 163 plants » cohérent. Conversion 1W/5W→1D/5D complète (aucun résidu).
- **SHOWSTOPPER** : `fig_spider_cross_exp` — collision massive titres/axes/groupes (5 panneaux, canvas trop petit) → agrandir layout.
- **SHOWSTOPPER** : `fig_spider_exp1_families` — labels d'axe ↔ labels de groupe gras se chevauchent → réduire/dégager.
- **SHOWSTOPPER** : `fig_direct_p1_base` — ticks X négatifs sans signe (« 50 » au lieu de « −50 ») → hallucinations lues comme actifs ; formatter signé.
- **MAJEUR** : `fig_exp2_coverage` — même bug ticks Y bas non signés (zone FP rouge).
- **MAJEUR** : `fig_direct_cost_quality` — split « Western / Asian labs » hors-spec, sémantiquement risqué (Mistral=FR « Western ») → faire valider/retirer.
- **MAJEUR (LM-2)** : garde ratio d'aspect incomplète — `plot_method_convergence.py` (génère `fig_direct_p1_base`) hors de `SLIDE_BOUND_PLOT_SCRIPTS` (sûr car height-driven, mais non protégé). Post-talk.
- **MINEUR** : timeline « 2022-2025 » vs axe jusqu'2026 ; légende cross_exp basse risque coupe ; alpha runs certainty.

## Synthèse consolidée (Tour 2) — showstoppers triés

| # | Showstopper | Experts | Effort | Décision auteur ? |
|---|-------------|---------|--------|-------------------|
| SS-A | Slide « deux modes » : données non corroborées (`:129-156`) | Verbatim | court (vérif) / triv (retrait) | oui |
| SS-B | Taxonomie qualité incohérente (4/5/5, mal classée) corps+annexe+spider | Contenu + Verbatim | court + régén spider | non |
| SS-C | Spider Claude = Opus seul vs 3 Claude demandés | Verbatim | court (régén) | oui |
| SS-D | Tension « Beyond RAG » vs « pas encore vérifié » | Contenu + Narration | court | non |
| SS-E | Araignées illisibles projetées (cross_exp, families) | Dataviz | court→long (régén) | non |
| SS-F | Ticks d'axe négatifs sans signe (p1_base, coverage) | Dataviz + Contenu | triv→court (régén) | non |

**Majeurs (si temps)** : SS-G gloses RAG/LP/faux positif (Narration+Contenu) ; SS-H « Multi-tour inutile » trop fort (Contenu) ; SS-I parapluie section Discussion (Narration) ; message 4 hors liste numérotée (Narration).

**Post-talk (pas un risque ce soir)** : DAG Makefile — 4 figures de slides sans recette (Verbatim) ; LM-2 garde ratio incomplète (`plot_method_convergence.py`).

**Convergence positive** : bloquants données 0336 résolus, 1W/5W→1D/5D complet, chiffres Exp1 internes-cohérents, 8 figures présentes (build 06:15).

## Arbitrages auteur en attente (5)
1. **SS-A** : après vérif logs, garder ou retirer la slide « deux modes » ?
2. **SS-C** : araignée 3-Claude (régénérer overlay) ou Opus seul assumé ?
3. **Msg « Fournir les sources »** : « nécessaire » (verbatim) vs « aide certains modèles » (livré) ?
4. **C-4** : suppression des 2 slides Cost Exp1 intentionnelle ?
5. **Cost vs Accuracy** : cadrage « Western / Asian labs » assumé ?

## Items tour 1 — statut après tour 2
- **C-4** : ouvert (slides Cost Exp1 absentes — arbitrage 4).
- **C-9** : confirmé SHOWSTOPPER (SS-B), étendu au spider.
- **AM-1/IC-2** : fil cause→résultat tient globalement ; « RAG FTW » dilué (majeur AM-4).
- **AM-5** : partiel (3 causes FP définies `:388`) ; convention visuelle rouge toujours non annoncée.
- **AM-8** : juge non évalué confirmé légitime ; à expliciter sur la frame design.
- **IC-3, IC-6, IC-7, IC-10** : toujours ouverts (non matérialisés dans le `.tex` livré).
- **IC-9** : partiel (épuré, pas diagrammé) — acceptable faute de temps.
- **LM-2** : partiel (test existe, ne couvre pas `plot_method_convergence.py`).
