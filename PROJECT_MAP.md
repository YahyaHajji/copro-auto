# PROJECT_MAP — Plateforme d’automatisation des dossiers de copropriété

Dernière mise à jour : 24 août 2026
Statut : produit technique Windows fonctionnel, packagé et vérifié — 54 tests standards verts, 2 tests d’intégration PostgreSQL réels verts, QA visuelle source + binaire, deux smoke tests du binaire et 23 pages DOCX inspectées; le service de licences et son tableau de bord privé sont déployés sur Vercel/Neon, tandis que les validations humaines, terrain et juridiques restent ouvertes

## [ASSUMPTIONS & DECISIONS]

- Produit desktop local destiné aux topographes individuels et aux bureaux au Maroc.
- L'objectif immédiat est un MVP d'apprentissage et de test privé, sans vente; l'hébergement doit utiliser les offres gratuites tant qu'elles suffisent.
- Cible officielle : Windows 10/11 x64. Windows 7 n’est pas pris en charge.
- Tous les postes de production connus disposent d’AutoCAD, mais l’application doit fonctionner entièrement sans import CAD.
- La saisie manuelle est le flux principal et la source de vérité éditable.
- L’import DWG/DXF est un accélérateur et un contrôle complémentaire ; il n’écrase jamais silencieusement une saisie.
- Les six fichiers fournis sont les modèles définitifs. Leur texte juridique, leur structure et leur mise en forme doivent être préservés.
- Aucun LLM ne rédige ou ne modifie le texte juridique. La génération est déterministe, locale et reproductible.
- L’interface reste native PySide6. Tailwind CSS n’est pas une dépendance ; son langage de design (échelle d’espacement, tokens, hiérarchie et états) inspire un système QSS propre à l’application.
- La méthode des plus forts restes est retenue pour produire exactement 10 000 tantièmes.
- Les deux décompositions des étages sont complémentaires et conservées :
  - cadastrale : `69 m² dans le titre + 11 m² de surplomb = 80 m²` ;
  - architecturale : `76 m² hors balcon + 4 m² de balcon = 80 m²`.
- Le bureau de stage reçoit un essai complet de six mois.
- L’essai commercial standard dure 30 jours et peut être prolongé manuellement.
- Pour le test terrain privé avant déploiement du serveur, une clé hors ligne portable signée peut activer les fonctions productives pendant 30 jours exactement. Elle est copiable et non révocable à distance, donc interdite pour une distribution commerciale.
- Plans initiaux : individuel et bureau multi-sièges.
- Licence commerciale hybride : contrôle serveur au démarrage, toutes les 15 minutes et avant les actions productives; lease signé de 24 heures, puis grâce de lecture seule de 2 jours. Les clés d’essai hors ligne portables restent valables 30 jours et non révocables à distance.
- Après expiration, les projets restent consultables et exportables ; création et génération/régénération DOCX sont bloquées.
- L’auteur souhaite posséder personnellement le produit. Un accord écrit avec le bureau sur le code, le workflow et les modèles est obligatoire avant toute vente.

### Emplacements confirmés

- **Racine réelle du dépôt et de tout le code source :** `C:\Users\yahya\Saved Games\intelligent document automation platform`.
- Cette racine est déjà le projet : aucun dossier parent supplémentaire nommé `copro_auto/` ne doit être créé.
- **Source externe des six modèles définitifs :** `C:\Users\yahya\OneDrive\Desktop\Copro\Copro`.
- Les originaux externes restent intacts. Au Milestone 0, ils sont copiés dans `resources/templates/originals/`; les versions DOCX préparées pour la génération résident dans `resources/templates/runtime/`.
- Le dossier actuel `work/` contient uniquement des scripts et extractions de recherche. Il n’est ni importé par l’application, ni inclus dans le package commercial.
- Les chemins absolus ci-dessus sont des chemins de développement uniquement. Le code produit n’intègre aucun chemin utilisateur codé en dur.

## [TECH_STACK]

### Desktop

- **Windows 10/11 x64** — environnement opérationnel et AutoCAD.
- **Python 3.13.12 x64** — version du build vérifié, compatible avec les dépendances retenues.
- **PySide6 6.11.1** — interface Qt officielle en français ; PyQt5/Qt 5 ne sont pas retenus.
- **QSS tokenisé** — thème natif professionnel à identité topographique/cadastrale; le mode clair blanc validé est désormais le thème produit par défaut, indépendamment du thème Windows, tandis que la palette sombre reste disponible explicitement dans le code.
- **python-docx 1.2.0 + lxml verrouillé** — modification contrôlée des modèles DOCX et opérations OOXML ciblées.
- **ezdxf 1.4.4** — lecture DXF R2018 ; ne lit pas directement DWG.
- **cryptography 49.0.0** — vérification locale des jetons Ed25519 signés.
- **Bibliothèque standard** — `dataclasses`, `decimal`, `json`, `logging`, `pathlib`, `subprocess`, `hashlib`, `uuid`, `zipfile`.
- **PyInstaller 6.21.0** — distribution Windows `onedir`, plus fiable et diagnosticable qu’un `onefile` pour Qt.
- **pytest 9.1.1** — tests unitaires, intégration et golden master.

### Import CAD

- **AutoCAD Core Console (`accoreconsole.exe`)** — export read-only de DWG vers DXF R2018 temporaire.
- **DXF direct** — entrée secondaire supportée.
- AutoCAD n’est jamais redistribué avec l’application.
- ODA File Converter n’est pas inclus dans la première version.

### Service de licences

- **FastAPI 0.139.0** — API minimale d’activation, rafraîchissement, désactivation et statut.
- **Uvicorn 0.51.0** — serveur ASGI derrière HTTPS.
- **PostgreSQL 18.x** — organisations, licences, sièges, activations et événements.
- **SQLAlchemy 2.0.51 + psycopg 3.3.4** — persistance transactionnelle.
- **cryptography 49.0.0 / Ed25519** — signature serveur ; clé privée uniquement sur le serveur, clé publique dans le desktop.
- MVP en ligne : Vercel Hobby pour l'API FastAPI HTTPS et Neon Free PostgreSQL 18 à Francfort, avec secrets injectés au déploiement; le VPS/Caddy reste une option future.
- Administration initiale par CLI protégée ; pas de portail SaaS ou paiement en ligne dans la première version.

### Choix de simplicité

- JSON atomique versionné pour les projets desktop ; aucune base locale SQL.
- PostgreSQL réservé au service de licences.
- Aucun LLM, OCR, dongle USB, DRM agressif, compte utilisateur ou télémétrie métier.
- Les paiements, factures et renouvellements sont gérés manuellement au début.
- Les versions exactes et dépendances transitives seront verrouillées dans les fichiers de build au début de l’exécution.

## [SYSTEM_FLOW]

1. **Démarrer et vérifier la licence**
   - Premier lancement : saisie d’une clé d’essai ou commerciale.
   - Envoi HTTPS limité à la clé, version de l’application et empreinte pseudonyme de l’appareil.
   - Le serveur retourne un jeton Ed25519 signé valable 24 heures.
   - Hors ligne, le client vérifie localement le jeton; après 24 heures, une grâce de 2 jours conserve uniquement la consultation et l’export JSON.
   - En ligne, le statut est synchronisé au démarrage, toutes les 15 minutes et avant création, import CAD ou génération; une révocation ou libération administrative invalide immédiatement le cache local.
   - Les états sont explicites : `TRIAL_ACTIVE`, `PAID_ACTIVE`, `EXPIRING_SOON`, `OFFLINE_GRACE`, `EXPIRED`, `REVOKED`, `DEVICE_LIMIT_REACHED`.

2. **Créer ou ouvrir un projet**
   - Création autorisée seulement avec une licence productive active.
   - Ouverture, consultation et export JSON toujours autorisés, y compris après expiration.
   - Validation de `schema_version` à l’ouverture.

3. **Saisir manuellement — flux principal**
   - Formulaire français : projet, situation, limites, niveaux, parties, composants de surface et métadonnées.
   - Un dossier complet peut être calculé, validé et généré sans dessin.

4. **Importer et comparer le CAD — flux complémentaire**
   - DXF direct ou DWG converti temporairement via AutoCAD Core Console.
   - Import possible avant, pendant ou après la saisie.
   - Comparaison champ par champ : identique, absent ou différent.
   - L’utilisateur choisit la valeur active ; les valeurs manuelle et CAD restent traçables.

5. **Normaliser et réconcilier**
   - Normalisation des décimales, unités, cotes, libellés et indices composés.
   - Extraction prioritaire des entités `TABLE`.
   - Repli spatial sur `TEXT`/`MTEXT` lorsque le tableau est dessiné comme primitives.
   - Aucune donnée importée n’est appliquée sans aperçu et confirmation.

6. **Calculer exactement**
   - Tous les calculs utilisent `Decimal`, jamais `float`.
   - Surface avec surplomb = surface intérieure au titre + surplomb.
   - Base de répartition = somme des surfaces totales privatives.
   - Tantièmes entiers au 1/10 000 par plus forts restes avec départage stable.
   - Quote-part affichée = tantième / 100 ; total exact 100,00 %.
   - Totaux par niveau, nature et consistance.

7. **Valider**
   - Bloquants : champs obligatoires, surfaces positives, cotes ordonnées, indices uniques, totaux de niveaux, tantièmes = 10 000, quotes = 100,00 %, modèles disponibles.
   - Avertissements : libellé inhabituel, écart manuel/CAD, limite absente, surplomb sans observation, composants incohérents.
   - Chaque message français identifie le champ, la valeur et la correction attendue.

8. **Prévisualiser**
   - Résumé des valeurs utilisées par chaque document.
   - Génération impossible tant qu’une erreur bloquante subsiste.

9. **Générer les six documents**
   - Instantané immuable unique du projet validé.
   - Génération dans un dossier temporaire.
   - Remplissage de marqueurs et duplication contrôlée des lignes/paragraphes variables.
   - Conservation des styles, fusions, entêtes, pieds et texte juridique.
   - Contrôle structurel et croisé, puis déplacement atomique des six DOCX.

10. **Sauvegarder et reprendre**
   - JSON atomique : fichier temporaire puis remplacement.
   - Les données source et décisions sont conservées ; les calculs dérivés sont recalculés.
   - Manifeste de génération : version application, empreintes modèles, sorties et validations.

11. **Renouveler ou déplacer la licence**
   - Renouvellement côté serveur sans réinstallation.
   - Désactivation volontaire d’un appareil et activation du remplaçant.
   - Réinitialisation manuelle possible par le propriétaire en cas de machine perdue.

## [ARCHITECTURE]

### Principes

- Le domaine métier ne dépend ni de Qt, ni d’AutoCAD, ni de Word, ni du réseau.
- L’application métier est locale et monoprocessus.
- Le service de licences est séparé et ne reçoit aucune donnée topographique.
- Les sources client ne sont jamais modifiées.
- Organisation par fonctionnalités ; aucune couche générique prématurée.
- Les six modèles versionnés sont les autorités visuelles et juridiques.

### Frontières

```text
PySide6 UI
   |
   v
Application services ----> Domain model + calculations + validation
   |                                      ^
   +----> CAD adapters -------------------+
   +----> JSON repository
   +----> DOCX generation
   +----> Licensing client --HTTPS--> Licensing API --> PostgreSQL
```

### Structure actuelle — éléments principaux

```text
C:\Users\yahya\Saved Games\intelligent document automation platform\
├── PROJECT_MAP.md
├── README.md
├── pyproject.toml                    # application desktop
├── dependency-lock.*                 # nom final choisi lors du bootstrap
├── .gitignore
├── src/
│   └── copro_auto/
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py
│       ├── logging_setup.py
│       ├── domain/
│       │   ├── models.py
│       │   ├── calculations.py
│       │   └── validation.py
│       ├── projects/
│       │   ├── service.py
│       │   └── json_repository.py
│       ├── cad_import/
│       │   ├── service.py
│       │   ├── dwg_converter.py
│       │   └── dxf_parser.py
│       ├── documents/
│       │   ├── service.py
│       │   ├── docx_renderer.py
│       │   └── mappings.py
│       ├── licensing/
│       │   ├── service.py
│       │   ├── client.py
│       │   └── token_store.py
│       └── ui/
│           ├── main_window.py
│           ├── project_editor.py
│           ├── import_review.py
│           ├── validation_panel.py
│           ├── license_dialog.py
│           └── theme.py
├── license_server/                   # sous-projet déployé séparément
│   ├── pyproject.toml
│   ├── dependency-lock.*
│   ├── src/
│   │   └── license_server/
│   │       ├── __init__.py
│   │       ├── app.py
│   │       ├── models.py
│   │       ├── service.py
│   │       ├── signing.py
│   │       ├── routes.py
│   │       └── admin_cli.py
│   ├── migrations/
│   └── tests/
├── resources/
│   ├── templates/
│   │   ├── originals/                # copies intactes des six références
│   │   │   ├── PV Division1.doc
│   │   │   ├── PV Division 2..docx
│   │   │   ├── Règlement.docx
│   │   │   ├── Tableau A def.docx
│   │   │   ├── Tableau B.docx
│   │   │   └── Tab Récap def.docx
│   │   └── runtime/                  # six modèles DOCX préparés et packagés
│   │       ├── pv_division_1.docx
│   │       ├── pv_division_2.docx
│   │       ├── reglement.docx
│   │       ├── tableau_a.docx
│   │       ├── tableau_b.docx
│   │       └── tableau_recapitulatif.docx
│   └── icons/
├── tests/
│   ├── fixtures/
│   │   └── yasmin_71/
│   ├── test_calculations.py
│   ├── test_validation.py
│   ├── test_json_roundtrip.py
│   ├── test_dxf_import.py
│   ├── test_document_generation.py
│   └── test_licensing.py
├── packaging/
│   ├── configure_license.py
│   ├── create_offline_trial.py
│   ├── copro_auto.spec
│   ├── sign_release.ps1
│   └── smoke_test.ps1
├── deploy/
│   └── license_server/               # Caddy, Compose, sauvegarde et exemple d’environnement
├── docs/
│   ├── data_dictionary.md
│   ├── template_mapping.md
│   ├── deployment.md
│   ├── field_validation_protocol.md
│   ├── ip_and_template_rights_agreement_draft.md
│   ├── commercial_license_agreement_draft.md
│   ├── trial_terms_draft.md
│   ├── privacy_notice_draft.md
│   └── user_manual.md
└── work/                              # existant, recherche uniquement, non packagé
    ├── extracted/
    └── *.py / *.scr
```

### Emplacements d’exécution hors du dépôt

- Projets client : emplacement choisi par l’utilisateur ; extension JSON dédiée à définir lors du bootstrap.
- Documents générés : dossier de sortie choisi par l’utilisateur, jamais `resources/` ni `work/`.
- Jeton/licence et préférences non sensibles : `%APPDATA%\CoproAuto\` avec protection Windows adaptée pour le jeton.
- Logs et caches : `%LOCALAPPDATA%\CoproAuto\`.
- Fichiers DWG→DXF temporaires : sous-dossier unique de `%TEMP%\CoproAuto\`, supprimé après import réussi ou au prochain démarrage après incident.
- Build local : `.venv/`, `build/` et `dist/` sous la racine, tous ignorés par Git et exclus du package source.
- Les ressources packagées sont résolues relativement à l’application/PyInstaller ; aucun chemin `C:\Users\yahya\...` n’apparaît dans le code distribué.

### Modèle métier desktop

- `Project` : identité foncière, situation, IGT, dates, géométrie, limites et niveaux.
- `Level` : UUID, ordre, nom, type, cotes, hauteur et parties.
- `Part` : UUID, indice, nature, consistance, surfaces `Decimal`, composants et observations.
- `SurfaceBreakdown` : surface dans le titre, surplomb, surface hors balcon, balcon, cour, terrasse, garage et total contrôlé.
- `SourceEvidence` : source manuelle/CAD, fichier, entité/position et valeur brute.
- `FieldDecision` : valeurs manuelle/CAD, valeur active, décision et date.
- `GenerationRecord` : version, empreintes des modèles, fichiers et validations.
- `schema_version` initial : `1`.

### Modèle de licence

- `Organization` : individu ou bureau et statut minimal.
- `License` : clé hachée, plan, période commerciale, statut et sièges.
- `Activation` : empreinte pseudonyme, dates, état et version application.
- `LicenseToken` : licence, plan, permissions, échéance de lease et activation, signé Ed25519.
- Plan `INDIVIDUAL` : un utilisateur, jusqu’à deux appareils activés.
- Plan `OFFICE` : nombre de sièges configurable ; une activation consomme un siège.
- Le serveur ne stocke aucun titre foncier, nom de propriété, surface, DWG, DXF, JSON projet ou DOCX.

### Génération DOCX

- Les originaux restent intacts ; seules des copies de travail deviennent des modèles contrôlés.
- Le `.doc` historique est converti en `.docx` de travail sans altérer l’original.
- Les champs sont recensés dans une matrice champ → document → emplacement.
- Les zones variables utilisent des marqueurs uniques et des lignes/paragraphes modèles clonables.
- Aucun texte juridique n’est inventé ou reformulé.
- Les valeurs critiques sont comparées entre les six sorties.

### Sécurité et confidentialité

- Clé privée Ed25519 absente du desktop et du dépôt ; clé publique seulement dans le client.
- La clé privée dédiée aux essais hors ligne reste dans `packaging/offline_trial_signing.key`, ignorée par Git et exclue du package; seul le jeton d’essai signé et la clé publique sont distribués.
- Clés de licence stockées hachées côté serveur et masquées dans les logs.
- Secrets injectés au déploiement ; HTTPS obligatoire ; limitation basique du débit.
- Empreinte d’appareil pseudonyme et stable, sans inventaire matériel détaillé.
- Le client ne téléverse aucune donnée métier.
- L’expiration ne détruit, ne chiffre et ne retient jamais les données utilisateur.

### Modèle de menace et limite de protection

- La signature Ed25519 empêche la fabrication ou la modification d’un jeton de licence authentique sans la clé privée.
- Elle ne peut pas garantir qu’un exécutable contrôlé par un attaquant continuera d’effectuer la vérification : un desktop peut être inspecté, patché ou exécuté dans un environnement manipulé.
- Objectif réaliste : empêcher la copie et la falsification ordinaires, augmenter le coût du contournement et conserver l’autorité commerciale côté serveur — pas promettre un DRM inviolable.
- Les contrôles de permission sont appliqués aux frontières sensibles (création, import nouveau, génération/régénération), sans disperser une logique métier fragile dans tous les écrans.
- Détection raisonnable du recul d’horloge à partir du dernier temps serveur signé et des horodatages locaux ; une anomalie déclenche une nouvelle vérification en ligne, jamais la suppression de données.
- Aucun secret de signature côté desktop, aucune confiance dans un simple booléen ou fichier JSON local, et aucune date d’expiration codée en dur.
- Les protections agressives (obfuscation lourde, pilotes, anti-débogage intrusif) restent hors périmètre initial ; elles augmenteraient les faux positifs et le support sans rendre le produit impossible à cracker.
- Le code signing Windows est prévu avant distribution commerciale pour permettre au client de vérifier l’éditeur et l’intégrité du package ; il est distinct de la signature des jetons de licence.

### Tests

- Unitaires : Decimal, plus forts restes, validation, normalisation et états de licence.
- Invariants : tantièmes entiers, non négatifs, somme 10 000.
- Intégration : JSON, DWG→DXF, parsing, génération DOCX et API licence.
- Golden master Yasmin 71 : `87/80/80 → 3522/3239/3239` et valeurs cohérentes dans six documents.
- Licence : jeton falsifié/expiré, panne réseau, grâce, horloge reculée, révocation, sièges et déplacement.
- Serveur de licences renforcé : révocation et expiration à l’activation comme au rafraîchissement, empreinte d’appareil incorrecte, libération utilisateur et administrateur d’un siège, limitation à 20 tentatives d’activation par minute et santé PostgreSQL réelle.
- PostgreSQL réel : migration initiale idempotente, activation API, sauvegarde `pg_dump`, restauration dans une base jetable et vérification des données restaurées. Les tests refusent toute base dont le nom ne commence pas par `copro_auto_test_`.
- Essai terrain hors ligne : signature, durée maximale de 30 jours, activation productive, actualisation locale et désactivation.
- Menace desktop : patch simulé des réponses du client, stockage local altéré et suppression du cache ; vérifier qu’aucun de ces scénarios ne révèle la clé privée ni ne compromet les données projet.
- Régression documentaire : extraction des valeurs critiques et inspection visuelle de toutes les pages.
- Packaging : poste Windows propre sans Python, AutoCAD présent/absent et réseau présent/absent.

## [LOGGING]

### Desktop

- `logging` avec `QueueHandler` + `QueueListener` pour ne pas bloquer l’UI.
- Niveaux : `DEBUG`, `INFO`, `WARNING`, `ERROR`; production en `INFO`.
- Rotation : `%LOCALAPPDATA%/CoproAuto/logs/app.log`, 2 Mo × 5.
- Événements : ouverture/sauvegarde, import, compte d’entités, validation, génération et erreurs.
- Aucun texte juridique, nom de propriétaire, dessin ou clé complète.

### Serveur de licences

- Logs structurés pour activation, rafraîchissement, désactivation, révocation et erreur.
- Identifiants internes seulement ; clés et empreintes complètes masquées.
- Journal d’audit minimal en base pour les opérations administratives.
- Alertes basiques : erreurs répétées, base indisponible et signature impossible.

## [ORPHANS & PENDING]

- [ ] Faire signer l'accord sur la propriété personnelle du code et le droit d'exploiter le workflow et les six modèles. Un projet prêt pour avocat existe dans `docs/ip_and_template_rights_agreement_draft.md`; la signature bloque la vente, pas le prototype.
- [x] Initialiser directement la racine `C:\Users\yahya\Saved Games\intelligent document automation platform` comme dépôt ; ne pas créer de sous-dossier `copro_auto/` parent supplémentaire.
- [x] Créer `.gitignore` pour `.venv/`, `build/`, `dist/`, secrets, caches, journaux et fichiers temporaires ; `work/` reste local et ignoré.
- [x] Créer les environnements desktop/serveur et verrouiller les dépendances directes et transitives.
- [x] Copier les six originaux depuis `C:\Users\yahya\OneDrive\Desktop\Copro\Copro` vers `resources/templates/originals/`, convertir le `.doc` dans `runtime/`, préparer les cinq autres copies et enregistrer toutes les empreintes.
- [x] Établir le dictionnaire métier et la matrice champ → document (`docs/data_dictionary.md`, `docs/template_mapping.md`).
- [x] Documenter les deux décompositions complémentaires de surface.
- [x] Définir les remplacements ciblés et lignes/paragraphes répétables clonés depuis chaque modèle.
- [x] Implémenter le modèle métier, `SurfaceBreakdown` et JSON v1.
- [x] Implémenter calculs Decimal, plus forts restes et agrégations.
- [x] Implémenter validations et messages français.
- [x] Implémenter sauvegarde atomique et migrations JSON.
- [x] Implémenter le workflow manuel complet PySide6, avec synchronisation garantie entre la ligne de niveau sélectionnée et son éditeur de parties; les boutons d'ajout isolent explicitement la valeur booléenne `checked` émise par Qt des objets métier `Level` et `Part`, la sauvegarde récupère une ancienne ligne incomplète sans liste Nature en la classant `Privative`, les UUID de niveaux/parties restent stables, le contrôle affiche `Niveau · Indice` sans boucle de rafraîchissement et `Discard` fonctionne par égalité de valeur PySide6.
- [x] Implémenter le système QSS tokenisé et l’identité visuelle topographique avec états accessibles, densité adaptée aux formulaires et mise à l’échelle Windows; appliquer par défaut la référence claire blanche et conserver un bouton de licence lisible au repos, au survol, au focus et à l’appui.
- [x] Implémenter conversion DWG→DXF et détection AutoCAD.
- [x] Implémenter parsing des tables natives exposées par ezdxf, puis repli spatial `TEXT/MTEXT` validé sur le DXF Yasmin 71.
- [x] Implémenter comparaison manuel/CAD et décisions traçables.
- [x] Implémenter les mappings, descriptions détaillées et génération des six DOCX par clonage des motifs sources ; fidélité structurelle et numérique validée.
- [x] Implémenter génération transactionnelle et contrôles structurels/croisés initiaux.
- [x] Implémenter modèle PostgreSQL et migration initiale idempotente des licences.
- [x] Implémenter génération de clés, stockage HMAC-SHA256 et jetons Ed25519.
- [x] Implémenter les quatre routes : activate, refresh, deactivate, status.
- [x] Implémenter administration CLI : créer, renouveler, révoquer, libérer une activation.
- [x] Implémenter client licence, stockage local et états UI.
- [x] Synchroniser automatiquement les révocations/libérations administratives au démarrage, toutes les 15 minutes et avant les actions productives, sans supprimer un lease valide lors d’une panne réseau.
- [x] Implémenter pour les licences commerciales un lease de 24 heures, une grâce de lecture seule de 2 jours et une expiration non destructive; conserver séparément l’essai portable hors ligne de 30 jours.
- [x] Centraliser les décisions de permission aux frontières sensibles et implémenter la détection raisonnable du recul d’horloge.
- [x] Implémenter plans individuel et office.
- [x] Implémenter journalisation desktop rotative, logs serveur structurés et audit administratif en base.
- [x] Créer tests unitaires, intégration, sécurité, UI et golden master : 54 tests standards verts et 2 tests PostgreSQL réels verts, incluant le clic réel sur un niveau nouvellement ajouté, l'ajout de sa partie, la sauvegarde robuste d'une ancienne ligne sans liste Nature, la stabilité des UUID, l'arrêt du rafraîchissement du contrôle, la confirmation `Discard`, la cohérence globale du thème clair et de tous les dialogues, l'essai hors ligne signé limité à 30 jours, la synchronisation des révocations/libérations avec maintien du cache pendant une panne réseau, le comportement DWG sans AutoCAD, l'import DXF autonome, la configuration gratuite Vercel/Neon et le tableau de bord administrateur sécurisé.
- [x] Rendre et inspecter visuellement les six sorties Yasmin 71 : 23 pages vérifiées avec LibreOffice local isolé, pagination conforme aux modèles, corrections des emplacements narratifs PV2/règlement, remplacement des valeurs intégrées aux zones de texte et mois français déterministes. Les audits structure/style/accessibilité ont été rejoués; les alertes d’accessibilité restantes (texte alternatif d’images et marquage d’en-têtes de tableaux) proviennent des modèles définitifs.
- [ ] Obtenir la validation humaine métier et juridique des six sorties Yasmin 71; cette décision ne peut pas être automatisée et reste obligatoire avant usage officiel/commercial.
- [x] Renforcer le service de licences avant exposition publique : tests de révocation, expiration, empreinte incorrecte, libération de siège et limiteur; `/health` vérifie `SELECT 1`; `backup.ps1` charge `.env`, écrit atomiquement et signale les erreurs; migration, sauvegarde et restauration validées sur un cluster PostgreSQL 16 jetable réel.
- [x] Déployer le MVP HTTPS sur Vercel Hobby et Neon Free : API FastAPI en production sur `https://copro-auto-license-api.vercel.app`, PostgreSQL 18 à Francfort, migration appliquée, secrets sensibles injectés, `/health` vert et parcours distant activate → verify → refresh → status → deactivate validé.
- [x] Construire et tester le package Windows x64 `onedir`; les modes `licensed-offline` et `fresh-unlicensed` passent. Binaire corrigé vérifié : `dist-updated/CoproAuto/CoproAuto.exe`, SHA-256 `47659AD5E37B68E40B196D955423423EDFA79A1268D2269353761A97B1A7C530`.
- [x] Préparer le package testeur `dist-updated/CoproAuto` avec une clé d'essai hors ligne signée valable jusqu'au 19 août 2026; smoke tests réussis, binaire SHA-256 `6A4B41767FDEABF3337B08D4E15CFD312B46EA9251476A7DFCA384711BAA54F6`.
- [x] Reconstruire le package Windows avec la configuration publique du service en ligne; les smoke tests `licensed-offline` et `fresh-unlicensed` passent, binaire SHA-256 `6E7CEE01BB4EB8E7C2BEFF643E27276EE5A07E679409866A56D442A8B72E9D63` (non signé).
- [x] Reconstruire `dist-updated/CoproAuto` avec le thème clair validé et les états lisibles du bouton de licence; les smoke tests `licensed-offline` et `fresh-unlicensed` passent, binaire SHA-256 `76E61FC864242B2657198529BB758F9D564CE5326F3CC54E097132561DFE1134` (non signé).
- [x] Reconstruire `dist-updated/CoproAuto` après la cohérence UI/UX globale : licence, import DWG/DXF, validation, reflow à 1080 × 700 et toutes les catégories de `QMessageBox` vérifiés; QA visuelle source + binaire et deux smoke tests réussis, SHA-256 `D39DBE935DFEE2B34B0099CCF327CF2891C29870FDC7A42D11E32B06F3F27F5A` (non signé). L'ancien package est conservé dans `dist-updated/CoproAuto-pre-ui-ux-20260812`.
- [x] Construire le candidat Windows avec synchronisation administrative en ligne; les smoke tests `licensed-offline` et `fresh-unlicensed` passent, SHA-256 `2E075E07BBE9292F72C0B0C066556ACCE7E8C33966180C709F3C911F479CD35E` (non signé). Le candidat reste dans `dist-updated/CoproAuto-license-sync-candidate` jusqu'à la fermeture de l'ancien exécutable qui verrouille `dist-updated/CoproAuto`.
- [ ] Signer le package Windows avec un certificat de signature de code avant la première distribution commerciale. `packaging/sign_release.ps1` signe, horodate et vérifie; le certificat reste à acquérir.
- [ ] Tester sur un poste Windows propre réel, avec/sans AutoCAD et avec/sans réseau. Les deux démarrages automatisés `licensed-offline` et `fresh-unlicensed` passent sur le poste de développement via `packaging/smoke_test.ps1`.
- [x] Rédiger manuels utilisateur, dictionnaire technique, mapping des modèles et déploiement.
- [ ] Tester au moins trois dossiers réels et mesurer les résultats selon `docs/field_validation_protocol.md`; les dossiers autorisés et le visa métier restent à fournir.
- [ ] Faire valider par un conseil juridique local les projets `docs/commercial_license_agreement_draft.md`, `docs/trial_terms_draft.md` et `docs/privacy_notice_draft.md`, puis accomplir la formalité CNDP appropriée avant production.

## [EXECUTION_PLAN]

### Milestone 0 — Droits et références figés

- Accord écrit de propriété/exploitation.
- Six modèles inventoriés, copiés et approuvés.
- Dictionnaire et matrice documentaire approuvés.
- **Vérifiable :** aucune règle critique ni source documentaire ambiguë.

### Milestone 1 — Domaine exact et JSON

- Modèle métier, surfaces doubles, calculs et validations.
- Sauvegarde atomique et rechargement.
- **Vérifiable :** Yasmin 71 donne exactement `3522/3239/3239` après un aller-retour JSON.

### Milestone 2 — Workflow manuel complet

- Interface française projet/niveaux/parties/surfaces.
- Erreurs, avertissements et aperçu.
- **Vérifiable :** dossier complet réalisable sans CAD.

### Milestone 3 — Six documents fidèles

- Modèles contrôlés, mappings et contenu variable déterministe.
- Génération transactionnelle et contrôles croisés.
- **Vérifiable :** six sorties Yasmin 71 visuellement et numériquement conformes.

### Milestone 4 — Import CAD complémentaire

- DWG→DXF, `TABLE`, repli spatial et écran de comparaison.
- **Vérifiable :** import Yasmin 71 contrôle/préremplit sans écrasement silencieux.

### Milestone 5 — Licence locale et service minimal

- API, PostgreSQL, Ed25519, client desktop et administration CLI.
- Essais 6 mois/30 jours, plans individuel/office.
- **Vérifiable :** activation, hors-ligne, grâce, expiration, renouvellement et déplacement fonctionnent.

### Milestone 6 — Robustesse et sécurité

- Tests complets, logs, reprise réseau, secrets et sauvegardes.
- **Vérifiable :** panne réseau ou expiration ne corrompt jamais un projet et n’empêche pas sa consultation.

### Milestone 7 — Distribution et terrain

- Package Windows, documentation et déploiement licence HTTPS.
- Validation IGT sur trois dossiers réels.
- **Vérifiable :** installation autonome et six documents acceptables sur postes cibles.

### Milestone 8 — Préparation commerciale

- Contrat de licence, confidentialité, support et renouvellement.
- Première licence bureau et première licence individuelle émises manuellement.
- **Vérifiable :** vente exploitable sans portail de paiement et sans accès aux données client.

## Plan approuvé à exécuter — Tableau de bord privé des licences (août 2026)

### [TECH_STACK]

- Python 3.13 et FastAPI 0.139.x sur le service Vercel existant; mise à jour corrective prévue de `0.139.0` vers la version stable `0.139.2`.
- SQLAlchemy 2.0.51 et psycopg 3.3.4 conservés pour Neon PostgreSQL 18.
- Interface HTML/CSS/JavaScript native servie par FastAPI, sans framework frontend ni chaîne de compilation supplémentaire.
- Authentification administrateur unique par mot de passe PBKDF2-HMAC-SHA256, session HMAC courte en cookie `Secure`, `HttpOnly`, `SameSite=Strict`, jeton CSRF et limitation des tentatives en PostgreSQL.
- Secrets supplémentaires uniquement dans Vercel : `ADMIN_PASSWORD_HASH` et `ADMIN_SESSION_SECRET`; aucun secret dans le navigateur, Git ou Neon en clair.

### [SYSTEM_FLOW]

1. L'administrateur ouvre `/admin` et voit l'écran de connexion.
2. Le serveur vérifie le mot de passe et la limite de tentatives, puis émet une session sécurisée de huit heures.
3. Le tableau de bord affiche les totaux et la liste des licences avec organisation, indice de clé, plan, statut, sièges, activations et échéance.
4. La création d'une licence demande le client, le plan, les sièges, la durée et le statut d'essai; la clé brute est affichée une seule fois pour copie.
5. L'administrateur peut renouveler, révoquer ou réactiver une licence après confirmation.
6. La fiche d'une licence affiche ses appareils; un siège peut être libéré après confirmation.
7. Chaque mutation est protégée par CSRF, enregistrée dans `audit_events` et immédiatement reflétée dans l'interface.
8. La déconnexion invalide le cookie côté navigateur.

### [ARCHITECTURE]

- `license_server/src/license_server/admin_web.py` : routes HTML/JSON, contrôle de session et orchestration des actions administratives.
- `license_server/src/license_server/admin_auth.py` : hachage/vérification du mot de passe, signature de session, CSRF et limiteur de connexion.
- `license_server/src/license_server/admin_service.py` : requêtes de liste/détail et mutations réutilisant `LicenseService`.
- `license_server/src/license_server/static/admin.html` : application visuelle unique, responsive et accessible; aucun secret ni accès direct à Neon.
- `license_server/src/license_server/models.py` et migration idempotente : tentatives de connexion administrateur; les licences, activations et audits existants restent la source de vérité.
- `license_server/src/license_server/app.py` : montage du module administrateur sur la même application Vercel.
- `license_server/tests/` : tests d'authentification, CSRF, limitation, permissions, création, renouvellement, révocation, réactivation, libération de siège et absence de fuite de clé.

### Journalisation

- Conserver les logs structurés standards vers la sortie Vercel, collectés de façon non bloquante par la plateforme.
- Journaliser succès/échec de connexion et mutations avec identifiants techniques, jamais le mot de passe, la clé brute, les cookies, le pepper ou la clé privée.
- Conserver les actions métier durables dans `audit_events` au sein de la même transaction que la mutation.

### [ORPHANS & PENDING]

Aucun élément technique restant pour le tableau de bord. Le test terrain sur deux ordinateurs reste suivi dans le jalon global de distribution.

### Jalons du tableau de bord

1. **Sécurité vérifiable :** connexion correcte acceptée, mauvais mots de passe limités, cookie/CSRF valides, routes administratives refusées sans session.
2. **Gestion vérifiable :** créer, lister, renouveler, révoquer, réactiver et libérer un siège depuis l'interface; la clé brute n'est visible qu'à la création.
3. **Interface vérifiable :** parcours complet en français sur ordinateur et fenêtre étroite, avec états chargement/vide/erreur et confirmations destructives.
4. **Déploiement vérifiable :** migration Neon appliquée, Preview verte, Production verte, `/health` intact et aucune erreur runtime après le smoke test.

## Plan proposé — cohérence UI/UX globale du desktop (août 2026)

### [ASSUMPTIONS & DECISIONS]

- La référence claire blanche approuvée devient l’autorité visuelle pour toutes les surfaces appartenant à Copro Auto.
- Le périmètre couvre la fenêtre principale, les deux onglets, le panneau de contrôle, le dialogue de licence, toutes les catégories de `QMessageBox` (information, succès, avertissement, erreur critique, question, licence requise et modifications non enregistrées), la comparaison DWG/DXF, les menus/calendriers/popups et tous les états interactifs.
- Les sélecteurs de fichiers et dossiers restent natifs Windows et suivent donc le thème du système; ils ne sont pas remplacés par une implémentation personnalisée.
- Aucun comportement métier, calcul, format JSON, génération DOCX, protocole de licence ou import CAD ne change.
- Aucun nouveau framework, paquet d’icônes ou moteur web n’est ajouté. Les icônes nécessaires utilisent les ressources Qt/Windows existantes.
- Le mode sombre reste une palette interne non exposée; aucun sélecteur de thème n’est ajouté dans ce lot.
- La fenêtre doit rester exploitable à 1080 × 700 et avec les facteurs d’échelle Windows usuels, sans chevauchement ni commande inaccessible.

### [TECH_STACK]

- Python 3.13.12 x64 conservé.
- PySide6 6.11.1 conservé; il s’agit de la version stable courante vérifiée en août 2026.
- QSS global tokenisé conservé; aucune combinaison `QPalette` + QSS susceptible de produire des résultats divergents.
- PyInstaller 6.21.0 conservé pour le package `onedir`; version stable courante vérifiée en août 2026.
- pytest 9.1.1 et `QTest` conservés pour les régressions fonctionnelles, géométriques et d’interaction.

### [SYSTEM_FLOW]

1. L’application applique le thème clair avant de créer toute fenêtre.
2. Toute fenêtre principale ou modale appartenant à Copro Auto reçoit un fond clair, un texte contrasté et, sous Windows, un chrome clair lorsque DWM le permet.
3. L’utilisateur crée, ouvre et saisit un dossier sans changement de logique métier.
4. Le panneau de contrôle rend succès, avertissements et erreurs avec texte, symbole et surface sémantique; les emplacements restent métier et français.
5. À largeur réduite, l’éditeur conserve les commandes et tables sans chevauchement; le panneau de contrôle garde une largeur bornée.
6. Le dialogue de licence montre un état lisible, une action principale claire, les actions secondaires regroupées et la désactivation isolée comme action destructive.
7. Tous les `QMessageBox` — information, succès, avertissement, erreur critique, question, licence requise et modifications non enregistrées — sont entièrement lisibles, localisés en français et conservent leurs valeurs de retour Qt.
8. La comparaison DWG/DXF distingue manquant/différent/identique, garde la saisie manuelle par défaut et offre des actions françaises cohérentes.
9. Les mêmes états sont rendus et vérifiés depuis le code source puis depuis le binaire packagé.

### [ARCHITECTURE]

- `src/copro_auto/ui/theme.py`
  - étendre les tokens sémantiques (`danger_soft`, `warning_soft`, `success_soft`, focus);
  - couvrir `QDialog`, `QMessageBox`, `QDialogButtonBox`, popups, calendriers, menus, vues et barres de défilement verticales/horizontales;
  - ajouter un petit filtre d’événements Windows pour demander un chrome clair aux fenêtres top-level Copro Auto.
- `src/copro_auto/ui/dialogs.py`
  - centraliser information, succès, avertissement, erreur critique, question, licence requise et modifications non enregistrées;
  - traduire explicitement OK/Oui/Non/Enregistrer/Ignorer/Annuler;
  - appliquer les rôles visuels sans changer les réponses `QMessageBox.StandardButton`.
- `src/copro_auto/ui/license_dialog.py`
  - structurer titre, aide, statut sémantique, champ de clé et groupes d’actions;
  - définir libellé associé, ordre de tabulation, bouton par défaut et zone destructive séparée.
- `src/copro_auto/ui/import_review.py`
  - corriger le fond, les états de comparaison, la densité du tableau, l’avertissement et les boutons français;
  - conserver exactement les choix manuels/CAD et leur application actuelle.
- `src/copro_auto/ui/project_editor.py`
  - remplacer les minimums de tables incompatibles par des facteurs d’étirement et minimums sûrs;
  - garantir la séparation entre en-têtes, tables, barres de défilement et texte d’aide à 1080 × 700.
- `src/copro_auto/ui/main_window.py`
  - borner la largeur du panneau de contrôle et préserver la priorité de l’éditeur;
  - utiliser les messages centralisés pour tous les flux existants.
- `src/copro_auto/ui/validation_panel.py`
  - rendre les trois sévérités accessibles et traduire les chemins techniques en emplacements métier.
- `tests/test_ui.py`
  - ajouter chaque catégorie de `QMessageBox`, les autres états de dialogue, la localisation, les rôles sémantiques, le focus et les non-chevauchements à taille minimale.

Le domaine, les services, les modèles de documents et le serveur de licences restent hors de cette modification.

### Journalisation

- Conserver la journalisation existante, non bloquante et sans donnée de licence brute.
- Ajouter uniquement des logs `DEBUG` pour le mode de mise en page appliqué et les décisions de dialogue utiles au diagnostic; aucun événement de survol/focus n’est journalisé.

### [ORPHANS & PENDING]

- [x] Étendre le QSS et le chrome clair à toutes les fenêtres top-level Copro Auto.
- [x] Centraliser, éclaircir, localiser et tester toutes les catégories de `QMessageBox`, sans exception.
- [x] Recomposer le dialogue de licence et ses états actif/inactif/invalide/expiré/hors ligne.
- [x] Recomposer la comparaison DWG/DXF et ses états identique/différent/manquant.
- [x] Corriger le reflow de Niveaux/Parties et le partage de largeur avec le panneau de contrôle.
- [x] Ajouter les états sémantiques du panneau de validation.
- [x] Tester clavier, focus visible, libellés associés et facteur d’échelle Windows.
- [x] Capturer la matrice visuelle avant/après et obtenir `final result: passed` dans `design-qa.md`.
- [x] Rejouer tous les tests, reconstruire le package Windows et exécuter les deux smoke tests.
- [x] Présenter le package final et sa matrice visuelle à l’utilisateur pour validation sur son écran principal.

### Jalons vérifiables

1. **Fondations visuelles :** toutes les surfaces app-owned sont claires et contrastées; menus, calendriers, popups et scrollbars suivent les tokens.
2. **Dialogues fiables :** licence et chaque catégorie de `QMessageBox` sont lisibles, français, accessibles au clavier et conservent les comportements actuels.
3. **Flux CAD cohérent :** comparaison DWG/DXF claire, compacte, sémantique et fonctionnellement inchangée.
4. **Reflow desktop :** Projet et Niveaux/Parties ne se chevauchent pas à 1080 × 700; les tables restent éditables et le panneau de contrôle ne prend pas l’espace de travail.
5. **Accessibilité vérifiable :** focus, ordre de tabulation, libellés, contrastes et états non dépendants de la couleur passent les tests prévus.
6. **Livraison vérifiée :** QA visuelle source + binaire réussie, suite pytest verte, deux smoke tests verts et `dist-updated/CoproAuto` reconstruit.

## Plan proposé — cinq documents métier entièrement dynamiques (août 2026)

Ce plan est approuvé uniquement après confirmation explicite de l'utilisateur. Il ne déclenche ni implémentation, ni reconstruction du binaire, ni commit, ni push, ni déploiement. Le travail restera local jusqu'à une décision ultérieure distincte.

### [ASSUMPTIONS & DECISIONS]

- Les six documents fournis restent les références métier. Les deux références PV sont assemblées en un seul document livré, ce qui produit désormais cinq sorties : `PV_Division.docx`, `Reglement_Copropriete.docx`, `Tableau_A.docx`, `Tableau_B.docx` et `Tableau_Recapitulatif.docx`.
- `PV_Division.docx` contient d'abord PV Division 1, puis un saut de page/section contrôlé, puis PV Division 2. Les originaux restent intacts.
- Un seul bloc client est saisi par dossier et alimente à la fois PV Division et le Règlement de copropriété. Il contient : nom complet, CNIE, adresse/domicile, qualité et date d'expiration de la CNIE.
- La phrase client est générée de façon déterministe sous une forme neutre : `M./Mme {nom}, CNIE n° {cnie}, demeurant à {adresse}, agissant en qualité de {qualité}, carte valable jusqu'au {date}.` Aucun texte juridique libre n'est inventé.
- Le dossier reçoit un champ heure, saisi au format `HH:mm`. La date et l'heure produisent toute la phrase française du PV, y compris le jour de la semaine, le jour, le mois, l'année et l'heure en lettres. À minute zéro, la phrase se termine par exemple par `à dix heures`; sinon les minutes sont ajoutées en lettres.
- `Conservation foncière`, `Préfecture` et `Commune` sont trois données indépendantes. Le défaut actuel est confirmé : le mapping global de `Meknès` utilise `identity.commune or identity.prefecture`, ce qui peut remplacer la préfecture par la commune. Il sera supprimé au profit de marqueurs explicites et ciblés.
- Le nom du topographe remplace aussi la forme longue statique `Mr DAANOUNI ABDELAAZIZ`; le système ne dépend plus d'une liste fragile de noms littéraux historiques.
- Les quatre limites `Nord-Est`, `Nord-Ouest`, `Sud-Est` et `Sud-Ouest` deviennent des champs explicites de l'interface et alimentent le Règlement de copropriété.
- La consistance générale et la hauteur totale alimentent la description de l'immeuble. La section `DESCRIPTION DE L’IMMEUBLE ET DE LA DIVISION PAR NIVEAU ET PAR PARTIE` est entièrement produite à partir des niveaux et parties réellement saisis.
- Aucun niveau `Terrasse`, paragraphe, titre ou tableau correspondant n'est généré si ce niveau n'existe pas dans le projet. À l'inverse, toute terrasse réellement saisie est générée normalement.
- Les cotes début/fin peuvent être négatives ou positives. Elles sont toujours écrites avec un signe et deux décimales séparées par une virgule : `-2,20`, `+0,40`, `+3,80`. Zéro s'écrit `+0,00`. Les surfaces conservent leur format métier actuel.
- Les libellés visibles deviennent `Hauteur` et `Surface`. Les noms internes existants `interior_height` et `inside_title` restent inchangés afin de préserver les calculs et de limiter la migration.
- Dans Tableau A et Tableau B, les parties privatives reçoivent une séquence globale `Nom propriété-1`, `Nom propriété-2`, etc. Les parties communes restent sans suffixe. Tableau B suit exactement l'ordre des parties privatives de Tableau A.
- Le texte placé sous le logo de Tableau A et Tableau B reçoit la valeur de Préfecture, conformément au besoin exprimé. Dans le Tableau récapitulatif, les occurrences d'`Al Ismaïlia` reçoivent aussi la Préfecture.
- Le format JSON passe de `schema_version: 1` à `schema_version: 2`. Les dossiers v1 restent ouvrables : les nouveaux champs sont initialisés proprement, puis sauvegardés en v2 sans modifier les niveaux, parties, UUID ni calculs existants.
- Les données métier restent locales. Aucun changement du serveur de licences, de Neon, de Vercel ou du tableau de bord administrateur n'appartient à ce lot.

### [TECH_STACK]

- Python 3.13.12 x64, PySide6 6.11.1, python-docx 1.2.0, lxml 6.1.1, PyInstaller 6.21.0 et pytest 9.1.1 sont conservés.
- Aucun nouveau paquet n'est nécessaire : le français de la date/heure, les cotes, la migration JSON et l'assemblage DOCX sont déterministes et peuvent être réalisés avec la bibliothèque standard et les dépendances déjà verrouillées.
- Python 3.13.14 est disponible comme correctif plus récent de la branche 3.13, mais la mise à niveau du runtime est séparée de cette modification fonctionnelle afin de réduire le risque de régression et de garder un diff ciblé.

### [SYSTEM_FLOW]

1. L'utilisateur saisit l'identité foncière, la conservation foncière, la date et l'heure, le topographe, le client, les quatre limites, les niveaux et les parties.
2. L'éditeur construit un `Project` v2 sans perdre les UUID ni les valeurs d'un dossier v1 ouvert.
3. La validation signale les nouveaux champs requis avec des emplacements métier lisibles avant toute génération.
4. Le service prend un seul instantané immuable du projet validé et calcule une seule fois les agrégats et les tantièmes.
5. Les formateurs déterministes produisent les textes partagés : identité ciblée, client, date/heure française, cotes signées à deux décimales et descriptions des niveaux.
6. Le moteur remplit le modèle PV combiné, le Règlement et les trois tableaux à partir de ce même instantané. Les blocs de niveaux sont clonés uniquement pour les niveaux présents.
7. Les cinq fichiers sont d'abord écrits dans un dossier temporaire, contrôlés structurellement et croisés, puis déplacés atomiquement vers le dossier choisi. Une erreur ne laisse pas une livraison partielle.
8. L'application affiche et documente partout cinq documents, sans reconstruction du package distribué tant que la validation locale n'est pas terminée.

### [ARCHITECTURE]

- `src/copro_auto/domain/models.py`
  - ajouter `project_time` et `land_registry_office` à l'identité du dossier;
  - ajouter un petit objet métier `ClientInformation` regroupant nom, CNIE, adresse, qualité et expiration;
  - conserver `boundaries` avec quatre clés canoniques (`northeast`, `northwest`, `southeast`, `southwest`) pour éviter une hiérarchie inutile.
- `src/copro_auto/infrastructure/json_repository.py`
  - écrire le schéma v2;
  - migrer explicitement v1 → v2 avec valeurs vides/defaults sûrs;
  - conserver la lecture stricte des types, des décimales et des UUID.
- `src/copro_auto/domain/validation.py`
  - valider les données nécessaires aux cinq documents : conservation, heure, client et quatre limites;
  - continuer d'accepter les cotes négatives et imposer seulement la cohérence `cote fin > cote début` lorsque les deux existent.
- `src/copro_auto/ui/project_editor.py`
  - ajouter les champs dans des groupes lisibles `Identification`, `Client` et `Limites` au sein de la zone défilante existante;
  - utiliser un `QTimeEdit` en `HH:mm`;
  - lire et réécrire tous les nouveaux champs sans supprimer `boundaries` lors de `project()`;
  - remplacer uniquement les libellés `Hauteur libre` par `Hauteur` et `Dans titre` par `Surface`.
- `src/copro_auto/documents/mappings.py`
  - supprimer les remplacements globaux ambigus fondés sur des valeurs exemples telles que `Meknès`;
  - ajouter des formateurs purs et testables pour date/heure française, client et cote signée à deux décimales;
  - construire une carte de marqueurs uniques, un marqueur par champ et par emplacement sémantique lorsque nécessaire.
- `src/copro_auto/documents/docx_renderer.py`
  - remplir les cellules, paragraphes, en-têtes, pieds de page et zones de texte par marqueurs explicites;
  - remplacer les quatre emplacements de niveaux codés en dur par un bloc prototype cloné pour chaque niveau réel, puis supprimer le prototype et tous les résidus inutilisés;
  - produire la description dynamique de l'immeuble, la consistance, les limites, le client et les parties dans le Règlement;
  - appliquer la numérotation `-N` uniquement aux parties privatives de Tableau A/B, à partir d'une séquence partagée.
- `src/copro_auto/application/document_service.py` et `src/copro_auto/ui/main_window.py`
  - remplacer les deux sorties PV par `PV_Division.docx`;
  - mettre à jour les compteurs, boutons, dialogues, messages et contrôles transactionnels de six vers cinq.
- `resources/templates/`
  - garder les six originaux inchangés;
  - préparer un modèle runtime autoritaire `pv_division.docx` composé de PV1 puis PV2, avec séparation de section/page préservant la mise en page;
  - introduire des marqueurs explicites et des blocs prototypes dans les copies runtime seulement;
  - ne plus packager deux modèles PV concurrents comme deux sorties distinctes.
- `tests/fixtures/` et `tests/`
  - ajouter un dossier de régression dérivé de `T.117564.59.json`;
  - couvrir la migration v1/v2, la persistance UI, les champs requis, les cinq noms de sortie, l'ordre PV1→PV2 et l'atomicité;
  - vérifier Préfecture ≠ Commune ≠ Conservation, topographe, client, date/heure, consistance et quatre limites dans chaque document concerné;
  - vérifier `-2,20`, `+0,40`, deux décimales, absence de `+-`, et absence de bloc Terrasse lorsque le niveau n'existe pas;
  - vérifier la séquence privée Tableau A/B et l'absence de suffixe sur les lignes communes;
  - extraire les valeurs critiques du corps, des tableaux, des en-têtes/pieds et des zones de texte OOXML.
- `docs/data_dictionary.md`, `docs/template_mapping.md`, `docs/user_manual.md` et `docs/field_validation_protocol.md`
  - documenter les nouveaux champs, le schéma v2, les cinq sorties et la matrice exacte champ → document → emplacement;
  - supprimer les instructions opérationnelles qui parlent encore de six fichiers lorsque le nombre de sorties est concerné.

### Journalisation

- Conserver `QueueHandler`/`QueueListener`, la rotation et l'absence de blocage de l'interface.
- Journaliser la version de schéma lue/migrée, les cinq types de documents, le nombre de niveaux/parties rendus, les empreintes des modèles et les résultats des contrôles.
- Ne jamais journaliser le nom du client, la CNIE, l'adresse, le texte juridique complet ni le contenu des documents.

### [ORPHANS & PENDING]

- [x] Obtenir l'approbation explicite de ce plan avant toute modification de code ou de modèle.
- [x] Figer la phrase client exacte avec la formulation neutre proposée; toute modification ultérieure doit rester un changement de modèle, pas une concaténation dispersée.
- [x] Créer et valider le jeu de régression basé sur `T.117564.59.json` et les six documents annotés fournis.
- [x] Implémenter et tester la migration JSON v1 → v2.
- [x] Implémenter les nouveaux champs UI et la persistance complète, y compris les quatre limites déjà présentes dans le domaine.
- [x] Corriger les mappings Préfecture/Commune/Conservation, topographe, date/heure, client, consistance et limites.
- [x] Remplacer les niveaux statiques par des blocs dynamiques sans Terrasse fantôme.
- [x] Assembler le modèle PV unique et réduire la transaction à cinq sorties.
- [x] Appliquer et vérifier les suffixes privés cohérents dans Tableau A/B.
- [x] Mettre à jour les tests et la documentation métier.
- [x] Rendre avec Microsoft Word et inspecter visuellement à la résolution native les 19 pages des cinq sorties, y compris polices, tailles, emplacements, accents français, tableaux, sauts de page et pieds de page.
- [ ] Faire valider les cinq documents par le topographe avant toute reconstruction, distribution ou mise en production.
- [x] Conserver hors périmètre : serveur de licences, dashboard, Neon, Vercel, package `dist-updated`, commit, push et déploiement.

### Jalons vérifiables

1. **Référence de régression figée** — le JSON fourni ouvre sans perte et les défauts actuels sont reproduits par des tests rouges ciblés : Préfecture incorrecte, champs statiques, Terrasse fantôme et six sorties.
2. **Données v2 et interface complètes** — création, sauvegarde et réouverture conservent heure, conservation, client et quatre limites; un dossier v1 reste ouvrable; les libellés `Hauteur` et `Surface` sont visibles.
3. **Texte déterministe correct** — les mappings ciblés distinguent Préfecture/Commune/Conservation, remplacent le topographe, génèrent la phrase date/heure et formatent chaque cote avec signe, virgule et deux décimales.
4. **PV et Règlement réellement dynamiques** — client, limites, consistance et description proviennent du projet; le nombre et l'ordre des blocs correspondent exactement aux niveaux présents; aucune Terrasse fantôme ne subsiste.
5. **Cinq sorties cohérentes** — le PV unique respecte l'ordre PV1 puis PV2, Tableau A/B partagent la même séquence privée, les lignes communes restent sans suffixe et la génération transactionnelle livre exactement cinq fichiers.
6. **Validation locale complète** — suite automatisée verte, contrôles OOXML verts, rendu visuel des cinq sorties inspecté page par page et aucune régression sur calculs, licences, import CAD ou sauvegarde.
7. **Visa métier avant livraison** — le topographe approuve les cinq documents générés à partir du dossier réel; seulement après ce visa pourra être planifiée séparément une reconstruction ou un déploiement.

### État d’exécution locale — 13 août 2026

- Schéma v2, migration v1, nouveaux champs UI, cinq sorties, PV fusionné, mappings ciblés, niveaux dynamiques, suffixes privés et documentation sont implémentés.
- Le formulaire Projet impose désormais explicitement la surface claire au contenu et au viewport défilant; `QTimeEdit` partage les mêmes états clair, focus et sélection que les autres champs, sans dépendre de la palette sombre de Windows.
- Un même indice cadastral peut désormais être réutilisé sur plusieurs niveaux (par exemple `1A` au S/SOL et au Rez-de-chaussée). Seule la répétition du même indice dans un même niveau reste une erreur bloquante.
- Les tableaux conservent désormais la `Consistance` courte exactement saisie (`Appartement`, `Garage`, etc.). Les paragraphes narratifs PV/Règlement combinent systématiquement cette consistance, la surface calculée, la description détaillée comme complément et les observations, au lieu de remplacer la consistance par la description.
- Pour la version de test topographe d’août 2026, l’entrée DWG/DXF est retirée de la navigation et du package à la demande de l’utilisateur. La saisie manuelle et les cinq documents restent le périmètre de validation; les adaptateurs CAD demeurent dans le dépôt pour une réactivation ultérieure.
- Le package topographe local est construit avec une configuration de ressources isolée : la clé publique d’essai hors ligne est embarquée sans modifier la configuration en ligne du dépôt, et aucun secret de signature n’entre dans le dossier distribué. Les smoke tests `licensed-offline` et `fresh-unlicensed` passent sur le binaire allégé. Le ZIP final `CoproAuto-Topographe-Test-2026-08-13.zip` contient 293 entrées, pèse 59 148 289 octets et porte le SHA-256 `A11CE60E27637DD6F7640328E8426C6D7AD90C186B078DA1D80BA4704AEB878C`.
- La suite complète passe : `71 passed, 2 skipped`; les deux tests sautés exigent la base PostgreSQL réelle et sont sans rapport avec ce lot documentaire.
- Les cinq fichiers QA sont générés depuis `T.117564.59.json` enrichi des nouveaux champs dans `work/qa-t117564-fidelity-20260813-v5/`. Les contrôles OOXML, métier, style, numérotation, caractères français et mise à jour des champs passent.
- Les 19 pages ont été rendues individuellement par Microsoft Word puis inspectées à la résolution native : PV 2 pages, Règlement 11 pages, Tableau A 2 pages, Tableau B 2 pages et Tableau récapitulatif 2 pages. Les polices, tailles, emplacements, tableaux et accents sont préservés; aucun `?` de conversion, niveau fantôme, page blanche finale ni numéro de page tronqué ne subsiste.
- Le seul gate restant est le visa métier du topographe. Aucun binaire, commit, push ou déploiement n’a été produit dans ce lot local.

## Plan proposé — import CAD vers dossier prérempli avec revue obligatoire (août 2026)

Ce plan traduit les trois décisions approuvées le 24 août 2026. Son implémentation locale a été autorisée et exécutée le même jour. Aucun packaging ni déploiement n’a été déclenché.

### [ASSUMPTIONS & DECISIONS]

- Deux parcours coexistent : `Créer par saisie manuelle` reste entièrement fonctionnel; `Importer depuis DWG/DXF` produit un brouillon prérempli soumis à revue.
- Sur un dossier existant, l’import devient une comparaison manuelle ↔ CAD et ne remplace jamais une valeur sans choix explicite.
- Le nombre de plans, niveaux et tableaux de contenances est dynamique : 2, 3, 4 ou davantage. Aucun nom ni nombre de niveaux n’est codé en dur.
- Le premier périmètre extrait l’identité disponible, les niveaux, les cotes, la hauteur, les lignes de chaque tableau, l’indice, la nature, les surfaces, le surplomb, la consistance et les observations.
- Les libellés de pièces peuvent proposer une `Description détaillée`, mais cette proposition reste non sélectionnée ou marquée incertaine tant que son rattachement géométrique à une partie n’est pas suffisamment fiable.
- Les valeurs absentes du dessin restent vides et clairement signalées. Le système n’invente ni information administrative, ni donnée client, ni limite, ni texte juridique.
- Le topographe complète seulement les champs factuels manquants. Le texte juridique continue d’être produit exclusivement par les modèles DOCX déterministes déjà validés.
- La version initiale lit les surfaces écrites dans les tableaux. Elle ne recalcule pas de surface légale à partir des polylignes, hachures ou pièces dessinées.
- Un DXF est lu directement. Un DWG est converti localement avec AutoCAD Core Console lorsqu’il est disponible; sinon l’utilisateur reçoit une instruction claire pour exporter en DXF R2018.
- Aucun convertisseur tiers, OCR, LLM, service cloud ou appel réseau n’est ajouté.
- Les plans sources ne sont jamais modifiés. L’application conserve dans le JSON les décisions et une empreinte du fichier, pas une copie silencieuse du DWG/DXF.
- Le fichier de référence `Les Planches.dxf` contient environ 3 039 entités dans Model Space, dont 546 `TEXT`, 4 `MTEXT`, 1 226 `LINE` et 667 `LWPOLYLINE`. Ses tableaux sont dessinés avec du texte et des lignes, pas avec des entités `TABLE` natives.
- Le même fichier contient quatre tableaux/niveaux exploitables, mais l’algorithme sera validé avec des fixtures à 2, 3 et 5 niveaux afin de prouver que le compte est dynamique.
- Le DXF de référence déclare `ANSI_1252` tout en contenant des octets UTF-8. La lecture doit préserver `Propriété`, `Préfecture` et `Meknès`; tout caractère `�` ou mojibake est une erreur d’import, jamais une valeur acceptable.
- La conservation foncière, le topographe, la date/heure, le client et les quatre limites ne sont pas présents de manière fiable dans le plan fourni; ils restent des champs manuels requis avant génération.
- Le serveur de licences, le dashboard, Neon, Vercel et les modèles DOCX sont hors périmètre de ce lot.

### [TECH_STACK]

- Conserver Python 3.13.12, PySide6 6.11.1, ezdxf 1.4.4, `Decimal`, `hashlib`, `subprocess`, `pathlib`, pytest 9.1.1 et PyInstaller 6.21.0 tels qu’ils sont verrouillés dans le dépôt.
- Aucun nouveau paquet n’est nécessaire. L’inspection de versions en ligne a été bloquée par la politique réseau de la session; aucune mise à niveau non vérifiée n’est introduite dans ce changement fonctionnel.
- Réactiver `ezdxf` et ses dépendances requises dans le package seulement après validation locale du flux. Ne pas réintroduire tous les sous-modules optionnels de dessin/scientifiques qui avaient fortement ralenti le build.
- Conserver AutoCAD Core Console comme adaptateur DWG facultatif et DXF R2018 comme format interne d’analyse.
- Conserver le modèle local JSON atomique. Une migration de schéma v2 vers v3 est autorisée uniquement pour persister proprement provenance, confiance et décisions CAD; les dossiers v1/v2 restent ouvrables.

### [SYSTEM_FLOW]

1. **Choisir le mode de création**
   - `Saisie manuelle` ouvre le formulaire actuel sans dépendance CAD.
   - `Importer DWG/DXF` ouvre le sélecteur de dessin sur un nouveau dossier.
   - `Vérifier avec DWG/DXF` reste disponible sur un dossier déjà rempli.
2. **Préparer la source**
   - DXF : lecture read-only directe.
   - DWG : conversion dans un dossier temporaire unique via AutoCAD Core Console, puis suppression garantie du DXF temporaire.
   - Calculer taille, extension et SHA-256; ne jamais journaliser le texte métier du plan.
3. **Charger sans corruption**
   - Détecter le codage réel avant de faire confiance à `$DWGCODEPAGE`.
   - Refuser ou avertir sur tout texte contenant `�`, `Ã`, `Â` ou une perte d’accent détectable.
   - Aplatir les textes utiles des blocs/INSERT sans modifier les coordonnées du dessin.
4. **Détecter les feuilles et tableaux**
   - Rechercher toutes les variantes normalisées de `Tableau des Contenances`.
   - Construire une région autour de chaque ancre; déduire la grille des lignes horizontales/verticales et associer les textes aux cellules par coordonnées.
   - Si une grille est incomplète, utiliser un repli spatial par baselines et colonnes; marquer alors la confiance comme moyenne ou faible.
5. **Interpréter les données**
   - Extraire les champs d’identité disponibles sans doublons contradictoires.
   - Associer chaque tableau au titre de plan et à la phrase de cotes la plus proche.
   - Normaliser accents, espaces, décimales, unités, indices fragmentés (`4-4` + `a`), nature privative/commune et synonymes de colonnes.
   - Produire un nombre dynamique de brouillons de niveaux et de parties dans leur ordre spatial/altimétrique.
6. **Attribuer confiance et provenance**
   - `Élevée` : valeur contenue dans une cellule attendue et cohérente avec la grille/totaux.
   - `Moyenne` : valeur reconstruite par proximité spatiale ou normalisation non ambiguë.
   - `Faible` : rattachement possible mais ambigu, notamment les pièces et descriptions.
   - Chaque candidat conserve fichier, empreinte, handles/coordonnées et texte source localement.
7. **Présenter la revue**
   - Résumé : niveaux détectés, parties, erreurs, avertissements et champs administratifs absents.
   - Onglets dynamiques par niveau, jamais quatre panneaux fixes.
   - Chaque valeur affiche `Manuel`, `CAD`, `État`, `Confiance`, `Source` et `Valeur retenue`.
   - Permettre de corriger, ajouter, supprimer, fusionner, renommer et réordonner niveaux/parties avant application.
8. **Appliquer atomiquement**
   - Nouveau dossier : les valeurs CAD confirmées construisent le projet en une opération; Annuler ne change rien.
   - Dossier existant : la saisie manuelle reste sélectionnée par défaut; seules les décisions explicites sont appliquées.
   - Les UUID existants sont préservés lorsque des entités existantes sont conservées; les nouvelles entités reçoivent de nouveaux UUID stables.
9. **Compléter le dossier**
   - Le formulaire normal s’ouvre avec les données approuvées.
   - Le panneau de contrôle identifie les champs factuels encore manquants : conservation, topographe, date/heure, client, limites ou toute valeur CAD incertaine non acceptée.
10. **Valider et générer**
   - Les mêmes validations et calculs manuels restent l’autorité.
   - La génération des cinq DOCX n’est possible qu’après disparition des erreurs bloquantes.
   - Aucun chemin direct CAD → DOCX ne contourne la revue ou la validation.

### [ARCHITECTURE]

- `src/copro_auto/cad_import/dxf_loader.py`
  - chargement read-only, détection/réparation contrôlée du codage, expansion des textes de blocs et inventaire d’entités;
  - aucun parsing métier dans ce module.
- `src/copro_auto/cad_import/table_detector.py`
  - détection dynamique des ancres et régions de tableaux;
  - reconstruction de grilles et placement texte → cellule;
  - repli spatial explicite avec baisse de confiance.
- `src/copro_auto/cad_import/dxf_parser.py`
  - orchestration identité + niveaux + parties à partir des cellules et textes normalisés;
  - abandon des regex globales comme mécanisme principal, tout en les conservant comme repli ciblé.
- `src/copro_auto/cad_import/models.py`
  - modèles temporaires `CadCandidate`, `CadLevelDraft`, `CadPartDraft`, `CadImportDraft`, `CadConfidence`;
  - aucune mutation de `Project` pendant l’extraction.
- `src/copro_auto/cad_import/service.py`
  - conversion DWG, empreinte, import, comparaison, application atomique et nettoyage;
  - correspondance par chemin métier stable, pas par numéro de ligne UI.
- `src/copro_auto/domain/models.py`
  - étendre minimalement `FieldDecision` avec confiance et référence de source, ou introduire un enregistrement d’import compact;
  - migrer JSON uniquement si nécessaire pour la traçabilité approuvée.
- `src/copro_auto/ui/cad_import_wizard.py`
  - assistant unique pour import nouveau et comparaison existante;
  - pages `Résumé`, `Projet`, `Niveaux et parties`, `Champs manquants`;
  - édition et sélection accessibles au clavier, sans fenêtre gigantesque ni tableau horizontal illisible.
- `src/copro_auto/ui/main_window.py`
  - restaurer l’entrée CAD avec deux contextes : `Importer depuis DWG/DXF` pour un dossier vide et `Vérifier avec DWG/DXF` pour un dossier existant;
  - lancer l’analyse dans `QThreadPool` afin de ne jamais bloquer l’interface.
- `src/copro_auto/ui/project_editor.py`
  - réutiliser `set_project()` après application atomique; aucun second formulaire métier concurrent.
- `packaging/copro_auto.spec`
  - réinclure uniquement les modules ezdxf requis par le parseur réel;
  - conserver `onedir`, les ressources DOCX et les tests de démarrage avec/sans licence.
- `tests/fixtures/cad/`
  - fixtures synthétiques sans données client : tableaux explosés à 2, 3 et 5 niveaux, accents UTF-8/codepage contradictoire, indices fragmentés, grille partielle et valeurs manquantes;
  - le plan externe fourni reste intact et n’entre ni dans Git ni dans le package sans autorisation distincte.

### Journalisation

- Réutiliser `QueueHandler`/`QueueListener` et la rotation existante.
- Journaliser seulement : extension, octets, préfixe SHA-256, durée, nombres d’entités/tables/niveaux/parties, répartitions de confiance, avertissements codifiés et résultat de revue.
- Ne jamais journaliser propriété, titre foncier, textes du dessin, client, CNIE, adresse, limites ou descriptions.
- Les exceptions techniques conservent leur traceback dans le journal local, tandis que l’interface affiche une correction française exploitable.

### [ORPHANS & PENDING]

- [x] Approuver le périmètre : extraction complète disponible, niveaux dynamiques, pièces seulement suggérées, DWG via AutoCAD et revue sans écrasement.
- [x] Inspecter `Les Planches.dwg/.dxf` et confirmer que les tableaux de référence sont des primitives texte/ligne.
- [x] Obtenir l’approbation explicite de ce plan architectural avant toute implémentation.
- [x] Créer les modèles de brouillon CAD et les fixtures synthétiques 2/3/5 niveaux.
- [x] Corriger et tester le chargement des accents lorsque codepage déclaré et octets réels divergent.
- [x] Implémenter la détection dynamique de tous les tableaux et la reconstruction géométrique de leurs cellules.
- [x] Parser identité, niveaux, cotes, hauteur, parties, surfaces, consistances et observations avec confiance/provenance.
- [x] Implémenter le rapprochement des pièces comme suggestions non fiables par défaut.
- [x] Remplacer le dialogue limité à quatre champs par l’assistant de revue dynamique.
- [x] Restaurer les actions CAD dans la fenêtre principale sans bloquer l’interface.
- [x] Garantir application atomique, annulation sans mutation, préservation des UUID et migration JSON rétrocompatible.
- [x] Tester DWG avec AutoCAD présent/absent et nettoyage systématique des fichiers temporaires.
- [x] Vérifier le parcours complet : import → revue → complétion manuelle → contrôle → cinq DOCX.
- [x] Rejouer la suite complète et l’inspection UI locale; ne reconstruire aucun package avant validation utilisateur distincte.
- [x] Recueillir au moins deux autres DXF de structures différentes avant de déclarer l’extracteur généraliste.
- [x] Corriger l’extraction séparée de la préfecture et de la commune observée dans `EX 1` et `EX 2`.
- [x] Signaler et représenter sans fausse précision les niveaux contenant plus de deux cotes.
- [x] Fusionner les segments de bordure des tableaux, associer titres/cotes hors bordure et ordonner les feuilles horizontales comme dans `EX 3`.
- [x] Adapter les colonnes à en-têtes fusionnés et abaisser la confiance lorsque des colonnes ou consistances restent incomplètes.
- [x] Rejouer les quatre DXF terrain, le parcours cinq DOCX et toute la suite automatisée après correction.
- [ ] Faire valider les résultats d’extraction et les cinq documents par le topographe.

### État d’exécution locale — 24 août 2026

- Le bouton `Appliquer les choix` de la revue CAD est connecté directement à l’application atomique du brouillon; un test UI reproduit le clic réel et vérifie la fermeture acceptée ainsi que la création du projet relu.
- Les plans terrain `Les Planches`, `EX 1`, `EX 2` et `EX 3` passent le parcours revue → application → JSON → validation → cinq DOCX. Les résultats respectifs sont 4/15, 5/18, 4/21 et 8/44 niveaux/parties; `EX 3` conserve toutes ses consistances et l’ordre Sous-sol → Terrasse.
- Les consistances multiligne de `EX 3` restent attachées à leur indice : les continuations telles que `cage d’ascenseur` ne migrent plus vers la partie suivante.
- `EX 1` extrait désormais `Meknes`/`Ait Ouallal`, `EX 2` extrait `Meknès`/`Ait Ouallal`, et les libellés génériques `Parties Communes` ne peuvent plus devenir une fausse commune.
- Les phrases à plusieurs cotes utilisent leurs bornes extérieures, laissent la hauteur à confirmer et affichent un avertissement dédié avec confiance moyenne.
- Le DXF `Les Planches.dxf` est lu sans corruption d’accents et produit dynamiquement 4 niveaux, 15 parties et les indices composés attendus. Les cotes, surfaces dans le titre, surplombs, consistances et observations sont reconstruits depuis les grilles texte/ligne.
- Les fixtures synthétiques prouvent les comptes dynamiques à 2, 3 et 5 niveaux, la réparation codepage/UTF-8, les indices fragmentés et le repli spatial lorsque la grille est incomplète.
- L’assistant de revue comporte Résumé, Projet, Niveaux et parties et Champs manquants. Les suggestions de pièces restent de confiance faible et désactivées par défaut.
- L’application du brouillon construit une copie atomique. Annuler conserve le projet byte-for-byte; un dossier existant garde ses valeurs et UUID tant que le remplacement explicite n’est pas sélectionné.
- Le schéma JSON v3 conserve confiance, source, handles et empreinte tout en ouvrant les dossiers v1/v2.
- Le flux DXF → revue → complétion → validation → cinq DOCX est couvert automatiquement. Suite complète : `89 passed, 2 skipped`; les deux sauts exigent PostgreSQL réel et sont hors de ce lot.
- AutoCAD Core Console 2019 est détecté, mais le DWG de référence dépasse le délai même avec profil temporaire isolé. Le chemin DWG est donc best-effort : arrêt à 90 secondes, nettoyage intégral et instruction DXF R2018. Le DXF direct reste le chemin terrain vérifié.
- Le package PyInstaller sait de nouveau inclure `ezdxf`/`numpy`, mais aucun binaire n’a été reconstruit et aucun code n’a été déployé conformément à la consigne utilisateur.

### Jalons vérifiables

1. **Chargeur fiable** — le DXF de référence restitue les accents exacts, inventorie les entités et ne modifie pas la source; DWG sans AutoCAD explique l’export DXF requis.
2. **Tables dynamiques** — les fixtures à 2, 3 et 5 niveaux produisent exactement 2, 3 et 5 brouillons, sans nom ni compte codé en dur; les cellules et indices fragmentés sont reconstruits.
3. **Brouillon métier complet** — identité disponible, niveaux, cotes, hauteurs, parties, surfaces, consistances et observations sont typés avec provenance et confiance; aucun champ absent n’est inventé.
4. **Revue sûre** — nouveau dossier et dossier existant partagent le même assistant; Annuler laisse le projet byte-for-byte inchangé et aucune valeur manuelle n’est écrasée implicitement.
5. **Intégration métier** — après approbation, le formulaire normal reçoit les valeurs choisies, affiche les champs administratifs manquants et conserve calculs, tantièmes et validation actuels.
6. **Parcours complet** — un projet extrait, complété manuellement et validé génère exactement les cinq DOCX sans différence de mise en forme par rapport au flux manuel.
7. **Préparation terrain** — au moins trois projets de structures différentes passent les contrôles; les résultats sont approuvés par le topographe avant packaging ou déploiement.

## Plan proposé — cotes et hauteurs multiples par niveau (août 2026)

**Profondeur : standard.** Le changement est visuellement limité à trois colonnes, mais il traverse le modèle métier, le schéma JSON, l'import CAD, la validation et les cinq documents. La rétrocompatibilité des dossiers déjà enregistrés justifie un plan standard. **État : `milestone-complete-awaiting-approval` — jalon 3 vérifié localement le 27 août 2026; aucun packaging, commit, push ou déploiement n'a été effectué.**

### Portée confirmée

- Un niveau accepte une ou plusieurs cotes de début, une ou plusieurs cotes de fin et zéro, une ou plusieurs hauteurs.
- Le cas terrain de référence doit conserver exactement : début `+0,20`, fins `+3,10` et `+5,70`, hauteurs `2,90` et `5,50`.
- La saisie manuelle et la revue CAD affichent les listes sans en masquer une valeur.
- Les cinq DOCX utilisent le singulier ou le pluriel français approprié et formatent chaque nombre avec signe, virgule et deux décimales.
- Les projets JSON v1, v2 et v3 restent ouvrables sans perte; le nouveau format devient le schéma v4.
- Les valeurs existantes à un seul nombre restent visuellement et textuellement inchangées.

### Exclusions

- Aucun changement du serveur de licences, dashboard, Neon ou Vercel.
- Aucun calcul géométrique des zones correspondant à chaque cote; l'application conserve les valeurs déclarées dans le plan ou confirmées par le topographe.
- Aucun package, commit, push ou déploiement avant une autorisation distincte après validation locale.

### Règles métier et UX

- `BR-ELEV-01` — l'ordre des valeurs suit l'ordre explicite de la phrase CAD ou l'ordre saisi par l'utilisateur; les doublons exacts sont éliminés sans tri destructif.
- `BR-ELEV-02` — dans l'éditeur, le séparateur de liste est le point-virgule afin de ne pas confondre la virgule décimale : `+3,10 ; +5,70`. Le point et la virgule restent acceptés comme séparateurs décimaux.
- `BR-ELEV-03` — toutes les cotes de fin doivent être strictement supérieures à toutes les cotes de début du même niveau; toutes les hauteurs doivent être positives.
- `BR-ELEV-04` — l'import CAD calcule les hauteurs seulement lorsque l'association est déterministe : un début vers plusieurs fins, plusieurs débuts vers une fin, ou listes de même longueur associées par ordre. Sinon les hauteurs restent à confirmer et un avertissement est affiché.
- `BR-ELEV-05` — une phrase structurée comme `De la cote +0.20m aux cotes +3.10m et +5.70m` n'est plus considérée ambiguë; une suite de nombres sans marqueurs linguistiques fiables reste de confiance moyenne et exige une revue.
- `BR-ELEV-06` — pour les hauteurs CAD, la différence déterministe entre cotes est la proposition primaire (`3,10 - 0,20 = 2,90`; `5,70 - 0,20 = 5,50`). Une étiquette de hauteur spatialement rattachée à la coupe confirme la valeur; concordance calcul + étiquette donne une confiance élevée, calcul seul une confiance moyenne, et une étiquette numérique isolée n'est jamais appliquée automatiquement.
- `UX-ELEV-01` — les colonnes deviennent `Cotes début`, `Cotes fin` et `Hauteurs`; chaque cellule montre toutes les valeurs sur une seule ligne séparées par ` ; ` et possède un exemple/infobulle.
- `UX-ELEV-02` — la revue CAD reprend exactement le même format; modifier une cellule puis appliquer les choix conserve chaque valeur dans le formulaire principal et le JSON.
- `DOC-ELEV-01` — les variantes déterministes sont : `de la cote … à la cote …`, `de la cote … aux cotes …`, `des cotes … à la cote …` et `des cotes … aux cotes …`.
- `DOC-ELEV-02` — une hauteur produit `d’une hauteur intérieure de …`; plusieurs produisent `de hauteurs intérieures de … et …`.

### Architecture et migration

- `domain/models.py` : remplacer les trois scalaires de `Level` par des tuples ordonnés de `Decimal` (`start_elevations`, `end_elevations`, `interior_heights`) afin d'éviter la duplication de source de vérité.
- `projects/json_repository.py` : écrire les trois listes dans le schéma v4; convertir automatiquement chaque scalaire v1-v3 en liste vide ou à un élément lors du chargement.
- `ui/project_editor.py` : ajouter des fonctions uniques de parsing/formatage des listes décimales et les réutiliser pour lecture et écriture des trois colonnes.
- `cad_import/models.py`, `dxf_parser.py` et `service.py` : conserver séparément les nombres situés après les marqueurs `cote`/`cotes`, dériver les hauteurs déterministes et trier les niveaux par leur première cote de début.
- `cad_import_wizard.py` : transporter et éditer les trois listes sans conversion scalaire intermédiaire.
- `domain/validation.py` : valider présence du début, ordre vertical et positivité; les associations non déterministes importées restent un avertissement, jamais une valeur inventée.
- `documents/mappings.py` et `docx_renderer.py` : centraliser le formatage des listes, la coordination française et les quatre variantes singulier/pluriel pour les paragraphes et en-têtes de tableaux.
- Documentation : actualiser dictionnaire de données, manuel, protocole terrain et mapping des modèles sans modifier les textes juridiques statiques.

Les données restent locales. Les journaux peuvent contenir uniquement le nombre de valeurs et le code d'avertissement; ils ne doivent pas enregistrer les cotes ou le texte métier du dessin.

### Acceptation et vérification

- `AC-ELEV-01` — saisir `0,20`, `3,10 ; 5,70` et `2,90 ; 5,50`, enregistrer, rouvrir et retrouver les cinq nombres dans le même ordre.
- `AC-ELEV-02` — ouvrir un dossier v3 à valeurs scalaires, l'enregistrer en v4 puis le rouvrir sans changement visible ni perte de parties.
- `AC-ELEV-03` — importer la fixture contenant la phrase terrain et obtenir début `[0.20]`, fins `[3.10, 5.70]`, hauteurs `[2.90, 5.50]`, sans avertissement de cotes ambiguës.
- `AC-ELEV-03B` — sur EX 3, les textes de coupe `2.90` et `5.50` concordent avec les différences calculées et élèvent leur confiance; une fixture contenant un nombre isolé identique hors de la coupe ne doit pas être retenue comme hauteur.
- `AC-ELEV-03C` — sur EX 1, le Sous-sol conserve début `[-2.20]`, fins `[-0.20, 0.40]` et hauteurs `[2.00, 2.60]`; le Rez-de-chaussée conserve débuts `[0.00, 0.60]`, fin `[3.60]` et hauteurs `[3.60, 3.00]`. Les étiquettes de coupe correspondantes confirment ces calculs sans que les répétitions sur plusieurs feuilles créent des doublons.
- `AC-ELEV-04` — une fin inférieure/égale à un début ou une hauteur nulle/négative bloque la génération avec un message français rattaché au niveau.
- `AC-ELEV-05` — PV Division, Règlement et les titres de niveaux des tableaux contiennent `de la cote +0,20 m aux cotes +3,10 m et +5,70 m`; le narratif contient `de hauteurs intérieures de 2,90 m et 5,50 m`.
- `AC-ELEV-06` — les dossiers à une seule cote de début/fin/hauteur produisent les mêmes textes qu'avant.
- `AC-ELEV-07` — toute la suite pytest passe; le parcours EX 3 import → revue → JSON → contrôle → cinq DOCX passe; les cinq DOCX sont inspectés en OOXML et visuellement page par page.

### Jalons avec gates d'approbation

1. **Données v4 et éditeur manuel** — migration rétrocompatible, saisie des listes et validations passent `AC-ELEV-01/02/04/06`. Gate : revue du formulaire et d'un JSON migré.
2. **Import et revue CAD fidèles** — la phrase terrain conserve les deux fins et les deux hauteurs, sans fausse ambiguïté; `AC-ELEV-03` passe. Gate : revue de l'écran CAD avec EX 3.
3. **Cinq documents cohérents** — grammaire, signes et décimales passent `AC-ELEV-05/06`; suite complète et QA documentaire passent `AC-ELEV-07`. Gate : visa local avant toute reconstruction ou distribution.

### Résultat du jalon 1 — données v4 et éditeur manuel

- `Level` conserve désormais trois tuples ordonnés de `Decimal`; les doublons exacts sont supprimés sans tri et les vues scalaires temporaires maintiennent la compatibilité des composants non encore migrés.
- Le dépôt JSON écrit le schéma v4 et convertit automatiquement les valeurs scalaires des schémas v1, v2 et v3 en listes, sans modifier les UUID des niveaux et parties.
- L’éditeur manuel affiche `Cotes début`, `Cotes fin` et `Hauteurs`, accepte le séparateur ` ; `, les virgules ou points décimaux, puis restitue signes et deux décimales.
- La validation bloque une liste de débuts vide, toute fin qui ne dépasse pas tous les débuts et toute hauteur nulle ou négative; le panneau rattache le message au niveau concerné.
- Verdicts : `AC-ELEV-01` réussi; `AC-ELEV-02` réussi; `AC-ELEV-04` réussi; compatibilité scalaire de `AC-ELEV-06` réussie. `AC-ELEV-03/03B/03C/05/07` restent volontairement aux jalons 2 et 3.
- Preuves : tests ciblés `20 passed`; suite complète `95 passed, 2 skipped` (tests PostgreSQL réels déjà optionnels), avec un avertissement Starlette de dépendance préexistant; `git diff --check` sans erreur d’espace.
- Limite de jalon : l’import/revue CAD produit encore une seule valeur par champ et les documents utilisent encore la vue scalaire de compatibilité. Aucun package, commit, push ni déploiement n’a été effectué.

### Résultat du jalon 2 — import et revue CAD fidèles

- `CadLevelDraft` transporte les trois tuples ordonnés sans conversion scalaire; le service de réconciliation les copie intégralement dans le projet v4.
- Le parseur distingue les groupes situés après `cote/cotes`, conserve leur ordre et dérive les hauteurs uniquement pour les associations déterministes prévues par `BR-ELEV-04`.
- Une hauteur calculée seule garde une confiance moyenne. La confiance devient élevée seulement si chaque hauteur est retrouvée sous le libellé de coupe verticale associé spatialement au tableau; les handles correspondants rejoignent les preuves.
- La revue CAD affiche et édite les listes au format `+3,10 ; +5,70`, conserve la confiance et l’ambiguïté, puis transfère toutes les valeurs avec **Appliquer les choix**. Une saisie invalide affiche un message au lieu de fermer silencieusement la revue.
- Verdicts : `AC-ELEV-03` réussi; `AC-ELEV-03B` réussi; `AC-ELEV-03C` réussi; `UX-ELEV-02` réussi. `AC-ELEV-05` et la partie documentaire/visuelle de `AC-ELEV-07` restent au jalon 3.
- Preuves synthétiques : `21 passed` dans `tests/test_cad_import_flow.py`, dont associations un→plusieurs, plusieurs→un, association non déterministe, nombre isolé et application de valeurs modifiées.
- Preuves réelles locales : EX 1 restitue Sous-sol `[-2.20] → [-0.20, 0.40] / [2.00, 2.60]` et RDC `[0.00, 0.60] → [3.60] / [3.60, 3.00]`; EX 3 restitue RDC `[0.20] → [3.10, 5.70] / [2.90, 5.50]`. Les deux flux passent revue → projet → sauvegarde v4 → réouverture sans avertissement CAD.
- Régression : suite complète `99 passed, 2 skipped`, avec le même avertissement Starlette préexistant; `git diff --check` sans erreur d’espace.
- Limite de jalon : les cinq DOCX utilisent encore la vue scalaire de compatibilité et ne rendent pas encore les variantes grammaticales multiples. Aucun package, commit, push ni déploiement n’a été effectué.

### Résultat du jalon 3 — cinq documents cohérents

- Le formateur documentaire central rend les quatre variantes singulier/pluriel de cotes et conserve exactement la formulation historique des dossiers scalaires.
- Le narratif écrit une hauteur au singulier et plusieurs valeurs sous la forme `de hauteurs intérieures de 2,90 m et 5,50 m`; les en-têtes de PV Division, Règlement et Tableau B partagent le même texte de cotes.
- Le parcours réel EX 3 passe import DXF → revue → projet v4 → sauvegarde/réouverture JSON → contrôle → génération des cinq DOCX. Le projet obtenu contient 8 niveaux et 44 parties, sans avertissement CAD.
- Les cinq DOCX ont été inspectés en OOXML : aucune séquence d'encodage suspecte (`?`, caractère de remplacement, `Ã`, `Â`) et les textes multi-cotes/multi-hauteurs attendus sont présents dans les documents concernés.
- Les cinq sorties ont été exportées localement par Microsoft Word et leurs 27 pages ont été inspectées en PNG : PV Division 4 pages, Règlement 15 pages, Tableau A 2 pages, Tableau B 4 pages et Tableau récapitulatif 2 pages. Les pieds du Règlement affichent intégralement `1/14` à `14/14`.
- Verdicts : `AC-ELEV-05` réussi; `AC-ELEV-06` réussi; partie automatisable et visuelle locale de `AC-ELEV-07` réussie. Suite complète : `106 passed, 2 skipped`, avec un avertissement Starlette/httpx préexistant.
- Le renderer canonique n'a pas trouvé LibreOffice sur cette station; l'export Word invisible a servi de solution de vérification locale. Aucun package, commit, push ou déploiement n'a été effectué.

### Résultat du jalon de distribution — version topographe du 27/08/2026

- Le paquet Windows a été reconstruit après suppression, dans la spécification PyInstaller, des DLL ICU étrangères qui masquaient les bibliothèques Qt et provoquaient `DLL load failed while importing QtCore` sur l'exécutable distribué.
- Le test de démarrage du paquet passe dans les modes licence locale, poste neuf sans licence et import CAD réel EX 3. Le même triplet de tests passe après extraction de l'archive finale dans un dossier distinct.
- La suite complète passe après packaging : `106 passed, 2 skipped`, avec le même avertissement Starlette/httpx préexistant.
- Archive USB : `CoproAuto-Topographe-2026-08-27.zip`, 76 265 461 octets, SHA-256 `167D0B10227A154470521CBB429768B03030D9482F5F9CC872B0E8876C67BFAB`.
- Exécutable : SHA-256 `DC420C68934A72A310CC9644D648704F211DCCAD0E155B80727A81925C318B5B`. Il reste non signé; Windows peut donc afficher SmartScreen sur un nouveau poste.
- Le ZIP ne contient ni code source, ni `.env`, clé privée, clé d'essai, document client ou artefact QA. Le guide `LISEZ-MOI.txt` est inclus à sa racine applicative.
- Sources sauvegardées dans le commit `6201fec` et poussées sur `origin/codex/ui-ux-overhaul`; la PR #4 est mise à jour mais n'est pas fusionnée automatiquement dans `main`.
- Serveur de licences déployé en production sur Vercel : déploiement `dpl_HCHrW59UfgjGkhtpCXDucHJU136e` en état `READY`. `https://copro-auto-license-api.vercel.app/health` retourne HTTP 200 avec `{"status":"ok"}`, ce qui vérifie aussi la connexion à la base. Aucun incident d'exécution n'a été détecté sur la dernière heure après déploiement.

### Proposition UX — dashboard administrateur v2 du 29/08/2026

- Décisions produit confirmées : informations système limitées et respectueuses de la vie privée, dates/heures en `Africa/Casablanca`, synthèse et filtres enrichis, activité contextualisée.
- La proposition distingue l'occupation d'une place (`Actif`/`Libéré`) de la présence récente (`En ligne` si dernier contact inférieur à 20 minutes, sinon `Hors ligne`).
- Le détail d'appareil prévu contient nom du poste, Windows/édition/build, architecture, version Copro Auto, identifiant support court, première activation, dernier contact et libération éventuelle. Numéros de série, MAC, IP complète et géolocalisation restent exclus.
- Révision UX v2 : la page Activité reçoit une pagination serveur stable par curseur (25/50/100), recherche et filtres combinables, regroupement optionnel des vérifications automatiques, contexte client/appareil/origine, export CSV filtré et restauration de l'état après consultation d'une licence.
- Spécification : `docs/admin-dashboard-v2/UX_SPEC.md`. Artifacts : `dashboard-overview`, `license-device-detail`, `activity-page` et `mobile-wireframe` en SVG et PNG.
- Statut : UX v2 explicitement approuvée le 29/08/2026; dashboard administrateur v2 implémenté et vérifié localement. Aucun déploiement n’est autorisé dans ce jalon.

### [ORPHANS & PENDING]

- [x] Obtenir l'approbation explicite de ce plan avant le jalon 1.
- [x] Exécuter et vérifier le jalon 1 : données v4, migration, éditeur manuel et validation.
- [x] Exécuter et vérifier le jalon 2 : extraction multi-cotes, hauteurs déterministes et revue CAD.
- [x] Exécuter un seul jalon à la fois et demander l'approbation après sa vérification.
- [x] Obtenir l'approbation explicite avant le jalon 3 documentaire.
- [x] Exécuter et vérifier le jalon 3 : grammaire multi-cotes, hauteurs multiples, parcours EX 3 et inspection des cinq DOCX.
- [x] Préparer et vérifier le paquet USB après autorisation explicite de distribution.
- [ ] Obtenir le visa terrain du topographe sur le paquet distribué, notamment le cas à deux fins/deux hauteurs.
- [x] Obtenir l'approbation explicite de `Dashboard administrateur UX v2 — 29/08/2026` avant implémentation.
- [x] Implémenter et vérifier localement le dashboard administrateur v2 sans déploiement.
