/**
 * useWebSocket Hook
 */

import { useEffect, useRef, useCallback } from 'react';
import { WSClient } from '@/services/api';
import { useConversationStore } from '@/stores/conversationStore';

export function useWebSocket(conversationId: string | null) {
  const clientRef = useRef<WSClient | null>(null);
  const {
    isConnected,
    connectWebSocket,
    disconnectWebSocket,
  } = useConversationStore();

  useEffect(() => {
    if (!conversationId) return;

    // 连接 WebSocket
    connectWebSocket();

    return () => {
      disconnectWebSocket();
    };
  }, [conversationId]);

  const sendMessage = useCallback((content: string) => {
    clientRef.current?.sendMessage(content);
  }, []);

  const pause = useCallback(() => {
    clientRef.current?.pause();
  }, []);

  const resume = useCallback(() => {
    clientRef.current?.resume();
  }, []);

  const stop = useCallback(() => {
    clientRef.current?.stop();
  }, []);

  return {
    isConnected,
    sendMessage,
    pause,
    resume,
    stop,
  };
}
