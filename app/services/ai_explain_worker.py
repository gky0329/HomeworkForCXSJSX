import asyncio
import logging
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

EXPLAIN_PROMPT = """你是 C++ 教学助手。请用中文解释以下 C++ 知识点。

输出要求：
- 使用 Markdown 格式输出（将在应用中渲染）
- 禁止任何开头寒暄和结尾总结（不要写"好的"、"当然"、"希望对你有所帮助"等废话）
- 直接以内容开头，结构如下：

## 概念
（1-2句精确定义）

## 内存模型
（描述该知识点涉及的内存布局：栈/堆分配方式、生命周期）

## 示例
```cpp
// 简洁可运行的 C++ 代码示例
```

## 常见错误
- 错误1的描述
- 错误2的描述

内容要求：每部分控制在2-4句话以内，代码示例不超过15行。
禁止使用"好的"、"我来解释"、"当然可以"等客套话，直接输出内容。"""

HINT_PROMPT = """你是 C++ 教学助手。用户正在复习一道 C++ 题目，请给出一个提示（hint），帮助用户回忆起正确答案。

规则：
1. 不要直接给出答案
2. 提示一个关键的语法点或概念
3. 用提问的方式引导思考
4. 保持在 3 句话以内
5. 禁止任何寒暄（不要写"好的"、"当然"等）
6. 直接输出提示内容，不要加任何前缀"""


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
            ))
            self.finished.emit(text)
        except Exception as e:
            logger.error("AIExplainWorker failed: %s", e)
            self.error.emit(str(e))
