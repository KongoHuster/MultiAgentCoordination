/**
 * Zustand 状态管理 - 对话 Store
 */

import { create } from 'zustand';
import type {
  Conversation,
  Message,
  AgentEvent,
  Task,
  LogEntry,
  GitStatus,
  GitCommit,
  WSEvent,
  AgentConfig,
  LLMConfig,
} from '@/types';
import { api, WSClient } from '@/services/api';

interface ConversationState {
  // 对话列表
  conversations: Conversation[];
  currentConversation: Conversation | null;

  // 消息
  messages: Message[];

  // 事件
  events: AgentEvent[];

  // 任务
  tasks: Task[];

  // 日志
  logs: LogEntry[];

  // Git 状态
  gitStatus: GitStatus | null;
  gitLog: GitCommit[];

  // WebSocket
  wsClient: WSClient | null;
  isConnected: boolean;

  // 状态
  isLoading: boolean;
  error: string | null;

  // Agent 配置
  agentConfigs: Record<string, AgentConfig>;

  // Actions
  fetchConversations: () => Promise<void>;
  createConversation: (name: string, task?: string) => Promise<Conversation>;
  selectConversation: (id: string) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;

  sendMessage: (content: string) => Promise<void>;
  startWorkflow: (task: string, agentConfigs?: Record<string, LLMConfig>) => Promise<void>;
  pauseWorkflow: () => Promise<void>;
  resumeWorkflow: () => Promise<void>;
  stopWorkflow: () => Promise<void>;

  fetchMessages: () => Promise<void>;
  fetchEvents: () => Promise<void>;
  fetchGitStatus: () => Promise<void>;
  fetchGitLog: () => Promise<void>;

  connectWebSocket: () => Promise<void>;
  disconnectWebSocket: () => void;

  addLog: (entry: Omit<LogEntry, 'id' | 'timestamp'>) => void;
  updateConversationStatus: (status: Conversation['status']) => void;
  handleWSEvent: (event: WSEvent) => void;

  setError: (error: string | null) => void;
  reset: () => void;
}

let logIdCounter = 0;

export const useConversationStore = create<ConversationState>((set, get) => ({
  // 初始状态
  conversations: [],
  currentConversation: null,
  messages: [],
  events: [],
  tasks: [],
  logs: [],
  gitStatus: null,
  gitLog: [],
  wsClient: null,
  isConnected: false,
  isLoading: false,
  error: null,
  agentConfigs: {
    orchestrator: { type: 'orchestrator', llmConfig: { backend: 'ollama', model: 'gemma2:9b' }, enabled: true },
    coder: { type: 'coder', llmConfig: { backend: 'ollama', model: 'gemma2:9b' }, enabled: true },
    reviewer: { type: 'reviewer', llmConfig: { backend: 'ollama', model: 'gemma2:9b' }, enabled: true },
    tester: { type: 'tester', llmConfig: { backend: 'ollama', model: 'gemma2:9b' }, enabled: true },
  },

  // 获取对话列表
  fetchConversations: async () => {
    set({ isLoading: true, error: null });
    try {
      const conversations = await api.listConversations();
      set({ conversations, isLoading: false });
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
    }
  },

  // 创建对话
  createConversation: async (name: string, task?: string) => {
    set({ isLoading: true, error: null });
    try {
      const conversation = await api.createConversation({ name, task });
      set((state) => ({
        conversations: [conversation, ...state.conversations],
        currentConversation: conversation,
        isLoading: false,
      }));
      return conversation;
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
      throw error;
    }
  },

  // 选择对话
  selectConversation: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const conversation = await api.getConversation(id);
      set({ currentConversation: conversation, isLoading: false });

      // 获取消息和事件
      const [messages, events] = await Promise.all([
        api.getMessages(id),
        api.getEvents(id),
      ]);
      set({ messages, events });

      // 获取 Git 状态
      get().fetchGitStatus();
      get().fetchGitLog();
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
    }
  },

  // 删除对话
  deleteConversation: async (id: string) => {
    try {
      await api.deleteConversation(id);
      set((state) => ({
        conversations: state.conversations.filter((c) => c.id !== id),
        currentConversation:
          state.currentConversation?.id === id ? null : state.currentConversation,
      }));
    } catch (error) {
      set({ error: (error as Error).message });
    }
  },

  // 发送消息
  sendMessage: async (content: string) => {
    const { currentConversation } = get();
    if (!currentConversation) return;

    try {
      const message = await api.sendMessage(currentConversation.id, { content, sender: 'user' });
      set((state) => ({
        messages: [...state.messages, message],
      }));
      get().addLog({
        agentName: 'user',
        level: 'info',
        content,
      });
    } catch (error) {
      set({ error: (error as Error).message });
    }
  },

  // 启动工作流
  startWorkflow: async (task: string, agentConfigs?: Record<string, LLMConfig>) => {
    const { currentConversation, agentConfigs: configs } = get();
    if (!currentConversation) return;

    set({ isLoading: true });
    try {
      const mergedConfigs = agentConfigs || Object.fromEntries(
        Object.entries(configs).map(([key, val]) => [key, val.llmConfig])
      );

      await api.startWorkflow(currentConversation.id, { task, agentConfigs: mergedConfigs });

      set((state) => ({
        currentConversation: state.currentConversation
          ? { ...state.currentConversation, status: 'running' }
          : null,
        isLoading: false,
      }));

      get().addLog({
        agentName: 'system',
        level: 'info',
        content: `开始执行任务: ${task}`,
      });
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
    }
  },

  // 暂停工作流
  pauseWorkflow: async () => {
    const { currentConversation } = get();
    if (!currentConversation) return;

    try {
      await api.pauseWorkflow(currentConversation.id);
      set((state) => ({
        currentConversation: state.currentConversation
          ? { ...state.currentConversation, status: 'paused' }
          : null,
      }));
      get().wsClient?.pause();
      get().addLog({ agentName: 'system', level: 'warning', content: '工作流已暂停' });
    } catch (error) {
      set({ error: (error as Error).message });
    }
  },

  // 恢复工作流
  resumeWorkflow: async () => {
    const { currentConversation } = get();
    if (!currentConversation) return;

    try {
      await api.resumeWorkflow(currentConversation.id);
      set((state) => ({
        currentConversation: state.currentConversation
          ? { ...state.currentConversation, status: 'running' }
          : null,
      }));
      get().wsClient?.resume();
      get().addLog({ agentName: 'system', level: 'info', content: '工作流已恢复' });
    } catch (error) {
      set({ error: (error as Error).message });
    }
  },

  // 停止工作流
  stopWorkflow: async () => {
    const { currentConversation } = get();
    if (!currentConversation) return;

    try {
      await api.stopWorkflow(currentConversation.id);
      set((state) => ({
        currentConversation: state.currentConversation
          ? { ...state.currentConversation, status: 'idle' }
          : null,
      }));
      get().wsClient?.stop();
      get().addLog({ agentName: 'system', level: 'warning', content: '工作流已停止' });
    } catch (error) {
      set({ error: (error as Error).message });
    }
  },

  // 获取消息
  fetchMessages: async () => {
    const { currentConversation } = get();
    if (!currentConversation) return;

    try {
      const messages = await api.getMessages(currentConversation.id);
      set({ messages });
    } catch (error) {
      set({ error: (error as Error).message });
    }
  },

  // 获取事件
  fetchEvents: async () => {
    const { currentConversation } = get();
    if (!currentConversation) return;

    try {
      const events = await api.getEvents(currentConversation.id);
      set({ events });
    } catch (error) {
      set({ error: (error as Error).message });
    }
  },

  // 获取 Git 状态
  fetchGitStatus: async () => {
    const { currentConversation } = get();
    if (!currentConversation) return;

    try {
      const gitStatus = await api.getGitStatus(currentConversation.id);
      set({ gitStatus });
    } catch (error) {
      // 忽略错误
    }
  },

  // 获取 Git 日志
  fetchGitLog: async () => {
    const { currentConversation } = get();
    if (!currentConversation) return;

    try {
      const gitLog = await api.getGitLog(currentConversation.id);
      set({ gitLog });
    } catch (error) {
      // 忽略错误
    }
  },

  // 连接 WebSocket
  connectWebSocket: async () => {
    const { currentConversation, wsClient } = get();
    if (!currentConversation || wsClient?.isConnected) return;

    const client = new WSClient(currentConversation.id);

    // 设置事件监听
    client.on('*', (data: unknown) => {
      const event = data as WSEvent;
      get().handleWSEvent(event);
    });

    try {
      await client.connect();
      set({ wsClient: client, isConnected: true });
    } catch (error) {
      set({ error: (error as Error).message });
    }
  },

  // 断开 WebSocket
  disconnectWebSocket: () => {
    const { wsClient } = get();
    if (wsClient) {
      wsClient.disconnect();
      set({ wsClient: null, isConnected: false });
    }
  },

  // 添加日志
  addLog: (entry: Omit<LogEntry, 'id' | 'timestamp'>) => {
    const log: LogEntry = {
      ...entry,
      id: `log_${++logIdCounter}`,
      timestamp: new Date().toISOString(),
    };
    set((state) => ({
      logs: [...state.logs, log],
    }));
  },

  // 更新对话状态
  updateConversationStatus: (status: Conversation['status']) => {
    set((state) => ({
      currentConversation: state.currentConversation
        ? { ...state.currentConversation, status }
        : null,
    }));
  },

  // 处理 WebSocket 事件
  handleWSEvent: (event: WSEvent) => {
    const { currentConversation } = get();

    if (event.conversationId !== currentConversation?.id) return;

    switch (event.type) {
      case 'workflow_start':
        get().updateConversationStatus('running');
        get().addLog({
          agentName: 'system',
          level: 'info',
          content: `开始执行任务: ${(event.data as { task: string }).task}`,
        });
        break;

      case 'workflow_complete':
        get().updateConversationStatus('completed');
        get().addLog({
          agentName: 'system',
          level: 'success',
          content: '任务执行完成',
        });
        get().fetchGitStatus();
        get().fetchGitLog();
        break;

      case 'task_decompose':
        get().addLog({
          agentName: 'system',
          level: 'info',
          content: `任务已分解为 ${((event.data as { subtasks: unknown[] }).subtasks.length)} 个子任务`,
        });
        break;

      case 'subtask_start':
        get().addLog({
          agentName: (event.data as { description: string }).description,
          level: 'info',
          content: `开始执行子任务`,
        });
        break;

      case 'subtask_complete':
        get().addLog({
          agentName: 'system',
          level: 'success',
          content: `子任务完成`,
        });
        break;

      case 'agent_thinking':
        get().addLog({
          agentName: event.agentName,
          level: 'info',
          content: `正在思考: ${(event.data as { thought: string }).thought}`,
        });
        break;

      case 'agent_acting':
        get().addLog({
          agentName: event.agentName,
          level: 'info',
          content: (event.data as { action: string }).action,
        });
        break;

      case 'agent_message':
        get().addLog({
          agentName: event.agentName,
          level: 'info',
          content: (event.data as { message: string }).message,
        });
        break;

      case 'user_message':
        get().addLog({
          agentName: 'user',
          level: 'info',
          content: (event.data as { message: string }).message,
        });
        break;

      case 'git_commit':
        get().addLog({
          agentName: 'git',
          level: 'success',
          content: `已提交: ${(event.data as { commit_hash: string; message: string }).message}`,
        });
        get().fetchGitStatus();
        get().fetchGitLog();
        break;

      case 'pause':
        get().updateConversationStatus('paused');
        get().addLog({ agentName: 'system', level: 'warning', content: '工作流已暂停' });
        break;

      case 'resume':
        get().updateConversationStatus('running');
        get().addLog({ agentName: 'system', level: 'info', content: '工作流已恢复' });
        break;

      case 'stop':
        get().updateConversationStatus('idle');
        get().addLog({ agentName: 'system', level: 'warning', content: '工作流已停止' });
        break;
    }
  },

  // 设置错误
  setError: (error: string | null) => {
    set({ error });
  },

  // 重置
  reset: () => {
    const { wsClient } = get();
    wsClient?.disconnect();

    set({
      conversations: [],
      currentConversation: null,
      messages: [],
      events: [],
      tasks: [],
      logs: [],
      gitStatus: null,
      gitLog: [],
      wsClient: null,
      isConnected: false,
      isLoading: false,
      error: null,
    });
  },
}));