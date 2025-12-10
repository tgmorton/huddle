/**
 * GameScreen - main game layout component
 */

import { useCallback, useEffect, useState } from 'react';
import { useGameStore } from '../../stores/gameStore';
import { gamesApi } from '../../api/client';
import { useWebSocket } from '../../hooks/useWebSocket';
import { Scoreboard } from '../Scoreboard';
import { FieldView } from '../FieldView';
import { PlayLog } from '../PlayLog';
import { StatsPanel } from '../StatsPanel';
import { PacingControl } from '../PacingControl';
import './GameScreen.css';

export function GameScreen() {
  const [isCreating, setIsCreating] = useState(false);
  const {
    gameId,
    gameState,
    error,
    initGame,
    setPaused,
    setPacing,
    setLoading,
    setError,
  } = useGameStore();

  const { isConnected, pause, resume, setPacing: wsPacing } = useWebSocket({
    gameId,
    autoConnect: true,
  });

  // Create a new game
  const handleCreateGame = useCallback(async () => {
    setIsCreating(true);
    setError(null);
    try {
      const response = await gamesApi.create({ generate_teams: true });
      initGame(response.game_state.id, response.game_state, response.home_team, response.away_team);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create game');
    } finally {
      setIsCreating(false);
    }
  }, [initGame, setError]);

  // Execute a single play (for step mode - triggers via REST, WebSocket will receive update)
  const handleStep = useCallback(async () => {
    if (!gameId) return;
    setLoading(true);
    try {
      await gamesApi.step(gameId);
      // WebSocket will receive the play_completed event
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute play');
    } finally {
      setLoading(false);
    }
  }, [gameId, setLoading, setError]);

  const handlePause = useCallback(() => {
    pause();
    setPaused(true);
  }, [pause, setPaused]);

  const handleResume = useCallback(() => {
    resume();
    setPaused(false);
  }, [resume, setPaused]);

  const handlePacingChange = useCallback(
    (pacing: 'instant' | 'fast' | 'normal' | 'slow') => {
      wsPacing(pacing);
      setPacing(pacing);
    },
    [wsPacing, setPacing]
  );

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      switch (e.key.toLowerCase()) {
        case ' ':
          e.preventDefault();
          if (useGameStore.getState().isPaused) {
            handleResume();
          } else {
            handlePause();
          }
          break;
        case 'n':
          e.preventDefault();
          handleStep();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handlePause, handleResume, handleStep]);

  // No game - show create button
  if (!gameId || !gameState) {
    return (
      <div className="game-screen game-screen--no-game">
        <div className="game-screen__welcome">
          <h1>Huddle</h1>
          <p>American Football Simulator</p>
          <button
            className="game-screen__create-btn"
            onClick={handleCreateGame}
            disabled={isCreating}
          >
            {isCreating ? 'Creating Game...' : 'New Game'}
          </button>
          {error && <p className="game-screen__error">{error}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="game-screen">
      <header className="game-screen__header">
        <Scoreboard />
      </header>

      <main className="game-screen__main">
        <div className="game-screen__left-panel">
          <FieldView />
          <StatsPanel />
        </div>

        <aside className="game-screen__sidebar">
          <PlayLog />
        </aside>
      </main>

      <footer className="game-screen__footer">
        <PacingControl
          onPause={handlePause}
          onResume={handleResume}
          onStep={handleStep}
          onPacingChange={handlePacingChange}
        />
        <div className="game-screen__status">
          {isConnected ? (
            <span className="game-screen__status--connected">● Connected</span>
          ) : (
            <span className="game-screen__status--disconnected">○ Disconnected</span>
          )}
        </div>
      </footer>
    </div>
  );
}
