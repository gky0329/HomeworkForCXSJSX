import math
import random
import re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QFrame, QLineEdit, QSplitter,
    QListWidget, QListWidgetItem, QGraphicsView,
    QGraphicsScene, QGraphicsEllipseItem, QGraphicsTextItem,
    QGraphicsLineItem, QStackedWidget,
)
from PySide6.QtCore import Qt, QMargins, QTimer
from PySide6.QtGui import (
    QFont, QColor, QPen, QBrush, QPainter, QLinearGradient, QMouseEvent,
)

from app.services import error_store
from app.services.ai_explain_worker import AIExplainWorker, EXPLAIN_PROMPT
from app.services.i18n import tr
from app.ui.widgets.helpers import mlabel, clear_layout
from app.ui.widgets.threading import retire_worker
import shiboken6
from app.ui.theme.colors import (
    CANVAS_BG, SURFACE, BORDER, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    STACK_BORDER, HEAP_BORDER, ACCENT, ACCENT_HOVER, EDGE_DANGLING, SUCCESS,
    EDITOR_BG,
)


def _md_to_html(text: str) -> str:
    """Convert markdown to HTML for QLabel RichText rendering."""
    text = re.sub(r'^好的[，,]\s*', '', text)
    text = re.sub(r'^当然[，,]\s*', '', text)
    text = re.sub(r'^我来解释.+?[：:]\s*', '', text)

    html = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    html = re.sub(r"```(\w*)\n(.*?)```", _code_block, html, flags=re.DOTALL)
    html = re.sub(r"`([^`\n]+)`", r"<code style='background:#2D2D2D;color:#CE9178;padding:1px 5px;font-family:monospace;'>\1</code>", html)
    html = re.sub(r"^\*\*\*(.+?)\*\*\*$", r"<h2 style='color:#9CDCFE;font-size:22px;font-weight:700;margin:16px 0 6px 0;border-bottom:1px solid #3E3E3E;padding-bottom:6px;'>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2 style='color:#9CDCFE;font-size:22px;font-weight:700;margin:16px 0 6px 0;border-bottom:1px solid #3E3E3E;padding-bottom:6px;'>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^### (.+)$", r"<h3 style='color:#569CD6;font-size:16px;font-weight:600;margin:12px 0 4px 0;'>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
    html = re.sub(r"^- (.+)$", r"<li style='margin:2px 0;'>\1</li>", html, flags=re.MULTILINE)
    html = re.sub(r"^(\d+)\. (.+)$", r"<li style='margin:2px 0;'>\2</li>", html, flags=re.MULTILINE)
    html = re.sub(r"---", r"<hr style='border:none;border-top:1px solid #3E3E3E;margin:10px 0;'>", html)
    html = re.sub(r"\n\n", "<br><br>", html)
    html = re.sub(r"\n", "<br>", html)
    return f"<div style='line-height:1.7;'>{html}</div>"


def _code_block(match: re.Match) -> str:
    _lang = match.group(1)
    code = match.group(2).strip()
    code_escaped = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    lines = code_escaped.split("\n")
    numbered = "".join(
        f"<span style='color:#808080;'>{i+1:>2} </span>{line}<br>"
        for i, line in enumerate(lines)
    )
    return (
        f"<div style='background:#1E1E1E;border:1px solid #3E3E3E;"
        f"padding:10px 14px;margin:8px 0;font-family:monospace;font-size:12px;"
        f"color:#D4D4D4;line-height:1.5;'>{numbered}</div>"
    )


TOGGLE_ACTIVE = (
    f"QPushButton {{ background-color: {ACCENT}; color: #FFFFFF; "
    f"border: none; padding: 4px 12px; font-size: 12px; font-weight: bold; }}"
)
TOGGLE_INACTIVE = (
    f"QPushButton {{ background-color: transparent; "
    f"color: {TEXT_SECONDARY}; border: 1px solid {BORDER}; "
    f"padding: 4px 12px; font-size: 12px; }}"
    f"QPushButton:hover {{ color: {TEXT_PRIMARY}; border-color: {ACCENT}; }}"
)


class _GraphCanvas(QGraphicsView):
    def wheelEvent(self, event):
        event.accept()


class GraphNode(QGraphicsEllipseItem):
    def __init__(self, x: float, y: float, r: float, label: str, color: QColor,
                 on_clicked=None):
        super().__init__(-r, -r, 2 * r, 2 * r)
        self.label = label
        self.radius = r
        self.vx = 0.0
        self.vy = 0.0
        self._on_clicked = on_clicked
        self._press_pos = None
        self.setPos(x, y)
        self.setPen(QPen(color, 2))
        gradient = QLinearGradient(-r, -r, r, r)
        gradient.setColorAt(0, color.lighter(140))
        gradient.setColorAt(1, color.darker(120))
        self.setBrush(QBrush(gradient))
        self.setFlag(self.GraphicsItemFlag.ItemIsMovable, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._text = QGraphicsTextItem(label, self)
        self._text.setDefaultTextColor(QColor("#FFFFFF"))
        self._text.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 10))
        trect = self._text.boundingRect()
        self._text.setPos(-trect.width() / 2, -trect.height() / 2)

    def mousePressEvent(self, event: QMouseEvent):
        self._press_pos = event.scenePos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._press_pos is not None and self._on_clicked:
            delta = event.scenePos() - self._press_pos
            if math.hypot(delta.x(), delta.y()) < 8:
                self._on_clicked(self.label)
        self._press_pos = None
        super().mouseReleaseEvent(event)


class KnowledgePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_kps: list[dict] = []
        self._graph_view = False
        self._graph_nodes: list[GraphNode] = []
        self._graph_edges: list[tuple[QGraphicsLineItem, GraphNode, GraphNode]] = []
        self._graph_timer = QTimer()
        self._graph_timer.timeout.connect(self._simulate)
        self._selected_node: str | None = None
        self._explain_worker: AIExplainWorker | None = None
        self._quiz_worker: AIExplainWorker | None = None
        self._auto_explain_worker: AIExplainWorker | None = None
        self._retired_workers: list[AIExplainWorker] = []
        self._setup_ui()
        self._refresh()

    def hideEvent(self, event):
        self._graph_timer.stop()
        super().hideEvent(event)

    # ── UI setup ────────────────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self._header_label = mlabel(tr("Knowledge Base"), STACK_BORDER, 16, True)
        header.addWidget(self._header_label)

        self._btn_list = QPushButton(tr("List"))
        self._btn_list.setStyleSheet(TOGGLE_ACTIVE)
        self._btn_list.clicked.connect(lambda: self._set_view(False))
        header.addWidget(self._btn_list)

        self._btn_graph = QPushButton(tr("Graph"))
        self._btn_graph.setStyleSheet(TOGGLE_INACTIVE)
        self._btn_graph.clicked.connect(lambda: self._set_view(True))
        header.addWidget(self._btn_graph)

        header.addStretch()

        self._search = QLineEdit()
        self._search.setPlaceholderText(tr("Search concepts..."))
        self._search.setFixedWidth(220)
        self._search.setStyleSheet(
            f"QLineEdit {{ background-color: transparent; "
            f"color: {TEXT_PRIMARY}; border: none; border-bottom: 1px solid {BORDER}; "
            f"padding: 6px 4px; font-size: 14px; }}"
            f"QLineEdit:focus {{ border-bottom: 1px solid {ACCENT}; }}"
        )
        self._search.textChanged.connect(self._on_search)
        header.addWidget(self._search)

        self._stats_label = mlabel("", TEXT_SECONDARY, 12)
        header.addWidget(self._stats_label)

        layout.addLayout(header)

        self._list_stack = QWidget()
        list_layout = QHBoxLayout(self._list_stack)
        list_layout.setContentsMargins(0, 0, 0, 0)

        self._concept_list = QListWidget()
        self._concept_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._concept_list.setWordWrap(True)
        self._concept_list.setStyleSheet(
            f"QListWidget {{ background-color: transparent; "
            f"color: {TEXT_PRIMARY}; border: none; "
            f"font-size: 14px; }}"
            f"QListWidget::item {{ padding: 10px 14px; min-height: 32px; "
            f"border-bottom: 1px solid {BORDER}; }}"
            f"QListWidget::item:selected {{ background-color: #1A3A5C; }}"
        )
        self._concept_list.currentRowChanged.connect(self._on_select)
        list_layout.addWidget(self._concept_list)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 0, 0, 0)
        self._detail_label = mlabel(tr("Select a concept"), TEXT_SECONDARY, 13)
        right_layout.addWidget(self._detail_label)
        self._detail = QFrame()
        self._detail.setObjectName("kbDetail")
        self._detail.setStyleSheet(
            f"QFrame#kbDetail {{ background-color: {SURFACE}; "
            f"border: none; padding: 16px; }}"
            f"QFrame#kbDetail QLabel {{ border: none; background: transparent; outline: none; }}"
        )
        self._detail_layout = QVBoxLayout(self._detail)
        self._detail_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setStyleSheet(f"QScrollArea {{ border: none; background: transparent; }}")
        detail_scroll.setWidget(self._detail)
        right_layout.addWidget(detail_scroll)
        list_layout.addWidget(right)

        self._graph_stack = QWidget()
        graph_layout = QVBoxLayout(self._graph_stack)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        self._graph_view_widget = _GraphCanvas()
        self._graph_view_widget.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._graph_view_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._graph_view_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._graph_scene = QGraphicsScene()
        self._graph_scene.setBackgroundBrush(QColor(CANVAS_BG))
        self._graph_scene.setSceneRect(-500, -500, 1000, 1000)
        self._graph_view_widget.setScene(self._graph_scene)
        graph_layout.addWidget(self._graph_view_widget)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._list_stack)
        self._stack.addWidget(self._graph_stack)
        self._stack.setCurrentWidget(self._list_stack)
        layout.addWidget(self._stack)

        bottom = QHBoxLayout()
        bottom.addStretch()
        self._refresh_btn = QPushButton(tr("Refresh"))
        self._refresh_btn.clicked.connect(self._refresh)
        bottom.addWidget(self._refresh_btn)
        layout.addLayout(bottom)

    def _set_view(self, graph: bool):
        was_graph = self._graph_view
        self._graph_view = graph
        if graph:
            self._search.hide()
            self._stack.setCurrentWidget(self._graph_stack)
            self._btn_list.setStyleSheet(TOGGLE_INACTIVE)
            self._btn_graph.setStyleSheet(TOGGLE_ACTIVE)
            self._build_graph()
        else:
            self._search.show()
            self._stack.setCurrentWidget(self._list_stack)
            self._btn_list.setStyleSheet(TOGGLE_ACTIVE)
            self._btn_graph.setStyleSheet(TOGGLE_INACTIVE)
            self._graph_timer.stop()
            if was_graph:
                self._refresh()

    # ── List View ────────────────────────────────────────────────────────

    def _refresh(self):
        self._all_kps = error_store.get_knowledge_points()
        scores = {s["name"]: s for s in error_store.get_ucb_queue()}
        freq = error_store.get_error_frequency()
        for kp in self._all_kps:
            name = kp["name"]
            kp["_errors"] = freq.get(name, 0)
            kp["_score"] = scores.get(name, {})
        self._all_kps.sort(key=lambda k: -(k.get("count", 0) * 0.5 + k.get("_errors", 0)))
        stats = error_store.get_all_stats()
        self._stats_label.setText(
            tr("{concepts} concepts, {errors} errors", concepts=stats['knowledge_points'], errors=stats['total_errors'])
        )
        if self._graph_view:
            self._build_graph()
        else:
            self._populate_list()
        self._auto_explain_new()

    def _populate_list(self, filter_text: str = ""):
        self._concept_list.clear()
        ft = filter_text.lower()
        for kp in self._all_kps:
            name = kp.get("name", "")
            if ft and ft not in name.lower():
                continue
            errs = kp.get("_errors", 0)
            label = f"  {name}"
            if errs:
                label += f"  ({errs})"
            item = QListWidgetItem(label)
            item.setSizeHint(item.sizeHint().grownBy(QMargins(0, 6, 0, 6)))
            if errs > 0:
                item.setForeground(QColor(EDGE_DANGLING))
            elif kp.get("count", 0) > 0:
                item.setForeground(QColor(SUCCESS))
            item.setData(Qt.ItemDataRole.UserRole, kp)
            self._concept_list.addItem(item)

    def _on_search(self, text: str):
        self._populate_list(text)

    def _on_select(self, idx: int):
        if idx < 0:
            return
        item = self._concept_list.item(idx)
        kp = item.data(Qt.ItemDataRole.UserRole)
        if not kp:
            return
        name = kp.get("name", "?")
        self._show_concept_detail(name)

    # ── Shared Detail Panel ──────────────────────────────────────────────

    def _show_concept_detail(self, name: str):
        self._selected_node = name
        kps = error_store.get_knowledge_points()
        kp = next((k for k in kps if k["name"] == name), None)
        if kp is None:
            kp = {"name": name, "count": 0, "source": "", "_errors": 0, "_score": {}}
        self._all_kps = kps

        clear_layout(self._detail_layout)
        self._detail_label.setText("")

        title = QLabel(name)
        title.setWordWrap(True)
        title.setStyleSheet(
            f"color: {STACK_BORDER}; font-size: 32px; font-weight: 800; "
            f"padding: 0 0 10px 0; border-bottom: 1px solid {BORDER};"
        )
        self._detail_layout.addWidget(title)

        source = kp.get("source", "")
        if source:
            src = QLabel(tr("via {source}", source=source))
            src.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; padding: 2px 0 8px 0;")
            self._detail_layout.addWidget(src)

        desc = kp.get("description", "")
        if desc:
            explanation = QLabel(_md_to_html(desc))
            explanation.setWordWrap(True)
            explanation.setTextFormat(Qt.TextFormat.RichText)
            explanation.setStyleSheet(
                f"color: {TEXT_PRIMARY}; font-size: 14px; line-height: 1.6; "
                f"padding: 8px 0;"
            )
            self._detail_layout.addWidget(explanation)
        else:
            self._detail_layout.addSpacing(8)
            self._add_explain_button(name)

        self._detail_layout.addSpacing(8)

        deps = error_store.get_dependencies(name)
        if deps:
            dep_label = QLabel(tr("Related: {deps}", deps=", ".join(deps)))
            dep_label.setWordWrap(True)
            dep_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; padding: 4px 0;")
            self._detail_layout.addWidget(dep_label)

        self._detail_layout.addSpacing(4)
        self._add_review_button(name)

        quiz_btn = QPushButton(tr("Quiz Me"))
        quiz_btn.setStyleSheet(
            f"QPushButton {{ background-color: transparent; "
            f"color: {ACCENT}; border: 1px solid {ACCENT}; "
            f"padding: 4px 14px; font-size: 11px; }}"
            f"QPushButton:hover {{ background-color: {ACCENT}; color: #FFFFFF; }}"
        )
        quiz_btn.clicked.connect(lambda: self._generate_quiz_for_concept(name, quiz_btn))
        self._detail_layout.addWidget(quiz_btn)

        del_btn = QPushButton(tr("Delete"))
        del_btn.setStyleSheet(
            f"QPushButton {{ background-color: transparent; "
            f"color: {TEXT_MUTED}; border: 1px solid {BORDER}; "
            f"padding: 4px 12px; font-size: 10px; }}"
            f"QPushButton:hover {{ color: {EDGE_DANGLING}; border-color: {EDGE_DANGLING}; }}"
        )
        del_btn.clicked.connect(lambda: self._delete_concept(name))
        self._detail_layout.addWidget(del_btn)

        self._detail_layout.addStretch()

    def _add_explain_button(self, concept_name: str):
        btn = QPushButton(tr("Explain with AI"))
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {ACCENT}; color: #FFFFFF; "
            f"border: none; padding: 8px 18px; font-size: 13px; }}"
            f"QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}"
        )

        def on_explain():
            kps = error_store.get_knowledge_points()
            cached = next((k.get("description", "") for k in kps if k["name"] == concept_name), "")
            if cached:
                explanation = QLabel(_md_to_html(cached))
                explanation.setWordWrap(True)
                explanation.setTextFormat(Qt.TextFormat.RichText)
                explanation.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; padding: 8px 0;")
                self._detail_layout.addWidget(explanation)
                self._detail_layout.addStretch()
                btn.hide()
                return

            btn.setEnabled(False)
            btn.setText(tr("Asking AI..."))
            if self._explain_worker is not None and self._explain_worker.isRunning():
                retire_worker(
                    self,
                    self._explain_worker,
                    disconnect=[
                        (self._explain_worker.finished, None),
                        (self._explain_worker.error, None),
                    ],
                )
            self._explain_worker = AIExplainWorker(EXPLAIN_PROMPT, f"请解释 C++ 知识点：{concept_name}")

            def on_done(text):
                if not shiboken6.isValid(btn):
                    return
                btn.setEnabled(True)
                btn.setText(tr("Explain with AI"))
                error_store.set_knowledge_description(concept_name, text)
                explanation = QLabel(_md_to_html(text))
                explanation.setWordWrap(True)
                explanation.setTextFormat(Qt.TextFormat.RichText)
                explanation.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; padding: 8px 0;")
                self._detail_layout.addWidget(explanation)
                self._detail_layout.addStretch()
                btn.hide()

            def on_err(msg):
                if not shiboken6.isValid(btn):
                    return
                btn.setEnabled(True)
                btn.setText(tr("Explain with AI (failed)"))

            self._explain_worker.finished.connect(on_done)
            self._explain_worker.error.connect(on_err)
            self._explain_worker.start()

        btn.clicked.connect(lambda: on_explain())
        self._detail_layout.addWidget(btn)

    def _add_review_button(self, name: str):
        btn = QPushButton(tr("Add to Review"))
        btn.setStyleSheet(
            f"QPushButton {{ background-color: transparent; "
            f"color: {EDGE_DANGLING}; border: 1px solid {EDGE_DANGLING}; "
            f"padding: 6px 14px; font-size: 12px; }}"
            f"QPushButton:hover {{ background-color: {EDGE_DANGLING}; color: #FFFFFF; }}"
        )

        def add():
            deck = error_store.suggest_deck(name)
            kps = error_store.get_knowledge_points()
            desc = next((k.get("description", "") for k in kps if k["name"] == name), "")
            if desc:
                question = tr("Review: {name}", name=name)
                correct = f"## {name}\n\n{desc}"
            else:
                question = tr("Review {name}", name=name)
                correct = tr("Study concept: {name}", name=name)
            error_store.add_error(
                knowledge_point=name,
                question=question,
                user_answer="",
                correct_answer=correct,
                deck=deck,
            )
            btn.setText("✓ " + tr("Added"))
            btn.setStyleSheet(
                f"QPushButton {{ background-color: #1A3A2A; color: #4EC9B0; "
                f"border: 1px solid #4EC9B0; padding: 4px 12px; font-size: 11px; }}"
            )
            btn.setEnabled(False)

        btn.clicked.connect(lambda: add())
        self._detail_layout.addWidget(btn)

    def _build_interactive_quiz(self, num: int, q: dict, kp_name: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {EDITOR_BG}; border: 1px solid {BORDER}; }}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        question = QLabel(f"Q{num}: {q.get('question', '')}")
        question.setWordWrap(True)
        question.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: bold;")
        layout.addWidget(question)

        options = q.get("options", [])
        answer_idx = q.get("answer", -1)
        labels = ["A", "B", "C", "D"]

        result_label = QLabel("")
        result_label.setVisible(False)
        layout.addWidget(result_label)

        answered = [False]

        def on_choice(choice_idx: int):
            if answered[0]:
                return
            answered[0] = True
            correct = (choice_idx == answer_idx)
            for b in btns:
                b.setEnabled(False)
            if correct:
                ans_text = f"{labels[answer_idx]}) {options[answer_idx]}" if 0 <= answer_idx < len(options) else ""
                result_label.setText("✓ " + tr("Correct!") + f"  {ans_text}")
                result_label.setStyleSheet(
                    f"color: #4EC9B0; font-size: 13px; font-weight: bold; padding: 4px 0;"
                )
            else:
                result_label.setText(
                    "✗ " + tr("Wrong - correct answer: {answer}",
                    answer=f"{labels[answer_idx]}) {options[answer_idx]}" if 0 <= answer_idx < len(options) else "?")
                )
                result_label.setStyleSheet(
                    f"color: {EDGE_DANGLING}; font-size: 13px; font-weight: bold; padding: 4px 0;"
                )
                add_btn = QPushButton(tr("Add to Review"))
                add_btn.setStyleSheet(
                    f"QPushButton {{ background-color: transparent; "
                    f"color: {EDGE_DANGLING}; border: 1px solid {EDGE_DANGLING}; "
                    f"padding: 3px 10px; font-size: 10px; margin-top: 2px; }}"
                    f"QPushButton:hover {{ background-color: {EDGE_DANGLING}; color: #FFFFFF; }}"
                )
                def save_error(q_text=q.get("question",""), o=options, a_i=answer_idx, c_i=choice_idx):
                    opts_text = "\n".join(f"  {labels[i]}) {o[i]}" for i in range(len(o)))
                    error_store.add_error(
                        knowledge_point=kp_name,
                        question=f"{q_text}\n\n{opts_text}",
                        user_answer=f"{labels[c_i]}) {o[c_i]}" if c_i < len(o) else "?",
                        correct_answer=f"{labels[a_i]}) {o[a_i]}" if 0 <= a_i < len(o) else "?",
                        deck=error_store.suggest_deck(kp_name),
                    )
                    add_btn.setText("✓ " + tr("Added"))
                    add_btn.setEnabled(False)
                add_btn.clicked.connect(lambda: save_error())
                layout.addWidget(add_btn)
            result_label.setVisible(True)

        btns = []
        for ci, opt in enumerate(options):
            btn = QPushButton(f"{labels[ci]}) {opt}")
            btn.setStyleSheet(
                f"QPushButton {{ background-color: transparent; color: {TEXT_PRIMARY}; "
                f"border: 1px solid {BORDER}; padding: 6px 10px; font-size: 12px; text-align: left; }}"
                f"QPushButton:hover {{ border-color: {ACCENT}; color: {TEXT_PRIMARY}; }}"
                f"QPushButton:disabled {{ color: {TEXT_MUTED}; border-color: {BORDER}; }}"
            )
            btn.clicked.connect(lambda checked, idx=ci: on_choice(idx))
            layout.addWidget(btn)
            btns.append(btn)

        return card

    def _delete_concept(self, name: str):
        error_store.delete_knowledge_point(name)
        self._refresh()
        clear_layout(self._detail_layout)
        self._detail_label.setText(tr("Select a concept"))

    def _auto_explain_new(self):
        """Auto-fetch AI explanation for the first concept without one."""
        if self._graph_view:
            return
        if hasattr(self, '_auto_explain_worker') and self._auto_explain_worker and self._auto_explain_worker.isRunning():
            return
        for kp in self._all_kps:
            if not kp.get("description"):
                name = kp["name"]
                self._auto_explain_worker = AIExplainWorker(EXPLAIN_PROMPT, f"请解释 C++ 知识点：{name}")
                def make_handler(concept_name=name):
                    def on_done(text):
                        error_store.set_knowledge_description(concept_name, text)
                        if self._selected_node == concept_name:
                            self._show_concept_detail(concept_name)
                    return on_done
                self._auto_explain_worker.finished.connect(make_handler())
                self._auto_explain_worker.start()
                break

    def _generate_quiz_for_concept(self, name: str, btn: QPushButton):
        kps = error_store.get_knowledge_points()
        desc = next((k.get("description", "") for k in kps if k["name"] == name), "")
        if not desc:
            self._detail_layout.addWidget(mlabel(tr("Please explain the concept with AI first."), TEXT_SECONDARY, 11))
            return

        btn.setEnabled(False)
        btn.setText(tr("Generating quiz..."))
        prompt = """你是 C++ 出题助手。根据以下知识点解释，出 2-3 道单选题。
输出 JSON 数组，每个元素都是对象：
[
  {
    "question": "题目",
    "options": ["选项A", "选项B", "选项C", "选项D"],
    "answer": 0,
    "explanation": "解析"
  }
]
直接输出 JSON，不要输出 markdown 代码块或解释文字。"""
        msg = f"知识点：{name}\n\n解释：{desc[:1500]}"

        from app.services.ai_explain_worker import AIExplainWorker
        if self._quiz_worker is not None and self._quiz_worker.isRunning():
            retire_worker(
                self,
                self._quiz_worker,
                disconnect=[
                    (self._quiz_worker.finished, None),
                    (self._quiz_worker.error, None),
                ],
            )
        self._quiz_worker = AIExplainWorker(prompt, msg)

        def on_done(text):
            import json
            if not shiboken6.isValid(btn):
                return
            btn.setEnabled(True)
            btn.setText(tr("Quiz Me"))
            try:
                text = text.strip()
                if text.startswith("```"):
                    parts = text.split("```")
                    text = parts[1] if len(parts) > 1 else text
                    if text.startswith("json"):
                        text = text[4:].strip()
                quizzes = json.loads(text)
                if isinstance(quizzes, dict):
                    quizzes = quizzes.get("quiz_questions", [quizzes])
                if not isinstance(quizzes, list):
                    quizzes = [quizzes]
            except json.JSONDecodeError:
                quizzes = []

            self._detail_layout.addSpacing(6)
            self._detail_layout.addWidget(mlabel(tr("Quiz"), ACCENT, 13, True))
            for i, q in enumerate(quizzes):
                self._detail_layout.addWidget(self._build_interactive_quiz(i + 1, q, name))
            self._detail_layout.addStretch()

        def on_err(msg):
            if not shiboken6.isValid(btn):
                return
            btn.setEnabled(True)
            btn.setText(tr("Quiz Me"))

        self._quiz_worker.finished.connect(on_done)
        self._quiz_worker.error.connect(on_err)
        self._quiz_worker.start()

    # ── Graph View ───────────────────────────────────────────────────────

    def _on_graph_node_clicked(self, name: str):
        self._show_concept_detail(name)
        self._search.hide()
        self._stack.setCurrentWidget(self._list_stack)
        self._graph_timer.stop()

    def _build_graph(self):
        self._graph_timer.stop()
        self._sim_tick = 0
        for e, _, _ in self._graph_edges:
            if e.scene() is not None:
                e.scene().removeItem(e)
        self._graph_edges.clear()
        for n in self._graph_nodes:
            if n.scene() is not None:
                n.scene().removeItem(n)
        self._graph_nodes.clear()
        self._graph_scene.clear()

        freq = error_store.get_error_frequency()
        kps = error_store.get_knowledge_points()
        stats = error_store.get_all_stats()
        self._stats_label.setText(
            tr(
                "{errored} errored concepts / {errors} errors / {learned} learned",
                errored=len(freq),
                errors=stats['total_errors'],
                learned=stats['knowledge_points'],
            )
        )

        all_names: dict[str, int] = {}
        for name, count in freq.items():
            all_names[name] = all_names.get(name, 0) + count * 3
        for kp_item in kps:
            name = kp_item["name"]
            all_names[name] = all_names.get(name, 0) + kp_item.get("count", 1)

        if not all_names:
            placeholder = QGraphicsTextItem(tr("No data yet - use OJ Analysis or File Import to build knowledge"))
            placeholder.setDefaultTextColor(QColor(TEXT_PRIMARY))
            placeholder.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 14))
            placeholder.setPos(-250, -20)
            self._graph_scene.addItem(placeholder)
            return

        items = sorted(all_names.items(), key=lambda x: -x[1])
        max_w = max(w for _, w in items) if items else 1

        for i, (name, weight) in enumerate(items):
            angle = (i / max(len(items), 1)) * 2 * math.pi
            r_base = 180 + random.uniform(-30, 30)
            x = r_base * math.cos(angle)
            y = r_base * math.sin(angle)
            radius = 22 + (weight / max(max_w, 1)) * 35
            ratio = weight / max(max_w, 1)
            r = int(200 * ratio)
            g = int(100 * (1 - ratio))
            b = int(255 * (1 - ratio))
            color = QColor(min(r, 255), min(g, 255), min(b, 255))
            node = GraphNode(x, y, radius, name, color,
                             on_clicked=self._on_graph_node_clicked)
            self._graph_scene.addItem(node)
            self._graph_nodes.append(node)

        name_to_node = {n.label: n for n in self._graph_nodes}
        seen = set()
        for parent_name, parent_node in name_to_node.items():
            for child_name in error_store.get_dependencies(parent_name):
                child_node = name_to_node.get(child_name)
                if child_node is None:
                    continue
                key = tuple(sorted((parent_name, child_name)))
                if key in seen:
                    continue
                seen.add(key)
                edge = QGraphicsLineItem(
                    parent_node.pos().x(), parent_node.pos().y(),
                    child_node.pos().x(), child_node.pos().y(),
                )
                edge.setPen(QPen(QColor("#444444"), 1))
                edge.setZValue(-1)
                self._graph_scene.addItem(edge)
                self._graph_edges.append((edge, parent_node, child_node))

        self._graph_timer.start(30)

    def _simulate(self):
        if not self._graph_nodes:
            self._graph_timer.stop()
            return

        self._sim_tick = getattr(self, '_sim_tick', 0) + 1
        if self._sim_tick > 200:
            self._graph_timer.stop()
            self._sim_tick = 0
            return

        cx = sum(n.pos().x() for n in self._graph_nodes) / len(self._graph_nodes)
        cy = sum(n.pos().y() for n in self._graph_nodes) / len(self._graph_nodes)

        ideal_dist = 240.0
        for n in self._graph_nodes:
            n.vx += (cx - n.pos().x()) * 0.003
            n.vy += (cy - n.pos().y()) * 0.003

        for i, a in enumerate(self._graph_nodes):
            for j, b in enumerate(self._graph_nodes):
                if i >= j:
                    continue
                dx = b.pos().x() - a.pos().x()
                dy = b.pos().y() - a.pos().y()
                dist = math.hypot(dx, dy) or 1
                ux = dx / dist
                uy = dy / dist

                if dist < ideal_dist * 0.7:
                    f = 300 / (dist * dist)
                elif dist > ideal_dist * 1.5:
                    f = -0.0003 * (dist - ideal_dist * 1.5)
                else:
                    f = 0.0

                a.vx -= f * ux
                a.vy -= f * uy
                b.vx += f * ux
                b.vy += f * uy

        for _, parent, child in self._graph_edges:
            dx = child.pos().x() - parent.pos().x()
            dy = child.pos().y() - parent.pos().y()
            dist = math.hypot(dx, dy) or 1
            f = 0.002 * dist
            parent.vx += f * dx / dist
            parent.vy += f * dy / dist
            child.vx -= f * dx / dist
            child.vy -= f * dy / dist

        for n in self._graph_nodes:
            max_v = 8.0
            n.vx = max(-max_v, min(max_v, n.vx))
            n.vy = max(-max_v, min(max_v, n.vy))
            n.vx *= 0.92
            n.vy *= 0.92
            n.setPos(n.pos().x() + n.vx, n.pos().y() + n.vy)

        for edge, p, c in self._graph_edges:
            edge.setLine(p.pos().x(), p.pos().y(), c.pos().x(), c.pos().y())

        total_v = sum(abs(n.vx) + abs(n.vy) for n in self._graph_nodes)
        if total_v < 0.5:
            self._graph_timer.stop()
            self._sim_tick = 0

    def retranslate_ui(self):
        self._header_label.setText(tr("Knowledge Base"))
        self._btn_list.setText(tr("List"))
        self._btn_graph.setText(tr("Graph"))
        self._search.setPlaceholderText(tr("Search concepts..."))
        self._refresh_btn.setText(tr("Refresh"))
        if self._selected_node:
            self._show_concept_detail(self._selected_node)
        elif self._concept_list.currentRow() < 0:
            self._detail_label.setText(tr("Select a concept"))
        self._refresh()
