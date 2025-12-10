/**
 * Stats panel showing simulation statistics
 */

import type { SandboxState } from '../../types/sandbox';
import { useSandboxStore } from '../../stores/sandboxStore';

interface StatsPanelProps {
  state: SandboxState;
}

export function StatsPanel({ state }: StatsPanelProps) {
  const { lastTick } = useSandboxStore();

  const outcomeText = {
    in_progress: 'In Progress',
    rusher_win: 'Rusher Wins (Pressure!)',
    blocker_win: 'Blocker Wins (Block Sustained)',
    pancake: 'Pancake! (Blocker Dominates)',
  }[state.outcome] || state.outcome;

  const outcomeColor = {
    in_progress: '#888',
    rusher_win: '#ef4444',
    blocker_win: '#3b82f6',
    pancake: '#3b82f6',
  }[state.outcome] || '#888';

  const totalContests = state.stats.rusher_wins_contest + state.stats.blocker_wins_contest + state.stats.neutral_contests;
  const rusherWinPct = totalContests > 0 ? (state.stats.rusher_wins_contest / totalContests * 100).toFixed(0) : '0';
  const blockerWinPct = totalContests > 0 ? (state.stats.blocker_wins_contest / totalContests * 100).toFixed(0) : '0';

  return (
    <div className="stats-panel">
      <h3>Simulation Stats</h3>

      <div className="outcome-display" style={{ borderColor: outcomeColor }}>
        <span className="outcome-label">Outcome</span>
        <span className="outcome-value" style={{ color: outcomeColor }}>
          {outcomeText}
        </span>
      </div>

      <div className="stats-grid">
        <div className="stat-item">
          <span className="stat-label">Ticks</span>
          <span className="stat-value">{state.current_tick} / {state.max_ticks}</span>
        </div>

        <div className="stat-item">
          <span className="stat-label">Rusher Depth</span>
          <span className="stat-value">
            {lastTick ? lastTick.rusher_depth.toFixed(2) : '0.00'} yd
          </span>
        </div>

        <div className="stat-item">
          <span className="stat-label">QB Zone</span>
          <span className="stat-value">{state.qb_zone_depth} yd</span>
        </div>

        <div className="stat-item">
          <span className="stat-label">Tick Rate</span>
          <span className="stat-value">{state.tick_rate_ms} ms</span>
        </div>
      </div>

      <div className="contest-stats">
        <h4>Contest Results</h4>
        <div className="contest-bar">
          <div
            className="contest-segment rusher"
            style={{ width: `${rusherWinPct}%` }}
            title={`Rusher: ${state.stats.rusher_wins_contest}`}
          />
          <div
            className="contest-segment neutral"
            style={{ width: `${100 - parseInt(rusherWinPct) - parseInt(blockerWinPct)}%` }}
            title={`Neutral: ${state.stats.neutral_contests}`}
          />
          <div
            className="contest-segment blocker"
            style={{ width: `${blockerWinPct}%` }}
            title={`Blocker: ${state.stats.blocker_wins_contest}`}
          />
        </div>
        <div className="contest-legend">
          <span className="legend-item rusher">Rusher: {state.stats.rusher_wins_contest}</span>
          <span className="legend-item neutral">Neutral: {state.stats.neutral_contests}</span>
          <span className="legend-item blocker">Blocker: {state.stats.blocker_wins_contest}</span>
        </div>
      </div>

      {lastTick && (
        <div className="last-tick">
          <h4>Last Tick</h4>
          <div className="tick-details">
            <div className="tick-techniques">
              <span className="rusher-tech">{lastTick.rusher_technique}</span>
              <span className="vs">vs</span>
              <span className="blocker-tech">{lastTick.blocker_technique}</span>
            </div>
            <div className="tick-scores">
              <span>Rusher: {lastTick.rusher_score.toFixed(1)}</span>
              <span>Blocker: {lastTick.blocker_score.toFixed(1)}</span>
              <span className={lastTick.margin > 0 ? 'positive' : lastTick.margin < 0 ? 'negative' : ''}>
                Margin: {lastTick.margin > 0 ? '+' : ''}{lastTick.margin.toFixed(1)}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
