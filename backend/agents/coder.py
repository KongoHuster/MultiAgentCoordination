"""
Coder Agent - 代码生成
"""

from typing import Optional, Callable, Awaitable
import re

from .base_agent import BaseAgent, AgentResponse, agent


CODER_SYSTEM_PROMPT = """你是一个专业的代码生成专家，负责根据任务描述生成高质量的代码。

工作原则：
1. 生成清晰、可维护的代码
2. 遵循最佳实践和语言规范
3. 添加必要的注释
4. 考虑错误处理和边界情况

输出格式：
每个文件以 `# FILE: filename.ext` 开头，例如：
```
# FILE: calculator.py
class Calculator:
    ...
```

支持多文件输出，每个文件单独一个块。
只输出代码，不要解释。"""


@agent("coder")
class CoderAgent(BaseAgent):
    """代码生成 Agent"""

    def __init__(self, llm_config=None):
        super().__init__(
            name="coder",
            system_prompt=CODER_SYSTEM_PROMPT,
            llm_config=llm_config
        )

    def get_system_prompt(self) -> str:
        return CODER_SYSTEM_PROMPT

    async def generate_code(
        self,
        task_description: str,
        language: Optional[str] = None,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> dict[str, str]:
        """生成代码"""
        prompt = task_description
        if language:
            prompt = f"使用 {language} 语言生成代码：\n\n{task_description}"

        response = await self.execute(
            prompt=prompt,
            stream_callback=stream_callback
        )

        return self._parse_code_files(response.content)

    def _parse_code_files(self, content: str) -> dict[str, str]:
        """解析代码文件"""
        files = {}

        # 匹配文件块
        pattern = r'# FILE: ([^\s]+)\s*\n([\s\S]*?)(?=# FILE:|$)'

        for match in re.finditer(pattern, content):
            filename = match.group(1).strip()
            code = match.group(2).strip()

            if filename and code:
                files[filename] = code

        # 如果没有匹配到，尝试简单分割
        if not files:
            lines = content.split('\n')
            current_file = None
            current_content = []

            for line in lines:
                if line.startswith('# FILE:'):
                    if current_file:
                        files[current_file] = '\n'.join(current_content)
                    current_file = line.replace('# FILE:', '').strip()
                    current_content = []
                elif current_file:
                    current_content.append(line)

            if current_file and current_content:
                files[current_file] = '\n'.join(current_content)

        return files

    async def modify_code(
        self,
        existing_code: str,
        modification: str,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> str:
        """修改现有代码"""
        prompt = f"""现有代码：
```python
{existing_code}
```

修改要求：{modification}

输出格式：
```
# FILE: modified_filename.py
...修改后的代码...
```"""

        response = await self.execute(
            prompt=prompt,
            stream_callback=stream_callback
        )

        files = self._parse_code_files(response.content)
        if files:
            return list(files.values())[0]

        return existing_code
