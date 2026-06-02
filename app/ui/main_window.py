import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
from collections.abc import Callable

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QPlainTextEdit, QGraphicsView,
    QGraphicsScene, QToolBar, QStatusBar, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMenu, QTabWidget, QCheckBox, QComboBox, QSlider,
)
from PySide6.QtCore import Qt, Signal, QEvent, QPointF, QRectF, QTimer
from PySide6.QtGui import QFont, QColor, QPainter, QWheelEvent, QAction, QMouseEvent

from app.ui.theme.colors import CANVAS_BG, TEXT_SECONDARY, TEXT_PRIMARY, ACCENT, ACCENT_HOVER, ACCENT_PRESSED, BORDER, SURFACE, EDITOR_BG, HIGHLIGHT, TEXT_PRIMARY, ACCENT
from app.ui.pages.file_import_page import FileImportPage
from app.ui.pages.oj_page import OJPage
from app.ui.pages.review_page import ReviewPage
from app.ui.pages.home_page import HomePage
from app.ui.pages.knowledge_page import KnowledgePage
from app.ui.canvas.tracker_panel import TrackerPanel
from app.ui.shortcut_registry import ShortcutBinding, ShortcutRegistry
from app.services.i18n import load_language, tr


ZOOM_FACTOR = 1.15
ZOOM_MIN = 0.1
ZOOM_MAX = 10.0
ZOOM_BTN_STYLE = (
    f"QPushButton {{ background-color: {ACCENT}; color: #FFFFFF; border: none; "
    "border-radius: 5px; "
    "padding: 2px 4px; font-size: 16px; font-weight: bold; "
    "min-height: 24px; min-width: 28px; } "
    f"QPushButton:hover {{ background-color: {ACCENT_HOVER}; }} "
    f"QPushButton:pressed {{ background-color: {ACCENT_PRESSED}; }}"
)

SCENE_W = 1600
SCENE_H = 2000

TAB_STYLE = (
    "QTabWidget::pane { border: none; background: #1E1E1E; }"
    f"QTabBar::tab {{ background: #2D2D2D; color: {TEXT_SECONDARY}; padding: 8px 24px; "
    f"border: none; border-bottom: 2px solid transparent; font-size: 13px; }}"
    f"QTabBar::tab:selected {{ color: {TEXT_PRIMARY}; border-bottom: 2px solid {ACCENT}; }}"
    f"QTabBar::tab:hover {{ color: {TEXT_PRIMARY}; }}"
)

EXAMPLE_CODES = {
    "Basic Variables": (
        "int a = 42;\n"
        "int b = a + 10;\n"
        "double pi = 3.14;\n"
    ),
    "Pointers": (
        "int a = 42;\n"
        "int* p = new int(100);\n"
        "int* q = &a;\n"
        "*p = 200;\n"
        "delete p;\n"
    ),
    "Arrays": (
        "int arr[3] = {10, 20, 30};\n"
        "int* heap_arr = new int[3]{1, 2, 3};\n"
        "arr[1] = 99;\n"
        "delete[] heap_arr;\n"
    ),
    "Class & Destructor": (
        "class Point {\n"
        "public:\n"
        "  int x, y;\n"
        "  Point(int _x, int _y) : x(_x), y(_y) {}\n"
        "  ~Point() { x = 0; y = 0; }\n"
        "};\n"
        "Point* pt = new Point(3, 4);\n"
        "pt->x = 10;\n"
        "delete pt;\n"
    ),
    "Inheritance": (
        "class Animal {\n"
        "public:\n"
        "  virtual void speak() {}\n"
        "};\n"
        "class Dog : public Animal {\n"
        "public:\n"
        "  void speak() override {}\n"
        "};\n"
        "Animal* a = new Dog();\n"
        "delete a;\n"
    ),
}


class CanvasView(QGraphicsView):
    variable_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom_level = 1.0
        self._panning = False
        self._pan_last_pos = QPointF()
        self.setAcceptDrops(True)
        self.setSceneRect(0, 0, SCENE_W, SCENE_H)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, False)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta == 0:
                event.accept()
                return
            factor = ZOOM_FACTOR if delta > 0 else 1 / ZOOM_FACTOR
            new_zoom = self._zoom_level * factor
            if ZOOM_MIN <= new_zoom <= ZOOM_MAX:
                self._zoom_level = new_zoom
                self.scale(factor, factor)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_last_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._panning:
            delta = event.position() - self._pan_last_pos
            self._pan_last_pos = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton and self._panning:
            self._panning = False
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            address = event.mimeData().text()
            self.variable_dropped.emit(address)
            event.acceptProposedAction()
        else:
            event.ignore()

    def zoom_in(self):
        if self._zoom_level * ZOOM_FACTOR <= ZOOM_MAX:
            self._zoom_level *= ZOOM_FACTOR
            self.scale(ZOOM_FACTOR, ZOOM_FACTOR)

    def zoom_out(self):
        if self._zoom_level / ZOOM_FACTOR >= ZOOM_MIN:
            self._zoom_level /= ZOOM_FACTOR
            self.scale(1 / ZOOM_FACTOR, 1 / ZOOM_FACTOR)

    def zoom_fit(self):
        fit_rect = self._fit_bounds()
        if not fit_rect.isValid() or fit_rect.isEmpty():
            return
        self.fitInView(fit_rect, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom_level = self.transform().m11()

    def _fit_bounds(self):
        scene = self.scene()
        if scene is None:
            return QRectF()

        scene_rect = scene.sceneRect()
        bounds = QRectF()

        for item in scene.items():
            if item.parentItem() is not None or not item.isVisible():
                continue

            visual_bounds = getattr(item, "visual_bounds", None)
            if callable(visual_bounds):
                item_bounds = item.mapRectToScene(visual_bounds())
            else:
                item_bounds = item.sceneBoundingRect()

            item_bounds = item_bounds.intersected(scene_rect)
            if item_bounds.isEmpty():
                continue

            bounds = item_bounds if bounds.isNull() else bounds.united(item_bounds)

        return bounds.adjusted(-24.0, -24.0, 24.0, 24.0)

    def reset_view(self):
        self.resetTransform()
        self._zoom_level = 1.0


class MainWindow(QMainWindow):

    def __init__(self, config_path: Path | None = None):
        super().__init__()
        self._config_path = config_path
        load_language(config_path)
        self._global_shortcuts: ShortcutRegistry | None = None
        self._code_shortcuts: ShortcutRegistry | None = None
        self._code_key_actions: dict[int, Callable[[], None]] = {}
        self._load_start_time: float = 0.0
        self._elapsed_timer: QTimer | None = None
        self.setWindowTitle(tr("C++ Memory Visualizer"))
        self.setMinimumSize(1200, 700)
        self._setup_ui()
        self._setup_toolbar()
        self._setup_menubar()
        self._setup_shortcuts()
        self._setup_statusbar()
        self._setup_overlay()
        self._retranslate_ui()

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def _setup_ui(self):
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(TAB_STYLE)

        self._home_tab = self._build_home_tab()
        self._code_tab = self._build_code_tab()
        self._file_tab = self._build_file_tab()
        self._oj_tab = self._build_oj_tab()
        self._review_tab = self._build_review_tab()
        self._kb_tab = self._build_kb_tab()

        self._tabs.addTab(self._home_tab, tr("Home"))
        self._tabs.addTab(self._code_tab, tr("Code Editor"))
        self._tabs.addTab(self._oj_tab, tr("OJ Analysis"))
        self._tabs.addTab(self._file_tab, tr("File Import"))
        self._tabs.addTab(self._review_tab, tr("Review"))
        self._tabs.addTab(self._kb_tab, tr("Knowledge Base"))
        self._review_tab_index = self._tabs.indexOf(self._review_tab)
        self._home_tab_index = self._tabs.indexOf(self._home_tab)
        self._tabs.currentChanged.connect(self._on_tab_changed)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tabs)
        self.setCentralWidget(central)

    def _build_home_tab(self) -> QWidget:
        self.home_page = HomePage()
        self.home_page.tab_switch_requested.connect(self._tabs.setCurrentIndex)
        return self.home_page

    def _build_code_tab(self) -> QWidget:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        self.code_editor = QPlainTextEdit()
        self.code_editor.setPlainText(EXAMPLE_CODES["Pointers"])
        font_size = self._read_config_font_size()
        self.code_editor.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", font_size))
        self.code_editor.setPlaceholderText(tr("// Enter C++ code here..."))

        self.canvas_view = CanvasView()
        self.canvas_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.canvas_scene = QGraphicsScene()
        self.canvas_scene.setBackgroundBrush(QColor(CANVAS_BG))
        self.canvas_scene.setSceneRect(0, 0, SCENE_W, SCENE_H)
        self.canvas_view.setScene(self.canvas_scene)

        right_pane = QWidget()
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        right_layout.addWidget(self.canvas_view, 1)

        step_bar = QHBoxLayout()
        step_bar.setContentsMargins(8, 4, 8, 4)
        step_bar.setSpacing(8)

        self.btn_prev_big = QPushButton()
        self.btn_prev_big.setStyleSheet(
            f"QPushButton {{ background-color: {ACCENT}; color: #FFFFFF; border: none; "
            f"border-radius: 5px; padding: 6px 16px; font-size: 13px; font-weight: bold; }} "
            f"QPushButton:hover {{ background-color: {ACCENT_HOVER}; }} "
            f"QPushButton:disabled {{ background-color: {BORDER}; color: {TEXT_SECONDARY}; }}"
        )
        self.btn_prev_big.setEnabled(False)
        step_bar.addWidget(self.btn_prev_big)

        self.btn_next_big = QPushButton()
        self.btn_next_big.setStyleSheet(self.btn_prev_big.styleSheet())
        self.btn_next_big.setEnabled(False)
        step_bar.addWidget(self.btn_next_big)

        self.btn_autoplay = QPushButton(tr("Auto Play"))
        self.btn_autoplay.setCheckable(True)
        self.btn_autoplay.setEnabled(False)
        self.btn_autoplay.setToolTip(tr("Auto-advance through steps"))
        step_bar.addWidget(self.btn_autoplay)

        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(200, 2000)
        self._speed_slider.setValue(800)
        self._speed_slider.setFixedWidth(80)
        self._speed_slider.setToolTip(tr("Auto-play speed (200ms fast - 2000ms slow)"))
        step_bar.addWidget(self._speed_slider)

        speed_label = QLabel(tr("speed"))
        self._speed_label = speed_label
        speed_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px;")
        step_bar.addWidget(speed_label)

        step_bar.addStretch()

        right_layout.addLayout(step_bar, 0)

        splitter.addWidget(self.code_editor)
        splitter.addWidget(right_pane)
        splitter.setSizes([500, 700])
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        self.tracker_panel = TrackerPanel()
        self.canvas_view.variable_dropped.connect(self.tracker_panel._toggle_track)

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(splitter, 1)
        layout.addWidget(self.tracker_panel, 0)
        return tab

    def _build_file_tab(self) -> QWidget:
        self.file_page = FileImportPage(self._config_path)
        self.file_page.visualize_requested.connect(self._on_visualize_from_file)
        return self.file_page

    def _build_oj_tab(self) -> QWidget:
        self.oj_page = OJPage(self._config_path)
        self.oj_page.visualize_requested.connect(self._on_visualize_from_file)
        return self.oj_page

    def _build_review_tab(self) -> QWidget:
        self.review_page = ReviewPage()
        return self.review_page

    def _build_kb_tab(self) -> QWidget:
        self.knowledge_page = KnowledgePage()
        return self.knowledge_page

    def _on_visualize_from_file(self, code: str):
        self.code_editor.setPlainText(code)
        self._tabs.setCurrentWidget(self._code_tab)
        self.statusBar().showMessage(tr("Code loaded - click Run to visualize"))

    def _setup_overlay(self):
        container = QWidget(self.centralWidget())
        container.setStyleSheet(
            "background-color: rgba(30,30,30,230);"
        )
        container.setVisible(False)
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        self._overlay_label = QLabel(tr("Analyzing code with AI..."))
        self._overlay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overlay_label.setStyleSheet(
            f"QLabel {{ color: {HIGHLIGHT}; font-size: 24px; font-weight: bold; background: transparent; }}"
        )
        layout.addWidget(self._overlay_label)

        self._overlay_time = QLabel("")
        self._overlay_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overlay_time.setStyleSheet(
            "QLabel { color: #808080; font-size: 14px; background: transparent; }"
        )
        layout.addWidget(self._overlay_time)

        self._overlay_cancel_btn = QPushButton(tr("Cancel"))
        cancel_btn = self._overlay_cancel_btn
        cancel_btn.setFixedWidth(120)
        cancel_btn.setStyleSheet(
            f"QPushButton {{ background-color: {BORDER}; color: {TEXT_PRIMARY}; border: 1px solid; "
            f"border-radius: 5px; padding: 6px 16px; font-size: 13px; }} "
            f"QPushButton:hover {{ background-color: #555; }}"
        )
        cancel_layout = QHBoxLayout()
        cancel_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cancel_layout.addWidget(cancel_btn)
        layout.addLayout(cancel_layout)

        self._overlay = container

        cancel_btn.clicked.connect(self._on_cancel_loading)
        self._elapsed_timer = QTimer()
        self._elapsed_timer.timeout.connect(self._update_elapsed)

    def _on_cancel_loading(self):
        if hasattr(self, "_engine") and self._engine is not None:
            self._engine.cancel_current_run()

    def _update_elapsed(self):
        elapsed = int(time.time() - self._load_start_time)
        self._overlay_time.setText(tr("Elapsed: {seconds}s", seconds=elapsed))

    def show_loading(self, visible: bool):
        self._overlay.setVisible(visible)
        if visible:
            self._overlay.setGeometry(self.centralWidget().rect())
            self._overlay.raise_()
            self._load_start_time = time.time()
            self._overlay_label.setText(tr("Analyzing code with AI..."))
            self._overlay_time.setText("")
            self._elapsed_timer.start(1000)
        else:
            self._elapsed_timer.stop()
            self._overlay_time.setText("")
        self.btn_run.setEnabled(not visible)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._overlay.setGeometry(self.centralWidget().rect())

    def _setup_shortcuts(self):
        self._global_shortcuts = ShortcutRegistry(self)
        self._global_shortcuts.register_many([
            ShortcutBinding(
                sequence="Ctrl+=",
                name="zoom_in",
                description="Zoom in the canvas",
                callback=self.canvas_view.zoom_in,
                context=Qt.ShortcutContext.WindowShortcut,
            ),
            ShortcutBinding(
                sequence="Ctrl+-",
                name="zoom_out",
                description="Zoom out the canvas",
                callback=self.canvas_view.zoom_out,
                context=Qt.ShortcutContext.WindowShortcut,
            ),
            ShortcutBinding(
                sequence="Ctrl+0",
                name="zoom_reset",
                description="Reset canvas zoom",
                callback=self.canvas_view.reset_view,
                context=Qt.ShortcutContext.WindowShortcut,
            ),
        ])

        self._code_shortcuts = ShortcutRegistry(self._code_tab)
        self._code_key_actions = {
            Qt.Key.Key_PageUp: self.btn_prev.click,
            Qt.Key.Key_PageDown: self.btn_next.click,
            Qt.Key.Key_F5: self.btn_run.click,
            Qt.Key.Key_F6: self.btn_reset.click,
        }
        self._code_shortcuts.register_many([
            ShortcutBinding(
                sequence="PageUp",
                name="prev step",
                description="Go to the previous execution step",
                callback=self.btn_prev.click,
            ),
            ShortcutBinding(
                sequence="PageDown",
                name="next step",
                description="Go to the next execution step",
                callback=self.btn_next.click,
            ),
            ShortcutBinding(
                sequence="F5",
                name="run",
                description="Run the current code",
                callback=self.btn_run.click,
            ),
            ShortcutBinding(
                sequence="F6",
                name="reset",
                description="Reset the current execution",
                callback=self.btn_reset.click,
            ),
        ])

    def _setup_toolbar(self):
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._example_label = QLabel(tr("Example:"))
        self._example_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; padding-left: 4px;")
        toolbar.addWidget(self._example_label)
        self._example_combo = QComboBox()
        for key in EXAMPLE_CODES:
            self._example_combo.addItem(tr(key), key)
        self._example_combo.setCurrentIndex(self._example_combo.findData("Pointers"))
        self._example_combo.currentIndexChanged.connect(self._on_example_changed)
        toolbar.addWidget(self._example_combo)
        toolbar.addSeparator()

        self.btn_run = QPushButton(tr("Run"))
        self.btn_next = QPushButton(tr("Next Step"))
        self.btn_prev = QPushButton(tr("Prev Step"))
        self.btn_reset = QPushButton(tr("Reset"))
        self.btn_run.setObjectName("run")
        self.btn_next.setEnabled(False)
        self.btn_prev.setEnabled(False)
        self.btn_reset.setEnabled(False)

        toolbar.addWidget(self.btn_run)
        toolbar.addSeparator()
        toolbar.addWidget(self.btn_prev)
        toolbar.addWidget(self.btn_next)
        toolbar.addSeparator()
        toolbar.addWidget(self.btn_reset)
        toolbar.addSeparator()

        self.btn_zoom_out = QPushButton("\u2212")
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_fit = QPushButton("\u21C5")
        self.btn_zoom_out.setFixedWidth(32)
        self.btn_zoom_in.setFixedWidth(32)
        self.btn_zoom_fit.setFixedWidth(36)
        self.btn_zoom_out.setStyleSheet(ZOOM_BTN_STYLE)
        self.btn_zoom_in.setStyleSheet(ZOOM_BTN_STYLE)
        self.btn_zoom_fit.setStyleSheet(ZOOM_BTN_STYLE)
        self.btn_zoom_out.setToolTip(tr("Zoom Out (Ctrl+-)"))
        self.btn_zoom_in.setToolTip(tr("Zoom In (Ctrl+=)"))
        self.btn_zoom_fit.setToolTip(tr("Fit to View"))
        self.btn_zoom_in.clicked.connect(self.canvas_view.zoom_in)
        self.btn_zoom_out.clicked.connect(self.canvas_view.zoom_out)
        self.btn_zoom_fit.clicked.connect(self.canvas_view.zoom_fit)
        toolbar.addWidget(self.btn_zoom_out)
        toolbar.addWidget(self.btn_zoom_in)
        toolbar.addWidget(self.btn_zoom_fit)

        self.auto_fit_check = QCheckBox(tr("Auto Fit"))
        self.auto_fit_check.setChecked(True)
        self.auto_fit_check.setToolTip(tr("Auto-fit canvas content on each step"))
        toolbar.addWidget(self.auto_fit_check)

        spacer = QWidget()
        spacer.setFixedWidth(16)
        toolbar.addWidget(spacer)

        self.step_label = QLabel(tr("Ready"))
        self.step_label.setStyleSheet(f"color: {TEXT_SECONDARY}; padding: 0 8px;")
        toolbar.addWidget(self.step_label)

    def _on_example_changed(self, index: int):
        key = self._example_combo.itemData(index)
        if key in EXAMPLE_CODES:
            self.code_editor.setPlainText(EXAMPLE_CODES[key])

    def _on_tab_changed(self, index: int):
        if index == self._home_tab_index:
            self.home_page.refresh()
        elif index == self._review_tab_index:
            self.review_page._refresh()
        if self._overlay.isVisible():
            self._overlay.setGeometry(self.centralWidget().rect())

    def _setup_menubar(self):
        self._settings_menu = QMenu(tr("Settings"), self)
        self._api_settings_action = QAction(tr("AI Settings..."), self)
        self._api_settings_action.triggered.connect(self._on_api_settings)
        self._settings_menu.addAction(self._api_settings_action)
        self.menuBar().addMenu(self._settings_menu)

    def _on_api_settings(self):
        from app.ui.widgets.api_key_dialog import show_api_key_dialog
        if show_api_key_dialog(self):
            load_language(self._config_path)
            self._retranslate_ui()
            self.statusBar().showMessage(tr("Settings saved."))

    def _setup_statusbar(self):
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(tr("Ready - Enter C++ code and click Run"))

    def set_step_info(self, current: int, total: int):
        if total > 0:
            self.step_label.setText(tr("Step {current}/{total}", current=current, total=total))
        else:
            self.step_label.setText(tr("Ready"))

    def get_code(self) -> str:
        return self.code_editor.toPlainText().strip()

    def eventFilter(self, obj, event):
        if self._current_code_tab_active():
            if event.type() in (
                QEvent.Type.ShortcutOverride,
                QEvent.Type.KeyPress,
            ):
                key = getattr(event, "key", lambda: None)()
                if key in self._code_key_actions and not event.modifiers():
                    event.accept()
                    if event.type() == QEvent.Type.KeyPress:
                        self._code_key_actions[key]()
                    return True
        return super().eventFilter(obj, event)

    def _current_code_tab_active(self) -> bool:
        return self._tabs.currentWidget() is self._code_tab

    def _retranslate_ui(self):
        self.setWindowTitle(tr("C++ Memory Visualizer"))

        tab_names = [
            (self._home_tab, "Home"),
            (self._code_tab, "Code Editor"),
            (self._oj_tab, "OJ Analysis"),
            (self._file_tab, "File Import"),
            (self._review_tab, "Review"),
            (self._kb_tab, "Knowledge Base"),
        ]
        for widget, key in tab_names:
            index = self._tabs.indexOf(widget)
            if index >= 0:
                self._tabs.setTabText(index, tr(key))

        self._example_label.setText(tr("Example:"))
        for index, key in enumerate(EXAMPLE_CODES):
            self._example_combo.setItemText(index, tr(key))
        self.btn_run.setText(tr("Run"))
        self.btn_next.setText(tr("Next Step"))
        self.btn_prev.setText(tr("Prev Step"))
        self.btn_reset.setText(tr("Reset"))
        self.btn_prev_big.setText(f"< {tr('Prev Step')}")
        self.btn_next_big.setText(f"{tr('Next Step')} >")
        self.btn_autoplay.setText(tr("Auto Play"))
        self.btn_autoplay.setToolTip(tr("Auto-advance through steps"))
        self._speed_slider.setToolTip(tr("Auto-play speed (200ms fast - 2000ms slow)"))
        self._speed_label.setText(tr("speed"))
        self.btn_zoom_out.setToolTip(tr("Zoom Out (Ctrl+-)"))
        self.btn_zoom_in.setToolTip(tr("Zoom In (Ctrl+=)"))
        self.btn_zoom_fit.setToolTip(tr("Fit to View"))
        self.auto_fit_check.setText(tr("Auto Fit"))
        self.auto_fit_check.setToolTip(tr("Auto-fit canvas content on each step"))
        self.step_label.setText(tr("Ready"))
        self.code_editor.setPlaceholderText(tr("// Enter C++ code here..."))
        self._overlay_label.setText(tr("Analyzing code with AI..."))
        self._overlay_cancel_btn.setText(tr("Cancel"))
        self._settings_menu.setTitle(tr("Settings"))
        self._api_settings_action.setText(tr("AI Settings..."))
        if hasattr(self, "home_page"):
            self.home_page.retranslate_ui()
        if hasattr(self, "oj_page"):
            self.oj_page.retranslate_ui()
        if hasattr(self, "file_page"):
            self.file_page.retranslate_ui()
        if hasattr(self, "review_page"):
            self.review_page.retranslate_ui()
        if hasattr(self, "knowledge_page"):
            self.knowledge_page.retranslate_ui()
        if hasattr(self, "tracker_panel"):
            self.tracker_panel.retranslate_ui()
        self.set_step_info(0, 0)

    def _read_config_font_size(self) -> int:
        try:
            import yaml
            config_path = self._config_path or Path(__file__).parent.parent.parent / "config.yaml"
            if config_path.exists():
                with open(config_path, "r") as f:
                    cfg = yaml.safe_load(f) or {}
                return int(cfg.get("ui", {}).get("code_font_size", 14))
        except Exception:
            logger.exception("Failed to read code font size from config")
        return 14
