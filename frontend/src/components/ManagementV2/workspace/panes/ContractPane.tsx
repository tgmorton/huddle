// ContractPane.tsx - Decision pane for trades, contracts, etc. with demo results

import React, { useState } from 'react';
import { ArrowLeftRight, FileText, CheckCircle, XCircle, DollarSign, Users } from 'lucide-react';
import { getDemoEvent } from '../../data/demo';
import { managementApi } from '../../../../api/managementClient';
import { useManagementStore, selectFranchiseId } from '../../../../stores/managementStore';

interface ContractPaneProps {
  eventId?: string;
  onComplete: () => void;
}

// Demo results for different decision types
const CONTRACT_RESULTS = {
  trade_accept: {
    title: 'Trade Accepted',
    icon: CheckCircle,
    variant: 'success' as const,
    effects: [
      { label: 'Roster Change', value: 'Pending physical' },
      { label: 'Cap Impact', value: '-$2.5M' },
      { label: 'Draft Capital', value: '+3rd Rd Pick' },
    ],
    summary: 'Trade will be finalized after physical examination.',
  },
  trade_decline: {
    title: 'Trade Declined',
    icon: XCircle,
    variant: 'info' as const,
    effects: [
      { label: 'Trade Status', value: 'Rejected' },
      { label: 'Relationship', value: 'Unchanged' },
    ],
    summary: 'You passed on this offer. They may come back with a better deal.',
  },
  trade_counter: {
    title: 'Counter Offered',
    icon: ArrowLeftRight,
    variant: 'warning' as const,
    effects: [
      { label: 'Negotiation', value: 'In Progress' },
      { label: 'Expected Response', value: '24 hours' },
    ],
    summary: 'Your counter offer has been sent. Awaiting response.',
  },
  contract_accept: {
    title: 'Contract Signed',
    icon: FileText,
    variant: 'success' as const,
    effects: [
      { label: 'Years', value: '4' },
      { label: 'Total Value', value: '$48M' },
      { label: 'Guaranteed', value: '$32M' },
      { label: 'Cap Hit (Y1)', value: '$8.5M' },
    ],
    summary: 'Player is now locked in through the extension.',
  },
  contract_decline: {
    title: 'Negotiations Stalled',
    icon: XCircle,
    variant: 'warning' as const,
    effects: [
      { label: 'Player Mood', value: 'Disappointed' },
      { label: 'Status', value: 'Will revisit' },
    ],
    summary: 'Player\'s agent indicated they\'ll explore other options.',
  },
  generic_accept: {
    title: 'Accepted',
    icon: CheckCircle,
    variant: 'success' as const,
    effects: [
      { label: 'Status', value: 'Confirmed' },
    ],
    summary: 'Decision recorded.',
  },
  generic_decline: {
    title: 'Declined',
    icon: XCircle,
    variant: 'info' as const,
    effects: [
      { label: 'Status', value: 'Passed' },
    ],
    summary: 'You passed on this opportunity.',
  },
};

export const ContractPane: React.FC<ContractPaneProps> = ({ eventId, onComplete }) => {
  const [result, setResult] = useState<keyof typeof CONTRACT_RESULTS | null>(null);
  const franchiseId = useManagementStore(selectFranchiseId);
  const bumpJournalVersion = useManagementStore(state => state.bumpJournalVersion);

  // Try to get demo event data
  const cleanId = eventId?.replace('demo-', '').replace('event-', '');
  const event = cleanId ? getDemoEvent(cleanId) : undefined;

  // Handle completing with a result
  const handleResult = async (resultType: keyof typeof CONTRACT_RESULTS) => {
    setResult(resultType);

    // Post to journal
    if (franchiseId) {
      const data = CONTRACT_RESULTS[resultType];
      const effectStr = data.effects.map(e => `${e.label}: ${e.value}`).join(', ');
      try {
        await managementApi.addJournalEntry(franchiseId, {
          category: 'transaction',
          title: data.title,
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
    const data = CONTRACT_RESULTS[result];
    const Icon = data.icon;
    return (
      <div className="pane pane--no-header">
        <div className="pane__body">
          <div className={`pane__alert pane__alert--${data.variant}`}>
            <Icon size={18} />
            <span>{data.title}</span>
          </div>
          <div className="pane-section">
            {data.effects.map((effect, i) => (
              <div key={i} className="ctrl-result">
                <span className="ctrl-result__label">{effect.label}</span>
                <span className="ctrl-result__value">{effect.value}</span>
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

  if (event?.type === 'trade_offer') {
    return (
      <div className="pane pane--no-header">
        <div className="pane__body">
          <div className="pane__alert pane__alert--info">
            <ArrowLeftRight size={18} />
            <span>Trade Offer</span>
          </div>
          <p className="pane__description">{event.description}</p>
          <div className="pane-section">
            <div className="ctrl-result">
              <span className="ctrl-result__label">You Receive</span>
              <span className="ctrl-result__value">2025 3rd Round Pick</span>
            </div>
            <div className="ctrl-result">
              <span className="ctrl-result__label">You Send</span>
              <span className="ctrl-result__value">Backup RB</span>
            </div>
          </div>
        </div>
        <footer className="pane__footer">
          <button className="pane__btn pane__btn--secondary" onClick={() => handleResult('trade_decline')}>
            Decline
          </button>
          <button className="pane__btn pane__btn--secondary" onClick={() => handleResult('trade_counter')}>
            Counter
          </button>
          <button className="pane__btn pane__btn--primary" onClick={() => handleResult('trade_accept')}>
            Accept
          </button>
        </footer>
      </div>
    );
  }

  if (event?.type === 'contract_demand') {
    return (
      <div className="pane pane--no-header">
        <div className="pane__body">
          <div className="pane__alert pane__alert--warning">
            <DollarSign size={18} />
            <span>Contract Negotiation</span>
          </div>
          <p className="pane__description">{event.description}</p>
          <div className="pane-section">
            <div className="ctrl-result">
              <span className="ctrl-result__label">Asking</span>
              <span className="ctrl-result__value">$52M / 4 years</span>
            </div>
            <div className="ctrl-result">
              <span className="ctrl-result__label">Market Value</span>
              <span className="ctrl-result__value ctrl-result__value--muted">$48M / 4 years</span>
            </div>
          </div>
        </div>
        <footer className="pane__footer">
          <button className="pane__btn pane__btn--secondary" onClick={() => handleResult('contract_decline')}>
            Pass
          </button>
          <button className="pane__btn pane__btn--primary" onClick={() => handleResult('contract_accept')}>
            Sign
          </button>
        </footer>
      </div>
    );
  }

  // Generic decision fallback
  return (
    <div className="pane pane--no-header">
      <div className="pane__body">
        <div className="pane__alert pane__alert--info">
          <Users size={18} />
          <span>Decision Required</span>
        </div>
        <p className="pane__description">Review and make your decision.</p>
      </div>
      <footer className="pane__footer">
        <button className="pane__btn pane__btn--secondary" onClick={() => handleResult('generic_decline')}>
          Decline
        </button>
        <button className="pane__btn pane__btn--primary" onClick={() => handleResult('generic_accept')}>
          Accept
        </button>
      </footer>
    </div>
  );
};

export default ContractPane;
