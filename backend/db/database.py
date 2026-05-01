"""
数据库模块
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator, Optional
from config import get_config


# 创建全局引擎（懒加载）
_engine = None
_SessionLocal = None


def get_engine():
    """获取数据库引擎"""
    global _engine
    if _engine is None:
        config = get_config()
        _engine = create_engine(config.database.url, echo=config.database.echo)
    return _engine


def get_session_local():
    """获取 SessionLocal"""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """获取数据库会话的上下文管理器"""
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库表"""
    engine = get_engine()
    from .models import Base
    Base.metadata.create_all(bind=engine)