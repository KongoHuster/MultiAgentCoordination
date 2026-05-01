"""
Tester Agent - 测试验证
"""

from typing import Optional, Callable, Awaitable, Dict
import json
import re

from .base_agent import BaseAgent, AgentResponse, agent


TESTER_SYSTEM_PROMPT = """你是一个测试专家，负责生成和执行测试用例来验证代码功能。

工作原则：
1. 全面覆盖各种输入情况
2. 包括正常和异常情况
3. 验证边界条件
4. 生成清晰的测试报告

输出格式（必须是有效的 JSON）：
```json
{
  "status": "PASS",
  "pass_rate": 0.85,
  "tests": [
    {
      "name": "test_add_positive_numbers",
      "status": "PASS",
      "description": "测试正数相加"
    },
    {
      "name": "test_add_negative_numbers",
      "status": "FAIL",
      "description": "测试负数相加",
      "error": "预期: -3, 实际: 3"
    }
  ],
  "summary": "10 个测试，8 个通过，2 个失败"
}
```

只输出 JSON，不要其他内容。"""


@agent("tester")
class TesterAgent(BaseAgent):
    """测试 Agent"""

    def __init__(self, llm_config=None):
        super().__init__(
            name="tester",
            system_prompt=TESTER_SYSTEM_PROMPT,
            llm_config=llm_config
        )

    def get_system_prompt(self) -> str:
        return TESTER_SYSTEM_PROMPT

    async def test_code(
        self,
        code: str,
        task_description: Optional[str] = None,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> dict:
        """测试代码"""
        prompt = "任务描述：" + (task_description or "无") + "\n\n"
        prompt += f"请测试以下代码：\n\n```python\n{code}\n```"

        response = await self.execute(
            prompt=prompt,
            stream_callback=stream_callback
        )

        return self._parse_test_result(response.content)

    async def generate_tests(
        self,
        code: str,
        language: str = "python",
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> dict[str, str]:
        """生成测试代码"""
        prompt = f"请为以下 {language} 代码生成测试用例：\n\n```{language}\n{code}\n```\n\n输出测试代码文件："

        response = await self.execute(
            prompt=prompt,
            stream_callback=stream_callback
        )

        files = {}

        # 解析测试文件
        pattern = r'# FILE: ([^\s]+)\s*\n([\s\S]*?)(?=# FILE:|$)'
        for match in re.finditer(pattern, response.content):
            filename = match.group(1).strip()
            test_code = match.group(2).strip()
            if filename and test_code:
                files[filename] = test_code

        return files

    def _parse_test_result(self, content: str) -> dict:
        """解析测试结果"""
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

        # 回退
        return {
            "status": "UNKNOWN",
            "pass_rate": 0.0,
            "tests": [],
            "summary": "无法解析测试结果"
        }

    def is_passed(self, test_result: dict, threshold: float = 0.8) -> bool:
        """检查是否通过测试"""
        return test_result.get("pass_rate", 0) >= threshold
