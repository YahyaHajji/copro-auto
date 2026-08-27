# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
RESOURCES_ROOT = Path(os.environ.get("COPRO_AUTO_RESOURCES_ROOT", ROOT / "resources")).resolve()

a = Analysis(
    [str(ROOT / "src" / "copro_auto" / "__main__.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[(str(RESOURCES_ROOT), "resources")],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["fastapi", "sqlalchemy", "uvicorn", "psycopg", "pytest"],
    noarchive=False,
)

# Windows 11 exposes its own ICU compatibility DLL while the Codex document
# runtime can also add a different ICU data DLL to PATH. PyInstaller may pair
# those unrelated files and shadow Qt's normal runtime lookup, which makes
# QtCore fail before the application starts. Qt/PySide does not ship these
# files in this environment, and the previously verified package did not
# contain them, so exclude only the accidentally discovered ICU binaries.
a.binaries = [
    entry
    for entry in a.binaries
    if not Path(entry[0]).name.casefold().startswith(("icudt", "icuin", "icuuc"))
]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CoproAuto",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="CoproAuto",
)
