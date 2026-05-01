"""
Base Agent - Agent 基类
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Awaitable, Any
from dataclasses import dataclass
import json
import re

from llm.base import LLMConfig, LLMResponse, Message, LLMBackend
from llm.gateway import get_gateway


@dataclass
class ToolResult:
    """工具调用结果"""
    tool_name: str
    success: bool
    output: str
    error: Optional[str] = None


@dataclass
class AgentResponse:
    """Agent 响应"""
    content: str
    tool_calls: list[dict] = None
    finish_reason: str = "stop"

    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []


class BaseAgent(ABC):
    """Agent 基类"""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        llm_config: Optional[LLMConfig] = None,
        max_tokens: int = 4096
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.llm_config = llm_config or self._default_llm_config()
        self.max_tokens = max_tokens
        self._gateway = get_gateway()
        self._stream_callback: Optional[Callable[[str], Awaitable[None]]] = None

    def _default_llm_config(self) -> LLMConfig:
        """获取默认 LLM 配置"""
        return LLMConfig(
            backend=LLMBackend.OLLAMA,
            model="gemma2:9b",
            max_tokens=self.max_tokens
        )

    async def execute(
        self,
        prompt: str,
        history: Optional[list[Message]] = None,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> AgentResponse:
        """执行 Agent"""
        self._stream_callback = stream_callback

        messages = []
        if self.system_prompt:
            messages.append(Message(role="system", content=self.system_prompt))

        if history:
            messages.extend(history)

        messages.append(Message(role="user", content=prompt))

        response = await self._gateway.complete(
            messages=messages,
            config=self.llm_config,
            stream_callback=self._on_stream if stream_callback else None
        )

        return AgentResponse(
            content=response.content,
            finish_reason=response.finish_reason or "stop"
        )

    async def _on_stream(self, chunk: str):
        """流式输出回调"""
        if self._stream_callback:
            await self._stream_callback(chunk)

    def set_llm_config(self, config: LLMConfig):
        """设置 LLM 配置"""
        self.llm_config = config

    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        pass


class AgentState:
    """Agent 状态"""

    def __init__(self):
        self.is_running = False
        self.is_paused = False
        self.current_task_id: Optional[str] = None
        self.last_message: Optional[str] = None
        self.thinking: Optional[str] = None
        self.metadata: dict = {}


class AgentRegistry:
    """Agent 注册表"""

    _agents: dict[str, type[BaseAgent]] = {}

    @classmethod
    def register(cls, name: str, agent_class: type[BaseAgent]):
        """注册 Agent"""
        cls._agents[name] = agent_class

    @classmethod
    def get(cls, name: str) -> Optional[type[BaseAgent]]:
        """获取 Agent 类"""
        return cls._agents.get(name)

    @classmethod
    def list_agents(cls) -> list[str]:
        """列出所有注册的 Agent"""
        return list(cls._agents.keys())


def agent(name: str):
    """Agent 注册装饰器"""
    def decorator(cls: type[BaseAgent]):
        AgentRegistry.register(name, cls)
        return cls
    return decorator