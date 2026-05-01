"""
API 路由 - 对话管理
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import uuid

from db import get_db, Conversation, Message, AgentEvent
from core.workflow_engine import create_workflow, get_workflow
from websocket.manager import get_ws_manager


router = APIRouter(prefix="/conversations", tags=["conversations"])


class CreateConversationRequest(BaseModel):
    name: str
    task: Optional[str] = None
    agent_configs: Optional[dict] = None


class SendMessageRequest(BaseModel):
    content: str
    sender: str = "user"


class ConversationResponse(BaseModel):
    id: str
    name: str
    status: str
    project_path: Optional[str] = None
    agent_configs: dict
    created_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: str
    sender: str
    content: str
    message_type: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("", response_model=ConversationResponse)
async def create_conversation(request: CreateConversationRequest):
    """创建新对话"""
    conversation_id = str(uuid.uuid4())

    with get_db() as db:
        conversation = Conversation(
            id=conversation_id,
            name=request.name,
            status="idle",
            agent_configs=request.agent_configs or {}
        )

        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    return conversation


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(skip: int = 0, limit: int = 50):
    """获取对话列表"""
    with get_db() as db:
        conversations = db.query(Conversation) \
            .order_by(Conversation.updated_at.desc()) \
            .offset(skip) \
            .limit(limit) \
            .all()

    return conversations


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str):
    """获取对话详情"""
    with get_db() as db:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除对话"""
    with get_db() as db:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        db.delete(conversation)
        db.commit()

    return {"status": "deleted"}


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(conversation_id: str, request: SendMessageRequest):
    """发送消息"""
    with get_db() as db:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        message = Message(
            conversation_id=conversation_id,
            sender=request.sender,
            content=request.content,
            message_type="text"
        )

        db.add(message)
        db.commit()
        db.refresh(message)

        # 广播到 WebSocket
        ws_manager = get_ws_manager()
        await ws_manager.emit_user_message(
            conversation_id,
            "user",
            request.content
        )

    return message


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(conversation_id: str, limit: int = 100):
    """获取消息历史"""
    with get_db() as db:
        messages = db.query(Message) \
            .filter(Message.conversation_id == conversation_id) \
            .order_by(Message.created_at.desc()) \
            .limit(limit) \
            .all()

    return list(reversed(messages))


@router.get("/{conversation_id}/events")
async def get_events(conversation_id: str, limit: int = 100):
    """获取 Agent 事件"""
    with get_db() as db:
        events = db.query(AgentEvent) \
            .filter(AgentEvent.conversation_id == conversation_id) \
            .order_by(AgentEvent.created_at.desc()) \
            .limit(limit) \
            .all()

    return events