from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton, QTableWidgetItem
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt

from copro_auto.domain.calculations import calculate_shares
from copro_auto.domain.models import PartNature, Project, ProjectIdentity
from copro_auto.domain.validation import validate_project
from copro_auto.ui.main_window import MainWindow
from copro_auto.ui.project_editor import ProjectEditor
from copro_auto.ui.validation_panel import ValidationPanel
from sample_projects import build_yasmin_project


def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_project_editor_preserves_manual_surface_decompositions() -> None:
    _application()
    editor = ProjectEditor()
    editor.set_project(build_yasmin_project())

    project = editor.project()

    assert [len(level.parts) for level in project.levels] == [3, 4, 4, 4]
    first_floor = project.levels[1].parts[0].surfaces
    assert first_floor.cadastral_total == 80
    assert first_floor.architectural_total == 80
    assert [share.ten_thousandths for share in calculate_shares(project)] == [3522, 3239, 3239]


def test_selected_level_row_always_drives_parts_editor() -> None:
    app = _application()
    editor = ProjectEditor()
    editor.set_project(build_yasmin_project())
    editor.show()
    app.processEvents()

    QTest.mouseClick(
        editor.levels.viewport(),
        Qt.MouseButton.LeftButton,
        pos=editor.levels.visualItemRect(editor.levels.item(1, 0)).center(),
    )
    app.processEvents()

    assert editor.levels.currentRow() == 1
    assert editor.part_title.text() == "Parties · Premier Étage"
    assert editor.parts.rowCount() == 4


def test_new_level_selection_allows_adding_parts_to_that_level() -> None:
    app = _application()
    editor = ProjectEditor()
    editor.set_project(Project(identity=ProjectIdentity(land_title="", property_name="")))
    editor.show()
    app.processEvents()
    buttons = {button.text(): button for button in editor.findChildren(QPushButton)}

    for name in ("Rez-de-chaussée", "Premier Étage", "Deuxième Étage"):
        QTest.mouseClick(buttons["+ Ajouter un niveau"], Qt.MouseButton.LeftButton)
        editor.levels.item(editor.levels.rowCount() - 1, 0).setText(name)
    app.processEvents()

    QTest.mouseClick(
        editor.levels.viewport(),
        Qt.MouseButton.LeftButton,
        pos=editor.levels.visualItemRect(editor.levels.item(1, 0)).center(),
    )
    QTest.mouseClick(buttons["+ Ajouter une partie"], Qt.MouseButton.LeftButton)
    app.processEvents()

    assert editor.levels.currentRow() == 1
    assert editor.part_title.text() == "Parties · Premier Étage"
    assert editor.parts.rowCount() == 1
    first_snapshot = editor.project()
    second_snapshot = editor.project()
    assert [level.id for level in first_snapshot.levels] == [level.id for level in second_snapshot.levels]
    assert first_snapshot.levels[1].parts[0].id == second_snapshot.levels[1].parts[0].id


def test_project_editor_recovers_part_row_without_nature_dropdown() -> None:
    _application()
    editor = ProjectEditor()
    editor.set_project(build_yasmin_project())
    row = editor.parts.rowCount()
    editor.parts.insertRow(row)
    editor.parts.setItem(row, 0, QTableWidgetItem("Legacy"))

    project = editor.project()

    recovered = project.levels[0].parts[-1]
    assert recovered.index == "Legacy"
    assert recovered.nature is PartNature.PRIVATE


def test_validation_panel_shows_level_and_index_instead_of_uuids() -> None:
    _application()
    project = build_yasmin_project()
    project.levels[1].parts[0].observations = ""
    panel = ValidationPanel()

    panel.set_issues(validate_project(project), project)

    messages = [panel.list.item(row).text() for row in range(panel.list.count())]
    assert any("Premier Étage · Indice 4-4a" in message for message in messages)
    assert all("levels." not in message for message in messages)


def test_main_window_accepts_complete_manual_project(monkeypatch) -> None:
    monkeypatch.setenv("COPRO_AUTO_DEV_LICENSE", "1")
    _application()
    window = MainWindow()
    window._building = True
    window.editor.set_project(build_yasmin_project())
    window._building = False

    assert window.refresh_validation() == []
    assert not window.validation_timer.isActive()
    assert window.generate_button.isEnabled()
    assert window.surface_metric.text() == "247 m²"
    assert window.share_metric.text() == "10 000"


def test_discard_unsaved_changes_uses_button_value(monkeypatch) -> None:
    monkeypatch.setenv("COPRO_AUTO_DEV_LICENSE", "1")
    _application()
    window = MainWindow()
    window.dirty = True

    class DiscardResult:
        def __eq__(self, other: object) -> bool:
            return other == QMessageBox.StandardButton.Discard

    monkeypatch.setattr(QMessageBox, "question", lambda *_args, **_kwargs: DiscardResult())

    assert window._can_discard()
