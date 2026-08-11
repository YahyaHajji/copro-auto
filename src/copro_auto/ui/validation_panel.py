from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QVBoxLayout

from copro_auto.domain.models import Project
from copro_auto.domain.validation import ValidationIssue


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
        self.list.setAlternatingRowColors(True)
        self.list.setMinimumWidth(290)
        layout.addWidget(self.list, 1)

    @staticmethod
    def _location(field: str, project: Project | None) -> str:
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
        return field

    def set_issues(self, issues: list[ValidationIssue], project: Project | None = None) -> None:
        self.list.clear()
        errors = sum(issue.severity.value == "error" for issue in issues)
        self.count.setText(f"{errors} erreur(s) · {len(issues) - errors} avertissement(s)")
        if not issues:
            item = QListWidgetItem("✓ Dossier cohérent — prêt pour la génération")
            item.setData(Qt.ItemDataRole.UserRole, "ok")
            self.list.addItem(item)
            return
        for issue in issues:
            prefix = "●" if issue.severity.value == "error" else "◆"
            item = QListWidgetItem(f"{prefix} {issue.message}\n{self._location(issue.field, project)}")
            item.setToolTip(issue.message)
            item.setData(Qt.ItemDataRole.UserRole, issue.field)
            self.list.addItem(item)
