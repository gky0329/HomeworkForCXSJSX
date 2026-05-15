from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme.config import Colors
from app.ui.theme.styles import APP_STYLE


@dataclass
class AiHelpPayload:
    api_url: str
    api_key: str
    model: str
    system_prompt: str
    user_prompt: str
    question_type: str = ""


class AiHelpWorker(QObject):
    chunk_received = Signal(str)
    connected = Signal()
    finished = Signal()
    failed = Signal(str)

    def __init__(self, payload: AiHelpPayload, logger: logging.Logger) -> None:
        super().__init__()
        self._payload = payload
        self._logger = logger

    def run(self) -> None:
        endpoint = _build_endpoint(self._payload.api_url)
        body = {
            "model": self._payload.model,
            "messages": [
                {"role": "system", "content": self._payload.system_prompt},
                {"role": "user", "content": self._payload.user_prompt},
            ],
            "stream": True,
        }
        data = json.dumps(body).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._payload.api_key}",
        }
        request = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
        self._logger.info("AI 请求发送")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                status = response.getcode()
                self._log_status(status)
                if status != 200:
                    self._emit_error(response.read().decode("utf-8", errors="ignore"))
                    return
                first_segment = True
                for raw in response:
                    line = raw.strip()
                    if not line.startswith(b"data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == b"[DONE]":
                        break
                    try:
                        message = json.loads(payload.decode("utf-8"))
                    except json.JSONDecodeError:
                        continue
                    delta = message.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        if first_segment:
                            first_segment = False
                            self.connected.emit()
                        self.chunk_received.emit(content)
        except urllib.error.HTTPError as exc:
            status = exc.code
            self._log_status(status)
            self._emit_error(_status_reason(status, exc.read().decode("utf-8", errors="ignore")))
            return
        except Exception as exc:  # pragma: no cover - network failure
            self._logger.warning("AI 请求异常: %s", exc)
            self._emit_error("未知错误")
            return
        self.finished.emit()

    def _emit_error(self, text: str) -> None:
        message = text or "未知错误"
        self._logger.warning("AI 请求失败: %s", message)
        self.failed.emit(message)

    def _log_status(self, status: int) -> None:
        if status == 200:
            self._logger.info("AI 响应成功")
        elif status == 429 or status >= 500:
            self._logger.warning("AI 响应异常: %s", status)
        elif status in _STATUS_MAP:
            self._logger.warning("AI 响应异常: %s", _STATUS_MAP[status][0])
        else:
            self._logger.warning("AI 响应异常: 未知错误(%s)", status)


class AiHelpDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(APP_STYLE)
        self.setWindowTitle("AI 提示")
        self.setMinimumSize(640, 420)
        self._logger = logging.getLogger("cpplab")
        self._thread: QThread | None = None
        self._worker: AiHelpWorker | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        bar_top = _build_bar_label("还有困难？试试问 AI")
        root.addWidget(bar_top)

        bar_input = _build_bar_widget()
        input_layout = QHBoxLayout(bar_input)
        input_layout.setContentsMargins(12, 8, 12, 8)
        input_layout.setSpacing(10)
        self._problem_input = QLineEdit()
        self._problem_input.setPlaceholderText("输入你的困惑")
        self._problem_input.setMinimumHeight(34)
        send_btn = QPushButton("发送")
        send_btn.setStyleSheet(_btn_style(Colors.OAK))
        send_btn.setMinimumHeight(34)
        send_btn.clicked.connect(self._on_send)
        input_layout.addWidget(self._problem_input)
        input_layout.addWidget(send_btn)
        root.addWidget(bar_input)

        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet(f"font-size: 13px; color: {Colors.GOLD};")
        root.addWidget(self._status)

        self._output = QPlainTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet(
            f"background: {Colors.CODE_BG}; color: {Colors.CREAM}; border: 2px solid {Colors.STONE_DARK};"
        )
        root.addWidget(self._output, stretch=1)

        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet(_btn_style(Colors.STONE))
        close_btn.clicked.connect(self.close)
        root.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self._send_btn = send_btn
        self._payload: AiHelpPayload | None = None

    def start(self, payload: AiHelpPayload) -> None:
        self._payload = payload
        self._output.clear()
        self._status.setText("")
        self._problem_input.clear()

    def _on_send(self) -> None:
        if not self._payload:
            return
        problem = self._problem_input.text().strip()
        if not problem:
            self._status.setText("请输入你的困惑")
            return
        self._status.setText("正在发送请求...")
        self._send_btn.setEnabled(False)
        payload = AiHelpPayload(
            api_url=self._payload.api_url,
            api_key=self._payload.api_key,
            model=self._payload.model,
            system_prompt=self._payload.system_prompt,
            user_prompt=self._payload.user_prompt.replace("{problem}", problem),
            question_type=self._payload.question_type,
        )
        self._start_worker(payload)

    def _on_connected(self) -> None:
        self._status.setText("✓ 小C收到你的问题了！他正在思考...")

    def _start_worker(self, payload: AiHelpPayload) -> None:
        self._thread = QThread()
        self._worker = AiHelpWorker(payload, self._logger)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.connected.connect(self._on_connected)
        self._worker.chunk_received.connect(self._append_text)
        self._worker.failed.connect(self._handle_error)
        self._worker.finished.connect(self._handle_done)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_worker)
        self._thread.start()

    def _append_text(self, text: str) -> None:
        self._output.moveCursor(QTextCursor.End)
        self._output.insertPlainText(text)

    def _handle_done(self) -> None:
        self._status.setText("")
        self._send_btn.setEnabled(True)

    def _handle_error(self, message: str) -> None:
        self._status.setText("请求失败，请稍后重试")
        if message:
            self._output.appendPlainText(message)
        self._send_btn.setEnabled(True)

    def _cleanup_worker(self) -> None:
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
        if self._thread:
            self._thread.deleteLater()
            self._thread = None


def _build_bar_label(text: str) -> QLabel:
    bar = QLabel(text)
    bar.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    bar.setStyleSheet(
        f"font-size: 14px; color: {Colors.CREAM}; background: {Colors.PANEL_BG}; "
        f"border: 2px solid {Colors.STONE_DARK}; padding: 8px 12px;"
    )
    return bar


def _build_bar_widget() -> QWidget:
    bar = QWidget()
    bar.setStyleSheet(
        f"background: {Colors.PANEL_BG}; border: 2px solid {Colors.STONE_DARK}; padding: 0;"
    )
    return bar


def _btn_style(color: str) -> str:
    return (
        f"QPushButton {{ background: {color}; color: white; font-weight: 700; "
        f"font-size: 14px; padding: 6px 16px; border: 2px solid {Colors.BLACK}; border-radius: 3px; }}"
        f"QPushButton:hover {{ background: {Colors.GOLD}; color: {Colors.BLACK}; }}"
        f"QPushButton:disabled {{ background: {Colors.DISABLED_BG}; color: {Colors.DISABLED_TEXT}; }}"
    )


_STATUS_MAP = {
    400: ("格式错误", "请根据错误信息提示修改请求体"),
    401: ("认证失败", "请检查 API key 是否正确"),
    402: ("余额不足", "请确认账户余额并充值"),
    422: ("参数错误", "请检查请求体参数"),
    429: ("请求速率达到上限", "请合理规划请求速率"),
    500: ("服务器故障", "请稍后重试"),
    503: ("服务器繁忙", "请稍后重试"),
}


def _status_reason(status: int, body: str) -> str:
    if status in _STATUS_MAP:
        title, hint = _STATUS_MAP[status]
        return f"{title}: {hint}"
    if body:
        return body
    return "未知错误"


def _build_endpoint(api_url: str) -> str:
    if api_url.endswith("/v1/chat/completions"):
        return api_url
    if api_url.endswith("/v1"):
        return f"{api_url}/chat/completions"
    return f"{api_url.rstrip('/')}/v1/chat/completions"
