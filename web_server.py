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
from agents.orchestrator import OrchestratorAgent
from agents.coder import CoderAgent
from agents.reviewer import ReviewerAgent
from agents.tester import TesterAgent

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
        # 配置
        self.config = get_config()

state = AppState()


# ========== AI Agent 执行器 ==========

class AgentExecutor:
    """AI Agent执行器 - 调用真实AI进行任务处理"""

    def __init__(self, project, config=None):
        self.project = project
        self.config = config or get_config()

        # 初始化Agent（使用Ollama）
        if self.config.use_ollama:
            base_url = self.config.ollama_url
            model = self.config.ollama_model
        else:
            base_url = self.config.base_url
            model = self.config.default_model

        self.orchestrator = OrchestratorAgent(
            api_key=self.config.anthropic_api_key,
            base_url=base_url,
            model=model
        )
        self.coder = CoderAgent(
            api_key=self.config.anthropic_api_key,
            base_url=base_url,
            model=model
        )
        self.reviewer = ReviewerAgent(
            api_key=self.config.anthropic_api_key,
            base_url=base_url,
            model=model
        )
        self.tester = TesterAgent(
            api_key=self.config.anthropic_api_key,
            base_url=base_url,
            model=model
        )

    def decompose_task(self, user_request):
        """调用AI进行任务分解"""
        try:
            result = self.orchestrator.decompose_task(user_request)
            return result.get('text', '')
        except Exception as e:
            return f"任务分解失败: {str(e)}"

    def generate_code(self, task):
        """调用AI生成代码"""
        try:
            result = self.coder.execute(task)
            return result.content if hasattr(result, 'content') else str(result)
        except Exception as e:
            return f"代码生成失败: {str(e)}"

    def review_code(self, code_content):
        """调用AI审查代码"""
        try:
            result = self.reviewer.execute(code_content)
            return result.content if hasattr(result, 'content') else str(result)
        except Exception as e:
            return f"代码审查失败: {str(e)}"

    def fix_issues(self, issues, code_content):
        """调用AI根据审查反馈修复代码"""
        try:
            prompt = f"""根据以下审查问题，修复代码中的问题。

审查问题：
{issues}

当前代码：
{code_content}

请生成修复后的代码，并说明做了哪些修改。"""
            result = self.coder.execute(prompt)
            return result.content if hasattr(result, 'content') else str(result)
        except Exception as e:
            return f"代码修复失败: {str(e)}"

    def generate_tests(self, code_content):
        """调用AI生成测试"""
        try:
            result = self.tester.execute(code_content)
            return result.content if hasattr(result, 'content') else str(result)
        except Exception as e:
            return f"测试生成失败: {str(e)}"


def find_agent(project, agent_id):
    """查找项目中的Agent"""
    for agent in project.get('agents', []):
        if agent['id'] == agent_id:
            return agent
    return {'id': agent_id, 'name': agent_id, 'icon': '🤖', 'color': '#6b7280'}


def send_ai_message(project, agent_id, content):
    """发送AI生成的消息到聊天"""
    agent = find_agent(project, agent_id)
    msg = {
        'id': f'msg-{len(project["messages"]) + 1}',
        'agent': agent_id,
        'agentName': agent['name'],
        'agentIcon': agent['icon'],
        'agentColor': agent.get('color', '#6b7280'),
        'content': content,
        'timestamp': __import__('datetime').datetime.now().isoformat(),
        'isAI': True
    }
    project['messages'].append(msg)
    return msg

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


@app.route('/api/projects/<project_id>/tasks', methods=['GET'])
def get_project_tasks(project_id):
    """获取项目任务列表"""
    if project_id not in state.projects:
        return jsonify({'error': '项目不存在'}), 404
    return jsonify({'tasks': state.projects[project_id].get('tasks', [])})


@app.route('/api/projects/<project_id>/tasks/<task_id>', methods=['PUT'])
def update_project_task(project_id, task_id):
    """更新任务状态"""
    if project_id not in state.projects:
        return jsonify({'error': '项目不存在'}), 404

    project = state.projects[project_id]
    data = request.json

    for task in project.get('tasks', []):
        if task['id'] == task_id:
            task.update(data)
            return jsonify({'success': True, 'task': task})

    return jsonify({'error': '任务不存在'}), 404


@app.route('/api/projects/<project_id>/messages', methods=['POST'])
def send_project_message(project_id):
    """向项目发送消息"""
    if project_id not in state.projects:
        return jsonify({'error': '项目不存在'}), 404

    data = request.json
    content = data.get('content', '')
    is_interrupt = data.get('isInterrupt', False)

    project = state.projects[project_id]
    user_msg = {
        'id': f'msg-{len(project.get("messages", [])) + 1}',
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

    # 检查是否启用AI模式
    use_ai = data.get('useAI', False)

    # 后台处理消息
    if use_ai and state.config.use_ollama:
        # 使用真实AI Agent
        thread = threading.Thread(target=process_project_message_with_ai,
                                args=(project_id, content, is_interrupt))
    else:
        # 使用模拟消息
        thread = threading.Thread(target=process_project_message,
                                args=(project_id, content, is_interrupt))
    thread.daemon = True
    thread.start()

    return jsonify({'success': True, 'message': user_msg})


def process_project_message_with_ai(project_id, content, is_interrupt=False):
    """使用真实AI Agent处理项目消息"""
    import time
    project = state.projects[project_id]

    # 初始化任务列表
    if 'tasks' not in project:
        project['tasks'] = []
    if 'pending_fixes' not in project:
        project['pending_fixes'] = []
    if 'generated_code' not in project:
        project['generated_code'] = ''

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

    # 初始化AI执行器
    executor = AgentExecutor(project, state.config)

    # ===== 阶段1: 项目经理任务分解 =====
    send_ai_message(project, 'orchestrator', '🎯 正在调用AI分析任务需求...')
    time.sleep(1)

    try:
        # 调用AI进行任务分解
        ai_task_list = executor.decompose_task(content)
        send_ai_message(project, 'orchestrator', f'📋 **AI任务分解结果:**\n\n{ai_task_list}')
    except Exception as e:
        send_ai_message(project, 'orchestrator', f'⚠️ AI任务分解失败，使用默认任务列表。错误: {str(e)}')

    # 初始化项目任务
    project['tasks'] = [
        {'id': 't1', 'title': '代码开发', 'assignee': 'coder', 'status': 'pending'},
        {'id': 't2', 'title': '代码审查', 'assignee': 'reviewer', 'status': 'pending', 'depends_on': ['t1']},
        {'id': 't3', 'title': '修复审查问题', 'assignee': 'coder', 'status': 'pending', 'depends_on': ['t2'], 'is_fix_task': True},
        {'id': 't4', 'title': '生成测试', 'assignee': 'tester', 'status': 'pending', 'depends_on': ['t3']},
    ]

    # 显示任务列表
    task_list_msg = '📋 **任务分解:**\n\n'
    for t in project['tasks']:
        status_icon = {'pending': '☐', 'in_progress': '◐', 'completed': '☑'}.get(t['status'], '?')
        task_list_msg += f'{status_icon} **[{t["id"]}] {t["title"]}** - {t["assignee"]}\n'
    send_ai_message(project, 'orchestrator', task_list_msg)

    # ===== 阶段2: 开发者代码生成 =====
    for task in project['tasks']:
        if task['assignee'] != 'coder' or task.get('is_fix_task'):
            continue

        task['status'] = 'in_progress'
        send_ai_message(project, 'coder', f'💻 **执行 [{task["id"]}] {task["title"]}...**')

        try:
            # 调用AI生成代码
            code_result = executor.generate_code(f"用户需求: {content}\n\n任务: {task['title']}")
            project['generated_code'] = code_result
            send_ai_message(project, 'coder', f'📝 **AI生成的代码:**\n\n```python\n{code_result}\n```')
        except Exception as e:
            send_ai_message(project, 'coder', f'⚠️ 代码生成失败: {str(e)}')

        task['status'] = 'completed'

    # ===== 阶段3: 审查员代码审查 =====
    review_task = next((t for t in project['tasks'] if t['assignee'] == 'reviewer'), None)
    if review_task:
        review_task['status'] = 'in_progress'
        send_ai_message(project, 'reviewer', f'🔍 **执行 [{review_task["id"]}] {review_task["title"]}...**')

        try:
            # 调用AI审查代码
            review_result = executor.review_code(project.get('generated_code', ''))
            send_ai_message(project, 'reviewer', f'🔍 **AI代码审查结果:**\n\n{review_result}')

            # 检查是否有问题需要修复
            if '问题' in review_result or 'issue' in review_result.lower() or 'BLOCKER' in review_result:
                # 自动创建修复任务
                project['pending_fixes'] = [{'issue': review_result}]
                fix_task = next((t for t in project['tasks'] if t.get('is_fix_task')), None)
                if fix_task:
                    fix_task['status'] = 'pending'
                    send_ai_message(project, 'reviewer', '⚠️ 发现问题，自动创建修复任务 [t3]')
        except Exception as e:
            send_ai_message(project, 'reviewer', f'⚠️ 代码审查失败: {str(e)}')

        review_task['status'] = 'completed'

    # ===== 阶段4: 开发者修复问题 =====
    fix_task = next((t for t in project['tasks'] if t.get('is_fix_task')), None)
    if fix_task and fix_task['status'] == 'pending':
        fix_task['status'] = 'in_progress'
        send_ai_message(project, 'coder', f'🔧 **执行 [{fix_task["id"]}] {fix_task["title"]}...**')

        try:
            # 调用AI修复问题
            fix_result = executor.fix_issues(
                project.get('pending_fixes', []),
                project.get('generated_code', '')
            )
            project['generated_code'] = fix_result  # 更新代码
            send_ai_message(project, 'coder', f'🔧 **AI修复结果:**\n\n```python\n{fix_result}\n```')
        except Exception as e:
            send_ai_message(project, 'coder', f'⚠️ 代码修复失败: {str(e)}')

        fix_task['status'] = 'completed'

    # ===== 阶段5: 测试工程师生成测试 =====
    test_task = next((t for t in project['tasks'] if t['assignee'] == 'tester'), None)
    if test_task:
        test_task['status'] = 'in_progress'
        send_ai_message(project, 'tester', f'🧪 **执行 [{test_task["id"]}] {test_task["title"]}...**')

        try:
            # 调用AI生成测试
            test_result = executor.generate_tests(project.get('generated_code', ''))
            send_ai_message(project, 'tester', f'🧪 **AI生成的测试:**\n\n```python\n{test_result}\n```')
        except Exception as e:
            send_ai_message(project, 'tester', f'⚠️ 测试生成失败: {str(e)}')

        test_task['status'] = 'completed'

    # ===== 完成 =====
    completion_msg = '✅ **全部任务完成!**\n\n📋 **任务状态:**\n\n'
    for t in project['tasks']:
        status_icon = {'pending': '☐', 'in_progress': '◐', 'completed': '☑'}.get(t['status'], '?')
        completion_msg += f'{status_icon} [{t["id"]}] {t["title"]} - {t["status"]}\n'
    send_ai_message(project, 'orchestrator', completion_msg)

    project['status'] = 'idle'


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

    # 初始化任务列表
    if 'tasks' not in project:
        project['tasks'] = []
    if 'pending_fixes' not in project:
        project['pending_fixes'] = []

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

    # 任务定义 - 结构化子任务列表
    task_definitions = [
        {
            'id': 't1',
            'title': '用户模块开发',
            'description': '实现用户认证、注册、个人信息管理',
            'assignee': 'coder',
            'assigneeName': '👨‍💻 开发者',
            'status': 'pending',
            'depends_on': [],
            'sub_tasks': [
                '实现 src/main.py Flask应用',
                '创建 src/models/user.py 用户模型',
                '编写 src/utils/auth.py 认证工具'
            ]
        },
        {
            'id': 't2',
            'title': '代码审查',
            'description': '审查用户模块代码质量和安全性',
            'assignee': 'reviewer',
            'assigneeName': '🔍 审查员',
            'status': 'pending',
            'depends_on': ['t1'],
            'sub_tasks': [
                '审查 src/models/user.py',
                '审查 src/utils/auth.py',
                '审查 src/main.py'
            ]
        },
        {
            'id': 't3',
            'title': '修复审查问题',
            'description': '根据审查反馈修复发现的问题',
            'assignee': 'coder',
            'assigneeName': '👨‍💻 开发者',
            'status': 'pending',
            'depends_on': ['t2'],
            'is_fix_task': True,
            'sub_tasks': []
        },
        {
            'id': 't4',
            'title': '编写测试用例',
            'description': '为用户模块编写单元测试和集成测试',
            'assignee': 'tester',
            'assigneeName': '🧪 测试工程师',
            'status': 'pending',
            'depends_on': ['t3'],
            'sub_tasks': [
                '创建 tests/test_user.py',
                '创建 tests/test_auth.py',
                '执行测试并生成报告'
            ]
        },
        {
            'id': 't5',
            'title': 'Docker部署配置',
            'description': '配置Docker镜像构建和部署',
            'assignee': 'builder',
            'assigneeName': '🏗️ 构建工程师',
            'status': 'pending',
            'depends_on': ['t4'],
            'sub_tasks': [
                '创建 Dockerfile',
                '创建 docker-compose.yml',
                '执行镜像构建'
            ]
        }
    ]

    # 详细的文件操作进展汇报 - 包含具体代码和内容
    # Orchestrator消息 - 包含任务分解
    def generate_orchestrator_task_list(tasks):
        """生成带checkbox的任务列表"""
        lines = ['📋 任务分解:\n']
        for t in tasks:
            checkbox = '☐' if t['status'] == 'pending' else ('◐' if t['status'] == 'in_progress' else '☑')
            lines.append(f'{checkbox} **[{t["id"]}] {t["title"]}**')
            lines.append(f'    👤 负责人: {t["assigneeName"]}')
            lines.append(f'    📝 {t["description"]}')
            if t['sub_tasks']:
                for st in t['sub_tasks']:
                    lines.append(f'       • {st}')
            lines.append('')
        return '\n'.join(lines)

    def generate_fix_task_message(fixes):
        """生成修复任务消息"""
        lines = ['⚠️ **需要修复的问题:**\n']
        for i, fix in enumerate(fixes, 1):
            lines.append(f'{i}. {fix["file"]}:{fix["line"]}')
            lines.append(f'   问题: {fix["issue"]}')
            lines.append(f'   建议: {fix["suggestion"]}')
            lines.append('')
        return '\n'.join(lines)

    def get_available_tasks(project):
        """获取当前可执行的任务（依赖已完成的）"""
        available = []
        completed_ids = [t['id'] for t in project['tasks'] if t['status'] == 'completed']
        for t in project['tasks']:
            if t['status'] == 'pending':
                deps = t.get('depends_on', [])
                if all(d in completed_ids for d in deps):
                    available.append(t)
        return available

    def update_task_status(project, task_id, status, agent_id=None):
        """更新任务状态"""
        for t in project['tasks']:
            if t['id'] == task_id:
                t['status'] = status
                if agent_id:
                    t['executed_by'] = agent_id
                return t
        return None

    # 初始化任务列表到项目状态
    project['tasks'] = [t.copy() for t in task_definitions]
    project['pending_fixes'] = []

    # Agent消息模板 - 包含任务相关的进展汇报
    agent_responses = {
        'orchestrator': [
            '🎯 正在分析任务需求，理解业务逻辑...',
            '''📋 任务分解完成:

项目: 用户认证模块

☐ **[t1] 用户模块开发**
   👤 负责人: 👨‍💻 开发者
   📝 实现用户认证、注册、个人信息管理
   • 实现 src/main.py Flask应用
   • 创建 src/models/user.py 用户模型
   • 编写 src/utils/auth.py 认证工具

☐ **[t2] 代码审查**
   👤 负责人: 🔍 审查员
   📝 审查用户模块代码质量和安全性

☐ **[t3] 修复审查问题** (等待审查完成)
   👤 负责人: 👨‍💻 开发者
   📝 根据审查反馈修复发现的问题

☐ **[t4] 编写测试用例**
   👤 负责人: 🧪 测试工程师
   📝 为用户模块编写单元测试和集成测试

☐ **[t5] Docker部署配置**
   👤 负责人: 🏗️ 构建工程师
   📝 配置Docker镜像构建和部署

📊 预计完成时间: 约30分钟
✅ 任务分配完成，各Agent开始执行''',
        ],
        'coder': [
            '''👨‍💻 **正在执行 [t1] 用户模块开发...**

☐ [t1] 用户模块开发 → ◐ 进行中

📄 创建文件: src/main.py
```python
from flask import Flask, request, jsonify
from auth import verify_token

app = Flask(__name__)

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    # 验证用户...
    return jsonify({'token': 'xxx'})
```''',
            '''📝 创建文件: src/models/user.py

📄 文件: src/models/user.py
```python
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120))
    password_hash = db.Column(db.String(255))

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email
        }
```

✅ 子任务完成: 创建 src/models/user.py 用户模型''',
            '''📝 创建文件: src/utils/auth.py

📄 文件: src/utils/auth.py
```python
import hashlib
import secrets

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return hashlib.pbkdf2_hmac('sha256',
        password.encode(), salt.encode(), 100000)

def verify_password(password: str, hash: str) -> bool:
    # 验证逻辑...
    return True
```

✅ 子任务完成: 编写 src/utils/auth.py 认证工具''',
            '''🔧 修改: src/config.json

📄 文件: src/config.json
```json
{
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "app_db"
  },
  "security": {
    "jwt_secret": "generated_key_here",
    "token_expire": 3600
  }
}
```
已添加数据库和安全配置''',
            '''✅ **[t1] 用户模块开发** 已完成!

📊 统计:
   - 新增文件: 3个
   - 修改文件: 2个
   - 代码行数: +186行
   - 状态: ☐ [t1] → ☑ [t1]

➡️ 通知项目经理: t1已完成，准备进入t2代码审查阶段''',
        ],
        'reviewer': [
            '''🔍 **正在执行 [t2] 代码审查...**

☐ [t2] 代码审查 → ◐ 进行中

审查范围:
   - src/models/user.py
   - src/utils/auth.py
   - src/main.py''',
            '''📂 审查文件: src/models/user.py

代码审查报告:

✅ 优点:
   - 使用ORM良好实践
   - to_dict方法设计合理

⚠️ 建议:
   - 第15行: 建议添加 email 唯一性验证
   - 第20行: password_hash 长度可以增加到 512''',
            '''📂 审查文件: src/utils/auth.py

代码审查报告:

✅ 优点:
   - 使用 secrets 模块生成盐值
   - PBKDF2 迭代次数足够

⚠️ 建议:
   - 第8行: 可以添加密码强度验证
   - 建议添加账户锁定机制''',
            '''⚠️ **发现的问题汇总:**

1. src/models/user.py:15
   问题: email 字段缺少唯一性约束
   建议: 添加 unique=True

2. src/utils/auth.py:20
   问题: 缺少登录失败次数限制
   建议: 添加账户锁定机制

3. src/main.py:25
   问题: 错误处理不够完善
   建议: 添加具体的错误码''',
            '''📋 **审查完成，自动生成修复任务 [t3]**

🔧 修复任务详情:
   • [t3-1] src/models/user.py:15 - 添加 email 唯一性约束
   • [t3-2] src/utils/auth.py:20 - 添加账户锁定机制
   • [t3-3] src/main.py:25 - 完善错误处理

👤 负责人: 👨‍💻 开发者
⏳ 依赖: [t2] 代码审查 (当前)
✅ 状态: ☐ [t3] → 等待开发者执行

➡️ 通知项目经理: t2已完成，发现3个问题需要开发者修复''',
        ],
        'coder_fix': [
            '''🔧 **执行 [t3] 修复审查问题...**

☐ [t3] 修复审查问题 → ◐ 进行中

根据审查反馈修复3个问题:

📄 [t3-1] 修复 src/models/user.py:15 - 添加 email 唯一性约束
```python
# 修改前
email = db.Column(db.String(120))

# 修改后
email = db.Column(db.String(120), unique=True)
```''',
            '''📄 [t3-2] 修复 src/utils/auth.py - 添加账户锁定机制
```python
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 300  # 5分钟

class AccountLockout:
    def __init__(self):
        self.attempts = {}

    def record_failure(self, username):
        self.attempts[username] = self.attempts.get(username, 0) + 1
        if self.attempts[username] >= MAX_LOGIN_ATTEMPTS:
            return True  # 账户被锁定
        return False

    def reset(self, username):
        self.attempts[username] = 0
```''',
            '''📄 [t3-3] 修复 src/main.py:25 - 完善错误处理
```python
class ErrorCode:
    AUTH_INVALID_CREDENTIALS = 1001
    AUTH_ACCOUNT_LOCKED = 1002
    AUTH_TOKEN_EXPIRED = 1003
    VALIDATION_ERROR = 2001
    INTERNAL_ERROR = 5001

def handle_error(error_code, message):
    return jsonify({
        'error': {
            'code': error_code,
            'message': message
        }
    }), get_http_status(error_code)
```''',
            '''✅ **[t3] 修复审查问题** 已完成!

📊 修复统计:
   - 修复文件: 3个
   - 修复问题: 3个 (100%)
   - 状态: ☐ [t3] → ☑ [t3]

➡️ 通知项目经理: t3已完成，代码已按审查意见修复''',
        ],
        'tester': [
            '''🧪 **正在执行 [t4] 编写测试用例...**

☐ [t4] 编写测试用例 → ◐ 进行中

测试计划:
   - 单元测试: 15个
   - 集成测试: 5个
   - 端到端测试: 3个''',
            '''📝 创建文件: tests/test_user.py

📄 文件: tests/test_user.py
```python
import pytest
from models.user import User

class TestUserModel:
    def test_create_user(self):
        user = User(username='test', email='test@test.com')
        assert user.id is not None

    def test_password_hashing(self):
        from utils.auth import hash_password
        hash = hash_password('test123')
        assert len(hash) == 64
```''',
            '''📝 创建文件: tests/test_auth.py

📄 文件: tests/test_auth.py
```python
import pytest
from auth import login, verify_token

class TestAuth:
    def test_login_success(self):
        result = login('admin', 'password123')
        assert 'token' in result

    def test_login_failure(self):
        with pytest.raises(AuthError):
            login('admin', 'wrong')
```''',
            '''🔄 运行测试中...

正在执行: pytest tests/ -v

✅ test_user.py::TestUserModel::test_create_user PASSED
✅ test_user.py::TestUserModel::test_password_hashing PASSED
✅ test_auth.py::TestAuth::test_login_success PASSED
✅ test_auth.py::TestAuth::test_login_failure PASSED''',
            '''✅ **[t4] 编写测试用例** 已完成!

📊 测试报告:
   - 总测试数: 23个
   - 通过: 23个 (100%)
   - 失败: 0个
   - 跳过: 0个
   - 状态: ☐ [t4] → ☑ [t4]

⏱️ 总耗时: 1.2秒
➡️ 通知项目经理: t4已完成，所有测试通过''',
        ],
        'builder': [
            '''🏗️ **正在执行 [t5] Docker部署配置...**

☐ [t5] Docker部署配置 → ◐ 进行中

构建配置:
   - Docker镜像构建
   - 多阶段构建优化
   - 环境变量配置''',
            '''📝 创建文件: Dockerfile

📄 文件: Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN pip install gunicorn

EXPOSE 8080
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "app:app"]
```''',
            '''📝 创建文件: docker-compose.yml

📄 文件: docker-compose.yml
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://db:5432/app
  db:
    image: postgres:15
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```''',
            '''🔨 执行构建...

$ docker build -t myapp:latest .

Step 1/7 : FROM python:3.11-slim
Step 2/7 : WORKDIR /app
Step 3/7 : COPY requirements.txt .
Step 4/7 : RUN pip install -r requirements.txt
Step 5/7 : COPY . .
Step 6/7 : RUN pip install gunicorn
Step 7/7 : CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "app:app"]
Successfully built abc123
Successfully tagged myapp:latest''',
            '''✅ **[t5] Docker部署配置** 已完成!

📊 构建统计:
   - 镜像名称: myapp:latest
   - 镜像大小: 245MB
   - 构建时间: 45秒
   - 状态: ☐ [t5] → ☑ [t5]

🚀 可以使用以下命令启动:
   docker-compose up -d

📋 **全部任务完成!**

☑ [t1] 用户模块开发
☑ [t2] 代码审查
☑ [t3] 修复审查问题
☑ [t4] 编写测试用例
☑ [t5] Docker部署配置

✅ 项目整体完成率: 100%''',
        ],
    }

    # 定义Agent执行顺序（基于任务依赖关系）
    agent_execution_order = [
        # 阶段1: 开发者执行t1
        {'agent': 'coder', 'task_id': 't1'},
        # 阶段2: 审查员执行t2（依赖t1）
        {'agent': 'reviewer', 'task_id': 't2'},
        # 阶段3: 开发者执行t3修复（依赖t2）
        {'agent': 'coder', 'task_id': 't3'},
        # 阶段4: 测试工程师执行t4（依赖t3）
        {'agent': 'tester', 'task_id': 't4'},
        # 阶段5: 构建工程师执行t5（依赖t4）
        {'agent': 'builder', 'task_id': 't5'},
    ]

    # 模拟Agent协作 - 按任务顺序执行
    agents = project.get('agents', [])

    # 创建Agent映射
    agent_map = {a['id']: a for a in agents}

    for exec_item in agent_execution_order:
        agent_id = exec_item['agent']
        task_id = exec_item['task_id']
        agent = agent_map.get(agent_id)

        if not agent:
            continue

        # 获取该Agent的消息（包含任务执行）
        messages = agent_responses.get(agent_id, [f'{agent["name"]} 正在处理...'])

        # 如果是修复任务(t3)，使用t3特定的消息
        if task_id == 't3':
            messages = agent_responses.get('coder_fix', [f'{agent["name"]} 正在修复审查问题...'])

        # 更新任务状态为进行中
        for t in project['tasks']:
            if t['id'] == task_id:
                t['status'] = 'in_progress'
                t['executed_by'] = agent_id
                break

        agent['status'] = 'working'

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
                'task_id': task_id,  # 关联任务ID
            }
            project['messages'].append(msg)

            # 更新Agent进度
            agent['progress'] = progress

        # 任务完成
        for t in project['tasks']:
            if t['id'] == task_id:
                t['status'] = 'completed'
                t['completed_by'] = agent_id
                break

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
