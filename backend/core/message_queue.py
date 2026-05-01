"""
消息队列 - Agent 间通信
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Awaitable
from datetime import datetime
from enum import Enum
from collections import defaultdict
import threading
import asyncio
import json


class MessageType(Enum):
    """消息类型"""
    TASK_ASSIGNED = "task_assigned"
    TASK_RESULT = "task_result"
    REVIEW_REQUEST = "review_request"
    REVIEW_RESULT = "review_result"
    TEST_REQUEST = "test_request"
    TEST_REPORT = "test_report"
    COMMAND = "command"
    NOTIFICATION = "notification"
    USER_MESSAGE = "user_message"


@dataclass
class Message:
    """消息"""
    id: str
    from_agent: str
    to_agent: str
    content: Any
    msg_type: MessageType
    task_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class MessageQueue:
    """线程安全的消息队列"""

    def __init__(self):
        self._queues: dict[str, list[Message]] = defaultdict(list)
        self._lock = threading.RLock()
        self._subscribers: dict[str, list[Callable[[Message], None]]] = defaultdict(list)
        self._message_counter = 0

    def send_message(
        self,
        to_agent: str,
        from_agent: str,
        content: Any,
        msg_type: MessageType = MessageType.NOTIFICATION,
        task_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Message:
        """发送消息到指定 Agent"""
        with self._lock:
            self._message_counter += 1
            msg = Message(
                id=f"msg_{self._message_counter}",
                from_agent=from_agent,
                to_agent=to_agent,
                content=content,
                msg_type=msg_type,
                task_id=task_id,
                metadata=metadata or {}
            )
            self._queues[to_agent].append(msg)
            return msg

    def get_messages(self, agent_id: str, clear: bool = True) -> list[Message]:
        """获取 Agent 的消息"""
        with self._lock:
            messages = self._queues.get(agent_id, []).copy()
            if clear:
                self._queues[agent_id] = []
            return messages

    def peek_messages(self, agent_id: str) -> list[Message]:
        """查看消息但不删除"""
        with self._lock:
            return self._queues.get(agent_id, []).copy()

    def broadcast(
        self,
        from_agent: str,
        content: Any,
        msg_type: MessageType = MessageType.NOTIFICATION,
        target_agents: Optional[list[str]] = None
    ) -> list[Message]:
        """广播消息到所有或指定的 Agents"""
        with self._lock:
            if target_agents is None:
                target_agents = list(self._queues.keys())

            messages = []
            for agent_id in target_agents:
                if agent_id != from_agent:  # 不给自己发
                    msg = self.send_message(
                        to_agent=agent_id,
                        from_agent=from_agent,
                        content=content,
                        msg_type=msg_type
                    )
                    messages.append(msg)
            return messages

    def subscribe(self, agent_id: str, callback: Callable[[Message], None]):
        """订阅消息"""
        with self._lock:
            self._subscribers[agent_id].append(callback)

    def unsubscribe(self, agent_id: str, callback: Callable[[Message], None]):
        """取消订阅"""
        with self._lock:
            if agent_id in self._subscribers:
                self._subscribers[agent_id].remove(callback)

    def clear(self, agent_id: Optional[str] = None):
        """清空消息"""
        with self._lock:
            if agent_id:
                self._queues[agent_id] = []
            else:
                self._queues.clear()


# 全局消息队列
_message_queue: Optional[MessageQueue] = None


def get_message_queue() -> MessageQueue:
    """获取全局消息队列"""
    global _message_queue
    if _message_queue is None:
        _message_queue = MessageQueue()
    return _message_queue


def reset_message_queue():
    """重置消息队列（用于测试）"""
    global _message_queue
    _message_queue = MessageQueue()