/**
 * SpecialTeamsModal - Decision modal for 4th down and special teams
 *
 * Appears on 4th down to offer:
 * - Go for it (offensive play)
 * - Punt
 * - Field goal attempt (if in range)
 *
 * Also handles:
 * - Kickoff decisions
 * - Two-point conversion attempts
 * - Extra point attempts
 */

import React from 'react';
import { Target, ArrowRight, Crosshair, X, AlertTriangle } from 'lucide-react';
import type { GameSituation } from '../types';

interface SpecialTeamsModalProps {
  situation: GameSituation;
  onGoForIt: () => void;
  onPunt: () => void;
  onFieldGoal: () => void;
  onClose: () => void;
  isOpen: boolean;
}

export const SpecialTeamsModal: React.FC<SpecialTeamsModalProps> = ({
  situation,
  onGoForIt,
  onPunt,
  onFieldGoal,
  onClose,
  isOpen,
}) => {
  if (!isOpen) return null;

  // Calculate field goal distance (add 17 yards for snap + endzone)
  const fgDistance = 100 - situation.los + 17;
  const canKickFG = fgDistance <= 58; // Max reasonable FG range
  const fgDifficulty = getFGDifficulty(fgDistance);

  // Determine context
  const isShortYardage = situation.distance <= 2;
  const isLongYardage = situation.distance >= 5;
  const isInFGRange = canKickFG;
  const isPuntTerritory = situation.los < 65; // Inside opponent's 35

  // Get recommendation
  const recommendation = getRecommendation(situation, fgDistance);

  return (
    <div className="special-teams-modal__overlay" onClick={onClose}>
      <div className="special-teams-modal" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="special-teams-modal__header">
          <div className="special-teams-modal__situation">
            <span className="special-teams-modal__down">4TH DOWN</span>
            <span className="special-teams-modal__distance">
              {situation.isGoalToGo ? '& GOAL' : `& ${situation.distance}`}
            </span>
          </div>
          <div className="special-teams-modal__location">
            at {situation.yardLineDisplay}
          </div>
          <button className="special-teams-modal__close" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        {/* Decision Context */}
        <div className="special-teams-modal__context">
          {situation.isGoalToGo && (
            <div className="special-teams-modal__context-item special-teams-modal__context-item--red-zone">
              <AlertTriangle size={14} />
              <span>GOAL TO GO - Scoring opportunity</span>
            </div>
          )}
          {situation.isRedZone && !situation.isGoalToGo && (
            <div className="special-teams-modal__context-item special-teams-modal__context-item--red-zone">
              <span>RED ZONE</span>
            </div>
          )}
        </div>

        {/* Recommendation */}
        <div className={`special-teams-modal__recommendation special-teams-modal__recommendation--${recommendation.type}`}>
          <span className="special-teams-modal__recommendation-label">RECOMMENDATION</span>
          <span className="special-teams-modal__recommendation-text">{recommendation.text}</span>
        </div>

        {/* Options */}
        <div className="special-teams-modal__options">
          {/* Go for it */}
          <button
            className={`special-teams-modal__option ${recommendation.type === 'go' ? 'special-teams-modal__option--recommended' : ''}`}
            onClick={onGoForIt}
          >
            <div className="special-teams-modal__option-icon">
              <Crosshair size={24} />
            </div>
            <div className="special-teams-modal__option-info">
              <span className="special-teams-modal__option-name">GO FOR IT</span>
              <span className="special-teams-modal__option-desc">
                {isShortYardage ? 'Short yardage - good chance' : isLongYardage ? 'Long distance - risky' : 'Medium risk'}
              </span>
            </div>
            {recommendation.type === 'go' && (
              <span className="special-teams-modal__option-badge">★</span>
            )}
          </button>

          {/* Field Goal */}
          <button
            className={`special-teams-modal__option ${!canKickFG ? 'special-teams-modal__option--disabled' : ''} ${recommendation.type === 'fg' ? 'special-teams-modal__option--recommended' : ''}`}
            onClick={onFieldGoal}
            disabled={!canKickFG}
          >
            <div className="special-teams-modal__option-icon">
              <Target size={24} />
            </div>
            <div className="special-teams-modal__option-info">
              <span className="special-teams-modal__option-name">FIELD GOAL</span>
              <span className="special-teams-modal__option-desc">
                {canKickFG
                  ? `${fgDistance} yards - ${fgDifficulty}`
                  : 'Out of range'}
              </span>
            </div>
            {canKickFG && (
              <div className={`special-teams-modal__option-meter special-teams-modal__option-meter--${fgDifficulty.toLowerCase().replace(' ', '-')}`}>
                <div
                  className="special-teams-modal__option-meter-fill"
                  style={{ width: `${Math.max(0, 100 - (fgDistance - 20) * 2)}%` }}
                />
              </div>
            )}
            {recommendation.type === 'fg' && (
              <span className="special-teams-modal__option-badge">★</span>
            )}
          </button>

          {/* Punt */}
          <button
            className={`special-teams-modal__option ${situation.isRedZone ? 'special-teams-modal__option--disabled' : ''} ${recommendation.type === 'punt' ? 'special-teams-modal__option--recommended' : ''}`}
            onClick={onPunt}
            disabled={situation.isRedZone}
          >
            <div className="special-teams-modal__option-icon">
              <ArrowRight size={24} />
            </div>
            <div className="special-teams-modal__option-info">
              <span className="special-teams-modal__option-name">PUNT</span>
              <span className="special-teams-modal__option-desc">
                {situation.isRedZone
                  ? 'Too close to punt'
                  : 'Pin them deep'}
              </span>
            </div>
            {recommendation.type === 'punt' && (
              <span className="special-teams-modal__option-badge">★</span>
            )}
          </button>
        </div>

        {/* Footer hint */}
        <div className="special-teams-modal__footer">
          <span className="special-teams-modal__hint">Press 1-3 to select, ESC to cancel</span>
        </div>
      </div>
    </div>
  );
};

function getFGDifficulty(distance: number): string {
  if (distance <= 30) return 'Chip shot';
  if (distance <= 40) return 'Routine';
  if (distance <= 48) return 'Moderate';
  if (distance <= 53) return 'Difficult';
  return 'Very long';
}

function getRecommendation(
  situation: GameSituation,
  fgDistance: number
): { type: 'go' | 'fg' | 'punt'; text: string } {
  const { distance, los, isRedZone, isGoalToGo } = situation;

  // Inside the 5 - always go for it
  if (isGoalToGo && los >= 95) {
    return { type: 'go', text: 'Goal line stand - take a shot' };
  }

  // FG range considerations
  if (fgDistance <= 40) {
    return { type: 'fg', text: `Easy ${fgDistance} yard field goal - take the points` };
  }

  if (fgDistance <= 48 && distance > 3) {
    return { type: 'fg', text: 'Field goal range - moderate attempt' };
  }

  // Short yardage
  if (distance <= 1) {
    return { type: 'go', text: '4th and inches - high conversion rate' };
  }

  if (distance <= 2 && isRedZone) {
    return { type: 'go', text: 'Short yardage in the red zone' };
  }

  // Too far to kick, close to midfield
  if (los >= 40 && los < 60 && distance <= 4) {
    return { type: 'go', text: 'Midfield - worth the gamble' };
  }

  // Deep in own territory
  if (los < 40) {
    return { type: 'punt', text: 'Deep in own territory - flip the field' };
  }

  // Default to punt for long yardage situations
  if (distance >= 5) {
    return { type: 'punt', text: 'Long yardage - punt is safer' };
  }

  return { type: 'fg', text: 'Take the points if possible' };
}

export default SpecialTeamsModal;
