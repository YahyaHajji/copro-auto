from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from copro_auto.cad_import.dxf_parser import CadImportResult
from copro_auto.cad_import.service import Comparison, apply_choice, compare
from copro_auto.domain.models import Project


FIELD_LABELS = {
    "identity.land_title": "Titre foncier",
    "identity.property_name": "Nom de la propriété",
    "identity.prefecture": "Préfecture",
    "identity.subdivision": "Lotissement / secteur",
}


class ImportReviewDialog(QDialog):
    def __init__(self, project: Project, result: CadImportResult, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Comparer la saisie avec le dessin")
        self.resize(920, 480)
        self.project = project
        self.comparisons = compare(project, result)
        layout = QVBoxLayout(self)
        title = QLabel("Comparaison manuelle ↔ DWG/DXF")
        title.setProperty("role", "title")
        layout.addWidget(title)
        explanation = QLabel(
            "La saisie manuelle reste sélectionnée par défaut. Choisissez explicitement une valeur du dessin pour la rendre active."
        )
        explanation.setWordWrap(True)
        explanation.setProperty("role", "muted")
        layout.addWidget(explanation)
        self.table = QTableWidget(len(self.comparisons), 5)
        self.table.setHorizontalHeaderLabels(("Champ", "Saisie manuelle", "Dessin", "État", "Valeur active"))
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for row, comparison in enumerate(self.comparisons):
            values = (
                FIELD_LABELS.get(comparison.field, comparison.field), comparison.manual_value or "—",
                comparison.cad_value or "—", comparison.status,
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
            choice = QComboBox()
            if comparison.manual_value is not None:
                choice.addItem("Saisie manuelle", False)
            if comparison.cad_value is not None:
                choice.addItem("Valeur DWG/DXF", True)
            self.table.setCellWidget(row, 4, choice)
        layout.addWidget(self.table)
        if result.warnings:
            warning = QLabel(" · ".join(result.warnings))
            warning.setWordWrap(True)
            warning.setProperty("role", "muted")
            layout.addWidget(warning)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Apply)
        buttons.button(QDialogButtonBox.StandardButton.Apply).setText("Appliquer les choix")
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply(self) -> None:
        for row, comparison in enumerate(self.comparisons):
            choice = self.table.cellWidget(row, 4)
            if choice is not None and choice.count():
                apply_choice(self.project, comparison, bool(choice.currentData()))
        self.accept()
