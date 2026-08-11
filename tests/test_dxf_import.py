from pathlib import Path

import ezdxf

from copro_auto.cad_import.dxf_parser import parse_dxf


def test_text_dxf_extracts_identity(tmp_path):
    path = tmp_path / "sample.dxf"
    document = ezdxf.new("R2018")
    space = document.modelspace()
    space.add_text("Propriété dite : Résidence Atlas")
    space.add_text("Titre : T 205431/03")
    space.add_mtext("Située à: Préfecture de Meknès, Lotissement Atlas")
    document.saveas(path)
    result = parse_dxf(path)
    assert result.values["identity.property_name"].value == "Résidence Atlas"
    assert result.values["identity.land_title"].value == "205431/03"
    assert result.values["identity.prefecture"].value == "Meknès"
    assert result.values["identity.subdivision"].value == "Atlas"


def test_real_reference_dxf_when_available():
    path = Path("work/extracted/Les_Planches.dxf")
    if not path.exists():
        return
    result = parse_dxf(path)
    assert len(result.texts) > 100
    assert result.values["identity.land_title"].value == "119753/59"
    assert result.values["identity.property_name"].value.strip() == "Yasmin 71"
    assert result.values["identity.subdivision"].value.strip() == "Yasmin"


def test_drawn_text_row_is_joined_before_identity_extraction(tmp_path):
    path = tmp_path / "drawn-table.dxf"
    document = ezdxf.new("R2018")
    space = document.modelspace()
    space.add_text("Propriété dite :", dxfattribs={"height": 0.25}).set_placement((10, 20))
    space.add_text("Résidence Zohour", dxfattribs={"height": 0.25}).set_placement((12.5, 20))
    space.add_text(
        "Située à: Préfecture de Meknès, lotissment Zohour", dxfattribs={"height": 0.12},
    ).set_placement((10, 19))
    document.saveas(path)

    result = parse_dxf(path)

    assert result.values["identity.property_name"].value == "Résidence Zohour"
    assert result.values["identity.subdivision"].value == "Zohour"
