from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QStyle, QVBoxLayout

from copro_auto.domain.models import Project
from copro_auto.domain.validation import ValidationIssue

from .theme import LIGHT


FIELD_LOCATIONS = {
    "identity.land_title": "Projet · Titre foncier",
    "identity.property_name": "Projet · Nom de la propriété",
    "identity.land_area": "Projet · Surface du terrain",
    "identity.prefecture": "Projet · Préfecture",
    "identity.commune": "Projet · Commune",
    "identity.subdivision": "Projet · Lotissement / secteur",
    "identity.surveyor": "Projet · Topographe",
    "identity.overall_consistency": "Projet · Consistance générale",
    "identity.total_height": "Projet · Hauteur totale",
}


class ValidationPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        heading = QHBoxLayout()
        title = QLabel("Contrôle du dossier")
        title.setProperty("role", "section")
        self.count = QLabel("0 anomalie")
        self.count.setProperty("role", "muted")
        heading.addWidget(title)
        heading.addStretch()
        heading.addWidget(self.count)
        layout.addLayout(heading)
        note = QLabel("Les erreurs bloquent la génération. Les avertissements restent vérifiables.")
        note.setWordWrap(True)
        note.setProperty("role", "muted")
        layout.addWidget(note)
        self.list = QListWidget()
        self.list.setAccessibleName("Résultats du contrôle du dossier")
        self.list.setAlternatingRowColors(False)
        self.list.setMinimumWidth(260)
        self.list.setWordWrap(True)
        layout.addWidget(self.list, 1)

    @staticmethod
    def _location(field: str, project: Project | None) -> str:
        if field in FIELD_LOCATIONS:
            return FIELD_LOCATIONS[field]
        if project is None:
            return field
        if field == "levels":
            return "Niveaux"
        if field == "levels.parts":
            return "Niveaux et parties"
        for level in project.levels:
            level_prefix = f"levels.{level.id}"
            if not field.startswith(level_prefix):
                continue
            level_name = level.name.strip() or f"Niveau {level.order + 1}"
            for part in level.parts:
                if field.startswith(f"{level_prefix}.parts.{part.id}"):
                    index = part.index.strip() or "non renseigné"
                    return f"{level_name} · Indice {index}"
            return f"Niveau · {level_name}"
        return field.replace("identity.", "Projet · ").replace("_", " ").capitalize()

    def set_issues(self, issues: list[ValidationIssue], project: Project | None = None) -> None:
        self.list.clear()
        errors = sum(issue.severity.value == "error" for issue in issues)
        self.count.setText(f"{errors} erreur(s) · {len(issues) - errors} avertissement(s)")
        if not issues:
            item = QListWidgetItem("Dossier cohérent — prêt pour la génération")
            item.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
            item.setData(Qt.ItemDataRole.UserRole, "success")
            item.setForeground(QBrush(LIGHT.success))
            item.setBackground(QBrush(LIGHT.success_soft))
            self.list.addItem(item)
            return
        for issue in issues:
            is_error = issue.severity.value == "error"
            tone = "danger" if is_error else "warning"
            icon = QStyle.StandardPixmap.SP_MessageBoxCritical if is_error else QStyle.StandardPixmap.SP_MessageBoxWarning
            foreground = LIGHT.danger if is_error else LIGHT.warning
            background = LIGHT.danger_soft if is_error else LIGHT.warning_soft
            item = QListWidgetItem(f"{issue.message}\n{self._location(issue.field, project)}")
            item.setIcon(self.style().standardIcon(icon))
            item.setToolTip(issue.message)
            item.setData(Qt.ItemDataRole.UserRole, tone)
            item.setData(Qt.ItemDataRole.UserRole + 1, issue.field)
            item.setForeground(QBrush(foreground))
            item.setBackground(QBrush(background))
            self.list.addItem(item)
