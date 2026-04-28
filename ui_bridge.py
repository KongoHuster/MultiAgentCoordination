"""
UI Bridge - PyWebView 桥接层
用于将 WorkflowEngine 的执行事件实时发送到前端聊天界面
"""
import json
import threading
import queue
from datetime import datetime
from typing import Optional, Callable

# 事件类型定义
class EventTypes:
    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETE = "workflow_complete"
    TASK_DECOMPOSE = "task_decompose"
    SUBTASK_START = "subtask_start"
    SUBTASK_COMPLETE = "subtask_complete"
    CODING_START = "coding_start"
    CODING_COMPLETE = "coding_complete"
    REVIEW_START = "review_start"
    REVIEW_RESULT = "review_result"
    TEST_START = "test_start"
    TEST_RESULT = "test_result"
    DECISION = "decision"
    RETRY = "retry"
    ERROR = "error"
    PROJECT_BUILD = "project_build"
    GIT_COMMIT = "git_commit"


# Agent 信息映射
AGENT_INFO = {
    "system": {"name": "System", "icon": "⚙️", "color": "#6b7280"},
    "orchestrator": {"name": "Orchestrator", "icon": "🎯", "color": "#8b5cf6"},
    "coder": {"name": "Coder", "icon": "💻", "color": "#3b82f6"},
    "reviewer": {"name": "Reviewer", "icon": "🔍", "color": "#f59e0b"},
    "tester": {"name": "Tester", "icon": "🧪", "color": "#10b981"},
    "project_builder": {"name": "ProjectBuilder", "icon": "🏗️", "color": "#ec4899"},
    "git_manager": {"name": "GitManager", "icon": "📦", "color": "#6366f1"},
    "user": {"name": "You", "icon": "👤", "color": "#22c55e"},
}


class UIEventEmitter:
    """UI事件发射器 - 线程安全地将事件发送到前端"""

    def __init__(self):
        self.window = None
        self.message_queue = queue.Queue()
        self.lock = threading.Lock()
        self._enabled = True

    def set_window(self, window):
        """设置窗口引用"""
        self.window = window

    def enable(self):
        """启用事件发送"""
        self._enabled = True

    def disable(self):
        """禁用事件发送（用于命令行模式）"""
        self._enabled = False

    def _get_agent_info(self, agent: str) -> dict:
        """获取Agent信息"""
        return AGENT_INFO.get(agent, {"name": agent, "icon": "❓", "color": "#6b7280"})

    def _format_message(self, event_type: str, data: dict, agent: str = "system") -> dict:
        """格式化消息"""
        agent_info = self._get_agent_info(agent)
        return {
            "type": event_type,
            "agent": agent,
            "agentName": agent_info["name"],
            "agentIcon": agent_info["icon"],
            "agentColor": agent_info["color"],
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }

    def emit(self, event_type: str, data: dict, agent: str = "system"):
        """发送事件到前端"""
        if not self._enabled:
            # 命令行模式：直接打印
            agent_info = self._get_agent_info(agent)
            print(f"{agent_info['icon']} [{agent_info['name']}] {data.get('message', '')}")
            return

        message = self._format_message(event_type, data, agent)

        # 线程安全地发送到前端
        if self.window:
            with self.lock:
                try:
                    js_code = f"window.addMessage({json.dumps(message, ensure_ascii=False)})"
                    self.window.evaluate_js(js_code)
                except Exception as e:
                    print(f"发送消息失败: {e}")

    def emit_user_message(self, text: str):
        """发送用户消息（右侧气泡）"""
        if not self._enabled:
            return

        if self.window:
            with self.lock:
                try:
                    message = {
                        "type": "user_message",
                        "agent": "user",
                        "agentName": "You",
                        "agentIcon": "👤",
                        "agentColor": "#22c55e",
                        "timestamp": datetime.now().isoformat(),
                        "data": {"message": text}
                    }
                    js_code = f"window.addUserMessage({json.dumps(message, ensure_ascii=False)})"
                    self.window.evaluate_js(js_code)
                except Exception as e:
                    print(f"发送用户消息失败: {e}")

    def emit_progress(self, current: int, total: int, task: str):
        """发送进度更新"""
        self.emit("progress", {
            "current": current,
            "total": total,
            "task": task,
            "message": f"进度: {current}/{total} - {task}"
        }, agent="system")


# 全局事件发射器实例
ui_emitter = UIEventEmitter()


def get_ui_emitter() -> UIEventEmitter:
    """获取全局UI事件发射器"""
    return ui_emitter


class WebViewManager:
    """WebView 窗口管理器"""

    def __init__(self, title: str = "多Agent协作系统", width: int = 1100, height: int = 800):
        self.title = title
        self.width = width
        self.height = height
        self.window = None
        self.event_emitter = ui_emitter
        self._html_path = None

    def set_html_path(self, path: str):
        """设置HTML文件路径"""
        self._html_path = path

    def create_window(self, html_content: str = None):
        """创建WebView窗口"""
        import os

        # 优先使用文件路径
        if self._html_path and os.path.exists(self._html_path):
            html_url = self._html_path
        elif html_content:
            html_url = html_content
        else:
            # 使用默认HTML
            html_url = self._get_default_html()

        self.window = webview.create_window(
            self.title,
            html_url,
            width=self.width,
            height=self.height,
            resizable=True,
            min_size=(800, 600),
            js_api=self.event_emitter
        )
        self.event_emitter.set_window(self.window)
        return self.window

    def _get_default_html(self) -> str:
        """获取默认HTML路径"""
        import os
        web_dir = os.path.join(os.path.dirname(__file__), 'web')
        index_path = os.path.join(web_dir, 'index.html')
        if os.path.exists(index_path):
            return index_path
        return self._get_embedded_html()

    def _get_embedded_html(self) -> str:
        """获取嵌入式HTML（备用方案）"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>多Agent协作系统</title>
            <style>
                body { font-family: system-ui, sans-serif; padding: 20px; background: #1a1a2e; color: #fff; }
                .message { padding: 10px; margin: 10px 0; background: #16213e; border-radius: 8px; }
            </style>
        </head>
        <body>
            <div id="messages"></div>
            <script>
                window.addMessage = function(msg) {
                    const div = document.createElement('div');
                    div.className = 'message';
                    div.innerHTML = msg.agentIcon + ' <strong>' + msg.agentName + '</strong>: ' + msg.data.message;
                    document.getElementById('messages').appendChild(div);
                };
                window.addUserMessage = window.addMessage;
            </script>
        </body>
        </html>
        """

    def start(self):
        """启动WebView事件循环"""
        import webview
        self.create_window()
        webview.start()


# 懒加载 webview
def _get_webview():
    """懒加载 webview 模块"""
    try:
        import webview
        return webview
    except ImportError:
        print("警告: pywebview 未安装，将使用命令行模式")
        print("安装命令: pip install pywebview")
        return None
