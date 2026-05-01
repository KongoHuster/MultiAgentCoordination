"""
Workflow Engine - 核心工作流引擎
"""

from typing import Optional, Callable, Awaitable, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio
import os

from agents.base_agent import BaseAgent
from agents.orchestrator import OrchestratorAgent
from agents.coder import CoderAgent
from agents.reviewer import ReviewerAgent
from agents.tester import TesterAgent
from agents.visual_bridge import VisualBridge, create_visual_bridge
from core.message_queue import get_message_queue, MessageType
from core.task_manager import get_task_manager, TaskStatus
from core.shared_memory import get_shared_memory
from websocket.manager import get_ws_manager, WSEvent, EventType
from git.manager import GitManager, create_git_manager
from llm.base import LLMConfig, LLMBackend


@dataclass
class WorkflowConfig:
    """工作流配置"""
    max_retries: int = 3
    pass_threshold: float = 0.8
    git_auto_commit: bool = True
    projects_dir: str = "generated_projects"


class WorkflowState:
    """工作流状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowEngine:
    """核心工作流引擎"""

    def __init__(
        self,
        conversation_id: str,
        config: Optional[WorkflowConfig] = None
    ):
        self.conversation_id = conversation_id
        self.config = config or WorkflowConfig()

        # 核心组件
        self._message_queue = get_message_queue()
        self._task_manager = get_task_manager()
        self._shared_memory = get_shared_memory()
        self._ws_manager = get_ws_manager()

        # 可视化桥接
        self._visual_bridge = create_visual_bridge(conversation_id)

        # Git 管理
        self._git_manager: Optional[GitManager] = None

        # Agents
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_configs: Dict[str, LLMConfig] = {}

        # 状态
        self._state = WorkflowState.IDLE
        self._is_paused = False
        self._is_cancelled = False
        self._user_messages: list[str] = []

        # 当前任务
        self._current_task = None
        self._retry_count = 0

    def set_agent_config(self, agent_type: str, config: LLMConfig):
        """设置 Agent 的 LLM 配置"""
        self._agent_configs[agent_type] = config

    def _get_agent(self, agent_type: str) -> BaseAgent:
        """获取或创建 Agent"""
        if agent_type not in self._agents:
            config = self._agent_configs.get(agent_type)
            if agent_type == "orchestrator":
                self._agents[agent_type] = OrchestratorAgent(llm_config=config)
            elif agent_type == "coder":
                self._agents[agent_type] = CoderAgent(llm_config=config)
            elif agent_type == "reviewer":
                self._agents[agent_type] = ReviewerAgent(llm_config=config)
            elif agent_type == "tester":
                self._agents[agent_type] = TesterAgent(llm_config=config)
            else:
                raise ValueError(f"Unknown agent type: {agent_type}")

        return self._agents[agent_type]

    async def _stream_callback(self, agent_name: str, task_id: str = None):
        """创建流式回调"""
        async def callback(chunk: str):
            await self._visual_bridge.on_stream_chunk(agent_name, chunk, task_id)
        return callback

    async def run(self, task: str) -> dict:
        """运行工作流"""
        if self._state == WorkflowState.RUNNING:
            raise RuntimeError("Workflow already running")

        self._state = WorkflowState.RUNNING
        self._is_cancelled = False

        try:
            # 初始化 Git 仓库
            self._init_git()

            # 发射工作流开始事件
            await self._ws_manager.emit_workflow_start(self.conversation_id, task)

            # 1. 任务分解
            await self._visual_bridge.on_agent_thinking("orchestrator", "开始分解任务...")
            subtasks = await self._decompose_task(task)

            if not subtasks:
                raise ValueError("Failed to decompose task")

            await self._ws_manager.emit_task_decompose(self.conversation_id, subtasks)

            # 2. 执行子任务
            for i, subtask in enumerate(subtasks):
                if self._is_cancelled:
                    break

                await self._execute_subtask(subtask, i + 1, len(subtasks))

            # 3. 完成
            await self._complete()

            return {
                "status": "success",
                "conversation_id": self.conversation_id,
                "project_path": self._git_manager.repo_path if self._git_manager else None
            }

        except Exception as e:
            self._state = WorkflowState.FAILED
            await self._ws_manager.emit_workflow_complete(self.conversation_id, {
                "status": "error",
                "error": str(e)
            })
            raise

    async def _decompose_task(self, task: str) -> list[dict]:
        """分解任务"""
        orchestrator = self._get_agent("orchestrator")

        await self._visual_bridge.on_agent_message(
            "orchestrator",
            f"正在分解任务: {task[:50]}...",
            None
        )

        subtasks = await orchestrator.decompose_task(
            task,
            stream_callback=await self._stream_callback("orchestrator")
        )

        await self._visual_bridge.on_agent_message(
            "orchestrator",
            f"任务已分解为 {len(subtasks)} 个子任务",
            None
        )

        return subtasks

    async def _execute_subtask(self, subtask: dict, index: int, total: int):
        """执行子任务"""
        task_id = subtask.get("description", "")[:20].replace(" ", "_")
        agent_type = subtask.get("agent", "coder")
        description = subtask.get("description", "")

        self._current_task = task_id
        self._retry_count = 0

        await self._ws_manager.emit_subtask_start(
            self.conversation_id,
            task_id,
            description,
            agent_type
        )

        await self._task_manager.update_task(task_id, TaskStatus.RUNNING)

        # 循环执行（允许重试）
        while self._retry_count < self.config.max_retries:
            if self._is_cancelled:
                break

            # 检查暂停
            while self._is_paused and not self._is_cancelled:
                await asyncio.sleep(0.1)

            try:
                # 1. 编码阶段
                code_result = await self._coding_phase(agent_type, description)

                # 2. 审查阶段
                review_result = await self._review_phase(code_result)

                # 3. 测试阶段
                test_result = await self._test_phase(code_result, description)

                # 4. 决策阶段
                decision = await self._decision_phase(
                    description,
                    code_result,
                    review_result,
                    test_result
                )

                if decision == "COMPLETE":
                    # 保存代码到 Git
                    await self._save_code(code_result, description)

                    await self._ws_manager.emit_subtask_complete(
                        self.conversation_id,
                        task_id,
                        {"status": "success"}
                    )
                    await self._task_manager.update_task(
                        task_id,
                        TaskStatus.COMPLETED,
                        result={"code": code_result, "review": review_result, "test": test_result}
                    )
                    return

                elif decision == "RETRY":
                    self._retry_count += 1
                    await self._visual_bridge.on_agent_message(
                        agent_type,
                        f"需要重试 ({self._retry_count}/{self.config.max_retries})",
                        task_id
                    )
                    continue

            except Exception as e:
                self._retry_count += 1
                await self._visual_bridge.on_error(agent_type, str(e), task_id)

        # 超过最大重试次数
        await self._task_manager.update_task(task_id, TaskStatus.FAILED)
        await self._ws_manager.emit_subtask_complete(
            self.conversation_id,
            task_id,
            {"status": "failed", "reason": "max_retries"}
        )

    async def _coding_phase(self, agent_type: str, description: str) -> dict:
        """编码阶段"""
        await self._visual_bridge.on_agent_acting(
            agent_type,
            "正在生成代码...",
            self._current_task
        )

        coder = self._get_agent("coder")
        code_files = await coder.generate_code(
            description,
            stream_callback=await self._stream_callback("coder", self._current_task)
        )

        await self._visual_bridge.on_agent_message(
            "coder",
            f"已生成 {len(code_files)} 个文件",
            self._current_task
        )

        return code_files

    async def _review_phase(self, code: dict) -> dict:
        """审查阶段"""
        await self._visual_bridge.on_agent_acting(
            "reviewer",
            "正在审查代码...",
            self._current_task
        )

        reviewer = self._get_agent("reviewer")
        review_result = {"issues": [], "score": 10}

        # 审查每个文件
        for filename, file_content in code.items():
            result = await reviewer.review_code(
                file_content,
                stream_callback=await self._stream_callback("reviewer", self._current_task)
            )
            result["file"] = filename
            review_result["issues"].append(result)

        avg_score = sum(r.get("score", 0) for r in review_result["issues"]) / max(len(review_result["issues"]), 1)
        review_result["score"] = avg_score

        has_blocker = reviewer.has_blocker(review_result)

        if has_blocker:
            await self._visual_bridge.on_agent_message(
                "reviewer",
                "发现阻塞性问题，需要重试",
                self._current_task
            )
        else:
            await self._visual_bridge.on_agent_message(
                "reviewer",
                f"审查通过 (评分: {avg_score:.1f}/10)",
                self._current_task
            )

        return review_result

    async def _test_phase(self, code: dict, description: str) -> dict:
        """测试阶段"""
        await self._visual_bridge.on_agent_acting(
            "tester",
            "正在运行测试...",
            self._current_task
        )

        tester = self._get_agent("tester")

        # 合并代码用于测试
        full_code = "\n\n".join(code.values())
        test_result = await tester.test_code(
            full_code,
            description,
            stream_callback=await self._stream_callback("tester", self._current_task)
        )

        pass_rate = test_result.get("pass_rate", 0)

        if test_result.get("status") == "PASS" or pass_rate >= self.config.pass_threshold:
            await self._visual_bridge.on_agent_message(
                "tester",
                f"测试通过 ({pass_rate:.0%})",
                self._current_task
            )
        else:
            await self._visual_bridge.on_agent_message(
                "tester",
                f"测试未达标 ({pass_rate:.0%} < {self.config.pass_threshold:.0%})",
                self._current_task
            )

        return test_result

    async def _decision_phase(
        self,
        description: str,
        code: dict,
        review_result: dict,
        test_result: dict
    ) -> str:
        """决策阶段"""
        orchestrator = self._get_agent("orchestrator")

        decision = await orchestrator.evaluate_result(
            test_result,
            review_result,
            self._retry_count
        )

        return decision.get("decision", "COMPLETE")

    async def _save_code(self, code: dict, commit_message: str):
        """保存代码到 Git"""
        if not self._git_manager:
            return

        try:
            # 添加文件
            for filename, content in code.items():
                self._git_manager.add_file(filename, content)

            # 提交
            if self.config.git_auto_commit:
                commit_hash = self._git_manager.commit(commit_message)
                await self._ws_manager.emit_git_commit(
                    self.conversation_id,
                    commit_hash[:8],
                    commit_message
                )

        except Exception as e:
            await self._visual_bridge.on_error("git", str(e))

    async def _complete(self):
        """工作流完成"""
        self._state = WorkflowState.COMPLETED

        # 提交所有待定更改
        if self._git_manager and self.config.git_auto_commit:
            try:
                commit_hash = self._git_manager.commit("任务完成")
                await self._ws_manager.emit_git_commit(
                    self.conversation_id,
                    commit_hash[:8],
                    "任务完成"
                )
            except Exception:
                pass

        await self._ws_manager.emit_workflow_complete(self.conversation_id, {
            "status": "success",
            "conversation_id": self.conversation_id
        })

    def _init_git(self):
        """初始化 Git 仓库"""
        if not os.path.exists(self.config.projects_dir):
            os.makedirs(self.config.projects_dir)

        self._git_manager = create_git_manager(
            self.conversation_id,
            self.config.projects_dir
        )

    def pause(self):
        """暂停工作流"""
        self._is_paused = True
        self._state = WorkflowState.PAUSED

    def resume(self):
        """恢复工作流"""
        self._is_paused = False
        self._state = WorkflowState.RUNNING

    def stop(self):
        """停止工作流"""
        self._is_cancelled = True
        self._is_paused = False
        self._state = WorkflowState.IDLE

    def add_user_message(self, message: str):
        """添加用户消息"""
        self._user_messages.append(message)

    def get_state(self) -> str:
        """获取状态"""
        return self._state

    def get_user_messages(self) -> list[str]:
        """获取用户消息"""
        return self._user_messages.copy()


# 全局工作流管理器
_workflows: Dict[str, WorkflowEngine] = {}


def get_workflow(conversation_id: str) -> Optional[WorkflowEngine]:
    """获取工作流实例"""
    return _workflows.get(conversation_id)


def create_workflow(conversation_id: str, config: Optional[WorkflowConfig] = None) -> WorkflowEngine:
    """创建工作流实例"""
    workflow = WorkflowEngine(conversation_id, config)
    _workflows[conversation_id] = workflow
    return workflow


def remove_workflow(conversation_id: str):
    """移除工作流实例"""
    if conversation_id in _workflows:
        del _workflows[conversation_id]