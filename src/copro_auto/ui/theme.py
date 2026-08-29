from __future__ import annotations

import ctypes
import logging
import sys
from dataclasses import dataclass

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication, QWidget


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Palette:
    canvas: str
    surface: str
    surface_raised: str
    sidebar: str
    text: str
    muted: str
    border: str
    primary: str
    primary_hover: str
    primary_soft: str
    accent: str
    danger: str
    warning: str
    success: str
    danger_soft: str
    warning_soft: str
    success_soft: str
    focus: str
    input: str


LIGHT = Palette(
    canvas="#F7FAFB", surface="#FFFFFF", surface_raised="#F3F8FA", sidebar="#FFFFFF",
    text="#10262B", muted="#60777B", border="#D5E1E4", primary="#0FA9A3",
    primary_hover="#0B8D88", primary_soft="#DDF7F5", accent="#E4B84F", danger="#B42318",
    warning="#B54708", success="#0D8B63", danger_soft="#FDECEA", warning_soft="#FFF3E0",
    success_soft="#E5F6EF", focus="#087F7A", input="#FFFFFF",
)
DARK = Palette(
    canvas="#0D1719", surface="#142124", surface_raised="#19292C", sidebar="#081113",
    text="#ECF3F3", muted="#9DB0B2", border="#2B3D40", primary="#2EB5A8",
    primary_hover="#55C7BC", primary_soft="#173C39", accent="#E0B86E", danger="#F97066",
    warning="#FDB022", success="#47CD89", danger_soft="#3B2020", warning_soft="#3A3018",
    success_soft="#15352B", focus="#55C7BC", input="#101C1F",
)


def _request_light_title_bar(widget: QWidget) -> None:
    if sys.platform != "win32":
        return
    try:
        enabled = ctypes.c_int(0)
        size = ctypes.sizeof(enabled)
        handle = int(widget.winId())
        for attribute in (20, 19):
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                handle, attribute, ctypes.byref(enabled), size,
            )
            if result == 0:
                break
    except (AttributeError, OSError, TypeError, ValueError):
        LOGGER.debug("light_title_bar_unavailable", exc_info=True)


class _LightChromeFilter(QObject):
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Show and isinstance(watched, QWidget) and watched.isWindow():
            _request_light_title_bar(watched)
        return super().eventFilter(watched, event)

def build_stylesheet(p: Palette) -> str:
    return f"""
    * {{ font-family: "Segoe UI Variable", "Segoe UI", sans-serif; font-size: 10pt; }}
    QMainWindow, QWidget#AppRoot, QDialog, QMessageBox {{ background: {p.canvas}; color: {p.text}; }}
    QWidget#Sidebar {{ background: {p.sidebar}; color: {p.text}; border-right: 1px solid {p.border}; }}
    QScrollArea#ProjectIdentityScroll, QScrollArea#ProjectIdentityScroll QWidget#qt_scrollarea_viewport,
    QWidget#ProjectIdentityContent {{ background: {p.surface}; color: {p.text}; }}
    QWidget#Header, QFrame#Card, QFrame#Panel {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: 12px; }}
    QFrame#Header {{ border-left: 4px solid {p.accent}; }}
    QLabel {{ background: transparent; color: {p.text}; }}
    QLabel[role="brand"] {{ color: {p.text}; font-size: 18pt; font-weight: 700; }}
    QLabel[role="brandSub"] {{ color: {p.muted}; font-size: 9pt; }}
    QLabel[role="eyebrow"] {{ color: {p.primary}; font-size: 8pt; font-weight: 700; }}
    QLabel[role="title"] {{ font-size: 20pt; font-weight: 700; }}
    QLabel[role="section"] {{ font-size: 12pt; font-weight: 650; }}
    QLabel[role="muted"] {{ color: {p.muted}; }}
    QLabel[role="metric"] {{ font-size: 18pt; font-weight: 700; color: {p.primary}; }}
    QLabel[role="sidebarSection"] {{ color: {p.muted}; font-size: 8pt; font-weight: 700; }}
    QLabel[role="dialogTitle"] {{ color: {p.text}; font-size: 18pt; font-weight: 700; }}
    QLabel[role="helper"] {{ color: {p.muted}; background: {p.surface_raised}; border: 1px solid {p.border}; border-radius: 7px; padding: 8px 10px; }}
    QLabel[role="fieldLabel"] {{ color: {p.text}; font-weight: 600; }}
    QLabel[role="status"], QFrame[role="status"] {{ color: {p.text}; border: 1px solid {p.border}; border-radius: 8px; padding: 10px 12px; }}
    QLabel[role="status"][tone="info"], QFrame[role="status"][tone="info"] {{ background: {p.primary_soft}; border-color: {p.primary}; }}
    QLabel[role="status"][tone="success"], QFrame[role="status"][tone="success"] {{ color: {p.success}; background: {p.success_soft}; border-color: {p.success}; }}
    QLabel[role="status"][tone="warning"], QFrame[role="status"][tone="warning"] {{ color: {p.warning}; background: {p.warning_soft}; border-color: {p.warning}; }}
    QLabel[role="status"][tone="danger"], QFrame[role="status"][tone="danger"] {{ color: {p.danger}; background: {p.danger_soft}; border-color: {p.danger}; }}
    QFrame[role="status"] QLabel {{ color: inherit; border: none; padding: 0; }}
    QFrame[role="destructive"] {{ background: {p.danger_soft}; border: 1px solid #F2B8B5; border-radius: 9px; }}
    QLabel[role="license"] {{ color: white; background: {p.primary}; padding: 7px 10px; border-radius: 9px; }}
    QPushButton[role="license"] {{ color: white; background: {p.primary}; border-color: {p.primary}; padding: 7px 10px; border-radius: 9px; text-align: left; }}
    QPushButton {{ background: {p.surface}; color: {p.text}; border: 1px solid {p.border}; border-radius: 8px; padding: 8px 13px; font-weight: 600; }}
    QPushButton:hover {{ background: {p.surface_raised}; border-color: {p.primary}; }}
    QPushButton:focus {{ border: 2px solid {p.focus}; padding: 7px 12px; }}
    QPushButton:disabled {{ color: {p.muted}; background: {p.canvas}; }}
    QPushButton[variant="primary"] {{ color: white; background: {p.primary}; border-color: {p.primary}; }}
    QPushButton[variant="primary"]:hover, QPushButton[variant="primary"]:pressed {{ color: white; background: {p.primary_hover}; border-color: {p.primary_hover}; }}
    QPushButton[variant="danger"] {{ color: {p.danger}; background: {p.danger_soft}; border-color: #F2B8B5; }}
    QPushButton[variant="danger"]:hover, QPushButton[variant="danger"]:pressed {{ color: white; background: {p.danger}; border-color: {p.danger}; }}
    QPushButton[role="license"]:hover {{ color: white; background: {p.primary_hover}; border-color: {p.primary_hover}; }}
    QPushButton[role="license"]:pressed {{ color: white; background: {p.primary_hover}; border-color: {p.primary_hover}; }}
    QPushButton[role="license"]:focus {{ color: white; background: {p.primary}; border: 2px solid {p.primary_hover}; padding: 6px 9px; }}
    QPushButton[variant="ghost"] {{ color: {p.text}; background: transparent; border-color: transparent; text-align: left; padding: 9px 12px; }}
    QPushButton[variant="ghost"]:hover {{ background: {p.primary_soft}; border-color: {p.primary_soft}; }}
    QLineEdit, QDateEdit, QTimeEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background: {p.input}; color: {p.text}; border: 1px solid {p.border}; border-radius: 7px; padding: 7px 9px; min-height: 20px; selection-background-color: {p.primary}; }}
    QLineEdit:focus, QDateEdit:focus, QTimeEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 2px solid {p.primary}; padding: 6px 8px; }}
    QLineEdit[invalid="true"] {{ border: 2px solid {p.danger}; }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox QAbstractItemView {{ color: {p.text}; background: {p.surface}; selection-color: {p.text}; selection-background-color: {p.primary_soft}; border: 1px solid {p.border}; }}
    QTabWidget::pane {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: 10px; top: -1px; }}
    QTabBar::tab {{ color: {p.muted}; background: transparent; padding: 10px 16px; border-bottom: 2px solid transparent; font-weight: 600; }}
    QTabBar::tab:selected {{ color: {p.primary}; border-bottom-color: {p.primary}; }}
    QTableWidget, QListWidget, QAbstractItemView {{ background: {p.input}; color: {p.text}; alternate-background-color: {p.surface_raised}; border: 1px solid {p.border}; border-radius: 8px; gridline-color: {p.border}; outline: none; }}
    QTableWidget:focus, QListWidget:focus {{ border: 2px solid {p.focus}; }}
    QTableWidget::item, QListWidget::item {{ padding: 6px; }}
    QTableWidget::item:selected, QListWidget::item:selected {{ color: {p.text}; background: {p.primary_soft}; }}
    QHeaderView::section {{ color: {p.muted}; background: {p.surface_raised}; border: none; border-bottom: 1px solid {p.border}; padding: 8px; font-size: 9pt; font-weight: 650; }}
    QTableCornerButton::section {{ background: {p.surface_raised}; border: none; border-bottom: 1px solid {p.border}; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {p.border}; border-radius: 4px; min-height: 30px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{ background: {p.surface_raised}; height: 10px; margin: 2px; border-radius: 4px; }}
    QScrollBar::handle:horizontal {{ background: {p.border}; border-radius: 4px; min-width: 30px; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    QSplitter::handle {{ background: {p.border}; }}
    QSplitter::handle:horizontal {{ width: 1px; margin: 8px 3px; }}
    QMenu, QCalendarWidget {{ color: {p.text}; background: {p.surface}; border: 1px solid {p.border}; }}
    QMenu::item {{ padding: 7px 22px; }}
    QMenu::item:selected {{ color: {p.text}; background: {p.primary_soft}; }}
    QCalendarWidget QToolButton {{ color: {p.text}; background: {p.surface}; border: none; padding: 6px; }}
    QCalendarWidget QAbstractItemView {{ color: {p.text}; background: {p.surface}; selection-color: white; selection-background-color: {p.primary}; }}
    QMessageBox QLabel#qt_msgbox_label {{ color: {p.text}; min-width: 360px; max-width: 560px; padding: 6px 4px; }}
    QMessageBox QLabel#qt_msgboxex_icon_label {{ background: transparent; }}
    QMessageBox[tone="info"] {{ background: {p.surface}; }}
    QMessageBox[tone="success"] {{ background: {p.success_soft}; }}
    QMessageBox[tone="warning"] {{ background: {p.warning_soft}; }}
    QMessageBox[tone="danger"] {{ background: {p.danger_soft}; }}
    QDialogButtonBox {{ background: transparent; }}
    QStatusBar {{ background: {p.surface}; color: {p.muted}; border-top: 1px solid {p.border}; }}
    QToolTip {{ color: {p.text}; background: {p.surface}; border: 1px solid {p.border}; padding: 5px; }}
    """


def apply_theme(application: QApplication, dark: bool = False) -> Palette:
    """Apply Copro Auto's theme, using the light product design by default."""
    palette = DARK if dark else LIGHT
    application.setStyle("Fusion")
    application.setStyleSheet(build_stylesheet(palette))
    chrome_filter = _LightChromeFilter(application)
    application.installEventFilter(chrome_filter)
    application._copro_light_chrome_filter = chrome_filter  # type: ignore[attr-defined]
    return palette
