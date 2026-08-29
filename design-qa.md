# Design QA — cohérence UI/UX globale Copro Auto

## Evidence

- Référence visuelle approuvée : `C:\Users\yahya\.codex\generated_images\019f7654-06df-7c03-ad8f-b6baf4f292e7\exec-bcb85e9c-444b-4d21-9228-9cb67d4150c3.png`.
- Matrice de l’application source : `work/ui-ux-final/06-application-matrix.png`.
- Matrice de toutes les catégories de messages : `work/ui-ux-final/07-messagebox-matrix.png`.
- Comparaison côte à côte référence/implémentation : `work/ui-ux-final/08-reference-comparison.png`.
- Capture Windows.Graphics.Capture du binaire packagé : `dist-updated/CoproAuto/CoproAuto.exe`, fenêtre 1435 × 899 avec chrome Windows clair.
- États inspectés : Projet vide, Niveaux et parties à taille contrainte, licence invalide, comparaison DWG/DXF identique/différent/manquant, information, succès, avertissement, erreur critique et question de modifications non enregistrées.

## Findings et corrections

- La composition reste fidèle à la référence : barre latérale blanche, canevas bleu-gris très clair, cartes blanches, accent or, actions teal et texte sombre.
- Toutes les surfaces applicatives sont désormais claires, y compris `QDialog`, `QMessageBox`, boutons de dialogue, listes, menus, calendriers, popups et barres de défilement horizontales.
- Le dialogue de licence possède une hiérarchie nette, un statut sémantique lisible, un libellé associé à la clé, une action principale et une zone destructive isolée.
- La comparaison DWG/DXF utilise texte, icône et couleur pour distinguer identique, différent et manquant; la saisie manuelle reste sélectionnée par défaut.
- Les messages information/succès/avertissement/critique/question utilisent des fonds et icônes sémantiques, des boutons français, un bouton principal visible et une action destructive distincte.
- La première capture a révélé un P1 absent des tests : une longue erreur critique pouvait être tronquée. Le wrapper central insère désormais des retours de ligne sûrs; la capture de contrôle affiche la phrase complète.
- À 1080 × 700, les tables Niveaux et Parties, leurs en-têtes et l’aide ne se chevauchent plus. Le panneau de contrôle est borné à 360 px et l’éditeur conserve la priorité de largeur.
- Les chemins techniques `identity.*` sont remplacés visuellement par des emplacements métier français; les erreurs et avertissements restent identifiables sans dépendre uniquement de la couleur.
- Le binaire final affiche les mêmes tokens et libellés que la source; son chrome natif est clair et la liste de validation reste lisible.

## Vérification

- Suite complète : **51 réussis, 2 ignorés**, aucune régression.
- Régressions UI dédiées : couverture QSS, localisation de tous les boutons standards, rôles sémantiques, accessibilité de la clé de licence, états CAD et non-chevauchement à la taille minimale.
- Smoke test du candidat : `licensed-offline` et `fresh-unlicensed` réussis.
- Smoke test après copie dans `dist-updated/CoproAuto` : `licensed-offline` et `fresh-unlicensed` réussis.
- SHA-256 final : `D39DBE935DFEE2B34B0099CCF327CF2891C29870FDC7A42D11E32B06F3F27F5A`.
- Authenticode : `NotSigned`, inchangé et acceptable pour ce MVP privé; une signature reste requise avant distribution commerciale.

## Résultat

Aucun écart P0, P1 ou P2 ne subsiste dans les surfaces inspectées. Le package précédent est conservé dans `dist-updated/CoproAuto-pre-ui-ux-20260812` pour retour arrière local.

final result: passed
