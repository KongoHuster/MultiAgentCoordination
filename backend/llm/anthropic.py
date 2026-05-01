"""Anthropic Claude 适配器"""

import anthropic
from typing import Optional, AsyncIterator
from .base import LLMConfig, LLMResponse, StreamCallback, Message


class AnthropicAdapter:
    """Anthropic Claude API 适配器"""

    DEFAULT_BASE_URL = "https://api.anthropic.com"
    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig(
            backend=LLMBackend.ANTHROPIC,
            model=self.DEFAULT_MODEL
        )
        self.api_key = self.config.api_key or ""
        self.base_url = self.config.base_url or self.DEFAULT_BASE_URL
        self.model = self.config.model or self.DEFAULT_MODEL
        self.max_tokens = self.config.max_tokens
        self.temperature = self.config.temperature
        self.timeout = self.config.timeout

        self.client = anthropic.Anthropic(
            api_key=self.api_key,
            base_url=self.base_url
        )

    async def complete(
        self,
        messages: list[Message],
        system: Optional[str] = None,
        stream_callback: Optional[StreamCallback] = None
    ) -> LLMResponse:
        """调用 Claude API"""
        formatted_messages = [msg.to_dict() for msg in messages]

        params = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": formatted_messages,
            "temperature": self.temperature
        }

        if system:
            params["system"] = system

        if stream_callback:
            return await self._stream_complete(params, stream_callback)
        else:
            return await self._blocking_complete(params)

    async def _blocking_complete(self, params: dict) -> LLMResponse:
        """阻塞式完整响应"""
        response = self.client.messages.create(**params)

        return LLMResponse(
            content=response.content[0].text if response.content else "",
            model=self.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            },
            finish_reason=response.stop_reason
        )

    async def _stream_complete(
        self,
        params: dict,
        stream_callback: StreamCallback
    ) -> LLMResponse:
        """流式响应"""
        full_content = ""

        with self.client.messages.stream(**params, stream=True) as stream:
            for event in stream:
                if event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        content = event.delta.text
                        full_content += content
                        # 注意：这里需要异步处理
                        # Claude SDK 的 stream 是同步迭代器

        return LLMResponse(
            content=full_content,
            model=self.model,
            finish_reason="stop"
        )

    async def list_models(self) -> list[dict]:
        """列出可用模型（需要特殊 API）"""
        # Anthropic 没有公开的模型列表 API
        return [
            {"name": "claude-3-5-sonnet-20241022", "description": "Claude 3.5 Sonnet"},
            {"name": "claude-3-opus-20240229", "description": "Claude 3 Opus"},
            {"name": "claude-3-haiku-20240307", "description": "Claude 3 Haiku"}
        ]

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            self.client.messages.create(
                model=self.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}]
            )
            return True
        except Exception:
            return False


from .base import LLMBackend