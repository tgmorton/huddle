# Ball Flight Physics - Frontend Visualization Guide

## Overview

The backend now sends realistic ball flight physics data based on the Dzielski & Blackburn paper. This data enables visualizing spin, wobble, and orientation during passes.

## New Data in BallFrame

```typescript
interface BallFrame {
  // ... existing fields ...

  // NEW: Ball flight physics
  spin_rate?: number;        // RPM (500+ = tight spiral)
  is_stable?: boolean;       // false = wobbly pass
  orientation?: {
    x: number;  // Lateral component
    y: number;  // Downfield component
    z: number;  // Vertical tilt (-0.3 to +0.3)
  };
}
```

## What Each Field Means

| Field | When Present | Values | Visual Meaning |
|-------|--------------|--------|----------------|
| `spin_rate` | In flight only | 350-650 RPM | Higher = tighter spiral |
| `is_stable` | Always | true/false | false = pass is wobbling |
| `orientation.z` | In flight | +0.3 → -0.3 | Nose-up at release, nose-down at catch |

## Already Implemented in BallRenderer.ts

I've added basic visualization in `BallRenderer.ts`:

1. **Physics-based rotation**: Ball orientation follows `orientation.x/y` instead of just movement direction
2. **Wobble animation**: When `is_stable === false`, the ball oscillates ±11° at ~5Hz
3. **Orange warning glow**: Wobbly passes get an orange tint behind the normal glow

## Visualization Ideas for Enhancement

### 1. Spin Trail Effect
Show a spiral trail behind the ball during flight:
```typescript
if (ball.spin_rate && ball.spin_rate > 400) {
  // Draw fading spiral trail
  // Tighter spiral for higher spin_rate
}
```

### 2. Nose Tilt Visualization
The `orientation.z` value shows nose angle:
- Start of throw: `z ≈ +0.3` (nose up)
- Apex: `z ≈ 0` (level)
- End of throw: `z ≈ -0.3` (nose down)

Could adjust the ball's visual pitch/perspective based on this.

### 3. Wobbly Pass Indicator
Current: Orange glow when `is_stable === false`

Enhanced options:
- Erratic trail pattern
- Ball shape distortion (slight stretching)
- Sound effect cue
- Commentary trigger ("wobbly pass!")

### 4. Spin Speed Visualization
```typescript
// Visual spin rate indicator
const spinQuality = ball.spin_rate ? ball.spin_rate / 600 : 1; // 0-1 scale
// Could affect:
// - Lace blur amount
// - Trail tightness
// - Ball glow intensity
```

## When to Expect Wobbly Passes

Wobbly passes (`is_stable: false`) occur when:
- Weak-armed QB (low throw_power) + deep throw
- LOB passes at distance
- Low spin rate falls below critical threshold (7.39 × velocity_mph)

Example: A QB with throw_power=60 throwing a 40-yard lob may produce a wobbly pass.

## Testing

To see the physics in action:
1. Run a game with a weak-armed QB
2. Force deep throws (LOB type)
3. Watch for `is_stable: false` in the ball data
4. Verify wobble animation and orange glow appear

Let me know if you need any clarification on the data format or have ideas for enhanced visualization!
