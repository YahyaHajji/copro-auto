# Dictionnaire métier

## Projet

`Project` est le dossier JSON versionné (`schema_version = 1`). Il contient une identité, des niveaux, les décisions de comparaison CAD et l’historique des générations. Les valeurs dérivées ne sont pas stockées : elles sont recalculées à l’ouverture.

### Identité (`ProjectIdentity`)

| Champ | Type | Règle |
|---|---|---|
| `property_name` | texte | Nom de la propriété dite, obligatoire |
| `land_title` | texte | Numéro du titre foncier, obligatoire |
| `prefecture`, `commune`, `subdivision` | texte | Situation administrative |
| `surveyor` | texte | Topographe responsable |
| `project_date` | date ISO | Date du dossier |
| `land_area` | Decimal m² | Strictement positive |
| `overall_consistency` | texte | Composition générale de l’immeuble |
| `total_height` | Decimal m | Hauteur totale au-dessus du trottoir |
| `boundaries` | objet texte | Limites cadastrales facultatives |

### Niveau (`Level`)

Un niveau possède un nom, un ordre stable, une cote de début, une cote de fin facultative, une hauteur intérieure facultative et une liste de parties. La cote de fin doit dépasser la cote de début.

### Partie (`Part`)

| Champ | Rôle |
|---|---|
| `index` | Indice cadastral, unique pour les parties privatives et unique dans un niveau |
| `nature` | `privative` ou `commune` |
| `consistency` | Libellé court utilisé dans les tableaux |
| `description` | Description détaillée saisie par l’utilisateur et insérée sans rédaction automatique dans les narratifs |
| `observations` | Surplomb, cour, garage ou autre remarque |
| `evidence` | Valeur et référence d’entité provenant éventuellement du DXF |

## Surfaces (`SurfaceBreakdown`)

Toutes les surfaces utilisent `Decimal`; aucun calcul métier ne passe par `float`.

| Champ | Sens |
|---|---|
| `inside_title` | Surface située dans le titre foncier |
| `overhang` | Surface en surplomb hors limite du titre |
| `excluding_balcony` | Surface architecturale hors balcon, pouvant inclure les sous-composants cour/garage |
| `balcony` | Balcon |
| `courtyard` | Cour |
| `terrace` | Terrasse privative |
| `garage` | Garage, ventilé séparément dans le tableau récapitulatif |

Calculs dérivés :

- `cadastral_total = inside_title + overhang` ;
- `architectural_total = excluding_balcony + balcony` si cette décomposition est renseignée, sinon `cadastral_total`.

Pour les étages Yasmin 71, les deux lectures sont conservées sans conversion arbitraire :

- cadastrale : `69 + 11 = 80 m²` ;
- architecturale : `76 + 4 = 80 m²`.

Au rez-de-chaussée, le récapitulatif ventile les 87 m² en habitation 56 m², cour 16 m² et garage 15 m².

## Tantièmes

La base est la somme des `cadastral_total` des parties privatives. La méthode des plus forts restes calcule les valeurs exactes, prend les parties entières, puis attribue les points manquants aux restes les plus élevés avec départage stable par ordre d’entrée.

Invariant : somme des tantièmes = `10 000`; quote-part affichée = tantième / 100; somme = `100,00 %`. Yasmin 71 : `87 / 80 / 80 → 3522 / 3239 / 3239`.

## Traçabilité CAD

`SourceEvidence` retient le fichier, la valeur brute, le type (`manual`, `dxf_table`, `dxf_text`) et le handle de l’entité. `FieldDecision` conserve les deux valeurs, la source choisie et la date. Une valeur CAD n’écrase jamais la saisie sans choix explicite.
