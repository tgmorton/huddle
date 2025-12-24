/**
 * Zustand store for AgentMail dashboard state
 */

import { create } from 'zustand';

// Types (matching backend models)
export interface AgentInfo {
  name: string;
  display_name: string;
  role: string;
  last_active: string;
  last_heartbeat?: string;
  is_online: boolean;
  inbox_count: number;
}

export interface AgentStatusItem {
  component: string;
  location: string;
  notes?: string;
}

export interface AgentStatus {
  name: string;
  role: string;
  last_updated: string;
  complete: AgentStatusItem[];
  in_progress: AgentStatusItem[];
  next_up: string[];
}

export interface FileReference {
  path: string;
  lines?: number[];
}

export interface AgentMailMessage {
  id: string;
  from_agent: string;
  to_agent: string;
  cc?: string[];  // CC recipients
  mentions?: string[];  // Agents mentioned with @ in body
  subject: string;
  type: string;
  severity?: string;
  status?: 'open' | 'in_progress' | 'resolved' | 'closed';
  date: string;
  preview?: string;
  filename: string;
  in_reply_to?: string;
  thread_id?: string;
  acknowledged_at?: string;
  acknowledged_by?: Record<string, string>;  // {agent_name: ISO timestamp}
  file_references?: FileReference[];
  blocked_by?: string[];
  blocks?: string[];
  // Archive
  archived?: boolean;
  archived_at?: string;
}

export interface AgentNote {
  id: string;
  filename: string;
  agent_name: string;
  title: string;
  date: string;
  tags: string[];
  domain?: string;
  content?: string;
}

export interface DashboardStats {
  total_agents: number;
  total_messages: number;
  bugs: number;
  blocking_bugs: number;
  archived_count: number;
  open_count: number;
  in_progress_count: number;
  resolved_count: number;
  closed_count: number;
}

export interface DashboardData {
  stats: DashboardStats;
  agents: AgentInfo[];
  agent_statuses: AgentStatus[];
  messages: AgentMailMessage[];
}

// WebSocket message types
export type AgentMailWSMessageType =
  | 'state_sync'
  | 'message_added'
  | 'message_updated'
  | 'status_changed'
  | 'agent_online'
  | 'note_added'
  | 'note_updated'
  | 'error'
  | 'request_sync';

export interface AgentMailWSMessage {
  type: AgentMailWSMessageType;
  payload?: unknown;
  error_message?: string;
  error_code?: string;
}

interface AgentMailStore {
  // Connection state
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;

  // Dashboard data
  data: DashboardData | null;

  // Actions - Connection
  setConnected: (connected: boolean) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // Actions - Data updates
  setDashboardData: (data: DashboardData) => void;
  updateMessage: (message: AgentMailMessage) => void;
  addMessage: (message: AgentMailMessage) => void;
  updateAgentStatus: (agentName: string, status: Partial<AgentInfo>) => void;
  setAgentOnline: (agentName: string, isOnline: boolean) => void;

  // Actions - Local state updates (for optimistic UI)
  updateMessageStatus: (messageId: string, status: AgentMailMessage['status']) => void;
  updateMessageRouting: (messageId: string, field: 'from' | 'to', value: string) => void;
  archiveMessage: (messageId: string, archived: boolean) => void;

  // Actions - Clear
  clearStore: () => void;
}

export const useAgentMailStore = create<AgentMailStore>((set, get) => ({
  // Initial state
  isConnected: false,
  isLoading: false,
  error: null,
  data: null,

  // Actions - Connection
  setConnected: (connected) => set({ isConnected: connected }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),

  // Actions - Data updates
  setDashboardData: (data) => set({ data, error: null }),

  updateMessage: (message) => {
    const { data } = get();
    if (!data) return;

    set({
      data: {
        ...data,
        messages: data.messages.map((m) =>
          m.id === message.id ? message : m
        ),
      },
    });
  },

  addMessage: (message) => {
    const { data } = get();
    if (!data) return;

    // Check if message already exists
    if (data.messages.some((m) => m.id === message.id)) {
      // Update existing
      set({
        data: {
          ...data,
          messages: data.messages.map((m) =>
            m.id === message.id ? message : m
          ),
        },
      });
    } else {
      // Add new
      set({
        data: {
          ...data,
          messages: [message, ...data.messages],
          stats: {
            ...data.stats,
            total_messages: data.stats.total_messages + 1,
          },
        },
      });
    }
  },

  updateAgentStatus: (agentName, status) => {
    const { data } = get();
    if (!data) return;

    set({
      data: {
        ...data,
        agents: data.agents.map((a) =>
          a.name === agentName ? { ...a, ...status } : a
        ),
      },
    });
  },

  setAgentOnline: (agentName, isOnline) => {
    const { data } = get();
    if (!data) return;

    set({
      data: {
        ...data,
        agents: data.agents.map((a) =>
          a.name === agentName ? { ...a, is_online: isOnline } : a
        ),
      },
    });
  },

  // Optimistic UI updates
  updateMessageStatus: (messageId, status) => {
    const { data } = get();
    if (!data) return;

    set({
      data: {
        ...data,
        messages: data.messages.map((m) =>
          m.id === messageId ? { ...m, status } : m
        ),
      },
    });
  },

  updateMessageRouting: (messageId, field, value) => {
    const { data } = get();
    if (!data) return;

    const fieldKey = field === 'from' ? 'from_agent' : 'to_agent';
    set({
      data: {
        ...data,
        messages: data.messages.map((m) =>
          m.id === messageId ? { ...m, [fieldKey]: value } : m
        ),
      },
    });
  },

  archiveMessage: (messageId, archived) => {
    const { data } = get();
    if (!data) return;

    set({
      data: {
        ...data,
        messages: data.messages.map((m) =>
          m.id === messageId
            ? { ...m, archived, archived_at: archived ? new Date().toISOString() : undefined }
            : m
        ),
        stats: {
          ...data.stats,
          archived_count: data.stats.archived_count + (archived ? 1 : -1),
        },
      },
    });
  },

  // Clear
  clearStore: () =>
    set({
      data: null,
      isConnected: false,
      isLoading: false,
      error: null,
    }),
}));

// Selectors
export const selectStats = (state: AgentMailStore) => state.data?.stats;
export const selectAgents = (state: AgentMailStore) => state.data?.agents ?? [];
export const selectMessages = (state: AgentMailStore) => state.data?.messages ?? [];
export const selectAgentStatuses = (state: AgentMailStore) => state.data?.agent_statuses ?? [];

export const selectOpenMessages = (state: AgentMailStore) =>
  state.data?.messages.filter((m) => m.status === 'open') ?? [];

export const selectInProgressMessages = (state: AgentMailStore) =>
  state.data?.messages.filter((m) => m.status === 'in_progress') ?? [];

export const selectBlockingBugs = (state: AgentMailStore) =>
  state.data?.messages.filter(
    (m) => m.type === 'bug' && m.severity === 'BLOCKING' && m.status !== 'resolved' && m.status !== 'closed'
  ) ?? [];

export const selectOnlineAgents = (state: AgentMailStore) =>
  state.data?.agents.filter((a) => a.is_online) ?? [];
