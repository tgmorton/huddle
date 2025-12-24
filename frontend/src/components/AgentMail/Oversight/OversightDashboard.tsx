/**
 * OversightDashboard - Manager's Inbox
 *
 * Gmail-style threaded view: thread list on left, thread detail on right
 */

import { useState, useMemo, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { Archive, ChevronDown, ChevronRight } from 'lucide-react';
import { useAgentMailStore } from '../../../stores/agentMailStore';
import './OversightDashboard.css';

const API_BASE = 'http://localhost:8000/api/v1/agentmail';

// Filter state type
interface FilterState {
  status: string[];      // ['open', 'in_progress']
  types: string[];       // ['bug', 'task']
  severity: string[];    // ['BLOCKING']
  agents: string[];      // ['qa_agent']
  showArchived: boolean;
}

// Grouping mode
type GroupBy = 'thread' | 'agent' | 'status' | 'time';

// Drag and drop state
interface DragState {
  draggedThreadId: string | null;
  dragOverThreadId: string | null;
}

// Agent colors
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
  claude_code_agent: '#ef4444',
};

function getAgentColor(name: string): string {
  return AGENT_COLORS[name] || '#6b7280';
}

function getAgentAbbrev(name: string): string {
  return name
    .replace('_agent', '')
    .split('_')
    .map(word => word[0]?.toUpperCase() || '')
    .join('');
}

function formatTime(dateStr: string): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();

  if (isToday) {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  }
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatFullDate(dateStr: string): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

// Strip the email header from content (everything before ---)
function stripEmailHeader(content: string): string {
  const separatorIndex = content.indexOf('\n---\n');
  if (separatorIndex !== -1) {
    return content.substring(separatorIndex + 5).trim();
  }
  // Also try just --- at start of line
  const altIndex = content.indexOf('\n---');
  if (altIndex !== -1) {
    return content.substring(altIndex + 4).trim();
  }
  return content;
}

// Highlight @mentions in content for markdown display
function highlightMentions(content: string): string {
  // Replace @agent_name with HTML span (ReactMarkdown allows HTML)
  return content.replace(/@(\w+)/g, (match, agentName) => {
    const color = getAgentColor(agentName);
    return `<span class="mention" style="background: ${color}22; color: ${color}; padding: 1px 4px; border-radius: 3px; font-weight: 500;">${match}</span>`;
  });
}

// Severity priority for sorting (higher = more urgent)
const SEVERITY_PRIORITY: Record<string, number> = {
  'BLOCKING': 3,
  'MAJOR': 2,
  'MINOR': 1,
};

interface Thread {
  id: string;  // thread_id or message id for standalone
  subject: string;
  messages: any[];
  participants: string[];
  latestDate: string;
  latestMessage: any;
  rootMessage: any;
  worstSeverity: string | null;
  hasOpen: boolean;
  hasInProgress: boolean;
  type: string;
}

interface ThreadGroup {
  key: string;
  label: string;
  count: number;
  threads: Thread[];
}

// Determine primary agent for a thread (who currently has the ball - latest message recipient)
function getPrimaryAgent(thread: Thread): string {
  const latestTo = thread.latestMessage?.to_agent;
  if (latestTo && latestTo !== 'coordinator') return latestTo;
  return thread.participants.find(p => p !== 'coordinator') || 'unknown';
}

// Determine time bucket for a date
function getTimeBucket(dateStr: string): { key: string; label: string; order: number } {
  const date = new Date(dateStr);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);

  if (date >= today) return { key: 'today', label: 'Today', order: 0 };
  if (date >= yesterday) return { key: 'yesterday', label: 'Yesterday', order: 1 };
  if (date >= weekAgo) return { key: 'thisWeek', label: 'This Week', order: 2 };
  return { key: 'older', label: 'Older', order: 3 };
}

interface OversightDashboardProps {
  isConnected: boolean;
  onRequestSync: () => void;
}

export function OversightDashboard({ isConnected, onRequestSync }: OversightDashboardProps) {
  const data = useAgentMailStore((state) => state.data);
  const agents = data?.agents ?? [];
  const messages = data?.messages ?? [];

  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [expandedMessageId, setExpandedMessageId] = useState<string | null>(null);
  const [messageContents, setMessageContents] = useState<Record<string, string>>({});
  const [loadingContent, setLoadingContent] = useState<string | null>(null);
  const [dragState, setDragState] = useState<DragState>({ draggedThreadId: null, dragOverThreadId: null });
  const [mergeStatus, setMergeStatus] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [composing, setComposing] = useState<{
    replyTo: any;  // The message we're replying to
    replyAll: boolean;
    to: string;
    cc: string[];
    subject: string;
    content: string;
    threadId: string;
    // Scheduling options
    scheduleMode: 'now' | 'schedule' | 'reminder';
    sendAt: string;  // ISO datetime
    remindAfterMinutes: number;
  } | null>(null);
  const [sendingReply, setSendingReply] = useState(false);
  const threadMessagesRef = useRef<HTMLDivElement>(null);
  const mainRef = useRef<HTMLDivElement>(null);

  // Resizable split pane
  const [splitPercent, setSplitPercent] = useState(50);
  const [isResizing, setIsResizing] = useState(false);

  // Focus mode - hides parent headers
  const [focusMode, setFocusMode] = useState(false);

  // Filters and grouping
  const [filters, setFilters] = useState<FilterState>(() => {
    const saved = localStorage.getItem('agentmail-filters');
    return saved ? JSON.parse(saved) : { status: [], types: [], severity: [], agents: [], showArchived: false };
  });
  const [groupBy, setGroupBy] = useState<GroupBy>(() => {
    return (localStorage.getItem('agentmail-groupby') as GroupBy) || 'thread';
  });
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  // Persist filters to localStorage
  useEffect(() => {
    localStorage.setItem('agentmail-filters', JSON.stringify(filters));
  }, [filters]);

  useEffect(() => {
    localStorage.setItem('agentmail-groupby', groupBy);
  }, [groupBy]);

  // Toggle filter helper
  const toggleFilter = (category: keyof Omit<FilterState, 'showArchived'>, value: string) => {
    setFilters(prev => {
      const arr = prev[category];
      if (arr.includes(value)) {
        return { ...prev, [category]: arr.filter(v => v !== value) };
      }
      return { ...prev, [category]: [...arr, value] };
    });
  };

  const clearFilters = () => {
    setFilters({ status: [], types: [], severity: [], agents: [], showArchived: false });
  };

  // Toggle focus mode body class
  useEffect(() => {
    if (focusMode) {
      document.body.classList.add('oversight-focus-mode');
    } else {
      document.body.classList.remove('oversight-focus-mode');
    }
    return () => {
      document.body.classList.remove('oversight-focus-mode');
    };
  }, [focusMode]);

  // Group messages into threads
  const threads = useMemo(() => {
    const threadMap = new Map<string, any[]>();

    // Group by thread_id, or use message id as standalone thread
    messages.forEach(msg => {
      const threadKey = msg.thread_id || msg.id;
      if (!threadMap.has(threadKey)) {
        threadMap.set(threadKey, []);
      }
      threadMap.get(threadKey)!.push(msg);
    });

    // Convert to Thread objects
    const threadList: Thread[] = [];

    threadMap.forEach((msgs, threadId) => {
      // Sort messages chronologically within thread
      msgs.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

      const rootMessage = msgs[0];
      const latestMessage = msgs[msgs.length - 1];

      // Get unique participants (including CC'd agents)
      const participants = [...new Set(
        msgs.flatMap(m => [m.from_agent, m.to_agent, ...(m.cc || [])]).filter(Boolean)
      )];

      // Find worst severity in thread
      let worstSeverity: string | null = null;
      let worstPriority = 0;
      msgs.forEach(m => {
        if (m.severity) {
          const priority = SEVERITY_PRIORITY[m.severity.toUpperCase()] || 0;
          if (priority > worstPriority) {
            worstPriority = priority;
            worstSeverity = m.severity;
          }
        }
      });

      // Check status based on latest message (current state of the thread)
      const latestStatus = latestMessage.status || 'open';
      const hasOpen = latestStatus === 'open';
      const hasInProgress = latestStatus === 'in_progress';

      threadList.push({
        id: threadId,
        subject: rootMessage.subject,
        messages: msgs,
        participants,
        latestDate: latestMessage.date,
        latestMessage,
        rootMessage,
        worstSeverity,
        hasOpen,
        hasInProgress,
        type: rootMessage.type,
      });
    });

    // Sort threads by latest message date (newest first)
    threadList.sort((a, b) => new Date(b.latestDate).getTime() - new Date(a.latestDate).getTime());

    return threadList;
  }, [messages]);

  // Filter threads based on current filters
  const filteredThreads = useMemo(() => {
    return threads.filter(thread => {
      // Archive filter - check if any message in thread is archived
      const hasArchivedMessage = thread.messages.some(m => m.archived);
      if (hasArchivedMessage && !filters.showArchived) return false;

      // Status filter
      if (filters.status.length > 0) {
        const threadStatus = thread.hasOpen ? 'open' : thread.hasInProgress ? 'in_progress' : 'resolved';
        if (!filters.status.includes(threadStatus)) return false;
      }

      // Type filter
      if (filters.types.length > 0) {
        if (!filters.types.includes(thread.type)) return false;
      }

      // Severity filter
      if (filters.severity.length > 0) {
        if (!thread.worstSeverity || !filters.severity.includes(thread.worstSeverity.toUpperCase())) return false;
      }

      // Agent filter
      if (filters.agents.length > 0) {
        if (!thread.participants.some(p => filters.agents.includes(p))) return false;
      }

      return true;
    });
  }, [threads, filters]);

  // Group threads based on groupBy mode
  const groupedThreads = useMemo((): ThreadGroup[] => {
    // Helper to get thread status
    const getStatus = (thread: Thread): string => {
      if (thread.hasOpen) return 'open';
      if (thread.hasInProgress) return 'in_progress';
      return 'resolved';
    };

    if (groupBy === 'thread') {
      // Single group with all threads (no header)
      return [{
        key: 'all',
        label: '',
        count: filteredThreads.length,
        threads: filteredThreads,
      }];
    }

    if (groupBy === 'agent') {
      const groups = new Map<string, Thread[]>();
      filteredThreads.forEach(thread => {
        const agent = getPrimaryAgent(thread);
        if (!groups.has(agent)) groups.set(agent, []);
        groups.get(agent)!.push(thread);
      });

      return Array.from(groups.entries())
        .map(([agent, threads]) => ({
          key: agent,
          label: agent.replace('_agent', '').replace(/_/g, ' '),
          count: threads.length,
          threads,
        }))
        .sort((a, b) => b.count - a.count); // Most active first
    }

    if (groupBy === 'status') {
      const statusOrder = ['open', 'in_progress', 'resolved'];
      const statusLabels: Record<string, string> = {
        open: 'Open',
        in_progress: 'In Progress',
        resolved: 'Resolved',
      };

      const groups = new Map<string, Thread[]>();
      statusOrder.forEach(s => groups.set(s, []));

      filteredThreads.forEach(thread => {
        const status = getStatus(thread);
        groups.get(status)?.push(thread);
      });

      return statusOrder
        .map(status => ({
          key: status,
          label: statusLabels[status],
          count: groups.get(status)?.length || 0,
          threads: groups.get(status) || [],
        }))
        .filter(g => g.count > 0); // Hide empty sections
    }

    if (groupBy === 'time') {
      const groups = new Map<string, { threads: Thread[]; label: string; order: number }>();

      filteredThreads.forEach(thread => {
        const bucket = getTimeBucket(thread.latestDate);
        if (!groups.has(bucket.key)) {
          groups.set(bucket.key, { threads: [], label: bucket.label, order: bucket.order });
        }
        groups.get(bucket.key)!.threads.push(thread);
      });

      return Array.from(groups.entries())
        .sort((a, b) => a[1].order - b[1].order)
        .map(([key, { threads, label }]) => ({
          key,
          label,
          count: threads.length,
          threads,
        }));
    }

    return [];
  }, [filteredThreads, groupBy]);

  // Selected thread
  const selectedThread = useMemo(() => {
    return threads.find(t => t.id === selectedThreadId) ?? null;
  }, [threads, selectedThreadId]);

  // Archive a message
  const archiveMessage = async (messageId: string, archived: boolean = true) => {
    try {
      const response = await fetch(`${API_BASE}/messages/archive`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_id: messageId, archived }),
      });
      if (response.ok) {
        // Optimistically update store
        useAgentMailStore.getState().archiveMessage(messageId, archived);
      }
    } catch (error) {
      console.error('Failed to archive message:', error);
    }
  };

  // Archive all messages in a thread
  const archiveThread = async (thread: Thread) => {
    for (const msg of thread.messages) {
      await archiveMessage(msg.id, true);
    }
    setMergeStatus({ message: `Archived thread "${thread.subject}"`, type: 'success' });
    setTimeout(() => setMergeStatus(null), 3000);
    onRequestSync();
  };

  // Update message status
  const updateMessageStatus = async (messageId: string, newStatus: string) => {
    try {
      const response = await fetch(`${API_BASE}/messages/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_id: messageId, status: newStatus }),
      });
      if (response.ok) {
        // Optimistically update store
        useAgentMailStore.getState().updateMessageStatus(messageId, newStatus as any);
        setMergeStatus({ message: `Status updated to "${newStatus}"`, type: 'success' });
        setTimeout(() => setMergeStatus(null), 2000);
      }
    } catch (error) {
      console.error('Failed to update status:', error);
      setMergeStatus({ message: 'Failed to update status', type: 'error' });
      setTimeout(() => setMergeStatus(null), 3000);
    }
  };

  // Load message content when expanded
  const loadMessageContent = async (messageId: string) => {
    if (messageContents[messageId]) return;

    setLoadingContent(messageId);
    try {
      const res = await fetch(`${API_BASE}/messages/${messageId}?render=false`);
      const data = await res.json();
      setMessageContents(prev => ({
        ...prev,
        [messageId]: data.content || data.preview || 'No content'
      }));
    } catch (err) {
      console.error('Failed to load message:', err);
      setMessageContents(prev => ({
        ...prev,
        [messageId]: 'Failed to load message content'
      }));
    } finally {
      setLoadingContent(null);
    }
  };

  // Merge threads by making dragged thread a reply to target thread
  const mergeThreads = async (draggedId: string, targetId: string) => {
    const draggedThread = threads.find(t => t.id === draggedId);
    const targetThread = threads.find(t => t.id === targetId);

    if (!draggedThread || !targetThread) return;

    // Get the root message of the dragged thread - this will become a reply
    const draggedRootMsg = draggedThread.rootMessage;
    // Get the latest message of the target thread - this is what we're replying to
    const targetLatestMsg = targetThread.latestMessage;

    try {
      const res = await fetch(`${API_BASE}/messages/threading`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_id: draggedRootMsg.id,
          in_reply_to: targetLatestMsg.id,
          thread_id: targetThread.id,
        }),
      });

      if (!res.ok) {
        throw new Error('Failed to merge threads');
      }

      setMergeStatus({ message: `Merged "${draggedThread.subject}" into "${targetThread.subject}"`, type: 'success' });

      // Request a sync to refresh data
      onRequestSync();
    } catch (err) {
      console.error('Failed to merge threads:', err);
      setMergeStatus({ message: 'Failed to merge threads', type: 'error' });
    }

    // Clear status after 3 seconds
    setTimeout(() => setMergeStatus(null), 3000);
  };

  // Drag handlers
  const handleDragStart = (e: React.DragEvent, threadId: string) => {
    e.dataTransfer.setData('text/plain', threadId);
    e.dataTransfer.effectAllowed = 'move';
    setDragState({ draggedThreadId: threadId, dragOverThreadId: null });
  };

  const handleDragOver = (e: React.DragEvent, threadId: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (dragState.draggedThreadId !== threadId) {
      setDragState(prev => ({ ...prev, dragOverThreadId: threadId }));
    }
  };

  const handleDragLeave = () => {
    setDragState(prev => ({ ...prev, dragOverThreadId: null }));
  };

  const handleDrop = (e: React.DragEvent, targetThreadId: string) => {
    e.preventDefault();
    const draggedId = e.dataTransfer.getData('text/plain');

    if (draggedId && draggedId !== targetThreadId) {
      mergeThreads(draggedId, targetThreadId);
    }

    setDragState({ draggedThreadId: null, dragOverThreadId: null });
  };

  const handleDragEnd = () => {
    setDragState({ draggedThreadId: null, dragOverThreadId: null });
  };

  // Start composing a reply
  const startReply = (msg: any, replyAll: boolean = false) => {
    const threadId = msg.thread_id || msg.id;
    const subject = msg.subject.startsWith('Re: ') ? msg.subject : `Re: ${msg.subject}`;

    if (replyAll) {
      // Reply-all: send to original sender, CC everyone else
      const allParticipants = new Set<string>();
      allParticipants.add(msg.from_agent);
      allParticipants.add(msg.to_agent);
      if (msg.cc) msg.cc.forEach((a: string) => allParticipants.add(a));

      // Remove coordinator (us) from recipients
      allParticipants.delete('coordinator');

      const participantList = Array.from(allParticipants);
      const to = msg.from_agent === 'coordinator' ? msg.to_agent : msg.from_agent;
      const cc = participantList.filter(p => p !== to);

      setComposing({
        replyTo: msg,
        replyAll: true,
        to,
        cc,
        subject,
        content: '',
        threadId,
        scheduleMode: 'now',
        sendAt: '',
        remindAfterMinutes: 60,
      });
    } else {
      // Simple reply: just to the sender
      setComposing({
        replyTo: msg,
        replyAll: false,
        to: msg.from_agent === 'coordinator' ? msg.to_agent : msg.from_agent,
        cc: [],
        subject,
        content: '',
        threadId,
        scheduleMode: 'now',
        sendAt: '',
        remindAfterMinutes: 60,
      });
    }
  };

  // Send or schedule the reply
  const sendReply = async () => {
    if (!composing) return;

    setSendingReply(true);
    try {
      // Determine endpoint and payload based on schedule mode
      const isScheduled = composing.scheduleMode !== 'now';
      const endpoint = isScheduled ? `${API_BASE}/schedule` : `${API_BASE}/send`;

      const basePayload = {
        from_agent: 'coordinator',
        to_agent: composing.to,
        cc: composing.cc.length > 0 ? composing.cc : undefined,
        subject: composing.subject,
        message_type: 'response',
        content: composing.content,
        in_reply_to: composing.replyTo.id,
        thread_id: composing.threadId,
      };

      // Add scheduling options if scheduled
      const payload = isScheduled
        ? {
            ...basePayload,
            send_at: composing.scheduleMode === 'schedule' ? composing.sendAt : undefined,
            remind_after_minutes: composing.scheduleMode === 'reminder' ? composing.remindAfterMinutes : undefined,
          }
        : basePayload;

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(isScheduled ? 'Failed to schedule reply' : 'Failed to send reply');
      }

      setComposing(null);
      const successMsg = isScheduled
        ? composing.scheduleMode === 'schedule'
          ? `Reply scheduled for ${new Date(composing.sendAt).toLocaleString()}`
          : `Reminder set for ${composing.remindAfterMinutes} minutes if no response`
        : 'Reply sent successfully';
      setMergeStatus({ message: successMsg, type: 'success' });
      onRequestSync();

      // Clear status after 3 seconds
      setTimeout(() => setMergeStatus(null), 3000);
    } catch (err) {
      console.error('Failed to send/schedule reply:', err);
      setMergeStatus({ message: 'Failed to send reply', type: 'error' });
      setTimeout(() => setMergeStatus(null), 3000);
    } finally {
      setSendingReply(false);
    }
  };

  // Auto-expand latest message when thread selected and scroll to bottom
  useEffect(() => {
    // Clear cached content when switching threads
    setMessageContents({});

    if (selectedThread && selectedThread.messages.length > 0) {
      const lastMsg = selectedThread.messages[selectedThread.messages.length - 1];
      setExpandedMessageId(lastMsg.id);
      loadMessageContent(lastMsg.id);

      // Scroll to bottom after render
      setTimeout(() => {
        if (threadMessagesRef.current) {
          threadMessagesRef.current.scrollTop = threadMessagesRef.current.scrollHeight;
        }
      }, 0);
    }
  }, [selectedThreadId]);

  // Resize handlers for split pane
  const handleResizeStart = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  };

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!mainRef.current) return;
      const rect = mainRef.current.getBoundingClientRect();
      const percent = ((e.clientX - rect.left) / rect.width) * 100;
      // Clamp between 25% and 75%
      setSplitPercent(Math.min(75, Math.max(25, percent)));
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  // Stats
  const onlineCount = agents.filter(a => a.is_online).length;
  const openThreads = threads.filter(t => t.hasOpen).length;
  const inProgressThreads = threads.filter(t => t.hasInProgress).length;

  // Get thread status (based on latest message)
  const getThreadStatus = (thread: Thread) => {
    return thread.latestMessage?.status || 'open';
  };

  return (
    <div className="oversight-dashboard">
      {/* Header */}
      <header className="oversight-header">
        <div className="oversight-title">
          <h1>MANAGER'S INBOX</h1>
          <span className="oversight-subtitle">{onlineCount} agents online</span>
        </div>
        <div className="oversight-stats">
          <span className="stat-badge open">{openThreads} open</span>
          <span className="stat-badge in-progress">{inProgressThreads} in progress</span>
          <span className="stat-badge total">{threads.length} threads</span>
        </div>
        <div className="oversight-status">
          <span className={`oversight-live-indicator ${isConnected ? 'connected' : ''}`}>
            <span className="live-dot" />
            {isConnected ? 'LIVE' : 'OFFLINE'}
          </span>
          <button className="oversight-sync-btn" onClick={onRequestSync} title="Sync">
            ↻
          </button>
          <button
            className={`oversight-focus-btn ${focusMode ? 'active' : ''}`}
            onClick={() => setFocusMode(!focusMode)}
            title={focusMode ? 'Exit Focus Mode' : 'Focus Mode'}
          >
            {focusMode ? '⊙' : '⛶'}
          </button>
        </div>
      </header>

      {/* Filter & Grouping Bar */}
      <div className="filter-bar">
        <div className="filter-section">
          <span className="filter-label">Filter:</span>
          <button
            className={`filter-chip ${filters.status.length === 0 && filters.types.length === 0 && filters.severity.length === 0 ? 'active' : ''}`}
            onClick={clearFilters}
          >
            All
          </button>
          <button
            className={`filter-chip ${filters.status.includes('open') ? 'active' : ''}`}
            onClick={() => toggleFilter('status', 'open')}
          >
            Open <span className="filter-count">{threads.filter(t => t.hasOpen).length}</span>
          </button>
          <button
            className={`filter-chip ${filters.status.includes('in_progress') ? 'active' : ''}`}
            onClick={() => toggleFilter('status', 'in_progress')}
          >
            In Progress <span className="filter-count">{threads.filter(t => t.hasInProgress && !t.hasOpen).length}</span>
          </button>
          <button
            className={`filter-chip ${filters.status.includes('resolved') ? 'active' : ''}`}
            onClick={() => toggleFilter('status', 'resolved')}
          >
            Resolved <span className="filter-count">{threads.filter(t => !t.hasOpen && !t.hasInProgress).length}</span>
          </button>
          <button
            className={`filter-chip ${filters.severity.includes('BLOCKING') ? 'active' : ''}`}
            onClick={() => toggleFilter('severity', 'BLOCKING')}
          >
            Blocking <span className="filter-count">{threads.filter(t => t.worstSeverity === 'BLOCKING').length}</span>
          </button>
          <span className="filter-divider">|</span>
          <button
            className={`filter-chip ${filters.types.includes('bug') ? 'active' : ''}`}
            onClick={() => toggleFilter('types', 'bug')}
          >
            Bug
          </button>
          <button
            className={`filter-chip ${filters.types.includes('task') ? 'active' : ''}`}
            onClick={() => toggleFilter('types', 'task')}
          >
            Task
          </button>
          <button
            className={`filter-chip ${filters.types.includes('question') ? 'active' : ''}`}
            onClick={() => toggleFilter('types', 'question')}
          >
            Question
          </button>
          <span className="filter-divider">|</span>
          <label className="filter-checkbox">
            <input
              type="checkbox"
              checked={filters.showArchived}
              onChange={(e) => setFilters(prev => ({ ...prev, showArchived: e.target.checked }))}
            />
            Archived <span className="filter-count">{data?.stats?.archived_count ?? 0}</span>
          </label>
        </div>
        <div className="grouping-section">
          <span className="filter-label">Group:</span>
          {(['thread', 'agent', 'status', 'time'] as GroupBy[]).map(mode => (
            <button
              key={mode}
              className={`filter-chip ${groupBy === mode ? 'active' : ''}`}
              onClick={() => setGroupBy(mode)}
            >
              {mode.charAt(0).toUpperCase() + mode.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Main Layout */}
      <div className={`oversight-main ${isResizing ? 'resizing' : ''}`} ref={mainRef}>
        {/* Thread List */}
        <div className="message-list" style={{ width: `${splitPercent}%` }}>
          {/* Merge status toast */}
          {mergeStatus && (
            <div className={`merge-toast ${mergeStatus.type}`}>
              {mergeStatus.message}
            </div>
          )}

          {filteredThreads.length === 0 ? (
            <div className="empty-state">{threads.length === 0 ? 'No messages' : 'No matches for current filters'}</div>
          ) : (
            groupedThreads.map(group => (
              <div key={group.key} className="thread-group">
                {/* Section header - only show for non-thread grouping */}
                {groupBy !== 'thread' && group.label && (
                  <div
                    className={`thread-group-header ${groupBy === 'status' ? `status-${group.key}` : ''} ${collapsedGroups.has(group.key) ? 'collapsed' : ''}`}
                    onClick={() => {
                      setCollapsedGroups(prev => {
                        const next = new Set(prev);
                        if (next.has(group.key)) {
                          next.delete(group.key);
                        } else {
                          next.add(group.key);
                        }
                        return next;
                      });
                    }}
                  >
                    <span className="thread-group-chevron">
                      {collapsedGroups.has(group.key) ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
                    </span>
                    <span className="thread-group-label">{group.label}</span>
                    <span className="thread-group-count">{group.count}</span>
                  </div>
                )}
                {/* Thread rows within group - hide if collapsed */}
                {!collapsedGroups.has(group.key) && group.threads.map(thread => (
                  <div
                    key={thread.id}
                    className={`message-row ${getThreadStatus(thread)} ${selectedThreadId === thread.id ? 'selected' : ''} ${dragState.draggedThreadId === thread.id ? 'dragging' : ''} ${dragState.dragOverThreadId === thread.id ? 'drag-over' : ''}`}
                    onClick={() => setSelectedThreadId(thread.id)}
                    onDragOver={(e) => handleDragOver(e, thread.id)}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => handleDrop(e, thread.id)}
                  >
                    <div
                      className="drag-handle"
                      draggable
                      onDragStart={(e) => handleDragStart(e, thread.id)}
                      onDragEnd={handleDragEnd}
                      title="Drag to merge into another thread"
                    >
                      <span className="grip-line" />
                      <span className="grip-line" />
                      <span className="grip-line" />
                    </div>
                    <div className="message-status-col">
                      <span className={`status-dot ${getThreadStatus(thread)}`} title={getThreadStatus(thread)} />
                    </div>
                    <div className="message-agents-col">
                      {thread.participants.slice(0, 3).map((agent, i) => (
                        <span
                          key={agent}
                          className="agent-badge"
                          style={{
                            background: getAgentColor(agent),
                            marginLeft: i > 0 ? '-4px' : 0,
                            zIndex: 3 - i,
                          }}
                          title={agent}
                        >
                          {getAgentAbbrev(agent)}
                        </span>
                      ))}
                      {thread.participants.length > 3 && (
                        <span className="agent-badge more">+{thread.participants.length - 3}</span>
                      )}
                    </div>
                    <div className="message-content-col">
                      <span className="message-subject">{thread.subject}</span>
                      <span className="message-preview">
                        {thread.latestMessage.from_agent.replace('_agent', '')}: {thread.latestMessage.preview || thread.latestMessage.subject}
                      </span>
                    </div>
                    <div className="message-meta-col">
                      {thread.messages.length > 1 && (
                        <span className="thread-msg-count" title={`${thread.messages.length} messages`}>
                          {thread.messages.length}
                        </span>
                      )}
                      {thread.worstSeverity && (
                        <span className={`severity-badge ${thread.worstSeverity.toLowerCase()}`}>
                          {thread.worstSeverity}
                        </span>
                      )}
                      <span className={`latest-status ${thread.latestMessage.status || 'open'}`}>
                        {thread.latestMessage.status || 'open'}
                      </span>
                      <span className="message-time">{formatTime(thread.latestDate)}</span>
                      <button
                        className="archive-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          archiveThread(thread);
                        }}
                        title="Archive thread"
                      >
                        <Archive size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>

        {/* Resize Divider */}
        <div
          className="resize-divider"
          onMouseDown={handleResizeStart}
        />

        {/* Thread Detail Pane */}
        <div className={`message-detail ${selectedThread ? 'has-message' : ''}`} style={{ width: `${100 - splitPercent}%` }}>
          {!selectedThread ? (
            <div className="empty-state">Select a thread to view</div>
          ) : (
            <>
              <div className="detail-header">
                <h2>{selectedThread.subject}</h2>
                <div className="detail-meta">
                  <span className="thread-info">
                    {selectedThread.messages.length} message{selectedThread.messages.length !== 1 ? 's' : ''}
                  </span>
                  <span className={`status-badge ${getThreadStatus(selectedThread)}`}>
                    {getThreadStatus(selectedThread)}
                  </span>
                  {selectedThread.worstSeverity && (
                    <span className={`severity-badge ${selectedThread.worstSeverity.toLowerCase()}`}>
                      {selectedThread.worstSeverity}
                    </span>
                  )}
                  <button
                    className="archive-thread-btn"
                    onClick={() => archiveThread(selectedThread)}
                    title="Archive entire thread"
                  >
                    <Archive size={14} /> Archive Thread
                  </button>
                </div>
                {/* Thread Participants with Acknowledgment Status */}
                <div className="thread-participants-grid">
                  {(() => {
                    // Collect all acknowledged_by across thread messages
                    const allAcks: Record<string, string> = {};
                    selectedThread.messages.forEach(msg => {
                      if (msg.acknowledged_by) {
                        Object.entries(msg.acknowledged_by).forEach(([agent, time]) => {
                          const timeStr = time as string;
                          if (!allAcks[agent] || timeStr > allAcks[agent]) {
                            allAcks[agent] = timeStr;
                          }
                        });
                      }
                    });

                    // Categorize participants
                    const toAgents = new Set<string>();
                    const ccAgents = new Set<string>();
                    const mentionedAgents = new Set<string>();

                    selectedThread.messages.forEach(msg => {
                      toAgents.add(msg.to_agent);
                      toAgents.add(msg.from_agent);
                      if (msg.cc) msg.cc.forEach((a: string) => ccAgents.add(a));
                      if (msg.mentions) msg.mentions.forEach((a: string) => mentionedAgents.add(a));
                    });

                    // Remove from CC/mentions if they're a direct participant
                    toAgents.forEach(a => {
                      ccAgents.delete(a);
                      mentionedAgents.delete(a);
                    });
                    ccAgents.forEach(a => mentionedAgents.delete(a));

                    const renderParticipant = (agent: string, role: 'to' | 'cc' | 'mention') => {
                      const hasAcked = agent in allAcks;
                      const ackTime = allAcks[agent];
                      return (
                        <div
                          key={agent}
                          className={`participant-chip ${role} ${hasAcked ? 'acked' : ''}`}
                          title={hasAcked ? `Acknowledged: ${ackTime}` : 'Not yet acknowledged'}
                        >
                          <span
                            className="participant-avatar"
                            style={{ background: getAgentColor(agent) }}
                          >
                            {getAgentAbbrev(agent)}
                          </span>
                          <span className="participant-name">
                            {agent.replace('_agent', '')}
                          </span>
                          {role === 'cc' && <span className="participant-role">cc</span>}
                          {role === 'mention' && <span className="participant-role">@</span>}
                          <span className={`participant-ack ${hasAcked ? 'yes' : 'no'}`}>
                            {hasAcked ? '✓' : '○'}
                          </span>
                        </div>
                      );
                    };

                    return (
                      <>
                        {Array.from(toAgents).map(a => renderParticipant(a, 'to'))}
                        {Array.from(ccAgents).map(a => renderParticipant(a, 'cc'))}
                        {Array.from(mentionedAgents).map(a => renderParticipant(a, 'mention'))}
                      </>
                    );
                  })()}
                </div>
              </div>
              <div className="thread-messages" ref={threadMessagesRef}>
                {selectedThread.messages.map((msg, index) => (
                  <div
                    key={msg.id}
                    className={`thread-message ${expandedMessageId === msg.id ? 'expanded' : ''}`}
                  >
                    <div
                      className="thread-message-header"
                      onClick={() => {
                        if (expandedMessageId === msg.id) {
                          setExpandedMessageId(null);
                        } else {
                          setExpandedMessageId(msg.id);
                          loadMessageContent(msg.id);
                        }
                      }}
                    >
                      <span
                        className="thread-message-sender"
                        style={{ color: getAgentColor(msg.from_agent) }}
                      >
                        {msg.from_agent.replace('_agent', '')}
                      </span>
                      <span className="thread-message-arrow">→</span>
                      <span
                        className="thread-message-recipient"
                        style={{ color: getAgentColor(msg.to_agent) }}
                      >
                        {msg.to_agent.replace('_agent', '')}
                      </span>
                      {/* Only show these when collapsed - chrome shows them when expanded */}
                      {expandedMessageId !== msg.id && (
                        <>
                          {msg.cc && msg.cc.length > 0 && (
                            <span className="thread-message-cc">
                              <span className="cc-label">+{msg.cc.length}</span>
                            </span>
                          )}
                          <span className={`thread-message-status ${msg.status || 'open'}`}>
                            {msg.status || 'open'}
                          </span>
                          <span className="thread-message-date">{formatFullDate(msg.date)}</span>
                        </>
                      )}
                      <span className="thread-message-expand">
                        {expandedMessageId === msg.id ? '▼' : '▶'}
                      </span>
                    </div>
                    {expandedMessageId === msg.id && (
                      <div className="thread-message-expanded">
                        {/* Email Header Chrome */}
                        <div className="email-header-chrome">
                          <div className="email-header-main">
                            <div
                              className="email-sender-avatar"
                              style={{ background: getAgentColor(msg.from_agent) }}
                            >
                              {getAgentAbbrev(msg.from_agent)}
                            </div>
                            <div className="email-header-details">
                              <span className="email-header-subject">{msg.subject}</span>
                              <span className="email-header-row email-header-from">
                                <span
                                  className="email-header-value"
                                  style={{ color: getAgentColor(msg.from_agent) }}
                                >
                                  {msg.from_agent.replace('_agent', '')}
                                </span>
                                <span className="email-header-arrow">→</span>
                                <span
                                  className="email-header-value"
                                  style={{ color: getAgentColor(msg.to_agent) }}
                                >
                                  {msg.to_agent.replace('_agent', '')}
                                </span>
                              </span>
                              {msg.cc && msg.cc.length > 0 && (
                                <span className="email-header-row">
                                  <span className="email-header-label">cc</span>
                                  <span className="email-header-value">
                                    {msg.cc.map((agent: string, i: number) => (
                                      <span key={agent}>
                                        {i > 0 && ', '}
                                        <span style={{ color: getAgentColor(agent) }}>
                                          {agent.replace('_agent', '')}
                                        </span>
                                      </span>
                                    ))}
                                  </span>
                                </span>
                              )}
                              {msg.mentions && msg.mentions.length > 0 && (
                                <span className="email-header-row">
                                  <span className="email-header-label">@</span>
                                  <span className="email-header-value">
                                    {msg.mentions.map((agent: string, i: number) => (
                                      <span key={agent}>
                                        {i > 0 && ', '}
                                        <span style={{ color: getAgentColor(agent) }}>
                                          {agent.replace('_agent', '')}
                                        </span>
                                      </span>
                                    ))}
                                  </span>
                                </span>
                              )}
                              {msg.thread_id && (
                                <span className="email-header-thread">
                                  <span className="email-thread-label">thread</span>
                                  <span className="email-thread-id">{msg.thread_id}</span>
                                </span>
                              )}
                              <span className="email-header-date">{formatFullDate(msg.date)}</span>
                            </div>
                            <div className="email-header-badges">
                              <span className={`email-type-badge ${msg.type}`}>
                                {msg.type}
                              </span>
                              {msg.severity && (
                                <span className={`email-severity-badge ${msg.severity.toLowerCase()}`}>
                                  {msg.severity}
                                </span>
                              )}
                              <span className={`email-status-badge ${msg.status || 'open'}`}>
                                {msg.status || 'open'}
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Email Body */}
                        <div className="email-body-content">
                          {loadingContent === msg.id ? (
                            <div className="loading">Loading...</div>
                          ) : (
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              rehypePlugins={[rehypeRaw]}
                            >
                              {highlightMentions(stripEmailHeader(messageContents[msg.id] || msg.preview || ''))}
                            </ReactMarkdown>
                          )}
                        </div>

                        {/* Actions */}
                        <div className="email-actions">
                          <button
                            className="email-action-btn reply"
                            onClick={(e) => { e.stopPropagation(); startReply(msg, false); }}
                          >
                            <span className="action-icon">↩</span> Reply
                          </button>
                          <button
                            className="email-action-btn reply-all"
                            onClick={(e) => { e.stopPropagation(); startReply(msg, true); }}
                          >
                            <span className="action-icon">↩↩</span> Reply All
                          </button>
                          <span className="action-divider" />
                          <div className="status-buttons">
                            {(['open', 'in_progress', 'resolved'] as const).map(status => (
                              <button
                                key={status}
                                className={`status-btn ${status} ${(msg.status || 'open') === status ? 'active' : ''}`}
                                onClick={(e) => { e.stopPropagation(); updateMessageStatus(msg.id, status); }}
                                title={`Mark as ${status.replace('_', ' ')}`}
                              >
                                {status === 'open' ? '○' : status === 'in_progress' ? '◐' : '●'}
                              </button>
                            ))}
                          </div>
                          <span className="action-divider" />
                          <button
                            className="email-action-btn archive"
                            onClick={(e) => { e.stopPropagation(); archiveMessage(msg.id, !msg.archived); }}
                            title={msg.archived ? 'Unarchive' : 'Archive'}
                          >
                            <Archive size={14} /> {msg.archived ? 'Unarchive' : 'Archive'}
                          </button>
                        </div>
                      </div>
                    )}
                    {index < selectedThread.messages.length - 1 && (
                      <div className="thread-connector" />
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Reply Compose Modal */}
      {composing && (
        <div className="reply-modal-overlay" onClick={() => setComposing(null)}>
          <div className="reply-modal" onClick={(e) => e.stopPropagation()}>
            <div className="reply-modal-header">
              <h3>{composing.replyAll ? 'Reply All' : 'Reply'}</h3>
              <button className="reply-modal-close" onClick={() => setComposing(null)}>×</button>
            </div>

            <div className="reply-modal-meta">
              <div className="reply-meta-row">
                <span className="reply-meta-label">To:</span>
                <span className="reply-meta-value" style={{ color: getAgentColor(composing.to) }}>
                  {composing.to.replace('_agent', '')}
                </span>
              </div>
              {composing.cc.length > 0 && (
                <div className="reply-meta-row">
                  <span className="reply-meta-label">CC:</span>
                  <span className="reply-meta-value">
                    {composing.cc.map((agent, i) => (
                      <span key={agent}>
                        {i > 0 && ', '}
                        <span style={{ color: getAgentColor(agent) }}>
                          {agent.replace('_agent', '')}
                        </span>
                      </span>
                    ))}
                  </span>
                </div>
              )}
              <div className="reply-meta-row">
                <span className="reply-meta-label">Subject:</span>
                <span className="reply-meta-value">{composing.subject}</span>
              </div>
              <div className="reply-meta-row">
                <span className="reply-meta-label">Thread:</span>
                <span className="reply-meta-value reply-thread-id">{composing.threadId}</span>
              </div>
            </div>

            <div className="reply-quote">
              <div className="reply-quote-header">
                Replying to {composing.replyTo.from_agent.replace('_agent', '')}:
              </div>
              <div className="reply-quote-preview">
                {composing.replyTo.preview || composing.replyTo.subject}
              </div>
            </div>

            <textarea
              className="reply-textarea"
              placeholder="Write your reply... (Markdown supported, use @agent_name to mention)"
              value={composing.content}
              onChange={(e) => setComposing({ ...composing, content: e.target.value })}
              autoFocus
            />

            {/* Scheduling Options */}
            <div className="schedule-options">
              <div className="schedule-mode-selector">
                <button
                  className={`schedule-mode-btn ${composing.scheduleMode === 'now' ? 'active' : ''}`}
                  onClick={() => setComposing({ ...composing, scheduleMode: 'now' })}
                >
                  Send Now
                </button>
                <button
                  className={`schedule-mode-btn ${composing.scheduleMode === 'schedule' ? 'active' : ''}`}
                  onClick={() => setComposing({ ...composing, scheduleMode: 'schedule' })}
                >
                  Schedule
                </button>
                <button
                  className={`schedule-mode-btn ${composing.scheduleMode === 'reminder' ? 'active' : ''}`}
                  onClick={() => setComposing({ ...composing, scheduleMode: 'reminder' })}
                >
                  Reminder
                </button>
              </div>

              {composing.scheduleMode === 'schedule' && (
                <div className="schedule-input-row">
                  <label>Send at:</label>
                  <input
                    type="datetime-local"
                    className="schedule-datetime"
                    value={composing.sendAt}
                    onChange={(e) => setComposing({ ...composing, sendAt: e.target.value })}
                  />
                </div>
              )}

              {composing.scheduleMode === 'reminder' && (
                <div className="schedule-input-row">
                  <label>Remind after:</label>
                  <select
                    className="schedule-select"
                    value={composing.remindAfterMinutes}
                    onChange={(e) => setComposing({ ...composing, remindAfterMinutes: parseInt(e.target.value) })}
                  >
                    <option value={30}>30 minutes</option>
                    <option value={60}>1 hour</option>
                    <option value={120}>2 hours</option>
                    <option value={240}>4 hours</option>
                    <option value={480}>8 hours</option>
                    <option value={1440}>24 hours</option>
                  </select>
                  <span className="schedule-hint">if no response</span>
                </div>
              )}
            </div>

            <div className="reply-modal-actions">
              <button
                className="reply-cancel-btn"
                onClick={() => setComposing(null)}
                disabled={sendingReply}
              >
                Cancel
              </button>
              <button
                className="reply-send-btn"
                onClick={sendReply}
                disabled={
                  !composing.content.trim() ||
                  sendingReply ||
                  (composing.scheduleMode === 'schedule' && !composing.sendAt)
                }
              >
                {sendingReply
                  ? 'Sending...'
                  : composing.scheduleMode === 'now'
                    ? 'Send Reply'
                    : composing.scheduleMode === 'schedule'
                      ? 'Schedule'
                      : 'Set Reminder'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default OversightDashboard;
