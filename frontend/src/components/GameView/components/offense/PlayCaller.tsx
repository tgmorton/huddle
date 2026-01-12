/**
 * PlayCaller - Offensive play selection interface
 *
 * Components:
 * - Formation selector with visual diagrams
 * - Play grid organized by category
 * - Situation tips from AI coordinator
 * - Snap button
 */

import React, { useMemo } from 'react';
import type { Formation, PersonnelGroup, PlayCategory, PlayOption, GameSituation } from '../../types';
import { PLAY_CATEGORIES } from '../../constants';
import { FormationPicker } from './FormationPicker';
import { PlayGrid } from './PlayGrid';

interface PlayCallerProps {
  selectedFormation: Formation | null;
  selectedPersonnel: PersonnelGroup;
  selectedPlay: string | null;
  selectedCategory: string;
  availablePlays: PlayOption[];
  situation?: GameSituation | null;
  recommendedPlay?: string;
  situationTip?: string;
  onFormationChange: (formation: Formation) => void;
  onPersonnelChange: (personnel: PersonnelGroup) => void;
  onPlaySelect: (playCode: string) => void;
  onCategoryChange: (category: string) => void;
  onSnap: () => void;
  disabled?: boolean;
}

export const PlayCaller: React.FC<PlayCallerProps> = ({
  selectedFormation,
  selectedPersonnel,
  selectedPlay,
  selectedCategory,
  availablePlays,
  situation: _situation,
  recommendedPlay,
  situationTip,
  onFormationChange,
  onPersonnelChange,
  onPlaySelect,
  onCategoryChange,
  onSnap,
  disabled = false,
}) => {
  const activeCategory = selectedCategory as PlayCategory;

  // Filter plays by category
  const filteredPlays = useMemo(() => {
    return availablePlays.filter(play => play.category === activeCategory);
  }, [availablePlays, activeCategory]);

  // Categories with play counts
  const categoriesWithCounts = useMemo(() => {
    const counts: Record<PlayCategory, number> = {
      run: 0,
      quick: 0,
      intermediate: 0,
      deep: 0,
      screen: 0,
      play_action: 0,
    };
    availablePlays.forEach(play => {
      counts[play.category]++;
    });
    return counts;
  }, [availablePlays]);

  const canSnap = selectedFormation && selectedPlay && !disabled;

  return (
    <div className="play-caller play-caller--offense">
      {/* Formation selector */}
      <FormationPicker
        selectedFormation={selectedFormation}
        selectedPersonnel={selectedPersonnel}
        onFormationChange={onFormationChange}
        onPersonnelChange={onPersonnelChange}
      />

      {/* Play selection */}
      <div className="play-caller__plays">
        {/* Category tabs */}
        <div className="play-caller__tabs">
          {(['run', 'quick', 'intermediate', 'deep', 'screen', 'play_action'] as PlayCategory[]).map(category => (
            <button
              key={category}
              className={`play-caller__tab ${activeCategory === category ? 'active' : ''}`}
              data-category={category}
              onClick={() => onCategoryChange(category)}
              disabled={categoriesWithCounts[category] === 0}
            >
              {PLAY_CATEGORIES[category].name}
              {categoriesWithCounts[category] > 0 && (
                <span className="play-caller__tab-count">{categoriesWithCounts[category]}</span>
              )}
            </button>
          ))}
        </div>

        {/* Play grid */}
        <PlayGrid
          plays={filteredPlays}
          selectedPlay={selectedPlay}
          recommendedPlay={recommendedPlay}
          onPlaySelect={onPlaySelect}
        />
      </div>

      {/* Right side: tip and snap */}
      <div className="play-caller__action">
        {/* Situation tip */}
        {situationTip && (
          <div className="play-caller__tip">
            <span className="play-caller__tip-star">★</span>
            <span className="play-caller__tip-text">{situationTip}</span>
          </div>
        )}

        {/* Selected play indicator */}
        {selectedPlay && (
          <div className="play-caller__selected">
            Selected: <strong>{selectedPlay}</strong>
          </div>
        )}

        {/* Snap button */}
        <button
          className="play-caller__snap"
          onClick={onSnap}
          disabled={!canSnap}
        >
          {disabled ? 'WAIT...' : 'SNAP BALL'}
        </button>

        <div className="play-caller__shortcut">
          Press SPACE to snap
        </div>
      </div>
    </div>
  );
};

export default PlayCaller;
