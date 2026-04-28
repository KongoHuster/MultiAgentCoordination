"""
Reviewer Agent - 代码审查 Agent
"""
from .base_agent import BaseAgent, AgentResponse


REVIEWER_PROMPT = """你是专业的代码审查员，负责检视代码质量并提出改进建议。

## 审查维度
1. **代码正确性** - 功能是否正确实现
2. **代码质量** - 是否遵循最佳实践
3. **安全性** - 是否存在安全漏洞
4. **性能** - 是否有性能问题
5. **可维护性** - 代码是否易于维护

## 问题等级
- **BLOCKER** - 必须修复，否则无法使用
- **MAJOR** - 建议修复，影响较大
- **MINOR** - 可选修复，影响较小
- **INFO** - 信息性建议

## 输出格式
请直接输出 JSON（双引号），不要有其他内容：
{
  "overall": "APPROVED|REQUEST_CHANGES|BLOCKED",
  "summary": "总体评价",
  "issues": [
    {
      "severity": "BLOCKER|MAJOR|MINOR|INFO",
      "location": "代码位置",
      "description": "问题描述",
      "suggestion": "修改建议"
    }
  ],
  "strengths": ["代码优点列表"],
  "score": 8
}

## 审查标准
- BLOCKER 问题必须为 0 才能 APPROVED
- 存在 BLOCKER 时必须 REQUEST_CHANGES
- 请客观、公正地进行审查"""


class ReviewerAgent(BaseAgent):
    """代码审查 Agent"""

    def __init__(self, api_key: str, model: str = "glm-5", base_url: str = "https://milukey.cn"):
        super().__init__(
            name="reviewer",
            system_prompt=REVIEWER_PROMPT,
            api_key=api_key,
            model=model,
            base_url=base_url
        )

    def execute(self, task: str, context: dict = None) -> AgentResponse:
        """执行审查任务"""
        messages = self.format_prompt(task, context)
        return self._call_api_with_tools(messages, [])
