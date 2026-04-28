"""
Tester Agent - 测试 Agent
"""
from .base_agent import BaseAgent, AgentResponse


TESTER_PROMPT = """你是专业的测试工程师，负责运行测试并生成详细的测试报告。

## 输出格式
直接输出 JSON（双引号），不要有其他内容：
{
  "status": "PASS",
  "summary": {
    "total": 10,
    "passed": 10,
    "failed": 0,
    "errors": 0
  },
  "pass_rate": 100.0,
  "test_cases": [
    {"name": "test_add", "status": "PASS", "duration_ms": 5}
  ],
  "recommendations": ["建议列表"]
}

## 测试标准
- 通过率 >= 80% 视为通过
- 提供清晰的测试报告"""


class TesterAgent(BaseAgent):
    """测试 Agent"""

    def __init__(self, api_key: str, model: str = "glm-5", base_url: str = "https://milukey.cn"):
        super().__init__(
            name="tester",
            system_prompt=TESTER_PROMPT,
            api_key=api_key,
            model=model,
            base_url=base_url
        )

    def execute(self, task: str, context: dict = None) -> AgentResponse:
        """执行测试任务"""
        messages = self.format_prompt(task, context)
        return self._call_api_with_tools(messages, [])
