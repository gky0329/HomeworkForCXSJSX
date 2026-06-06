import asyncio
import json
import os
from pathlib import Path

import httpx
import yaml


DEFAULT_PROVIDERS = {
    "deepseek": {
        "api_base": "https://api.deepseek.com",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
    },
    "openai": {
        "api_base": "https://api.openai.com",
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-4.1-mini",
    },
    "anthropic": {
        "api_base": "https://api.anthropic.com",
        "api_key_env": "ANTHROPIC_API_KEY",
        "model": "claude-sonnet-4-5",
    },
    "gemini": {
        "api_base": "https://generativelanguage.googleapis.com",
        "api_key_env": "GEMINI_API_KEY",
        "model": "gemini-2.5-flash",
    },
}


class AIService:
    def __init__(self, config_path: Path | None = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config.yaml"

        self._config = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}

        llm_cfg = self._config.get("llm", {})
        self.provider = str(llm_cfg.get("provider", "deepseek")).lower()
        if self.provider not in DEFAULT_PROVIDERS:
            raise RuntimeError(f"Unsupported LLM provider: {self.provider}")

        provider_cfg = dict(DEFAULT_PROVIDERS[self.provider])
        stored_providers = llm_cfg.get("providers", {})
        if isinstance(stored_providers, dict):
            provider_cfg.update(stored_providers.get(self.provider, {}) or {})

        # Keep old DeepSeek-only config.yaml files working.
        if self.provider == "deepseek":
            for key in ("api_base", "api_key", "model"):
                if llm_cfg.get(key):
                    provider_cfg[key] = llm_cfg[key]

        self.api_base = str(provider_cfg.get("api_base", ""))
        self.model = str(provider_cfg.get("model", ""))
        self.max_tokens = int(llm_cfg.get("max_tokens", 4096))
        self.temperature = float(llm_cfg.get("temperature", 0.0))

        self.api_key_env = str(provider_cfg.get("api_key_env", ""))
        self.api_key = (
            os.environ.get(self.api_key_env, "")
            or str(provider_cfg.get("api_key", ""))
        )
        self._proxy = (
            provider_cfg.get("proxy")
            or llm_cfg.get("proxy")
            or os.environ.get("HTTPS_PROXY")
            or os.environ.get("HTTP_PROXY")
            or None
        )

    async def chat_json(
        self,
        system_prompt: str,
        user_message: str,
        max_retries: int = 2,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        if self.provider in ("deepseek", "openai"):
            return await self._chat_openai_compatible(
                system_prompt,
                user_message,
                max_retries,
                model,
                json_mode=True,
                max_tokens=max_tokens,
            )
        if self.provider == "anthropic":
            return await self._chat_anthropic(
                system_prompt,
                user_message,
                max_retries,
                model,
                json_mode=True,
                max_tokens=max_tokens,
            )
        if self.provider == "gemini":
            return await self._chat_gemini(
                system_prompt,
                user_message,
                max_retries,
                model,
                json_mode=True,
                max_tokens=max_tokens,
            )
        raise RuntimeError(f"Unsupported LLM provider: {self.provider}")

    async def chat_text(
        self,
        system_prompt: str,
        user_message: str,
        max_retries: int = 1,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        if self.provider in ("deepseek", "openai"):
            return await self._chat_openai_compatible(
                system_prompt,
                user_message,
                max_retries,
                model,
                json_mode=False,
                max_tokens=max_tokens,
            )
        if self.provider == "anthropic":
            return await self._chat_anthropic(
                system_prompt,
                user_message,
                max_retries,
                model,
                json_mode=False,
                max_tokens=max_tokens,
            )
        if self.provider == "gemini":
            return await self._chat_gemini(
                system_prompt,
                user_message,
                max_retries,
                model,
                json_mode=False,
                max_tokens=max_tokens,
            )
        raise RuntimeError(f"Unsupported LLM provider: {self.provider}")

    def _require_key(self):
        if self.api_key:
            return
        hint = self.api_key_env or f"{self.provider.upper()}_API_KEY"
        raise RuntimeError(
            f"{self.provider} API key not configured. "
            f"Set {hint} or fill llm.providers.{self.provider}.api_key in config.yaml"
        )

    async def _chat_openai_compatible(
        self,
        system_prompt: str,
        user_message: str,
        max_retries: int,
        model: str | None,
        json_mode: bool,
        max_tokens: int | None,
    ) -> str:
        self._require_key()

        url = f"{self.api_base.rstrip('/')}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model or self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": self.temperature,
            "max_tokens": self._token_limit(json_mode, max_tokens),
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        data = await self._post_json(url, headers, payload, max_retries)
        choice = data["choices"][0]
        text = choice["message"]["content"]
        if json_mode and self._finish_reason_is_truncated(choice.get("finish_reason")):
            raise self._truncated_response_error(text, payload["max_tokens"])
        return self._normalize_json(text) if json_mode else text

    async def _chat_anthropic(
        self,
        system_prompt: str,
        user_message: str,
        max_retries: int,
        model: str | None,
        json_mode: bool,
        max_tokens: int | None,
    ) -> str:
        self._require_key()

        url = f"{self.api_base.rstrip('/')}/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        system = system_prompt
        if json_mode:
            system += "\n\nReturn only valid JSON. Do not include markdown fences."

        payload = {
            "model": model or self.model,
            "max_tokens": self._token_limit(json_mode, max_tokens),
            "temperature": self.temperature,
            "system": system,
            "messages": [
                {"role": "user", "content": user_message},
            ],
        }

        data = await self._post_json(url, headers, payload, max_retries)
        text = "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        )
        if json_mode and self._finish_reason_is_truncated(data.get("stop_reason")):
            raise self._truncated_response_error(text, payload["max_tokens"])
        return self._normalize_json(text) if json_mode else text

    async def _chat_gemini(
        self,
        system_prompt: str,
        user_message: str,
        max_retries: int,
        model: str | None,
        json_mode: bool,
        max_tokens: int | None,
    ) -> str:
        self._require_key()

        selected_model = model or self.model
        url = (
            f"{self.api_base.rstrip('/')}/v1beta/models/"
            f"{selected_model}:generateContent?key={self.api_key}"
        )
        headers = {"Content-Type": "application/json"}
        generation_config = {
            "temperature": self.temperature,
            "maxOutputTokens": self._token_limit(json_mode, max_tokens),
        }
        if json_mode:
            generation_config["responseMimeType"] = "application/json"

        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_message}],
                }
            ],
            "generationConfig": generation_config,
        }

        data = await self._post_json(url, headers, payload, max_retries)
        candidate = data["candidates"][0]
        parts = candidate["content"].get("parts", [])
        text = "".join(part.get("text", "") for part in parts)
        if json_mode and self._finish_reason_is_truncated(candidate.get("finishReason")):
            raise self._truncated_response_error(text, generation_config["maxOutputTokens"])
        return self._normalize_json(text) if json_mode else text

    def _token_limit(self, json_mode: bool, max_tokens: int | None) -> int:
        if max_tokens is not None:
            return int(max_tokens)
        return self.max_tokens if json_mode else 2048

    @staticmethod
    def _finish_reason_is_truncated(reason: object) -> bool:
        return str(reason or "").strip().lower() in {"length", "max_tokens", "max_tokens_limit", "max_output_tokens"}

    @staticmethod
    def _truncated_response_error(text: str, max_tokens: int) -> RuntimeError:
        return RuntimeError(
            "AI response was cut off by the token limit before valid JSON completed. "
            f"max_tokens={max_tokens}\n\n---RAW RESPONSE---\n{text[:4000]}"
        )

    async def _post_json(
        self,
        url: str,
        headers: dict,
        payload: dict,
        max_retries: int,
    ) -> dict:
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=60.0,
                    proxy=self._proxy,
                    trust_env=False,
                ) as client:
                    response = await client.post(url, json=payload, headers=headers)
                status_code = getattr(response, "status_code", None)
                if status_code is not None and status_code >= 400:
                    raise RuntimeError(
                        f"HTTP {response.status_code}: {response.text[:800]}"
                    )
                if status_code is None and hasattr(response, "raise_for_status"):
                    response.raise_for_status()
                return response.json()
            except (
                httpx.ConnectError,
                httpx.TimeoutException,
                httpx.HTTPStatusError,
                RuntimeError,
                json.JSONDecodeError,
                KeyError,
                IndexError,
            ) as e:
                last_error = e
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue

        raise RuntimeError(
            f"AI API call failed after {max_retries + 1} attempts: {last_error}"
        )

    @staticmethod
    def _normalize_json(text: str) -> str:
        cleaned = AIService.extract_json_text(text)
        try:
            json.loads(cleaned)
        except json.JSONDecodeError as e:
            context = AIService._json_error_context(cleaned, e)
            raise RuntimeError(
                "AI returned invalid JSON. This usually means the model response was "
                "truncated or mixed with non-JSON text. "
                f"{e.msg} at line {e.lineno}, column {e.colno}.\n"
                f"{context}\n\n---RAW RESPONSE---\n{text[:4000]}"
            ) from e
        return cleaned

    @staticmethod
    def extract_json_text(text: str) -> str:
        cleaned = (text or "").strip().lstrip("\ufeff")
        if not cleaned:
            return cleaned

        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        candidate = AIService._first_balanced_json(cleaned)
        return candidate or cleaned

    @staticmethod
    def load_json_text(text: str):
        normalized = AIService._normalize_json(text)
        return json.loads(normalized)

    @staticmethod
    def _first_balanced_json(text: str) -> str:
        start = -1
        for i, ch in enumerate(text):
            if ch in "{[":
                start = i
                break
        if start < 0:
            return ""

        stack: list[str] = []
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
            elif ch in "{[":
                stack.append("}" if ch == "{" else "]")
            elif ch in "}]":
                if not stack or ch != stack[-1]:
                    return text[start:i + 1].strip()
                stack.pop()
                if not stack:
                    return text[start:i + 1].strip()

        return text[start:].strip()

    @staticmethod
    def _json_error_context(text: str, error: json.JSONDecodeError) -> str:
        lines = text.splitlines()
        if not lines:
            return "No JSON content was returned."
        line_index = max(0, min(error.lineno - 1, len(lines) - 1))
        line = lines[line_index]
        pointer = " " * max(error.colno - 1, 0) + "^"
        return f"Near JSON line {error.lineno}:\n{line[:240]}\n{pointer[:240]}"
