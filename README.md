# Copro Auto

Application Windows locale pour saisir ou importer les données d'un dossier de copropriété, vérifier les calculs et produire cinq documents Word cohérents.

## Développement

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\pytest
.\.venv\Scripts\copro-auto
```

Pour lancer sans serveur de licence pendant le développement :

```powershell
$env:COPRO_AUTO_DEV_LICENSE = "1"
.\.venv\Scripts\copro-auto
```

## Vérification et package Windows

```powershell
.\.venv\Scripts\pytest
.\.venv\Scripts\pyinstaller --noconfirm --clean packaging\copro_auto.spec
& packaging\smoke_test.ps1
```

Le package `onedir` est créé dans `dist\CoproAuto`. Les modèles de référence sont conservés dans `resources/templates/originals`; les copies préparées et packagées se trouvent dans `resources/templates/runtime`. `work/` contient uniquement les analyses et sorties de QA locales et n'est pas une dépendance de l'application.

Documentation :

- `docs/user_manual.md` — utilisation du desktop ;
- `docs/data_dictionary.md` — modèle métier et calculs ;
- `docs/template_mapping.md` — contrat des six modèles ;
- `docs/deployment.md` — serveur de licences, clés et package commercial.
- `docs/field_validation_protocol.md` — validation métier sur trois dossiers réels ;
- `docs/ip_and_template_rights_agreement_draft.md` — accord de propriété/exploitation à faire revoir ;
- `docs/commercial_license_agreement_draft.md`, `docs/trial_terms_draft.md` et `docs/privacy_notice_draft.md` — pack contractuel de travail pour le conseil juridique.
