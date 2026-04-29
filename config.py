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

    # Ollama 配置
    use_ollama: bool = True
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma2:9b"

    # 模型配置
    default_model: str = "glm-5"
    max_tokens: int = 4096

    # 工作流配置
    max_retries: int = 3
    max_concurrent_tasks: int = 5

    # Git 配置
    git_auto_commit: bool = True
    git_branch: str = "main"

    # 数据库配置
    database_url: str = "postgresql://postgres:postgres@localhost:5432/multiagent"

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            base_url=os.getenv("ANTHROPIC_BASE_URL", "https://milukey.cn"),
            use_ollama=os.getenv("USE_OLLAMA", "true").lower() == "true",
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "gemma2:9b"),
            default_model=os.getenv("ANTHROPIC_DEFAULT_SONNET_MODEL", "glm-5"),
            max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            git_auto_commit=os.getenv("GIT_AUTO_COMMIT", "true").lower() == "true",
            database_url=os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/multiagent")
        )


def get_config() -> Config:
    """获取配置"""
    return Config.from_env()
