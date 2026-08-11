from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from copro_auto.cad_import.service import import_cad
from copro_auto.documents.service import DocumentGenerationService, GenerationError
from copro_auto.domain.calculations import calculate_shares, private_parts
from copro_auto.domain.models import Project, ProjectIdentity
from copro_auto.domain.validation import has_errors, validate_project
from copro_auto.licensing.service import LicenseDecision, LicenseService
from copro_auto.projects.service import ProjectService

from .import_review import ImportReviewDialog
from .license_dialog import LicenseDialog
from .project_editor import ProjectEditor
from .validation_panel import ValidationPanel
from .dialogs import critical, information, question, success, warning


LOGGER = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Copro Auto — Dossiers de copropriété")
        self.resize(1440, 900)
        self.setMinimumSize(1080, 700)
        self.project_service = ProjectService()
        self.document_service = DocumentGenerationService()
        self.license_service = LicenseService.from_environment()
        self.license_decision = self.license_service.evaluate()
        self.project_path: Path | None = None
        self.dirty = False
        self._building = True
        self._build_ui()
        self._build_actions()
        self.validation_timer = QTimer(self)
        self.validation_timer.setSingleShot(True)
        self.validation_timer.setInterval(220)
        self.validation_timer.timeout.connect(self.refresh_validation)
        self.editor.project_changed.connect(self._project_changed)
        self.new_project(confirm=False)
        self._apply_license(self.license_decision)
        self._building = False

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("AppRoot")
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(self._build_sidebar())
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(22, 18, 22, 16)
        content_layout.setSpacing(14)
        content_layout.addWidget(self._build_header())
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.editor = ProjectEditor()
        self.validation_panel = ValidationPanel()
        self.validation_panel.setMinimumWidth(280)
        self.validation_panel.setMaximumWidth(360)
        splitter.addWidget(self.editor)
        splitter.addWidget(self.validation_panel)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([1020, 320])
        content_layout.addWidget(splitter, 1)
        shell.addWidget(content, 1)
        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Prêt")

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(236)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 24, 20, 20)
        layout.setSpacing(8)
        brand = QLabel("COPRO AUTO")
        brand.setProperty("role", "brand")
        layout.addWidget(brand)
        sub = QLabel("Dossiers topographiques\nfiables et reproductibles")
        sub.setProperty("role", "brandSub")
        layout.addWidget(sub)
        layout.addSpacing(24)
        section = QLabel("DOSSIER")
        section.setProperty("role", "sidebarSection")
        layout.addWidget(section)
        self.new_button = self._sidebar_button("＋  Nouveau dossier")
        self.open_button = self._sidebar_button("↗  Ouvrir un projet")
        self.save_button = self._sidebar_button("↓  Enregistrer")
        self.import_button = self._sidebar_button("◇  Vérifier par DWG/DXF")
        for button in (self.new_button, self.open_button, self.save_button, self.import_button):
            layout.addWidget(button)
        layout.addSpacing(20)
        workflow = QLabel("MÉTHODE")
        workflow.setProperty("role", "sidebarSection")
        layout.addWidget(workflow)
        for number, text in (("01", "Saisie manuelle"), ("02", "Contrôles"), ("03", "Aperçu"), ("04", "Six documents")):
            item = QLabel(f"{number}   {text}")
            item.setProperty("role", "brandSub")
            layout.addWidget(item)
        layout.addStretch()
        self.license_button = QPushButton("●  Vérifier la licence")
        self.license_button.setProperty("role", "license")
        layout.addWidget(self.license_button)
        version = QLabel("Données métier conservées localement")
        version.setWordWrap(True)
        version.setProperty("role", "brandSub")
        layout.addWidget(version)
        return sidebar

    @staticmethod
    def _sidebar_button(text: str) -> QPushButton:
        button = QPushButton(text)
        button.setProperty("variant", "ghost")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("Header")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 16, 18, 16)
        title_box = QVBoxLayout()
        eyebrow = QLabel("DOSSIER ACTIF")
        eyebrow.setProperty("role", "eyebrow")
        self.project_title = QLabel("Nouveau dossier")
        self.project_title.setProperty("role", "title")
        self.project_subtitle = QLabel("Renseignez le nom de la propriété et le titre foncier")
        self.project_subtitle.setProperty("role", "muted")
        title_box.addWidget(eyebrow)
        title_box.addWidget(self.project_title)
        title_box.addWidget(self.project_subtitle)
        layout.addLayout(title_box, 1)
        metrics = QHBoxLayout()
        metrics.setSpacing(24)
        self.surface_metric = self._metric(metrics, "0 m²", "Surface privative")
        self.share_metric = self._metric(metrics, "—", "Tantièmes")
        self.document_metric = self._metric(metrics, "6", "Documents")
        layout.addLayout(metrics)
        layout.addSpacing(12)
        self.validate_button = QPushButton("Contrôler")
        self.generate_button = QPushButton("Générer les 6 DOCX")
        self.generate_button.setProperty("variant", "primary")
        layout.addWidget(self.validate_button)
        layout.addWidget(self.generate_button)
        return header

    @staticmethod
    def _metric(layout: QHBoxLayout, value: str, caption: str) -> QLabel:
        box = QVBoxLayout()
        label = QLabel(value)
        label.setProperty("role", "metric")
        text = QLabel(caption)
        text.setProperty("role", "muted")
        box.addWidget(label)
        box.addWidget(text)
        layout.addLayout(box)
        return label

    def _build_actions(self) -> None:
        self.action_new = QAction("Nouveau", self, shortcut="Ctrl+N", triggered=self.new_project)
        self.action_open = QAction("Ouvrir", self, shortcut="Ctrl+O", triggered=self.open_project)
        self.action_save = QAction("Enregistrer", self, shortcut="Ctrl+S", triggered=self.save_project)
        self.action_save_as = QAction("Enregistrer sous", self, shortcut="Ctrl+Shift+S", triggered=self.save_project_as)
        self.addActions((self.action_new, self.action_open, self.action_save, self.action_save_as))
        self.new_button.clicked.connect(self.new_project)
        self.open_button.clicked.connect(self.open_project)
        self.save_button.clicked.connect(self.save_project)
        self.import_button.clicked.connect(self.import_drawing)
        self.license_button.clicked.connect(self.manage_license)
        self.validate_button.clicked.connect(self.refresh_validation)
        self.generate_button.clicked.connect(self.generate_documents)

    def _project_changed(self) -> None:
        if self._building:
            return
        self.dirty = True
        self.validation_timer.start()

    def current_project(self) -> Project:
        return self.editor.project()

    def new_project(self, _checked: bool = False, *, confirm: bool = True) -> None:
        if confirm and not self.license_decision.permits("create"):
            self._license_required("créer un nouveau dossier")
            return
        if confirm and not self._can_discard():
            return
        self._building = True
        self.project_path = None
        self.editor.set_project(Project(identity=ProjectIdentity(land_title="", property_name="")))
        self.dirty = False
        self._building = False
        self.refresh_validation()
        self.statusBar().showMessage("Nouveau dossier créé", 3000)

    def open_project(self) -> None:
        if not self._can_discard():
            return
        filename, _ = QFileDialog.getOpenFileName(self, "Ouvrir un projet", "", "Projet Copro Auto (*.json)")
        if not filename:
            return
        try:
            project = self.project_service.open(filename)
            self._building = True
            self.editor.set_project(project)
            self.project_path = Path(filename)
            self.dirty = False
            self._building = False
            self.refresh_validation()
            self.statusBar().showMessage(f"Projet ouvert : {Path(filename).name}", 4000)
            LOGGER.info("project_opened file=%s", Path(filename).name)
        except Exception as exc:
            self._building = False
            critical(self, "Ouverture impossible", str(exc))

    def save_project(self) -> bool:
        if self.project_path is None:
            return self.save_project_as()
        return self._save_to(self.project_path)

    def save_project_as(self) -> bool:
        filename, _ = QFileDialog.getSaveFileName(self, "Enregistrer le projet", "dossier-copropriete.json", "Projet Copro Auto (*.json)")
        if not filename:
            return False
        path = Path(filename)
        if path.suffix.casefold() != ".json":
            path = path.with_suffix(".json")
        return self._save_to(path)

    def _save_to(self, path: Path) -> bool:
        try:
            self.project_service.save(self.current_project(), path)
            self.project_path = path
            self.dirty = False
            self.statusBar().showMessage(f"Projet enregistré : {path.name}", 4000)
            LOGGER.info("project_saved file=%s", path.name)
            return True
        except Exception as exc:
            critical(self, "Enregistrement impossible", str(exc))
            return False

    def refresh_validation(self) -> list:
        try:
            project = self.current_project()
            issues = validate_project(project)
            self.validation_panel.set_issues(issues, project)
            self.project_title.setText(project.identity.property_name or "Nouveau dossier")
            subtitle = project.identity.land_title or "Titre foncier non renseigné"
            self.project_subtitle.setText(f"Titre foncier · {subtitle}")
            total_surface = sum((part.surfaces.cadastral_total for part in private_parts(project)), Decimal("0"))
            self.surface_metric.setText(f"{total_surface} m²")
            if not has_errors(issues):
                shares = calculate_shares(project)
                self.share_metric.setText(f"{sum(s.ten_thousandths for s in shares):,}".replace(",", " "))
            else:
                self.share_metric.setText("À contrôler")
            self.generate_button.setEnabled(not has_errors(issues) and self.license_decision.permits("generate_docx"))
            return issues
        except (ValueError, TypeError) as exc:
            self.generate_button.setEnabled(False)
            self.share_metric.setText("Valeur invalide")
            self.statusBar().showMessage(str(exc), 5000)
            return []

    def import_drawing(self) -> None:
        if not self.license_decision.permits("import_cad"):
            self._license_required("importer un dessin")
            return
        filename, _ = QFileDialog.getOpenFileName(self, "Sélectionner un dessin", "", "Dessin AutoCAD (*.dwg *.dxf)")
        if not filename:
            return
        try:
            project = self.current_project()
            result = import_cad(filename)
            dialog = ImportReviewDialog(project, result, self)
            if dialog.exec():
                self._building = True
                self.editor.set_project(project)
                self._building = False
                self.dirty = True
                self.refresh_validation()
                self.statusBar().showMessage("Choix du dessin appliqués et tracés", 4000)
        except Exception as exc:
            critical(self, "Import impossible", str(exc))

    def generate_documents(self) -> None:
        if not self.license_decision.permits("generate_docx"):
            self._license_required("générer les documents")
            return
        try:
            project = self.current_project()
        except ValueError as exc:
            warning(self, "Valeur invalide", str(exc))
            return
        issues = validate_project(project)
        self.validation_panel.set_issues(issues, project)
        if has_errors(issues):
            warning(self, "Dossier incomplet", "Corrigez les erreurs affichées avant la génération.")
            return
        directory = QFileDialog.getExistingDirectory(self, "Dossier de sortie des six documents")
        if not directory:
            return
        try:
            outputs = self.document_service.generate(project, directory)
            self.statusBar().showMessage("Six documents générés avec succès", 6000)
            success(
                self, "Dossier généré",
                "Les six documents ont été créés :\n\n" + "\n".join(path.name for path in outputs),
            )
            LOGGER.info("documents_generated count=%d", len(outputs))
        except GenerationError as exc:
            critical(self, "Génération impossible", str(exc))

    def _can_discard(self) -> bool:
        if not self.dirty:
            return True
        answer = question(
            self,
            "Modifications non enregistrées",
            "Enregistrer les modifications avant de continuer ?",
            buttons=(
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel
            ),
            default=QMessageBox.StandardButton.Save,
            tone="warning",
            danger=QMessageBox.StandardButton.Discard,
        )
        LOGGER.debug("unsaved_changes_choice=%s", answer)
        if answer == QMessageBox.StandardButton.Save:
            return self.save_project()
        return answer == QMessageBox.StandardButton.Discard

    def manage_license(self) -> None:
        dialog = LicenseDialog(self.license_service, self)
        dialog.exec()
        self._apply_license(self.license_service.evaluate())

    def _apply_license(self, decision: LicenseDecision) -> None:
        self.license_decision = decision
        self.license_button.setText(f"●  {decision.message}")
        productive = decision.permits("create")
        self.new_button.setEnabled(productive)
        self.import_button.setEnabled(decision.permits("import_cad"))
        self.editor.setEnabled(productive)
        self.refresh_validation()

    def _license_required(self, action: str) -> None:
        information(
            self, "Licence requise",
            f"Une licence active est nécessaire pour {action}. Les projets existants restent consultables et exportables.",
        )
        self.manage_license()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._can_discard():
            event.accept()
        else:
            event.ignore()
