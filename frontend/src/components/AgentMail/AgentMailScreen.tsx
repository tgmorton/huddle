import { useState, useEffect, useCallback, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Menu,
  Inbox,
  Users,
  LayoutGrid,
  Search,
  PenSquare,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Gamepad2,
  Box,
  Play,
  Zap,
  Target,
  Circle,
  Route,
  GitBranch,
  ClipboardList,
  Settings,
  Sun,
  Wrench,
  Mail,
  Trash2,
  CheckCircle,
  Archive,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import './AgentMailScreen.css';
import { useAgentMailWebSocket } from '../../hooks/useAgentMailWebSocket';
import {
  useAgentMailStore,
  type AgentMailMessage,
  type AgentStatus,
  type AgentNote,
} from '../../stores/agentMailStore';
import { OversightDashboard } from './Oversight';

const API_BASE = 'http://localhost:8000/api/v1/agentmail';

const AGENT_COLORS: Record<string, string> = {
  live_sim_agent: '#f59e0b',
  qa_agent: '#10b981',
  behavior_tree_agent: '#8b5cf6',
  management_agent: '#3b82f6',
  frontend_agent: '#ec4899',
  documentation_agent: '#06b6d4',
  researcher_agent: '#f97316',
  simulation_agent: '#84cc16',
  coordinator: '#6366f1',
  auditor_agent: '#dc2626',
};

function getAgentColor(name: string): string {
  return AGENT_COLORS[name] || '#6b7280';
}

export function AgentMailScreen() {
  // Use Zustand store for data
  const {
    data,
    isLoading: loading,
    isConnected,
    error,
    updateMessageStatus: storeUpdateStatus,
    updateMessageRouting: storeUpdateRouting,
  } = useAgentMailStore();

  // WebSocket connection
  const { requestSync } = useAgentMailWebSocket({ autoConnect: true });

  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [rightTab, setRightTab] = useState<'inbox' | 'sent' | 'plans' | 'notes'>('inbox');
  const [agentNotes, setAgentNotes] = useState<AgentNote[]>([]);
  const [notesLoading, setNotesLoading] = useState(false);
  const [viewingNote, setViewingNote] = useState<{
    title: string;
    content: string;
    date: string;
    tags: string[];
    domain?: string;
  } | null>(null);
  const [viewingThread, setViewingThread] = useState<{
    thread_id: string;
    root_message: AgentMailMessage;
    messages: AgentMailMessage[];
    participants: string[];
    reply_tree: Array<AgentMailMessage & { replies: unknown[] }>;
  } | null>(null);
  const [viewingMessage, setViewingMessage] = useState<{
    id: string;
    subject: string;
    content: string;
    metadata: {
      from?: string;
      to?: string;
      date?: string;
      type?: string;
      severity?: string;
      status?: string;
      inReplyTo?: string;
      thread?: string;
      fileReferences?: Array<{ path: string; lines?: number[] }>;
    };
  } | null>(null);
  const [expandedFileRef, setExpandedFileRef] = useState<{
    path: string;
    content: string;
    language: string;
    lines?: number[];
  } | null>(null);
  const [viewingStatus, setViewingStatus] = useState<{
    agentName: string;
    content: string;
    filePath: string;
  } | null>(null);
  const [hideCompleted, setHideCompleted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [composing, setComposing] = useState<{
    toAgent: string;
    subject: string;
    content: string;
    type: string;
  } | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'kanban' | 'oversight'>('oversight');
  const [kanbanData, setKanbanData] = useState<{
    columns: Record<string, Array<{
      id: string;
      subject: string;
      from_agent: string;
      to_agent: string;
      type: string;
      severity?: string;
      date: string;
    }>>;
    counts: Record<string, number>;
  } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [maintenanceExpanded, setMaintenanceExpanded] = useState(false);
  const [bulkSelectModal, setBulkSelectModal] = useState<{
    type: 'resolve' | 'archive';
    messages: Array<{ id: string; subject: string; selected: boolean }>;
  } | null>(null);
  const [searchResults, setSearchResults] = useState<Array<{
    type: string;
    id: string;
    title: string;
    subtitle: string;
    date: string;
    matches: string[];
    score: number;
    metadata: Record<string, unknown>;
  }> | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [modalScrolled, setModalScrolled] = useState(false);
  const modalBodyRef = useRef<HTMLDivElement>(null);

  // App navigation and sidebar state
  const [appNavOpen, setAppNavOpen] = useState(false);
  const [sidebarExpanded, setSidebarExpanded] = useState(() => {
    return localStorage.getItem('sidebar-expanded') === 'true';
  });

  // Close app nav when clicking outside
  useEffect(() => {
    if (!appNavOpen) return;
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('.am-app-nav-dropdown') && !target.closest('.am-sidebar-btn')) {
        setAppNavOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [appNavOpen]);

  // Refresh data via WebSocket
  const refreshData = useCallback(() => {
    requestSync();
  }, [requestSync]);

  // Fetch notes for selected agent
  const fetchAgentNotes = useCallback(async (agentName: string) => {
    setNotesLoading(true);
    try {
      const response = await fetch(`${API_BASE}/agents/${agentName}/notes`);
      if (!response.ok) throw new Error('Failed to fetch notes');
      const notes = await response.json();
      setAgentNotes(notes);
    } catch (err) {
      console.error('Failed to fetch agent notes:', err);
      setAgentNotes([]);
    } finally {
      setNotesLoading(false);
    }
  }, []);

  // Load notes when switching to notes tab
  useEffect(() => {
    if (selectedAgent && rightTab === 'notes') {
      fetchAgentNotes(selectedAgent);
    }
  }, [selectedAgent, rightTab, fetchAgentNotes]);

  // Fetch kanban data
  const fetchKanban = useCallback(async () => {
    try {
      const url = selectedAgent
        ? `${API_BASE}/kanban?agent=${selectedAgent}`
        : `${API_BASE}/kanban`;
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch kanban');
      const data = await response.json();
      setKanbanData(data);
    } catch (err) {
      console.error('Failed to fetch kanban:', err);
    }
  }, [selectedAgent]);

  // Fetch kanban when switching to kanban view
  useEffect(() => {
    if (viewMode === 'kanban') {
      fetchKanban();
    }
  }, [viewMode, selectedAgent, fetchKanban]);

  // Search across all content
  const performSearch = async (query: string) => {
    if (!query.trim()) {
      setSearchResults(null);
      return;
    }
    setIsSearching(true);
    try {
      const response = await fetch(`${API_BASE}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      if (!response.ok) throw new Error('Search failed');
      const data = await response.json();
      setSearchResults(data.results);
    } catch (err) {
      console.error('Search failed:', err);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  // Debounced search
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (searchQuery) {
        performSearch(searchQuery);
      }
    }, 300);
    return () => clearTimeout(timeout);
  }, [searchQuery]);

  // Fetch file preview
  const fetchFilePreview = async (path: string, lines?: number[]) => {
    try {
      let url = `${API_BASE}/file-preview?path=${encodeURIComponent(path)}`;
      if (lines && lines.length >= 1) {
        url += `&start_line=${lines[0]}`;
        if (lines.length >= 2) {
          url += `&end_line=${lines[1]}`;
        }
      }
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch file');
      const data = await response.json();
      setExpandedFileRef({
        path: data.path,
        content: data.content,
        language: data.language,
        lines,
      });
    } catch (err) {
      console.error('Failed to fetch file preview:', err);
    }
  };

  // View a thread
  const viewThread = async (threadId: string) => {
    try {
      const response = await fetch(`${API_BASE}/threads/${encodeURIComponent(threadId)}`);
      if (!response.ok) throw new Error('Failed to fetch thread');
      const thread = await response.json();
      setViewingThread(thread);
    } catch (err) {
      console.error('Failed to load thread:', err);
    }
  };

  // View a specific note
  const viewNote = async (agentName: string, noteId: string) => {
    try {
      const response = await fetch(`${API_BASE}/agents/${agentName}/notes/${noteId}`);
      if (!response.ok) throw new Error('Failed to fetch note');
      const note = await response.json();

      // Parse content - remove header section
      let content = note.content || '';
      const headerEnd = content.indexOf('\n---\n');
      if (headerEnd !== -1) {
        content = content.substring(headerEnd + 5).trim();
      }

      setViewingNote({
        title: note.title,
        content,
        date: note.date,
        tags: note.tags || [],
        domain: note.domain,
      });
    } catch (err) {
      console.error('Failed to load note:', err);
    }
  };

  const parseMessageContent = (rawContent: string) => {
    const metadata: {
      from?: string;
      to?: string;
      date?: string;
      type?: string;
      severity?: string;
      status?: string;
      inReplyTo?: string;
      thread?: string;
      fileReferences?: Array<{ path: string; lines?: number[] }>;
    } = {};

    // Extract metadata fields
    const fromMatch = rawContent.match(/\*\*From:\*\*\s*(.+)/);
    const toMatch = rawContent.match(/\*\*To:\*\*\s*(.+)/);
    const dateMatch = rawContent.match(/\*\*Date:\*\*\s*(.+)/);
    const typeMatch = rawContent.match(/\*\*Type:\*\*\s*(.+)/);
    const severityMatch = rawContent.match(/\*\*Severity:\*\*\s*(.+)/);
    const statusMatch = rawContent.match(/\*\*Status:\*\*\s*(.+)/);
    const replyMatch = rawContent.match(/\*\*(?:In-Reply-To|Reply-To):\*\*\s*(.+)/);
    const threadMatch = rawContent.match(/\*\*Thread:\*\*\s*(.+)/);

    if (fromMatch) metadata.from = fromMatch[1].trim();
    if (toMatch) metadata.to = toMatch[1].trim();
    if (dateMatch) metadata.date = dateMatch[1].trim();
    if (typeMatch) metadata.type = typeMatch[1].trim();
    if (severityMatch) metadata.severity = severityMatch[1].trim();
    if (statusMatch) metadata.status = statusMatch[1].trim();
    if (replyMatch) metadata.inReplyTo = replyMatch[1].trim();
    if (threadMatch) metadata.thread = threadMatch[1].trim();

    // Extract file references - format: **File-References:** path:lines, path:lines
    const fileRefsMatch = rawContent.match(/\*\*File-References:\*\*\s*(.+)/);
    if (fileRefsMatch) {
      const refs: Array<{ path: string; lines?: number[] }> = [];
      const refsStr = fileRefsMatch[1].trim();
      for (const ref of refsStr.split(',')) {
        const [path, linesStr] = ref.trim().split(':');
        if (path) {
          const fileRef: { path: string; lines?: number[] } = { path: path.trim() };
          if (linesStr) {
            fileRef.lines = linesStr.split('-').map(n => parseInt(n.trim(), 10)).filter(n => !isNaN(n));
          }
          refs.push(fileRef);
        }
      }
      if (refs.length > 0) metadata.fileReferences = refs;
    }

    // Remove the header section (everything up to and including the first ---)
    let content = rawContent;
    const headerEnd = content.indexOf('\n---\n');
    if (headerEnd !== -1) {
      content = content.substring(headerEnd + 5).trim();
    } else {
      // Fallback: remove individual metadata lines and title
      content = content
        .replace(/^#\s+.+\n+/, '')
        .replace(/\*\*From:\*\*\s*.+\n?/g, '')
        .replace(/\*\*To:\*\*\s*.+\n?/g, '')
        .replace(/\*\*Date:\*\*\s*.+\n?/g, '')
        .replace(/\*\*Type:\*\*\s*.+\n?/g, '')
        .replace(/\*\*Severity:\*\*\s*.+\n?/g, '')
        .replace(/\*\*Status:\*\*\s*.+\n?/g, '')
        .replace(/\*\*(?:In-Reply-To|Reply-To):\*\*\s*.+\n?/g, '')
        .replace(/\*\*Thread:\*\*\s*.+\n?/g, '')
        .replace(/\*\*Priority:\*\*\s*.+\n?/g, '')
        .replace(/\*\*File-References:\*\*\s*.+\n?/g, '')
        .replace(/\*\*Blocked-By:\*\*\s*.+\n?/g, '')
        .replace(/\*\*Blocks:\*\*\s*.+\n?/g, '')
        .replace(/\*\*Acknowledged:\*\*\s*.+\n?/g, '')
        .replace(/^---\n/gm, '')
        .trim();
    }

    return { metadata, content };
  };

  const viewMessage = async (messageId: string) => {
    try {
      const response = await fetch(`${API_BASE}/messages/${encodeURIComponent(messageId)}?render=false`);
      if (!response.ok) throw new Error('Failed to fetch message');
      const msg = await response.json();
      const { metadata, content } = parseMessageContent(msg.content || '');
      // Use msg.status as source of truth (from API), fallback to parsed metadata
      setViewingMessage({
        id: messageId,
        subject: msg.subject,
        content,
        metadata: {
          ...metadata,
          status: msg.status || metadata.status || 'open'
        }
      });
    } catch (err) {
      console.error('Failed to load message:', err);
    }
  };

  const updateMessageStatus = async (messageId: string, newStatus: string) => {
    try {
      // Optimistic update via store
      storeUpdateStatus(messageId, newStatus as AgentMailMessage['status']);

      // Update viewing message state
      if (viewingMessage && viewingMessage.id === messageId) {
        setViewingMessage({
          ...viewingMessage,
          metadata: { ...viewingMessage.metadata, status: newStatus }
        });
      }

      // Send to server
      const response = await fetch(`${API_BASE}/messages/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_id: messageId, status: newStatus }),
      });
      if (!response.ok) throw new Error('Failed to update status');
    } catch (err) {
      console.error('Failed to update message status:', err);
      // On error, request fresh data
      refreshData();
    }
  };

  const updateMessageRouting = async (messageId: string, field: 'from' | 'to', value: string) => {
    try {
      const displayValue = value.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

      // Optimistic update via store
      storeUpdateRouting(messageId, field, value);

      // Update viewing message state
      setViewingMessage(prev => {
        if (!prev || prev.id !== messageId) return prev;
        return {
          ...prev,
          metadata: {
            ...prev.metadata,
            [field]: displayValue
          }
        };
      });

      // Send to server
      const response = await fetch(`${API_BASE}/messages/routing`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_id: messageId, field, value }),
      });
      if (!response.ok) throw new Error('Failed to update routing');
    } catch (err) {
      console.error('Failed to update message routing:', err);
      // On error, request fresh data
      refreshData();
    }
  };

  const sendNewMessage = async () => {
    if (!composing) return;
    try {
      const response = await fetch(`${API_BASE}/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from_agent: 'coordinator',
          to_agent: composing.toAgent,
          subject: composing.subject,
          message_type: composing.type,
          content: composing.content,
        }),
      });
      if (!response.ok) throw new Error('Failed to send message');
      setComposing(null);
      // File watcher will pick up the new message and broadcast via WebSocket
    } catch (err) {
      console.error('Failed to send message:', err);
    }
  };

  // Maintenance Actions
  const requestStatusUpdate = (agentName: string) => {
    const openMessages = data?.messages.filter(m =>
      m.to_agent === agentName && (m.status === 'open' || m.status === 'in_progress')
    ) || [];

    const content = `Please provide status updates on your ${openMessages.length} open/in-progress items:\n\n${
      openMessages.map(m => `- **${m.subject}** (${m.status})`).join('\n')
    }\n\nFor each item, please update the status or reply with progress.`;

    setComposing({
      toAgent: agentName,
      subject: 'Status Update Request',
      content,
      type: 'directive',
    });
  };

  const requestThreadCleanup = (agentName: string) => {
    const staleMessages = data?.messages.filter(m => {
      if (m.to_agent !== agentName && m.from_agent !== agentName) return false;
      if (m.status === 'closed' || m.archived) return false;
      // Check if message is older than 3 days
      const msgDate = new Date(m.date);
      const threeDaysAgo = new Date();
      threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);
      return msgDate < threeDaysAgo;
    }) || [];

    const content = `Please review and close any stale threads:\n\n${
      staleMessages.map(m => `- **${m.subject}** (${m.status}, ${m.date})`).join('\n')
    }\n\nMark as resolved/closed if complete, or reply with blockers.`;

    setComposing({
      toAgent: agentName,
      subject: 'Thread Cleanup Request',
      content,
      type: 'directive',
    });
  };

  const openBulkResolveModal = (agentName: string) => {
    const openMessages = data?.messages.filter(m =>
      m.to_agent === agentName && (m.status === 'open' || m.status === 'in_progress')
    ) || [];

    setBulkSelectModal({
      type: 'resolve',
      messages: openMessages.map(m => ({ id: m.id, subject: m.subject, selected: false })),
    });
  };

  const openBulkArchiveModal = (agentName: string) => {
    const closedMessages = data?.messages.filter(m =>
      (m.to_agent === agentName || m.from_agent === agentName) &&
      (m.status === 'closed' || m.status === 'resolved') &&
      !m.archived
    ) || [];

    setBulkSelectModal({
      type: 'archive',
      messages: closedMessages.map(m => ({ id: m.id, subject: m.subject, selected: true })),
    });
  };

  const executeBulkAction = async () => {
    if (!bulkSelectModal) return;

    const selectedIds = bulkSelectModal.messages
      .filter(m => m.selected)
      .map(m => m.id);

    if (selectedIds.length === 0) {
      setBulkSelectModal(null);
      return;
    }

    try {
      if (bulkSelectModal.type === 'resolve') {
        const response = await fetch(`${API_BASE}/messages/status/bulk`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message_ids: selectedIds, status: 'resolved' }),
        });
        if (!response.ok) throw new Error('Failed to update status');
      } else {
        const response = await fetch(`${API_BASE}/messages/archive/bulk`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message_ids: selectedIds, archived: true }),
        });
        if (!response.ok) throw new Error('Failed to archive');
      }
      setBulkSelectModal(null);
      refreshData();
    } catch (err) {
      console.error('Bulk action failed:', err);
    }
  };

  const toggleBulkSelectAll = () => {
    if (!bulkSelectModal) return;
    const allSelected = bulkSelectModal.messages.every(m => m.selected);
    setBulkSelectModal({
      ...bulkSelectModal,
      messages: bulkSelectModal.messages.map(m => ({ ...m, selected: !allSelected })),
    });
  };

  const toggleBulkSelectItem = (id: string) => {
    if (!bulkSelectModal) return;
    setBulkSelectModal({
      ...bulkSelectModal,
      messages: bulkSelectModal.messages.map(m =>
        m.id === id ? { ...m, selected: !m.selected } : m
      ),
    });
  };

  const viewStatusFile = async (agentName: string) => {
    try {
      // Fetch raw markdown content
      const response = await fetch(`${API_BASE}/agents/${agentName}/status/raw`);
      if (!response.ok) throw new Error('No status file found');
      const data = await response.json();
      const filePath = `agentmail/status/${agentName}_status.md`;
      setViewingStatus({ agentName, content: data.content, filePath });
    } catch (err) {
      console.error('Failed to load status:', err);
    }
  };

  // WebSocket handles real-time updates automatically via useAgentMailWebSocket

  // Handle modal scroll to hide/show header
  useEffect(() => {
    const modalBody = modalBodyRef.current;
    if (!modalBody || !viewingMessage) return;

    const handleScroll = () => {
      setModalScrolled(modalBody.scrollTop > 20);
    };

    modalBody.addEventListener('scroll', handleScroll);
    return () => modalBody.removeEventListener('scroll', handleScroll);
  }, [viewingMessage]);

  // Reset scroll state when modal opens
  useEffect(() => {
    if (viewingMessage) {
      setModalScrolled(false);
    }
  }, [viewingMessage]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in inputs
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      // ESC - close modal or deselect agent
      if (e.key === 'Escape') {
        if (viewingMessage) {
          setViewingMessage(null);
        } else if (viewingThread) {
          setViewingThread(null);
        } else if (viewingNote) {
          setViewingNote(null);
        } else if (viewingStatus) {
          setViewingStatus(null);
        } else if (selectedAgent) {
          setSelectedAgent(null);
        }
        return;
      }

      // R - refresh
      if (e.key === 'r' && !e.metaKey && !e.ctrlKey) {
        refreshData();
        return;
      }

      // 1/2/3/4 - switch tabs when agent selected
      if (selectedAgent) {
        if (e.key === '1') setRightTab('inbox');
        if (e.key === '2') setRightTab('sent');
        if (e.key === '3') setRightTab('plans');
        if (e.key === '4') setRightTab('notes');
      }

      // Cmd+K - open search
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('.am-search-input') as HTMLInputElement;
        if (searchInput) {
          searchInput.focus();
        }
        return;
      }

      // J/K - navigate agents (without cmd/ctrl)
      if (data?.agents && !e.metaKey && !e.ctrlKey && (e.key === 'j' || e.key === 'k')) {
        const currentIndex = selectedAgent
          ? data.agents.findIndex(a => a.name === selectedAgent)
          : -1;

        if (e.key === 'j') {
          // Next agent
          const nextIndex = currentIndex < data.agents.length - 1 ? currentIndex + 1 : 0;
          setSelectedAgent(data.agents[nextIndex].name);
          setRightTab('inbox');
        } else if (e.key === 'k') {
          // Previous agent
          const prevIndex = currentIndex > 0 ? currentIndex - 1 : data.agents.length - 1;
          setSelectedAgent(data.agents[prevIndex].name);
          setRightTab('inbox');
        }
      }

      // ? - show help
      if (e.key === '?') {
        e.preventDefault();
        alert(`Keyboard Shortcuts:
━━━━━━━━━━━━━━━━━━━━
ESC     Close modal / Deselect
R       Refresh data
J/K     Next/Previous agent
1/2/3/4 Inbox/Sent/Plans/Notes tabs
?       Show this help`);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [viewingMessage, viewingThread, viewingNote, viewingStatus, selectedAgent, data, refreshData]);

  const getStatus = (agentName: string): AgentStatus | undefined => {
    return data?.agent_statuses.find(s => s.name === agentName);
  };

  const filterMessages = (messages: AgentMailMessage[]): AgentMailMessage[] => {
    let filtered = hideCompleted
      ? messages.filter(m => m.status !== 'resolved' && m.status !== 'closed')
      : messages;

    // Sort: open/in_progress first, then resolved/closed
    return filtered.sort((a, b) => {
      const aCompleted = a.status === 'resolved' || a.status === 'closed';
      const bCompleted = b.status === 'resolved' || b.status === 'closed';
      if (aCompleted !== bCompleted) return aCompleted ? 1 : -1;
      // Secondary sort by date (newest first)
      return b.date.localeCompare(a.date);
    });
  };

  const getAgentInbox = (agentName: string): AgentMailMessage[] => {
    const messages = data?.messages.filter(m => m.to_agent === agentName) || [];
    return filterMessages(messages);
  };

  const getAgentSent = (agentName: string): AgentMailMessage[] => {
    const messages = data?.messages.filter(m => m.from_agent === agentName) || [];
    return filterMessages(messages);
  };

  const getAgentPlans = (agentName: string): AgentMailMessage[] => {
    const messages = data?.messages.filter(m =>
      (m.to_agent === agentName || m.from_agent === agentName) && m.type === 'plan'
    ) || [];
    return filterMessages(messages);
  };

  // Message-based stats for selected agent
  const getAgentMessageStats = (agentName: string) => {
    const inbox = data?.messages.filter(m => m.to_agent === agentName) || [];
    return {
      total: inbox.length,
      open: inbox.filter(m => m.status === 'open').length,
      inProgress: inbox.filter(m => m.status === 'in_progress').length,
      resolved: inbox.filter(m => m.status === 'resolved').length,
      closed: inbox.filter(m => m.status === 'closed').length,
    };
  };

  const selectedAgentInfo = data?.agents.find(a => a.name === selectedAgent);

  if (loading && !data) {
    return (
      <div className="agentmail-screen">
        <div className="am-loading">Loading AgentMail Dashboard...</div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="agentmail-screen">
        <div className="am-error">
          <h2>Connection Error</h2>
          <p>{error}</p>
          <p className="hint">Make sure the API server is running on localhost:8000</p>
          <button onClick={refreshData} className="am-btn">Retry</button>
        </div>
      </div>
    );
  }

  const getStatusLabel = (status?: string) => {
    switch (status) {
      case 'open': return 'Open';
      case 'in_progress': return 'In Progress';
      case 'resolved': return 'Resolved';
      case 'closed': return 'Closed';
      default: return 'Open';
    }
  };

  // Strip structural markdown (headers, code blocks, etc) but keep inline formatting
  const preparePreview = (text: string) => {
    return text
      // Remove headers
      .replace(/^#{1,6}\s+/gm, '')
      // Remove code blocks
      .replace(/```[\s\S]*?```/g, '')
      // Remove images
      .replace(/!\[.*?\]\(.*?\)/g, '')
      // Remove horizontal rules
      .replace(/^[-*_]{3,}\s*$/gm, '')
      // Remove table syntax
      .replace(/\|/g, ' ')
      .replace(/^[-:|\s]+$/gm, '')
      // Collapse newlines to spaces (keeps inline md like **bold**)
      .replace(/\n+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 400);
  };

  const renderMessageCard = (msg: AgentMailMessage) => {
    const fromColor = getAgentColor(msg.from_agent);
    const toColor = getAgentColor(msg.to_agent);
    const severityClass = msg.severity ? `severity-${msg.severity.toLowerCase()}` : '';
    const statusClass = `status-${msg.status || 'open'}`;

    return (
      <div
        key={msg.id}
        className={`am-message-card ${severityClass}`}
        onClick={() => viewMessage(msg.id)}
      >
        {/* Title first */}
        <h3 className="am-message-subject">{msg.subject}</h3>

        {/* Status and metadata row */}
        <div className="am-message-meta-row">
          <div className="am-message-flow">
            <span className="flow-agent" style={{ '--agent-color': fromColor } as React.CSSProperties}>
              {msg.from_agent.replace('_agent', '')}
            </span>
            <span className="flow-arrow">→</span>
            <span className="flow-agent" style={{ '--agent-color': toColor } as React.CSSProperties}>
              {msg.to_agent.replace('_agent', '')}
            </span>
          </div>
          <span className={`am-status-badge ${statusClass}`}>{getStatusLabel(msg.status)}</span>
          {msg.severity && (
            <span className={`am-severity ${severityClass}`}>{msg.severity}</span>
          )}
          <span className="am-message-type">{msg.type}</span>
          {msg.thread_id && (
            <span
              className="am-thread-badge clickable"
              title={`Thread: ${msg.thread_id}`}
              onClick={(e) => { e.stopPropagation(); viewThread(msg.thread_id!); }}
            >
              ◈
            </span>
          )}
          {msg.acknowledged_at && (
            <span className="am-ack-badge" title={`Acknowledged: ${msg.acknowledged_at}`}>✓</span>
          )}
          <span className="am-message-date">{msg.date}</span>
        </div>

        {/* Content preview - rendered markdown */}
        {msg.preview && (
          <div className="am-message-preview">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {preparePreview(msg.preview)}
            </ReactMarkdown>
          </div>
        )}
      </div>
    );
  };

  const NAV_GROUPS = [
    {
      label: 'Simulation',
      items: [
        { to: '/', label: 'Game', icon: <Gamepad2 size={16} /> },
        { to: '/sandbox', label: 'Sandbox', icon: <Box size={16} /> },
        { to: '/play-sim', label: 'Play', icon: <Play size={16} /> },
        { to: '/integrated', label: 'Integrated', icon: <Zap size={16} /> },
        { to: '/v2-sim', label: 'V2 Sim', icon: <Target size={16} /> },
      ]
    },
    {
      label: 'Routes',
      items: [
        { to: '/pocket', label: 'Pocket', icon: <Circle size={16} /> },
        { to: '/routes', label: 'Routes', icon: <Route size={16} /> },
        { to: '/team-routes', label: 'Team Routes', icon: <GitBranch size={16} /> },
      ]
    },
    {
      label: 'Management',
      items: [
        { to: '/manage', label: 'Manage', icon: <ClipboardList size={16} /> },
        { to: '/admin', label: 'Admin', icon: <Settings size={16} /> },
      ]
    }
  ];

  const toggleTheme = () => {
    const isSepia = document.documentElement.classList.contains('sepia-mode');
    if (isSepia) {
      document.documentElement.classList.remove('sepia-mode');
      localStorage.setItem('sepia-mode', 'false');
    } else {
      document.documentElement.classList.add('sepia-mode');
      localStorage.setItem('sepia-mode', 'true');
    }
  };

  return (
    <div className="agentmail-screen">
      {/* Vertical Sidebar */}
      <aside className={`am-sidebar ${sidebarExpanded ? 'expanded' : ''}`}>
        <div className="am-sidebar-top">
          {/* App Navigation Dropdown */}
          <div className="am-sidebar-app-nav">
            <button
              className={`am-sidebar-btn ${appNavOpen ? 'active' : ''}`}
              onClick={() => setAppNavOpen(!appNavOpen)}
              title="Switch App"
            >
              <Menu size={18} />
              {sidebarExpanded && <span className="sidebar-label">Apps</span>}
            </button>

            {appNavOpen && (
              <div className="am-app-nav-dropdown">
                {NAV_GROUPS.map(group => (
                  <div key={group.label} className="app-nav-group">
                    <div className="app-nav-group-label">{group.label}</div>
                    {group.items.map(item => (
                      <a
                        key={item.to}
                        href={item.to}
                        className="app-nav-item"
                        onClick={() => setAppNavOpen(false)}
                      >
                        <span className="app-nav-icon">{item.icon}</span>
                        <span className="app-nav-label">{item.label}</span>
                      </a>
                    ))}
                  </div>
                ))}
                <div className="app-nav-group">
                  <div className="app-nav-group-label">Theme</div>
                  <button className="app-nav-item" onClick={toggleTheme}>
                    <span className="app-nav-icon"><Sun size={16} /></span>
                    <span className="app-nav-label">Toggle Theme</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="am-sidebar-divider" />

          <button
            className={`am-sidebar-btn ${viewMode === 'oversight' ? 'active' : ''}`}
            onClick={() => setViewMode('oversight')}
            title="Inbox"
          >
            <Inbox size={18} />
            {sidebarExpanded && <span className="sidebar-label">Inbox</span>}
          </button>

          <button
            className={`am-sidebar-btn ${viewMode === 'list' ? 'active' : ''}`}
            onClick={() => setViewMode('list')}
            title="Agents"
          >
            <Users size={18} />
            {sidebarExpanded && <span className="sidebar-label">Agents</span>}
          </button>

          <button
            className={`am-sidebar-btn ${viewMode === 'kanban' ? 'active' : ''}`}
            onClick={() => setViewMode('kanban')}
            title="Board"
          >
            <LayoutGrid size={18} />
            {sidebarExpanded && <span className="sidebar-label">Board</span>}
          </button>

          <div className="am-sidebar-divider" />

          <button
            className="am-sidebar-btn"
            onClick={() => {
              const searchInput = document.querySelector('.am-search-input') as HTMLInputElement;
              if (searchInput) searchInput.focus();
              else setSearchQuery(' ');
            }}
            title="Search"
          >
            <Search size={18} />
            {sidebarExpanded && <span className="sidebar-label">Search</span>}
          </button>

          <button
            className="am-sidebar-btn compose"
            onClick={() => setComposing({ toAgent: '', subject: '', content: '', type: 'task' })}
            title="Compose"
          >
            <PenSquare size={18} />
            {sidebarExpanded && <span className="sidebar-label">New</span>}
          </button>
        </div>

        <div className="am-sidebar-bottom">
          <button
            className="am-sidebar-btn"
            onClick={refreshData}
            title="Sync"
          >
            <RefreshCw size={18} />
            {sidebarExpanded && <span className="sidebar-label">Sync</span>}
          </button>

          <button
            className="am-sidebar-btn toggle"
            onClick={() => {
              const newVal = !sidebarExpanded;
              setSidebarExpanded(newVal);
              localStorage.setItem('sidebar-expanded', String(newVal));
            }}
            title={sidebarExpanded ? 'Collapse' : 'Expand'}
          >
            {sidebarExpanded ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
          </button>

          <div className={`am-sidebar-status ${isConnected ? 'online' : 'offline'}`} title={isConnected ? 'Connected' : 'Offline'}>
            <span className="status-dot" />
            {sidebarExpanded && <span className="status-label">{isConnected ? 'Live' : 'Offline'}</span>}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="am-main-content">

      {/* Search Results Overlay */}
      {searchResults !== null && (
        <div className="am-search-overlay" onClick={() => { setSearchResults(null); setSearchQuery(''); }}>
          <div className="am-search-panel" onClick={e => e.stopPropagation()}>
            <div className="am-search-header">
              <input
                type="text"
                className="am-search-modal-input"
                placeholder="Search messages, notes, status..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                autoFocus
              />
              <button className="am-search-close" onClick={() => { setSearchResults(null); setSearchQuery(''); }}>×</button>
            </div>
            <div className="am-search-results-count">
              {isSearching ? 'Searching...' : `${searchResults.length} results`}
            </div>
            <div className="am-search-results">
              {searchResults.length === 0 ? (
                <div className="am-search-empty">No results found</div>
              ) : (
                searchResults.map((result, idx) => (
                  <div
                    key={`${result.type}-${result.id}-${idx}`}
                    className="am-search-result"
                    onClick={() => {
                      if (result.type === 'message') {
                        viewMessage(result.id);
                      }
                      setSearchResults(null);
                      setSearchQuery('');
                    }}
                  >
                    <div className="am-search-result-header">
                      <span className={`am-search-type type-${result.type}`}>{result.type}</span>
                      <span className="am-search-title">{result.title}</span>
                      <span className="am-search-date">{result.date}</span>
                    </div>
                    <div className="am-search-subtitle">{result.subtitle}</div>
                    {result.matches.length > 0 && (
                      <div className="am-search-matches">
                        {result.matches.slice(0, 2).map((match, i) => (
                          <div key={i} className="am-search-match">{match}</div>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {data && viewMode === 'oversight' && (
        <OversightDashboard isConnected={isConnected} onRequestSync={requestSync} />
      )}

      {data && viewMode !== 'oversight' && (
        <div className={`am-content ${selectedAgent ? 'agent-selected' : ''}`}>
          {/* Left Panel - Agents */}
          <section className="am-panel agents-panel">
            <h2>Agents</h2>
            <div className="am-agents-list">
              {data.agents.map(agent => {
                const status = getStatus(agent.name);
                const isActive = (status?.in_progress?.length || 0) > 0;
                const isSelected = selectedAgent === agent.name;
                const color = getAgentColor(agent.name);

                return (
                  <div
                    key={agent.name}
                    className={`am-agent-card ${isActive ? 'active' : ''} ${isSelected ? 'selected' : ''} ${agent.is_online ? 'online' : ''}`}
                    style={{ '--agent-color': color } as React.CSSProperties}
                    onClick={() => {
                      if (viewMode === 'kanban') {
                        // In kanban view, toggle agent filter without leaving kanban
                        setSelectedAgent(isSelected ? null : agent.name);
                      } else {
                        setSelectedAgent(isSelected ? null : agent.name);
                        setRightTab('inbox');
                      }
                    }}
                  >
                    <div className="am-agent-header">
                      <div className={`am-agent-indicator ${agent.is_online ? 'online' : ''}`}></div>
                      <h3 className="am-agent-name">{agent.display_name}</h3>
                      <button
                        className="am-status-btn"
                        title="View status file"
                        onClick={(e) => {
                          e.stopPropagation();
                          viewStatusFile(agent.name);
                        }}
                      >
                        Status
                      </button>
                    </div>
                    <p className="am-agent-role">{agent.role || 'No role defined'}</p>
                    <div className="am-agent-meta">
                      <span className="am-agent-updated">{agent.last_active || 'Never'}</span>
                      <span className="am-agent-inbox">{agent.inbox_count} in inbox</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Right Panel - Agent Details or Welcome */}
          <section className="am-panel detail-panel">
            {viewMode === 'kanban' ? (
              /* Kanban Board View */
              <div className="am-kanban-board">
                {selectedAgent && (
                  <div className="am-kanban-filter">
                    Filtered by: <span style={{ color: getAgentColor(selectedAgent) }}>{selectedAgent.replace('_agent', '').replace('_', ' ')}</span>
                    <button className="am-kanban-clear-filter" onClick={() => setSelectedAgent(null)}>× Clear</button>
                  </div>
                )}
                <div className="am-kanban-columns">
                  {(['open', 'in_progress', 'resolved', 'closed'] as const).map(status => (
                    <div key={status} className="am-kanban-column">
                      <div className="am-kanban-column-header">
                        <span className={`am-kanban-status status-${status}`}>
                          {status.replace('_', ' ')}
                        </span>
                        <span className="am-kanban-count">{kanbanData?.counts[status] || 0}</span>
                      </div>
                      <div className="am-kanban-cards">
                        {(kanbanData?.columns[status] || []).map(card => (
                          <div
                            key={card.id}
                            className={`am-kanban-card ${card.severity ? `severity-${card.severity.toLowerCase()}` : ''}`}
                            onClick={() => viewMessage(card.id)}
                          >
                            <div className="am-kanban-card-subject">{card.subject}</div>
                            <div className="am-kanban-card-meta">
                              <span
                                className="am-kanban-from"
                                style={{ '--agent-color': getAgentColor(card.from_agent) } as React.CSSProperties}
                              >
                                {card.from_agent.replace('_agent', '')}
                              </span>
                              <span className="am-kanban-arrow">→</span>
                              <span
                                className="am-kanban-to"
                                style={{ '--agent-color': getAgentColor(card.to_agent) } as React.CSSProperties}
                              >
                                {card.to_agent.replace('_agent', '')}
                              </span>
                            </div>
                            <div className="am-kanban-card-footer">
                              <span className="am-kanban-type">{card.type}</span>
                              {card.severity && (
                                <span className={`am-kanban-severity severity-${card.severity.toLowerCase()}`}>
                                  {card.severity}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                        {(kanbanData?.columns[status] || []).length === 0 && (
                          <div className="am-kanban-empty">{kanbanData ? 'No items' : 'Loading...'}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : selectedAgent && selectedAgentInfo ? (
              <>
                <div className="am-detail-header">
                  <div className="am-detail-title">
                    <div
                      className="am-agent-badge"
                      style={{ '--agent-color': getAgentColor(selectedAgent) } as React.CSSProperties}
                    >
                      {selectedAgentInfo.display_name}
                    </div>
                    {(() => {
                      const stats = getAgentMessageStats(selectedAgent);
                      return (
                        <div className="am-status-summary">
                          <span className="status-item open">{stats.open} open</span>
                          <span className="status-item progress">{stats.inProgress} active</span>
                          <span className="status-item resolved">{stats.resolved} resolved</span>
                          <span className="status-item closed">{stats.closed} closed</span>
                        </div>
                      );
                    })()}
                  </div>
                  <div className="am-detail-controls">
                    <label className="am-filter-toggle">
                      <input
                        type="checkbox"
                        checked={hideCompleted}
                        onChange={(e) => setHideCompleted(e.target.checked)}
                      />
                      Hide completed
                    </label>
                  </div>
                  <div className="am-detail-tabs">
                    <button
                      className={`am-tab ${rightTab === 'inbox' ? 'active' : ''}`}
                      onClick={() => setRightTab('inbox')}
                    >
                      Inbox ({getAgentInbox(selectedAgent).length})
                    </button>
                    <button
                      className={`am-tab ${rightTab === 'sent' ? 'active' : ''}`}
                      onClick={() => setRightTab('sent')}
                    >
                      Sent ({getAgentSent(selectedAgent).length})
                    </button>
                    <button
                      className={`am-tab ${rightTab === 'plans' ? 'active' : ''}`}
                      onClick={() => setRightTab('plans')}
                    >
                      Plans ({getAgentPlans(selectedAgent).length})
                    </button>
                    <button
                      className={`am-tab ${rightTab === 'notes' ? 'active' : ''}`}
                      onClick={() => setRightTab('notes')}
                    >
                      Notes {agentNotes.length > 0 && `(${agentNotes.length})`}
                    </button>
                  </div>
                </div>

                {/* Maintenance Panel */}
                <div className="am-maintenance-panel">
                  <button
                    className="am-maintenance-toggle"
                    onClick={() => setMaintenanceExpanded(!maintenanceExpanded)}
                  >
                    <Wrench size={14} />
                    <span>Maintenance</span>
                    {maintenanceExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                  {maintenanceExpanded && (
                    <div className="am-maintenance-actions">
                      <button
                        className="am-maintenance-btn"
                        onClick={() => requestStatusUpdate(selectedAgent)}
                        title="Send a message requesting status updates on open items"
                      >
                        <Mail size={14} />
                        <span>Request Status Update</span>
                      </button>
                      <button
                        className="am-maintenance-btn"
                        onClick={() => requestThreadCleanup(selectedAgent)}
                        title="Send a message requesting cleanup of stale threads"
                      >
                        <Trash2 size={14} />
                        <span>Request Thread Cleanup</span>
                      </button>
                      <button
                        className="am-maintenance-btn"
                        onClick={() => openBulkResolveModal(selectedAgent)}
                        title="Bulk mark messages as resolved"
                      >
                        <CheckCircle size={14} />
                        <span>Bulk Mark Resolved</span>
                      </button>
                      <button
                        className="am-maintenance-btn"
                        onClick={() => openBulkArchiveModal(selectedAgent)}
                        title="Archive all closed messages"
                      >
                        <Archive size={14} />
                        <span>Archive All Closed</span>
                      </button>
                    </div>
                  )}
                </div>

                <div className="am-messages-list" key={`${selectedAgent}-${rightTab}-${hideCompleted}`}>
                  {rightTab === 'inbox' && getAgentInbox(selectedAgent).map(renderMessageCard)}
                  {rightTab === 'sent' && getAgentSent(selectedAgent).map(renderMessageCard)}
                  {rightTab === 'plans' && getAgentPlans(selectedAgent).map(renderMessageCard)}

                  {rightTab === 'inbox' && getAgentInbox(selectedAgent).length === 0 && (
                    <div className="am-empty">No messages in inbox</div>
                  )}
                  {rightTab === 'sent' && getAgentSent(selectedAgent).length === 0 && (
                    <div className="am-empty">No sent messages</div>
                  )}
                  {rightTab === 'plans' && getAgentPlans(selectedAgent).length === 0 && (
                    <div className="am-empty">No plans</div>
                  )}

                  {/* Notes Tab */}
                  {rightTab === 'notes' && (
                    notesLoading ? (
                      <div className="am-empty">Loading notes...</div>
                    ) : agentNotes.length === 0 ? (
                      <div className="am-empty">No notes yet</div>
                    ) : (
                      agentNotes.map(note => (
                        <div
                          key={note.id}
                          className="am-message-card am-note-card"
                          onClick={() => viewNote(selectedAgent, note.id)}
                        >
                          <h3 className="am-message-subject">{note.title}</h3>
                          <div className="am-message-meta-row">
                            <span className="am-message-date">{note.date}</span>
                            {note.domain && (
                              <span className="am-note-domain">{note.domain}</span>
                            )}
                            {note.tags.map(tag => (
                              <span key={tag} className="am-note-tag">{tag}</span>
                            ))}
                          </div>
                        </div>
                      ))
                    )
                  )}
                </div>
              </>
            ) : (
              <div className="am-dashboard">
                {/* Dashboard Stats */}
                <div className="am-dash-stats">
                  <div className="am-dash-stat">
                    <span className="stat-value">{data.messages.filter(m => m.status === 'open').length}</span>
                    <span className="stat-label">Open</span>
                  </div>
                  <div className="am-dash-stat">
                    <span className="stat-value">{data.messages.filter(m => m.status === 'in_progress').length}</span>
                    <span className="stat-label">In Progress</span>
                  </div>
                  <div className="am-dash-stat urgent">
                    <span className="stat-value">{data.messages.filter(m => m.type === 'bug' && m.severity === 'BLOCKING').length}</span>
                    <span className="stat-label">Blocking Bugs</span>
                  </div>
                  <div className="am-dash-stat">
                    <span className="stat-value">{data.agents.filter(a => a.is_online).length}</span>
                    <span className="stat-label">Online</span>
                  </div>
                </div>

                {/* Action Required Section */}
                {(() => {
                  const actionItems = data.messages.filter(m =>
                    (m.type === 'bug' && m.severity === 'BLOCKING' && m.status !== 'resolved' && m.status !== 'closed') ||
                    (m.type === 'question' && m.status === 'open') ||
                    (m.type === 'task' && m.status === 'open')
                  );
                  if (actionItems.length === 0) return null;
                  return (
                    <div className="am-dash-section">
                      <h3 className="am-dash-title urgent">Action Required ({actionItems.length})</h3>
                      <div className="am-messages-list">
                        {actionItems.slice(0, 5).map(renderMessageCard)}
                      </div>
                    </div>
                  );
                })()}

                {/* Open Bugs */}
                {(() => {
                  const bugs = data.messages.filter(m => m.type === 'bug' && m.status !== 'resolved' && m.status !== 'closed');
                  if (bugs.length === 0) return null;
                  return (
                    <div className="am-dash-section">
                      <h3 className="am-dash-title">Open Bugs ({bugs.length})</h3>
                      <div className="am-messages-list">
                        {bugs.slice(0, 4).map(renderMessageCard)}
                      </div>
                    </div>
                  );
                })()}

                {/* In Progress */}
                {(() => {
                  const inProgress = data.messages.filter(m => m.status === 'in_progress');
                  if (inProgress.length === 0) return null;
                  return (
                    <div className="am-dash-section">
                      <h3 className="am-dash-title">In Progress ({inProgress.length})</h3>
                      <div className="am-messages-list">
                        {inProgress.slice(0, 4).map(renderMessageCard)}
                      </div>
                    </div>
                  );
                })()}

                {/* Lost/Unrouted Messages */}
                {(() => {
                  const knownAgents = new Set(['coordinator', ...data.agents.map(a => a.name)]);
                  const lostMessages = data.messages.filter(m =>
                    !knownAgents.has(m.to_agent) || !knownAgents.has(m.from_agent)
                  );
                  if (lostMessages.length === 0) return null;
                  return (
                    <div className="am-dash-section">
                      <h3 className="am-dash-title warning">Lost Messages ({lostMessages.length})</h3>
                      <div className="am-messages-list">
                        {lostMessages.map(renderMessageCard)}
                      </div>
                    </div>
                  );
                })()}

                {/* Recent Activity */}
                <div className="am-dash-section">
                  <h3 className="am-dash-title">Recent Activity</h3>
                  <div className="am-messages-list">
                    {data.messages.slice(0, 5).map(renderMessageCard)}
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>
      )}

      {/* Message Modal with Markdown */}
      {viewingMessage && (
        <div className="am-modal-overlay" onClick={() => { setViewingMessage(null); setIsFullscreen(false); }}>
          <div className={`am-modal ${isFullscreen ? 'fullscreen' : ''} ${modalScrolled ? 'scrolled' : ''}`} onClick={e => e.stopPropagation()}>
            <div className="am-modal-chrome">
              <div className="am-modal-header">
                <h2>{viewingMessage.subject}</h2>
                <div className="am-modal-actions">
                  <button
                    className="am-modal-btn"
                    onClick={() => setIsFullscreen(!isFullscreen)}
                    title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
                  >
                    {isFullscreen ? '⊙' : '⛶'}
                  </button>
                  <button className="am-modal-close" onClick={() => { setViewingMessage(null); setIsFullscreen(false); }}>×</button>
                </div>
              </div>

              {/* Metadata Header */}
              <div className="am-message-metadata">
              <div className="am-metadata-row">
                <div className="am-metadata-item">
                  <span className="am-metadata-label">From</span>
                  <select
                    className="am-routing-select"
                    value={viewingMessage.metadata.from?.toLowerCase().replace(/ /g, '_') || ''}
                    onChange={(e) => updateMessageRouting(viewingMessage.id, 'from', e.target.value)}
                    style={{ '--agent-color': getAgentColor(viewingMessage.metadata.from?.toLowerCase().replace(/ /g, '_') || '') } as React.CSSProperties}
                  >
                    <option value="">Unknown</option>
                    <option value="coordinator">Coordinator</option>
                    {data?.agents.map(agent => (
                      <option key={agent.name} value={agent.name}>
                        {agent.display_name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="am-metadata-item">
                  <span className="am-metadata-label">To</span>
                  <select
                    className="am-routing-select"
                    value={viewingMessage.metadata.to?.toLowerCase().replace(/ /g, '_') || ''}
                    onChange={(e) => updateMessageRouting(viewingMessage.id, 'to', e.target.value)}
                    style={{ '--agent-color': getAgentColor(viewingMessage.metadata.to?.toLowerCase().replace(/ /g, '_') || '') } as React.CSSProperties}
                  >
                    <option value="">Unknown</option>
                    <option value="coordinator">Coordinator</option>
                    {data?.agents.map(agent => (
                      <option key={agent.name} value={agent.name}>
                        {agent.display_name}
                      </option>
                    ))}
                  </select>
                </div>
                {viewingMessage.metadata.date && (
                  <div className="am-metadata-item">
                    <span className="am-metadata-label">Date</span>
                    <span className="am-metadata-value">{viewingMessage.metadata.date}</span>
                  </div>
                )}
              </div>
              <div className="am-metadata-row">
                {viewingMessage.metadata.type && (
                  <div className="am-metadata-item">
                    <span className="am-metadata-label">Type</span>
                    <span className="am-metadata-value type">{viewingMessage.metadata.type}</span>
                  </div>
                )}
                {viewingMessage.metadata.severity && (
                  <div className="am-metadata-item">
                    <span className="am-metadata-label">Severity</span>
                    <span className={`am-metadata-value severity severity-${viewingMessage.metadata.severity.toLowerCase()}`}>
                      {viewingMessage.metadata.severity}
                    </span>
                  </div>
                )}
                {viewingMessage.metadata.thread && (
                  <div className="am-metadata-item">
                    <span className="am-metadata-label">Thread</span>
                    <span className="am-metadata-value thread">{viewingMessage.metadata.thread}</span>
                  </div>
                )}
                {viewingMessage.metadata.inReplyTo && (
                  <div className="am-metadata-item">
                    <span className="am-metadata-label">Reply To</span>
                    <span className="am-metadata-value reply">{viewingMessage.metadata.inReplyTo}</span>
                  </div>
                )}
              </div>
              {/* File References */}
              {viewingMessage.metadata.fileReferences && viewingMessage.metadata.fileReferences.length > 0 && (
                <div className="am-file-references">
                  <span className="am-file-refs-label">File References:</span>
                  <div className="am-file-refs-list">
                    {viewingMessage.metadata.fileReferences.map((ref, idx) => (
                      <button
                        key={idx}
                        className="am-file-ref-btn"
                        onClick={() => fetchFilePreview(ref.path, ref.lines)}
                      >
                        {ref.path}
                        {ref.lines && ref.lines.length > 0 && (
                          <span className="am-file-ref-lines">
                            :{ref.lines.join('-')}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {/* Expanded File Preview */}
              {expandedFileRef && (
                <div className="am-file-preview">
                  <div className="am-file-preview-header">
                    <span className="am-file-preview-path">{expandedFileRef.path}</span>
                    {expandedFileRef.lines && (
                      <span className="am-file-preview-lines">
                        Lines {expandedFileRef.lines.join('-')}
                      </span>
                    )}
                    <button
                      className="am-file-preview-close"
                      onClick={() => setExpandedFileRef(null)}
                    >
                      ×
                    </button>
                  </div>
                  <pre className={`am-file-preview-code language-${expandedFileRef.language}`}>
                    <code>{expandedFileRef.content}</code>
                  </pre>
                </div>
              )}
              <div className="am-status-actions">
                <span className="am-status-label">Set Status:</span>
                {(['open', 'in_progress', 'resolved', 'closed'] as const).map(status => (
                  <button
                    key={status}
                    className={`am-status-action-btn ${viewingMessage.metadata.status === status ? 'active' : ''}`}
                    onClick={() => updateMessageStatus(viewingMessage.id, status)}
                  >
                    {status.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>
            </div>

            <div className="am-modal-body" ref={modalBodyRef}>
              <div className="am-markdown">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {viewingMessage.content}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Status File Modal */}
      {viewingStatus && (
        <div className="am-modal-overlay" onClick={() => setViewingStatus(null)}>
          <div className="am-modal am-simple-modal" onClick={e => e.stopPropagation()}>
            <div className="am-modal-header">
              <h2>{viewingStatus.agentName.replace('_', ' ')} Status</h2>
              <button className="am-modal-close" onClick={() => setViewingStatus(null)}>×</button>
            </div>
            <div className="am-status-file-path">
              <span className="path-label">File:</span>
              <code>{viewingStatus.filePath}</code>
            </div>
            <div className="am-modal-body">
              <div className="am-markdown">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {viewingStatus.content}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Note Viewing Modal */}
      {viewingNote && (
        <div className="am-modal-overlay" onClick={() => setViewingNote(null)}>
          <div className="am-modal am-simple-modal" onClick={e => e.stopPropagation()}>
            <div className="am-modal-header">
              <h2>{viewingNote.title}</h2>
              <button className="am-modal-close" onClick={() => setViewingNote(null)}>×</button>
            </div>
            <div className="am-note-metadata">
              <span className="am-note-date">{viewingNote.date}</span>
              {viewingNote.domain && (
                <span className="am-note-domain">{viewingNote.domain}</span>
              )}
              {viewingNote.tags.map(tag => (
                <span key={tag} className="am-note-tag">{tag}</span>
              ))}
            </div>
            <div className="am-modal-body">
              <div className="am-markdown">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {viewingNote.content}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Thread View Modal */}
      {viewingThread && (
        <div className="am-modal-overlay" onClick={() => setViewingThread(null)}>
          <div className="am-modal am-thread-modal" onClick={e => e.stopPropagation()}>
            <div className="am-modal-header">
              <h2>Thread: {viewingThread.thread_id}</h2>
              <button className="am-modal-close" onClick={() => setViewingThread(null)}>×</button>
            </div>
            <div className="am-thread-metadata">
              <span className="am-thread-count">{viewingThread.messages.length} messages</span>
              <span className="am-thread-participants">
                {viewingThread.participants.map(p => (
                  <span
                    key={p}
                    className="am-participant-badge"
                    style={{ '--agent-color': getAgentColor(p) } as React.CSSProperties}
                  >
                    {p.replace('_agent', '')}
                  </span>
                ))}
              </span>
            </div>
            <div className="am-modal-body am-thread-body">
              {/* Render thread messages with indentation */}
              {(() => {
                const renderThreadMessage = (
                  msg: AgentMailMessage & { replies?: unknown[] },
                  depth: number = 0
                ): React.ReactNode => {
                  const fromColor = getAgentColor(msg.from_agent);
                  return (
                    <div key={msg.id} className="am-thread-message" style={{ marginLeft: depth * 24 }}>
                      <div className="am-thread-message-header">
                        <span
                          className="flow-agent"
                          style={{ '--agent-color': fromColor } as React.CSSProperties}
                        >
                          {msg.from_agent.replace('_agent', '')}
                        </span>
                        <span className="am-thread-arrow">→</span>
                        <span
                          className="flow-agent"
                          style={{ '--agent-color': getAgentColor(msg.to_agent) } as React.CSSProperties}
                        >
                          {msg.to_agent.replace('_agent', '')}
                        </span>
                        <span className="am-thread-date">{msg.date}</span>
                        <button
                          className="am-thread-view-btn"
                          onClick={() => { setViewingThread(null); viewMessage(msg.id); }}
                        >
                          View
                        </button>
                      </div>
                      <div className="am-thread-message-subject">{msg.subject}</div>
                      {msg.preview && (
                        <div className="am-thread-message-preview">{msg.preview.slice(0, 150)}...</div>
                      )}
                      {(msg.replies as Array<AgentMailMessage & { replies?: unknown[] }> | undefined)?.map(reply =>
                        renderThreadMessage(reply, depth + 1)
                      )}
                    </div>
                  );
                };

                return viewingThread.reply_tree.map(msg => renderThreadMessage(msg, 0));
              })()}
            </div>
          </div>
        </div>
      )}

      {/* Compose Message Modal */}
      {composing && (
        <div className="am-modal-overlay" onClick={() => setComposing(null)}>
          <div className="am-modal am-simple-modal am-compose-modal" onClick={e => e.stopPropagation()}>
            <div className="am-modal-header">
              <h2>Compose Message</h2>
              <button className="am-modal-close" onClick={() => setComposing(null)}>×</button>
            </div>
            <div className="am-modal-body">
              <div className="am-compose-form">
                <div className="am-compose-row">
                  <div className="am-compose-field">
                    <label className="am-compose-label">To Agent</label>
                    <select
                      className="am-compose-select"
                      value={composing.toAgent}
                      onChange={e => setComposing({ ...composing, toAgent: e.target.value })}
                    >
                      <option value="">Select an agent...</option>
                      {data?.agents.map(agent => (
                        <option key={agent.name} value={agent.name}>
                          {agent.display_name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="am-compose-field">
                    <label className="am-compose-label">Type</label>
                    <select
                      className="am-compose-select"
                      value={composing.type}
                      onChange={e => setComposing({ ...composing, type: e.target.value })}
                    >
                      <option value="task">Task</option>
                      <option value="directive">Directive</option>
                      <option value="question">Question</option>
                      <option value="feedback">Feedback</option>
                      <option value="info">Info</option>
                    </select>
                  </div>
                </div>

                <div className="am-compose-field full">
                  <label className="am-compose-label">Subject</label>
                  <input
                    type="text"
                    className="am-compose-input"
                    placeholder="Enter subject..."
                    value={composing.subject}
                    onChange={e => setComposing({ ...composing, subject: e.target.value })}
                  />
                </div>

                <div className="am-compose-field full">
                  <label className="am-compose-label">Message (Markdown supported)</label>
                  <textarea
                    className="am-compose-textarea"
                    placeholder="Write your message here...&#10;&#10;You can use **markdown** formatting, `code blocks`, and more."
                    value={composing.content}
                    onChange={e => setComposing({ ...composing, content: e.target.value })}
                  />
                </div>

                <div className="am-compose-actions">
                  <button
                    className="am-btn secondary"
                    onClick={() => setComposing(null)}
                  >
                    Cancel
                  </button>
                  <button
                    className="am-btn primary"
                    onClick={sendNewMessage}
                    disabled={!composing.toAgent || !composing.subject || !composing.content}
                  >
                    Send Message
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Bulk Select Modal */}
      {bulkSelectModal && (
        <div className="am-modal-overlay" onClick={() => setBulkSelectModal(null)}>
          <div className="am-modal am-simple-modal am-bulk-modal" onClick={e => e.stopPropagation()}>
            <div className="am-modal-header">
              <h2>{bulkSelectModal.type === 'resolve' ? 'Bulk Mark Resolved' : 'Bulk Archive'}</h2>
              <button className="am-modal-close" onClick={() => setBulkSelectModal(null)}>×</button>
            </div>
            <div className="am-modal-body">
              {bulkSelectModal.messages.length === 0 ? (
                <div className="am-empty">
                  {bulkSelectModal.type === 'resolve'
                    ? 'No open or in-progress messages to resolve'
                    : 'No closed messages to archive'}
                </div>
              ) : (
                <>
                  <div className="am-bulk-header">
                    <label className="am-bulk-select-all">
                      <input
                        type="checkbox"
                        checked={bulkSelectModal.messages.every(m => m.selected)}
                        onChange={toggleBulkSelectAll}
                      />
                      Select All ({bulkSelectModal.messages.filter(m => m.selected).length}/{bulkSelectModal.messages.length})
                    </label>
                  </div>
                  <div className="am-bulk-list">
                    {bulkSelectModal.messages.map(msg => (
                      <label key={msg.id} className="am-bulk-item">
                        <input
                          type="checkbox"
                          checked={msg.selected}
                          onChange={() => toggleBulkSelectItem(msg.id)}
                        />
                        <span className="am-bulk-subject">{msg.subject}</span>
                      </label>
                    ))}
                  </div>
                  <div className="am-compose-actions">
                    <button
                      className="am-btn secondary"
                      onClick={() => setBulkSelectModal(null)}
                    >
                      Cancel
                    </button>
                    <button
                      className="am-btn primary"
                      onClick={executeBulkAction}
                      disabled={bulkSelectModal.messages.filter(m => m.selected).length === 0}
                    >
                      {bulkSelectModal.type === 'resolve' ? 'Mark Resolved' : 'Archive Selected'}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
}
