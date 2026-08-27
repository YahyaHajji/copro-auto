from __future__ import annotations

import os
from copy import deepcopy
from datetime import date
from decimal import Decimal
from pathlib import Path

import ezdxf
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialog

from copro_auto.cad_import.dxf_loader import DxfLoadResult, DxfNativeTable, DxfTextItem
from copro_auto.cad_import.dxf_parser import _elevations, _native_table_to_level, parse_dxf
from copro_auto.cad_import.service import apply_reviewed_draft, import_cad
from copro_auto.documents.service import DocumentGenerationService
from copro_auto.domain.models import ClientInformation, Level, Project, ProjectIdentity
from copro_auto.domain.validation import has_errors, validate_project
from copro_auto.projects.json_repository import project_from_dict, project_to_dict
from copro_auto.ui.cad_import_wizard import CadImportWizard


def _text(space, value: str, x: float, y: float, height: float = 0.15):
    return space.add_text(value, dxfattribs={"height": height}).set_placement((x, y))


def _exploded_table(space, number: int, top: float, *, complete_grid: bool = True) -> None:
    columns = (9.5, 11.5, 12.5, 13.5, 14.5, 15.0, 16.0, 17.0, 19.0, 21.0)
    bottom = top - 3.0
    if complete_grid:
        for x in columns:
            space.add_line((x, bottom), (x, top))
    space.add_line((columns[0], top), (columns[-1], top))
    space.add_line((columns[0], top - 1.0), (columns[-1], top - 1.0))
    space.add_line((columns[0], bottom), (columns[-1], bottom))
    _text(space, "Tableau des Contenances", 10.0, top + 0.12)
    _text(space, f"Plan du Niveau {number + 1}", 13.0, top + 1.5)
    _text(space, f"De la cote {number * 3:+.2f}m à la cote {(number + 1) * 3:+.2f}m", 13.0, top + 0.8)
    headers = (
        (11.7, "Titre N°"), (12.7, "Privatives"), (13.7, "Communes"),
        (15.2, "à l'intérieur du Titre"), (16.2, "avec Surplomb"),
        (17.2, "Consistances"), (19.2, "Observations"),
    )
    for x, value in headers:
        _text(space, value, x, top - 0.5, 0.10)
    first_y = top - 1.45
    if number == 0:
        _text(space, "4-4", 12.65, first_y)
        _text(space, "a", 13.10, first_y + 0.08)
    else:
        _text(space, str(number + 1), 12.8, first_y)
    _text(space, "69", 15.2, first_y)
    _text(space, "80", 16.2, first_y)
    _text(space, "Appartement", 17.2, first_y)
    _text(space, "11 m² en surplomb", 19.2, first_y)
    second_y = top - 2.25
    _text(space, "9", 13.8, second_y)
    _text(space, "8", 15.2, second_y)
    _text(space, "8", 16.2, second_y)
    _text(space, "Murs et gaines", 17.2, second_y)


def _build_fixture(path: Path, level_count: int, *, complete_grid: bool = True) -> Path:
    document = ezdxf.new("R2018")
    document.header["$DWGCODEPAGE"] = "ANSI_1252"
    space = document.modelspace()
    _text(space, "Propriété dite : Résidence Émeraude", 0, 110)
    _text(space, "Titre : T 205431/03", 0, 109)
    _text(space, "Située à: Préfecture de Meknès, Lotissement Zohour", 0, 108)
    for number in range(level_count):
        _exploded_table(space, number, 100 - number * 10, complete_grid=complete_grid)
    document.saveas(path)
    return path


def _split_header_table(space, origin: float, top: float, title: str, cote: str, index: str) -> None:
    columns = tuple(origin + value for value in (0, 2, 3.5, 4.5, 5.5, 6.5, 7.5, 10, 13))
    bottom = top - 3.5
    for column_index, x in enumerate(columns):
        vertical_top = top - 0.6 if column_index in (3, 5) else top
        space.add_line((x, bottom), (x, vertical_top))
    space.add_line((columns[0], top), (columns[6] + 0.05, top))
    space.add_line((columns[6] - 0.05, top), (columns[-1], top))
    space.add_line((columns[0], top - 1.0), (columns[-1], top - 1.0))
    space.add_line((columns[0], bottom), (columns[-1], bottom))
    _text(space, "Tableau des Contenances", origin + 0.2, top + 0.15)
    _text(space, title, origin - 0.6, top + 1.5)
    _text(space, cote, origin - 0.6, top + 0.8)
    headers = (
        (origin + 0.5, "Propriété dite"), (origin + 2.3, "Titre N°"),
        (origin + 3.65, "Privatives"), (origin + 4.65, "Communes"),
        (origin + 5.65, "Intérieur du titre"), (origin + 6.65, "Avec surplomb"),
        (origin + 7.7, "Consistances"), (origin + 10.2, "Observations"),
    )
    for x, value in headers:
        _text(space, value, x, top - 0.5, 0.10)
    first_y = top - 1.5
    _text(space, index, origin + 3.7, first_y)
    _text(space, "70", origin + 5.7, first_y)
    _text(space, "80", origin + 6.7, first_y)
    _text(space, "Appartement", origin + 7.7, first_y)
    _text(space, "avec garage", origin + 7.7, top - 2.2)
    _text(space, "10 m² en surplomb", origin + 10.2, first_y)
    second_y = top - 2.6
    _text(space, "2", origin + 4.7, second_y)
    _text(space, "20", origin + 5.7, second_y)
    _text(space, "20", origin + 6.7, second_y)
    _text(space, "Murs et gaines", origin + 7.7, second_y)


def _build_horizontal_fixture(path: Path) -> Path:
    document = ezdxf.new("R2018")
    space = document.modelspace()
    _text(space, "Propriété dite : Projet horizontal", 0, 120)
    _text(space, "Titre : 1000/10", 0, 119)
    _text(space, "Située à : Préfecture Meknes, Commune Ait Ouallal, Lotissement Atlas", 0, 118)
    _split_header_table(space, 0, 100, "PLAN DE LA MEZZANINE", "De la côte +3.30m à la côte +5.70m", "3-3a")
    _split_header_table(space, 40, 100, "PLAN DU SOUS/SOL", "De la côte -2.80m à la côte +0.00m", "1")
    _split_header_table(space, 20, 100, "PLAN DU REZ-DE-CHAUSSÉE", "Des côtes +0.00m et +0.60m à la côte +3.60m", "2")
    document.saveas(path)
    return path


def _build_multi_end_fixture(path: Path, *, confirm_heights: bool, isolated_label: bool = False) -> Path:
    document = ezdxf.new("R2018")
    space = document.modelspace()
    _text(space, "Propriété dite : Projet multi-cotes", 0, 120)
    _text(space, "Titre : 2000/20", 0, 119)
    _split_header_table(
        space, 0, 100, "PLAN DU REZ-DE-CHAUSSÉE",
        "De la côte +0.20m aux côtes +3.10m et +5.70m", "1",
    )
    if confirm_heights:
        _text(space, "Coupe verticale des hauteurs 1/100", 0.2, 92)
        _text(space, "2.90", 1.0, 90)
        _text(space, "5.50", 2.0, 89)
    if isolated_label:
        _text(space, "2.90", 100, 90)
        _text(space, "5.50", 101, 89)
    document.saveas(path)
    return path


@pytest.mark.parametrize("level_count", (2, 3, 5))
def test_exploded_tables_are_detected_dynamically(tmp_path: Path, level_count: int) -> None:
    draft = parse_dxf(_build_fixture(tmp_path / f"{level_count}-levels.dxf", level_count))

    assert len(draft.levels) == level_count
    assert draft.part_count == level_count * 2
    assert draft.levels[0].parts[0].index == "4-4a"
    assert draft.levels[0].parts[0].inside_title == Decimal("69")
    assert draft.levels[0].parts[0].overhang == Decimal("11")


def test_declared_codepage_does_not_corrupt_utf8_accents(tmp_path: Path) -> None:
    draft = parse_dxf(_build_fixture(tmp_path / "accents.dxf", 2))

    assert draft.values["identity.property_name"].value == "Résidence Émeraude"
    assert draft.values["identity.prefecture"].value == "Meknès"
    assert all("�" not in text for text in draft.texts)


@pytest.mark.parametrize(
    ("situation", "prefecture", "commune"),
    (
        ("Située à : Préfecture Meknes, Commune Ait Ouallal, Lotissement Atlas", "Meknes", "Ait Ouallal"),
        ("Située à : Préfecture de Meknès, Commune Ait Ouallal, Lotissement Atlas", "Meknès", "Ait Ouallal"),
        ("Située à : Préfecture et Commune de Meknès, Lotissement Atlas", "Meknès", "Meknès"),
    ),
)
def test_prefecture_and_commune_are_extracted_separately(
    tmp_path: Path, situation: str, prefecture: str, commune: str,
) -> None:
    document = ezdxf.new("R2018")
    space = document.modelspace()
    _text(space, "Parties Communes", 0, 11)
    _text(space, situation, 0, 10)
    source = tmp_path / "situation.dxf"
    document.saveas(source)

    draft = parse_dxf(source)

    assert draft.values["identity.prefecture"].value == prefecture
    assert draft.values["identity.commune"].value == commune


def test_split_header_tables_are_merged_ordered_and_fully_extracted(tmp_path: Path) -> None:
    draft = parse_dxf(_build_horizontal_fixture(tmp_path / "horizontal.dxf"))

    assert [level.name for level in draft.levels] == ["Sous-sol", "Rez-de-chaussée", "Mezzanine"]
    assert [len(level.parts) for level in draft.levels] == [2, 2, 2]
    assert all(part.consistency for level in draft.levels for part in level.parts)
    assert all(level.parts[0].consistency == "Appartement avec garage" for level in draft.levels)
    assert all(level.parts[1].consistency == "Murs et gaines" for level in draft.levels)
    assert draft.levels[0].parts[0].overhang == Decimal("10")
    assert draft.levels[2].start_elevations == (Decimal("3.30"),)


def test_multiple_start_cotes_are_preserved_and_heights_are_derived(tmp_path: Path) -> None:
    draft = parse_dxf(_build_horizontal_fixture(tmp_path / "multiple-cotes.dxf"))
    ground_floor = next(level for level in draft.levels if level.name == "Rez-de-chaussée")

    assert ground_floor.start_elevations == (Decimal("0.00"), Decimal("0.60"))
    assert ground_floor.end_elevations == (Decimal("3.60"),)
    assert ground_floor.interior_heights == (Decimal("3.60"), Decimal("3.00"))
    assert not ground_floor.elevation_ambiguous
    assert ground_floor.confidence.value == "moyenne"
    assert not any(warning.startswith("CAD_LEVEL_MULTIPLE_ELEVATIONS:") for warning in draft.warnings)


def test_multiple_end_cotes_and_confirmed_heights_are_high_confidence(tmp_path: Path) -> None:
    draft = parse_dxf(_build_multi_end_fixture(tmp_path / "multi-end.dxf", confirm_heights=True))
    level = draft.levels[0]

    assert level.start_elevations == (Decimal("0.20"),)
    assert level.end_elevations == (Decimal("3.10"), Decimal("5.70"))
    assert level.interior_heights == (Decimal("2.90"), Decimal("5.50"))
    assert level.confidence.value == "élevée"
    assert not level.elevation_ambiguous
    assert {item.raw_value for item in level.evidence} >= {"2.90", "5.50"}
    assert not any(warning.startswith("CAD_LEVEL_MULTIPLE_ELEVATIONS:") for warning in draft.warnings)


def test_isolated_height_numbers_do_not_confirm_calculated_heights(tmp_path: Path) -> None:
    draft = parse_dxf(_build_multi_end_fixture(
        tmp_path / "isolated-heights.dxf", confirm_heights=False, isolated_label=True,
    ))
    level = draft.levels[0]

    assert level.interior_heights == (Decimal("2.90"), Decimal("5.50"))
    assert level.confidence.value == "moyenne"
    assert all(item.raw_value not in {"2.90", "5.50"} for item in level.evidence)


def test_non_deterministic_or_unstructured_cotes_remain_for_manual_review() -> None:
    starts, ends, heights, ambiguous = _elevations(
        "Des cotes +0.00m et +0.20m aux cotes +3.00m, +3.20m et +5.50m"
    )
    assert starts == (Decimal("0.00"), Decimal("0.20"))
    assert ends == (Decimal("3.00"), Decimal("3.20"), Decimal("5.50"))
    assert heights == ()
    assert ambiguous

    starts, ends, heights, ambiguous = _elevations("+0.20 +3.10 +5.70")
    assert starts == (Decimal("0.20"),)
    assert ends == (Decimal("3.10"), Decimal("5.70"))
    assert heights == ()
    assert ambiguous


def test_native_autocad_table_cells_take_priority_when_available(tmp_path: Path) -> None:
    table = DxfNativeTable(
        cells=(
            ("Privatives", "Communes", "Intérieur du titre", "Avec Surplomb", "Consistances", "Observations"),
            ("4-4a", "", "69", "80", "Appartement", "4a = 11 m² en surplomb"),
            ("", "2", "8", "8", "Murs et gaines", ""),
        ),
        x=10,
        y=100,
        entity_reference="ABC",
    )
    loaded = DxfLoadResult(
        source=tmp_path / "native.dxf", fingerprint="abc", size_bytes=1,
        texts=[
            DxfTextItem("Plan du Premier Étage", 10, 101, .2, "T1"),
            DxfTextItem("De la cote +3,40m à la cote +6,40m", 10, 100.5, .1, "T2"),
        ],
        lines=[], entity_counts={"ACAD_TABLE": 1}, native_tables=[table],
    )

    level = _native_table_to_level(loaded, table, 0)

    assert level.name == "Premier Étage"
    assert level.start_elevations == (Decimal("3.40"),)
    assert level.end_elevations == (Decimal("6.40"),)
    assert level.interior_heights == (Decimal("3.00"),)
    assert [part.index for part in level.parts] == ["4-4a", "2"]
    assert level.parts[0].overhang == Decimal("11")


def test_incomplete_grid_uses_spatial_fallback_with_reduced_confidence(tmp_path: Path) -> None:
    draft = parse_dxf(_build_fixture(tmp_path / "partial-grid.dxf", 3, complete_grid=False))

    assert len(draft.levels) == 3
    assert all(level.confidence.value != "élevée" for level in draft.levels)
    assert draft.levels[0].parts[0].index == "4-4a"


def test_review_application_is_atomic_and_keeps_original_untouched(tmp_path: Path) -> None:
    draft = parse_dxf(_build_fixture(tmp_path / "atomic.dxf", 2))
    original = Project(identity=ProjectIdentity(land_title="MANUEL/01", property_name="Dossier manuel"))
    before = deepcopy(project_to_dict(original))
    selected = {field: candidate.value for field, candidate in draft.values.items()}

    reviewed = apply_reviewed_draft(original, draft, selected, replace_levels=True)

    assert project_to_dict(original) == before
    assert reviewed is not original
    assert reviewed.identity.property_name == "Résidence Émeraude"
    assert len(reviewed.levels) == 2
    assert reviewed.decisions[-1].source_fingerprint == draft.fingerprint
    reopened = project_from_dict(project_to_dict(reviewed))
    assert reopened.decisions[-1].source_fingerprint == draft.fingerprint
    assert reopened.levels[0].parts[0].evidence[0].entity_reference


def test_existing_project_keeps_levels_when_replacement_is_not_selected(tmp_path: Path) -> None:
    draft = parse_dxf(_build_fixture(tmp_path / "comparison.dxf", 3))
    existing_level = Level("Niveau manuel", 0, (Decimal("0"),), (Decimal("3"),), (Decimal("3"),))
    original = Project(
        identity=ProjectIdentity(land_title="MANUEL/01", property_name="Dossier manuel"),
        levels=[existing_level],
    )

    reviewed = apply_reviewed_draft(original, draft, {}, replace_levels=False)

    assert reviewed.levels[0].id == existing_level.id
    assert reviewed.levels[0].name == "Niveau manuel"


def test_wizard_cancel_path_does_not_mutate_project(tmp_path: Path) -> None:
    application = QApplication.instance() or QApplication([])
    draft = parse_dxf(_build_fixture(tmp_path / "wizard.dxf", 2))
    original = Project(identity=ProjectIdentity(land_title="MANUEL/01", property_name="Dossier manuel"))
    before = deepcopy(project_to_dict(original))

    dialog = CadImportWizard(original, draft)
    dialog.reject()
    application.processEvents()

    assert dialog.reviewed_project is None
    assert project_to_dict(original) == before
    assert not dialog.replace_levels.isChecked()


def test_wizard_apply_button_applies_review_and_accepts_dialog(tmp_path: Path) -> None:
    application = QApplication.instance() or QApplication([])
    draft = parse_dxf(_build_multi_end_fixture(tmp_path / "wizard-apply.dxf", confirm_heights=True))
    original = Project(identity=ProjectIdentity(land_title="", property_name=""))

    dialog = CadImportWizard(original, draft)
    assert dialog.detail_start.text() == "+0,20"
    assert dialog.detail_end.text() == "+3,10 ; +5,70"
    assert dialog.detail_height.text() == "2,90 ; 5,50"
    dialog.apply_button.click()
    application.processEvents()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.reviewed_project is not None
    assert dialog.reviewed_project.levels[0].start_elevations == (Decimal("0.20"),)
    assert dialog.reviewed_project.levels[0].end_elevations == (Decimal("3.10"), Decimal("5.70"))
    assert dialog.reviewed_project.levels[0].interior_heights == (Decimal("2.90"), Decimal("5.50"))


def test_wizard_preserves_reviewed_multi_value_edits(tmp_path: Path) -> None:
    application = QApplication.instance() or QApplication([])
    draft = parse_dxf(_build_multi_end_fixture(tmp_path / "wizard-edit.dxf", confirm_heights=True))
    dialog = CadImportWizard(Project(identity=ProjectIdentity(land_title="", property_name="")), draft)

    dialog.detail_end.setText("+3,10 ; +5,70 ; +6,20")
    dialog.detail_height.setText("2,90 ; 5,50 ; 6,00")
    dialog.apply_button.click()
    application.processEvents()

    assert dialog.reviewed_project is not None
    level = dialog.reviewed_project.levels[0]
    assert level.end_elevations == (Decimal("3.10"), Decimal("5.70"), Decimal("6.20"))
    assert level.interior_heights == (Decimal("2.90"), Decimal("5.50"), Decimal("6.00"))


def test_dwg_temporary_conversion_is_always_removed(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source.dwg"
    source.write_bytes(b"dwg-placeholder")
    temporary = tmp_path / "converted" / "source.dxf"
    temporary.parent.mkdir()
    _build_fixture(temporary, 2)
    monkeypatch.setattr("copro_auto.cad_import.service.convert_dwg_to_dxf", lambda _source: temporary)

    draft = import_cad(source)

    assert len(draft.levels) == 2
    assert draft.source == source.resolve()
    assert not temporary.parent.exists()


def test_reviewed_cad_draft_can_complete_the_five_document_flow(tmp_path: Path) -> None:
    draft = parse_dxf(_build_fixture(tmp_path / "complete-flow.dxf", 3))
    original = Project(identity=ProjectIdentity(land_title="", property_name=""))
    selected = {field: candidate.value for field, candidate in draft.values.items()}
    project = apply_reviewed_draft(original, draft, selected, replace_levels=True)
    project.identity.commune = "Meknès"
    project.identity.surveyor = "A. TOPOGRAPHE"
    project.identity.land_registry_office = "Meknès Al Ismaïlia"
    project.identity.land_area = Decimal("77")
    project.identity.total_height = Decimal("9")
    project.identity.overall_consistency = "RDC + 2 étages"
    project.identity.client = ClientInformation(
        full_name="Client de test", national_id="TEST0001", address="Adresse de test",
        capacity="Propriétaire", national_id_expiry=date(2030, 1, 1),
    )
    project.identity.boundaries = {
        "northeast": "Voie 1", "northwest": "Lot 2", "southeast": "Lot 3", "southwest": "Rue 4",
    }
    for level in project.levels:
        for part in level.parts:
            part.description = part.consistency

    issues = validate_project(project)
    assert not has_errors(issues)
    outputs = DocumentGenerationService().generate(project, tmp_path / "documents")

    assert len(outputs) == 5
    assert {path.name for path in outputs} == {
        "PV_Division.docx", "Reglement_Copropriete.docx", "Tableau_A.docx",
        "Tableau_B.docx", "Tableau_Recapitulatif.docx",
    }
