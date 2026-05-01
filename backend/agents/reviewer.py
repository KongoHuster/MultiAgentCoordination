"""
Reviewer Agent - 代码审查
"""

from typing import Optional, Callable, Awaitable, List
import json
import re

from .base_agent import BaseAgent, AgentResponse, agent


REVIEWER_SYSTEM_PROMPT = """你是一个严格的代码审查专家，负责审查代码质量并发现问题。

审查标准：
1. 正确性：代码逻辑是否正确
2. 安全性：是否有安全漏洞
3. 性能：是否有性能问题
4. 可维护性：代码是否清晰易读
5. 最佳实践：是否遵循语言和框架的最佳实践

问题严重级别：
- BLOCKER: 阻塞性问题，必须修复
- MAJOR: 重要问题，建议修复
- MINOR: 次要问题，可选修复

输出格式（必须是有效的 JSON）：
```json
{
  "score": 8.5,
  "summary": "代码整体质量良好，存在一些小问题",
  "issues": [
    {
      "type": "BLOCKER",
      "line": 42,
      "description": "未处理的异常可能导致程序崩溃",
      "suggestion": "添加 try-except 块"
    }
  ]
}
```

只输出 JSON，不要其他内容。"""


@agent("reviewer")
class ReviewerAgent(BaseAgent):
    """代码审查 Agent"""

    def __init__(self, llm_config=None):
        super().__init__(
            name="reviewer",
            system_prompt=REVIEWER_SYSTEM_PROMPT,
            llm_config=llm_config
        )

    def get_system_prompt(self) -> str:
        return REVIEWER_SYSTEM_PROMPT

    async def review_code(
        self,
        code: str,
        language: Optional[str] = None,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> dict:
        """审查代码"""
        prompt = f"请审查以下代码：\n\n```{language or 'code'}\n{code}\n```"

        response = await self.execute(
            prompt=prompt,
            stream_callback=stream_callback
        )

        return self._parse_review_result(response.content)

    def _parse_review_result(self, content: str) -> dict:
        """解析审查结果"""
        # 尝试提取 JSON
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            content = json_match.group(1)
        else:
            json_match = re.search(r'\{[\s\S]*\}', content)

        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # 回退：返回默认结果
        return {
            "score": 5.0,
            "summary": "无法解析审查结果",
            "issues": []
        }

    def has_blocker(self, review_result: dict) -> bool:
        """检查是否有阻塞性问题"""
        return any(
            issue.get("type") == "BLOCKER"
            for issue in review_result.get("issues", [])
        )

    def get_score(self, review_result: dict) -> float:
        """获取代码评分"""
        return review_result.get("score", 0.0)
