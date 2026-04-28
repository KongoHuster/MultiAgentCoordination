/**
 * 多Agent协作系统 - 前端逻辑
 * 使用轮询/SSE获取后端消息
 */

// ===================================
// 全局状态
// ===================================
const state = {
    isRunning: false,
    tasks: [],
    currentTaskIndex: 0,
    agentStatus: 'idle',
    passRate: null,
    lastMessageCount: 0,
    useSSE: true,
    taskProgress: { current: 0, total: 0, currentTask: '' },
};

// ===================================
// DOM 元素
// ===================================
const elements = {
    chatContainer: document.getElementById('chatContainer'),
    taskInput: document.getElementById('taskInput'),
    sendButton: document.getElementById('sendButton'),
    statusIndicator: document.getElementById('statusIndicator'),
    taskList: document.getElementById('taskList'),
    agentStatus: document.getElementById('agentStatus'),
    passRate: document.getElementById('passRate'),
    notificationContainer: document.getElementById('notificationContainer'),
    pauseButton: document.getElementById('pauseButton'),
    resumeButton: document.getElementById('resumeButton'),
};

// ===================================
// 工具函数
// ===================================

function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function scrollToBottom() {
    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
}

function showNotification(message, type = 'info', duration = 3000) {
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };

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
    }, duration);
}

function updateStatus(status) {
    const statusText = {
        ready: '就绪',
        running: '运行中',
        completed: '完成',
        error: '错误'
    };

    elements.statusIndicator.className = `status-indicator ${status}`;
    elements.statusIndicator.querySelector('.status-text').textContent =
        statusText[status] || status;
}

// ===================================
// 消息渲染
// ===================================

function createMessageElement(message) {
    const { type, agent, agentName, agentIcon, agentColor, timestamp, data } = message;

    const messageEl = document.createElement('div');
    messageEl.className = `message ${type === 'user_message' ? 'user' : ''}`;
    messageEl.dataset.agent = agent;

    const avatarBg = agentColor || '#6b7280';

    messageEl.innerHTML = `
        <div class="message-avatar" style="background: ${avatarBg}">
            ${agentIcon || '❓'}
        </div>
        <div class="message-content">
            <div class="message-header">
                <span class="message-agent-name">${escapeHtml(agentName || agent)}</span>
                <span class="message-time">${timestamp ? formatTime(timestamp) : ''}</span>
            </div>
            <div class="message-body">
                ${formatMessageBody(data)}
            </div>
        </div>
    `;

    return messageEl;
}

function formatMessageBody(data) {
    if (!data) return '';

    if (typeof data === 'string') {
        return `<p>${escapeHtml(data)}</p>`;
    }

    let html = '';

    if (data.message) {
        html += `<p>${escapeHtml(data.message)}</p>`;
    }

    if (data.status) {
        const statusClass = getStatusClass(data.status);
        html += `<span class="status-badge ${statusClass}">${escapeHtml(data.status)}</span>`;
    }

    if (data.current !== undefined && data.total !== undefined) {
        const percent = Math.round((data.current / data.total) * 100);
        html += `
            <div class="progress-container">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${percent}%"></div>
                </div>
                <span class="progress-text">${data.current} / ${data.total}</span>
            </div>
        `;
    }

    if (data.decision) {
        const decisionIcon = getDecisionIcon(data.decision);
        const decisionClass = getStatusClass(data.decision.toLowerCase());
        html += `
            <span class="status-badge ${decisionClass}">
                ${decisionIcon} ${escapeHtml(data.decision)}
            </span>
        `;
    }

    if (data.score !== undefined) {
        html += `<p><strong>评分:</strong> ${data.score}/10</p>`;
    }

    if (data.pass_rate !== undefined) {
        html += `<p><strong>通过率:</strong> ${data.pass_rate}%</p>`;
    }

    if (data.retry_count !== undefined) {
        html += `<p><strong>重试次数:</strong> ${data.retry_count}</p>`;
    }

    if (data.issues && Array.isArray(data.issues)) {
        html += '<p><strong>问题:</strong></p><ul>';
        data.issues.forEach(issue => {
            html += `<li>${escapeHtml(issue)}</li>`;
        });
        html += '</ul>';
    }

    if (data.code) {
        const code = escapeHtml(data.code);
        html += `<pre><code>${code}</code></pre>`;
    }

    // 处理 result 对象
    if (data.status && data.summary) {
        html += `<p><strong>总结:</strong> ${escapeHtml(data.summary)}</p>`;
    }

    return html || `<p>${JSON.stringify(data, null, 2)}</p>`;
}

function getStatusClass(status) {
    const statusMap = {
        'complete': 'success',
        'success': 'success',
        'passed': 'success',
        'retry': 'warning',
        'warning': 'warning',
        'error': 'error',
        'failed': 'error',
        'blocker': 'error',
        'skip': 'info',
        'skipped': 'info',
        'next': 'info',
        'pending': 'info',
        'running': 'info',
        'in_progress': 'info',
    };
    return statusMap[status?.toLowerCase()] || 'info';
}

function getDecisionIcon(decision) {
    const iconMap = {
        'COMPLETE': '✅',
        'RETRY': '🔄',
        'NEXT': '➡️',
        'SKIP': '⏭️',
    };
    return iconMap[decision] || '🎯';
}

// ===================================
// 消息处理
// ===================================

function addMessage(message) {
    // 移除欢迎消息
    const welcome = elements.chatContainer.querySelector('.welcome-message');
    if (welcome) {
        welcome.remove();
    }

    // 更新任务进度
    if (message.type === 'subtask_start' && message.data) {
        state.taskProgress.current = message.data.task_index || 0;
        state.taskProgress.total = message.data.total_tasks || 0;
        state.taskProgress.currentTask = message.data.task_description || '';
        updateTaskProgress();
    }

    if (message.type === 'workflow_complete') {
        state.taskProgress.current = state.taskProgress.total;
        updateTaskProgress();
    }

    // 处理流式更新 - 追加到上一个消息
    if (message.type === 'stream_update') {
        const lastMessage = elements.chatContainer.lastElementChild;
        if (lastMessage && (lastMessage.classList.contains('streaming') || lastMessage.dataset.agent === 'coder' || lastMessage.dataset.agent === 'reviewer' || lastMessage.dataset.agent === 'tester')) {
            const body = lastMessage.querySelector('.message-body');
            if (body && message.data && message.data.content) {
                // 直接显示完整内容，包含代码格式
                body.innerHTML = `<pre><code>${escapeHtml(message.data.content)}</code></pre>`;
                scrollToBottom();
                return;
            }
        }
    }

    const messageEl = createMessageElement(message);

    // 如果是流式阶段的消息，添加标记
    if (message.type === 'coding_start' || message.type === 'review_start' || message.type === 'test_start') {
        messageEl.classList.add('streaming');
    }

    elements.chatContainer.appendChild(messageEl);
    scrollToBottom();

    // 更新Agent状态
    if (message.agent && message.agent !== 'system') {
        elements.agentStatus.textContent = message.agentName || message.agent;
    }

    // 更新统计数据
    if (message.data) {
        if (message.data.pass_rate !== undefined) {
            elements.passRate.textContent = `${message.data.pass_rate}%`;
        }
    }

    // 检查工作流完成
    if (message.type === 'workflow_complete') {
        updateStatus('completed');
        state.isRunning = false;
        elements.sendButton.disabled = false;
        elements.pauseButton.style.display = 'none';
        elements.resumeButton.style.display = 'none';
        showNotification('工作流执行完成！', 'success');
    }

    if (message.type === 'workflow_paused') {
        elements.pauseButton.style.display = 'none';
        elements.resumeButton.style.display = 'inline-flex';
        showNotification('任务已暂停', 'info');
    }

    if (message.type === 'workflow_resumed') {
        elements.pauseButton.style.display = 'inline-flex';
        elements.resumeButton.style.display = 'none';
        showNotification('任务已恢复', 'success');
    }

    if (message.type === 'error') {
        updateStatus('error');
        showNotification(message.data?.message || '发生错误', 'error');
        state.isRunning = false;
        elements.sendButton.disabled = false;
    }
}

function updateTaskProgress() {
    // 更新侧边栏任务列表
    const taskList = elements.taskList;
    taskList.innerHTML = '';

    if (state.taskProgress.total === 0) {
        taskList.innerHTML = `
            <div class="task-item task-empty">
                <span class="task-icon">📋</span>
                <span class="task-text">暂无任务</span>
            </div>
        `;
        return;
    }

    for (let i = 1; i <= state.taskProgress.total; i++) {
        const isActive = i === state.taskProgress.current;
        const isCompleted = i < state.taskProgress.current;
        const statusIcon = isCompleted ? '✅' : (isActive ? '🔄' : '⏳');
        const statusClass = isActive ? 'active' : '';
        const taskText = i === state.taskProgress.current && state.taskProgress.currentTask
            ? state.taskProgress.currentTask
            : `任务 ${i}/${state.taskProgress.total}`;

        const taskItem = document.createElement('div');
        taskItem.className = `task-item ${statusClass}`;
        taskItem.innerHTML = `
            <span class="task-icon">${statusIcon}</span>
            <span class="task-text">${escapeHtml(taskText)}</span>
        `;
        taskList.appendChild(taskItem);
    }
}

// ===================================
// 后端通信
// ===================================

let eventSource = null;

function startPolling() {
    // 使用轮询获取消息
    const poll = async () => {
        if (!state.isRunning) return;

        try {
            const response = await fetch('/api/messages');
            const data = await response.json();

            // 检查新消息
            if (data.messages.length > state.lastMessageCount) {
                for (let i = state.lastMessageCount; i < data.messages.length; i++) {
                    addMessage(data.messages[i]);
                }
                state.lastMessageCount = data.messages.length;
            }

            // 检查是否还在运行
            if (!data.is_running && state.isRunning) {
                state.isRunning = false;
                elements.sendButton.disabled = false;
            }
        } catch (error) {
            console.error('轮询失败:', error);
        }

        if (state.isRunning) {
            setTimeout(poll, 1000);
        }
    };

    poll();
}

function startSSE() {
    // 使用 Server-Sent Events
    if (eventSource) {
        eventSource.close();
    }

    eventSource = new EventSource('/api/messages/stream');

    eventSource.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);

            if (message.type === 'done') {
                eventSource.close();
                state.isRunning = false;
                elements.sendButton.disabled = false;
                elements.loadingOverlay.classList.remove('active');
                return;
            }

            addMessage(message);
        } catch (error) {
            console.error('解析消息失败:', error);
        }
    };

    eventSource.onerror = (error) => {
        console.error('SSE错误，切换到轮询模式', error);
        eventSource.close();
        state.useSSE = false;
        startPolling();
    };
}

// ===================================
// 用户交互
// ===================================

async function sendTask() {
    const taskText = elements.taskInput.value.trim();

    if (!taskText) {
        showNotification('请输入任务描述', 'warning');
        return;
    }

    if (state.isRunning) {
        showNotification('任务正在执行中...', 'warning');
        return;
    }

    // 开始执行
    state.isRunning = true;
    state.lastMessageCount = 0;
    state.agentStatus = 'running';
    updateStatus('running');
    elements.sendButton.disabled = true;
    elements.pauseButton.style.display = 'inline-flex';
    elements.resumeButton.style.display = 'none';

    // 添加用户消息
    addMessage({
        type: 'user_message',
        agent: 'user',
        agentName: 'You',
        agentIcon: '👤',
        agentColor: '#22c55e',
        timestamp: new Date().toISOString(),
        data: { message: taskText }
    });

    // 清空输入框
    elements.taskInput.value = '';

    // 调用后端API
    try {
        const response = await fetch('/api/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ task: taskText })
        });

        const result = await response.json();

        if (result.error) {
            showNotification(result.error, 'error');
            state.isRunning = false;
            elements.sendButton.disabled = false;
            elements.loadingOverlay.classList.remove('active');
            return;
        }

        // 开始接收消息
        if (state.useSSE) {
            startSSE();
        } else {
            startPolling();
        }

    } catch (error) {
        console.error('启动工作流失败:', error);
        showNotification('启动失败: ' + error.message, 'error');
        state.isRunning = false;
        updateStatus('error');
        elements.sendButton.disabled = false;
    }
}

// ===================================
// 事件监听
// ===================================

elements.sendButton.addEventListener('click', sendTask);

// 暂停按钮
elements.pauseButton.addEventListener('click', async () => {
    try {
        const response = await fetch('/api/pause', { method: 'POST' });
        const result = await response.json();
        if (result.status === 'paused') {
            elements.pauseButton.style.display = 'none';
            elements.resumeButton.style.display = 'inline-flex';
        }
    } catch (error) {
        showNotification('暂停失败', 'error');
    }
});

// 继续按钮
elements.resumeButton.addEventListener('click', async () => {
    try {
        const response = await fetch('/api/resume', { method: 'POST' });
        const result = await response.json();
        if (result.status === 'resumed') {
            elements.pauseButton.style.display = 'inline-flex';
            elements.resumeButton.style.display = 'none';
        }
    } catch (error) {
        showNotification('恢复失败', 'error');
    }
});

elements.taskInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendTask();
    }
});

elements.taskInput.addEventListener('input', () => {
    elements.taskInput.style.height = 'auto';
    elements.taskInput.style.height = Math.min(elements.taskInput.scrollHeight, 150) + 'px';
});

// ===================================
// 初始化
// ===================================

// 清空之前的消息
fetch('/api/clear', { method: 'POST' }).catch(() => {});

console.log('多Agent协作系统 UI 已加载');
