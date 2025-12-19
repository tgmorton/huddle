// QueuePanel.tsx - Panel showing upcoming agenda items

import React from 'react';
import type { AgendaItem } from '../types';
import { TYPE_CONFIG } from '../constants';

// === QueueCard (internal component) ===

interface QueueCardProps {
  item: AgendaItem;
  onClick?: () => void;
}

const QueueCard: React.FC<QueueCardProps> = ({ item, onClick }) => {
  const config = TYPE_CONFIG[item.type];

  return (
    <button className="queue-card" data-type={item.type} onClick={onClick}>
      <span className="queue-card__abbr" data-type={item.type}>{config.abbr}</span>
      <div className="queue-card__content">
        <h3 className="queue-card__title">{item.title}</h3>
        <p className="queue-card__subtitle">{item.subtitle}</p>
      </div>
      {item.timeLeft && (
        <span className="queue-card__time">{item.timeLeft}</span>
      )}
    </button>
  );
};

// === QueuePanel ===

interface QueuePanelProps {
  items: AgendaItem[];
  onItemClick?: (item: AgendaItem) => void;
}

export const QueuePanel: React.FC<QueuePanelProps> = ({ items, onItemClick }) => {
  return (
    <div className="queue-panel">
      <h2 className="queue-panel__title">Up Next</h2>
      {items.length > 0 ? (
        <div className="queue-panel__list">
          {items.map(item => (
            <QueueCard key={item.id} item={item} onClick={() => onItemClick?.(item)} />
          ))}
        </div>
      ) : (
        <p className="queue-panel__empty">Nothing else today</p>
      )}
    </div>
  );
};

export default QueuePanel;
