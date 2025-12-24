// DeadlinePane.tsx - Compact injury/deadline pane with real player data

import React, { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, Clock, Calendar, Shield, Activity } from 'lucide-react';
import type { WorkspaceItem } from '../../types';
import { getDemoEvent } from '../../data/demo';
import { InlinePlayerCard, type InlinePlayerData } from '../../components';
import { managementApi } from '../../../../api/managementClient';
import { adminApi } from '../../../../api/adminClient';
import { useManagementStore, selectFranchiseId, selectLeagueId } from '../../../../stores/managementStore';

interface DeadlinePaneProps {
  item: WorkspaceItem;
  onComplete: () => void;
}

// Injury data separate from player data
interface InjuryInfo {
  type: string;
  severity: 'minor' | 'moderate' | 'severe';
  recovery: string;
}

// Compact injury options
interface InjuryOption {
  id: string;
  label: string;
  effect: string;
  effectType: 'positive' | 'negative' | 'warning';
  recommended?: boolean;
  risky?: boolean;
}

const INJURY_OPTIONS: Record<string, InjuryOption[]> = {
  minor: [
    { id: 'rest', label: 'Rest 1 Week', effect: 'Full recovery', effectType: 'positive', recommended: true },
    { id: 'play', label: 'Play Through', effect: '10% re-injury risk', effectType: 'warning' },
  ],
  moderate: [
    { id: 'ir_short', label: 'IR (3 Weeks)', effect: 'Full recovery', effectType: 'positive', recommended: true },
    { id: 'rest_extended', label: 'Rest 2 Weeks', effect: '85-90% capacity', effectType: 'warning' },
    { id: 'play_risky', label: 'Play Through', effect: '35% aggravation', effectType: 'negative', risky: true },
  ],
  severe: [
    { id: 'ir_long', label: 'IR (4-6 Weeks)', effect: 'Expected recovery', effectType: 'positive', recommended: true },
    { id: 'second_opinion', label: 'Second Opinion', effect: '+1 day delay', effectType: 'warning' },
    { id: 'surgery', label: 'Season-Ending', effect: 'Full recovery next yr', effectType: 'negative' },
  ],
};

const RESULT_DATA: Record<string, { title: string; icon: typeof Clock; variant: string; effects: { label: string; value: string }[]; summary: string }> = {
  rest: { title: 'Resting', icon: Clock, variant: 'success', effects: [{ label: 'Status', value: 'Day-to-Day' }, { label: 'Return', value: 'Next Week' }], summary: 'Player will rest and return at full strength.' },
  play: { title: 'Playing Through', icon: Activity, variant: 'warning', effects: [{ label: 'Status', value: 'Active' }, { label: 'Performance', value: '-5%' }], summary: 'Monitored closely during games.' },
  ir_short: { title: 'Placed on IR', icon: Calendar, variant: 'info', effects: [{ label: 'Recovery', value: '3 weeks' }, { label: 'Roster', value: 'Spot opened' }], summary: 'Time to evaluate depth chart.' },
  ir_long: { title: 'Placed on IR', icon: Calendar, variant: 'info', effects: [{ label: 'Recovery', value: '4-6 weeks' }, { label: 'Roster', value: 'Spot opened' }], summary: 'Consider backup options.' },
  rest_extended: { title: 'Extended Rest', icon: Clock, variant: 'warning', effects: [{ label: 'Status', value: 'Out' }, { label: 'Return', value: '2 Weeks' }], summary: 'Conservative healing approach.' },
  play_risky: { title: 'High Risk', icon: AlertTriangle, variant: 'critical', effects: [{ label: 'Status', value: 'Active' }, { label: 'Risk', value: 'HIGH' }], summary: 'Medical staff concerned.' },
  second_opinion: { title: 'Second Opinion', icon: Shield, variant: 'info', effects: [{ label: 'Status', value: 'Eval' }, { label: 'Timeline', value: '+1 Day' }], summary: 'Consulting specialist.' },
  surgery: { title: 'Surgery', icon: Calendar, variant: 'critical', effects: [{ label: 'Status', value: 'Out for Season' }], summary: 'Long-term health secured.' },
  complete: { title: 'Completed', icon: CheckCircle, variant: 'success', effects: [{ label: 'Status', value: 'Done' }], summary: 'Task completed.' },
  defer: { title: 'Deferred', icon: Clock, variant: 'warning', effects: [{ label: 'Deadline', value: '+2 days' }], summary: 'Pushed back.' },
};

export const DeadlinePane: React.FC<DeadlinePaneProps> = ({ item, onComplete }) => {
  const [result, setResult] = useState<string | null>(null);
  const [player, setPlayer] = useState<InlinePlayerData | null>(null);
  const [injury, setInjury] = useState<InjuryInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const franchiseId = useManagementStore(selectFranchiseId);
  const leagueId = useManagementStore(selectLeagueId);
  const state = useManagementStore(s => s.state);
  const bumpJournalVersion = useManagementStore(s => s.bumpJournalVersion);

  const eventId = item.eventId?.replace('demo-', '').replace('event-', '') || item.id.replace('demo-', '');
  const event = getDemoEvent(eventId);
  const isInjury = event?.type === 'injury';

  // Fetch real starting QB from depth chart
  useEffect(() => {
    if (!isInjury) {
      setLoading(false);
      return;
    }

    const fetchStarter = async () => {
      // Set injury info (separate from player)
      setInjury({
        type: 'Shoulder Strain',
        severity: 'moderate',
        recovery: '1-2 weeks',
      });

      try {
        // Get team abbreviation from franchise state
        const teamAbbr = (state as { team_abbr?: string })?.team_abbr;

        if (teamAbbr) {
          const depthChart = await adminApi.getTeamDepthChart(teamAbbr);
          const qb1 = depthChart.offense.find(e => e.slot === 'QB1');

          if (qb1 && qb1.player_id && qb1.player_name) {
            setPlayer({
              id: qb1.player_id,
              name: qb1.player_name,
              position: 'QB',
              overall: qb1.overall || 85,
              number: 12,
              // No status badge - decision not yet made
            });
            setLoading(false);
            return;
          }
        }
      } catch (err) {
        console.error('Failed to fetch depth chart:', err);
      }

      // Fallback to demo data - no status until decision is made
      setPlayer({
        id: 'qb1',
        name: 'M. Johnson',
        position: 'QB',
        overall: 88,
        number: 12,
        age: 27,
      });
      setLoading(false);
    };

    fetchStarter();
  }, [isInjury, state]);

  const injurySeverity = injury?.severity || 'moderate';
  const injuryOptions = INJURY_OPTIONS[injurySeverity] || INJURY_OPTIONS.moderate;

  const handleResult = async (resultType: string) => {
    setResult(resultType);

    if (franchiseId) {
      const data = RESULT_DATA[resultType];
      if (data) {
        const effectStr = data.effects.map(e => `${e.label}: ${e.value}`).join(', ');
        const playerName = player?.name || 'Player';

        try {
          await managementApi.addJournalEntry(franchiseId, {
            category: isInjury ? 'injury' : 'intel',
            title: isInjury ? `${playerName} - ${data.title}` : data.title,
            effect: effectStr,
            detail: data.summary,
          });
          bumpJournalVersion();
        } catch (err) {
          console.error('Failed to add journal entry:', err);
        }
      }
    }
  };

  // Result view
  if (result && RESULT_DATA[result]) {
    const data = RESULT_DATA[result];
    const Icon = data.icon;
    return (
      <div className="pane pane--no-header">
        <div className="pane__body">
          <div className={`pane__alert pane__alert--${data.variant}`}>
            <Icon size={16} />
            <span>{data.title}</span>
          </div>
          {player && (
            <InlinePlayerCard player={player} leagueId={leagueId || undefined} variant="compact" />
          )}
          <div className="pane-section pane-section--compact">
            {data.effects.map((e, i) => (
              <div key={i} className="ctrl-result">
                <span className="ctrl-result__label">{e.label}</span>
                <span className="ctrl-result__value">{e.value}</span>
              </div>
            ))}
          </div>
        </div>
        <footer className="pane__footer">
          <button className="pane__btn pane__btn--primary" onClick={onComplete}>Done</button>
        </footer>
      </div>
    );
  }

  // Loading
  if (loading && isInjury) {
    return (
      <div className="pane pane--no-header">
        <div className="pane__body">
          <p className="pane__description pane__description--muted">Loading...</p>
        </div>
      </div>
    );
  }

  // Injury view - compact layout with separated player card and injury info
  if (isInjury && player && injury) {
    return (
      <div className="pane pane--no-header">
        <div className="pane__body">
          {/* Generic player card */}
          <InlinePlayerCard
            player={player}
            leagueId={leagueId || undefined}
            variant="standard"
          />

          {/* Separate injury info */}
          <div className="injury-info">
            <div className="injury-info__row">
              <span className="injury-info__label">Injury</span>
              <span className="injury-info__value injury-info__value--type">{injury.type}</span>
            </div>
            <div className="injury-info__row">
              <span className="injury-info__label">Severity</span>
              <span className={`injury-info__value injury-info__value--${injury.severity}`}>
                {injury.severity.charAt(0).toUpperCase() + injury.severity.slice(1)}
              </span>
            </div>
            <div className="injury-info__row">
              <span className="injury-info__label">Recovery</span>
              <span className="injury-info__value">{injury.recovery}</span>
            </div>
          </div>

          {/* Decision options */}
          <div className="injury-options">
            {injuryOptions.map((opt) => (
              <button
                key={opt.id}
                className={`injury-option ${opt.recommended ? 'injury-option--recommended' : ''} ${opt.risky ? 'injury-option--risky' : ''}`}
                onClick={() => handleResult(opt.id)}
              >
                <span className="injury-option__label">{opt.label}</span>
                <span className={`injury-option__effect injury-option__effect--${opt.effectType}`}>
                  {opt.effect}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Generic deadline
  return (
    <div className="pane pane--no-header">
      <div className="pane__body">
        <p className="pane__description">{item.detail || 'Action required.'}</p>
        {item.timeLeft && (
          <div className="ctrl-result">
            <span className="ctrl-result__label">Time Left</span>
            <span className="ctrl-result__value ctrl-result__value--warning">{item.timeLeft}</span>
          </div>
        )}
      </div>
      <footer className="pane__footer">
        <button className="pane__btn pane__btn--secondary" onClick={() => handleResult('defer')}>Defer</button>
        <button className="pane__btn pane__btn--primary" onClick={() => handleResult('complete')}>Complete</button>
      </footer>
    </div>
  );
};

export default DeadlinePane;
