from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from copro_auto.licensing.client import LicenseApiError
from copro_auto.licensing.service import LicenseDecision, LicenseService, LicenseState

from .dialogs import critical, question, warning


SUCCESS_STATES = {
    LicenseState.DEVELOPMENT,
    LicenseState.TRIAL_ACTIVE,
    LicenseState.PAID_ACTIVE,
}
WARNING_STATES = {
    LicenseState.EXPIRING_SOON,
    LicenseState.OFFLINE_GRACE,
    LicenseState.ONLINE_CHECK_REQUIRED,
}
DANGER_STATES = {
    LicenseState.INVALID,
    LicenseState.EXPIRED,
    LicenseState.REVOKED,
    LicenseState.DEVICE_LIMIT_REACHED,
}


class LicenseDialog(QDialog):
    def __init__(self, service: LicenseService, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.decision = service.evaluate()
        self.setObjectName("AppDialog")
        self.setWindowTitle("Licence Copro Auto")
        self.setMinimumWidth(600)
        self.resize(680, 450)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(14)

        title = QLabel("Activer Copro Auto")
        title.setProperty("role", "dialogTitle")
        layout.addWidget(title)

        description = QLabel(
            "Une licence commerciale s’active en ligne. Une clé d’essai hors ligne signée "
            "reste utilisable pendant 30 jours."
        )
        description.setWordWrap(True)
        description.setProperty("role", "muted")
        layout.addWidget(description)

        self.status_container = QFrame()
        self.status_container.setProperty("role", "status")
        status_layout = QHBoxLayout(self.status_container)
        status_layout.setContentsMargins(12, 10, 12, 10)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setProperty("role", "statusText")
        status_layout.addWidget(self.status)
        layout.addWidget(self.status_container)

        key_label = QLabel("Clé de licence")
        key_label.setProperty("role", "fieldLabel")
        layout.addWidget(key_label)
        self.key = QLineEdit()
        self.key.setAccessibleName("Clé de licence")
        self.key.setPlaceholderText("COPRO-XXXX-… ou COPRO-TRIAL-…")
        self.key.setClearButtonEnabled(True)
        key_label.setBuddy(self.key)
        layout.addWidget(self.key)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.activate_button = QPushButton("Activer cette licence")
        self.activate_button.setProperty("variant", "primary")
        self.activate_button.setDefault(True)
        self.refresh_button = QPushButton("Actualiser en ligne")
        self.refresh_button.setProperty("variant", "secondary")
        self.close_button = QPushButton("Fermer")
        self.close_button.setProperty("variant", "secondary")
        actions.addWidget(self.activate_button)
        actions.addWidget(self.refresh_button)
        actions.addStretch()
        actions.addWidget(self.close_button)
        layout.addLayout(actions)

        destructive = QFrame()
        destructive.setProperty("role", "destructive")
        destructive_layout = QHBoxLayout(destructive)
        destructive_layout.setContentsMargins(12, 10, 12, 10)
        destructive_copy = QLabel(
            "Libérer cet appareil permet d’utiliser la licence sur un autre ordinateur."
        )
        destructive_copy.setWordWrap(True)
        destructive_copy.setProperty("role", "muted")
        self.deactivate_button = QPushButton("Désactiver cet appareil")
        self.deactivate_button.setProperty("variant", "danger")
        destructive_layout.addWidget(destructive_copy, 1)
        destructive_layout.addWidget(self.deactivate_button)
        layout.addWidget(destructive)

        self.close_button.clicked.connect(self.accept)
        self.activate_button.clicked.connect(self._activate)
        self.refresh_button.clicked.connect(self._refresh)
        self.deactivate_button.clicked.connect(self._deactivate)
        self._show_decision(self.decision)

    @staticmethod
    def _tone(decision: LicenseDecision) -> str:
        if decision.state in SUCCESS_STATES:
            return "success"
        if decision.state in WARNING_STATES:
            return "warning"
        if decision.state in DANGER_STATES:
            return "danger"
        return "info"

    def _show_decision(self, decision: LicenseDecision) -> None:
        self.decision = decision
        self.status.setText(decision.message)
        self.status_container.setProperty("tone", self._tone(decision))
        self.status_container.style().unpolish(self.status_container)
        self.status_container.style().polish(self.status_container)
        activated = decision.claims is not None
        self.refresh_button.setEnabled(activated)
        self.deactivate_button.setEnabled(activated)

    def _activate(self) -> None:
        if not self.key.text().strip():
            warning(self, "Clé manquante", "Saisissez la clé reçue avec votre essai ou votre achat.")
            return
        try:
            self._show_decision(self.service.activate(self.key.text()))
            self.key.clear()
        except (LicenseApiError, ValueError) as exc:
            critical(self, "Activation refusée", str(exc))

    def _refresh(self) -> None:
        try:
            self._show_decision(self.service.refresh())
        except (LicenseApiError, ValueError) as exc:
            critical(self, "Actualisation impossible", str(exc))

    def _deactivate(self) -> None:
        answer = question(
            self,
            "Libérer cet appareil",
            "Cette opération libère une place de licence. Continuer ?",
            default=QMessageBox.StandardButton.No,
            tone="warning",
            danger=QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.deactivate()
            self._show_decision(self.service.evaluate())
        except (LicenseApiError, ValueError) as exc:
            critical(self, "Désactivation impossible", str(exc))
