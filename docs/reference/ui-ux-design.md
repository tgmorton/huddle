# Huddle: UI/UX Design System

> The interface should feel like a coach's desk—organized chaos, competing demands, and the tools to make hard decisions. Not a spreadsheet. Not a dashboard. A workspace where every screen asks something of you.

This document translates the [Design Philosophy](./DESIGN_PHILOSOPHY.md) into concrete UI/UX patterns, screen layouts, interaction models, and visual language.

---

## Table of Contents

1. [Design Principles](#design-principles)
2. [Visual Language](#visual-language)
3. [Core UI Patterns](#core-ui-patterns)
4. [Screen Architecture](#screen-architecture)
5. [Navigation & Flow](#navigation--flow)
6. [Key Screens](#key-screens)
7. [Component Library](#component-library)
8. [Interaction Patterns](#interaction-patterns)
9. [Information Density & Hierarchy](#information-density--hierarchy)
10. [Responsive Considerations](#responsive-considerations)

---

## Design Principles

These principles guide every UI decision:

### 1. Weight Over Speed

The UI should feel **deliberate**, not snappy. Decisions should have a moment of pause before execution. Confirmations for irreversible actions. A beat before time advances. The interface shouldn't rush you—it should make you feel the weight of your choices.

**Implications:**
- Avoid instant feedback for major decisions
- Use transitions that feel substantial, not zippy
- Confirmation states for roster moves, contract signings, etc.
- Never auto-advance through critical moments

### 2. Competing Demands are Visible

The UI should constantly surface tension. When you're looking at one thing, you should be aware that other things need attention. The clipboard badge counts. The ticker scrolling by. The owner's goals in your peripheral vision.

**Implications:**
- Persistent notification indicators
- Split attention between active panel and event queue
- Ticker never stops (unless paused)
- Stakeholder sentiment always visible somewhere

### 3. Context is King

Every screen should know where you are in the season, what decisions are pressing, what matters right now. "Week 7" should feel different from "Week 17." Free agency should feel different from training camp.

**Implications:**
- Phase-aware UI theming and emphasis
- Contextual actions based on current phase
- Time pressure visualized (deadlines, countdowns)
- Seasonal rhythm reflected in available actions

### 4. Uncertainty is Visual

When information is incomplete, the UI should show that. Scouting reports should look different from confirmed stats. Projections should feel like projections, not facts. The interface should train players to understand what they know vs. what they're guessing.

**Implications:**
- Visual treatments for certainty levels (solid vs. fuzzy, confident vs. estimated)
- Explicit "scout disagreement" indicators
- Question marks, ranges, and qualitative descriptors over false precision
- Different typography/styling for known vs. projected values

### 5. Stories Over Stats

When showing player information, lead with narrative, not numbers. Who is this person? What's their story? The stats are there if you dig, but the first impression should be human.

**Implications:**
- Player cards emphasize personality, background, situation
- News and narrative integrated throughout
- Stats accessible but not the default view
- Contextual storytelling (draft pick origins, career arcs)

### 6. Your Attention is a Resource

The UI should make you feel the cost of attention. You can't look at everything. Choosing to focus on the draft board means not watching free agency. The interface shouldn't let you see everything at once—it should make you choose.

**Implications:**
- Limited simultaneous views
- Clear "main focus" with peripheral awareness
- Switching contexts should feel like a decision
- No omniscient dashboard view

---

## Visual Language

### Color Palette

```
Background Tones (Dark Theme Primary):
├── bg-deepest:    #0a0a0f     (base background, field background)
├── bg-deep:       #12121a     (panel backgrounds)
├── bg-surface:    #1a1a24     (card backgrounds, elevated surfaces)
├── bg-raised:     #24242f     (hover states, selected items)
└── bg-highlight:  #2e2e3a     (active states, focus)

Text Hierarchy:
├── text-primary:   #f0f0f5    (headings, important content)
├── text-secondary: #a0a0b0    (body text, descriptions)
├── text-tertiary:  #606070    (labels, metadata, timestamps)
└── text-muted:     #404050    (disabled, placeholders)

Accent Colors (Semantic):
├── accent-primary:  #3b82f6   (interactive elements, links, primary actions)
├── accent-success:  #10b981   (positive outcomes, signings, good news)
├── accent-warning:  #f59e0b   (deadlines, attention needed, caution)
├── accent-danger:   #ef4444   (negative outcomes, injuries, critical issues)
├── accent-info:     #6366f1   (informational, neutral highlights)
└── accent-neutral:  #6b7280   (low priority, background events)

Team Colors:
- Dynamically applied based on player's team
- Used for jersey accents, team indicators, rivalry emphasis

Phase Accent (Subtle Tint):
├── offseason:      slight blue tint
├── free-agency:    slight green tint (money/deals)
├── draft:          slight purple tint (potential/unknown)
├── training:       slight orange tint (work/development)
├── regular-season: neutral
└── playoffs:       slight gold tint (stakes/intensity)
```

### Typography

```
Font Stack:
├── Primary:    'Inter', system-ui, sans-serif     (UI text, body)
├── Display:    'Oswald', 'Impact', sans-serif     (headlines, numbers, scores)
├── Mono:       'JetBrains Mono', monospace        (stats, numbers, code)
└── Narrative:  'Georgia', 'Times', serif          (stories, quotes, flavor text)

Scale:
├── xs:   11px / 0.6875rem   (timestamps, badges, micro-labels)
├── sm:   13px / 0.8125rem   (secondary labels, metadata)
├── base: 15px / 0.9375rem   (body text, descriptions)
├── md:   17px / 1.0625rem   (emphasized body, card titles)
├── lg:   21px / 1.3125rem   (section headers)
├── xl:   27px / 1.6875rem   (screen titles, major headings)
├── 2xl:  35px / 2.1875rem   (splash numbers, scores)
└── 3xl:  48px / 3rem        (hero moments, game scores)

Weights:
├── normal:   400   (body text)
├── medium:   500   (emphasis, labels)
├── semibold: 600   (headings, important)
└── bold:     700   (display, impact)
```

### Spacing System

```
Base unit: 4px

├── space-1:   4px    (tight, within components)
├── space-2:   8px    (related elements)
├── space-3:   12px   (standard gap)
├── space-4:   16px   (section internal padding)
├── space-5:   20px   (card padding)
├── space-6:   24px   (between sections)
├── space-8:   32px   (major divisions)
├── space-10:  40px   (screen regions)
└── space-12:  48px   (hero spacing)
```

### Elevation & Depth

```
Layers (z-index):
├── base:        0      (background, field)
├── surface:     10     (cards, panels)
├── raised:      20     (dropdowns, popovers)
├── overlay:     30     (modals, dialogs)
├── sticky:      40     (fixed headers, ticker)
├── toast:       50     (notifications, alerts)
└── tooltip:     60     (tooltips, hover info)

Shadows (for light accents on dark theme):
├── shadow-sm:   0 1px 2px rgba(0,0,0,0.3)
├── shadow-md:   0 4px 6px rgba(0,0,0,0.4)
├── shadow-lg:   0 10px 15px rgba(0,0,0,0.5)
└── shadow-glow: 0 0 20px rgba(accent, 0.2)   (for emphasis)
```

### Borders & Dividers

```
├── border-subtle:   1px solid rgba(255,255,255,0.05)
├── border-default:  1px solid rgba(255,255,255,0.1)
├── border-emphasis: 1px solid rgba(255,255,255,0.2)
├── border-accent:   2px solid var(--accent-primary)
└── divider:         1px solid rgba(255,255,255,0.08)
```

---

## Core UI Patterns

### The Management Shell

The primary interface for franchise mode. Always present, providing context and navigation.

```
┌─────────────────────────────────────────────────────────────────────┐
│  TOP BAR                                                            │
│  [Phase] [Date/Time] [Week] ──────────── [Speed Controls] [Pause]   │
├───────────────────────────────────────┬─────────────────────────────┤
│                                       │                             │
│                                       │       CLIPBOARD             │
│          ACTIVE PANEL                 │                             │
│                                       │   [Tab Bar]                 │
│   (Primary workspace area -           │   ├── Events (3)            │
│    events, roster views,              │   ├── Roster                │
│    negotiations, etc.)                │   ├── Depth Chart           │
│                                       │   └── ...                   │
│                                       │                             │
│                                       │   [Tab Content]             │
│                                       │   (List view, quick ref)    │
│                                       │                             │
├───────────────────────────────────────┴─────────────────────────────┤
│  TICKER                                                             │
│  [NEWS] ▸ Signing: J. Smith signs 3yr deal... ▸ Injury: ...         │
└─────────────────────────────────────────────────────────────────────┘
```

**Rationale:**
- Top bar provides constant context (when are we, what's the pace)
- Active panel is the "desk" where work happens
- Clipboard is the reference material, always accessible but not primary
- Ticker keeps the world alive, scrolling even when you're focused elsewhere

### The Event-Driven Model

Events are the heartbeat of the game. They drive the simulation forward and demand decisions.

```
Event Lifecycle:
SCHEDULED → PENDING → [User Decision] → RESOLVED
                ↓
            EXPIRED (if ignored past deadline)

Event Card Structure:
┌────────────────────────────────────────┐
│ [PRIORITY] [CATEGORY]         [TIMER]  │
│                                        │
│ Title of Event                         │
│ Description text explaining what       │
│ happened and what decision is needed.  │
│                                        │
│ [Related: Player Name, Team Logo]      │
│                                        │
│ ┌──────────┐ ┌──────────┐              │
│ │  ATTEND  │ │ DISMISS  │              │
│ └──────────┘ └──────────┘              │
└────────────────────────────────────────┘
```

### The Split Focus Model

The player should never feel omniscient. The active panel shows one thing deeply; the clipboard shows other things at a glance.

**Active Panel Uses:**
- Negotiation interfaces (full attention)
- Player evaluation (detailed view)
- Game day (immersive)
- Draft war room (focused)

**Clipboard Uses:**
- Event queue (what's waiting)
- Roster reference (quick lookups)
- Standings (context)
- Schedule (upcoming)

Clicking something in the clipboard can promote it to the active panel.

---

## Screen Architecture

### Screen Hierarchy

```
Career Mode
├── New Career Setup
│   ├── Coach Creation
│   ├── Team Selection
│   └── Difficulty/Settings
│
├── Management Shell (persistent)
│   ├── [Active Panel - contextual]
│   ├── [Clipboard - persistent]
│   └── [Ticker - persistent]
│
├── Phase-Specific Screens
│   ├── Offseason
│   │   ├── Staff Management
│   │   ├── Contract Decisions
│   │   └── Philosophy Setup
│   │
│   ├── Free Agency
│   │   ├── Available Players Feed
│   │   ├── Bidding Interface
│   │   └── Negotiation Room
│   │
│   ├── Draft
│   │   ├── Big Board / Draft Board
│   │   ├── War Room (live draft)
│   │   └── Post-Pick Reactions
│   │
│   ├── Training Camp
│   │   ├── Roster Battles
│   │   ├── Practice Allocation
│   │   └── Cut Decisions
│   │
│   ├── Regular Season (weekly)
│   │   ├── Week Overview
│   │   ├── Practice Management
│   │   ├── Game Prep
│   │   └── Game Day
│   │
│   └── Playoffs
│       └── (Enhanced week view with stakes)
│
├── Game Day Mode
│   ├── Pre-Game
│   ├── In-Game (coaching view)
│   ├── Halftime
│   └── Post-Game
│
└── Reference Screens (from clipboard)
    ├── Full Roster
    ├── Full Depth Chart
    ├── League Standings
    ├── Statistics Leaders
    ├── Transaction History
    └── Scouting Reports
```

### Navigation Patterns

**Primary Navigation:** Phase-driven, not menu-driven
- The current phase determines what's available
- No global menu with all options at all times
- Context-appropriate actions surface naturally

**Secondary Navigation:** Clipboard tabs
- Quick access to reference material
- Doesn't change the active panel unless explicitly promoted

**Tertiary Navigation:** Event attendance
- Events can take over the active panel
- "Attending" an event means focusing on it

---

## Navigation & Flow

### Time as Navigation

The game advances through time. Time is the primary axis of navigation.

```
[<<] [<] ───────●──────────────────── [>] [>>]
     ↑          ↑                      ↑
   slower    current               faster

Speed Settings:
- PAUSED:    Time frozen, full control
- SLOW:      1 game-minute = 2 real-seconds
- NORMAL:    1 game-minute = 1 real-second
- FAST:      1 game-minute = 0.5 real-seconds
- VERY_FAST: 1 game-minute = 0.1 real-seconds
```

**Auto-Pause Triggers:**
- Event requires attention (based on settings)
- Game day arrival
- Critical deadline approaching
- User-configured triggers

### The "Attend" Pattern

When you attend an event, you're committing attention to it.

```
Event in Clipboard          Active Panel
┌──────────────┐            ┌─────────────────────────┐
│ FA: J. Smith │ ──ATTEND──>│ Free Agent Negotiation  │
│   available  │            │                         │
└──────────────┘            │ [Full negotiation UI]   │
                            │                         │
                            │ [Complete] [Walk Away]  │
                            └─────────────────────────┘
```

Attending removes the event from pending and opens the relevant interface.

### Phase Transitions

When the phase changes, the UI should mark it.

```
┌─────────────────────────────────────────┐
│                                         │
│          FREE AGENCY BEGINS             │
│                                         │
│   The legal tampering period has ended. │
│   Players are now available to sign.    │
│                                         │
│            [Continue]                   │
│                                         │
└─────────────────────────────────────────┘
```

These interstitials provide narrative beats and ensure the player notices transitions.

---

## Key Screens

### 1. Week Overview (Regular Season)

The hub for in-season management. Shows the current week at a glance.

```
┌─────────────────────────────────────────────────────────────────────┐
│  WEEK 7 │ Tuesday, October 15                           [▶ Normal]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─ THIS WEEK ─────────────────────────────────────────────────┐    │
│  │                                                             │    │
│  │   SUNDAY @ 1:00 PM                                          │    │
│  │   ┌─────────┐     ┌─────────┐                               │    │
│  │   │  [LOGO] │ vs  │ [LOGO]  │                               │    │
│  │   │  Bears  │     │ Vikings │                               │    │
│  │   │  (3-3)  │     │  (5-1)  │                               │    │
│  │   └─────────┘     └─────────┘                               │    │
│  │                                                             │    │
│  │   Division Rivalry • "Must Win" - Owner Goal                │    │
│  │                                                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─ PRACTICE FOCUS ─────────────┐  ┌─ INJURY REPORT ───────────┐   │
│  │                              │  │                           │   │
│  │  Development  ████████░░ 80% │  │  J. Fields (QB)    Prob   │   │
│  │  Execution    ██░░░░░░░░ 20% │  │  A. Jones (RB)     Quest  │   │
│  │  Scheme       ░░░░░░░░░░  0% │  │  D. Smith (WR)     Out    │   │
│  │                              │  │                           │   │
│  │  [Adjust Practice]           │  │  [Full Report]            │   │
│  └──────────────────────────────┘  └───────────────────────────┘   │
│                                                                     │
│  ┌─ PENDING DECISIONS ──────────────────────────────────────────┐   │
│  │  2 Events Need Attention                                     │   │
│  │  • Practice Squad: Elevate player for Sunday?        [View]  │   │
│  │  • Player Meeting: D. Smith unhappy with role        [View]  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  ▸ TRADE: Bears acquire 2025 3rd round pick from...                 │
└─────────────────────────────────────────────────────────────────────┘
```

### 2. Free Agency Feed

Event-driven player availability. Not a list you browse—a feed that unfolds.

```
┌─────────────────────────────────────────────────────────────────────┐
│  FREE AGENCY │ Day 3 of 14 │ Cap Space: $12.4M          [▶ Normal]  │
├───────────────────────────────────────┬─────────────────────────────┤
│                                       │  ACTIVITY                   │
│  ┌─ NEW: Available Now ────────────┐  │                             │
│  │                                 │  │  ┌─ Your Negotiations ────┐ │
│  │  ┌───────────────────────────┐  │  │  │                        │ │
│  │  │ [PHOTO]  Marcus Williams  │  │  │  │  T. Smith (OT)         │ │
│  │  │          Safety • 28yo    │  │  │  │  Waiting for response  │ │
│  │  │          83 OVR           │  │  │  │  ████████░░ 2 days     │ │
│  │  │                           │  │  │  │                        │ │
│  │  │  Asking: $8M/yr           │  │  │  │  [Check In]            │ │
│  │  │  Interest: 4 teams        │  │  │  │                        │ │
│  │  │                           │  │  │  └────────────────────────┘ │
│  │  │  [PURSUE]  [PASS]         │  │  │                             │
│  │  └───────────────────────────┘  │  │  ┌─ Watching ─────────────┐ │
│  │                                 │  │  │                        │ │
│  │  ──── Earlier Today ─────────   │  │  │  J. Jackson (CB)       │ │
│  │                                 │  │  │  Bidding at $6.2M      │ │
│  │  ┌───────────────────────────┐  │  │  │  You're outbid         │ │
│  │  │ [PHOTO]  Derek Barnes     │  │  │  │                        │ │
│  │  │          DT • 31yo        │  │  │  │  [Raise Bid] [Drop]    │ │
│  │  │          79 OVR           │  │  │  │                        │ │
│  │  │                           │  │  │  └────────────────────────┘ │
│  │  │  Asking: $5M/yr           │  │  │                             │
│  │  │  Interest: 2 teams        │  │  │  Slots Used: 2/3            │
│  │  │                           │  │  │                             │
│  │  │  [PURSUE]  [PASS]         │  │  │  You can only pursue 3     │
│  │  └───────────────────────────┘  │  │  players simultaneously.   │
│  │                                 │  │                             │
│  └─────────────────────────────────┘  │                             │
│                                       │                             │
├───────────────────────────────────────┴─────────────────────────────┤
│  ▸ SIGNING: Vikings sign Marcus Peters to 2yr/$14M deal...          │
└─────────────────────────────────────────────────────────────────────┘
```

**Key UX Elements:**
- **Pursuit Slots**: Limited to 3 simultaneous negotiations (scarcity of attention)
- **Bidding**: Other teams visible as competition, not just background
- **Time Pressure**: Negotiations have deadlines, visible countdowns
- **Feed Format**: New players appear as events, scroll down for history

### 3. Negotiation Room

Full-screen focus when negotiating. This is a conversation, not a form.

```
┌─────────────────────────────────────────────────────────────────────┐
│  NEGOTIATION │ Marcus Williams, S                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                             │    │
│  │  [AGENT PORTRAIT]                                           │    │
│  │                                                             │    │
│  │  "Marcus is looking for a team where he can compete for     │    │
│  │   a championship. The money matters, but he wants to know   │    │
│  │   he'll be a starter and the defense is built to win."      │    │
│  │                                                             │    │
│  │  Agent: David Chen │ Personality: Aggressive                │    │
│  │                                                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─ CURRENT TERMS ──────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  Length:      [3 years ▼]                                    │   │
│  │  Total Value: [$24,000,000        ]                          │   │
│  │  Guaranteed:  [$15,000,000        ]     (62.5%)              │   │
│  │  Structure:   [Front-loaded ▼]                               │   │
│  │                                                              │   │
│  │  Cap Hit:  Y1: $9.2M  │  Y2: $8.0M  │  Y3: $6.8M             │   │
│  │                                                              │   │
│  │  ──────────────────────────────────────────────────────────  │   │
│  │  Market Value: ~$8.5M/yr  │  His Ask: $9.0M/yr               │   │
│  │  Your Cap Space: $12.4M (after signing: $3.2M)               │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ PLAYER PRIORITIES ───────────┐  ┌─ YOUR LEVERAGE ───────────┐  │
│  │  1. Role (Starter)       ████ │  │  Championship Window  ███ │  │
│  │  2. Winning              ███░ │  │  Cap Space            ██░ │  │
│  │  3. Money                ██░░ │  │  Scheme Fit           ██░ │  │
│  │  4. Location             █░░░ │  │  Coaching Staff       ██░ │  │
│  └───────────────────────────────┘  └───────────────────────────┘  │
│                                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐    │
│  │ MAKE OFFER   │ │ WALK AWAY    │ │ PROMISE ROLE (costs rep) │    │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Key UX Elements:**
- **Agent Dialogue**: Personality-driven, gives hints about what matters
- **Player Priorities**: Visual hierarchy of what this player cares about
- **Your Leverage**: What you can offer beyond money
- **Promises**: Can commit to role/playing time, but it costs reputation if broken

### 4. Draft War Room

Live draft experience. Other teams are visible actors.

```
┌─────────────────────────────────────────────────────────────────────┐
│  2025 NFL DRAFT │ Round 1 │ Pick 14 (Your Pick)         ON THE CLOCK│
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─ ON THE CLOCK: YOUR PICK ────────────────────────────────────┐   │
│  │                                                              │   │
│  │   ⏱ 2:34 remaining                                           │   │
│  │                                                              │   │
│  │  ┌─────────────────────────────────────────────────────┐     │   │
│  │  │  YOUR BIG BOARD               │  AVAILABLE NOW      │     │   │
│  │  │                               │                     │     │   │
│  │  │  #1 Marcus Thompson, EDGE ✓   │  1. J. Williams, OT │     │   │
│  │  │     (Drafted #3)              │     Your Grade: A-  │     │   │
│  │  │                               │     Need: HIGH      │     │   │
│  │  │  #2 J. Williams, OT           │                     │     │   │
│  │  │     AVAILABLE ←               │  2. D. Carter, WR   │     │   │
│  │  │                               │     Your Grade: B+  │     │   │
│  │  │  #3 D. Carter, WR             │     Need: MEDIUM    │     │   │
│  │  │     AVAILABLE                 │                     │     │   │
│  │  │                               │  3. T. Brooks, LB   │     │   │
│  │  │  #4 T. Brooks, LB             │     Your Grade: B+  │     │   │
│  │  │     AVAILABLE                 │     Need: LOW       │     │   │
│  │  │                               │                     │     │   │
│  │  └─────────────────────────────────────────────────────┘     │   │
│  │                                                              │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌───────────────────┐     │   │
│  │  │ SELECT       │ │ TRADE DOWN   │ │ VIEW PROSPECT     │     │   │
│  │  │ J. Williams  │ │              │ │                   │     │   │
│  │  └──────────────┘ └──────────────┘ └───────────────────┘     │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ RECENT PICKS ───────────────────────────────────────────────┐   │
│  │  13. Raiders: S. Martinez, CB   "Surprise pick - was #23..."│   │
│  │  12. Broncos: K. Johnson, RB    "Great value at 12..."      │   │
│  │  11. Giants:  M. Thompson, EDGE "The best pass rusher..."   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ TRADE OFFERS ───────────────────────────────────────────────┐   │
│  │  Patriots want to trade up! Offering: #18 + #52 + 2026 3rd   │   │
│  │  [VIEW OFFER]                                                │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  ▸ SCHEFTER: "League sources say Bears are targeting J. Williams..."│
└─────────────────────────────────────────────────────────────────────┘
```

**Key UX Elements:**
- **On The Clock**: Timer creates real pressure
- **Big Board vs Available**: Your rankings vs who's still there
- **Trade Offers**: Other teams actively trying to trade with you
- **Commentary**: Schefter-style narrative on each pick
- **Surprise Indicators**: When a pick doesn't match projections

### 5. Player Card

The core unit of player information. Narrative-first.

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  ┌─────────┐  MARCUS WILLIAMS                                       │
│  │         │  Safety │ 28 years old │ 6'1" 202 lbs                  │
│  │ [PHOTO] │                                                        │
│  │         │  "A ball-hawk with elite range who's looking           │
│  └─────────┘   for one more shot at a ring."                        │
│                                                                     │
│  ───────────────────────────────────────────────────────────────    │
│                                                                     │
│  OVERALL        EXPERIENCE       CONTRACT                           │
│  ┌────────┐     ┌──────────┐     ┌─────────────────────────────┐    │
│  │   83   │     │  7 Years │     │  Free Agent                 │    │
│  │  ████  │     │  Saints  │     │  Asking: ~$8M/yr            │    │
│  └────────┘     │  Ravens  │     │  Interest: 4 teams          │    │
│                 └──────────┘     └─────────────────────────────┘    │
│                                                                     │
│  ┌─ SCOUTING REPORT ────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  STRENGTHS                    WEAKNESSES                     │   │
│  │  • Elite ball skills          • Lost a step in speed         │   │
│  │  • Smart in coverage          • Tackling inconsistent        │   │
│  │  • Leadership presence        • Injury history (hamstring)   │   │
│  │                                                              │   │
│  │  SCHEME FIT                                                  │   │
│  │  Your System: Cover 3  →  FIT: ████████░░ Good               │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ PERSONALITY ────────────────────────────────────────────────┐   │
│  │  Type: Veteran Leader │ Motivation: Winning                  │   │
│  │  "Will mentor young players. Expects to start."              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [View Full Stats]  [View Career History]  [Add to Watchlist]       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Key UX Elements:**
- **Narrative Quote**: First impression is human, not a number
- **Overall is Present but Not Dominant**: It's there, but it's not the headline
- **Scheme Fit**: Immediately relevant to your team
- **Personality**: Affects how they'll behave, negotiate, fit in locker room
- **Expandable Detail**: Stats available but not default

### 6. Scouting Report (Draft Prospect)

Deliberately uncertain. This is an opinion, not a fact.

```
┌─────────────────────────────────────────────────────────────────────┐
│  SCOUTING REPORT │ Jake Williams, OT │ Ohio State                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────┐  HEIGHT: 6'5"    WEIGHT: 315 lbs    ARM: 34.5"         │
│  │         │  40-YARD: 5.12s  BENCH: 28 reps    VERT: 29"           │
│  │ [PHOTO] │                                                        │
│  │         │  PROJECTION: Round 1 (Top 15)                          │
│  └─────────┘                                                        │
│                                                                     │
│  ───────────────────────────────────────────────────────────────    │
│                                                                     │
│  YOUR SCOUTS' ASSESSMENT                     CERTAINTY: ███░░░      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  GRADE: A-                                                   │   │
│  │  "Day one starter at left tackle. Elite feet, strong anchor. │   │
│  │   Some concerns about consistency in pass protection         │   │
│  │   against speed rushers."                                    │   │
│  │                                                              │   │
│  │  ────────────────────────────────────────────────────────    │   │
│  │                                                              │   │
│  │  ATTRIBUTES (Scout Impressions)                              │   │
│  │                                                              │   │
│  │  Pass Blocking:    ██████████░░  Excellent                   │   │
│  │  Run Blocking:     ████████░░░░  Good                        │   │
│  │  Footwork:         ██████████░░  Excellent                   │   │
│  │  Strength:         ████████░░░░  Good                        │   │
│  │  Football IQ:      ██████░░░░░░  Average?                    │   │
│  │                    ↑ scouts disagree on this                 │   │
│  │                                                              │   │
│  │  LEARNING:         Unknown (need interview)                  │   │
│  │  PERSONALITY:      Unknown (need interview)                  │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ SCOUT NOTES ────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  Regional Scout (West):                                      │   │
│  │  "Best tackle prospect I've seen in 3 years. Will start     │   │
│  │   immediately and anchor a line for a decade."              │   │
│  │                                                              │   │
│  │  National Scout:                                             │   │
│  │  "Good player, but I worry about his processing speed.      │   │
│  │   Struggled against complex blitz packages."                │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ YOUR NOTES ─────────────────────────────────────────────────┐   │
│  │  [Add your own notes about this prospect...]                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [Request Private Workout: 1 slot]  [Invite to Interview: USED]     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Key UX Elements:**
- **Certainty Indicator**: How much do you actually know?
- **Scout Disagreement**: Visible when scouts don't agree (signal, not noise)
- **Qualitative Descriptors**: "Excellent", "Good", "Average?" not numbers
- **Unknown Fields**: Explicitly shows what you don't know yet
- **Your Notes**: Player can annotate (the paper notebook, digitized)
- **Resource Costs**: Private workouts and interviews are limited

### 7. Game Day - Coaching View

Not Madden. Slower, more deliberate. You're watching and intervening.

```
┌─────────────────────────────────────────────────────────────────────┐
│  BEARS 14  │  VIKINGS 17  │  Q3 8:42  │  2nd & 7 at MIN 34         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                             │    │
│  │                     [FIELD VISUALIZATION]                   │    │
│  │                                                             │    │
│  │         ○ ○ ○   ○ ○ ○ ○   ○ ○ ○                             │    │
│  │                   ●                                         │    │
│  │         ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○                               │    │
│  │                                                             │    │
│  │                     MIN 34                                  │    │
│  │                                                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─ PLAY CALL ──────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  FORMATION           PLAY                    PERSONNEL       │   │
│  │  ┌─────────────┐    ┌─────────────────┐     11 Personnel    │   │
│  │  │  Shotgun    │    │ HB Dive         │     (1RB, 1TE, 3WR) │   │
│  │  │  Spread     │    │ Slant Flat      │                     │   │
│  │  │  I-Form     │    │ PA Boot         │◄── OC Suggestion    │   │
│  │  │  Singleback │    │ Screen          │                     │   │
│  │  └─────────────┘    └─────────────────┘                     │   │
│  │                                                              │   │
│  │  [CALL PLAY]  [TIMEOUT (2)]  [CHALLENGE]  [LET OC CALL]     │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ SIDELINE ───────────────────┐  ┌─ SITUATION ─────────────────┐ │
│  │                              │  │                             │ │
│  │  QB: J. Fields               │  │  Win Prob: 38%              │ │
│  │  Status: 18/29, 203 yds, 1TD │  │  This Drive: 6 plays, 42yds │ │
│  │  Confidence: ████████░░      │  │  Time of Poss: 18:42        │ │
│  │                              │  │                             │ │
│  │  [View Matchups] [Substitution]│  │  Vikings rushing D: Elite  │ │
│  │                              │  │  Consider passing downs     │ │
│  └──────────────────────────────┘  └─────────────────────────────┘ │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  [Last Play: Incomplete pass to D. Moore, defended by P. Peterson]  │
└─────────────────────────────────────────────────────────────────────┘
```

**Key UX Elements:**
- **OC Suggestion**: Your coordinator has an opinion (you can defer or override)
- **Let OC Call**: Explicitly give up control (but watch)
- **Situation Context**: Not just the score—matchup info, tendencies
- **Sideline Info**: Player status, confidence (not just stats)
- **Win Probability**: Stakes are visible

---

## Component Library

### Core Components

#### EventCard
```
Props:
- event: ManagementEvent
- onAttend: () => void
- onDismiss: () => void
- compact?: boolean

States:
- default
- urgent (pulsing border)
- expiring (countdown visible)
- attended (muted, resolved)
```

#### PlayerCard
```
Props:
- player: Player
- context: 'roster' | 'free_agent' | 'prospect' | 'trade'
- showContract?: boolean
- showFit?: boolean
- onAction?: (action: string) => void

Variants:
- compact (list item)
- standard (card)
- expanded (full detail)
```

#### ProgressBar
```
Props:
- value: number
- max: number
- label?: string
- variant: 'default' | 'health' | 'learning' | 'confidence'
- showUncertainty?: boolean
```

#### StatDisplay
```
Props:
- value: number | string | null
- label: string
- certainty?: 'known' | 'estimated' | 'unknown'
- trend?: 'up' | 'down' | 'stable'
```

#### PhaseIndicator
```
Props:
- phase: SeasonPhase
- week?: number
- deadline?: Date
```

#### Ticker
```
Props:
- items: TickerItem[]
- speed: 'slow' | 'normal' | 'fast'
- onItemClick?: (item: TickerItem) => void
```

#### TimeControls
```
Props:
- currentSpeed: TimeSpeed
- isPaused: boolean
- onSpeedChange: (speed: TimeSpeed) => void
- onPause: () => void
- onPlay: () => void
```

### Layout Components

#### ManagementShell
```
The persistent wrapper for all management screens.
Contains: TopBar, ActivePanel slot, Clipboard, Ticker
```

#### SplitPanel
```
Props:
- left: ReactNode (Active Panel content)
- right: ReactNode (Clipboard content)
- leftWidth?: string (default: '65%')
```

#### TabPanel
```
Props:
- tabs: Tab[]
- activeTab: string
- onTabChange: (tab: string) => void
- badges?: Record<string, number>
```

---

## Interaction Patterns

### Decision Confirmation

For irreversible decisions (cuts, signings, trades):

```
┌─────────────────────────────────────────────┐
│                                             │
│  Sign Marcus Williams?                      │
│                                             │
│  3 years, $24M ($15M guaranteed)            │
│                                             │
│  Cap Impact:                                │
│  • 2025: -$9.2M (remaining: $3.2M)          │
│  • 2026: -$8.0M                             │
│  • 2027: -$6.8M                             │
│                                             │
│  This action cannot be undone.              │
│                                             │
│  ┌───────────────┐  ┌───────────────┐       │
│  │    CONFIRM    │  │    CANCEL     │       │
│  └───────────────┘  └───────────────┘       │
│                                             │
└─────────────────────────────────────────────┘
```

### Hover/Focus Information

Additional context appears on hover without cluttering the default view:

```
Player Name ──────────► [Hover Card]
                        ┌─────────────────────┐
                        │ Marcus Williams, S  │
                        │ 83 OVR │ 28yo       │
                        │ Contract: FA        │
                        │ [Click for more]    │
                        └─────────────────────┘
```

### Keyboard Shortcuts

```
Global:
- Space:        Play/Pause time
- 1-4:          Speed settings
- Escape:       Close modal / Go back
- Tab:          Cycle clipboard tabs
- /:            Open search/command palette

Context-specific:
- N:            Next play (game day)
- T:            Call timeout (game day)
- Enter:        Confirm action
- Backspace:    Go back
```

### Notifications & Toasts

```
Types:
- Info:     Blue, auto-dismiss after 5s
- Success:  Green, auto-dismiss after 3s
- Warning:  Yellow, requires dismiss
- Error:    Red, requires dismiss
- Event:    Accent color, click to attend

Position: Top-right, stacked
Max visible: 3 (older ones queue)
```

---

## Information Density & Hierarchy

### The Glance → Scan → Read Model

Every screen should support three levels of engagement:

**Glance (1 second):**
- What phase am I in?
- Are there urgent issues?
- What's the score/status?

**Scan (5 seconds):**
- What are my options?
- What needs attention?
- What's changed since I last looked?

**Read (30+ seconds):**
- Full details available
- Context and history
- Deep analysis possible

### Visual Hierarchy Rules

1. **Urgency rises to the top.** Critical events above normal events.
2. **Actions are visually distinct.** Buttons don't look like labels.
3. **Numbers are de-emphasized.** Text descriptions preferred; numbers available on demand.
4. **Uncertainty is visible.** Unknown ≠ hidden. Show what you don't know.
5. **Time is always visible.** Current date/phase/deadline always in peripheral vision.

---

## Responsive Considerations

### Primary Target: Desktop (1920x1080 minimum)

This is a dense management game. The full experience requires screen real estate.

### Tablet Support (1024x768 minimum)

- Clipboard collapses to bottom sheet
- Ticker becomes notification badge
- Touch targets enlarged

### Mobile: Not Supported for Core Gameplay

Mobile can support:
- Notification checking
- Quick roster views
- News/ticker browsing

But active management requires desktop.

---

## Appendix: Existing Component Audit

Current components in `/frontend/src/components/`:

| Component | Status | Notes |
|-----------|--------|-------|
| ManagementScreen | Shell exists | Needs refinement for design system |
| TopBar | Functional | Align with typography/spacing spec |
| Clipboard | Functional | Needs tab content implementations |
| Ticker | Functional | Good foundation |
| ActivePanel | Placeholder | Needs all panel implementations |
| GameScreen | Functional | Separate from management shell |
| FieldView | Exists | Pixi.js based |
| PlayerSprite | Exists | Needs design system colors |

### Migration Path

1. Establish design tokens (CSS custom properties)
2. Update existing components to use tokens
3. Build new components with design system from start
4. Create Storybook for component documentation

---

## Next Steps

1. **Implement Design Tokens**: Create CSS custom properties for colors, typography, spacing
2. **Build Component Library**: Start with core components (EventCard, PlayerCard, ProgressBar)
3. **Week Overview Screen**: First full screen implementation following this spec
4. **Free Agency Flow**: Event-driven player availability with negotiation
5. **Player Card System**: Narrative-first player information display

---

## Experimental Concepts: Pushing the Genre Forward

> Sports management games have been stuck in the same paradigm for 15 years: spreadsheets with team logos. We have an opportunity to fundamentally rethink how these games feel, how they communicate, and what emotions they evoke. This section explores ideas that are risky, unproven, and potentially transformative.

### The Thesis

Every sports management game treats the player as an omniscient optimizer. You see all the numbers, you make the "correct" decisions, you win. This is fundamentally at odds with what real coaching and management feel like—which is navigating uncertainty, managing relationships, and making judgment calls that might be wrong.

**We should design for feeling, not optimization.**

---

### 1. The Living Office

**Concept:** Your "home base" isn't a menu—it's a space.

Instead of a dashboard with buttons, you have an office. A desk with papers. A window showing the practice field. A TV playing highlights. A phone that rings. A door that people knock on.

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  ┌─────────────────┐                              ┌──────────────┐  │
│  │                 │   [WINDOW: Practice field    │              │  │
│  │   [TV]          │    visible, players moving]  │   [DOOR]     │  │
│  │   Highlights    │                              │              │  │
│  │   playing       │                              │   * knock *  │  │
│  │                 │                              │              │  │
│  └─────────────────┘                              └──────────────┘  │
│                                                                     │
│         ┌──────────────────────────────────────────────┐            │
│         │                                              │            │
│         │   [DESK]                                     │            │
│         │                                              │            │
│         │   ┌────────┐  ┌────────┐  ┌────────┐        │            │
│         │   │ Roster │  │ Inbox  │  │ Phone  │        │            │
│         │   │ Folder │  │ (3)    │  │        │        │            │
│         │   └────────┘  └────────┘  └────────┘        │            │
│         │                                              │            │
│         │   [Scattered papers: scouting reports,      │            │
│         │    contract offers, newspaper clippings]    │            │
│         │                                              │            │
│         └──────────────────────────────────────────────┘            │
│                                                                     │
│  ┌──────────────┐                        ┌───────────────────────┐  │
│  │ [WHITEBOARD] │                        │ [BOOKSHELF]           │  │
│  │ Team depth   │                        │ Playbooks, trophies,  │  │
│  │ chart        │                        │ career mementos       │  │
│  └──────────────┘                        └───────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Why this matters:**
- Creates a *sense of place* that menus never can
- Natural affordances: papers pile up when you ignore them, the phone rings for urgent matters
- Environmental storytelling: your office changes based on success (trophies appear, photos with players)
- Interruptions feel like interruptions, not notifications
- The window to the practice field gives ambient awareness without data overload

**Implementation thought:** This doesn't replace functional UI—clicking the roster folder opens the roster screen. But it reframes the experience from "navigating menus" to "being in a space."

---

### 2. The Memory Wall

**Concept:** A persistent visual history of your career's defining moments.

Most games show you stats. Wins, losses, championships. But that's not how we remember. We remember *moments*. The draft pick that became a star. The game-winning drive in the playoffs. The player who held out and poisoned the locker room.

```
┌─────────────────────────────────────────────────────────────────────┐
│  YOUR CAREER │ Season 4                                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                             │    │
│  │  [Polaroid-style memory cards, slightly scattered]          │    │
│  │                                                             │    │
│  │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │    │
│  │   │ ░░░░░░░ │  │ ░░░░░░░ │  │ ░░░░░░░ │  │ ░░░░░░░ │       │    │
│  │   │ ░░░░░░░ │  │ ░░░░░░░ │  │ ░░░░░░░ │  │ ░░░░░░░ │       │    │
│  │   │ ░░░░░░░ │  │ ░░░░░░░ │  │ ░░░░░░░ │  │ ░░░░░░░ │       │    │
│  │   ├─────────┤  ├─────────┤  ├─────────┤  ├─────────┤       │    │
│  │   │ Draft   │  │ The     │  │ Contract│  │ NFC     │       │    │
│  │   │ Day     │  │ Catch   │  │ Disaster│  │ Champs  │       │    │
│  │   │ Yr 1    │  │ Yr 2    │  │ Yr 3    │  │ Yr 4    │       │    │
│  │   └─────────┘  └─────────┘  └─────────┘  └─────────┘       │    │
│  │                                                             │    │
│  │        ┌─────────┐  ┌─────────┐                             │    │
│  │        │ ░░░░░░░ │  │ ░░░░░░░ │                             │    │
│  │        │ ░░░░░░░ │  │ ░░░░░░░ │                             │    │
│  │        │ ░░░░░░░ │  │ ░░░░░░░ │                             │    │
│  │        ├─────────┤  ├─────────┤                             │    │
│  │        │ Rookie  │  │ The     │                             │    │
│  │        │ Record  │  │ Trade   │                             │    │
│  │        │ Yr 2    │  │ Yr 4    │                             │    │
│  │        └─────────┘  └─────────┘                             │    │
│  │                                                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  [Hover/click a memory to expand it]                                │
│                                                                     │
│  ┌─ THE CATCH ──────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  "Season 2, Week 14 vs. Packers. Down 4 with 0:08 left.      │   │
│  │   You called 'Hail Mary' - D. Johnson made an impossible     │   │
│  │   catch in triple coverage. Final: 31-28.                    │   │
│  │                                                              │   │
│  │   You drafted Johnson in round 5. Everyone said he was       │   │
│  │   too slow. You saw something else."                         │   │
│  │                                                              │   │
│  │   [Watch Replay]  [View Game Stats]  [Johnson's Career]      │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Why this matters:**
- **Creates emotional continuity.** You're not just optimizing—you're building a story.
- **Surfaces narrative automatically.** The game identifies "story-worthy" moments and preserves them.
- **Makes consequences visible.** "Contract Disaster" reminds you of that bad signing every time you see it.
- **Reinforces good decisions.** Seeing "Rookie Record" next to a player you believed in is satisfying in a way stats never are.

**Story detection heuristics:**
- Dramatic game moments (comebacks, last-second wins, upsets)
- Draft picks who exceed or dramatically fail expectations
- Free agent signings (good and bad outcomes)
- Firing/hiring staff
- Owner conflicts
- Player milestones achieved on your team

---

### 3. Relationship Webs

**Concept:** Make the social dynamics of your organization visible and interactive.

Football teams are social organisms. Players have friends, mentors, rivals. Coaches have proteges and enemies. The locker room has factions. None of this is visible in current sports games.

```
┌─────────────────────────────────────────────────────────────────────┐
│  LOCKER ROOM DYNAMICS                                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                          [TEAM CAPTAIN]                             │
│                           M. Williams                               │
│                               │                                     │
│               ┌───────────────┼───────────────┐                     │
│               │               │               │                     │
│           respects        mentors         friends                   │
│               │               │               │                     │
│               ▼               ▼               ▼                     │
│          J. Fields       T. Johnson      D. Smith                   │
│             (QB)            (S)            (WR)                     │
│               │               │               │                     │
│               │           mentors             │                     │
│               │               │               │                     │
│               │               ▼               │                     │
│               │          R. Adams ◄───────────┘                     │
│               │            (S)           friends                    │
│               │                                                     │
│               │    ════════════════════                             │
│               │         TENSION                                     │
│               │    ════════════════════                             │
│               │               │                                     │
│               └───────────────┤                                     │
│                   frustrated  │                                     │
│                      with     │                                     │
│                               ▼                                     │
│                          K. Brown                                   │
│                            (WR)                                     │
│                    "Wants more targets"                             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Relationship types:**
- **Mentorship:** Veterans teaching young players (accelerates development)
- **Friendship:** Players who support each other (morale boost when both play)
- **Rivalry:** Players competing for the same role (can be healthy or toxic)
- **Respect:** Players who admire each other's game
- **Tension:** Conflicts that affect locker room chemistry

**Why this matters:**
- Cutting a player has social consequences (who was connected to them?)
- Chemistry is visible, not just a hidden modifier
- Mentorship is a resource you can cultivate
- You can see locker room factions forming
- Makes roster decisions feel like they affect people, not just numbers

**Gameplay implications:**
- Signing a player who has existing relationships on your team (college teammates, former teammates) has benefits
- Cutting a team captain has ripple effects
- Young players need mentors to reach potential
- Toxic relationships can spread

---

### 4. The Confidence Model

**Concept:** Replace "morale" with something more nuanced—confidence that affects performance dynamically.

"Morale" in games is usually a single bar that goes up or down. Real confidence is more complex. A QB can be confident in his arm but rattled after interceptions. A kicker can be automatic from 40 but terrified from 50+.

```
┌─────────────────────────────────────────────────────────────────────┐
│  PLAYER CONFIDENCE │ Justin Fields, QB                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  OVERALL STATE: Confident (but fragile)                             │
│                                                                     │
│  ┌─ CONFIDENCE BREAKDOWN ───────────────────────────────────────┐   │
│  │                                                              │   │
│  │  Deep Ball         ████████████████░░░░  Confident           │   │
│  │  "Hit two 40+ yard TDs last week"                            │   │
│  │                                                              │   │
│  │  Pocket Presence   ████████░░░░░░░░░░░░  Shaky               │   │
│  │  "Took 5 sacks vs. Vikings, seeing ghosts"                   │   │
│  │                                                              │   │
│  │  Red Zone          ████████████░░░░░░░░  Steady              │   │
│  │  "2 TDs, 1 INT in red zone this season"                      │   │
│  │                                                              │   │
│  │  Clutch Moments    ██████████████████░░  Elite               │   │
│  │  "4th quarter passer rating: 118.2"                          │   │
│  │                                                              │   │
│  │  vs. Pressure      ██████░░░░░░░░░░░░░░  Struggling          │   │
│  │  "Completion % drops 30% when pressured"                     │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ RECENT EVENTS AFFECTING CONFIDENCE ─────────────────────────┐   │
│  │                                                              │   │
│  │  ▲ Week 6: Game-winning drive vs. Lions (+clutch)            │   │
│  │  ▼ Week 5: 5 sacks, 2 fumbles vs. Vikings (-pocket)          │   │
│  │  ▲ Week 4: 3 TD passes, 0 INT vs. Broncos (+overall)         │   │
│  │  ▼ Week 3: Benched in 4th quarter (-overall, -trust)         │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ COACHING ACTIONS ───────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  [Schedule QB Meeting]     Address pocket presence issues    │   │
│  │  [Extra Practice Reps]     Costs practice time               │   │
│  │  [Simplify Gameplan]       Reduce reads, safer throws        │   │
│  │  [Show Confidence]         Public statement, but risky       │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Why this matters:**
- Performance becomes context-dependent, not just a rating
- Recent events create gameplay narratives ("he's been off since that benching")
- Coaching actions can address specific confidence issues
- Creates more realistic player arcs (slumps, hot streaks, yips)
- Decision to bench or start has psychological consequences

---

### 5. The Unseen Conversation

**Concept:** Use AI-generated dialogue to make interactions feel real, without voice acting.

You mentioned wanting AI-generated commentary and conversations. Here's a vision for how that could work in player interactions:

```
┌─────────────────────────────────────────────────────────────────────┐
│  PLAYER MEETING │ Derek Smith, WR                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                             │    │
│  │  [PLAYER PORTRAIT]                                          │    │
│  │                                                             │    │
│  │  Derek shifts in his chair, not making eye contact.         │    │
│  │                                                             │    │
│  │  "Coach, I wanted to talk about my role. I've been here     │    │
│  │   three years now. I know Kendrick is the number one guy,   │    │
│  │   and that's fine. But I'm getting four targets a game.     │    │
│  │   Four. I didn't sign here to be invisible."                │    │
│  │                                                             │    │
│  │  He finally looks up. "What's the plan for me?"             │    │
│  │                                                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─ YOUR RESPONSE ──────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  ┌────────────────────────────────────────────────────────┐  │   │
│  │  │ "You're right. I'm going to design more plays for you  │  │   │
│  │  │  this week. You'll get your chances."                  │  │   │
│  │  │                                                        │  │   │
│  │  │  [PROMISE: 6+ targets next game]                       │  │   │
│  │  │  Risk: If broken, trust damage is severe               │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  │                                                              │   │
│  │  ┌────────────────────────────────────────────────────────┐  │   │
│  │  │ "I hear you, Derek. But the gameplan is the gameplan.  │  │   │
│  │  │  When you're open, Justin will find you."              │  │   │
│  │  │                                                        │  │   │
│  │  │  [NO PROMISE: Honest but unhelpful]                    │  │   │
│  │  │  Risk: Morale drops, may affect effort                 │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  │                                                              │   │
│  │  ┌────────────────────────────────────────────────────────┐  │   │
│  │  │ "You want more targets? Earn them. Your route running  │  │   │
│  │  │  has been sloppy. Get sharper or get comfortable."     │  │   │
│  │  │                                                        │  │   │
│  │  │  [CHALLENGE: Tough love approach]                      │  │   │
│  │  │  Risk: Could motivate or could backfire based on       │  │   │
│  │  │  personality. Derek is 'Sensitive' - high risk.        │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  │                                                              │   │
│  │  ┌────────────────────────────────────────────────────────┐  │   │
│  │  │ [Type your own response...]                            │  │   │
│  │  │                                                        │  │   │
│  │  │  AI will interpret intent and determine outcome        │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**The "type your own response" option:**

This is where LLM integration becomes transformative. Instead of picking from preset options, you can:
- Write your own dialogue
- The AI interprets your intent and tone
- Outcomes are determined by what you said + player personality + context
- Creates genuinely emergent conversations

**Example free-form responses and interpretations:**
- "I'm counting on you for the playoffs" → Interpreted as future promise, creates expectation
- "What do you need from me?" → Opens negotiation, player may ask for specific role
- "Between us, I'm looking to trade Kendrick in the offseason" → Secret shared, creates leverage but also risk

**Why this matters:**
- Conversations feel real, not like dialogue trees
- Player personality actually matters (some respond to tough love, some don't)
- Promises create obligations the game tracks
- Free-form input allows for genuine role-playing
- No two playthroughs have the same conversations

---

### 6. The Fog of War Depth Chart

**Concept:** You don't know your own team perfectly until you've seen them play.

In real football, coaches are constantly learning about their players. Training camp reveals things. Preseason games reveal more. Regular season games reveal the most. But in games, you know everything immediately.

```
┌─────────────────────────────────────────────────────────────────────┐
│  DEPTH CHART │ Wide Receivers                      [PRESEASON WK 2] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  WR1: K. Johnson                                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  KNOWN                          │  UNCERTAIN                 │   │
│  │  ─────                          │  ─────────                 │   │
│  │  Route Running: Elite           │  Clutch Factor: ???        │   │
│  │  Speed: 4.38 40-yard            │  Chemistry w/ Fields: ???  │   │
│  │  Hands: Very Good               │  Run Blocking: ???         │   │
│  │                                 │                            │   │
│  │  [You've seen 2 preseason       │  [Hasn't been tested in   │   │
│  │   games, 11 targets]            │   pressure situations]    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  WR2: D. Smith                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  KNOWN                          │  UNCERTAIN                 │   │
│  │  ─────                          │  ─────────                 │   │
│  │  Speed: Good (4.48)             │  Route Running: Developing?│   │
│  │  Size: 6'3", good catch radius  │  Hands: Inconsistent?     │   │
│  │                                 │  Attitude: ???             │   │
│  │  [New acquisition, only         │  [Haven't seen him in     │   │
│  │   practice tape]                │   game situations]        │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  WR3: R. Adams (Rookie)                                             │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  KNOWN                          │  UNCERTAIN                 │   │
│  │  ─────                          │  ─────────                 │   │
│  │  College Production: 1,200 yds  │  NFL Speed: ???            │   │
│  │  Scout Grade: B+                │  Route Tree: ???           │   │
│  │                                 │  Pro Readiness: ???        │   │
│  │  [Draft pick, combine data      │  [Everything about NFL    │   │
│  │   only]                         │   translation unknown]    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ WAYS TO LEARN MORE ─────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  • Play them in preseason games (most revealing)             │   │
│  │  • Give them practice reps (moderate reveal)                 │   │
│  │  • Watch film with position coach (small reveals)            │   │
│  │  • Wait for regular season (forced reveals, high stakes)     │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Why this matters:**
- Preseason games become genuinely important (you're learning about your team)
- Practice reps have strategic value beyond development
- New acquisitions are risks until proven
- Creates realistic "he looked good in practice but can't do it on Sundays" narratives
- Depth chart decisions are based on what you've *seen*, not what you *know*

**Reveal mechanics:**
- Each game situation reveals specific attributes
- Clutch situations reveal clutch ratings
- Pressure reveals composure
- Complex defensive looks reveal football IQ
- The game tells you when something is revealed: "You learned: D. Smith struggles against press coverage"

---

### 7. The Pressure Gauge

**Concept:** Make the meta-pressure of your job visible and ever-present.

In HC09, the hot seat was real. But it was somewhat binary. What if the pressure was granular, multi-dimensional, and always visible?

```
┌─────────────────────────────────────────────────────────────────────┐
│  JOB SECURITY │ Season 2, Week 10                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─ THE BOARD ROOM ─────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  [OWNER]              [GM]                [BOARD]            │   │
│  │  ████████░░           ██████░░░░          █████░░░░░         │   │
│  │  Satisfied            Concerned           Restless           │   │
│  │                                                              │   │
│  │  "Wins matter.        "Cap situation      "Attendance is     │   │
│  │   We're 5-4.          is tight. We        down 8% from       │   │
│  │   I'm watching."      need a plan."       last year."        │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ THEIR EXPECTATIONS VS. REALITY ─────────────────────────────┐   │
│  │                                                              │   │
│  │  OWNER GOALS                    STATUS                       │   │
│  │  ─────────────                  ──────                       │   │
│  │  Win 10+ games                  On pace: 9 wins ⚠            │   │
│  │  Make playoffs                  Currently: 6th seed ✓        │   │
│  │  Beat the Packers (rival)       Lost Week 4 ✗ (rematch Wk 16)│   │
│  │                                                              │   │
│  │  GM CONCERNS                                                 │   │
│  │  ─────────────                                               │   │
│  │  Cap space next year: $8M (needs $20M for extensions)        │   │
│  │  Draft capital: Missing 2nd round pick                       │   │
│  │  Age curve: Core getting older                               │   │
│  │                                                              │   │
│  │  FAN SENTIMENT                                               │   │
│  │  ──────────────                                              │   │
│  │  Approval: 58% (↓ from 71% start of season)                  │   │
│  │  Hot topics: "Start the rookie QB", "Fire the DC"            │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ YOUR STANDING ──────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  SECURITY:  ██████░░░░░░░░░░░░░░  WARM SEAT                  │   │
│  │                                                              │   │
│  │  "You're not in immediate danger, but another losing         │   │
│  │   streak and questions will be asked. The owner is           │   │
│  │   watching the Packers rematch closely."                     │   │
│  │                                                              │   │
│  │  ESTIMATED RUNWAY: Through end of season if playoffs made    │   │
│  │                    4-6 weeks if playoff hopes collapse       │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Why this matters:**
- Pressure comes from multiple sources with different priorities
- You can see exactly what each stakeholder cares about
- Creates strategic thinking about "managing up"
- Fan sentiment affects owner patience
- GM relationship affects your ability to make moves
- Makes specific games feel more important (the rivalry rematch)

---

### 8. The Living World Ticker

**Concept:** The ticker isn't just news—it's a window into a living league.

Every other team is making decisions. Players are getting injured. Trades are happening. The world moves whether you're watching or not. The ticker should make that world feel alive.

```
Current ticker items (functional):
- SIGNING: J. Smith signs 3yr deal with Patriots
- INJURY: A. Brown (ACL) out for season

Enhanced ticker items (narrative):
- DRAMA: "Sources say Vikings locker room is divided after loss"
- RUMOR: "Multiple teams calling about disgruntled Rams WR"
- UPSET: "Jaguars shock Chiefs in OT, playoff picture scrambled"
- HOT SEAT: "Panthers owner seen meeting with coaching candidates"
- EMERGENCE: "Undrafted rookie RB rushes for 180 yards in debut"
- TRADE BUZZ: "Eagles shopping veteran CB ahead of deadline"
- MILESTONE: "T. Brady passes Favre for career TD record"
- RIVALRY: "Bears-Packers Sunday: Winner takes division lead"
- YOUR NEWS: "League reacts to your controversial fourth-down call"
```

**Personalized ticker:**
- The ticker occasionally features news about YOUR team from the outside perspective
- "Analysts question Bears' decision to start rookie QB"
- "Bears' trade acquisition proving worth early investment"
- "Former Bears draft pick thriving in new home" (callback to your decisions)

---

### 9. The Decision Replay

**Concept:** At the end of each season, replay your key decisions and see their outcomes.

```
┌─────────────────────────────────────────────────────────────────────┐
│  SEASON 2 IN REVIEW │ Your Decisions                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─ FEBRUARY: The Signing ──────────────────────────────────────┐   │
│  │                                                              │   │
│  │  You signed Marcus Williams to a 3yr/$24M deal.              │   │
│  │                                                              │   │
│  │  AT THE TIME:                   │  IN HINDSIGHT:             │   │
│  │  "Worth it for a ball-hawk      │  8 INTs, 2 Pro Bowl        │   │
│  │   safety in his prime"          │  votes, beloved in         │   │
│  │                                 │  locker room               │   │
│  │  Fan approval: 62%              │                            │   │
│  │  Cap hit: $9.2M                 │  VERDICT: Great signing    │   │
│  │                                 │           ████████████     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ APRIL: The Draft ───────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  Round 1, Pick 14: You selected Jake Williams, OT            │   │
│  │                                                              │   │
│  │  AT THE TIME:                   │  IN HINDSIGHT:             │   │
│  │  "Schefter called it a reach.   │  Started 16 games.         │   │
│  │   Fans at 48% approval."        │  Allowed 2 sacks all       │   │
│  │                                 │  season. Rookie of the     │   │
│  │  Alternative: D. Carter, WR     │  Year finalist.            │   │
│  │  (went #15 to Packers,          │                            │   │
│  │   had 1,100 yards)              │  VERDICT: Vindicated       │   │
│  │                                 │           ██████████░░     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ OCTOBER: The Cut ───────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  You released T. Robinson, LB to make room for a waiver claim│   │
│  │                                                              │   │
│  │  AT THE TIME:                   │  IN HINDSIGHT:             │   │
│  │  "Depth piece, not a big loss"  │  Robinson signed with      │   │
│  │                                 │  Cowboys, made Pro Bowl    │   │
│  │  Cap savings: $1.2M             │                            │   │
│  │                                 │  VERDICT: Mistake          │   │
│  │                                 │           ███░░░░░░░░░     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  OVERALL DECISION GRADE: B+                                         │
│  "Strong draft, good free agency, but the Robinson cut hurts."      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Why this matters:**
- Creates accountability for decisions
- Shows what you were thinking vs. what happened
- The "alternative" paths are visible (who did you pass on?)
- Builds long-term narrative (you'll remember "the Robinson mistake" for seasons)
- Makes the game reflective, not just forward-moving

---

### 10. The Sound of Pressure

**Concept:** Audio design that reflects your mental state, not just the game state.

This isn't a UI element, but it affects the UX profoundly.

**The Office:**
- Quiet ambience. Clock ticking. Muffled sounds from outside.
- When events pile up: phone ringing more often, papers shuffling, assistant interrupting
- Owner meeting approaching: subtle tension in the score

**Game Day:**
- Not just crowd noise—your internal state
- Confident: clear audio, steady heartbeat, crisp sounds
- Pressure mounting: slight audio compression, heartbeat audible, crowd more intense
- Critical moment: audio narrows, focused, time slows slightly

**Draft:**
- War room has a specific sound: hushed voices, phones ringing, TV murmuring
- On the clock: ticking becomes prominent
- Trade offer incoming: phone cuts through

**The Idea:** The audio tells you how you should be feeling before you consciously realize it. Games do this in horror. Why not in sports management?

---

### 11. The Unreliable Narrator

**Concept:** Your staff gives you information, but they have biases. Learn who to trust.

```
┌─────────────────────────────────────────────────────────────────────┐
│  SCOUTING REPORT │ D. Carter, WR │ Clemson                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─ SCOUT ASSESSMENTS ──────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  TONY MARTINEZ (Regional Scout - Southeast)                  │   │
│  │  Grade: A                                                    │   │
│  │  "Best receiver in this class. Reminds me of Julio Jones.    │   │
│  │   Can't miss prospect."                                      │   │
│  │                                                              │   │
│  │  Track Record: Tends to overrate SEC/ACC receivers           │   │
│  │  Last 3 years: 2 hits, 4 misses on "can't miss" calls       │   │
│  │  ────────────────────────────────────────────────────────    │   │
│  │                                                              │   │
│  │  SARAH CHEN (National Scout)                                 │   │
│  │  Grade: B+                                                   │   │
│  │  "Good player, but I have concerns about his releases at     │   │
│  │   the line. NFL corners will disrupt him more than college   │   │
│  │   corners did."                                              │   │
│  │                                                              │   │
│  │  Track Record: Conservative but accurate                     │   │
│  │  Last 3 years: Rarely misses, but also rarely finds steals  │   │
│  │  ────────────────────────────────────────────────────────    │   │
│  │                                                              │   │
│  │  MARCUS THOMPSON (Director of Scouting)                      │   │
│  │  Grade: A-                                                   │   │
│  │  "I trust Tony's eye for receivers. But Sarah's concern      │   │
│  │   about releases is valid. He'll need technique coaching."   │   │
│  │                                                              │   │
│  │  Track Record: Synthesis. Usually right on Day 1-2 picks.   │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  WHO DO YOU BELIEVE?                                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Why this matters:**
- Scouts become *characters*, not just information sources
- You learn over time who to trust for what
- Creates emergent narratives ("My regional scout misses on receivers but nails linemen")
- Makes scouting feel like managing a staff, not reading reports
- Disagreement is signal: if everyone agrees, you can be more confident

---

### Implementation Priority

If we were to build these experimental features, here's the order I'd suggest:

| Priority | Feature | Complexity | Impact |
|----------|---------|------------|--------|
| 1 | Confidence Model | Medium | High - Changes how players perform |
| 2 | Memory Wall | Low | High - Adds emotional continuity |
| 3 | Unreliable Narrator | Medium | High - Makes scouting meaningful |
| 4 | Living World Ticker | Low | Medium - World feels alive |
| 5 | Fog of War Depth Chart | Medium | High - Preseason becomes important |
| 6 | Relationship Webs | High | High - Social dynamics visible |
| 7 | Decision Replay | Low | Medium - Reflective storytelling |
| 8 | Unseen Conversation (LLM) | High | Very High - Transformative if done well |
| 9 | Pressure Gauge | Low | Medium - Job security visible |
| 10 | Living Office | High | Medium - Aesthetic, not functional |
| 11 | Sound of Pressure | Medium | Medium - Emotional atmosphere |

---

### The Bet We're Making

Traditional sports games optimize for information access. More stats, faster navigation, complete knowledge.

We're betting on the opposite: **that constraint, uncertainty, and emotion create a more compelling experience than omniscience.**

The player who finishes Huddle shouldn't feel like they optimized a system. They should feel like they lived a career. They should have regrets. They should have triumphs. They should remember specific players, specific games, specific decisions.

That's the mark we're trying to leave on this genre.

---

## LLM Integration: The Living World Engine

> Most games use AI as a black box that makes decisions. We're going to use it as a **narrative engine** that makes the world feel written, reactive, and alive—while maintaining the coherence and memory that makes stories meaningful.

This section explores how Large Language Models can be integrated throughout Huddle to create dynamic, contextual, and emotionally resonant content at every layer of the experience.

### The Core Philosophy

**LLMs should be invisible infrastructure, not a feature.**

Players shouldn't think "oh, the AI wrote this." They should think "this world feels alive." The goal is seamless integration where generated content is indistinguishable from hand-crafted content in quality and coherence.

**Three principles:**

1. **Context is everything.** Every generation has access to rich game state—not just "write a news article" but "write a news article about this specific game, these specific players, this team's season arc, the coach's history with this rival."

2. **Memory creates meaning.** The system remembers what it generated before. If a reporter was skeptical of your draft pick in April, they should eat crow (or double down) in December. Callbacks, continuity, and consequences.

3. **Depth on demand.** Don't generate everything upfront. Generate summaries by default, then generate detail when the player asks for it. Infinite depth, finite compute.

---

### Architecture: The Context Engine

Before diving into specific features, here's how the system works:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CONTEXT ENGINE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─ GAME STATE LAYER ───────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  • Current roster, depth chart, injuries                     │   │
│  │  • Season record, standings, playoff picture                 │   │
│  │  • Recent game results and statistics                        │   │
│  │  • Contract situations, cap space                            │   │
│  │  • Draft picks, scouting reports                             │   │
│  │  • Staff, owner goals, job security                          │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                           │                                         │
│                           ▼                                         │
│  ┌─ NARRATIVE STATE LAYER ──────────────────────────────────────┐   │
│  │                                                              │   │
│  │  • Ongoing storylines (QB controversy, contract holdout)     │   │
│  │  • Relationship history (rivalries, mentorships)             │   │
│  │  • Media personalities and their takes                       │   │
│  │  • Fan sentiment arcs                                        │   │
│  │  • Previous generated content (for continuity)               │   │
│  │  • Player personality profiles                               │   │
│  │  • Decision history and consequences                         │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                           │                                         │
│                           ▼                                         │
│  ┌─ GENERATION LAYER ───────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  LLM receives: game state + narrative state + specific task  │   │
│  │  LLM outputs: content + metadata (for future continuity)     │   │
│  │                                                              │   │
│  │  All outputs stored in narrative state for future reference  │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Key insight:** The LLM isn't just generating text—it's generating text *and* updating the narrative state. When a reporter writes a skeptical article, that skepticism is logged. When a player complains in a meeting, their complaint is logged. This creates continuity.

---

### 1. Dynamic News & Media Ecosystem

**Concept:** A fully simulated sports media landscape with personalities, biases, and memory.

#### Media Personalities

Instead of generic "news," create distinct media voices:

```
┌─────────────────────────────────────────────────────────────────────┐
│  MEDIA LANDSCAPE                                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─ BEAT REPORTERS ─────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  MIKE CHEN │ Chicago Tribune │ Bears Beat                    │   │
│  │  Style: Old school, skeptical of analytics                   │   │
│  │  Bias: Values toughness, questions "soft" players            │   │
│  │  History with you: Initially skeptical, warming up           │   │
│  │                                                              │   │
│  │  Latest: "Coach's gamble on fourth down pays off—this time.  │   │
│  │          But how long can he keep rolling the dice?"         │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ NATIONAL ANALYSTS ──────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  SARAH MARTINEZ │ ESPN │ NFL Analysis                        │   │
│  │  Style: Analytics-driven, scheme-focused                     │   │
│  │  Bias: Loves innovation, critical of conservative play       │   │
│  │  History with you: Praised your offensive scheme early       │   │
│  │                                                              │   │
│  │  Latest: "The Bears' RPO concepts are creating mismatches    │   │
│  │          that defenses simply can't solve."                  │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ HOT TAKE PERSONALITIES ─────────────────────────────────────┐   │
│  │                                                              │   │
│  │  TONY CRAWFORD │ FS1 │ First Things First                    │   │
│  │  Style: Provocative, contrarian, loud                        │   │
│  │  Bias: Changes positions frequently for engagement           │   │
│  │  History with you: Called you "in over your head" Week 3     │   │
│  │                                                              │   │
│  │  Latest: "I TOLD you this coach was special! Everyone        │   │
│  │          doubted him but I saw it from day one!"             │   │
│  │          [Editor's note: He did not.]                        │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Generation approach:**
- Each personality has a defined voice, biases, and history
- When generating their content, include their previous takes for consistency
- Track when they're wrong—they can double down, admit error, or quietly move on
- Their relationship with you evolves based on access, results, and your media handling

#### Depth on Demand: The Article Drill-Down

```
TICKER: "Tribune: Questions linger about Bears' secondary after loss"
                                    │
                                    │ [Click to expand]
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  CHICAGO TRIBUNE │ Mike Chen                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  BEARS' SECONDARY CONCERNS MOUNT AFTER VIKINGS EXPOSE WEAKNESSES   │
│                                                                     │
│  "For the third consecutive week, opposing quarterbacks have        │
│   found success attacking the Bears' cornerbacks on the outside.   │
│   Sunday's 31-24 loss to Minnesota saw Kirk Cousins complete       │
│   78% of his passes, with most of the damage coming against        │
│   second-year corner Marcus Thompson."                              │
│                                                                     │
│  [Generated on click - first paragraph only by default]            │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  [Read Full Article]  [View Box Score]  [Thompson's Stats]   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│                         │                                           │
│                         │ [Click "Read Full Article"]              │
│                         ▼                                           │
│                                                                     │
│  [Full 800-word article generates, including:]                      │
│  • Specific plays and stats from the game                          │
│  • Quote from "a source close to the team"                         │
│  • Historical context (Thompson's draft position, development)     │
│  • Coach's post-game comments (from press conference)              │
│  • What's next: upcoming opponent's passing attack                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Key mechanic:** Headlines are generated cheaply. Article summaries generate on hover/click. Full articles only generate if the player actually wants to read them. Infinite content, finite compute.

#### Newspapers & Publications

```
┌─────────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ ╔═══════════════════════════════════════════════════════╗   │    │
│  │ ║         CHICAGO TRIBUNE SPORTS                        ║   │    │
│  │ ║         Monday, October 16, 2024                      ║   │    │
│  │ ╠═══════════════════════════════════════════════════════╣   │    │
│  │ ║                                                       ║   │    │
│  │ ║  BEARS FALL TO VIKINGS IN DIVISIONAL CLASH           ║   │    │
│  │ ║  Secondary struggles continue in 31-24 defeat         ║   │    │
│  │ ║                                                       ║   │    │
│  │ ║  ┌─────────────────────────────────────────────────┐ ║   │    │
│  │ ║  │         [GAME PHOTO PLACEHOLDER]                │ ║   │    │
│  │ ║  │                                                 │ ║   │    │
│  │ ║  └─────────────────────────────────────────────────┘ ║   │    │
│  │ ║                                                       ║   │    │
│  │ ║  ALSO IN SPORTS:                                      ║   │    │
│  │ ║  • Fields shows flashes despite loss (B2)            ║   │    │
│  │ ║  • Injury report: Two starters questionable (B3)     ║   │    │
│  │ ║  • Column: Time to trust the young corners? (B4)     ║   │    │
│  │ ║                                                       ║   │    │
│  │ ╚═══════════════════════════════════════════════════════╝   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  [Click any headline to read full article]                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Publications have different voices:**
- Local paper: Detailed, invested, knows the history
- National outlet: Big picture, comparison to other teams
- Athletic/Ringer style: Long-form, analytical, personality-driven
- Hot take shows: Provocative, surface-level, engagement-focused
- Fan blogs: Passionate, biased, emotionally reactive

---

### 2. The Draft Experience: Schefter & The War Room

**Concept:** The draft isn't just picks—it's theater. Commentary, reactions, trades, drama.

#### Live Draft Commentary

```
┌─────────────────────────────────────────────────────────────────────┐
│  NFL DRAFT │ Round 1 │ Pick 14 (Your Pick)              ON THE CLOCK│
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─ BROADCAST FEED ─────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  ┌────────────────────────────────────────────────────────┐  │   │
│  │  │  ADAM SCHEFTER @AdamSchefter                    2m ago  │  │   │
│  │  │  "Hearing the Bears are torn between Williams (OT)     │  │   │
│  │  │   and Carter (WR). Could go either way. Some in the    │  │   │
│  │  │   building pushing hard for Carter."                   │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  │                                                              │   │
│  │  ┌────────────────────────────────────────────────────────┐  │   │
│  │  │  MEL KIPER @MelKiperESPN                        1m ago  │  │   │
│  │  │  "If Chicago takes Carter here, that's a B+ pick.      │  │   │
│  │  │   Good value, fills a need. Williams would be an A—    │  │   │
│  │  │   best tackle in the class and they need OL help."     │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  │                                                              │   │
│  │  ┌────────────────────────────────────────────────────────┐  │   │
│  │  │  LIVE: ESPN BROADCAST                                  │  │   │
│  │  │  "The Bears are on the clock and this is a pivotal     │  │   │
│  │  │   moment for the franchise. After last year's          │  │   │
│  │  │   disappointing 7-10 season, they need to nail this    │  │   │
│  │  │   pick. Let's go to our Bears insider..."              │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│                         [YOU SELECT: Jake Williams, OT]             │
│                                       │                             │
│                                       ▼                             │
│                                                                     │
│  ┌─ IMMEDIATE REACTIONS ────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  SCHEFTER: "Bears go with the safe pick in Williams.        │   │
│  │  Solid choice. Day 1 starter. Some in the building wanted   │   │
│  │  Carter but the coach pushed for OL help."                  │   │
│  │                                                              │   │
│  │  FAN POLL: 67% Approval │ 23% Wanted Carter │ 10% Other     │   │
│  │                                                              │   │
│  │  GRADE FROM ANALYSTS:                                        │   │
│  │  Kiper: A- │ McShay: B+ │ Jeremiah: A │ PFF: 8.2/10        │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**What the LLM knows when generating draft commentary:**
- Your team's needs and recent history
- The prospect's scouting report and college stats
- How this pick compares to consensus rankings
- What other teams might have wanted this player
- Your previous draft history (do you favor certain positions?)
- The analyst's personality and past accuracy

#### Pick Announcement & Backstory

```
┌─────────────────────────────────────────────────────────────────────┐
│  THE PICK IS IN                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                             │    │
│  │  "With the 14th pick in the 2025 NFL Draft, the Chicago    │    │
│  │   Bears select..."                                          │    │
│  │                                                             │    │
│  │                   JAKE WILLIAMS                              │    │
│  │                   Offensive Tackle                           │    │
│  │                   Ohio State                                 │    │
│  │                                                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─ THE STORY ──────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  "Williams grew up in Columbus, Ohio, a die-hard Buckeyes   │   │
│  │   fan who walked on to the program as an undersized         │   │
│  │   defensive end. Converted to offensive tackle his          │   │
│  │   sophomore year, he became a three-year starter and        │   │
│  │   unanimous All-American.                                   │   │
│  │                                                              │   │
│  │   His father, Marcus Williams, played six seasons in the    │   │
│  │   NFL as a guard. Jake has talked about wanting to          │   │
│  │   'finish what my dad started' and win a championship.      │   │
│  │                                                              │   │
│  │   At his pro day, he told reporters: 'I don't care where    │   │
│  │   I go. I just want a team that's ready to compete.'"       │   │
│  │                                                              │   │
│  │  [Watch Pro Day Highlights]  [Full Scouting Report]         │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Backstory generation:**
- Each draft prospect gets a procedurally generated backstory
- Hometown, family, college journey, personality
- Generated once during draft class creation, stored for continuity
- Future articles can reference this backstory ("Williams, who walked on at Ohio State...")

---

### 3. Communications Hub: Texts, Emails, Calls

**Concept:** Communication happens through realistic channels—texts, emails, voicemails—each with appropriate tone and urgency.

#### The Phone

```
┌─────────────────────────────────────────────────────────────────────┐
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                         iPHONE                                │  │
│  │  ─────────────────────────────────────────────────────────── │  │
│  │                                                               │  │
│  │   MESSAGES (3)                                     9:41 AM    │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │  Derek Smith                              5 min ago     │ │  │
│  │  │  Hey coach, you got a minute? Need to talk              │ │  │
│  │  │  about something.                                       │ │  │
│  │  │                                               [URGENT]  │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │  Agent: David Chen                        2 hours ago   │ │  │
│  │  │  Coach, David Chen here. Marcus is excited about        │ │  │
│  │  │  the progress. Let's get a deal done this week.         │ │  │
│  │  │  Call me when you can.                                  │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │  Mom                                          Yesterday │ │  │
│  │  │  Watched the game! So proud of you. Dad would           │ │  │
│  │  │  have loved that fourth quarter comeback.               │ │  │
│  │  │  Call when you can. Love you.                           │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  │                                                               │  │
│  │  ─────────────────────────────────────────────────────────── │  │
│  │                                                               │  │
│  │   VOICEMAIL (1)                                               │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │  Owner: Richard Morrison                  This morning  │ │  │
│  │  │  Duration: 0:34                                         │ │  │
│  │  │  [PLAY]                                                 │ │  │
│  │  │                                                         │ │  │
│  │  │  Transcript: "Coach, Richard here. Good win Sunday.     │ │  │
│  │  │  But we need to talk about the secondary situation.     │ │  │
│  │  │  Come by my office tomorrow. Not a request."            │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Communication channels serve different purposes:**

| Channel | Tone | Use Cases |
|---------|------|-----------|
| Text (Player) | Casual, personal | Quick check-ins, complaints, locker room pulse |
| Text (Agent) | Professional-casual | Negotiation probes, relationship building |
| Text (Family) | Humanizing | Emotional grounding, personal stakes |
| Email | Formal | Official communications, memos, league notices |
| Voicemail | Urgent/Important | Owner demands, agent ultimatums, media requests |
| Call (Live) | Real-time | Critical negotiations, confrontations |

#### Text Conversations

```
┌─────────────────────────────────────────────────────────────────────┐
│  ← Derek Smith                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                           TUESDAY 9:36 AM                           │
│                                                                     │
│  ┌────────────────────────────────────────┐                         │
│  │ Hey coach, you got a minute? Need to   │                         │
│  │ talk about something.                  │                         │
│  └────────────────────────────────────────┘                         │
│                                                                     │
│                         ┌────────────────────────────────────────┐  │
│                         │ What's on your mind?                   │  │
│                         └────────────────────────────────────────┘  │
│                                                                     │
│  ┌────────────────────────────────────────┐                         │
│  │ It's about Sunday. I was open three    │                         │
│  │ times in the fourth quarter and Justin │                         │
│  │ didn't even look my way.               │                         │
│  └────────────────────────────────────────┘                         │
│                                                                     │
│  ┌────────────────────────────────────────┐                         │
│  │ I'm not trying to cause problems but   │                         │
│  │ I need to know if there's a future for │                         │
│  │ me here or if I should ask for a trade │                         │
│  └────────────────────────────────────────┘                         │
│                                                                     │
│  ┌─ YOUR RESPONSE ──────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐    │   │
│  │  │ I saw those plays. Let me talk to Justin. You're     │    │   │
│  │  │ a big part of this team's future.                    │    │   │
│  │  │                                            [SEND]    │    │   │
│  │  └──────────────────────────────────────────────────────┘    │   │
│  │                                                              │   │
│  │  [Type custom response...]                                   │   │
│  │                                                              │   │
│  │  Quick replies:                                              │   │
│  │  [Come to my office] [I'll look at the film] [We'll talk]   │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### Email Inbox

```
┌─────────────────────────────────────────────────────────────────────┐
│  INBOX                                                    2 Unread  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ★ NFL League Office                               Today, 8:00 AM   │
│    RE: Fines and Violations - Week 7                                │
│    "This notice confirms a fine of $25,000 has been assessed..."    │
│                                                                     │
│  ★ Mike Chen (Tribune)                             Today, 7:15 AM   │
│    Interview Request - Secondary Concerns                           │
│    "Coach, would you be available for 15 minutes today to..."       │
│                                                                     │
│    David Chen (Agent)                              Yesterday        │
│    RE: Marcus Williams Contract Extension                           │
│    "Coach, I've attached the revised term sheet. Marcus is..."      │
│                                                                     │
│    Sarah Martinez (ESPN)                           Yesterday        │
│    Feature Request - Your Offensive Philosophy                      │
│    "We're doing a piece on innovative offensive minds and..."       │
│                                                                     │
│    HR Department                                   Monday           │
│    Coaching Staff Evaluations Due                                   │
│    "Please complete your mid-season coaching staff evaluations..."  │
│                                                                     │
│    NFL League Office                               Monday           │
│    Trade Deadline Reminder                                          │
│    "This is a reminder that the trade deadline is..."               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Emails can require responses that affect the game:**
- Media interview requests (accept/decline affects relationship, coverage tone)
- League notices (fines, rule changes, investigations)
- Agent communications (formal negotiation steps)
- Internal staff (evaluations, requests, complaints)

---

### 4. Press Conferences & Media Availability

**Concept:** You speak to the media. Your words have consequences.

```
┌─────────────────────────────────────────────────────────────────────┐
│  POST-GAME PRESS CONFERENCE                                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                             │    │
│  │  [PRESS ROOM - You at podium, reporters seated]             │    │
│  │                                                             │    │
│  │  MODERATOR: "Coach, opening statement?"                     │    │
│  │                                                             │    │
│  │  [You gave opening statement - see transcript]              │    │
│  │                                                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─ CURRENT QUESTION ───────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  MIKE CHEN (Tribune):                                        │   │
│  │  "Coach, Marcus Thompson got beat badly on three             │   │
│  │   touchdowns today. At what point do you consider making     │   │
│  │   a change at corner?"                                       │   │
│  │                                                              │   │
│  │  [Chen is testing you - he wrote critically this week]       │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ YOUR RESPONSE OPTIONS ──────────────────────────────────────┐   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐    │   │
│  │  │ [DEFEND] "Marcus is our guy. He had a tough day but  │    │   │
│  │  │ he's been solid all year. I'm not making any changes."│   │   │
│  │  │                                                       │   │   │
│  │  │ Effect: Thompson's confidence +, Chen relationship -  │    │   │
│  │  │ Risk: If Thompson struggles again, you look stubborn  │    │   │
│  │  └──────────────────────────────────────────────────────┘    │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐    │   │
│  │  │ [DEFLECT] "We're evaluating everything on film.      │    │   │
│  │  │ I'm not going to make any decisions standing here."  │    │   │
│  │  │                                                       │   │   │
│  │  │ Effect: Neutral, but evasive—may frustrate media     │    │   │
│  │  │ Risk: "Coach refuses to address secondary issues"    │    │   │
│  │  └──────────────────────────────────────────────────────┘    │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐    │   │
│  │  │ [CHALLENGE] "You want to talk about Marcus? Let's    │    │   │
│  │  │ talk about the three dropped passes by our receivers.│    │   │
│  │  │ There's plenty of blame to go around."               │    │   │
│  │  │                                                       │   │   │
│  │  │ Effect: Redirects narrative, but may upset WR room   │    │   │
│  │  │ Risk: "Coach throws receivers under the bus"         │    │   │
│  │  └──────────────────────────────────────────────────────┘    │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐    │   │
│  │  │ [FREE RESPONSE] Type your own answer...              │    │   │
│  │  │                                                       │   │   │
│  │  │ AI interprets tone and content for consequences      │    │   │
│  │  └──────────────────────────────────────────────────────┘    │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Questions remaining: 4 │ [END PRESS CONFERENCE EARLY]              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Press conference consequences:**
- Your quotes appear in generated articles
- Players read what you say about them (affects morale, trust)
- Consistent messaging builds reputation
- Contradicting yourself gets noticed ("Last week you said...")
- Walking out early has consequences
- Going viral (good or bad) affects fan sentiment

#### The Follow-Up Coverage

After your press conference:

```
┌─────────────────────────────────────────────────────────────────────┐
│  MEDIA REACTION TO YOUR PRESS CONFERENCE                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  YOUR STATEMENT: "Marcus is our guy. He had a tough day but         │
│  he's been solid all year. I'm not making any changes."             │
│                                                                     │
│  ┌─ COVERAGE ───────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  TRIBUNE: "Coach doubles down on struggling Thompson"        │   │
│  │  Tone: Critical │ "Stubbornness may cost Bears season"      │   │
│  │                                                              │   │
│  │  ESPN: "Bears coach shows loyalty to young corner"           │   │
│  │  Tone: Neutral │ "Whether that loyalty pays off..."         │   │
│  │                                                              │   │
│  │  TWITTER: Mixed reaction │ 45% support, 55% critical         │   │
│  │  Trending: #BenchThompson                                    │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ LOCKER ROOM REACTION ───────────────────────────────────────┐   │
│  │                                                              │   │
│  │  Marcus Thompson heard your comments.                        │   │
│  │  Confidence: ████████████░░░░░░░░ (+15%)                     │   │
│  │  "Coach has my back. I'm going to show him he's right."      │   │
│  │                                                              │   │
│  │  Derek Smith (WR) also noticed.                              │   │
│  │  Thought: "He defends Thompson but won't commit to me?"      │   │
│  │  [Potential friction developing]                             │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 5. Staff Meetings & One-on-Ones

**Concept:** Regular meetings with staff that affect strategy, morale, and information flow.

```
┌─────────────────────────────────────────────────────────────────────┐
│  WEEKLY STAFF MEETING │ Wednesday, 8:00 AM                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                             │    │
│  │  [MEETING ROOM - Coordinators seated around table]          │    │
│  │                                                             │    │
│  │  PRESENT:                                                   │    │
│  │  • Jim Bradley (OC) - Energetic today                       │    │
│  │  • Marcus Cole (DC) - Defensive, frustrated                 │    │
│  │  • Tony Reeves (ST) - Quiet as usual                        │    │
│  │  • Sarah Chen (GM) - Taking notes                           │    │
│  │                                                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─ CURRENT TOPIC ──────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  DC MARCUS COLE:                                             │   │
│  │                                                              │   │
│  │  "Coach, I've got to be honest with you. Thompson isn't      │   │
│  │   ready. I've been saying it for weeks. We need to look      │   │
│  │   at moving Jenkins outside or signing someone."             │   │
│  │                                                              │   │
│  │  He glances at the GM. "I know we don't have cap room,       │   │
│  │  but something has to change."                               │   │
│  │                                                              │   │
│  │  [Cole gave up DB depth chart control to get hired.          │   │
│  │   He's frustrated you won't follow his recommendation.]      │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ STAFF REACTIONS (visible) ──────────────────────────────────┐   │
│  │                                                              │   │
│  │  OC Bradley: [Neutral - not his area, staying quiet]         │   │
│  │  GM Chen: [Agrees with Cole but won't contradict you]        │   │
│  │  ST Reeves: [Checking his phone]                             │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ YOUR RESPONSE ──────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  [AGREE] "You're right. Let's look at Jenkins outside."      │   │
│  │  → Improves Cole relationship, changes depth chart           │   │
│  │                                                              │   │
│  │  [DEFER] "Let's give Thompson one more week."                │   │
│  │  → Cole frustrated, but complies                             │   │
│  │                                                              │   │
│  │  [PUSH BACK] "I've seen the film. Thompson is fine."         │   │
│  │  → Cole may disengage, stop giving honest opinions           │   │
│  │                                                              │   │
│  │  [REDIRECT] "Sarah, what are our options on the market?"     │   │
│  │  → Opens new discussion, shows you're listening              │   │
│  │                                                              │   │
│  │  [Free response...]                                          │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  MEETING AGENDA:                                                    │
│  ✓ Vikings game review                                              │
│  → Secondary concerns (current)                                     │
│  ○ Packers game prep                                                │
│  ○ Injury updates                                                   │
│  ○ Practice schedule                                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Staff meeting dynamics:**
- Coordinators have opinions and agendas
- They react to each other, not just you
- Information flows through these meetings (injury updates, scout reports)
- Your responses shape the culture (do people speak up or stay quiet?)
- Skip meetings to save time, but miss information and damage relationships

---

### 6. Voice & Audio Integration

**Concept:** Use voice LLMs for key dramatic moments—not everything, but pivotal scenes.

#### When to Use Voice

| Context | Voice? | Rationale |
|---------|--------|-----------|
| Ticker/News | No | High volume, reading preferred |
| Emails/Texts | No | Natural format |
| Owner calls | Yes | Power dynamic, intimidation |
| Draft announcement | Yes | Theatrical moment |
| Locker room speech | Yes | Emotional peak |
| Post-game presser | Optional | Player choice |
| Agent negotiations | Maybe | Key moments only |

#### The Owner Call

```
┌─────────────────────────────────────────────────────────────────────┐
│  INCOMING CALL: Richard Morrison (Owner)                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                             │    │
│  │                    [PHONE RINGING]                          │    │
│  │                                                             │    │
│  │                      RICHARD                                │    │
│  │                      MORRISON                               │    │
│  │                        Owner                                │    │
│  │                                                             │    │
│  │          [ANSWER]              [DECLINE]                    │    │
│  │                                                             │    │
│  │   (Declining will not make this go away)                    │    │
│  │                                                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

[Player answers]

┌─────────────────────────────────────────────────────────────────────┐
│  CALL: Richard Morrison                                    2:34     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [AUDIO PLAYS - Voice generated, stern older male voice]            │
│                                                                     │
│  "Coach. I'm going to be direct with you. I didn't buy this         │
│   team to finish 8-9. The Packers game is Sunday. A hundred         │
│   thousand fans are going to be watching. Half the city.            │
│                                                                     │
│   I need to know—can we win this game? And don't give me            │
│   coach-speak. I want a real answer."                               │
│                                                                     │
│  ┌─ YOUR RESPONSE ──────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  [CONFIDENT] "We'll win. This team is ready."                │   │
│  │  → Sets expectation. Losing badly will have consequences.    │   │
│  │                                                              │   │
│  │  [HONEST] "It'll be close. Their pass rush is elite."        │   │
│  │  → He respects honesty, but wants to hear confidence.        │   │
│  │                                                              │   │
│  │  [DEFLECT] "We're preparing like it's the Super Bowl."       │   │
│  │  → Safe but unsatisfying. He wanted a real answer.           │   │
│  │                                                              │   │
│  │  [Record your response]  🎤                                  │   │
│  │  → Voice input interpreted by AI                             │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Voice input option:**
- Player can speak their response
- AI transcribes and interprets
- Allows for natural conversation
- Optional—presets always available

#### Locker Room Speech

```
┌─────────────────────────────────────────────────────────────────────┐
│  PRE-GAME │ Locker Room │ vs. Packers                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                             │    │
│  │  [LOCKER ROOM - Team gathered, waiting]                     │    │
│  │                                                             │    │
│  │  The room is quiet. You can feel the tension.               │    │
│  │  This is the biggest game of the season.                    │    │
│  │                                                             │    │
│  │  53 players. Your coaching staff. All eyes on you.          │    │
│  │                                                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─ GIVE YOUR SPEECH ───────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  SPEECH TYPE:                                                │   │
│  │  ○ Fire them up (intensity, aggression)                      │   │
│  │  ○ Focus them (calm, precise, execution)                     │   │
│  │  ○ Inspire them (meaning, legacy, brotherhood)               │   │
│  │  ○ Challenge them (doubt, prove everyone wrong)              │   │
│  │                                                              │   │
│  │  PERSONALIZE:                                                │   │
│  │  □ Call out Marcus Thompson (he needs confidence)            │   │
│  │  □ Reference the Week 4 loss to Green Bay                    │   │
│  │  □ Mention the owner's expectations                          │   │
│  │  □ Talk about the fans                                       │   │
│  │                                                              │   │
│  │  [Generate Speech]                                           │   │
│  │                                                              │   │
│  │  ─── OR ───                                                  │   │
│  │                                                              │   │
│  │  [Write/Record Your Own Speech]  🎤                          │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

[Player selects "Fire them up" + "Call out Thompson" + "Reference Week 4"]

┌─────────────────────────────────────────────────────────────────────┐
│  YOUR SPEECH                                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [AUDIO PLAYS - Your coach's voice, intense]                        │
│                                                                     │
│  "Listen up! Week 4, we went into Green Bay and they                │
│   embarrassed us. 34-17. Their fans were laughing at us.            │
│   Their players were talking trash all week.                        │
│                                                                     │
│   Today? They're in OUR house. And they think they already won.     │
│                                                                     │
│   Marcus—" [looks at Thompson] "—you've heard what they're          │
│   saying about you. Every analyst, every reporter. They think       │
│   you can't play. You want to prove them wrong? Today's the day.    │
│                                                                     │
│   This is our moment. Let's TAKE it!"                               │
│                                                                     │
│  [TEAM REACTION: Energy HIGH │ Thompson Confidence +20%]            │
│                                                                     │
│  [Play Ball]                                                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 7. Dynamic Depth: Click to Generate More

**Concept:** Content generates at the level of detail you want. Drill down infinitely.

```
SURFACE LEVEL (Always visible):
┌─────────────────────────────────────────────────────────────────┐
│  Jake Williams │ OT │ Ohio State │ Your Grade: A-               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ [Click for more]
                                ▼
FIRST EXPANSION (Generated on click):
┌─────────────────────────────────────────────────────────────────┐
│  Jake Williams │ OT │ Ohio State                                │
├─────────────────────────────────────────────────────────────────┤
│  Height: 6'5" │ Weight: 315 │ 40-yard: 5.12                     │
│  Projected: Round 1 (Top 15) │ Your Board: #2 OT                │
│                                                                 │
│  SCOUT SUMMARY:                                                 │
│  "Elite feet, strong anchor. Day 1 starter. Some concerns       │
│   about consistency in pass protection vs. speed."              │
│                                                                 │
│  [Full Scouting Report] [College Stats] [Personality Profile]   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ [Click "Full Scouting Report"]
                                ▼
SECOND EXPANSION (Generated on click):
┌─────────────────────────────────────────────────────────────────┐
│  FULL SCOUTING REPORT: Jake Williams                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [2000-word detailed report generates, including:]              │
│                                                                 │
│  • Detailed technique analysis by your scouts                   │
│  • Game-by-game breakdown of key matchups                       │
│  • Comparison to NFL players with similar profiles              │
│  • Interview notes and personality assessment                   │
│  • Injury history and durability concerns                       │
│  • Projection for your specific scheme                          │
│                                                                 │
│  [Watch Film Highlights] [Scout Disagreements] [Ask Scout]      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ [Click "Ask Scout"]
                                ▼
THIRD EXPANSION (Live conversation):
┌─────────────────────────────────────────────────────────────────┐
│  CONVERSATION: Tony Martinez (Regional Scout)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  You: "Tony, you've watched Williams more than anyone.          │
│        What's your gut say?"                                    │
│                                                                 │
│  Tony: "Coach, he's the real deal. I've seen every snap         │
│         he's played in three years. That game against Michigan  │
│         where he handled Hutchinson? That's NFL ready.          │
│                                                                 │
│         My one concern—and this is just my gut—he sometimes     │
│         gets lazy in the run game. Like he knows he's better    │
│         than everyone and doesn't need to finish blocks.        │
│         Coachable? Probably. But worth watching."               │
│                                                                 │
│  [Ask follow-up question...]                                    │
│  [End conversation]                                             │
└─────────────────────────────────────────────────────────────────┘
```

**Key insight:** You can keep drilling down forever. Each click generates more. But you don't have to. The surface level is always coherent and sufficient.

---

### 8. Living Game Recaps & Commentary

**Concept:** Every game gets a unique, contextual recap—not just stats.

```
┌─────────────────────────────────────────────────────────────────────┐
│  GAME RECAP │ Bears 31, Packers 28                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─ THE STORY ──────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  REDEMPTION IN THE RIVALRY                                   │   │
│  │                                                              │   │
│  │  "Three months ago, the Bears left Green Bay humiliated.     │   │
│  │   34-17. Their secondary in tatters, their playoff hopes     │   │
│  │   seemingly doomed.                                          │   │
│  │                                                              │   │
│  │   Sunday at Soldier Field, they answered.                    │   │
│  │                                                              │   │
│  │   Marcus Thompson—the same cornerback critics wanted         │   │
│  │   benched all week—picked off Jordan Love twice in the       │   │
│  │   fourth quarter. The second one, a diving interception      │   │
│  │   at the goal line with 1:34 remaining, sealed a 31-28       │   │
│  │   victory that puts Chicago in control of the NFC North.     │   │
│  │                                                              │   │
│  │   'I heard everything they said,' Thompson told reporters    │   │
│  │   after the game. 'Coach believed in me. I wasn't going      │   │
│  │   to let him down.'                                          │   │
│  │                                                              │   │
│  │   Indeed, head coach [YOUR NAME] defended Thompson all       │   │
│  │   week, telling reporters Monday that he was 'our guy.'      │   │
│  │   That faith was rewarded in spectacular fashion."           │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ KEY MOMENTS ────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  Q2 4:32 │ Fields to Smith │ 43-yard TD                      │   │
│  │  "The connection that had been missing all season finally    │   │
│  │   clicked. Smith beat double coverage and Fields delivered." │   │
│  │                                                              │   │
│  │  Q4 3:12 │ Thompson INT #1                                   │   │
│  │  "Love tried to force it to Watson. Thompson read it         │   │
│  │   perfectly. The stadium erupted."                           │   │
│  │                                                              │   │
│  │  Q4 1:34 │ Thompson INT #2 │ GAME-SEALING                    │   │
│  │  "Diving interception at the goal line. The play that        │   │
│  │   silenced every critic."                                    │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [Full Box Score] [Play-by-Play] [Watch Highlights] [Reactions]     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**What makes this work:**
- Knows the story (Thompson was criticized, you defended him)
- Callbacks to previous events (Week 4 loss, your press conference)
- Generates player quotes that match their personality
- Frames the game in narrative terms, not just stats
- Different publications would write this differently

---

### 9. Procedural Player Personalities & Histories

**Concept:** Every generated player has a coherent personality, history, and voice.

```
┌─────────────────────────────────────────────────────────────────────┐
│  PLAYER PROFILE │ Generated on Draft Day, Persistent Forever       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  MARCUS WILLIAMS │ S │ 28 years old                                 │
│                                                                     │
│  ┌─ BIOGRAPHY ──────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  Born in Baton Rouge, Louisiana. Third of five children.     │   │
│  │  Father was a high school coach who died when Marcus was 16. │   │
│  │  Played at LSU, walking distance from home, to stay close    │   │
│  │  to family. Second-round pick by the Saints in 2019.         │   │
│  │                                                              │   │
│  │  Deeply religious. Known for community work. Quiet in the    │   │
│  │  locker room but respected. Teammates call him "Deacon."     │   │
│  │                                                              │   │
│  │  Two Pro Bowls. One All-Pro. Missed playoffs every year.     │   │
│  │  Obsessed with winning a championship before he retires.     │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ PERSONALITY TRAITS ─────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  Leadership:     ████████████████░░░░  High                  │   │
│  │  Ego:            ████░░░░░░░░░░░░░░░░  Low                   │   │
│  │  Work Ethic:     ██████████████████░░  Elite                 │   │
│  │  Volatility:     ██░░░░░░░░░░░░░░░░░░  Very Low              │   │
│  │  Media Comfort:  ████████░░░░░░░░░░░░  Moderate              │   │
│  │                                                              │   │
│  │  MOTIVATIONS:                                                │   │
│  │  1. Championship (primary - will sacrifice money for it)     │   │
│  │  2. Team culture (wants to be on a "good" team)              │   │
│  │  3. Role (expects to start)                                  │   │
│  │  4. Money (secondary - but has a family to support)          │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ COMMUNICATION STYLE ────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  Texts: Short, formal, uses proper grammar                   │   │
│  │  In person: Thoughtful, makes eye contact, listens           │   │
│  │  Under stress: Gets quieter, not louder                      │   │
│  │  When unhappy: Will come to you directly, no drama           │   │
│  │                                                              │   │
│  │  Sample voice: "Coach, I appreciate you being straight       │   │
│  │  with me. That's all I ask. Just tell me where I stand."     │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**This profile informs ALL future generations:**
- His texts sound like him
- His interview quotes match his personality
- His negotiations reflect his motivations
- His reactions to events are consistent
- Media describes him consistently

---

### 10. The Meta-Narrative Engine

**Concept:** The game tracks storylines and weaves them through all content.

```
┌─────────────────────────────────────────────────────────────────────┐
│  ACTIVE STORYLINES (System Tracking)                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─ STORYLINE: "Thompson's Redemption Arc" ─────────────────────┐   │
│  │                                                              │   │
│  │  Started: Week 5 (after Vikings game)                        │   │
│  │  Status: ONGOING → Potential resolution Week 12 vs. Packers  │   │
│  │                                                              │   │
│  │  Key beats:                                                  │   │
│  │  • Week 5: Thompson struggles, 3 TDs allowed                 │   │
│  │  • Week 6: Media calls for benching                          │   │
│  │  • Week 6: You defend him in press conference                │   │
│  │  • Week 7: Thompson has bounce-back game                     │   │
│  │  • Week 11: Stakes raised—Packers rematch looming            │   │
│  │                                                              │   │
│  │  Potential resolutions:                                      │   │
│  │  • He balls out vs. Packers (vindication)                    │   │
│  │  • He struggles again (you were wrong)                       │   │
│  │  • Mixed performance (story continues)                       │   │
│  │                                                              │   │
│  │  This storyline affects: All Thompson media coverage,        │   │
│  │  his confidence, your job security narrative, fan sentiment  │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─ STORYLINE: "The Owner's Patience" ──────────────────────────┐   │
│  │                                                              │   │
│  │  Started: Preseason (owner set playoff expectation)          │   │
│  │  Status: TENSION BUILDING                                    │   │
│  │                                                              │   │
│  │  Key beats:                                                  │   │
│  │  • Preseason: Owner says "playoffs or else"                  │   │
│  │  • Week 4: Lose to Packers, owner calls you                  │   │
│  │  • Week 8: 4-4 record, owner "watching closely"              │   │
│  │  • Week 10: Currently 6-4, playoff spot in reach             │   │
│  │                                                              │   │
│  │  Affects: Job security, owner call frequency, media          │   │
│  │  speculation about your future, end-of-season evaluation     │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  OTHER ACTIVE STORYLINES:                                           │
│  • "Derek Smith's Contract Year" (pending resolution: offseason)    │
│  • "Rookie QB Development" (Jake Williams learning curve)           │
│  • "Rivalry Renewed" (Bears-Packers season series)                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**How storylines work:**
- System identifies emerging narratives from game events
- Tracks key beats and potential resolutions
- Injects storyline context into all relevant generations
- Creates callbacks ("Remember when you said...")
- Builds toward climactic moments

---

### Technical Implementation Notes

#### Generation Tiers

| Tier | Content | Generation | Cache |
|------|---------|------------|-------|
| 1 | Headlines, ticker | Pre-generated batch | Session |
| 2 | Article summaries | On-demand, simple | Long |
| 3 | Full articles | On-demand, detailed | Short |
| 4 | Conversations | Real-time, contextual | None |
| 5 | Voice output | Real-time, expensive | None |

#### Context Window Management

```
PROMPT STRUCTURE:

[SYSTEM: Role and voice definition]
[GAME STATE: Compressed current state - ~500 tokens]
[NARRATIVE STATE: Active storylines, relationships - ~300 tokens]
[ENTITY CONTEXT: Relevant player/staff profiles - ~400 tokens]
[HISTORY: Recent related generations - ~300 tokens]
[TASK: Specific generation request - ~100 tokens]

Total context budget: ~1600 tokens input
Output budget: Varies by tier (100-2000 tokens)
```

#### Consistency Enforcement

- Entity database with immutable facts (names, birthdates, draft positions)
- Mutable state (relationships, confidence, storyline status)
- Generation validation against known facts
- Contradiction detection and resolution

#### Cost Management

- Batch generation during natural pauses (loading screens, sim time)
- Aggressive caching of reusable content
- Tiered model selection (smaller models for simple content)
- Player-controlled verbosity settings

---

### The Promise

With this system, every career is unique. Not because the stats are different—but because the *stories* are different. The reporter who doubted you. The player who became your guy. The owner who almost fired you. The draft pick everyone laughed at.

These aren't just things that happened. They're things the game *remembers* and *talks about*. They become part of the narrative fabric that makes your career feel like it mattered.

That's the promise of LLM integration done right: not artificial intelligence, but artificial *memory*. A world that remembers what you did and never lets you forget it.

---

### The Bet We're Making (Revisited)

Traditional sports games optimize for information access. More stats, faster navigation, complete knowledge.

We're betting on the opposite: **that constraint, uncertainty, and emotion create a more compelling experience than omniscience.**

And now, with LLMs, we're adding a second bet: **that a world with memory, voice, and narrative creates more meaning than a world of pure mechanics.**

The player who finishes Huddle shouldn't feel like they optimized a system. They should feel like they lived a career. They should have regrets. They should have triumphs. They should remember specific players, specific games, specific decisions.

And the game should remember them too.

That's the mark we're trying to leave on this genre.

---

*This is a living document. Update as we learn what works and what doesn't.*
