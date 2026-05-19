import json
import asyncio
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QPlainTextEdit, QFileDialog, QScrollArea, QFrame, QComboBox,
    QSplitter,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont

from app.services.file_service import (
    extract_text, SUPPORTED_EXTENSIONS, file_type_label,
)
from app.services.ai_service import AIService
from app.services import error_store
from app.services.prompt_templates import PDF_SYSTEM_PROMPT, PDF_USER_TEMPLATE
from app.ui.theme.colors import (
    CANVAS_BG, SURFACE, BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    ACCENT, STACK_BORDER, HEAP_BORDER, EDGE_DANGLING,
)

logger = logging.getLogger(__name__)

FILE_FILTER = "All Supported Files (" + " ".join(
    f"*{e}" for e in SUPPORTED_EXTENSIONS
) + ");;PDF (*.pdf);;Word (*.docx *.doc);;C++ (*.cpp *.h);;" \
    "Python (*.py);;Markdown (*.md);;Text (*.txt);;All Files (*)"

PAGE_STYLE = f"""
QFrame#resultCard {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 12px;
    margin: 4px 0;
}}
QPushButton#visualizeBtn {{
    background-color: {ACCENT};
    color: #FFFFFF;
    border: none;
    border-radius: 3px;
    padding: 3px 10px;
    font-size: 11px;
}}
QLabel#conceptName {{
    color: {STACK_BORDER};
    font-size: 14px;
    font-weight: bold;
}}
QLabel#quizQuestion {{
    color: {HEAP_BORDER};
    font-size: 13px;
    font-weight: bold;
}}
"""

BTN_OPT = (
    f"QPushButton {{ background-color: {CANVAS_BG}; "
    f"color: {TEXT_PRIMARY}; border: 1px solid {BORDER}; "
    f"border-radius: 6px; padding: 6px 14px; "
    f"font-size: 12px; text-align: left; }}"
    f"QPushButton:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}"
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
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        toolbar = QHBoxLayout()

        type_label = QLabel("File type:")
        type_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        toolbar.addWidget(type_label)

        self._type_combo = QComboBox()
        self._type_combo.addItem("Auto-detect", "")
        self._type_combo.addItem("C++ Source", ".cpp")
        self._type_combo.addItem("C/C++ Header", ".h")
        self._type_combo.addItem("Python", ".py")
        self._type_combo.addItem("Markdown", ".md")
        self._type_combo.addItem("Plain Text", ".txt")
        self._type_combo.setStyleSheet(
            f"QComboBox {{ background-color: {SURFACE}; color: {TEXT_PRIMARY}; "
            f"border: 1px solid {BORDER}; border-radius: 4px; padding: 4px 8px; }}"
        )
        toolbar.addWidget(self._type_combo)

        toolbar.addSpacing(8)

        self._upload_btn = QPushButton("Upload File")
        self._upload_btn.clicked.connect(self._on_upload)
        toolbar.addWidget(self._upload_btn)

        self._file_label = QLabel("No file selected")
        self._file_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        toolbar.addWidget(self._file_label)

        toolbar.addStretch()

        self._process_btn = QPushButton("Extract Knowledge Points")
        self._process_btn.setEnabled(False)
        self._process_btn.clicked.connect(self._on_process)
        toolbar.addWidget(self._process_btn)

        layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setPlaceholderText("File content appears here after upload...")
        self._preview.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 11))
        splitter.addWidget(self._preview)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)

        self._status = QLabel("Upload a file to begin")
        self._status.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 12px; padding: 4px;"
        )
        right_layout.addWidget(self._status)

        self._result_scroll = QScrollArea()
        self._result_scroll.setWidgetResizable(True)
        self._result_scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background: {CANVAS_BG}; }}"
        )
        self._result_container = QWidget()
        self._result_layout = QVBoxLayout(self._result_container)
        self._result_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._result_scroll.setWidget(self._result_container)
        right_layout.addWidget(self._result_scroll)

        splitter.addWidget(right)
        splitter.setSizes([400, 500])

        layout.addWidget(splitter)

    def _on_upload(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select File", "", FILE_FILTER
        )
        if not path:
            return

        try:
            file_path = Path(path)
            ext = file_path.suffix.lower()
            self._file_label.setText(
                f"{file_path.name}  ({file_type_label(ext)})"
            )
            self._status.setText("Extracting text...")

            self._file_text = extract_text(str(file_path))

            preview = self._file_text[:20000]
            if len(self._file_text) > 20000:
                preview += (
                    f"\n\n... ({len(self._file_text)} chars total, "
                    "truncated for preview)"
                )
            self._preview.setPlainText(preview)
            self._process_btn.setEnabled(True)
            self._status.setText(
                f"Loaded: {file_path.name} ({len(self._file_text)} chars). "
                "Click 'Extract Knowledge Points' to process with AI."
            )
        except Exception as e:
            self._status.setText(f"Error: {e}")
            self._file_label.setText("Error loading file")

    def _on_process(self):
        if not self._file_text:
            return

        self._process_btn.setEnabled(False)
        self._upload_btn.setEnabled(False)
        self._clear_results()
        self._status.setText("Processing with AI...")

        self._worker = ProcessWorker(self._file_text, self._config_path)
        self._worker.finished.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_result(self, data: dict):
        self._process_btn.setEnabled(True)
        self._upload_btn.setEnabled(True)

        kps = data.get("knowledge_points", [])
        quizzes = data.get("quiz_questions", [])

        self._status.setText(
            f"Done: {len(kps)} knowledge points, {len(quizzes)} questions"
        )
        error_store.log_activity("File Import", f"Extracted {len(kps)} KPs, {len(quizzes)} quizzes")

        if kps:
            section = QLabel(" Knowledge Points")
            section.setStyleSheet(
                f"color: {STACK_BORDER}; font-size: 15px; font-weight: bold; "
                "padding: 8px 0 4px 0;"
            )
            self._result_layout.addWidget(section)

            for kp in kps:
                self._result_layout.addWidget(self._build_kp_card(kp))

        if quizzes:
            section = QLabel(" Quiz Questions")
            section.setStyleSheet(
                f"color: {HEAP_BORDER}; font-size: 15px; font-weight: bold; "
                "padding: 12px 0 4px 0;"
            )
            self._result_layout.addWidget(section)

            for i, q in enumerate(quizzes):
                self._result_layout.addWidget(self._build_quiz_card(i + 1, q))

        self._result_layout.addStretch()

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
            label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px;")
            layout.addWidget(label)

        code = kp.get("code_snippet", "")
        if code:
            code_frame = QFrame()
            code_frame.setStyleSheet(
                f"background-color: {CANVAS_BG}; border: 1px solid {BORDER}; "
                "border-radius: 4px; padding: 6px; margin: 4px 0;"
            )
            cf_layout = QVBoxLayout(code_frame)
            cf_layout.setContentsMargins(6, 4, 6, 4)

            code_label = QLabel(code)
            code_label.setFont(QFont("JetBrains Mono, Menlo, SF Mono, Courier New, monospace", 11))
            code_label.setStyleSheet(
                f"color: {TEXT_PRIMARY}; background: transparent; border: none;"
            )
            code_label.setWordWrap(True)
            cf_layout.addWidget(code_label)

            viz_btn = QPushButton("Visualize this code")
            viz_btn.setObjectName("visualizeBtn")
            viz_btn.clicked.connect(
                lambda checked=None, c=code: self.visualize_requested.emit(c)
            )
            cf_layout.addWidget(viz_btn)

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
            f"color: {TEXT_SECONDARY}; font-size: 11px; padding-left: 12px;"
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
                            f"QPushButton {{ background-color: #1A3A2A; "
                            f"color: #4EC9B0; border: 1px solid #4EC9B0; "
                            f"border-radius: 6px; padding: 6px 14px; "
                            f"font-size: 12px; text-align: left; font-weight: bold; }}"
                        )
                    else:
                        btn.setStyleSheet(
                            f"QPushButton {{ background-color: #3A1A1A; "
                            f"color: {EDGE_DANGLING}; border: 1px solid {EDGE_DANGLING}; "
                            f"border-radius: 6px; padding: 6px 14px; "
                            f"font-size: 12px; text-align: left; font-weight: bold; }}"
                        )
                elif i == answer_idx:
                    btn.setStyleSheet(
                        f"QPushButton {{ background-color: #1A3A2A; "
                        f"color: #4EC9B0; border: 1px solid #4EC9B0; "
                        f"border-radius: 6px; padding: 6px 14px; "
                        f"font-size: 12px; text-align: left; }}"
                    )
                else:
                    btn.setStyleSheet(
                        BTN_OPT
                    )
                btn.setEnabled(False)

            if correct:
                result_label.setText("✓ Correct!")
                result_label.setStyleSheet(
                    f"color: #4EC9B0; font-size: 13px; font-weight: bold; padding: 4px 0;"
                )
            else:
                result_label.setText(
                    f"✗ Wrong — correct answer: {labels[answer_idx]}) {options[answer_idx]}"
                )
                result_label.setStyleSheet(
                    f"color: {EDGE_DANGLING}; font-size: 13px; font-weight: bold; padding: 4px 0;"
                )

                wrong_btn = QPushButton("Add to My Errors")
                wrong_btn.setStyleSheet(
                    f"QPushButton {{ background-color: transparent; "
                    f"color: {EDGE_DANGLING}; border: 1px solid {EDGE_DANGLING}; "
                    f"border-radius: 3px; padding: 3px 12px; font-size: 10px; margin-top: 4px; }}"
                    f"QPushButton:hover {{ background-color: {EDGE_DANGLING}; color: #FFFFFF; }}"
                )
                q_text = q.get("question", "")
                def save_and_feedback(btn=wrong_btn, q_text=q_text, a_idx=answer_idx, opts=options, lbl=labels, ci=choice_idx):
                    error_store.add_error(
                        knowledge_point="quiz",
                        question=q_text,
                        user_answer=lbl[ci] if ci < len(lbl) else "?",
                        correct_answer=opts[a_idx] if 0 <= a_idx < len(opts) else "?",
                    )
                    btn.setText("✓ Added")
                    btn.setStyleSheet(
                        f"QPushButton {{ background-color: #1A3A2A; "
                        f"color: #4EC9B0; border: 1px solid #4EC9B0; "
                        f"border-radius: 3px; padding: 3px 12px; font-size: 10px; margin-top: 4px; }}"
                    )
                    btn.setEnabled(False)
                wrong_btn.clicked.connect(save_and_feedback)
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
        self._status.setText(f"Error: {msg}")

    def _clear_results(self):
        while self._result_layout.count():
            item = self._result_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
