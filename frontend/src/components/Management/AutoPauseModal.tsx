/**
 * AutoPauseModal - Modal shown when game auto-pauses for important events
 */

import React from 'react';
import { useManagementStore } from '../../stores/managementStore';
import type { TimeSpeed } from '../../types/management';
import './AutoPauseModal.css';

interface AutoPauseModalProps {
  onDismiss: (speed?: TimeSpeed) => void;
}

export const AutoPauseModal: React.FC<AutoPauseModalProps> = ({ onDismiss }) => {
  const { autoPauseReason, autoPauseEventId: _autoPauseEventId, dismissAutoPause } = useManagementStore();

  const handleContinue = () => {
    dismissAutoPause();
    onDismiss('NORMAL');
  };

  const handleStayPaused = () => {
    dismissAutoPause();
  };

  return (
    <div className="auto-pause-modal__overlay">
      <div className="auto-pause-modal">
        <div className="auto-pause-modal__icon">⏸️</div>
        <h2 className="auto-pause-modal__title">Game Paused</h2>
        <p className="auto-pause-modal__reason">{autoPauseReason}</p>
        <p className="auto-pause-modal__hint">
          An important event requires your attention
        </p>
        <div className="auto-pause-modal__actions">
          <button
            className="auto-pause-modal__btn auto-pause-modal__btn--secondary"
            onClick={handleStayPaused}
          >
            Stay Paused
          </button>
          <button
            className="auto-pause-modal__btn auto-pause-modal__btn--primary"
            onClick={handleContinue}
          >
            Continue
          </button>
        </div>
      </div>
    </div>
  );
};
