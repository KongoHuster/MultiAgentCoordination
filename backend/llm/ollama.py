"""Ollama 本地模型适配器"""

import httpx
from typing import Optional, AsyncIterator
from .base import LLMConfig, LLMResponse, StreamCallback, Message


class OllamaAdapter:
    """Ollama 本地模型适配器"""

    DEFAULT_BASE_URL = "http://localhost:11434"
    DEFAULT_MODEL = "gemma2:9b"

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig(
            backend=LLMBackend.OLLAMA,
            model=self.DEFAULT_MODEL,
            base_url=self.DEFAULT_BASE_URL
        )
        self.base_url = self.config.base_url or self.DEFAULT_BASE_URL
        self.model = self.config.model or self.DEFAULT_MODEL
        self.timeout = self.config.timeout

    async def complete(
        self,
        messages: list[Message],
        system: Optional[str] = None,
        stream_callback: Optional[StreamCallback] = None
    ) -> LLMResponse:
        """同步调用 - 返回完整响应"""
        payload = self._build_payload(messages, system)

        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            if stream_callback:
                return await self._stream_complete(client, payload, stream_callback)
            else:
                return await self._blocking_complete(client, payload)

    async def _blocking_complete(self, client: httpx.AsyncClient, payload: dict) -> LLMResponse:
        """阻塞式完整响应"""
        response = await client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data.get("message", {}).get("content", ""),
            model=self.model,
            usage=data.get("usage", {}),
            finish_reason="stop"
        )

    async def _stream_complete(
        self,
        client: httpx.AsyncClient,
        payload: dict,
        stream_callback: StreamCallback
    ) -> LLMResponse:
        """流式响应"""
        full_content = ""

        async with client.stream("POST", "/api/chat", json={**payload, "stream": True}) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line.strip():
                    continue

                try:
                    chunk = json.loads(line)
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        full_content += content
                        if stream_callback:
                            await stream_callback(content)
                except json.JSONDecodeError:
                    continue

        return LLMResponse(
            content=full_content,
            model=self.model,
            finish_reason="stop"
        )

    def _build_payload(self, messages: list[Message], system: Optional[str]) -> dict:
        """构建请求 payload"""
        formatted_messages = []

        if system:
            formatted_messages.append({"role": "system", "content": system})

        for msg in messages:
            formatted_messages.append(msg.to_dict())

        return {
            "model": self.model,
            "messages": formatted_messages,
            "stream": False
        }

    async def list_models(self) -> list[dict]:
        """列出可用模型"""
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=5) as client:
                response = await client.get("/api/tags")
                return response.status_code == 200
        except Exception:
            return False


# 修复导入
from .base import LLMBackend

OllamaAdapter.__init__.__annotations__["config"] = Optional[LLMConfig]