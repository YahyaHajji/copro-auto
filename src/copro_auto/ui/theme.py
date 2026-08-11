from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication


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
    input: str


LIGHT = Palette(
    canvas="#F4F7F8", surface="#FFFFFF", surface_raised="#F9FBFB", sidebar="#102A2E",
    text="#162629", muted="#63777A", border="#D8E1E2", primary="#0F766E",
    primary_hover="#0B5F59", primary_soft="#DDF4F0", accent="#D6A756", danger="#B42318",
    warning="#B54708", success="#067647", input="#FFFFFF",
)
DARK = Palette(
    canvas="#0D1719", surface="#142124", surface_raised="#19292C", sidebar="#081113",
    text="#ECF3F3", muted="#9DB0B2", border="#2B3D40", primary="#2EB5A8",
    primary_hover="#55C7BC", primary_soft="#173C39", accent="#E0B86E", danger="#F97066",
    warning="#FDB022", success="#47CD89", input="#101C1F",
)


def system_prefers_dark() -> bool:
    hints = QGuiApplication.styleHints()
    try:
        return hints.colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:
        return False


def build_stylesheet(p: Palette) -> str:
    return f"""
    * {{ font-family: "Segoe UI Variable", "Segoe UI", sans-serif; font-size: 10pt; }}
    QMainWindow, QWidget#AppRoot {{ background: {p.canvas}; color: {p.text}; }}
    QWidget#Sidebar {{ background: {p.sidebar}; color: #F6FAFA; }}
    QWidget#Header, QFrame#Card, QFrame#Panel {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: 12px; }}
    QFrame#Header {{ border-left: 4px solid {p.accent}; }}
    QLabel {{ background: transparent; color: {p.text}; }}
    QLabel[role="brand"] {{ color: #FFFFFF; font-size: 18pt; font-weight: 700; }}
    QLabel[role="brandSub"] {{ color: #B8CACB; font-size: 9pt; }}
    QLabel[role="eyebrow"] {{ color: {p.primary}; font-size: 8pt; font-weight: 700; }}
    QLabel[role="title"] {{ font-size: 20pt; font-weight: 700; }}
    QLabel[role="section"] {{ font-size: 12pt; font-weight: 650; }}
    QLabel[role="muted"] {{ color: {p.muted}; }}
    QLabel[role="metric"] {{ font-size: 18pt; font-weight: 700; color: {p.primary}; }}
    QLabel[role="sidebarSection"] {{ color: #8FA7A9; font-size: 8pt; font-weight: 700; }}
    QLabel[role="license"] {{ color: #BFF5D2; background: #174B3B; padding: 7px 10px; border-radius: 9px; }}
    QPushButton[role="license"] {{ color: #BFF5D2; background: #174B3B; border-color: #246C56; padding: 7px 10px; border-radius: 9px; text-align: left; }}
    QPushButton {{ background: {p.surface}; color: {p.text}; border: 1px solid {p.border}; border-radius: 8px; padding: 8px 13px; font-weight: 600; }}
    QPushButton:hover {{ background: {p.surface_raised}; border-color: {p.primary}; }}
    QPushButton:focus {{ border: 2px solid {p.primary}; padding: 7px 12px; }}
    QPushButton:disabled {{ color: {p.muted}; background: {p.canvas}; }}
    QPushButton[variant="primary"] {{ color: white; background: {p.primary}; border-color: {p.primary}; }}
    QPushButton[variant="primary"]:hover {{ background: {p.primary_hover}; }}
    QPushButton[variant="ghost"] {{ color: #E8F1F1; background: transparent; border-color: transparent; text-align: left; padding: 9px 12px; }}
    QPushButton[variant="ghost"]:hover {{ background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.08); }}
    QPushButton[variant="danger"] {{ color: {p.danger}; }}
    QLineEdit, QDateEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background: {p.input}; color: {p.text}; border: 1px solid {p.border}; border-radius: 7px; padding: 7px 9px; min-height: 20px; selection-background-color: {p.primary}; }}
    QLineEdit:focus, QDateEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border: 2px solid {p.primary}; padding: 6px 8px; }}
    QLineEdit[invalid="true"] {{ border: 2px solid {p.danger}; }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QTabWidget::pane {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: 10px; top: -1px; }}
    QTabBar::tab {{ color: {p.muted}; background: transparent; padding: 10px 16px; border-bottom: 2px solid transparent; font-weight: 600; }}
    QTabBar::tab:selected {{ color: {p.primary}; border-bottom-color: {p.primary}; }}
    QTableWidget, QListWidget {{ background: {p.input}; color: {p.text}; alternate-background-color: {p.surface_raised}; border: 1px solid {p.border}; border-radius: 8px; gridline-color: {p.border}; outline: none; }}
    QTableWidget::item, QListWidget::item {{ padding: 6px; }}
    QTableWidget::item:selected, QListWidget::item:selected {{ color: {p.text}; background: {p.primary_soft}; }}
    QHeaderView::section {{ color: {p.muted}; background: {p.surface_raised}; border: none; border-bottom: 1px solid {p.border}; padding: 8px; font-size: 9pt; font-weight: 650; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {p.border}; border-radius: 4px; min-height: 30px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QStatusBar {{ background: {p.surface}; color: {p.muted}; border-top: 1px solid {p.border}; }}
    QToolTip {{ color: {p.text}; background: {p.surface}; border: 1px solid {p.border}; padding: 5px; }}
    """


def apply_theme(application: QApplication, dark: bool | None = None) -> Palette:
    palette = DARK if (system_prefers_dark() if dark is None else dark) else LIGHT
    application.setStyle("Fusion")
    application.setStyleSheet(build_stylesheet(palette))
    return palette
