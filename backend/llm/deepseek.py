"""DeepSeek 适配器"""

import httpx
import json
from typing import Optional
from .base import LLMConfig, LLMResponse, StreamCallback, Message


class DeepSeekAdapter:
    """DeepSeek API 适配器"""

    DEFAULT_BASE_URL = "https://api.deepseek.com"
    DEFAULT_MODEL = "deepseek-chat"

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig(
            backend=LLMBackend.DEEPSEEK,
            model=self.DEFAULT_MODEL
        )
        self.api_key = self.config.api_key or ""
        self.base_url = self.config.base_url or self.DEFAULT_BASE_URL
        self.model = self.config.model or self.DEFAULT_MODEL
        self.max_tokens = self.config.max_tokens
        self.temperature = self.config.temperature
        self.timeout = self.config.timeout

    async def complete(
        self,
        messages: list[Message],
        system: Optional[str] = None,
        stream_callback: Optional[StreamCallback] = None
    ) -> LLMResponse:
        """调用 DeepSeek API"""
        formatted_messages = []

        if system:
            formatted_messages.append({"role": "system", "content": system})

        formatted_messages.extend([msg.to_dict() for msg in messages])

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": stream_callback is not None
        }

        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            if stream_callback:
                return await self._stream_complete(client, headers, payload, stream_callback)
            else:
                return await self._blocking_complete(client, headers, payload)

    async def _blocking_complete(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        payload: dict
    ) -> LLMResponse:
        """阻塞式完整响应"""
        response = await client.post("/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=self.model,
            usage=data.get("usage", {}),
            finish_reason=data["choices"][0].get("finish_reason")
        )

    async def _stream_complete(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        payload: dict,
        stream_callback: StreamCallback
    ) -> LLMResponse:
        """流式响应"""
        full_content = ""

        async with client.stream("POST", "/chat/completions", json=payload, headers=headers) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line.strip() or not line.startswith("data:"):
                    continue

                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break

                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if delta:
                        full_content += delta
                        await stream_callback(delta)
                except json.JSONDecodeError:
                    continue

        return LLMResponse(
            content=full_content,
            model=self.model,
            finish_reason="stop"
        )

    async def list_models(self) -> list[dict]:
        """列出可用模型"""
        return [
            {"name": "deepseek-chat", "description": "DeepSeek Chat"},
            {"name": "deepseek-coder", "description": "DeepSeek Coder"}
        ]

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 10
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                return response.status_code == 200
        except Exception:
            return False


from .base import LLMBackend