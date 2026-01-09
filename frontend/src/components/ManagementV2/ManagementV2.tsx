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

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
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
  Settings,
  Terminal,
  Archive,
  PlayCircle,
  SkipForward,
  Pause,
  Play,
  Pencil,
  Package,
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
import { TYPE_CONFIG, TYPE_SIZE, NAV_GROUPS, PANEL_WIDTHS } from './constants';
import type { PaneSize } from './types';
import { DEMO_EVENTS, INITIAL_WORKSPACE_ITEMS, DEMO_NEWS } from './data/demo';
// TimeControls removed - using day-based progression now
import { EventModal } from './components/EventModal';
import { AdminSidebar, WorkshopPanel, DeskDrawer, ManagementEventModal } from './components';
import type { LogEntry } from './components';
import { ReferencePanel } from './panels/ReferencePanel';
import { WorkspaceItemComponent } from './workspace';
import { useManagementWebSocket } from '../../hooks/useManagementWebSocket';
import { useManagementStore, selectTeamRecord, selectNextGame, type NextGameInfo } from '../../stores/managementStore';
import { savePinnedItems, loadPinnedItems, eventsToWorkspaceItems, isModalEvent, eventToWorkspaceItem } from './utils';
import { managementApi, type DrawerItem } from '../../api/managementClient';
import { adminApi, type SavedLeague } from '../../api/adminClient';
import type { ManagementEvent } from '../../types/management';
// QueuePanel exported from ./components/QueuePanel but not currently used in main layout

export const ManagementV2: React.FC = () => {
  const [leftPanel, setLeftPanel] = useState<LeftPanelView>(null);
  const [tickerPaused, setTickerPaused] = useState(false);
  const [sidebarExpanded, setSidebarExpanded] = useState(() => {
    return localStorage.getItem('mgmt2-sidebar-expanded') === 'true';
  });
  const [appNavOpen, setAppNavOpen] = useState(false);
  const [activeEvent, setActiveEvent] = useState<GameEvent | null>(null);
  const [eventIndex, setEventIndex] = useState(0);

  // Dev panel state
  const [showAdminSidebar, setShowAdminSidebar] = useState(false);
  const [showWorkshopPanel, setShowWorkshopPanel] = useState(false);
  const [franchiseId, setFranchiseIdState] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);

  // Saved leagues for quick load
  const [savedLeagues, setSavedLeagues] = useState<SavedLeague[]>([]);
  const [loadingLeague, setLoadingLeague] = useState(false);

  // Get store's setFranchiseId to keep it in sync
  const { setFranchiseId: setStoreFranchiseId } = useManagementStore();

  // Persist franchiseId to localStorage and store
  const setFranchiseId = useCallback((id: string | null) => {
    setFranchiseIdState(id);
    setStoreFranchiseId(id);
    if (id) {
      localStorage.setItem('huddle_franchise_id', id);
    } else {
      localStorage.removeItem('huddle_franchise_id');
    }
  }, [setStoreFranchiseId]);

  // Auto-rejoin last session on mount
  useEffect(() => {
    const savedFranchiseId = localStorage.getItem('huddle_franchise_id');
    if (savedFranchiseId && !franchiseId) {
      setFranchiseIdState(savedFranchiseId);
      setStoreFranchiseId(savedFranchiseId);
    }
  }, []);

  // Fetch saved leagues when no franchise is loaded
  useEffect(() => {
    if (!franchiseId) {
      adminApi.listLeagues()
        .then(setSavedLeagues)
        .catch(() => setSavedLeagues([]));
    }
  }, [franchiseId]);

  // Load a saved league
  const handleLoadLeague = useCallback(async (leagueId: string) => {
    setLoadingLeague(true);
    try {
      await adminApi.loadLeague(leagueId);
      // After loading, we need to create/find a franchise for this league
      // For now, just reload to pick up the league
      window.location.reload();
    } catch (err) {
      console.error('Failed to load league:', err);
      setLoadingLeague(false);
    }
  }, []);

  // Log helper
  const addLog = useCallback((message: string, type: LogEntry['type'] = 'info') => {
    setLogs(prev => [...prev, {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      timestamp: new Date(),
      message,
      type,
    }]);
  }, []);

  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  // Management WebSocket connection
  const wsOptions = useMemo(() => ({
    franchiseId: franchiseId || '',
    autoConnect: false, // We'll manually connect when franchiseId is set
  }), [franchiseId]);

  const {
    connect: wsConnect,
    disconnect: wsDisconnect,
    runPractice,
    attendEvent,
    dismissEvent,
  } = useManagementWebSocket(wsOptions);

  const { isConnected, calendar, events: storeEvents, updateCalendar, mergeEvents } = useManagementStore();
  const teamRecord = useManagementStore(selectTeamRecord);
  const nextGame = useManagementStore(selectNextGame);
  const { setTeamAbbr, setSchedule, setTeamRecord, setNextGame } = useManagementStore();

  // Modal event state (for events that should display as blocking modals)
  const [modalEvent, setModalEvent] = useState<ManagementEvent | null>(null);

  // Blocking events warning state
  const [blockingEvents, setBlockingEvents] = useState<ManagementEvent[]>([]);

  // Connect/disconnect WebSocket when franchiseId changes
  useEffect(() => {
    if (franchiseId) {
      addLog(`Connecting WebSocket to franchise ${franchiseId.slice(0, 8)}...`, 'ws');
      wsConnect();
    } else {
      wsDisconnect();
    }
    return () => {
      wsDisconnect();
    };
  }, [franchiseId, wsConnect, wsDisconnect, addLog]);

  // Log connection status changes
  useEffect(() => {
    if (isConnected) {
      addLog('WebSocket connected', 'success');
    }
  }, [isConnected, addLog]);

  // Load schedule and standings when franchise is connected
  useEffect(() => {
    if (!franchiseId || !isConnected) return;

    const loadScheduleData = async () => {
      try {
        // First get team abbreviation from financials endpoint (it has team_abbr)
        const financials = await managementApi.getContracts(franchiseId);
        const teamAbbr = financials.team_abbr;
        setTeamAbbr(teamAbbr);

        // Now fetch schedule filtered by team
        const scheduleData = await managementApi.getTeamSchedule(teamAbbr);
        // Note: scheduleData might not have is_divisional/is_conference fields, but that's ok for storage
        setSchedule(scheduleData as any);

        // Compute record from played games
        let wins = 0, losses = 0, ties = 0;
        let nextGameFound: NextGameInfo | null = null;

        for (const game of scheduleData) {
          if (game.is_played && game.winner) {
            if (game.winner === teamAbbr) {
              wins++;
            } else {
              losses++;
            }
          } else if (game.is_played && !game.winner) {
            ties++;
          }

          // Find next unplayed game
          if (!game.is_played && !nextGameFound) {
            const isHome = game.home_team === teamAbbr;
            const opponent = isHome ? game.away_team : game.home_team;
            nextGameFound = {
              week: game.week,
              opponent,
              is_home: isHome,
              is_divisional: false,  // API may not have this
              is_conference: false,  // API may not have this
            };
          }
        }

        setTeamRecord({ wins, losses, ties });
        setNextGame(nextGameFound);
        addLog(`Loaded schedule: ${wins}-${losses}${ties > 0 ? `-${ties}` : ''}, next: ${nextGameFound?.opponent ?? 'none'}`, 'info');
      } catch (err) {
        addLog(`Failed to load schedule: ${err}`, 'error');
      }
    };

    loadScheduleData();
  }, [franchiseId, isConnected, calendar?.current_week, setTeamAbbr, setSchedule, setTeamRecord, setNextGame, addLog]);

  // Workspace state
  const [workspaceItems, setWorkspaceItems] = useState<WorkspaceItem[]>(() => {
    // Load pinned items from storage, merge with demo items
    const pinned = loadPinnedItems();
    const pinnedIds = new Set(pinned.map(p => p.id));
    // Filter out demo items that might conflict with pinned items
    const demoItems = INITIAL_WORKSPACE_ITEMS.filter(item => !pinnedIds.has(item.id));
    return [...pinned, ...demoItems];
  });
  const [drawerItems, setDrawerItems] = useState<WorkspaceItem[]>([]);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dropIndex, setDropIndex] = useState<number | null>(null);
  const [isEditMode, setIsEditMode] = useState(false);
  const itemHeights = useRef<Map<string, number>>(new Map());

  // Persist pinned items when workspace changes
  useEffect(() => {
    savePinnedItems(workspaceItems);
  }, [workspaceItems]);

  // Sync store events to workspace items
  // When events change: add new ones, remove completed/dismissed ones
  useEffect(() => {
    if (!storeEvents?.pending) return;

    const pendingEvents = storeEvents.pending;
    const pendingEventIds = new Set(pendingEvents.map(e => e.id));

    // Find modal events - show the first one
    const modalEvents = pendingEvents.filter(isModalEvent);

    // Clear stale modal if current modal event is no longer in pending
    if (modalEvent && !pendingEventIds.has(modalEvent.id)) {
      // Current modal event was resolved elsewhere, switch to next modal or clear
      setModalEvent(modalEvents.length > 0 ? modalEvents[0] : null);
    } else if (modalEvents.length > 0 && !modalEvent) {
      // No current modal, show the first pending modal event
      setModalEvent(modalEvents[0]);
    }

    // Convert pane events to workspace items
    const eventItems = eventsToWorkspaceItems(pendingEvents);

    // Sync workspace with pending events
    setWorkspaceItems(current => {
      // Get IDs of current event-based workspace items
      const existingEventIds = new Set(
        current.filter(item => item.eventId).map(item => item.eventId)
      );

      // Find new events to add
      const newEventItems = eventItems.filter(item => !existingEventIds.has(item.eventId));

      // Keep non-event items (player cards, prospects, news)
      const nonEventItems = current.filter(item => !item.eventId);

      // Keep event items that are still pending (remove completed ones)
      // Also preserve items when there are no pane events to replace them with
      const stillPendingItems = current.filter(item => {
        if (!item.eventId) return false;
        // If this item's eventId is in pending events, keep it
        if (pendingEventIds.has(item.eventId)) return true;
        // If there are no pane events coming in, preserve existing event items
        // (This prevents clearing the workspace when events are empty or only modal/ticker)
        if (eventItems.length === 0) return true;
        return false;
      });

      // New events go at the start, then existing pending events, then non-event items
      return [...newEventItems, ...stillPendingItems, ...nonEventItems];
    });
  }, [storeEvents, modalEvent]);

  // Helper to convert API drawer item to WorkspaceItem format
  const apiItemToWorkspaceItem = useCallback((item: DrawerItem): WorkspaceItem => ({
    id: item.id,
    type: item.type as WorkspaceItem['type'],
    title: item.title,
    subtitle: item.subtitle || undefined,
    status: 'archived',
    isOpen: false,
    archivedAt: new Date(item.archived_at).getTime(),
    note: item.note || undefined,
    playerId: item.ref_id,
  }), []);

  // Load drawer items from API when franchise is connected
  useEffect(() => {
    if (!franchiseId) {
      setDrawerItems([]);
      return;
    }

    const loadDrawer = async () => {
      try {
        const response = await managementApi.getDrawer(franchiseId);
        setDrawerItems(response.items.map(apiItemToWorkspaceItem));
      } catch (error) {
        console.error('Failed to load drawer items:', error);
      }
    };

    loadDrawer();
  }, [franchiseId, apiItemToWorkspaceItem]);


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

  // Pack workspace - reorder items for efficient layout (tall/large items first)
  // Pinned items stay first and maintain their relative order
  const packWorkspace = useCallback(() => {
    const sizeOrder: Record<PaneSize, number> = { large: 0, medium: 1, small: 2 };

    setWorkspaceItems(items => {
      // Separate pinned from non-pinned
      const pinned = items.filter(i => i.status === 'pinned');
      const unpinned = items.filter(i => i.status !== 'pinned');

      // Sort only unpinned items by size (large first)
      const sortedUnpinned = [...unpinned].sort((a, b) => {
        const sizeA = a.isOpen ? TYPE_SIZE[a.type] : 'small';
        const sizeB = b.isOpen ? TYPE_SIZE[b.type] : 'small';
        return sizeOrder[sizeA] - sizeOrder[sizeB];
      });

      // Pinned items first (unchanged order), then sorted unpinned
      return [...pinned, ...sortedUnpinned];
    });
  }, []);

  // Remove an item entirely - also removes from store events if it has an eventId
  const removeItem = useCallback((id: string) => {
    // Find the item to check for eventId
    const item = workspaceItems.find(i => i.id === id);

    // Remove from workspace
    setWorkspaceItems(items => items.filter(item => item.id !== id));

    // Also remove from store events if this was an event item
    if (item?.eventId) {
      useManagementStore.getState().removeEvent(item.eventId);
    }
  }, [workspaceItems]);

  // Toggle pin status on an item
  const togglePinItem = useCallback((id: string) => {
    setWorkspaceItems(items =>
      items.map(item =>
        item.id === id
          ? { ...item, status: item.status === 'pinned' ? 'active' : 'pinned' }
          : item
      )
    );
  }, []);

  // Archive an item (move to drawer via API)
  const archiveItem = useCallback(async (id: string) => {
    const item = workspaceItems.find(i => i.id === id);
    if (!item || !franchiseId) return;

    // Determine the ref_id based on item type
    // For player/prospect items, extract the ID from the playerId field
    const refId = item.playerId || item.id;

    // Only certain types can be archived
    const archivableTypes = ['player', 'prospect', 'news', 'game'];
    if (!archivableTypes.includes(item.type)) return;

    try {
      // Add to drawer via API
      const apiItem = await managementApi.addDrawerItem(franchiseId, {
        type: item.type as 'player' | 'prospect' | 'news' | 'game',
        ref_id: refId,
      });

      // Add to local state
      setDrawerItems(items => [apiItemToWorkspaceItem(apiItem), ...items]);

      // Remove from workspace
      setWorkspaceItems(items => items.filter(i => i.id !== id));
    } catch (error) {
      console.error('Failed to archive item:', error);
    }
  }, [workspaceItems, franchiseId, apiItemToWorkspaceItem]);

  // Restore an item from drawer to workspace (copy, keeps in drawer)
  const restoreFromDrawer = useCallback((item: WorkspaceItem) => {
    // Create a new active copy on workspace
    const restoredItem: WorkspaceItem = {
      ...item,
      id: `${item.id}-${Date.now()}`, // New ID to avoid conflicts
      status: 'active',
      isOpen: true,
      archivedAt: undefined,
    };
    setWorkspaceItems(items => [restoredItem, ...items]);
  }, []);

  // Delete an item from drawer permanently via API
  const deleteFromDrawer = useCallback(async (id: string) => {
    if (!franchiseId) return;

    try {
      await managementApi.deleteDrawerItem(franchiseId, id);
      setDrawerItems(items => items.filter(i => i.id !== id));
    } catch (error) {
      console.error('Failed to delete drawer item:', error);
    }
  }, [franchiseId]);

  // Update note on a drawer item via API
  const updateDrawerNote = useCallback(async (id: string, note: string) => {
    if (!franchiseId) return;

    try {
      const updatedItem = await managementApi.updateDrawerItemNote(franchiseId, id, note || null);
      setDrawerItems(items =>
        items.map(i => i.id === id ? apiItemToWorkspaceItem(updatedItem) : i)
      );
    } catch (error) {
      console.error('Failed to update drawer item note:', error);
    }
  }, [franchiseId, apiItemToWorkspaceItem]);

  // Add a player card to workspace (pop-out from sidebar)
  const addPlayerToWorkspace = useCallback((player: { id: string; name: string; position: string; overall: number }) => {
    const newItem: WorkspaceItem = {
      id: `player-${player.id}-${Date.now()}`,
      type: 'player',
      title: player.name,
      subtitle: `${player.position} • ${player.overall} OVR`,
      isOpen: true,
      playerId: player.id,
      status: 'active',
    };
    setWorkspaceItems(items => [newItem, ...items]);
  }, []);

  // Add a prospect card to workspace (pop-out from draft panel)
  const addProspectToWorkspace = useCallback((prospect: { id: string; name: string; position: string; overall: number }) => {
    const newItem: WorkspaceItem = {
      id: `prospect-${prospect.id}-${Date.now()}`,
      type: 'prospect',
      title: prospect.name,
      subtitle: `${prospect.position} • Prospect`,
      isOpen: true,
      playerId: prospect.id,
      status: 'active',
    };
    setWorkspaceItems(items => [newItem, ...items]);
  }, []);

  // Add a contract detail pane to workspace (pop-out from contracts list)
  const addContractToWorkspace = useCallback((contract: { id: string; name: string; position: string; salary: number }) => {
    const salaryStr = contract.salary >= 1000 ? `${(contract.salary / 1000).toFixed(1)}M` : `${contract.salary}K`;
    const newItem: WorkspaceItem = {
      id: `contract-${contract.id}-${Date.now()}`,
      type: 'contract',
      title: contract.name,
      subtitle: `${contract.position} • ${salaryStr}`,
      isOpen: true,
      playerId: contract.id,
      status: 'active',
    };
    setWorkspaceItems(items => [newItem, ...items]);
  }, []);

  // Add a negotiation pane to workspace (start negotiation with free agent)
  const addNegotiationToWorkspace = useCallback((player: { id: string; name: string; position: string; overall: number }) => {
    const newItem: WorkspaceItem = {
      id: `negotiation-${player.id}-${Date.now()}`,
      type: 'negotiation',
      title: `Negotiate: ${player.name}`,
      subtitle: `${player.position} • ${player.overall} OVR`,
      isOpen: true,
      playerId: player.id,
      status: 'active',
    };
    setWorkspaceItems(items => [newItem, ...items]);
  }, []);

  // Add an auction pane to workspace (competitive bidding for elite free agent)
  const addAuctionToWorkspace = useCallback((player: { id: string; name: string; position: string; overall: number }) => {
    const newItem: WorkspaceItem = {
      id: `auction-${player.id}-${Date.now()}`,
      type: 'auction',
      title: `Auction: ${player.name}`,
      subtitle: `${player.position} • ${player.overall} OVR`,
      isOpen: true,
      playerId: player.id,
      status: 'active',
    };
    setWorkspaceItems(items => [newItem, ...items]);
  }, []);

  // Add a news item to workspace (click from ticker)
  const addNewsToWorkspace = useCallback((news: { id: string; text: string; isBreaking?: boolean }) => {
    // Check if this news item is already on the workspace
    const exists = workspaceItems.some(item => item.id === `news-${news.id}`);
    if (exists) return;

    const newItem: WorkspaceItem = {
      id: `news-${news.id}`,
      type: 'news',
      title: news.isBreaking ? 'BREAKING NEWS' : 'League News',
      subtitle: news.text,
      isOpen: false,
      status: 'active',
    };
    setWorkspaceItems(items => [newItem, ...items]);
  }, [workspaceItems]);

  // Open an event in the workspace (click from WorkshopPanel or elsewhere)
  const handleEventClick = useCallback((event: ManagementEvent) => {
    // Convert event to workspace item
    const workspaceItem = eventToWorkspaceItem(event);
    if (!workspaceItem) return; // Skip if event can't be converted (ticker-only, etc.)

    // Check if this event is already on the workspace
    const existingIndex = workspaceItems.findIndex(item => item.eventId === event.id);

    if (existingIndex >= 0) {
      // Event exists - just open it
      setWorkspaceItems(items => {
        const updated = [...items];
        const existing = updated[existingIndex];
        // Move to front and open
        updated.splice(existingIndex, 1);
        return [{ ...existing, isOpen: true }, ...updated];
      });
    } else {
      // Event not on workspace - add and open it
      setWorkspaceItems(items => [{ ...workspaceItem, isOpen: true }, ...items]);
    }

    addLog(`Opened event: ${event.title}`, 'event');
  }, [workspaceItems, addLog]);

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

  // Calendar state - use real data from store, fallback to demo values
  const weekPhase: WeekPhase = calendar?.phase?.toLowerCase().includes('regular') ? 'practice'
    : calendar?.phase?.toLowerCase().includes('game') ? 'gameday'
    : calendar?.phase?.toLowerCase().includes('prep') ? 'prep'
    : 'practice';
  const currentWeek = calendar?.current_week ?? 1;
  const dayName = calendar?.day_name ?? 'Tuesday';

  // Use real schedule data from store
  const record = teamRecord ?? { wins: 0, losses: 0, ties: 0 };
  const nextOpponent = nextGame?.opponent ?? '---';

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

  const dismissDemoEvent = () => {
    setActiveEvent(null);
  };

  // Handle attending a management event (modal)
  const handleAttendModalEvent = useCallback(() => {
    if (modalEvent) {
      attendEvent(modalEvent.id);
      setModalEvent(null);
    }
  }, [modalEvent, attendEvent]);

  // Handle dismissing a management event (modal)
  const handleDismissModalEvent = useCallback(() => {
    if (modalEvent) {
      dismissEvent(modalEvent.id);
      setModalEvent(null);
    }
  }, [modalEvent, dismissEvent]);

  // Check if an event blocks day advancement
  const isBlockingEvent = useCallback((event: ManagementEvent): boolean => {
    // GAME events always block - can't skip past game day
    if (event.category === 'GAME') return true;
    // Events that require attention and can't be dismissed block
    if (event.requires_attention && !event.can_dismiss) return true;
    return false;
  }, []);

  // Get all blocking events from the current pending events
  const getBlockingEvents = useCallback((): ManagementEvent[] => {
    if (!storeEvents?.pending) return [];
    return storeEvents.pending.filter(isBlockingEvent);
  }, [storeEvents, isBlockingEvent]);

  // Handle advancing to next day
  const handleAdvanceDay = useCallback(async () => {
    if (!franchiseId) return;

    // Check for blocking events first
    const blockers = getBlockingEvents();
    if (blockers.length > 0) {
      setBlockingEvents(blockers);
      addLog(`Cannot advance: ${blockers.length} event(s) require attention`, 'warning');
      return;
    }

    try {
      addLog('Advancing day...', 'info');
      const response = await managementApi.advanceDay(franchiseId);

      // Update store with new calendar state
      updateCalendar(response.calendar as any);

      // Convert API events to ManagementEvent format and update store
      const events = response.day_events.map(e => ({
        ...e,
        created_at: new Date(e.created_at).toISOString(),
      })) as ManagementEvent[];
      mergeEvents(events);

      addLog(`Day advanced: ${response.calendar.day_name} - ${response.event_count} event(s)`, 'success');
    } catch (err) {
      addLog(`Failed to advance day: ${err}`, 'error');
    }
  }, [franchiseId, addLog, updateCalendar, mergeEvents, getBlockingEvents]);

  // Clear blocking events warning when user handles them
  useEffect(() => {
    if (blockingEvents.length > 0) {
      const currentBlockers = getBlockingEvents();
      if (currentBlockers.length === 0) {
        setBlockingEvents([]);
      }
    }
  }, [storeEvents, blockingEvents.length, getBlockingEvents]);

  const rootClassName = [
    'mgmt2',
    showAdminSidebar && 'mgmt2--admin-open',
    showWorkshopPanel && 'mgmt2--workshop-open',
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClassName} data-phase={weekPhase}>
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

          {/* Week: Weekly gameplay loop */}
          <button
            className={`mgmt2__nav-btn ${leftPanel === 'week' ? 'active' : ''}`}
            onClick={() => togglePanel('week')}
            title="This Week"
          >
            <PlayCircle size={18} />
            {sidebarExpanded && <span className="mgmt2__nav-label">Week</span>}
          </button>

          {/* Drawer: Archived workspace items */}
          <button
            className={`mgmt2__nav-btn mgmt2__nav-btn--drawer ${leftPanel === 'drawer' ? 'active' : ''}`}
            onClick={() => togglePanel('drawer')}
            title="Desk Drawer"
          >
            <Archive size={18} />
            {sidebarExpanded && <span className="mgmt2__nav-label">Drawer</span>}
            {drawerItems.length > 0 && (
              <span className="mgmt2__nav-badge">{drawerItems.length}</span>
            )}
          </button>

          <div className="mgmt2__nav-divider" />

          {/* Personnel: Roster, Depth, Coaches */}
          <button
            className={`mgmt2__nav-btn ${leftPanel === 'personnel' ? 'active' : ''}`}
            onClick={() => togglePanel('personnel')}
            title="Personnel"
          >
            <Users size={18} />
            {sidebarExpanded && <span className="mgmt2__nav-label">Squad</span>}
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

          <div className="mgmt2__nav-divider" />

          {/* Market: Free Agents, Trades, Waivers */}
          <button
            className={`mgmt2__nav-btn ${leftPanel === 'transactions' ? 'active' : ''}`}
            onClick={() => togglePanel('transactions')}
            title="Market"
          >
            <ArrowLeftRight size={18} />
            {sidebarExpanded && <span className="mgmt2__nav-label">Market</span>}
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

          <div className="mgmt2__nav-divider" />

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
        {/* Context Bar - Status | Ticker | Next Day */}
        <header className="mgmt2__context">
          {/* Left: Status Cluster */}
          <div className="mgmt2__status">
            <span className="mgmt2__status-item">Week {currentWeek}</span>
            <span className="mgmt2__status-sep">·</span>
            <span className="mgmt2__status-item">{dayName}</span>
            <span className="mgmt2__status-sep">·</span>
            <span className="mgmt2__status-item">{calendar?.phase?.replace(/_/g, ' ') || 'Regular Season'}</span>
            <span className="mgmt2__status-sep">·</span>
            <span className="mgmt2__status-record">
              {record.wins}-{record.losses}{record.ties > 0 ? `-${record.ties}` : ''}
            </span>
            <span className="mgmt2__status-opponent">
              {nextGame ? (nextGame.is_home ? 'vs' : '@') : 'vs'} {nextOpponent}
            </span>
          </div>

          {/* Center: News Ticker */}
          <div className={`mgmt2__ticker ${tickerPaused ? 'mgmt2__ticker--paused' : ''}`}>
            <div className="mgmt2__ticker-scroll">
              {/* Duplicate items for seamless loop (animation scrolls 50%) */}
              {[...DEMO_NEWS, ...DEMO_NEWS].map((item, i) => (
                <React.Fragment key={`${item.id}-${i}`}>
                  <button
                    className={`mgmt2__ticker-item ${item.isBreaking ? 'mgmt2__ticker-item--breaking' : ''}`}
                    onClick={() => addNewsToWorkspace(item)}
                  >
                    {item.isBreaking && <span className="mgmt2__ticker-tag">BREAKING</span>}
                    {item.text}
                  </button>
                  <span className="mgmt2__ticker-sep">|</span>
                </React.Fragment>
              ))}
            </div>
            <button
              className="mgmt2__ticker-pause"
              onClick={() => setTickerPaused(!tickerPaused)}
              title={tickerPaused ? 'Resume ticker' : 'Pause ticker'}
            >
              {tickerPaused ? <Play size={16} /> : <Pause size={16} />}
            </button>
          </div>

          {/* Right: Next Day Button with Blocking Warning */}
          <div className="mgmt2__advance-wrapper">
            <button
              className={`mgmt2__next-day-btn ${blockingEvents.length > 0 ? 'mgmt2__next-day-btn--blocked' : ''}`}
              onClick={handleAdvanceDay}
              disabled={!franchiseId}
              title={blockingEvents.length > 0 ? `${blockingEvents.length} event(s) require attention` : 'Advance to next day'}
            >
              <SkipForward size={14} />
              <span>Next Day</span>
              {blockingEvents.length > 0 && (
                <span className="mgmt2__block-badge">{blockingEvents.length}</span>
              )}
            </button>

            {/* Blocking Events Popup */}
            {blockingEvents.length > 0 && (
              <div className="mgmt2__block-popup">
                <div className="mgmt2__block-popup-header">
                  <AlertTriangle size={14} />
                  <span>Handle before advancing:</span>
                </div>
                <ul className="mgmt2__block-popup-list">
                  {blockingEvents.slice(0, 3).map(evt => (
                    <li key={evt.id}>
                      <button
                        className="mgmt2__block-popup-item"
                        onClick={() => handleEventClick(evt)}
                      >
                        <span className="mgmt2__block-popup-category">{evt.category}</span>
                        <span className="mgmt2__block-popup-title">{evt.title}</span>
                      </button>
                    </li>
                  ))}
                  {blockingEvents.length > 3 && (
                    <li className="mgmt2__block-popup-more">
                      +{blockingEvents.length - 3} more
                    </li>
                  )}
                </ul>
              </div>
            )}
          </div>
        </header>

        {/* Middle Area - Left Panel + Focus */}
        <div className="mgmt2__middle">
          {/* Left Panel - Reference panels and drawer */}
          {leftPanel && (
            <aside
              className="mgmt2__left-panel"
              style={{ width: leftPanel === 'drawer' ? 360 : (PANEL_WIDTHS[leftPanel] || 360) }}
              data-view={leftPanel}
            >
              {leftPanel === 'drawer' ? (
                <DeskDrawer
                  items={drawerItems}
                  onRestore={restoreFromDrawer}
                  onDelete={deleteFromDrawer}
                  onUpdateNote={updateDrawerNote}
                />
              ) : (
                <ReferencePanel type={leftPanel} onAddPlayerToWorkspace={addPlayerToWorkspace} onAddProspectToWorkspace={addProspectToWorkspace} onAddContractToWorkspace={addContractToWorkspace} onStartNegotiation={addNegotiationToWorkspace} onResumeNegotiation={addNegotiationToWorkspace} onStartAuction={addAuctionToWorkspace} franchiseId={franchiseId} />
              )}
            </aside>
          )}

          {/* Main Content Area - Workspace Grid */}
          <main className="mgmt2__main">
            {/* Workspace Grid - all items flat, dense packing fills gaps */}
            {/* Sort so open items always come first, then closed items */}
            <div className={`workspace ${isEditMode ? 'workspace--edit-mode' : ''}`}>
              {workspaceItems.length > 0 ? (
                [...workspaceItems]
                  .sort((a, b) => {
                    const EVENT_TYPES = new Set(['practice', 'game', 'meeting', 'deadline', 'decision', 'scout']);
                    // Open items always first
                    if (a.isOpen !== b.isOpen) return a.isOpen ? -1 : 1;
                    // For collapsed items: pinned first, then events, then non-events
                    if (!a.isOpen && !b.isOpen) {
                      // Pinned first
                      if (a.status === 'pinned' && b.status !== 'pinned') return -1;
                      if (a.status !== 'pinned' && b.status === 'pinned') return 1;
                      // Events before non-events
                      const aIsEvent = EVENT_TYPES.has(a.type);
                      const bIsEvent = EVENT_TYPES.has(b.type);
                      if (aIsEvent && !bIsEvent) return -1;
                      if (!aIsEvent && bIsEvent) return 1;
                    }
                    return 0;
                  })
                  .map((item, index) => (
                  <WorkspaceItemComponent
                    key={item.id}
                    item={item}
                    index={index}
                    isEditMode={isEditMode}
                    isDragging={dragIndex === index}
                    isDropTarget={dropIndex === index}
                    franchiseId={franchiseId}
                    onToggle={() => toggleItem(item.id)}
                    onCollapse={() => closeItem(item.id)}
                    onRemove={() => removeItem(item.id)}
                    onPin={() => togglePinItem(item.id)}
                    onArchive={() => archiveItem(item.id)}
                    onRunPractice={runPractice}
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
              ) : !franchiseId && savedLeagues.length > 0 ? (
                <div className="workspace__empty workspace__empty--load">
                  <p>No franchise loaded</p>
                  <button
                    className="workspace__load-btn"
                    onClick={() => handleLoadLeague(savedLeagues[0].id)}
                    disabled={loadingLeague}
                  >
                    {loadingLeague ? 'Loading...' : `Load ${savedLeagues[0].name} (${savedLeagues[0].season})`}
                  </button>
                  {savedLeagues.length > 1 && (
                    <p className="workspace__load-hint">{savedLeagues.length - 1} other saved league{savedLeagues.length > 2 ? 's' : ''} available</p>
                  )}
                </div>
              ) : null}
            </div>
          </main>
        </div>

      </div>

      {/* Demo Event Modal Overlay */}
      {activeEvent && (
        <EventModal event={activeEvent} onDismiss={dismissDemoEvent} />
      )}

      {/* Real Management Event Modal */}
      {modalEvent && (
        <ManagementEventModal
          event={modalEvent}
          onAttend={handleAttendModalEvent}
          onDismiss={handleDismissModalEvent}
        />
      )}

      {/* Dev Panels */}
      <AdminSidebar
        isOpen={showAdminSidebar}
        onClose={() => setShowAdminSidebar(false)}
        franchiseId={franchiseId}
        onFranchiseChange={setFranchiseId}
        onLog={addLog}
      />

      <WorkshopPanel
        isOpen={showWorkshopPanel}
        onClose={() => setShowWorkshopPanel(false)}
        logs={logs}
        onClearLogs={clearLogs}
        onLog={addLog}
        onEventClick={handleEventClick}
      />

      {/* Dev Toggle Buttons */}
      <div className="mgmt2__dev-toggle">
        <button
          className={`mgmt2__dev-btn ${isEditMode ? 'mgmt2__dev-btn--active' : ''}`}
          onClick={() => setIsEditMode(!isEditMode)}
          title="Edit Mode"
        >
          <Pencil size={18} />
        </button>
        <button
          className="mgmt2__dev-btn"
          onClick={packWorkspace}
          title="Pack Workspace"
        >
          <Package size={18} />
        </button>
        <button
          className={`mgmt2__dev-btn ${showWorkshopPanel ? 'mgmt2__dev-btn--active' : ''}`}
          onClick={() => setShowWorkshopPanel(!showWorkshopPanel)}
          title="Workshop Panel"
        >
          <Terminal size={18} />
        </button>
        <button
          className={`mgmt2__dev-btn ${showAdminSidebar ? 'mgmt2__dev-btn--active' : ''}`}
          onClick={() => setShowAdminSidebar(!showAdminSidebar)}
          title="Admin Panel"
        >
          <Settings size={18} />
        </button>
      </div>
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
