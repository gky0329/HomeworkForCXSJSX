from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QDialogButtonBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


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
        "color: #F44747; font-size: 13px; font-weight: bold; padding: 8px 0;"
    )
    layout.addWidget(msg_label)

    if code:
        code_label = QLabel("Code being executed:")
        code_label.setStyleSheet("color: #808080; font-size: 11px; padding-top: 8px;")
        layout.addWidget(code_label)
        code_text = QTextEdit()
        code_text.setPlainText(code)
        code_text.setReadOnly(True)
        code_text.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 11))
        code_text.setMaximumHeight(100)
        code_text.setStyleSheet(
            "QTextEdit { background-color: #1E1E1E; color: #D4D4D4; "
            "border: 1px solid #3C3C3C; border-radius: 4px; padding: 6px; }"
        )
        layout.addWidget(code_text)

    if raw_response:
        raw_label = QLabel("Raw LLM response (first 2000 chars):")
        raw_label.setStyleSheet("color: #808080; font-size: 11px; padding-top: 8px;")
        layout.addWidget(raw_label)
        raw_text = QTextEdit()
        raw_text.setPlainText(raw_response[:2000])
        raw_text.setReadOnly(True)
        raw_text.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10))
        raw_text.setStyleSheet(
            "QTextEdit { background-color: #1E1E1E; color: #808080; "
            "border: 1px solid #3C3C3C; border-radius: 4px; padding: 6px; }"
        )
        layout.addWidget(raw_text)

    btn_row = QHBoxLayout()
    if on_retry:
        retry_btn = QPushButton("Retry")
        retry_btn.setStyleSheet(
            "QPushButton { background-color: #007ACC; color: #FFFFFF; "
            "border: none; border-radius: 4px; padding: 8px 24px; "
            "font-size: 13px; font-weight: bold; }"
            "QPushButton:hover { background-color: #1A8CD8; }"
        )
        retry_btn.clicked.connect(on_retry)
        btn_row.addWidget(retry_btn)

    close_btn = QPushButton("Close")
    close_btn.clicked.connect(dlg.reject)
    btn_row.addWidget(close_btn)
    layout.addLayout(btn_row)

    dlg.exec()
