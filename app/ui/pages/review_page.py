from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTextEdit, QDialog, QLineEdit,
    QDialogButtonBox, QComboBox, QSizePolicy, QScrollArea,
    QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QTextDocument, QIcon

from app.services import error_store
from app.services import export_service
from app.services.ai_explain_worker import AIExplainWorker, HINT_PROMPT
from app.services.i18n import tr
from app.ui.widgets.helpers import mlabel, clear_layout
from app.ui.widgets.empty_state import PixelEmptyState
from app.ui.widgets.threading import retire_worker
import shiboken6
from app.ui.theme.colors import (
    CANVAS_BG, SURFACE, BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    STACK_BORDER, HEAP_BORDER, ACCENT, EDGE_DANGLING, SUCCESS, SUCCESS_BG,
    TEXT_INVERSE, TEXT_BUTTON_PRIMARY, ERROR_BG, WARN, WARN_BG, INFO, INFO_BG,
)
from app.ui.theme.minecraft_assets import asset_path


def _fmt_interval(days: float) -> str:
    if days < 1:
        return "<10m"
    if days == 1:
        return "1d"
    if days < 30:
        return f"{int(days)}d"
    months = days / 30
    if months < 12:
        return f"{months:.1f}mo"
    return f"{days / 365:.1f}y"


def _predict_sm2(n: int, ef: float, interval: int, quality: int) -> str:
    if quality < 3:
        return "<10m"
    if n == 0:
        next_i = 1
    elif n == 1:
        next_i = 6
    else:
        next_i = round(interval * ef)
    new_ef = ef + (0.1 - (3 - quality) * (0.08 + (3 - quality) * 0.02))
    new_ef = max(1.3, new_ef)
    return _fmt_interval(max(1, next_i))


RATE_STYLES = {
    "again": (
        f"QPushButton {{ background-color: {ERROR_BG}; color: {EDGE_DANGLING}; "
        f"border: 2px solid {EDGE_DANGLING}; "
        f"padding: 12px 20px; font-size: 15px; font-weight: bold; }}"
        f"QPushButton:hover {{ background-color: {EDGE_DANGLING}; color: {TEXT_BUTTON_PRIMARY}; }}"
    ),
    "hard": (
        f"QPushButton {{ background-color: {WARN_BG}; color: {WARN}; "
        f"border: 2px solid {WARN}; "
        f"padding: 12px 20px; font-size: 15px; font-weight: bold; }}"
        f"QPushButton:hover {{ background-color: {WARN}; color: {TEXT_BUTTON_PRIMARY}; }}"
    ),
    "good": (
        f"QPushButton {{ background-color: {SUCCESS_BG}; color: {SUCCESS}; "
        f"border: 2px solid {SUCCESS}; "
        f"padding: 12px 20px; font-size: 15px; font-weight: bold; }}"
        f"QPushButton:hover {{ background-color: {SUCCESS}; color: {TEXT_BUTTON_PRIMARY}; }}"
    ),
    "easy": (
        f"QPushButton {{ background-color: {INFO_BG}; color: {INFO}; "
        f"border: 2px solid {INFO}; "
        f"padding: 12px 20px; font-size: 15px; font-weight: bold; }}"
        f"QPushButton:hover {{ background-color: {INFO}; color: {TEXT_BUTTON_PRIMARY}; }}"
    ),
}

CARD_STYLE = (
    f"QFrame#reviewCard {{ background-color: {SURFACE}; border: 2px solid {BORDER}; "
    f"}}"
    f"QFrame#reviewCard QLabel {{ border: none; background: transparent; outline: none; }}"
)

NOTES_STYLE = (
    f"QTextEdit {{ background-color: {CANVAS_BG}; color: {TEXT_PRIMARY}; "
    f"border: 1px solid {BORDER}; padding: 8px; "
    f"font-size: 14px; }}"
)


class ReviewScrollArea(QScrollArea):
    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            delta = event.angleDelta().y() or event.angleDelta().x()
            if delta:
                bar = self.horizontalScrollBar()
                step = max(24, bar.singleStep())
                bar.setValue(bar.value() - int(delta / 120) * step)
                event.accept()
                return
        super().wheelEvent(event)


class ReviewPage(QWidget):
    _session_limit = 20

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: list[dict] = []
        self._current_idx = 0
        self._answer_revealed = False
        self._notes_edit: QTextEdit | None = None
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(600)
        self._save_timer.timeout.connect(self._flush_notes)
        self._pending_card_id: str = ""
        self._hint_worker: AIExplainWorker | None = None
        self._cls_worker: AIExplainWorker | None = None
        self._retired_workers: list[AIExplainWorker] = []
        self._current_deck: str = ""
        self._card_frame: QFrame | None = None
        self._card_scroll: ReviewScrollArea | None = None
        self._card_content: QWidget | None = None
        self._question_label: QLabel | None = None
        self._user_answer_label: QLabel | None = None
        self._hint_label: QLabel | None = None
        self._answer_widget: QWidget | None = None
        self._answer_rich_text = False
        self._answer_text = ""
        self._setup_ui()
        self._auto_classify_uncategorized()
        self._populate_deck_combo()
        self._load_cards()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)

        header = QHBoxLayout()
        self._header_label = mlabel(tr("Review"), STACK_BORDER, 18, True)
        header.addWidget(self._header_label)
        header.addSpacing(12)

        self._deck_combo = QComboBox()
        self._deck_combo.setMinimumWidth(200)
        self._deck_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._deck_combo.currentTextChanged.connect(self._on_deck_changed)
        header.addWidget(self._deck_combo)

        header.addStretch()

        self._add_btn = QPushButton(tr("+ Add"))
        self._add_btn.setProperty("variant", "secondary")
        self._add_btn.setIcon(QIcon(asset_path("icons", "action_add")))
        self._add_btn.setIconSize(QSize(18, 18))
        self._add_btn.clicked.connect(self._on_add_error)
        header.addWidget(self._add_btn)

        self._export_md_btn = QPushButton(tr("Export Markdown"))
        self._export_md_btn.setProperty("variant", "secondary")
        self._export_md_btn.clicked.connect(self._export_markdown)
        header.addWidget(self._export_md_btn)

        self._export_anki_btn = QPushButton(tr("Export Anki Deck"))
        self._export_anki_btn.setProperty("variant", "secondary")
        self._export_anki_btn.clicked.connect(self._export_anki)
        header.addWidget(self._export_anki_btn)

        layout.addLayout(header)

        self._progress = mlabel("", TEXT_SECONDARY, 12)
        self._progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._progress)

        self._card_area = QVBoxLayout()
        layout.addLayout(self._card_area, 1)

        self._empty_state = QVBoxLayout()
        layout.addLayout(self._empty_state)

        layout.addStretch()
        self._render_empty_or_card()

    def _load_cards(self):
        if self._current_deck:
            self._cards = error_store.get_due_cards_by_deck(self._current_deck)
        else:
            self._cards = error_store.get_due_cards()
        if len(self._cards) > self._session_limit:
            self._cards = self._cards[:self._session_limit]
        self._current_idx = 0
        self._answer_revealed = False
        self._render_empty_or_card()

    def _on_deck_changed(self, text: str):
        if text == "All Decks":
            text = ""
        else:
            # Strip count suffix e.g. "指针与内存 (3)" → "指针与内存"
            idx = text.rfind(" (")
            if idx > 0:
                text = text[:idx]
        self._current_deck = text
        self._populate_deck_combo()
        self._load_cards()

    def _populate_deck_combo(self):
        self._deck_combo.blockSignals(True)
        self._deck_combo.clear()
        self._deck_combo.addItem("All Decks")
        due_all = len(error_store.get_due_cards())
        if not self._current_deck:
            self._deck_combo.setItemText(0, f"All Decks ({due_all})")
        for deck in error_store.get_decks():
            count = len(error_store.get_due_cards_by_deck(deck))
            self._deck_combo.addItem(f"{deck} ({count})")
        if self._current_deck:
            for i in range(self._deck_combo.count()):
                if self._current_deck in self._deck_combo.itemText(i):
                    self._deck_combo.setCurrentIndex(i)
                    break
        self._deck_combo.blockSignals(False)

    def _auto_classify_uncategorized(self):
        """Use AI to classify cards without a deck."""
        uncategorized = error_store.get_uncategorized_cards()
        if not uncategorized:
            self._populate_deck_combo()
            return
        batch = uncategorized[:5]
        kps = list(set(e.get("knowledge_point", "") for e in batch if e.get("knowledge_point")))
        if not kps:
            return

        prompt = """你是 C++ 知识分类助手。将以下知识点归入最合适的类别。
可用类别：指针与内存、面向对象、STL容器、基础语法、其他
对于每个知识点，只输出 "知识点名 -> 类别"，每行一个。不要任何解释。"""
        msg = "\n".join(kps)

        def on_done(text):
            mapping = {}
            for line in text.strip().splitlines():
                if "->" in line:
                    parts = line.split("->")
                    if len(parts) == 2:
                        mapping[parts[0].strip()] = parts[1].strip()
            for entry in batch:
                kp = entry.get("knowledge_point", "")
                deck = mapping.get(kp, "")
                if deck and deck in ("指针与内存", "面向对象", "STL容器", "基础语法", "其他"):
                    error_store.update_deck(entry["id"], deck)
            self._populate_deck_combo()

        self._cls_worker = AIExplainWorker(prompt, msg)
        self._cls_worker.finished.connect(on_done)
        self._cls_worker.start()

    def _render_empty_or_card(self):
        self._clear_card_area()
        clear_layout(self._empty_state)

        if not self._cards:
            self._progress.setText("")
            self._empty_state.addStretch()
            empty = PixelEmptyState(
                "empty_chest",
                tr("No cards due - great job!"),
                tr("Come back later or add errors via OJ / File Import"),
            )
            self._empty_state.addWidget(empty)
            self._empty_state.addStretch()
            return

        self._render_card(self._cards[self._current_idx])

    def _clear_card_area(self):
        self._card_frame = None
        self._card_scroll = None
        self._card_content = None
        self._question_label = None
        self._user_answer_label = None
        self._hint_label = None
        self._answer_widget = None
        self._answer_rich_text = False
        self._answer_text = ""
        while self._card_area.count():
            item = self._card_area.takeAt(0)
            if item.layout():
                self._recursive_delete_layout(item.layout())
            elif item.widget():
                item.widget().deleteLater()

    @staticmethod
    def _recursive_delete_layout(layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.layout():
                ReviewPage._recursive_delete_layout(child.layout())
            elif child.widget():
                child.widget().deleteLater()
        layout.deleteLater()

    def _render_card(self, card: dict):
        n_cards = len(self._cards)
        idx = self._current_idx
        self._progress.setText(
            f"{idx + 1} / {n_cards}" if n_cards > 1 else ""
        )
        self._answer_revealed = False

        main = QVBoxLayout()
        main.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        c = QFrame()
        self._card_frame = c
        c.setObjectName("reviewCard")
        c.setStyleSheet(CARD_STYLE)
        c.setMinimumWidth(680)
        c.setMaximumWidth(680)
        c.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        card_layout = QVBoxLayout(c)
        card_layout.setContentsMargins(0, 0, 0, 0)

        scroll = ReviewScrollArea()
        self._card_scroll = scroll
        scroll.setWidgetResizable(False)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background: transparent; }}"
            f"QScrollArea > QWidget > QWidget {{ background: transparent; }}"
        )

        scroll_content = QWidget()
        self._card_content = scroll_content
        v = QVBoxLayout(scroll_content)
        v.setContentsMargins(28, 28, 18, 28)
        v.setSpacing(16)
        scroll.setWidget(scroll_content)
        card_layout.addWidget(scroll)

        kp = card.get("knowledge_point", "")
        if kp:
            kpl = QLabel(kp)
            kpl.setWordWrap(True)
            kpl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
            kpl.setStyleSheet(
                f"color: {HEAP_BORDER}; font-size: 14px; font-weight: bold; "
                f"background-color: {WARN_BG}; "
                f"padding: 6px 14px;"
            )
            v.addWidget(kpl, alignment=Qt.AlignmentFlag.AlignCenter)

        qtext = card.get("question", "")
        ql = QLabel(qtext)
        self._question_label = ql
        ql.setWordWrap(True)
        ql.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ql.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        ql.setMargin(10)
        ql.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 700; "
            f"padding: 0;"
        )
        v.addWidget(ql)

        user_ans = card.get("user_answer", "")
        if user_ans:
            ul = QLabel(tr("Your answer: {answer}", answer=user_ans))
            self._user_answer_label = ul
            ul.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ul.setMargin(6)
            ul.setStyleSheet(
                f"color: {EDGE_DANGLING}; font-size: 13px; font-weight: 600; font-style: italic; padding: 0;"
            )
            v.addWidget(ul)

        v.addSpacing(12)

        hint_btn = QPushButton(tr("Hint"))
        hint_btn.setIcon(QIcon(asset_path("icons", "action_hint")))
        hint_btn.setIconSize(QSize(18, 18))
        hint_btn.setStyleSheet(
            f"QPushButton {{ background-color: transparent; "
            f"color: {ACCENT}; border: 2px solid {ACCENT}; "
            f"padding: 6px 16px; font-size: 14px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {ACCENT}; color: {TEXT_BUTTON_PRIMARY}; }}"
        )
        q_text = card.get("question", "")
        kp_text = card.get("knowledge_point", "")
        hint_label = QLabel("")
        self._hint_label = hint_label
        hint_label.setWordWrap(True)
        hint_label.setVisible(False)
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setMargin(6)
        hint_label.setStyleSheet(f"color: {ACCENT}; font-size: 14px; font-weight: 600; padding: 0;")
        hint_btn.clicked.connect(self._make_hint_handler(hint_btn, hint_label, kp_text, q_text))
        v.addWidget(hint_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        v.addWidget(hint_label)

        v.addSpacing(8)

        reveal_btn = QPushButton(tr("Show Answer"))
        reveal_btn.clicked.connect(lambda: self._reveal_answer(card))
        v.addWidget(reveal_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self._reveal_area = QVBoxLayout()
        v.addLayout(self._reveal_area, 1)

        main.addWidget(c, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._card_area.addLayout(main, 1)
        self._schedule_card_geometry_refresh()

    def _update_card_geometry(self):
        if self._card_frame is None or self._card_scroll is None or self._card_content is None:
            return

        available_width = max(420, self.width() - 64)
        preferred_content_width = self._preferred_content_width()
        frame_width = min(max(680, preferred_content_width + 56), available_width)
        frame_width = max(420, frame_width)

        margins = self.layout().contentsMargins() if self.layout() else None
        top_margin = margins.top() if margins else 0
        bottom_margin = margins.bottom() if margins else 0
        progress_bottom = self._progress.geometry().bottom() if self._progress is not None else 0
        reserved_height = progress_bottom + top_margin + bottom_margin + 40
        available_height = max(260, self.height() - reserved_height)

        scrollbar_width = self._card_scroll.verticalScrollBar().sizeHint().width()
        viewport_width = max(320, frame_width - 2)
        content_width = max(viewport_width - scrollbar_width - 24, preferred_content_width)

        self._card_frame.setMinimumWidth(frame_width)
        self._card_frame.setMaximumWidth(frame_width)
        self._card_frame.setMaximumHeight(available_height)
        self._card_scroll.setMinimumWidth(frame_width - 2)
        self._card_scroll.setMaximumHeight(max(220, available_height - 2))
        self._card_content.setMinimumWidth(content_width)
        self._card_content.resize(content_width, self._card_content.sizeHint().height())
        self._refresh_text_layouts(content_width)

    def _refresh_text_layouts(self, content_width: int):
        text_widgets = [
            self._question_label,
            self._user_answer_label,
            self._hint_label,
            self._answer_widget if isinstance(self._answer_widget, QLabel) else None,
        ]
        usable_width = max(160, content_width - 24)
        for widget in text_widgets:
            if widget is None:
                continue
            margin = widget.margin() * 2
            target_width = max(120, usable_width - margin)
            widget.setMinimumWidth(target_width)
            widget.setMaximumWidth(target_width)
            widget.updateGeometry()
            widget.adjustSize()
            height = widget.heightForWidth(target_width)
            if height > 0:
                widget.setMinimumHeight(height + margin + 4)
        self._card_content.adjustSize()
        self._card_content.resize(content_width, self._card_content.sizeHint().height())

    def _schedule_card_geometry_refresh(self):
        QTimer.singleShot(0, self._update_card_geometry)
        QTimer.singleShot(50, self._update_card_geometry)

    def _preferred_content_width(self) -> int:
        preferred = 620
        if self._answer_revealed and self._answer_text:
            preferred = max(preferred, self._estimate_answer_width())
        return min(preferred, 1800)

    def _estimate_answer_width(self) -> int:
        if not self._answer_text:
            return 620
        if self._answer_rich_text:
            doc = QTextDocument()
            if self._answer_widget is not None:
                doc.setDefaultFont(self._answer_widget.font())
            doc.setHtml(self._answer_text)
            return int(doc.idealWidth()) + 48

        lines = self._answer_text.splitlines() or [self._answer_text]
        metrics = self.fontMetrics()
        return max(metrics.horizontalAdvance(line) for line in lines) + 72

    def _make_hint_handler(self, btn, label, kp_text, q_text):
        def on_hint():
            btn.setEnabled(False)
            btn.setText(tr("Thinking..."))
            if self._hint_worker is not None and self._hint_worker.isRunning():
                retire_worker(
                    self,
                    self._hint_worker,
                    disconnect=[
                        (self._hint_worker.finished, None),
                        (self._hint_worker.error, None),
                    ],
                )
            self._hint_worker = AIExplainWorker(
                HINT_PROMPT,
                f"知识点：{kp_text}\n题目：{q_text}\n请给提示",
            )
            def on_done(text):
                if not shiboken6.isValid(btn) or not shiboken6.isValid(label):
                    return
                btn.setEnabled(True)
                btn.setText(tr("Hint"))
                label.setText(tr("Hint: {hint}", hint=text))
                label.setVisible(True)
            def on_err(msg):
                if not shiboken6.isValid(btn):
                    return
                btn.setEnabled(True)
                btn.setText(tr("Hint (failed)"))
            self._hint_worker.finished.connect(on_done)
            self._hint_worker.error.connect(on_err)
            self._hint_worker.start()
        return lambda: on_hint()

    def _reveal_answer(self, card: dict):
        if self._answer_revealed:
            return
        self._answer_revealed = True

        clear_layout(self._reveal_area)

        correct = card.get("correct_answer", "")

        if correct.startswith("## ") or "```" in correct or "<br>" in correct:
            from app.ui.pages.knowledge_page import _md_to_html
            html = _md_to_html(correct)
            al = QLabel(html)
            al.setTextFormat(Qt.TextFormat.RichText)
            self._answer_rich_text = True
            self._answer_text = html
        else:
            al = QLabel(tr("Correct: {answer}", answer=correct))
            self._answer_rich_text = False
            self._answer_text = tr("Correct: {answer}", answer=correct)
        al.setWordWrap(True)
        al.setMargin(16)
        al.setStyleSheet(
            f"color: {SUCCESS}; font-size: 17px; font-weight: 700; "
            f"background-color: {SUCCESS_BG}; "
            f"padding: 0; border-bottom: 2px solid {SUCCESS};"
        )
        self._answer_widget = al
        self._reveal_area.addWidget(al)

        notes = card.get("notes", "")
        self._notes_edit = QTextEdit()
        self._notes_edit.setStyleSheet(NOTES_STYLE)
        self._notes_edit.setPlainText(notes)
        self._notes_edit.setMaximumHeight(60)
        self._notes_edit.setPlaceholderText(tr("Notes..."))
        self._pending_card_id = card["id"]
        self._notes_edit.textChanged.connect(
            lambda: self._save_timer.start()
        )
        self._reveal_area.addWidget(self._notes_edit)

        self._reveal_area.addSpacing(8)

        n = card.get("n", 0)
        ef = card.get("ef", 2.5)
        interval = card.get("interval", 1)

        rating_labels = [
            ("Again",    "again", 0),
            ("Hard",     "hard",  2),
            ("Good",     "good",  3),
            ("Easy",     "easy",  5),
        ]

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for label, style_key, quality in rating_labels:
            est = _predict_sm2(n, ef, interval, quality)
            btn = QPushButton(f"{tr(label)}\n({est})")
            btn.setStyleSheet(RATE_STYLES[style_key])
            btn.clicked.connect(
                lambda checked=None, q=quality: self._rate_and_next(card["id"], q)
            )
            btn_row.addWidget(btn)

        self._reveal_area.addLayout(btn_row)
        if self._card_content is not None:
            self._card_content.adjustSize()
        self._schedule_card_geometry_refresh()

    def _flush_notes(self):
        if self._notes_edit and self._pending_card_id:
            error_store.update_notes(
                self._pending_card_id, self._notes_edit.toPlainText()
            )

    def _rate_and_next(self, eid: str, quality: int):
        self._flush_notes()
        error_store.schedule_review(eid, quality)
        self._cards.pop(self._current_idx)
        if self._current_idx >= len(self._cards):
            self._current_idx = 0
        self._notes_edit = None
        self._pending_card_id = ""
        self._populate_deck_combo()
        self._render_empty_or_card()

    def _on_add_error(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Add Card"))
        dialog.setMinimumWidth(420)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(tr("Knowledge Point:")))
        kp_edit = QLineEdit()
        kp_edit.setPlaceholderText(tr("e.g. Pointers, STL..."))
        layout.addWidget(kp_edit)
        layout.addWidget(QLabel(tr("Question:")))
        q_edit = QTextEdit()
        q_edit.setPlaceholderText(tr("What did you get wrong?"))
        q_edit.setMaximumHeight(80)
        layout.addWidget(q_edit)
        layout.addWidget(QLabel(tr("Correct Answer:")))
        a_edit = QLineEdit()
        a_edit.setPlaceholderText(tr("The right answer"))
        layout.addWidget(a_edit)
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            kp = kp_edit.text().strip() or tr("manual")
            q = q_edit.toPlainText().strip() or tr("Manual entry")
            a = a_edit.text().strip() or ""
            error_store.add_error(kp, q, "", a, "", deck=error_store.suggest_deck(kp))
            self._populate_deck_combo()
        self._load_cards()

    def _export_cards(self) -> list[dict]:
        cards = error_store.get_errors()
        if self._current_deck:
            cards = [card for card in cards if card.get("deck", "") == self._current_deck]
        return cards

    def _export_markdown(self):
        cards = self._export_cards()
        if not cards:
            QMessageBox.information(self, tr("Export Markdown"), tr("No review cards to export."))
            return
        default_base = export_service.safe_filename(self._current_deck, "review_cards")
        default_name = "review_cards.md" if not self._current_deck else f"{default_base}_review_cards.md"
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Export Markdown"),
            default_name,
            f"{tr('Markdown Files')} (*.md);;{tr('All Files')} (*)",
        )
        if not path:
            return
        try:
            export_service.write_review_markdown(path, cards, self._current_deck)
            QMessageBox.information(self, tr("Export Markdown"), tr("Markdown exported: {path}", path=path))
        except Exception as exc:
            QMessageBox.warning(self, tr("Export failed"), str(exc))

    def _export_anki(self):
        cards = self._export_cards()
        if not cards:
            QMessageBox.information(self, tr("Export Anki Deck"), tr("No review cards to export."))
            return
        default_base = export_service.safe_filename(self._current_deck, "review_cards")
        default_name = "review_cards.apkg" if not self._current_deck else f"{default_base}_review_cards.apkg"
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Export Anki Deck"),
            default_name,
            f"{tr('Anki Deck')} (*.apkg);;{tr('All Files')} (*)",
        )
        if not path:
            return
        try:
            deck_name = "C++rafting Table::Review"
            if self._current_deck:
                deck_name += f"::{self._current_deck}"
            export_service.write_review_anki(path, cards, deck_name)
            QMessageBox.information(self, tr("Export Anki Deck"), tr("Anki deck exported: {path}", path=path))
        except Exception as exc:
            QMessageBox.warning(self, tr("Export failed"), str(exc))

    def _refresh(self):
        self._populate_deck_combo()
        self._load_cards()

    def retranslate_ui(self):
        self._header_label.setText(tr("Review"))
        self._add_btn.setText(tr("+ Add"))
        self._export_md_btn.setText(tr("Export Markdown"))
        self._export_anki_btn.setText(tr("Export Anki Deck"))
        self._render_empty_or_card()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule_card_geometry_refresh()
