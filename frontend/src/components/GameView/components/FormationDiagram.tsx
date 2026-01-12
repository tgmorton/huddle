/**
 * FormationDiagram - Visual formation display
 *
 * Shows player positions in a formation:
 * - Offensive formations (Shotgun, I-Form, etc.)
 * - Defensive formations (for opponent display)
 * - Position labels (optional)
 */

import React from 'react';
import type { Formation, PersonnelGroup } from '../types';

interface FormationDiagramProps {
  formation: Formation;
  personnel: PersonnelGroup;
  isOffense?: boolean;
  showLabels?: boolean;
  size?: 'small' | 'medium' | 'large';
}

// Position configurations for each formation
const FORMATION_LAYOUTS: Record<Formation, PlayerPosition[]> = {
  shotgun: [
    // WRs
    { x: 5, y: 30, role: 'WR', label: 'X' },
    { x: 30, y: 25, role: 'WR', label: 'Z' },
    { x: 70, y: 25, role: 'WR', label: 'H' },
    // OL
    { x: 35, y: 50, role: 'OL', label: 'LT' },
    { x: 42, y: 50, role: 'OL', label: 'LG' },
    { x: 50, y: 50, role: 'OL', label: 'C' },
    { x: 58, y: 50, role: 'OL', label: 'RG' },
    { x: 65, y: 50, role: 'OL', label: 'RT' },
    // TE
    { x: 75, y: 50, role: 'TE', label: 'TE' },
    // QB (in shotgun)
    { x: 50, y: 65, role: 'QB', label: 'QB' },
    // RB
    { x: 42, y: 68, role: 'RB', label: 'RB' },
  ],
  i_form: [
    // WRs
    { x: 5, y: 30, role: 'WR', label: 'X' },
    { x: 95, y: 30, role: 'WR', label: 'Z' },
    // OL
    { x: 35, y: 50, role: 'OL', label: 'LT' },
    { x: 42, y: 50, role: 'OL', label: 'LG' },
    { x: 50, y: 50, role: 'OL', label: 'C' },
    { x: 58, y: 50, role: 'OL', label: 'RG' },
    { x: 65, y: 50, role: 'OL', label: 'RT' },
    // TE
    { x: 75, y: 50, role: 'TE', label: 'TE' },
    // QB under center
    { x: 50, y: 55, role: 'QB', label: 'QB' },
    // FB
    { x: 50, y: 65, role: 'FB', label: 'FB' },
    // RB
    { x: 50, y: 75, role: 'RB', label: 'RB' },
  ],
  singleback: [
    // WRs
    { x: 5, y: 30, role: 'WR', label: 'X' },
    { x: 25, y: 25, role: 'WR', label: 'H' },
    { x: 95, y: 30, role: 'WR', label: 'Z' },
    // OL
    { x: 35, y: 50, role: 'OL', label: 'LT' },
    { x: 42, y: 50, role: 'OL', label: 'LG' },
    { x: 50, y: 50, role: 'OL', label: 'C' },
    { x: 58, y: 50, role: 'OL', label: 'RG' },
    { x: 65, y: 50, role: 'OL', label: 'RT' },
    // TE
    { x: 75, y: 50, role: 'TE', label: 'TE' },
    // QB
    { x: 50, y: 58, role: 'QB', label: 'QB' },
    // RB
    { x: 50, y: 70, role: 'RB', label: 'RB' },
  ],
  pistol: [
    // WRs
    { x: 5, y: 30, role: 'WR', label: 'X' },
    { x: 30, y: 25, role: 'WR', label: 'H' },
    { x: 95, y: 30, role: 'WR', label: 'Z' },
    // OL
    { x: 35, y: 50, role: 'OL', label: 'LT' },
    { x: 42, y: 50, role: 'OL', label: 'LG' },
    { x: 50, y: 50, role: 'OL', label: 'C' },
    { x: 58, y: 50, role: 'OL', label: 'RG' },
    { x: 65, y: 50, role: 'OL', label: 'RT' },
    // TE
    { x: 75, y: 50, role: 'TE', label: 'TE' },
    // QB (pistol depth)
    { x: 50, y: 60, role: 'QB', label: 'QB' },
    // RB (directly behind QB)
    { x: 50, y: 72, role: 'RB', label: 'RB' },
  ],
  empty: [
    // 5 WRs spread out
    { x: 5, y: 30, role: 'WR', label: 'X' },
    { x: 25, y: 35, role: 'WR', label: 'H' },
    { x: 50, y: 30, role: 'WR', label: 'Y' },
    { x: 75, y: 35, role: 'WR', label: 'F' },
    { x: 95, y: 30, role: 'WR', label: 'Z' },
    // OL
    { x: 35, y: 50, role: 'OL', label: 'LT' },
    { x: 42, y: 50, role: 'OL', label: 'LG' },
    { x: 50, y: 50, role: 'OL', label: 'C' },
    { x: 58, y: 50, role: 'OL', label: 'RG' },
    { x: 65, y: 50, role: 'OL', label: 'RT' },
    // QB in shotgun
    { x: 50, y: 65, role: 'QB', label: 'QB' },
  ],
  goal_line: [
    // WR
    { x: 5, y: 50, role: 'WR', label: 'X' },
    // Heavy OL/TE
    { x: 28, y: 50, role: 'TE', label: 'TE' },
    { x: 35, y: 50, role: 'OL', label: 'LT' },
    { x: 42, y: 50, role: 'OL', label: 'LG' },
    { x: 50, y: 50, role: 'OL', label: 'C' },
    { x: 58, y: 50, role: 'OL', label: 'RG' },
    { x: 65, y: 50, role: 'OL', label: 'RT' },
    { x: 72, y: 50, role: 'TE', label: 'TE' },
    // QB under center
    { x: 50, y: 58, role: 'QB', label: 'QB' },
    // FB
    { x: 45, y: 68, role: 'FB', label: 'FB' },
    // RB
    { x: 55, y: 68, role: 'RB', label: 'RB' },
  ],
  jumbo: [
    // Extra OL as TE
    { x: 25, y: 50, role: 'OL', label: 'EL' },
    { x: 35, y: 50, role: 'OL', label: 'LT' },
    { x: 42, y: 50, role: 'OL', label: 'LG' },
    { x: 50, y: 50, role: 'OL', label: 'C' },
    { x: 58, y: 50, role: 'OL', label: 'RG' },
    { x: 65, y: 50, role: 'OL', label: 'RT' },
    { x: 75, y: 50, role: 'OL', label: 'EL' },
    // TE inline
    { x: 82, y: 50, role: 'TE', label: 'TE' },
    // QB under center
    { x: 50, y: 58, role: 'QB', label: 'QB' },
    // FB
    { x: 45, y: 68, role: 'FB', label: 'FB' },
    // RB
    { x: 55, y: 68, role: 'RB', label: 'RB' },
  ],
};

interface PlayerPosition {
  x: number; // Percentage 0-100
  y: number; // Percentage 0-100
  role: 'QB' | 'RB' | 'FB' | 'WR' | 'TE' | 'OL';
  label: string;
}

export const FormationDiagram: React.FC<FormationDiagramProps> = ({
  formation,
  personnel,
  isOffense = true,
  showLabels = false,
  size = 'medium',
}) => {
  const layout = FORMATION_LAYOUTS[formation] || FORMATION_LAYOUTS.shotgun;

  const classNames = [
    'formation-diagram',
    `formation-diagram--${size}`,
    isOffense ? 'formation-diagram--offense' : 'formation-diagram--defense',
    showLabels ? 'formation-diagram--show-labels' : '',
  ].filter(Boolean).join(' ');

  return (
    <div className={classNames}>
      {/* Line of scrimmage */}
      <div className="formation-diagram__los" />

      {/* Players */}
      {layout.map((player, index) => (
        <div
          key={index}
          className={`formation-diagram__player formation-diagram__player--${player.role.toLowerCase()}`}
          style={{
            left: `${player.x}%`,
            top: `${player.y}%`,
          }}
        >
          <span className="formation-diagram__label">{player.label}</span>
        </div>
      ))}

      {/* Formation name */}
      <div className="formation-diagram__name">
        {formatFormationName(formation)} ({personnel})
      </div>
    </div>
  );
};

function formatFormationName(formation: Formation): string {
  const names: Record<Formation, string> = {
    i_form: 'I-Form',
    shotgun: 'Shotgun',
    singleback: 'Singleback',
    pistol: 'Pistol',
    empty: 'Empty',
    goal_line: 'Goal Line',
    jumbo: 'Jumbo',
  };
  return names[formation] || formation;
}

export default FormationDiagram;
