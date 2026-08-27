# Protocole de validation sur trois dossiers réels

Ce protocole transforme l'essai terrain restant en une validation reproductible. Il doit être exécuté sur trois copropriétés différentes, avec des copies de travail autorisées et anonymisées lorsque c'est possible.

## Échantillon minimal

1. un dossier simple saisi entièrement à la main ;
2. un dossier avec DXF ou DWG et comparaison manuel/CAD ;
3. un dossier comportant une particularité de surface, plusieurs niveaux ou davantage de lots.

Ne pas utiliser Yasmin 71 comme l'un des trois dossiers : il sert déjà de référence technique.

## Procédure par dossier

1. Archiver les six documents de référence, le dessin éventuel et le résultat calculé manuellement par le topographe. Les deux références PV produisent un seul fichier livré.
2. Saisir le dossier sans modifier les modèles Word.
3. Importer le dessin lorsqu'il existe, résoudre chaque divergence et enregistrer la source retenue.
4. Vérifier avant génération : surfaces, somme des surfaces, tantièmes entiers, total 10 000 et total 100,00 %.
5. Pour un niveau possédant plusieurs cotes, saisir les listes avec ` ; `, enregistrer le JSON, le rouvrir et vérifier que toutes les valeurs et leur ordre sont conservés. Vérifier aussi qu’un ancien projet v1-v3 à valeurs scalaires s’ouvre puis s’enregistre en v4 sans perte.
6. Pour un dessin CAD à plusieurs cotes, vérifier que la revue affiche toutes les valeurs avec ` ; `, que les hauteurs calculées correspondent aux différences de cotes et que la confiance ne devient élevée qu’en présence des mêmes valeurs dans la coupe verticale rattachée au niveau.
7. Générer les cinq DOCX dans un dossier vide.
8. Faire relire chaque document par le topographe : identité foncière, surfaces, lots, tantièmes, texte juridique, tableaux, pagination et signatures.
9. Comparer au dossier produit manuellement et classifier chaque écart : erreur produit, donnée source, choix métier ou différence de présentation acceptable.
10. Corriger le produit et rejouer les trois dossiers après toute correction commune.

## Mesures à consigner

| Mesure | Critère d'acceptation |
|---|---|
| Somme des tantièmes | exactement 10 000 pour chaque dossier |
| Somme des pourcentages | exactement 100,00 % à l'affichage |
| Valeurs critiques erronées | 0 après résolution des données source |
| Documents produits | 5 sur 5, sans fichier partiel |
| Cotes et hauteurs multiples | toutes les valeurs et leur ordre sont conservés après sauvegarde/réouverture |
| Migration JSON v1-v3 | ouverture puis sauvegarde v4 sans perte de niveau, partie ou identifiant |
| EX 1 — Sous-sol | débuts `-2,20`; fins `-0,20 ; +0,40`; hauteurs `2,00 ; 2,60` |
| EX 1 — Rez-de-chaussée | débuts `+0,00 ; +0,60`; fin `+3,60`; hauteurs `3,60 ; 3,00` |
| EX 3 — Rez-de-chaussée | début `+0,20`; fins `+3,10 ; +5,70`; hauteurs `2,90 ; 5,50` |
| Texte juridique non ciblé modifié | 0 modification |
| Défaut visuel bloquant | 0 après correction |
| Temps opérateur | mesuré pour le manuel et pour Copro Auto |
| Reprise manuelle après génération | liste et durée mesurées |

## Fiche de résultat

Pour chaque dossier, consigner : identifiant anonymisé, date, version de l'application, poste Windows, version AutoCAD, mode de saisie, nombre de lots, durée manuelle, durée Copro Auto, écarts trouvés, corrections apportées, nom et visa du réviseur métier.

La validation terrain est terminée seulement lorsque les trois fiches sont signées par le réviseur métier et qu'aucune anomalie bloquante n'est ouverte.
