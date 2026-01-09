/**
 * ManagementEventModal - Modal for displaying critical management events.
 *
 * Used for events with display_mode: 'MODAL' - injuries, critical decisions,
 * trade deadlines, etc. that require immediate attention.
 */

import React from 'react';
import { X, AlertTriangle, Briefcase, Shield, Users, FileText, DollarSign, UserMinus, Clock, MessageSquare } from 'lucide-react';
import type { ManagementEvent } from '../../../types/management';

interface ManagementEventModalProps {
  event: ManagementEvent;
  onAttend: () => void;
  onDismiss: () => void;
}

// Map categories to icons
const categoryIcons: Record<string, React.FC<{ size: number }>> = {
  FREE_AGENCY: Users,
  TRADE: Briefcase,
  CONTRACT: FileText,
  ROSTER: Users,
  PRACTICE: Shield,
  MEETING: Users,
  GAME: Shield,
  SCOUTING: Users,
  DRAFT: Users,
  STAFF: Briefcase,
  DEADLINE: AlertTriangle,
  SYSTEM: AlertTriangle,
};

// Map event subtypes to more specific icons
const getContractIcon = (payload: Record<string, unknown> | undefined): React.FC<{ size: number }> => {
  const subtype = payload?.subtype as string | undefined;
  switch (subtype) {
    case 'holdout': return UserMinus;
    case 'extension_deadline': return Clock;
    case 'agent_demand': return MessageSquare;
    case 'signed': return FileText;
    default: return DollarSign;
  }
};

// Map priority to severity class
const priorityToSeverity: Record<string, string> = {
  CRITICAL: 'critical',
  HIGH: 'warning',
  NORMAL: 'info',
  LOW: 'info',
  BACKGROUND: 'info',
};

export const ManagementEventModal: React.FC<ManagementEventModalProps> = ({
  event,
  onAttend,
  onDismiss,
}) => {
  // Use contract-specific icons when applicable
  const IconComponent = event.category === 'CONTRACT'
    ? getContractIcon(event.payload)
    : categoryIcons[event.category] || AlertTriangle;
  const severity = priorityToSeverity[event.priority] || 'info';

  return (
    <div className="event-modal-overlay" onClick={event.can_dismiss ? onDismiss : undefined}>
      <div
        className="event-modal"
        data-severity={severity}
        onClick={e => e.stopPropagation()}
      >
        {event.can_dismiss && (
          <button className="event-modal__close" onClick={onDismiss}>
            <X size={18} />
          </button>
        )}

        <header className="event-modal__header">
          <span className="event-modal__icon">
            <IconComponent size={24} />
          </span>
          <div className="event-modal__titles">
            <h2 className="event-modal__title">{event.title}</h2>
            <span className="event-modal__subtitle">{event.category.replace('_', ' ')}</span>
          </div>
        </header>

        <div className="event-modal__body">
          <p className="event-modal__description">{event.description}</p>
        </div>

        <footer className="event-modal__footer">
          {event.can_dismiss && (
            <button
              className="event-modal__btn event-modal__btn--secondary"
              onClick={onDismiss}
            >
              {event.can_delegate ? 'Delegate' : 'Dismiss'}
            </button>
          )}
          <button
            className="event-modal__btn event-modal__btn--primary"
            onClick={onAttend}
          >
            Attend
          </button>
        </footer>
      </div>
    </div>
  );
};

export default ManagementEventModal;
