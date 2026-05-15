from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QPlainTextEdit, QGraphicsView,
    QGraphicsScene, QToolBar, QStatusBar, QWidget, QVBoxLayout,
    QLabel, QPushButton, QMenu, QTabWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QFont, QColor, QPainter, QWheelEvent, QAction, QKeySequence, QShortcut,
)

from app.ui.theme.colors import CANVAS_BG, TEXT_SECONDARY
from app.ui.theme.styles import GLOBAL_STYLESHEET
from app.ui.pages.file_import_page import FileImportPage
from app.ui.pages.oj_page import OJPage
from app.ui.pages.review_page import ReviewPage
from app.ui.pages.graph_page import GraphPage
from app.ui.canvas.tracker_panel import TrackerPanel


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
    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom_level = 1.0
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

    def zoom_in(self):
        if self._zoom_level * ZOOM_FACTOR <= ZOOM_MAX:
            self._zoom_level *= ZOOM_FACTOR
            self.scale(ZOOM_FACTOR, ZOOM_FACTOR)

    def zoom_out(self):
        if self._zoom_level / ZOOM_FACTOR >= ZOOM_MIN:
            self._zoom_level /= ZOOM_FACTOR
            self.scale(1 / ZOOM_FACTOR, 1 / ZOOM_FACTOR)

    def zoom_fit(self):
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom_level = self.transform().m11()

    def reset_view(self):
        self.resetTransform()
        self._zoom_level = 1.0


class MainWindow(QMainWindow):

    def __init__(self, config_path: Path | None = None):
        super().__init__()
        self._config_path = config_path
        self.setWindowTitle("C++ Memory Visualizer")
        self.setMinimumSize(1200, 700)
        self._setup_ui()
        self._setup_toolbar()
        self._setup_menubar()
        self._setup_shortcuts()
        self._setup_statusbar()
        self._setup_overlay()

    def _setup_ui(self):
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(TAB_STYLE)

        self._code_tab = self._build_code_tab()
        self._file_tab = self._build_file_tab()
        self._oj_tab = self._build_oj_tab()
        self._review_tab = self._build_review_tab()
        self._graph_tab = self._build_graph_tab()

        self._tabs.addTab(self._code_tab, "Code Editor")
        self._tabs.addTab(self._oj_tab, "OJ Analysis")
        self._tabs.addTab(self._file_tab, "File Import")
        self._tabs.addTab(self._review_tab, "Review")
        self._tabs.addTab(self._graph_tab, "Knowledge Graph")

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tabs)
        self.setCentralWidget(central)

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
        self.code_editor.setFont(QFont("JetBrains Mono", 14))
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

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(splitter, 1)
        layout.addWidget(self.tracker_panel)
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

    def _build_graph_tab(self) -> QWidget:
        self.graph_page = GraphPage()
        return self.graph_page

    def _on_visualize_from_file(self, code: str):
        self.code_editor.setPlainText(code)
        self._tabs.setCurrentIndex(0)
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
        QShortcut(QKeySequence("Ctrl+="), self, self.canvas_view.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self.canvas_view.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, self.canvas_view.reset_view)

    def _setup_toolbar(self):
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.btn_run = QPushButton("Run")
        self.btn_next = QPushButton("Next Step")
        self.btn_prev = QPushButton("Prev Step")
        self.btn_reset = QPushButton("Reset")
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
