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

## Service HTTPS

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
