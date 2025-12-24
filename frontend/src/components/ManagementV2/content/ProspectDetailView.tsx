// ProspectDetailView.tsx - Prospect detail view for sidebar (matches PlayerDetailView pattern)

import React, { useEffect, useState } from 'react';
import { Maximize2, ChevronDown, ChevronRight, Eye, EyeOff, HelpCircle } from 'lucide-react';
import { managementApi, type ProspectData } from '../../../api/managementClient';
import { StatBar, PlayerPortrait } from '../components';
import { useManagementStore, selectLeagueId } from '../../../stores/managementStore';

// Get overall scout grade
const getOverallGrade = (overall: number): string => {
  if (overall >= 85) return 'A';
  if (overall >= 80) return 'A-';
  if (overall >= 75) return 'B+';
  if (overall >= 70) return 'B';
  if (overall >= 65) return 'B-';
  if (overall >= 60) return 'C+';
  if (overall >= 55) return 'C';
  return 'C-';
};

// Get color for grade
const getGradeColor = (overall: number): string => {
  if (overall >= 80) return 'var(--success)';
  if (overall >= 70) return 'var(--accent)';
  if (overall >= 60) return 'var(--text-secondary)';
  return 'var(--text-muted)';
};

// Get percentile color
const getPercentileColor = (percentile: number | null): string => {
  if (percentile === null) return 'var(--text-secondary)';
  if (percentile >= 90) return 'var(--success)';
  if (percentile >= 75) return 'var(--accent)';
  if (percentile >= 50) return 'var(--text-secondary)';
  if (percentile >= 25) return 'var(--warning)';
  return 'var(--danger)';
};

// Format attribute name
const formatAttrName = (name: string): string => {
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

interface ProspectDetailViewProps {
  prospectId: string;
  franchiseId: string;
  onPopOut?: (prospect: { id: string; name: string; position: string; overall: number }) => void;
  onBack: () => void;
}

export const ProspectDetailView: React.FC<ProspectDetailViewProps> = ({
  prospectId,
  franchiseId,
  onPopOut,
  onBack,
}) => {
  const [prospect, setProspect] = useState<ProspectData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [combineExpanded, setCombineExpanded] = useState(false);
  const leagueId = useManagementStore(selectLeagueId);

  useEffect(() => {
    const fetchProspect = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await managementApi.getProspect(franchiseId, prospectId);
        setProspect(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load prospect');
      } finally {
        setLoading(false);
      }
    };
    fetchProspect();
  }, [prospectId, franchiseId]);

  // No loading state - avoids layout jump since data loads quickly
  if (loading) {
    return null;
  }

  if (error || !prospect) {
    return (
      <div className="player-detail">
        <div className="player-detail__error">{error || 'Prospect not found'}</div>
        <button className="player-detail__back" onClick={onBack}>← Back to prospects</button>
      </div>
    );
  }

  const grade = getOverallGrade(prospect.overall_projection);

  return (
    <div className="player-detail">
      {/* Header */}
      <div className="player-detail__header">
        <PlayerPortrait
          playerId={prospectId}
          leagueId={leagueId ?? undefined}
          size="lg"
          status="prospect"
        />
        <div className="player-detail__info">
          <h3 className="player-detail__name">{prospect.name}</h3>
          <span className="player-detail__pos">
            {prospect.position} • {prospect.college}
          </span>
        </div>
        <span className="player-detail__ovr" style={{ color: getGradeColor(prospect.overall_projection) }}>
          {grade}
        </span>
        {onPopOut && (
          <button
            className="player-detail__popout"
            onClick={() => onPopOut({
              id: prospect.player_id,
              name: prospect.name,
              position: prospect.position,
              overall: prospect.overall_projection,
            })}
            title="Open in workspace"
          >
            <Maximize2 size={14} />
          </button>
        )}
      </div>

      <div className="player-detail__body">
        {/* Scouting Progress */}
        <div className="player-detail__section">
          <div className="player-detail__label">Scouting Progress</div>
          <div className="prospect-certainty">
            <div className="prospect-certainty__bar">
              <div
                className="prospect-certainty__fill"
                style={{ width: `${prospect.scouted_percentage}%` }}
              />
            </div>
            <div className="prospect-certainty__info">
              <span className="prospect-certainty__label">Scouted: {prospect.scouted_percentage}%</span>
              <div className="prospect-certainty__badges">
                {prospect.interviewed ? (
                  <span className="prospect-badge prospect-badge--yes"><Eye size={10} /> Interviewed</span>
                ) : (
                  <span className="prospect-badge prospect-badge--no"><EyeOff size={10} /> Not Interviewed</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Scout Estimates */}
        {prospect.scout_estimates && prospect.scout_estimates.length > 0 && (
          <div className="player-detail__section">
            <div className="player-detail__label">
              Scout Assessment
              <HelpCircle size={10} style={{ marginLeft: 4, opacity: 0.5 }} />
            </div>
            <div className="player-detail__key-stats">
              {prospect.scout_estimates.map((est) => (
                <StatBar
                  key={est.name}
                  label={formatAttrName(est.name)}
                  value={est.projected_value}
                  min={est.min_estimate}
                  max={est.max_estimate}
                />
              ))}
            </div>
          </div>
        )}

        {/* Bio */}
        <div className="player-detail__section">
          <div className="player-detail__label">Biographical</div>
          <div className="player-detail__row">
            <span>Age {prospect.age}</span>
            <span>{prospect.height}, {prospect.weight} lbs</span>
          </div>
          <div className="player-detail__row">
            <span>Projection</span>
            <span style={{ color: 'var(--accent)' }}>
              {prospect.projected_round ? `Round ${prospect.projected_round}` : 'Unknown'}
            </span>
          </div>
        </div>

        {/* Combine - Collapsible */}
        {prospect.combine && (prospect.combine.forty_yard_dash || prospect.combine.bench_press_reps) && (
          <div className="player-detail__section player-detail__section--collapsible">
            <button
              className="player-detail__label player-detail__label--toggle"
              onClick={() => setCombineExpanded(!combineExpanded)}
            >
              <span>Combine Measurables</span>
              {combineExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            </button>
            {combineExpanded && (
              <div className="player-detail__combine">
                {prospect.combine.forty_yard_dash && (
                  <div className="player-detail__row">
                    <span>40-Yard</span>
                    <span style={{ color: getPercentileColor(prospect.combine.forty_percentile) }}>
                      {prospect.combine.forty_yard_dash.toFixed(2)}s
                    </span>
                  </div>
                )}
                {prospect.combine.bench_press_reps && (
                  <div className="player-detail__row">
                    <span>Bench Press</span>
                    <span style={{ color: getPercentileColor(prospect.combine.bench_percentile) }}>
                      {prospect.combine.bench_press_reps} reps
                    </span>
                  </div>
                )}
                {prospect.combine.vertical_jump && (
                  <div className="player-detail__row">
                    <span>Vertical</span>
                    <span style={{ color: getPercentileColor(prospect.combine.vertical_percentile) }}>
                      {prospect.combine.vertical_jump}"
                    </span>
                  </div>
                )}
                {prospect.combine.broad_jump && (
                  <div className="player-detail__row">
                    <span>Broad Jump</span>
                    <span style={{ color: getPercentileColor(prospect.combine.broad_percentile) }}>
                      {prospect.combine.broad_jump}"
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="player-detail__actions">
        <button className="player-detail__action">Add to Board</button>
        <button className="player-detail__action player-detail__action--secondary">Request Workout</button>
      </div>
    </div>
  );
};

export default ProspectDetailView;
