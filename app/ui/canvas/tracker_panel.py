from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.core.memory_model import MemoryState, Variable
from app.ui.theme.colors import (
    CANVAS_BG, SURFACE, BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    STACK_BORDER, HEAP_BORDER, ACCENT, EDGE_DANGLING, HIGHLIGHT, SUCCESS,
)


PANEL_BG = (
    f"background-color: {SURFACE}; border-top: 2px solid {BORDER};"
)

CHIP = (
    f"QPushButton {{ background-color: {CANVAS_BG}; color: {TEXT_PRIMARY}; "
    f"border: 1px solid {BORDER}; border-radius: 8px; "
    f"padding: 4px 12px; font-size: 12px; }}"
    f"QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}"
)
CHIP_TRACKED = (
    f"QPushButton {{ background-color: #1A3A5C; color: {STACK_BORDER}; "
    f"border: 1px solid {STACK_BORDER}; border-radius: 8px; "
    f"padding: 4px 12px; font-size: 12px; font-weight: bold; }}"
    f"QPushButton:hover {{ border-color: {TEXT_PRIMARY}; }}"
)
CHIP_PTR = (
    f"QPushButton {{ background-color: #3D2916; color: {HEAP_BORDER}; "
    f"border: 1px solid {HEAP_BORDER}; border-radius: 8px; "
    f"padding: 4px 12px; font-size: 12px; }}"
    f"QPushButton:hover {{ border-color: {ACCENT}; }}"
)
TRACK_ALL_BTN = (
    f"QPushButton {{ background-color: transparent; color: {ACCENT}; "
    f"border: 1px solid {ACCENT}; border-radius: 8px; "
    f"padding: 4px 12px; font-size: 12px; }}"
    f"QPushButton:hover {{ background-color: {ACCENT}; color: #FFFFFF; }}"
)

CARD_STYLE = (
    f"QFrame {{ background-color: {CANVAS_BG}; border: 1px solid {BORDER}; "
    f"border-radius: 8px; }}"
)
CARD_DESTROYED = (
    f"QFrame {{ background-color: {CANVAS_BG}; "
    f"border: 1px dashed {EDGE_DANGLING}; border-radius: 8px; }}"
)

HINT_COLOR = TEXT_SECONDARY
TITLE_COLOR = STACK_BORDER


class TrackerPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tracked_addresses: set[str] = set()
        self._cards: dict[str, QFrame] = {}
        self._current_state: MemoryState | None = None
        self._chip_buttons: dict[str, QPushButton] = {}
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(PANEL_BG)
        self.setMinimumHeight(150)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("Tracker")
        title.setStyleSheet(
            f"color: {TITLE_COLOR}; font-size: 12px; font-weight: bold; "
            f"background: transparent; border: none;"
        )
        header.addWidget(title)
        header.addSpacing(12)

        self._hint = QLabel("")
        self._hint.setStyleSheet(
            f"color: {HINT_COLOR}; font-size: 11px; "
            f"background: transparent; border: none;"
        )
        header.addWidget(self._hint)

        header.addStretch()

        self._track_all_btn = QPushButton("Pin All")
        self._track_all_btn.setVisible(False)
        self._track_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._track_all_btn.setStyleSheet(TRACK_ALL_BTN)
        self._track_all_btn.clicked.connect(self._on_track_all)
        header.addWidget(self._track_all_btn)

        self._clear_all_btn = QPushButton("Clear All")
        self._clear_all_btn.setVisible(False)
        self._clear_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_all_btn.setStyleSheet(TRACK_ALL_BTN)
        self._clear_all_btn.clicked.connect(self._on_clear_all)
        header.addWidget(self._clear_all_btn)

        layout.addLayout(header)

        self._chips_area = QScrollArea()
        self._chips_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._chips_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._chips_area.setFixedHeight(38)
        self._chips_area.setStyleSheet(
            f"QScrollArea {{ border: none; background: transparent; }}"
        )
        self._chips_widget = QWidget()
        self._chips_layout = QHBoxLayout(self._chips_widget)
        self._chips_layout.setContentsMargins(0, 0, 0, 0)
        self._chips_layout.setSpacing(6)
        self._chips_layout.addStretch()
        self._chips_area.setWidget(self._chips_widget)
        layout.addWidget(self._chips_area)

        self._cards_scroll = QScrollArea()
        self._cards_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._cards_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._cards_scroll.setFixedHeight(96)
        self._cards_scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background: transparent; }}"
        )
        self._cards_widget = QWidget()
        self._cards_layout = QHBoxLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(0, 4, 0, 4)
        self._cards_layout.setSpacing(8)
        self._cards_layout.addStretch()
        self._cards_scroll.setWidget(self._cards_widget)
        layout.addWidget(self._cards_scroll)

    def set_state(self, state: MemoryState):
        self._current_state = state
        self._rebuild_chips(state)
        self._refresh_cards()

    def _rebuild_chips(self, state: MemoryState):
        for _, b in self._chip_buttons.items():
            try:
                b.deleteLater()
            except Exception:
                pass
        self._chip_buttons.clear()

        all_addrs = []

        for frame in state.stack:
            for var in frame.variables:
                all_addrs.append(var.address)
                tracked = var.address in self._tracked_addresses
                prefix = "✓ " if tracked else "+ "
                text = f"{prefix}{var.name} : {var.value}"
                btn = QPushButton(text)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)

                if tracked:
                    btn.setStyleSheet(CHIP_TRACKED)
                elif var.is_pointer:
                    btn.setStyleSheet(CHIP_PTR)
                else:
                    btn.setStyleSheet(CHIP)

                addr = var.address
                btn.clicked.connect(
                    lambda checked=None, a=addr: self._toggle_track(a)
                )
                idx = self._chips_layout.count() - 1
                self._chips_layout.insertWidget(max(0, idx), btn)
                self._chip_buttons[addr] = btn

        n = len(all_addrs)
        self._hint.setText(
            f"{n} variable(s) above — click + to pin"
            if n else "Run code to see variables"
        )
        self._track_all_btn.setVisible(n > 0)
        self._clear_all_btn.setVisible(bool(self._tracked_addresses))

    def _toggle_track(self, address: str):
        if address in self._tracked_addresses:
            self._tracked_addresses.discard(address)
        else:
            self._tracked_addresses.add(address)
        # Rebuild chips to update prefix
        if self._current_state:
            self._rebuild_chips(self._current_state)
            self._refresh_cards()

    def _on_track_all(self):
        if self._current_state is None:
            return
        for frame in self._current_state.stack:
            for var in frame.variables:
                self._tracked_addresses.add(var.address)
        self._rebuild_chips(self._current_state)
        self._refresh_cards()

    def _on_clear_all(self):
        self._tracked_addresses.clear()
        if self._current_state:
            self._rebuild_chips(self._current_state)
        self._refresh_cards()

    def _refresh_cards(self):
        for addr, card in list(self._cards.items()):
            self._cards_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        if not self._tracked_addresses or self._current_state is None:
            self._clear_all_btn.setVisible(False)
            return

        self._clear_all_btn.setVisible(True)

        for address in self._tracked_addresses:
            var, frame_name = self._find_var(self._current_state, address)
            card = self._build_card(var, frame_name, address)
            idx = self._cards_layout.count() - 1
            self._cards_layout.insertWidget(max(0, idx), card)
            self._cards[address] = card

    def _find_var(self, state: MemoryState, address: str):
        for frame in state.stack:
            for var in frame.variables:
                if var.address == address:
                    return var, frame.frame_name
        return None, ""

    def _build_card(
        self, var: Variable | None, frame_name: str, address: str
    ) -> QFrame:
        card = QFrame()
        card.setFixedSize(175, 88)
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(10, 6, 10, 6)
        vbox.setSpacing(2)

        if var is None:
            card.setStyleSheet(CARD_DESTROYED)

            name_text = self._addr_name(address)
            nl = QLabel(name_text)
            nl.setStyleSheet(
                f"color: {EDGE_DANGLING}; font-size: 12px; font-weight: bold;"
            )
            vbox.addWidget(nl)

            dl = QLabel("out of scope")
            dl.setStyleSheet(f"color: {EDGE_DANGLING}; font-size: 10px;")
            vbox.addWidget(dl)

            close = self._make_close_btn(address, card)
            close.move(card.width() - 22, 4)
            return card

        card.setStyleSheet(CARD_STYLE)

        nl = QLabel(var.name)
        nl.setStyleSheet(
            f"color: {STACK_BORDER}; font-size: 13px; font-weight: bold;"
        )
        vbox.addWidget(nl)

        il = QLabel(f"{var.type}  =  {var.value}")
        il.setFont(QFont("JetBrains Mono", 10))
        il.setStyleSheet(f"color: {TEXT_PRIMARY};")
        vbox.addWidget(il)

        sl = QLabel(f"scope: {frame_name}  [{var.address}]")
        sl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 9px;")
        vbox.addWidget(sl)

        close = self._make_close_btn(address, card)
        close.move(card.width() - 22, 4)

        return card

    def _make_close_btn(self, address: str, parent: QFrame) -> QPushButton:
        btn = QPushButton("✕", parent)
        btn.setFixedSize(18, 18)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {TEXT_SECONDARY}; "
            f"border: none; font-size: 10px; }}"
            f"QPushButton:hover {{ color: {EDGE_DANGLING}; }}"
        )
        btn.clicked.connect(
            lambda checked=None, a=address: self._toggle_track(a)
        )
        return btn

    def _addr_name(self, address: str) -> str:
        if self._current_state:
            var, _ = self._find_var(self._current_state, address)
            if var:
                return var.name
        return address
