// MeetingPane.tsx - Meeting/media event pane with demo completion results

import React, { useState } from 'react';
import { Mic, CheckCircle, TrendingUp, TrendingDown } from 'lucide-react';
import { getDemoEvent } from '../../data/demo';
import { managementApi } from '../../../../api/managementClient';
import { useManagementStore, selectFranchiseId } from '../../../../stores/managementStore';

interface MeetingPaneProps {
  eventId?: string;
  onComplete: () => void;
}

// Demo results for different response types
const MEETING_RESULTS = {
  positive: {
    title: 'Good Response',
    effects: [
      { label: 'Team Morale', value: '+5', trend: 'up' },
      { label: 'Media Relations', value: '+3', trend: 'up' },
    ],
    summary: 'Your measured response was well-received by the media.',
  },
  neutral: {
    title: 'No Comment',
    effects: [
      { label: 'Media Relations', value: '-1', trend: 'down' },
    ],
    summary: 'The media noted your reluctance to engage.',
  },
  deflect: {
    title: 'Deflected',
    effects: [
      { label: 'Focus', value: '+2', trend: 'up' },
    ],
    summary: 'You kept the focus on the game.',
  },
};

export const MeetingPane: React.FC<MeetingPaneProps> = ({ eventId, onComplete }) => {
  const [result, setResult] = useState<keyof typeof MEETING_RESULTS | null>(null);
  const franchiseId = useManagementStore(selectFranchiseId);
  const bumpJournalVersion = useManagementStore(state => state.bumpJournalVersion);

  // Try to get demo event data
  const cleanId = eventId?.replace('demo-', '').replace('event-', '');
  const event = cleanId ? getDemoEvent(cleanId) : undefined;

  // Handle completing the meeting with a result
  const handleResult = async (resultType: keyof typeof MEETING_RESULTS) => {
    setResult(resultType);

    // Post to journal
    if (franchiseId) {
      const data = MEETING_RESULTS[resultType];
      const effectStr = data.effects.map(e => `${e.label} ${e.value}`).join(', ');
      try {
        await managementApi.addJournalEntry(franchiseId, {
          category: 'conversation',
          title: event?.type === 'media' ? 'Press Conference' : 'Meeting',
          effect: effectStr,
          detail: data.summary,
        });
        bumpJournalVersion();
      } catch (err) {
        console.error('Failed to add journal entry:', err);
      }
    }
  };

  // Show results after completing
  if (result) {
    const data = MEETING_RESULTS[result];
    return (
      <div className="pane pane--no-header">
        <div className="pane__body">
          <div className="pane__alert pane__alert--success">
            <CheckCircle size={18} />
            <span>{data.title}</span>
          </div>
          <div className="pane-section">
            {data.effects.map((effect, i) => (
              <div key={i} className="ctrl-result">
                <span className="ctrl-result__label">{effect.label}</span>
                <span className={`ctrl-result__value ctrl-result__value--${effect.trend === 'up' ? 'success' : 'warning'}`}>
                  {effect.trend === 'up' ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                  {effect.value}
                </span>
              </div>
            ))}
          </div>
          <p className="pane__description pane__description--muted">{data.summary}</p>
        </div>
        <footer className="pane__footer">
          <button className="pane__btn pane__btn--primary" onClick={onComplete}>
            Done
          </button>
        </footer>
      </div>
    );
  }

  if (event?.type === 'media') {
    return (
      <div className="pane pane--no-header">
        <div className="pane__body">
          <div className="pane__alert pane__alert--warning">
            <Mic size={18} />
            <span>Press Conference</span>
          </div>
          <p className="pane__description pane__description--quote">"{event.description.replace(/^"|"$/g, '')}"</p>
        </div>
        <footer className="pane__footer">
          {event.options.map((opt, i) => (
            <button
              key={i}
              className={`pane__btn pane__btn--${opt.variant}`}
              onClick={() => handleResult(i === 0 ? 'positive' : i === 1 ? 'neutral' : 'deflect')}
            >
              {opt.label}
            </button>
          ))}
        </footer>
      </div>
    );
  }

  // Generic meeting fallback
  return (
    <div className="pane pane--no-header">
      <div className="pane__body">
        <p className="pane__description">Meeting in progress.</p>
      </div>
      <footer className="pane__footer">
        <button className="pane__btn pane__btn--secondary" onClick={() => handleResult('neutral')}>Skip</button>
        <button className="pane__btn pane__btn--primary" onClick={() => handleResult('positive')}>Attend</button>
      </footer>
    </div>
  );
};

export default MeetingPane;
