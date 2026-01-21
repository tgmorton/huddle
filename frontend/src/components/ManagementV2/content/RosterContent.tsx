// RosterContent.tsx - Roster panel content with player list and detail views

import React, { useEffect, useState, useCallback } from 'react';
import { Maximize2, RefreshCw } from 'lucide-react';
import type { RosterView } from '../types';
import { adminApi } from '../../../api/adminClient';
import type { PlayerSummary } from '../../../types/admin';
import { useManagementStore, selectLeagueId } from '../../../stores/managementStore';
import { PlayerPortrait, PlayerView } from '../components';

// === Color Helpers ===

const getOvrColor = (ovr: number): string => {
  if (ovr >= 90) return 'var(--success)';
  if (ovr >= 85) return 'var(--accent)';
  if (ovr >= 75) return 'var(--text-secondary)';
  return 'var(--text-muted)';
};

const getAgeColor = (age: number): string => {
  if (age <= 25) return 'var(--success)';
  if (age <= 28) return 'var(--text-secondary)';
  if (age <= 30) return 'var(--accent)';
  return 'var(--danger)';
};

const getContractColor = (years: number | null | undefined): string => {
  if (!years) return 'var(--text-muted)';
  if (years >= 3) return 'var(--text-secondary)';
  if (years === 2) return 'var(--accent)';
  return 'var(--danger)';
};

const formatSalary = (salary: number | undefined): string => {
  if (!salary) return 'N/A';
  if (salary >= 1000) return `$${(salary / 1000).toFixed(1)}M`;
  return `$${salary}K`;
};

// Archetype display formatting
const ARCHETYPE_LABELS: Record<string, { label: string; color: string }> = {
  // QB
  strong_arm: { label: 'ARM', color: '#ef4444' },
  pure_passer: { label: 'PASS', color: '#3b82f6' },
  field_general: { label: 'IQ', color: '#8b5cf6' },
  dual_threat: { label: 'DUAL', color: '#22c55e' },
  scrambler: { label: 'SCRAM', color: '#f59e0b' },
  // RB
  power: { label: 'PWR', color: '#ef4444' },
  speed: { label: 'SPD', color: '#22c55e' },
  elusive: { label: 'ELUS', color: '#f59e0b' },
  all_purpose: { label: 'AP', color: '#8b5cf6' },
  receiving: { label: 'RCV', color: '#3b82f6' },
  // WR
  deep_threat: { label: 'DEEP', color: '#22c55e' },
  possession: { label: 'POSS', color: '#3b82f6' },
  slot: { label: 'SLOT', color: '#f59e0b' },
  yac: { label: 'YAC', color: '#ef4444' },
  // TE
  receiving_te: { label: 'RCV', color: '#3b82f6' },
  blocking_te: { label: 'BLK', color: '#ef4444' },
  hybrid_te: { label: 'HYBD', color: '#8b5cf6' },
  // OL
  pass_protector: { label: 'PASS', color: '#3b82f6' },
  road_grader: { label: 'RUN', color: '#ef4444' },
  athletic: { label: 'ATH', color: '#22c55e' },
  technician: { label: 'TECH', color: '#8b5cf6' },
  // DL
  run_stuffer: { label: 'RUN', color: '#ef4444' },
  pass_rusher: { label: 'RUSH', color: '#22c55e' },
  interior_disruptor: { label: 'DISR', color: '#f59e0b' },
  // LB
  run_stopper: { label: 'RUN', color: '#ef4444' },
  coverage_lb: { label: 'COV', color: '#3b82f6' },
  blitzer: { label: 'BLTZ', color: '#22c55e' },
  // CB
  shutdown: { label: 'LOCK', color: '#ef4444' },
  ball_hawk: { label: 'HAWK', color: '#22c55e' },
  zone_cb: { label: 'ZONE', color: '#3b82f6' },
  // S
  center_fielder: { label: 'CF', color: '#3b82f6' },
  box_safety: { label: 'BOX', color: '#ef4444' },
  hybrid_safety: { label: 'HYBD', color: '#8b5cf6' },
  enforcer: { label: 'ENF', color: '#ef4444' },
};

const formatArchetype = (archetype: string | null | undefined): { label: string; color: string } | null => {
  if (!archetype) return null;
  return ARCHETYPE_LABELS[archetype] || { label: archetype.slice(0, 4).toUpperCase(), color: 'var(--text-muted)' };
};

// === RosterContent ===

interface RosterContentProps {
  onAddPlayerToWorkspace?: (player: { id: string; name: string; position: string; overall: number }) => void;
  view: RosterView;
  setView: (view: RosterView) => void;
}

export const RosterContent: React.FC<RosterContentProps> = ({ onAddPlayerToWorkspace, view, setView }) => {
  const [players, setPlayers] = useState<PlayerSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const leagueId = useManagementStore(selectLeagueId);
  const state = useManagementStore(s => s.state);
  const [teamAbbr, setTeamAbbr] = useState<string>('BUF');

  const loadRoster = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const roster = await adminApi.getTeamRoster(teamAbbr);
      setPlayers(roster);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load roster');
      setPlayers([]);
    } finally {
      setLoading(false);
    }
  }, [teamAbbr]);

  useEffect(() => {
    loadRoster();
  }, [loadRoster]);

  // Try to get team from franchise state
  useEffect(() => {
    if (state?.player_team_id) {
      adminApi.listTeams().then(teams => {
        const team = teams.find(t => t.id === state.player_team_id);
        if (team) {
          setTeamAbbr(team.abbreviation);
        }
      }).catch(() => {});
    }
  }, [state?.player_team_id]);

  // Group players by position
  const positionOrder = ['QB', 'RB', 'FB', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT', 'DE', 'DT', 'NT', 'OLB', 'MLB', 'ILB', 'CB', 'FS', 'SS', 'K', 'P'];
  const grouped = players.reduce((acc, player) => {
    const pos = player.position;
    if (!acc[pos]) acc[pos] = [];
    acc[pos].push(player);
    return acc;
  }, {} as Record<string, PlayerSummary[]>);

  Object.values(grouped).forEach(group => {
    group.sort((a, b) => b.overall - a.overall);
  });

  const orderedGroups = positionOrder.filter(pos => grouped[pos]?.length);

  if (loading) return null;

  if (error) {
    return (
      <div className="ref-content">
        <div className="ref-content__error">{error}</div>
        <button className="ref-content__retry" onClick={loadRoster}>
          <RefreshCw size={14} /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className="ref-content">
      {view.type === 'list' ? (
        <div className="roster-tables">
          {orderedGroups.map(pos => (
            <table key={pos} className="roster-table">
              <thead>
                <tr>
                  <th colSpan={2} className="roster-table__pos">{pos} {grouped[pos].length}</th>
                  <th>OVR</th>
                  <th>POT</th>
                  <th>AGE</th>
                  <th>SAL</th>
                  <th>YRS</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {grouped[pos].map(player => (
                  <tr key={player.id} onClick={() => setView({ type: 'player', playerId: player.id })}>
                    <td className="roster-table__portrait">
                      <PlayerPortrait
                        playerId={player.id}
                        leagueId={leagueId || undefined}
                        size="roster"
                      />
                    </td>
                    <td className="roster-table__name">
                      {player.full_name}
                      {player.player_archetype && (() => {
                        const arch = formatArchetype(player.player_archetype);
                        return arch ? (
                          <span
                            className="roster-table__archetype"
                            style={{ color: arch.color, borderColor: arch.color }}
                          >
                            {arch.label}
                          </span>
                        ) : null;
                      })()}
                    </td>
                    <td style={{ color: getOvrColor(player.overall) }}>{player.overall}</td>
                    <td style={{ color: player.potential > player.overall ? 'var(--success)' : 'var(--text-muted)' }}>{player.potential}</td>
                    <td style={{ color: getAgeColor(player.age) }}>{player.age}</td>
                    <td>{player.salary ? formatSalary(player.salary) : '—'}</td>
                    <td style={{ color: getContractColor(player.contract_year_remaining ?? undefined) }}>{player.contract_year_remaining ?? '—'}</td>
                    <td className="roster-table__action">
                      <button
                        className="roster-table__popout"
                        onClick={(e) => {
                          e.stopPropagation();
                          onAddPlayerToWorkspace?.({
                            id: player.id,
                            name: player.full_name,
                            position: player.position,
                            overall: player.overall,
                          });
                        }}
                      >
                        <Maximize2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ))}
        </div>
      ) : (
        <PlayerView
          playerId={view.playerId}
          variant="sideview"
          onBack={() => setView({ type: 'list' })}
          onPopOut={onAddPlayerToWorkspace}
        />
      )}
    </div>
  );
};

export default RosterContent;
