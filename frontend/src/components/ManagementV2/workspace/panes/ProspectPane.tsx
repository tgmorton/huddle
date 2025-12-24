// ProspectPane.tsx - Prospect detail pane for workspace (matches PlayerPane design)

import React, { useEffect, useState } from 'react';
import { ChevronDown, ChevronRight, Eye, EyeOff } from 'lucide-react';
import { managementApi, type ProspectData } from '../../../../api/managementClient';
import { StatBar, PlayerPortrait } from '../../components';
import { useManagementStore, selectLeagueId } from '../../../../stores/managementStore';

// Get color for percentile
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

interface ProspectPaneProps {
  playerId: string;
  franchiseId?: string;
  onComplete: () => void;
}

export const ProspectPane: React.FC<ProspectPaneProps> = ({ playerId, franchiseId }) => {
  const [prospect, setProspect] = useState<ProspectData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const leagueId = useManagementStore(selectLeagueId);
  // Collapsible section states
  const [sections, setSections] = useState({
    scouting: true,
    scoutAssessment: true,
    bio: false,
    combine: false,
  });

  const toggleSection = (section: keyof typeof sections) => {
    setSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  useEffect(() => {
    const fetchProspect = async () => {
      setLoading(true);
      setError(null);

      if (!franchiseId) {
        setError('No franchise selected');
        setLoading(false);
        return;
      }

      try {
        const data = await managementApi.getProspect(franchiseId, playerId);
        setProspect(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load prospect');
      } finally {
        setLoading(false);
      }
    };
    fetchProspect();
  }, [playerId, franchiseId]);

  // No loading state - avoids layout jump since data loads quickly
  if (loading) {
    return null;
  }

  if (error || !prospect) {
    return (
      <div className="pane pane--no-header">
        <div className="pane__body pane__body--placeholder">
          <p>{error || 'Prospect Not Found'}</p>
        </div>
      </div>
    );
  }

  const hasCombine = prospect.combine && (
    prospect.combine.forty_yard_dash ||
    prospect.combine.bench_press_reps ||
    prospect.combine.vertical_jump ||
    prospect.combine.broad_jump
  );

  return (
    <div className="pane pane--no-header">
      <div className="pane__body">
        {/* Prospect Header - Portrait + Key Info Side-by-Side */}
        <div className="prospect-header">
          <div className="prospect-header__portrait">
            <PlayerPortrait
              playerId={playerId}
              leagueId={leagueId || undefined}
              size="lg"
              bracketed
              status="prospect"
            />
          </div>
          <div className="prospect-header__info">
            <div className="prospect-header__name">{prospect.name}</div>
            <div className="prospect-header__top">
              <span className="prospect-header__position">{prospect.position}</span>
              {prospect.projected_round && (
                <span className="prospect-header__round">Rd {prospect.projected_round}</span>
              )}
            </div>
            <div className="prospect-header__college">{prospect.college}</div>
            <div className="prospect-header__physical">
              {prospect.age} yrs · {prospect.height} · {prospect.weight} lbs
            </div>
            <div className="prospect-header__grade">
              <div className="prospect-header__grade-bar">
                <div
                  className="prospect-header__grade-fill"
                  style={{ width: `${prospect.overall_projection}%` }}
                />
              </div>
              <span className="prospect-header__grade-value">{prospect.overall_projection}</span>
            </div>
          </div>
        </div>

        {/* Scouting Progress - collapsible */}
        <div className="pane-section pane-section--collapsible">
          <button
            className="pane-section__header pane-section__header--toggle"
            onClick={() => toggleSection('scouting')}
          >
            <span>Scouting Progress</span>
            <span className="pane-section__preview">
              <span>{prospect.scouted_percentage}%</span>
              {sections.scouting ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </span>
          </button>
          {sections.scouting && (
            <>
              <div className="player-pane__morale">
                <div className="player-pane__morale-bar">
                  <div
                    className="player-pane__morale-fill"
                    style={{
                      width: `${prospect.scouted_percentage}%`,
                      backgroundColor: 'var(--accent)'
                    }}
                  />
                </div>
                <div className="player-pane__morale-info">
                  <span className="player-pane__morale-label">
                    Scouted: {prospect.scouted_percentage}%
                  </span>
                </div>
              </div>
              <div className="prospect-pane__badges">
                {prospect.interviewed ? (
                  <span className="prospect-badge prospect-badge--yes"><Eye size={10} /> Interviewed</span>
                ) : (
                  <span className="prospect-badge prospect-badge--no"><EyeOff size={10} /> Not Interviewed</span>
                )}
                {prospect.private_workout ? (
                  <span className="prospect-badge prospect-badge--yes">Private Workout</span>
                ) : (
                  <span className="prospect-badge prospect-badge--no">No Workout</span>
                )}
              </div>
            </>
          )}
        </div>

        {/* Scout Assessment - collapsible */}
        {prospect.scout_estimates && prospect.scout_estimates.length > 0 && (
          <div className="pane-section pane-section--collapsible">
            <button
              className="pane-section__header pane-section__header--toggle"
              onClick={() => toggleSection('scoutAssessment')}
            >
              <span>Scout Assessment</span>
              {sections.scoutAssessment ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </button>
            {sections.scoutAssessment && (
              <div className="player-pane__key-stats">
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
            )}
          </div>
        )}

        {/* Biographical - collapsible */}
        <div className="pane-section pane-section--collapsible">
          <button
            className="pane-section__header pane-section__header--toggle"
            onClick={() => toggleSection('bio')}
          >
            <span>Biographical</span>
            <span className="pane-section__preview">
              {sections.bio ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </span>
          </button>
          {sections.bio && (
            <>
              <div className="ctrl-result">
                <span className="ctrl-result__label">Age</span>
                <span className="ctrl-result__value ctrl-result__value--muted">{prospect.age}</span>
              </div>
              <div className="ctrl-result">
                <span className="ctrl-result__label">Size</span>
                <span className="ctrl-result__value ctrl-result__value--muted">
                  {prospect.height}, {prospect.weight} lbs
                </span>
              </div>
              <div className="ctrl-result">
                <span className="ctrl-result__label">College</span>
                <span className="ctrl-result__value ctrl-result__value--muted">{prospect.college}</span>
              </div>
              <div className="ctrl-result">
                <span className="ctrl-result__label">Projection</span>
                <span className="ctrl-result__value" style={{ color: 'var(--accent)' }}>
                  {prospect.projected_round ? `Round ${prospect.projected_round}` : 'Unknown'}
                </span>
              </div>
            </>
          )}
        </div>

        {/* Combine Measurables - collapsible */}
        {hasCombine && (
          <div className="pane-section pane-section--collapsible">
            <button
              className="pane-section__header pane-section__header--toggle"
              onClick={() => toggleSection('combine')}
            >
              <span>Combine Measurables</span>
              {sections.combine ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </button>
            {sections.combine && (
              <>
                {prospect.combine?.forty_yard_dash && (
                  <div className="ctrl-result">
                    <span className="ctrl-result__label">40-Yard</span>
                    <span
                      className="ctrl-result__value"
                      style={{ color: getPercentileColor(prospect.combine.forty_percentile) }}
                    >
                      {prospect.combine.forty_yard_dash.toFixed(2)}s
                    </span>
                  </div>
                )}
                {prospect.combine?.bench_press_reps && (
                  <div className="ctrl-result">
                    <span className="ctrl-result__label">Bench Press</span>
                    <span
                      className="ctrl-result__value"
                      style={{ color: getPercentileColor(prospect.combine.bench_percentile) }}
                    >
                      {prospect.combine.bench_press_reps} reps
                    </span>
                  </div>
                )}
                {prospect.combine?.vertical_jump && (
                  <div className="ctrl-result">
                    <span className="ctrl-result__label">Vertical</span>
                    <span
                      className="ctrl-result__value"
                      style={{ color: getPercentileColor(prospect.combine.vertical_percentile) }}
                    >
                      {prospect.combine.vertical_jump}"
                    </span>
                  </div>
                )}
                {prospect.combine?.broad_jump && (
                  <div className="ctrl-result">
                    <span className="ctrl-result__label">Broad Jump</span>
                    <span
                      className="ctrl-result__value"
                      style={{ color: getPercentileColor(prospect.combine.broad_percentile) }}
                    >
                      {prospect.combine.broad_jump}"
                    </span>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ProspectPane;
