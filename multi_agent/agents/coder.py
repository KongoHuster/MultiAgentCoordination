"""
Coder Agent - 编码 Agent
"""
from .base_agent import BaseAgent, AgentResponse


CODER_PROMPT = """你是专业的编程助手，负责根据任务描述编写高质量代码。

## 你的职责
1. 仔细理解任务需求
2. 编写清晰、可维护的代码
3. 包含必要的注释和文档
4. 考虑边界情况和错误处理

## 代码规范
- 遵循 PEP 8 Python 代码风格
- 使用有意义的变量和函数名
- 添加必要的类型注解
- 编写清晰的 docstring
- 处理异常情况

## 输出格式
请提供：
1. 完整的代码实现
2. 简要说明代码结构
3. 使用示例（如果适用）

## 注意事项
- 代码应该是可直接运行的
- 包含单元测试（如果合理）
- 不要留下 TODO 或未完成的代码"""


class CoderAgent(BaseAgent):
    """编码 Agent"""

    def __init__(self, api_key: str, model: str = "glm-5", base_url: str = "https://milukey.cn"):
        super().__init__(
            name="coder",
            system_prompt=CODER_PROMPT,
            api_key=api_key,
            model=model,
            base_url=base_url
        )

    def execute(self, task: str, context: dict = None) -> AgentResponse:
        """执行编码任务"""
        messages = self.format_prompt(task, context)
        return self._call_api_with_tools(messages, [])

    def write_code(self, task_description: str, requirements: list = None) -> str:
        """编写代码"""
        prompt = task_description
        if requirements:
            prompt += "\n\n要求：\n" + "\n".join(f"- {r}" for r in requirements)

        messages = [{"role": "user", "content": prompt}]
        response = self._call_api(messages)
        return response["text"]
