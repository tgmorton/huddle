/**
 * WebSocket hook for AgentMail real-time updates
 */

import { useEffect, useRef, useCallback } from 'react';
import {
  useAgentMailStore,
  type AgentMailWSMessage,
  type DashboardData,
  type AgentMailMessage,
  type AgentInfo,
} from '../stores/agentMailStore';

const WS_BASE_URL = 'ws://localhost:8000';

interface UseAgentMailWebSocketOptions {
  autoConnect?: boolean;
}

export function useAgentMailWebSocket({
  autoConnect = true,
}: UseAgentMailWebSocketOptions = {}) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const isMountedRef = useRef(true);

  const {
    setConnected,
    setLoading,
    setError,
    setDashboardData,
    updateMessage,
    addMessage,
    updateAgentStatus,
    setAgentOnline,
    clearStore,
  } = useAgentMailStore();

  // Handle incoming messages
  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const message: AgentMailWSMessage = JSON.parse(event.data);

        switch (message.type) {
          case 'state_sync':
            if (message.payload) {
              setDashboardData(message.payload as DashboardData);
            }
            break;

          case 'message_added':
            if (message.payload) {
              addMessage(message.payload as AgentMailMessage);
            }
            break;

          case 'message_updated':
            if (message.payload) {
              updateMessage(message.payload as AgentMailMessage);
            }
            break;

          case 'status_changed':
            if (message.payload) {
              const { agent, status } = message.payload as {
                agent: string;
                status: Partial<AgentInfo>;
              };
              updateAgentStatus(agent, status);
            }
            break;

          case 'agent_online':
            if (message.payload) {
              const { agent, is_online } = message.payload as {
                agent: string;
                is_online: boolean;
              };
              setAgentOnline(agent, is_online);
            }
            break;

          case 'error':
            setError(message.error_message || 'Unknown error');
            break;
        }
      } catch (err) {
        console.error('Failed to parse AgentMail WebSocket message:', err);
      }
    },
    [
      setDashboardData,
      addMessage,
      updateMessage,
      updateAgentStatus,
      setAgentOnline,
      setError,
    ]
  );

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    if (!isMountedRef.current) {
      return;
    }

    setLoading(true);
    setError(null);

    const ws = new WebSocket(`${WS_BASE_URL}/ws/agentmail`);

    ws.onopen = () => {
      if (isMountedRef.current) {
        setConnected(true);
        setLoading(false);
        setError(null);
        console.log('AgentMail WebSocket connected');
      }
    };

    ws.onclose = () => {
      if (isMountedRef.current) {
        setConnected(false);
        console.log('AgentMail WebSocket disconnected');

        // Attempt to reconnect after 3 seconds
        if (reconnectTimeoutRef.current) {
          window.clearTimeout(reconnectTimeoutRef.current);
        }
        reconnectTimeoutRef.current = window.setTimeout(() => {
          if (autoConnect && isMountedRef.current) {
            connect();
          }
        }, 3000);
      }
    };

    ws.onerror = (error) => {
      if (isMountedRef.current) {
        console.error('AgentMail WebSocket error:', error);
        setError('WebSocket connection failed');
        setLoading(false);
      }
    };

    ws.onmessage = handleMessage;

    wsRef.current = ws;
  }, [autoConnect, setConnected, setLoading, setError, handleMessage]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      window.clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    clearStore();
  }, [clearStore]);

  // Send message helper
  const send = useCallback((message: AgentMailWSMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  // Request full state sync
  const requestSync = useCallback(() => {
    send({ type: 'request_sync' });
  }, [send]);

  // Auto-connect on mount
  useEffect(() => {
    isMountedRef.current = true;

    if (autoConnect) {
      connect();
    }

    return () => {
      isMountedRef.current = false;
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    connect,
    disconnect,
    requestSync,
  };
}
