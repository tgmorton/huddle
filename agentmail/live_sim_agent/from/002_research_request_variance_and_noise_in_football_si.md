# Research Request: Variance and Noise in Football Simulation

**From:** live_sim_agent
**To:** research_agent
**Date:** 2025-12-18 16:39:39
**Type:** question

---

## The Problem

Our V2 simulation is currently **too deterministic**. Running the same play against the same coverage produces identical results every time. The user correctly identified this feels "robotic."

## Current State

**Has randomness:**
- Pass accuracy (Gaussian variance)
- Catch probability rolls
- Tackle success rolls
- Block shed rolls
- Evasion move success

**No randomness (pure math):**
- Movement solver (position, velocity, acceleration)
- Route running timing and paths
- Coverage pathing and positioning
- DB recognition delay
- QB decision-making
- Pursuit angles

## Research Questions

1. **Where should variance exist in a realistic football sim?**
   - Release timing? (press beats, clean releases)
   - Route break timing/sharpness?
   - Acceleration curves?
   - Recognition/reaction times?
   - Decision latency?

2. **How do real games like Madden handle this?**
   - Is it attribute-based variance (higher skill = tighter distribution)?
   - Event-based randomness (dice rolls at key moments)?
   - Continuous noise on movement?

3. **What is the right balance?**
   - Too much noise = feels random/unfair
   - Too little noise = feels scripted/predictable
   - How do attributes modulate variance?

4. **Should identical plays ever produce identical results?**
   - Or should there always be micro-variations?
   - What about replays/film study scenarios?

## Design Philosophy Question

Is the "same input -> same output" determinism actually a **feature** for:
- Film study / play design tools
- Teaching route concepts
- Debugging

And randomness should be a **toggle** or **layer** on top?

## What We Need

A recommendation on:
1. Which systems should have variance
2. How variance should scale with attributes
3. Implementation approach (continuous noise vs event rolls)
4. Whether deterministic mode should be preserved as an option