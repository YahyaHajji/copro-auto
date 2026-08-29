# Audit UI/UX global — Copro Auto

Date : 11 août 2026

## Périmètre et cible

L’audit couvre toutes les surfaces PySide6 appartenant à Copro Auto : fenêtre principale, onglets Projet et Niveaux/Parties, panneau de contrôle, dialogue de licence, toutes les catégories de `QMessageBox` (information, succès, avertissement, erreur critique, question, licence requise et modifications non enregistrées), comparaison DWG/DXF, états de survol/focus/désactivation et fenêtre minimale de 1080 × 700.

La référence visuelle reste le mode clair blanc approuvé : surfaces blanches, fond bleu-gris très pâle, texte bleu-noir, actions turquoise, accent cadastral doré. Les sélecteurs de fichiers Windows restent des surfaces natives du système.

## Parcours audité

1. **Fenêtre principale — Projet : sain.** La hiérarchie, les cartes, les formulaires et les actions principales sont cohérents avec la référence claire.
2. **Fenêtre principale — Niveaux et parties : à corriger.** La table reste utilisable en grande fenêtre, mais la barre de défilement horizontale sombre et le texte d’aide collé à la table cassent la cohérence visuelle.
3. **Fenêtre minimale 1080 × 700 : critique.** Les boutons recouvrent les titres, les tables se compressent au-delà de leur contenu utile et le texte d’aide recouvre les lignes. Le panneau de contrôle prend trop de largeur.
4. **Dialogue de licence : critique.** Le fond reste sombre alors que les libellés utilisent les couleurs du thème clair, ce qui produit un contraste presque nul. Les actions ne sont pas suffisamment regroupées par niveau de risque.
5. **Tous les `QMessageBox` : critique.** Le problème de couleurs appartient au composant global, pas uniquement à l’erreur d’activation. Les boîtes d’information, de succès après génération, d’avertissement, d’erreur critique, de question, de licence requise et de modifications non enregistrées utilisent toutes le même fond sombre incompatible avec le texte du thème clair.
6. **Comparaison DWG/DXF : critique.** Le titre, l’explication et l’avertissement sont illisibles; `Cancel` reste en anglais; les états identique/différent/manquant n’ont aucune distinction sémantique; l’espace vide domine la fenêtre.
7. **États de validation : à améliorer.** Le succès est lisible mais trop discret; erreurs, avertissements et succès doivent utiliser des fonds doux, une icône/forme et un libellé, jamais la couleur seule.

## Forces confirmées

- Architecture Qt native simple et sans moteur web.
- Palette principale claire déjà solide sur la fenêtre principale.
- Libellés métier français et parcours de saisie compréhensible.
- Actions principales, secondaires et destructives déjà identifiables par propriétés QSS.
- Navigation clavier native disponible sur les contrôles Qt.

## Risques UX prioritaires

- **P1 — contraste bloquant :** toutes les catégories de `QMessageBox`, ainsi que les autres dialogues secondaires, peuvent rendre leur information pratiquement invisible.
- **P1 — reflow bloquant :** le minimum 1080 × 700 ne garantit pas une interface utilisable sans chevauchement.
- **P1 — récupération d’erreur :** les erreurs réseau indiquent le problème, mais leur présentation ne permet pas de le lire rapidement et n’oriente pas clairement vers la nouvelle tentative ou la fermeture.
- **P2 — incohérence de langue :** les boutons standards peuvent apparaître en anglais.
- **P2 — hiérarchie :** l’action destructive de désactivation de licence ressemble à une action ordinaire pleine largeur.
- **P2 — densité des tables :** les tables ont des minimums rigides et leurs barres horizontales ne suivent pas le thème.
- **P2 — jargon interne :** certaines localisations du panneau de validation peuvent encore exposer des chemins techniques au lieu d’un emplacement métier français.

## Risques d’accessibilité

- Contraste visiblement insuffisant dans les dialogues et messages secondaires.
- Le focus clavier n’est pas vérifié pour tous les boutons standards, listes et cellules éditables.
- Les états de licence et de validation ne doivent pas dépendre uniquement de la couleur.
- Les libellés de clé de licence et les champs doivent avoir des relations accessibles explicites.
- Le redimensionnement à 1080 × 700 échoue visuellement; le zoom et les facteurs d’échelle Windows élevés doivent être testés séparément.

Cet audit visuel ne constitue pas une certification WCAG. Une passe clavier complète et une inspection avec un lecteur d’écran Windows restent nécessaires pour confirmer les noms accessibles, l’ordre de lecture et l’annonce des changements d’état.

## Recommandations retenues

1. Étendre le thème global à `QDialog`, `QMessageBox`, `QDialogButtonBox`, menus, calendriers, fenêtres contextuelles et barres de défilement horizontales.
2. Forcer le chrome clair des fenêtres Copro Auto sous Windows 10/11 lorsque DWM le permet, sans modifier les sélecteurs de fichiers natifs.
3. Centraliser toutes les catégories de `QMessageBox` — information, succès, avertissement, erreur critique, question, licence requise et modifications non enregistrées — afin de garantir le thème clair, le français, les rôles primary/secondary/danger et des valeurs de retour inchangées.
4. Recomposer le dialogue de licence avec un bandeau d’état sémantique, un champ clairement étiqueté et une zone destructive séparée.
5. Recomposer la comparaison DWG/DXF avec statuts lisibles, boutons français et hauteur de table adaptée au contenu.
6. Supprimer les minimums verticaux incompatibles dans Niveaux/Parties, donner des facteurs d’étirement aux tables et empêcher tout chevauchement à 1080 × 700.
7. Contraindre la largeur du panneau de validation et traduire ses emplacements techniques en libellés métier.
8. Ajouter une matrice de tests UI et une QA visuelle native couvrant chaque catégorie de `QMessageBox` avant de reconstruire `dist-updated/CoproAuto`.

## Preuves locales

- `work/ui-audit/00-approved-light-reference.png`
- `work/ui-audit/01-main-window.png`
- `work/ui-audit/02-license-dialog.png`
- `work/ui-audit/03-activation-error.png`
- `work/ui-audit/04-import-review.png`
- `work/ui-audit/05-levels-and-parts.png`
- `work/ui-audit/06-minimum-window.png`
- `work/ui-audit/07-user-license-dialog.png`
- `work/ui-audit/08-user-activation-error.png`
