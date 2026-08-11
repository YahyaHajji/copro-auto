from pathlib import Path

import ezdxf
import pytest

from copro_auto.cad_import import dwg_converter
from copro_auto.cad_import.dwg_converter import DwgConversionError
from copro_auto.cad_import.service import import_cad


def test_dwg_import_explains_autocad_requirement(tmp_path, monkeypatch) -> None:
    drawing = tmp_path / "plan.dwg"
    drawing.write_bytes(b"not-a-real-dwg")
    monkeypatch.setattr(dwg_converter, "find_accoreconsole", lambda: None)

    with pytest.raises(DwgConversionError, match="AutoCAD Core Console est introuvable"):
        dwg_converter.convert_dwg_to_dxf(drawing)


def test_dxf_import_remains_available_without_autocad(tmp_path, monkeypatch) -> None:
    drawing = tmp_path / "plan.dxf"
    document = ezdxf.new("R2018")
    document.modelspace().add_text("Propriété dite : Résidence Atlas")
    document.saveas(drawing)
    monkeypatch.setattr(
        "copro_auto.cad_import.service.convert_dwg_to_dxf",
        lambda _path: pytest.fail("DXF import must not invoke AutoCAD"),
    )

    result = import_cad(Path(drawing))

    assert result.values["identity.property_name"].value == "Résidence Atlas"
