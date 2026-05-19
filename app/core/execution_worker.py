import asyncio
import logging
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.core.memory_model import ExecutionTrace
from app.core.ai_executor import AIExecutor

logger = logging.getLogger(__name__)


class ExecutionWorker(QThread):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, code: str, config_path: Path | None = None):
        super().__init__()
        self._code = code
        self._config_path = config_path

    def run(self):
        try:
            executor = AIExecutor(self._config_path)
            trace = asyncio.run(executor.run_code(self._code))
            self.finished.emit(trace)
        except Exception as e:
            logger.exception("ExecutionWorker failed")
            self.error.emit(str(e))
