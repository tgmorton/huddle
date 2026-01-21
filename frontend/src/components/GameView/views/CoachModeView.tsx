/**
 * CoachModeView - Play calling interface for coach mode
 *
 * Extracted from GameView to separate coach-specific UI:
 * - PlayCaller for offense
 * - DefenseCaller for defense
 * - SpecialTeamsModal for 4th down decisions
 */

import React from 'react';
import { PlayCaller } from '../components/offense/PlayCaller';
import { DefenseCaller } from '../components/defense/DefenseCaller';
import { SpecialTeamsModal } from '../components/SpecialTeamsModal';
import type {
  GameSituation,
  GamePhase,
  Formation,
  PersonnelGroup,
  CoverageScheme,
  BlitzPackage,
  PlayOption,
} from '../types';

interface CoachModeViewProps {
  // Game state
  situation: GameSituation;
  phase: GamePhase;
  loading: boolean;
  userOnOffense: boolean;

  // Offense state
  selectedFormation: Formation | null;
  selectedPersonnel: PersonnelGroup;
  selectedPlayCode: string | null;
  selectedCategory: string;
  availablePlays: PlayOption[];

  // Defense state
  selectedCoverage: CoverageScheme | null;
  selectedBlitz: BlitzPackage;

  // Special teams modal
  showSpecialTeamsModal: boolean;

  // Offense handlers
  onFormationChange: (formation: Formation | null) => void;
  onPersonnelChange: (personnel: PersonnelGroup) => void;
  onPlaySelect: (playCode: string | null) => void;
  onCategoryChange: (category: string) => void;
  onSnap: () => void;

  // Defense handlers
  onCoverageChange: (coverage: CoverageScheme | null) => void;
  onBlitzChange: (blitz: BlitzPackage) => void;
  onSetDefense: () => void;

  // Special teams handlers
  onGoForIt: () => void;
  onPunt: () => void;
  onFieldGoal: () => void;
  onCloseSpecialTeams: () => void;
}

export const CoachModeView: React.FC<CoachModeViewProps> = ({
  situation,
  phase,
  loading,
  userOnOffense,
  selectedFormation,
  selectedPersonnel,
  selectedPlayCode,
  selectedCategory,
  availablePlays,
  selectedCoverage,
  selectedBlitz,
  showSpecialTeamsModal,
  onFormationChange,
  onPersonnelChange,
  onPlaySelect,
  onCategoryChange,
  onSnap,
  onCoverageChange,
  onBlitzChange,
  onSetDefense,
  onGoForIt,
  onPunt,
  onFieldGoal,
  onCloseSpecialTeams,
}) => {
  const disabled = phase !== 'pre_snap' || loading;

  return (
    <>
      <div className="game-view__play-caller">
        {userOnOffense ? (
          <PlayCaller
            selectedFormation={selectedFormation}
            selectedPersonnel={selectedPersonnel}
            selectedPlay={selectedPlayCode}
            selectedCategory={selectedCategory}
            availablePlays={availablePlays}
            situation={situation}
            onFormationChange={onFormationChange}
            onPersonnelChange={onPersonnelChange}
            onPlaySelect={onPlaySelect}
            onCategoryChange={onCategoryChange}
            onSnap={onSnap}
            disabled={disabled}
          />
        ) : (
          <DefenseCaller
            selectedCoverage={selectedCoverage}
            selectedBlitz={selectedBlitz}
            situation={situation}
            onCoverageChange={onCoverageChange}
            onBlitzChange={onBlitzChange}
            onSetDefense={onSetDefense}
            disabled={disabled}
          />
        )}
      </div>

      {/* Special Teams Modal */}
      <SpecialTeamsModal
        situation={situation}
        isOpen={showSpecialTeamsModal}
        onGoForIt={onGoForIt}
        onPunt={onPunt}
        onFieldGoal={onFieldGoal}
        onClose={onCloseSpecialTeams}
      />
    </>
  );
};

export default CoachModeView;
