// StandingsContent.tsx - Division standings panel content (wired to real data)

import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw } from 'lucide-react';
import { adminApi } from '../../../api/adminClient';
import type { DivisionStandings } from '../../../types/admin';
import { useManagementStore } from '../../../stores/managementStore';

interface StandingsContentProps {
  playerTeamAbbr?: string;
}

export const StandingsContent: React.FC<StandingsContentProps> = ({ playerTeamAbbr }) => {
  const [standings, setStandings] = useState<DivisionStandings[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Get player team from management store if not provided
  const { state } = useManagementStore();
  const [teamAbbr, setTeamAbbr] = useState<string | undefined>(playerTeamAbbr);

  const loadStandings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminApi.getStandings();
      setStandings(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load standings');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStandings();
  }, [loadStandings]);

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

  if (loading) return null;

  if (error) {
    return (
      <div className="ref-content">
        <div className="ref-content__error">{error}</div>
        <button className="ref-content__retry" onClick={loadStandings}>
          <RefreshCw size={14} /> Retry
        </button>
      </div>
    );
  }

  if (standings.length === 0) {
    return (
      <div className="ref-content">
        <div className="ref-content__empty">No standings available</div>
      </div>
    );
  }

  return (
    <div className="ref-content">
      {standings.map(division => (
        <div key={division.division} className="ref-content__group">
          <div className="ref-content__group-header">{division.division}</div>
          {division.teams.map(team => (
            <div
              key={team.abbreviation}
              className={`ref-content__standing ${team.abbreviation === teamAbbr ? 'ref-content__standing--you' : ''}`}
            >
              <span>{team.rank}.</span>
              <span>{team.team_name}</span>
              <span>{team.record}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
};

export default StandingsContent;
