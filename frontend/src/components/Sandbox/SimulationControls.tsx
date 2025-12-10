/**
 * Simulation control buttons
 */

interface SimulationControlsProps {
  isRunning: boolean;
  isComplete: boolean;
  isPaused: boolean;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onReset: () => void;
}

export function SimulationControls({
  isRunning,
  isComplete,
  isPaused,
  onStart,
  onPause,
  onResume,
  onReset,
}: SimulationControlsProps) {
  return (
    <div className="simulation-controls">
      {!isRunning && !isComplete && (
        <button className="control-btn start" onClick={onStart}>
          Start Simulation
        </button>
      )}

      {isRunning && !isPaused && (
        <button className="control-btn pause" onClick={onPause}>
          Pause
        </button>
      )}

      {isRunning && isPaused && (
        <button className="control-btn resume" onClick={onResume}>
          Resume
        </button>
      )}

      <button className="control-btn reset" onClick={onReset}>
        Reset
      </button>

      {isComplete && (
        <div className="simulation-complete">
          Simulation Complete
        </div>
      )}
    </div>
  );
}
