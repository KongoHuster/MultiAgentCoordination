"""
Task Manager - 任务状态管理
"""
import uuid
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_REVIEW = "waiting_review"
    WAITING_TEST = "waiting_test"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class Task:
    """任务对象"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: TaskStatus = TaskStatus.PENDING
    description: str = ""
    assigned_agent: Optional[str] = None
    result: Optional[dict] = None
    parent_id: Optional[str] = None
    subtask_ids: list[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    error: Optional[str] = None
    commit_sha: Optional[str] = None

    def can_retry(self) -> bool:
        """检查是否可以重试"""
        return self.retry_count < self.max_retries


class TaskManager:
    """任务管理器"""

    def __init__(self):
        self.tasks: dict[str, Task] = {}

    def create_task(self, description: str, parent_id: str = None,
                    assigned_agent: str = None) -> Task:
        """创建新任务"""
        task = Task(
            description=description,
            parent_id=parent_id,
            assigned_agent=assigned_agent
        )
        self.tasks[task.id] = task
        return task

    def create_subtasks(self, parent_id: str, subtask_descriptions: list[dict]) -> list[Task]:
        """批量创建子任务"""
        parent = self.tasks.get(parent_id)
        if not parent:
            raise ValueError(f"Parent task {parent_id} not found")

        subtasks = []
        for desc_info in subtask_descriptions:
            if isinstance(desc_info, dict):
                desc = desc_info.get("description", "")
                agent = desc_info.get("agent")
            else:
                desc = desc_info
                agent = None

            subtask = self.create_task(desc, parent_id=parent_id, assigned_agent=agent)
            subtasks.append(subtask)

        parent.subtask_ids = [t.id for t in subtasks]
        parent.status = TaskStatus.IN_PROGRESS
        return subtasks

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)

    def get_pending_tasks(self, agent_id: str = None) -> list[Task]:
        """获取待处理任务"""
        return [
            t for t in self.tasks.values()
            if t.status == TaskStatus.PENDING
            and (agent_id is None or t.assigned_agent == agent_id)
        ]

    def get_next_task(self, agent_id: str = None) -> Optional[Task]:
        """获取下一个待处理任务"""
        pending = self.get_pending_tasks(agent_id)
        return pending[0] if pending else None

    def update_status(self, task_id: str, status: TaskStatus,
                      result: dict = None, error: str = None) -> bool:
        """更新任务状态"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        task.status = status
        task.updated_at = datetime.utcnow().isoformat()

        if result:
            task.result = result
        if error:
            task.error = error
        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.utcnow().isoformat()

        return True

    def increment_retry(self, task_id: str) -> int:
        """增加重试次数"""
        task = self.tasks.get(task_id)
        if task:
            task.retry_count += 1
            task.updated_at = datetime.utcnow().isoformat()
            return task.retry_count
        return 0

    def set_commit(self, task_id: str, commit_sha: str) -> bool:
        """设置 Git 提交记录"""
        task = self.tasks.get(task_id)
        if task:
            task.commit_sha = commit_sha
            return True
        return False

    def get_parent_task(self, task_id: str) -> Optional[Task]:
        """获取父任务"""
        task = self.tasks.get(task_id)
        if task and task.parent_id:
            return self.tasks.get(task.parent_id)
        return None

    def get_subtasks(self, parent_id: str) -> list[Task]:
        """获取子任务列表"""
        parent = self.tasks.get(parent_id)
        if parent:
            return [self.tasks[sid] for sid in parent.subtask_ids if sid in self.tasks]
        return []

    def are_all_subtasks_completed(self, parent_id: str) -> bool:
        """检查所有子任务是否完成"""
        subtasks = self.get_subtasks(parent_id)
        return all(t.status == TaskStatus.COMPLETED for t in subtasks)

    def get_task_tree(self, root_id: str) -> dict:
        """获取任务树结构"""
        def build_tree(task_id: str) -> dict:
            task = self.tasks.get(task_id)
            if not task:
                return {}
            return {
                "id": task.id,
                "description": task.description,
                "status": task.status.value,
                "agent": task.assigned_agent,
                "result": task.result is not None,
                "children": [build_tree(cid) for cid in task.subtask_ids]
            }
        return build_tree(root_id)

    def get_summary(self) -> dict:
        """获取任务统计摘要"""
        status_counts = {}
        for task in self.tasks.values():
            status_counts[task.status.value] = status_counts.get(task.status.value, 0) + 1
        return {
            "total": len(self.tasks),
            "by_status": status_counts
        }
