/**
 * AnalysisPanel - Right-side panel showing engine internals
 *
 * Sections:
 * 1. QB Brain - Read progression, pressure, coverage shell
 * 2. Selected Player - Dynamic content based on player type
 * 3. Coverage Overview - All assignments
 * 4. Reasoning Trace - Decision logs
 */

import { Brain, User, Shield, ScrollText, Activity, Swords, Target } from 'lucide-react';
import type {
  SimState,
  PlayerState,
  CoverageAssignment,
  PressureLevel,
  ReceiverStatus,
  TraceEntry,
} from './types';

interface AnalysisPanelProps {
  simState: SimState | null;
  selectedPlayer: PlayerState | null;
  coverageAssignments: CoverageAssignment[];
  onSelectPlayer: (id: string) => void;
  playerTraces: Map<string, TraceEntry[]>;
}

// Status badge colors
const STATUS_BADGE: Record<ReceiverStatus, string> = {
  OPEN: 'panel-row__badge--success',
  WINDOW: 'panel-row__badge--accent',
  CONTESTED: 'panel-row__badge--accent',
  COVERED: 'panel-row__badge--danger',
};

const PRESSURE_COLOR: Record<PressureLevel, string> = {
  CLEAN: 'panel-row__value--success',
  LIGHT: 'panel-row__value',
  MODERATE: 'panel-row__value',
  HEAVY: 'panel-row__value--danger',
  CRITICAL: 'panel-row__value--danger',
};

export function AnalysisPanel({
  simState,
  selectedPlayer,
  coverageAssignments,
  onSelectPlayer,
  playerTraces,
}: AnalysisPanelProps) {
  const qbState = simState?.qb_state;
  const qbTrace = simState?.qb_trace || [];

  // Get traces for selected player
  const selectedPlayerTraces = selectedPlayer
    ? playerTraces.get(selectedPlayer.id) || []
    : [];

  // Find receiver for current read
  const receivers = simState?.players.filter(p => p.player_type === 'receiver') || [];
  const currentReadReceiver = qbState?.current_read
    ? receivers.find(r => r.read_order === qbState.current_read)
    : null;

  return (
    <div className="analysis-panel">
      {/* QB Brain Section */}
      <div className="analysis-panel__section">
        <div className="analysis-panel__header">
          <Brain size={12} />
          <span>QB BRAIN</span>
        </div>

        {qbState ? (
          <>
            <div className="panel-row">
              <span className="panel-row__badge panel-row__badge--accent">READ</span>
              <span className="panel-row__title">Progression</span>
              <span className="panel-row__value">
                #{qbState.current_read} {currentReadReceiver?.name ? `(${currentReadReceiver.name.split(' ').pop()})` : ''}
              </span>
            </div>

            <div className="panel-row">
              <span className="panel-row__badge">PRES</span>
              <span className="panel-row__title">Pressure Level</span>
              <span className={`panel-row__value ${PRESSURE_COLOR[qbState.pressure_level]}`}>
                {qbState.pressure_level}
              </span>
            </div>

            <div className="panel-row">
              <span className="panel-row__badge">TIME</span>
              <span className="panel-row__title">In Pocket</span>
              <span className="panel-row__value">{qbState.time_in_pocket.toFixed(2)}s</span>
            </div>

            {qbState.coverage_shell && (
              <div className="panel-row">
                <span className="panel-row__badge">SHEL</span>
                <span className="panel-row__title">Coverage Shell</span>
                <span className="panel-row__value">{qbState.coverage_shell.replace('_', ' ')}</span>
              </div>
            )}

            {qbState.blitz_look && qbState.blitz_look !== 'NONE' && (
              <div className="panel-row">
                <span className="panel-row__badge panel-row__badge--danger">BLTZ</span>
                <span className="panel-row__title">Blitz Look</span>
                <span className="panel-row__value panel-row__value--danger">{qbState.blitz_look}</span>
              </div>
            )}
          </>
        ) : (
          <div className="panel-empty">No QB data available</div>
        )}
      </div>

      {/* Run Game Section (only show for run plays) */}
      {simState?.is_run_play && (
        <div className="analysis-panel__section">
          <div className="analysis-panel__header">
            <Target size={12} />
            <span>RUN GAME</span>
          </div>

          <div className="panel-row">
            <span className="panel-row__badge panel-row__badge--accent">PLAY</span>
            <span className="panel-row__title">Concept</span>
            <span className="panel-row__value">
              {simState.run_concept?.replace(/_/g, ' ').toUpperCase() || 'RUN'}
            </span>
          </div>

          <div className="panel-row">
            <span className="panel-row__badge">GAP</span>
            <span className="panel-row__title">Designed Gap</span>
            <span className="panel-row__value">
              {simState.designed_gap?.replace(/_/g, ' ').toUpperCase() || '-'}
            </span>
          </div>

          {simState.ball_carrier_id && (
            <div className="panel-row">
              <span className="panel-row__badge panel-row__badge--success">BALL</span>
              <span className="panel-row__title">Carrier</span>
              <span className="panel-row__value panel-row__value--success">
                {simState.players.find(p => p.id === simState.ball_carrier_id)?.name || simState.ball_carrier_id}
              </span>
            </div>
          )}

          {/* Yards gained (ball carrier Y position relative to LOS) */}
          {simState.ball_carrier_id && (() => {
            const carrier = simState.players.find(p => p.id === simState.ball_carrier_id);
            if (carrier) {
              const yards = carrier.y;  // LOS is at y=0
              const isGain = yards > 0;
              return (
                <div className="panel-row">
                  <span className={`panel-row__badge ${isGain ? 'panel-row__badge--success' : 'panel-row__badge--danger'}`}>
                    YDS
                  </span>
                  <span className="panel-row__title">Yards</span>
                  <span className={`panel-row__value ${isGain ? 'panel-row__value--success' : 'panel-row__value--danger'}`}>
                    {isGain ? '+' : ''}{yards.toFixed(1)}
                  </span>
                </div>
              );
            }
            return null;
          })()}
        </div>
      )}

      {/* Blocking Engagements Section */}
      <BlockingEngagementsSection
        players={simState?.players || []}
        selectedPlayerId={selectedPlayer?.id}
        onSelectPlayer={onSelectPlayer}
      />

      {/* Selected Player Section */}
      <div className="analysis-panel__section">
        <div className="analysis-panel__header">
          <User size={12} />
          <span>SELECTED: {selectedPlayer?.name || 'None'}</span>
        </div>

        {selectedPlayer ? (
          <SelectedPlayerContent player={selectedPlayer} qbState={qbState} />
        ) : (
          <div className="panel-empty">Click a player to select</div>
        )}
      </div>

      {/* Coverage Overview */}
      <div className="analysis-panel__section">
        <div className="analysis-panel__header">
          <Shield size={12} />
          <span>COVERAGE ({coverageAssignments.length})</span>
        </div>

        {coverageAssignments.length > 0 ? (
          coverageAssignments.map(assignment => (
            <div
              key={assignment.defender_id}
              className={`panel-row panel-row--clickable ${
                selectedPlayer?.id === assignment.defender_id ? 'panel-row--selected' : ''
              }`}
              onClick={() => onSelectPlayer(assignment.defender_id)}
            >
              <span className={`panel-row__badge ${
                assignment.coverage_type === 'zone' ? 'panel-row__badge--accent' : ''
              }`}>
                {assignment.coverage_type === 'zone' ? 'ZN' : 'MAN'}
              </span>
              <span className="panel-row__title">
                {assignment.defender_name.split(' ').pop()}
                {assignment.target_name && ` → ${assignment.target_name.split(' ').pop()}`}
                {assignment.zone_type && ` (${assignment.zone_type.replace(/_/g, ' ')})`}
              </span>
              <span className="panel-row__value">
                {assignment.separation !== undefined
                  ? `${assignment.separation.toFixed(1)}yd`
                  : assignment.is_triggered
                    ? 'TRIG'
                    : '-'}
              </span>
            </div>
          ))
        ) : (
          <div className="panel-empty">No coverage data</div>
        )}
      </div>

      {/* Reasoning Trace */}
      <div className="analysis-panel__section">
        <div className="analysis-panel__header">
          <ScrollText size={12} />
          <span>TRACE ({qbTrace.length})</span>
        </div>

        {qbTrace.length > 0 ? (
          <div className="trace-log">
            {qbTrace.slice(-20).map((line, i) => (
              <div
                key={i}
                className={`trace-line ${getTraceLineClass(line)}`}
              >
                {line}
              </div>
            ))}
          </div>
        ) : (
          <div className="panel-empty">No trace data available</div>
        )}
      </div>

      {/* Player AI Trace (when player selected) */}
      {selectedPlayer && (
        <div className="analysis-panel__section">
          <div className="analysis-panel__header">
            <Activity size={12} />
            <span>{selectedPlayer.name.toUpperCase()} TRACE ({selectedPlayerTraces.length})</span>
          </div>

          {selectedPlayerTraces.length > 0 ? (
            <div className="trace-log">
              {selectedPlayerTraces.slice(-25).map((trace, i) => (
                <div
                  key={`${trace.tick}-${i}`}
                  className={`trace-line trace-line--${trace.category}`}
                  title={`Tick ${trace.tick} (${trace.time.toFixed(2)}s)`}
                >
                  <span className="trace-tick">{trace.tick}</span>
                  <span className={`trace-category trace-category--${trace.category}`}>
                    {trace.category.slice(0, 3).toUpperCase()}
                  </span>
                  <span className="trace-message">{trace.message}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="panel-empty">No AI trace for this player</div>
          )}
        </div>
      )}
    </div>
  );
}

// Helper to classify trace lines by category
function getTraceLineClass(line: string): string {
  if (line.includes('[VISION]') || line.includes('[READ]')) {
    return 'trace-line--perception';
  }
  if (line.includes('[DECISION]') || line.includes('[THROW]')) {
    return 'trace-line--decision';
  }
  return 'trace-line--action';
}

// Selected player content based on player type
interface SelectedPlayerContentProps {
  player: PlayerState;
  qbState: SimState['qb_state'];
}

function SelectedPlayerContent({ player, qbState }: SelectedPlayerContentProps) {
  switch (player.player_type) {
    case 'qb':
      return <QBPlayerContent player={player} />;
    case 'receiver':
      return <ReceiverPlayerContent player={player} qbState={qbState} />;
    case 'defender':
      return <DefenderPlayerContent player={player} />;
    case 'ol':
      return <OLPlayerContent player={player} />;
    case 'dl':
      return <DLPlayerContent player={player} />;
    case 'rb':
    case 'fb':
      return <RBPlayerContent player={player} />;
    default:
      return <GenericPlayerContent player={player} />;
  }
}

function QBPlayerContent({ player }: { player: PlayerState }) {
  return (
    <>
      <div className="panel-row">
        <span className="panel-row__badge">POS</span>
        <span className="panel-row__title">Position</span>
        <span className="panel-row__value">({player.x.toFixed(0)}, {player.y.toFixed(0)})</span>
      </div>
      <div className="panel-row">
        <span className="panel-row__badge">SPD</span>
        <span className="panel-row__title">Speed</span>
        <span className="panel-row__value">{player.speed.toFixed(1)} yd/s</span>
      </div>
      {player.has_ball && (
        <div className="panel-row">
          <span className="panel-row__badge panel-row__badge--success">BALL</span>
          <span className="panel-row__title">Has Ball</span>
          <span className="panel-row__value panel-row__value--success">YES</span>
        </div>
      )}
    </>
  );
}

function ReceiverPlayerContent({
  player,
  qbState,
}: {
  player: PlayerState;
  qbState: SimState['qb_state'];
}) {
  const qbEval = player.qb_eval;

  return (
    <>
      <div className="panel-row">
        <span className="panel-row__badge panel-row__badge--accent">RTE</span>
        <span className="panel-row__title">Route</span>
        <span className="panel-row__value">{player.route_name?.toUpperCase() || '-'}</span>
      </div>

      <div className="panel-row">
        <span className="panel-row__badge">PHS</span>
        <span className="panel-row__title">Phase</span>
        <span className="panel-row__value">{player.route_phase || '-'}</span>
      </div>

      <div className="panel-row">
        <span className="panel-row__badge">WPT</span>
        <span className="panel-row__title">Waypoint</span>
        <span className="panel-row__value">
          {player.current_waypoint !== undefined && player.total_waypoints
            ? `${player.current_waypoint + 1}/${player.total_waypoints}`
            : '-'}
        </span>
      </div>

      {player.read_order && (
        <div className="panel-row">
          <span className={`panel-row__badge ${
            qbState?.current_read === player.read_order ? 'panel-row__badge--accent' : ''
          }`}>
            RD{player.read_order}
          </span>
          <span className="panel-row__title">Read Order</span>
          <span className="panel-row__value">
            {qbState?.current_read === player.read_order ? 'CURRENT' : `#${player.read_order}`}
          </span>
        </div>
      )}

      {player.is_hot_route && (
        <div className="panel-row">
          <span className="panel-row__badge panel-row__badge--danger">HOT</span>
          <span className="panel-row__title">Hot Route</span>
          <span className="panel-row__value panel-row__value--danger">ACTIVE</span>
        </div>
      )}

      {qbEval && (
        <>
          <div className="panel-row">
            <span className={`panel-row__badge ${STATUS_BADGE[qbEval.status]}`}>
              {qbEval.status.slice(0, 3)}
            </span>
            <span className="panel-row__title">Separation</span>
            <span className="panel-row__value">{qbEval.separation.toFixed(1)} yd</span>
          </div>

          <div className="panel-row">
            <span className="panel-row__badge">VIS</span>
            <span className="panel-row__title">Detection Quality</span>
            <span className="panel-row__value">{(qbEval.detection_quality * 100).toFixed(0)}%</span>
          </div>
        </>
      )}
    </>
  );
}

function DefenderPlayerContent({ player }: { player: PlayerState }) {
  const recognitionProgress = player.recognition_delay && player.recognition_timer
    ? (player.recognition_timer / player.recognition_delay) * 100
    : null;

  return (
    <>
      <div className="panel-row">
        <span className={`panel-row__badge ${
          player.coverage_type === 'zone' ? 'panel-row__badge--accent' : ''
        }`}>
          {player.coverage_type === 'zone' ? 'ZN' : 'MAN'}
        </span>
        <span className="panel-row__title">Coverage Type</span>
        <span className="panel-row__value">{player.coverage_type?.toUpperCase() || '-'}</span>
      </div>

      <div className="panel-row">
        <span className="panel-row__badge">PHS</span>
        <span className="panel-row__title">Phase</span>
        <span className="panel-row__value">{player.coverage_phase || '-'}</span>
      </div>

      {player.zone_type && (
        <div className="panel-row">
          <span className="panel-row__badge">ZONE</span>
          <span className="panel-row__title">Zone Assignment</span>
          <span className="panel-row__value">{player.zone_type.replace(/_/g, ' ')}</span>
        </div>
      )}

      {player.has_triggered !== undefined && (
        <div className="panel-row">
          <span className={`panel-row__badge ${player.has_triggered ? 'panel-row__badge--danger' : ''}`}>
            TRIG
          </span>
          <span className="panel-row__title">Triggered</span>
          <span className={`panel-row__value ${player.has_triggered ? 'panel-row__value--danger' : 'panel-row__value--muted'}`}>
            {player.has_triggered ? 'YES' : 'NO'}
          </span>
        </div>
      )}

      {player.has_recognized_break !== undefined && (
        <div className="panel-row">
          <span className={`panel-row__badge ${player.has_recognized_break ? 'panel-row__badge--success' : 'panel-row__badge--accent'}`}>
            REC
          </span>
          <span className="panel-row__title">Break Recognition</span>
          <span className={`panel-row__value ${player.has_recognized_break ? 'panel-row__value--success' : ''}`}>
            {player.has_recognized_break
              ? 'RECOGNIZED'
              : recognitionProgress !== null
                ? `${recognitionProgress.toFixed(0)}%`
                : 'WAITING'}
          </span>
        </div>
      )}

      {player.pursuit_target_x !== undefined && (
        <div className="panel-row">
          <span className="panel-row__badge panel-row__badge--danger">PRST</span>
          <span className="panel-row__title">Pursuit Target</span>
          <span className="panel-row__value">
            ({player.pursuit_target_x.toFixed(0)}, {player.pursuit_target_y?.toFixed(0)})
          </span>
        </div>
      )}
    </>
  );
}

function OLPlayerContent({ player }: { player: PlayerState }) {
  return (
    <>
      <div className="panel-row">
        <span className="panel-row__badge">POS</span>
        <span className="panel-row__title">Position</span>
        <span className="panel-row__value">({player.x.toFixed(1)}, {player.y.toFixed(1)})</span>
      </div>

      {player.blocking_assignment && (
        <div className="panel-row">
          <span className="panel-row__badge panel-row__badge--accent">ASGN</span>
          <span className="panel-row__title">Assignment</span>
          <span className="panel-row__value">
            {player.blocking_assignment.replace(/_/g, ' ').toUpperCase()}
          </span>
        </div>
      )}

      <div className="panel-row">
        <span className={`panel-row__badge ${player.is_engaged ? 'panel-row__badge--success' : ''}`}>
          ENG
        </span>
        <span className="panel-row__title">Engaged</span>
        <span className="panel-row__value">
          {player.is_engaged ? (player.engaged_with_id || 'YES') : 'NO'}
        </span>
      </div>

      {player.is_pulling && (
        <div className="panel-row">
          <span className="panel-row__badge panel-row__badge--accent">PULL</span>
          <span className="panel-row__title">Pull Target</span>
          <span className="panel-row__value">
            ({player.pull_target_x?.toFixed(0) || '?'}, {player.pull_target_y?.toFixed(0) || '?'})
          </span>
        </div>
      )}
    </>
  );
}

function DLPlayerContent({ player }: { player: PlayerState }) {
  const shedProgress = player.block_shed_progress || 0;

  return (
    <>
      <div className="panel-row">
        <span className="panel-row__badge">POS</span>
        <span className="panel-row__title">Position</span>
        <span className="panel-row__value">({player.x.toFixed(0)}, {player.y.toFixed(0)})</span>
      </div>

      <div className="panel-row">
        <span className={`panel-row__badge ${player.is_engaged ? 'panel-row__badge--accent' : ''}`}>
          ENG
        </span>
        <span className="panel-row__title">Engaged</span>
        <span className="panel-row__value">{player.is_engaged ? 'YES' : 'NO'}</span>
      </div>

      {player.is_engaged && (
        <div className="panel-row">
          <span className={`panel-row__badge ${shedProgress > 0.7 ? 'panel-row__badge--success' : ''}`}>
            SHED
          </span>
          <span className="panel-row__title">Shed Progress</span>
          <span className={`panel-row__value ${shedProgress > 0.7 ? 'panel-row__value--success' : ''}`}>
            {(shedProgress * 100).toFixed(0)}%
          </span>
        </div>
      )}

      {player.pursuit_target_x !== undefined && (
        <div className="panel-row">
          <span className="panel-row__badge panel-row__badge--danger">PRST</span>
          <span className="panel-row__title">Pursuit Target</span>
          <span className="panel-row__value">
            ({player.pursuit_target_x.toFixed(0)}, {player.pursuit_target_y?.toFixed(0)})
          </span>
        </div>
      )}
    </>
  );
}

function RBPlayerContent({ player }: { player: PlayerState }) {
  const yards = player.y;  // LOS is at y=0
  const isGain = yards > 0;

  return (
    <>
      <div className="panel-row">
        <span className="panel-row__badge">POS</span>
        <span className="panel-row__title">Position</span>
        <span className="panel-row__value">({player.x.toFixed(1)}, {player.y.toFixed(1)})</span>
      </div>

      <div className="panel-row">
        <span className="panel-row__badge">SPD</span>
        <span className="panel-row__title">Speed</span>
        <span className="panel-row__value">{player.speed.toFixed(1)} yd/s</span>
      </div>

      {player.has_ball && (
        <div className="panel-row">
          <span className="panel-row__badge panel-row__badge--success">BALL</span>
          <span className="panel-row__title">Has Ball</span>
          <span className="panel-row__value panel-row__value--success">YES</span>
        </div>
      )}

      {player.has_ball && (
        <div className="panel-row">
          <span className={`panel-row__badge ${isGain ? 'panel-row__badge--success' : 'panel-row__badge--danger'}`}>
            YDS
          </span>
          <span className="panel-row__title">Yards</span>
          <span className={`panel-row__value ${isGain ? 'panel-row__value--success' : 'panel-row__value--danger'}`}>
            {isGain ? '+' : ''}{yards.toFixed(1)}
          </span>
        </div>
      )}

      {player.target_gap && (
        <div className="panel-row">
          <span className="panel-row__badge panel-row__badge--accent">GAP</span>
          <span className="panel-row__title">Target Gap</span>
          <span className="panel-row__value">
            {player.target_gap.replace(/_/g, ' ').toUpperCase()}
          </span>
        </div>
      )}

      {player.read_point_x !== undefined && (
        <div className="panel-row">
          <span className="panel-row__badge">READ</span>
          <span className="panel-row__title">Read Point</span>
          <span className="panel-row__value">
            ({player.read_point_x.toFixed(0)}, {player.read_point_y?.toFixed(0)})
          </span>
        </div>
      )}

      {player.vision_target_x !== undefined && (
        <div className="panel-row">
          <span className="panel-row__badge">VIS</span>
          <span className="panel-row__title">Vision Target</span>
          <span className="panel-row__value">
            ({player.vision_target_x.toFixed(0)}, {player.vision_target_y?.toFixed(0)})
          </span>
        </div>
      )}

      {player.current_move && (
        <div className="panel-row">
          <span className="panel-row__badge panel-row__badge--accent">MOVE</span>
          <span className="panel-row__title">Current Move</span>
          <span className="panel-row__value">
            {player.current_move.toUpperCase()}
            {player.move_success !== undefined && (
              <span className={player.move_success ? 'panel-row__value--success' : 'panel-row__value--danger'}>
                {' '}{player.move_success ? '✓' : '✗'}
              </span>
            )}
          </span>
        </div>
      )}
    </>
  );
}

function GenericPlayerContent({ player }: { player: PlayerState }) {
  return (
    <>
      <div className="panel-row">
        <span className="panel-row__badge">TYPE</span>
        <span className="panel-row__title">Player Type</span>
        <span className="panel-row__value">{player.player_type.toUpperCase()}</span>
      </div>

      <div className="panel-row">
        <span className="panel-row__badge">POS</span>
        <span className="panel-row__title">Position</span>
        <span className="panel-row__value">({player.x.toFixed(0)}, {player.y.toFixed(0)})</span>
      </div>

      <div className="panel-row">
        <span className="panel-row__badge">SPD</span>
        <span className="panel-row__title">Speed</span>
        <span className="panel-row__value">{player.speed.toFixed(1)} yd/s</span>
      </div>
    </>
  );
}

// ============================================================================
// Blocking Engagements Section
// ============================================================================

interface BlockingEngagementsSectionProps {
  players: PlayerState[];
  selectedPlayerId?: string;
  onSelectPlayer: (id: string) => void;
}

function BlockingEngagementsSection({
  players,
  selectedPlayerId,
  onSelectPlayer,
}: BlockingEngagementsSectionProps) {
  // Find all OL and DL players
  const olPlayers = players.filter(p => p.player_type === 'ol');
  const dlPlayers = players.filter(p => p.player_type === 'dl');

  // Build engagement pairs
  const engagements: Array<{
    ol: PlayerState;
    dl: PlayerState;
    shedProgress: number;
  }> = [];

  for (const ol of olPlayers) {
    if (ol.is_engaged && ol.engaged_with_id) {
      const dl = dlPlayers.find(d => d.id === ol.engaged_with_id);
      if (dl) {
        engagements.push({
          ol,
          dl,
          shedProgress: dl.block_shed_progress || 0,
        });
      }
    }
  }

  // Only show if there are OL/DL in the play
  if (olPlayers.length === 0 && dlPlayers.length === 0) {
    return null;
  }

  return (
    <div className="analysis-panel__section">
      <div className="analysis-panel__header">
        <Swords size={12} />
        <span>BLOCKING ({engagements.length}/{Math.max(olPlayers.length, dlPlayers.length)})</span>
      </div>

      {engagements.length > 0 ? (
        engagements.map(({ ol, dl, shedProgress }) => {
          const isSelected = selectedPlayerId === ol.id || selectedPlayerId === dl.id;
          const shedPercent = shedProgress * 100;
          const isNearShed = shedPercent > 70;
          const isShed = shedPercent >= 100;

          return (
            <div
              key={`${ol.id}-${dl.id}`}
              className={`panel-row panel-row--clickable ${isSelected ? 'panel-row--selected' : ''}`}
              onClick={() => onSelectPlayer(ol.id)}
            >
              <span className={`panel-row__badge ${
                isShed ? 'panel-row__badge--danger' :
                isNearShed ? 'panel-row__badge--accent' :
                'panel-row__badge--success'
              }`}>
                {isShed ? 'SHED' : 'ENG'}
              </span>
              <span className="panel-row__title">
                {ol.name} vs {dl.name}
              </span>
              <span className={`panel-row__value ${
                isShed ? 'panel-row__value--danger' :
                isNearShed ? 'panel-row__value--accent' : ''
              }`}>
                {shedPercent.toFixed(0)}%
              </span>
            </div>
          );
        })
      ) : (
        // Show unengaged OL/DL if no engagements
        <>
          {olPlayers.filter(ol => !ol.is_engaged).map(ol => (
            <div
              key={ol.id}
              className={`panel-row panel-row--clickable ${selectedPlayerId === ol.id ? 'panel-row--selected' : ''}`}
              onClick={() => onSelectPlayer(ol.id)}
            >
              <span className="panel-row__badge">{ol.blocking_assignment?.slice(0, 4).toUpperCase() || 'FREE'}</span>
              <span className="panel-row__title">{ol.name}</span>
              <span className="panel-row__value panel-row__value--muted">
                {ol.is_pulling ? 'PULL' : 'SCAN'}
              </span>
            </div>
          ))}
          {dlPlayers.filter(dl => !dl.is_engaged).map(dl => (
            <div
              key={dl.id}
              className={`panel-row panel-row--clickable ${selectedPlayerId === dl.id ? 'panel-row--selected' : ''}`}
              onClick={() => onSelectPlayer(dl.id)}
            >
              <span className="panel-row__badge panel-row__badge--danger">FREE</span>
              <span className="panel-row__title">{dl.name}</span>
              <span className="panel-row__value panel-row__value--danger">RUSH</span>
            </div>
          ))}
          {olPlayers.length === 0 && dlPlayers.length === 0 && (
            <div className="panel-empty">No OL/DL in play</div>
          )}
        </>
      )}
    </div>
  );
}
