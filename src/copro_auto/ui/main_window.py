from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, Signal, Slot
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

from copro_auto.cad_import.service import import_cad, project_is_empty
from copro_auto.documents.service import DocumentGenerationService, GenerationError
from copro_auto.domain.calculations import calculate_shares, private_parts
from copro_auto.domain.models import Project, ProjectIdentity
from copro_auto.domain.validation import has_errors, validate_project
from copro_auto.licensing.service import LicenseDecision, LicenseService, LicenseState
from copro_auto.projects.service import ProjectService

from .license_dialog import LicenseDialog
from .cad_import_wizard import CadImportWizard
from .project_editor import ProjectEditor
from .validation_panel import ValidationPanel
from .dialogs import critical, information, question, success, warning


LOGGER = logging.getLogger(__name__)
LICENSE_SYNC_INTERVAL_MS = 15 * 60 * 1000


class _LicenseSyncSignals(QObject):
    finished = Signal(object)


class _LicenseSyncTask(QRunnable):
    def __init__(self, service: LicenseService) -> None:
        super().__init__()
        self.service = service
        self.signals = _LicenseSyncSignals()

    @Slot()
    def run(self) -> None:
        try:
            decision = self.service.sync_status()
        except Exception:
            LOGGER.exception("license_sync_failed")
            decision = self.service.evaluate()
        self.signals.finished.emit(decision)


class _CadImportSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)


class _CadImportTask(QRunnable):
    def __init__(self, source: Path) -> None:
        super().__init__()
        self.source = source
        self.signals = _CadImportSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = import_cad(self.source)
        except Exception as exc:
            LOGGER.exception("cad_import_failed extension=%s", self.source.suffix.casefold())
            self.signals.failed.emit(str(exc))
            return
        self.signals.finished.emit(result)


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
        self._license_syncing = False
        self._license_sync_task: _LicenseSyncTask | None = None
        self._license_sync_callbacks: list[Callable[[LicenseDecision], None]] = []
        self._cad_import_task: _CadImportTask | None = None
        self.project_path: Path | None = None
        self.dirty = False
        self._building = True
        self._build_ui()
        self._build_actions()
        self.validation_timer = QTimer(self)
        self.validation_timer.setSingleShot(True)
        self.validation_timer.setInterval(220)
        self.validation_timer.timeout.connect(self.refresh_validation)
        self.license_sync_timer = QTimer(self)
        self.license_sync_timer.setInterval(LICENSE_SYNC_INTERVAL_MS)
        self.license_sync_timer.timeout.connect(self._sync_license_async)
        self.license_sync_timer.start()
        self.editor.project_changed.connect(self._project_changed)
        self.new_project(confirm=False)
        self._apply_license(self.license_decision)
        self._building = False
        QTimer.singleShot(0, self._sync_license_async)

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
        self.cad_button = self._sidebar_button("◇  Importer DWG/DXF")
        for button in (self.new_button, self.open_button, self.save_button, self.cad_button):
            layout.addWidget(button)
        layout.addSpacing(20)
        workflow = QLabel("MÉTHODE")
        workflow.setProperty("role", "sidebarSection")
        layout.addWidget(workflow)
        for number, text in (("01", "Saisie manuelle"), ("02", "Contrôles"), ("03", "Aperçu"), ("04", "Cinq documents")):
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
        self.document_metric = self._metric(metrics, "5", "Documents")
        layout.addLayout(metrics)
        layout.addSpacing(12)
        self.validate_button = QPushButton("Contrôler")
        self.generate_button = QPushButton("Générer les 5 DOCX")
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
        self.action_cad = QAction("Importer ou vérifier DWG/DXF", self, shortcut="Ctrl+D", triggered=self.import_cad_drawing)
        self.addActions((self.action_new, self.action_open, self.action_save, self.action_save_as, self.action_cad))
        self.new_button.clicked.connect(self.new_project)
        self.open_button.clicked.connect(self.open_project)
        self.save_button.clicked.connect(self.save_project)
        self.cad_button.clicked.connect(self.import_cad_drawing)
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

    def import_cad_drawing(self, _checked: bool = False, *, _license_checked: bool = False) -> None:
        if not _license_checked:
            self._with_synced_license(
                "create",
                "importer ou vérifier un dessin DWG/DXF",
                lambda: self.import_cad_drawing(_license_checked=True),
            )
            return
        if self._cad_import_task is not None:
            return
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Importer ou vérifier un dessin",
            "",
            "Dessins AutoCAD (*.dwg *.dxf)",
        )
        if not filename:
            return
        self.cad_button.setEnabled(False)
        self.statusBar().showMessage("Analyse locale du dessin…")
        task = _CadImportTask(Path(filename))
        task.signals.finished.connect(self._cad_import_finished)
        task.signals.failed.connect(self._cad_import_failed)
        self._cad_import_task = task
        QThreadPool.globalInstance().start(task)

    @Slot(object)
    def _cad_import_finished(self, draft) -> None:
        self._cad_import_task = None
        self.cad_button.setEnabled(self.license_decision.permits("create"))
        LOGGER.info(
            "cad_import_ready extension=%s levels=%d parts=%d warnings=%d",
            draft.source.suffix.casefold(), len(draft.levels), draft.part_count, len(draft.warnings),
        )
        dialog = CadImportWizard(self.current_project(), draft, self)
        if dialog.exec() and dialog.reviewed_project is not None:
            self._building = True
            self.editor.set_project(dialog.reviewed_project)
            self._building = False
            self.dirty = True
            self.refresh_validation()
            self.statusBar().showMessage("Brouillon CAD appliqué — complétez et contrôlez le dossier", 6000)
            LOGGER.info("cad_review_applied levels=%d parts=%d", len(draft.levels), draft.part_count)
        else:
            self.statusBar().showMessage("Import CAD annulé — dossier inchangé", 4000)
            LOGGER.info("cad_review_cancelled")

    @Slot(str)
    def _cad_import_failed(self, message: str) -> None:
        self._cad_import_task = None
        self.cad_button.setEnabled(self.license_decision.permits("create"))
        self.statusBar().showMessage("Import CAD impossible", 4000)
        critical(self, "Import CAD impossible", message)

    def _sync_license_async(self, callback: Callable[[LicenseDecision], None] | None = None) -> None:
        if self.license_decision.state is LicenseState.DEVELOPMENT:
            if callback is not None:
                callback(self.license_decision)
            return
        if callback is not None:
            self._license_sync_callbacks.append(callback)
        if self._license_syncing:
            return
        self._license_syncing = True
        task = _LicenseSyncTask(self.license_service)
        task.signals.finished.connect(self._license_sync_finished)
        self._license_sync_task = task
        QThreadPool.globalInstance().start(task)

    @Slot(object)
    def _license_sync_finished(self, decision: LicenseDecision) -> None:
        self._license_syncing = False
        self._license_sync_task = None
        self._apply_license(decision)
        callbacks = tuple(self._license_sync_callbacks)
        self._license_sync_callbacks.clear()
        for callback in callbacks:
            callback(decision)

    def _with_synced_license(
        self,
        permission: str,
        action: str,
        continuation: Callable[[], None],
    ) -> None:
        if self.license_decision.state is LicenseState.DEVELOPMENT:
            continuation()
            return
        if self.license_decision.claims is None:
            self._license_required(action)
            return
        self.statusBar().showMessage("Vérification de la licence en ligne…")
        self._sync_license_async(
            lambda decision: self._continue_after_license_sync(decision, permission, action, continuation),
        )

    def _continue_after_license_sync(
        self,
        decision: LicenseDecision,
        permission: str,
        action: str,
        continuation: Callable[[], None],
    ) -> None:
        if decision.permits(permission):
            self.statusBar().showMessage("Licence vérifiée", 2500)
            continuation()
            return
        information(
            self,
            "Licence non valide",
            f"{decision.message}\n\nReconnectez-vous pour {action}.",
        )
        self.manage_license()

    def new_project(
        self, _checked: bool = False, *, confirm: bool = True, _license_checked: bool = False,
    ) -> None:
        if confirm and not _license_checked:
            self._with_synced_license(
                "create",
                "créer un nouveau dossier",
                lambda: self.new_project(confirm=True, _license_checked=True),
            )
            return
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
            empty = project_is_empty(project)
            self.cad_button.setText("◇  Importer DWG/DXF" if empty else "◇  Vérifier DWG/DXF")
            self.cad_button.setToolTip(
                "Créer un brouillon depuis un dessin" if empty else "Comparer ce dossier avec un dessin"
            )
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

    def generate_documents(self, _checked: bool = False, *, _license_checked: bool = False) -> None:
        if not _license_checked:
            self._with_synced_license(
                "generate_docx",
                "générer les documents",
                lambda: self.generate_documents(_license_checked=True),
            )
            return
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
        directory = QFileDialog.getExistingDirectory(self, "Dossier de sortie des cinq documents")
        if not directory:
            return
        try:
            outputs = self.document_service.generate(project, directory)
            self.statusBar().showMessage("Cinq documents générés avec succès", 6000)
            success(
                self, "Dossier généré",
                "Les cinq documents ont été créés :\n\n" + "\n".join(path.name for path in outputs),
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
        self._apply_license(dialog.decision)

    def _apply_license(self, decision: LicenseDecision) -> None:
        self.license_decision = decision
        self.license_button.setText(f"●  {decision.message}")
        productive = decision.permits("create")
        self.new_button.setEnabled(productive)
        self.cad_button.setEnabled(productive and self._cad_import_task is None)
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
