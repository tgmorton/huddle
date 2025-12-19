/**
 * ManagementV2 - Redesigned management screen
 *
 * Design principles:
 * 1. Primary view answers "what needs attention?"
 * 2. Reference panels (Roster, Depth Chart) open as overlays
 * 3. Context always visible (season position, week phase)
 * 4. Extensible slot system for new content types
 */

import React, { useState } from 'react';
import './ManagementV2.css';

// Types
type WeekPhase = 'recovery' | 'practice' | 'prep' | 'gameday';
type OverlayType = 'roster' | 'depth-chart' | 'schedule' | 'staff' | 'standings' | null;

interface AgendaItem {
  id: string;
  type: 'practice' | 'game' | 'meeting' | 'deadline' | 'decision';
  title: string;
  subtitle?: string;
  urgency: 'now' | 'today' | 'soon' | 'info';
  timeLeft?: string;
  action?: string;
}

interface NewsItem {
  id: string;
  text: string;
  isBreaking?: boolean;
}

// Demo data
const DEMO_AGENDA: AgendaItem[] = [
  { id: '1', type: 'practice', title: 'Practice Session', subtitle: '2 hours scheduled', urgency: 'now', action: 'Run Practice' },
  { id: '2', type: 'decision', title: 'WR Contract Decision', subtitle: 'J. Smith wants extension', urgency: 'today', timeLeft: '6h left' },
  { id: '3', type: 'meeting', title: 'Scout Report Ready', subtitle: 'vs Dallas defense breakdown', urgency: 'soon' },
  { id: '4', type: 'deadline', title: 'Roster Cutdown', subtitle: 'Must reach 53 players', urgency: 'soon', timeLeft: '2 days' },
];

const DEMO_NEWS: NewsItem[] = [
  { id: '1', text: 'Cowboys lose starting QB to injury, out 4-6 weeks', isBreaking: true },
  { id: '2', text: 'League announces new overtime rules for playoffs' },
  { id: '3', text: 'Giants sign veteran CB from practice squad' },
];

export const ManagementV2: React.FC = () => {
  const [activeOverlay, setActiveOverlay] = useState<OverlayType>(null);
  const [isTickerCollapsed, setIsTickerCollapsed] = useState(false);
  const [isPaused, setIsPaused] = useState(true);
  const [speed, setSpeed] = useState<1 | 2 | 3>(2);

  // Demo state
  const weekPhase: WeekPhase = 'practice';
  const currentWeek = 5;
  const dayName = 'Thursday';
  const record = { wins: 3, losses: 1 };
  const nextOpponent = 'DAL';

  const getPhaseLabel = (phase: WeekPhase) => {
    switch (phase) {
      case 'recovery': return 'Recovery Day';
      case 'practice': return 'Practice Day';
      case 'prep': return 'Final Prep';
      case 'gameday': return 'Game Day';
    }
  };

  return (
    <div className="mgmt2" data-phase={weekPhase}>
      {/* Context Bar - Always visible, shows where you are */}
      <header className="mgmt2__context">
        <div className="mgmt2__context-left">
          <span className="mgmt2__week">Week {currentWeek}</span>
          <span className="mgmt2__separator">·</span>
          <span className="mgmt2__day">{dayName}</span>
          <span className="mgmt2__separator">·</span>
          <span className="mgmt2__phase" data-phase={weekPhase}>{getPhaseLabel(weekPhase)}</span>
        </div>

        <div className="mgmt2__context-center">
          <TimeControls
            isPaused={isPaused}
            speed={speed}
            onTogglePause={() => setIsPaused(!isPaused)}
            onSetSpeed={setSpeed}
          />
        </div>

        <div className="mgmt2__context-right">
          <span className="mgmt2__record">{record.wins}-{record.losses}</span>
          <span className="mgmt2__next">Next: vs {nextOpponent}</span>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="mgmt2__main">
        {/* Primary View - The Agenda */}
        <section className="mgmt2__primary">
          <div className="mgmt2__primary-header">
            <h1 className="mgmt2__title">Today's Agenda</h1>
            <span className="mgmt2__count">{DEMO_AGENDA.length} items</span>
          </div>

          <div className="mgmt2__agenda">
            {DEMO_AGENDA.map(item => (
              <AgendaCard key={item.id} item={item} />
            ))}
          </div>

          {DEMO_AGENDA.length === 0 && (
            <div className="mgmt2__empty">
              <p>Nothing requires attention right now.</p>
              <p className="mgmt2__empty-hint">Time will advance automatically, or use the controls above.</p>
            </div>
          )}
        </section>

        {/* Quick Access Bar - Reference panels */}
        <nav className="mgmt2__quickbar">
          <QuickAccessButton
            label="Roster"
            badge="53"
            isActive={activeOverlay === 'roster'}
            onClick={() => setActiveOverlay(activeOverlay === 'roster' ? null : 'roster')}
          />
          <QuickAccessButton
            label="Depth Chart"
            isActive={activeOverlay === 'depth-chart'}
            onClick={() => setActiveOverlay(activeOverlay === 'depth-chart' ? null : 'depth-chart')}
          />
          <QuickAccessButton
            label="Schedule"
            badge="12"
            isActive={activeOverlay === 'schedule'}
            onClick={() => setActiveOverlay(activeOverlay === 'schedule' ? null : 'schedule')}
          />
          <QuickAccessButton
            label="Staff"
            isActive={activeOverlay === 'staff'}
            onClick={() => setActiveOverlay(activeOverlay === 'staff' ? null : 'staff')}
          />
          <QuickAccessButton
            label="Standings"
            isActive={activeOverlay === 'standings'}
            onClick={() => setActiveOverlay(activeOverlay === 'standings' ? null : 'standings')}
          />
        </nav>
      </main>

      {/* News Ticker - Collapsible */}
      <footer className={`mgmt2__ticker ${isTickerCollapsed ? 'mgmt2__ticker--collapsed' : ''}`}>
        <button
          className="mgmt2__ticker-toggle"
          onClick={() => setIsTickerCollapsed(!isTickerCollapsed)}
          aria-label={isTickerCollapsed ? 'Show news' : 'Hide news'}
        >
          {isTickerCollapsed ? '▲ NEWS' : '▼'}
        </button>
        {!isTickerCollapsed && (
          <div className="mgmt2__ticker-content">
            {DEMO_NEWS.map((item, i) => (
              <span key={item.id} className={`mgmt2__ticker-item ${item.isBreaking ? 'mgmt2__ticker-item--breaking' : ''}`}>
                {item.isBreaking && <span className="mgmt2__ticker-breaking">BREAKING</span>}
                {item.text}
                {i < DEMO_NEWS.length - 1 && <span className="mgmt2__ticker-sep">•</span>}
              </span>
            ))}
          </div>
        )}
      </footer>

      {/* Overlay Panel - Opens over main content */}
      {activeOverlay && (
        <OverlayPanel
          type={activeOverlay}
          onClose={() => setActiveOverlay(null)}
        />
      )}
    </div>
  );
};

// === Sub-components ===

interface TimeControlsProps {
  isPaused: boolean;
  speed: 1 | 2 | 3;
  onTogglePause: () => void;
  onSetSpeed: (speed: 1 | 2 | 3) => void;
}

const TimeControls: React.FC<TimeControlsProps> = ({ isPaused, speed, onTogglePause, onSetSpeed }) => {
  return (
    <div className="time-controls">
      <button
        className={`time-controls__playpause ${isPaused ? '' : 'time-controls__playpause--playing'}`}
        onClick={onTogglePause}
        aria-label={isPaused ? 'Play' : 'Pause'}
      >
        {isPaused ? '▶' : '❚❚'}
      </button>
      <div className="time-controls__speed">
        {[1, 2, 3].map(s => (
          <button
            key={s}
            className={`time-controls__speed-btn ${speed === s ? 'time-controls__speed-btn--active' : ''}`}
            onClick={() => onSetSpeed(s as 1 | 2 | 3)}
            disabled={isPaused}
          >
            {'▸'.repeat(s)}
          </button>
        ))}
      </div>
      <span className="time-controls__label">
        {isPaused ? 'Paused' : `${['Slow', 'Normal', 'Fast'][speed - 1]}`}
      </span>
    </div>
  );
};

interface AgendaCardProps {
  item: AgendaItem;
}

const AgendaCard: React.FC<AgendaCardProps> = ({ item }) => {
  const urgencyLabel = {
    now: 'Now',
    today: 'Today',
    soon: 'Soon',
    info: '',
  };

  return (
    <article className={`agenda-card agenda-card--${item.urgency}`} data-type={item.type}>
      <div className="agenda-card__urgency">
        {urgencyLabel[item.urgency]}
      </div>

      <div className="agenda-card__content">
        <h3 className="agenda-card__title">{item.title}</h3>
        {item.subtitle && <p className="agenda-card__subtitle">{item.subtitle}</p>}
      </div>

      <div className="agenda-card__meta">
        {item.timeLeft && <span className="agenda-card__time">{item.timeLeft}</span>}
        {item.action && (
          <button className="agenda-card__action">{item.action}</button>
        )}
      </div>
    </article>
  );
};

interface QuickAccessButtonProps {
  label: string;
  badge?: string;
  isActive: boolean;
  onClick: () => void;
}

const QuickAccessButton: React.FC<QuickAccessButtonProps> = ({ label, badge, isActive, onClick }) => {
  return (
    <button
      className={`quickbar__btn ${isActive ? 'quickbar__btn--active' : ''}`}
      onClick={onClick}
    >
      <span className="quickbar__label">{label}</span>
      {badge && <span className="quickbar__badge">{badge}</span>}
    </button>
  );
};

interface OverlayPanelProps {
  type: OverlayType;
  onClose: () => void;
}

const OverlayPanel: React.FC<OverlayPanelProps> = ({ type, onClose }) => {
  const titles: Record<NonNullable<OverlayType>, string> = {
    'roster': 'Team Roster',
    'depth-chart': 'Depth Chart',
    'schedule': 'Season Schedule',
    'staff': 'Coaching Staff',
    'standings': 'League Standings',
  };

  return (
    <div className="overlay">
      <div className="overlay__backdrop" onClick={onClose} />
      <div className="overlay__panel">
        <header className="overlay__header">
          <h2 className="overlay__title">{type ? titles[type] : ''}</h2>
          <button className="overlay__close" onClick={onClose} aria-label="Close">×</button>
        </header>
        <div className="overlay__content">
          {/* Placeholder - would render actual RosterPanel, DepthChartPanel, etc. */}
          <div className="overlay__placeholder">
            <p>{type ? titles[type] : ''} content would render here.</p>
            <p className="overlay__placeholder-hint">
              This overlay pattern allows reference panels to open without losing
              context of the main agenda view.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ManagementV2;
