from pathlib import Path
from collections.abc import Callable

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QPlainTextEdit, QGraphicsView,
    QGraphicsScene, QToolBar, QStatusBar, QWidget, QVBoxLayout,
    QLabel, QPushButton, QMenu, QTabWidget,
)
from PySide6.QtCore import Qt, Signal, QEvent, QPointF, QRectF
from PySide6.QtGui import QFont, QColor, QPainter, QWheelEvent, QAction, QMouseEvent

from app.ui.theme.colors import CANVAS_BG, TEXT_SECONDARY
from app.ui.pages.file_import_page import FileImportPage
from app.ui.pages.oj_page import OJPage
from app.ui.pages.review_page import ReviewPage
from app.ui.pages.home_page import HomePage
from app.ui.pages.knowledge_page import KnowledgePage
from app.ui.canvas.tracker_panel import TrackerPanel
from app.ui.shortcut_registry import ShortcutBinding, ShortcutRegistry


ZOOM_FACTOR = 1.15
ZOOM_MIN = 0.1
ZOOM_MAX = 10.0
ZOOM_BTN_STYLE = (
    "QPushButton { background-color: #007ACC; color: #FFFFFF; border: none; "
    "border-radius: 4px; padding: 2px 4px; font-size: 16px; font-weight: bold; "
    "min-height: 24px; min-width: 28px; } "
    "QPushButton:hover { background-color: #1A8CD8; } "
    "QPushButton:pressed { background-color: #005A9E; }"
)

SCENE_W = 1600
SCENE_H = 2000

TAB_STYLE = (
    "QTabWidget::pane { border: none; background: #1E1E1E; }"
    "QTabBar::tab { background: #2D2D2D; color: #808080; padding: 8px 24px; "
    "border: none; border-bottom: 2px solid transparent; font-size: 13px; }"
    "QTabBar::tab:selected { color: #D4D4D4; border-bottom: 2px solid #007ACC; }"
    "QTabBar::tab:hover { color: #D4D4D4; }"
)


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
        self._global_shortcuts: ShortcutRegistry | None = None
        self._code_shortcuts: ShortcutRegistry | None = None
        self._code_key_actions: dict[int, Callable[[], None]] = {}
        self.setWindowTitle("C++ Memory Visualizer")
        self.setMinimumSize(1200, 700)
        self._setup_ui()
        self._setup_toolbar()
        self._setup_menubar()
        self._setup_shortcuts()
        self._setup_statusbar()
        self._setup_overlay()

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

        self._tabs.addTab(self._home_tab, "Home")
        self._tabs.addTab(self._code_tab, "Code Editor")
        self._tabs.addTab(self._oj_tab, "OJ Analysis")
        self._tabs.addTab(self._file_tab, "File Import")
        self._tabs.addTab(self._review_tab, "Review")
        self._tabs.addTab(self._kb_tab, "Knowledge Base")
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
        self.code_editor.setPlainText(
            "int a = 42;\n"
            "int* p = new int(100);\n"
            "int* q = &a;\n"
            "*p = 200;\n"
            "delete p;\n"
        )
        self.code_editor.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 14))
        self.code_editor.setPlaceholderText("// Enter C++ code here...")

        self.canvas_view = CanvasView()
        self.canvas_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.canvas_scene = QGraphicsScene()
        self.canvas_scene.setBackgroundBrush(QColor(CANVAS_BG))
        self.canvas_scene.setSceneRect(0, 0, SCENE_W, SCENE_H)
        self.canvas_view.setScene(self.canvas_scene)

        splitter.addWidget(self.code_editor)
        splitter.addWidget(self.canvas_view)
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
        return self.oj_page

    def _build_review_tab(self) -> QWidget:
        self.review_page = ReviewPage()
        return self.review_page

    def _build_kb_tab(self) -> QWidget:
        self.knowledge_page = KnowledgePage()
        return self.knowledge_page

    def _on_tab_changed(self, index: int):
        if index == self._home_tab_index:
            self.home_page.refresh()
        elif index == self._review_tab_index:
            self.review_page._refresh()
        if self._overlay.isVisible():
            self._overlay.setGeometry(self.centralWidget().rect())

    def _on_visualize_from_file(self, code: str):
        self.code_editor.setPlainText(code)
        self._tabs.setCurrentWidget(self._code_tab)
        self.statusBar().showMessage("Code loaded from PDF — click Run to visualize")

    def _setup_overlay(self):
        self._overlay = QLabel("Analyzing code with AI...", self.centralWidget())
        self._overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overlay.setStyleSheet(
            "QLabel { background-color: rgba(30,30,30,230); color: #FFD700; "
            "font-size: 24px; font-weight: bold; }"
        )
        self._overlay.setVisible(False)

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

        self.btn_run = QPushButton("Run")
        self.btn_next = QPushButton("Next Step")
        self.btn_prev = QPushButton("Prev Step")
        self.btn_reset = QPushButton("Reset")
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
        self.btn_zoom_out.setToolTip("Zoom Out (Ctrl+-)")
        self.btn_zoom_in.setToolTip("Zoom In (Ctrl+=)")
        self.btn_zoom_fit.setToolTip("Fit to View")
        self.btn_zoom_in.clicked.connect(self.canvas_view.zoom_in)
        self.btn_zoom_out.clicked.connect(self.canvas_view.zoom_out)
        self.btn_zoom_fit.clicked.connect(self.canvas_view.zoom_fit)
        toolbar.addWidget(self.btn_zoom_out)
        toolbar.addWidget(self.btn_zoom_in)
        toolbar.addWidget(self.btn_zoom_fit)

        spacer = QWidget()
        spacer.setFixedWidth(16)
        toolbar.addWidget(spacer)

        self.step_label = QLabel("Ready")
        self.step_label.setStyleSheet(f"color: {TEXT_SECONDARY}; padding: 0 8px;")
        toolbar.addWidget(self.step_label)

    def _setup_menubar(self):
        settings_menu = QMenu("Settings", self)
        api_action = QAction("API Key...", self)
        api_action.triggered.connect(self._on_api_settings)
        settings_menu.addAction(api_action)
        self.menuBar().addMenu(settings_menu)

    def _on_api_settings(self):
        from app.ui.widgets.api_key_dialog import show_api_key_dialog
        show_api_key_dialog(self)

    def _setup_statusbar(self):
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready — Enter C++ code and click Run")

    def show_loading(self, visible: bool):
        self._overlay.setVisible(visible)
        if visible:
            self._overlay.raise_()
            self._overlay.setGeometry(self.centralWidget().rect())
        self.btn_run.setEnabled(not visible)

    def set_step_info(self, current: int, total: int):
        if total > 0:
            self.step_label.setText(f"Step {current}/{total}")
        else:
            self.step_label.setText("Ready")

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
