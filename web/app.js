/**
 * 多Agent协作系统 - 前端逻辑
 * 处理消息渲染、用户交互、事件响应
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
    loadingOverlay: document.getElementById('loadingOverlay'),
    notificationContainer: document.getElementById('notificationContainer'),
};

// ===================================
// 工具函数
// ===================================

/**
 * 格式化时间
 */
function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

/**
 * 转义HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 滚动到底部
 */
function scrollToBottom() {
    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
}

/**
 * 显示通知
 */
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

/**
 * 更新状态指示器
 */
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

/**
 * 创建消息元素
 */
function createMessageElement(message) {
    const { type, agent, agentName, agentIcon, agentColor, timestamp, data } = message;

    const messageEl = document.createElement('div');
    messageEl.className = `message ${type === 'user_message' ? 'user' : ''}`;
    messageEl.dataset.agent = agent;

    // 头像背景色
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

/**
 * 格式化消息内容
 */
function formatMessageBody(data) {
    if (!data) return '';

    // 如果是字符串
    if (typeof data === 'string') {
        return `<p>${escapeHtml(data)}</p>`;
    }

    // 如果是对象
    let html = '';

    if (data.message) {
        html += `<p>${escapeHtml(data.message)}</p>`;
    }

    // 状态徽章
    if (data.status) {
        const statusClass = getStatusClass(data.status);
        html += `<span class="status-badge ${statusClass}">${escapeHtml(data.status)}</span>`;
    }

    // 进度条
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

    // 决策结果
    if (data.decision) {
        const decisionIcon = getDecisionIcon(data.decision);
        const decisionClass = getStatusClass(data.decision.toLowerCase());
        html += `
            <span class="status-badge ${decisionClass}">
                ${decisionIcon} ${escapeHtml(data.decision)}
            </span>
        `;
    }

    // 分数/通过率
    if (data.score !== undefined) {
        html += `<p><strong>评分:</strong> ${data.score}/10</p>`;
    }

    if (data.pass_rate !== undefined) {
        html += `<p><strong>通过率:</strong> ${data.pass_rate}%</p>`;
    }

    // 重试信息
    if (data.retry_count !== undefined) {
        html += `<p><strong>重试次数:</strong> ${data.retry_count}</p>`;
    }

    // 问题列表
    if (data.issues && Array.isArray(data.issues)) {
        html += '<p><strong>问题:</strong></p><ul>';
        data.issues.forEach(issue => {
            html += `<li>${escapeHtml(issue)}</li>`;
        });
        html += '</ul>';
    }

    // 代码片段
    if (data.code) {
        const code = escapeHtml(data.code);
        html += `<pre><code>${code}</code></pre>`;
    }

    return html || `<p>${JSON.stringify(data, null, 2)}</p>`;
}

/**
 * 获取状态对应的CSS类
 */
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

/**
 * 获取决策图标
 */
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
// 公开API (供Python调用)
// ===================================

/**
 * 添加Agent消息
 */
window.addMessage = function(message) {
    // 移除欢迎消息
    const welcome = elements.chatContainer.querySelector('.welcome-message');
    if (welcome) {
        welcome.remove();
    }

    const messageEl = createMessageElement(message);
    elements.chatContainer.appendChild(messageEl);
    scrollToBottom();

    // 更新状态
    if (message.agent && message.agent !== 'system') {
        elements.agentStatus.textContent = message.agentName || message.agent;
    }

    // 检查特殊事件
    if (message.type === 'workflow_complete') {
        updateStatus('completed');
        state.isRunning = false;
        elements.sendButton.disabled = false;
        elements.loadingOverlay.classList.remove('active');
        showNotification('工作流执行完成！', 'success');
    }

    if (message.type === 'error') {
        updateStatus('error');
        showNotification(message.data?.message || '发生错误', 'error');
    }
};

/**
 * 添加用户消息
 */
window.addUserMessage = function(message) {
    // 移除欢迎消息
    const welcome = elements.chatContainer.querySelector('.welcome-message');
    if (welcome) {
        welcome.remove();
    }

    const messageEl = createMessageElement(message);
    elements.chatContainer.appendChild(messageEl);
    scrollToBottom();
};

/**
 * 更新进度
 */
window.updateProgress = function(progress) {
    if (progress.current !== undefined) {
        // 可以在这里更新进度显示
    }
};

/**
 * 更新统计数据
 */
window.updateStats = function(stats) {
    if (stats.passRate !== undefined) {
        elements.passRate.textContent = `${stats.passRate}%`;
    }
    if (stats.agentStatus) {
        elements.agentStatus.textContent = stats.agentStatus;
    }
};

// ===================================
// 用户交互
// ===================================

/**
 * 发送任务
 */
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
    state.agentStatus = 'running';
    updateStatus('running');
    elements.sendButton.disabled = true;
    elements.loadingOverlay.classList.add('active');

    // 添加用户消息
    window.addUserMessage({
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

    // 尝试调用Python后端
    try {
        // 通过 expose 的函数调用
        if (window.start_workflow) {
            await window.start_workflow(taskText);
        } else if (window.pywebview && window.pywebview.api) {
            await window.pywebview.api.startWorkflow(taskText);
        } else {
            // 模拟执行
            simulateWorkflow(taskText);
        }
    } catch (error) {
        console.error('启动工作流失败:', error);
        showNotification('启动失败: ' + error.message, 'error');
        state.isRunning = false;
        updateStatus('error');
        elements.sendButton.disabled = false;
        elements.loadingOverlay.classList.remove('active');
    }
}

/**
 * 模拟工作流执行（用于测试）
 */
async function simulateWorkflow(taskText) {
    const steps = [
        { type: 'workflow_start', agent: 'system', agentName: 'System', agentIcon: '🚀', delay: 500 },
        { type: 'task_decompose', agent: 'orchestrator', agentName: 'Orchestrator', agentIcon: '🎯', delay: 1500 },
        { type: 'subtask_start', agent: 'orchestrator', agentName: 'Orchestrator', agentIcon: '🎯', delay: 800 },
        { type: 'coding_start', agent: 'coder', agentName: 'Coder', agentIcon: '💻', delay: 2000 },
        { type: 'coding_complete', agent: 'coder', agentName: 'Coder', agentIcon: '💻', delay: 1000 },
        { type: 'review_start', agent: 'reviewer', agentName: 'Reviewer', agentIcon: '🔍', delay: 1200 },
        { type: 'review_result', agent: 'reviewer', agentName: 'Reviewer', agentIcon: '🔍', delay: 800 },
        { type: 'test_start', agent: 'tester', agentName: 'Tester', agentIcon: '🧪', delay: 1000 },
        { type: 'test_result', agent: 'tester', agentName: 'Tester', agentIcon: '🧪', delay: 800 },
        { type: 'decision', agent: 'orchestrator', agentName: 'Orchestrator', agentIcon: '🎯', delay: 500 },
        { type: 'workflow_complete', agent: 'system', agentName: 'System', agentIcon: '🎉', delay: 300 },
    ];

    const messages = [
        { message: '开始处理您的请求...' },
        { message: '正在分解任务为子任务...', agent: 'orchestrator' },
        { message: '开始处理子任务...', agent: 'orchestrator' },
        { message: 'Coder 正在编写代码...', agent: 'coder' },
        { message: '代码生成完成！', agent: 'coder', status: 'success' },
        { message: 'Reviewer 正在审查代码...', agent: 'reviewer' },
        { message: '审查完成，未发现问题', agent: 'reviewer', status: 'success', score: 9 },
        { message: 'Tester 正在运行测试...', agent: 'tester' },
        { message: '测试完成，通过率: 95%', agent: 'tester', status: 'success', pass_rate: 95 },
        { message: '决策: 任务完成 ✅', agent: 'orchestrator', decision: 'COMPLETE', reason: '测试通过率 >= 80% 且无阻塞问题' },
        { message: '🎉 工作流执行完成！项目已保存', agent: 'system' },
    ];

    for (let i = 0; i < steps.length; i++) {
        await new Promise(resolve => setTimeout(resolve, steps[i].delay));
        window.addMessage({
            type: steps[i].type,
            agent: steps[i].agent,
            agentName: steps[i].agentName,
            agentIcon: steps[i].agentIcon,
            timestamp: new Date().toISOString(),
            data: messages[i]
        });
    }
}

// ===================================
// 事件监听
// ===================================

// 发送按钮
elements.sendButton.addEventListener('click', sendTask);

// 输入框 - Enter发送
elements.taskInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendTask();
    }
});

// 自动调整输入框高度
elements.taskInput.addEventListener('input', () => {
    elements.taskInput.style.height = 'auto';
    elements.taskInput.style.height = Math.min(elements.taskInput.scrollHeight, 150) + 'px';
});

// ===================================
// 初始化
// ===================================
console.log('多Agent协作系统 UI 已加载');
