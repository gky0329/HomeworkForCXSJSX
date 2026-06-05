import json
import logging
from pathlib import Path

from pydantic import ValidationError
from app.core.memory_model import ExecutionTrace
from app.core.debug_executor import DebugExecutionError, DebugExecutor
from app.services.ai_service import AIService
from app.services.prompt_templates import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

AI_JSON_RETRY_MIN_TOKENS = 8192


class AIExecutor:
    def __init__(self, config_path: Path | None = None):
        self._ai_service = AIService(config_path)
        self._debug_executor = DebugExecutor(config_path=config_path)
        self.execution_summary = ""

    async def run_code(self, code: str, stdin_text: str = "") -> ExecutionTrace:
        self.execution_summary = ""
        fallback_reason = ""
        prefer_ai = (
            bool(getattr(self._ai_service, "api_key", ""))
            and DebugExecutor.should_prefer_ai_for_complex_code(code)
        )
        if prefer_ai:
            self.execution_summary = "AI fallback: complex code skipped native debugger"
            logger.info("DebugExecutor skipped complex code; using AI fallback")
        else:
            try:
                trace = self._debug_executor.run_code(code, stdin_text)
                backend_label = getattr(self._debug_executor, "last_backend_label", "") or "native debugger"
                self.execution_summary = f"Native debugger: {backend_label}"
                logger.info("DebugExecutor produced %d steps", len(trace.steps))
                return trace
            except DebugExecutionError as e:
                fallback_reason = str(e)
                self.execution_summary = f"AI fallback: {fallback_reason}"
                logger.info("DebugExecutor fallback to AI: %s", e)

        user_msg = USER_PROMPT_TEMPLATE.format(code=code)
        if stdin_text.strip():
            user_msg += f"\n\n[Program stdin]\n{stdin_text.strip()}"
        try:
            raw_response = await self._chat_json_with_retry(user_msg)
        except RuntimeError as e:
            if fallback_reason:
                raise RuntimeError(
                    f"Native debugger failed first: {fallback_reason}\n"
                    f"AI fallback failed: {e}"
                ) from e
            raise
        try:
            data = json.loads(raw_response)
            trace = ExecutionTrace.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            prefix = ""
            if fallback_reason:
                prefix = f"Native debugger failed first: {fallback_reason}\n"
            raise RuntimeError(
                f"{prefix}LLM returned invalid response: {e}\n\n---RAW RESPONSE---\n{raw_response[:2000]}"
            ) from e
        if not self.execution_summary:
            self.execution_summary = "AI provider"
        elif fallback_reason and self.execution_summary == f"AI fallback: {fallback_reason}":
            self.execution_summary = f"AI fallback after native debugger failed: {fallback_reason}"
        logger.info(f"ExecutionTrace validated: {len(trace.steps)} steps")
        return trace

    async def _chat_json_with_retry(self, user_msg: str) -> str:
        configured_limit = int(getattr(self._ai_service, "max_tokens", 4096) or 4096)
        retry_limit = max(AI_JSON_RETRY_MIN_TOKENS, configured_limit * 2)
        token_limits: list[int | None] = [None]
        if retry_limit > configured_limit:
            token_limits.append(retry_limit)

        last_error: RuntimeError | None = None
        for index, token_limit in enumerate(token_limits):
            try:
                return await self._ai_service.chat_json(
                    system_prompt=SYSTEM_PROMPT,
                    user_message=user_msg,
                    max_tokens=token_limit,
                )
            except RuntimeError as e:
                if index == 0 and self._should_retry_json_error(str(e)):
                    last_error = e
                    logger.info(
                        "Retrying AI JSON execution with max_tokens=%s after: %s",
                        retry_limit,
                        str(e).splitlines()[0],
                    )
                    continue
                if last_error is not None:
                    raise RuntimeError(
                        f"{last_error}\n\nRetry with max_tokens={token_limit} also failed: {e}"
                    ) from e
                raise

        if last_error is not None:
            raise last_error
        raise RuntimeError("AI execution returned no response")

    @staticmethod
    def _should_retry_json_error(message: str) -> bool:
        retry_markers = (
            "AI returned invalid JSON",
            "cut off by the token limit",
            "truncated",
            "Unterminated string",
            "Expecting value",
        )
        return any(marker in message for marker in retry_markers)
