# Panel de révision slides Econom'IA 2026 — état sauvegardé

Session : 2026-05-26
Tour : 1 (synthèse prête, 2e tour à venir)

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
