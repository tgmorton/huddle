import React, { useState, useMemo } from 'react';
import './AgentMailDashboard.css';

// Types for the agentmail system
interface AgentStatus {
  name: string;
  displayName: string;
  role: string;
  lastUpdated: string;
  complete: StatusItem[];
  inProgress: StatusItem[];
  blocked: BlockedItem[];
  nextUp: string[];
  coordinationNotes: string[];
}

interface StatusItem {
  component: string;
  location: string;
  notes: string;
}

interface BlockedItem {
  issue: string;
  waitingOn: string;
  notes: string;
}

interface Message {
  id: string;
  filename: string;
  from: string;
  to: string;
  subject: string;
  date: string;
  severity?: 'BLOCKING' | 'MAJOR' | 'MINOR' | 'INFO';
  type: 'task' | 'response' | 'bug' | 'plan';
  preview: string;
}

interface TuningNote {
  id: string;
  filename: string;
  topic: string;
  date: string;
}

// Mock data - in production this would come from an API that reads the agentmail folder
const mockAgents: AgentStatus[] = [
  {
    name: 'live_sim_agent',
    displayName: 'Live Simulation',
    role: 'Core simulation systems, orchestrator, physics, run game',
    lastUpdated: '2025-12-17',
    complete: [
      { component: 'Core', location: 'core/vec2.py, entities.py, field.py', notes: 'All solid' },
      { component: 'Physics', location: 'physics/movement.py, spatial.py', notes: 'Movement solver, influence zones' },
      { component: 'Route Runner', location: 'systems/route_runner.py', notes: 'Full route execution with phases' },
      { component: 'Coverage', location: 'systems/coverage.py', notes: 'Man + zone coverage' },
      { component: 'Passing', location: 'systems/passing.py', notes: 'Ball flight, catch resolution' },
      { component: 'Orchestrator', location: 'orchestrator.py', notes: 'NEW - Main loop, WorldState' },
    ],
    inProgress: [],
    blocked: [],
    nextUp: [
      'Build tackle resolver so plays can end',
      'Build pursuit system for defenders',
      'Integrate with AI brains when ready',
    ],
    coordinationNotes: ['Behavior tree agent building ai/ layer', 'Interface: Brains receive WorldState, return BrainDecision'],
  },
  {
    name: 'qa_agent',
    displayName: 'QA Agent',
    role: 'Quality assurance, integration testing, bug finding',
    lastUpdated: '2025-12-18',
    complete: [
      { component: 'Agent specification', location: 'qa_agent/plans/', notes: 'Full spec from dev agent' },
    ],
    inProgress: [
      { component: 'Initial setup', location: '-', notes: 'Reading spec, preparing to test' },
    ],
    blocked: [],
    nextUp: [
      'Run test_passing_integration.py multi to baseline',
      'Investigate defense pursuit angle issue',
      'Check route running implementation',
      'Create test scenarios for edge cases',
    ],
    coordinationNotes: ['Working with: live_sim_agent (primary partner)'],
  },
  {
    name: 'researcher_agent',
    displayName: 'Researcher',
    role: 'Cross-domain research, cognitive science',
    lastUpdated: '2025-12-17',
    complete: [
      { component: 'Cognitive state model', location: 'researcher_agent/plans/', notes: 'Research complete' },
    ],
    inProgress: [],
    blocked: [],
    nextUp: ['Apply findings to player mental states'],
    coordinationNotes: [],
  },
  {
    name: 'management_agent',
    displayName: 'Management',
    role: 'Management systems (contracts, scouting, etc.)',
    lastUpdated: '2025-12-17',
    complete: [
      { component: 'Morale/confidence pipeline', location: 'management_agent/to/', notes: 'Spec ready' },
    ],
    inProgress: [
      { component: 'Scout cognitive biases', location: 'management_agent/to/', notes: 'In design' },
    ],
    blocked: [],
    nextUp: ['Inner weather core ownership'],
    coordinationNotes: [],
  },
  {
    name: 'behavior_tree_agent',
    displayName: 'Behavior Trees',
    role: 'AI brains for players (QB, ballcarrier, etc.)',
    lastUpdated: '2025-12-17',
    complete: [],
    inProgress: [],
    blocked: [],
    nextUp: ['Build QB brain', 'Build ballcarrier brain', 'Build DB brain'],
    coordinationNotes: ['Interface contract from live_sim_agent'],
  },
  {
    name: 'frontend_agent',
    displayName: 'Frontend',
    role: 'React/TypeScript UI',
    lastUpdated: 'Pending',
    complete: [],
    inProgress: [],
    blocked: [],
    nextUp: ['Inner weather UX design'],
    coordinationNotes: [],
  },
];

const mockMessages: Message[] = [
  {
    id: '1',
    filename: '001_bug_pursuit_never_triggers.md',
    from: 'qa_agent',
    to: 'live_sim_agent',
    subject: 'Defense Pursuit Never Triggers After Catch',
    date: '2025-12-18',
    severity: 'BLOCKING',
    type: 'bug',
    preview: 'After a receiver catches the ball, defenders never switch to pursuit mode. They continue targeting the receiver\'s current position...',
  },
  {
    id: '2',
    filename: '002_bug_route_waypoints_unused.md',
    from: 'qa_agent',
    to: 'live_sim_agent',
    subject: 'Route Waypoints Unused',
    date: '2025-12-18',
    severity: 'MAJOR',
    type: 'bug',
    preview: 'Route waypoints are defined but appear to be unused in route execution...',
  },
  {
    id: '3',
    filename: '001_interface_contract.md',
    from: 'live_sim_agent',
    to: 'behavior_tree_agent',
    subject: 'Interface Contract: WorldState ↔ BrainDecision',
    date: '2025-12-17',
    severity: 'INFO',
    type: 'plan',
    preview: 'Defines the interface between simulation orchestrator and AI brains...',
  },
  {
    id: '4',
    filename: '001_initial_testing_task.md',
    from: 'coordinator',
    to: 'qa_agent',
    subject: 'Initial Testing Task',
    date: '2025-12-18',
    severity: 'INFO',
    type: 'task',
    preview: 'Begin integration testing of v2 simulation systems...',
  },
];

const mockTuningNotes: TuningNote[] = [
  {
    id: '1',
    filename: '001_coverage_separation.md',
    topic: 'Coverage Separation',
    date: '2025-12-17',
  },
];

// Component
export const AgentMailDashboard: React.FC = () => {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'messages' | 'timeline'>('overview');
  const [messageFilter, setMessageFilter] = useState<'all' | 'bugs' | 'tasks' | 'plans'>('all');

  const stats = useMemo(() => {
    const totalComplete = mockAgents.reduce((sum, a) => sum + a.complete.length, 0);
    const totalInProgress = mockAgents.reduce((sum, a) => sum + a.inProgress.length, 0);
    const totalBlocked = mockAgents.reduce((sum, a) => sum + a.blocked.length, 0);
    const activeAgents = mockAgents.filter(a => a.lastUpdated !== 'Pending').length;
    const criticalBugs = mockMessages.filter(m => m.severity === 'BLOCKING').length;

    return { totalComplete, totalInProgress, totalBlocked, activeAgents, criticalBugs };
  }, []);

  const filteredMessages = useMemo(() => {
    if (messageFilter === 'all') return mockMessages;
    if (messageFilter === 'bugs') return mockMessages.filter(m => m.type === 'bug');
    if (messageFilter === 'tasks') return mockMessages.filter(m => m.type === 'task');
    if (messageFilter === 'plans') return mockMessages.filter(m => m.type === 'plan');
    return mockMessages;
  }, [messageFilter]);

  const getAgentColor = (name: string): string => {
    const colors: Record<string, string> = {
      live_sim_agent: '#f59e0b',
      qa_agent: '#ef4444',
      behavior_tree_agent: '#10b981',
      management_agent: '#6366f1',
      researcher_agent: '#8b5cf6',
      frontend_agent: '#ec4899',
      documentation_agent: '#06b6d4',
      data_generation_agent: '#84cc16',
      simulation_agent: '#f97316',
      narrative_agent: '#14b8a6',
    };
    return colors[name] || '#64748b';
  };

  const getStatusIndicator = (agent: AgentStatus) => {
    if (agent.blocked.length > 0) return 'blocked';
    if (agent.inProgress.length > 0) return 'active';
    if (agent.complete.length > 0) return 'idle';
    return 'pending';
  };

  const getSeverityClass = (severity?: string) => {
    switch (severity) {
      case 'BLOCKING': return 'severity-blocking';
      case 'MAJOR': return 'severity-major';
      case 'MINOR': return 'severity-minor';
      default: return 'severity-info';
    }
  };

  return (
    <div className="agentmail-dashboard">
      {/* Background grid effect */}
      <div className="dashboard-grid-bg" />

      {/* Header */}
      <header className="dashboard-header">
        <div className="header-left">
          <div className="logo-mark">
            <span className="logo-icon">◈</span>
            <span className="logo-text">AGENTMAIL</span>
          </div>
          <span className="header-subtitle">Multi-Agent Coordination Hub</span>
        </div>
        <div className="header-right">
          <div className="header-stat">
            <span className="stat-value">{stats.activeAgents}</span>
            <span className="stat-label">Active Agents</span>
          </div>
          <div className="header-stat warning">
            <span className="stat-value">{stats.criticalBugs}</span>
            <span className="stat-label">Critical Bugs</span>
          </div>
          <div className="live-indicator">
            <span className="pulse" />
            <span>LIVE</span>
          </div>
        </div>
      </header>

      {/* Navigation tabs */}
      <nav className="dashboard-nav">
        <button
          className={`nav-tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <span className="tab-icon">◫</span>
          Overview
        </button>
        <button
          className={`nav-tab ${activeTab === 'messages' ? 'active' : ''}`}
          onClick={() => setActiveTab('messages')}
        >
          <span className="tab-icon">✉</span>
          Messages
          <span className="tab-badge">{mockMessages.length}</span>
        </button>
        <button
          className={`nav-tab ${activeTab === 'timeline' ? 'active' : ''}`}
          onClick={() => setActiveTab('timeline')}
        >
          <span className="tab-icon">◷</span>
          Timeline
        </button>
      </nav>

      {/* Main content */}
      <main className="dashboard-main">
        {activeTab === 'overview' && (
          <div className="overview-layout">
            {/* Stats bar */}
            <div className="stats-bar">
              <div className="stat-card">
                <div className="stat-icon complete">✓</div>
                <div className="stat-content">
                  <span className="stat-number">{stats.totalComplete}</span>
                  <span className="stat-title">Complete</span>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon progress">◐</div>
                <div className="stat-content">
                  <span className="stat-number">{stats.totalInProgress}</span>
                  <span className="stat-title">In Progress</span>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon blocked">⊘</div>
                <div className="stat-content">
                  <span className="stat-number">{stats.totalBlocked}</span>
                  <span className="stat-title">Blocked</span>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon notes">📋</div>
                <div className="stat-content">
                  <span className="stat-number">{mockTuningNotes.length}</span>
                  <span className="stat-title">Tuning Notes</span>
                </div>
              </div>
            </div>

            {/* Agent grid */}
            <div className="agents-section">
              <h2 className="section-title">
                <span className="title-icon">◇</span>
                Agent Registry
              </h2>
              <div className="agents-grid">
                {mockAgents.map((agent) => (
                  <div
                    key={agent.name}
                    className={`agent-card ${selectedAgent === agent.name ? 'selected' : ''} status-${getStatusIndicator(agent)}`}
                    onClick={() => setSelectedAgent(selectedAgent === agent.name ? null : agent.name)}
                    style={{ '--agent-color': getAgentColor(agent.name) } as React.CSSProperties}
                  >
                    <div className="agent-header">
                      <div className="agent-indicator" />
                      <h3 className="agent-name">{agent.displayName}</h3>
                      <span className="agent-updated">{agent.lastUpdated}</span>
                    </div>
                    <p className="agent-role">{agent.role}</p>

                    <div className="agent-stats">
                      <div className="agent-stat">
                        <span className="count">{agent.complete.length}</span>
                        <span className="label">Done</span>
                      </div>
                      <div className="agent-stat">
                        <span className="count">{agent.inProgress.length}</span>
                        <span className="label">Active</span>
                      </div>
                      <div className="agent-stat">
                        <span className="count">{agent.nextUp.length}</span>
                        <span className="label">Next</span>
                      </div>
                    </div>

                    {selectedAgent === agent.name && (
                      <div className="agent-details">
                        {agent.complete.length > 0 && (
                          <div className="detail-section">
                            <h4>✓ Complete</h4>
                            <ul>
                              {agent.complete.map((item, i) => (
                                <li key={i}>
                                  <span className="item-name">{item.component}</span>
                                  <span className="item-location">{item.location}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {agent.inProgress.length > 0 && (
                          <div className="detail-section">
                            <h4>◐ In Progress</h4>
                            <ul>
                              {agent.inProgress.map((item, i) => (
                                <li key={i}>
                                  <span className="item-name">{item.component}</span>
                                  <span className="item-notes">{item.notes}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {agent.nextUp.length > 0 && (
                          <div className="detail-section">
                            <h4>→ Next Up</h4>
                            <ul>
                              {agent.nextUp.map((item, i) => (
                                <li key={i}>{item}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {agent.coordinationNotes.length > 0 && (
                          <div className="detail-section coordination">
                            <h4>⟷ Coordination</h4>
                            <ul>
                              {agent.coordinationNotes.map((note, i) => (
                                <li key={i}>{note}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Tuning notes */}
            <div className="tuning-section">
              <h2 className="section-title">
                <span className="title-icon">◇</span>
                Shared Tuning Notes
              </h2>
              <div className="tuning-list">
                {mockTuningNotes.map((note) => (
                  <div key={note.id} className="tuning-card">
                    <span className="tuning-id">{note.filename.split('_')[0]}</span>
                    <span className="tuning-topic">{note.topic}</span>
                    <span className="tuning-date">{note.date}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'messages' && (
          <div className="messages-layout">
            <div className="messages-filters">
              <button
                className={`filter-btn ${messageFilter === 'all' ? 'active' : ''}`}
                onClick={() => setMessageFilter('all')}
              >
                All
              </button>
              <button
                className={`filter-btn ${messageFilter === 'bugs' ? 'active' : ''}`}
                onClick={() => setMessageFilter('bugs')}
              >
                🐛 Bugs
              </button>
              <button
                className={`filter-btn ${messageFilter === 'tasks' ? 'active' : ''}`}
                onClick={() => setMessageFilter('tasks')}
              >
                📋 Tasks
              </button>
              <button
                className={`filter-btn ${messageFilter === 'plans' ? 'active' : ''}`}
                onClick={() => setMessageFilter('plans')}
              >
                📐 Plans
              </button>
            </div>

            <div className="messages-list">
              {filteredMessages.map((msg) => (
                <div key={msg.id} className={`message-card ${getSeverityClass(msg.severity)}`}>
                  <div className="message-header">
                    <div className="message-flow">
                      <span
                        className="flow-agent from"
                        style={{ '--agent-color': getAgentColor(msg.from) } as React.CSSProperties}
                      >
                        {msg.from.replace('_agent', '')}
                      </span>
                      <span className="flow-arrow">→</span>
                      <span
                        className="flow-agent to"
                        style={{ '--agent-color': getAgentColor(msg.to) } as React.CSSProperties}
                      >
                        {msg.to.replace('_agent', '')}
                      </span>
                    </div>
                    {msg.severity && (
                      <span className={`message-severity ${getSeverityClass(msg.severity)}`}>
                        {msg.severity}
                      </span>
                    )}
                    <span className="message-date">{msg.date}</span>
                  </div>
                  <h3 className="message-subject">{msg.subject}</h3>
                  <p className="message-preview">{msg.preview}</p>
                  <div className="message-footer">
                    <span className="message-file">{msg.filename}</span>
                    <button className="view-btn">View Full →</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'timeline' && (
          <div className="timeline-layout">
            <div className="timeline">
              <div className="timeline-item">
                <div className="timeline-marker" style={{ '--agent-color': '#ef4444' } as React.CSSProperties} />
                <div className="timeline-content">
                  <span className="timeline-time">Today 00:27</span>
                  <span className="timeline-agent">QA Agent</span>
                  <p className="timeline-event">Status updated - Initial setup in progress</p>
                </div>
              </div>
              <div className="timeline-item">
                <div className="timeline-marker" style={{ '--agent-color': '#ef4444' } as React.CSSProperties} />
                <div className="timeline-content">
                  <span className="timeline-time">Today 00:15</span>
                  <span className="timeline-agent">QA Agent</span>
                  <p className="timeline-event">Bug filed: Defense Pursuit Never Triggers (BLOCKING)</p>
                </div>
              </div>
              <div className="timeline-item">
                <div className="timeline-marker" style={{ '--agent-color': '#ef4444' } as React.CSSProperties} />
                <div className="timeline-content">
                  <span className="timeline-time">Today 00:10</span>
                  <span className="timeline-agent">QA Agent</span>
                  <p className="timeline-event">Bug filed: Route Waypoints Unused (MAJOR)</p>
                </div>
              </div>
              <div className="timeline-item">
                <div className="timeline-marker" style={{ '--agent-color': '#8b5cf6' } as React.CSSProperties} />
                <div className="timeline-content">
                  <span className="timeline-time">Dec 17 23:06</span>
                  <span className="timeline-agent">Researcher Agent</span>
                  <p className="timeline-event">Status updated - Cognitive state model research complete</p>
                </div>
              </div>
              <div className="timeline-item">
                <div className="timeline-marker" style={{ '--agent-color': '#6366f1' } as React.CSSProperties} />
                <div className="timeline-content">
                  <span className="timeline-time">Dec 17 23:06</span>
                  <span className="timeline-agent">Management Agent</span>
                  <p className="timeline-event">Status updated - Scout cognitive biases in progress</p>
                </div>
              </div>
              <div className="timeline-item">
                <div className="timeline-marker" style={{ '--agent-color': '#f59e0b' } as React.CSSProperties} />
                <div className="timeline-content">
                  <span className="timeline-time">Dec 17 22:45</span>
                  <span className="timeline-agent">Live Sim Agent</span>
                  <p className="timeline-event">Orchestrator complete - WorldState, BrainDecision interfaces ready</p>
                </div>
              </div>
              <div className="timeline-item">
                <div className="timeline-marker" style={{ '--agent-color': '#f59e0b' } as React.CSSProperties} />
                <div className="timeline-content">
                  <span className="timeline-time">Dec 17 22:39</span>
                  <span className="timeline-agent">Live Sim Agent</span>
                  <p className="timeline-event">Tuning note added: Coverage Separation</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="dashboard-footer">
        <div className="footer-left">
          <span className="footer-protocol">Agentmail Protocol v1.0</span>
        </div>
        <div className="footer-right">
          <span className="footer-path">/Users/thomasmorton/huddle/agentmail</span>
        </div>
      </footer>
    </div>
  );
};

export default AgentMailDashboard;
