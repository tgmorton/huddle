/**
 * DepthChartPanel - Interactive depth chart display
 *
 * Design Philosophy:
 * - Every choice is a tradeoff (Pillar 2) - Starting the rookie means benching the vet
 * - Competing stakeholders (Pillar 3) - Players want playing time
 * - Show WHO is at each position, not just names
 */

import React, { useState, useEffect } from 'react';
import type { DepthChartResponse, DepthChartEntry } from '../../types/management';
import './DepthChartPanel.css';

interface DepthChartPanelProps {
  teamAbbr: string;
}

type UnitType = 'offense' | 'defense' | 'special_teams';

const UNIT_LABELS: Record<UnitType, string> = {
  offense: 'Offense',
  defense: 'Defense',
  special_teams: 'Special Teams',
};

// Group offense slots into logical sections
const OFFENSE_SECTIONS = [
  { label: 'Backfield', slots: ['QB1', 'QB2', 'QB3', 'RB1', 'RB2', 'RB3', 'FB1'] },
  { label: 'Receivers', slots: ['WR1', 'WR2', 'WR3', 'WR4', 'WR5', 'TE1', 'TE2'] },
  { label: 'Offensive Line', slots: ['LT1', 'LG1', 'C1', 'RG1', 'RT1', 'LT2', 'LG2', 'C2', 'RG2', 'RT2'] },
];

const DEFENSE_SECTIONS = [
  { label: 'Defensive Line', slots: ['DE1', 'DE2', 'DT1', 'DT2', 'NT1'] },
  { label: 'Linebackers', slots: ['MLB1', 'MLB2', 'OLB1', 'OLB2', 'ILB1', 'ILB2'] },
  { label: 'Secondary', slots: ['CB1', 'CB2', 'CB3', 'FS1', 'SS1', 'S1'] },
];

const SPECIAL_TEAMS_SECTIONS = [
  { label: 'Specialists', slots: ['K1', 'P1', 'LS1'] },
  { label: 'Returners', slots: ['KR1', 'PR1'] },
];

export const DepthChartPanel: React.FC<DepthChartPanelProps> = ({ teamAbbr }) => {
  const [depthChart, setDepthChart] = useState<DepthChartResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeUnit, setActiveUnit] = useState<UnitType>('offense');

  useEffect(() => {
    const fetchDepthChart = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/v1/admin/teams/${teamAbbr}/depth-chart`);
        if (!response.ok) {
          throw new Error('Failed to load depth chart');
        }
        const data = await response.json();
        setDepthChart(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    if (teamAbbr) {
      fetchDepthChart();
    }
  }, [teamAbbr]);

  if (loading) {
    return (
      <div className="depth-chart-panel depth-chart-panel--loading">
        <div className="depth-chart-panel__loader">Loading depth chart...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="depth-chart-panel depth-chart-panel--error">
        <div className="depth-chart-panel__error">{error}</div>
      </div>
    );
  }

  if (!depthChart) {
    return null;
  }

  const units: UnitType[] = ['offense', 'defense', 'special_teams'];
  const currentEntries = depthChart[activeUnit];

  const getSections = () => {
    switch (activeUnit) {
      case 'offense': return OFFENSE_SECTIONS;
      case 'defense': return DEFENSE_SECTIONS;
      case 'special_teams': return SPECIAL_TEAMS_SECTIONS;
    }
  };

  // Build a map for quick lookup
  const entryMap = new Map<string, DepthChartEntry>();
  currentEntries.forEach(entry => entryMap.set(entry.slot, entry));

  return (
    <div className="depth-chart-panel">
      {/* Header */}
      <div className="depth-chart-panel__header">
        <div className="depth-chart-panel__title">
          <span className="depth-chart-panel__team">{teamAbbr}</span>
          <span className="depth-chart-panel__label">Depth Chart</span>
        </div>
      </div>

      {/* Unit Tabs */}
      <div className="depth-chart-panel__units">
        {units.map(unit => (
          <button
            key={unit}
            className={`depth-chart-panel__unit ${activeUnit === unit ? 'active' : ''}`}
            onClick={() => setActiveUnit(unit)}
          >
            {UNIT_LABELS[unit]}
          </button>
        ))}
      </div>

      {/* Depth Chart Grid */}
      <div className="depth-chart-panel__grid">
        {getSections().map(section => (
          <div key={section.label} className="depth-chart-panel__section">
            <div className="depth-chart-panel__section-header">{section.label}</div>
            <div className="depth-chart-panel__section-slots">
              {section.slots.map(slot => {
                const entry = entryMap.get(slot);
                return (
                  <DepthChartSlot key={slot} slot={slot} entry={entry} />
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

interface DepthChartSlotProps {
  slot: string;
  entry?: DepthChartEntry;
}

const DepthChartSlot: React.FC<DepthChartSlotProps> = ({ slot, entry }) => {
  const isEmpty = !entry?.player_id;
  const isBackup = slot.match(/[2-9]$/);

  // Parse slot to get position and depth
  const position = slot.replace(/[0-9]+$/, '');
  const depth = parseInt(slot.match(/[0-9]+$/)?.[0] || '1', 10);

  const getOverallClass = (ovr: number) => {
    if (ovr >= 85) return 'elite';
    if (ovr >= 75) return 'starter';
    if (ovr >= 65) return 'backup';
    return 'depth';
  };

  return (
    <div className={`depth-slot ${isEmpty ? 'depth-slot--empty' : ''} ${isBackup ? 'depth-slot--backup' : ''}`}>
      <div className="depth-slot__position">
        <span className="depth-slot__pos">{position}</span>
        <span className="depth-slot__depth">{depth === 1 ? '' : depth}</span>
      </div>

      {isEmpty ? (
        <div className="depth-slot__empty">---</div>
      ) : (
        <div className="depth-slot__player">
          <div className="depth-slot__name">{entry?.player_name}</div>
          {entry?.overall && (
            <div className={`depth-slot__overall depth-slot__overall--${getOverallClass(entry.overall)}`}>
              {entry.overall}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DepthChartPanel;
