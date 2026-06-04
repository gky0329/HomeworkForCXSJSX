import json
import logging
from pathlib import Path

from pydantic import ValidationError
from app.core.memory_model import ExecutionTrace
from app.core.debug_executor import DebugExecutionError, DebugExecutor
from app.services.ai_service import AIService
from app.services.prompt_templates import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class AIExecutor:
    def __init__(self, config_path: Path | None = None):
        self._ai_service = AIService(config_path)
        self._debug_executor = DebugExecutor()

    async def run_code(self, code: str, stdin_text: str = "") -> ExecutionTrace:
        try:
            trace = self._debug_executor.run_code(code, stdin_text)
            logger.info("DebugExecutor produced %d steps", len(trace.steps))
            return trace
        except DebugExecutionError as e:
            logger.info("DebugExecutor fallback to AI: %s", e)

        user_msg = USER_PROMPT_TEMPLATE.format(code=code)
        if stdin_text.strip():
            user_msg += f"\n\n[Program stdin]\n{stdin_text.strip()}"
        raw_response = await self._ai_service.chat_json(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_msg,
        )
        try:
            data = json.loads(raw_response)
            trace = ExecutionTrace.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise RuntimeError(
                f"LLM returned invalid response: {e}\n\n---RAW RESPONSE---\n{raw_response[:2000]}"
            ) from e
        logger.info(f"ExecutionTrace validated: {len(trace.steps)} steps")
        return trace
