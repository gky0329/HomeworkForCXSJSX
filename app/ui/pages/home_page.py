from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

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
ACTION_BTN = (
    f"QPushButton {{ background-color: {SURFACE}; color: {TEXT_PRIMARY}; "
    f"border: 1px solid {BORDER}; border-radius: 10px; padding: 16px 20px; "
    f"font-size: 14px; text-align: left; }}"
    f"QPushButton:hover {{ border-color: {ACCENT}; background-color: #2A3A4A; }}"
)

TAB_NAMES = {
    "Code Editor": 1,
    "OJ Analysis": 2,
    "File Import": 3,
    "Review": 4,
    "Knowledge Graph": 5,
}


class HomePage(QWidget):
    tab_switch_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
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

        code_btn = self._action_card("Code Editor", "Write & visualize C++ code\nline by line", STACK_BORDER, "Code Editor")
        ojl_btn = self._action_card("OJ Analysis", "Paste OJ problems &\nget AI explanations", HEAP_BORDER, "OJ Analysis")
        file_btn = self._action_card("File Import", "Upload PDF / Word / C++\nextract knowledge + quiz", ACCENT, "File Import")

        actions.addWidget(code_btn)
        actions.addWidget(ojl_btn)
        actions.addWidget(file_btn)
        main.addLayout(actions)

        main.addSpacing(8)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        self._error_stat = self._stat_card("0", "Pending Review")
        self._kp_stat = self._stat_card("0", "Knowledge Points")
        self._activity_stat = self._stat_card("0", "Recent Activities")

        stats_row.addWidget(self._error_stat)
        stats_row.addWidget(self._kp_stat)
        stats_row.addWidget(self._activity_stat)
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

    def _action_card(self, title: str, desc: str, color: str, tab_name: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(CARD_BG)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        t = QLabel(title)
        t.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: bold;")
        layout.addWidget(t)

        d = QLabel(desc)
        d.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(d)

        card.setCursor(Qt.CursorShape.PointingHandCursor)

        def on_click(event, tn=tab_name):
            idx = TAB_NAMES.get(tn, 0)
            self.tab_switch_requested.emit(idx)

        card.mousePressEvent = on_click
        return card

    def _stat_card(self, num: str, label: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(CARD_BG)
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

        return card

    def refresh(self):
        stats = error_store.get_all_stats()
        activities = error_store.get_recent_activity()

        stat_num = self._error_stat.findChild(QLabel)
        if stat_num:
            stat_num.setText(str(stats["unreviewed"]))

        kp_labels = self._kp_stat.findChildren(QLabel)
        if len(kp_labels) > 0:
            kp_labels[0].setText(str(stats["knowledge_points"]))

        act_labels = self._activity_stat.findChildren(QLabel)
        if len(act_labels) > 0:
            act_labels[0].setText(str(len(activities)))

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
