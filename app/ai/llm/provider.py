import json
import os
from typing import Any

import httpx


class LLMProvider:
    """Small OpenAI-compatible adapter returning validated JSON only.

    It is intentionally opt-in. The assistant remains deterministic when no
    endpoint and key are configured, and this provider never writes databases.
    """

    def __init__(self, endpoint: str | None = None, api_key: str | None = None):
        self.endpoint = endpoint or os.getenv("LLM_API_URL")
        self.api_key = api_key or os.getenv("LLM_API_KEY")

    @property
    def enabled(self) -> bool:
        return bool(self.endpoint and self.api_key)

    async def structured_json(self, system_prompt: str, user_message: str) -> dict[str, Any] | None:
        if not self.enabled:
            return None

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.post(self.endpoint, json=payload, headers=headers)
                response.raise_for_status()
                body = response.json()
                content = body.get("choices", [{}])[0].get("message", {}).get("content")
                if not isinstance(content, str):
                    return None
                parsed = json.loads(content)
                return parsed if isinstance(parsed, dict) else None
        except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError):
            return None