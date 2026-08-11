# Déploiement et exploitation

## Desktop

Prérequis de build : Windows 10/11 x64, Python 3.13 x64. Installer `dependency-lock.txt`, injecter la configuration publique puis lancer PyInstaller :

```powershell
.\.venv\Scripts\python packaging\configure_license.py `
  --server-url "https://licence.votre-domaine.ma" `
  --public-key "CLE_PUBLIQUE_BASE64"
.\.venv\Scripts\pyinstaller --noconfirm --clean packaging\copro_auto.spec
```

`resources/license/config.json` est ignoré par Git. Il ne contient que l’URL et la clé publique; jamais la clé privée. Le package final est `dist\CoproAuto`. Avant vente, signer l’exécutable et l’installeur avec un certificat de signature de code Windows.

Vérifier d'abord les démarrages sous profil neuf, avec une licence de développement hors ligne puis sans licence :

```powershell
& packaging\smoke_test.ps1
```

Après acquisition d'un certificat Authenticode avec clé privée dans le magasin Windows :

```powershell
& packaging\sign_release.ps1 -CertificateThumbprint "EMPREINTE_DU_CERTIFICAT"
& packaging\smoke_test.ps1 -RequireValidSignature
```

Le script de signature refuse un certificat absent, expiré ou sans clé privée, horodate la signature SHA-256 puis la vérifie. Conserver aussi l'empreinte SHA-256 affichée avec le dossier de livraison.

## Générer la paire Ed25519

Dans un environnement serveur sûr :

```powershell
$env:PYTHONPATH = "license_server/src"
.\.venv\Scripts\python -m license_server.keygen
```

La ligne privée va uniquement dans le secret `LICENSE_SIGNING_PRIVATE_KEY` du serveur. La ligne publique est injectée dans le desktop. Une perte de la clé privée empêche de signer de nouveaux leases; une fuite exige rotation et nouvelle version du desktop.

## MVP d'apprentissage gratuit : Neon + Render

Le chemin le plus simple pour l'essai en ligne utilise Neon Free pour PostgreSQL et Render Free pour l'API HTTPS. Le fichier `render.yaml` décrit le service Docker, le contrôle `/health`, la région de Francfort et les trois secrets à saisir manuellement. Aucun secret ni URL PostgreSQL n'est enregistré dans Git.

1. Créer un projet Neon PostgreSQL 18 dans la région Frankfurt, sans Neon Auth.
2. Appliquer `license_server/migrations/0001_initial.sql` avec l'URL directe Neon.
3. Déployer le dépôt privé comme Blueprint Render à partir de `render.yaml`.
4. Dans Render, fournir l'URL Neon avec pool de connexions comme `DATABASE_URL`, puis `LICENSE_SIGNING_PRIVATE_KEY` et `LICENSE_KEY_PEPPER`.
5. Vérifier que `https://<service>.onrender.com/health` répond `200 {"status":"ok"}`.
6. Injecter l'URL Render et uniquement la clé publique Ed25519 dans le desktop avec `packaging/configure_license.py`, puis reconstruire le package.

Le service gratuit Render peut s'endormir lorsqu'il est inactif. Le client accorde donc jusqu'à 75 secondes au premier appel de licence afin de laisser le service redémarrer. Render peut demander une carte pour vérifier l'identité même lorsque le plan sélectionné est gratuit; cette opération doit être faite directement par le propriétaire du compte.

Pour les migrations, sauvegardes ou commandes administratives, utiliser l'URL Neon directe. Pour l'API Render, utiliser l'URL Neon avec pool de connexions. Les URL et clés restent uniquement dans les gestionnaires de secrets Neon/Render ou dans l'environnement local temporaire.

## Service HTTPS sur VPS (option future)

Prérequis : petit VPS Linux avec Docker, nom de domaine pointant vers le VPS et ports 80/443. L’hébergement n’est pas intrinsèquement gratuit : un niveau gratuit peut suffire aux essais, mais un domaine, la disponibilité et les sauvegardes ont généralement un coût faible.

Copier `deploy/license_server/.env.example` vers `.env`, remplacer tous les secrets, puis :

```bash
cd deploy/license_server
docker compose up -d --build
curl https://licence.votre-domaine.ma/health
```

`/health` exécute réellement `SELECT 1` sur la base. Il répond `200 {"status":"ok"}` quand PostgreSQL est joignable et `503 {"status":"unavailable"}` si la connexion échoue. Le superviseur ne doit donc considérer le service prêt que sur HTTP 200.

Une validation locale exige un vrai moteur Docker. Un exécutable ou stub nommé `docker` ne suffit pas : vérifier que `docker version` affiche une section serveur avant de considérer PostgreSQL, la migration et l'API comme testés. La première mise en production doit ensuite tester création, activation, rafraîchissement, désactivation, sauvegarde et restauration sur le VPS réel.

Caddy obtient et renouvelle automatiquement le certificat TLS. PostgreSQL n’est pas exposé publiquement. L’API ne reçoit aucune donnée de dossier.

## Créer les licences

Essai commercial standard de 30 jours :

```bash
docker compose exec api python -m license_server.admin_cli create "Client" --plan individual --seats 2 --days 30 --trial
```

Essai de stage de six mois :

```bash
docker compose exec api python -m license_server.admin_cli create "Bureau de stage" --plan office --seats 10 --days 183 --trial
```

La clé brute est affichée une seule fois; la base ne conserve que son HMAC SHA-256. Commandes disponibles : `renew`, `revoke`, `release`.

## Sauvegarde et contrôle

- copier `.env.example` vers `.env`, renseigner les secrets, puis créer une sauvegarde sur un volume externe :

```powershell
& deploy\license_server\backup.ps1 -OutputDirectory 'D:\Sauvegardes\CoproAuto'
```

Le script charge automatiquement `deploy/license_server/.env`, tout en laissant les variables du processus prioritaires comme Docker Compose. Il lance `pg_dump` dans le conteneur, écrit d'abord un fichier `.partial`, refuse une sortie vide et ne publie le fichier `.sql` final qu'après un code de sortie réussi. Les mots de passe ne sont ni affichés ni placés dans les arguments de commande.

Les tests PostgreSQL réels exigent une base jetable dont le nom commence par `copro_auto_test_` :

```powershell
$env:TEST_POSTGRES_URL = 'postgresql+psycopg://test_user:test_password@127.0.0.1:5432/copro_auto_test_hardening'
$env:TEST_POSTGRES_BIN = 'C:\Program Files\PostgreSQL\16\bin'
& .\.venv\Scripts\python.exe -m pytest license_server\tests\test_postgres_integration.py -q
```

Ce test applique deux fois la migration, exerce l'API sur PostgreSQL, lance le vrai `backup.ps1` avec `pg_dump`, restaure le fichier dans une seconde base jetable et vérifie les données restaurées. Ne jamais pointer `TEST_POSTGRES_URL` vers une base de production.

- tester une restauration après chaque modification du schéma et régulièrement en exploitation ;
- surveiller `/health`, les erreurs API et l’espace disque ;
- conserver `.env`, clé privée et sauvegardes hors du dépôt ;
- limiter l’accès SSH et appliquer les mises à jour de sécurité ;
- ne pas promettre un desktop impossible à cracker : la signature empêche la fabrication de jetons valides, pas le patch d’un exécutable contrôlé par un attaquant.
