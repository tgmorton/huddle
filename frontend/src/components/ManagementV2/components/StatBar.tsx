// StatBar.tsx - Shared stat bar component with gradient coloring

import React from 'react';

// Linear interpolation between two hex colors
const lerpColor = (color1: string, color2: string, t: number): string => {
  const r1 = parseInt(color1.slice(1, 3), 16);
  const g1 = parseInt(color1.slice(3, 5), 16);
  const b1 = parseInt(color1.slice(5, 7), 16);
  const r2 = parseInt(color2.slice(1, 3), 16);
  const g2 = parseInt(color2.slice(3, 5), 16);
  const b2 = parseInt(color2.slice(5, 7), 16);

  const r = Math.round(r1 + (r2 - r1) * t);
  const g = Math.round(g1 + (g2 - g1) * t);
  const b = Math.round(b1 + (b2 - b1) * t);

  return `rgb(${r}, ${g}, ${b})`;
};

// Get color for attribute value - interpolates along red→green gradient
export const getStatColor = (value: number): string => {
  // Clamp value to 0-100
  const v = Math.max(0, Math.min(100, value));

  // Color stops: red (0) → orange (25) → yellow (50) → lime (75) → green (100)
  if (v <= 25) {
    return lerpColor('#dc2626', '#f97316', v / 25);
  } else if (v <= 50) {
    return lerpColor('#f97316', '#eab308', (v - 25) / 25);
  } else if (v <= 75) {
    return lerpColor('#eab308', '#84cc16', (v - 50) / 25);
  } else {
    return lerpColor('#84cc16', '#22c55e', (v - 75) / 25);
  }
};

// StatBar component for visual attribute display
export interface StatBarProps {
  label: string;
  value: number;
  min?: number;  // For uncertainty range (lower bound)
  max?: number;  // For uncertainty range (upper bound)
  potential?: number;  // Show ceiling/potential as muted bar
}

export const StatBar: React.FC<StatBarProps> = ({ label, value, min, max, potential }) => {
  const color = getStatColor(value);
  const hasUncertainty = min !== undefined && max !== undefined && min !== max;
  const hasPotential = potential !== undefined && potential > value;

  // For uncertainty bars, show gradient from min color to max color
  const minColor = hasUncertainty ? getStatColor(min!) : color;
  const maxColor = hasUncertainty ? getStatColor(max!) : color;

  return (
    <div className="stat-bar">
      <div className="stat-bar__header">
        <span className="stat-bar__value" style={{ color }}>
          {value}
          {hasPotential && <span className="stat-bar__potential-text">({potential})</span>}
        </span>
        <span className="stat-bar__label">{label}</span>
      </div>
      <div className="stat-bar__track">
        {hasUncertainty ? (
          /* Uncertainty range as gradient */
          <div
            className="stat-bar__fill"
            style={{
              left: `${min}%`,
              width: `${max! - min!}%`,
              background: `linear-gradient(to right, ${minColor}, ${maxColor})`,
            }}
          />
        ) : (
          <>
            {/* Standard solid fill for current value */}
            <div
              className="stat-bar__fill"
              style={{
                width: `${value}%`,
                backgroundColor: color,
              }}
            />
            {/* Muted potential bar showing room to grow */}
            {hasPotential && (
              <div
                className="stat-bar__potential-fill"
                style={{
                  left: `${value}%`,
                  width: `${potential! - value}%`,
                }}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default StatBar;
