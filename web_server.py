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
        # 多项目支持
        self.projects = {}
        self.current_project_id = None

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


# ========== 多项目 API ==========

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """获取所有项目列表"""
    projects_list = [
        {
            'id': pid,
            'name': p.get('name', '未命名项目'),
            'icon': p.get('icon', '📁'),
            'status': p.get('status', 'idle'),
            'agents': p.get('agents', []),
        }
        for pid, p in state.projects.items()
    ]
    return jsonify({'projects': projects_list})


@app.route('/api/projects', methods=['POST'])
def create_project():
    """创建新项目"""
    data = request.json
    name = data.get('name', '新项目')
    agent_types = data.get('agents', ['orchestrator', 'coder'])

    project_id = f"project-{len(state.projects) + 1}"

    # 角色配置
    agent_configs = {
        'orchestrator': {'id': 'orchestrator', 'name': '项目经理', 'icon': '🎯', 'status': 'idle', 'progress': 0},
        'coder': {'id': 'coder', 'name': '开发者', 'icon': '💻', 'status': 'idle', 'progress': 0},
        'reviewer': {'id': 'reviewer', 'name': '审查员', 'icon': '🔍', 'status': 'idle', 'progress': 0},
        'tester': {'id': 'tester', 'name': '测试员', 'icon': '🧪', 'status': 'idle', 'progress': 0},
        'builder': {'id': 'builder', 'name': '构建师', 'icon': '🔧', 'status': 'idle', 'progress': 0},
    }

    icons = ['📁', '🌐', '🔌', '📱', '💻', '🎯', '🚀', '⚡']

    project = {
        'id': project_id,
        'name': name,
        'icon': icons[len(state.projects) % len(icons)],
        'status': 'idle',
        'agents': [agent_configs.get(t, {'id': t, 'name': t, 'icon': '👤', 'status': 'idle', 'progress': 0}) for t in agent_types],
        'messages': [],
    }

    state.projects[project_id] = project
    return jsonify({'success': True, 'project': project}), 201


@app.route('/api/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    """删除项目"""
    if project_id in state.projects:
        del state.projects[project_id]
        return jsonify({'success': True})
    return jsonify({'error': '项目不存在'}), 404


@app.route('/api/projects/<project_id>/messages', methods=['GET'])
def get_project_messages(project_id):
    """获取项目消息历史"""
    if project_id not in state.projects:
        return jsonify({'error': '项目不存在'}), 404
    return jsonify({'messages': state.projects[project_id].get('messages', [])})


@app.route('/api/projects/<project_id>/messages', methods=['POST'])
def send_project_message(project_id):
    """向项目发送消息"""
    if project_id not in state.projects:
        return jsonify({'error': '项目不存在'}), 404

    data = request.json
    content = data.get('content', '')
    is_interrupt = data.get('isInterrupt', False)

    # 添加用户消息
    user_msg = {
        'id': f'msg-{len(state.projects[project_id]["messages"]) + 1}',
        'agent': 'user',
        'agentName': '我',
        'agentIcon': '👤',
        'agentColor': '#12b7f5',
        'content': content,
        'timestamp': __import__('datetime').datetime.now().isoformat(),
        'isInterrupt': is_interrupt,
    }
    state.projects[project_id]['messages'].append(user_msg)

    # 更新项目状态
    state.projects[project_id]['status'] = 'running'

    # 后台处理消息
    thread = threading.Thread(target=process_project_message, args=(project_id, content, is_interrupt))
    thread.daemon = True
    thread.start()

    return jsonify({'success': True, 'message': user_msg})


@app.route('/api/projects/<project_id>/stream')
def project_stream(project_id):
    """SSE流，推送项目进度更新"""
    from flask import Response

    if project_id not in state.projects:
        return '', 404

    def generate():
        project = state.projects[project_id]
        last_msg_count = len(project.get('messages', []))

        while True:
            messages = project.get('messages', [])
            if len(messages) > last_msg_count:
                for msg in messages[last_msg_count:]:
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                last_msg_count = len(messages)

            if project.get('status') == 'idle' and len(messages) > 0 and last_msg_count == len(messages):
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                break

            import time
            time.sleep(0.5)

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/projects/<project_id>/interrupt', methods=['POST'])
def interrupt_project(project_id):
    """打断项目执行"""
    if project_id not in state.projects:
        return jsonify({'error': '项目不存在'}), 404

    data = request.json
    message = data.get('message', '')

    # 重置所有Agent状态
    project = state.projects[project_id]
    for agent in project.get('agents', []):
        agent['status'] = 'idle'
        agent['progress'] = 0

    # 添加打断消息
    interrupt_msg = {
        'id': f'msg-{len(project["messages"]) + 1}',
        'agent': 'user',
        'agentName': '我 (打断)',
        'agentIcon': '👤',
        'agentColor': '#faad14',
        'content': f'⚡ {message}',
        'timestamp': __import__('datetime').datetime.now().isoformat(),
        'isInterrupt': True,
    }
    project['messages'].append(interrupt_msg)

    return jsonify({'success': True, 'message': interrupt_msg})


def process_project_message(project_id, content, is_interrupt=False):
    """后台处理项目消息"""
    import time
    project = state.projects[project_id]

    if is_interrupt:
        # 打断处理
        time.sleep(0.5)
        msg = {
            'id': f'msg-{len(project["messages"]) + 1}',
            'agent': 'orchestrator',
            'agentName': '项目经理',
            'agentIcon': '🎯',
            'agentColor': '#8b5cf6',
            'content': f'收到您的打断："{content}"，正在调整任务...',
            'timestamp': __import__('datetime').datetime.now().isoformat(),
        }
        project['messages'].append(msg)
        project['status'] = 'idle'
        return

    # 详细的文件操作进展汇报
    agent_responses = {
        'orchestrator': [
            '🎯 正在分析任务需求...',
            '📋 任务已分解为:\n   • 前端页面开发\n   • 后端API实现\n   • 数据库设计',
            '📊 预计总进度: ████░░░░░░ 40%',
            '✅ 任务分配完成，等待执行'
        ],
        'coder': [
            '💻 正在编写 src/main.py...',
            '📝 创建文件: src/models/user.py',
            '📝 创建文件: src/utils/auth.py',
            '🔧 修改: src/config.json 添加数据库配置',
            '🔧 修改: src/auth.py 的登录逻辑',
            '✅ 已完成用户模块核心代码'
        ],
        'reviewer': [
            '🔍 正在审查代码...',
            '📂 审查文件: src/models/user.py',
            '⚠️ 建议优化: user.py 第23行可以使用缓存',
            '⚠️ 建议优化: auth.py 缺少错误处理',
            '✅ 审查通过，代码质量良好'
        ],
        'tester': [
            '🧪 正在编写测试用例...',
            '📝 创建文件: tests/test_user.py',
            '📝 创建文件: tests/test_auth.py',
            '🔄 运行单元测试中...',
            '✅ 12个测试用例全部通过'
        ],
        'builder': [
            '🔧 正在配置构建环境...',
            '📝 创建文件: Dockerfile',
            '📝 创建文件: docker-compose.yml',
            '🔨 执行构建命令: npm run build',
            '✅ 构建成功，镜像大小: 245MB'
        ],
    }

    # 模拟Agent协作
    agents = project.get('agents', [])
    for i, agent in enumerate(agents):
        if agent['id'] == 'user':
            continue

        agent['status'] = 'working'

        # 获取该Agent的详细进展消息
        messages = agent_responses.get(agent['id'], [f'{agent["name"]} 正在处理...'])

        for idx, msg_content in enumerate(messages):
            time.sleep(0.5)

            # 计算进度
            progress = int((idx + 1) / len(messages) * 100)

            msg = {
                'id': f'msg-{len(project["messages"]) + 1}',
                'agent': agent['id'],
                'agentName': agent['name'],
                'agentIcon': agent['icon'],
                'agentColor': agent.get('color', '#6b7280'),
                'content': msg_content,
                'timestamp': __import__('datetime').datetime.now().isoformat(),
                'status': 'working',
                'progress': progress,
            }
            project['messages'].append(msg)

            # 更新Agent进度
            agent['progress'] = progress

        # 完成
        agent['status'] = 'completed'
        agent['progress'] = 100

    project['status'] = 'idle'


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
