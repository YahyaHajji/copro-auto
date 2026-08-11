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

- exécuter `backup.ps1` vers un volume externe et tester régulièrement une restauration ;
- surveiller `/health`, les erreurs API et l’espace disque ;
- conserver `.env`, clé privée et sauvegardes hors du dépôt ;
- limiter l’accès SSH et appliquer les mises à jour de sécurité ;
- ne pas promettre un desktop impossible à cracker : la signature empêche la fabrication de jetons valides, pas le patch d’un exécutable contrôlé par un attaquant.
