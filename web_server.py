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
        self.is_paused = False
        self.lock = threading.Lock()
        self.workflow_thread = None
        self.pause_event = threading.Event()  # 用于暂停控制
        self.pause_event.set()  # 默认不暂停

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

@app.route('/api/pause', methods=['POST'])
def pause_workflow():
    """暂停工作流"""
    if state.is_running:
        state.is_paused = True
        state.pause_event.clear()  # 阻塞等待
        state.messages.append({
            'type': 'workflow_paused',
            'agent': 'system',
            'agentName': '系统',
            'agentIcon': '⏸️',
            'agentColor': '#6b7280',
            'data': {'message': '任务已暂停'}
        })
        return jsonify({'status': 'paused'})
    return jsonify({'error': '没有正在运行的任务'}), 400

@app.route('/api/resume', methods=['POST'])
def resume_workflow():
    """恢复工作流"""
    if state.is_paused:
        state.is_paused = False
        state.pause_event.set()  # 解除阻塞
        state.messages.append({
            'type': 'workflow_resumed',
            'agent': 'system',
            'agentName': '系统',
            'agentIcon': '▶️',
            'agentColor': '#6b7280',
            'data': {'message': '任务已恢复'}
        })
        return jsonify({'status': 'resumed'})
    return jsonify({'error': '任务未暂停'}), 400


# ========== 历史记录 API ==========
@app.route('/api/conversations')
def list_conversations():
    """获取历史对话列表"""
    from database import get_session
    from models import Conversation
    try:
        session = get_session()
        conversations = session.query(Conversation).order_by(Conversation.created_at.desc()).limit(50).all()
        result = [{
            "id": c.id,
            "user_request": c.user_request,
            "project_name": c.project_name,
            "project_path": c.project_path,
            "git_repo_path": c.git_repo_path,
            "status": c.status,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None
        } for c in conversations]
        session.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/conversations/<conv_id>')
def get_conversation(conv_id):
    """获取对话详情"""
    from database import get_session
    from models import Conversation, Task, Message, CodeResult, ReviewRecord, TestRecord
    try:
        session = get_session()

        # 获取对话
        conv = session.query(Conversation).filter_by(id=conv_id).first()
        if not conv:
            session.close()
            return jsonify({'error': '对话不存在'}), 404

        # 获取任务列表
        tasks = session.query(Task).filter_by(conversation_id=conv_id).all()

        # 获取消息列表
        messages = session.query(Message).filter_by(conversation_id=conv_id).order_by(Message.created_at).all()

        # 获取代码结果
        task_ids = [t.id for t in tasks]
        code_results = session.query(CodeResult).filter(CodeResult.task_id.in_(task_ids)).all() if task_ids else []

        # 获取审查记录
        review_records = session.query(ReviewRecord).filter(ReviewRecord.task_id.in_(task_ids)).all() if task_ids else []

        # 获取测试记录
        test_records = session.query(TestRecord).filter(TestRecord.task_id.in_(task_ids)).all() if task_ids else []

        session.close()

        result = {
            "conversation": conv.to_dict(),
            "tasks": [t.to_dict() for t in tasks],
            "messages": [m.to_dict() for m in messages],
            "code_results": [c.to_dict() for c in code_results],
            "review_records": [r.to_dict() for r in review_records],
            "test_records": [t.to_dict() for t in test_records]
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/conversations/<conv_id>/tasks')
def get_conversation_tasks(conv_id):
    """获取对话的所有任务"""
    from database import get_session
    from models import Task
    try:
        session = get_session()
        tasks = session.query(Task).filter_by(conversation_id=conv_id).all()
        session.close()
        return jsonify([t.to_dict() for t in tasks])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
                        # 更新消息内容，保留完整内容
                        content = data.get('content', '')
                        last_msg['data']['content'] = content
                        last_msg['data']['message'] = content
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
