from __future__ import annotations

import logging
from datetime import date, time
from decimal import Decimal, InvalidOperation
from copy import deepcopy
from uuid import uuid4

from PySide6.QtCore import QDate, QSignalBlocker, QTime, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from copro_auto.domain.models import (
    ClientInformation,
    Level,
    Part,
    PartNature,
    Project,
    ProjectIdentity,
    SurfaceBreakdown,
)
from copro_auto.projects.json_repository import CURRENT_SCHEMA_VERSION


LOGGER = logging.getLogger(__name__)


LEVEL_COLUMNS = ("Niveau", "Ordre", "Cotes début", "Cotes fin", "Hauteurs")
PART_COLUMNS = (
    "Indice", "Nature", "Consistance", "Description détaillée", "Surface", "Surplomb", "Hors balcon",
    "Balcon", "Cour", "Terrasse", "Garage", "Observations",
)


def _decimal(text: str) -> Decimal:
    normalized = text.strip().replace(",", ".")
    if not normalized:
        return Decimal("0")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Nombre invalide : « {text} »") from exc


def _decimal_values(text: str) -> tuple[Decimal, ...]:
    result: list[Decimal] = []
    for token in text.replace("\n", ";").split(";"):
        if not token.strip():
            continue
        value = _decimal(token)
        if value not in result:
            result.append(value)
    return tuple(result)


def _format_decimal_values(values: tuple[Decimal, ...], *, signed: bool) -> str:
    pattern = "+.2f" if signed else ".2f"
    return " ; ".join(format(value, pattern).replace(".", ",") for value in values)


def _item(value: object = "") -> QTableWidgetItem:
    return QTableWidgetItem(str(value))


class ProjectEditor(QFrame):
    project_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Card")
        self._project_id = ""
        self._created_at = ""
        self._modified_at = ""
        self._schema_version = CURRENT_SCHEMA_VERSION
        self._decisions = []
        self._generations = []
        self._loading_project = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_identity_tab(), "Projet")
        self.tabs.addTab(self._build_levels_tab(), "Niveaux et parties")
        outer.addWidget(self.tabs)
        self.levels.currentCellChanged.connect(self._level_selected)
        self.levels.itemSelectionChanged.connect(self._synchronize_selected_level)
        self.levels.itemChanged.connect(self._emit_changed)
        self.parts.itemChanged.connect(self._emit_changed)
        self._connect_identity_fields()

    def _build_identity_tab(self) -> QWidget:
        content = QWidget()
        content.setObjectName("ProjectIdentityContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 18, 18, 18)
        intro = QLabel("IDENTIFICATION CADASTRALE")
        intro.setProperty("role", "eyebrow")
        layout.addWidget(intro)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setHorizontalSpacing(20)
        form.setVerticalSpacing(12)
        self.property_name = QLineEdit()
        self.property_name.setPlaceholderText("Ex. YASMIN 71")
        self.land_title = QLineEdit()
        self.land_title.setPlaceholderText("Ex. 119753/59")
        self.prefecture = QLineEdit()
        self.land_registry_office = QLineEdit()
        self.land_registry_office.setPlaceholderText("Ex. Meknès Al Ismaïlia")
        self.commune = QLineEdit()
        self.subdivision = QLineEdit()
        self.surveyor = QLineEdit()
        self.project_date = QDateEdit(QDate.currentDate())
        self.project_date.setCalendarPopup(True)
        self.project_date.setDisplayFormat("dd/MM/yyyy")
        self.project_time = QTimeEdit(QTime(10, 0))
        self.project_time.setDisplayFormat("HH:mm")
        self.land_area = QLineEdit()
        self.land_area.setPlaceholderText("m²")
        self.total_height = QLineEdit()
        self.total_height.setPlaceholderText("m")
        self.overall_consistency = QLineEdit()
        self.overall_consistency.setPlaceholderText("RDC + étages + terrasse")
        fields = (
            ("Nom de la propriété *", self.property_name), ("Titre foncier *", self.land_title),
            ("Conservation foncière *", self.land_registry_office),
            ("Préfecture", self.prefecture), ("Commune", self.commune),
            ("Lotissement / secteur", self.subdivision), ("Topographe", self.surveyor),
            ("Date du dossier", self.project_date), ("Heure du dossier", self.project_time),
            ("Surface du terrain (m²)", self.land_area),
            ("Hauteur totale (m)", self.total_height), ("Consistance générale", self.overall_consistency),
        )
        for label, widget in fields:
            form.addRow(label, widget)

        client_heading = QLabel("INFORMATIONS DU CLIENT")
        client_heading.setProperty("role", "eyebrow")
        form.addRow(client_heading)
        self.client_name = QLineEdit()
        self.client_national_id = QLineEdit()
        self.client_address = QLineEdit()
        self.client_capacity = QLineEdit()
        self.client_expiry = QDateEdit(QDate(1900, 1, 1))
        self.client_expiry.setMinimumDate(QDate(1900, 1, 1))
        self.client_expiry.setSpecialValueText("Sélectionner une date")
        self.client_expiry.setCalendarPopup(True)
        self.client_expiry.setDisplayFormat("dd/MM/yyyy")
        for label, widget in (
            ("Nom complet *", self.client_name), ("CNIE *", self.client_national_id),
            ("Adresse / domicile *", self.client_address), ("Qualité *", self.client_capacity),
            ("Expiration de la CNIE *", self.client_expiry),
        ):
            form.addRow(label, widget)

        boundaries_heading = QLabel("LIMITES DE LA PROPRIÉTÉ")
        boundaries_heading.setProperty("role", "eyebrow")
        form.addRow(boundaries_heading)
        self.boundary_northeast = QLineEdit()
        self.boundary_northwest = QLineEdit()
        self.boundary_southeast = QLineEdit()
        self.boundary_southwest = QLineEdit()
        for label, widget in (
            ("Nord-Est *", self.boundary_northeast), ("Nord-Ouest *", self.boundary_northwest),
            ("Sud-Est *", self.boundary_southeast), ("Sud-Ouest *", self.boundary_southwest),
        ):
            form.addRow(label, widget)
        layout.addLayout(form)
        surfaces = QLabel(
            "Les surfaces cadastrales (dans titre + surplomb) et architecturales "
            "(hors balcon + balcon) sont conservées séparément."
        )
        surfaces.setWordWrap(True)
        surfaces.setProperty("role", "muted")
        layout.addWidget(surfaces)
        layout.addStretch()
        page = QScrollArea()
        page.setObjectName("ProjectIdentityScroll")
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.Shape.NoFrame)
        page.setWidget(content)
        return page

    def _build_levels_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        level_header = QHBoxLayout()
        label = QLabel("Niveaux")
        label.setProperty("role", "section")
        level_header.addWidget(label)
        level_header.addStretch()
        add_level = QPushButton("+ Ajouter un niveau")
        remove_level = QPushButton("Supprimer")
        remove_level.setProperty("variant", "danger")
        add_level.clicked.connect(lambda _checked=False: self.add_level())
        remove_level.clicked.connect(self.remove_level)
        level_header.addWidget(add_level)
        level_header.addWidget(remove_level)
        layout.addLayout(level_header)
        self.levels = QTableWidget(0, len(LEVEL_COLUMNS))
        self.levels.setHorizontalHeaderLabels(LEVEL_COLUMNS)
        examples = {
            2: "Une ou plusieurs cotes séparées par ;  Exemple : +0,20 ; +0,60",
            3: "Une ou plusieurs cotes séparées par ;  Exemple : +3,10 ; +5,70",
            4: "Une ou plusieurs hauteurs séparées par ;  Exemple : 2,90 ; 5,50",
        }
        for column, tooltip in examples.items():
            self.levels.horizontalHeaderItem(column).setToolTip(tooltip)
        self.levels.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.levels.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.levels.setAlternatingRowColors(True)
        self.levels.verticalHeader().setVisible(False)
        self.levels.verticalHeader().setDefaultSectionSize(36)
        self.levels.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, len(LEVEL_COLUMNS)):
            self.levels.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.levels.setMinimumHeight(96)
        layout.addWidget(self.levels, 2)

        part_header = QHBoxLayout()
        self.part_title = QLabel("Parties du niveau sélectionné")
        self.part_title.setProperty("role", "section")
        part_header.addWidget(self.part_title)
        part_header.addStretch()
        add_part = QPushButton("+ Ajouter une partie")
        remove_part = QPushButton("Supprimer")
        remove_part.setProperty("variant", "danger")
        add_part.clicked.connect(lambda _checked=False: self.add_part())
        remove_part.clicked.connect(self.remove_part)
        part_header.addWidget(add_part)
        part_header.addWidget(remove_part)
        layout.addLayout(part_header)
        self.parts = QTableWidget(0, len(PART_COLUMNS))
        self.parts.setHorizontalHeaderLabels(PART_COLUMNS)
        self.parts.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.parts.setAlternatingRowColors(True)
        self.parts.verticalHeader().setVisible(False)
        self.parts.verticalHeader().setDefaultSectionSize(42)
        part_widths = (70, 112, 180, 320, 94, 94, 104, 86, 82, 92, 82, 260)
        for column, width in enumerate(part_widths):
            self.parts.setColumnWidth(column, width)
        self.parts.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.parts.setMinimumHeight(128)
        layout.addWidget(self.parts, 3)
        self.levels_help = QLabel(
            "Saisie principale : séparez plusieurs cotes ou hauteurs par un point-virgule "
            "(ex. +3,10 ; +5,70). L’import DWG/DXF reste une comparaison, jamais un écrasement automatique."
        )
        self.levels_help.setWordWrap(True)
        self.levels_help.setProperty("role", "helper")
        layout.addWidget(self.levels_help)
        return page

    def _connect_identity_fields(self) -> None:
        for field in (
            self.property_name, self.land_title, self.prefecture, self.commune, self.subdivision,
            self.land_registry_office, self.surveyor, self.land_area, self.total_height,
            self.overall_consistency, self.client_name, self.client_national_id,
            self.client_address, self.client_capacity, self.boundary_northeast,
            self.boundary_northwest, self.boundary_southeast, self.boundary_southwest,
        ):
            field.textChanged.connect(self.project_changed)
        self.project_date.dateChanged.connect(self.project_changed)
        self.project_time.timeChanged.connect(self.project_changed)
        self.client_expiry.dateChanged.connect(self.project_changed)

    def _emit_changed(self, *_args: object) -> None:
        self.project_changed.emit()

    def add_level(self, level: Level | None = None) -> None:
        row = self.levels.rowCount()
        self.levels.insertRow(row)
        values = (
            level.name if level else f"Niveau {row + 1}",
            level.order if level else row,
            _format_decimal_values(level.start_elevations, signed=True) if level else "+0,00",
            "" if level is None else _format_decimal_values(level.end_elevations, signed=True),
            "" if level is None else _format_decimal_values(level.interior_heights, signed=False),
        )
        for column, value in enumerate(values):
            self.levels.setItem(row, column, _item(value))
        self.levels.item(row, 0).setData(256, str(uuid4()) if level is None else level.id)
        self.levels.item(row, 0).setData(257, [] if level is None else list(level.parts))
        self.levels.selectRow(row)
        self.project_changed.emit()

    def remove_level(self) -> None:
        row = self.levels.currentRow()
        if row >= 0:
            self.levels.removeRow(row)
            self.parts.setRowCount(0)
            self.project_changed.emit()

    def _save_current_parts(self, level_row: int) -> None:
        if level_row < 0 or level_row >= self.levels.rowCount() or self.levels.item(level_row, 0) is None:
            return
        blocker = QSignalBlocker(self.levels)
        self.levels.item(level_row, 0).setData(257, self._parts_from_table())
        del blocker

    def _synchronize_selected_level(self) -> None:
        selected_rows = self.levels.selectionModel().selectedRows()
        if selected_rows and self.levels.currentRow() != selected_rows[0].row():
            self.levels.setCurrentCell(selected_rows[0].row(), 0)

    def _level_selected(self, current_row: int, _current_column: int, previous_row: int, _previous_column: int) -> None:
        if not self._loading_project:
            self._save_current_parts(previous_row)
        self.parts.blockSignals(True)
        self.parts.setRowCount(0)
        if 0 <= current_row < self.levels.rowCount():
            name = self.levels.item(current_row, 0).text()
            self.part_title.setText(f"Parties · {name}")
            LOGGER.debug("level_selected row=%d name=%s", current_row, name)
            for part in self.levels.item(current_row, 0).data(257) or []:
                self.add_part(part, emit=False)
        self.parts.blockSignals(False)

    def add_part(self, part: Part | None = None, *, emit: bool = True) -> None:
        if self.levels.currentRow() < 0:
            return
        row = self.parts.rowCount()
        self.parts.insertRow(row)
        combo = QComboBox()
        combo.addItem("Privative", PartNature.PRIVATE.value)
        combo.addItem("Commune", PartNature.COMMON.value)
        if part is not None:
            combo.setCurrentIndex(0 if part.nature is PartNature.PRIVATE else 1)
        combo.currentIndexChanged.connect(self.project_changed)
        self.parts.setCellWidget(row, 1, combo)
        values = {
            0: part.index if part else "",
            2: part.consistency if part else "",
            3: part.description if part else "",
            4: part.surfaces.inside_title if part else "0",
            5: part.surfaces.overhang if part else "0",
            6: part.surfaces.excluding_balcony if part else "0",
            7: part.surfaces.balcony if part else "0",
            8: part.surfaces.courtyard if part else "0",
            9: part.surfaces.terrace if part else "0",
            10: part.surfaces.garage if part else "0",
            11: part.observations if part else "",
        }
        for column, value in values.items():
            self.parts.setItem(row, column, _item(value))
        self.parts.item(row, 0).setData(256, str(uuid4()) if part is None else part.id)
        if emit:
            self.project_changed.emit()

    def remove_part(self) -> None:
        row = self.parts.currentRow()
        if row >= 0:
            self.parts.removeRow(row)
            self.project_changed.emit()

    def _parts_from_table(self) -> list[Part]:
        result: list[Part] = []
        for row in range(self.parts.rowCount()):
            text = lambda column: self.parts.item(row, column).text() if self.parts.item(row, column) else ""
            nature_widget = self.parts.cellWidget(row, 1)
            if isinstance(nature_widget, QComboBox) and nature_widget.currentData():
                nature = PartNature(nature_widget.currentData())
            else:
                nature = PartNature.PRIVATE
                LOGGER.warning("part_nature_recovered row=%d default=%s", row, nature.value)
            kwargs = {
                "index": text(0), "nature": nature, "consistency": text(2), "description": text(3),
                "surfaces": SurfaceBreakdown(
                    inside_title=_decimal(text(4)), overhang=_decimal(text(5)),
                    excluding_balcony=_decimal(text(6)), balcony=_decimal(text(7)),
                    courtyard=_decimal(text(8)), terrace=_decimal(text(9)), garage=_decimal(text(10)),
                ),
                "observations": text(11),
            }
            part_id = self.parts.item(row, 0).data(256)
            if part_id:
                kwargs["id"] = part_id
            part = Part(**kwargs)
            if not part_id:
                blocker = QSignalBlocker(self.parts)
                self.parts.item(row, 0).setData(256, part.id)
                del blocker
                LOGGER.debug("part_id_assigned row=%d", row)
            result.append(part)
        return result

    def set_project(self, project: Project) -> None:
        self._loading_project = True
        self._project_id = project.id
        self._created_at = project.created_at
        self._modified_at = project.modified_at
        self._schema_version = CURRENT_SCHEMA_VERSION
        self._decisions = deepcopy(project.decisions)
        self._generations = deepcopy(project.generations)
        i = project.identity
        self.property_name.setText(i.property_name)
        self.land_title.setText(i.land_title)
        self.prefecture.setText(i.prefecture)
        self.land_registry_office.setText(i.land_registry_office)
        self.commune.setText(i.commune)
        self.subdivision.setText(i.subdivision)
        self.surveyor.setText(i.surveyor)
        self.project_date.setDate(QDate(i.project_date.year, i.project_date.month, i.project_date.day))
        self.project_time.setTime(QTime(i.project_time.hour, i.project_time.minute))
        self.land_area.setText(str(i.land_area))
        self.total_height.setText(str(i.total_height))
        self.overall_consistency.setText(i.overall_consistency)
        self.client_name.setText(i.client.full_name)
        self.client_national_id.setText(i.client.national_id)
        self.client_address.setText(i.client.address)
        self.client_capacity.setText(i.client.capacity)
        expiry = i.client.national_id_expiry
        self.client_expiry.setDate(
            QDate(1900, 1, 1) if expiry is None else QDate(expiry.year, expiry.month, expiry.day)
        )
        self.boundary_northeast.setText(i.boundaries.get("northeast", ""))
        self.boundary_northwest.setText(i.boundaries.get("northwest", ""))
        self.boundary_southeast.setText(i.boundaries.get("southeast", ""))
        self.boundary_southwest.setText(i.boundaries.get("southwest", ""))
        self.levels.blockSignals(True)
        self.levels.setRowCount(0)
        for level in sorted(project.levels, key=lambda value: value.order):
            self.add_level(level)
        self.levels.blockSignals(False)
        if self.levels.rowCount():
            self.levels.selectRow(0)
        else:
            self.parts.setRowCount(0)
        self._loading_project = False

    def project(self) -> Project:
        current = self.levels.currentRow()
        self._save_current_parts(current)
        expiry_date = self.client_expiry.date()
        expiry = None if expiry_date == QDate(1900, 1, 1) else date(
            expiry_date.year(), expiry_date.month(), expiry_date.day()
        )
        identity = ProjectIdentity(
            property_name=self.property_name.text().strip(), land_title=self.land_title.text().strip(),
            prefecture=self.prefecture.text().strip(), commune=self.commune.text().strip(),
            land_registry_office=self.land_registry_office.text().strip(),
            subdivision=self.subdivision.text().strip(), surveyor=self.surveyor.text().strip(),
            project_date=date(self.project_date.date().year(), self.project_date.date().month(), self.project_date.date().day()),
            project_time=time(self.project_time.time().hour(), self.project_time.time().minute()),
            land_area=_decimal(self.land_area.text()), total_height=_decimal(self.total_height.text()),
            overall_consistency=self.overall_consistency.text().strip(),
            client=ClientInformation(
                full_name=self.client_name.text().strip(),
                national_id=self.client_national_id.text().strip(),
                address=self.client_address.text().strip(),
                capacity=self.client_capacity.text().strip(),
                national_id_expiry=expiry,
            ),
            boundaries={
                "northeast": self.boundary_northeast.text().strip(),
                "northwest": self.boundary_northwest.text().strip(),
                "southeast": self.boundary_southeast.text().strip(),
                "southwest": self.boundary_southwest.text().strip(),
            },
        )
        levels: list[Level] = []
        for row in range(self.levels.rowCount()):
            text = lambda column: self.levels.item(row, column).text() if self.levels.item(row, column) else ""
            kwargs = {
                "name": text(0), "order": int(text(1) or row),
                "start_elevations": _decimal_values(text(2)),
                "end_elevations": _decimal_values(text(3)),
                "interior_heights": _decimal_values(text(4)),
                "parts": self.levels.item(row, 0).data(257) or [],
            }
            level_id = self.levels.item(row, 0).data(256)
            if level_id:
                kwargs["id"] = level_id
            level = Level(**kwargs)
            if not level_id:
                blocker = QSignalBlocker(self.levels)
                self.levels.item(row, 0).setData(256, level.id)
                del blocker
                LOGGER.debug("level_id_assigned row=%d", row)
            levels.append(level)
        kwargs = {
            "identity": identity,
            "levels": levels,
            "schema_version": self._schema_version,
            "decisions": deepcopy(self._decisions),
            "generations": deepcopy(self._generations),
        }
        if self._project_id:
            kwargs["id"] = self._project_id
        if self._created_at:
            kwargs["created_at"] = self._created_at
        if self._modified_at:
            kwargs["modified_at"] = self._modified_at
        return Project(**kwargs)
