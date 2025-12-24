/**
 * SimWorkshopPanel - Engine debugging panel for SimAnalyzer
 *
 * Shows:
 * - Simulation state (phase, tick, time, outcome)
 * - QB brain state (pressure, read, pocket time)
 * - QB trace (reasoning lines)
 * - Game events
 *
 * Based on ManagementV2's WorkshopPanel pattern.
 */

import React, { useRef, useEffect, useState } from 'react';
import { X, Wifi, WifiOff, Trash2, Download, Brain, Zap } from 'lucide-react';
import type { SimState } from './types';

export interface LogEntry {
  id: string;
  timestamp: Date;
  message: string;
  type: 'info' | 'success' | 'error' | 'warning' | 'event' | 'brain' | 'ws';
}

interface SimWorkshopPanelProps {
  isOpen: boolean;
  onClose: () => void;
  simState: SimState | null;
  isConnected: boolean;
  logs: LogEntry[];
  onClearLogs: () => void;
}

export const SimWorkshopPanel: React.FC<SimWorkshopPanelProps> = ({
  isOpen,
  onClose,
  simState,
  isConnected,
  logs,
  onClearLogs,
}) => {
  const logEndRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState<'trace' | 'events' | 'log'>('trace');

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs.length, simState?.qb_trace?.length]);

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  };

  const getTypeClass = (type: LogEntry['type']) => {
    switch (type) {
      case 'success': return 'sim-workshop-log__entry--success';
      case 'error': return 'sim-workshop-log__entry--error';
      case 'warning': return 'sim-workshop-log__entry--warning';
      case 'event': return 'sim-workshop-log__entry--event';
      case 'brain': return 'sim-workshop-log__entry--brain';
      case 'ws': return 'sim-workshop-log__entry--ws';
      default: return '';
    }
  };

  const getTypePrefix = (type: LogEntry['type']) => {
    switch (type) {
      case 'success': return '[OK]';
      case 'error': return '[ERR]';
      case 'warning': return '[WARN]';
      case 'event': return '[EVT]';
      case 'brain': return '[BRAIN]';
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
    a.download = `sim-workshop-log-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getPressureColor = (level?: string) => {
    switch (level) {
      case 'CLEAN': return 'var(--success)';
      case 'LIGHT': return 'var(--success)';
      case 'MODERATE': return 'var(--warning)';
      case 'HEAVY': return 'var(--error)';
      case 'CRITICAL': return 'var(--error)';
      default: return 'var(--text-muted)';
    }
  };

  if (!isOpen) return null;

  const qbState = simState?.qb_state;
  const qbTrace = simState?.qb_trace || [];
  const events = simState?.events || [];

  return (
    <aside className="sim-workshop-panel">
      <header className="sim-workshop-panel__header">
        <h2>Engine</h2>
        <div className="sim-workshop-panel__status">
          {isConnected ? (
            <span className="sim-workshop-panel__connected">
              <Wifi size={14} />
              Live
            </span>
          ) : (
            <span className="sim-workshop-panel__disconnected">
              <WifiOff size={14} />
              Offline
            </span>
          )}
        </div>
        <button className="sim-workshop-panel__close" onClick={onClose}>
          <X size={16} />
        </button>
      </header>

      <div className="sim-workshop-panel__content">
        {/* Sim Status Section */}
        <section className="sim-workshop-panel__section sim-workshop-panel__section--status">
          <h3><Zap size={12} /> Simulation</h3>
          <div className="sim-workshop-panel__status-grid">
            <div className="sim-workshop-panel__stat">
              <span className="sim-workshop-panel__stat-label">Phase</span>
              <span className="sim-workshop-panel__stat-value">
                {simState?.phase || 'N/A'}
              </span>
            </div>
            <div className="sim-workshop-panel__stat">
              <span className="sim-workshop-panel__stat-label">Tick</span>
              <span className="sim-workshop-panel__stat-value">
                {simState?.tick ?? 'N/A'}
              </span>
            </div>
            <div className="sim-workshop-panel__stat">
              <span className="sim-workshop-panel__stat-label">Time</span>
              <span className="sim-workshop-panel__stat-value">
                {simState?.time?.toFixed(2) ?? 'N/A'}s
              </span>
            </div>
            <div className="sim-workshop-panel__stat">
              <span className="sim-workshop-panel__stat-label">Outcome</span>
              <span className="sim-workshop-panel__stat-value">
                {simState?.play_outcome || 'in_progress'}
              </span>
            </div>
            {simState?.is_run_play && (
              <>
                <div className="sim-workshop-panel__stat">
                  <span className="sim-workshop-panel__stat-label">Run</span>
                  <span className="sim-workshop-panel__stat-value">
                    {simState.run_concept || 'Yes'}
                  </span>
                </div>
                <div className="sim-workshop-panel__stat">
                  <span className="sim-workshop-panel__stat-label">Gap</span>
                  <span className="sim-workshop-panel__stat-value">
                    {simState.designed_gap?.toUpperCase() || 'N/A'}
                  </span>
                </div>
              </>
            )}
          </div>
        </section>

        {/* QB Brain Section */}
        {qbState && (
          <section className="sim-workshop-panel__section sim-workshop-panel__section--brain">
            <h3><Brain size={12} /> QB Brain</h3>
            <div className="sim-workshop-panel__status-grid">
              <div className="sim-workshop-panel__stat">
                <span className="sim-workshop-panel__stat-label">Pressure</span>
                <span
                  className="sim-workshop-panel__stat-value"
                  style={{ color: getPressureColor(qbState.pressure_level) }}
                >
                  {qbState.pressure_level || 'N/A'}
                </span>
              </div>
              <div className="sim-workshop-panel__stat">
                <span className="sim-workshop-panel__stat-label">Read #</span>
                <span className="sim-workshop-panel__stat-value">
                  {qbState.current_read ?? 'N/A'}
                </span>
              </div>
              <div className="sim-workshop-panel__stat">
                <span className="sim-workshop-panel__stat-label">Pocket</span>
                <span className="sim-workshop-panel__stat-value">
                  {qbState.time_in_pocket?.toFixed(2) ?? 'N/A'}s
                </span>
              </div>
              <div className="sim-workshop-panel__stat">
                <span className="sim-workshop-panel__stat-label">Dropback</span>
                <span className="sim-workshop-panel__stat-value">
                  {qbState.dropback_complete ? 'Done' : 'In Progress'}
                </span>
              </div>
              {qbState.coverage_shell && (
                <div className="sim-workshop-panel__stat">
                  <span className="sim-workshop-panel__stat-label">Coverage</span>
                  <span className="sim-workshop-panel__stat-value">
                    {qbState.coverage_shell}
                  </span>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Tab Bar */}
        <div className="sim-workshop-panel__tabs">
          <button
            className={`sim-workshop-panel__tab ${activeTab === 'trace' ? 'active' : ''}`}
            onClick={() => setActiveTab('trace')}
          >
            Trace ({qbTrace.length})
          </button>
          <button
            className={`sim-workshop-panel__tab ${activeTab === 'events' ? 'active' : ''}`}
            onClick={() => setActiveTab('events')}
          >
            Events ({events.length})
          </button>
          <button
            className={`sim-workshop-panel__tab ${activeTab === 'log' ? 'active' : ''}`}
            onClick={() => setActiveTab('log')}
          >
            Log ({logs.length})
          </button>
        </div>

        {/* Trace Section */}
        {activeTab === 'trace' && (
          <section className="sim-workshop-panel__section sim-workshop-panel__section--log">
            <div className="sim-workshop-log">
              {qbTrace.length === 0 ? (
                <div className="sim-workshop-log__empty">No trace entries</div>
              ) : (
                qbTrace.map((line, i) => (
                  <div key={i} className="sim-workshop-log__entry sim-workshop-log__entry--brain">
                    <span className="sim-workshop-log__prefix">[{i + 1}]</span>
                    <span className="sim-workshop-log__message">{line}</span>
                  </div>
                ))
              )}
              <div ref={logEndRef} />
            </div>
          </section>
        )}

        {/* Events Section */}
        {activeTab === 'events' && (
          <section className="sim-workshop-panel__section sim-workshop-panel__section--log">
            <div className="sim-workshop-log">
              {events.length === 0 ? (
                <div className="sim-workshop-log__empty">No events yet</div>
              ) : (
                events.map((evt, i) => (
                  <div key={i} className="sim-workshop-log__entry sim-workshop-log__entry--event">
                    <span className="sim-workshop-log__time">{evt.time.toFixed(2)}s</span>
                    <span className="sim-workshop-log__prefix">[{evt.type.toUpperCase()}]</span>
                    <span className="sim-workshop-log__message">{evt.description}</span>
                  </div>
                ))
              )}
              <div ref={logEndRef} />
            </div>
          </section>
        )}

        {/* Log Section */}
        {activeTab === 'log' && (
          <section className="sim-workshop-panel__section sim-workshop-panel__section--log">
            <div className="sim-workshop-panel__log-header">
              <div className="sim-workshop-panel__log-actions">
                <button
                  className="sim-workshop-panel__btn"
                  onClick={exportLogs}
                  title="Export logs"
                  disabled={logs.length === 0}
                >
                  <Download size={12} />
                </button>
                <button
                  className="sim-workshop-panel__btn"
                  onClick={onClearLogs}
                  title="Clear logs"
                  disabled={logs.length === 0}
                >
                  <Trash2 size={12} />
                </button>
              </div>
            </div>

            <div className="sim-workshop-log">
              {logs.length === 0 ? (
                <div className="sim-workshop-log__empty">No log entries</div>
              ) : (
                logs.map(log => (
                  <div
                    key={log.id}
                    className={`sim-workshop-log__entry ${getTypeClass(log.type)}`}
                  >
                    <span className="sim-workshop-log__time">{formatTime(log.timestamp)}</span>
                    <span className="sim-workshop-log__prefix">{getTypePrefix(log.type)}</span>
                    <span className="sim-workshop-log__message">{log.message}</span>
                  </div>
                ))
              )}
              <div ref={logEndRef} />
            </div>
          </section>
        )}
      </div>
    </aside>
  );
};

export default SimWorkshopPanel;
