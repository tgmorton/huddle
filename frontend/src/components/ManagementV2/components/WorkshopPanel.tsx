/**
 * WorkshopPanel - Development debug panel with tabbed interface
 *
 * Tabs:
 * - Status: Franchise/calendar state overview
 * - Events: Event queue inspector with scheduled times
 * - Calendar: Time controls and week timeline
 * - Actions: Quick dev actions for testing
 * - Log: Real-time log entries
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { X, Wifi, WifiOff, Trash2, Download, Activity, List, Calendar, Zap, Terminal, GripHorizontal, RefreshCw, Play, Clock } from 'lucide-react';
import { useManagementStore } from '../../../stores/managementStore';
import { managementApi } from '../../../api/managementClient';
import type { ManagementEvent } from '../../../types/management';

// Tab types
type DebugTab = 'status' | 'events' | 'calendar' | 'actions' | 'log';

interface TabConfig {
  id: DebugTab;
  label: string;
  icon: typeof Activity;
}

const TABS: TabConfig[] = [
  { id: 'status', label: 'Status', icon: Activity },
  { id: 'events', label: 'Events', icon: List },
  { id: 'calendar', label: 'Calendar', icon: Calendar },
  { id: 'actions', label: 'Actions', icon: Zap },
  { id: 'log', label: 'Log', icon: Terminal },
];

const MIN_HEIGHT = 150;
const MAX_HEIGHT = 600;
const DEFAULT_HEIGHT = 280;

export interface LogEntry {
  id: string;
  timestamp: Date;
  message: string;
  type: 'info' | 'success' | 'error' | 'warning' | 'event' | 'ws';
}

interface WorkshopPanelProps {
  isOpen: boolean;
  onClose: () => void;
  logs: LogEntry[];
  onClearLogs: () => void;
  onLog?: (message: string, type: LogEntry['type']) => void;
  onEventClick?: (event: ManagementEvent) => void;  // Click to open event in workspace
}

export const WorkshopPanel: React.FC<WorkshopPanelProps> = ({
  isOpen,
  onClose,
  logs,
  onClearLogs,
  onLog,
  onEventClick,
}) => {
  const logEndRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLElement>(null);
  const [activeTab, setActiveTab] = useState<DebugTab>('status');
  const [panelHeight, setPanelHeight] = useState(DEFAULT_HEIGHT);
  const [isDragging, setIsDragging] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Get state from management store
  const store = useManagementStore();
  const {
    isConnected,
    isLoading,
    error,
    franchiseId,
    calendar,
    events,
    state,
    updateCalendar,
    setEvents,
  } = store;

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (activeTab === 'log') {
      logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs.length, activeTab]);

  // Drag handlers for resizing
  const handleDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const newHeight = window.innerHeight - e.clientY;
      setPanelHeight(Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, newHeight)));
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  };

  // Format relative time for events
  const formatRelativeTime = (dateStr: string | null, currentDate: string | null): string => {
    if (!dateStr) return '';
    if (!currentDate) return dateStr;

    const eventDate = new Date(dateStr);
    const now = new Date(currentDate);
    const diffMs = eventDate.getTime() - now.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays < 0) return `${Math.abs(diffDays)}d ago`;
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Tomorrow';
    if (diffDays < 7) return `in ${diffDays}d`;
    if (diffDays < 14) return 'next week';
    return `in ${Math.floor(diffDays / 7)}w`;
  };

  const getTypeClass = (type: LogEntry['type']) => {
    switch (type) {
      case 'success': return 'workshop-log__entry--success';
      case 'error': return 'workshop-log__entry--error';
      case 'warning': return 'workshop-log__entry--warning';
      case 'event': return 'workshop-log__entry--event';
      case 'ws': return 'workshop-log__entry--ws';
      default: return '';
    }
  };

  const getTypePrefix = (type: LogEntry['type']) => {
    switch (type) {
      case 'success': return '[OK]';
      case 'error': return '[ERR]';
      case 'warning': return '[WARN]';
      case 'event': return '[EVT]';
      case 'ws': return '[WS]';
      default: return '[INFO]';
    }
  };

  const exportLogs = () => {
    const content = logs
      .map(log => `${formatTime(log.timestamp)} ${getTypePrefix(log.type)} ${log.message}`)
      .join('\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `workshop-log-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Action handlers
  const handleAction = async (action: string) => {
    if (!franchiseId || actionLoading) return;
    setActionLoading(action);

    try {
      switch (action) {
        case 'refresh': {
          const data = await managementApi.getFranchise(franchiseId);
          if (data.calendar) {
            updateCalendar(data.calendar as any);
          }
          if (data.events && typeof data.events === 'object') {
            const evts = data.events as { pending?: ManagementEvent[] };
            if (evts.pending) {
              setEvents(evts.pending);
            }
          }
          onLog?.('State refreshed', 'success');
          break;
        }
        case 'advance': {
          const response = await managementApi.advanceDay(franchiseId);
          updateCalendar(response.calendar as any);
          const newEvents = response.day_events.map(e => ({
            ...e,
            created_at: new Date(e.created_at).toISOString(),
          })) as ManagementEvent[];
          setEvents(newEvents);
          onLog?.(`Advanced to ${response.calendar.current_date}`, 'success');
          break;
        }
        case 'generate': {
          // Generate a test practice event
          const testEvent: ManagementEvent = {
            id: `test-${Date.now()}`,
            event_type: 'practice',
            category: 'PRACTICE',
            priority: 'NORMAL',
            title: 'Position Drills Available',
            description: 'Work on specific skills with your players',
            icon: '🏈',
            created_at: new Date().toISOString(),
            scheduled_for: calendar?.current_date || null,
            deadline: null,
            status: 'PENDING',
            display_mode: 'PANE',
            auto_pause: false,
            requires_attention: true,
            can_dismiss: true,
            can_delegate: false,
            team_id: null,
            player_ids: [],
            payload: {},
            is_urgent: false,
          };
          store.addEvent(testEvent);
          onLog?.('Generated test event', 'success');
          break;
        }
        case 'clear-events': {
          setEvents([]);
          onLog?.('Cleared all events', 'warning');
          break;
        }
      }
    } catch (err) {
      onLog?.(`Action failed: ${err}`, 'error');
    } finally {
      setActionLoading(null);
    }
  };

  if (!isOpen) return null;

  // Get current day name from calendar
  const getDayName = () => {
    if (!calendar?.current_date) return null;
    const date = new Date(calendar.current_date);
    return date.toLocaleDateString('en-US', { weekday: 'long' });
  };

  // Sort events by scheduled date
  const getSortedEvents = () => {
    const eventList = events?.pending || [];
    return [...eventList].sort((a, b) => {
      // Urgent first
      if (a.is_urgent && !b.is_urgent) return -1;
      if (!a.is_urgent && b.is_urgent) return 1;
      // Then by scheduled_for
      if (a.scheduled_for && b.scheduled_for) {
        return new Date(a.scheduled_for).getTime() - new Date(b.scheduled_for).getTime();
      }
      if (a.scheduled_for) return -1;
      if (b.scheduled_for) return 1;
      return 0;
    });
  };

  // Render Status tab content
  const renderStatusTab = () => (
    <div className="workshop-panel__tab-content">
      <div className="workshop-panel__status-grid">
        <div className="workshop-panel__stat">
          <span className="workshop-panel__stat-label">Franchise</span>
          <span className="workshop-panel__stat-value">
            {franchiseId ? (
              <code>{franchiseId.slice(0, 8)}...</code>
            ) : (
              <span className="workshop-panel__stat-value--muted">None</span>
            )}
          </span>
        </div>

        {calendar && (
          <>
            <div className="workshop-panel__stat">
              <span className="workshop-panel__stat-label">Date</span>
              <span className="workshop-panel__stat-value">
                {calendar.current_date || 'N/A'}
              </span>
            </div>
            <div className="workshop-panel__stat">
              <span className="workshop-panel__stat-label">Day</span>
              <span className="workshop-panel__stat-value">{getDayName() || 'N/A'}</span>
            </div>
            <div className="workshop-panel__stat">
              <span className="workshop-panel__stat-label">Phase</span>
              <span className="workshop-panel__stat-value">{calendar.phase}</span>
            </div>
            <div className="workshop-panel__stat">
              <span className="workshop-panel__stat-label">Week</span>
              <span className="workshop-panel__stat-value">{calendar.current_week}</span>
            </div>
            <div className="workshop-panel__stat">
              <span className="workshop-panel__stat-label">Speed</span>
              <span className="workshop-panel__stat-value">{calendar.speed}</span>
            </div>
            <div className="workshop-panel__stat">
              <span className="workshop-panel__stat-label">Paused</span>
              <span className="workshop-panel__stat-value">
                {calendar.is_paused ? 'Yes' : 'No'}
              </span>
            </div>
          </>
        )}

        {events && (
          <div className="workshop-panel__stat">
            <span className="workshop-panel__stat-label">Events</span>
            <span className="workshop-panel__stat-value">
              {events.total_count}
              {events.urgent_count > 0 && (
                <span className="workshop-panel__stat-urgent">
                  ({events.urgent_count} urgent)
                </span>
              )}
            </span>
          </div>
        )}

        <div className="workshop-panel__stat">
          <span className="workshop-panel__stat-label">Connection</span>
          <span className={`workshop-panel__stat-value ${isConnected ? 'workshop-panel__stat-value--success' : 'workshop-panel__stat-value--error'}`}>
            {isConnected ? 'Connected' : isLoading ? 'Connecting...' : 'Disconnected'}
          </span>
        </div>

        {error && (
          <div className="workshop-panel__stat workshop-panel__stat--error">
            <span className="workshop-panel__stat-label">Error</span>
            <span className="workshop-panel__stat-value">{error}</span>
          </div>
        )}
      </div>
    </div>
  );

  // Render a single event item (clickable to open in workspace)
  const renderEventItem = (evt: ManagementEvent, isUpcoming: boolean = false) => {
    const relTime = formatRelativeTime(evt.scheduled_for, calendar?.current_date || null);
    const isClickable = onEventClick && evt.display_mode !== 'TICKER';

    return (
      <button
        key={evt.id}
        className={`workshop-panel__event workshop-panel__event--${evt.priority || 'normal'} ${evt.is_urgent ? 'workshop-panel__event--urgent-flag' : ''} ${isUpcoming ? 'workshop-panel__event--upcoming' : ''} ${isClickable ? 'workshop-panel__event--clickable' : ''}`}
        onClick={() => isClickable && onEventClick(evt)}
        disabled={!isClickable}
        type="button"
      >
        <div className="workshop-panel__event-header">
          <span className={`workshop-panel__event-category workshop-panel__event-category--${evt.category}`}>
            {evt.category?.toUpperCase() || 'EVENT'}
          </span>
          <div className="workshop-panel__event-meta">
            {relTime && (
              <span className="workshop-panel__event-time">
                <Clock size={10} />
                {relTime}
              </span>
            )}
            <span className="workshop-panel__event-priority">{evt.priority}</span>
          </div>
        </div>
        <div className="workshop-panel__event-title">{evt.title}</div>
        {evt.description && (
          <div className="workshop-panel__event-detail">{evt.description}</div>
        )}
      </button>
    );
  };

  // Render Events tab content with pending and upcoming sections
  const renderEventsTab = () => {
    const sortedPending = getSortedEvents();
    const upcomingEvents = events?.upcoming || [];

    const totalCount = sortedPending.length + upcomingEvents.length;

    return (
      <div className="workshop-panel__tab-content">
        <div className="workshop-panel__events-header">
          <span>{totalCount} events</span>
          {events?.urgent_count ? (
            <span className="workshop-panel__urgent-badge">{events.urgent_count} urgent</span>
          ) : null}
        </div>

        {totalCount === 0 ? (
          <div className="workshop-panel__empty">No events</div>
        ) : (
          <div className="workshop-panel__event-sections">
            {/* Pending/Active Events */}
            {sortedPending.length > 0 && (
              <div className="workshop-panel__event-section">
                <div className="workshop-panel__section-label">Active ({sortedPending.length})</div>
                <div className="workshop-panel__event-list">
                  {sortedPending.map(evt => renderEventItem(evt, false))}
                </div>
              </div>
            )}

            {/* Upcoming/Scheduled Events */}
            {upcomingEvents.length > 0 && (
              <div className="workshop-panel__event-section">
                <div className="workshop-panel__section-label workshop-panel__section-label--upcoming">
                  Upcoming ({upcomingEvents.length})
                </div>
                <div className="workshop-panel__event-list">
                  {upcomingEvents.map(evt => renderEventItem(evt, true))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  // Render Calendar tab content
  const renderCalendarTab = () => {
    const days = ['M', 'Tu', 'W', 'Th', 'F', 'Sa', 'Su'];
    const currentDayIdx = calendar?.current_date
      ? (() => {
          const d = new Date(calendar.current_date).getDay();
          return d === 0 ? 6 : d - 1; // Convert Sun=0 to Mon=0
        })()
      : 0;

    return (
      <div className="workshop-panel__tab-content">
        <div className="workshop-panel__calendar">
          {/* Week timeline */}
          <div className="workshop-panel__week-timeline">
            {days.map((day, idx) => (
              <div
                key={day}
                className={`workshop-panel__day ${idx < currentDayIdx ? 'workshop-panel__day--past' : ''} ${idx === currentDayIdx ? 'workshop-panel__day--current' : ''} ${idx === 6 ? 'workshop-panel__day--gameday' : ''}`}
              >
                {day}
              </div>
            ))}
          </div>

          {/* Calendar info */}
          <div className="workshop-panel__calendar-info">
            <div className="workshop-panel__stat">
              <span className="workshop-panel__stat-label">Current Date</span>
              <span className="workshop-panel__stat-value">{calendar?.current_date || 'N/A'}</span>
            </div>
            <div className="workshop-panel__stat">
              <span className="workshop-panel__stat-label">Phase</span>
              <span className="workshop-panel__stat-value">{calendar?.phase || 'N/A'}</span>
            </div>
            <div className="workshop-panel__stat">
              <span className="workshop-panel__stat-label">Week</span>
              <span className="workshop-panel__stat-value">{calendar?.current_week || 'N/A'}</span>
            </div>
          </div>

          {/* Time controls info */}
          <div className="workshop-panel__time-controls">
            <span className="workshop-panel__control-label">Speed: {calendar?.speed || 'normal'}</span>
            <span className="workshop-panel__control-label">
              {calendar?.is_paused ? '⏸ Paused' : '▶ Running'}
            </span>
          </div>
        </div>
      </div>
    );
  };

  // Render Actions tab content
  const renderActionsTab = () => (
    <div className="workshop-panel__tab-content workshop-panel__tab-content--actions">
      <div className="workshop-panel__actions-grid">
        <button
          className="workshop-panel__action-btn"
          onClick={() => handleAction('refresh')}
          disabled={!franchiseId || actionLoading === 'refresh'}
        >
          <RefreshCw size={14} className={actionLoading === 'refresh' ? 'spinning' : ''} />
          <span>Refresh State</span>
        </button>

        <button
          className="workshop-panel__action-btn"
          onClick={() => handleAction('advance')}
          disabled={!franchiseId || actionLoading === 'advance'}
        >
          <Play size={14} />
          <span>Advance Day</span>
        </button>

        <button
          className="workshop-panel__action-btn"
          onClick={() => handleAction('generate')}
          disabled={!franchiseId || actionLoading === 'generate'}
        >
          <Zap size={14} />
          <span>Generate Event</span>
        </button>

        <button
          className="workshop-panel__action-btn workshop-panel__action-btn--danger"
          onClick={() => handleAction('clear-events')}
          disabled={actionLoading === 'clear-events'}
        >
          <Trash2 size={14} />
          <span>Clear Events</span>
        </button>
      </div>

      <div className="workshop-panel__actions-info">
        <div className="workshop-panel__stat">
          <span className="workshop-panel__stat-label">Franchise ID</span>
          <span className="workshop-panel__stat-value">
            {franchiseId ? <code>{franchiseId}</code> : 'None'}
          </span>
        </div>
        <div className="workshop-panel__stat">
          <span className="workshop-panel__stat-label">Store State Keys</span>
          <span className="workshop-panel__stat-value">
            {state ? Object.keys(state).length : 0} keys
          </span>
        </div>
      </div>
    </div>
  );

  // Render Log tab content
  const renderLogTab = () => (
    <div className="workshop-panel__tab-content workshop-panel__tab-content--log">
      <div className="workshop-panel__log-header">
        <span>Log ({logs.length})</span>
        <div className="workshop-panel__log-actions">
          <button
            className="workshop-panel__btn"
            onClick={exportLogs}
            title="Export logs"
            disabled={logs.length === 0}
          >
            <Download size={12} />
          </button>
          <button
            className="workshop-panel__btn"
            onClick={onClearLogs}
            title="Clear logs"
            disabled={logs.length === 0}
          >
            <Trash2 size={12} />
          </button>
        </div>
      </div>

      <div className="workshop-log">
        {logs.length === 0 ? (
          <div className="workshop-log__empty">No log entries</div>
        ) : (
          logs.map(log => (
            <div
              key={log.id}
              className={`workshop-log__entry ${getTypeClass(log.type)}`}
            >
              <span className="workshop-log__time">{formatTime(log.timestamp)}</span>
              <span className="workshop-log__prefix">{getTypePrefix(log.type)}</span>
              <span className="workshop-log__message">{log.message}</span>
            </div>
          ))
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );

  // Render active tab content
  const renderTabContent = () => {
    switch (activeTab) {
      case 'status': return renderStatusTab();
      case 'events': return renderEventsTab();
      case 'calendar': return renderCalendarTab();
      case 'actions': return renderActionsTab();
      case 'log': return renderLogTab();
      default: return renderStatusTab();
    }
  };

  return (
    <aside
      ref={panelRef}
      className={`workshop-panel ${isDragging ? 'workshop-panel--dragging' : ''}`}
      style={{ height: panelHeight }}
    >
      {/* Drag Handle */}
      <div
        className="workshop-panel__drag-handle"
        onMouseDown={handleDragStart}
      >
        <GripHorizontal size={16} />
      </div>

      <header className="workshop-panel__header">
        <h2>Workshop</h2>
        <div className="workshop-panel__status">
          {isConnected ? (
            <span className="workshop-panel__connected">
              <Wifi size={14} />
            </span>
          ) : (
            <span className="workshop-panel__disconnected">
              <WifiOff size={14} />
            </span>
          )}
        </div>
        <button className="workshop-panel__close" onClick={onClose}>
          <X size={16} />
        </button>
      </header>

      {/* Tab Bar */}
      <nav className="workshop-panel__tabs">
        {TABS.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              className={`workshop-panel__tab ${activeTab === tab.id ? 'workshop-panel__tab--active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon size={14} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Tab Content */}
      <div className="workshop-panel__content">
        {renderTabContent()}
      </div>
    </aside>
  );
};

export default WorkshopPanel;
