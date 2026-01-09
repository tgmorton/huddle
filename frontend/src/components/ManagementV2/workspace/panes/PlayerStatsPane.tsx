// PlayerStatsPane.tsx - Full career stats pop-out pane (6-col workspace pane)
// Shows complete career history, career highs, and extended stat columns

import React, { useEffect, useState, useMemo } from 'react';
import { ChevronDown, ChevronRight, Trophy, TrendingUp } from 'lucide-react';
import { adminApi } from '../../../../api/adminClient';
import type { PlayerDetail } from '../../../../types/admin';
import { PlayerPortrait, StatsTable } from '../../components';
import { useManagementStore, selectLeagueId } from '../../../../stores/managementStore';
import { generateMockCareerStats } from '../../../../utils/mockStats';
import type { CareerHighs } from '../../../../types/stats';

// === Career Highs Display ===

const CAREER_HIGH_LABELS: Record<string, { label: string; suffix: string }> = {
  // Game highs
  passing_yards_game: { label: 'Pass Yds (Game)', suffix: '' },
  passing_tds_game: { label: 'Pass TDs (Game)', suffix: '' },
  rushing_yards_game: { label: 'Rush Yds (Game)', suffix: '' },
  rushing_tds_game: { label: 'Rush TDs (Game)', suffix: '' },
  receiving_yards_game: { label: 'Rec Yds (Game)', suffix: '' },
  receptions_game: { label: 'Receptions (Game)', suffix: '' },
  receiving_tds_game: { label: 'Rec TDs (Game)', suffix: '' },
  tackles_game: { label: 'Tackles (Game)', suffix: '' },
  sacks_game: { label: 'Sacks (Game)', suffix: '' },
  // Season highs
  passing_yards_season: { label: 'Pass Yds (Season)', suffix: '' },
  passing_tds_season: { label: 'Pass TDs (Season)', suffix: '' },
  passer_rating_season: { label: 'Passer Rating (Season)', suffix: '' },
  rushing_yards_season: { label: 'Rush Yds (Season)', suffix: '' },
  rushing_tds_season: { label: 'Rush TDs (Season)', suffix: '' },
  receiving_yards_season: { label: 'Rec Yds (Season)', suffix: '' },
  receptions_season: { label: 'Receptions (Season)', suffix: '' },
  receiving_tds_season: { label: 'Rec TDs (Season)', suffix: '' },
  sacks_season: { label: 'Sacks (Season)', suffix: '' },
  interceptions_season: { label: 'INTs (Season)', suffix: '' },
};

interface PlayerStatsPaneProps {
  playerId: string;
  onComplete?: () => void;
}

export const PlayerStatsPane: React.FC<PlayerStatsPaneProps> = ({
  playerId,
}) => {
  const [player, setPlayer] = useState<PlayerDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const leagueId = useManagementStore(selectLeagueId);

  // Collapsible section states
  const [sections, setSections] = useState({
    fullStats: true,
    careerHighs: true,
  });

  const toggleSection = (section: keyof typeof sections) => {
    setSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // Fetch player data
  useEffect(() => {
    const fetchPlayer = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await adminApi.getPlayer(playerId);
        setPlayer(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load player');
      } finally {
        setLoading(false);
      }
    };
    fetchPlayer();
  }, [playerId]);

  // Generate mock career stats
  const careerStats = useMemo(() => {
    if (!player) return null;
    return generateMockCareerStats(
      player.id,
      player.full_name,
      player.position,
      player.overall,
      player.experience,
      player.team_abbreviation || 'FA'
    );
  }, [player]);

  // Loading
  if (loading) return null;

  // Error
  if (error || !player) {
    return (
      <div className="pane pane--stats">
        <div className="pane__body pane__body--placeholder">
          <p>{error || 'Player not found'}</p>
        </div>
      </div>
    );
  }

  // Get relevant career highs for display
  const getRelevantCareerHighs = (highs: CareerHighs): { key: string; label: string; value: number }[] => {
    return Object.entries(highs)
      .filter(([, value]) => value !== undefined && value > 0)
      .map(([key, value]) => ({
        key,
        label: CAREER_HIGH_LABELS[key]?.label || key,
        value: value as number,
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8); // Show top 8 career highs
  };

  const relevantHighs = careerStats ? getRelevantCareerHighs(careerStats.career_highs) : [];

  return (
    <div className="pane pane--stats">
      {/* Header */}
      <div className="stats-pane__header">
        <PlayerPortrait
          playerId={playerId}
          leagueId={leagueId || undefined}
          size="md"
          bracketed
        />
        <div className="stats-pane__header-info">
          <div className="stats-pane__name">
            #{player.jersey_number} {player.full_name}
          </div>
          <div className="stats-pane__meta">
            <span className="stats-pane__position">{player.position}</span>
            <span className="stats-pane__team">{player.team_abbreviation || 'FA'}</span>
            <span className="stats-pane__experience">
              {player.experience > 0 ? `${player.experience} yrs` : 'Rookie'}
            </span>
          </div>
          <div className="stats-pane__overall">
            <span className="stats-pane__overall-value">{player.overall}</span>
            <span className="stats-pane__overall-label">OVR</span>
          </div>
        </div>
      </div>

      <div className="pane__body">
        {/* Full Career Stats */}
        {careerStats && careerStats.seasons.length > 0 && (
          <div className="pane-section pane-section--collapsible">
            <button
              className="pane-section__header pane-section__header--toggle"
              onClick={() => toggleSection('fullStats')}
            >
              <span><TrendingUp size={14} /> Career Statistics</span>
              <span className="pane-section__preview">
                <span>{careerStats.seasons.length} seasons</span>
                {sections.fullStats ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </span>
            </button>
            {sections.fullStats && (
              <div className="stats-pane__table-container">
                <StatsTable
                  seasons={careerStats.seasons}
                  careerTotals={careerStats.career_totals}
                  position={player.position}
                  variant="full"
                  showCareer={true}
                />
              </div>
            )}
          </div>
        )}

        {/* Career Highs */}
        {relevantHighs.length > 0 && (
          <div className="pane-section pane-section--collapsible">
            <button
              className="pane-section__header pane-section__header--toggle"
              onClick={() => toggleSection('careerHighs')}
            >
              <span><Trophy size={14} /> Career Highs</span>
              {sections.careerHighs ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </button>
            {sections.careerHighs && (
              <div className="stats-pane__career-highs">
                {relevantHighs.map(({ key, label, value }) => (
                  <div key={key} className="stats-pane__career-high">
                    <span className="stats-pane__career-high-value">
                      {typeof value === 'number' && value % 1 !== 0
                        ? value.toFixed(1)
                        : value.toLocaleString()}
                    </span>
                    <span className="stats-pane__career-high-label">{label}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PlayerStatsPane;
