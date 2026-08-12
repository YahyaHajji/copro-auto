# Manuel utilisateur — Copro Auto

## 1. Licence

Au premier lancement commercial, cliquez sur l’état de licence en bas à gauche, saisissez la clé puis activez. Une connexion est requise pour l’activation et l’actualisation. Le poste commercial fonctionne hors ligne pendant 24 heures après sa dernière vérification réussie. L’application contrôle automatiquement le serveur au démarrage, toutes les 15 minutes et avant création, import CAD ou génération. Une révocation ou une libération administrative bloque alors le poste. Après les 24 heures, une grâce de 2 jours conserve uniquement l’ouverture et l’export JSON; création, modification productive, import CAD et génération DOCX restent bloqués jusqu’au retour de la connexion. Les clés d’essai hors ligne portables conservent leur durée fixe de 30 jours et ne sont pas révocables à distance.

## 2. Créer ou ouvrir

- **Nouveau dossier** crée une fiche vide.
- **Ouvrir un projet** charge un JSON Copro Auto.
- **Enregistrer** utilise une écriture atomique; le fichier antérieur n’est remplacé qu’après succès.

Renseignez d’abord le nom de la propriété, le titre foncier et la surface du terrain. Les erreurs obligatoires apparaissent dans le panneau de contrôle.

## 3. Niveaux et parties

Ajoutez les niveaux dans leur ordre vertical, avec cotes et hauteur libre. Sélectionnez un niveau pour saisir ses parties.

Pour chaque partie :

- choisissez `Privative` ou `Commune` ;
- indiquez l’indice et la consistance courte ;
- saisissez la description détaillée destinée aux paragraphes narratifs ;
- renseignez séparément dans-titre, surplomb, hors-balcon, balcon, cour, terrasse et garage ;
- ajoutez une observation pour tout surplomb.

Ne transformez pas `69 + 11` en `76 + 4` : saisissez les deux décompositions dans leurs colonnes respectives.

## 4. Contrôler

Le bouton **Contrôler** vérifie champs obligatoires, surfaces, cotes, indices et tantièmes. La génération est activée seulement sans erreur bloquante. Les avertissements signalent un point à vérifier mais ne détruisent aucune valeur.

## 5. Vérifier par DWG/DXF

Cette étape est facultative. Un DXF est lu directement; un DWG est converti temporairement par AutoCAD Core Console. L’écran de comparaison affiche saisie, dessin et état. La saisie reste choisie par défaut. Toute valeur CAD retenue est tracée dans le JSON.

## 6. Générer

Choisissez **Générer les 6 DOCX**, puis un dossier vide ou dédié. L’application prépare les six fichiers dans un répertoire temporaire, vérifie leur structure et leurs valeurs critiques, puis les déplace ensemble. Une erreur laisse la sortie précédente intacte.

Les fichiers produits sont : PV Division 1, PV Division 2, règlement de copropriété, Tableau A, Tableau B et tableau récapitulatif.

## 7. Bonnes pratiques

- conserver le JSON avec les DOCX ;
- ne jamais modifier les modèles dans `resources/templates/originals` ;
- vérifier visuellement et juridiquement les six documents avant dépôt ;
- effectuer une sauvegarde séparée des projets et sorties.
