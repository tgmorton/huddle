/**
 * ActivePanel - Left side content panel that shows event details or other views
 */

import React from 'react';
import { useManagementStore } from '../../stores/managementStore';
import './ActivePanel.css';

interface ActivePanelProps {
  onGoBack: () => void;
}

export const ActivePanel: React.FC<ActivePanelProps> = ({ onGoBack }) => {
  const clipboard = useManagementStore((state) => state.clipboard);
  const events = useManagementStore((state) => state.events);

  if (!clipboard) {
    return (
      <div className="active-panel active-panel--loading">
        <div className="active-panel__loader">Loading...</div>
      </div>
    );
  }

  const { panel } = clipboard;
  const canGoBack = panel.can_go_back;

  // If viewing an event detail
  if (panel.panel_type === 'EVENT_DETAIL' && panel.event_id) {
    const event = events?.pending.find((e) => e.id === panel.event_id);
    if (event) {
      return (
        <div className="active-panel">
          {canGoBack && (
            <button className="active-panel__back-btn" onClick={onGoBack}>
              ← Back
            </button>
          )}
          <EventDetailView event={event} />
        </div>
      );
    }
  }

  // Default welcome/dashboard view
  return (
    <div className="active-panel">
      <DashboardView />
    </div>
  );
};

interface EventDetailViewProps {
  event: {
    id: string;
    title: string;
    description: string;
    category: string;
    priority: string;
    deadline: string | null;
    payload: Record<string, unknown>;
  };
}

const EventDetailView: React.FC<EventDetailViewProps> = ({ event }) => {
  return (
    <div className="event-detail">
      <div className="event-detail__header">
        <span className="event-detail__category">{event.category}</span>
        <span className="event-detail__priority">{event.priority}</span>
      </div>

      <h2 className="event-detail__title">{event.title}</h2>
      <p className="event-detail__description">{event.description}</p>

      {event.deadline && (
        <div className="event-detail__deadline">
          <strong>Deadline:</strong> {new Date(event.deadline).toLocaleString()}
        </div>
      )}

      <div className="event-detail__content">
        {/* Event-specific content would go here */}
        <div className="event-detail__placeholder">
          <p>Event details and actions will appear here based on event type.</p>
          <p>This could include:</p>
          <ul>
            <li>Free agent signing interface</li>
            <li>Trade negotiation screen</li>
            <li>Practice drill selection</li>
            <li>Game preparation options</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

const DashboardView: React.FC = () => {
  const calendar = useManagementStore((state) => state.calendar);
  const events = useManagementStore((state) => state.events);

  return (
    <div className="dashboard">
      <div className="dashboard__header">
        <h1 className="dashboard__title">Franchise Dashboard</h1>
        {calendar && (
          <div className="dashboard__subtitle">
            {calendar.week_display} - {calendar.season_year} Season
          </div>
        )}
      </div>

      <div className="dashboard__grid">
        {/* Quick Stats */}
        <div className="dashboard__card">
          <h3 className="dashboard__card-title">Pending Events</h3>
          <div className="dashboard__card-value">{events?.pending.length ?? 0}</div>
          <div className="dashboard__card-label">
            {events?.urgent_count ?? 0} urgent
          </div>
        </div>

        <div className="dashboard__card">
          <h3 className="dashboard__card-title">Current Phase</h3>
          <div className="dashboard__card-value">
            {calendar?.phase.replace(/_/g, ' ') ?? '-'}
          </div>
          <div className="dashboard__card-label">
            {calendar?.day_name ?? '-'}
          </div>
        </div>

        <div className="dashboard__card">
          <h3 className="dashboard__card-title">Time</h3>
          <div className="dashboard__card-value">{calendar?.time_display ?? '-'}</div>
          <div className="dashboard__card-label">{calendar?.date_display ?? '-'}</div>
        </div>
      </div>

      <div className="dashboard__instructions">
        <h3>Getting Started</h3>
        <p>
          Welcome to your franchise! Use the clipboard on the right to manage
          events and navigate through different aspects of your team.
        </p>
        <ul>
          <li>
            <strong>Events Tab:</strong> Handle incoming events like free agent
            signings, trades, and games
          </li>
          <li>
            <strong>Roster Tab:</strong> View and manage your team's roster
          </li>
          <li>
            <strong>Schedule Tab:</strong> See upcoming games
          </li>
        </ul>
        <p>
          Use the time controls in the top bar to pause, play, or speed up the
          simulation.
        </p>
      </div>
    </div>
  );
};
