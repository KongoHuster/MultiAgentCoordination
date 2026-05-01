/**
 * TypeScript 类型定义
 */

// 对话状态
export type ConversationStatus = 'idle' | 'running' | 'paused' | 'completed' | 'failed';

// Agent 类型
export type AgentType = 'orchestrator' | 'coder' | 'reviewer' | 'tester';

// LLM 后端
export type LLMBackend = 'ollama' | 'anthropic' | 'zhipu' | 'deepseek';

// LLM 配置
export interface LLMConfig {
  backend: LLMBackend;
  model: string;
  api_key?: string;
  base_url?: string;
  max_tokens?: number;
  temperature?: number;
}

// Agent 配置
export interface AgentConfig {
  type: AgentType;
  llmConfig: LLMConfig;
  enabled: boolean;
}

// 对话
export interface Conversation {
  id: string;
  name: string;
  status: ConversationStatus;
  projectPath?: string;
  agentConfigs: Record<string, AgentConfig> | AgentConfig[];
  createdAt: string;
  updatedAt: string;
}

// 任务
export interface Task {
  id: string;
  conversationId: string;
  description: string;
  agentType: AgentType;
  status: 'pending' | 'running' | 'completed' | 'failed';
  priority: 'low' | 'normal' | 'high';
  retryCount: number;
  orderIndex: number;
  result?: Record<string, unknown>;
}

// 消息
export interface Message {
  id: string;
  conversationId: string;
  sender: string;
  content: string;
  messageType: 'text' | 'system' | 'command';
  createdAt: string;
}

// Agent 事件
export interface AgentEvent {
  id: string;
  conversationId: string;
  agentName: string;
  eventType: 'thinking' | 'acting' | 'message' | 'task_progress' | 'error';
  content?: string;
  taskId?: string;
  metadata?: Record<string, unknown>;
  timestamp: string;
}

// WebSocket 事件
export interface WSEvent {
  type: string;
  conversationId: string;
  data: unknown;
  timestamp: string;
  agentName?: string;
  taskId?: string;
}

// Git 提交
export interface GitCommit {
  hash: string;
  shortHash: string;
  message: string;
  author: string;
  date: string;
  files: string[];
}

// Git 状态
export interface GitStatus {
  branch: string;
  isClean: boolean;
  staged: string[];
  modified: string[];
  untracked: string[];
}

// LLM 提供商
export interface LLMProvider {
  id: string;
  name: string;
  defaultModel: string;
  requiresApiKey: boolean;
  supportsStreaming: boolean;
}

// 日志条目
export interface LogEntry {
  id: string;
  timestamp: string;
  agentName?: string;
  level: 'info' | 'success' | 'warning' | 'error';
  content: string;
}

// API 响应类型
export interface ApiResponse<T> {
  data?: T;
  error?: string;
}

// 创建对话请求
export interface CreateConversationRequest {
  name: string;
  task?: string;
  agentConfigs?: Record<string, LLMConfig>;
}

// 发送消息请求
export interface SendMessageRequest {
  content: string;
  sender?: string;
}

// 启动任务请求
export interface StartTaskRequest {
  task: string;
  agentConfigs?: Record<string, LLMConfig>;
}

// 提交请求
export interface CommitRequest {
  message: string;
}