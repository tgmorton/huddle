/**
 * Main sandbox screen component - REST-based animation
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { SandboxCanvas } from './SandboxCanvas';
import { PlayerControls } from './PlayerControls';
import { SimulationControls } from './SimulationControls';
import { StatsPanel } from './StatsPanel';
import { useSandboxStore } from '../../stores/sandboxStore';
import type { SandboxState, TickResult, SandboxPlayer } from '../../types/sandbox';
import './SandboxScreen.css';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export function SandboxScreen() {
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [tickResults, setTickResults] = useState<TickResult[]>([]);
  const [currentTickIndex, setCurrentTickIndex] = useState(0);
  const animationRef = useRef<number | null>(null);

  const {
    sessionId,
    state,
    error,
    setSessionId,
    setState,
    setError,
    clearSession,
    updateFromTick,
    setTargetPositions,
  } = useSandboxStore();

  // Create a new session
  const createSession = useCallback(async () => {
    setIsCreatingSession(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/sandbox/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        throw new Error('Failed to create session');
      }

      const data: SandboxState = await response.json();
      setSessionId(data.session_id);
      setState(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsCreatingSession(false);
    }
  }, [setSessionId, setState, setError]);

  // Delete current session
  const deleteSession = useCallback(async () => {
    if (!sessionId) return;

    try {
      await fetch(`${API_BASE_URL}/sandbox/sessions/${sessionId}`, {
        method: 'DELETE',
      });
    } catch (err) {
      console.error('Failed to delete session:', err);
    }

    clearSession();
    setTickResults([]);
    setCurrentTickIndex(0);
    setIsSimulating(false);
  }, [sessionId, clearSession]);

  // Run simulation and get all ticks
  const runSimulation = useCallback(async () => {
    if (!sessionId) return;

    setIsSimulating(true);
    setCurrentTickIndex(0);
    setError(null);

    try {
      // First reset the session
      await fetch(`${API_BASE_URL}/sandbox/sessions/${sessionId}/reset`, {
        method: 'POST',
      });

      // Then run the simulation
      const response = await fetch(
        `${API_BASE_URL}/sandbox/sessions/${sessionId}/run-sync`,
        { method: 'POST' }
      );

      if (!response.ok) {
        throw new Error('Failed to run simulation');
      }

      const results: TickResult[] = await response.json();
      setTickResults(results);

      // Start animation
      if (results.length > 0) {
        animateTicks(results);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setIsSimulating(false);
    }
  }, [sessionId, setError]);

  // Animate through ticks
  const animateTicks = useCallback((results: TickResult[]) => {
    let index = 0;
    const tickRate = state?.tick_rate_ms ?? 100;

    const animate = () => {
      if (index >= results.length) {
        setIsSimulating(false);
        // Refresh session state to get final outcome
        if (sessionId) {
          fetch(`${API_BASE_URL}/sandbox/sessions/${sessionId}`)
            .then((r) => r.json())
            .then((data) => setState(data))
            .catch(() => {});
        }
        return;
      }

      const tick = results[index];
      updateFromTick(tick);
      setTargetPositions(tick.blocker_position, tick.rusher_position);
      setCurrentTickIndex(index);

      index++;
      animationRef.current = window.setTimeout(animate, tickRate);
    };

    animate();
  }, [sessionId, state?.tick_rate_ms, updateFromTick, setTargetPositions, setState]);

  // Reset simulation
  const resetSimulation = useCallback(async () => {
    if (animationRef.current) {
      clearTimeout(animationRef.current);
      animationRef.current = null;
    }

    setIsSimulating(false);
    setTickResults([]);
    setCurrentTickIndex(0);

    if (!sessionId) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/sandbox/sessions/${sessionId}/reset`,
        { method: 'POST' }
      );

      if (response.ok) {
        const data = await response.json();
        setState(data);
      }
    } catch (err) {
      console.error('Failed to reset:', err);
    }
  }, [sessionId, setState]);

  // Update player
  const updatePlayer = useCallback(
    async (role: 'blocker' | 'rusher', updates: Partial<SandboxPlayer>) => {
      if (!sessionId || isSimulating) return;

      try {
        const currentPlayer = role === 'blocker' ? state?.blocker : state?.rusher;
        const updatedPlayer = { ...currentPlayer, ...updates };

        const response = await fetch(
          `${API_BASE_URL}/sandbox/sessions/${sessionId}/player`,
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role, player: updatedPlayer }),
          }
        );

        if (response.ok) {
          const data = await response.json();
          setState(data);
        }
      } catch (err) {
        console.error('Failed to update player:', err);
      }
    },
    [sessionId, isSimulating, state, setState]
  );

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (animationRef.current) {
        clearTimeout(animationRef.current);
      }
      if (sessionId) {
        fetch(`${API_BASE_URL}/sandbox/sessions/${sessionId}`, {
          method: 'DELETE',
        }).catch(() => {});
      }
    };
  }, [sessionId]);

  // No session - show create button
  if (!sessionId) {
    return (
      <div className="sandbox-screen">
        <div className="sandbox-header">
          <h1>Blocking Sandbox</h1>
          <p>Test 1v1 blocking matchups between an offensive lineman and defensive tackle</p>
        </div>

        <div className="sandbox-create">
          <button
            className="create-session-btn"
            onClick={createSession}
            disabled={isCreatingSession}
          >
            {isCreatingSession ? 'Creating...' : 'Create Session'}
          </button>

          {error && <div className="error-message">{error}</div>}
        </div>
      </div>
    );
  }

  return (
    <div className="sandbox-screen">
      <div className="sandbox-header">
        <h1>Blocking Sandbox</h1>
        <div className="session-info">
          Session: {sessionId.slice(0, 8)}...
        </div>
        <button className="end-session-btn" onClick={deleteSession}>
          End Session
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="sandbox-content">
        <div className="sandbox-main">
          <SandboxCanvas qbZoneDepth={state?.qb_zone_depth ?? 7} />

          <SimulationControls
            isRunning={isSimulating}
            isComplete={state?.is_complete ?? false}
            isPaused={false}
            onStart={runSimulation}
            onPause={() => {}}
            onResume={() => {}}
            onReset={resetSimulation}
          />

          {tickResults.length > 0 && (
            <div className="tick-progress">
              Tick {currentTickIndex + 1} / {tickResults.length}
            </div>
          )}
        </div>

        <div className="sandbox-sidebar">
          {state && (
            <>
              <PlayerControls
                player={state.blocker}
                onUpdate={(updates) => updatePlayer('blocker', updates)}
                disabled={isSimulating}
              />
              <PlayerControls
                player={state.rusher}
                onUpdate={(updates) => updatePlayer('rusher', updates)}
                disabled={isSimulating}
              />
              <StatsPanel state={state} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
