from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from copro_auto.cad_import.dxf_parser import CadImportResult
from copro_auto.cad_import.service import apply_choice, compare
from copro_auto.domain.models import Project

from .theme import LIGHT


FIELD_LABELS = {
    "identity.land_title": "Titre foncier",
    "identity.property_name": "Nom de la propriété",
    "identity.prefecture": "Préfecture",
    "identity.subdivision": "Lotissement / secteur",
}

STATUS_PRESENTATION = {
    "identique": ("success", QStyle.StandardPixmap.SP_DialogApplyButton, LIGHT.success, LIGHT.success_soft),
    "différent": ("danger", QStyle.StandardPixmap.SP_MessageBoxCritical, LIGHT.danger, LIGHT.danger_soft),
    "manquant": ("warning", QStyle.StandardPixmap.SP_MessageBoxWarning, LIGHT.warning, LIGHT.warning_soft),
}


class ImportReviewDialog(QDialog):
    def __init__(self, project: Project, result: CadImportResult, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("AppDialog")
        self.setWindowTitle("Comparer la saisie avec le dessin")
        self.resize(960, min(720, 350 + max(1, len(compare(project, result))) * 42))
        self.setMinimumSize(760, 420)
        self.project = project
        self.comparisons = compare(project, result)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)
        title = QLabel("Comparaison manuelle ↔ DWG/DXF")
        title.setProperty("role", "dialogTitle")
        layout.addWidget(title)
        explanation = QLabel(
            "La saisie manuelle reste sélectionnée par défaut. Choisissez explicitement une valeur "
            "du dessin pour la rendre active."
        )
        explanation.setWordWrap(True)
        explanation.setProperty("role", "muted")
        layout.addWidget(explanation)

        self.table = QTableWidget(len(self.comparisons), 5)
        self.table.setHorizontalHeaderLabels(("Champ", "Saisie manuelle", "Dessin", "État", "Valeur active"))
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(220)
        for row, comparison in enumerate(self.comparisons):
            values = (
                FIELD_LABELS.get(comparison.field, comparison.field),
                comparison.manual_value or "—",
                comparison.cad_value or "—",
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
            normalized = comparison.status.casefold()
            tone, icon_name, foreground, background = STATUS_PRESENTATION.get(
                normalized,
                ("warning", QStyle.StandardPixmap.SP_MessageBoxWarning, LIGHT.warning, LIGHT.warning_soft),
            )
            status = QTableWidgetItem(comparison.status.capitalize())
            status.setData(Qt.ItemDataRole.UserRole + 1, tone)
            status.setIcon(self.style().standardIcon(icon_name))
            status.setForeground(QBrush(foreground))
            status.setBackground(QBrush(background))
            self.table.setItem(row, 3, status)
            choice = QComboBox()
            choice.setAccessibleName(f"Valeur active — {values[0]}")
            if comparison.manual_value is not None:
                choice.addItem("Saisie manuelle", False)
            if comparison.cad_value is not None:
                choice.addItem("Valeur DWG/DXF", True)
            self.table.setCellWidget(row, 4, choice)
        layout.addWidget(self.table, 1)

        if result.warnings:
            self.warning = QLabel(" · ".join(result.warnings))
            self.warning.setWordWrap(True)
            self.warning.setProperty("role", "status")
            self.warning.setProperty("tone", "warning")
            layout.addWidget(self.warning)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Apply
        )
        self.apply_button = self.buttons.button(QDialogButtonBox.StandardButton.Apply)
        self.cancel_button = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        self.apply_button.setText("Appliquer les choix")
        self.apply_button.setProperty("variant", "primary")
        self.apply_button.setDefault(True)
        self.cancel_button.setText("Annuler")
        self.cancel_button.setProperty("variant", "secondary")
        self.buttons.accepted.connect(self._apply)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _apply(self) -> None:
        for row, comparison in enumerate(self.comparisons):
            choice = self.table.cellWidget(row, 4)
            if choice is not None and choice.count():
                apply_choice(self.project, comparison, bool(choice.currentData()))
        self.accept()
