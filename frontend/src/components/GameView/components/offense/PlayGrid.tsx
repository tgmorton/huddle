/**
 * PlayGrid - Grid of play selection buttons
 *
 * Shows plays organized by category with:
 * - Play name
 * - Recommended indicator
 * - Hover description
 */

import React from 'react';
import { Star } from 'lucide-react';
import type { PlayOption } from '../../types';

interface PlayGridProps {
  plays: PlayOption[];
  selectedPlay: string | null;
  recommendedPlay?: string;
  onPlaySelect: (playCode: string) => void;
}

export const PlayGrid: React.FC<PlayGridProps> = ({
  plays,
  selectedPlay,
  recommendedPlay,
  onPlaySelect,
}) => {
  if (plays.length === 0) {
    return (
      <div className="play-grid play-grid--empty">
        <p>No plays available in this category</p>
      </div>
    );
  }

  return (
    <div className="play-grid">
      {plays.map(play => {
        const isSelected = selectedPlay === play.code;
        const isRecommended = recommendedPlay === play.code;

        return (
          <button
            key={play.code}
            className={`play-grid__btn ${isSelected ? 'active' : ''} ${isRecommended ? 'recommended' : ''}`}
            onClick={() => onPlaySelect(play.code)}
            title={play.description}
          >
            {isRecommended && (
              <Star className="play-grid__star" size={12} fill="currentColor" />
            )}
            <span className="play-grid__name">{play.name}</span>
          </button>
        );
      })}
    </div>
  );
};

export default PlayGrid;
