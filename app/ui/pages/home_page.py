from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton,
)
from PySide6.QtCore import Qt, Signal

from app.services import error_store
from app.ui.theme.colors import (
    CANVAS_BG, SURFACE, BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    STACK_BORDER, HEAP_BORDER, ACCENT, EDGE_DANGLING, HIGHLIGHT, SUCCESS,
)


HEADLINE = f"color: {TEXT_PRIMARY}; font-size: 20px; font-weight: bold; padding: 4px 0;"
SUBTITLE = f"color: {TEXT_SECONDARY}; font-size: 12px; padding: 2px 0;"
STAT_NUM = f"color: {STACK_BORDER}; font-size: 26px; font-weight: bold;"
STAT_LABEL = f"color: {TEXT_SECONDARY}; font-size: 11px;"
CARD_BG = (
    f"QFrame {{ background-color: {SURFACE}; border: 1px solid {BORDER}; "
    f"border-radius: 10px; }}"
    f"QFrame:hover {{ border-color: {STACK_BORDER}; }}"
)
LINK_BTN = (
    f"QPushButton {{ background-color: {SURFACE}; color: {ACCENT}; "
    f"border: 1px solid {BORDER}; border-radius: 10px; "
    f"padding: 14px 24px; font-size: 15px; font-weight: bold; text-align: left; }}"
    f"QPushButton:hover {{ border-color: {ACCENT}; background-color: #2A3A4A; color: {STACK_BORDER}; }}"
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
        main = QVBoxLayout(self)
        main.setContentsMargins(24, 20, 24, 20)
        main.setSpacing(16)

        title = QLabel("C++ Memory Visualizer")
        title.setStyleSheet(HEADLINE)
        main.addWidget(title)

        sub = QLabel("Visualize memory, learn pointers, master C++")
        sub.setStyleSheet(SUBTITLE)
        main.addWidget(sub)

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

    def _stat_card(self, num: str, label: str, tab_name: str | None) -> QFrame:
        card = QFrame()
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

        while self._activity_list.count():
            item = self._activity_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not activities:
            placeholder = QLabel("No activity yet — start by running some code or importing a file")
            placeholder.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; padding: 8px 0;")
            self._activity_list.addWidget(placeholder)
            self._activity_list.addStretch()
            return

        for a in activities[:5]:
            ts = a.get("timestamp", "")[:16].replace("T", " ")
            act = a.get("action", "?")
            detail = a.get("detail", "")
            row = QLabel(f"  {ts}   {act}  —  {detail}")
            row.setStyleSheet(
                f"color: {TEXT_PRIMARY}; font-size: 11px; "
                f"padding: 3px 8px;"
            )
            self._activity_list.addWidget(row)

        if len(activities) > 5:
            more = QLabel(f"  ... and {len(activities) - 5} more")
            more.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px; padding: 3px 8px;")
            self._activity_list.addWidget(more)

        self._activity_list.addStretch()
