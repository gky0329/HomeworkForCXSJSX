import asyncio
import logging
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

EXPLAIN_PROMPT = """你是一个 C++ 教学助手。请用中文详细解释以下 C++ 知识点，包含：
1. 概念定义
2. 内存模型（栈/堆分配方式）
3. 代码示例
4. 常见错误

只输出纯文本解释。"""

HINT_PROMPT = """你是 C++ 教学助手。用户正在复习一道 C++ 题目，请给出一个提示（hint），帮助用户回忆起正确答案。

规则：
1. 不要直接给出答案
2. 提示一个关键的语法点或概念
3. 用提问的方式引导思考
4. 保持在 3 句话以内

只输出纯文本。"""


class AIExplainWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, system_prompt: str, user_message: str,
                 config_path: Path | None = None):
        super().__init__()
        self._system = system_prompt
        self._message = user_message
        self._config_path = config_path

    def run(self):
        try:
            service = AIService(self._config_path)
            text = asyncio.run(service.chat_text(
                system_prompt=self._system,
                user_message=self._message,
                model="deepseek-chat",
            ))
            self.finished.emit(text)
        except Exception as e:
            logger.error("AIExplainWorker failed: %s", e)
            self.error.emit(str(e))
