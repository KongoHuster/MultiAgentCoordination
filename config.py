"""
配置模块
"""
import os
from dataclasses import dataclass


@dataclass
class Config:
    """系统配置"""
    # API 配置
    anthropic_api_key: str = ""
    base_url: str = "https://milukey.cn"

    # 模型配置
    default_model: str = "glm-5"
    max_tokens: int = 4096

    # 工作流配置
    max_retries: int = 3
    max_concurrent_tasks: int = 5

    # Git 配置
    git_auto_commit: bool = True
    git_branch: str = "main"

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            base_url=os.getenv("ANTHROPIC_BASE_URL", "https://milukey.cn"),
            default_model=os.getenv("ANTHROPIC_DEFAULT_SONNET_MODEL", "glm-5"),
            max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            git_auto_commit=os.getenv("GIT_AUTO_COMMIT", "true").lower() == "true"
        )


def get_config() -> Config:
    """获取配置"""
    return Config.from_env()
