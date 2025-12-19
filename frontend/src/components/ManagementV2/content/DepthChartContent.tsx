// DepthChartContent.tsx - Depth chart panel with stat table

import React from 'react';
import type { PlayerStats } from '../types';
import { DEMO_ROSTER } from '../data/demo';

// === Constants ===

// Position groups with their 4 key attributes
const POSITION_ATTRS: Record<string, string[]> = {
  QB: ['ARM', 'ACC', 'AWR', 'SPD'],
  RB: ['SPD', 'AGI', 'BTK', 'CAR'],
  WR: ['SPD', 'CTH', 'RTE', 'REL'],
  TE: ['CTH', 'RBK', 'SPD', 'STR'],
  OL: ['STR', 'PBK', 'RBK', 'AWR'],
  DL: ['STR', 'PWM', 'BSH', 'SPD'],
  LB: ['TAK', 'SPD', 'AWR', 'COV'],
  CB: ['SPD', 'MCV', 'ZCV', 'PRS'],
  S: ['SPD', 'ZCV', 'TAK', 'AWR'],
};

// Map specific positions to their attribute group
const POS_TO_GROUP: Record<string, string> = {
  QB: 'QB', RB: 'RB', FB: 'RB',
  WR: 'WR', WR1: 'WR', WR2: 'WR', WR3: 'WR',
  TE: 'TE',
  LT: 'OL', LG: 'OL', C: 'OL', RG: 'OL', RT: 'OL',
  DE: 'DL', DT: 'DL', NT: 'DL',
  LB: 'LB', MLB: 'LB', OLB: 'LB', LOLB: 'LB', ROLB: 'LB',
  CB: 'CB', CB1: 'CB', CB2: 'CB',
  FS: 'S', SS: 'S',
};

// Position display order
const POSITION_ORDER = ['QB', 'RB', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT', 'DE', 'DT', 'LB', 'CB', 'FS', 'SS'];

// === Helpers ===

// Color scale for stat values - tighter thresholds so amber is special
const getStatColor = (value: number): string => {
  if (value >= 90) return 'var(--success)';
  if (value >= 85) return 'var(--accent)';
  if (value >= 70) return 'var(--text-secondary)';
  if (value >= 60) return 'var(--text-muted)';
  return 'var(--danger)';
};

// === PlayerStatTable (reusable) ===

interface PlayerStatTableProps {
  players: PlayerStats[];
  showDepth?: boolean;
}

export const PlayerStatTable: React.FC<PlayerStatTableProps> = ({ players, showDepth = true }) => {
  // Group players by position
  const grouped = players.reduce((acc, player) => {
    const group = POS_TO_GROUP[player.pos] || player.pos;
    if (!acc[group]) acc[group] = [];
    acc[group].push(player);
    return acc;
  }, {} as Record<string, PlayerStats[]>);

  // Sort each group by depth then OVR
  Object.values(grouped).forEach(group => {
    group.sort((a, b) => {
      if (showDepth && a.depth !== b.depth) return (a.depth || 99) - (b.depth || 99);
      return b.ovr - a.ovr;
    });
  });

  // Get ordered position groups
  const orderedGroups = POSITION_ORDER
    .map(pos => POS_TO_GROUP[pos] || pos)
    .filter((v, i, a) => a.indexOf(v) === i) // unique
    .filter(group => grouped[group]?.length);

  return (
    <div className="stat-table">
      {orderedGroups.map(group => {
        const attrs = POSITION_ATTRS[group] || ['OVR', 'SPD', 'STR', 'AWR'];
        const groupPlayers = grouped[group];

        return (
          <div key={group} className="stat-table__group">
            <div className="stat-table__header">
              <span className="stat-table__header-pos">{group}</span>
              {attrs.map(attr => (
                <span key={attr} className="stat-table__header-attr">{attr}</span>
              ))}
            </div>
            {groupPlayers.map(player => (
              <div key={player.id} className="stat-table__row">
                <span className="stat-table__name">
                  {showDepth && player.depth && (
                    <span className={player.depth === 1 ? 'stat-table__starter' : 'stat-table__backup'}>
                      {player.depth}
                    </span>
                  )}
                  {player.name}
                </span>
                {attrs.map(attr => {
                  const value = player.attrs[attr] ?? 0;
                  return (
                    <span
                      key={attr}
                      className="stat-table__stat"
                      style={{ color: getStatColor(value) }}
                    >
                      {value}
                    </span>
                  );
                })}
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
};

// === DepthChartContent ===

export const DepthChartContent: React.FC = () => {
  return (
    <div className="ref-content">
      <PlayerStatTable players={DEMO_ROSTER} showDepth={true} />
    </div>
  );
};

export default DepthChartContent;
