# PROJECT_MAP — Plateforme d’automatisation des dossiers de copropriété

Dernière mise à jour : 12 août 2026
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
