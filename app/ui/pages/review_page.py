from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSplitter, QFrame, QTextEdit, QDialog, QLineEdit,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt, QTimer

from app.services import error_store
from app.services.ai_explain_worker import AIExplainWorker, HINT_PROMPT
from app.ui.widgets.helpers import mlabel, clear_layout
from app.ui.theme.colors import (
    CANVAS_BG, SURFACE, BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    STACK_BORDER, HEAP_BORDER, ACCENT, EDGE_DANGLING, SUCCESS,
)


RATE_GOOD = (
    f"QPushButton {{ background-color: #1A3A2A; color: {SUCCESS}; "
    f"border: 1px solid {SUCCESS}; border-radius: 8px; "
    f"padding: 10px 28px; font-size: 14px; font-weight: bold; }}"
    f"QPushButton:hover {{ background-color: #2A4A3A; }}"
)
RATE_AGAIN = (
    f"QPushButton {{ background-color: #3A1A1A; color: {EDGE_DANGLING}; "
    f"border: 1px solid {EDGE_DANGLING}; border-radius: 8px; "
    f"padding: 10px 28px; font-size: 14px; font-weight: bold; }}"
    f"QPushButton:hover {{ background-color: #4A2A2A; }}"
)
CARD = (
    f"QFrame {{ background-color: {SURFACE}; border: 1px solid {BORDER}; "
    f"border-radius: 12px; }}"
)
REVEAL_BTN = (
    f"QPushButton {{ background-color: {CANVAS_BG}; color: {ACCENT}; "
    f"border: 1px solid {ACCENT}; border-radius: 8px; padding: 8px 24px; "
    f"font-size: 13px; }}"
    f"QPushButton:hover {{ background-color: {ACCENT}; color: #FFFFFF; }}"
)
NOTES_STYLE = (
    f"QTextEdit {{ background-color: {CANVAS_BG}; color: {TEXT_PRIMARY}; "
    f"border: 1px solid {BORDER}; border-radius: 6px; padding: 8px; "
    f"font-size: 12px; }}"
)


class ReviewPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: list[dict] = []
        self._current_idx = 0
        self._answer_revealed = False
        self._setup_ui()
        self._load_cards()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.addWidget(mlabel("Review", STACK_BORDER, 16, True))
        header.addSpacing(12)
        self._add_btn = QPushButton("+ Add Error")
        self._add_btn.clicked.connect(self._on_add_error)
        header.addWidget(self._add_btn)

        self._queue_btn = QPushButton("Smart Queue")
        self._queue_btn.clicked.connect(self._on_show_queue)
        header.addWidget(self._queue_btn)

        header.addStretch()
        self._progress = mlabel("", TEXT_SECONDARY, 12)
        header.addWidget(self._progress)
        layout.addLayout(header)

        self._card_area = QVBoxLayout()
        layout.addLayout(self._card_area, 1)

        self._empty_state = QVBoxLayout()
        layout.addLayout(self._empty_state)

        self._render_empty_or_card()

    def _load_cards(self):
        self._cards = error_store.get_due_cards()
        self._current_idx = 0
        self._answer_revealed = False
        self._render_empty_or_card()

    def _render_empty_or_card(self):
        clear_layout(self._card_area)
        clear_layout(self._empty_state)

        if not self._cards:
            self._progress.setText("")
            done = mlabel("No cards due — great job!", SUCCESS, 14, True)
            done.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._empty_state.addStretch()
            self._empty_state.addWidget(done)
            self._empty_state.addWidget(mlabel(
                "Come back later or add errors via OJ / File Import",
                TEXT_SECONDARY, 12
            ))
            self._empty_state.addStretch()
            return

        self._render_card(self._cards[self._current_idx])

    def _render_card(self, card: dict):
        self._progress.setText(
            f"Card {self._current_idx + 1} of {len(self._cards)}"
        )
        self._answer_revealed = False

        c = QFrame()
        c.setStyleSheet(CARD)
        v = QVBoxLayout(c)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(12)

        kp = card.get("knowledge_point", "")
        if kp:
            kpl = QLabel(kp)
            kpl.setStyleSheet(
                f"color: {HEAP_BORDER}; font-size: 13px; font-weight: bold; "
                f"background-color: #3D2916; border-radius: 6px; "
                f"padding: 4px 12px;"
            )
            kpl.setWordWrap(True)
            v.addWidget(kpl)

        qtext = card.get("question", "")
        ql = QLabel(qtext)
        ql.setWordWrap(True)
        ql.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 16px; "
            f"padding: 8px 0;"
        )
        v.addWidget(ql)

        user_ans = card.get("user_answer", "")
        if user_ans:
            ul = QLabel(f"Your answer: {user_ans}")
            ul.setStyleSheet(
                f"color: {EDGE_DANGLING}; font-size: 12px; font-style: italic;"
            )
            v.addWidget(ul)

        v.addStretch()

        reveal_widget = QWidget()
        reveal_widget.setObjectName("reveal_area")
        reveal_layout = QVBoxLayout(reveal_widget)
        reveal_layout.setContentsMargins(0, 0, 0, 0)
        reveal_layout.setSpacing(8)

        reveal_btn = QPushButton("Show Answer")
        reveal_btn.setStyleSheet(REVEAL_BTN)
        reveal_layout.addWidget(reveal_btn)

        self._reveal_stack = QVBoxLayout()
        reveal_layout.addLayout(self._reveal_stack)

        reveal_btn.clicked.connect(
            lambda: self._reveal_answer(card)
        )

        v.addWidget(reveal_widget)
        self._card_area.addWidget(c)

    def _reveal_answer(self, card: dict):
        if self._answer_revealed:
            return
        self._answer_revealed = True

        clear_layout(self._reveal_stack)

        correct = card.get("correct_answer", "")
        al = QLabel(f"Correct: {correct}")
        al.setWordWrap(True)
        al.setStyleSheet(
            f"color: {SUCCESS}; font-size: 15px; font-weight: bold; "
            f"background-color: #1A2A22; border-radius: 6px; "
            f"padding: 12px;"
        )
        self._reveal_stack.addWidget(al)

        notes = card.get("notes", "")
        nl = QLabel("Notes (edit below):")
        nl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; padding-top: 8px;")
        self._reveal_stack.addWidget(nl)

        notes_edit = QTextEdit()
        notes_edit.setStyleSheet(NOTES_STYLE)
        notes_edit.setPlainText(notes)
        notes_edit.setMaximumHeight(80)
        notes_edit.setObjectName("notes_edit")
        save_timer = QTimer()
        save_timer.setSingleShot(True)
        save_timer.setInterval(600)
        def debounced_save():
            error_store.update_notes(card["id"], notes_edit.toPlainText())
        save_timer.timeout.connect(debounced_save)
        notes_edit.textChanged.connect(save_timer.start)
        self._reveal_stack.addWidget(notes_edit)

        hint_btn = QPushButton("AI Hint")
        hint_btn.setStyleSheet(
            f"QPushButton {{ background-color: transparent; "
            f"color: {ACCENT}; border: 1px solid {ACCENT}; "
            f"border-radius: 6px; padding: 6px 16px; font-size: 12px; }}"
            f"QPushButton:hover {{ background-color: {ACCENT}; color: #FFFFFF; }}"
        )
        q_text = card.get("question", "")
        kp = card.get("knowledge_point", "")
        def on_hint(btn=hint_btn):
            btn.setEnabled(False)
            btn.setText("Thinking...")
            worker = AIExplainWorker(
                HINT_PROMPT,
                f"知识点：{kp}\n题目：{q_text}\n请给提示",
            )
            def on_done(text):
                btn.setEnabled(True)
                btn.setText("AI Hint")
                self._reveal_stack.addWidget(mlabel(f"💡 {text}", ACCENT, 12))
            def on_err(msg):
                btn.setEnabled(True)
                btn.setText("AI Hint (failed)")
            worker.finished.connect(on_done)
            worker.error.connect(on_err)
            worker.start()
        hint_btn.clicked.connect(on_hint)
        self._reveal_stack.addWidget(hint_btn)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        again_btn = QPushButton("Needs Review")
        again_btn.setStyleSheet(RATE_AGAIN)
        again_btn.clicked.connect(
            lambda: self._rate_and_next(card["id"], 0)
        )
        btn_row.addWidget(again_btn)

        good_btn = QPushButton("Got It")
        good_btn.setStyleSheet(RATE_GOOD)
        good_btn.clicked.connect(
            lambda: self._rate_and_next(card["id"], 3)
        )
        btn_row.addWidget(good_btn)

        self._reveal_stack.addLayout(btn_row)

    def _rate_and_next(self, eid: str, quality: int):
        error_store.schedule_review(eid, quality)
        self._cards.pop(self._current_idx)
        if self._current_idx >= len(self._cards):
            self._current_idx = 0
        self._render_empty_or_card()

    def _on_add_error(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Error")
        dialog.setMinimumWidth(420)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Knowledge Point:"))
        kp_edit = QLineEdit()
        kp_edit.setPlaceholderText("e.g. Pointers, STL...")
        layout.addWidget(kp_edit)
        layout.addWidget(QLabel("Question / Description:"))
        q_edit = QTextEdit()
        q_edit.setPlaceholderText("What did you get wrong?")
        q_edit.setMaximumHeight(80)
        layout.addWidget(q_edit)
        layout.addWidget(QLabel("Correct Answer:"))
        a_edit = QLineEdit()
        a_edit.setPlaceholderText("The right answer")
        layout.addWidget(a_edit)
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            kp = kp_edit.text().strip() or "manual"
            q = q_edit.toPlainText().strip() or "Manual entry"
            a = a_edit.text().strip() or ""
            error_store.add_error(kp, q, "", a, "")
            self._load_cards()
            self._add_btn.setText("✓ Added")
            self._add_btn.setStyleSheet(
                f"QPushButton {{ background-color: #1A3A2A; "
                f"color: #4EC9B0; border: 1px solid #4EC9B0; "
                f"border-radius: 3px; padding: 4px 12px; font-size: 12px; }}"
            )
            QTimer.singleShot(2000, self._reset_add_btn)

    def _reset_add_btn(self):
        self._add_btn.setText("+ Add Error")
        self._add_btn.setStyleSheet("")

    def _on_show_queue(self):
        queue = error_store.get_ucb_queue()
        dialog = QDialog(self)
        dialog.setWindowTitle("Smart Queue (UCB)")
        dialog.setMinimumWidth(420)
        layout = QVBoxLayout(dialog)
        layout.addWidget(mlabel("Review Priority (UCB)", STACK_BORDER, 14, True))
        for i, item in enumerate(queue[:8]):
            row = QLabel(
                f"  #{i + 1}  {item['name']}  "
                f"[✓{item['correct']} ✗{item['wrong']}]  "
                f"{int(item['ucb'] * 100)}%"
            )
            row.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px; padding: 4px 0;")
            layout.addWidget(row)
        ok = QPushButton("OK")
        ok.clicked.connect(dialog.accept)
        layout.addWidget(ok)
        dialog.exec()

    def _refresh(self):
        self._load_cards()
