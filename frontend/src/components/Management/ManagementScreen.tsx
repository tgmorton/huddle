/**
 * ManagementScreen - Main management/franchise mode screen
 *
 * Layout:
 * ┌─────────────────────────────────────────────────────────────┐
 * │                         TOP BAR                              │
 * │  Date/Time  │  Week/Phase  │  [Speed Controls]              │
 * ├─────────────────────────────────┬───────────────────────────┤
 * │                                 │                           │
 * │         ACTIVE PANEL            │       CLIPBOARD           │
 * │                                 │   [Tabs]                  │
 * │   (Event detail / Roster /      │   [Event List]            │
 * │    Depth chart / etc.)          │                           │
 * │                                 │                           │
 * ├─────────────────────────────────┴───────────────────────────┤
 * │                         TICKER                               │
 * └─────────────────────────────────────────────────────────────┘
 */

import React, { useEffect, useState } from 'react';
import { useManagementStore } from '../../stores/managementStore';
import { useManagementWebSocket } from '../../hooks/useManagementWebSocket';
import { TopBar } from './TopBar';
import { Clipboard } from './Clipboard';
import { Ticker } from './Ticker';
import { ActivePanel } from './ActivePanel';
import { AutoPauseModal } from './AutoPauseModal';
import './ManagementScreen.css';

interface ManagementScreenProps {
  franchiseId: string;
}

export const ManagementScreen: React.FC<ManagementScreenProps> = ({ franchiseId }) => {
  const { isConnected, isLoading, error, showAutoPauseModal } = useManagementStore();

  const {
    pause,
    play,
    setSpeed,
    selectTab,
    attendEvent,
    dismissEvent,
    runPractice,
    playGame,
    simGame,
    goBack,
  } = useManagementWebSocket({ franchiseId });

  if (isLoading) {
    return (
      <div className="management-screen management-screen--loading">
        <div className="management-screen__loader">
          <div className="management-screen__spinner" />
          <div className="management-screen__loading-text">
            Loading franchise...
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="management-screen management-screen--error">
        <div className="management-screen__error">
          <div className="management-screen__error-icon">⚠️</div>
          <div className="management-screen__error-title">Connection Error</div>
          <div className="management-screen__error-message">{error}</div>
        </div>
      </div>
    );
  }

  if (!isConnected) {
    return (
      <div className="management-screen management-screen--disconnected">
        <div className="management-screen__disconnected">
          <div className="management-screen__disconnected-icon">🔌</div>
          <div className="management-screen__disconnected-text">
            Connecting to server...
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="management-screen">
      {/* Top Bar */}
      <TopBar onPause={pause} onPlay={play} onSetSpeed={setSpeed} />

      {/* Main Content */}
      <div className="management-screen__content">
        {/* Active Panel (Left) */}
        <div className="management-screen__panel">
          <ActivePanel
            onGoBack={goBack}
            onRunPractice={runPractice}
            onPlayGame={playGame}
            onSimGame={simGame}
          />
        </div>

        {/* Clipboard (Right) */}
        <div className="management-screen__clipboard">
          <Clipboard
            onSelectTab={selectTab}
            onAttendEvent={attendEvent}
            onDismissEvent={dismissEvent}
          />
        </div>
      </div>

      {/* Ticker (Bottom) */}
      <Ticker />

      {/* Auto-pause Modal */}
      {showAutoPauseModal && <AutoPauseModal onDismiss={play} />}
    </div>
  );
};

// Wrapper component that handles franchise creation
export const ManagementScreenWrapper: React.FC = () => {
  const [franchiseId, setFranchiseId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const createFranchise = async (signal?: AbortSignal) => {
    setIsCreating(true);
    setCreateError(null);

    try {
      const response = await fetch('http://localhost:8000/api/v1/management/franchise', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          team_id: crypto.randomUUID(),
          team_name: 'My Team',
          season_year: 2024,
          start_phase: 'REGULAR_SEASON',
        }),
        signal,
      });

      if (!response.ok) {
        throw new Error('Failed to create franchise');
      }

      const data = await response.json();

      // Only set state if not aborted
      if (!signal?.aborted) {
        setFranchiseId(data.franchise_id);
      }
    } catch (err) {
      // Ignore abort errors
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      if (!signal?.aborted) {
        setCreateError(err instanceof Error ? err.message : 'Unknown error');
      }
    } finally {
      if (!signal?.aborted) {
        setIsCreating(false);
      }
    }
  };

  // Auto-create franchise on mount (for demo purposes)
  useEffect(() => {
    const controller = new AbortController();
    createFranchise(controller.signal);

    return () => {
      controller.abort();
    };
  }, []);

  if (isCreating) {
    return (
      <div className="management-screen management-screen--loading">
        <div className="management-screen__loader">
          <div className="management-screen__spinner" />
          <div className="management-screen__loading-text">
            Creating franchise...
          </div>
        </div>
      </div>
    );
  }

  if (createError) {
    return (
      <div className="management-screen management-screen--error">
        <div className="management-screen__error">
          <div className="management-screen__error-icon">⚠️</div>
          <div className="management-screen__error-title">Failed to Create Franchise</div>
          <div className="management-screen__error-message">{createError}</div>
          <button
            className="management-screen__retry-btn"
            onClick={() => createFranchise()}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!franchiseId) {
    return null;
  }

  return <ManagementScreen franchiseId={franchiseId} />;
};
