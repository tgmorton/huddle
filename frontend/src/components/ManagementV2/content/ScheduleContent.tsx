// ScheduleContent.tsx - Season schedule panel content (wired to real data)

import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw } from 'lucide-react';
import { adminApi } from '../../../api/adminClient';
import type { ScheduledGame, LeagueSummary } from '../../../types/admin';
import { useManagementStore } from '../../../stores/managementStore';

interface ScheduleContentProps {
  playerTeamAbbr?: string;
}

export const ScheduleContent: React.FC<ScheduleContentProps> = ({ playerTeamAbbr }) => {
  const [schedule, setSchedule] = useState<ScheduledGame[]>([]);
  const [league, setLeague] = useState<LeagueSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Get player team from management store if not provided
  const { state } = useManagementStore();
  const [teamAbbr, setTeamAbbr] = useState<string | undefined>(playerTeamAbbr);

  const loadSchedule = useCallback(async () => {
    if (!teamAbbr) return;

    setLoading(true);
    setError(null);
    try {
      const [scheduleData, leagueData] = await Promise.all([
        adminApi.getSchedule(undefined, teamAbbr),
        adminApi.getLeague(),
      ]);
      setSchedule(scheduleData);
      setLeague(leagueData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load schedule');
    } finally {
      setLoading(false);
    }
  }, [teamAbbr]);

  useEffect(() => {
    if (teamAbbr) {
      loadSchedule();
    }
  }, [teamAbbr, loadSchedule]);

  // Try to get team abbr from franchise state
  useEffect(() => {
    if (!playerTeamAbbr && state?.player_team_id) {
      adminApi.listTeams().then(teams => {
        const team = teams.find(t => t.id === state.player_team_id);
        if (team) {
          setTeamAbbr(team.abbreviation);
        }
      }).catch(() => {});
    }
  }, [playerTeamAbbr, state?.player_team_id]);

  // Format the game result or status
  const formatGameResult = (game: ScheduledGame, teamAbbr: string) => {
    if (!game.is_played) {
      return 'Upcoming';
    }

    const isHome = game.home_team === teamAbbr;
    const teamScore = isHome ? game.home_score : game.away_score;
    const oppScore = isHome ? game.away_score : game.home_score;

    if (teamScore === null || oppScore === null) {
      return 'Upcoming';
    }

    const won = teamScore > oppScore;
    const tied = teamScore === oppScore;

    if (tied) {
      return `T ${teamScore}-${oppScore}`;
    }
    return `${won ? 'W' : 'L'} ${teamScore}-${oppScore}`;
  };

  // Get result class
  const getResultClass = (game: ScheduledGame, teamAbbr: string) => {
    if (!game.is_played || game.home_score === null || game.away_score === null) {
      return '';
    }

    const isHome = game.home_team === teamAbbr;
    const teamScore = isHome ? game.home_score : game.away_score;
    const oppScore = isHome ? game.away_score : game.home_score;

    if (teamScore > oppScore) return 'ref-content__result--win';
    if (teamScore < oppScore) return 'ref-content__result--loss';
    return 'ref-content__result--tie';
  };

  if (!teamAbbr) {
    return (
      <div className="ref-content">
        <div className="ref-content__empty">Select a team to view schedule</div>
      </div>
    );
  }

  if (loading) return null;

  if (error) {
    return (
      <div className="ref-content">
        <div className="ref-content__error">{error}</div>
        <button className="ref-content__retry" onClick={loadSchedule}>
          <RefreshCw size={14} /> Retry
        </button>
      </div>
    );
  }

  if (schedule.length === 0) {
    return (
      <div className="ref-content">
        <div className="ref-content__empty">No games scheduled</div>
      </div>
    );
  }

  const currentWeek = league?.current_week || 1;
  const totalWeeks = 17; // Regular season

  return (
    <div className="ref-content">
      <div className="ref-content__stat-row">
        <span className="ref-content__stat">Week {currentWeek}</span>
        <span className="ref-content__stat-label">of {totalWeeks}</span>
      </div>
      <div className="ref-content__group">
        {schedule.map(game => {
          const isHome = game.home_team === teamAbbr;
          const opponent = isHome ? game.away_team : game.home_team;
          const prefix = isHome ? 'vs' : '@';
          const isCurrent = game.week === currentWeek && !game.is_played;
          const isPast = game.is_played;

          return (
            <div
              key={game.id}
              className={`ref-content__schedule-item ${
                isCurrent ? 'ref-content__schedule-item--current' : ''
              } ${isPast ? 'ref-content__schedule-item--past' : ''}`}
            >
              <span>W{game.week}</span>
              <span>{prefix} {opponent}</span>
              <span className={getResultClass(game, teamAbbr)}>
                {formatGameResult(game, teamAbbr)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ScheduleContent;
