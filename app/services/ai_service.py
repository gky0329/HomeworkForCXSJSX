import json
import os
import httpx
import yaml
from pathlib import Path
from typing import Optional


class AIService:
    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config.yaml"

        self._config = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}

        llm_cfg = self._config.get("llm", {})
        self.api_key = os.environ.get("DEEPSEEK_API_KEY") or llm_cfg.get("api_key", "")
        self.api_base = llm_cfg.get("api_base", "https://api.deepseek.com")
        self.model = llm_cfg.get("model", "deepseek-chat")
        self.max_tokens = llm_cfg.get("max_tokens", 4096)
        self.temperature = llm_cfg.get("temperature", 0.0)

    async def chat_json(
        self,
        system_prompt: str,
        user_message: str,
        max_retries: int = 2,
    ) -> str:
        if not self.api_key:
            raise RuntimeError(
                "DeepSeek API key not configured. "
                "Set DEEPSEEK_API_KEY environment variable or "
                "fill llm.api_key in config.yaml"
            )

        url = f"{self.api_base.rstrip('/')}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    return json.dumps(parsed, ensure_ascii=False)

            except httpx.HTTPStatusError as e:
                last_error = e
                if attempt < max_retries:
                    continue
            except (json.JSONDecodeError, KeyError) as e:
                last_error = e
                if attempt < max_retries:
                    continue

        raise RuntimeError(
            f"AI API call failed after {max_retries + 1} attempts: {last_error}"
        )
