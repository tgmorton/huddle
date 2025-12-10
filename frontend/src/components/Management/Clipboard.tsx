/**
 * Clipboard - Right side panel with tabs and event list
 */

import React from 'react';
import {
  useManagementStore,
  selectActiveTab,
  selectAvailableTabs,
  selectTabBadges,
  selectPendingEvents,
} from '../../stores/managementStore';
import type { ClipboardTab, ManagementEvent } from '../../types/management';
import { TAB_DISPLAY_NAMES, PRIORITY_COLORS } from '../../types/management';
import './Clipboard.css';

interface ClipboardProps {
  onSelectTab: (tab: ClipboardTab) => void;
  onAttendEvent: (eventId: string) => void;
  onDismissEvent: (eventId: string) => void;
}

export const Clipboard: React.FC<ClipboardProps> = ({
  onSelectTab,
  onAttendEvent,
  onDismissEvent,
}) => {
  const activeTab = useManagementStore(selectActiveTab);
  const availableTabs = useManagementStore(selectAvailableTabs);
  const tabBadges = useManagementStore(selectTabBadges);
  const pendingEvents = useManagementStore(selectPendingEvents);

  return (
    <div className="clipboard">
      {/* Tab Bar */}
      <div className="clipboard__tabs">
        {availableTabs.slice(0, 6).map((tab) => (
          <button
            key={tab}
            className={`clipboard__tab ${activeTab === tab ? 'active' : ''}`}
            onClick={() => onSelectTab(tab)}
          >
            <span className="clipboard__tab-name">{TAB_DISPLAY_NAMES[tab]}</span>
            {tabBadges[tab] > 0 && (
              <span className="clipboard__tab-badge">{tabBadges[tab]}</span>
            )}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div className="clipboard__content">
        {activeTab === 'EVENTS' && (
          <EventList
            events={pendingEvents}
            onAttend={onAttendEvent}
            onDismiss={onDismissEvent}
          />
        )}
        {activeTab === 'ROSTER' && <PlaceholderPanel title="Roster" />}
        {activeTab === 'DEPTH_CHART' && <PlaceholderPanel title="Depth Chart" />}
        {activeTab === 'SCHEDULE' && <PlaceholderPanel title="Schedule" />}
        {activeTab === 'COACHING_STAFF' && <PlaceholderPanel title="Coaching Staff" />}
        {activeTab === 'STANDINGS' && <PlaceholderPanel title="Standings" />}
      </div>
    </div>
  );
};

interface EventListProps {
  events: ManagementEvent[];
  onAttend: (eventId: string) => void;
  onDismiss: (eventId: string) => void;
}

const EventList: React.FC<EventListProps> = ({ events, onAttend, onDismiss }) => {
  if (events.length === 0) {
    return (
      <div className="clipboard__empty">
        <div className="clipboard__empty-icon">📋</div>
        <div className="clipboard__empty-text">No pending events</div>
        <div className="clipboard__empty-hint">
          Events will appear here as time progresses
        </div>
      </div>
    );
  }

  return (
    <div className="clipboard__events">
      {events.map((event) => (
        <EventCard
          key={event.id}
          event={event}
          onAttend={() => onAttend(event.id)}
          onDismiss={() => onDismiss(event.id)}
        />
      ))}
    </div>
  );
};

interface EventCardProps {
  event: ManagementEvent;
  onAttend: () => void;
  onDismiss: () => void;
}

const EventCard: React.FC<EventCardProps> = ({ event, onAttend, onDismiss }) => {
  const priorityColor = PRIORITY_COLORS[event.priority];
  const isUrgent = event.is_urgent;

  return (
    <div
      className={`event-card ${isUrgent ? 'urgent' : ''}`}
      style={{ borderLeftColor: priorityColor }}
    >
      <div className="event-card__header">
        <span
          className="event-card__priority"
          style={{ backgroundColor: priorityColor }}
        >
          {event.priority}
        </span>
        <span className="event-card__category">{event.category}</span>
      </div>

      <div className="event-card__title">{event.title}</div>
      <div className="event-card__description">{event.description}</div>

      {event.deadline && (
        <div className="event-card__deadline">
          Deadline: {formatDeadline(event.deadline)}
        </div>
      )}

      <div className="event-card__actions">
        <button className="event-card__btn event-card__btn--attend" onClick={onAttend}>
          Attend
        </button>
        {event.can_dismiss && (
          <button
            className="event-card__btn event-card__btn--dismiss"
            onClick={onDismiss}
          >
            Dismiss
          </button>
        )}
      </div>
    </div>
  );
};

interface PlaceholderPanelProps {
  title: string;
}

const PlaceholderPanel: React.FC<PlaceholderPanelProps> = ({ title }) => {
  return (
    <div className="clipboard__placeholder">
      <div className="clipboard__placeholder-title">{title}</div>
      <div className="clipboard__placeholder-text">Coming soon...</div>
    </div>
  );
};

function formatDeadline(deadline: string): string {
  const date = new Date(deadline);
  const now = new Date();
  const diff = date.getTime() - now.getTime();

  if (diff < 0) return 'Expired';

  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

  if (hours > 24) {
    const days = Math.floor(hours / 24);
    return `${days}d ${hours % 24}h`;
  }

  return `${hours}h ${minutes}m`;
}
