from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QListWidget, QListWidgetItem, QMessageBox,
    QSplitter,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.services import error_store
from app.ui.theme.colors import (
    CANVAS_BG, SURFACE, BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    STACK_BORDER, HEAP_BORDER, ACCENT, EDGE_DANGLING, SUCCESS, HIGHLIGHT,
)


def _mlabel(text: str, color: str = TEXT_PRIMARY, size: int = 12,
            bold: bool = False) -> QLabel:
    w = "bold" if bold else "normal"
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(
        f"color: {color}; font-size: {size}px; font-weight: {w};"
        f"background: transparent; border: none;"
    )
    return label


class ReviewPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._errors: list = []
        self._setup_ui()
        self._refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QHBoxLayout()
        header.addWidget(_mlabel("Error Review", STACK_BORDER, 16, True))
        header.addStretch()
        self._stats_label = _mlabel("", TEXT_SECONDARY, 12)
        header.addWidget(self._stats_label)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(_mlabel("Errors", HEAP_BORDER, 13, True))
        self._error_list = QListWidget()
        self._error_list.setStyleSheet(
            f"QListWidget {{ background-color: {CANVAS_BG}; "
            f"border: 1px solid {BORDER}; border-radius: 6px; "
            f"color: {TEXT_PRIMARY}; font-size: 12px; }}"
            f"QListWidget::item {{ padding: 8px; border-bottom: 1px solid {BORDER}; }}"
            f"QListWidget::item:selected {{ background-color: {SURFACE}; }}"
        )
        self._error_list.currentRowChanged.connect(self._on_select)
        left_layout.addWidget(self._error_list)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.addWidget(_mlabel("Details", HEAP_BORDER, 13, True))

        self._detail = QFrame()
        self._detail.setStyleSheet(
            f"QFrame {{ background-color: {SURFACE}; "
            f"border: 1px solid {BORDER}; border-radius: 8px; padding: 12px; }}"
        )
        self._detail_layout = QVBoxLayout(self._detail)
        right_layout.addWidget(self._detail)

        btn_row = QHBoxLayout()
        self._review_btn = QPushButton("Mark Reviewed")
        self._review_btn.setEnabled(False)
        self._review_btn.clicked.connect(self._on_review)
        btn_row.addWidget(self._review_btn)
        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(self._delete_btn)
        btn_row.addStretch()
        right_layout.addLayout(btn_row)

        splitter.addWidget(right)
        splitter.setSizes([350, 500])
        layout.addWidget(splitter)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh)
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(refresh_btn)
        layout.addLayout(bottom)

    def _refresh(self):
        self._errors = error_store.get_errors()
        stats = error_store.get_all_stats()
        self._stats_label.setText(
            f"{stats['total_errors']} total / {stats['unreviewed']} unreviewed"
        )
        self._error_list.clear()
        for e in self._errors:
            kp = e.get("knowledge_point", "?")
            ts = e.get("timestamp", "")[:10]
            rv = "" if e.get("reviewed") else "  [NEW]"
            text = f"[{kp}] {e.get('question', '')[:50]}... ({ts}){rv}"
            item = QListWidgetItem(text)
            if e.get("reviewed"):
                item.setForeground(Qt.GlobalColor.gray)
            self._error_list.addItem(item)

    def _on_select(self, idx: int):
        if idx < 0 or idx >= len(self._errors):
            return
        e = self._errors[idx]
        self._clear_detail()
        self._detail_layout.addWidget(
            _mlabel(f"Knowledge: {e.get('knowledge_point', '?')}", STACK_BORDER, 13, True)
        )
        self._detail_layout.addWidget(
            _mlabel(f"Q: {e.get('question', '')}", TEXT_PRIMARY, 12)
        )
        self._detail_layout.addWidget(
            _mlabel(f"Your answer: {e.get('user_answer', '')}", EDGE_DANGLING, 12)
        )
        self._detail_layout.addWidget(
            _mlabel(f"Correct: {e.get('correct_answer', '')}", SUCCESS, 12)
        )
        self._detail_layout.addWidget(
            _mlabel(f"Time: {e.get('timestamp', '')}", TEXT_SECONDARY, 10)
        )
        self._review_btn.setEnabled(not e.get("reviewed", False))
        self._delete_btn.setEnabled(True)

    def _on_review(self):
        idx = self._error_list.currentRow()
        if 0 <= idx < len(self._errors):
            error_store.mark_reviewed(idx)
            self._refresh()

    def _on_delete(self):
        idx = self._error_list.currentRow()
        if 0 <= idx < len(self._errors):
            error_store.delete_error(idx)
            self._refresh()

    def _clear_detail(self):
        while self._detail_layout.count():
            item = self._detail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
