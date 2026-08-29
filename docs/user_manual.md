# Manuel utilisateur — Copro Auto

## 1. Licence

Au premier lancement commercial, cliquez sur l’état de licence en bas à gauche, saisissez la clé puis activez. Une connexion est requise pour l’activation et l’actualisation. Le poste commercial fonctionne hors ligne pendant 24 heures après sa dernière vérification réussie. L’application contrôle automatiquement le serveur au démarrage, toutes les 15 minutes et avant création, import CAD ou génération. Une révocation ou une libération administrative bloque alors le poste. Après les 24 heures, une grâce de 2 jours conserve uniquement l’ouverture et l’export JSON; création, modification productive, import CAD et génération DOCX restent bloqués jusqu’au retour de la connexion. Les clés d’essai hors ligne portables conservent leur durée fixe de 30 jours et ne sont pas révocables à distance.

## 2. Créer ou ouvrir

- **Nouveau dossier** crée une fiche vide.
- **Ouvrir un projet** charge un JSON Copro Auto.
- **Enregistrer** utilise une écriture atomique; le fichier antérieur n’est remplacé qu’après succès.

Renseignez d’abord le nom de la propriété, le titre foncier et la surface du terrain. Les erreurs obligatoires apparaissent dans le panneau de contrôle.

## 3. Niveaux et parties

Ajoutez les niveaux dans leur ordre vertical, avec leurs cotes et hauteurs. Les colonnes **Cotes début**, **Cotes fin** et **Hauteurs** acceptent plusieurs valeurs séparées par un point-virgule. Exemple : `+0,20`, `+3,10 ; +5,70` et `2,90 ; 5,50`. Utilisez le point-virgule car la virgule reste le séparateur décimal français. Sélectionnez ensuite un niveau pour saisir ses parties.

Au moins une cote de début est obligatoire. Toutes les cotes de fin doivent être supérieures à toutes les cotes de début et les hauteurs doivent être positives. Le contrôle signale ces erreurs sur le niveau concerné.

Pour chaque partie :

- choisissez `Privative` ou `Commune` ;
- indiquez l’indice et la consistance courte ;
- saisissez la description détaillée destinée aux paragraphes narratifs ;
- renseignez séparément dans-titre, surplomb, hors-balcon, balcon, cour, terrasse et garage ;
- ajoutez une observation pour tout surplomb.

Ne transformez pas `69 + 11` en `76 + 4` : saisissez les deux décompositions dans leurs colonnes respectives.

## 4. Contrôler

Le bouton **Contrôler** vérifie champs obligatoires, surfaces, cotes, indices et tantièmes. La génération est activée seulement sans erreur bloquante. Les avertissements signalent un point à vérifier mais ne détruisent aucune valeur.

## 5. Import DWG/DXF

- Sur un dossier vide, cliquez sur **Importer DWG/DXF** : le dessin prépare un brouillon prérempli.
- Sur un dossier déjà saisi, le même bouton devient **Vérifier DWG/DXF** : les valeurs manuelles restent retenues par défaut.
- Un DXF R2018 est lu directement. Un DWG passe par AutoCAD Core Console lorsqu’il répond correctement; sinon l’application demande d’exporter le dessin en DXF R2018.
- La page **Projet** compare les valeurs manuelles et CAD. La page **Niveaux et parties** permet de corriger, ajouter, supprimer et réordonner les éléments détectés.
- Dans la revue des niveaux, **Cotes début**, **Cotes fin** et **Hauteurs** affichent toutes les valeurs séparées par ` ; `. Vous pouvez corriger ces listes avant **Appliquer les choix**; chaque valeur est ensuite transférée au formulaire principal.
- Une hauteur est proposée par différence entre une cote de début et une cote de fin seulement lorsque leur association est certaine. La confiance est **Moyenne** pour le calcul seul et **Élevée** lorsque les mêmes hauteurs sont retrouvées dans la coupe verticale correspondante. Un nombre isolé ailleurs dans le plan n’est pas utilisé comme confirmation.
- Un avertissement d’association incertaine signifie que les valeurs ont été conservées pour la revue, mais qu’aucune hauteur n’a été inventée. Le topographe doit alors corriger ou confirmer les listes.
- Les suggestions de pièces ont une confiance faible et restent désactivées tant que le topographe ne coche pas explicitement leur utilisation.
- **Annuler** ne modifie jamais le dossier. **Appliquer les choix** copie le brouillon relu dans le formulaire normal, où les champs factuels absents doivent être complétés.

La conservation foncière, le topographe, la date/heure, le client et les limites restent manuels lorsqu’ils ne figurent pas explicitement dans le dessin. Aucun texte juridique n’est demandé : il provient toujours des modèles DOCX validés.

## 6. Générer

Choisissez **Générer les 5 DOCX**, puis un dossier vide ou dédié. L’application prépare les cinq fichiers dans un répertoire temporaire, vérifie leur structure et leurs valeurs critiques, puis les déplace ensemble. Une erreur laisse la sortie précédente intacte. `PV_Division.docx` contient PV Division 1 puis PV Division 2 après un saut de section/page.

Dans les documents, chaque cote garde son signe et deux décimales. Par exemple, un début `+0,20` et deux fins `+3,10 ; +5,70` deviennent `de la cote +0,20 m aux cotes +3,10 m et +5,70 m`. Deux hauteurs `2,90 ; 5,50` deviennent `de hauteurs intérieures de 2,90 m et 5,50 m`. Les dossiers contenant une seule cote et une seule hauteur conservent la formulation historique.

Les fichiers produits sont : `PV_Division.docx` (PV 1 puis PV 2), `Reglement_Copropriete.docx`, `Tableau_A.docx`, `Tableau_B.docx` et `Tableau_Recapitulatif.docx`.

## 7. Bonnes pratiques

- conserver le JSON avec les DOCX ;
- ne jamais modifier les modèles dans `resources/templates/originals` ;
- vérifier visuellement et juridiquement les cinq documents avant dépôt ;
- effectuer une sauvegarde séparée des projets et sorties.
