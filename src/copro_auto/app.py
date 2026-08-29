from __future__ import annotations

import logging
import os
import sys

from PySide6.QtCore import QCoreApplication, QTimer, Qt
from PySide6.QtWidgets import QApplication

from copro_auto.logging_setup import configure_logging
from copro_auto.ui.main_window import MainWindow
from copro_auto.ui.theme import apply_theme


LOGGER = logging.getLogger(__name__)


def create_application(argv: list[str] | None = None) -> QApplication:
    QCoreApplication.setOrganizationName("Copro Auto")
    QCoreApplication.setApplicationName("Copro Auto")
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    application = QApplication(argv if argv is not None else sys.argv)
    apply_theme(application)
    return application


def run() -> int:
    configure_logging()
    if "--smoke-cad" in sys.argv:
        source = os.environ.get("COPRO_AUTO_SMOKE_CAD", "").strip()
        if not source:
            LOGGER.error("cad_package_smoke_missing_source")
            return 2
        try:
            from copro_auto.cad_import.service import import_cad

            draft = import_cad(source)
        except Exception:
            LOGGER.exception("cad_package_smoke_failed")
            return 3
        if not draft.levels:
            LOGGER.error("cad_package_smoke_no_levels")
            return 4
        return 0

    application = create_application()
    window = MainWindow()
    window.show()
    if "--smoke-test" in sys.argv:
        QTimer.singleShot(300, application.quit)
    return application.exec()
