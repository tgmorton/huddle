/**
 * ScoutingIntel - Opponent tendencies and scouting information panel
 *
 * Displays:
 * - Defensive tendencies (coverage percentages)
 * - Blitz rates by situation
 * - Identified weaknesses
 * - Key matchup advantages
 */

import React from 'react';
import { Target, AlertTriangle, TrendingUp } from 'lucide-react';

interface TendencyData {
  label: string;
  percentage: number;
}

interface ScoutingIntelProps {
  coverageTendencies?: TendencyData[];
  blitzRates?: {
    thirdDown?: number;
    redZone?: number;
    overall?: number;
  };
  weaknesses?: string[];
  keyMatchups?: {
    player: string;
    advantage: string;
    rating: 'favorable' | 'neutral' | 'unfavorable';
  }[];
  className?: string;
}

// Default mock data for development
const DEFAULT_COVERAGE: TendencyData[] = [
  { label: 'Cover 2', percentage: 45 },
  { label: 'Cover 3', percentage: 30 },
  { label: 'Man', percentage: 25 },
];

const DEFAULT_BLITZ = {
  thirdDown: 68,
  redZone: 42,
  overall: 35,
};

const DEFAULT_WEAKNESSES = [
  'Deep middle open',
  'Slot WR mismatch',
  'Weak edge contain',
];

export const ScoutingIntel: React.FC<ScoutingIntelProps> = ({
  coverageTendencies = DEFAULT_COVERAGE,
  blitzRates = DEFAULT_BLITZ,
  weaknesses = DEFAULT_WEAKNESSES,
  keyMatchups = [],
  className = '',
}) => {
  return (
    <div className={`scouting-intel ${className}`}>
      {/* Coverage Tendencies */}
      <div className="scouting-intel__section">
        <h4 className="scouting-intel__section-title">
          <Target size={12} />
          DEF TENDENCY
        </h4>
        <div className="scouting-intel__tendencies">
          {coverageTendencies.map(({ label, percentage }) => (
            <div key={label} className="scouting-intel__tendency">
              <span className="scouting-intel__tendency-label">{label}</span>
              <div className="scouting-intel__tendency-bar">
                <div
                  className="scouting-intel__tendency-fill"
                  style={{ width: `${percentage}%` }}
                />
              </div>
              <span className="scouting-intel__tendency-value">{percentage}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* Blitz Rates */}
      <div className="scouting-intel__section">
        <h4 className="scouting-intel__section-title">
          <AlertTriangle size={12} />
          BLITZ RATE
        </h4>
        <div className="scouting-intel__rates">
          {blitzRates.thirdDown !== undefined && (
            <div className="scouting-intel__rate">
              <span className="scouting-intel__rate-label">3rd Down</span>
              <span className={`scouting-intel__rate-value ${blitzRates.thirdDown > 50 ? 'high' : ''}`}>
                {blitzRates.thirdDown}%
              </span>
            </div>
          )}
          {blitzRates.redZone !== undefined && (
            <div className="scouting-intel__rate">
              <span className="scouting-intel__rate-label">Red Zone</span>
              <span className={`scouting-intel__rate-value ${blitzRates.redZone > 50 ? 'high' : ''}`}>
                {blitzRates.redZone}%
              </span>
            </div>
          )}
          {blitzRates.overall !== undefined && (
            <div className="scouting-intel__rate">
              <span className="scouting-intel__rate-label">Overall</span>
              <span className="scouting-intel__rate-value">{blitzRates.overall}%</span>
            </div>
          )}
        </div>
      </div>

      {/* Identified Weaknesses */}
      {weaknesses.length > 0 && (
        <div className="scouting-intel__section">
          <h4 className="scouting-intel__section-title">
            <TrendingUp size={12} />
            WEAKNESS
          </h4>
          <div className="scouting-intel__weaknesses">
            {weaknesses.map((weakness, i) => (
              <div key={i} className="scouting-intel__weakness">
                <span className="scouting-intel__weakness-arrow">→</span>
                <span className="scouting-intel__weakness-text">{weakness}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Key Matchups */}
      {keyMatchups.length > 0 && (
        <div className="scouting-intel__section">
          <h4 className="scouting-intel__section-title">KEY MATCHUPS</h4>
          <div className="scouting-intel__matchups">
            {keyMatchups.map(({ player, advantage, rating }, i) => (
              <div key={i} className={`scouting-intel__matchup scouting-intel__matchup--${rating}`}>
                <span className="scouting-intel__matchup-player">{player}</span>
                <span className="scouting-intel__matchup-advantage">{advantage}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ScoutingIntel;
