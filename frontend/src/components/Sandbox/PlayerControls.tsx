/**
 * Player attribute controls with sliders
 */

import type { SandboxPlayer } from '../../types/sandbox';

interface PlayerControlsProps {
  player: SandboxPlayer;
  onUpdate: (updates: Partial<SandboxPlayer>) => void;
  disabled?: boolean;
}

interface AttributeSliderProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
}

function AttributeSlider({ label, value, onChange, disabled }: AttributeSliderProps) {
  return (
    <div className="attribute-slider">
      <div className="attribute-header">
        <span className="attribute-label">{label}</span>
        <span className="attribute-value">{value}</span>
      </div>
      <input
        type="range"
        min="40"
        max="99"
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value, 10))}
        disabled={disabled}
        className="slider"
      />
    </div>
  );
}

export function PlayerControls({ player, onUpdate, disabled = false }: PlayerControlsProps) {
  const isBlocker = player.role === 'blocker';
  const roleColor = isBlocker ? '#3b82f6' : '#ef4444';

  // Attributes relevant to each role
  const blockerAttributes = [
    { key: 'strength', label: 'Strength' },
    { key: 'pass_block', label: 'Pass Block' },
    { key: 'awareness', label: 'Awareness' },
    { key: 'agility', label: 'Agility' },
  ];

  const rusherAttributes = [
    { key: 'strength', label: 'Strength' },
    { key: 'block_shedding', label: 'Block Shed' },
    { key: 'power_moves', label: 'Power Moves' },
    { key: 'finesse_moves', label: 'Finesse Moves' },
    { key: 'speed', label: 'Speed' },
  ];

  const attributes = isBlocker ? blockerAttributes : rusherAttributes;

  return (
    <div className="player-controls" style={{ borderColor: roleColor }}>
      <div className="player-header" style={{ backgroundColor: roleColor }}>
        <span className="player-name">{player.name}</span>
        <span className="player-role">{isBlocker ? 'Offensive Line' : 'Defensive Tackle'}</span>
      </div>

      <div className="attributes-list">
        {attributes.map(({ key, label }) => (
          <AttributeSlider
            key={key}
            label={label}
            value={player[key as keyof SandboxPlayer] as number}
            onChange={(value) => onUpdate({ [key]: value })}
            disabled={disabled}
          />
        ))}
      </div>

      {disabled && (
        <div className="controls-disabled-overlay">
          Stop simulation to edit
        </div>
      )}
    </div>
  );
}
