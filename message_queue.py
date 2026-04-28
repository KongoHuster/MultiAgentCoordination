"""
Message Queue - Agent 间消息传递
"""
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class MessageType(Enum):
    TASK_ASSIGNED = "task_assigned"
    TASK_RESULT = "task_result"
    REVIEW_REQUEST = "review_request"
    REVIEW_RESULT = "review_result"
    TEST_REQUEST = "test_request"
    TEST_REPORT = "test_report"
    COMMAND = "command"
    NOTIFICATION = "notification"


@dataclass
class Message:
    """消息对象"""
    id: str = field(default="")
    type: MessageType = MessageType.NOTIFICATION
    from_agent: str = ""
    to_agent: str = ""
    content: Any = None
    task_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            import uuid
            self.id = str(uuid.uuid4())[:8]


class MessageQueue:
    """消息队列"""

    def __init__(self):
        self._queues: dict[str, list[Message]] = {}  # agent_id -> messages
        self._all_messages: list[Message] = []

    def send_message(self, to_agent: str, from_agent: str,
                    content: Any, msg_type: MessageType = MessageType.NOTIFICATION,
                    task_id: str = None, metadata: dict = None) -> Message:
        """发送消息"""
        message = Message(
            type=msg_type,
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            task_id=task_id,
            metadata=metadata or {}
        )

        # 添加到目标队列
        if to_agent not in self._queues:
            self._queues[to_agent] = []
        self._queues[to_agent].append(message)

        # 添加到全局历史
        self._all_messages.append(message)

        return message

    def get_messages(self, agent_id: str, clear: bool = True) -> list[Message]:
        """获取消息（默认取出后清除）"""
        messages = self._queues.get(agent_id, [])
        if clear:
            self._queues[agent_id] = []
        return messages

    def peek_messages(self, agent_id: str) -> list[Message]:
        """查看消息（不删除）"""
        return self._queues.get(agent_id, [])

    def broadcast(self, from_agent: str, content: Any,
                 msg_type: MessageType = MessageType.NOTIFICATION,
                 target_agents: list[str] = None) -> list[Message]:
        """广播消息"""
        if target_agents is None:
            target_agents = list(self._queues.keys())

        messages = []
        for agent in target_agents:
            msg = self.send_message(
                to_agent=agent,
                from_agent=from_agent,
                content=content,
                msg_type=msg_type
            )
            messages.append(msg)
        return messages

    def get_message_history(self, agent_id: str = None,
                           msg_type: MessageType = None) -> list[Message]:
        """获取消息历史"""
        history = self._all_messages

        if agent_id:
            history = [m for m in history if m.to_agent == agent_id or m.from_agent == agent_id]

        if msg_type:
            history = [m for m in history if m.type == msg_type]

        return history

    def count_pending(self, agent_id: str) -> int:
        """获取待处理消息数量"""
        return len(self._queues.get(agent_id, []))

    def clear_queue(self, agent_id: str) -> int:
        """清空指定队列"""
        count = len(self._queues.get(agent_id, []))
        self._queues[agent_id] = []
        return count

    def clear_all(self) -> None:
        """清空所有队列"""
        self._queues.clear()
        self._all_messages.clear()


# 便捷函数
def create_task_message(from_agent: str, to_agent: str,
                        task: dict, task_id: str) -> Message:
    """创建任务分配消息"""
    return Message(
        type=MessageType.TASK_ASSIGNED,
        from_agent=from_agent,
        to_agent=to_agent,
        content=task,
        task_id=task_id
    )


def create_result_message(from_agent: str, to_agent: str,
                         result: dict, task_id: str) -> Message:
    """创建结果消息"""
    return Message(
        type=MessageType.TASK_RESULT,
        from_agent=from_agent,
        to_agent=to_agent,
        content=result,
        task_id=task_id
    )


def create_test_report_message(from_agent: str, to_agent: str,
                               report: dict, task_id: str) -> Message:
    """创建测试报告消息"""
    return Message(
        type=MessageType.TEST_REPORT,
        from_agent=from_agent,
        to_agent=to_agent,
        content=report,
        task_id=task_id
    )
