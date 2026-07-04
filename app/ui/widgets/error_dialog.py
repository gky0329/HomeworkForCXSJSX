from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.services.i18n import tr
from app.ui.theme.colors import ERROR, TEXT_SECONDARY, TEXT_PRIMARY, TEXT_MUTED, EDITOR_BG, BORDER


def show_error_dialog(parent, title: str, message: str, code: str = "",
                      raw_response: str = "", on_retry=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setMinimumSize(500, 400)
    layout = QVBoxLayout(dlg)
    layout.setSpacing(10)

    msg_label = QLabel(message)
    msg_label.setWordWrap(True)
    msg_label.setStyleSheet(
        f"color: {ERROR}; font-size: 15px; font-weight: bold; padding: 8px 0;"
    )
    layout.addWidget(msg_label)

    if code:
        code_label = QLabel(tr("Code being executed:"))
        code_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: 600; padding-top: 8px;")
        layout.addWidget(code_label)
        code_text = QTextEdit()
        code_text.setPlainText(code)
        code_text.setReadOnly(True)
        code_text.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 14))
        code_text.setMaximumHeight(100)
        code_text.setStyleSheet(
            f"QTextEdit {{ background-color: {EDITOR_BG}; color: {TEXT_PRIMARY}; "
            f"border: 2px solid {BORDER}; padding: 6px; }}"
        )
        layout.addWidget(code_text)

    if raw_response:
        raw_label = QLabel(tr("Raw LLM response (first 2000 chars):"))
        raw_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: 600; padding-top: 8px;")
        layout.addWidget(raw_label)
        raw_text = QTextEdit()
        raw_text.setPlainText(raw_response[:2000])
        raw_text.setReadOnly(True)
        raw_text.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 13))
        raw_text.setStyleSheet(
            f"QTextEdit {{ background-color: {EDITOR_BG}; color: {TEXT_MUTED}; "
            f"border: 2px solid {BORDER}; padding: 6px; }}"
        )
        layout.addWidget(raw_text)

    btn_row = QHBoxLayout()
    if on_retry:
        retry_btn = QPushButton(tr("Retry"))
        retry_btn.clicked.connect(on_retry)
        btn_row.addWidget(retry_btn)

    close_btn = QPushButton(tr("Close"))
    close_btn.clicked.connect(dlg.reject)
    btn_row.addWidget(close_btn)
    layout.addLayout(btn_row)

    dlg.exec()
