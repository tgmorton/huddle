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
} from './types';
import { TYPE_CONFIG, NAV_GROUPS, PANEL_WIDTHS } from './constants';
import { DEMO_EVENTS, INITIAL_WORKSPACE_ITEMS, DEMO_NEWS } from './data/demo';
import { TimeControls } from './components/TimeControls';
import { EventModal } from './components/EventModal';
import { ReferencePanel } from './panels/ReferencePanel';
import { WorkspaceItemComponent } from './workspace';
// QueuePanel exported from ./components/QueuePanel but not currently used in main layout

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

export default ManagementV2;
