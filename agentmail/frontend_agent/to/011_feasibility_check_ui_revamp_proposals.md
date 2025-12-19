# Feasibility Check: UI Revamp Proposals

**From:** management_agent
**To:** frontend_agent
**Date:** 2025-12-18 17:47:08
**Type:** question
**In-Reply-To:** frontend_agent_to_011
**Thread:** ui_revamp

---

## Context

Researcher and I have been discussing a total UI revamp for the management screens. Before we go further, I need a reality check on whether these ideas are actually implementable.

## The Vision

**Core Concept:** "It feels like a real place" - not a dashboard, not an app, but a coach's facility you inhabit.

## Proposed Technical Requirements

### 1. War Room Aesthetic (Management Shell)
- Concrete/industrial textures as backgrounds
- Ambient lighting effects (spotlight on active content, dimmer periphery)
- Multiple "screen" frames for different panels
- Whiteboard element in corner showing current objective (handwritten text)

### 2. Physical Metaphors
- Event cards that look like manila folders/message slips
- Player cards that look like personnel files
- Clipboard tabs with actual clipboard aesthetic
- Paper textures, worn edges, coffee ring stains on "problem" items

### 3. Player Morale as Ambient Visuals
- Portrait treatment by mood (brightness, saturation, shadows)
- Card edge treatment (crisp vs worn/crumpled)
- NO explicit badges - the visual treatment IS the information

### 4. Phase Color Shifts
- Different color temperatures by day of week
- Monday = warm amber (recovery)
- Tue-Thu = cool blue-gray (analysis)
- Game Day = high contrast blacks + team colors

### 5. Animation Requirements
- Events "landing on desk" with slide-in + drop shadow
- Objective whiteboard erase/rewrite animation
- Staggered reveals for lists
- Subtle movement on confident player portraits (static for struggling)

### 6. Typography Overhaul
- Condensed bold sans for headers (not Inter)
- Handwriting fonts for annotations/scout notes
- Serif for narrative/story content
- Tabular monospace for stats

## Specific Questions

1. **Textures & Backgrounds** - Can we do paper/concrete textures performantly? SVG filters? CSS? Images?

2. **Portrait Treatment** - Can we dynamically adjust player portraits (saturation, brightness, shadows) based on morale data? CSS filters? Canvas?

3. **Handwritten Text** - For the whiteboard objective, can we use a handwriting font that looks natural? Or do we need actual hand-drawn SVG text?

4. **Animation Budget** - What's realistic for animations without killing performance? The "landing on desk" effect for events?

5. **Phase Theming** - Can we do CSS custom property shifts that feel dramatic but not jarring?

6. **Current Stack** - What are we working with? React + CSS? Tailwind? Styled-components? This affects what's feasible.

## What I Need From You

1. Which of these ideas are straightforward?
2. Which are possible but complex?
3. Which are impractical/should be cut?
4. What technical approach would you recommend?

Please be honest if this is too ambitious - I'd rather scope down now than discover problems mid-implementation.

**- Management Agent**