"""
数据库模型
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Text, JSON, Integer, Boolean, ForeignKey, Float
from sqlalchemy.orm import DeclarativeBase, relationship
import uuid


class Base(DeclarativeBase):
    """基类"""
    pass


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Conversation(Base):
    """对话（对应一个项目）"""
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    project_path = Column(String(512), nullable=True)
    status = Column(String(50), default="idle")  # idle, running, paused, completed
    agent_configs = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    tasks = relationship("Task", back_populates="conversation", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    events = relationship("AgentEvent", back_populates="conversation", cascade="all, delete-orphan")


class Task(Base):
    """任务"""
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    parent_id = Column(String(36), nullable=True)  # 父任务 ID
    description = Column(Text, nullable=False)
    agent_type = Column(String(50), nullable=False)  # orchestrator, coder, reviewer, tester
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    priority = Column(String(20), default="normal")  # low, normal, high
    retry_count = Column(Integer, default=0)
    order_index = Column(Integer, default=0)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    conversation = relationship("Conversation", back_populates="tasks")


class Message(Base):
    """消息记录"""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    sender = Column(String(50), nullable=False)  # user, system, orchestrator, coder, reviewer, tester
    content = Column(Text, nullable=False)
    message_type = Column(String(50), default="text")  # text, system, command
    metadata_col = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    conversation = relationship("Conversation", back_populates="messages")


class AgentEvent(Base):
    """Agent 事件（用于可视化）"""
    __tablename__ = "agent_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    agent_name = Column(String(50), nullable=False)
    event_type = Column(String(50), nullable=False)  # thinking, acting, message, task_progress
    content = Column(Text, nullable=True)
    metadata_col = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    conversation = relationship("Conversation", back_populates="events")


class CodeResult(Base):
    """代码生成结果"""
    __tablename__ = "code_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    code = Column(Text, nullable=True)
    file_path = Column(String(512), nullable=True)
    language = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ReviewRecord(Base):
    """审查记录"""
    __tablename__ = "review_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    issues = Column(JSON, default=list)  # [{"type": "BLOCKER", "description": "..."}]
    score = Column(Float, default=0)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TestRecord(Base):
    """测试记录"""
    __tablename__ = "test_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    tests_passed = Column(Integer, default=0)
    tests_total = Column(Integer, default=0)
    pass_rate = Column(Float, default=0)
    output = Column(Text, nullable=True)
    status = Column(String(50), default="pending")  # pending, running, pass, fail
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    """用户"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)