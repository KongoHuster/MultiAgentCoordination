"""LLM Gateway - 统一入口

提供统一的 LLM 调用接口，根据配置选择对应的适配器
"""

from typing import Optional, AsyncIterator
from .base import LLMConfig, LLMResponse, LLMBackend, StreamCallback, Message
from .ollama import OllamaAdapter
from .anthropic import AnthropicAdapter
from .zhipu import ZhipuAdapter
from .deepseek import DeepSeekAdapter


class LLMGateway:
    """统一 LLM 网关"""

    def __init__(self):
        self._adapters = {
            LLMBackend.OLLAMA: OllamaAdapter,
            LLMBackend.ANTHROPIC: AnthropicAdapter,
            LLMBackend.ZHIPU: ZhipuAdapter,
            LLMBackend.DEEPSEEK: DeepSeekAdapter,
        }
        self._instances = {}

    def get_adapter(self, config: LLMConfig):
        """获取对应后端的适配器实例"""
        if config.backend not in self._adapters:
            raise ValueError(f"Unsupported backend: {config.backend}")

        # 缓存实例
        cache_key = f"{config.backend.value}:{config.model}"
        if cache_key not in self._instances:
            adapter_class = self._adapters[config.backend]
            self._instances[cache_key] = adapter_class(config)

        return self._instances[cache_key]

    async def complete(
        self,
        messages: list[Message],
        config: LLMConfig,
        system: Optional[str] = None,
        stream_callback: Optional[StreamCallback] = None
    ) -> LLMResponse:
        """统一调用接口"""
        adapter = self.get_adapter(config)
        return await adapter.complete(messages, system, stream_callback)

    async def health_check(self, config: LLMConfig) -> dict[str, bool]:
        """检查所有后端或指定后端的健康状态"""
        if config:
            adapter = self.get_adapter(config)
            return {config.backend.value: await adapter.health_check()}

        # 检查所有已配置的后端
        results = {}
        for backend in self._adapters.keys():
            try:
                # 使用默认配置检查
                default_config = self._get_default_config(backend)
                adapter = self.get_adapter(default_config)
                results[backend.value] = await adapter.health_check()
            except Exception:
                results[backend.value] = False

        return results

    async def list_models(self, config: LLMConfig) -> list[dict]:
        """列出指定后端的可用模型"""
        adapter = self.get_adapter(config)
        return await adapter.list_models()

    def _get_default_config(self, backend: LLMBackend) -> LLMConfig:
        """获取后端的默认配置"""
        defaults = {
            LLMBackend.OLLAMA: LLMConfig(backend=LLMBackend.OLLAMA, model="gemma2:9b"),
            LLMBackend.ANTHROPIC: LLMConfig(backend=LLMBackend.ANTHROPIC, model="claude-3-5-sonnet-20241022"),
            LLMBackend.ZHIPU: LLMConfig(backend=LLMBackend.ZHIPU, model="glm-4-flash"),
            LLMBackend.DEEPSEEK: LLMConfig(backend=LLMBackend.DEEPSEEK, model="deepseek-chat"),
        }
        return defaults.get(backend, LLMConfig(backend=backend, model=""))


# 全局单例
_gateway: Optional[LLMGateway] = None


def get_gateway() -> LLMGateway:
    """获取 LLM Gateway 单例"""
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway