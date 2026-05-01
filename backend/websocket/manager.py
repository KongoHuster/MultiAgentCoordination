"""
WebSocket 管理器 - 实时通信
"""

from typing import Optional, Callable, Awaitable, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from collections import defaultdict
import asyncio
import json
import threading


class EventType(Enum):
    """事件类型"""
    # 工作流事件
    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETE = "workflow_complete"
    WORKFLOW_ERROR = "workflow_error"

    # 任务事件
    TASK_DECOMPOSE = "task_decompose"
    SUBTASK_START = "subtask_start"
    SUBTASK_COMPLETE = "subtask_complete"
    SUBTASK_FAILED = "subtask_failed"

    # Agent 事件
    AGENT_THINKING = "agent_thinking"
    AGENT_ACTING = "agent_acting"
    AGENT_MESSAGE = "agent_message"

    # 用户交互
    USER_MESSAGE = "user_message"
    USER_INTERVENTION = "user_intervention"

    # Git 事件
    GIT_COMMIT = "git_commit"
    GIT_STATUS = "git_status"

    # 控制事件
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"

    # 心跳
    PING = "ping"
    PONG = "pong"


@dataclass
class WSEvent:
    """WebSocket 事件"""
    type: str
    conversation_id: str
    data: Any
    timestamp: str = None
    agent_name: Optional[str] = None
    task_id: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "conversation_id": self.conversation_id,
            "data": self.data,
            "timestamp": self.timestamp,
            "agent_name": self.agent_name,
            "task_id": self.task_id
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class WSConnection:
    """WebSocket 连接"""

    def __init__(
        self,
        websocket,
        conversation_id: str,
        user_id: Optional[str] = None
    ):
        self.websocket = websocket
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.connected_at = datetime.utcnow()


class WSManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self._connections: dict[str, list[WSConnection]] = defaultdict(list)
        self._lock = threading.RLock()
        self._subscribers: list[Callable[[WSEvent], Awaitable[None]]] = []
        self._ping_task: Optional[asyncio.Task] = None

    def add_connection(self, connection: WSConnection):
        """添加连接"""
        with self._lock:
            self._connections[connection.conversation_id].append(connection)

    def remove_connection(self, websocket, conversation_id: str):
        """移除连接"""
        with self._lock:
            if conversation_id in self._connections:
                self._connections[conversation_id] = [
                    c for c in self._connections[conversation_id]
                    if c.websocket != websocket
                ]
                if not self._connections[conversation_id]:
                    del self._connections[conversation_id]

    async def broadcast(
        self,
        event: WSEvent,
        conversation_id: Optional[str] = None
    ):
        """广播消息到指定对话的所有连接"""
        with self._lock:
            connections = self._connections.get(conversation_id or event.conversation_id, [])

        if not connections:
            return

        disconnected = []

        for connection in connections:
            try:
                await connection.websocket.send_text(event.to_json())
            except Exception:
                disconnected.append(connection)

        # 清理断开的连接
        for conn in disconnected:
            self.remove_connection(conn.websocket, conn.conversation_id)

    async def send_to_user(
        self,
        event: WSEvent,
        conversation_id: str,
        user_id: str
    ):
        """发送给指定用户"""
        with self._lock:
            connections = [
                c for c in self._connections.get(conversation_id, [])
                if c.user_id == user_id
            ]

        for connection in connections:
            try:
                await connection.websocket.send_text(event.to_json())
            except Exception:
                pass

    def subscribe(self, callback: Callable[[WSEvent], Awaitable[None]]):
        """订阅全局事件"""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[WSEvent], Awaitable[None]]):
        """取消订阅"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def notify_subscribers(self, event: WSEvent):
        """通知全局订阅者"""
        for callback in self._subscribers:
            try:
                await callback(event)
            except Exception:
                pass

    def get_connection_count(self, conversation_id: Optional[str] = None) -> int:
        """获取连接数"""
        with self._lock:
            if conversation_id:
                return len(self._connections.get(conversation_id, []))
            return sum(len(c) for c in self._connections.values())

    def get_conversations(self) -> list[str]:
        """获取所有活跃对话"""
        with self._lock:
            return list(self._connections.keys())

    # 便捷方法
    async def emit_workflow_start(self, conversation_id: str, task: str):
        """发射工作流开始事件"""
        event = WSEvent(
            type=EventType.WORKFLOW_START.value,
            conversation_id=conversation_id,
            data={"task": task}
        )
        await self.broadcast(event)

    async def emit_workflow_complete(self, conversation_id: str, result: dict):
        """发射工作流完成事件"""
        event = WSEvent(
            type=EventType.WORKFLOW_COMPLETE.value,
            conversation_id=conversation_id,
            data=result
        )
        await self.broadcast(event)

    async def emit_task_decompose(
        self,
        conversation_id: str,
        subtasks: list[dict]
    ):
        """发射任务分解事件"""
        event = WSEvent(
            type=EventType.TASK_DECOMPOSE.value,
            conversation_id=conversation_id,
            data={"subtasks": subtasks}
        )
        await self.broadcast(event)

    async def emit_subtask_start(
        self,
        conversation_id: str,
        task_id: str,
        description: str,
        agent_name: str
    ):
        """发射子任务开始事件"""
        event = WSEvent(
            type=EventType.SUBTASK_START.value,
            conversation_id=conversation_id,
            data={"task_id": task_id, "description": description},
            agent_name=agent_name,
            task_id=task_id
        )
        await self.broadcast(event)

    async def emit_subtask_complete(
        self,
        conversation_id: str,
        task_id: str,
        result: dict
    ):
        """发射子任务完成事件"""
        event = WSEvent(
            type=EventType.SUBTASK_COMPLETE.value,
            conversation_id=conversation_id,
            data={"task_id": task_id, "result": result},
            task_id=task_id
        )
        await self.broadcast(event)

    async def emit_agent_thinking(
        self,
        conversation_id: str,
        agent_name: str,
        thought: str
    ):
        """发射 Agent 思考事件"""
        event = WSEvent(
            type=EventType.AGENT_THINKING.value,
            conversation_id=conversation_id,
            data={"thought": thought},
            agent_name=agent_name
        )
        await self.broadcast(event)

    async def emit_agent_message(
        self,
        conversation_id: str,
        agent_name: str,
        message: str,
        task_id: Optional[str] = None
    ):
        """发射 Agent 消息事件"""
        event = WSEvent(
            type=EventType.AGENT_MESSAGE.value,
            conversation_id=conversation_id,
            data={"message": message},
            agent_name=agent_name,
            task_id=task_id
        )
        await self.broadcast(event)

    async def emit_user_message(
        self,
        conversation_id: str,
        user_id: str,
        message: str
    ):
        """发射用户消息事件"""
        event = WSEvent(
            type=EventType.USER_MESSAGE.value,
            conversation_id=conversation_id,
            data={"user_id": user_id, "message": message}
        )
        await self.broadcast(event)

    async def emit_git_commit(
        self,
        conversation_id: str,
        commit_hash: str,
        message: str
    ):
        """发射 Git 提交事件"""
        event = WSEvent(
            type=EventType.GIT_COMMIT.value,
            conversation_id=conversation_id,
            data={"commit_hash": commit_hash, "message": message}
        )
        await self.broadcast(event)


# 全局 WebSocket 管理器
_ws_manager: Optional[WSManager] = None


def get_ws_manager() -> WSManager:
    """获取全局 WebSocket 管理器"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WSManager()
    return _ws_manager