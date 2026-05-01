"""LLM 配置和响应类型定义"""

from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable
from enum import Enum
import json


class LLMBackend(Enum):
    """支持的 LLM 后端"""
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    ZHIPU = "zhipu"
    DEEPSEEK = "deepseek"


@dataclass
class LLMConfig:
    """LLM 调用配置"""
    backend: LLMBackend
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 300

    def to_json(self) -> str:
        return json.dumps({
            "backend": self.backend.value,
            "model": self.model,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "timeout": self.timeout
        })

    @classmethod
    def from_json(cls, data: str) -> "LLMConfig":
        d = json.loads(data)
        return cls(
            backend=LLMBackend(d["backend"]),
            model=d["model"],
            api_key=d.get("api_key"),
            base_url=d.get("base_url"),
            max_tokens=d.get("max_tokens", 4096),
            temperature=d.get("temperature", 0.7),
            timeout=d.get("timeout", 300)
        )


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    model: str
    usage: dict = field(default_factory=dict)
    finish_reason: Optional[str] = None
    raw_response: Optional[dict] = None

    @property
    def is_complete(self) -> bool:
        return self.finish_reason in ("stop", "complete", "eos")


# 流式回调类型
StreamCallback = Callable[[str], Awaitable[None]]


@dataclass
class Message:
    """对话消息"""
    role: str  # system, user, assistant
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass
class ToolCall:
    """工具调用"""
    name: str
    arguments: dict


@dataclass
class ToolResult:
    """工具结果"""
    tool_call_id: str
    output: str