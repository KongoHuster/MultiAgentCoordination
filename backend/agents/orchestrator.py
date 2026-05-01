"""
Orchestrator Agent - 任务编排器
"""

from typing import Optional, Callable, Awaitable
import json
import re

from .base_agent import BaseAgent, AgentResponse, agent


ORCHESTRATOR_SYSTEM_PROMPT = """你是一个任务编排专家，负责将复杂任务分解为可执行的子任务。

工作流程：
1. 理解用户需求
2. 将任务分解为逻辑清晰的子任务
3. 为每个子任务指定合适的执行 Agent

输出格式（必须是有效的 JSON）：
```json
[
  {
    "description": "子任务描述",
    "agent": "coder",
    "priority": "normal"
  }
]
```

Agent 类型：
- coder: 代码生成
- reviewer: 代码审查
- tester: 测试验证
- orchestrator: 需要进一步分解的复杂任务

优先级：low, normal, high"""


@agent("orchestrator")
class OrchestratorAgent(BaseAgent):
    """编排器 Agent"""

    def __init__(self, llm_config=None, max_retries: int = 3):
        super().__init__(
            name="orchestrator",
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            llm_config=llm_config
        )
        self.max_retries = max_retries

    def get_system_prompt(self) -> str:
        return ORCHESTRATOR_SYSTEM_PROMPT

    async def decompose_task(
        self,
        task: str,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> list[dict]:
        """分解任务"""
        prompt = f"请分解以下任务，输出 JSON 数组：\n\n{task}"

        response = await self.execute(
            prompt=prompt,
            stream_callback=stream_callback
        )

        # 解析 JSON
        return self._parse_subtasks(response.content)

    def _parse_subtasks(self, content: str) -> list[dict]:
        """解析子任务"""
        # 尝试提取 JSON
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            content = json_match.group(1)
        else:
            # 尝试直接解析
            json_match = re.search(r'\[[\s\S]*\]', content)

        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # 回退：返回空列表
        return []

    async def evaluate_result(
        self,
        test_result: dict,
        review_result: dict,
        retry_count: int
    ) -> dict:
        """评估结果并决定下一步"""
        pass_rate = test_result.get("pass_rate", 0)
        has_blocker = any(
            issue.get("type") == "BLOCKER"
            for issue in review_result.get("issues", [])
        )

        if retry_count >= self.max_retries:
            return {"decision": "COMPLETE", "reason": "max_retries_reached"}

        if pass_rate >= 80 and not has_blocker:
            return {"decision": "COMPLETE", "reason": "quality_satisfied"}

        if has_blocker:
            return {"decision": "RETRY", "reason": "blocker_found"}

        if pass_rate < 80:
            return {"decision": "RETRY", "reason": "low_pass_rate"}

        return {"decision": "COMPLETE", "reason": "unknown"}
