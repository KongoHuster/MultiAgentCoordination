"""api 模块"""
from fastapi import APIRouter
from .routes import conversations, agents, git_ops, llm


def create_api_router() -> APIRouter:
    """创建 API 路由"""
    api_router = APIRouter(prefix="/api")

    api_router.include_router(conversations.router)
    api_router.include_router(agents.router)
    api_router.include_router(git_ops.router)
    api_router.include_router(llm.router)

    return api_router


__all__ = ["create_api_router"]
