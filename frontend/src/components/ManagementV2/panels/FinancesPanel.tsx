// FinancesPanel.tsx - Salary Cap, Contracts tabs

import React, { useState, useCallback } from 'react';
import { SalaryCapContent } from '../content/SalaryCapContent';
import { ContractsContent } from '../content/ContractsContent';

type FinancesTab = 'cap' | 'contracts';

interface FinancesPanelProps {
  onAddPlayerToWorkspace?: (player: { id: string; name: string; position: string; overall: number }) => void;
}

export const FinancesPanel: React.FC<FinancesPanelProps> = ({ onAddPlayerToWorkspace }) => {
  const [tab, setTab] = useState<FinancesTab>('cap');

  // Handler for player clicks - will fetch player details and add to workspace
  const handlePlayerClick = useCallback((playerId: string, playerName: string, position: string, overall: number) => {
    if (onAddPlayerToWorkspace) {
      onAddPlayerToWorkspace({
        id: playerId,
        name: playerName,
        position,
        overall,
      });
    }
  }, [onAddPlayerToWorkspace]);

  return (
    <div className="tabbed-panel">
      <div className="tabbed-panel__tabs">
        <button className={`tabbed-panel__tab ${tab === 'cap' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('cap')}>Salary Cap</button>
        <button className={`tabbed-panel__tab ${tab === 'contracts' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('contracts')}>Contracts</button>
      </div>
      <div className="tabbed-panel__content">
        {tab === 'cap' && <SalaryCapContent onPlayerClick={handlePlayerClick} />}
        {tab === 'contracts' && <ContractsContent onPlayerClick={handlePlayerClick} />}
      </div>
    </div>
  );
};

export default FinancesPanel;
