from dataclasses import dataclass
from collections.abc import Callable, Iterable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut


@dataclass(frozen=True)
class ShortcutBinding:
    sequence: str
    name: str
    description: str
    callback: Callable[[], None]
    context: Qt.ShortcutContext = Qt.ShortcutContext.WidgetWithChildrenShortcut


class ShortcutRegistry:
    def __init__(self, parent):
        self._parent = parent
        self._shortcuts: list[QShortcut] = []
        self._bindings: list[ShortcutBinding] = []

    def register(self, binding: ShortcutBinding) -> QShortcut:
        shortcut = QShortcut(QKeySequence(binding.sequence), self._parent)
        shortcut.setContext(binding.context)
        shortcut.setAutoRepeat(False)
        shortcut.activated.connect(binding.callback)
        self._shortcuts.append(shortcut)
        self._bindings.append(binding)
        return shortcut

    def register_many(self, bindings: Iterable[ShortcutBinding]):
        for binding in bindings:
            self.register(binding)

    def clear(self):
        for shortcut in self._shortcuts:
            shortcut.deleteLater()
        self._shortcuts.clear()
        self._bindings.clear()

    @property
    def bindings(self) -> tuple[ShortcutBinding, ...]:
        return tuple(self._bindings)