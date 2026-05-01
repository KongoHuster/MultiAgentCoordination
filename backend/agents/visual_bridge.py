"""
可视化桥接 - Agent 事件推送到前端
"""

from typing import Optional, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json

from websocket.manager import WSEvent, EventType, get_ws_manager


class AgentEventType(Enum):
    """Agent 事件类型"""
    THINKING = "thinking"
    ACTING = "acting"
    MESSAGE = "message"
    TASK_PROGRESS = "task_progress"
    ERROR = "error"


@dataclass
class AgentEvent:
    """Agent 事件"""
    conversation_id: str
    agent_name: str
    event_type: AgentEventType
    content: Optional[str] = None
    task_id: Optional[str] = None
    metadata: Optional[dict] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

    def to_ws_event(self) -> WSEvent:
        """转换为 WebSocket 事件"""
        return WSEvent(
            type=self.event_type.value,
            conversation_id=self.conversation_id,
            data={
                "content": self.content,
                "metadata": self.metadata
            },
            agent_name=self.agent_name,
            task_id=self.task_id
        )


class VisualBridge:
    """可视化桥接 - 将 Agent 执行状态实时推送给前端"""

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self._ws_manager = get_ws_manager()
        self._pending_events: list[AgentEvent] = []
        self._stream_callbacks: dict[str, Callable[[str], Awaitable[None]]] = {}

    async def emit_event(
        self,
        agent_name: str,
        event_type: AgentEventType,
        content: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ):
        """发射 Agent 事件"""
        event = AgentEvent(
            conversation_id=self.conversation_id,
            agent_name=agent_name,
            event_type=event_type,
            content=content,
            task_id=task_id,
            metadata=metadata
        )

        # 发送到 WebSocket
        ws_event = event.to_ws_event()
        await self._ws_manager.broadcast(ws_event, self.conversation_id)

        # 存储事件
        self._pending_events.append(event)

    async def on_agent_thinking(
        self,
        agent_name: str,
        thought: str,
        task_id: Optional[str] = None
    ):
        """Agent 思考中"""
        await self.emit_event(
            agent_name=agent_name,
            event_type=AgentEventType.THINKING,
            content=thought,
            task_id=task_id
        )

    async def on_agent_acting(
        self,
        agent_name: str,
        action: str,
        task_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ):
        """Agent 正在执行动作"""
        await self.emit_event(
            agent_name=agent_name,
            event_type=AgentEventType.ACTING,
            content=action,
            task_id=task_id,
            metadata=metadata
        )

    async def on_agent_message(
        self,
        agent_name: str,
        message: str,
        task_id: Optional[str] = None
    ):
        """Agent 输出消息"""
        await self.emit_event(
            agent_name=agent_name,
            event_type=AgentEventType.MESSAGE,
            content=message,
            task_id=task_id
        )

    async def on_task_progress(
        self,
        agent_name: str,
        task_id: str,
        progress: int,
        total: int,
        description: str
    ):
        """任务进度更新"""
        await self.emit_event(
            agent_name=agent_name,
            event_type=AgentEventType.TASK_PROGRESS,
            content=description,
            task_id=task_id,
            metadata={"progress": progress, "total": total}
        )

    async def on_error(
        self,
        agent_name: str,
        error: str,
        task_id: Optional[str] = None
    ):
        """错误事件"""
        await self.emit_event(
            agent_name=agent_name,
            event_type=AgentEventType.ERROR,
            content=error,
            task_id=task_id,
            metadata={"severity": "error"}
        )

    async def on_user_message(
        self,
        conversation_id: str,
        user_id: str,
        message: str
    ):
        """用户消息（用于日志显示）"""
        await self._ws_manager.emit_user_message(
            conversation_id=conversation_id,
            user_id=user_id,
            message=message
        )

    def register_stream_callback(
        self,
        agent_name: str,
        callback: Callable[[str], Awaitable[None]]
    ):
        """注册流式输出回调"""
        self._stream_callbacks[agent_name] = callback

    def unregister_stream_callback(self, agent_name: str):
        """取消注册流式输出回调"""
        if agent_name in self._stream_callbacks:
            del self._stream_callbacks[agent_name]

    async def on_stream_chunk(
        self,
        agent_name: str,
        chunk: str,
        task_id: Optional[str] = None
    ):
        """流式输出片段"""
        if agent_name in self._stream_callbacks:
            await self._stream_callbacks[agent_name](chunk)

    def get_events(
        self,
        event_type: Optional[AgentEventType] = None,
        agent_name: Optional[str] = None,
        limit: int = 100
    ) -> list[AgentEvent]:
        """获取事件历史"""
        events = self._pending_events

        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if agent_name:
            events = [e for e in events if e.agent_name == agent_name]

        return events[-limit:]

    def clear_events(self):
        """清空事件历史"""
        self._pending_events.clear()


# 便捷函数
def create_visual_bridge(conversation_id: str) -> VisualBridge:
    """创建可视化桥接实例"""
    return VisualBridge(conversation_id)