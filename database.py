"""
Database - 数据库连接模块
支持 PostgreSQL 数据库
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

# 数据库配置 - 支持环境变量和配置
def get_database_url():
    """获取数据库URL"""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/multiagent"
    )

# 创建引擎
_engine = None
_Session = None


def get_engine():
    """获取数据库引擎"""
    global _engine
    if _engine is None:
        DATABASE_URL = get_database_url()
        _engine = create_engine(
            DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False
        )
    return _engine


def get_session():
    """获取数据库会话"""
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=get_engine())
    return _Session()


def init_db():
    """初始化数据库 - 创建所有表"""
    from models import Conversation, Task, Message, CodeResult, ReviewRecord, TestRecord
    Base.metadata.create_all(get_engine())


def drop_db():
    """删除所有表"""
    Base.metadata.drop_all(get_engine())