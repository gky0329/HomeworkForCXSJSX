import re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGridLayout,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap

from app.services import error_store
from app.services.i18n import tr
from app.ui.widgets.helpers import clear_layout
from app.ui.theme.minecraft_assets import asset_path
from app.ui.theme.colors import (
    CANVAS_BG, SURFACE, BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    STACK_BORDER, ACCENT, SUCCESS, SURFACE_HOVER, use_minecraft_assets,
)


HEADLINE = f"color: {TEXT_PRIMARY}; font-size: 32px; font-weight: 800; padding: 6px 0;"
SUBTITLE = f"color: {TEXT_SECONDARY}; font-size: 15px; font-weight: 600; padding: 2px 0;"
STAT_NUM = f"color: {STACK_BORDER}; font-size: 36px; font-weight: 800;"
STAT_LABEL = f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: 600;"
LINK_BTN = (
    f"QPushButton {{ background-color: {SURFACE}; color: {ACCENT}; "
    f"border: 2px solid {BORDER}; "
    f"padding: 14px 24px; font-size: 16px; font-weight: 700; text-align: left; }}"
    f"QPushButton:hover {{ border-color: {ACCENT}; background-color: {SURFACE_HOVER}; color: {STACK_BORDER}; }}"
)

CARD_BG = (
    f"QFrame#statCard {{ background-color: {SURFACE}; border: 2px solid {BORDER}; }}"
    f"QFrame#statCard:hover {{ border-color: {STACK_BORDER}; }}"
    f"QFrame#statCard QLabel {{ border: none; background: transparent; outline: none; }}"
)
ELEMENT_CARD_BG = (
    f"QFrame#elementCard {{ background-color: {SURFACE}; border: 2px solid {BORDER}; padding: 12px; }}"
    f"QFrame#elementCard:hover {{ border-color: {SUCCESS}; background-color: {SURFACE_HOVER}; }}"
    f"QFrame#elementCard QLabel {{ border: none; background: transparent; outline: none; }}"
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
        self._use_theme_assets = use_minecraft_assets()
        self._setup_ui()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        main = QVBoxLayout(content)
        main.setContentsMargins(24, 20, 24, 20)
        main.setSpacing(16)

        title = QLabel(tr("C++rafting Table"))
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
            f"color: {STACK_BORDER}; font-size: 18px; font-weight: bold; padding: 4px 0;"
        )
        main.addWidget(quick_label)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(10)

        self._quick_cards: list[tuple[QLabel, QLabel, str, str]] = []
        for number, (label, tab, desc, icon_name) in enumerate([
            ("Write Code", "Code Editor", "Run C++ code and watch\nmemory state step by step", "nav_code"),
            ("Import & Learn", "File Import", "Upload PDF/DOCX/CPP files\nand extract knowledge points", "nav_file"),
            ("Review Mistakes", "Review", "Practice with spaced repetition\nto master C++ concepts", "empty_chest"),
        ], start=1):
            card = QFrame()
            card.setObjectName("quickCard")
            card.setStyleSheet(
                f"QFrame#quickCard {{ background-color: {SURFACE}; border: 2px solid {BORDER}; "
                f"padding: 10px 14px; }}"
                f"QFrame#quickCard:hover {{ border-color: {ACCENT}; background-color: {SURFACE_HOVER}; }}"
                f"QFrame#quickCard QLabel {{ border: none; background: transparent; outline: none; }}"
            )
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            idx = TAB_NAMES.get(tab, 0)
            card.mousePressEvent = lambda e, i=idx: self.tab_switch_requested.emit(i)

            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(10)

            if self._use_theme_assets:
                icon = QLabel()
                icon.setPixmap(QPixmap(asset_path("icons", icon_name)).scaled(
                    38, 38, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation,
                ))
                card_layout.addWidget(icon)
            else:
                index_label = QLabel(f"{number:02d}")
                index_label.setFixedWidth(44)
                index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                index_label.setStyleSheet(
                    f"color: {ACCENT}; font-size: 20px; font-weight: 900; "
                    f"border-right: 1px solid {BORDER}; padding-right: 10px;"
                )
                card_layout.addWidget(index_label)

            text_box = QVBoxLayout()
            text_box.setSpacing(2)

            title_lbl = QLabel(tr(label))
            title_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 17px; font-weight: 700;")
            text_box.addWidget(title_lbl)

            desc_lbl = QLabel(tr(desc))
            desc_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: 600;")
            text_box.addWidget(desc_lbl)
            card_layout.addLayout(text_box)
            card_layout.addStretch()

            arrow = QLabel()
            if self._use_theme_assets:
                arrow.setPixmap(QPixmap(asset_path("icons", "item_arrow")).scaled(
                    24, 24, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation,
                ))
            else:
                arrow.setText("->")
                arrow.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 16px; font-weight: 800;")
            card_layout.addWidget(arrow)
            self._quick_cards.append((title_lbl, desc_lbl, label, desc))

            quick_row.addWidget(card)

        main.addLayout(quick_row)

        main.addSpacing(8)

        element_label = QLabel(tr("C++ Workbench Elements"))
        self._element_label = element_label
        element_label.setStyleSheet(
            f"color: {STACK_BORDER}; font-size: 18px; font-weight: bold; padding: 4px 0;"
        )
        main.addWidget(element_label)

        elements_grid = QGridLayout()
        elements_grid.setSpacing(10)
        self._element_cards: list[tuple[QLabel, QLabel, str, str]] = []
        for index, (label, desc, icon_name) in enumerate([
            (
                "Code Forge",
                "Write, run, and step through C++ snippets",
                "nav_code",
            ),
            (
                "Memory Canvas",
                "Stack, heap, pointer, object and vtable relationships on one canvas",
                "action_search",
            ),
            (
                "OJ Analyzer",
                "Turn problem statements and code into guided explanations",
                "nav_oj",
            ),
            (
                "Knowledge Loop",
                "Import course files, build a graph, and review mistakes",
                "nav_knowledge",
            ),
        ]):
            elements_grid.addWidget(
                self._element_card(label, desc, icon_name, index + 1),
                index // 2,
                index % 2,
            )
        main.addLayout(elements_grid)

        main.addSpacing(8)

        actions = QHBoxLayout()
        actions.setSpacing(12)

        self._action_buttons: list[tuple[QPushButton, str]] = []
        for label, tab, icon_name in [
            ("Code Editor", "Code Editor", "nav_code"),
            ("OJ Analysis", "OJ Analysis", "nav_oj"),
            ("File Import", "File Import", "nav_file"),
        ]:
            btn = QPushButton(tr(label))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if self._use_theme_assets:
                btn.setIcon(QIcon(asset_path("icons", icon_name)))
            idx = TAB_NAMES.get(tab, 0)
            btn.clicked.connect(lambda checked=None, i=idx: self.tab_switch_requested.emit(i))
            actions.addWidget(btn)
            self._action_buttons.append((btn, label))

        main.addLayout(actions)

        main.addSpacing(8)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        self._error_card = self._stat_card("0", "Pending Review", "Review", "empty_chest")
        self._kp_card = self._stat_card("0", "Knowledge Points", "Knowledge Base", "nav_knowledge")
        self._act_card = self._stat_card("0", "Recent Activities", None, "block_grass")

        stats_row.addWidget(self._error_card)
        stats_row.addWidget(self._kp_card)
        stats_row.addWidget(self._act_card)
        main.addLayout(stats_row)

        main.addSpacing(4)

        activity_label = QLabel(tr("Recent Activity"))
        self._activity_title = activity_label
        activity_label.setStyleSheet(
            f"color: {STACK_BORDER}; font-size: 18px; font-weight: bold; padding: 4px 0;"
        )
        main.addWidget(activity_label)

        self._activity_list = QVBoxLayout()
        main.addLayout(self._activity_list)

        main.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _stat_card(self, num: str, label: str, tab_name: str | None, icon_name: str) -> QFrame:
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

        if self._use_theme_assets:
            icon = QLabel()
            icon.setPixmap(QPixmap(asset_path("icons", icon_name)).scaled(
                42, 42, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            ))
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(icon)

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

    def _element_card(self, title_key: str, desc_key: str, icon_name: str, number: int) -> QFrame:
        card = QFrame()
        card.setObjectName("elementCard")
        card.setStyleSheet(ELEMENT_CARD_BG)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        if self._use_theme_assets:
            icon = QLabel()
            icon.setFixedSize(46, 46)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setPixmap(QPixmap(asset_path("icons", icon_name)).scaled(
                40, 40, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            ))
            layout.addWidget(icon, 0)
        else:
            index_label = QLabel(f"{number:02d}")
            index_label.setFixedSize(48, 48)
            index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            index_label.setStyleSheet(
                f"color: {ACCENT}; font-size: 18px; font-weight: 900; "
                f"border: 1px solid {BORDER};"
            )
            layout.addWidget(index_label, 0)

        text_box = QVBoxLayout()
        text_box.setSpacing(3)

        title = QLabel(tr(title_key))
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 16px; font-weight: 800;")
        text_box.addWidget(title)

        desc = QLabel(tr(desc_key))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: 600;")
        text_box.addWidget(desc)

        layout.addLayout(text_box, 1)
        self._element_cards.append((title, desc, title_key, desc_key))
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
            placeholder.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: 600; padding: 8px 0;")
            self._activity_list.addWidget(placeholder)
            self._activity_list.addStretch()
            return

        for a in activities[:15]:
            ts = a.get("timestamp", "")[:19].replace("T", " ")
            act = tr(a.get("action", "?"))
            detail = self._translate_activity_detail(a.get("detail", ""))
            row_frame = QFrame()
            row_frame.setProperty("panel", "card")
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(8, 4, 8, 4)
            row_layout.setSpacing(8)
            if self._use_theme_assets:
                icon = QLabel()
                icon.setPixmap(QPixmap(asset_path("icons", "block_grass")).scaled(
                    18, 18, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation,
                ))
                row_layout.addWidget(icon)
            else:
                marker = QLabel("|")
                marker.setStyleSheet(f"color: {ACCENT}; font-size: 14px; font-weight: 900;")
                row_layout.addWidget(marker)
            row = QLabel(f"{ts}   {act}  -  {detail}")
            row.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 600;")
            row_layout.addWidget(row)
            row_layout.addStretch()
            self._activity_list.addWidget(row_frame)

        if len(activities) > 15:
            more = QLabel(tr("... and {count} more", count=len(activities) - 15))
            more.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; font-weight: 600; padding: 3px 8px;")
            self._activity_list.addWidget(more)

        self._activity_list.addStretch()

    def retranslate_ui(self):
        self._title.setText(tr("C++rafting Table"))
        self._subtitle.setText(tr("Visualize memory, learn pointers, master C++"))
        self._quick_label.setText(tr("Quick Start"))
        self._element_label.setText(tr("C++ Workbench Elements"))
        self._activity_title.setText(tr("Recent Activity"))
        for title_lbl, desc_lbl, title_key, desc_key in self._quick_cards:
            title_lbl.setText(tr(title_key))
            desc_lbl.setText(tr(desc_key))
        for title_lbl, desc_lbl, title_key, desc_key in self._element_cards:
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
