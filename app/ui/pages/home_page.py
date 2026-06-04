import re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea,
)
from PySide6.QtCore import Qt, Signal

from app.services import error_store
from app.services.i18n import tr
from app.ui.widgets.helpers import clear_layout
from app.ui.theme.colors import (
    CANVAS_BG, SURFACE, BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    STACK_BORDER, ACCENT, SUCCESS,
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

        title = QLabel(tr("C++ Memory Visualizer"))
        self._title = title
        title.setStyleSheet(HEADLINE)
        main.addWidget(title)

        sub = QLabel(tr("Visualize memory, learn pointers, master C++"))
        self._subtitle = sub
        sub.setStyleSheet(SUBTITLE)
        main.addWidget(sub)

        main.addSpacing(8)

        quick_label = QLabel(tr("Quick Start"))
        self._quick_label = quick_label
        quick_label.setStyleSheet(
            f"color: {STACK_BORDER}; font-size: 13px; font-weight: bold; padding: 4px 0;"
        )
        main.addWidget(quick_label)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(10)

        self._quick_cards: list[tuple[QLabel, QLabel, str, str]] = []
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

            title_lbl = QLabel(tr(label))
            title_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 15px; font-weight: 700;")
            card_layout.addWidget(title_lbl)

            desc_lbl = QLabel(tr(desc))
            desc_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 400;")
            card_layout.addWidget(desc_lbl)
            self._quick_cards.append((title_lbl, desc_lbl, label, desc))

            quick_row.addWidget(card)

        main.addLayout(quick_row)

        main.addSpacing(8)

        actions = QHBoxLayout()
        actions.setSpacing(12)

        self._action_buttons: list[tuple[QPushButton, str]] = []
        for label, tab in [("Code Editor", "Code Editor"),
                           ("OJ Analysis", "OJ Analysis"),
                           ("File Import", "File Import")]:
            btn = QPushButton(tr(label))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(LINK_BTN)
            idx = TAB_NAMES.get(tab, 0)
            btn.clicked.connect(lambda checked=None, i=idx: self.tab_switch_requested.emit(i))
            actions.addWidget(btn)
            self._action_buttons.append((btn, label))

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

        activity_label = QLabel(tr("Recent Activity"))
        self._activity_title = activity_label
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
        self._stat_title_labels = getattr(self, "_stat_title_labels", {})
        self._stat_title_labels[label] = l
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
            placeholder = QLabel(tr("No activity yet - start by running some code or importing a file"))
            placeholder.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; padding: 8px 0;")
            self._activity_list.addWidget(placeholder)
            self._activity_list.addStretch()
            return

        for a in activities[:15]:
            ts = a.get("timestamp", "")[:19].replace("T", " ")
            act = tr(a.get("action", "?"))
            detail = self._translate_activity_detail(a.get("detail", ""))
            row = QLabel(f"  {ts}   {act}  -  {detail}")
            row.setStyleSheet(
                f"color: {TEXT_PRIMARY}; font-size: 11px; "
                f"padding: 3px 8px;"
            )
            self._activity_list.addWidget(row)

        if len(activities) > 15:
            more = QLabel(tr("... and {count} more", count=len(activities) - 15))
            more.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px; padding: 3px 8px;")
            self._activity_list.addWidget(more)

        self._activity_list.addStretch()

    def retranslate_ui(self):
        self._title.setText(tr("C++ Memory Visualizer"))
        self._subtitle.setText(tr("Visualize memory, learn pointers, master C++"))
        self._quick_label.setText(tr("Quick Start"))
        self._activity_title.setText(tr("Recent Activity"))
        for title_lbl, desc_lbl, title_key, desc_key in self._quick_cards:
            title_lbl.setText(tr(title_key))
            desc_lbl.setText(tr(desc_key))
        for btn, key in self._action_buttons:
            btn.setText(tr(key))
        for key, label in getattr(self, "_stat_title_labels", {}).items():
            label.setText(tr(key))
        self.refresh()

    @staticmethod
    def _translate_activity_detail(detail: str) -> str:
        if not detail:
            return detail
        matched = re.fullmatch(r"Analyzed (\d+) steps", detail)
        if matched:
            return tr("Analyzed {count} steps", count=matched.group(1))
        matched = re.fullmatch(r"Executed (\d+) steps", detail)
        if matched:
            return tr("Executed {count} steps", count=matched.group(1))
        matched = re.fullmatch(r"Extracted (\d+) KPs, (\d+) quizzes", detail)
        if matched:
            return tr("Extracted {kps} KPs, {quizzes} quizzes", kps=matched.group(1), quizzes=matched.group(2))
        return detail
