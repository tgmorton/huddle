// GamePane.tsx - Game day pane with sim and results

import React, { useState } from 'react';
import { Trophy, Play, Clock, TrendingUp, TrendingDown } from 'lucide-react';
import { managementApi } from '../../../../api/managementClient';
import type { GameResult } from '../../../../api/managementClient';
import { useManagementStore, selectFranchiseId } from '../../../../stores/managementStore';

interface GamePaneProps {
  eventId?: string;
  eventPayload?: {
    opponent_name?: string;
    opponent_id?: string;
    is_home?: boolean;
    week?: number;
  };
  onComplete: () => void;
}

export const GamePane: React.FC<GamePaneProps> = ({ eventId, eventPayload, onComplete }) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<GameResult | null>(null);
  const franchiseId = useManagementStore(selectFranchiseId);
  const bumpJournalVersion = useManagementStore(state => state.bumpJournalVersion);

  const opponentName = eventPayload?.opponent_name || 'Opponent';
  const isHome = eventPayload?.is_home ?? true;
  const week = eventPayload?.week || 1;

  const handleSimGame = async () => {
    if (!eventId || !franchiseId) return;

    setLoading(true);
    try {
      const gameResult = await managementApi.simGame(franchiseId, eventId);
      setResult(gameResult);
      bumpJournalVersion();
    } catch (err) {
      console.error('Game sim failed:', err);
    } finally {
      setLoading(false);
    }
  };

  // Post-game results view
  if (result) {
    const won = result.won;
    const Icon = won ? TrendingUp : TrendingDown;
    const resultClass = won ? 'pane__alert--success' : 'pane__alert--warning';
    const resultText = won ? 'Victory' : 'Defeat';

    return (
      <div className="pane pane--no-header">
        <div className="pane__body">
          {/* Result Header */}
          <div className={`pane__alert ${resultClass}`}>
            <Icon size={18} />
            <span>{resultText}</span>
          </div>

          {/* Score */}
          <div className="pane-section">
            <div className="pane-section__header">Final Score</div>
            <div className="game-score">
              <div className="game-score__team">
                <span className="game-score__name">{result.away_team}</span>
                <span className="game-score__points">{result.away_score}</span>
              </div>
              <div className="game-score__at">@</div>
              <div className="game-score__team">
                <span className="game-score__name">{result.home_team}</span>
                <span className="game-score__points">{result.home_score}</span>
              </div>
            </div>
          </div>

          {/* Team Stats */}
          <div className="pane-section">
            <div className="pane-section__header">Your Stats</div>
            <div className="ctrl-result">
              <span className="ctrl-result__label">Passing</span>
              <span className="ctrl-result__value">{result.user_stats.passing_yards} yds</span>
            </div>
            <div className="ctrl-result">
              <span className="ctrl-result__label">Rushing</span>
              <span className="ctrl-result__value">{result.user_stats.rushing_yards} yds</span>
            </div>
            <div className="ctrl-result">
              <span className="ctrl-result__label">Total Yards</span>
              <span className="ctrl-result__value">{result.user_stats.total_yards}</span>
            </div>
            <div className="ctrl-result">
              <span className="ctrl-result__label">Turnovers</span>
              <span className={`ctrl-result__value ${result.user_stats.turnovers > 0 ? 'ctrl-result__value--danger' : 'ctrl-result__value--success'}`}>
                {result.user_stats.turnovers}
              </span>
            </div>
            <div className="ctrl-result">
              <span className="ctrl-result__label">3rd Down</span>
              <span className="ctrl-result__value">{result.user_stats.third_down_pct}%</span>
            </div>
          </div>

          {/* MVP */}
          {result.mvp && (
            <div className="pane-section">
              <div className="pane-section__header">Player of the Game</div>
              <div className="ctrl-result">
                <span className="ctrl-result__label">{result.mvp.position}</span>
                <span className="ctrl-result__value">{result.mvp.name}</span>
              </div>
              <div className="ctrl-result">
                <span className="ctrl-result__label">Stats</span>
                <span className="ctrl-result__value ctrl-result__value--muted">{result.mvp.stat_line}</span>
              </div>
            </div>
          )}
        </div>

        <footer className="pane__footer">
          <button className="pane__btn pane__btn--primary" onClick={onComplete}>
            Done
          </button>
        </footer>
      </div>
    );
  }

  // Pre-game view
  return (
    <div className="pane pane--no-header">
      <div className="pane__body">
        {/* Game Info Header */}
        <div className="pane__alert pane__alert--critical">
          <Trophy size={18} />
          <span>Game Day</span>
        </div>

        {/* Matchup */}
        <div className="pane-section">
          <div className="pane-section__header">Week {week}</div>
          <div className="game-matchup">
            <span className="game-matchup__location">{isHome ? 'vs' : '@'}</span>
            <span className="game-matchup__opponent">{opponentName}</span>
          </div>
        </div>

        {/* Game Prep Summary */}
        <div className="pane-section">
          <div className="pane-section__header">Preparation</div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Scout Report</span>
            <span className="ctrl-result__value ctrl-result__value--success">Reviewed</span>
          </div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Practices</span>
            <span className="ctrl-result__value">4/4 Complete</span>
          </div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Game Prep</span>
            <span className="ctrl-result__value">Ready</span>
          </div>
        </div>

        {/* Game Options */}
        <div className="pane-section">
          <p className="pane__description pane__description--muted">
            Your team is ready. Choose how to handle this matchup.
          </p>
        </div>
      </div>

      <footer className="pane__footer">
        <button
          className="pane__btn pane__btn--secondary"
          disabled
          title="Coming soon"
        >
          <Play size={14} />
          Play Game
        </button>
        <button
          className="pane__btn pane__btn--primary"
          onClick={handleSimGame}
          disabled={loading || !franchiseId || !eventId}
        >
          <Clock size={14} />
          {loading ? 'Simulating...' : 'Sim Game'}
        </button>
      </footer>
    </div>
  );
};

export default GamePane;
