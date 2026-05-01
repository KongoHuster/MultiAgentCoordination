"""
任务管理器 - 管理任务状态
"""

from typing import Optional, Callable, Awaitable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """任务"""
    id: str
    conversation_id: str
    description: str
    agent_type: str
    status: TaskStatus = TaskStatus.PENDING
    parent_id: Optional[str] = None
    priority: str = "normal"
    retry_count: int = 0
    max_retries: int = 3
    result: Optional[dict] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    order_index: int = 0
    metadata: dict = field(default_factory=dict)


class TaskManager:
    """任务状态管理器"""

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._lock = None  # 延迟初始化
        self._subscribers: list[Callable[[str, Task, Optional[Task]], None]] = []

    def _get_lock(self):
        """获取锁（延迟初始化以避免循环导入）"""
        if self._lock is None:
            import threading
            self._lock = threading.RLock()
        return self._lock

    def create_task(
        self,
        conversation_id: str,
        description: str,
        agent_type: str,
        parent_id: Optional[str] = None,
        priority: str = "normal",
        order_index: int = 0
    ) -> Task:
        """创建新任务"""
        with self._get_lock():
            task_id = str(uuid.uuid4())[:8]
            task = Task(
                id=task_id,
                conversation_id=conversation_id,
                description=description,
                agent_type=agent_type,
                parent_id=parent_id,
                priority=priority,
                order_index=order_index
            )
            self._tasks[task_id] = task
            self._notify("created", task, None)
            return task

    def create_subtasks(
        self,
        conversation_id: str,
        subtasks: list[dict],
        parent_id: Optional[str] = None
    ) -> list[Task]:
        """批量创建子任务"""
        with self._get_lock():
            created_tasks = []
            for i, subtask in enumerate(subtasks):
                task = self.create_task(
                    conversation_id=conversation_id,
                    description=subtask.get("description", ""),
                    agent_type=subtask.get("agent", "coder"),
                    parent_id=parent_id,
                    priority=subtask.get("priority", "normal"),
                    order_index=i
                )
                created_tasks.append(task)
            return created_tasks

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        with self._get_lock():
            return self._tasks.get(task_id)

    def get_tasks(
        self,
        conversation_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        agent_type: Optional[str] = None
    ) -> list[Task]:
        """获取任务列表"""
        with self._get_lock():
            tasks = list(self._tasks.values())

            if conversation_id:
                tasks = [t for t in tasks if t.conversation_id == conversation_id]
            if status:
                tasks = [t for t in tasks if t.status == status]
            if agent_type:
                tasks = [t for t in tasks if t.agent_type == agent_type]

            return sorted(tasks, key=lambda t: t.order_index)

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        result: Optional[dict] = None,
        increment_retry: bool = False
    ) -> Optional[Task]:
        """更新任务"""
        with self._get_lock():
            task = self._tasks.get(task_id)
            if task is None:
                return None

            old_task = Task(**task.__dict__)  # 复制

            if status:
                task.status = status
            if result is not None:
                task.result = result
            if increment_retry:
                task.retry_count += 1

            task.updated_at = datetime.utcnow()

            self._notify("updated", task, old_task)
            return task

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        with self._get_lock():
            if task_id in self._tasks:
                task = self._tasks[task_id]
                del self._tasks[task_id]
                self._notify("deleted", task, None)
                return True
            return False

    def delete_conversation_tasks(self, conversation_id: str) -> int:
        """删除对话的所有任务"""
        with self._get_lock():
            task_ids = [t for t in self._tasks if self._tasks[t].conversation_id == conversation_id]
            for task_id in task_ids:
                del self._tasks[task_id]
            return len(task_ids)

    def get_pending_count(self, conversation_id: str) -> int:
        """获取待处理任务数"""
        with self._get_lock():
            return len([t for t in self._tasks.values()
                      if t.conversation_id == conversation_id and t.status == TaskStatus.PENDING])

    def get_running_count(self, conversation_id: str) -> int:
        """获取运行中任务数"""
        with self._get_lock():
            return len([t for t in self._tasks.values()
                      if t.conversation_id == conversation_id and t.status == TaskStatus.RUNNING])

    def subscribe(self, callback: Callable[[str, Task, Optional[Task]], None]):
        """订阅任务变化"""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[str, Task, Optional[Task]], None]):
        """取消订阅"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify(self, event_type: str, task: Task, old_task: Optional[Task]):
        """通知订阅者"""
        for callback in self._subscribers:
            try:
                callback(event_type, task, old_task)
            except Exception:
                pass


# 全局任务管理器
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """获取全局任务管理器"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


def reset_task_manager():
    """重置任务管理器（用于测试）"""
    global _task_manager
    _task_manager = TaskManager()