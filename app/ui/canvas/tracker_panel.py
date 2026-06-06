from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton,
)
from PySide6.QtCore import Qt, QTimer, QMimeData, QPoint
from PySide6.QtGui import QFont, QColor, QDrag

from app.core.memory_model import MemoryState, Variable
from app.services.i18n import tr
from app.ui.widgets.helpers import clear_layout
from app.ui.theme.colors import (
    CANVAS_BG, SURFACE, BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    STACK_BORDER, HEAP_BORDER, ACCENT, EDGE_DANGLING, HIGHLIGHT,
    STACK_BG, HEAP_BG, HIGHLIGHT_BG, TEXT_INVERSE, TEXT_BUTTON_PRIMARY,
)


PANEL_BG = (
    f"background-color: {SURFACE}; border-top: 2px solid {STACK_BORDER};"
)

CHIP = (
    f"QPushButton {{ background-color: {CANVAS_BG}; color: {TEXT_PRIMARY}; "
    f"border: 2px solid {BORDER}; "
    f"padding: 5px 16px; font-size: 13px; font-weight: 500; }}"
    f"QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}"
)
CHIP_TRACKED = (
    f"QPushButton {{ background-color: {STACK_BG}; color: {STACK_BORDER}; "
    f"border: 2px solid {STACK_BORDER}; "
    f"padding: 5px 16px; font-size: 13px; font-weight: bold; }}"
    f"QPushButton:hover {{ border-color: {ACCENT}; }}"
)
CHIP_PTR = (
    f"QPushButton {{ background-color: {HEAP_BG}; color: {HEAP_BORDER}; "
    f"border: 2px solid {HEAP_BORDER}; "
    f"padding: 5px 16px; font-size: 13px; }}"
    f"QPushButton:hover {{ border-color: {ACCENT}; }}"
)
TRACK_ALL_BTN = (
    f"QPushButton {{ background-color: transparent; color: {ACCENT}; "
    f"border: 2px solid {ACCENT}; "
    f"padding: 5px 12px; font-size: 14px; font-weight: 600; }}"
    f"QPushButton:hover {{ background-color: {ACCENT}; color: {TEXT_BUTTON_PRIMARY}; }}"
)
CARD_STYLE = (
    f"QFrame#trackCard {{ background-color: {STACK_BG}; border: 2px solid {STACK_BORDER}; "
    f"}}"
    f"QFrame#trackCard QLabel {{ border: none; background: transparent; outline: none; }}"
)
CARD_DESTROYED = (
    f"QFrame#trackCardDestroyed {{ background-color: {CANVAS_BG}; "
    f"border: 1px dashed {EDGE_DANGLING}; }}"
    f"QFrame#trackCardDestroyed QLabel {{ border: none; background: transparent; outline: none; }}"
)


class DragChipButton(QPushButton):
    def __init__(self, text: str, address: str, parent=None):
        super().__init__(text, parent)
        self._address = address
        self._drag_start: QPoint | None = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start is None:
            super().mouseMoveEvent(event)
            return
        if (event.position().toPoint() - self._drag_start).manhattanLength() < 10:
            return
        mime = QMimeData()
        mime.setText(self._address)
        drag = QDrag(self)
        drag.setMimeData(mime)
        self._drag_start = None
        drag.exec(Qt.DropAction.CopyAction)


class TrackerPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tracked_addresses: set[str] = set()
        self._cards: dict[str, QFrame] = {}
        self._prev_values: dict[str, str] = {}
        self._current_state: MemoryState | None = None
        self._chip_buttons: dict[str, QPushButton] = {}
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(PANEL_BG)
        self.setMinimumHeight(220)
        self.setSizePolicy(
            self.sizePolicy().horizontalPolicy(),
            self.sizePolicy().verticalPolicy(),
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 6)
        layout.setSpacing(4)

        header = QHBoxLayout()
        title = QLabel()
        self._title = title
        title.setStyleSheet(
            f"color: {STACK_BORDER}; font-size: 14px; font-weight: bold; "
            f"background: transparent; border: none;"
        )
        header.addWidget(title)

        self._hint = QLabel(tr("Run code to see variables"))
        self._hint.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: 600; "
            f"background: transparent; border: none;"
        )
        header.addWidget(self._hint)
        header.addStretch()

        self._track_all_btn = QPushButton(tr("Pin All"))
        self._track_all_btn.setVisible(False)
        self._track_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._track_all_btn.setStyleSheet(TRACK_ALL_BTN)
        self._track_all_btn.clicked.connect(self._on_track_all)
        header.addWidget(self._track_all_btn)

        self._clear_all_btn = QPushButton(tr("Clear All"))
        self._clear_all_btn.setVisible(False)
        self._clear_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_all_btn.setStyleSheet(TRACK_ALL_BTN)
        self._clear_all_btn.clicked.connect(self._on_clear_all)
        header.addWidget(self._clear_all_btn)

        layout.addLayout(header)

        self._chips_widget = QWidget()
        self._chips_layout = QHBoxLayout(self._chips_widget)
        self._chips_layout.setContentsMargins(0, 0, 0, 4)
        self._chips_layout.setSpacing(8)
        layout.addWidget(self._chips_widget, 0)

        self._cards_widget = QWidget()
        self._cards_layout = QHBoxLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(10)
        self._cards_layout.addStretch()
        layout.addWidget(self._cards_widget, 1)

    def set_state(self, state: MemoryState):
        self._current_state = state
        self._rebuild_chips(state)
        self._refresh_cards()

    def clear(self):
        self._current_state = None
        self._tracked_addresses.clear()
        self._prev_values.clear()
        self._rebuild_chips(None)
        self._refresh_cards()

    def _rebuild_chips(self, state: MemoryState | None):
        clear_layout(self._chips_layout)
        self._chip_buttons.clear()

        if state is None:
            self._hint.setText(tr("Run code to see variables"))
            self._track_all_btn.setVisible(False)
            self._clear_all_btn.setVisible(False)
            self._chips_layout.addStretch()
            return

        all_addrs = []
        for frame in state.stack:
            for var in frame.variables:
                all_addrs.append(var.address)
                tracked = var.address in self._tracked_addresses
                prefix = "✓ " if tracked else "+ "
                text = f"{prefix}{var.name} = {var.value}"
                btn = DragChipButton(text, var.address)
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
                self._chips_layout.addWidget(btn)
                self._chip_buttons[addr] = btn

        self._chips_layout.addStretch()

        n = len(all_addrs)
        self._hint.setText(
            tr("{count} variable(s) - click + to pin", count=n)
            if n else tr("Run code to see variables")
        )
        self._track_all_btn.setVisible(n > 0)
        self._clear_all_btn.setVisible(bool(self._tracked_addresses))

    def _toggle_track(self, address: str):
        if address in self._tracked_addresses:
            self._tracked_addresses.discard(address)
        else:
            self._tracked_addresses.add(address)
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
        self._prev_values.clear()
        if self._current_state:
            self._rebuild_chips(self._current_state)
        self._refresh_cards()

    def _refresh_cards(self):
        current = set(self._tracked_addresses)

        for addr in list(self._cards):
            if addr not in current:
                card = self._cards.pop(addr)
                self._prev_values.pop(addr, None)
                self._cards_layout.removeWidget(card)
                card.deleteLater()

        if self._current_state is None:
            self._clear_all_btn.setVisible(False)
            return

        for addr in current:
            var, frame_name = self._find_var(self._current_state, addr)
            old_val = self._prev_values.get(addr)
            new_val = var.value if var else None

            if addr in self._cards:
                self._update_card(addr, var, frame_name, old_val, new_val)
            else:
                card = self._build_card(var, frame_name, addr)
                idx = self._cards_layout.count()
                self._cards_layout.insertWidget(max(0, idx - 1), card)
                self._cards[addr] = card

            if var:
                self._prev_values[addr] = new_val

        self._clear_all_btn.setVisible(bool(self._tracked_addresses))

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
        card.setFixedWidth(220)
        card.setMinimumHeight(82)
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(10, 8, 10, 6)
        vbox.setSpacing(2)

        if var is None:
            card.setObjectName("trackCardDestroyed")
            card.setStyleSheet(CARD_DESTROYED)
            nl = QLabel(self._addr_name(address))
            nl.setStyleSheet(
                f"color: {EDGE_DANGLING}; font-size: 14px; font-weight: bold;"
            )
            vbox.addWidget(nl)
            dl = QLabel(tr("out of scope"))
            dl.setStyleSheet(f"color: {EDGE_DANGLING}; font-size: 12px; font-weight: 600;")
            vbox.addWidget(dl)
            return card

        card.setObjectName("trackCard")
        card.setStyleSheet(CARD_STYLE)

        nl = QLabel(var.name)
        nl.setStyleSheet(
            f"color: {STACK_BORDER}; font-size: 13px; font-weight: bold;"
        )
        vbox.addWidget(nl)

        il = QLabel(f"{var.type}  =  {var.value}")
        il.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 12))
        il.setWordWrap(True)
        il.setStyleSheet(f"color: {TEXT_PRIMARY};")
        vbox.addWidget(il)
        il.setObjectName("value_label")

        sl = QLabel(tr("scope: {frame}  [{address}]", frame=frame_name, address=var.address))
        sl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; font-weight: 600;")
        sl.setObjectName("scope_label")
        vbox.addWidget(sl)

        return card

    def _update_card(self, addr: str, var, frame_name: str,
                     old_val: str | None, new_val: str | None):
        card = self._cards.get(addr)
        if card is None:
            return

        if var is None:
            card.setObjectName("trackCardDestroyed")
            card.setStyleSheet(CARD_DESTROYED)
            value_label = card.findChild(QLabel, "value_label")
            if value_label:
                value_label.setText(tr("out of scope"))
                value_label.setStyleSheet(
                    f"color: {EDGE_DANGLING}; font-size: 12px; font-weight: 600;"
                )
            return

        card.setObjectName("trackCard")
        card.setStyleSheet(CARD_STYLE)
        value_label = card.findChild(QLabel, "value_label")
        if value_label is None:
            return

        changed = old_val is not None and new_val is not None and old_val != new_val
        if changed:
            value_label.setText(f"{var.type}  =  {old_val} → {new_val}")
            value_label.setStyleSheet(
                f"color: {HIGHLIGHT}; font-weight: bold;"
            )
            card.setStyleSheet(
                f"QFrame#trackCard {{ background-color: {HIGHLIGHT_BG}; "
                f"border: 2px solid {HIGHLIGHT}; }}"
                f"QFrame#trackCard QLabel {{ border: none; background: transparent; outline: none; }}"
            )

            def restore(addr=addr, lbl=value_label, card=card):
                if self._cards.get(addr) is not card:
                    return
                if self._current_state is not None:
                    v, _ = self._find_var(self._current_state, addr)
                    if v:
                        lbl.setText(f"{v.type}  =  {v.value}")
                lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
                card.setObjectName("trackCard")
                card.setStyleSheet(CARD_STYLE)

            QTimer.singleShot(1200, restore)
        else:
            value_label.setText(f"{var.type}  =  {new_val or ''}")
            value_label.setStyleSheet(f"color: {TEXT_PRIMARY};")
        scope_label = card.findChild(QLabel, "scope_label")
        if scope_label is not None:
            scope_label.setText(tr("scope: {frame}  [{address}]", frame=frame_name, address=var.address))

    def _addr_name(self, address: str) -> str:
        if self._current_state:
            v, _ = self._find_var(self._current_state, address)
            if v:
                return v.name
        return address

    def retranslate_ui(self):
        self._title.setText(f" {tr('Tracker')}")
        self._track_all_btn.setText(tr("Pin All"))
        self._clear_all_btn.setText(tr("Clear All"))
        if self._current_state is None:
            self._hint.setText(tr("Run code to see variables"))
        else:
            self._rebuild_chips(self._current_state)
            self._refresh_cards()
