/**
 * WebSocket hook for real-time game updates
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useGameStore } from '../stores/gameStore';
import type {
  ClientMessage,
  ServerMessage,
  PlayCompletedMessage,
  ScoringMessage,
  TurnoverMessage,
  QuarterEndMessage,
  GameEndMessage,
  AwaitingPlayCallMessage,
  StateSyncMessage,
  ErrorMessage,
} from '../types/events';

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

interface UseWebSocketOptions {
  gameId: string | null;
  autoConnect?: boolean;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  connect: () => void;
  disconnect: () => void;
  send: (message: ClientMessage) => void;
  pause: () => void;
  resume: () => void;
  setPacing: (pacing: 'instant' | 'fast' | 'normal' | 'slow') => void;
  submitPlayCall: (playType: string, runType?: string, passType?: string) => void;
  requestSync: () => void;
}

export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const { gameId, autoConnect = true, reconnectAttempts = 3, reconnectInterval = 2000 } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const [isConnected, setIsConnected] = useState(false);

  const {
    initGame,
    addPlayFromWS,
    setAwaitingPlayCall,
    setConnected,
    setError,
  } = useGameStore();

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const message: ServerMessage = JSON.parse(event.data);

        switch (message.type) {
          case 'state_sync': {
            const { game_state, home_team, away_team } = (message as StateSyncMessage).payload;
            initGame(game_state.id, game_state, home_team, away_team);
            break;
          }
          case 'play_completed': {
            const payload = (message as PlayCompletedMessage).payload;
            addPlayFromWS(payload);
            setAwaitingPlayCall(false);
            break;
          }
          case 'scoring': {
            const payload = (message as ScoringMessage).payload;
            console.log('Scoring:', payload.description);
            break;
          }
          case 'turnover': {
            const payload = (message as TurnoverMessage).payload;
            console.log('Turnover:', payload.description);
            break;
          }
          case 'quarter_end': {
            const payload = (message as QuarterEndMessage).payload;
            console.log(`End of Q${payload.quarter}: ${payload.home_score} - ${payload.away_score}`);
            break;
          }
          case 'game_end': {
            const payload = (message as GameEndMessage).payload;
            console.log(
              `Game Over: ${payload.home_score} - ${payload.away_score}`,
              payload.is_tie ? '(TIE)' : ''
            );
            break;
          }
          case 'awaiting_play_call': {
            const payload = (message as AwaitingPlayCallMessage).payload;
            setAwaitingPlayCall(true, payload.available_plays);
            break;
          }
          case 'error': {
            const payload = (message as ErrorMessage).payload;
            setError(payload.message);
            break;
          }
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    },
    [initGame, addPlayFromWS, setAwaitingPlayCall, setError]
  );

  const connect = useCallback(() => {
    if (!gameId || wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_BASE_URL}/ws/games/${gameId}`);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      setConnected(true);
      reconnectCountRef.current = 0;
    };

    ws.onmessage = handleMessage;

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      setConnected(false);

      // Attempt reconnection
      if (reconnectCountRef.current < reconnectAttempts) {
        reconnectCountRef.current += 1;
        console.log(`Reconnecting... (${reconnectCountRef.current}/${reconnectAttempts})`);
        setTimeout(connect, reconnectInterval);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('WebSocket connection error');
    };

    wsRef.current = ws;
  }, [gameId, handleMessage, reconnectAttempts, reconnectInterval, setConnected, setError]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      reconnectCountRef.current = reconnectAttempts; // Prevent reconnection
      wsRef.current.close();
      wsRef.current = null;
    }
  }, [reconnectAttempts]);

  const send = useCallback((message: ClientMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  const pause = useCallback(() => {
    send({ type: 'pause' });
  }, [send]);

  const resume = useCallback(() => {
    send({ type: 'resume' });
  }, [send]);

  const setPacing = useCallback(
    (pacing: 'instant' | 'fast' | 'normal' | 'slow') => {
      send({ type: 'set_pacing', payload: { pacing } });
    },
    [send]
  );

  const submitPlayCall = useCallback(
    (playType: string, runType?: string, passType?: string) => {
      send({
        type: 'play_call',
        payload: { play_type: playType, run_type: runType, pass_type: passType },
      });
    },
    [send]
  );

  const requestSync = useCallback(() => {
    send({ type: 'request_sync' });
  }, [send]);

  // Auto-connect when gameId changes
  useEffect(() => {
    if (autoConnect && gameId) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [autoConnect, gameId, connect, disconnect]);

  return {
    isConnected,
    connect,
    disconnect,
    send,
    pause,
    resume,
    setPacing,
    submitPlayCall,
    requestSync,
  };
}
