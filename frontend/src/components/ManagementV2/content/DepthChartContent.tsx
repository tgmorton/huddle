// DepthChartContent.tsx - Depth chart panel with stat table (wired to real data)

import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw } from 'lucide-react';
import { adminApi } from '../../../api/adminClient';
import type { DepthChart, DepthChartEntry } from '../../../types/admin';
import { useManagementStore } from '../../../stores/managementStore';

// === Constants ===

// Slot display order for offense
const OFFENSE_ORDER = ['QB1', 'QB2', 'RB1', 'RB2', 'FB1', 'WR1', 'WR2', 'WR3', 'WR4', 'TE1', 'TE2', 'LT1', 'LG1', 'C1', 'RG1', 'RT1'];

// Slot display order for defense
const DEFENSE_ORDER = ['DE1', 'DE2', 'DT1', 'DT2', 'MLB1', 'OLB1', 'OLB2', 'CB1', 'CB2', 'FS1', 'SS1'];

// Slot display order for special teams
const SPECIAL_ORDER = ['K1', 'P1', 'LS1'];

// === Helpers ===

// Color scale for stat values
const getStatColor = (value: number | null): string => {
  if (value === null) return 'var(--text-muted)';
  if (value >= 90) return 'var(--success)';
  if (value >= 85) return 'var(--accent)';
  if (value >= 70) return 'var(--text-secondary)';
  if (value >= 60) return 'var(--text-muted)';
  return 'var(--danger)';
};

// Extract position group from slot (e.g., "QB1" -> "QB")
const getPositionFromSlot = (slot: string): string => {
  return slot.replace(/[0-9]/g, '');
};

// Get depth number from slot (e.g., "QB1" -> 1)
const getDepthFromSlot = (slot: string): number => {
  const match = slot.match(/(\d+)/);
  return match ? parseInt(match[1], 10) : 1;
};

// === DepthChartSection ===

interface DepthChartSectionProps {
  title: string;
  entries: DepthChartEntry[];
  slotOrder: string[];
}

const DepthChartSection: React.FC<DepthChartSectionProps> = ({ title, entries, slotOrder }) => {
  // Create a map for quick lookup
  const entryMap = new Map(entries.map(e => [e.slot, e]));

  // Group by position
  const positionGroups: Record<string, DepthChartEntry[]> = {};

  slotOrder.forEach(slot => {
    const entry = entryMap.get(slot);
    if (entry) {
      const pos = getPositionFromSlot(slot);
      if (!positionGroups[pos]) {
        positionGroups[pos] = [];
      }
      positionGroups[pos].push(entry);
    }
  });

  // Get unique positions in order
  const orderedPositions = [...new Set(slotOrder.map(getPositionFromSlot))];

  return (
    <div className="depth-section">
      <div className="depth-section__title">{title}</div>
      <div className="depth-tables">
        {orderedPositions.map(pos => {
          const posEntries = positionGroups[pos] || [];
          if (posEntries.length === 0) return null;

          return (
            <table key={pos} className="roster-table">
              <thead>
                <tr>
                  <th colSpan={2} className="roster-table__pos">{pos}</th>
                  <th>OVR</th>
                </tr>
              </thead>
              <tbody>
                {posEntries.map(entry => (
                  <tr key={entry.slot}>
                    <td className="depth-table__depth">
                      <span className={getDepthFromSlot(entry.slot) === 1 ? 'depth-starter' : 'depth-backup'}>
                        {getDepthFromSlot(entry.slot)}
                      </span>
                    </td>
                    <td className="roster-table__name">{entry.player_name || '—'}</td>
                    <td style={{ color: getStatColor(entry.overall) }}>{entry.overall ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          );
        })}
      </div>
    </div>
  );
};

// === DepthChartContent ===

interface DepthChartContentProps {
  playerTeamAbbr?: string;
}

export const DepthChartContent: React.FC<DepthChartContentProps> = ({ playerTeamAbbr }) => {
  const [depthChart, setDepthChart] = useState<DepthChart | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Get player team from management store if not provided
  const { state } = useManagementStore();
  const [teamAbbr, setTeamAbbr] = useState<string | undefined>(playerTeamAbbr);

  const loadDepthChart = useCallback(async () => {
    if (!teamAbbr) return;

    setLoading(true);
    setError(null);
    try {
      const data = await adminApi.getTeamDepthChart(teamAbbr);
      setDepthChart(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load depth chart');
    } finally {
      setLoading(false);
    }
  }, [teamAbbr]);

  useEffect(() => {
    if (teamAbbr) {
      loadDepthChart();
    }
  }, [teamAbbr, loadDepthChart]);

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

  if (!teamAbbr) {
    return (
      <div className="ref-content">
        <div className="ref-content__empty">Select a team to view depth chart</div>
      </div>
    );
  }

  if (loading) return null;

  if (error) {
    return (
      <div className="ref-content">
        <div className="ref-content__error">{error}</div>
        <button className="ref-content__retry" onClick={loadDepthChart}>
          <RefreshCw size={14} /> Retry
        </button>
      </div>
    );
  }

  if (!depthChart) {
    return (
      <div className="ref-content">
        <div className="ref-content__empty">No depth chart available</div>
      </div>
    );
  }

  return (
    <div className="ref-content">
      <DepthChartSection
        title="Offense"
        entries={depthChart.offense}
        slotOrder={OFFENSE_ORDER}
      />
      <DepthChartSection
        title="Defense"
        entries={depthChart.defense}
        slotOrder={DEFENSE_ORDER}
      />
      <DepthChartSection
        title="Special Teams"
        entries={depthChart.special_teams}
        slotOrder={SPECIAL_ORDER}
      />
    </div>
  );
};

export default DepthChartContent;
