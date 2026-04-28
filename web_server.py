#!/usr/bin/env python3
"""
多Agent协作系统 - Flask Web服务器
使用Flask提供Web界面和API服务
"""
import os
import sys
import threading
import json
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_config
from workflow_engine import WorkflowEngine
from ui_bridge import get_ui_emitter, EventTypes, UIEventEmitter

# 创建Flask应用
app = Flask(__name__, static_folder='web', static_url_path='')
CORS(app)

# 全局状态
class AppState:
    def __init__(self):
        self.workflow_engine = None
        self.messages = []
        self.is_running = False
        self.lock = threading.Lock()

state = AppState()

# Web界面
@app.route('/')
def index():
    """返回主页面"""
    return send_from_directory('web', 'index.html')

@app.route('/styles.css')
def styles():
    return send_from_directory('web', 'styles.css')

@app.route('/app.js')
def app_js():
    return send_from_directory('web', 'app.js')

# API接口
@app.route('/api/start', methods=['POST'])
def start_workflow():
    """启动工作流"""
    data = request.json
    task = data.get('task', '')

    if not task:
        return jsonify({'error': '任务描述不能为空'}), 400

    if state.is_running:
        return jsonify({'error': '工作流正在运行中'}), 400

    def run_workflow():
        state.is_running = True
        state.messages = []

        # 创建自定义的事件发射器来收集消息
        collector = MessageCollector()
        old_emitter = get_ui_emitter()
        collector.window = old_emitter.window
        collector._enabled = True

        # 临时替换全局发射器
        import ui_bridge
        ui_bridge.ui_emitter = collector

        try:
            config = get_config()
            engine = WorkflowEngine(config.anthropic_api_key)
            state.workflow_engine = engine
            result = engine.run(task)
            state.messages.append({
                'type': 'workflow_complete',
                'agent': 'system',
                'agentName': 'System',
                'agentIcon': '🎉',
                'agentColor': '#6b7280',
                'data': result
            })
        except Exception as e:
            state.messages.append({
                'type': 'error',
                'agent': 'system',
                'agentName': 'System',
                'agentIcon': '❌',
                'agentColor': '#6b7280',
                'data': {'message': str(e)}
            })
        finally:
            # 恢复原发射器
            ui_bridge.ui_emitter = old_emitter
            state.is_running = False

    thread = threading.Thread(target=run_workflow)
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'started', 'message': '工作流已启动'})

@app.route('/api/messages')
def get_messages():
    """获取消息列表（轮询）"""
    return jsonify({'messages': state.messages, 'is_running': state.is_running})

@app.route('/api/messages/stream')
def stream_messages():
    """Server-Sent Events 实时推送消息"""
    from flask import Response

    def generate():
        last_index = 0
        while True:
            if len(state.messages) > last_index:
                for msg in state.messages[last_index:]:
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                last_index = len(state.messages)

            if not state.is_running and len(state.messages) > 0 and last_index == len(state.messages):
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                break

            import time
            time.sleep(0.5)

    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/status')
def get_status():
    """获取当前状态"""
    return jsonify({
        'is_running': state.is_running,
        'message_count': len(state.messages)
    })

@app.route('/api/clear', methods=['POST'])
def clear_messages():
    """清空消息"""
    state.messages = []
    return jsonify({'status': 'ok'})


class MessageCollector(UIEventEmitter):
    """消息收集器 - 替代UI事件发射器收集消息"""

    def emit(self, event_type: str, data: dict, agent: str = "system"):
        """收集消息"""
        message = self._format_message(event_type, data, agent)
        with state.lock:
            # 检查是否是流式更新
            if event_type == "stream_update":
                # 流式更新只更新最后一条消息
                if state.messages:
                    last_msg = state.messages[-1]
                    if last_msg.get('type') in ['coding_start', 'review_start', 'test_start']:
                        last_msg['data']['content'] = data.get('content', '')
                        last_msg['data']['message'] = data.get('content', '')[:500] + ('...' if len(data.get('content', '')) > 500 else '')
                        return
            state.messages.append(message)
        print(f"[{agent}] {data.get('message', '')[:100]}...")

    def emit_stream(self, event_type: str, data: dict, agent: str = "system"):
        """收集流式消息片段"""
        message = self._format_message(event_type, data, agent)
        with state.lock:
            state.messages.append(message)
        # 打印流式内容
        content = data.get('content', data.get('message', ''))
        print(content, end='', flush=True)


def main():
    """主入口"""
    print("=" * 60)
    print("多Agent协作系统 - Web服务器模式")
    print("=" * 60)

    config = get_config()
    print(f"API Key: {'已设置' if config.anthropic_api_key else '未设置'}")
    print(f"Base URL: {config.base_url}")
    print()

    print("启动Web服务器...")
    print("访问地址: http://localhost:5000")
    print()
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)

    app.run(host='0.0.0.0', port=8080, debug=True, threaded=True)


if __name__ == "__main__":
    main()
