from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from copro_auto.licensing.client import LicenseApiError
from copro_auto.licensing.service import LicenseDecision, LicenseService


class LicenseDialog(QDialog):
    def __init__(self, service: LicenseService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.decision = service.evaluate()
        self.setWindowTitle("Licence Copro Auto")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        title = QLabel("Activer Copro Auto")
        title.setProperty("role", "title")
        layout.addWidget(title)
        description = QLabel(
            "Une licence commerciale s’active en ligne. Une clé d’essai hors ligne signée reste utilisable pendant 30 jours."
        )
        description.setWordWrap(True)
        description.setProperty("role", "muted")
        layout.addWidget(description)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.key = QLineEdit()
        self.key.setPlaceholderText("COPRO-XXXX-… ou COPRO-TRIAL-…")
        layout.addWidget(self.key)
        actions = QHBoxLayout()
        self.activate_button = QPushButton("Activer cette licence")
        self.activate_button.setProperty("variant", "primary")
        self.refresh_button = QPushButton("Actualiser en ligne")
        self.deactivate_button = QPushButton("Désactiver cet appareil")
        self.deactivate_button.setProperty("variant", "danger")
        close = QPushButton("Fermer")
        actions.addWidget(self.activate_button)
        actions.addWidget(self.refresh_button)
        actions.addStretch()
        actions.addWidget(close)
        layout.addLayout(actions)
        layout.addWidget(self.deactivate_button)
        close.clicked.connect(self.accept)
        self.activate_button.clicked.connect(self._activate)
        self.refresh_button.clicked.connect(self._refresh)
        self.deactivate_button.clicked.connect(self._deactivate)
        self._show_decision(self.decision)

    def _show_decision(self, decision: LicenseDecision) -> None:
        self.decision = decision
        self.status.setText(f"État : {decision.message}")
        activated = decision.claims is not None
        self.refresh_button.setEnabled(activated)
        self.deactivate_button.setEnabled(activated)

    def _activate(self) -> None:
        if not self.key.text().strip():
            QMessageBox.warning(self, "Clé manquante", "Saisissez la clé reçue avec votre essai ou votre achat.")
            return
        try:
            self._show_decision(self.service.activate(self.key.text()))
            self.key.clear()
        except (LicenseApiError, ValueError) as exc:
            QMessageBox.critical(self, "Activation refusée", str(exc))

    def _refresh(self) -> None:
        try:
            self._show_decision(self.service.refresh())
        except (LicenseApiError, ValueError) as exc:
            QMessageBox.critical(self, "Actualisation impossible", str(exc))

    def _deactivate(self) -> None:
        answer = QMessageBox.question(
            self, "Libérer cet appareil",
            "Cette opération libère une place de licence. Continuer ?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.deactivate()
            self._show_decision(self.service.evaluate())
        except (LicenseApiError, ValueError) as exc:
            QMessageBox.critical(self, "Désactivation impossible", str(exc))
