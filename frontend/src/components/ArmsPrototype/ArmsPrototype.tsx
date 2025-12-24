/**
 * Arms Prototype Visualizer
 *
 * A "Film Room" style visualization for the 1v1 OL vs DL blocking simulation
 * with physical arm mechanics.
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import './ArmsPrototype.css';

const API_BASE = 'http://localhost:8000/api/v1/arms-prototype';

// Types
interface Vec2 {
  x: number;
  y: number;
}

interface HandData {
  x: number;
  y: number;
  state: string;
}

interface FootData {
  x: number;
  y: number;
  phase: string;  // grounded, lifting, airborne, planting
  weight: number;
  cycle_progress: number;  // 0.0 to 1.0 through step cycle
  step_target: Vec2 | null;
}

interface ForceDebtData {
  x: number;
  y: number;
  magnitude: number;
}

interface AssignmentData {
  target_id: string | null;
  block_type: string;  // "single", "double_post", "double_drive", "none"
  partner_id: string | null;
}

interface DoubleTeamData {
  post_blocker_id: string;
  drive_blocker_id: string;
  active: boolean;
  ticks_active: number;
  drive_direction: number;
}

interface PlayerData {
  position: Vec2;
  facing: number;
  pad_level: number;
  balance: number;
  left_hand: HandData;
  right_hand: HandData;
  left_shoulder: Vec2;
  right_shoulder: Vec2;
  left_foot: FootData;
  right_foot: FootData;
  stance_width: number;
  stance_balance: number;
  force_debt: ForceDebtData;
  grounded_count: number;
  role: string;
}

interface FrameData {
  tick: number;
  time: number;
  players: Record<string, PlayerData>;
  // Multi-player scenario data
  assignments?: Record<string, AssignmentData>;
  double_teams?: Record<string, DoubleTeamData>;
  shed_players?: string[];
}

interface SimulationResult {
  ticks: number;
  time: number;
  rusher_won: boolean;
  blocker_held: boolean;
}

// Calculate arm extension from shoulder to hand positions
function calculateArmExtension(shoulder: Vec2, hand: Vec2, maxLength: number): number {
  const dx = hand.x - shoulder.x;
  const dy = hand.y - shoulder.y;
  const length = Math.sqrt(dx * dx + dy * dy);
  return Math.min(1, length / maxLength);
}

// Calculate effective power based on extension (bell curve centered at 0.5)
function calculateEffectivePower(extension: number): number {
  const factor = 1.0 - 2.0 * Math.abs(extension - 0.5);
  return Math.max(0.3, factor);
}

// Colors for hand states
const HAND_COLORS: Record<string, string> = {
  free: '#5f6368',
  reaching: '#ffc107',
  placed: '#b388ff',
  controlling: '#69f0ae',
  controlled: '#ff5252',
  locked: '#ff9100',
};

// Colors for foot phases
const FOOT_COLORS: Record<string, string> = {
  grounded: '#69f0ae',   // Green - stable, on ground
  lifting: '#ffc107',    // Yellow - starting to lift
  airborne: '#ff9100',   // Orange - in the air, moving
  planting: '#00b8d4',   // Cyan - about to touch down
};

// Player colors
const OL_COLOR = '#2196f3';
const DL_COLOR = '#f44336';
const TARGET_COLOR = '#ffc107';

// Derive body parts for human-like rendering
interface BodyParts {
  head: Vec2;
  shoulderMid: Vec2;
  leftShoulder: Vec2;
  rightShoulder: Vec2;
  leftElbow: Vec2;
  rightElbow: Vec2;
  leftHand: Vec2;
  rightHand: Vec2;
  hips: Vec2;
  leftHip: Vec2;
  rightHip: Vec2;
  leftKnee: Vec2;
  rightKnee: Vec2;
  leftFoot: Vec2;
  rightFoot: Vec2;
}

function deriveBodyParts(
  player: PlayerData,
  toCanvas: (p: Vec2) => Vec2
): BodyParts {
  // This is a TOP-DOWN view, so we see players from above
  // Y-axis on canvas goes down, but in simulation "forward" is toward the opponent

  const leftShoulder = toCanvas(player.left_shoulder);
  const rightShoulder = toCanvas(player.right_shoulder);
  const leftHand = toCanvas({ x: player.left_hand.x, y: player.left_hand.y });
  const rightHand = toCanvas({ x: player.right_hand.x, y: player.right_hand.y });
  const leftFoot = toCanvas({ x: player.left_foot.x, y: player.left_foot.y });
  const rightFoot = toCanvas({ x: player.right_foot.x, y: player.right_foot.y });
  const center = toCanvas(player.position);

  // Shoulder midpoint
  const shoulderMid = {
    x: (leftShoulder.x + rightShoulder.x) / 2,
    y: (leftShoulder.y + rightShoulder.y) / 2
  };

  // Head - in front of shoulders in facing direction (top-down view)
  // Canvas Y is flipped, so we use -sin for the Y component
  const headOffset = 12;
  const head = {
    x: shoulderMid.x + Math.cos(player.facing) * headOffset,
    y: shoulderMid.y - Math.sin(player.facing) * headOffset
  };

  // Hips/butt - behind shoulders (opposite of facing direction)
  // In top-down view, this represents the back of the player
  const hipOffset = 10 + player.pad_level * 5; // Further back when standing tall
  const hips = {
    x: shoulderMid.x - Math.cos(player.facing) * hipOffset,
    y: shoulderMid.y + Math.sin(player.facing) * hipOffset
  };

  // Hip positions - perpendicular to facing, narrower than shoulders
  const shoulderWidth = Math.sqrt(
    Math.pow(rightShoulder.x - leftShoulder.x, 2) +
    Math.pow(rightShoulder.y - leftShoulder.y, 2)
  );
  const hipWidth = shoulderWidth * 0.7;
  const perpAngle = player.facing - Math.PI / 2;
  const leftHip = {
    x: hips.x + Math.cos(perpAngle) * hipWidth / 2,
    y: hips.y - Math.sin(perpAngle) * hipWidth / 2
  };
  const rightHip = {
    x: hips.x - Math.cos(perpAngle) * hipWidth / 2,
    y: hips.y + Math.sin(perpAngle) * hipWidth / 2
  };

  // Elbows - bent outward from shoulder-to-hand line
  // Add perpendicular offset for natural elbow bend
  const leftArmVec = { x: leftHand.x - leftShoulder.x, y: leftHand.y - leftShoulder.y };
  const rightArmVec = { x: rightHand.x - rightShoulder.x, y: rightHand.y - rightShoulder.y };

  const elbowBend = 8;
  const leftElbow = {
    x: (leftShoulder.x + leftHand.x) / 2 + leftArmVec.y * 0.15 - elbowBend * Math.cos(perpAngle),
    y: (leftShoulder.y + leftHand.y) / 2 - leftArmVec.x * 0.15 + elbowBend * Math.sin(perpAngle)
  };
  const rightElbow = {
    x: (rightShoulder.x + rightHand.x) / 2 - rightArmVec.y * 0.15 + elbowBend * Math.cos(perpAngle),
    y: (rightShoulder.y + rightHand.y) / 2 + rightArmVec.x * 0.15 - elbowBend * Math.sin(perpAngle)
  };

  // Knees - between hips and feet, bent slightly outward
  const kneeBend = 6;
  const leftKnee = {
    x: (leftHip.x + leftFoot.x) / 2 + kneeBend * Math.cos(perpAngle),
    y: (leftHip.y + leftFoot.y) / 2 - kneeBend * Math.sin(perpAngle)
  };
  const rightKnee = {
    x: (rightHip.x + rightFoot.x) / 2 - kneeBend * Math.cos(perpAngle),
    y: (rightHip.y + rightFoot.y) / 2 + kneeBend * Math.sin(perpAngle)
  };

  return {
    head, shoulderMid, leftShoulder, rightShoulder,
    leftElbow, rightElbow, leftHand, rightHand,
    hips, leftHip, rightHip,
    leftKnee, rightKnee, leftFoot, rightFoot
  };
}

// Draw a human-like figure from TOP-DOWN view
function drawHumanPlayer(
  ctx: CanvasRenderingContext2D,
  player: PlayerData,
  parts: BodyParts,
  color: string
): void {
  const jointRadius = 2.5;
  const headRadius = 10;

  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  // === TORSO (oval body from above) ===
  // Draw an oval connecting shoulders to hips to represent the torso
  ctx.beginPath();
  ctx.moveTo(parts.leftShoulder.x, parts.leftShoulder.y);
  ctx.lineTo(parts.leftHip.x, parts.leftHip.y);
  ctx.lineTo(parts.rightHip.x, parts.rightHip.y);
  ctx.lineTo(parts.rightShoulder.x, parts.rightShoulder.y);
  ctx.closePath();
  ctx.globalAlpha = 0.85;
  ctx.fill();
  ctx.globalAlpha = 1;
  ctx.lineWidth = 2;
  ctx.stroke();

  // === SPINE LINE (center of body) ===
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.globalAlpha = 0.9;
  ctx.beginPath();
  ctx.moveTo(parts.head.x, parts.head.y);
  ctx.lineTo(parts.shoulderMid.x, parts.shoulderMid.y);
  ctx.lineTo(parts.hips.x, parts.hips.y);
  ctx.stroke();
  ctx.globalAlpha = 1;

  // === LEFT ARM ===
  ctx.strokeStyle = color;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(parts.leftShoulder.x, parts.leftShoulder.y);
  ctx.lineTo(parts.leftElbow.x, parts.leftElbow.y);
  ctx.lineTo(parts.leftHand.x, parts.leftHand.y);
  ctx.stroke();

  // === RIGHT ARM ===
  ctx.beginPath();
  ctx.moveTo(parts.rightShoulder.x, parts.rightShoulder.y);
  ctx.lineTo(parts.rightElbow.x, parts.rightElbow.y);
  ctx.lineTo(parts.rightHand.x, parts.rightHand.y);
  ctx.stroke();

  // === LEFT LEG ===
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(parts.leftHip.x, parts.leftHip.y);
  ctx.lineTo(parts.leftKnee.x, parts.leftKnee.y);
  ctx.lineTo(parts.leftFoot.x, parts.leftFoot.y);
  ctx.stroke();

  // === RIGHT LEG ===
  ctx.beginPath();
  ctx.moveTo(parts.rightHip.x, parts.rightHip.y);
  ctx.lineTo(parts.rightKnee.x, parts.rightKnee.y);
  ctx.lineTo(parts.rightFoot.x, parts.rightFoot.y);
  ctx.stroke();

  // === HEAD (helmet from above) ===
  ctx.beginPath();
  ctx.arc(parts.head.x, parts.head.y, headRadius, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.globalAlpha = 0.9;
  ctx.fill();
  ctx.globalAlpha = 1;
  ctx.lineWidth = 2;
  ctx.strokeStyle = color;
  ctx.stroke();

  // Facemask direction indicator
  const faceDir = player.facing;
  const maskLength = 6;
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.7)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(parts.head.x, parts.head.y);
  ctx.lineTo(
    parts.head.x + Math.cos(faceDir) * maskLength,
    parts.head.y - Math.sin(faceDir) * maskLength
  );
  ctx.stroke();

  // === SHOULDER PADS (emphasize shoulders) ===
  ctx.fillStyle = color;
  ctx.globalAlpha = 1;
  ctx.beginPath();
  ctx.arc(parts.leftShoulder.x, parts.leftShoulder.y, 5, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(parts.rightShoulder.x, parts.rightShoulder.y, 5, 0, Math.PI * 2);
  ctx.fill();

  // === JOINTS (small circles at elbows and knees) ===
  ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
  [parts.leftElbow, parts.rightElbow, parts.leftKnee, parts.rightKnee].forEach(joint => {
    ctx.beginPath();
    ctx.arc(joint.x, joint.y, jointRadius, 0, Math.PI * 2);
    ctx.fill();
  });
}

export const ArmsPrototype: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | null>(null);

  // Simulation state
  const [frames, setFrames] = useState<FrameData[]>([]);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [isLoading, setIsLoading] = useState(false);

  // Configuration
  const [olWeight, setOlWeight] = useState(315);
  const [dlWeight, setDlWeight] = useState(280);
  const [olPreset, setOlPreset] = useState<string>('average_ol');
  const [dlPreset, setDlPreset] = useState<string>('average_dt');

  // Scenario selection
  const [scenario, setScenario] = useState<string>('1v1');
  const [doubleTeamTarget, setDoubleTeamTarget] = useState<string>('DT1');

  // Scenario options
  const scenarios = [
    { id: '1v1', name: '1v1', description: 'Single OL vs single DL' },
    { id: 'double_team', name: 'Double Team', description: '2 OL vs 1 DL' },
    { id: '3v2', name: '3v2 Interior', description: 'C, LG, RG vs 2 DTs' },
  ];

  // Preset options
  const olPresets = [
    { id: 'average_ol', name: 'Average OL', description: 'STR 60, AGI 45' },
    { id: 'elite_tackle', name: 'Elite Tackle', description: 'STR 80, AGI 70' },
    { id: 'mauler_guard', name: 'Mauler Guard', description: 'STR 90, AGI 50' },
    { id: 'backup_ol', name: 'Backup OL', description: 'STR 50, AGI 40' },
  ];

  const dlPresets = [
    { id: 'average_dt', name: 'Average DT', description: 'STR 65, AGI 45' },
    { id: 'elite_pass_rusher', name: 'Elite Edge', description: 'STR 75, AGI 85' },
    { id: 'power_rusher', name: 'Power Rusher', description: 'STR 95, AGI 80' },
  ];

  // View mode
  const [viewMode, setViewMode] = useState<'technical' | 'human'>('technical');

  // Arm length for extension calculations (in yards)
  const ARM_MAX_LENGTH = 0.85;

  // Canvas dimensions
  const CANVAS_WIDTH = 600;
  const CANVAS_HEIGHT = 500;
  const SCALE = 40; // pixels per yard
  const CENTER_X = CANVAS_WIDTH / 2;
  const CENTER_Y = CANVAS_HEIGHT / 2 + 50;

  // Convert simulation coords to canvas coords
  const toCanvas = useCallback((pos: Vec2): Vec2 => ({
    x: CENTER_X + pos.x * SCALE,
    y: CENTER_Y - pos.y * SCALE, // Flip Y
  }), []);

  // Run simulation
  const runSimulation = async () => {
    setIsLoading(true);
    setResult(null);
    setFrames([]);
    setCurrentFrame(0);
    setIsPlaying(false);

    try {
      const response = await fetch(`${API_BASE}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario,
          ol_weight: olWeight,
          dl_weight: dlWeight,
          ol_preset: olPreset,
          dl_preset: dlPreset,
          double_team_target: doubleTeamTarget,
          max_ticks: 200,
        }),
      });

      if (!response.ok) throw new Error('Failed to run simulation');

      const data = await response.json();
      setFrames(data.frames);
      setResult(data.result);
      setCurrentFrame(0);
      setIsPlaying(true);
    } catch (error) {
      console.error('Simulation error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Animation loop
  useEffect(() => {
    if (!isPlaying || frames.length === 0) return;

    const interval = 50 / playbackSpeed; // Base interval is 50ms

    const animate = () => {
      setCurrentFrame(prev => {
        if (prev >= frames.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    };

    const timer = setInterval(animate, interval);
    return () => clearInterval(timer);
  }, [isPlaying, frames.length, playbackSpeed]);

  // Draw frame
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.fillStyle = '#0a0c10';
    ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

    // Draw subtle grid
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
    ctx.lineWidth = 1;
    for (let x = 0; x < CANVAS_WIDTH; x += 20) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, CANVAS_HEIGHT);
      ctx.stroke();
    }
    for (let y = 0; y < CANVAS_HEIGHT; y += 20) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(CANVAS_WIDTH, y);
      ctx.stroke();
    }

    // Draw target (QB position)
    const targetPos = toCanvas({ x: 0, y: -5 });
    ctx.beginPath();
    ctx.arc(targetPos.x, targetPos.y, 12, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(255, 193, 7, 0.1)';
    ctx.fill();
    ctx.strokeStyle = TARGET_COLOR;
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 4]);
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw "QB" label
    ctx.font = '600 10px "JetBrains Mono", monospace';
    ctx.fillStyle = TARGET_COLOR;
    ctx.textAlign = 'center';
    ctx.fillText('QB', targetPos.x, targetPos.y + 4);

    // Draw LOS
    const losY = toCanvas({ x: 0, y: 0 }).y;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
    ctx.lineWidth = 1;
    ctx.setLineDash([8, 4]);
    ctx.beginPath();
    ctx.moveTo(0, losY);
    ctx.lineTo(CANVAS_WIDTH, losY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw "LOS" label
    ctx.font = '500 9px "JetBrains Mono", monospace';
    ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.textAlign = 'left';
    ctx.fillText('LOS', 8, losY - 6);

    if (frames.length === 0 || !frames[currentFrame]) return;

    const frame = frames[currentFrame];

    // Draw players
    Object.entries(frame.players).forEach(([id, player]) => {
      const isOL = player.role === 'blocker';
      const color = isOL ? OL_COLOR : DL_COLOR;
      const glow = isOL ? 'rgba(33, 150, 243, 0.4)' : 'rgba(244, 67, 54, 0.4)';

      // Convert positions
      const center = toCanvas(player.position);
      const leftShoulder = toCanvas(player.left_shoulder);
      const rightShoulder = toCanvas(player.right_shoulder);
      const leftHand = toCanvas({ x: player.left_hand.x, y: player.left_hand.y });
      const rightHand = toCanvas({ x: player.right_hand.x, y: player.right_hand.y });
      const leftFoot = player.left_foot ? toCanvas({ x: player.left_foot.x, y: player.left_foot.y }) : null;
      const rightFoot = player.right_foot ? toCanvas({ x: player.right_foot.x, y: player.right_foot.y }) : null;

      // Draw glow
      const gradient = ctx.createRadialGradient(
        center.x, center.y, 0,
        center.x, center.y, 30
      );
      gradient.addColorStop(0, glow);
      gradient.addColorStop(1, 'transparent');
      ctx.fillStyle = gradient;
      ctx.fillRect(center.x - 30, center.y - 30, 60, 60);

      // Hand colors (used by both modes)
      const leftHandColor = HAND_COLORS[player.left_hand.state] || '#5f6368';
      const rightHandColor = HAND_COLORS[player.right_hand.state] || '#5f6368';

      // Foot colors (used by both modes)
      const leftFootColor = player.left_foot ? (FOOT_COLORS[player.left_foot.phase] || '#5f6368') : '#5f6368';
      const rightFootColor = player.right_foot ? (FOOT_COLORS[player.right_foot.phase] || '#5f6368') : '#5f6368';

      if (viewMode === 'human') {
        // ========== HUMAN MODE ==========
        // Draw stick figure with proper body parts
        const parts = deriveBodyParts(player, toCanvas);
        drawHumanPlayer(ctx, player, parts, color);

        // Draw feet with state colors (on top of leg endpoints)
        if (leftFoot && rightFoot && player.left_foot && player.right_foot) {
          // Left foot - oval shape
          ctx.save();
          ctx.translate(parts.leftFoot.x, parts.leftFoot.y);
          ctx.rotate(-player.facing);
          ctx.beginPath();
          ctx.ellipse(0, 0, 5, 8, 0, 0, Math.PI * 2);
          ctx.fillStyle = leftFootColor;
          ctx.globalAlpha = 0.7 + player.left_foot.weight * 0.3;
          ctx.fill();
          ctx.globalAlpha = 1;
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
          ctx.lineWidth = 1;
          ctx.stroke();
          ctx.restore();

          // Right foot - oval shape
          ctx.save();
          ctx.translate(parts.rightFoot.x, parts.rightFoot.y);
          ctx.rotate(-player.facing);
          ctx.beginPath();
          ctx.ellipse(0, 0, 5, 8, 0, 0, Math.PI * 2);
          ctx.fillStyle = rightFootColor;
          ctx.globalAlpha = 0.7 + player.right_foot.weight * 0.3;
          ctx.fill();
          ctx.globalAlpha = 1;
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
          ctx.lineWidth = 1;
          ctx.stroke();
          ctx.restore();
        }

        // Draw hands with state colors (on top of arm endpoints)
        ctx.beginPath();
        ctx.arc(parts.leftHand.x, parts.leftHand.y, 6, 0, Math.PI * 2);
        ctx.fillStyle = leftHandColor;
        ctx.fill();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.lineWidth = 1;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(parts.rightHand.x, parts.rightHand.y, 6, 0, Math.PI * 2);
        ctx.fillStyle = rightHandColor;
        ctx.fill();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.lineWidth = 1;
        ctx.stroke();

      } else {
        // ========== TECHNICAL MODE ==========
        // Draw feet (below the body visually)
        if (leftFoot && rightFoot && player.left_foot && player.right_foot) {
          // Draw step targets if stepping
          if (player.left_foot.step_target) {
            const leftTarget = toCanvas(player.left_foot.step_target);
            ctx.beginPath();
            ctx.arc(leftTarget.x, leftTarget.y, 5, 0, Math.PI * 2);
            ctx.strokeStyle = leftFootColor;
            ctx.lineWidth = 1;
            ctx.setLineDash([2, 2]);
            ctx.stroke();
            ctx.setLineDash([]);
          }
          if (player.right_foot.step_target) {
            const rightTarget = toCanvas(player.right_foot.step_target);
            ctx.beginPath();
            ctx.arc(rightTarget.x, rightTarget.y, 5, 0, Math.PI * 2);
            ctx.strokeStyle = rightFootColor;
            ctx.lineWidth = 1;
            ctx.setLineDash([2, 2]);
            ctx.stroke();
            ctx.setLineDash([]);
          }

          // Stance line connecting feet
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
          ctx.lineWidth = 1;
          ctx.setLineDash([3, 3]);
          ctx.beginPath();
          ctx.moveTo(leftFoot.x, leftFoot.y);
          ctx.lineTo(rightFoot.x, rightFoot.y);
          ctx.stroke();
          ctx.setLineDash([]);

          // Left foot - oval shape
          ctx.save();
          ctx.translate(leftFoot.x, leftFoot.y);
          ctx.rotate(-player.facing);
          ctx.beginPath();
          ctx.ellipse(0, 0, 4, 7, 0, 0, Math.PI * 2);
          ctx.fillStyle = leftFootColor;
          ctx.globalAlpha = 0.6 + player.left_foot.weight * 0.4;
          ctx.fill();
          ctx.globalAlpha = 1;
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
          ctx.lineWidth = 1;
          ctx.stroke();
          ctx.restore();

          // Right foot - oval shape
          ctx.save();
          ctx.translate(rightFoot.x, rightFoot.y);
          ctx.rotate(-player.facing);
          ctx.beginPath();
          ctx.ellipse(0, 0, 4, 7, 0, 0, Math.PI * 2);
          ctx.fillStyle = rightFootColor;
          ctx.globalAlpha = 0.6 + player.right_foot.weight * 0.4;
          ctx.fill();
          ctx.globalAlpha = 1;
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
          ctx.lineWidth = 1;
          ctx.stroke();
          ctx.restore();
        }

        // Draw body (torso rectangle)
        ctx.save();
        ctx.translate(center.x, center.y);
        ctx.rotate(-player.facing); // Canvas rotation is opposite

        // Body dimensions (approximate)
        const bodyWidth = 0.5 * SCALE;
        const bodyDepth = 0.3 * SCALE;

        // Fill body
        ctx.fillStyle = color;
        ctx.globalAlpha = 0.3;
        ctx.fillRect(-bodyWidth / 2, -bodyDepth / 2, bodyWidth, bodyDepth);
        ctx.globalAlpha = 1;

        // Stroke body
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(-bodyWidth / 2, -bodyDepth / 2, bodyWidth, bodyDepth);

        ctx.restore();

        // Draw shoulders as circles
        ctx.beginPath();
        ctx.arc(leftShoulder.x, leftShoulder.y, 4, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(rightShoulder.x, rightShoulder.y, 4, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();

        // Draw arms (lines from shoulders to hands)
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
        ctx.lineWidth = 3;
        ctx.lineCap = 'round';

        ctx.beginPath();
        ctx.moveTo(leftShoulder.x, leftShoulder.y);
        ctx.lineTo(leftHand.x, leftHand.y);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(rightShoulder.x, rightShoulder.y);
        ctx.lineTo(rightHand.x, rightHand.y);
        ctx.stroke();

        // Draw hands
        ctx.beginPath();
        ctx.arc(leftHand.x, leftHand.y, 6, 0, Math.PI * 2);
        ctx.fillStyle = leftHandColor;
        ctx.fill();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.lineWidth = 1;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(rightHand.x, rightHand.y, 6, 0, Math.PI * 2);
        ctx.fillStyle = rightHandColor;
        ctx.fill();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Draw facing direction arrow
        const arrowLength = 15;
        const arrowEnd = {
          x: center.x + Math.cos(player.facing) * arrowLength,
          y: center.y - Math.sin(player.facing) * arrowLength,
        };

        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(center.x, center.y);
        ctx.lineTo(arrowEnd.x, arrowEnd.y);
        ctx.stroke();

        // Arrowhead
        const arrowAngle = Math.atan2(center.y - arrowEnd.y, arrowEnd.x - center.x);
        ctx.beginPath();
        ctx.moveTo(arrowEnd.x, arrowEnd.y);
        ctx.lineTo(
          arrowEnd.x - 6 * Math.cos(arrowAngle - Math.PI / 6),
          arrowEnd.y + 6 * Math.sin(arrowAngle - Math.PI / 6)
        );
        ctx.lineTo(
          arrowEnd.x - 6 * Math.cos(arrowAngle + Math.PI / 6),
          arrowEnd.y + 6 * Math.sin(arrowAngle + Math.PI / 6)
        );
        ctx.closePath();
        ctx.fillStyle = color;
        ctx.fill();
      }

      // Draw player label
      ctx.font = '700 11px "Bebas Neue", sans-serif';
      ctx.fillStyle = color;
      ctx.textAlign = 'center';
      ctx.fillText(id, center.x, center.y - 25);

      // Draw block type label for multi-player scenarios
      if (frame.assignments && frame.assignments[id]) {
        const assignment = frame.assignments[id];
        if (assignment.block_type === 'double_post' || assignment.block_type === 'double_drive') {
          const label = assignment.block_type === 'double_post' ? 'POST' : 'DRIVE';
          ctx.font = '600 8px "JetBrains Mono", monospace';
          ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
          ctx.textAlign = 'center';
          ctx.fillText(label, center.x, center.y + 35);
        }
      }
    });

    // Draw assignment lines (from blockers to their targets)
    if (frame.assignments) {
      ctx.setLineDash([4, 4]);
      ctx.lineWidth = 1;

      Object.entries(frame.assignments).forEach(([blockerId, assignment]) => {
        if (!assignment.target_id) return;

        const blocker = frame.players[blockerId];
        const target = frame.players[assignment.target_id];
        if (!blocker || !target) return;

        const blockerPos = toCanvas(blocker.position);
        const targetPos = toCanvas(target.position);

        // Assignment line color based on block type
        let lineColor = 'rgba(255, 255, 255, 0.2)';
        if (assignment.block_type === 'double_post') {
          lineColor = 'rgba(105, 240, 174, 0.4)'; // Green for post
        } else if (assignment.block_type === 'double_drive') {
          lineColor = 'rgba(255, 193, 7, 0.4)'; // Gold for drive
        }

        ctx.strokeStyle = lineColor;
        ctx.beginPath();
        ctx.moveTo(blockerPos.x, blockerPos.y);
        ctx.lineTo(targetPos.x, targetPos.y);
        ctx.stroke();
      });

      ctx.setLineDash([]);
    }

    // Draw double team indicators (arc connecting blockers)
    if (frame.double_teams) {
      Object.entries(frame.double_teams).forEach(([dlId, dt]) => {
        if (!dt.active) return;

        const post = frame.players[dt.post_blocker_id];
        const drive = frame.players[dt.drive_blocker_id];
        const target = frame.players[dlId];
        if (!post || !drive || !target) return;

        const postPos = toCanvas(post.position);
        const drivePos = toCanvas(drive.position);
        const targetPos = toCanvas(target.position);

        // Draw arc connecting the two blockers
        ctx.strokeStyle = 'rgba(255, 193, 7, 0.6)';
        ctx.lineWidth = 2;
        ctx.setLineDash([]);

        // Draw curved line between post and drive blockers
        const midX = (postPos.x + drivePos.x) / 2;
        const midY = (postPos.y + drivePos.y) / 2;
        const ctrlX = midX + (targetPos.x - midX) * 0.3;
        const ctrlY = midY + (targetPos.y - midY) * 0.3;

        ctx.beginPath();
        ctx.moveTo(postPos.x, postPos.y);
        ctx.quadraticCurveTo(ctrlX, ctrlY, drivePos.x, drivePos.y);
        ctx.stroke();

        // Draw "2v1" label
        ctx.font = '600 10px "JetBrains Mono", monospace';
        ctx.fillStyle = 'rgba(255, 193, 7, 0.9)';
        ctx.textAlign = 'center';
        ctx.fillText('2v1', midX, midY - 10);
      });
    }

    // Draw shed indicator for players who beat their block
    if (frame.shed_players && frame.shed_players.length > 0) {
      frame.shed_players.forEach(playerId => {
        const player = frame.players[playerId];
        if (!player) return;

        const pos = toCanvas(player.position);

        // Draw "FREE" indicator
        ctx.font = '700 10px "JetBrains Mono", monospace';
        ctx.fillStyle = '#ff5252';
        ctx.textAlign = 'center';
        ctx.fillText('FREE', pos.x, pos.y - 40);
      });
    }

    // Draw tick/time info
    ctx.font = '500 11px "JetBrains Mono", monospace';
    ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
    ctx.textAlign = 'right';
    ctx.fillText(
      `TICK ${frame.tick} | ${frame.time.toFixed(2)}s`,
      CANVAS_WIDTH - 12,
      20
    );
  }, [frames, currentFrame, toCanvas, viewMode]);

  // Get current frame data for stats
  const currentData = frames[currentFrame];

  return (
    <div className="arms-prototype">
      <header className="arms-header">
        <div>
          <h1>ARMS PROTOTYPE</h1>
          <div className="arms-header-subtitle">
            {scenario === '1v1' && '1v1 OL/DL Physics Simulation'}
            {scenario === 'double_team' && 'Double Team (2v1) Simulation'}
            {scenario === '3v2' && '3v2 Interior Line Simulation'}
          </div>
        </div>
      </header>

      <main className="arms-main">
        <div className="arms-canvas-container">
          {/* Status badge */}
          <div className={`arms-live-badge ${isPlaying ? 'running' : result ? 'ended' : 'paused'}`}>
            {isPlaying ? 'LIVE' : result ? 'COMPLETE' : 'READY'}
          </div>

          <canvas
            ref={canvasRef}
            className="arms-canvas"
            width={CANVAS_WIDTH}
            height={CANVAS_HEIGHT}
          />

          {/* Result overlay */}
          {result && !isPlaying && currentFrame >= frames.length - 1 && (
            <div className={`arms-result-overlay ${result.rusher_won ? 'rusher-won' : 'blocker-held'}`}>
              <div className="arms-result-title">
                {result.rusher_won ? 'PRESSURE!' : 'PROTECTION'}
              </div>
              <div className="arms-result-time">
                {result.time.toFixed(2)}s ({result.ticks} ticks)
              </div>
            </div>
          )}
        </div>

        <aside className="arms-sidebar">
          {/* Controls */}
          <div className="arms-controls">
            <div className="arms-controls-title">PLAYBACK</div>

            <div className="arms-playback">
              <button
                className="arms-btn primary"
                onClick={runSimulation}
                disabled={isLoading}
              >
                {isLoading ? '...' : 'RUN'}
              </button>

              <button
                className="arms-btn"
                onClick={() => setIsPlaying(!isPlaying)}
                disabled={frames.length === 0}
              >
                {isPlaying ? (
                  <svg viewBox="0 0 24 24" fill="currentColor">
                    <rect x="6" y="4" width="4" height="16" />
                    <rect x="14" y="4" width="4" height="16" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" fill="currentColor">
                    <polygon points="5,3 19,12 5,21" />
                  </svg>
                )}
              </button>

              <button
                className="arms-btn"
                onClick={() => setCurrentFrame(prev => Math.min(prev + 1, frames.length - 1))}
                disabled={frames.length === 0}
              >
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5,5 15,12 5,19" />
                  <rect x="15" y="5" width="3" height="14" />
                </svg>
              </button>

              <button
                className="arms-btn"
                onClick={() => {
                  setCurrentFrame(0);
                  setIsPlaying(false);
                }}
                disabled={frames.length === 0}
              >
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <rect x="4" y="4" width="3" height="16" />
                  <polygon points="20,4 8,12 20,20" />
                </svg>
              </button>
            </div>

            <div className="arms-speed-control">
              <label>SPEED</label>
              <input
                type="range"
                min="0.25"
                max="4"
                step="0.25"
                value={playbackSpeed}
                onChange={(e) => setPlaybackSpeed(parseFloat(e.target.value))}
              />
              <span className="arms-speed-value">{playbackSpeed}x</span>
            </div>

            <div className="arms-view-toggle">
              <label>VIEW</label>
              <div className="arms-view-buttons">
                <button
                  className={`arms-btn ${viewMode === 'technical' ? 'active' : ''}`}
                  onClick={() => setViewMode('technical')}
                >
                  Technical
                </button>
                <button
                  className={`arms-btn ${viewMode === 'human' ? 'active' : ''}`}
                  onClick={() => setViewMode('human')}
                >
                  Human
                </button>
              </div>
            </div>

            {/* Scenario Selector */}
            <div className="arms-scenario-section">
              <label className="arms-scenario-label">SCENARIO</label>
              <div className="arms-scenario-buttons">
                {scenarios.map(s => (
                  <button
                    key={s.id}
                    className={`arms-btn scenario ${scenario === s.id ? 'active' : ''}`}
                    onClick={() => setScenario(s.id)}
                    title={s.description}
                  >
                    {s.name}
                  </button>
                ))}
              </div>
              <span className="arms-scenario-desc">
                {scenarios.find(s => s.id === scenario)?.description}
              </span>
            </div>

            {/* 3v2 Options */}
            {scenario === '3v2' && (
              <div className="arms-3v2-options">
                <label className="arms-preset-label">DOUBLE TEAM TARGET</label>
                <div className="arms-double-target-buttons">
                  <button
                    className={`arms-btn ${doubleTeamTarget === 'DT1' ? 'active' : ''}`}
                    onClick={() => setDoubleTeamTarget('DT1')}
                  >
                    DT1 (Left)
                  </button>
                  <button
                    className={`arms-btn ${doubleTeamTarget === 'DT2' ? 'active' : ''}`}
                    onClick={() => setDoubleTeamTarget('DT2')}
                  >
                    DT2 (Right)
                  </button>
                </div>
              </div>
            )}

            {/* Player Presets */}
            <div className="arms-presets">
              <div className="arms-preset-group">
                <label className="arms-preset-label ol">OL TYPE</label>
                <select
                  className="arms-preset-select ol"
                  value={olPreset}
                  onChange={(e) => setOlPreset(e.target.value)}
                >
                  {olPresets.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
                <span className="arms-preset-desc">
                  {olPresets.find(p => p.id === olPreset)?.description}
                </span>
              </div>

              <div className="arms-preset-group">
                <label className="arms-preset-label dl">DL TYPE</label>
                <select
                  className="arms-preset-select dl"
                  value={dlPreset}
                  onChange={(e) => setDlPreset(e.target.value)}
                >
                  {dlPresets.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
                <span className="arms-preset-desc">
                  {dlPresets.find(p => p.id === dlPreset)?.description}
                </span>
              </div>
            </div>

            {frames.length > 0 && (
              <div className="arms-timeline">
                <label>FRAME</label>
                <input
                  type="range"
                  min="0"
                  max={frames.length - 1}
                  value={currentFrame}
                  onChange={(e) => {
                    setCurrentFrame(parseInt(e.target.value));
                    setIsPlaying(false);
                  }}
                />
                <div className="arms-timeline-info">
                  <span>Frame {currentFrame + 1} / {frames.length}</span>
                  <span>{currentData?.time.toFixed(2)}s</span>
                </div>
              </div>
            )}
          </div>

          {/* Stats */}
          <div className="arms-stats">
            <div className="arms-stats-section">
              <div className="arms-stats-title">PLAYER STATUS</div>

              {currentData?.players && Object.entries(currentData.players).map(([id, player]) => (
                <div key={id} className={`arms-player-card ${player.role === 'blocker' ? 'ol' : 'dl'}`}>
                  <div className="arms-player-header">
                    <span className="arms-player-name">{id}</span>
                    <span className="arms-player-role">
                      {player.role === 'blocker' ? 'BLOCKER' : 'RUSHER'}
                    </span>
                  </div>

                  <div className="arms-stat-bar-container">
                    <div className="arms-stat-row">
                      <span className="arms-stat-label">Balance</span>
                      <span className="arms-stat-value">{(player.balance * 100).toFixed(0)}%</span>
                    </div>
                    <div className="arms-stat-bar">
                      <div
                        className="arms-stat-bar-fill balance"
                        style={{ width: `${player.balance * 100}%` }}
                      />
                    </div>
                  </div>

                  <div className="arms-stat-bar-container">
                    <div className="arms-stat-row">
                      <span className="arms-stat-label">Pad Level</span>
                      <span className="arms-stat-value">{(player.pad_level * 100).toFixed(0)}%</span>
                    </div>
                    <div className="arms-stat-bar">
                      <div
                        className="arms-stat-bar-fill pad-level"
                        style={{ width: `${player.pad_level * 100}%` }}
                      />
                    </div>
                  </div>

                  <div className="arms-hands-display">
                    <div className={`arms-hand ${player.left_hand.state}`}>
                      <div className="arms-hand-label">L</div>
                      <div className="arms-hand-state">{player.left_hand.state}</div>
                    </div>
                    <div className={`arms-hand ${player.right_hand.state}`}>
                      <div className="arms-hand-label">R</div>
                      <div className="arms-hand-state">{player.right_hand.state}</div>
                    </div>
                  </div>

                  {/* Feet display */}
                  {player.left_foot && player.right_foot && (
                    <>
                      <div className="arms-feet-header">FEET</div>
                      <div className="arms-feet-display">
                        <div className={`arms-foot ${player.left_foot.phase}`}>
                          <div className="arms-foot-label">L</div>
                          <div className="arms-foot-phase">{player.left_foot.phase}</div>
                          <div className="arms-foot-weight">{(player.left_foot.weight * 100).toFixed(0)}%</div>
                          {player.left_foot.cycle_progress > 0 && (
                            <div className="arms-foot-cycle">
                              <div
                                className="arms-foot-cycle-fill"
                                style={{ width: `${player.left_foot.cycle_progress * 100}%` }}
                              />
                            </div>
                          )}
                        </div>
                        <div className={`arms-foot ${player.right_foot.phase}`}>
                          <div className="arms-foot-label">R</div>
                          <div className="arms-foot-phase">{player.right_foot.phase}</div>
                          <div className="arms-foot-weight">{(player.right_foot.weight * 100).toFixed(0)}%</div>
                          {player.right_foot.cycle_progress > 0 && (
                            <div className="arms-foot-cycle">
                              <div
                                className="arms-foot-cycle-fill"
                                style={{ width: `${player.right_foot.cycle_progress * 100}%` }}
                              />
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="arms-stance-info">
                        <span>Width: {(player.stance_width * 36).toFixed(0)}"</span>
                        <span>Grounded: {player.grounded_count}/2</span>
                      </div>
                      {/* Force Debt indicator */}
                      {player.force_debt && (
                        <div className="arms-force-debt">
                          <div className="arms-force-debt-label">
                            Force Debt: {(player.force_debt.magnitude * 100).toFixed(0)}%
                          </div>
                          <div className="arms-force-debt-bar">
                            <div
                              className="arms-force-debt-fill"
                              style={{
                                width: `${Math.min(100, player.force_debt.magnitude * 200)}%`,
                                background: player.force_debt.magnitude > 0.3
                                  ? '#ff5252'
                                  : player.force_debt.magnitude > 0.15
                                    ? '#ffc107'
                                    : '#69f0ae'
                              }}
                            />
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Arm Mechanics Diagram */}
          <div className="arms-mechanics">
            <div className="arms-mechanics-title">ARM POWER CURVE</div>
            <div className="arms-power-diagram">
              <svg viewBox="0 0 200 80" className="arms-power-svg">
                {/* Background grid */}
                <line x1="30" y1="10" x2="30" y2="60" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
                <line x1="30" y1="60" x2="190" y2="60" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />

                {/* Power curve (bell curve centered at 50% extension) */}
                <path
                  d="M 30 55 Q 70 55, 90 20 Q 110 55, 130 55 Q 150 55, 170 50 L 190 55"
                  fill="none"
                  stroke="url(#powerGradient)"
                  strokeWidth="2"
                />
                <defs>
                  <linearGradient id="powerGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#ff5252" />
                    <stop offset="35%" stopColor="#ffc107" />
                    <stop offset="50%" stopColor="#69f0ae" />
                    <stop offset="65%" stopColor="#ffc107" />
                    <stop offset="100%" stopColor="#ff5252" />
                  </linearGradient>
                </defs>

                {/* Labels */}
                <text x="30" y="72" fill="rgba(255,255,255,0.5)" fontSize="8" fontFamily="JetBrains Mono">0%</text>
                <text x="105" y="72" fill="rgba(255,255,255,0.5)" fontSize="8" fontFamily="JetBrains Mono" textAnchor="middle">50%</text>
                <text x="185" y="72" fill="rgba(255,255,255,0.5)" fontSize="8" fontFamily="JetBrains Mono" textAnchor="end">100%</text>
                <text x="15" y="20" fill="rgba(255,255,255,0.5)" fontSize="7" fontFamily="JetBrains Mono" transform="rotate(-90, 15, 35)">POWER</text>

                {/* Optimal zone highlight */}
                <rect x="75" y="8" width="50" height="55" fill="rgba(105, 240, 174, 0.1)" rx="2" />
                <text x="100" y="6" fill="#69f0ae" fontSize="6" fontFamily="JetBrains Mono" textAnchor="middle">OPTIMAL</text>
              </svg>
              <div className="arms-power-explanation">
                Arms are strongest at ~50% extension (bent elbows). Fully extended or retracted = weaker.
              </div>
            </div>

            {/* Arm diagrams for current players */}
            {currentData?.players && Object.entries(currentData.players).map(([id, player]) => {
              const leftExt = calculateArmExtension(player.left_shoulder, { x: player.left_hand.x, y: player.left_hand.y }, ARM_MAX_LENGTH);
              const rightExt = calculateArmExtension(player.right_shoulder, { x: player.right_hand.x, y: player.right_hand.y }, ARM_MAX_LENGTH);
              const leftPower = calculateEffectivePower(leftExt);
              const rightPower = calculateEffectivePower(rightExt);
              const isOL = player.role === 'blocker';

              return (
                <div key={id} className={`arms-arm-detail ${isOL ? 'ol' : 'dl'}`}>
                  <div className="arms-arm-detail-header">{id} ARM STATUS</div>
                  <div className="arms-arm-bars">
                    <div className="arms-arm-bar-group">
                      <div className="arms-arm-bar-label">L EXT</div>
                      <div className="arms-arm-bar">
                        <div
                          className="arms-arm-bar-fill"
                          style={{
                            width: `${leftExt * 100}%`,
                            background: leftExt > 0.4 && leftExt < 0.6 ? '#69f0ae' : leftExt > 0.3 && leftExt < 0.7 ? '#ffc107' : '#ff5252'
                          }}
                        />
                        <div className="arms-arm-bar-marker" style={{ left: '50%' }} />
                      </div>
                      <div className="arms-arm-power">{(leftPower * 100).toFixed(0)}%</div>
                    </div>
                    <div className="arms-arm-bar-group">
                      <div className="arms-arm-bar-label">R EXT</div>
                      <div className="arms-arm-bar">
                        <div
                          className="arms-arm-bar-fill"
                          style={{
                            width: `${rightExt * 100}%`,
                            background: rightExt > 0.4 && rightExt < 0.6 ? '#69f0ae' : rightExt > 0.3 && rightExt < 0.7 ? '#ffc107' : '#ff5252'
                          }}
                        />
                        <div className="arms-arm-bar-marker" style={{ left: '50%' }} />
                      </div>
                      <div className="arms-arm-power">{(rightPower * 100).toFixed(0)}%</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Physics Info */}
          <div className="arms-physics-info">
            <div className="arms-physics-title">KEY MECHANICS</div>
            <div className="arms-physics-items">
              <div className="arms-physics-item">
                <div className="arms-physics-icon">&#x2693;</div>
                <div className="arms-physics-text">
                  <strong>Pad Level</strong>
                  <span>Lower = better leverage. High pad level is vulnerable.</span>
                </div>
              </div>
              <div className="arms-physics-item">
                <div className="arms-physics-icon">&#x270B;</div>
                <div className="arms-physics-text">
                  <strong>Inside Hands</strong>
                  <span>Hands on chest = control. Outside hands get controlled.</span>
                </div>
              </div>
              <div className="arms-physics-item">
                <div className="arms-physics-icon">&#x2696;</div>
                <div className="arms-physics-text">
                  <strong>Balance</strong>
                  <span>Affected by hits. Low balance = falling over.</span>
                </div>
              </div>
              <div className="arms-physics-item">
                <div className="arms-physics-icon">&#x1F4AA;</div>
                <div className="arms-physics-text">
                  <strong>Mass</strong>
                  <span>Heavier = harder to move. OL: {olWeight}lbs, DL: {dlWeight}lbs</span>
                </div>
              </div>
              <div className="arms-physics-item">
                <div className="arms-physics-icon">&#x1F463;</div>
                <div className="arms-physics-text">
                  <strong>Footwork</strong>
                  <span>Linemen pump feet continuously. Grounded = power. Airborne = vulnerable.</span>
                </div>
              </div>
              <div className="arms-physics-item">
                <div className="arms-physics-icon">&#x26A1;</div>
                <div className="arms-physics-text">
                  <strong>Force Debt</strong>
                  <span>Accumulated force not absorbed by stepping. High debt = losing balance.</span>
                </div>
              </div>
            </div>
          </div>

          {/* Legend */}
          <div className="arms-legend">
            <div className="arms-legend-title">HAND STATES</div>
            <div className="arms-legend-items">
              <div className="arms-legend-item">
                <div className="arms-legend-color" style={{ background: HAND_COLORS.free }} />
                <span>Free</span>
              </div>
              <div className="arms-legend-item">
                <div className="arms-legend-color" style={{ background: HAND_COLORS.reaching }} />
                <span>Reaching</span>
              </div>
              <div className="arms-legend-item">
                <div className="arms-legend-color" style={{ background: HAND_COLORS.controlling }} />
                <span>Controlling</span>
              </div>
              <div className="arms-legend-item">
                <div className="arms-legend-color" style={{ background: HAND_COLORS.controlled }} />
                <span>Controlled</span>
              </div>
              <div className="arms-legend-item">
                <div className="arms-legend-color" style={{ background: HAND_COLORS.locked }} />
                <span>Locked</span>
              </div>
            </div>
            <div className="arms-legend-title" style={{ marginTop: '12px' }}>FOOT PHASES</div>
            <div className="arms-legend-items">
              <div className="arms-legend-item">
                <div className="arms-legend-color" style={{ background: FOOT_COLORS.grounded }} />
                <span>Grounded</span>
              </div>
              <div className="arms-legend-item">
                <div className="arms-legend-color" style={{ background: FOOT_COLORS.lifting }} />
                <span>Lifting</span>
              </div>
              <div className="arms-legend-item">
                <div className="arms-legend-color" style={{ background: FOOT_COLORS.airborne }} />
                <span>Airborne</span>
              </div>
              <div className="arms-legend-item">
                <div className="arms-legend-color" style={{ background: FOOT_COLORS.planting }} />
                <span>Planting</span>
              </div>
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
};

export default ArmsPrototype;
