import json
import asyncio
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QPlainTextEdit, QFileDialog, QScrollArea, QFrame, QComboBox,
    QSplitter, QStackedWidget,
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QFont, QIcon

from app.services.file_service import (
    extract_text, SUPPORTED_EXTENSIONS, file_type_label,
)
from app.services.ai_service import AIService
from app.services import error_store
from app.services.i18n import tr
from app.services.prompt_templates import PDF_SYSTEM_PROMPT, PDF_USER_TEMPLATE
from app.ui.widgets.helpers import clear_layout, build_code_block
from app.ui.widgets.empty_state import PixelEmptyState
from app.ui.widgets.error_dialog import show_error_dialog
from app.ui.widgets.threading import retire_worker
from app.ui.theme.colors import (
    CANVAS_BG, SURFACE, BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    ACCENT, ACCENT_HOVER, STACK_BORDER, HEAP_BORDER, EDGE_DANGLING,
    TEXT_INVERSE, TEXT_BUTTON_PRIMARY, SUCCESS, SUCCESS_BG, ERROR_BG,
)
from app.ui.theme.minecraft_assets import asset_path

logger = logging.getLogger(__name__)

def _file_filter() -> str:
    supported = " ".join(f"*{e}" for e in SUPPORTED_EXTENSIONS)
    return (
        f"{tr('All Supported Files')} ({supported});;"
        "PDF (*.pdf);;"
        f"{tr('Word')} (*.docx *.doc);;"
        "C++ (*.cpp *.h);;"
        "Python (*.py);;"
        "Markdown (*.md);;"
        f"{tr('Text')} (*.txt);;"
        f"{tr('All Files')} (*)"
    )

PAGE_STYLE = f"""
QFrame#resultCard {{
    background-color: {SURFACE};
    border: 2px solid {BORDER};
    
    padding: 12px;
    margin: 4px 0;
}}
QPushButton#visualizeBtn {{
    background-color: {ACCENT};
    color: {TEXT_BUTTON_PRIMARY};
    border: 2px solid {BORDER};
    
    padding: 3px 10px;
    font-size: 14px;
    font-weight: 700;
}}
QLabel#conceptName {{
    color: {STACK_BORDER};
    font-size: 17px;
    font-weight: bold;
}}
QLabel#quizQuestion {{
    color: {HEAP_BORDER};
    font-size: 15px;
    font-weight: bold;
}}
"""

BTN_OPT = (
    f"QPushButton {{ background-color: {CANVAS_BG}; "
    f"color: {TEXT_PRIMARY}; border: 1px solid {BORDER}; "
    f"padding: 6px 14px; "
    f"font-size: 14px; font-weight: 600; text-align: left; }}"
    f"QPushButton:hover {{ border-color: {ACCENT}; color: {TEXT_BUTTON_PRIMARY}; }}"
)


class ProcessWorker(QThread):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, file_text: str, config_path: Path | None = None):
        super().__init__()
        self._text = file_text
        self._config_path = config_path

    def run(self):
        try:
            service = AIService(self._config_path)
            user_msg = PDF_USER_TEMPLATE.format(content=self._text[:15000])
            raw = asyncio.run(service.chat_json(
                system_prompt=PDF_SYSTEM_PROMPT,
                user_message=user_msg,
            ))
            data = json.loads(raw)
            self.finished.emit(data)
        except Exception as e:
            logger.error("ProcessWorker failed: %s", e)
            self.error.emit(str(e))


class FileImportPage(QWidget):
    visualize_requested = Signal(str)

    def __init__(self, config_path: Path | None = None, parent=None):
        super().__init__(parent)
        self._config_path = config_path
        self._file_text = ""
        self._worker: ProcessWorker | None = None
        self._quiz_worker: AIExplainWorker | None = None
        self._retired_workers: list[QThread] = []
        self._kps_data: list[dict] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        toolbar = QHBoxLayout()

        self._type_label = QLabel(tr("File type:"))
        self._type_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px; font-weight: 600;")
        toolbar.addWidget(self._type_label)

        self._type_combo = QComboBox()
        self._populate_type_combo()
        toolbar.addWidget(self._type_combo)

        toolbar.addSpacing(8)

        self._upload_btn = QPushButton(tr("Upload File"))
        self._upload_btn.setIcon(QIcon(asset_path("icons", "action_upload")))
        self._upload_btn.setIconSize(QSize(18, 18))
        self._upload_btn.clicked.connect(self._on_upload)
        toolbar.addWidget(self._upload_btn)

        self._file_label = QLabel(tr("No file selected"))
        self._file_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 14px; font-weight: 600;")
        toolbar.addWidget(self._file_label)

        toolbar.addStretch()

        self._process_btn = QPushButton(tr("Extract Knowledge Points"))
        self._process_btn.setIcon(QIcon(asset_path("icons", "empty_book")))
        self._process_btn.setIconSize(QSize(18, 18))
        self._process_btn.setEnabled(False)
        self._process_btn.clicked.connect(self._on_process)
        toolbar.addWidget(self._process_btn)

        layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._preview_stack = QStackedWidget()
        self._preview_empty = PixelEmptyState(
            "empty_scroll",
            tr("No file uploaded"),
            tr("Upload a supported source or document file to preview it here."),
        )
        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setPlaceholderText(tr("File content appears here after upload..."))
        self._preview.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 11))
        self._preview_stack.addWidget(self._preview_empty)
        self._preview_stack.addWidget(self._preview)
        splitter.addWidget(self._preview_stack)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)

        self._status = QLabel(tr("Upload a file to begin"))
        self._status.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 14px; font-weight: 600; padding: 4px;"
        )
        right_layout.addWidget(self._status)

        self._result_stack = QStackedWidget()
        self._result_empty = PixelEmptyState(
            "empty_book",
            tr("Extraction results will appear here"),
            tr("After upload, AI will extract knowledge points and quiz questions here."),
        )

        self._result_scroll = QScrollArea()
        self._result_scroll.setWidgetResizable(True)
        self._result_scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background: {CANVAS_BG}; }}"
        )
        self._result_container = QWidget()
        self._result_layout = QVBoxLayout(self._result_container)
        self._result_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._result_scroll.setWidget(self._result_container)
        self._result_stack.addWidget(self._result_empty)
        self._result_stack.addWidget(self._result_scroll)
        right_layout.addWidget(self._result_stack)

        splitter.addWidget(right)
        splitter.setSizes([400, 500])

        layout.addWidget(splitter)

    def _populate_type_combo(self):
        current = self._type_combo.currentData() if hasattr(self, "_type_combo") else ""
        self._type_combo.clear()
        for label, value in [
            ("Auto-detect", ""),
            ("C++ Source", ".cpp"),
            ("C/C++ Header", ".h"),
            ("Python", ".py"),
            ("Markdown", ".md"),
            ("Plain Text", ".txt"),
        ]:
            self._type_combo.addItem(tr(label), value)
        index = self._type_combo.findData(current)
        self._type_combo.setCurrentIndex(index if index >= 0 else 0)

    def _on_upload(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Select File"), "", _file_filter()
        )
        if not path:
            return

        try:
            file_path = Path(path)
            ext = file_path.suffix.lower()
            self._file_label.setText(
                f"{file_path.name}  ({file_type_label(ext)})"
            )
            self._status.setText(tr("Extracting text..."))

            self._file_text = extract_text(str(file_path))

            preview = self._file_text[:20000]
            if len(self._file_text) > 20000:
                preview += (
                    "\n\n" + tr(
                        "... ({count} chars total, truncated for preview)",
                        count=len(self._file_text),
                    )
                )
            self._preview.setPlainText(preview)
            self._preview_stack.setCurrentWidget(self._preview)
            self._process_btn.setEnabled(True)
            self._status.setText(
                tr(
                    "Loaded: {name} ({count} chars). Click 'Extract Knowledge Points' to process with AI.",
                    name=file_path.name,
                    count=len(self._file_text),
                )
            )
        except Exception as e:
            self._status.setText(tr("Error: {message}", message=e))
            self._file_label.setText(tr("Error loading file"))

    def _on_process(self):
        if not self._file_text:
            return

        self._process_btn.setEnabled(False)
        self._upload_btn.setEnabled(False)
        self._clear_results()
        self._status.setText(tr("Processing with AI..."))

        if self._worker is not None and self._worker.isRunning():
            retire_worker(
                self,
                self._worker,
                disconnect=[
                    (self._worker.finished, self._on_result),
                    (self._worker.error, self._on_error),
                ],
            )

        self._worker = ProcessWorker(self._file_text, self._config_path)
        self._worker.finished.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_result(self, data: dict):
        self._process_btn.setEnabled(True)
        self._upload_btn.setEnabled(True)

        kps = data.get("knowledge_points", [])
        quizzes = data.get("quiz_questions", [])
        self._kps_data = kps

        self._status.setText(
            tr("Done: {kps} knowledge points, {quizzes} questions", kps=len(kps), quizzes=len(quizzes))
        )
        error_store.log_activity("File Import", f"Extracted {len(kps)} KPs, {len(quizzes)} quizzes")

        if kps:
            section = QLabel(" " + tr("Knowledge Points"))
            section.setStyleSheet(
                f"color: {STACK_BORDER}; font-size: 15px; font-weight: bold; "
                "padding: 8px 0 4px 0;"
            )
            self._result_layout.addWidget(section)

            for kp in kps:
                self._result_layout.addWidget(self._build_kp_card(kp))

        if quizzes:
            section = QLabel(" " + tr("Quiz Questions"))
            section.setStyleSheet(
                f"color: {HEAP_BORDER}; font-size: 15px; font-weight: bold; "
                "padding: 12px 0 4px 0;"
            )
            self._result_layout.addWidget(section)

            for i, q in enumerate(quizzes):
                self._result_layout.addWidget(self._build_quiz_card(i + 1, q))

        if kps:
            gen_quiz_btn = QPushButton(tr("Generate Quiz Questions"))
            gen_quiz_btn.clicked.connect(self._on_generate_quiz)
            self._gen_quiz_btn = gen_quiz_btn
            self._result_layout.addWidget(gen_quiz_btn)

        self._result_layout.addStretch()
        self._result_stack.setCurrentWidget(self._result_scroll)

    def _build_kp_card(self, kp: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("resultCard")
        card.setStyleSheet(PAGE_STYLE)
        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        name = QLabel(kp.get("name", ""))
        name.setObjectName("conceptName")
        layout.addWidget(name)

        expl = kp.get("explanation", "")
        if expl:
            label = QLabel(expl)
            label.setWordWrap(True)
            label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 14px; font-weight: 600;")
            layout.addWidget(label)

        code = kp.get("code_snippet", "")
        if code:
            code_frame = build_code_block(code, text_color=TEXT_PRIMARY,
                                           bg_color=CANVAS_BG, border_color=BORDER)

            viz_btn = QPushButton(tr("Visualize this code"))
            viz_btn.setObjectName("visualizeBtn")
            viz_btn.clicked.connect(
                lambda checked=None, c=code: self.visualize_requested.emit(c)
            )
            code_frame.layout().addWidget(viz_btn)

            layout.addWidget(code_frame)

        return card

    def _build_quiz_card(self, num: int, q: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("resultCard")
        card.setStyleSheet(PAGE_STYLE)
        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        question = QLabel(f"Q{num}: {q.get('question', '')}")
        question.setObjectName("quizQuestion")
        question.setWordWrap(True)
        layout.addWidget(question)

        options = q.get("options", [])
        answer_idx = q.get("answer", -1)
        labels = ["A", "B", "C", "D"]

        result_label = QLabel("")
        result_label.setVisible(False)
        layout.addWidget(result_label)

        explanation = q.get("explanation", "")
        expl_label = QLabel(f"  {explanation}" if explanation else "")
        expl_label.setWordWrap(True)
        expl_label.setVisible(False)
        expl_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 13px; font-weight: 600; padding-left: 12px;"
        )
        layout.addWidget(expl_label)

        answered = [False]

        def on_choice(choice_idx: int, btn_widgets: list[QPushButton]):
            if answered[0]:
                return
            answered[0] = True

            correct = (choice_idx == answer_idx)

            kp_name = q.get("knowledge_point", "quiz")
            error_store.record_review_result(kp_name, correct)

            for i, btn in enumerate(btn_widgets):
                if i == choice_idx:
                    if correct:
                        btn.setStyleSheet(
                            f"QPushButton {{ background-color: {SUCCESS_BG}; "
                            f"color: {SUCCESS}; border: 2px solid {SUCCESS}; "
                            f"padding: 6px 14px; "
                            f"font-size: 14px; text-align: left; font-weight: bold; }}"
                        )
                    else:
                        btn.setStyleSheet(
                            f"QPushButton {{ background-color: {ERROR_BG}; "
                            f"color: {EDGE_DANGLING}; border: 2px solid {EDGE_DANGLING}; "
                            f"padding: 6px 14px; "
                            f"font-size: 14px; text-align: left; font-weight: bold; }}"
                        )
                elif i == answer_idx:
                    btn.setStyleSheet(
                        f"QPushButton {{ background-color: {SUCCESS_BG}; "
                        f"color: {SUCCESS}; border: 2px solid {SUCCESS}; "
                        f"padding: 6px 14px; "
                        f"font-size: 14px; font-weight: 600; text-align: left; }}"
                    )
                else:
                    btn.setStyleSheet(
                        BTN_OPT
                    )
                btn.setEnabled(False)

            if correct:
                result_label.setText("✓ " + tr("Correct!"))
                result_label.setStyleSheet(
                    f"color: {SUCCESS}; font-size: 14px; font-weight: bold; padding: 4px 0;"
                )
            else:
                result_label.setText(
                    "✗ " + tr(
                        "Wrong - correct answer: {answer}",
                        answer=f"{labels[answer_idx]}) {options[answer_idx]}" if 0 <= answer_idx < len(options) else "?",
                    )
                )
                result_label.setStyleSheet(
                    f"color: {EDGE_DANGLING}; font-size: 14px; font-weight: bold; padding: 4px 0;"
                )

                wrong_btn = QPushButton(tr("Add to My Errors"))
                wrong_btn.setStyleSheet(
                    f"QPushButton {{ background-color: transparent; "
                    f"color: {EDGE_DANGLING}; border: 2px solid {EDGE_DANGLING}; "
                    f"padding: 4px 12px; font-size: 13px; font-weight: 600; margin-top: 4px; }}"
                    f"QPushButton:hover {{ background-color: {EDGE_DANGLING}; color: {TEXT_BUTTON_PRIMARY}; }}"
                )
                q_text = q.get("question", "")
                kp_name = q.get("knowledge_point", "quiz")
                opts = options
                lbl = labels
                a_idx = answer_idx
                ci = choice_idx
                def save_and_feedback():
                    opts_text = "\n".join(f"  {lbl[i]}) {opts[i]}" for i in range(len(opts)))
                    question_full = f"{q_text}\n\n{opts_text}"
                    error_store.add_error(
                        knowledge_point=kp_name,
                        question=question_full,
                        user_answer=f"{lbl[ci]}) {opts[ci]}" if ci < len(opts) else "?",
                        correct_answer=f"{lbl[a_idx]}) {opts[a_idx]}" if 0 <= a_idx < len(opts) else "?",
                        deck=error_store.suggest_deck(kp_name),
                    )
                    wrong_btn.setText("✓ " + tr("Added"))
                    wrong_btn.setStyleSheet(
                        f"QPushButton {{ background-color: {SUCCESS_BG}; "
                        f"color: {SUCCESS}; border: 2px solid {SUCCESS}; "
                        f"padding: 4px 12px; font-size: 13px; font-weight: 600; margin-top: 4px; }}"
                    )
                    wrong_btn.setEnabled(False)
                wrong_btn.clicked.connect(lambda: save_and_feedback())
                layout.addWidget(wrong_btn)

            result_label.setVisible(True)
            if explanation:
                expl_label.setVisible(True)

        btns = []
        for i, opt in enumerate(options):
            btn = QPushButton(f"{labels[i]}) {opt}")
            btn.setStyleSheet(BTN_OPT)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(
                lambda checked=None, idx=i, bw=btns: on_choice(idx, bw)
            )
            layout.addWidget(btn)
            btns.append(btn)

        return card

    def _on_error(self, msg: str):
        self._process_btn.setEnabled(True)
        self._upload_btn.setEnabled(True)
        self._status.setText(tr("Error: {message}", message=msg[:60]))

        raw = ""
        display_msg = msg
        if "---RAW RESPONSE---" in msg:
            parts = msg.split("---RAW RESPONSE---", 1)
            display_msg = parts[0].strip()
            raw = parts[1].strip()

        show_error_dialog(
            self,
            tr("File Import Error"),
            display_msg,
            raw_response=raw,
            on_retry=lambda: self._on_process(),
        )

    def _clear_results(self):
        clear_layout(self._result_layout)

    def _on_generate_quiz(self):
        if not self._kps_data:
            self._status.setText(tr("No knowledge points to generate quizzes from"))
            return
        self._process_btn.setEnabled(False)
        self._gen_quiz_btn.setEnabled(False)
        self._status.setText(tr("Generating quiz questions..."))
        kps_text = "\n".join(
            f"{kp.get('name', '')}: {kp.get('explanation', '')[:200]}"
            for kp in self._kps_data
        )

        quiz_prompt = """你是 C++ 出题助手。根据以下知识点，生成 3-5 道单选题。
输出 JSON：{ "quiz_questions": [{"question":"...","options":["A","B","C","D"],"answer":0,"explanation":"...","knowledge_point":"知识点名"}] }
直接输出 JSON，不要任何解释。"""
        msg = f"知识点列表：\n{kps_text}"

        from app.services.ai_explain_worker import AIExplainWorker
        if hasattr(self, '_quiz_worker') and self._quiz_worker is not None and self._quiz_worker.isRunning():
            retire_worker(
                self,
                self._quiz_worker,
                disconnect=[
                    (self._quiz_worker.finished, self._on_quiz_result),
                    (self._quiz_worker.error, self._on_quiz_error),
                ],
            )
        self._quiz_worker = AIExplainWorker(quiz_prompt, msg)
        self._quiz_worker.finished.connect(self._on_quiz_result)
        self._quiz_worker.error.connect(self._on_quiz_error)
        self._quiz_worker.start()

    def _on_quiz_result(self, text: str):
        import json
        self._process_btn.setEnabled(True)
        if hasattr(self, '_gen_quiz_btn'):
            self._gen_quiz_btn.setEnabled(True)
        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                parts = cleaned.split("```")
                cleaned = parts[1] if len(parts) > 1 else cleaned
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:].strip()
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            self._status.setText(tr("Quiz generation returned invalid JSON"))
            return
        quizzes = data.get("quiz_questions", [])
        self._status.setText(tr("Generated {n} quiz questions", n=len(quizzes)))
        if quizzes:
            section = QLabel(" " + tr("Generated Quizzes"))
            section.setStyleSheet(
                f"color: {HEAP_BORDER}; font-size: 15px; font-weight: bold; padding: 12px 0 4px 0;"
            )
            self._result_layout.addWidget(section)
            for i, q in enumerate(quizzes):
                self._result_layout.addWidget(self._build_quiz_card(i + 1, q))

    def _on_quiz_error(self, msg: str):
        self._process_btn.setEnabled(True)
        if hasattr(self, '_gen_quiz_btn'):
            self._gen_quiz_btn.setEnabled(True)
        self._status.setText(tr("Quiz generation failed"))

    def retranslate_ui(self):
        self._type_label.setText(tr("File type:"))
        self._populate_type_combo()
        self._upload_btn.setText(tr("Upload File"))
        self._process_btn.setText(tr("Extract Knowledge Points"))
        self._preview.setPlaceholderText(tr("File content appears here after upload..."))
        if not self._file_label.text() or self._file_label.text() == tr("No file selected"):
            self._file_label.setText(tr("No file selected"))
        if not self._file_text and not self._worker:
            self._status.setText(tr("Upload a file to begin"))
