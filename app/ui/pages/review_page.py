from datetime import datetime, timezone

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTextEdit, QDialog, QLineEdit,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt, QTimer

from app.services import error_store
from app.services.ai_explain_worker import AIExplainWorker, HINT_PROMPT
from app.ui.widgets.helpers import mlabel, clear_layout
from app.ui.theme.colors import (
    CANVAS_BG, SURFACE, BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    STACK_BORDER, HEAP_BORDER, ACCENT, EDGE_DANGLING, SUCCESS, SUCCESS_BG,
)


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
        f"QPushButton {{ background-color: #3A1A1A; color: {EDGE_DANGLING}; "
        f"border: 1px solid {EDGE_DANGLING}; "
        f"padding: 12px 20px; font-size: 13px; font-weight: bold; }}"
        f"QPushButton:hover {{ background-color: #4A2A2A; }}"
    ),
    "hard": (
        f"QPushButton {{ background-color: #3A2A1A; color: #DCDCAA; "
        f"border: 1px solid #DCDCAA; "
        f"padding: 12px 20px; font-size: 13px; font-weight: bold; }}"
        f"QPushButton:hover {{ background-color: #4A3A2A; }}"
    ),
    "good": (
        f"QPushButton {{ background-color: #1A3A2A; color: {SUCCESS}; "
        f"border: 1px solid {SUCCESS}; "
        f"padding: 12px 20px; font-size: 13px; font-weight: bold; }}"
        f"QPushButton:hover {{ background-color: #2A4A3A; }}"
    ),
    "easy": (
        f"QPushButton {{ background-color: #1A2A3A; color: #569CD6; "
        f"border: 1px solid #569CD6; "
        f"padding: 12px 20px; font-size: 13px; font-weight: bold; }}"
        f"QPushButton:hover {{ background-color: #2A3A4A; }}"
    ),
}

CARD_STYLE = (
    f"QFrame#reviewCard {{ background-color: {SURFACE}; border: 1px solid {BORDER}; "
    f"}}"
    f"QFrame#reviewCard QLabel {{ border: none; background: transparent; outline: none; }}"
)

NOTES_STYLE = (
    f"QTextEdit {{ background-color: {CANVAS_BG}; color: {TEXT_PRIMARY}; "
    f"border: 1px solid {BORDER}; padding: 8px; "
    f"font-size: 12px; }}"
)


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
        self._setup_ui()
        self._load_cards()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)

        header = QHBoxLayout()
        header.addWidget(mlabel("Review", STACK_BORDER, 18, True))
        header.addStretch()

        self._add_btn = QPushButton("+ Add")
        self._add_btn.setStyleSheet(
            f"QPushButton {{ background-color: transparent; color: {TEXT_SECONDARY}; "
            f"border: 1px solid {BORDER}; padding: 4px 12px; font-size: 11px; }}"
            f"QPushButton:hover {{ border-color: {ACCENT}; color: {TEXT_PRIMARY}; }}"
        )
        self._add_btn.clicked.connect(self._on_add_error)
        header.addWidget(self._add_btn)

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
        self._cards = error_store.get_due_cards()
        if len(self._cards) > self._session_limit:
            self._cards = self._cards[:self._session_limit]
        self._current_idx = 0
        self._answer_revealed = False
        self._render_empty_or_card()

    def _render_empty_or_card(self):
        self._clear_card_area()
        clear_layout(self._empty_state)

        if not self._cards:
            self._progress.setText("")
            self._empty_state.addStretch()
            empty = mlabel("🎉 No cards due — great job!", SUCCESS, 16, True)
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._empty_state.addWidget(empty)
            self._empty_state.addWidget(mlabel(
                "Come back later or add errors via OJ / File Import",
                TEXT_SECONDARY, 12
            ))
            self._empty_state.addStretch()
            return

        self._render_card(self._cards[self._current_idx])

    def _clear_card_area(self):
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

    def _render_card(self, card: dict):
        n_cards = len(self._cards)
        idx = self._current_idx
        self._progress.setText(
            f"{idx + 1} / {n_cards}" if n_cards > 1 else ""
        )
        self._answer_revealed = False

        main = QVBoxLayout()
        main.setAlignment(Qt.AlignmentFlag.AlignCenter)

        c = QFrame()
        c.setObjectName("reviewCard")
        c.setStyleSheet(CARD_STYLE)
        c.setMaximumWidth(680)
        v = QVBoxLayout(c)
        v.setContentsMargins(28, 24, 28, 24)
        v.setSpacing(16)

        kp = card.get("knowledge_point", "")
        if kp:
            kpl = QLabel(kp)
            kpl.setStyleSheet(
                f"color: {HEAP_BORDER}; font-size: 12px; font-weight: bold; "
                f"background-color: #3D2916; "
                f"padding: 4px 12px;"
            )
            kpl.setWordWrap(True)
            v.addWidget(kpl, alignment=Qt.AlignmentFlag.AlignCenter)

        qtext = card.get("question", "")
        ql = QLabel(qtext)
        ql.setWordWrap(True)
        ql.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ql.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 22px; font-weight: 700; "
            f"padding: 8px 0; line-height: 1.4;"
        )
        v.addWidget(ql)

        user_ans = card.get("user_answer", "")
        if user_ans:
            ul = QLabel(f"Your answer: {user_ans}")
            ul.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ul.setStyleSheet(
                f"color: {EDGE_DANGLING}; font-size: 12px; font-style: italic; padding: 4px 0;"
            )
            v.addWidget(ul)

        v.addSpacing(12)

        hint_btn = QPushButton("💡 Hint")
        hint_btn.setStyleSheet(
            f"QPushButton {{ background-color: transparent; "
            f"color: {ACCENT}; border: 1px solid {ACCENT}; "
            f"padding: 6px 16px; font-size: 12px; }}"
            f"QPushButton:hover {{ background-color: {ACCENT}; color: #FFFFFF; }}"
        )
        q_text = card.get("question", "")
        kp_text = card.get("knowledge_point", "")
        hint_label = QLabel("")
        hint_label.setWordWrap(True)
        hint_label.setVisible(False)
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setStyleSheet(f"color: {ACCENT}; font-size: 12px; padding: 4px 0;")
        hint_btn.clicked.connect(self._make_hint_handler(hint_btn, hint_label, kp_text, q_text))
        v.addWidget(hint_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        v.addWidget(hint_label)

        v.addSpacing(8)

        reveal_btn = QPushButton("Show Answer")
        reveal_btn.setStyleSheet(
            f"QPushButton {{ background-color: {ACCENT}; color: #FFFFFF; "
            f"border: none; padding: 12px 32px; "
            f"font-size: 15px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: #1A8CD8; }}"
        )
        reveal_btn.clicked.connect(lambda: self._reveal_answer(card))
        v.addWidget(reveal_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self._reveal_area = QVBoxLayout()
        v.addLayout(self._reveal_area)

        main.addWidget(c, alignment=Qt.AlignmentFlag.AlignCenter)
        self._card_area.addLayout(main)

    def _make_hint_handler(self, btn, label, kp_text, q_text):
        def on_hint():
            btn.setEnabled(False)
            btn.setText("Thinking...")
            if self._hint_worker is not None and self._hint_worker.isRunning():
                try:
                    self._hint_worker.finished.disconnect()
                    self._hint_worker.error.disconnect()
                except Exception:
                    pass
                self._hint_worker.quit()
                self._hint_worker.wait(1000)
            self._hint_worker = AIExplainWorker(
                HINT_PROMPT,
                f"知识点：{kp_text}\n题目：{q_text}\n请给提示",
            )
            def on_done(text):
                btn.setEnabled(True)
                btn.setText("💡 Hint")
                label.setText(f"💡 提示: {text}")
                label.setVisible(True)
            def on_err(msg):
                btn.setEnabled(True)
                btn.setText("💡 Hint (failed)")
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
        al = QLabel(f"Correct: {correct}")
        al.setWordWrap(True)
        al.setAlignment(Qt.AlignmentFlag.AlignCenter)
        al.setStyleSheet(
            f"color: {SUCCESS}; font-size: 17px; font-weight: 700; "
            f"background-color: {SUCCESS_BG}; "
            f"padding: 16px; border-bottom: 2px solid {SUCCESS};"
        )
        self._reveal_area.addWidget(al)

        notes = card.get("notes", "")
        self._notes_edit = QTextEdit()
        self._notes_edit.setStyleSheet(NOTES_STYLE)
        self._notes_edit.setPlainText(notes)
        self._notes_edit.setMaximumHeight(60)
        self._notes_edit.setPlaceholderText("Notes...")
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
            btn = QPushButton(f"{label}\n({est})")
            btn.setStyleSheet(RATE_STYLES[style_key])
            btn.clicked.connect(
                lambda checked=None, q=quality: self._rate_and_next(card["id"], q)
            )
            btn_row.addWidget(btn)

        self._reveal_area.addLayout(btn_row)

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
        self._render_empty_or_card()

    def _on_add_error(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Card")
        dialog.setMinimumWidth(420)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Knowledge Point:"))
        kp_edit = QLineEdit()
        kp_edit.setPlaceholderText("e.g. Pointers, STL...")
        layout.addWidget(kp_edit)
        layout.addWidget(QLabel("Question:"))
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

    def _refresh(self):
        self._load_cards()
