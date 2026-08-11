from __future__ import annotations

import sys

from PySide6.QtCore import QCoreApplication, QTimer, Qt
from PySide6.QtWidgets import QApplication

from copro_auto.logging_setup import configure_logging
from copro_auto.ui.main_window import MainWindow
from copro_auto.ui.theme import apply_theme


def create_application(argv: list[str] | None = None) -> QApplication:
    QCoreApplication.setOrganizationName("Copro Auto")
    QCoreApplication.setApplicationName("Copro Auto")
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    application = QApplication(argv if argv is not None else sys.argv)
    apply_theme(application)
    return application


def run() -> int:
    configure_logging()
    application = create_application()
    window = MainWindow()
    window.show()
    if "--smoke-test" in sys.argv:
        QTimer.singleShot(300, application.quit)
    return application.exec()
