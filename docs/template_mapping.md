# Contrat des six modèles Word

Les fichiers de `resources/templates/originals/` sont intacts. Les six DOCX de `resources/templates/runtime/` sont les autorités de génération. La génération part toujours d’une copie du modèle correspondant.

## Inventaire de référence

| Modèle runtime | SHA-256 | Sections | Paragraphes | Tables | Styles |
|---|---|---:|---:|---:|---:|
| `pv_division_1.docx` | `0625a091c2454d1eeecff8a4b67bee78c060e99af2ca063963eeb5f1bcfbb137` | 1 | 34 | 0 | 23 |
| `pv_division_2.docx` | `c2543644b86cecdae98386ba5ee0d1acc4be73f1fe7529081a61783818ee969e` | 2 | 19 | 7 | 91 |
| `reglement.docx` | `fa822bc01e65d895558eeaff50bf93513baf8fd341353428314fcb8e85059494` | 4 | 327 | 13 | 102 |
| `tableau_a.docx` | `07c1843017ad2f2a2ba2f0c3d5831c4e0562d3a68b29f49478a0e5e0ea165cb2` | 1 | 7 | 1 | 23 |
| `tableau_b.docx` | `3e129da3bac2352fd9d2c831de709d36039226f95ade034cbc32d8dd3a149cc3` | 1 | 5 | 1 | 23 |
| `tableau_recapitulatif.docx` | `af4c35eb780838aeb809eb0de647bb79b06c284b38238df592abfbf79bdacfef` | 1 | 58 | 4 | 8 |

Le nombre de pages rendu reste non résolu dans cette station : le renderer canonique ne trouve pas LibreOffice et l’automatisation Word est bloquée tant qu’une session Word utilisateur est ouverte. C’est un gate de livraison commerciale, pas une donnée inventée.

## Géométrie observée

Tous les modèles sont A4 portrait (8,27 × 11,69 pouces). Marges principales : PV1 `0,30/0,29/0,39/0,49`, PV2 deux sections, règlement quatre sections, Tableau A `0,79/0,59/0,50/0,67`, Tableau B `0,59/0,79/0,67/0,50`, récapitulatif `0,79/0,79/0,50/0,50` (gauche/droite/haut/bas, pouces). Les sections, entêtes, pieds, liens entre sections, styles et dimensions de colonnes sont conservés par copie et clonage des lignes sources.

## Emplacements modifiables

| Document | Emplacements alimentés |
|---|---|
| PV Division 1 | Identité, titre, situation, topographe et date par remplacement ciblé |
| PV Division 2 | Paragraphe de consistance générale, nombre de parties uniques, descriptions de niveaux et lignes narratives clonées par partie |
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
- les six fichiers utilisent le même instantané projet et les mêmes empreintes de modèles.

## Gates Yasmin 71

- Tableau B : 25 lignes ; règlement table 9 : 27 lignes ; voix : 5 lignes ;
- récapitulatif : habitation `56`, cour `16`, garage `15`, étages `76 + 4`, total habitation `232` ;
- surfaces privatives `87 / 80 / 80`, total `247` ; surfaces dans titre `225` ;
- tantièmes `3522 / 3239 / 3239`, total `10 000` ;
- structures et valeurs couvertes par pytest ;
- dernier gate restant : rendu PNG de chaque page et validation juridique humaine des six sorties.
