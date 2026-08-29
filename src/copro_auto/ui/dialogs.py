from __future__ import annotations

import textwrap

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMessageBox, QWidget


BUTTON_TEXT = {
    QMessageBox.StandardButton.Ok: "OK",
    QMessageBox.StandardButton.Yes: "Oui",
    QMessageBox.StandardButton.No: "Non",
    QMessageBox.StandardButton.Save: "Enregistrer",
    QMessageBox.StandardButton.Discard: "Ignorer",
    QMessageBox.StandardButton.Cancel: "Annuler",
    QMessageBox.StandardButton.Close: "Fermer",
}


def _wrapped(text: str) -> str:
    return "\n".join(
        textwrap.fill(line, width=58, break_long_words=False, break_on_hyphens=False) if line else ""
        for line in text.splitlines()
    )


def build_message_box(
    parent: QWidget | None,
    icon: QMessageBox.Icon,
    title: str,
    text: str,
    *,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    default: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    tone: str = "info",
    danger: QMessageBox.StandardButton | None = None,
) -> QMessageBox:
    box = QMessageBox(icon, title, _wrapped(text), buttons, parent)
    box.setObjectName("AppMessageBox")
    box.setProperty("tone", tone)
    box.setTextFormat(Qt.TextFormat.PlainText)
    box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    message_label = box.findChild(QLabel, "qt_msgbox_label")
    if message_label is not None:
        message_label.setWordWrap(True)
        message_label.setMinimumWidth(360)
        message_label.setMaximumWidth(560)
    for standard_button, label in BUTTON_TEXT.items():
        button = box.button(standard_button)
        if button is not None:
            button.setText(label)
            button.setProperty("variant", "secondary")
    default_button = box.button(default)
    if default_button is not None:
        default_button.setProperty("variant", "primary")
        box.setDefaultButton(default)
    if danger is not None:
        danger_button = box.button(danger)
        if danger_button is not None:
            danger_button.setProperty("variant", "danger")
    escape = box.button(QMessageBox.StandardButton.Cancel)
    if escape is None:
        escape = box.button(QMessageBox.StandardButton.Close)
    if escape is None:
        escape = box.button(QMessageBox.StandardButton.No)
    if escape is not None:
        box.setEscapeButton(escape)
    for button in box.buttons():
        button.style().unpolish(button)
        button.style().polish(button)
    return box


def _show(
    parent: QWidget | None,
    icon: QMessageBox.Icon,
    title: str,
    text: str,
    *,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    default: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    tone: str = "info",
    danger: QMessageBox.StandardButton | None = None,
) -> QMessageBox.StandardButton:
    box = build_message_box(
        parent, icon, title, text,
        buttons=buttons, default=default, tone=tone, danger=danger,
    )
    return QMessageBox.StandardButton(box.exec())


def information(parent: QWidget | None, title: str, text: str) -> QMessageBox.StandardButton:
    return _show(parent, QMessageBox.Icon.Information, title, text, tone="info")


def success(parent: QWidget | None, title: str, text: str) -> QMessageBox.StandardButton:
    return _show(parent, QMessageBox.Icon.Information, title, text, tone="success")


def warning(parent: QWidget | None, title: str, text: str) -> QMessageBox.StandardButton:
    return _show(parent, QMessageBox.Icon.Warning, title, text, tone="warning")


def critical(parent: QWidget | None, title: str, text: str) -> QMessageBox.StandardButton:
    return _show(parent, QMessageBox.Icon.Critical, title, text, tone="danger")


def question(
    parent: QWidget | None,
    title: str,
    text: str,
    *,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    default: QMessageBox.StandardButton = QMessageBox.StandardButton.Yes,
    tone: str = "info",
    danger: QMessageBox.StandardButton | None = None,
) -> QMessageBox.StandardButton:
    return _show(
        parent, QMessageBox.Icon.Question, title, text,
        buttons=buttons, default=default, tone=tone, danger=danger,
    )
