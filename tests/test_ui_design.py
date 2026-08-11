from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton

from copro_auto.cad_import.dxf_parser import CadImportResult
from copro_auto.domain.models import Project, ProjectIdentity
from copro_auto.licensing.service import LicenseDecision, LicenseState
from copro_auto.ui.dialogs import build_message_box
from copro_auto.ui.import_review import ImportReviewDialog
from copro_auto.ui.license_dialog import LicenseDialog
from copro_auto.ui.main_window import MainWindow
from copro_auto.ui.theme import apply_theme


def _application() -> QApplication:
    application = QApplication.instance() or QApplication([])
    apply_theme(application)
    return application


def _global_rect(widget) -> QRect:
    return QRect(widget.mapToGlobal(widget.rect().topLeft()), widget.size())


class _InvalidLicenseService:
    @staticmethod
    def evaluate() -> LicenseDecision:
        return LicenseDecision(LicenseState.INVALID, "Signature du jeton de licence invalide.")


def test_theme_covers_every_app_owned_dialog_surface_and_scrollbar() -> None:
    application = _application()
    stylesheet = application.styleSheet()

    assert "QDialog, QMessageBox" in stylesheet
    assert "QMessageBox QLabel#qt_msgbox_label" in stylesheet
    assert "QScrollBar:horizontal" in stylesheet
    assert "QCalendarWidget" in stylesheet
    assert "QMenu" in stylesheet


def test_message_box_factory_localizes_all_standard_actions() -> None:
    _application()
    buttons = (
        QMessageBox.StandardButton.Ok
        | QMessageBox.StandardButton.Yes
        | QMessageBox.StandardButton.No
        | QMessageBox.StandardButton.Save
        | QMessageBox.StandardButton.Discard
        | QMessageBox.StandardButton.Cancel
        | QMessageBox.StandardButton.Close
    )

    box = build_message_box(
        None,
        QMessageBox.Icon.Information,
        "Information",
        "Message lisible",
        buttons=buttons,
        default=QMessageBox.StandardButton.Ok,
        tone="info",
        danger=QMessageBox.StandardButton.Discard,
    )

    expected = {
        QMessageBox.StandardButton.Ok: "OK",
        QMessageBox.StandardButton.Yes: "Oui",
        QMessageBox.StandardButton.No: "Non",
        QMessageBox.StandardButton.Save: "Enregistrer",
        QMessageBox.StandardButton.Discard: "Ignorer",
        QMessageBox.StandardButton.Cancel: "Annuler",
        QMessageBox.StandardButton.Close: "Fermer",
    }
    assert box.property("tone") == "info"
    for standard_button, label in expected.items():
        assert box.button(standard_button).text() == label
    assert box.button(QMessageBox.StandardButton.Ok).property("variant") == "primary"
    assert box.button(QMessageBox.StandardButton.Discard).property("variant") == "danger"


def test_license_dialog_exposes_a_semantic_status_and_safe_action_hierarchy() -> None:
    _application()
    dialog = LicenseDialog(_InvalidLicenseService())

    assert dialog.objectName() == "AppDialog"
    assert dialog.status_container.property("tone") == "danger"
    assert dialog.status.text() == "Signature du jeton de licence invalide."
    assert dialog.activate_button.property("variant") == "primary"
    assert dialog.deactivate_button.property("variant") == "danger"
    assert dialog.key.accessibleName() == "Clé de licence"


def test_import_review_uses_french_actions_and_semantic_statuses() -> None:
    _application()
    project = Project(identity=ProjectIdentity(
        land_title="119753/59",
        property_name="YASMIN 71",
        prefecture="Meknès",
        subdivision="Yasmin",
    ))
    dialog = ImportReviewDialog(project, CadImportResult(source=Path("reference.dxf")))

    assert dialog.cancel_button.text() == "Annuler"
    assert dialog.apply_button.text() == "Appliquer les choix"
    assert dialog.apply_button.property("variant") == "primary"
    assert {dialog.table.item(row, 3).data(257) for row in range(dialog.table.rowCount())} == {"warning"}


def test_minimum_window_keeps_editor_controls_separate(monkeypatch) -> None:
    monkeypatch.setenv("COPRO_AUTO_DEV_LICENSE", "1")
    application = _application()
    window = MainWindow()
    window.resize(1080, 700)
    window.editor.tabs.setCurrentIndex(1)
    window.show()
    application.processEvents()

    assert window.validation_panel.maximumWidth() == 360
    assert window.editor.levels.minimumHeight() <= 110
    assert window.editor.parts.minimumHeight() <= 150
    assert not _global_rect(window.editor.levels).intersects(_global_rect(window.editor.part_title))
    assert not _global_rect(window.editor.parts).intersects(_global_rect(window.editor.levels_help))
