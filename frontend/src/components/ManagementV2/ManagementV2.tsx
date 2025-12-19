/**
 * ManagementV2 - Redesigned management screen (v6)
 *
 * Layout:
 * - Left icon nav (full height) - app switcher, queue, quick access views
 * - Header and ticker span full width of body
 * - Left panel (queue/reference) sits between header and ticker
 * - Panel swaps content based on icon selection
 * - No panel header - icon nav shows what's active
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Menu,
  Users,
  Calendar,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  X,
  GripVertical,
  Maximize2,
  ArrowLeftRight,
  DollarSign,
  ClipboardCheck,
  Heart,
} from 'lucide-react';
import './ManagementV2.css';

// Local imports
import type {
  WeekPhase,
  WorkspaceItem,
  AgendaItem,
  GameEvent,
  LeftPanelView,
  Player,
  RosterView,
  PlayerStats,
} from './types';
import { TYPE_SIZE, TYPE_CONFIG, NAV_GROUPS, PANEL_WIDTHS } from './constants';
import { DEMO_EVENTS, INITIAL_WORKSPACE_ITEMS, DEMO_NEWS, DEMO_PLAYERS, DEMO_ROSTER } from './data/demo';

export const ManagementV2: React.FC = () => {
  const [leftPanel, setLeftPanel] = useState<LeftPanelView>(null);
  const [isPaused, setIsPaused] = useState(true);
  const [speed, setSpeed] = useState<1 | 2 | 3>(2);
  const [sidebarExpanded, setSidebarExpanded] = useState(() => {
    return localStorage.getItem('mgmt2-sidebar-expanded') === 'true';
  });
  const [appNavOpen, setAppNavOpen] = useState(false);
  const [activeEvent, setActiveEvent] = useState<GameEvent | null>(null);
  const [eventIndex, setEventIndex] = useState(0);

  // Workspace state
  const [workspaceItems, setWorkspaceItems] = useState<WorkspaceItem[]>(INITIAL_WORKSPACE_ITEMS);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dropIndex, setDropIndex] = useState<number | null>(null);
  const [isEditMode, setIsEditMode] = useState(false);
  const itemHeights = useRef<Map<string, number>>(new Map());

  // Callback for items to report their heights
  const handleHeightChange = useCallback((id: string, height: number) => {
    itemHeights.current.set(id, height);
  }, []);

  // Toggle item open/closed - opening moves item after other open items
  const toggleItem = (id: string) => {
    setWorkspaceItems(items => {
      const item = items.find(i => i.id === id);
      if (!item) return items;

      // If opening, move after other open items (but before closed ones)
      if (!item.isOpen) {
        const openItems = items.filter(i => i.isOpen && i.id !== id);
        const closedItems = items.filter(i => !i.isOpen && i.id !== id);
        return [...openItems, { ...item, isOpen: true }, ...closedItems];
      }

      // If closing, just toggle in place
      return items.map(i =>
        i.id === id ? { ...i, isOpen: false } : i
      );
    });
  };

  // Close a specific item (collapse it)
  const closeItem = (id: string) => {
    setWorkspaceItems(items =>
      items.map(item =>
        item.id === id ? { ...item, isOpen: false } : item
      )
    );
  };

  // Remove an item entirely (for reference items like player cards)
  const removeItem = (id: string) => {
    setWorkspaceItems(items => items.filter(item => item.id !== id));
  };

  // Add a player card to workspace (pop-out from sidebar)
  const addPlayerToWorkspace = useCallback((player: { id: string; name: string; position: string; overall: number }) => {
    const newItem: WorkspaceItem = {
      id: `player-${player.id}-${Date.now()}`,
      type: 'player',
      title: player.name,
      subtitle: `${player.position} • ${player.overall} OVR`,
      isOpen: true,
      playerId: player.id,
    };
    setWorkspaceItems(items => [newItem, ...items]);
  }, []);

  // Close app nav when clicking outside
  useEffect(() => {
    if (!appNavOpen) return;
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('.mgmt2__app-nav-dropdown') && !target.closest('.mgmt2__nav-btn')) {
        setAppNavOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [appNavOpen]);

  // Demo state
  const weekPhase: WeekPhase = 'practice';
  const currentWeek = 5;
  const dayName = 'Thursday';
  const record = { wins: 3, losses: 1 };
  const nextOpponent = 'DAL';

  const getPhaseLabel = (phase: WeekPhase) => {
    switch (phase) {
      case 'recovery': return 'Recovery';
      case 'practice': return 'Practice';
      case 'prep': return 'Prep';
      case 'gameday': return 'Game Day';
    }
  };

  const toggleSidebar = () => {
    const newVal = !sidebarExpanded;
    setSidebarExpanded(newVal);
    localStorage.setItem('mgmt2-sidebar-expanded', String(newVal));
  };

  const togglePanel = (panel: Exclude<LeftPanelView, null>) => {
    // Toggle panel: if clicking active panel, close it; otherwise open it
    if (panel === leftPanel) {
      setLeftPanel(null);
    } else {
      setLeftPanel(panel);
    }
  };

  const triggerNextEvent = () => {
    setActiveEvent(DEMO_EVENTS[eventIndex]);
    setEventIndex((eventIndex + 1) % DEMO_EVENTS.length);
  };

  const dismissEvent = () => {
    setActiveEvent(null);
  };

  return (
    <div className="mgmt2" data-phase={weekPhase}>
      {/* Left Sidebar - Icons */}
      <aside className={`mgmt2__nav ${sidebarExpanded ? 'expanded' : ''}`}>
        <div className="mgmt2__nav-top">
          {/* App Switcher */}
          <div className="mgmt2__nav-app">
            <button
              className={`mgmt2__nav-btn ${appNavOpen ? 'active' : ''}`}
              onClick={() => setAppNavOpen(!appNavOpen)}
              title="Switch App"
            >
              <Menu size={18} />
              {sidebarExpanded && <span className="mgmt2__nav-label">Apps</span>}
            </button>

            {appNavOpen && (
              <div className="mgmt2__app-nav-dropdown">
                {NAV_GROUPS.map(group => (
                  <div key={group.label} className="mgmt2__app-nav-group">
                    <div className="mgmt2__app-nav-group-label">{group.label}</div>
                    {group.items.map(item => (
                      <a
                        key={item.to}
                        href={item.to}
                        className="mgmt2__app-nav-item"
                        onClick={() => setAppNavOpen(false)}
                      >
                        <item.icon size={16} />
                        <span>{item.label}</span>
                      </a>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Personnel: Roster, Depth, Coaches */}
          <button
            className={`mgmt2__nav-btn ${leftPanel === 'personnel' ? 'active' : ''}`}
            onClick={() => togglePanel('personnel')}
            title="Personnel"
          >
            <Users size={18} />
            {sidebarExpanded && <span className="mgmt2__nav-label">Personnel</span>}
          </button>

          {/* Transactions: Free Agents, Trades, Waivers */}
          <button
            className={`mgmt2__nav-btn ${leftPanel === 'transactions' ? 'active' : ''}`}
            onClick={() => togglePanel('transactions')}
            title="Transactions"
          >
            <ArrowLeftRight size={18} />
            {sidebarExpanded && <span className="mgmt2__nav-label">Transactions</span>}
          </button>

          {/* Finances: Cap, Contracts */}
          <button
            className={`mgmt2__nav-btn ${leftPanel === 'finances' ? 'active' : ''}`}
            onClick={() => togglePanel('finances')}
            title="Finances"
          >
            <DollarSign size={18} />
            {sidebarExpanded && <span className="mgmt2__nav-label">Finances</span>}
          </button>

          {/* Draft: Board, Scouts, Prospects */}
          <button
            className={`mgmt2__nav-btn ${leftPanel === 'draft' ? 'active' : ''}`}
            onClick={() => togglePanel('draft')}
            title="Draft"
          >
            <ClipboardCheck size={18} />
            {sidebarExpanded && <span className="mgmt2__nav-label">Draft</span>}
          </button>

          {/* Season: Schedule, Standings, Playoffs */}
          <button
            className={`mgmt2__nav-btn ${leftPanel === 'season' ? 'active' : ''}`}
            onClick={() => togglePanel('season')}
            title="Season"
          >
            <Calendar size={18} />
            {sidebarExpanded && <span className="mgmt2__nav-label">Season</span>}
          </button>

          {/* Team: Strategy, Chemistry, Front Office */}
          <button
            className={`mgmt2__nav-btn ${leftPanel === 'team' ? 'active' : ''}`}
            onClick={() => togglePanel('team')}
            title="Team"
          >
            <Heart size={18} />
            {sidebarExpanded && <span className="mgmt2__nav-label">Team</span>}
          </button>
        </div>

        <div className="mgmt2__nav-bottom">
          {/* Demo Event Trigger */}
          <button
            className="mgmt2__nav-btn mgmt2__nav-btn--event"
            onClick={triggerNextEvent}
            title="Trigger Demo Event"
          >
            <AlertTriangle size={18} />
            {sidebarExpanded && <span className="mgmt2__nav-label">Event</span>}
          </button>

          <button
            className="mgmt2__nav-btn mgmt2__nav-toggle"
            onClick={toggleSidebar}
            title={sidebarExpanded ? 'Collapse' : 'Expand'}
          >
            {sidebarExpanded ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
          </button>
        </div>
      </aside>

      {/* Main Body - Header, Middle, Ticker */}
      <div className="mgmt2__body">
        {/* Context Bar - spans full width */}
        <header className="mgmt2__context">
          <div className="mgmt2__context-left">
            <div className="mgmt2__when">
              <span className="mgmt2__week">Week {currentWeek}</span>
              <span className="mgmt2__day">{dayName}</span>
            </div>
            <span className="mgmt2__phase" data-phase={weekPhase}>{getPhaseLabel(weekPhase)}</span>
          </div>

          <TimeControls
            isPaused={isPaused}
            speed={speed}
            onTogglePause={() => setIsPaused(!isPaused)}
            onSetSpeed={setSpeed}
          />

          <button
            className={`mgmt2__edit-btn ${isEditMode ? 'mgmt2__edit-btn--active' : ''}`}
            onClick={() => setIsEditMode(!isEditMode)}
            title={isEditMode ? 'Done editing' : 'Edit layout'}
          >
            {isEditMode ? 'Done' : 'Edit'}
          </button>

          <button
            className="mgmt2__edit-btn"
            onClick={() => {
              // Optimize: sort by actual measured height for best bin packing
              // Taller items first - they anchor columns, shorter items fill gaps beside them
              setWorkspaceItems(items => [...items].sort((a, b) => {
                // Open items first
                if (a.isOpen !== b.isOpen) return a.isOpen ? -1 : 1;
                // Then by measured height (taller first)
                const aHeight = itemHeights.current.get(a.id) || 0;
                const bHeight = itemHeights.current.get(b.id) || 0;
                return bHeight - aHeight;
              }));
            }}
            title="Optimize layout"
          >
            Pack
          </button>

          <div className="mgmt2__context-right">
            <span className="mgmt2__record">{record.wins}-{record.losses}</span>
            <span className="mgmt2__next">vs {nextOpponent}</span>
          </div>
        </header>

        {/* Middle Area - Left Panel + Focus */}
        <div className="mgmt2__middle">
          {/* Left Panel - Reference panels only */}
          {leftPanel && (
            <aside
              className="mgmt2__left-panel"
              style={{ width: PANEL_WIDTHS[leftPanel] || 360 }}
              data-view={leftPanel}
            >
              <ReferencePanel type={leftPanel} onAddPlayerToWorkspace={addPlayerToWorkspace} />
            </aside>
          )}

          {/* Main Content Area - Workspace Grid */}
          <main className="mgmt2__main">
            {/* Workspace Grid - all items flat, dense packing fills gaps */}
            {/* Sort so open items always come first, then closed items */}
            <div className={`workspace ${isEditMode ? 'workspace--edit-mode' : ''}`}>
              {workspaceItems.length > 0 ? (
                [...workspaceItems]
                  .sort((a, b) => (a.isOpen === b.isOpen ? 0 : a.isOpen ? -1 : 1))
                  .map((item, index) => (
                  <WorkspaceItemComponent
                    key={item.id}
                    item={item}
                    index={index}
                    isEditMode={isEditMode}
                    isDragging={dragIndex === index}
                    isDropTarget={dropIndex === index}
                    onToggle={() => toggleItem(item.id)}
                    onClose={() => item.type === 'player' ? removeItem(item.id) : closeItem(item.id)}
                    onHeightChange={handleHeightChange}
                    onDragStart={(e) => {
                      if (!isEditMode) return;
                      setDragIndex(index);
                      e.dataTransfer.effectAllowed = 'move';
                    }}
                    onDragOver={(e) => {
                      e.preventDefault();
                      if (index !== dragIndex) setDropIndex(index);
                    }}
                    onDragEnd={() => {
                      setDragIndex(null);
                      setDropIndex(null);
                    }}
                    onDrop={(e) => {
                      e.preventDefault();
                      if (dragIndex !== null && dragIndex !== index) {
                        const newItems = [...workspaceItems];
                        const [removed] = newItems.splice(dragIndex, 1);
                        newItems.splice(index, 0, removed);
                        setWorkspaceItems(newItems);
                      }
                      setDragIndex(null);
                      setDropIndex(null);
                    }}
                  />
                ))
              ) : (
                <div className="workspace__empty">
                  <p>Nothing needs immediate attention.</p>
                  <p>Time will advance automatically.</p>
                </div>
              )}
            </div>
          </main>
        </div>

        {/* News Ticker - spans full width */}
        <footer className="mgmt2__ticker">
          <span className="mgmt2__ticker-label">NEWS</span>
          <div className="mgmt2__ticker-scroll">
            {DEMO_NEWS.map((item, i) => (
              <span key={item.id} className={`mgmt2__ticker-item ${item.isBreaking ? 'mgmt2__ticker-item--breaking' : ''}`}>
                {item.isBreaking && <span className="mgmt2__ticker-tag">BREAKING</span>}
                {item.text}
                {i < DEMO_NEWS.length - 1 && <span className="mgmt2__ticker-dot">•</span>}
              </span>
            ))}
          </div>
        </footer>
      </div>

      {/* Event Modal Overlay */}
      {activeEvent && (
        <EventModal event={activeEvent} onDismiss={dismissEvent} />
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
  const speedLabels = ['Slow', 'Normal', 'Fast'];

  return (
    <div className="time-ctrl">
      <button
        className={`time-ctrl__play ${isPaused ? '' : 'time-ctrl__play--active'}`}
        onClick={onTogglePause}
      >
        {isPaused ? '▶ Play' : '❚❚ Pause'}
      </button>

      <div className="time-ctrl__speed">
        {[1, 2, 3].map(s => (
          <button
            key={s}
            className={`time-ctrl__speed-btn ${speed === s ? 'time-ctrl__speed-btn--active' : ''}`}
            onClick={() => onSetSpeed(s as 1 | 2 | 3)}
            disabled={isPaused}
          >
            {speedLabels[s - 1]}
          </button>
        ))}
      </div>
    </div>
  );
};

// === Event Modal (Interruption Layer) ===

interface EventModalProps {
  event: GameEvent;
  onDismiss: () => void;
}

const EventModal: React.FC<EventModalProps> = ({ event, onDismiss }) => {
  const typeIcon = {
    injury: '🏥',
    trade_offer: '🔄',
    media: '🎤',
    contract_demand: '💰',
    morale: '😤',
  };

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

interface FocusCardProps {
  item: AgendaItem;
  onAction?: () => void;
}

export const FocusCard: React.FC<FocusCardProps> = ({ item, onAction }) => {
  const config = TYPE_CONFIG[item.type];

  return (
    <article className="focus-card" data-type={item.type}>
      <header className="focus-card__header">
        <span className="focus-card__abbr" data-type={item.type}>{config.abbr}</span>
        <span className="focus-card__type">{config.label}</span>
      </header>

      <div className="focus-card__body">
        <h1 className="focus-card__title">{item.title}</h1>
        {item.subtitle && <p className="focus-card__subtitle">{item.subtitle}</p>}
        {item.detail && <p className="focus-card__detail">{item.detail}</p>}
      </div>

      <footer className="focus-card__footer">
        {item.action && (
          <button className="focus-card__action" onClick={onAction}>
            {item.action}
          </button>
        )}
        {item.actionSecondary && (
          <button className="focus-card__skip">
            {item.actionSecondary}
          </button>
        )}
      </footer>
    </article>
  );
};

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

// === Agenda Card (compact, for main area list) ===
interface AgendaCardProps {
  item: AgendaItem;
  onClick?: () => void;
}

export const AgendaCard: React.FC<AgendaCardProps> = ({ item, onClick }) => {
  const config = TYPE_CONFIG[item.type];

  return (
    <button className="agenda-card" data-type={item.type} onClick={onClick}>
      <div className="agenda-card__header">
        <span className="agenda-card__abbr" data-type={item.type}>{config.abbr}</span>
        <span className="agenda-card__type">{config.label}</span>
        {item.timeLeft && (
          <span className="agenda-card__time">{item.timeLeft}</span>
        )}
      </div>
      <div className="agenda-card__body">
        <h3 className="agenda-card__title">{item.title}</h3>
        {item.subtitle && <p className="agenda-card__subtitle">{item.subtitle}</p>}
      </div>
    </button>
  );
};

// === Workspace Item (Card or Pane based on isOpen) ===
interface WorkspaceItemProps {
  item: WorkspaceItem;
  index: number;
  isEditMode: boolean;
  isDragging: boolean;
  isDropTarget: boolean;
  onToggle: () => void;
  onClose: () => void;
  onHeightChange: (id: string, height: number) => void;
  onDragStart: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragEnd: () => void;
  onDrop: (e: React.DragEvent) => void;
}

const WorkspaceItemComponent: React.FC<WorkspaceItemProps> = ({
  item,
  isEditMode,
  isDragging,
  isDropTarget,
  onToggle,
  onClose,
  onHeightChange,
  onDragStart,
  onDragOver,
  onDragEnd,
  onDrop,
}) => {
  const config = TYPE_CONFIG[item.type];
  const size = item.isOpen ? TYPE_SIZE[item.type] : 'small';
  const itemRef = useRef<HTMLDivElement>(null);

  // Measure actual content height and set CSS variable for masonry
  useEffect(() => {
    const el = itemRef.current;
    if (!el) return;

    const updateHeight = () => {
      // Use scrollHeight to get natural content height, not constrained height
      const height = el.scrollHeight;
      if (height > 0) {
        el.style.setProperty('--item-height', `${height}px`);
        onHeightChange(item.id, height);
      }
    };

    // Delay measurement to after paint
    requestAnimationFrame(() => {
      requestAnimationFrame(updateHeight);
    });

    // Watch for content changes
    const observer = new ResizeObserver(() => {
      requestAnimationFrame(updateHeight);
    });
    observer.observe(el);

    return () => observer.disconnect();
  }, [item.isOpen, item.id, onHeightChange]); // Re-run when open state changes

  const className = [
    'workspace-item',
    item.isOpen ? 'workspace-item--open' : 'workspace-item--collapsed',
    `workspace-item--${size}`,
    isDragging && 'workspace-item--dragging',
    isDropTarget && 'workspace-item--drop-target',
  ].filter(Boolean).join(' ');

  return (
    <div
      ref={itemRef}
      className={className}
      data-type={item.type}
      draggable={isEditMode}
      onDragStart={onDragStart}
      onDragOver={onDragOver}
      onDragEnd={onDragEnd}
      onDrop={onDrop}
    >
      {item.isOpen ? (
        // Expanded pane content
        <div className="workspace-item__pane">
          {item.type === 'practice' && (
            <PracticeAllocationPane onComplete={onClose} />
          )}
          {item.type === 'decision' && (
            <ContractNegotiationPane onComplete={onClose} />
          )}
          {item.type === 'scout' && (
            <ScoutReportPane onComplete={onClose} />
          )}
          {item.type === 'deadline' && (
            <DeadlinePane item={item} onComplete={onClose} />
          )}
          {item.type === 'player' && item.playerId && (
            <PlayerPane playerId={item.playerId} onComplete={onClose} />
          )}
        </div>
      ) : (
        // Collapsed card
        <button className="workspace-item__card" onClick={onToggle}>
          {isEditMode && (
            <div className="workspace-item__drag-handle">
              <GripVertical size={14} />
            </div>
          )}
          <div className="workspace-item__card-header">
            <span className="workspace-item__abbr" data-type={item.type}>{config.abbr}</span>
            {item.timeLeft && (
              <span className="workspace-item__time">{item.timeLeft}</span>
            )}
          </div>
          <h3 className="workspace-item__title">{item.title}</h3>
          {item.subtitle && <p className="workspace-item__subtitle">{item.subtitle}</p>}
        </button>
      )}
    </div>
  );
};

// Simple placeholder pane for deadline type
const DeadlinePane: React.FC<{ item: WorkspaceItem; onComplete: () => void }> = ({ item, onComplete }) => (
  <div className="pane">
    <header className="pane__header">
      <div className="pane__header-left">
        <span className="pane__type">DUE</span>
        <div>
          <h2 className="pane__title">{item.title}</h2>
          <p className="pane__subtitle">{item.subtitle}</p>
        </div>
      </div>
      <button className="pane__close" onClick={onComplete}>Close</button>
    </header>
    <div className="pane__body pane__body--placeholder">
      <p>Deadline management UI would go here.</p>
    </div>
    <footer className="pane__footer">
      <button className="pane__btn pane__btn--secondary" onClick={onComplete}>Dismiss</button>
      <button className="pane__btn pane__btn--primary" onClick={onComplete}>Take Action</button>
    </footer>
  </div>
);

// === Queue Panel ===
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

// === Reference Panel (no header - icon nav shows selection) ===

interface ReferencePanelProps {
  type: Exclude<LeftPanelView, 'queue'>;
  onAddPlayerToWorkspace?: (player: { id: string; name: string; position: string; overall: number }) => void;
}

const ReferencePanel: React.FC<ReferencePanelProps> = ({ type, onAddPlayerToWorkspace }) => {
  return (
    <div className="ref-panel">
      {type === 'personnel' && <PersonnelPanel onAddPlayerToWorkspace={onAddPlayerToWorkspace} />}
      {type === 'transactions' && <TransactionsPanel />}
      {type === 'finances' && <FinancesPanel />}
      {type === 'draft' && <DraftPanel />}
      {type === 'season' && <SeasonPanel />}
      {type === 'team' && <TeamPanel />}
    </div>
  );
};

// === Tabbed Panel Components ===

type PersonnelTab = 'roster' | 'depth' | 'coaches';
const PersonnelPanel: React.FC<{ onAddPlayerToWorkspace?: (player: { id: string; name: string; position: string; overall: number }) => void }> = ({ onAddPlayerToWorkspace }) => {
  const [tab, setTab] = useState<PersonnelTab>('roster');
  const [rosterView, setRosterView] = useState<RosterView>({ type: 'list' });

  const handleTabClick = (newTab: PersonnelTab) => {
    setTab(newTab);
    if (newTab !== 'roster') {
      setRosterView({ type: 'list' });
    }
  };

  return (
    <div className="tabbed-panel">
      <div className="tabbed-panel__tabs">
        <button
          className={`tabbed-panel__tab ${tab === 'roster' ? 'tabbed-panel__tab--active' : ''}`}
          onClick={() => { handleTabClick('roster'); setRosterView({ type: 'list' }); }}
        >
          Roster
        </button>
        <button className={`tabbed-panel__tab ${tab === 'depth' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => handleTabClick('depth')}>Depth</button>
        <button className={`tabbed-panel__tab ${tab === 'coaches' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => handleTabClick('coaches')}>Coaches</button>
      </div>
      <div className="tabbed-panel__content">
        {tab === 'roster' && <RosterContent onAddPlayerToWorkspace={onAddPlayerToWorkspace} view={rosterView} setView={setRosterView} />}
        {tab === 'depth' && <DepthChartContent />}
        {tab === 'coaches' && <CoachesContent />}
      </div>
    </div>
  );
};

type TransactionsTab = 'free-agents' | 'trades' | 'waivers';
const TransactionsPanel: React.FC = () => {
  const [tab, setTab] = useState<TransactionsTab>('free-agents');
  return (
    <div className="tabbed-panel">
      <div className="tabbed-panel__tabs">
        <button className={`tabbed-panel__tab ${tab === 'free-agents' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('free-agents')}>Free Agents</button>
        <button className={`tabbed-panel__tab ${tab === 'trades' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('trades')}>Trades</button>
        <button className={`tabbed-panel__tab ${tab === 'waivers' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('waivers')}>Waivers</button>
      </div>
      <div className="tabbed-panel__content">
        {tab === 'free-agents' && <PlaceholderContent title="Free Agents" />}
        {tab === 'trades' && <PlaceholderContent title="Trade Block" />}
        {tab === 'waivers' && <PlaceholderContent title="Waivers" />}
      </div>
    </div>
  );
};

type FinancesTab = 'cap' | 'contracts';
const FinancesPanel: React.FC = () => {
  const [tab, setTab] = useState<FinancesTab>('cap');
  return (
    <div className="tabbed-panel">
      <div className="tabbed-panel__tabs">
        <button className={`tabbed-panel__tab ${tab === 'cap' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('cap')}>Salary Cap</button>
        <button className={`tabbed-panel__tab ${tab === 'contracts' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('contracts')}>Contracts</button>
      </div>
      <div className="tabbed-panel__content">
        {tab === 'cap' && <PlaceholderContent title="Salary Cap" />}
        {tab === 'contracts' && <PlaceholderContent title="Contracts" />}
      </div>
    </div>
  );
};

type DraftTab = 'board' | 'scouts' | 'prospects';
const DraftPanel: React.FC = () => {
  const [tab, setTab] = useState<DraftTab>('board');
  return (
    <div className="tabbed-panel">
      <div className="tabbed-panel__tabs">
        <button className={`tabbed-panel__tab ${tab === 'board' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('board')}>Board</button>
        <button className={`tabbed-panel__tab ${tab === 'scouts' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('scouts')}>Scouts</button>
        <button className={`tabbed-panel__tab ${tab === 'prospects' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('prospects')}>Prospects</button>
      </div>
      <div className="tabbed-panel__content">
        {tab === 'board' && <PlaceholderContent title="Draft Board" />}
        {tab === 'scouts' && <PlaceholderContent title="Scouts" />}
        {tab === 'prospects' && <PlaceholderContent title="Prospects" />}
      </div>
    </div>
  );
};

type SeasonTab = 'schedule' | 'standings' | 'playoffs';
const SeasonPanel: React.FC = () => {
  const [tab, setTab] = useState<SeasonTab>('schedule');
  return (
    <div className="tabbed-panel">
      <div className="tabbed-panel__tabs">
        <button className={`tabbed-panel__tab ${tab === 'schedule' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('schedule')}>Schedule</button>
        <button className={`tabbed-panel__tab ${tab === 'standings' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('standings')}>Standings</button>
        <button className={`tabbed-panel__tab ${tab === 'playoffs' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('playoffs')}>Playoffs</button>
      </div>
      <div className="tabbed-panel__content">
        {tab === 'schedule' && <ScheduleContent />}
        {tab === 'standings' && <StandingsContent />}
        {tab === 'playoffs' && <PlaceholderContent title="Playoff Picture" />}
      </div>
    </div>
  );
};

type TeamTab = 'strategy' | 'chemistry' | 'front-office';
const TeamPanel: React.FC = () => {
  const [tab, setTab] = useState<TeamTab>('strategy');
  return (
    <div className="tabbed-panel">
      <div className="tabbed-panel__tabs">
        <button className={`tabbed-panel__tab ${tab === 'strategy' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('strategy')}>Strategy</button>
        <button className={`tabbed-panel__tab ${tab === 'chemistry' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('chemistry')}>Chemistry</button>
        <button className={`tabbed-panel__tab ${tab === 'front-office' ? 'tabbed-panel__tab--active' : ''}`} onClick={() => setTab('front-office')}>Front Office</button>
      </div>
      <div className="tabbed-panel__content">
        {tab === 'strategy' && <PlaceholderContent title="Strategy" />}
        {tab === 'chemistry' && <PlaceholderContent title="Team Chemistry" />}
        {tab === 'front-office' && <PlaceholderContent title="Front Office" />}
      </div>
    </div>
  );
};

// Placeholder for panels not yet built
const PlaceholderContent: React.FC<{ title: string }> = ({ title }) => (
  <div className="ref-content">
    <div className="placeholder-content">
      <span className="placeholder-content__title">{title}</span>
      <span className="placeholder-content__subtitle">Coming soon</span>
    </div>
  </div>
);

// Coaches content placeholder
const CoachesContent: React.FC = () => (
  <div className="ref-content">
    <div className="panel-section">
      <div className="panel-section__header">Coaching Staff</div>
      <div className="stat-table__row"><span className="stat-table__name">Bill Thompson</span><span className="stat-table__stat">HC</span></div>
      <div className="stat-table__row"><span className="stat-table__name">Mike Roberts</span><span className="stat-table__stat">OC</span></div>
      <div className="stat-table__row"><span className="stat-table__name">James Wilson</span><span className="stat-table__stat">DC</span></div>
    </div>
  </div>
);

// === Roster Content ===

// Color helpers for roster management view
const getOvrColor = (ovr: number): string => {
  if (ovr >= 90) return 'var(--success)';
  if (ovr >= 85) return 'var(--accent)';
  if (ovr >= 75) return 'var(--text-secondary)';
  return 'var(--text-muted)';
};

const getAgeColor = (age: number): string => {
  if (age <= 25) return 'var(--success)';
  if (age <= 28) return 'var(--text-secondary)';
  if (age <= 30) return 'var(--accent)';
  return 'var(--danger)';
};

const getContractColor = (years: number): string => {
  if (years >= 3) return 'var(--text-secondary)';
  if (years === 2) return 'var(--accent)';
  return 'var(--danger)'; // 1 year = expiring
};

const getMoraleIndicator = (morale: 'high' | 'neutral' | 'low'): { symbol: string; color: string } => {
  if (morale === 'high') return { symbol: '●', color: 'var(--success)' };
  if (morale === 'low') return { symbol: '●', color: 'var(--danger)' };
  return { symbol: '●', color: 'var(--text-muted)' };
};

interface RosterContentProps {
  onAddPlayerToWorkspace?: (player: { id: string; name: string; position: string; overall: number }) => void;
  view: RosterView;
  setView: (view: RosterView) => void;
}

const RosterContent: React.FC<RosterContentProps> = ({ onAddPlayerToWorkspace, view, setView }) => {
  const selectedPlayer = view.type === 'player'
    ? DEMO_PLAYERS.find(p => p.id === view.playerId)
    : null;

  const handlePopOut = (player: Player) => {
    if (onAddPlayerToWorkspace) {
      onAddPlayerToWorkspace({
        id: player.id,
        name: player.name,
        position: player.position,
        overall: player.overall,
      });
    }
  };

  // Group players by position
  const positionOrder = ['QB', 'RB', 'WR', 'TE', 'DE', 'DT', 'LB', 'CB', 'S'];
  const grouped = DEMO_PLAYERS.reduce((acc, player) => {
    const pos = player.position;
    if (!acc[pos]) acc[pos] = [];
    acc[pos].push(player);
    return acc;
  }, {} as Record<string, Player[]>);

  // Sort each group by overall
  Object.values(grouped).forEach(group => {
    group.sort((a, b) => b.overall - a.overall);
  });

  const orderedGroups = positionOrder.filter(pos => grouped[pos]?.length);

  return (
    <div className="ref-content">
      {/* Content based on view */}
      {view.type === 'list' ? (
        <div className="stat-table">
          {orderedGroups.map(pos => (
            <div key={pos} className="stat-table__group">
              <div className="stat-table__header">
                <span className="stat-table__header-pos">{pos}</span>
                <span className="stat-table__header-attr">OVR</span>
                <span className="stat-table__header-attr">AGE</span>
                <span className="stat-table__header-attr">SAL</span>
                <span className="stat-table__header-attr">YRS</span>
              </div>
              {grouped[pos].map(player => {
                const morale = getMoraleIndicator(player.morale);
                return (
                  <button
                    key={player.id}
                    className="stat-table__row"
                    onClick={() => setView({ type: 'player', playerId: player.id })}
                  >
                    <span className="stat-table__name">
                      <span style={{ color: morale.color, fontSize: '8px' }}>{morale.symbol}</span>
                      {player.name}
                    </span>
                    <span className="stat-table__stat" style={{ color: getOvrColor(player.overall) }}>
                      {player.overall}
                    </span>
                    <span className="stat-table__stat" style={{ color: getAgeColor(player.age) }}>
                      {player.age}
                    </span>
                    <span className="stat-table__stat" style={{ color: 'var(--text-secondary)' }}>
                      {player.salary.replace('$', '').replace('.0M', 'M')}
                    </span>
                    <span className="stat-table__stat" style={{ color: getContractColor(player.contractYears) }}>
                      {player.contractYears}
                    </span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      ) : selectedPlayer ? (
        <PlayerDetailView player={selectedPlayer} onPopOut={handlePopOut} />
      ) : null}
    </div>
  );
};

interface PlayerDetailViewProps {
  player: Player;
  onPopOut?: (player: Player) => void;
}

const PlayerDetailView: React.FC<PlayerDetailViewProps> = ({ player, onPopOut }) => {
  const moraleColor = player.morale === 'high' ? 'var(--success)' : player.morale === 'low' ? 'var(--danger)' : 'var(--text-muted)';

  return (
    <div className="player-detail">
      <div className="player-detail__header">
        <span className="player-detail__number">#{player.number}</span>
        <div className="player-detail__info">
          <h3 className="player-detail__name">{player.name}</h3>
          <span className="player-detail__pos">{player.position} • {player.experience}</span>
        </div>
        <span className="player-detail__ovr">{player.overall}</span>
        {onPopOut && (
          <button
            className="player-detail__popout"
            onClick={() => onPopOut(player)}
            title="Open in workspace"
          >
            <Maximize2 size={14} />
          </button>
        )}
      </div>

      <div className="player-detail__section">
        <div className="player-detail__label">Contract</div>
        <div className="player-detail__row">
          <span>{player.salary}/yr</span>
          <span>{player.contractYears} yr{player.contractYears > 1 ? 's' : ''} left</span>
        </div>
      </div>

      <div className="player-detail__section">
        <div className="player-detail__label">Status</div>
        <div className="player-detail__row">
          <span>Age {player.age}</span>
          <span style={{ color: moraleColor }}>
            {player.morale === 'high' ? '● Happy' : player.morale === 'low' ? '● Unhappy' : '● Neutral'}
          </span>
        </div>
      </div>

      <div className="player-detail__section">
        <div className="player-detail__label">Traits</div>
        <div className="player-detail__traits">
          {player.traits.map(trait => (
            <span key={trait} className="player-detail__trait">{trait}</span>
          ))}
        </div>
      </div>

      <div className="player-detail__actions">
        <button className="player-detail__action">View Contract</button>
        <button className="player-detail__action player-detail__action--secondary">Release</button>
      </div>
    </div>
  );
};

// === Player Stat Table (reusable for Depth Chart and Roster) ===

// Position groups with their 4 key attributes
const POSITION_ATTRS: Record<string, string[]> = {
  QB: ['ARM', 'ACC', 'AWR', 'SPD'],
  RB: ['SPD', 'AGI', 'BTK', 'CAR'],
  WR: ['SPD', 'CTH', 'RTE', 'REL'],
  TE: ['CTH', 'RBK', 'SPD', 'STR'],
  OL: ['STR', 'PBK', 'RBK', 'AWR'],
  DL: ['STR', 'PWM', 'BSH', 'SPD'],
  LB: ['TAK', 'SPD', 'AWR', 'COV'],
  CB: ['SPD', 'MCV', 'ZCV', 'PRS'],
  S: ['SPD', 'ZCV', 'TAK', 'AWR'],
};

// Map specific positions to their attribute group
const POS_TO_GROUP: Record<string, string> = {
  QB: 'QB', RB: 'RB', FB: 'RB',
  WR: 'WR', WR1: 'WR', WR2: 'WR', WR3: 'WR',
  TE: 'TE',
  LT: 'OL', LG: 'OL', C: 'OL', RG: 'OL', RT: 'OL',
  DE: 'DL', DT: 'DL', NT: 'DL',
  LB: 'LB', MLB: 'LB', OLB: 'LB', LOLB: 'LB', ROLB: 'LB',
  CB: 'CB', CB1: 'CB', CB2: 'CB',
  FS: 'S', SS: 'S',
};

// Color scale for stat values - tighter thresholds so amber is special
const getStatColor = (value: number): string => {
  if (value >= 90) return 'var(--success)';
  if (value >= 85) return 'var(--accent)';
  if (value >= 70) return 'var(--text-secondary)';
  if (value >= 60) return 'var(--text-muted)';
  return 'var(--danger)';
};

// Position display order
const POSITION_ORDER = ['QB', 'RB', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT', 'DE', 'DT', 'LB', 'CB', 'FS', 'SS'];

interface PlayerStatTableProps {
  players: PlayerStats[];
  showDepth?: boolean;
}

const PlayerStatTable: React.FC<PlayerStatTableProps> = ({ players, showDepth = true }) => {
  // Group players by position
  const grouped = players.reduce((acc, player) => {
    const group = POS_TO_GROUP[player.pos] || player.pos;
    if (!acc[group]) acc[group] = [];
    acc[group].push(player);
    return acc;
  }, {} as Record<string, PlayerStats[]>);

  // Sort each group by depth then OVR
  Object.values(grouped).forEach(group => {
    group.sort((a, b) => {
      if (showDepth && a.depth !== b.depth) return (a.depth || 99) - (b.depth || 99);
      return b.ovr - a.ovr;
    });
  });

  // Get ordered position groups
  const orderedGroups = POSITION_ORDER
    .map(pos => POS_TO_GROUP[pos] || pos)
    .filter((v, i, a) => a.indexOf(v) === i) // unique
    .filter(group => grouped[group]?.length);

  return (
    <div className="stat-table">
      {orderedGroups.map(group => {
        const attrs = POSITION_ATTRS[group] || ['OVR', 'SPD', 'STR', 'AWR'];
        const groupPlayers = grouped[group];

        return (
          <div key={group} className="stat-table__group">
            <div className="stat-table__header">
              <span className="stat-table__header-pos">{group}</span>
              {attrs.map(attr => (
                <span key={attr} className="stat-table__header-attr">{attr}</span>
              ))}
            </div>
            {groupPlayers.map(player => (
              <div key={player.id} className="stat-table__row">
                <span className="stat-table__name">
                  {showDepth && player.depth && (
                    <span className={player.depth === 1 ? 'stat-table__starter' : 'stat-table__backup'}>
                      {player.depth}
                    </span>
                  )}
                  {player.name}
                </span>
                {attrs.map(attr => {
                  const value = player.attrs[attr] ?? 0;
                  return (
                    <span
                      key={attr}
                      className="stat-table__stat"
                      style={{ color: getStatColor(value) }}
                    >
                      {value}
                    </span>
                  );
                })}
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
};

const DepthChartContent: React.FC = () => {
  return (
    <div className="ref-content">
      <PlayerStatTable players={DEMO_ROSTER} showDepth={true} />
    </div>
  );
};

const ScheduleContent: React.FC = () => (
  <div className="ref-content">
    <div className="ref-content__stat-row">
      <span className="ref-content__stat">Week 5</span>
      <span className="ref-content__stat-label">of 17</span>
    </div>
    <div className="ref-content__group">
      <div className="ref-content__schedule-item ref-content__schedule-item--past">
        <span>W1</span><span>vs NYG</span><span className="ref-content__result--win">W 24-17</span>
      </div>
      <div className="ref-content__schedule-item ref-content__schedule-item--past">
        <span>W2</span><span>@ PHI</span><span className="ref-content__result--loss">L 14-21</span>
      </div>
      <div className="ref-content__schedule-item ref-content__schedule-item--past">
        <span>W3</span><span>vs WAS</span><span className="ref-content__result--win">W 31-20</span>
      </div>
      <div className="ref-content__schedule-item ref-content__schedule-item--past">
        <span>W4</span><span>@ CHI</span><span className="ref-content__result--win">W 28-14</span>
      </div>
      <div className="ref-content__schedule-item ref-content__schedule-item--current">
        <span>W5</span><span>vs DAL</span><span>Sunday</span>
      </div>
    </div>
  </div>
);

const StandingsContent: React.FC = () => (
  <div className="ref-content">
    <div className="ref-content__group">
      <div className="ref-content__group-header">NFC East</div>
      <div className="ref-content__standing ref-content__standing--you">
        <span>1.</span><span>Your Team</span><span>3-1</span>
      </div>
      <div className="ref-content__standing">
        <span>2.</span><span>Dallas</span><span>3-1</span>
      </div>
      <div className="ref-content__standing">
        <span>3.</span><span>Philadelphia</span><span>2-2</span>
      </div>
      <div className="ref-content__standing">
        <span>4.</span><span>NY Giants</span><span>1-3</span>
      </div>
      <div className="ref-content__standing">
        <span>5.</span><span>Washington</span><span>1-3</span>
      </div>
    </div>
  </div>
);

// === Event Panes (Complex Focus Area Components) ===

interface PaneProps {
  onComplete: () => void;
}

const PracticeAllocationPane: React.FC<PaneProps> = ({ onComplete }) => {
  const [allocation, setAllocation] = useState({
    playbook: 40,
    conditioning: 30,
    gamePrep: 30,
  });
  const [intensity, setIntensity] = useState<'light' | 'normal' | 'intense'>('normal');

  const total = allocation.playbook + allocation.conditioning + allocation.gamePrep;
  const remaining = 100 - total;
  const isMaxed = remaining === 0;

  const updateAllocation = (key: keyof typeof allocation, value: number) => {
    const oldValue = allocation[key];
    const otherTotal = total - oldValue;
    // Cap at 100% total
    const maxAllowed = 100 - otherTotal;
    const clampedValue = Math.min(value, maxAllowed);
    setAllocation({ ...allocation, [key]: clampedValue });
  };

  const riskLevel = intensity === 'light' ? 'Low' : intensity === 'normal' ? 'Medium' : 'High';
  const riskClass = intensity === 'intense' ? 'ctrl-result__value--danger' : intensity === 'normal' ? 'ctrl-result__value--warning' : 'ctrl-result__value--muted';

  return (
    <div className="pane">
      <header className="pane__header">
        <div className="pane__header-left">
          <span className="pane__type">PRC</span>
          <div>
            <h2 className="pane__title">Practice Allocation</h2>
            <p className="pane__subtitle">Thursday Practice • 120 min</p>
          </div>
        </div>
        <button className="pane__close" onClick={onComplete}>Cancel</button>
      </header>

      <div className="pane__body">
        {/* Allocation Section */}
        <div className="pane-section">
          <div className="pane-section__header">Allocation</div>
          <div className="ctrl-slider">
            <span className="ctrl-slider__label">Playbook</span>
            <input
              type="range"
              min="0"
              max="100"
              value={allocation.playbook}
              onChange={e => updateAllocation('playbook', Number(e.target.value))}
              className="ctrl-slider__input"
            />
            <span className="ctrl-slider__value">{allocation.playbook}%</span>
          </div>
          <div className="ctrl-slider">
            <span className="ctrl-slider__label">Conditioning</span>
            <input
              type="range"
              min="0"
              max="100"
              value={allocation.conditioning}
              onChange={e => updateAllocation('conditioning', Number(e.target.value))}
              className="ctrl-slider__input"
            />
            <span className="ctrl-slider__value">{allocation.conditioning}%</span>
          </div>
          <div className="ctrl-slider">
            <span className="ctrl-slider__label">Game Prep</span>
            <input
              type="range"
              min="0"
              max="100"
              value={allocation.gamePrep}
              onChange={e => updateAllocation('gamePrep', Number(e.target.value))}
              className="ctrl-slider__input"
            />
            <span className="ctrl-slider__value">{allocation.gamePrep}%</span>
          </div>
          <div className={`ctrl-status ${isMaxed ? 'ctrl-status--maxed' : ''}`}>
            {isMaxed ? '100% allocated' : `${remaining}% remaining`}
          </div>
        </div>

        {/* Intensity Toggle */}
        <div className="pane-section">
          <div className="ctrl-toggle">
            <span className="ctrl-toggle__label">Intensity</span>
            <div className="ctrl-toggle__options">
              {(['light', 'normal', 'intense'] as const).map(level => (
                <button
                  key={level}
                  className={`ctrl-toggle__btn ${intensity === level ? 'ctrl-toggle__btn--active' : ''}`}
                  onClick={() => setIntensity(level)}
                >
                  {level.charAt(0).toUpperCase() + level.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Projected Results */}
        <div className="pane-section">
          <div className="pane-section__header">Projected Results</div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Play Mastery</span>
            <span className="ctrl-result__value">+{Math.round(allocation.playbook * 0.3)}%</span>
          </div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Player Development</span>
            <span className="ctrl-result__value">+{Math.round(allocation.conditioning * 0.2)} XP</span>
          </div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Game Prep vs DAL</span>
            <span className="ctrl-result__value">+{Math.round(allocation.gamePrep * 0.4)}%</span>
          </div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Injury Risk</span>
            <span className={`ctrl-result__value ${riskClass}`}>{riskLevel}</span>
          </div>
        </div>
      </div>

      <footer className="pane__footer">
        <button className="pane__btn pane__btn--secondary" onClick={onComplete}>Skip</button>
        <button className="pane__btn pane__btn--primary" onClick={onComplete}>Run Practice</button>
      </footer>
    </div>
  );
};

const ContractNegotiationPane: React.FC<PaneProps> = ({ onComplete }) => (
  <div className="pane">
    <header className="pane__header">
      <div className="pane__header-left">
        <span className="pane__type">DEC</span>
        <div>
          <h2 className="pane__title">Contract Negotiation</h2>
          <p className="pane__subtitle">Jaylen Smith (WR) • Extension Request</p>
        </div>
      </div>
      <button className="pane__close" onClick={onComplete}>Cancel</button>
    </header>
    <div className="pane__body pane__body--placeholder">
      <p>Contract negotiation UI would go here with offer/counter-offer interface.</p>
    </div>
    <footer className="pane__footer">
      <button className="pane__btn pane__btn--secondary" onClick={onComplete}>Walk Away</button>
      <button className="pane__btn pane__btn--primary" onClick={onComplete}>Make Offer</button>
    </footer>
  </div>
);

const ScoutReportPane: React.FC<PaneProps> = ({ onComplete }) => (
  <div className="pane">
    <header className="pane__header">
      <div className="pane__header-left">
        <span className="pane__type">SCT</span>
        <div>
          <h2 className="pane__title">Dallas Cowboys</h2>
          <p className="pane__subtitle">Week 5 • 3-1 Record</p>
        </div>
      </div>
      <button className="pane__close" onClick={onComplete}>Done</button>
    </header>

    <div className="pane__body">
      {/* Rankings */}
      <div className="pane-section">
        <div className="pane-section__header">Rankings</div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">Offense</span>
          <span className="ctrl-result__value">#5</span>
        </div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">Defense</span>
          <span className="ctrl-result__value ctrl-result__value--warning">#18</span>
        </div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">Turnover Margin</span>
          <span className="ctrl-result__value">+6</span>
        </div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">Blitz Rate</span>
          <span className="ctrl-result__value ctrl-result__value--muted">38%</span>
        </div>
      </div>

      {/* Key Threats */}
      <div className="pane-section">
        <div className="pane-section__header">Key Threats</div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">DE M. Parsons</span>
          <span className="ctrl-result__value ctrl-result__value--danger">6 sacks</span>
        </div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">CB T. Diggs</span>
          <span className="ctrl-result__value ctrl-result__value--danger">3 INTs</span>
        </div>
      </div>

      {/* Tendencies */}
      <div className="pane-section">
        <div className="pane-section__header">Tendencies</div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">Base Defense</span>
          <span className="ctrl-result__value ctrl-result__value--muted">4-3 Under</span>
        </div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">3rd Down</span>
          <span className="ctrl-result__value ctrl-result__value--muted">Cover 3</span>
        </div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">Red Zone</span>
          <span className="ctrl-result__value ctrl-result__value--muted">Man</span>
        </div>
      </div>

      {/* Attack Vectors */}
      <div className="pane-section">
        <div className="pane-section__header">Attack Vectors</div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">Slot CB</span>
          <span className="ctrl-result__value">Weak vs quick routes</span>
        </div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">LB Coverage</span>
          <span className="ctrl-result__value">Middle open</span>
        </div>
        <div className="ctrl-result">
          <span className="ctrl-result__label">DE Crash</span>
          <span className="ctrl-result__value">Bootleg opportunity</span>
        </div>
      </div>
    </div>

    <footer className="pane__footer">
      <button className="pane__btn pane__btn--secondary" onClick={onComplete}>Save Notes</button>
      <button className="pane__btn pane__btn--primary" onClick={onComplete}>Got It</button>
    </footer>
  </div>
);

// Player Pane - workspace version of player detail
interface PlayerPaneProps {
  playerId: string;
  onComplete: () => void;
}

const PlayerPane: React.FC<PlayerPaneProps> = ({ playerId, onComplete }) => {
  const player = DEMO_PLAYERS.find(p => p.id === playerId);

  if (!player) {
    return (
      <div className="pane">
        <header className="pane__header">
          <div className="pane__header-left">
            <span className="pane__type">PLR</span>
            <h2 className="pane__title">Player Not Found</h2>
          </div>
          <button className="pane__close" onClick={onComplete}><X size={16} /></button>
        </header>
      </div>
    );
  }

  const moraleColor = player.morale === 'high' ? 'var(--success)' : player.morale === 'low' ? 'var(--danger)' : 'var(--text-muted)';
  const moraleLabel = player.morale === 'high' ? 'Happy' : player.morale === 'low' ? 'Unhappy' : 'Neutral';

  return (
    <div className="pane">
      <header className="pane__header">
        <div className="pane__header-left">
          <span className="pane__type">PLR</span>
          <div>
            <h2 className="pane__title">#{player.number} {player.name}</h2>
            <p className="pane__subtitle">{player.position} • {player.experience}</p>
          </div>
        </div>
        <span className="pane__ovr">{player.overall}</span>
        <button className="pane__close" onClick={onComplete}><X size={16} /></button>
      </header>

      <div className="pane__body">
        {/* Contract */}
        <div className="pane-section">
          <div className="pane-section__header">Contract</div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Salary</span>
            <span className="ctrl-result__value ctrl-result__value--muted">{player.salary}/yr</span>
          </div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Years Left</span>
            <span className="ctrl-result__value" style={{ color: player.contractYears <= 1 ? 'var(--danger)' : 'var(--text-secondary)' }}>
              {player.contractYears}
            </span>
          </div>
        </div>

        {/* Status */}
        <div className="pane-section">
          <div className="pane-section__header">Status</div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Age</span>
            <span className="ctrl-result__value ctrl-result__value--muted">{player.age}</span>
          </div>
          <div className="ctrl-result">
            <span className="ctrl-result__label">Morale</span>
            <span className="ctrl-result__value" style={{ color: moraleColor }}>{moraleLabel}</span>
          </div>
        </div>

        {/* Traits */}
        <div className="pane-section">
          <div className="pane-section__header">Traits</div>
          <div className="player-pane__traits">
            {player.traits.map(trait => (
              <span key={trait} className="player-pane__trait">{trait}</span>
            ))}
          </div>
        </div>
      </div>

      <footer className="pane__footer">
        <button className="pane__btn pane__btn--secondary" onClick={onComplete}>View Contract</button>
        <button className="pane__btn pane__btn--danger" onClick={onComplete}>Release</button>
      </footer>
    </div>
  );
};

export default ManagementV2;
