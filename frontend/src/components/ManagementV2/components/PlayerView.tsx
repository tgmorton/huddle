// PlayerView.tsx - Unified player detail component for workspace panes and sideviews
// Combines PlayerPane and PlayerDetailView into a single reusable component

import React, { useEffect, useState, useMemo } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Maximize2,
  ArrowLeft,
  BarChart2,
} from 'lucide-react';
import { adminApi } from '../../../api/adminClient';
import { managementApi } from '../../../api/managementClient';
import type { PlayerDetail, ArchetypeType, PersonalityTrait } from '../../../types/admin';
import { StatBar, getStatColor, PlayerPortrait, StatsTable } from './index';
import { useManagementStore, selectLeagueId, selectFranchiseId } from '../../../stores/managementStore';
import { generateMockCareerStats } from '../../../utils/mockStats';

// === Position-Based Key Stats ===

const POSITION_KEY_STATS: Record<string, string[]> = {
  QB: ['throw_power', 'throw_accuracy_short', 'throw_accuracy_mid', 'throw_accuracy_deep', 'awareness', 'speed'],
  RB: ['speed', 'acceleration', 'carrying', 'ball_carrier_vision', 'break_tackle', 'agility'],
  FB: ['run_block', 'carrying', 'strength', 'speed', 'catching'],
  WR: ['speed', 'catching', 'route_running_short', 'route_running_mid', 'release', 'acceleration'],
  TE: ['catching', 'route_running_short', 'run_block', 'speed', 'strength'],
  LT: ['pass_block', 'run_block', 'strength', 'awareness', 'agility'],
  LG: ['pass_block', 'run_block', 'strength', 'awareness', 'agility'],
  C: ['pass_block', 'run_block', 'strength', 'awareness', 'agility'],
  RG: ['pass_block', 'run_block', 'strength', 'awareness', 'agility'],
  RT: ['pass_block', 'run_block', 'strength', 'awareness', 'agility'],
  DE: ['block_shedding', 'finesse_moves', 'power_moves', 'speed', 'tackle'],
  DT: ['block_shedding', 'power_moves', 'strength', 'tackle', 'pursuit'],
  NT: ['block_shedding', 'strength', 'tackle', 'power_moves', 'pursuit'],
  MLB: ['tackle', 'pursuit', 'play_recognition', 'speed', 'zone_coverage'],
  ILB: ['tackle', 'pursuit', 'play_recognition', 'speed', 'zone_coverage'],
  OLB: ['tackle', 'pursuit', 'speed', 'block_shedding', 'play_recognition'],
  CB: ['man_coverage', 'zone_coverage', 'speed', 'press', 'play_recognition'],
  FS: ['zone_coverage', 'tackle', 'speed', 'play_recognition', 'pursuit'],
  SS: ['tackle', 'zone_coverage', 'hit_power', 'speed', 'play_recognition'],
  K: ['kick_power', 'kick_accuracy', 'awareness'],
  P: ['kick_power', 'kick_accuracy', 'awareness'],
};

// Attribute category groupings
const ATTRIBUTE_CATEGORIES: Record<string, { label: string; attrs: string[] }> = {
  physical: {
    label: 'Physical',
    attrs: ['speed', 'acceleration', 'agility', 'strength', 'jumping', 'stamina', 'injury'],
  },
  passing: {
    label: 'Passing',
    attrs: ['throw_power', 'throw_accuracy_short', 'throw_accuracy_mid', 'throw_accuracy_deep', 'throw_on_run', 'play_action'],
  },
  rushing: {
    label: 'Rushing',
    attrs: ['carrying', 'ball_carrier_vision', 'break_tackle', 'stiff_arm', 'spin_move', 'juke_move', 'trucking'],
  },
  receiving: {
    label: 'Receiving',
    attrs: ['catching', 'catch_in_traffic', 'spectacular_catch', 'release', 'route_running_short', 'route_running_mid', 'route_running_deep'],
  },
  blocking: {
    label: 'Blocking',
    attrs: ['run_block', 'pass_block', 'impact_blocking', 'lead_block'],
  },
  defense: {
    label: 'Defense',
    attrs: ['tackle', 'hit_power', 'pursuit', 'play_recognition', 'man_coverage', 'zone_coverage', 'press', 'block_shedding', 'finesse_moves', 'power_moves'],
  },
  mental: {
    label: 'Mental',
    attrs: ['awareness', 'football_iq', 'clutch', 'consistency'],
  },
};

// === Helpers ===

const formatAttrName = (attr: string): string => {
  return attr
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

const getMoodInfo = (approval: number): { label: string; color: string } => {
  if (approval >= 80) return { label: 'Motivated', color: 'var(--success)' };
  if (approval >= 60) return { label: 'Content', color: 'var(--text-secondary)' };
  if (approval >= 50) return { label: 'Neutral', color: 'var(--text-muted)' };
  if (approval >= 40) return { label: 'Unhappy', color: 'var(--warning)' };
  if (approval >= 25) return { label: 'Frustrated', color: 'var(--danger)' };
  return { label: 'Disgruntled', color: 'var(--danger)' };
};

const formatArchetype = (archetype: ArchetypeType): string => {
  return archetype
    .split('_')
    .map(word => word.charAt(0) + word.slice(1).toLowerCase())
    .join(' ');
};

const formatTrait = (trait: string): string => {
  return trait
    .split('_')
    .map(word => word.charAt(0) + word.slice(1).toLowerCase())
    .join(' ');
};

const getTopTraits = (
  traits: Record<PersonalityTrait, number> | undefined,
  count: number = 3
): { trait: string; value: number }[] => {
  if (!traits) return [];
  return Object.entries(traits)
    .filter(([, value]) => value >= 0.6)
    .sort(([, a], [, b]) => b - a)
    .slice(0, count)
    .map(([trait, value]) => ({ trait: formatTrait(trait), value }));
};

const formatSalary = (salary: number | null | undefined): string => {
  if (!salary) return 'N/A';
  if (salary >= 1000) return `$${(salary / 1000).toFixed(1)}M`;
  return `$${salary}K`;
};

const getContractColor = (years: number | null | undefined): string => {
  if (!years) return 'var(--text-muted)';
  if (years >= 3) return 'var(--text-secondary)';
  if (years === 2) return 'var(--accent)';
  return 'var(--danger)';
};

// Portrait attributes for debug display
interface PortraitAttributes {
  skin_tone: number;
  face_width: number;
  hair_style: number[] | null;
  hair_style_name: string | null;
  hair_color: string | null;
  facial_style: number[] | null;
  facial_style_name: string | null;
  facial_color: string | null;
}

// === Component Props ===

export interface PlayerViewProps {
  playerId: string;

  // Display mode
  variant?: 'pane' | 'sideview';  // pane = workspace, sideview = roster panel

  // Navigation
  onBack?: () => void;
  onPopOut?: (player: { id: string; name: string; position: string; overall: number }) => void;
  onOpenStats?: (player: { id: string; name: string; position: string; overall: number }) => void;

  // Initial state
  defaultAttributesExpanded?: boolean;

  // Callbacks
  onComplete?: () => void;  // For workspace pane completion
}

export const PlayerView: React.FC<PlayerViewProps> = ({
  playerId,
  variant = 'pane',
  onBack,
  onPopOut,
  onOpenStats,
  defaultAttributesExpanded = false,
}) => {
  const [player, setPlayer] = useState<PlayerDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [portraitAttrs, setPortraitAttrs] = useState<PortraitAttributes | null>(null);
  const [potentials, setPotentials] = useState<Record<string, number>>({});

  const leagueId = useManagementStore(selectLeagueId);
  const franchiseId = useManagementStore(selectFranchiseId);

  // Collapsible section states
  const [sections, setSections] = useState({
    keyStats: true,
    statistics: true,
    morale: true,
    personality: false,
    contract: false,
    status: false,
    allAttributes: defaultAttributesExpanded,
    debug: false,
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

  // Fetch per-attribute potentials
  useEffect(() => {
    if (!franchiseId) return;

    const fetchPotentials = async () => {
      try {
        const data = await managementApi.getDevelopment(franchiseId);
        const playerDev = data.players.find(p => p.player_id === playerId);
        if (playerDev) {
          const potMap: Record<string, number> = {};
          for (const pot of playerDev.potentials) {
            potMap[pot.name] = pot.potential;
          }
          setPotentials(potMap);
        }
      } catch {
        // Silent fail - potentials are optional
      }
    };
    fetchPotentials();
  }, [franchiseId, playerId]);

  // Fetch portrait attributes when debug section is expanded
  useEffect(() => {
    if (!sections.debug || !leagueId || portraitAttrs) return;

    const fetchPortraitAttrs = async () => {
      try {
        const res = await fetch(`/api/v1/portraits/${leagueId}/${playerId}/attributes`);
        if (res.ok) {
          setPortraitAttrs(await res.json());
        }
      } catch {
        // Silent fail - debug info is optional
      }
    };
    fetchPortraitAttrs();
  }, [sections.debug, leagueId, playerId, portraitAttrs]);

  // Get categories with attributes for this player
  const getRelevantCategories = (attributes: Record<string, number>) => {
    return Object.entries(ATTRIBUTE_CATEGORIES)
      .map(([key, config]) => {
        const relevantAttrs = config.attrs.filter(attr => attributes[attr] !== undefined);
        if (relevantAttrs.length === 0) return null;
        return { key, label: config.label, attrs: relevantAttrs };
      })
      .filter(Boolean) as { key: string; label: string; attrs: string[] }[];
  };

  // Loading state
  if (loading) return null;

  // Error state
  if (error || !player) {
    return (
      <div className="player-view player-view--error">
        <p>{error || 'Player not found'}</p>
        {onBack && (
          <button className="player-view__back" onClick={onBack}>
            <ArrowLeft size={14} /> Back
          </button>
        )}
      </div>
    );
  }

  // Extract data
  const approvalValue = player.approval?.approval ?? 50;
  const approvalTrend = player.approval?.trend ?? 0;
  const mood = getMoodInfo(approvalValue);
  const isTradeCandidate = approvalValue < 40;
  const isHoldoutRisk = approvalValue < 25;
  const archetype = player.personality?.archetype;
  const topTraits = getTopTraits(player.personality?.traits);
  const yearsLeft = player.contract_year_remaining ?? player.contract_years;
  const attrs = player.attributes || {};
  const attrCount = Object.keys(attrs).length;

  const keyStatKeys = POSITION_KEY_STATS[player.position] || POSITION_KEY_STATS['QB'];
  const keyStats = keyStatKeys
    .filter(key => attrs[key] !== undefined)
    .map(key => ({ key, label: formatAttrName(key), value: attrs[key] }));

  const isPaneVariant = variant === 'pane';

  // Generate mock career stats (memoized to avoid regeneration on re-renders)
  const careerStats = useMemo(() => {
    return generateMockCareerStats(
      player.id,
      player.full_name,
      player.position,
      player.overall,
      player.experience,
      player.team_abbreviation || 'FA'
    );
  }, [player.id, player.full_name, player.position, player.overall, player.experience, player.team_abbreviation]);

  return (
    <div className={`player-view player-view--${variant}`}>
      {/* Header */}
      <div className="player-view__header">
        {onBack && (
          <button className="player-view__back" onClick={onBack}>
            <ArrowLeft size={14} />
          </button>
        )}
        <PlayerPortrait
          playerId={playerId}
          leagueId={leagueId || undefined}
          size={isPaneVariant ? 'lg' : 'md'}
          bracketed={isPaneVariant}
        />
        {!isPaneVariant && (
          <div className="player-view__header-info">
            <span className="player-view__name">#{player.jersey_number} {player.full_name}</span>
            <span className="player-view__meta">
              {player.position} • {player.experience > 0 ? `${player.experience} yrs` : 'Rookie'}
            </span>
          </div>
        )}
        {onPopOut && (
          <button
            className="player-view__popout"
            onClick={() => onPopOut({
              id: player.id,
              name: player.full_name,
              position: player.position,
              overall: player.overall,
            })}
            title="Open in workspace"
          >
            <Maximize2 size={14} />
          </button>
        )}
      </div>

      {/* Body */}
      <div className="player-view__body">
        {/* Key Attributes */}
        {keyStats.length > 0 && (
          <div className="player-view__section player-view__section--collapsible">
            <button
              className="player-view__section-header"
              onClick={() => toggleSection('keyStats')}
            >
              <span>Key Attributes</span>
              {sections.keyStats ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </button>
            {sections.keyStats && (
              <div className="player-view__key-stats">
                {keyStats.map(({ key, label, value }) => (
                  <StatBar key={key} label={label} value={value} potential={potentials[key]} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Statistics */}
        {careerStats.seasons.length > 0 && (
          <div className="player-view__section player-view__section--collapsible">
            <button
              className="player-view__section-header"
              onClick={() => toggleSection('statistics')}
            >
              <span>Statistics</span>
              <span className="player-view__section-preview">
                <span>{careerStats.seasons.length} seasons</span>
                {sections.statistics ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </span>
            </button>
            {sections.statistics && (
              <div className="player-view__statistics">
                <StatsTable
                  seasons={careerStats.seasons}
                  careerTotals={careerStats.career_totals}
                  position={player.position}
                  variant="compact"
                  maxSeasons={3}
                  showCareer={true}
                />
                {onOpenStats && careerStats.seasons.length > 3 && (
                  <button
                    className="player-view__stats-expand"
                    onClick={() => onOpenStats({
                      id: player.id,
                      name: player.full_name,
                      position: player.position,
                      overall: player.overall,
                    })}
                  >
                    <BarChart2 size={12} />
                    View Full Stats ({careerStats.seasons.length} seasons)
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {/* Morale */}
        <div className="player-view__section player-view__section--collapsible">
          <button
            className="player-view__section-header"
            onClick={() => toggleSection('morale')}
          >
            <span>Morale</span>
            <span className="player-view__section-preview">
              <span style={{ color: mood.color }}>{mood.label}</span>
              {sections.morale ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </span>
          </button>
          {sections.morale && (
            <>
              <div className="player-view__morale">
                <div className="player-view__morale-bar">
                  <div
                    className="player-view__morale-fill"
                    style={{ width: `${approvalValue}%`, backgroundColor: mood.color }}
                  />
                </div>
                <div className="player-view__morale-info">
                  <span style={{ color: mood.color }}>{mood.label}</span>
                  <span>{Math.round(approvalValue)}</span>
                  {approvalTrend !== 0 ? (
                    approvalTrend > 0 ? (
                      <TrendingUp size={12} style={{ color: 'var(--success)' }} />
                    ) : (
                      <TrendingDown size={12} style={{ color: 'var(--danger)' }} />
                    )
                  ) : (
                    <Minus size={12} style={{ color: 'var(--text-muted)' }} />
                  )}
                </div>
              </div>
              {(isTradeCandidate || isHoldoutRisk) && (
                <div className="player-view__risks">
                  {isTradeCandidate && (
                    <span className="player-view__risk player-view__risk--trade">
                      <AlertTriangle size={12} /> Trade Request Risk
                    </span>
                  )}
                  {isHoldoutRisk && (
                    <span className="player-view__risk player-view__risk--holdout">
                      <AlertTriangle size={12} /> Holdout Risk
                    </span>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Personality */}
        {(archetype || topTraits.length > 0) && (
          <div className="player-view__section player-view__section--collapsible">
            <button
              className="player-view__section-header"
              onClick={() => toggleSection('personality')}
            >
              <span>Personality</span>
              <span className="player-view__section-preview">
                {archetype && <span>{formatArchetype(archetype)}</span>}
                {sections.personality ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </span>
            </button>
            {sections.personality && (
              <>
                {archetype && (
                  <div className="player-view__row">
                    <span className="player-view__row-label">Archetype</span>
                    <span>{formatArchetype(archetype)}</span>
                  </div>
                )}
                {topTraits.length > 0 && (
                  <div className="player-view__traits">
                    {topTraits.map(({ trait, value }) => (
                      <span
                        key={trait}
                        className="player-view__trait"
                        style={{ opacity: 0.6 + (value * 0.4) }}
                      >
                        {trait}
                      </span>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Contract */}
        <div className="player-view__section player-view__section--collapsible">
          <button
            className="player-view__section-header"
            onClick={() => toggleSection('contract')}
          >
            <span>Contract</span>
            <span className="player-view__section-preview">
              <span>{formatSalary(player.salary)}/yr</span>
              {sections.contract ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </span>
          </button>
          {sections.contract && (
            <>
              <div className="player-view__row">
                <span className="player-view__row-label">Salary</span>
                <span>{formatSalary(player.salary)}/yr</span>
              </div>
              {yearsLeft != null && (
                <div className="player-view__row">
                  <span className="player-view__row-label">Years Left</span>
                  <span style={{ color: getContractColor(yearsLeft) }}>{yearsLeft}</span>
                </div>
              )}
            </>
          )}
        </div>

        {/* Status */}
        <div className="player-view__section player-view__section--collapsible">
          <button
            className="player-view__section-header"
            onClick={() => toggleSection('status')}
          >
            <span>Status</span>
            <span className="player-view__section-preview">
              <span>Age {player.age}</span>
              {player.potential > player.overall && (
                <span style={{ color: 'var(--success)' }}>POT {player.potential}</span>
              )}
              {sections.status ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </span>
          </button>
          {sections.status && (
            <>
              <div className="player-view__row">
                <span className="player-view__row-label">Age</span>
                <span>{player.age}</span>
              </div>
              <div className="player-view__row">
                <span className="player-view__row-label">Potential</span>
                <span style={{ color: player.potential > player.overall ? 'var(--success)' : 'var(--text-muted)' }}>
                  {player.potential}
                </span>
              </div>
            </>
          )}
        </div>

        {/* All Attributes */}
        {attrCount > 0 && (
          <div className="player-view__section player-view__section--collapsible">
            <button
              className="player-view__section-header"
              onClick={() => toggleSection('allAttributes')}
            >
              <span>All Attributes ({attrCount})</span>
              {sections.allAttributes ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </button>
            {sections.allAttributes && (
              <div className="player-view__all-attrs">
                {getRelevantCategories(attrs).map(({ key, label, attrs: categoryAttrs }) => (
                  <div key={key} className="player-view__attr-category">
                    <div className="player-view__attr-category-label">{label}</div>
                    <div className="player-view__attr-grid">
                      {categoryAttrs.map(attr => {
                        const current = attrs[attr];
                        const pot = potentials[attr];
                        const hasGrowth = pot !== undefined && pot > current;
                        return (
                          <div key={attr} className="player-view__attr-item">
                            <span className="player-view__attr-name">{formatAttrName(attr)}</span>
                            <span className="player-view__attr-values">
                              <span
                                className="player-view__attr-value"
                                style={{ color: getStatColor(current) }}
                              >
                                {current}
                              </span>
                              {hasGrowth && (
                                <span className="player-view__attr-potential">({pot})</span>
                              )}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Debug */}
        <div className="player-view__section player-view__section--collapsible player-view__section--debug">
          <button
            className="player-view__section-header"
            onClick={() => toggleSection('debug')}
          >
            <span>Debug</span>
            {sections.debug ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
          {sections.debug && (
            <div className="player-view__debug">
              <div className="player-view__debug-item">
                <span>Player ID</span>
                <code>{playerId}</code>
              </div>
              <div className="player-view__debug-item">
                <span>League ID</span>
                <code>{leagueId || 'N/A'}</code>
              </div>
              <div className="player-view__debug-item">
                <span>Franchise ID</span>
                <code>{franchiseId || 'N/A'}</code>
              </div>
              {portraitAttrs && (
                <>
                  <div className="player-view__debug-divider" />
                  <div className="player-view__debug-item">
                    <span>Skin Tone</span>
                    <code>{portraitAttrs.skin_tone}</code>
                  </div>
                  <div className="player-view__debug-item">
                    <span>Face Width</span>
                    <code>{portraitAttrs.face_width}</code>
                  </div>
                  {portraitAttrs.hair_style && (
                    <div className="player-view__debug-item">
                      <span>Hair Style</span>
                      <code>[{portraitAttrs.hair_style.join(', ')}] {portraitAttrs.hair_style_name}</code>
                    </div>
                  )}
                  {portraitAttrs.hair_color && (
                    <div className="player-view__debug-item">
                      <span>Hair Color</span>
                      <code>{portraitAttrs.hair_color}</code>
                    </div>
                  )}
                  {portraitAttrs.facial_style && (
                    <div className="player-view__debug-item">
                      <span>Facial Style</span>
                      <code>[{portraitAttrs.facial_style.join(', ')}] {portraitAttrs.facial_style_name}</code>
                    </div>
                  )}
                  {portraitAttrs.facial_color && (
                    <div className="player-view__debug-item">
                      <span>Facial Color</span>
                      <code>{portraitAttrs.facial_color}</code>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PlayerView;
