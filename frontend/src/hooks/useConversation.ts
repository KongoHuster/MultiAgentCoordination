/**
 * useConversation Hook
 */

import { useCallback } from 'react';
import { useConversationStore } from '@/stores/conversationStore';

export function useConversation() {
  const {
    conversations,
    currentConversation,
    messages,
    events,
    tasks,
    logs,
    gitStatus,
    gitLog,
    isLoading,
    error,
    agentConfigs,

    fetchConversations,
    createConversation,
    selectConversation,
    deleteConversation,
    sendMessage,
    startWorkflow,
    pauseWorkflow,
    resumeWorkflow,
    stopWorkflow,
    connectWebSocket,
    disconnectWebSocket,
    addLog,
    setError,
    reset,
  } = useConversationStore();

  const start = useCallback(
    async (task: string) => {
      await connectWebSocket();
      await startWorkflow(task);
    },
    [connectWebSocket, startWorkflow]
  );

  const restart = useCallback(async () => {
    disconnectWebSocket();
    await connectWebSocket();
  }, [connectWebSocket, disconnectWebSocket]);

  return {
    // 状态
    conversations,
    currentConversation,
    messages,
    events,
    tasks,
    logs,
    gitStatus,
    gitLog,
    isLoading,
    error,
    agentConfigs,

    // 对话操作
    fetchConversations,
    createConversation,
    selectConversation,
    deleteConversation,
    sendMessage,

    // 工作流控制
    start,
    startWorkflow,
    pauseWorkflow,
    resumeWorkflow,
    stopWorkflow,
    restart,

    // WebSocket
    connectWebSocket,
    disconnectWebSocket,

    // 日志
    addLog,
    setError,

    // 重置
    reset,
  };
}
