from enum import Enum, auto

from PySide6.QtCore import QObject, Signal


class AppPage(Enum):
    SPLASH = auto()
    MAIN_MENU = auto()
    WORLD_SELECT = auto()
    CREATE_WORLD = auto()
    CREATING_WORLD = auto()
    LESSON_INTRO = auto()
    QUIZ = auto()
    RESULT = auto()


_TRANSITIONS: dict[AppPage, set[AppPage]] = {
    AppPage.SPLASH:         {AppPage.MAIN_MENU},
    AppPage.MAIN_MENU:      {AppPage.WORLD_SELECT},
    AppPage.WORLD_SELECT:   {AppPage.MAIN_MENU, AppPage.CREATE_WORLD, AppPage.CREATING_WORLD},
    AppPage.CREATE_WORLD:   {AppPage.WORLD_SELECT, AppPage.CREATING_WORLD},
    AppPage.CREATING_WORLD: {AppPage.LESSON_INTRO, AppPage.WORLD_SELECT},
    AppPage.LESSON_INTRO:   {AppPage.QUIZ, AppPage.WORLD_SELECT},
    AppPage.QUIZ:           {AppPage.RESULT},
    AppPage.RESULT:         {AppPage.WORLD_SELECT, AppPage.QUIZ},
}


class NavigationManager(QObject):
    page_changed = Signal(AppPage, object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._current = AppPage.SPLASH
        self._history: list[AppPage] = []

    @property
    def current_page(self) -> AppPage:
        return self._current

    def navigate_to(self, target: AppPage, payload: object = None) -> None:
        allowed = _TRANSITIONS.get(self._current, set())
        if target not in allowed:
            raise ValueError(f"非法跳转: {self._current.name} -> {target.name}")
        self._history.append(self._current)
        self._current = target
        self.page_changed.emit(target, payload)

    def go_back(self) -> AppPage | None:
        if not self._history:
            return None
        prev = self._history.pop()
        self._current = prev
        self.page_changed.emit(prev, None)
        return prev
