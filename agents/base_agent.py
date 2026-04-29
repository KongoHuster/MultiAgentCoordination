"""
Base Agent - 所有 Agent 的基类
支持流式输出和 Ollama
"""
import anthropic
import httpx
from abc import ABC, abstractmethod
from typing import Any, Optional, Callable
from dataclasses import dataclass


@dataclass
class AgentResponse:
    """Agent 响应"""
    success: bool
    content: Any
    error: Optional[str] = None
    usage: Optional[dict] = None


class BaseAgent(ABC):
    """Agent 基类"""

    def __init__(self, name: str, system_prompt: str,
                 api_key: str, model: str = "glm-5",
                 base_url: str = "https://milukey.cn",
                 max_tokens: int = 4096):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.max_tokens = max_tokens
        self.max_retries = 3

        # 检测是否使用 Ollama
        self.use_ollama = "localhost" in base_url or "ollama" in base_url.lower()

        if self.use_ollama:
            # Ollama 使用 httpx
            self.client = httpx.Client(base_url=base_url, timeout=300)
        else:
            # Anthropic API
            self.client = anthropic.Anthropic(
                api_key=api_key,
                base_url=base_url
            )

    @abstractmethod
    def execute(self, task: str, context: dict = None) -> AgentResponse:
        """执行任务"""
        pass

    def _call_api(self, messages: list[dict],
                  system: str = None,
                  tools: list = None,
                  stream_callback: Callable[[str], None] = None) -> dict:
        """调用 API - 支持 Ollama 和 Anthropic"""

        if self.use_ollama:
            return self._call_ollama(messages, system, stream_callback)
        else:
            return self._call_anthropic(messages, system, tools, stream_callback)

    def _call_ollama(self, messages: list[dict],
                     system: str = None,
                     stream_callback: Callable[[str], None] = None) -> dict:
        """调用 Ollama API"""
        import json

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True
        }
        if system:
            # Ollama 使用 system 字段
            payload["system"] = system

        try:
            result_text = ""
            with self.client.stream("POST", "/api/chat", json=payload) as response:
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                content = data["message"]["content"]
                                result_text += content
                                if stream_callback:
                                    stream_callback(content)
                            elif data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue

            return {
                "text": result_text,
                "tool_calls": [],
                "usage": {"input_tokens": 0, "output_tokens": 0},
                "stop_reason": "end_turn"
            }
        except Exception as e:
            print(f"Ollama 调用失败: {e}")
            return {"text": f"错误: {str(e)}", "tool_calls": [], "usage": {}, "stop_reason": "error"}

    def _call_anthropic(self, messages: list[dict],
                        system: str = None,
                        tools: list = None,
                        stream_callback: Callable[[str], None] = None) -> dict:
        """调用 Anthropic API - 支持流式输出"""

        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": messages
        }

        if system:
            try:
                kwargs["system"] = system
            except Exception:
                pass

        if tools:
            kwargs["tools"] = tools

        # 添加超时和重试
        import time
        last_error = None

        for attempt in range(self.max_retries):
            try:
                # 使用流式输出
                kwargs["stream"] = True
                response = self.client.messages.create(**kwargs)

                result_text = ""
                tool_calls = []

                # 处理流式响应
                for event in response:
                    if hasattr(event, 'type'):
                        if event.type == "content_block_delta":
                            # 文本增量
                            if hasattr(event, 'delta') and hasattr(event.delta, 'text'):
                                text = event.delta.text
                                result_text += text
                                if stream_callback:
                                    stream_callback(text)
                        elif event.type == "tool_use_delta":
                            # 工具调用增量
                            if hasattr(event, 'delta') and hasattr(event.delta, 'input'):
                                pass
                        elif event.type == "message_delta":
                            pass

                # 如果没有流式输出，回退到普通调用
                if not result_text:
                    kwargs["stream"] = False
                    response = self.client.messages.create(**kwargs)

                    if response.content:
                        for block in response.content:
                            if hasattr(block, 'type'):
                                if block.type == "text":
                                    result_text += block.text
                                    if stream_callback:
                                        stream_callback(block.text)
                                elif block.type == "tool_use":
                                    tool_calls.append({
                                        "name": block.name,
                                        "input": block.input,
                                        "id": block.id
                                    })

                return {
                    "text": result_text,
                    "tool_calls": tool_calls,
                    "usage": {"input_tokens": 0, "output_tokens": 0},
                    "stop_reason": "end_turn"
                }

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"API 调用失败，重试 ({attempt + 1}/{self.max_retries})...")
                    time.sleep(wait_time)
                    continue
                raise last_error

    def _call_api_with_tools(self, messages: list[dict],
                            tools: list,
                            max_turns: int = 5,
                            stream_callback: Callable[[str], None] = None) -> AgentResponse:
        """带工具调用的 API 调用"""
        current_messages = messages.copy()
        turn = 0

        while turn < max_turns:
            response = self._call_api(current_messages, tools=tools, stream_callback=stream_callback)

            if not response["tool_calls"]:
                return AgentResponse(
                    success=True,
                    content=response["text"],
                    usage=response["usage"]
                )

            tool_results = []
            for tool_call in response["tool_calls"]:
                result = self._execute_tool(tool_call)
                tool_results.append({
                    "tool_use_id": tool_call["id"],
                    "output": result
                })

            current_messages.append({
                "role": "assistant",
                "content": response["text"]
            })

            for tc, tr in zip(response["tool_calls"], tool_results):
                current_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tc["id"],
                        "content": str(tr)
                    }]
                })

            turn += 1

        return AgentResponse(
            success=False,
            content="",
            error=f"Max tool call turns ({max_turns}) exceeded"
        )

    def _execute_tool(self, tool_call: dict) -> Any:
        """执行工具调用（子类可重写）"""
        return {"error": f"Unknown tool: {tool_call['name']}"}

    def format_prompt(self, task: str, context: dict = None) -> list[dict]:
        """格式化提示词"""
        messages = []
        if context:
            context_str = self._format_context(context)
            messages.append({
                "role": "user",
                "content": f"Context:\n{context_str}\n\nTask:\n{task}"
            })
        else:
            messages.append({
                "role": "user",
                "content": task
            })
        return messages

    def _format_context(self, context: dict) -> str:
        """格式化上下文信息"""
        lines = []
        for key, value in context.items():
            lines.append(f"## {key}:")
            if isinstance(value, dict):
                lines.append("```\n" + str(value) + "\n```")
            else:
                lines.append(str(value))
            lines.append("")
        return "\n".join(lines)
