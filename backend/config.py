"""
配置管理模块
"""

from dataclasses import dataclass, field
from typing import Optional
import os
import json


@dataclass
class DatabaseConfig:
    """数据库配置"""
    url: str = os.getenv("DATABASE_URL", "sqlite:///./agency_visual.db")
    echo: bool = False


@dataclass
class LLMProviderConfig:
    """LLM 提供商配置"""
    backend: str = os.getenv("LLM_BACKEND", "ollama")
    api_key: Optional[str] = os.getenv("API_KEY", None)
    base_url: Optional[str] = os.getenv("LLM_BASE_URL", None)
    model: str = os.getenv("LLM_MODEL", "gemma2:9b")
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 300


@dataclass
class AppConfig:
    """应用配置"""
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"])

    # 项目相关
    projects_dir: str = os.getenv("PROJECTS_DIR", "generated_projects")
    max_retries: int = 3
    git_auto_commit: bool = True

    # LLM 配置
    default_llm: LLMProviderConfig = field(default_factory=LLMProviderConfig)
    orchestrator_llm: LLMProviderConfig = field(default_factory=LLMProviderConfig)
    coder_llm: LLMProviderConfig = field(default_factory=LLMProviderConfig)
    reviewer_llm: LLMProviderConfig = field(default_factory=LLMProviderConfig)
    tester_llm: LLMProviderConfig = field(default_factory=LLMProviderConfig)


@dataclass
class Config:
    """全局配置"""
    app: AppConfig = field(default_factory=AppConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config(config_dict: dict = None):
    """重新加载配置"""
    global _config

    if config_dict is None:
        _config = Config()
    else:
        _config = Config(
            app=AppConfig(**config_dict.get("app", {})),
            database=DatabaseConfig(**config_dict.get("database", {}))
        )

    return _config