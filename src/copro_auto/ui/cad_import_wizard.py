from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStyle,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from copro_auto.cad_import.models import CadConfidence, CadImportDraft, CadLevelDraft, CadPartDraft
from copro_auto.cad_import.service import apply_reviewed_draft, compare, project_is_empty
from copro_auto.domain.models import PartNature, Project

from .theme import LIGHT


FIELD_LABELS = {
    "identity.land_title": "Titre foncier",
    "identity.property_name": "Nom de la propriété",
    "identity.prefecture": "Préfecture",
    "identity.commune": "Commune",
    "identity.subdivision": "Lotissement / secteur",
}

STATUS_PRESENTATION = {
    "identique": ("success", QStyle.StandardPixmap.SP_DialogApplyButton, LIGHT.success, LIGHT.success_soft),
    "différent": ("danger", QStyle.StandardPixmap.SP_MessageBoxCritical, LIGHT.danger, LIGHT.danger_soft),
    "manquant": ("warning", QStyle.StandardPixmap.SP_MessageBoxWarning, LIGHT.warning, LIGHT.warning_soft),
}

TREE_COLUMNS = (
    "Type", "Niveau", "Indice", "Nature", "Cotes début", "Cotes fin", "Hauteurs",
    "Surface", "Surplomb", "Consistance", "Observations", "Suggestion pièces", "Confiance",
    "Suggestion acceptée",
)

WARNING_LABELS = {
    "CAD_NO_TEXT": "Aucun texte exploitable n’a été trouvé dans le dessin.",
    "CAD_NO_CONTAINMENT_TABLE": "Aucun tableau des contenances n’a été détecté.",
}


def _decimal_values(text: str) -> tuple[Decimal, ...]:
    values: list[Decimal] = []
    for token in text.replace("\n", ";").split(";"):
        normalized = token.strip().replace(",", ".")
        if not normalized:
            continue
        try:
            value = Decimal(normalized)
        except InvalidOperation as exc:
            raise ValueError(f"Liste de nombres CAD invalide : « {text} »") from exc
        if value not in values:
            values.append(value)
    return tuple(values)


def _format_decimal_values(values: tuple[Decimal, ...], *, signed: bool) -> str:
    pattern = "+.2f" if signed else ".2f"
    return " ; ".join(format(value, pattern).replace(".", ",") for value in values)


def _warning_label(code: str) -> str:
    if code.startswith("CAD_LEVEL_WITHOUT_PARTS:"):
        return f"Le niveau détecté n° {int(code.rsplit(':', 1)[1]) + 1} ne contient aucune partie exploitable."
    if code.startswith("CAD_LEVEL_MISSING_ELEVATION:"):
        return f"La cote du niveau détecté n° {int(code.rsplit(':', 1)[1]) + 1} reste à vérifier."
    if code.startswith("CAD_LEVEL_MULTIPLE_ELEVATIONS:"):
        return (
            f"Le niveau détecté n° {int(code.rsplit(':', 1)[1]) + 1} contient des cotes "
            "dont l’association début/fin est incertaine : vérifiez les listes et les hauteurs proposées."
        )
    return WARNING_LABELS.get(code, code)


class CadImportWizard(QDialog):
    def __init__(self, project: Project, draft: CadImportDraft, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("AppDialog")
        self.setWindowTitle("Revoir l’import DWG/DXF")
        self.resize(1180, 760)
        self.setMinimumSize(900, 600)
        self.original_project = project
        self.draft = deepcopy(draft)
        self.reviewed_project: Project | None = None
        self.comparisons = compare(project, draft)
        self.value_editors: dict[str, QLineEdit] = {}
        self._loading_detail = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)
        title = QLabel("Revue obligatoire de l’extraction CAD")
        title.setProperty("role", "dialogTitle")
        layout.addWidget(title)
        explanation = QLabel(
            "Le dessin prépare un brouillon. Rien ne modifie le dossier avant « Appliquer les choix ». "
            "Les suggestions de pièces restent facultatives et ne sont pas copiées automatiquement."
        )
        explanation.setWordWrap(True)
        explanation.setProperty("role", "muted")
        layout.addWidget(explanation)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._summary_page(), "Résumé")
        self.tabs.addTab(self._identity_page(), "Projet")
        self.tabs.addTab(self._levels_page(), "Niveaux et parties")
        self.tabs.addTab(self._missing_page(), "Champs manquants")
        layout.addWidget(self.tabs, 1)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Apply)
        self.apply_button = self.buttons.button(QDialogButtonBox.StandardButton.Apply)
        self.cancel_button = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        self.apply_button.setText("Appliquer les choix")
        self.apply_button.setProperty("variant", "primary")
        self.apply_button.setDefault(True)
        self.cancel_button.setText("Annuler")
        self.cancel_button.setProperty("variant", "secondary")
        self.apply_button.clicked.connect(self._apply)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _summary_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 16, 12, 12)
        summary = QLabel(
            f"{len(self.draft.levels)} niveau(x) · {self.draft.part_count} partie(s) · "
            f"{len(self.draft.values)} champ(s) de projet détecté(s)"
        )
        summary.setProperty("role", "title")
        layout.addWidget(summary)
        source = QLabel(
            f"Source : {self.draft.source.name}\n"
            f"Empreinte : {self.draft.fingerprint[:12] or 'non calculée'} · {self.draft.size_bytes} octets"
        )
        source.setProperty("role", "muted")
        layout.addWidget(source)
        if self.draft.warnings:
            warning = QLabel("Avertissements techniques :\n• " + "\n• ".join(map(_warning_label, self.draft.warnings)))
            warning.setWordWrap(True)
            warning.setProperty("role", "status")
            warning.setProperty("tone", "warning")
            layout.addWidget(warning)
        else:
            ok = QLabel("Le dessin a été lu sans avertissement technique.")
            ok.setProperty("role", "status")
            ok.setProperty("tone", "success")
            layout.addWidget(ok)
        layout.addStretch()
        return page

    def _identity_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.table = QTableWidget(len(self.comparisons), 7)
        self.table.setHorizontalHeaderLabels((
            "Champ", "Saisie manuelle", "Dessin", "État", "Confiance", "Source retenue", "Valeur retenue",
        ))
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        for row, comparison in enumerate(self.comparisons):
            label = FIELD_LABELS.get(comparison.field, comparison.field)
            self.table.setItem(row, 0, QTableWidgetItem(label))
            self.table.setItem(row, 1, QTableWidgetItem(comparison.manual_value or "—"))
            self.table.setItem(row, 2, QTableWidgetItem(comparison.cad_value or "—"))
            tone, icon_name, foreground, background = STATUS_PRESENTATION[comparison.status]
            status = QTableWidgetItem(comparison.status.capitalize())
            status.setData(Qt.ItemDataRole.UserRole + 1, tone)
            status.setIcon(self.style().standardIcon(icon_name))
            status.setForeground(QBrush(foreground))
            status.setBackground(QBrush(background))
            self.table.setItem(row, 3, status)
            confidence = comparison.candidate.confidence.value if comparison.candidate else "—"
            self.table.setItem(row, 4, QTableWidgetItem(confidence.capitalize()))
            source = QComboBox()
            source.setAccessibleName(f"Source retenue — {label}")
            if comparison.manual_value is not None:
                source.addItem("Saisie manuelle", comparison.manual_value)
            if comparison.cad_value is not None:
                source.addItem("Valeur DWG/DXF", comparison.cad_value)
            editor = QLineEdit()
            initial = comparison.manual_value if comparison.manual_value is not None else comparison.cad_value or ""
            editor.setText(initial)
            editor.setAccessibleName(f"Valeur retenue — {label}")
            source.currentIndexChanged.connect(lambda _index, combo=source, line=editor: line.setText(combo.currentData() or ""))
            self.table.setCellWidget(row, 5, source)
            self.table.setCellWidget(row, 6, editor)
            self.value_editors[comparison.field] = editor
        layout.addWidget(self.table)
        return page

    def _levels_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.replace_levels = QCheckBox("Utiliser les niveaux et parties relus ci-dessous")
        self.replace_levels.setChecked(project_is_empty(self.original_project))
        if not project_is_empty(self.original_project):
            self.replace_levels.setText("Remplacer explicitement les niveaux actuels par les niveaux relus ci-dessous")
        layout.addWidget(self.replace_levels)
        note = QLabel("Sur un dossier existant, cette option reste décochée afin de protéger la saisie manuelle.")
        note.setProperty("role", "muted")
        layout.addWidget(note)
        self.level_tree = QTreeWidget()
        self.level_tree.setColumnCount(len(TREE_COLUMNS))
        self.level_tree.setHeaderLabels(TREE_COLUMNS)
        self.level_tree.setAlternatingRowColors(True)
        self.level_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.level_tree.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        for level in self.draft.levels:
            self._append_level(level)
        self.level_tree.expandAll()
        for column in (4, 5, 6, 7, 8, 10, 11, 13):
            self.level_tree.setColumnHidden(column, True)
        self.level_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.level_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.level_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.level_tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.level_tree.header().setSectionResizeMode(12, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.level_tree, 1)
        layout.addWidget(self._detail_panel())
        self.level_tree.currentItemChanged.connect(self._detail_selection_changed)
        if self.level_tree.topLevelItemCount():
            self.level_tree.setCurrentItem(self.level_tree.topLevelItem(0))
        controls = QHBoxLayout()
        add_level = QPushButton("+ Niveau")
        add_part = QPushButton("+ Partie")
        remove = QPushButton("Supprimer")
        up = QPushButton("Monter")
        down = QPushButton("Descendre")
        remove.setProperty("variant", "danger")
        add_level.clicked.connect(self._add_level)
        add_part.clicked.connect(self._add_part)
        remove.clicked.connect(self._remove_item)
        up.clicked.connect(lambda: self._move_item(-1))
        down.clicked.connect(lambda: self._move_item(1))
        for button in (add_level, add_part, remove, up, down):
            controls.addWidget(button)
        controls.addStretch()
        layout.addLayout(controls)
        return page

    def _append_level(self, level: CadLevelDraft) -> QTreeWidgetItem:
        item = QTreeWidgetItem(self.level_tree)
        item.setText(0, "Niveau")
        item.setText(1, level.name)
        item.setText(4, _format_decimal_values(level.start_elevations, signed=True))
        item.setText(5, _format_decimal_values(level.end_elevations, signed=True))
        item.setText(6, _format_decimal_values(level.interior_heights, signed=False))
        item.setText(12, level.confidence.value.capitalize())
        item.setData(0, Qt.ItemDataRole.UserRole, deepcopy(level.evidence))
        item.setData(0, Qt.ItemDataRole.UserRole + 1, level.confidence.value)
        item.setData(0, Qt.ItemDataRole.UserRole + 2, level.elevation_ambiguous)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        for part in level.parts:
            self._append_part(item, part)
        return item

    @staticmethod
    def _append_part(parent: QTreeWidgetItem, part: CadPartDraft) -> QTreeWidgetItem:
        item = QTreeWidgetItem(parent)
        item.setText(0, "Partie")
        item.setText(2, part.index)
        item.setText(3, "Privative" if part.nature is PartNature.PRIVATE else "Commune")
        item.setText(7, str(part.inside_title))
        item.setText(8, str(part.overhang))
        item.setText(9, part.consistency)
        item.setText(10, part.observations)
        item.setText(11, part.description_suggestion)
        item.setText(12, part.confidence.value.capitalize())
        item.setText(13, "1" if part.accept_description_suggestion else "0")
        item.setData(0, Qt.ItemDataRole.UserRole, deepcopy(part.evidence))
        item.setToolTip(11, "Suggestion faible : elle n’est pas copiée dans la description détaillée.")
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        return item

    def _detail_panel(self) -> QGroupBox:
        panel = QGroupBox("Détail de l’élément sélectionné")
        grid = QGridLayout(panel)
        self.detail_name = QLineEdit()
        self.detail_index = QLineEdit()
        self.detail_nature = QComboBox()
        self.detail_nature.addItems(("Privative", "Commune"))
        self.detail_start = QLineEdit()
        self.detail_end = QLineEdit()
        self.detail_height = QLineEdit()
        self.detail_surface = QLineEdit()
        self.detail_overhang = QLineEdit()
        self.detail_consistency = QLineEdit()
        self.detail_observations = QLineEdit()
        self.detail_suggestion = QLineEdit()
        self.accept_suggestion = QCheckBox("Utiliser la suggestion comme description détaillée")
        fields = (
            ("Nom du niveau", self.detail_name), ("Indice", self.detail_index),
            ("Nature", self.detail_nature), ("Cotes début", self.detail_start),
            ("Cotes fin", self.detail_end), ("Hauteurs", self.detail_height),
            ("Surface", self.detail_surface), ("Surplomb", self.detail_overhang),
        )
        for position, (label, widget) in enumerate(fields):
            row = (position // 4) * 2
            column = (position % 4) * 2
            grid.addWidget(QLabel(label), row, column)
            grid.addWidget(widget, row + 1, column)
        grid.addWidget(QLabel("Consistance"), 4, 0)
        grid.addWidget(self.detail_consistency, 5, 0, 1, 2)
        grid.addWidget(QLabel("Observations"), 4, 2)
        grid.addWidget(self.detail_observations, 5, 2, 1, 2)
        grid.addWidget(QLabel("Suggestion de pièces (faible confiance)"), 4, 4)
        grid.addWidget(self.detail_suggestion, 5, 4, 1, 2)
        grid.addWidget(self.accept_suggestion, 5, 6, 1, 2)
        self.detail_suggestion.setReadOnly(True)
        self.accept_suggestion.setChecked(False)
        self.detail_start.setPlaceholderText("Ex. +0,20 ; +0,60")
        self.detail_end.setPlaceholderText("Ex. +3,10 ; +5,70")
        self.detail_height.setPlaceholderText("Ex. 2,90 ; 5,50")
        for editor in (self.detail_start, self.detail_end, self.detail_height):
            editor.setToolTip("Séparez plusieurs valeurs par un point-virgule.")
        for editor in (
            self.detail_name, self.detail_index, self.detail_start, self.detail_end, self.detail_height,
            self.detail_surface, self.detail_overhang, self.detail_consistency, self.detail_observations,
        ):
            editor.editingFinished.connect(self._commit_current_detail)
        self.detail_nature.currentIndexChanged.connect(self._commit_current_detail)
        self.accept_suggestion.toggled.connect(self._commit_current_detail)
        return panel

    def _detail_selection_changed(self, current: QTreeWidgetItem | None, previous: QTreeWidgetItem | None) -> None:
        if previous is not None:
            self._write_detail(previous)
        self._load_detail(current)

    def _load_detail(self, item: QTreeWidgetItem | None) -> None:
        widgets = (
            self.detail_name, self.detail_index, self.detail_nature, self.detail_start, self.detail_end,
            self.detail_height, self.detail_surface, self.detail_overhang, self.detail_consistency,
            self.detail_observations, self.detail_suggestion, self.accept_suggestion,
        )
        if item is None:
            for widget in widgets:
                widget.setEnabled(False)
            return
        self._loading_detail = True
        is_level = item.parent() is None
        self.detail_name.setText(item.text(1))
        self.detail_index.setText(item.text(2))
        self.detail_nature.setCurrentText(item.text(3) or "Privative")
        self.detail_start.setText(item.text(4))
        self.detail_end.setText(item.text(5))
        self.detail_height.setText(item.text(6))
        self.detail_surface.setText(item.text(7))
        self.detail_overhang.setText(item.text(8))
        self.detail_consistency.setText(item.text(9))
        self.detail_observations.setText(item.text(10))
        self.detail_suggestion.setText(item.text(11))
        self.accept_suggestion.setChecked(item.text(13) == "1")
        self.detail_name.setEnabled(is_level)
        self.detail_start.setEnabled(is_level)
        self.detail_end.setEnabled(is_level)
        self.detail_height.setEnabled(is_level)
        for widget in (
            self.detail_index, self.detail_nature, self.detail_surface, self.detail_overhang,
            self.detail_consistency, self.detail_observations,
        ):
            widget.setEnabled(not is_level)
        self.detail_suggestion.setEnabled(not is_level and bool(item.text(11)))
        self.accept_suggestion.setEnabled(not is_level and bool(item.text(11)))
        self._loading_detail = False

    def _write_detail(self, item: QTreeWidgetItem) -> None:
        is_level = item.parent() is None
        if is_level:
            item.setText(1, self.detail_name.text().strip())
            item.setText(4, self.detail_start.text().strip())
            item.setText(5, self.detail_end.text().strip())
            item.setText(6, self.detail_height.text().strip())
        else:
            item.setText(2, self.detail_index.text().strip())
            item.setText(3, self.detail_nature.currentText())
            item.setText(7, self.detail_surface.text().strip())
            item.setText(8, self.detail_overhang.text().strip())
            item.setText(9, self.detail_consistency.text().strip())
            item.setText(10, self.detail_observations.text().strip())
            item.setText(13, "1" if self.accept_suggestion.isChecked() else "0")

    def _commit_current_detail(self, *_args) -> None:
        if self._loading_detail:
            return
        item = self.level_tree.currentItem()
        if item is not None:
            self._write_detail(item)

    def _missing_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        label = QLabel(
            "Ces informations factuelles ne sont pas déduites du dessin et restent à compléter dans le formulaire :\n\n"
            "• Conservation foncière\n• Commune si elle n’est pas explicitement présente\n"
            "• Topographe, date et heure du dossier\n• Informations du client\n• Limites Nord-Est, Nord-Ouest, Sud-Est et Sud-Ouest\n\n"
            "Aucun texte juridique ne doit être saisi : les modèles DOCX restent l’unique source du texte juridique."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addStretch()
        return page

    def _add_level(self) -> None:
        level = CadLevelDraft(name="Nouveau niveau", order=self.level_tree.topLevelItemCount())
        self.level_tree.setCurrentItem(self._append_level(level))

    def _selected_level(self) -> QTreeWidgetItem | None:
        item = self.level_tree.currentItem()
        if item is None:
            return None
        return item if item.parent() is None else item.parent()

    def _add_part(self) -> None:
        level = self._selected_level()
        if level is None:
            return
        part = CadPartDraft(index="", nature=PartNature.PRIVATE)
        self.level_tree.setCurrentItem(self._append_part(level, part))
        level.setExpanded(True)

    def _remove_item(self) -> None:
        item = self.level_tree.currentItem()
        if item is None:
            return
        parent = item.parent()
        if parent is None:
            self.level_tree.takeTopLevelItem(self.level_tree.indexOfTopLevelItem(item))
        else:
            parent.takeChild(parent.indexOfChild(item))

    def _move_item(self, offset: int) -> None:
        item = self.level_tree.currentItem()
        if item is None:
            return
        parent = item.parent()
        if parent is None:
            index = self.level_tree.indexOfTopLevelItem(item)
            target = index + offset
            if 0 <= target < self.level_tree.topLevelItemCount():
                moved = self.level_tree.takeTopLevelItem(index)
                self.level_tree.insertTopLevelItem(target, moved)
                self.level_tree.setCurrentItem(moved)
        else:
            index = parent.indexOfChild(item)
            target = index + offset
            if 0 <= target < parent.childCount():
                moved = parent.takeChild(index)
                parent.insertChild(target, moved)
                self.level_tree.setCurrentItem(moved)

    @staticmethod
    def _number(text: str) -> Decimal:
        value = text.strip().replace(",", ".")
        try:
            return Decimal(value or "0")
        except InvalidOperation as exc:
            raise ValueError(f"Nombre CAD invalide : {text!r}") from exc

    def _draft_from_tree(self) -> CadImportDraft:
        self._commit_current_detail()
        reviewed = deepcopy(self.draft)
        reviewed.levels = []
        for order in range(self.level_tree.topLevelItemCount()):
            item = self.level_tree.topLevelItem(order)
            level = CadLevelDraft(
                name=item.text(1).strip() or f"Niveau importé {order + 1}",
                order=order,
                start_elevations=_decimal_values(item.text(4)),
                end_elevations=_decimal_values(item.text(5)),
                interior_heights=_decimal_values(item.text(6)),
                confidence=CadConfidence(item.data(0, Qt.ItemDataRole.UserRole + 1) or CadConfidence.MEDIUM.value),
                elevation_ambiguous=bool(item.data(0, Qt.ItemDataRole.UserRole + 2)),
                evidence=deepcopy(item.data(0, Qt.ItemDataRole.UserRole) or []),
            )
            for child_index in range(item.childCount()):
                child = item.child(child_index)
                nature = PartNature.PRIVATE if child.text(3).strip().casefold().startswith("priv") else PartNature.COMMON
                level.parts.append(CadPartDraft(
                    index=child.text(2).strip(),
                    nature=nature,
                    inside_title=self._number(child.text(7)) or Decimal("0"),
                    overhang=self._number(child.text(8)) or Decimal("0"),
                    consistency=child.text(9).strip(),
                    observations=child.text(10).strip(),
                    description_suggestion=child.text(11).strip(),
                    accept_description_suggestion=child.text(13) == "1",
                    confidence=CadConfidence.MEDIUM,
                    evidence=deepcopy(child.data(0, Qt.ItemDataRole.UserRole) or []),
                ))
            reviewed.levels.append(level)
        return reviewed

    def _apply(self) -> None:
        selected = {field: editor.text().strip() for field, editor in self.value_editors.items()}
        try:
            reviewed = self._draft_from_tree()
        except ValueError as exc:
            QMessageBox.warning(self, "Valeur CAD invalide", str(exc))
            return
        self.reviewed_project = apply_reviewed_draft(
            self.original_project,
            reviewed,
            selected,
            replace_levels=self.replace_levels.isChecked(),
        )
        self.accept()
