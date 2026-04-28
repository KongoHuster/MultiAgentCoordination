"""
Orchestrator Agent - 主控 Agent（任务分解与协调）
"""
from .base_agent import BaseAgent, AgentResponse


# 主控 Agent 系统提示词
ORCHESTRATOR_PROMPT = """你是任务编排大师，负责协调多个专业 Agent 完成复杂任务。

## 你的职责
1. 分析用户请求，将复杂任务分解为可执行的小任务
2. 为每个子任务分配最合适的 Agent
3. 评估执行结果，做出决策
4. 整合最终结果

## 决策规则
基于测试报告和检视结果，你需要做出以下决策之一：

1. **COMPLETE** - 任务完成
   - 测试通过率 >= 80%
   - 无严重（BLOCKER）级别的问题
   - 可以提交代码

2. **RETRY** - 需要重做
   - 测试通过率 < 80%
   - 存在 BLOCKER 问题
   - 存在明显错误
   - 最多重试 3 次

3. **NEXT** - 进入下一个任务
   - 当前任务已完成
   - 可以继续处理下一个子任务

## 输出格式
请以 JSON 格式输出决策：
```json
{
  "decision": "COMPLETE|RETRY|NEXT",
  "reason": "决策原因说明",
  "next_action": "具体下一步行动",
  "feedback_for_agent": "给执行 Agent 的反馈（如果需要重做）"
}
```

## 注意事项
- 决策要基于事实和数据，不是主观臆断
- 如果需要重做，要给出具体的改进建议
- 保持任务的上下文，确保 Agent 知道需要修改什么
"""


# 工具定义
ORCHESTRATOR_TOOLS = [
    {
        "name": "delegate_task",
        "description": "将任务分配给专业 Agent",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_type": {
                    "type": "string",
                    "enum": ["coder", "reviewer", "tester"],
                    "description": "目标 Agent 类型"
                },
                "task_description": {
                    "type": "string",
                    "description": "任务描述"
                },
                "task_id": {
                    "type": "string",
                    "description": "任务 ID"
                },
                "priority": {
                    "type": "string",
                    "enum": ["high", "normal", "low"],
                    "default": "normal"
                }
            },
            "required": ["agent_type", "task_description", "task_id"]
        }
    },
    {
        "name": "make_decision",
        "description": "根据执行结果做出决策",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "test_report": {
                    "type": "object",
                    "description": "测试报告"
                },
                "review_result": {
                    "type": "object",
                    "description": "检视结果"
                },
                "retry_count": {"type": "integer"}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "summarize_results",
        "description": "整合所有子任务结果生成最终报告",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"}
            },
            "required": ["task_id"]
        }
    }
]


class OrchestratorAgent(BaseAgent):
    """主控 Agent"""

    def __init__(self, api_key: str, model: str = "glm-5", base_url: str = "https://milukey.cn"):
        super().__init__(
            name="orchestrator",
            system_prompt=ORCHESTRATOR_PROMPT,
            api_key=api_key,
            model=model,
            base_url=base_url
        )

    def execute(self, task: str, context: dict = None) -> AgentResponse:
        """执行任务分解"""
        messages = self.format_prompt(task, context)
        return self._call_api_with_tools(messages, ORCHESTRATOR_TOOLS)

    def decompose_task(self, user_request: str) -> dict:
        """分解复杂任务"""
        prompt = f"""分析以下用户请求，将其分解为独立的子任务。

用户请求：
{user_request}

请按以下格式输出子任务列表：
```json
[
  {{
    "description": "任务描述",
    "agent": "coder|reviewer|tester",
    "priority": "high|normal|low",
    "dependencies": ["task_id1"]  // 依赖的其他任务，可为空
  }}
]
```

规则：
1. 每个子任务应该是独立的、可验证的
2. 明确指定需要的 Agent 类型
3. 标记任务优先级
4. 如果有依赖关系，注明依赖的任务"""
        messages = [{"role": "user", "content": prompt}]
        response = self._call_api(messages)
        return {"text": response["text"], "usage": response["usage"]}

    def evaluate_result(self, task_id: str, test_report: dict,
                       review_result: dict = None, retry_count: int = 0) -> dict:
        """评估执行结果并决策"""
        prompt = f"""评估以下任务执行结果并做出决策。

任务 ID: {task_id}
重试次数: {retry_count}/3

测试报告:
```json
{test_report}
```

检视结果:
```json
{review_result or "无"}
```

请根据以下规则做出决策：

1. **COMPLETE** - 测试通过率 >= 80% 且无 BLOCKER → 任务完成，提交代码
2. **RETRY** - 测试通过率 < 80% 或存在 BLOCKER → 需要重做，最多3次
3. **NEXT** - 当前任务完成 → 进入下一个任务

输出 JSON 格式决策：
```json
{{
  "decision": "COMPLETE|RETRY|NEXT",
  "reason": "决策原因",
  "pass_rate": 数字（测试通过率）,
  "issues": ["问题列表，如果有"],
  "feedback": "给 Agent 的改进建议（如果需要重做）"
}}
```"""
        messages = [{"role": "user", "content": prompt}]
        response = self._call_api(messages)

        # 解析 JSON 决策
        import json
        import re

        text = response["text"]
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                decision = json.loads(json_match.group())
                return decision
            except:
                pass

        return {
            "decision": "RETRY",
            "reason": "无法解析决策结果",
            "error": text
        }
