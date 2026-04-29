"""
Models - 数据库模型定义
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


def generate_id():
    """生成唯一ID"""
    return str(uuid.uuid4())


class Conversation(Base):
    """对话记录"""
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=generate_id)
    user_request = Column(Text, nullable=False)
    project_name = Column(String)
    project_path = Column(String)
    git_repo_path = Column(String)
    status = Column(String, default="running")  # running, completed, failed
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    tasks = relationship("Task", back_populates="conversation", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_request": self.user_request,
            "project_name": self.project_name,
            "project_path": self.project_path,
            "git_repo_path": self.git_repo_path,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Task(Base):
    """任务记录"""
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=generate_id)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"))
    parent_id = Column(String, nullable=True)
    description = Column(Text)
    agent = Column(String, default="coder")  # coder, reviewer, tester
    status = Column(String, default="pending")  # pending, in_progress, completed, failed, retry
    retries = Column(Integer, default=0)
    result = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    conversation = relationship("Conversation", back_populates="tasks")
    code_result = relationship("CodeResult", back_populates="task", uselist=False, cascade="all, delete-orphan")
    review_record = relationship("ReviewRecord", back_populates="task", uselist=False, cascade="all, delete-orphan")
    test_record = relationship("TestRecord", back_populates="task", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "parent_id": self.parent_id,
            "description": self.description,
            "agent": self.agent,
            "status": self.status,
            "retries": self.retries,
            "result": self.result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Message(Base):
    """消息记录"""
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=generate_id)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"))
    agent = Column(String)  # orchestrator, coder, reviewer, tester, system
    agent_name = Column(String)
    agent_icon = Column(String)
    message_type = Column(String)  # workflow_start, coding_start, coding_complete, etc.
    content = Column(Text)
    extra_data = Column(JSON)  # 使用 extra_data 代替 metadata（metadata 是 SQLAlchemy 保留字）
    created_at = Column(DateTime, default=datetime.now)

    # 关系
    conversation = relationship("Conversation", back_populates="messages")

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "agent": self.agent,
            "agent_name": self.agent_name,
            "agent_icon": self.agent_icon,
            "message_type": self.message_type,
            "content": self.content,
            "extra_data": self.extra_data,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class CodeResult(Base):
    """代码结果"""
    __tablename__ = "code_results"

    id = Column(String, primary_key=True, default=generate_id)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), unique=True)
    code = Column(Text)
    language = Column(String, default="python")
    file_path = Column(String)
    created_at = Column(DateTime, default=datetime.now)

    # 关系
    task = relationship("Task", back_populates="code_result")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "code": self.code,
            "language": self.language,
            "file_path": self.file_path,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class ReviewRecord(Base):
    """审查记录"""
    __tablename__ = "review_records"

    id = Column(String, primary_key=True, default=generate_id)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), unique=True)
    score = Column(Integer, default=0)  # 1-10
    has_blocker = Column(Boolean, default=False)
    issues = Column(JSON)  # [{"severity": "BLOCKER/WARNING", "description": "..."}]
    review_content = Column(Text)  # 完整审查内容
    created_at = Column(DateTime, default=datetime.now)

    # 关系
    task = relationship("Task", back_populates="review_record")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "score": self.score,
            "has_blocker": self.has_blocker,
            "issues": self.issues,
            "review_content": self.review_content,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class TestRecord(Base):
    """测试记录"""
    __tablename__ = "test_records"

    id = Column(String, primary_key=True, default=generate_id)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), unique=True)
    status = Column(String, default="UNKNOWN")  # PASS, FAIL, N/A
    pass_rate = Column(Integer, default=0)  # 0-100
    tests = Column(JSON)  # [{"name": "test_xxx", "passed": true/false, "error": "..."}]
    test_content = Column(Text)  # 完整测试内容
    created_at = Column(DateTime, default=datetime.now)

    # 关系
    task = relationship("Task", back_populates="test_record")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "status": self.status,
            "pass_rate": self.pass_rate,
            "tests": self.tests,
            "test_content": self.test_content,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }