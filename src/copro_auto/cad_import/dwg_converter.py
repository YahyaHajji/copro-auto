from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class DwgConversionError(RuntimeError):
    pass


def find_accoreconsole() -> Path | None:
    executable = shutil.which("accoreconsole.exe")
    if executable:
        return Path(executable)
    roots = [Path(r"C:\Program Files\Autodesk"), Path(r"C:\Program Files (x86)\Autodesk")]
    candidates = [path for root in roots if root.exists() for path in root.glob("AutoCAD */accoreconsole.exe")]
    return max(candidates, key=lambda path: path.parent.name, default=None)


def convert_dwg_to_dxf(source: str | Path, destination: str | Path | None = None) -> Path:
    source_path = Path(source).resolve(strict=True)
    if source_path.suffix.casefold() != ".dwg":
        raise DwgConversionError("Le fichier source doit être un dessin DWG.")
    console = find_accoreconsole()
    if console is None:
        raise DwgConversionError("AutoCAD Core Console est introuvable. Exportez le dessin en DXF R2018.")

    owned_temp = destination is None
    output = Path(destination) if destination else Path(tempfile.mkdtemp(prefix="CoproAuto-")) / f"{source_path.stem}.dxf"
    output.parent.mkdir(parents=True, exist_ok=True)
    isolation = Path(tempfile.mkdtemp(prefix="CoproAuto-AutoCAD-"))
    script = output.parent / f"{source_path.stem}-export.scr"
    script.write_text(f"_.FILEDIA\n0\n_.DXFOUT\n{output}\n16\n_.QUIT\n_N\n", encoding="ascii", errors="strict")
    LOGGER.info("cad_conversion_started extension=%s", source_path.suffix.casefold())
    try:
        completed = subprocess.run(
            [
                str(console), "/i", str(source_path), "/s", str(script), "/l", "en-US",
                "/isolate", f"CoproAuto-{os.getpid()}", str(isolation), "/readonly",
            ],
            capture_output=True,
            timeout=90,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        if owned_temp:
            shutil.rmtree(output.parent, ignore_errors=True)
        raise DwgConversionError(
            "AutoCAD n’a pas terminé la conversion dans le délai prévu. "
            "Ouvrez le dessin dans AutoCAD, exportez-le en DXF R2018, puis importez ce DXF."
        ) from None
    except OSError as exc:
        if owned_temp:
            shutil.rmtree(output.parent, ignore_errors=True)
        raise DwgConversionError("AutoCAD n’a pas pu démarrer la conversion. Exportez le dessin en DXF R2018.") from None
    finally:
        script.unlink(missing_ok=True)
        shutil.rmtree(isolation, ignore_errors=True)
    if completed.returncode != 0 or not output.exists() or output.stat().st_size == 0:
        if owned_temp:
            shutil.rmtree(output.parent, ignore_errors=True)
        LOGGER.warning("cad_conversion_no_output returncode=%d", completed.returncode)
        raise DwgConversionError(
            "AutoCAD n’a pas produit de DXF valide. Exportez le dessin en DXF R2018, puis importez ce DXF."
        )
    LOGGER.info("cad_conversion_completed bytes=%d", output.stat().st_size)
    return output
