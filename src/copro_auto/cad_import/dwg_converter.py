from __future__ import annotations

import logging
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
    script = output.parent / f"{source_path.stem}-export.scr"
    script.write_text(f"_.DXFOUT\n{output}\n16\n_.QUIT\n_N\n", encoding="ascii", errors="strict")
    LOGGER.info("cad_conversion_started source=%s", source_path.name)
    try:
        completed = subprocess.run(
            [str(console), "/i", str(source_path), "/s", str(script), "/l", "en-US"],
            capture_output=True,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DwgConversionError(f"La conversion DWG a échoué : {exc}") from exc
    finally:
        script.unlink(missing_ok=True)
    if completed.returncode != 0 or not output.exists() or output.stat().st_size == 0:
        if owned_temp:
            shutil.rmtree(output.parent, ignore_errors=True)
        detail = completed.stderr.decode(errors="replace")[-500:]
        raise DwgConversionError(f"AutoCAD n'a pas produit de DXF valide. {detail}")
    LOGGER.info("cad_conversion_completed bytes=%d", output.stat().st_size)
    return output

