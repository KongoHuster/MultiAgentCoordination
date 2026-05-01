"""
API 路由 - LLM 配置
"""

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from llm.base import LLMBackend
from llm.gateway import get_gateway


router = APIRouter(prefix="/llm", tags=["llm"])


class LLMProviderConfig(BaseModel):
    backend: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None


@router.get("/providers")
async def list_providers():
    """列出支持的 LLM 提供商"""
    return {
        "providers": [
            {
                "id": "ollama",
                "name": "Ollama (本地)",
                "default_model": "gemma2:9b",
                "requires_api_key": False,
                "supports_streaming": True
            },
            {
                "id": "anthropic",
                "name": "Anthropic Claude",
                "default_model": "claude-3-5-sonnet-20241022",
                "requires_api_key": True,
                "supports_streaming": True
            },
            {
                "id": "zhipu",
                "name": "智谱 GLM",
                "default_model": "glm-4-flash",
                "requires_api_key": True,
                "supports_streaming": True
            },
            {
                "id": "deepseek",
                "name": "DeepSeek",
                "default_model": "deepseek-chat",
                "requires_api_key": True,
                "supports_streaming": True
            }
        ]
    }


@router.get("/health")
async def check_llm_health(backend: Optional[str] = None):
    """检查 LLM 服务健康状态"""
    gateway = get_gateway()

    if backend:
        try:
            config = LLMConfig(
                backend=LLMBackend(backend),
                model="default"
            )
            result = await gateway.health_check(config)
            return {"backend": backend, "healthy": result.get(backend, False)}
        except Exception as e:
            return {"backend": backend, "healthy": False, "error": str(e)}
    else:
        # 检查所有
        results = await gateway.health_check(None)
        return {"backends": results}


@router.get("/models/{backend}")
async def list_models(backend: str):
    """列出指定后端的可用模型"""
    try:
        llm_backend = LLMBackend(backend)
    except ValueError:
        return {"error": f"Unknown backend: {backend}"}

    gateway = get_gateway()
    config = gateway._get_default_config(llm_backend)

    try:
        models = await gateway.list_models(config)
        return {"backend": backend, "models": models}
    except Exception as e:
        return {"backend": backend, "error": str(e)}


from llm.base import LLMConfig