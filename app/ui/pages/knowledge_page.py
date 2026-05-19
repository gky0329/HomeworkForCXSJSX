from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QScrollArea, QFrame, QLineEdit, QSplitter,
    QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt, QMargins

from app.services import error_store
from app.ui.widgets.helpers import mlabel
from app.ui.theme.colors import (
    CANVAS_BG, SURFACE, BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    STACK_BORDER, HEAP_BORDER, ACCENT,
)


CARD_BG = (
    f"QFrame {{ background-color: {SURFACE}; border: 1px solid {BORDER}; "
    f"border-radius: 10px; }}"
    f"QFrame:hover {{ border-color: {STACK_BORDER}; }}"
)


class KnowledgePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_kps: list[dict] = []
        self._setup_ui()
        self._refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.addWidget(mlabel("Knowledge Base", STACK_BORDER, 16, True))
        header.addStretch()

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search concepts...")
        self._search.setStyleSheet(
            f"QLineEdit {{ background-color: {CANVAS_BG}; "
            f"color: {TEXT_PRIMARY}; border: 1px solid {BORDER}; "
            f"border-radius: 6px; padding: 6px 12px; font-size: 13px; }}"
            f"QLineEdit:focus {{ border-color: {ACCENT}; }}"
        )
        self._search.textChanged.connect(self._on_search)
        header.addWidget(self._search)

        self._stats_label = mlabel("", TEXT_SECONDARY, 12)
        header.addWidget(self._stats_label)

        layout.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._concept_list = QListWidget()
        self._concept_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._concept_list.setWordWrap(True)
        self._concept_list.setStyleSheet(
            f"QListWidget {{ background-color: {CANVAS_BG}; "
            f"border: 1px solid {BORDER}; border-radius: 8px; "
            f"color: {TEXT_PRIMARY}; font-size: 13px; }}"
            f"QListWidget::item {{ padding: 10px 14px; min-height: 32px; "
            f"border-bottom: 1px solid {BORDER}; }}"
            f"QListWidget::item:selected {{ background-color: #1A3A5C; }}"
        )
        self._concept_list.currentRowChanged.connect(self._on_select)
        splitter.addWidget(self._concept_list)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 0, 0, 0)

        self._detail_label = mlabel("Select a concept", TEXT_SECONDARY, 13)
        right_layout.addWidget(self._detail_label)

        self._detail = QFrame()
        self._detail.setStyleSheet(
            f"QFrame {{ background-color: {SURFACE}; "
            f"border: 1px solid {BORDER}; border-radius: 10px; padding: 16px; }}"
        )
        self._detail_layout = QVBoxLayout(self._detail)
        self._detail_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background: transparent; }}"
        )
        detail_scroll.setWidget(self._detail)
        right_layout.addWidget(detail_scroll)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 5)
        layout.addWidget(splitter)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh)
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(refresh_btn)
        layout.addLayout(bottom)

    def _refresh(self):
        self._all_kps = error_store.get_knowledge_points()
        scores = {s["name"]: s for s in error_store.get_ucb_queue()}
        freq = error_store.get_error_frequency()

        # Merge
        for kp in self._all_kps:
            name = kp["name"]
            kp["_errors"] = freq.get(name, 0)
            kp["_score"] = scores.get(name, {})

        self._all_kps.sort(
            key=lambda k: -(k.get("count", 0) * 0.5 + k.get("_errors", 0))
        )

        stats = error_store.get_all_stats()
        self._stats_label.setText(
            f"{stats['knowledge_points']} concepts, "
            f"{stats['total_errors']} errors"
        )

        self._populate_list()

    def _populate_list(self, filter_text: str = ""):
        self._concept_list.clear()
        ft = filter_text.lower()

        for kp in self._all_kps:
            name = kp.get("name", "")
            if ft and ft not in name.lower():
                continue

            count = kp.get("count", 1)
            errs = kp.get("_errors", 0)
            source = kp.get("source", "")

            score = kp.get("_score", {})
            correct = score.get("correct", 0)
            wrong = score.get("wrong", 0)
            ucb = score.get("ucb", 0)

            line1 = name
            parts = []
            if count:
                parts.append(f"seen {count}×")
            if correct or wrong:
                parts.append(f"quiz ✓{correct} ✗{wrong}")
            if errs:
                parts.append(f"errors {errs}")
            if source:
                parts.append(f"from {source}")

            label = f"{line1}\n  {' · '.join(parts) if parts else ''}"

            item = QListWidgetItem(label)
            item.setSizeHint(item.sizeHint().grownBy(QMargins(0, 6, 0, 6)))

            if errs > 0:
                item.setForeground(Qt.GlobalColor.red)
            elif count > 0:
                item.setForeground(Qt.GlobalColor.green)

            item.setData(Qt.ItemDataRole.UserRole, kp)
            self._concept_list.addItem(item)

    def _on_search(self, text: str):
        self._populate_list(text)

    def _on_select(self, idx: int):
        if idx < 0:
            return

        while self._detail_layout.count():
            item = self._detail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        item = self._concept_list.item(idx)
        kp = item.data(Qt.ItemDataRole.UserRole)
        if not kp:
            return

        name = kp.get("name", "?")
        count = kp.get("count", 1)
        source = kp.get("source", "")

        self._detail_label.setText(name)

        self._detail_layout.addWidget(
            mlabel(name, STACK_BORDER, 18, True)
        )

        stats = [
            f"Encountered: {count} times",
            f"Source: {source or 'unknown'}",
        ]
        score = kp.get("_score", {})
        if score:
            correct = score.get("correct", 0)
            wrong = score.get("wrong", 0)
            ucb = score.get("ucb", 0)
            stats.append(f"Quiz: ✓{correct} ✗{wrong}  UCB: {int(ucb * 100)}%")

        errs = kp.get("_errors", 0)
        if errs:
            stats.append(f"Errors tracked: {errs}")

        for s in stats:
            self._detail_layout.addWidget(
                mlabel(s, TEXT_SECONDARY, 12)
            )

        self._detail_layout.addSpacing(8)

        deps = error_store.get_dependencies(name)
        if deps:
            self._detail_layout.addWidget(
                mlabel("Dependencies", HEAP_BORDER, 13, True)
            )
            for dep in deps:
                self._detail_layout.addWidget(
                    mlabel(f"  → {dep}", TEXT_PRIMARY, 12)
                )
        else:
            self._detail_layout.addWidget(
                mlabel("No dependencies recorded", TEXT_SECONDARY, 11)
            )

        related_errors = error_store.get_errors()
        related = [
            e for e in related_errors
            if e.get("knowledge_point", "") == name
        ][:5]

        if related:
            self._detail_layout.addSpacing(4)
            self._detail_layout.addWidget(
                mlabel(f"Recent Cards ({len(related)})", ACCENT, 12, True)
            )
            for e in related:
                q = e.get("question", "")[:80]
                reviewed = "✓" if e.get("reviewed") else " "
                self._detail_layout.addWidget(
                    mlabel(f"  [{reviewed}] {q}", TEXT_SECONDARY, 11)
                )

        self._detail_layout.addStretch()
