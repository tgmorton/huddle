/**
 * WebSocket hook for management/franchise mode
 */

import { useEffect, useRef, useCallback } from 'react';
import { useManagementStore } from '../stores/managementStore';
import type {
  ManagementWSMessage,
  LeagueState,
  CalendarState,
  ManagementEvent,
  TickerItem,
  ClipboardState,
  EventQueue,
  TimeSpeed,
  ClipboardTab,
} from '../types/management';

const WS_BASE_URL = 'ws://localhost:8000';

interface UseManagementWebSocketOptions {
  franchiseId: string;
  autoConnect?: boolean;
}

export function useManagementWebSocket({
  franchiseId,
  autoConnect = true,
}: UseManagementWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const {
    setConnected,
    setLoading,
    setError,
    setFullState,
    updateCalendar,
    updateEvents,
    setEvents,
    mergeEvents,
    updateClipboard,
    addTickerItem,
    addEvent,
    showAutoPause,
    clearSession,
  } = useManagementStore();

  // Handle incoming messages
  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const message: ManagementWSMessage = JSON.parse(event.data);

        switch (message.type) {
          case 'state_sync':
            if (message.payload) {
              setFullState(message.payload as unknown as LeagueState);
            }
            break;

          case 'calendar_update':
            if (message.payload) {
              const payload = message.payload as unknown as CalendarState & { events?: ManagementEvent[] };
              updateCalendar(payload);
              // Merge events from server to prevent drift between server tick loop and client
              // mergeEvents dedupes by ID, so concurrent REST calls won't cause duplicates
              if (payload.events && Array.isArray(payload.events)) {
                mergeEvents(payload.events);
              }
            }
            break;

          case 'event_added':
            if (message.payload) {
              addEvent(message.payload as unknown as ManagementEvent);
            }
            break;

          case 'event_updated':
            if (message.payload) {
              updateEvents(message.payload as unknown as EventQueue);
            }
            break;

          case 'clipboard_update':
            if (message.payload) {
              updateClipboard(message.payload as unknown as ClipboardState);
            }
            break;

          case 'ticker_item':
            if (message.payload) {
              addTickerItem(message.payload as unknown as TickerItem);
            }
            break;

          case 'auto_paused':
            if (message.payload) {
              const { reason, event_id } = message.payload as {
                reason: string;
                event_id: string | null;
              };
              showAutoPause(reason, event_id);
            }
            break;

          case 'error':
            setError(message.error_message || 'Unknown error');
            break;
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    },
    [
      setFullState,
      updateCalendar,
      updateEvents,
      setEvents,
      updateClipboard,
      addTickerItem,
      addEvent,
      showAutoPause,
      setError,
    ]
  );

  // Track if component is mounted
  const isMountedRef = useRef(true);

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

    const ws = new WebSocket(`${WS_BASE_URL}/ws/management/${franchiseId}`);

    ws.onopen = () => {
      if (isMountedRef.current) {
        setConnected(true);
        setLoading(false);
        setError(null);  // Clear any previous errors
        console.log('Management WebSocket connected');
      }
    };

    ws.onclose = () => {
      if (isMountedRef.current) {
        setConnected(false);
        console.log('Management WebSocket disconnected');

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
        console.error('Management WebSocket error:', error);
        setError('WebSocket connection failed');
        setLoading(false);
      }
    };

    ws.onmessage = handleMessage;

    wsRef.current = ws;
  }, [franchiseId, autoConnect, setConnected, setLoading, setError, handleMessage]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      window.clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    clearSession();
  }, [clearSession]);

  // Send message helper
  const send = useCallback((message: ManagementWSMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  // === Control Actions ===

  const pause = useCallback(() => {
    send({ type: 'pause' });
  }, [send]);

  const play = useCallback((speed: TimeSpeed = 'NORMAL') => {
    send({ type: 'play', payload: { speed } });
  }, [send]);

  const setSpeed = useCallback((speed: TimeSpeed) => {
    send({ type: 'set_speed', payload: { speed } });
  }, [send]);

  const selectTab = useCallback((tab: ClipboardTab) => {
    send({ type: 'select_tab', payload: { tab } });
  }, [send]);

  const attendEvent = useCallback((eventId: string) => {
    send({ type: 'attend_event', payload: { event_id: eventId } });
  }, [send]);

  const dismissEvent = useCallback((eventId: string) => {
    send({ type: 'dismiss_event', payload: { event_id: eventId } });
  }, [send]);

  const runPractice = useCallback((eventId: string, allocation: {
    playbook: number;
    development: number;
    gamePrep: number;
  }) => {
    send({
      type: 'run_practice',
      payload: {
        event_id: eventId,
        allocation,
      },
    });
  }, [send]);

  const playGame = useCallback((eventId: string) => {
    send({
      type: 'play_game',
      payload: { event_id: eventId },
    });
  }, [send]);

  const simGame = useCallback((eventId: string) => {
    send({
      type: 'sim_game',
      payload: { event_id: eventId },
    });
  }, [send]);

  const goBack = useCallback(() => {
    send({ type: 'go_back' });
  }, [send]);

  const requestSync = useCallback(() => {
    send({ type: 'request_sync' });
  }, [send]);

  // Auto-connect on mount
  useEffect(() => {
    isMountedRef.current = true;

    if (autoConnect && franchiseId) {
      connect();
    }

    return () => {
      isMountedRef.current = false;
      disconnect();
    };
  }, [franchiseId, autoConnect, connect, disconnect]);

  return {
    // Connection
    connect,
    disconnect,

    // Controls
    pause,
    play,
    setSpeed,

    // Navigation
    selectTab,
    goBack,

    // Events
    attendEvent,
    dismissEvent,
    runPractice,
    playGame,
    simGame,

    // Utility
    requestSync,
  };
}
