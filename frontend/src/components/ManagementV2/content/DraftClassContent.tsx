// DraftClassContent.tsx - Draft class prospects list (wired to real data)

import React, { useEffect, useState, useCallback } from 'react';
import { RefreshCw, Filter, Maximize2, Star, Check } from 'lucide-react';
import { adminApi } from '../../../api/adminClient';
import type { PlayerSummary } from '../../../types/admin';
import { managementApi, type ProspectData } from '../../../api/managementClient';
import { useManagementStore } from '../../../stores/managementStore';

// Position groups for filtering
const POSITION_GROUPS: Record<string, string[]> = {
  'OL': ['LT', 'LG', 'C', 'RG', 'RT'],
  'DL': ['DE', 'DT', 'NT'],
  'LB': ['MLB', 'ILB', 'OLB'],
  'S': ['FS', 'SS'],
};

// Position filter options - use groups for UI, expand for filtering
const POSITION_FILTERS = [
  { value: '', label: 'All' },
  { value: 'QB', label: 'QB' },
  { value: 'RB', label: 'RB' },
  { value: 'FB', label: 'FB' },
  { value: 'WR', label: 'WR' },
  { value: 'TE', label: 'TE' },
  { value: 'OL', label: 'OL' },  // Group: LT, LG, C, RG, RT
  { value: 'DL', label: 'DL' },  // Group: DE, DT, NT
  { value: 'LB', label: 'LB' },  // Group: MLB, ILB, OLB
  { value: 'CB', label: 'CB' },
  { value: 'S', label: 'S' },    // Group: FS, SS
  { value: 'K', label: 'K' },
  { value: 'P', label: 'P' },
];

// Color helpers
const getOvrColor = (ovr: number): string => {
  if (ovr >= 85) return 'var(--success)';
  if (ovr >= 75) return 'var(--accent)';
  if (ovr >= 65) return 'var(--text-secondary)';
  return 'var(--text-muted)';
};

const getRoundColor = (round: number | null): string => {
  if (!round) return 'var(--text-muted)';
  if (round === 1) return 'var(--success)';
  if (round <= 3) return 'var(--accent)';
  if (round <= 5) return 'var(--text-secondary)';
  return 'var(--text-muted)';
};

// Helper for potential future use: returns color based on percentile ranking
export const getPercentileColor = (pct: number | null): string => {
  if (pct === null) return 'var(--text-muted)';
  if (pct >= 90) return 'var(--success)';
  if (pct >= 75) return 'var(--accent)';
  if (pct >= 50) return 'var(--text-secondary)';
  return 'var(--text-muted)';
};

interface DraftClassContentProps {
  onSelectPlayer?: (player: PlayerSummary) => void;
  onPopoutPlayer?: (player: PlayerSummary, e: React.MouseEvent) => void;
  selectedPlayerId?: string;
}

export const DraftClassContent: React.FC<DraftClassContentProps> = ({
  onSelectPlayer,
  onPopoutPlayer,
  selectedPlayerId,
}) => {
  const [allProspects, setAllProspects] = useState<ProspectData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [positionFilter, setPositionFilter] = useState('');
  const [onBoard, setOnBoard] = useState<Set<string>>(new Set());
  const [addingToBoard, setAddingToBoard] = useState<string | null>(null);
  const { franchiseId } = useManagementStore();

  const loadDraftClass = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (franchiseId) {
        // Load detailed prospect data from management API
        const data = await managementApi.getDraftProspects(franchiseId);
        setAllProspects(data.prospects);
      } else {
        // Fallback to basic admin API if no franchise
        const data = await adminApi.getDraftClass(undefined, 300);
        // Convert to ProspectData format (minimal)
        setAllProspects(data.map(p => ({
          player_id: p.id,
          name: p.full_name,
          position: p.position,
          college: '',
          age: p.age,
          height: '',
          weight: 0,
          scouted_percentage: 0,
          interviewed: false,
          private_workout: false,
          combine: {
            forty_yard_dash: null,
            forty_percentile: null,
            bench_press_reps: null,
            bench_percentile: null,
            vertical_jump: null,
            vertical_percentile: null,
            broad_jump: null,
            broad_percentile: null,
          },
          scout_estimates: [],
          overall_projection: p.overall,
          projected_round: null,
        })));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load draft class');
    } finally {
      setLoading(false);
    }
  }, [franchiseId]);

  useEffect(() => {
    loadDraftClass();
  }, [loadDraftClass]);

  // Load draft board status to know which prospects are already on board
  useEffect(() => {
    if (!franchiseId) return;

    const loadBoardStatus = async () => {
      try {
        const data = await managementApi.getDraftBoard(franchiseId);
        setOnBoard(new Set(data.entries.map(e => e.prospect_id)));
      } catch (err) {
        console.error('Failed to load draft board status:', err);
      }
    };

    loadBoardStatus();
  }, [franchiseId]);

  // Add to board handler
  const handleAddToBoard = useCallback(async (prospectId: string) => {
    if (!franchiseId || addingToBoard) return;

    setAddingToBoard(prospectId);
    try {
      await managementApi.addToBoard(franchiseId, prospectId);
      setOnBoard(prev => new Set(prev).add(prospectId));
    } catch (err) {
      console.error('Failed to add to board:', err);
    } finally {
      setAddingToBoard(null);
    }
  }, [franchiseId, addingToBoard]);

  // Filter prospects client-side based on position group
  const filteredProspects = positionFilter
    ? allProspects.filter(p => {
        const groupPositions = POSITION_GROUPS[positionFilter];
        if (groupPositions) {
          return groupPositions.includes(p.position);
        }
        return p.position === positionFilter;
      })
    : allProspects;

  // Sort by OVR and assign ranks within the filtered group
  const prospects = [...filteredProspects]
    .sort((a, b) => b.overall_projection - a.overall_projection)
    .map((p, i) => ({ ...p, rank: i + 1 }));

  // Convert ProspectData to PlayerSummary for callbacks
  const toPlayerSummary = (p: ProspectData): PlayerSummary => ({
    id: p.player_id,
    first_name: p.name.split(' ')[0] || '',
    last_name: p.name.split(' ').slice(1).join(' ') || '',
    full_name: p.name,
    position: p.position,
    overall: p.overall_projection,
    potential: p.overall_projection,
    age: p.age,
    experience: 0,
    jersey_number: 0,
    team_abbr: null,
    salary: null,
    contract_year_remaining: null,
  });

  if (loading) return null;

  if (error) {
    return (
      <div className="ref-content">
        <div className="ref-content__error">{error}</div>
        <button className="ref-content__retry" onClick={loadDraftClass}>
          <RefreshCw size={14} /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className="ref-content">
      {/* Filters */}
      <div className="ref-content__filters">
        <div className="ref-content__filter-group">
          <Filter size={12} />
          <select
            value={positionFilter}
            onChange={(e) => setPositionFilter(e.target.value)}
            className="ref-content__select"
          >
            {POSITION_FILTERS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Results count */}
      <div className="ref-content__count">
        {prospects.length} prospect{prospects.length !== 1 ? 's' : ''}
      </div>

      {/* Prospect table */}
      {prospects.length === 0 ? (
        <div className="ref-content__empty">No prospects match filters</div>
      ) : (
        <table className="roster-table roster-table--prospects">
          <thead>
            <tr>
              <th></th>
              <th></th>
              <th className="roster-table__pos">Prospect</th>
              <th>Proj</th>
              <th>OVR</th>
              <th>Scouted</th>
            </tr>
          </thead>
          <tbody>
            {prospects.map(prospect => (
              <tr
                key={prospect.player_id}
                className={`prospect-row ${prospect.player_id === selectedPlayerId ? 'roster-table__row--selected' : ''} ${onBoard.has(prospect.player_id) ? 'prospect-row--on-board' : ''}`}
                onClick={() => onSelectPlayer?.(toPlayerSummary(prospect))}
              >
                <td className="roster-table__pos-tag">{prospect.position}</td>
                <td className="roster-table__rank">{prospect.rank}</td>
                <td className="roster-table__name roster-table__name--nowrap">{prospect.name}</td>
                <td style={{ color: getRoundColor(prospect.projected_round) }}>
                  {prospect.projected_round ? `R${prospect.projected_round}` : '—'}
                </td>
                <td style={{ color: getOvrColor(prospect.overall_projection) }}>
                  {prospect.overall_projection}
                </td>
                <td className="roster-table__scout-cell">
                  <div className="roster-table__scout-content">
                    <div className="roster-table__scout-bar">
                      <div
                        className="roster-table__scout-fill"
                        style={{ width: `${prospect.scouted_percentage}%` }}
                      />
                    </div>
                    <span>{prospect.scouted_percentage}%</span>
                  </div>
                  <div className="prospect-row__actions">
                    <button
                      className="prospect-row__btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        onPopoutPlayer?.(toPlayerSummary(prospect), e);
                      }}
                      title="Open in workspace"
                    >
                      <Maximize2 size={14} />
                    </button>
                    <button
                      className={`prospect-row__btn ${onBoard.has(prospect.player_id) ? 'prospect-row__btn--on-board' : ''}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (!onBoard.has(prospect.player_id)) {
                          handleAddToBoard(prospect.player_id);
                        }
                      }}
                      title={onBoard.has(prospect.player_id) ? 'On your board' : 'Add to board'}
                      disabled={addingToBoard === prospect.player_id || onBoard.has(prospect.player_id)}
                    >
                      {onBoard.has(prospect.player_id) ? <Check size={14} /> : <Star size={14} />}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default DraftClassContent;
