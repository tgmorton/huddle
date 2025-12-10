/**
 * Scoreboard component - displays clock, score, and down/distance
 */

import { useGameStore } from '../../stores/gameStore';
import './Scoreboard.css';

export function Scoreboard() {
  const { gameState, homeTeam, awayTeam } = useGameStore();

  if (!gameState || !homeTeam || !awayTeam) {
    return <div className="scoreboard scoreboard--loading">Loading...</div>;
  }

  const { clock, score, down_state, possession } = gameState;
  const isHomePossession = possession.team_with_ball === homeTeam.id;

  return (
    <div className="scoreboard">
      <div className="scoreboard__teams">
        <div
          className={`scoreboard__team ${isHomePossession ? 'scoreboard__team--possession' : ''}`}
          style={{ '--team-color': homeTeam.primary_color } as React.CSSProperties}
        >
          <span className="scoreboard__team-name">{homeTeam.abbreviation}</span>
          <span className="scoreboard__team-score">{score.home_score}</span>
          <span className="scoreboard__team-timeouts">
            {'●'.repeat(possession.home_timeouts)}
            {'○'.repeat(3 - possession.home_timeouts)}
          </span>
        </div>

        <div className="scoreboard__center">
          <div className="scoreboard__clock">
            <span className="scoreboard__quarter">Q{clock.quarter}</span>
            <span className="scoreboard__time">{clock.display}</span>
          </div>
          <div className="scoreboard__down">
            <span className="scoreboard__down-text">{down_state.display}</span>
            <span className="scoreboard__field-pos">{down_state.field_position_display}</span>
          </div>
        </div>

        <div
          className={`scoreboard__team ${!isHomePossession ? 'scoreboard__team--possession' : ''}`}
          style={{ '--team-color': awayTeam.primary_color } as React.CSSProperties}
        >
          <span className="scoreboard__team-name">{awayTeam.abbreviation}</span>
          <span className="scoreboard__team-score">{score.away_score}</span>
          <span className="scoreboard__team-timeouts">
            {'●'.repeat(possession.away_timeouts)}
            {'○'.repeat(3 - possession.away_timeouts)}
          </span>
        </div>
      </div>
    </div>
  );
}
