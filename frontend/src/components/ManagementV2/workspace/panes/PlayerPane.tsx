// PlayerPane.tsx - Player detail pane for workspace
// Wraps the unified PlayerView component

import React from 'react';
import { PlayerView } from '../../components';

interface PlayerPaneProps {
  playerId: string;
  onComplete?: () => void;
  defaultAttributesExpanded?: boolean;
}

export const PlayerPane: React.FC<PlayerPaneProps> = ({
  playerId,
  onComplete,
  defaultAttributesExpanded = false,
}) => {
  return (
    <div className="pane pane--no-header">
      <div className="pane__body">
        <PlayerView
          playerId={playerId}
          variant="pane"
          defaultAttributesExpanded={defaultAttributesExpanded}
          onComplete={onComplete}
        />
      </div>
    </div>
  );
};

export default PlayerPane;
