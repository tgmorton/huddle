/**
 * Broadcast Lab - Sandbox for TV graphics prototypes
 *
 * A playground for experimenting with broadcast-style visuals:
 * - Scorebugs
 * - Stadium flyovers
 * - Tunnel entrances
 * - Lower thirds
 * - And more...
 */

import { useState } from 'react';
import { ScoreBugLab } from './prototypes/ScoreBug/ScoreBugLab';
import { StadiumFlyover } from './prototypes/StadiumFlyover';
import './BroadcastLab.css';

type PrototypeKey = 'hub' | 'scorebug' | 'tunnel' | 'flyover';

interface Prototype {
  key: PrototypeKey;
  title: string;
  description: string;
  icon: string;
  status: 'ready' | 'wip' | 'planned';
}

const PROTOTYPES: Prototype[] = [
  {
    key: 'scorebug',
    title: 'Score Bugs',
    description: 'CBS, ESPN, NBC-style score overlays with animations',
    icon: '📺',
    status: 'ready',
  },
  {
    key: 'tunnel',
    title: 'Tunnel Entrance',
    description: 'Team tunnel entrance with smoke and silhouettes',
    icon: '🚇',
    status: 'planned',
  },
  {
    key: 'flyover',
    title: 'Stadium Flyover',
    description: 'Animated stadium reveal and flyover sequence',
    icon: '🏟️',
    status: 'ready',
  },
];

export function BroadcastLab() {
  const [activePrototype, setActivePrototype] = useState<PrototypeKey>('hub');

  const renderPrototype = () => {
    switch (activePrototype) {
      case 'scorebug':
        return <ScoreBugLab />;
      case 'flyover':
        return <StadiumFlyover />;
      default:
        return null;
    }
  };

  if (activePrototype !== 'hub') {
    return (
      <div className="broadcast-lab">
        <button
          className="back-button"
          onClick={() => setActivePrototype('hub')}
        >
          ← Back to Lab
        </button>
        {renderPrototype()}
      </div>
    );
  }

  return (
    <div className="broadcast-lab">
      <div className="lab-header">
        <h1>📡 Broadcast Lab</h1>
        <p>Experimental TV graphics and broadcast-style visuals</p>
      </div>

      <div className="prototypes-grid">
        {PROTOTYPES.map((proto) => (
          <button
            key={proto.key}
            className={`prototype-card ${proto.status}`}
            onClick={() => setActivePrototype(proto.key)}
            disabled={proto.status === 'planned'}
          >
            <span className="prototype-icon">{proto.icon}</span>
            <h3>{proto.title}</h3>
            <p>{proto.description}</p>
            <span className={`status-badge ${proto.status}`}>
              {proto.status === 'ready' ? '✓ Ready' : proto.status === 'wip' ? '🔧 WIP' : '📋 Planned'}
            </span>
          </button>
        ))}
      </div>

      <div className="lab-footer">
        <p>More prototypes coming soon: Lower Thirds, Replay Graphics, Weather Effects...</p>
      </div>
    </div>
  );
}
