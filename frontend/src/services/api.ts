/**
 * API 客户端
 */

import type {
  Conversation,
  Message,
  AgentEvent,
  GitStatus,
  GitCommit,
  LLMProvider,
  CreateConversationRequest,
  SendMessageRequest,
  StartTaskRequest,
  CommitRequest,
} from '@/types';

const API_BASE = '/api';
const WS_BASE = 'ws://localhost:8000/ws';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    const data = await response.json();
    // 转换 snake_case 到 camelCase
    return this.transformResponse(data);
  }

  private transformResponse<T>(data: T): T {
    if (Array.isArray(data)) {
      return data.map(item => this.transformResponse(item)) as T;
    }
    if (data && typeof data === 'object') {
      const result: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
        // 转换 snake_case 到 camelCase
        const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
        result[camelKey] = this.transformResponse(value);
      }
      return result as T;
    }
    return data;
  }

  // 对话管理
  async createConversation(data: CreateConversationRequest): Promise<Conversation> {
    return this.request<Conversation>('/conversations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async listConversations(skip = 0, limit = 50): Promise<Conversation[]> {
    return this.request<Conversation[]>(`/conversations?skip=${skip}&limit=${limit}`);
  }

  async getConversation(id: string): Promise<Conversation> {
    return this.request<Conversation>(`/conversations/${id}`);
  }

  async deleteConversation(id: string): Promise<void> {
    await this.request(`/conversations/${id}`, { method: 'DELETE' });
  }

  // 消息
  async sendMessage(conversationId: string, data: SendMessageRequest): Promise<Message> {
    return this.request<Message>(`/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getMessages(conversationId: string, limit = 100): Promise<Message[]> {
    return this.request<Message[]>(`/conversations/${conversationId}/messages?limit=${limit}`);
  }

  async getEvents(conversationId: string, limit = 100): Promise<AgentEvent[]> {
    return this.request<AgentEvent[]>(`/conversations/${conversationId}/events?limit=${limit}`);
  }

  // Agent 控制
  async startWorkflow(conversationId: string, data: StartTaskRequest): Promise<{ status: string }> {
    return this.request(`/conversations/${conversationId}/start`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async pauseWorkflow(conversationId: string): Promise<{ status: string }> {
    return this.request(`/conversations/${conversationId}/pause`, {
      method: 'POST',
    });
  }

  async resumeWorkflow(conversationId: string): Promise<{ status: string }> {
    return this.request(`/conversations/${conversationId}/resume`, {
      method: 'POST',
    });
  }

  async stopWorkflow(conversationId: string): Promise<{ status: string }> {
    return this.request(`/conversations/${conversationId}/stop`, {
      method: 'POST',
    });
  }

  async getWorkflowStatus(conversationId: string): Promise<{
    conversationId: string;
    status: string;
    userMessages: string[];
    state?: string;
  }> {
    return this.request(`/conversations/${conversationId}/status`);
  }

  // Git 操作
  async getGitStatus(conversationId: string): Promise<GitStatus> {
    return this.request<GitStatus>(`/conversations/${conversationId}/git/status`);
  }

  async getGitLog(conversationId: string, limit = 50): Promise<GitCommit[]> {
    return this.request<GitCommit[]>(`/conversations/${conversationId}/git/log?limit=${limit}`);
  }

  async gitCommit(conversationId: string, data: CommitRequest): Promise<{ commitHash: string }> {
    return this.request(`/conversations/${conversationId}/git/commit`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async listFiles(conversationId: string, ref?: string): Promise<{ files: string[] }> {
    const url = ref
      ? `/conversations/${conversationId}/git/files?ref=${ref}`
      : `/conversations/${conversationId}/git/files`;
    return this.request(url);
  }

  async getFileContent(conversationId: string, filePath: string, ref?: string): Promise<{
    filePath: string;
    content: string;
  }> {
    const url = ref
      ? `/conversations/${conversationId}/git/files/${filePath}?ref=${ref}`
      : `/conversations/${conversationId}/git/files/${filePath}`;
    return this.request(url);
  }

  // LLM
  async listLLMProviders(): Promise<{ providers: LLMProvider[] }> {
    return this.request<{ providers: LLMProvider[] }>('/llm/providers');
  }

  async checkLLMHealth(backend?: string): Promise<Record<string, boolean>> {
    const url = backend
      ? `/llm/health?backend=${backend}`
      : '/llm/health';
    return this.request(url);
  }

  async listModels(backend: string): Promise<{ backend: string; models: { name: string; description: string }[] }> {
    return this.request(`/llm/models/${backend}`);
  }
}

// WebSocket 客户端
export class WSClient {
  private ws: WebSocket | null = null;
  private conversationId: string;
  private userId: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private listeners: Map<string, Set<(data: unknown) => void>> = new Map();
  private onConnectCallback: (() => void) | null = null;
  private onDisconnectCallback: (() => void) | null = null;

  constructor(conversationId: string, userId = 'user') {
    this.conversationId = conversationId;
    this.userId = userId;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const url = `${WS_BASE}/${this.conversationId}?user_id=${this.userId}`;
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.onConnectCallback?.();
        resolve();
      };

      this.ws.onclose = () => {
        this.onDisconnectCallback?.();
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.notifyListeners(data.type, data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };
    });
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(data: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  sendMessage(content: string): void {
    this.send({
      type: 'user_message',
      content,
      user_id: this.userId,
    });
  }

  sendPing(): void {
    this.send({ type: 'ping', timestamp: Date.now() });
  }

  pause(): void {
    this.send({ type: 'pause' });
  }

  resume(): void {
    this.send({ type: 'resume' });
  }

  stop(): void {
    this.send({ type: 'stop' });
  }

  on(eventType: string, callback: (data: unknown) => void): void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType)!.add(callback);
  }

  off(eventType: string, callback: (data: unknown) => void): void {
    this.listeners.get(eventType)?.delete(callback);
  }

  onConnect(callback: () => void): void {
    this.onConnectCallback = callback;
  }

  onDisconnect(callback: () => void): void {
    this.onDisconnectCallback = callback;
  }

  private notifyListeners(eventType: string, data: unknown): void {
    this.listeners.get(eventType)?.forEach((callback) => {
      try {
        callback(data);
      } catch (error) {
        console.error('Error in WebSocket listener:', error);
      }
    });

    // 通知通配符监听器
    this.listeners.get('*')?.forEach((callback) => {
      try {
        callback(data);
      } catch (error) {
        console.error('Error in WebSocket wildcard listener:', error);
      }
    });
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    setTimeout(() => {
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
      this.connect().catch(() => {
        // 继续重连
      });
    }, delay);
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// 导出单例
export const api = new ApiClient();
