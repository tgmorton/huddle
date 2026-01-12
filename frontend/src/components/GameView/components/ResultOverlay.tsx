/**
 * ResultOverlay - Play result display
 *
 * Shows animated result after play execution:
 * - Outcome (complete, incomplete, sack, etc.)
 * - Yards gained/lost
 * - First down indicator
 * - Touchdown celebration
 * - Turnover alert
 */

import React, { useEffect, useState } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Trophy, Zap } from 'lucide-react';
import type { PlayResult } from '../types';

interface ResultOverlayProps {
  result: PlayResult;
  onDismiss?: () => void;
  autoDismissMs?: number;
}

export const ResultOverlay: React.FC<ResultOverlayProps> = ({
  result,
  onDismiss,
  autoDismissMs = 3000,
}) => {
  const [visible, setVisible] = useState(true);
  const [exiting, setExiting] = useState(false);

  // Auto-dismiss after delay
  useEffect(() => {
    if (autoDismissMs > 0) {
      const timer = setTimeout(() => {
        setExiting(true);
        setTimeout(() => {
          setVisible(false);
          onDismiss?.();
        }, 300);
      }, autoDismissMs);

      return () => clearTimeout(timer);
    }
  }, [autoDismissMs, onDismiss]);

  if (!visible) return null;

  const {
    outcome,
    yardsGained,
    description,
    firstDown,
    touchdown,
    turnover,
    passerName,
    receiverName,
    tacklerName,
  } = result;

  // Determine result type for styling
  const isPositive = yardsGained > 0;
  const isNegative = yardsGained < 0;
  const isBigPlay = Math.abs(yardsGained) >= 15;

  // Format outcome text
  const outcomeText = formatOutcome(outcome);

  // Get icon based on result
  const ResultIcon = getResultIcon(outcome, touchdown, turnover);

  // Build player description
  const playerDesc = buildPlayerDescription(outcome, passerName, receiverName, tacklerName);

  return (
    <div
      className={`result-overlay ${exiting ? 'result-overlay--exiting' : ''} ${
        touchdown ? 'result-overlay--touchdown' : ''
      } ${turnover ? 'result-overlay--turnover' : ''}`}
      onClick={() => {
        setExiting(true);
        setTimeout(() => {
          setVisible(false);
          onDismiss?.();
        }, 300);
      }}
    >
      <div className="result-overlay__content">
        {/* Icon */}
        <div className={`result-overlay__icon ${isPositive ? 'positive' : isNegative ? 'negative' : ''}`}>
          <ResultIcon size={32} />
        </div>

        {/* Outcome */}
        <div className="result-overlay__outcome">{outcomeText}</div>

        {/* Yards */}
        <div className={`result-overlay__yards ${isPositive ? 'positive' : isNegative ? 'negative' : ''} ${isBigPlay ? 'big-play' : ''}`}>
          {yardsGained > 0 ? '+' : ''}{yardsGained} YDS
        </div>

        {/* Player description */}
        {playerDesc && (
          <div className="result-overlay__players">{playerDesc}</div>
        )}

        {/* Special indicators */}
        {firstDown && !touchdown && (
          <div className="result-overlay__first-down">
            <Zap size={16} />
            FIRST DOWN
          </div>
        )}

        {touchdown && (
          <div className="result-overlay__touchdown">
            <Trophy size={20} />
            TOUCHDOWN!
          </div>
        )}

        {turnover && (
          <div className="result-overlay__turnover">
            <AlertTriangle size={16} />
            TURNOVER
          </div>
        )}

        {/* Description */}
        {description && (
          <div className="result-overlay__description">{description}</div>
        )}

        {/* Dismiss hint */}
        <div className="result-overlay__hint">Click to continue</div>
      </div>
    </div>
  );
};

function formatOutcome(outcome: string): string {
  const map: Record<string, string> = {
    complete: 'COMPLETE',
    incomplete: 'INCOMPLETE',
    sack: 'SACK',
    run: 'RUN',
    interception: 'INTERCEPTED',
    fumble: 'FUMBLE',
    touchdown: 'TOUCHDOWN',
    penalty: 'PENALTY',
  };
  return map[outcome] || outcome.toUpperCase();
}

function getResultIcon(outcome: string, touchdown: boolean, turnover: boolean) {
  if (touchdown) return Trophy;
  if (turnover) return AlertTriangle;
  if (outcome === 'complete' || outcome === 'run') return CheckCircle;
  if (outcome === 'incomplete' || outcome === 'sack') return XCircle;
  return CheckCircle;
}

function buildPlayerDescription(
  outcome: string,
  passer?: string,
  receiver?: string,
  tackler?: string
): string | null {
  const parts: string[] = [];

  if (outcome === 'complete' && passer && receiver) {
    parts.push(`${passer} → ${receiver}`);
  } else if (outcome === 'incomplete' && passer) {
    parts.push(`${passer} pass incomplete`);
  } else if (outcome === 'sack' && passer && tackler) {
    parts.push(`${passer} sacked by ${tackler}`);
  } else if (outcome === 'run' && receiver) {
    // receiver is often used for ball carrier on runs
    parts.push(receiver);
  }

  if (tackler && outcome !== 'sack' && outcome !== 'incomplete') {
    parts.push(`tackled by ${tackler}`);
  }

  return parts.length > 0 ? parts.join(' ') : null;
}

export default ResultOverlay;
