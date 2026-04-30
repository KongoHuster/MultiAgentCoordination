/**
 * MultiAgent协作系统 - QQ风格前端逻辑
 * 多项目支持、多角色协作、实时进度、打断功能
 */

// ===================================
// 全局状态
// ===================================
const state = {
    projects: [],              // 项目列表
    currentProjectId: null,    // 当前项目ID
    currentProject: null,      // 当前项目对象
    agents: [],                // 当前项目Agent列表
    messages: [],              // 当前项目消息
    unreadCount: {},           // 未读消息数
    isRunning: false,          // 是否运行中
    isInterrupt: false,        // 是否打断模式
    eventSource: null,         // SSE连接
};

// ===================================
// DOM元素
// ===================================
const elements = {};

// ===================================
// 初始化
// ===================================
document.addEventListener('DOMContentLoaded', async () => {
    initElements();
    initEventListeners();
    await loadProjects();
    console.log('MultiAgent协作系统已初始化');
});

function initElements() {
    // 侧边栏
    elements.sidebar = document.getElementById('sidebar');
    elements.projectList = document.getElementById('projectList');
    elements.newProjectBtn = document.getElementById('newProjectBtn');
    elements.projectSearch = document.getElementById('projectSearch');
    elements.onlineCount = document.getElementById('onlineCount');
    elements.waitingCount = document.getElementById('waitingCount');
    elements.completedCount = document.getElementById('completedCount');

    // 主区域
    elements.mainContent = document.getElementById('mainContent');
    elements.welcomePanel = document.getElementById('welcomePanel');
    elements.welcomeNewProject = document.getElementById('welcomeNewProject');
    elements.chatPanel = document.getElementById('chatPanel');

    // 聊天头部
    elements.currentProjectIcon = document.getElementById('currentProjectIcon');
    elements.currentProjectName = document.getElementById('currentProjectName');
    elements.currentProjectStatus = document.getElementById('currentProjectStatus');
    elements.projectSettingsBtn = document.getElementById('projectSettingsBtn');
    elements.toggleAgentPanel = document.getElementById('toggleAgentPanel');

    // Agent状态栏
    elements.agentStatusBar = document.getElementById('agentStatusBar');

    // 消息容器
    elements.messageContainer = document.getElementById('messageContainer');

    // 输入区域
    elements.interruptHint = document.getElementById('interruptHint');
    elements.messageInput = document.getElementById('messageInput');
    elements.sendBtn = document.getElementById('sendBtn');

    // Agent面板
    elements.agentPanel = document.getElementById('agentPanel');
    elements.closeAgentPanel = document.getElementById('closeAgentPanel');
    elements.agentList = document.getElementById('agentList');

    // 模态框
    elements.newProjectModal = document.getElementById('newProjectModal');
    elements.closeNewProjectModal = document.getElementById('closeNewProjectModal');
    elements.projectNameInput = document.getElementById('projectNameInput');
    elements.agentSelector = document.getElementById('agentSelector');
    elements.confirmNewProject = document.getElementById('confirmNewProject');
    elements.cancelNewProject = document.getElementById('cancelNewProject');

    elements.deleteProjectModal = document.getElementById('deleteProjectModal');
    elements.deleteProjectName = document.getElementById('deleteProjectName');
    elements.confirmDeleteProject = document.getElementById('confirmDeleteProject');
    elements.cancelDeleteProject = document.getElementById('cancelDeleteProject');

    // 通知容器
    elements.notificationContainer = document.getElementById('notificationContainer');
}

function initEventListeners() {
    // 新建项目
    elements.newProjectBtn.addEventListener('click', openNewProjectModal);
    elements.welcomeNewProject.addEventListener('click', openNewProjectModal);
    elements.closeNewProjectModal.addEventListener('click', closeNewProjectModal);
    elements.cancelNewProject.addEventListener('click', closeNewProjectModal);
    elements.confirmNewProject.addEventListener('click', createProject);

    // 删除项目
    elements.cancelDeleteProject.addEventListener('click', closeDeleteProjectModal);
    elements.confirmDeleteProject.addEventListener('click', confirmDeleteProject);

    // 发送消息
    elements.sendBtn.addEventListener('click', sendMessage);
    elements.messageInput.addEventListener('keydown', handleInputKeydown);
    elements.messageInput.addEventListener('input', autoResizeInput);

    // Agent面板
    elements.toggleAgentPanel.addEventListener('click', toggleAgentPanel);
    elements.closeAgentPanel.addEventListener('click', () => elements.agentPanel.classList.remove('open'));

    // 搜索项目
    elements.projectSearch.addEventListener('input', filterProjects);
}

// ===================================
// 项目管理
// ===================================

async function loadProjects() {
    try {
        const response = await fetch('/api/projects');
        const data = await response.json();
        state.projects = data.projects || [];

        // 如果API返回空，使用模拟数据
        if (state.projects.length === 0) {
            console.log('API无项目，使用模拟数据');
            state.projects = getMockProjects();
        }

        renderProjectList();
        updateStats();
    } catch (error) {
        console.error('加载项目失败:', error);
        // API失败时使用模拟数据
        state.projects = getMockProjects();
        renderProjectList();
        updateStats();
    }
}

function getMockProjects() {
    return [
        {
            id: 'project-1',
            name: '网站开发项目',
            icon: '🌐',
            status: 'running',
            agents: [
                { id: 'orchestrator', name: '项目经理', icon: '🎯', status: 'working', progress: 65 },
                { id: 'coder', name: '开发者', icon: '💻', status: 'working', progress: 45 },
                { id: 'reviewer', name: '审查员', icon: '🔍', status: 'idle', progress: 0 },
                { id: 'tester', name: '测试员', icon: '🧪', status: 'idle', progress: 0 },
            ],
            messages: [
                {
                    id: 'msg-1',
                    agent: 'orchestrator',
                    agentName: '项目经理',
                    agentIcon: '🎯',
                    agentColor: '#8b5cf6',
                    content: '项目已启动，正在分析需求...',
                    timestamp: new Date(Date.now() - 300000).toISOString(),
                },
                {
                    id: 'msg-2',
                    agent: 'coder',
                    agentName: '开发者',
                    agentIcon: '💻',
                    agentColor: '#3b82f6',
                    content: '开始编写前端页面代码，预计完成60%',
                    timestamp: new Date(Date.now() - 180000).toISOString(),
                },
            ],
        },
        {
            id: 'project-2',
            name: 'API接口开发',
            icon: '🔌',
            status: 'idle',
            agents: [
                { id: 'orchestrator', name: '项目经理', icon: '🎯', status: 'idle', progress: 0 },
                { id: 'coder', name: '开发者', icon: '💻', status: 'idle', progress: 0 },
            ],
            messages: [],
        },
    ];
}

function renderProjectList() {
    elements.projectList.innerHTML = '';

    if (state.projects.length === 0) {
        elements.projectList.innerHTML = `
            <div class="empty-projects">
                <p style="color: var(--sidebar-text); text-align: center; padding: 20px; font-size: 13px;">
                    暂无项目<br>点击上方 + 创建新项目
                </p>
            </div>
        `;
        return;
    }

    state.projects.forEach(project => {
        const isActive = project.id === state.currentProjectId;
        const unread = state.unreadCount[project.id] || 0;
        const statusClass = getStatusClass(project.status);

        const projectEl = document.createElement('div');
        projectEl.className = `project-item ${isActive ? 'active' : ''}`;
        projectEl.dataset.projectId = project.id;

        projectEl.innerHTML = `
            <span class="project-icon">${project.icon || '📁'}</span>
            <div class="project-info">
                <span class="project-name">${escapeHtml(project.name)}</span>
                <span class="project-meta">${project.agents?.length || 0} 个角色</span>
            </div>
            <span class="status-dot ${statusClass}"></span>
            ${unread > 0 ? `<span class="unread-badge">${unread}</span>` : ''}
            <button class="delete-project" title="删除项目">×</button>
        `;

        projectEl.addEventListener('click', (e) => {
            if (!e.target.classList.contains('delete-project')) {
                switchProject(project.id);
            }
        });

        const deleteBtn = projectEl.querySelector('.delete-project');
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            openDeleteProjectModal(project);
        });

        elements.projectList.appendChild(projectEl);
    });
}

function switchProject(projectId) {
    if (state.currentProjectId === projectId) return;

    state.currentProjectId = projectId;
    state.currentProject = state.projects.find(p => p.id === projectId);
    state.agents = state.currentProject?.agents || [];
    state.messages = state.currentProject?.messages || [];

    // 清除未读
    state.unreadCount[projectId] = 0;

    // 更新UI
    renderProjectList();
    showChatPanel();
    renderChatHeader();
    renderAgentStatusBar();
    renderMessages();
}

function showChatPanel() {
    elements.welcomePanel.style.display = 'none';
    elements.chatPanel.style.display = 'flex';
}

function showWelcomePanel() {
    elements.chatPanel.style.display = 'none';
    elements.welcomePanel.style.display = 'flex';
}

// ===================================
// 项目CRUD
// ===================================

function openNewProjectModal() {
    elements.newProjectModal.style.display = 'flex';
    elements.projectNameInput.value = '';
    elements.projectNameInput.focus();

    // 默认选中常用角色
    const checkboxes = elements.agentSelector.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(cb => {
        if (['orchestrator', 'coder', 'reviewer', 'tester'].includes(cb.value)) {
            cb.checked = true;
        } else {
            cb.checked = false;
        }
    });
}

function closeNewProjectModal() {
    elements.newProjectModal.style.display = 'none';
}

async function createProject() {
    const name = elements.projectNameInput.value.trim();
    if (!name) {
        showNotification('请输入项目名称', 'warning');
        return;
    }

    const selectedAgents = [];
    const checkboxes = elements.agentSelector.querySelectorAll('input[type="checkbox"]:checked');
    checkboxes.forEach(cb => {
        selectedAgents.push(cb.value);
    });

    if (selectedAgents.length === 0) {
        showNotification('请至少选择一个角色', 'warning');
        return;
    }

    const projectData = {
        name,
        agents: selectedAgents,
    };

    try {
        const response = await fetch('/api/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(projectData),
        });
        const result = await response.json();

        if (result.success) {
            const newProject = {
                id: result.project.id,
                name: result.project.name,
                icon: result.project.icon || '📁',
                status: 'idle',
                agents: result.project.agents || [],
                messages: [],
            };
            state.projects.push(newProject);
            renderProjectList();
            switchProject(newProject.id);
            closeNewProjectModal();
            showNotification(`项目 "${name}" 创建成功`, 'success');
        }
    } catch (error) {
        // 模拟创建（API不可用时）
        const newProject = {
            id: 'project-' + Date.now(),
            name,
            icon: getProjectIcon(name),
            status: 'idle',
            agents: getDefaultAgents(selectedAgents),
            messages: [],
        };
        state.projects.push(newProject);
        renderProjectList();
        switchProject(newProject.id);
        closeNewProjectModal();
        showNotification(`项目 "${name}" 创建成功`, 'success');
    }
}

function getProjectIcon(name) {
    const icons = ['📁', '🌐', '🔌', '📱', '💻', '🎯', '🚀', '⚡'];
    const index = name.length % icons.length;
    return icons[index];
}

function getDefaultAgents(agentTypes) {
    const agentConfigs = {
        orchestrator: { id: 'orchestrator', name: '项目经理', icon: '🎯', status: 'idle', progress: 0 },
        coder: { id: 'coder', name: '开发者', icon: '💻', status: 'idle', progress: 0 },
        reviewer: { id: 'reviewer', name: '审查员', icon: '🔍', status: 'idle', progress: 0 },
        tester: { id: 'tester', name: '测试员', icon: '🧪', status: 'idle', progress: 0 },
        builder: { id: 'builder', name: '构建师', icon: '🔧', status: 'idle', progress: 0 },
    };

    return agentTypes.map(type => agentConfigs[type] || { id: type, name: type, icon: '👤', status: 'idle', progress: 0 });
}

function openDeleteProjectModal(project) {
    elements.deleteProjectModal.style.display = 'flex';
    elements.deleteProjectName.textContent = project.name;
    elements.confirmDeleteProject.dataset.projectId = project.id;
}

function closeDeleteProjectModal() {
    elements.deleteProjectModal.style.display = 'none';
}

async function confirmDeleteProject() {
    const projectId = elements.confirmDeleteProject.dataset.projectId;

    try {
        await fetch(`/api/projects/${projectId}`, { method: 'DELETE' });
    } catch (error) {
        // 忽略API错误
    }

    state.projects = state.projects.filter(p => p.id !== projectId);
    delete state.unreadCount[projectId];

    if (state.currentProjectId === projectId) {
        state.currentProjectId = null;
        state.currentProject = null;
        showWelcomePanel();
    }

    renderProjectList();
    closeDeleteProjectModal();
    showNotification('项目已删除', 'success');
}

function filterProjects() {
    const query = elements.projectSearch.value.toLowerCase();
    const items = elements.projectList.querySelectorAll('.project-item');

    items.forEach(item => {
        const name = item.querySelector('.project-name').textContent.toLowerCase();
        item.style.display = name.includes(query) ? 'flex' : 'none';
    });
}

// ===================================
// 聊天界面
// ===================================

function renderChatHeader() {
    if (!state.currentProject) return;

    elements.currentProjectIcon.textContent = state.currentProject.icon || '📁';
    elements.currentProjectName.textContent = state.currentProject.name;

    const statusText = getStatusText(state.currentProject.status);
    elements.currentProjectStatus.textContent = statusText;
    elements.currentProjectStatus.className = `project-status ${state.currentProject.status}`;
}

function renderAgentStatusBar() {
    elements.agentStatusBar.innerHTML = '';

    if (!state.agents || state.agents.length === 0) {
        elements.agentStatusBar.innerHTML = '<p style="color: var(--text-muted); font-size: 13px;">暂无角色</p>';
        return;
    }

    state.agents.forEach(agent => {
        const card = document.createElement('div');
        card.className = `agent-status-card ${agent.status === 'working' ? 'active' : ''}`;
        card.dataset.agentId = agent.id;

        card.innerHTML = `
            <div class="agent-avatar" style="background: ${getAgentColor(agent.id)}">${agent.icon || '👤'}</div>
            <div class="agent-details">
                <span class="agent-name">${agent.name || agent.id}</span>
                <span class="agent-status-text">${getAgentStatusText(agent.status)}</span>
                <div class="agent-progress">
                    <div class="agent-progress-fill" style="width: ${agent.progress || 0}%"></div>
                </div>
            </div>
            <span class="agent-status-indicator ${agent.status || 'idle'}"></span>
        `;

        elements.agentStatusBar.appendChild(card);
    });
}

function renderMessages() {
    elements.messageContainer.innerHTML = '';

    if (!state.messages || state.messages.length === 0) {
        elements.messageContainer.innerHTML = `
            <div class="empty-messages">
                <div style="text-align: center; padding: 60px 20px; color: var(--text-muted);">
                    <p style="font-size: 48px; margin-bottom: 16px;">💬</p>
                    <p>开始对话，向Agent发送任务</p>
                </div>
            </div>
        `;
        return;
    }

    state.messages.forEach(message => {
        appendMessage(message);
    });

    scrollToBottom();
}

function appendMessage(message) {
    const isUser = message.agent === 'user';
    const isInterrupt = message.isInterrupt || false;

    const msgEl = document.createElement('div');
    msgEl.className = `message ${isUser ? 'user' : ''} ${isInterrupt ? 'interrupt' : ''}`;
    msgEl.dataset.messageId = message.id || Date.now();

    const avatarColor = isUser ? 'var(--agent-user)' : getAgentColor(message.agent);
    const avatarIcon = message.agentIcon || (isUser ? '👤' : '🤖');

    msgEl.innerHTML = `
        <div class="message-avatar" style="background: ${avatarColor}">${avatarIcon}</div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-sender">${escapeHtml(message.agentName || (isUser ? '我' : message.agent))}</span>
                <span class="message-time">${message.timestamp ? formatTime(message.timestamp) : ''}</span>
            </div>
            <div class="message-bubble">${escapeHtml(message.content)}</div>
            ${message.progress !== undefined ? `
                <div class="message-progress">
                    <div class="message-progress-bar">
                        <div class="message-progress-fill" style="width: ${message.progress}%"></div>
                    </div>
                    <span class="message-progress-text">${message.progress}%</span>
                </div>
            ` : ''}
        </div>
    `;

    elements.messageContainer.appendChild(msgEl);
    scrollToBottom();
}

// ===================================
// 消息发送
// ===================================

async function sendMessage() {
    const content = elements.messageInput.value.trim();
    if (!content) {
        showNotification('请输入消息', 'warning');
        return;
    }

    if (!state.currentProject) {
        showNotification('请先选择或创建项目', 'warning');
        return;
    }

    // 添加用户消息
    const userMessage = {
        id: 'msg-' + Date.now(),
        agent: 'user',
        agentName: '我',
        agentIcon: '👤',
        agentColor: 'var(--agent-user)',
        content,
        timestamp: new Date().toISOString(),
        isInterrupt: state.isInterrupt,
    };

    state.messages.push(userMessage);
    appendMessage(userMessage);
    elements.messageInput.value = '';
    autoResizeInput();

    // 如果是打断模式
    if (state.isInterrupt) {
        state.isInterrupt = false;
        elements.interruptHint.style.display = 'none';
        await handleInterrupt(content);
    } else {
        // 正常发送消息给后端
        await sendToBackend(content);
    }
}

async function handleInterrupt(content) {
    try {
        await fetch(`/api/projects/${state.currentProjectId}/interrupt`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: content }),
        });
    } catch (error) {
        // 模拟打断响应
        simulateInterruptResponse(content);
    }
}

async function sendToBackend(content) {
    try {
        const response = await fetch(`/api/projects/${state.currentProjectId}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content }),
        });

        const result = await response.json();
        if (result.success) {
            state.isRunning = true;
            updateProjectStatus('running');
            connectSSE();
        }
    } catch (error) {
        // 模拟响应
        simulateAgentResponse(content);
    }
}

function simulateAgentResponse(userMessage) {
    // 更新项目状态
    state.currentProject.status = 'running';
    updateProjectStatus('running');

    // 模拟Agent响应
    const agents = ['orchestrator', 'coder', 'reviewer'];
    let delay = 500;

    agents.forEach((agentId, index) => {
        setTimeout(() => {
            const agent = state.agents.find(a => a.id === agentId);
            if (!agent) return;

            // 更新Agent状态
            agent.status = 'working';
            renderAgentStatusBar();

            // 模拟消息
            const responses = {
                orchestrator: `收到任务：${userMessage}。正在分析需求并分配任务...`,
                coder: `开始编写代码，预计需要10分钟完成主要功能模块...`,
                reviewer: `代码审查中，发现1处可优化的地方...`,
            };

            const msg = {
                id: 'msg-' + Date.now() + '-' + index,
                agent: agentId,
                agentName: agent.name,
                agentIcon: agent.icon,
                agentColor: getAgentColor(agentId),
                content: responses[agentId],
                timestamp: new Date().toISOString(),
            };

            state.messages.push(msg);
            appendMessage(msg);

            // 更新进度
            agent.progress = 30 + (index * 20);
            renderAgentStatusBar();

            if (index === agents.length - 1) {
                setTimeout(() => {
                    agent.progress = 100;
                    agent.status = 'completed';
                    renderAgentStatusBar();
                    updateStats();
                    showNotification(`${agent.name} 任务完成`, 'success');
                }, 2000);
            }
        }, delay * (index + 1));
    });
}

function simulateInterruptResponse(interruptMessage) {
    // 停止当前任务
    state.agents.forEach(agent => {
        agent.status = 'idle';
    });
    renderAgentStatusBar();

    // 模拟Agent响应打断
    const orchestrator = state.agents.find(a => a.id === 'orchestrator');
    if (orchestrator) {
        setTimeout(() => {
            const msg = {
                id: 'msg-' + Date.now(),
                agent: 'orchestrator',
                agentName: orchestrator.name,
                agentIcon: orchestrator.icon,
                agentColor: getAgentColor('orchestrator'),
                content: `收到您的打断消息："${interruptMessage}"。正在调整任务优先级...`,
                timestamp: new Date().toISOString(),
            };
            state.messages.push(msg);
            appendMessage(msg);
            showNotification('已响应您的打断请求', 'info');
        }, 500);
    }
}

// ===================================
// SSE实时通信
// ===================================

function connectSSE() {
    if (state.eventSource) {
        state.eventSource.close();
    }

    try {
        state.eventSource = new EventSource(`/api/projects/${state.currentProjectId}/stream`);

        state.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleSSEMessage(data);
            } catch (error) {
                console.error('解析SSE消息失败:', error);
            }
        };

        state.eventSource.onerror = (error) => {
            console.error('SSE连接错误:', error);
            state.eventSource.close();
        };
    } catch (error) {
        console.error('建立SSE连接失败:', error);
    }
}

function handleSSEMessage(data) {
    // 处理有type字段的消息
    if (data.type === 'message' || data.type === 'progress' || data.type === 'done') {
        if (data.type === 'done') {
            state.isRunning = false;
            updateProjectStatus('idle');
            if (state.eventSource) state.eventSource.close();
            showNotification('任务完成', 'success');
            return;
        }
    }

    // 处理包含agent字段的消息（后端发送的消息没有type字段）
    if (data.agent && data.content) {
        const msg = {
            id: data.id || 'msg-' + Date.now(),
            agent: data.agent,
            agentName: data.agentName || data.agent,
            agentIcon: data.agentIcon || '🤖',
            agentColor: data.agentColor || '#6b7280',
            content: data.content,
            timestamp: data.timestamp || new Date().toISOString(),
        };
        state.messages.push(msg);
        appendMessage(msg);

        // 如果是Agent消息，更新Agent状态
        if (data.agent !== 'user') {
            const agent = state.agents.find(a => a.id === data.agent);
            if (agent) {
                agent.status = data.status || 'working';
                agent.progress = data.progress || 50;
                renderAgentStatusBar();
            }
        }
    }

    // 处理进度更新
    if (data.agentId && data.progress !== undefined) {
        const agent = state.agents.find(a => a.id === data.agentId);
        if (agent) {
            agent.progress = data.progress;
            agent.status = data.status || 'working';
            renderAgentStatusBar();
        }
    }
}

// ===================================
// 工具函数
// ===================================

function updateProjectStatus(status) {
    if (state.currentProject) {
        state.currentProject.status = status;
        renderChatHeader();
        renderProjectList();
        updateStats();
    }
}

function updateStats() {
    const totalAgents = state.projects.reduce((sum, p) => sum + (p.agents?.length || 0), 0);
    const onlineAgents = state.projects.reduce((sum, p) => {
        return sum + (p.agents?.filter(a => a.status !== 'idle').length || 0);
    }, 0);
    const waitingAgents = totalAgents - onlineAgents;
    const avgProgress = state.currentProject
        ? Math.round(state.currentProject.agents?.reduce((sum, a) => sum + (a.progress || 0), 0) / (state.currentProject.agents?.length || 1))
        : 0;

    elements.onlineCount.textContent = `${onlineAgents}/${totalAgents}`;
    elements.waitingCount.textContent = waitingAgents;
    elements.completedCount.textContent = `${avgProgress}%`;
}

function getStatusClass(status) {
    const map = { running: '', idle: 'idle', error: 'error' };
    return map[status] || '';
}

function getStatusText(status) {
    const map = { running: '运行中', idle: '就绪', error: '错误' };
    return map[status] || '就绪';
}

function getAgentStatusText(status) {
    const map = {
        idle: '等待中',
        working: '执行中',
        completed: '已完成',
        error: '错误',
    };
    return map[status] || '等待中';
}

function getAgentColor(agentId) {
    const colors = {
        orchestrator: '#8b5cf6',
        coder: '#3b82f6',
        reviewer: '#f59e0b',
        tester: '#10b981',
        builder: '#ec4899',
        user: '#12b7f5',
    };
    return colors[agentId] || '#6b7280';
}

function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
    });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom() {
    elements.messageContainer.scrollTop = elements.messageContainer.scrollHeight;
}

function autoResizeInput() {
    elements.messageInput.style.height = 'auto';
    elements.messageInput.style.height = Math.min(elements.messageInput.scrollHeight, 120) + 'px';
}

function handleInputKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function toggleAgentPanel() {
    elements.agentPanel.classList.toggle('open');
}

// ===================================
// 通知系统
// ===================================

function showNotification(message, type = 'info') {
    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <span class="notification-icon">${icons[type] || icons.info}</span>
        <span class="notification-message">${escapeHtml(message)}</span>
    `;

    elements.notificationContainer.appendChild(notification);

    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ===================================
// 测试接口
// ===================================

// 暴露测试接口到全局
window.testAPI = {
    getState: () => state,
    loadProjects,
    createProject: openNewProjectModal,
    switchProject,
    sendMessage: () => {
        elements.messageInput.value = '测试消息';
        sendMessage();
    },
    simulateInterrupt: () => {
        state.isInterrupt = true;
        elements.interruptHint.style.display = 'flex';
        elements.messageInput.placeholder = '正在打断...';
    },
    getProjects: () => state.projects,
    getCurrentProject: () => state.currentProject,
};
