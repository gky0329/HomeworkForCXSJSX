import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
from collections.abc import Callable

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QPlainTextEdit, QGraphicsView,
    QGraphicsScene, QStatusBar, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QCheckBox, QComboBox, QSlider,
)
from PySide6.QtCore import Qt, Signal, QEvent, QPointF, QRectF, QTimer, QSize
from PySide6.QtGui import QFont, QColor, QPainter, QWheelEvent, QMouseEvent, QIcon

from app.ui.theme.colors import (
    BORDER, CANVAS_BG, EDITOR_BG, EDITOR_SELECTION, HIGHLIGHT, SURFACE,
    TEXT_PRIMARY, TEXT_SECONDARY,
)
from app.ui.theme.minecraft_assets import asset_path
from app.ui.pages.home_page import HomePage
from app.ui.canvas.tracker_panel import TrackerPanel
from app.ui.shortcut_registry import ShortcutBinding, ShortcutRegistry
from app.services.i18n import load_language, tr
from app.core.demo_examples import ROADSHOW_DEMO_CODE
from app.utils.startup_profiler import StartupProfiler


ZOOM_FACTOR = 1.15
ZOOM_MIN = 0.1
ZOOM_MAX = 10.0
ZOOM_BTN_STYLE = ""

SCENE_W = 1600
SCENE_H = 2000

TAB_STYLE = ""

EXAMPLE_CODES = {
    "Roadshow Demo": ROADSHOW_DEMO_CODE,
    "Teaching Basics": (
        "class Student {\n"
        "public:\n"
        "  int score;\n"
        "  double progress;\n"
        "};\n"
        "int scores[3] = {72, 85, 91};\n"
        "int total = scores[0] + scores[1] + scores[2];\n"
        "double average = total / 3.0;\n"
        "int* focus = &total;\n"
        "*focus = total + 5;\n"
        "Student alice;\n"
        "alice.score = 88;\n"
        "alice.progress = 0.75;\n"
        "Student* mentor = new Student();\n"
        "mentor->score = alice.score + 7;\n"
        "mentor->progress = 0.95;\n"
        "int* reward = new int(mentor->score);\n"
        "*reward = *reward + 2;\n"
        "delete reward;\n"
        "delete mentor;\n"
    ),
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
DEFAULT_EXAMPLE_KEY = "Roadshow Demo"


class CanvasView(QGraphicsView):
    variable_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom_level = 1.0
        self._panning = False
        self._pan_last_pos = QPointF()
        self._stable_fit_bounds = QRectF()
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
        fit_rect = self._stable_fit_bounds if self._stable_fit_bounds.isValid() else self._fit_bounds()
        if not fit_rect.isValid() or fit_rect.isEmpty():
            return
        self.fitInView(fit_rect, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom_level = self.transform().m11()

    def set_stable_fit_bounds(self, bounds: QRectF):
        self._stable_fit_bounds = QRectF(bounds)

    def clear_stable_fit_bounds(self):
        self._stable_fit_bounds = QRectF()

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
    code_page_ready = Signal()
    _CODE_PAGE_ATTRS = {
        "_example_combo", "btn_run", "btn_prev", "btn_next", "btn_reset",
        "btn_zoom_out", "btn_zoom_in", "btn_zoom_fit", "btn_fullscreen",
        "auto_fit_check", "step_label", "code_editor", "stdin_label", "stdin_editor",
        "canvas_view", "canvas_scene", "btn_prev_big", "btn_next_big",
        "btn_autoplay", "_speed_slider", "_speed_label", "tracker_panel",
    }

    def __init__(self, config_path: Path | None = None, startup_profiler: StartupProfiler | None = None):
        super().__init__()
        self._config_path = config_path
        self._startup_profiler = startup_profiler
        if self._startup_profiler is not None:
            with self._startup_profiler.span("language"):
                load_language(config_path)
        else:
            load_language(config_path)
        self._global_shortcuts: ShortcutRegistry | None = None
        self._code_shortcuts: ShortcutRegistry | None = None
        self._code_key_actions: dict[int, Callable[[], None]] = {}
        self._load_start_time: float = 0.0
        self._elapsed_timer: QTimer | None = None
        self._lazy_tabs: dict[int, str] = {}
        self._replacing_lazy_tab = False
        self.setWindowTitle(tr("C++rafting Table"))
        self.setWindowIcon(QIcon(str(Path(__file__).resolve().parents[2] / "assets" / "icons" / "app_icon.png")))
        self.setMinimumSize(1200, 700)
        self._setup_ui()
        self._setup_statusbar()
        self._setup_overlay()
        self._retranslate_ui()

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def __getattr__(self, name: str):
        if name in MainWindow._CODE_PAGE_ATTRS and "_code_tab_index" in self.__dict__:
            self._ensure_tab(self.__dict__["_code_tab_index"])
            if name in self.__dict__:
                return self.__dict__[name]
        raise AttributeError(f"{type(self).__name__!s} object has no attribute {name!r}")

    def _setup_ui(self):
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(TAB_STYLE)
        self._tabs.setIconSize(QSize(28, 28))

        self._home_tab = self._build_home_tab()
        self._code_tab = None
        self._file_tab = None
        self._oj_tab = None
        self._review_tab = None
        self._kb_tab = None

        self._home_tab_index = self._tabs.addTab(self._home_tab, QIcon(asset_path("icons", "nav_home")), tr("Home"))
        self._code_tab_index = self._add_lazy_tab("code", "nav_code", "Code Editor")
        self._oj_tab_index = self._add_lazy_tab("oj", "nav_oj", "OJ Analysis")
        self._file_tab_index = self._add_lazy_tab("file", "nav_file", "File Import")
        self._review_tab_index = self._add_lazy_tab("review", "nav_review", "Review")
        self._kb_tab_index = self._add_lazy_tab("knowledge", "nav_knowledge", "Knowledge Base")
        self._tabs.currentChanged.connect(self._on_tab_changed)

        self._settings_btn = QPushButton(tr("Settings"))
        self._settings_btn.setIcon(QIcon(asset_path("icons", "nav_settings")))
        self._settings_btn.setIconSize(QSize(24, 24))
        self._settings_btn.setProperty("variant", "secondary")
        self._settings_btn.clicked.connect(self._on_api_settings)
        self._tabs.setCornerWidget(self._settings_btn, Qt.Corner.TopRightCorner)

        central = QWidget()
        central.setObjectName("appShell")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tabs)
        self.setCentralWidget(central)

    def _add_lazy_tab(self, key: str, icon_name: str, label_key: str) -> int:
        tab = self._build_loading_tab(label_key)
        index = self._tabs.addTab(tab, QIcon(asset_path("icons", icon_name)), tr(label_key))
        self._lazy_tabs[index] = key
        return index

    def _build_loading_tab(self, label_key: str) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel(tr("Loading {name}...", name=tr(label_key)))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 18px; font-weight: 700;")
        layout.addWidget(label)
        return tab

    def _ensure_tab(self, index: int) -> QWidget | None:
        key = self._lazy_tabs.get(index)
        if key is None:
            return self._tabs.widget(index)

        builders = {
            "code": self._build_code_tab,
            "oj": self._build_oj_tab,
            "file": self._build_file_tab,
            "review": self._build_review_tab,
            "knowledge": self._build_kb_tab,
        }
        builder = builders[key]
        if self._startup_profiler is not None:
            with self._startup_profiler.span(f"lazy build page {key}"):
                widget = builder()
        else:
            widget = builder()

        icon_names = {
            "code": "nav_code",
            "oj": "nav_oj",
            "file": "nav_file",
            "review": "nav_review",
            "knowledge": "nav_knowledge",
        }
        label_keys = {
            "code": "Code Editor",
            "oj": "OJ Analysis",
            "file": "File Import",
            "review": "Review",
            "knowledge": "Knowledge Base",
        }
        self._replacing_lazy_tab = True
        self._tabs.removeTab(index)
        self._tabs.insertTab(index, widget, QIcon(asset_path("icons", icon_names[key])), tr(label_keys[key]))
        self._tabs.setCurrentIndex(index)
        self._replacing_lazy_tab = False
        self._lazy_tabs.pop(index, None)
        if key == "code":
            self._setup_shortcuts()
            self.code_page_ready.emit()
        return widget

    def _build_home_tab(self) -> QWidget:
        if self._startup_profiler is not None:
            with self._startup_profiler.span("build page home"):
                self.home_page = HomePage()
        else:
            self.home_page = HomePage()
        self.home_page.tab_switch_requested.connect(self._tabs.setCurrentIndex)
        return self.home_page

    def _build_code_tab(self) -> QWidget:
        header = QHBoxLayout()
        header.setContentsMargins(8, 6, 8, 6)
        header.setSpacing(6)

        example_label = QLabel(tr("Example:"))
        example_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: 600;")
        header.addWidget(example_label)

        self._example_combo = QComboBox()
        for key in EXAMPLE_CODES:
            self._example_combo.addItem(tr(key), key)
        self._example_combo.setCurrentIndex(self._example_combo.findData(DEFAULT_EXAMPLE_KEY))
        self._example_combo.currentIndexChanged.connect(self._on_example_changed)
        header.addWidget(self._example_combo)
        header.addStretch()

        self.btn_run = QPushButton(tr("Run"))
        self.btn_run.setObjectName("run")
        self.btn_run.setIcon(QIcon(asset_path("icons", "action_run")))
        self.btn_run.setIconSize(QSize(18, 18))
        header.addWidget(self.btn_run)

        self.btn_prev = QPushButton(tr("Prev"))
        self.btn_prev.setEnabled(False)
        header.addWidget(self.btn_prev)

        self.btn_next = QPushButton(tr("Next"))
        self.btn_next.setEnabled(False)
        header.addWidget(self.btn_next)

        self.btn_reset = QPushButton(tr("Reset"))
        self.btn_reset.setEnabled(False)
        header.addWidget(self.btn_reset)

        self.btn_zoom_out = QPushButton("\u2212")
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_fit = QPushButton("\u21C5")
        self.btn_fullscreen = QPushButton()
        self.btn_fullscreen.setIcon(QIcon(asset_path("icons", "action_fullscreen")))
        self.btn_fullscreen.setIconSize(QSize(18, 18))
        for b in (self.btn_zoom_out, self.btn_zoom_in, self.btn_zoom_fit, self.btn_fullscreen):
            b.setFixedSize(28, 28)
            b.setProperty("variant", "icon")
        self.btn_zoom_out.setToolTip(tr("Zoom Out (Ctrl+-)"))
        self.btn_zoom_in.setToolTip(tr("Zoom In (Ctrl+=)"))
        self.btn_zoom_fit.setToolTip(tr("Fit to View"))
        self.btn_fullscreen.setToolTip(tr("Full Screen (F11)"))
        self._sync_fullscreen_button()
        header.addWidget(self.btn_zoom_out)
        header.addWidget(self.btn_zoom_in)
        header.addWidget(self.btn_zoom_fit)
        header.addWidget(self.btn_fullscreen)

        self.auto_fit_check = QCheckBox(tr("Auto Fit"))
        self.auto_fit_check.setChecked(False)
        self.auto_fit_check.setToolTip(tr("Keep fitting canvas content on every step"))
        header.addWidget(self.auto_fit_check)

        self.step_label = QLabel(tr("Ready"))
        self.step_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px; font-weight: 600; padding: 0 4px;")
        header.addWidget(self.step_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        self.code_editor = QPlainTextEdit()
        self.code_editor.setPlainText(EXAMPLE_CODES[DEFAULT_EXAMPLE_KEY])
        font_size = self._read_config_font_size()
        self.code_editor.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", font_size))
        self.code_editor.setPlaceholderText(tr("// Enter C++ code here..."))
        self.code_editor.setStyleSheet(
            f"QPlainTextEdit {{ background-color: {EDITOR_BG}; color: {TEXT_PRIMARY}; "
            f"selection-background-color: {EDITOR_SELECTION}; border: none; padding: 6px; }}"
        )

        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        left_layout.addWidget(self.code_editor, 1)

        self.stdin_label = QLabel(tr("Program Input (stdin)"))
        self.stdin_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: 600; padding: 4px 8px; "
            f"background-color: {SURFACE}; border-top: 1px solid {BORDER};"
        )
        left_layout.addWidget(self.stdin_label, 0)

        self.stdin_editor = QPlainTextEdit()
        self.stdin_editor.setFixedHeight(92)
        self.stdin_editor.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", max(13, font_size - 1)))
        self.stdin_editor.setPlaceholderText(tr("Optional stdin for cin / scanf, one sample input block"))
        self.stdin_editor.setStyleSheet(
            f"QPlainTextEdit {{ background-color: {EDITOR_BG}; color: {TEXT_PRIMARY}; "
            f"border: none; border-top: 1px solid {BORDER}; padding: 6px; }}"
        )
        left_layout.addWidget(self.stdin_editor, 0)

        self.canvas_view = CanvasView()
        self.canvas_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.canvas_scene = QGraphicsScene()
        self.canvas_scene.setBackgroundBrush(QColor(CANVAS_BG))
        self.canvas_scene.setSceneRect(0, 0, SCENE_W, SCENE_H)
        self.canvas_view.setScene(self.canvas_scene)

        self.btn_zoom_in.clicked.connect(self.canvas_view.zoom_in)
        self.btn_zoom_out.clicked.connect(self.canvas_view.zoom_out)
        self.btn_zoom_fit.clicked.connect(self.canvas_view.zoom_fit)
        self.btn_fullscreen.clicked.connect(self._toggle_fullscreen)

        right_pane = QWidget()
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        right_layout.addWidget(self.canvas_view, 1)

        step_bar = QHBoxLayout()
        step_bar.setContentsMargins(8, 4, 8, 4)
        step_bar.setSpacing(8)

        self.btn_prev_big = QPushButton(f"< {tr('Prev Step')}")
        self.btn_prev_big.setProperty("variant", "secondary")
        self.btn_prev_big.setEnabled(False)
        step_bar.addWidget(self.btn_prev_big)

        self.btn_next_big = QPushButton(f"{tr('Next Step')} >")
        self.btn_next_big.setProperty("variant", "secondary")
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
        speed_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; font-weight: 600;")
        step_bar.addWidget(speed_label)

        step_bar.addStretch()

        right_layout.addLayout(step_bar, 0)

        splitter.addWidget(left_pane)
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
        layout.addLayout(header, 0)
        layout.addWidget(splitter, 1)
        layout.addWidget(self.tracker_panel, 0)
        self._code_tab = tab
        return tab

    def _build_file_tab(self) -> QWidget:
        from app.ui.pages.file_import_page import FileImportPage
        self.file_page = FileImportPage(self._config_path)
        self._file_tab = self.file_page
        self.file_page.visualize_requested.connect(self._on_visualize_from_file)
        return self.file_page

    def _build_oj_tab(self) -> QWidget:
        from app.ui.pages.oj_page import OJPage
        self.oj_page = OJPage(self._config_path)
        self._oj_tab = self.oj_page
        self.oj_page.visualize_requested.connect(self._on_visualize_from_file)
        return self.oj_page

    def _build_review_tab(self) -> QWidget:
        from app.ui.pages.review_page import ReviewPage
        self.review_page = ReviewPage()
        self._review_tab = self.review_page
        return self.review_page

    def _build_kb_tab(self) -> QWidget:
        from app.ui.pages.knowledge_page import KnowledgePage
        self.knowledge_page = KnowledgePage()
        self._kb_tab = self.knowledge_page
        return self.knowledge_page

    def _on_visualize_from_file(self, code: str):
        self._ensure_tab(self._code_tab_index)
        self.code_editor.setPlainText(code)
        self._tabs.setCurrentIndex(self._code_tab_index)
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

        self._overlay_label = QLabel(tr("Analyzing code..."))
        self._overlay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overlay_label.setStyleSheet(
            f"QLabel {{ color: {HIGHLIGHT}; font-size: 26px; font-weight: bold; background: transparent; }}"
        )
        layout.addWidget(self._overlay_label)

        self._overlay_time = QLabel("")
        self._overlay_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overlay_time.setStyleSheet(
            f"QLabel {{ color: {TEXT_SECONDARY}; font-size: 14px; font-weight: 600; background: transparent; }}"
        )
        layout.addWidget(self._overlay_time)

        self._overlay_cancel_btn = QPushButton(tr("Cancel"))
        cancel_btn = self._overlay_cancel_btn
        cancel_btn.setFixedWidth(120)
        cancel_btn.setProperty("variant", "secondary")
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
        elapsed = time.time() - self._load_start_time
        self._overlay_time.setText(tr("Elapsed: {seconds}s", seconds=f"{elapsed:.1f}"))

    def show_loading(self, visible: bool):
        self._overlay.setVisible(visible)
        if visible:
            self._overlay.setGeometry(self.centralWidget().rect())
            self._overlay.raise_()
            self._load_start_time = time.time()
            self._overlay_label.setText(tr("Analyzing code..."))
            self._overlay_time.setText("")
            self._elapsed_timer.start(100)
        else:
            self._elapsed_timer.stop()
            self._overlay_time.setText("")
        self.btn_run.setEnabled(not visible)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._overlay.setGeometry(self.centralWidget().rect())

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._sync_fullscreen_button()

    def closeEvent(self, event):
        for page_attr in ("review_page", "knowledge_page", "file_page", "oj_page"):
            page = getattr(self, page_attr, None)
            shutdown = getattr(page, "shutdown_workers", None)
            if callable(shutdown):
                shutdown()
        super().closeEvent(event)

    def _setup_shortcuts(self):
        if self._global_shortcuts is not None or self._code_tab is None:
            return
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
            ShortcutBinding(
                sequence="F11",
                name="toggle_fullscreen",
                description="Toggle full screen mode",
                callback=self._toggle_fullscreen,
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

    def _on_example_changed(self, index: int):
        key = self._example_combo.itemData(index)
        if key in EXAMPLE_CODES:
            self.code_editor.setPlainText(EXAMPLE_CODES[key])

    def _on_tab_changed(self, index: int):
        if self._replacing_lazy_tab:
            return
        self._ensure_tab(index)
        if index == self._home_tab_index:
            self.home_page.refresh()
        elif index == self._review_tab_index and hasattr(self, "review_page"):
            self.review_page._refresh()
        if hasattr(self, "_overlay") and self._overlay.isVisible():
            self._overlay.setGeometry(self.centralWidget().rect())

    def _on_api_settings(self):
        from app.ui.widgets.api_key_dialog import show_api_key_dialog
        show_api_key_dialog(self)
        load_language(self._config_path)
        self.statusBar().showMessage(tr("Settings saved."))
        self._retranslate()

    def _retranslate(self):
        self.setWindowTitle(tr("C++rafting Table"))
        self._tabs.setTabText(self._home_tab_index, tr("Home"))
        self._tabs.setTabText(self._code_tab_index, tr("Code Editor"))
        self._tabs.setTabText(self._oj_tab_index, tr("OJ Analysis"))
        self._tabs.setTabText(self._file_tab_index, tr("File Import"))
        self._tabs.setTabText(self._review_tab_index, tr("Review"))
        self._tabs.setTabText(self._kb_tab_index, tr("Knowledge Base"))
        self._settings_btn.setText(tr("Settings"))
        if self._code_tab is None:
            return
        self.btn_run.setText(tr("Run"))
        self.btn_prev.setText(tr("Prev"))
        self.btn_next.setText(tr("Next"))
        self.btn_reset.setText(tr("Reset"))
        self.auto_fit_check.setText(tr("Auto Fit"))
        self._sync_fullscreen_button()
        self.stdin_label.setText(tr("Program Input (stdin)"))
        self.stdin_editor.setPlaceholderText(tr("Optional stdin for cin / scanf, one sample input block"))
        self.step_label.setText(tr("Ready") if "Ready" in self.step_label.text() or "就绪" in self.step_label.text() else self.step_label.text())

    def _setup_statusbar(self):
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(tr("Ready - Enter C++ code and click Run"))

    def set_step_info(self, current: int, total: int):
        if self._code_tab is None:
            return
        if total > 0:
            self.step_label.setText(tr("Step {current}/{total}", current=current, total=total))
        else:
            self.step_label.setText(tr("Ready"))

    def get_code(self) -> str:
        self._ensure_tab(self._code_tab_index)
        return self.code_editor.toPlainText().strip()

    def get_stdin(self) -> str:
        self._ensure_tab(self._code_tab_index)
        return self.stdin_editor.toPlainText()

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
        if not hasattr(self, "_tabs") or not hasattr(self, "_code_tab"):
            return False
        return self._tabs.currentWidget() is self._code_tab

    def _retranslate_ui(self):
        self.setWindowTitle(tr("C++rafting Table"))

        self._tabs.setTabText(self._home_tab_index, tr("Home"))
        self._tabs.setTabText(self._code_tab_index, tr("Code Editor"))
        self._tabs.setTabText(self._oj_tab_index, tr("OJ Analysis"))
        self._tabs.setTabText(self._file_tab_index, tr("File Import"))
        self._tabs.setTabText(self._review_tab_index, tr("Review"))
        self._tabs.setTabText(self._kb_tab_index, tr("Knowledge Base"))
        self._settings_btn.setText(tr("Settings"))
        if self._code_tab is None:
            if hasattr(self, "home_page"):
                self.home_page.retranslate_ui()
            return
        self.btn_run.setText(tr("Run"))
        self.btn_prev.setText(tr("Prev"))
        self.btn_next.setText(tr("Next"))
        self.btn_reset.setText(tr("Reset"))
        self.btn_prev_big.setText(f"< {tr('Prev Step')}")
        self.btn_next_big.setText(f"{tr('Next Step')} >")
        self.btn_autoplay.setText(tr("Auto Play"))
        self._speed_label.setText(tr("speed"))
        self.auto_fit_check.setText(tr("Auto Fit"))
        self._sync_fullscreen_button()
        self.step_label.setText(tr("Ready"))
        self.code_editor.setPlaceholderText(tr("// Enter C++ code here..."))
        self.stdin_label.setText(tr("Program Input (stdin)"))
        self.stdin_editor.setPlaceholderText(tr("Optional stdin for cin / scanf, one sample input block"))
        self._overlay_label.setText(tr("Analyzing code..."))
        self._overlay_cancel_btn.setText(tr("Cancel"))
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
                return max(15, int(cfg.get("ui", {}).get("code_font_size", 16)))
        except Exception:
            logger.exception("Failed to read code font size from config")
        return 16

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
        self._sync_fullscreen_button()

    def _sync_fullscreen_button(self):
        if not hasattr(self, "btn_fullscreen"):
            return
        self.btn_fullscreen.setText("")
        if self.isFullScreen():
            self.btn_fullscreen.setToolTip(tr("Exit Full Screen (F11)"))
        else:
            self.btn_fullscreen.setToolTip(tr("Full Screen (F11)"))
