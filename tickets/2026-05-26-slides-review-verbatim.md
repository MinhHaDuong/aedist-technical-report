# Verbatim remarques slides — session 2026-05-26

## Diapo 1 (Titre)
> Titre: revoir en fonction du résultat principal, du take home message, de l'annonce sur le programme
> Mettre Dr. avant Minh
> Remplace second CIRED - CNRS par le multi logo (fallback text = logo CIRED avec les tutelles)

## Diapo 2
> 2. Titre: remplacer Le problème par L'IA peut-elle produire des données qualité recherche ?  ( le supprimer du corps)

## Diapo 3
> 3. Vérifier les chiffres dans les logs.
> Supprimer le prompt de la slide, dire Engineered, 84 lignes
> Ajouter une slide montrant la structure du prompt  prompts/sotal/protocol_07 ... (sections, sous sections ou 1er para).
> Condition: ajouter "Effort de raisonnement par défaut."

> [retour diapo 3] Remonter Conditions au bloc modèle de la slide

## Ticket DÉFERRÉ (hors slides, créé pendant diapo 3)
> TICKET à créer en Deferré: Prompt amélios:
> Ordonner de commencer la réponse exactement par -> | Status | Nom (Tieng Viet) | Nom (EN) | Province | Fuel | Capacity | ... + donner 2 lignes d'exemples.
> Dire d'ajouter un # Caption sous la table avec un modèle à trou "Inventaire historico-prospectif des assets et projets de génération thermique au Vietnam. Table statistique générée le <YYYY-MM-DD> à <HH-MM-SS> par <NOM DU MODELE, VARIANTE> pour Minh Ha-Duong (CIRED-CNRS).
> Puis les # Notes to the table, puis les # Sources

## Diapo 4
> 4. Image alignée à gauche dans la slide, colonne de texte au fer alignée à droite dans la slide marge 2em.
> Titre (hardcodé dans le fichier figure): How do models recall Vietnam's thermal power assets ? Not well.

## Diapo 5
> 5. Remplacer slide 5. Qualité du résultat  par une slide "# Quality dimensions" verbatim du prompt. (2 slides avant on avait seulement montré le plan du prompt). La slide Qualité de la méthode va dans la section Architecture rebaptisée Discussion, juste après Question centrale et avant DIrections Futures qui monte là.

## Diapo 7 (araignées)
> 7. Figure des araignées.
> subplot en bas droite, garder seulement Qwen, supprimer DeepSeek
> titre: Qualité des réponses: ask one shot, reasoning on, websearch off, docs provided none.
>
> - ajouter une slide avec une seule araignée en grand. Celle des 3 Claude. Avec la mention des 5 axes et des 2 critères par axe en français en clair.
>
> - sur le multipanel, on garde seulement le nom des axes pas les critères. Les légendes nom des 3 modèles: sur une colonne, à côté pas en dessous, pour gagner un peu de taille et de lisibilité. Le titre de panel intègre la légende et n'est pas repris Exemple:
> (a) Claude
> -- Haiku 4.5
> -- Sonnet 4.6
> -- Opus 4.6

## Figure Cost vs Accuracy
> Figure suivante, 2 panels cost vs accuracy
> Titre -> Cost vs Accuracy across 5 model familly (no search, one shot, no docs)
> La figure déborde à droite. Translater à gauche, sans réduore la taille,

## Figure suivante (AI industry)
> Figure suivante: remplacer "AI" par "AI industry" dans le titre. Idem précédente, translater à gauche sans réduire

## Diapo 10
> 10. Titre -> Expérience 2: web search on, (oneshot,  multiturn) x (without , with docs)
> Drop la colonne Enjeu et la ligne Facteur, Valeurs
> (3 relances) -> (3 à 5)
> retirer + web search
> Retirer 4 SOTA, remplacer Qwen3-max par Qwen 3.7 max
> Runs -> Répétitions
> Ajouter une ligne Contrôles  Default reasoning effort, Web search allowed, no tools, no code, direct lab API provider, même prompt de base
> Ajouter une ligne: Documents  18 tables, sources primaires, format MD
> Supprimer le tableau arm 1... et la ligne Les 4 agents...
> Au final la slide c'est titre + tableau 2 colonnes, avec la col de droite 1 mot en gras

> [retour diapo 10] Dans les contrôles ajouter < $6, < 50,000 tokens

## Diapo 11
> 11. Supprimer le second  "Infrastructure :"
> Remplacer "Même script, .. hash" par "5 claws: Imagine, Plan, Execute, Verify, Celebrate."
> Supprimer les "/ 4"
> Ajouter "codéveloppé, " avant relu
> Rappeler très brievement les réserves après "fondées: "

## Diapo 12
> 12. Supprimer (Exp 2)
> Phase A. Remplacer "et planifie le job" par "connaissant le protocole". Supprimer ($1)
> Remplacer "Un jury de pairs -- mais le jury est aussi un modèle" par "Évaluattion par les pairs: TBD"

> [discussion inline] remplacer "L'agent conçoit son propre protocole, l'exécute, et un autre LLM l'arbitre" par "It's LLMs all the way down — but Knowledge Graphs are not dead."

## Diapo 16 (remonte)
> Slide 16. elle remonte juste après la slide "Which models recall"  et avant le prompt, titre "La bonne statistique exige plus que des vrais chiffres". Citer "Connaissance: croyance vraie justifiée". Aligner sur les 4 dimensions suivant le manuscrit. Noter la 5e qui est le Niveau de détail approprié. Remplacer "Chaque défaillance a un mécanisme correcteur" par "-> Grille de notation multi-axes"

## Figure Coverage and costs, experiment 2
> Figure One query providing documents..
> Titrer -> Coverage and costs, experiment 2
> Le sous titre est les 4 modalités: "1B = Singleshot, no doc.    5B = Multiturn no doc   1A = Singleshot RAG   5A = Multiturn RAG". Supprimer Matched / Hallucinated
> il faut introduire RAG avant, au moment de la description et dans la timeline industrie
> Il faut introduire les 4 labels avant: à la fin de la slide présenant l'éxperience, on dit: Quatre conditions 1N (single turn, no docs) ; 5N ; 1W ; 5W (multiturn, with docs)
>
> Principe de la figure
> Pour chaque modèle un bar graph avec 4 barres labelisées 1N, 5N, 1W, 5W,
> 4 barres séparées par un petit blanc, avec plus d'espace entre les 4 modèles.
> Hauteur de barre = moyenne des 5 reps. Couleur = celle du modèle dans le talk.
> Variance inter-run montrée: On ajoute par dessus une ligne d'incertitude fine en noir avec les 5 valeurs en petits segments horizontaux sur la ligne.
> Panel de gauche (Coverage): les hallucinations sont uniformément EN ROUGE dans les négatifs, le nombre d assets bien reconnus en couleur du modèle dans les positifs. Même principe que pour la figure "Which model recalls..." de l'exp 1 mais en mode barrre à moustache vertical. Conserver l'axe vertical avec ses ticks de -50 à +150 et la barre verte horizontale. La légende d'axe Y en haut de l'axe, écriture horizontale, "163 plants". Remplacer Coverage par "Number of assets identified (red are False Positive)."
> Panel de droite (Cost). Idem faire un 4 bars plot à moustaches par modèle.  Remplacer Cost par "API Cost per run, USD" et supprimer la légende d'axe y.

> [Et translater à gauche un peu sans réduire. Toutes les figures, ca doit Être un bug. Suspect: positionné centré  dans le form factor plus wide que le rendu final, puis clipé]

## Figure Coverage vs Corroboration
> Figure Coverage vs. Corroboration (out of 163 assets).
> Titrer : How many rows are justified by two sources ?
> Sous titre = la légende glyph style sur une ligne, sans nommer les arm mais 1N, 5N, 1W, 5W .
> Dans TOUT ce qui précède, remplacer le W de 1W et 5W par le D de documents -> 1D, 5D.
> Declutter: Mettre les 5 run en alpha faible (quasi invisible), et les seulement moyennes en alpha normal
> Debug: 175+ c

> [175+ c'est pas possible. Cohérence avec la figure precédente, on montre les assets correctly identified.
> On place aussi les hallucitaions, en ROUGE (sans dénoncer personne): on verra sont elles justifiées quand même?]

## Diapos 17-18
> 17, 18: la fonction de ces slides est de vérifier de façon plus quanti  les messages clé qu'on a vu sur les graphes et qu'on va rabacher en conclusion sur la suivante. Sans aller jusqu au p-values.

## Diapo 19
> 19: Reformuler, réordonner
> 1. Multi-tour: pas si utile
> 2. Fournir les sources: nécessaire
> 3. Coût: de quelques centimes à quelques euros par requête
> 4. L'IA produit elle des données de qualité recherche: pas encore

## Diapo Merci
> Merci: lien cliquable  ctif dans le PDF, + code barre vers le repo (en gros).

## Contenu verbatim diapo Quality dimensions (fourni en session)
Source : `experiments/sota/protocol_07_naive_prompt.md` lignes 15-26

> # QUALITY DIMENSIONS
>
> Your output is judged on four axes:
>
> 1. *Accuracy* — right assets and right attributes. Row level: recall and precision against a curated reference (F1). Cell level: capacity, fuel, location, operator, COD, status correct. Confident fabrication is the policed failure mode.
> 2. *Coherence* — internally and externally consistent. Totals reconcile with known subtotals; no negative capacities, no double-counted units, no cross-row contradiction; values plausible in unit, magnitude, geography, technology, date. Conflicting sources reconciled explicitly (which chosen and why), not silently.
> 3. *Provenance* — each value traces to a source that actually supports it, not a merely plausible citation. Two independent primaries is the ideal; one primary, a regulator database, or a marked secondary is weaker but acceptable if its status is explicit. Unsupported values are the failure.
> 4. *Temporality* — every value carries a best-effort as-of date; status changes are flagged. Distinguish current status from past reports, planned from operating capacity, source date from fact date.
>
> We prefer a comprehensive inventory with uncertainty clearly expressed over a shortlist of well-known assets.

## Corrections globales
> Dans TOUT ce qui précède, remplacer 1W → 1D et 5W → 5D (W → D pour « documents »)
> Bug toutes figures : décalage à droite — fix systémique suspicion canvas trop large puis clippé
