// DraftPanel.tsx - Board, Prospects, Scouts tabs

import React, { useState, useCallback } from 'react';
import { PlaceholderContent } from '../content/PlaceholderContent';
import { DraftBoardContent } from '../content/DraftBoardContent';
import { DraftClassContent } from '../content/DraftClassContent';
import { ProspectDetailView } from '../content/ProspectDetailView';
import type { PlayerSummary } from '../../../types/admin';

type DraftTab = 'board' | 'scouts' | 'prospects';
type ProspectsView = { type: 'list' } | { type: 'prospect'; prospectId: string };

interface DraftPanelProps {
  onAddProspectToWorkspace?: (prospect: { id: string; name: string; position: string; overall: number }) => void;
  franchiseId?: string | null;
}

export const DraftPanel: React.FC<DraftPanelProps> = ({ onAddProspectToWorkspace, franchiseId }) => {
  const [tab, setTab] = useState<DraftTab>('board');
  const [prospectsView, setProspectsView] = useState<ProspectsView>({ type: 'list' });

  // Click row → show prospect detail
  const handleSelectPlayer = useCallback((player: PlayerSummary) => {
    setProspectsView({ type: 'prospect', prospectId: player.id });
  }, []);

  // Popout button → add to workspace
  const handlePopout = useCallback((player: PlayerSummary, e: React.MouseEvent) => {
    e.stopPropagation();
    if (onAddProspectToWorkspace) {
      onAddProspectToWorkspace({
        id: player.id,
        name: player.full_name,
        position: player.position,
        overall: player.overall,
      });
    }
  }, [onAddProspectToWorkspace]);

  // Back to list
  const handleBack = useCallback(() => {
    setProspectsView({ type: 'list' });
  }, []);

  // Reset view when switching tabs (including clicking current tab)
  const handleTabChange = (newTab: DraftTab) => {
    setTab(newTab);
    // Always reset to list when clicking prospects tab
    if (newTab === 'prospects') {
      setProspectsView({ type: 'list' });
    }
  };

  return (
    <div className="tabbed-panel">
      <div className="tabbed-panel__tabs">
        <button
          className={`tabbed-panel__tab ${tab === 'board' ? 'tabbed-panel__tab--active' : ''}`}
          onClick={() => handleTabChange('board')}
        >
          Board
        </button>
        <button
          className={`tabbed-panel__tab ${tab === 'prospects' ? 'tabbed-panel__tab--active' : ''}`}
          onClick={() => handleTabChange('prospects')}
        >
          Prospects
        </button>
        <button
          className={`tabbed-panel__tab ${tab === 'scouts' ? 'tabbed-panel__tab--active' : ''}`}
          onClick={() => handleTabChange('scouts')}
        >
          Scouts
        </button>
      </div>

      <div className="tabbed-panel__body">
        {tab === 'board' && <DraftBoardContent onPopoutProspect={onAddProspectToWorkspace} />}
        {tab === 'scouts' && <PlaceholderContent title="Scouts" />}
        {tab === 'prospects' && (
          prospectsView.type === 'list' ? (
            <DraftClassContent
              onSelectPlayer={handleSelectPlayer}
              onPopoutPlayer={handlePopout}
            />
          ) : (
            franchiseId ? (
              <ProspectDetailView
                prospectId={prospectsView.prospectId}
                franchiseId={franchiseId}
                onPopOut={onAddProspectToWorkspace}
                onBack={handleBack}
              />
            ) : (
              <div className="ref-content">
                <div className="ref-content__error">No franchise connected</div>
                <button className="player-detail__back" onClick={handleBack}>← Back to prospects</button>
              </div>
            )
          )
        )}
      </div>
    </div>
  );
};

export default DraftPanel;
