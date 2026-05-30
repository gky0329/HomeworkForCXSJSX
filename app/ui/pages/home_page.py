from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea,
)
from PySide6.QtCore import Qt, Signal

from app.services import error_store
from app.ui.widgets.helpers import clear_layout
from app.ui.theme.colors import (
    CANVAS_BG, SURFACE, BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    STACK_BORDER, HEAP_BORDER, ACCENT, EDGE_DANGLING, HIGHLIGHT, SUCCESS,
)


HEADLINE = f"color: {TEXT_PRIMARY}; font-size: 28px; font-weight: 800; padding: 6px 0;"
SUBTITLE = f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: 400; padding: 2px 0;"
STAT_NUM = f"color: {STACK_BORDER}; font-size: 36px; font-weight: 800;"
STAT_LABEL = f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 400;"
LINK_BTN = (
    f"QPushButton {{ background-color: {SURFACE}; color: {ACCENT}; "
    f"border: 1px solid {BORDER}; "
    f"padding: 14px 24px; font-size: 15px; font-weight: 700; text-align: left; }}"
    f"QPushButton:hover {{ border-color: {ACCENT}; background-color: #2A3A4A; color: {STACK_BORDER}; }}"
)

CARD_BG = (
    f"QFrame#statCard {{ background-color: {SURFACE}; border: 1px solid {BORDER}; }}"
    f"QFrame#statCard:hover {{ border-color: {STACK_BORDER}; }}"
    f"QFrame#statCard QLabel {{ border: none; background: transparent; outline: none; }}"
)

TAB_NAMES = {
    "Code Editor": 1,
    "OJ Analysis": 2,
    "File Import": 3,
    "Review": 4,
    "Knowledge Base": 5,
}


class HomePage(QWidget):
    tab_switch_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stat_labels: dict[str, QLabel] = {}
        self._setup_ui()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        main = QVBoxLayout(content)
        main.setContentsMargins(24, 20, 24, 20)
        main.setSpacing(16)

        title = QLabel("C++ Memory Visualizer")
        title.setStyleSheet(HEADLINE)
        main.addWidget(title)

        sub = QLabel("Visualize memory, learn pointers, master C++")
        sub.setStyleSheet(SUBTITLE)
        main.addWidget(sub)

        main.addSpacing(8)

        quick_label = QLabel("Quick Start")
        quick_label.setStyleSheet(
            f"color: {STACK_BORDER}; font-size: 13px; font-weight: bold; padding: 4px 0;"
        )
        main.addWidget(quick_label)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(10)

        for label, tab, desc in [
            ("Write Code", "Code Editor", "Run C++ code and watch\nmemory state step by step"),
            ("Import & Learn", "File Import", "Upload PDF/DOCX/CPP files\nand extract knowledge points"),
            ("Review Mistakes", "Review", "Practice with spaced repetition\nto master C++ concepts"),
        ]:
            card = QFrame()
            card.setObjectName("quickCard")
            card.setStyleSheet(
                f"QFrame#quickCard {{ background-color: {SURFACE}; border: 1px solid {BORDER}; "
                f"padding: 10px 14px; }}"
                f"QFrame#quickCard:hover {{ border-color: {ACCENT}; background-color: #2A3A4A; }}"
                f"QFrame#quickCard QLabel {{ border: none; background: transparent; outline: none; }}"
            )
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            idx = TAB_NAMES.get(tab, 0)
            card.mousePressEvent = lambda e, i=idx: self.tab_switch_requested.emit(i)

            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(4)

            title_lbl = QLabel(label)
            title_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 15px; font-weight: 700;")
            card_layout.addWidget(title_lbl)

            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 400;")
            card_layout.addWidget(desc_lbl)

            quick_row.addWidget(card)

        main.addLayout(quick_row)

        main.addSpacing(8)

        actions = QHBoxLayout()
        actions.setSpacing(12)

        for label, tab in [("Code Editor", "Code Editor"),
                           ("OJ Analysis", "OJ Analysis"),
                           ("File Import", "File Import")]:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(LINK_BTN)
            idx = TAB_NAMES.get(tab, 0)
            btn.clicked.connect(lambda checked=None, i=idx: self.tab_switch_requested.emit(i))
            actions.addWidget(btn)

        main.addLayout(actions)

        main.addSpacing(8)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        self._error_card = self._stat_card("0", "Pending Review", "Review")
        self._kp_card = self._stat_card("0", "Knowledge Points", "Knowledge Base")
        self._act_card = self._stat_card("0", "Recent Activities", None)

        stats_row.addWidget(self._error_card)
        stats_row.addWidget(self._kp_card)
        stats_row.addWidget(self._act_card)
        main.addLayout(stats_row)

        main.addSpacing(4)

        activity_label = QLabel("Recent Activity")
        activity_label.setStyleSheet(
            f"color: {STACK_BORDER}; font-size: 13px; font-weight: bold; padding: 4px 0;"
        )
        main.addWidget(activity_label)

        self._activity_list = QVBoxLayout()
        main.addLayout(self._activity_list)

        main.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _stat_card(self, num: str, label: str, tab_name: str | None) -> QFrame:
        card = QFrame()
        card.setObjectName("statCard")
        card.setStyleSheet(CARD_BG)

        if tab_name:
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            idx = TAB_NAMES.get(tab_name, 0)

            def on_click(event, i=idx):
                self.tab_switch_requested.emit(i)

            card.mousePressEvent = on_click

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        n = QLabel(num)
        n.setStyleSheet(STAT_NUM)
        n.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(n)

        l = QLabel(label)
        l.setStyleSheet(STAT_LABEL)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(l)

        self._stat_labels[label] = n
        return card

    def refresh(self):
        stats = error_store.get_all_stats()
        activities = error_store.get_recent_activity()

        if "Pending Review" in self._stat_labels:
            self._stat_labels["Pending Review"].setText(str(stats["unreviewed"]))
        if "Knowledge Points" in self._stat_labels:
            self._stat_labels["Knowledge Points"].setText(str(stats["knowledge_points"]))
        if "Recent Activities" in self._stat_labels:
            self._stat_labels["Recent Activities"].setText(str(len(activities)))

        clear_layout(self._activity_list)

        if not activities:
            placeholder = QLabel("No activity yet — start by running some code or importing a file")
            placeholder.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; padding: 8px 0;")
            self._activity_list.addWidget(placeholder)
            self._activity_list.addStretch()
            return

        for a in activities[:15]:
            ts = a.get("timestamp", "")[:19].replace("T", " ")
            act = a.get("action", "?")
            detail = a.get("detail", "")
            row = QLabel(f"  {ts}   {act}  —  {detail}")
            row.setStyleSheet(
                f"color: {TEXT_PRIMARY}; font-size: 11px; "
                f"padding: 3px 8px;"
            )
            self._activity_list.addWidget(row)

        if len(activities) > 15:
            more = QLabel(f"  ... and {len(activities) - 15} more")
            more.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px; padding: 3px 8px;")
            self._activity_list.addWidget(more)

        self._activity_list.addStretch()
