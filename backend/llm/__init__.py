"""LLM Gateway - 统一接口模块

提供统一的 LLM 调用接口，支持多种后端：
- Ollama (本地)
- Anthropic Claude
- 智谱 GLM
- DeepSeek
"""

from .base import LLMConfig, LLMResponse
from .gateway import LLMGateway

__all__ = ["LLMConfig", "LLMResponse", "LLMGateway"]