import asyncio
import logging
from pathlib import Path
from dataclasses import dataclass

from PySide6.QtCore import QThread, Signal

from app.core.memory_model import ExecutionTrace
from app.core.ai_executor import AIExecutor

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecutionResult:
    trace: ExecutionTrace
    diagnostics: str = ""


class ExecutionWorker(QThread):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, code: str, config_path: Path | None = None, stdin_text: str = ""):
        super().__init__()
        self._code = code
        self._config_path = config_path
        self._stdin_text = stdin_text

    def run(self):
        try:
            executor = AIExecutor(self._config_path)
            trace = asyncio.run(executor.run_code(self._code, self._stdin_text))
            self.finished.emit(ExecutionResult(
                trace=trace,
                diagnostics=getattr(executor, "execution_summary", ""),
            ))
        except Exception as e:
            logger.error("Execution failed: %s", e)
            self.error.emit(str(e))
