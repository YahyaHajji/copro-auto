# Dictionnaire métier

## Projet

`Project` est le dossier JSON versionné (`schema_version = 4`; ouverture rétrocompatible des versions 1, 2 et 3). Il contient une identité, des niveaux, les décisions de comparaison CAD et l’historique des générations. Les valeurs dérivées ne sont pas stockées : elles sont recalculées à l’ouverture.

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

Un niveau possède un nom, un ordre stable, une liste ordonnée de cotes de début, une liste ordonnée de cotes de fin, une liste ordonnée de hauteurs intérieures et une liste de parties. Au moins une cote de début est obligatoire. Chaque cote de fin doit être strictement supérieure à toutes les cotes de début du niveau et chaque hauteur doit être positive.

| Champ JSON v4 | Type | Règle |
|---|---|---|
| `start_elevations` | liste de Decimal m | Une ou plusieurs valeurs, ordre de saisie conservé |
| `end_elevations` | liste de Decimal m | Zéro ou plusieurs valeurs, ordre de saisie conservé |
| `interior_heights` | liste de Decimal m | Zéro ou plusieurs valeurs strictement positives |

Dans l’éditeur, plusieurs nombres sont séparés par un point-virgule, par exemple `+0,20` puis `+3,10 ; +5,70` et `2,90 ; 5,50`. La virgule et le point sont acceptés comme séparateurs décimaux. Les doublons exacts sont éliminés sans trier les autres valeurs.

À l’ouverture d’un projet v1 à v3, les anciens champs scalaires `start_elevation`, `end_elevation` et `interior_height` sont automatiquement convertis en listes v4 vides ou à un élément. Les identifiants, niveaux et parties existants sont conservés.

### Partie (`Part`)

| Champ | Rôle |
|---|---|
| `index` | Indice cadastral, unique pour les parties privatives et unique dans un niveau |
| `nature` | `privative` ou `commune` |
| `consistency` | Libellé court utilisé dans les tableaux |
| `description` | Description détaillée saisie par l’utilisateur et insérée sans rédaction automatique dans les narratifs |
| `observations` | Surplomb, cour, garage ou autre remarque |
| `evidence` | Valeur et référence d’entité provenant éventuellement du DXF |

Une décision CAD conserve aussi la confiance, le fichier source, les handles d’entités et l’empreinte SHA-256. Le dessin lui-même n’est pas copié dans le projet JSON.

Le brouillon CAD utilise les mêmes listes `start_elevations`, `end_elevations` et `interior_heights` que le projet v4. Une phrase structurée par `cote/cotes` conserve chaque valeur dans son ordre. Les hauteurs sont calculées seulement pour une association déterministe : un début vers plusieurs fins, plusieurs débuts vers une fin, ou deux listes de même longueur associées par ordre.

Une hauteur calculée seule reçoit une confiance moyenne. Lorsque chaque différence calculée correspond à une étiquette numérique située dans la coupe verticale rattachée au tableau du niveau, la confiance devient élevée et les handles de ces étiquettes sont ajoutés aux preuves. Un nombre identique isolé ailleurs dans le dessin ne confirme jamais une hauteur.

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
# Données de dossier ajoutées au schéma v2

- `identity.project_time` : heure du dossier au format `HH:mm`, utilisée avec la date pour la phrase française du PV.
- `identity.land_registry_office` : conservation foncière, distincte de la préfecture et de la commune.
- `identity.client` : nom complet, CNIE, adresse/domicile, qualité et date d’expiration de la CNIE.
- `identity.boundaries` : limites `northeast`, `northwest`, `southeast`, `southwest` utilisées par le Règlement.
