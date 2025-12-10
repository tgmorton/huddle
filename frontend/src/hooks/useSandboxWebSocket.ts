/**
 * WebSocket hook for sandbox simulation
 */

import { useCallback, useEffect, useRef } from 'react';
import { useSandboxStore } from '../stores/sandboxStore';
import type { SandboxServerMessage, SandboxPlayer } from '../types/sandbox';

const WS_BASE_URL = 'ws://localhost:8000';

interface UseSandboxWebSocketOptions {
  sessionId: string | null;
  autoConnect?: boolean;
}

export function useSandboxWebSocket({ sessionId, autoConnect = true }: UseSandboxWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const {
    setConnected,
    setError,
    setState,
    updateFromTick,
  } = useSandboxStore();

  // Handle incoming messages
  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const message: SandboxServerMessage = JSON.parse(event.data);

        switch (message.type) {
          case 'state_sync':
            setState(message.payload);
            break;

          case 'tick_update':
            updateFromTick(message.payload);
            break;

          case 'simulation_complete':
            setState(message.payload);
            break;

          case 'error':
            setError(message.message);
            break;

          default:
            console.warn('Unknown message type:', message);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    },
    [setState, updateFromTick, setError]
  );

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!sessionId) {
      console.warn('No session ID provided');
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const ws = new WebSocket(`${WS_BASE_URL}/ws/sandbox/${sessionId}`);

    ws.onopen = () => {
      console.log('Sandbox WebSocket connected');
      setConnected(true);
      setError(null);
    };

    ws.onmessage = handleMessage;

    ws.onerror = (error) => {
      console.error('Sandbox WebSocket error:', error);
      setError('WebSocket connection error');
    };

    ws.onclose = () => {
      console.log('Sandbox WebSocket disconnected');
      setConnected(false);
    };

    wsRef.current = ws;
  }, [sessionId, handleMessage, setConnected, setError]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // Send message to server
  const sendMessage = useCallback((message: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected');
    }
  }, []);

  // Control methods
  const startSimulation = useCallback(() => {
    sendMessage({ type: 'start_simulation' });
  }, [sendMessage]);

  const pauseSimulation = useCallback(() => {
    sendMessage({ type: 'pause_simulation' });
  }, [sendMessage]);

  const resumeSimulation = useCallback(() => {
    sendMessage({ type: 'resume_simulation' });
  }, [sendMessage]);

  const resetSimulation = useCallback(() => {
    sendMessage({ type: 'reset_simulation' });
  }, [sendMessage]);

  const updatePlayer = useCallback(
    (role: 'blocker' | 'rusher', player: Partial<SandboxPlayer>) => {
      sendMessage({ type: 'update_player', role, player });
    },
    [sendMessage]
  );

  const setTickRate = useCallback(
    (tickRateMs: number) => {
      sendMessage({ type: 'set_tick_rate', tick_rate_ms: tickRateMs });
    },
    [sendMessage]
  );

  const requestSync = useCallback(() => {
    sendMessage({ type: 'request_sync' });
  }, [sendMessage]);

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect && sessionId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, sessionId, connect, disconnect]);

  return {
    connect,
    disconnect,
    sendMessage,
    startSimulation,
    pauseSimulation,
    resumeSimulation,
    resetSimulation,
    updatePlayer,
    setTickRate,
    requestSync,
  };
}
