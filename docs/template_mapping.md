# Contrat des six références et des cinq sorties Word

Les six fichiers de `resources/templates/originals/` restent intacts. Les cinq sorties utilisent les modèles de `resources/templates/runtime/`; `pv_division.docx` assemble PV Division 1 puis PV Division 2. La génération part toujours d’une copie du modèle correspondant.

Les champs `Conservation foncière`, `Préfecture` et `Commune` sont indépendants. Le client (nom, CNIE, adresse, qualité et expiration) alimente PV Division et le Règlement. Les quatre limites alimentent le Règlement. Les niveaux narratifs sont clonés d’après les niveaux réellement saisis; aucun bloc Terrasse n’est conservé si le niveau n’existe pas.

Les cotes sont rendues avec signe et deux décimales françaises (`-2,20`, `+0,40`). Les listes utilisent la grammaire française déterministe : `de la cote … à la cote …`, `de la cote … aux cotes …`, `des cotes … à la cote …` ou `des cotes … aux cotes …`. Une hauteur conserve la formulation historique; plusieurs hauteurs sont écrites sous la forme `de hauteurs intérieures de 2,90 m et 5,50 m`. Tableau A et Tableau B partagent une séquence globale `Nom propriété-N` limitée aux parties privatives.

## Inventaire de référence

| Modèle runtime | SHA-256 | Sections | Paragraphes | Tables | Styles |
|---|---|---:|---:|---:|---:|
| `pv_division.docx` | `c91738debbbfca917af98fde753347523cb23239aa371cf61926795ef80f0a31` | 3 | 54 | 7 | 91 |
| `pv_division_1.docx` | `0625a091c2454d1eeecff8a4b67bee78c060e99af2ca063963eeb5f1bcfbb137` | 1 | 34 | 0 | 23 |
| `pv_division_2.docx` | `c2543644b86cecdae98386ba5ee0d1acc4be73f1fe7529081a61783818ee969e` | 2 | 19 | 7 | 91 |
| `reglement.docx` | `fa822bc01e65d895558eeaff50bf93513baf8fd341353428314fcb8e85059494` | 4 | 327 | 13 | 102 |
| `tableau_a.docx` | `07c1843017ad2f2a2ba2f0c3d5831c4e0562d3a68b29f49478a0e5e0ea165cb2` | 1 | 7 | 1 | 23 |
| `tableau_b.docx` | `3e129da3bac2352fd9d2c831de709d36039226f95ade034cbc32d8dd3a149cc3` | 1 | 5 | 1 | 23 |
| `tableau_recapitulatif.docx` | `af4c35eb780838aeb809eb0de647bb79b06c284b38238df592abfbf79bdacfef` | 1 | 58 | 4 | 8 |

Le renderer canonique ne trouve pas LibreOffice sur cette station. La vérification locale utilise donc Microsoft Word en mode invisible pour exporter les DOCX en PDF, puis rasterise les PDF en PNG. Pour le cas réel EX 3, les cinq sorties totalisent 27 pages inspectées : PV Division 4, Règlement 15, Tableau A 2, Tableau B 4 et Tableau récapitulatif 2. Les contrôles structurels OOXML et la suite automatisée restent obligatoires; le visa métier/juridique humain reste requis avant livraison officielle.

## Géométrie observée

Tous les modèles sont A4 portrait (8,27 × 11,69 pouces). Marges principales : PV1 `0,30/0,29/0,39/0,49`, PV2 deux sections, règlement quatre sections, Tableau A `0,79/0,59/0,50/0,67`, Tableau B `0,59/0,79/0,67/0,50`, récapitulatif `0,79/0,79/0,50/0,50` (gauche/droite/haut/bas, pouces). Les sections, entêtes, pieds, liens entre sections, styles et dimensions de colonnes sont conservés par copie et clonage des lignes sources.

## Emplacements modifiables

| Document | Emplacements alimentés |
|---|---|
| PV Division | PV Division 1 puis PV Division 2; identité, titre, situation, conservation, topographe, client, date/heure, consistance, nombre de parties et un bloc narratif cloné par niveau réel |
| Règlement | Identité ciblée; descriptions de niveaux/parties; table 9 de répartition; table 12 des voix |
| Tableau A | Table 0 : une ligne clonée par partie privative |
| Tableau B | Table 0 : bandeau de niveau, parties privatives/communes et total par niveau |
| Tableau récapitulatif | Table 1 : ventilation habitation/cour/balcon/terrasse/garage; table 3 : agrégats par consistance |

Les textes détaillés proviennent de `Part.description`, saisis par l’utilisateur. Le programme ne complète pas des pièces, équipements ou clauses absentes.

## Motifs répétables

Les lignes ne sont pas créées avec le style Word par défaut. Chaque type clone sa ligne source : privative, commune, total, bandeau de niveau, total général ou voix. Les cellules fusionnées, propriétés de paragraphes, runs, bordures et largeurs du modèle servent de prototypes.

## Préservation obligatoire

- aucun original n’est modifié ;
- section count, page geometry, styles, numérotation, entêtes, pieds et relations non ciblées restent présents ;
- les articles juridiques non variables restent identiques; l’Article 1 du règlement est comparé au modèle par test ;
- aucune génération n’est déplacée vers la sortie si un DOCX est invalide ou si une valeur critique manque ;
- les cinq sorties utilisent le même instantané projet et les mêmes empreintes de modèles.

## Gates Yasmin 71

- Tableau B : 25 lignes ; règlement table 9 : 27 lignes ; voix : 5 lignes ;
- récapitulatif : habitation `56`, cour `16`, garage `15`, étages `76 + 4`, total habitation `232` ;
- surfaces privatives `87 / 80 / 80`, total `247` ; surfaces dans titre `225` ;
- tantièmes `3522 / 3239 / 3239`, total `10 000` ;
- structures et valeurs couvertes par pytest ;
- gate automatisé satisfait : structure OOXML, valeurs critiques et rendu PNG page par page ;
- dernier gate restant : validation métier et juridique humaine des cinq sorties.
