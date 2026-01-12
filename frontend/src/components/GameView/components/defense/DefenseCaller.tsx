/**
 * DefenseCaller - Defensive play selection interface
 *
 * Components:
 * - Coverage scheme selector
 * - Blitz package selector
 * - Pre-snap reads (opponent formation)
 * - Set defense button
 */

import React from 'react';
import { Shield, Zap, AlertTriangle } from 'lucide-react';
import type { CoverageScheme, BlitzPackage, GameSituation } from '../../types';
import { COVERAGE_SCHEMES, BLITZ_PACKAGES } from '../../constants';

interface DefenseCallerProps {
  selectedCoverage: CoverageScheme | null;
  selectedBlitz: BlitzPackage;
  situation: GameSituation | null;
  offenseFormation?: string; // What the offense is showing
  onCoverageChange: (coverage: CoverageScheme) => void;
  onBlitzChange: (blitz: BlitzPackage) => void;
  onSetDefense: () => void;
  disabled?: boolean;
}

export const DefenseCaller: React.FC<DefenseCallerProps> = ({
  selectedCoverage,
  selectedBlitz,
  situation,
  offenseFormation,
  onCoverageChange,
  onBlitzChange,
  onSetDefense,
  disabled = false,
}) => {
  const canSet = selectedCoverage && !disabled;

  // Calculate blitz risk based on situation
  const getBlitzRisk = (blitz: BlitzPackage): 'safe' | 'risky' | 'dangerous' => {
    const config = BLITZ_PACKAGES[blitz];
    if (config.riskLevel === 'low') return 'safe';
    if (config.riskLevel === 'high') return 'dangerous';
    return 'risky';
  };

  return (
    <div className="play-caller play-caller--defense">
      {/* Pre-snap read */}
      {offenseFormation && (
        <div className="defense-caller__read">
          <span className="defense-caller__read-label">OFFENSE SHOWING:</span>
          <span className="defense-caller__read-formation">{offenseFormation}</span>
        </div>
      )}

      {/* Coverage selector */}
      <div className="defense-caller__coverages">
        <h4>
          <Shield size={14} />
          COVERAGE
        </h4>
        <div className="defense-caller__coverage-grid">
          {(['cover_2', 'cover_3', 'cover_4', 'man', 'cover_1', 'cover_0'] as CoverageScheme[]).map(coverage => {
            const config = COVERAGE_SCHEMES[coverage];
            return (
              <button
                key={coverage}
                className={`defense-caller__coverage-btn ${selectedCoverage === coverage ? 'active' : ''}`}
                onClick={() => onCoverageChange(coverage)}
                title={`${config.description}\nStrength: ${config.strength}\nWeakness: ${config.weakness}`}
              >
                <span className="defense-caller__coverage-name">{config.name}</span>
              </button>
            );
          })}
        </div>
        {selectedCoverage && (
          <div className="defense-caller__coverage-desc">
            {COVERAGE_SCHEMES[selectedCoverage].description}
          </div>
        )}
      </div>

      {/* Blitz selector */}
      <div className="defense-caller__blitz">
        <h4>
          <Zap size={14} />
          BLITZ
        </h4>
        <div className="defense-caller__blitz-grid">
          {(['none', 'zone_blitz', 'lb_blitz', 'db_blitz', 'all_out'] as BlitzPackage[]).map(blitz => {
            const config = BLITZ_PACKAGES[blitz];
            const risk = getBlitzRisk(blitz);
            return (
              <button
                key={blitz}
                className={`defense-caller__blitz-btn ${selectedBlitz === blitz ? 'active' : ''} defense-caller__blitz-btn--${risk}`}
                onClick={() => onBlitzChange(blitz)}
                title={`${config.description}\nRushers: ${config.rushers}`}
              >
                <span className="defense-caller__blitz-name">{config.name}</span>
                {risk === 'dangerous' && <AlertTriangle size={10} />}
              </button>
            );
          })}
        </div>
        {selectedBlitz !== 'none' && (
          <div className="defense-caller__blitz-desc">
            {BLITZ_PACKAGES[selectedBlitz].description}
          </div>
        )}
      </div>

      {/* Set defense button */}
      <div className="defense-caller__action">
        <button
          className="play-caller__snap play-caller__snap--defense"
          onClick={onSetDefense}
          disabled={!canSet}
        >
          {disabled ? 'WAIT...' : 'SET DEFENSE'}
        </button>
        <div className="play-caller__shortcut">
          Press SPACE to set
        </div>
      </div>
    </div>
  );
};

export default DefenseCaller;
