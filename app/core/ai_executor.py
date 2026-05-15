import json
import logging
from pathlib import Path

from app.core.memory_model import ExecutionTrace
from app.services.ai_service import AIService
from app.services.prompt_templates import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

FALLBACK_DIR = Path(__file__).parent.parent.parent / "data" / "fallback"


class AIExecutor:
    def __init__(self, config_path: Path | None = None):
        self._ai_service = AIService(config_path)

    async def run_code(self, code: str) -> ExecutionTrace:
        user_msg = USER_PROMPT_TEMPLATE.format(code=code)
        raw_json = await self._ai_service.chat_json(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_msg,
        )
        data = json.loads(raw_json)
        trace = ExecutionTrace.model_validate(data)
        logger.info(f"ExecutionTrace validated: {len(trace.steps)} steps")
        return trace

    async def run_code_with_fallback(self, code: str) -> ExecutionTrace:
        try:
            return await self.run_code(code)
        except Exception as e:
            logger.warning(f"LLM execution failed: {e}")
            fallback = self._load_fallback(code)
            if fallback:
                return fallback
            raise

    def _load_fallback(self, code: str) -> ExecutionTrace | None:
        fallback_path = FALLBACK_DIR / "default.json"
        if not fallback_path.exists():
            return None
        with open(fallback_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ExecutionTrace.model_validate(data)
