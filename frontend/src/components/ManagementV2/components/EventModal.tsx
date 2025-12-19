// EventModal.tsx - Modal overlay for game events (injuries, trades, etc.)

import React from 'react';
import { X } from 'lucide-react';
import type { GameEvent } from '../types';

interface EventModalProps {
  event: GameEvent;
  onDismiss: () => void;
}

const typeIcon: Record<string, string> = {
  injury: '🏥',
  trade_offer: '🔄',
  media: '🎤',
  contract_demand: '💰',
  morale: '😤',
};

export const EventModal: React.FC<EventModalProps> = ({ event, onDismiss }) => {
  return (
    <div className="event-modal-overlay" onClick={onDismiss}>
      <div
        className="event-modal"
        data-severity={event.severity}
        onClick={e => e.stopPropagation()}
      >
        <button className="event-modal__close" onClick={onDismiss}>
          <X size={18} />
        </button>

        <header className="event-modal__header">
          <span className="event-modal__icon">{typeIcon[event.type]}</span>
          <div className="event-modal__titles">
            <h2 className="event-modal__title">{event.title}</h2>
            <span className="event-modal__subtitle">{event.subtitle}</span>
          </div>
        </header>

        <div className="event-modal__body">
          <p className="event-modal__description">{event.description}</p>
        </div>

        <footer className="event-modal__footer">
          {event.options.map((option, idx) => (
            <button
              key={idx}
              className={`event-modal__btn event-modal__btn--${option.variant}`}
              onClick={onDismiss}
            >
              {option.label}
            </button>
          ))}
        </footer>
      </div>
    </div>
  );
};

export default EventModal;
