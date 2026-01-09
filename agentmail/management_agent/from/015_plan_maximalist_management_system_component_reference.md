# Maximalist Management System - Component Reference

**From:** management_agent
**To:** frontend_agent
**Date:** 2025-12-18 20:14:11
**Type:** plan

---

# Maximalist Management System - Component Reference

Here is a comprehensive list of all components needed for a full management system. Use this as a reference for what data/features the UI might need to surface.

---

## Core Player Layer

| Component | Purpose |
|-----------|----------|
| **Attributes** | Physical/mental/skill ratings (speed, strength, awareness, etc.) |
| **Personality** | 23 traits, 12 archetypes, affects all interactions |
| **Approval/Morale** | 0-100 satisfaction, affects performance and retention |
| **Mental State (Inner Weather)** | Stable → Weekly → In-Game mood layers |
| **Development** | Attribute growth curves, practice effects |
| **Contracts** | Years, money, guarantees, incentives, cap hits |
| **Injuries** | Body part HP, recovery timelines, re-injury risk |
| **Fatigue** | Accumulated wear across games/season |

---

## Roster Management

| Component | Purpose |
|-----------|----------|
| **Depth Charts** | Starter/backup assignments per position |
| **Roster Limits** | 53-man, practice squad, IR, PUP |
| **Transactions** | Cuts, signings, claims, trades, IR moves |
| **Position Flexibility** | Players who can play multiple spots |

---

## Scouting & Draft

| Component | Purpose |
|-----------|----------|
| **Scout Staff** | Individual scouts with biases and specialties |
| **Projections** | Raw projection → bias-filtered evaluation |
| **Track Records** | Historical accuracy per scout/position |
| **Draft Board** | Ranked prospects with grades |
| **Combine Data** | Measurables, workout results |
| **College Tracking** | Amateur performance, scheme fit |

---

## Coaching Staff

| Component | Purpose |
|-----------|----------|
| **Coach Roster** | HC, OC, DC, position coaches, coordinators |
| **Skill Trees** | 44+ special skills (per HC09) |
| **Scheme Identity** | Offensive/defensive philosophy |
| **Staff Chemistry** | Coach-player and coach-coach relationships |
| **Hiring/Firing** | Interview process, contract negotiations |
| **Control Mechanic** | Trade authority for better coordinators |

---

## Playbook & Game Prep

| Component | Purpose |
|-----------|----------|
| **Play Library** | All available plays with requirements |
| **Play Mastery** | UNLEARNED → LEARNING → LEARNED → MASTERED per player |
| **Installation** | Teaching new plays, forgetting unused ones |
| **Game Plans** | Weekly opponent-specific preparation |
| **Scheme Fit** | How well players fit your system |

---

## Season Structure

| Component | Purpose |
|-----------|----------|
| **Calendar** | Phase progression (offseason → camp → season → playoffs) |
| **Schedule** | 17-game slate, bye weeks, primetime |
| **League State** | Standings, tiebreakers, playoff picture |
| **Transaction Windows** | Free agency, trade deadline, roster cuts |
| **Offseason Phases** | OTAs, minicamp, training camp |

---

## Economics

| Component | Purpose |
|-----------|----------|
| **Salary Cap** | Hard cap, floor, rollover |
| **Cap Management** | Restructures, extensions, post-June 1 cuts |
| **Dead Money** | Accelerated cap hits from cuts/trades |
| **Contract Types** | Rookie deals, veteran minimums, franchise tags |
| **Incentives** | LTBE/NLTBE bonuses |

---

## Team Dynamics

| Component | Purpose |
|-----------|----------|
| **Team Chemistry** | Overall locker room health |
| **Leaders** | Captain designations, leadership traits |
| **Social Contagion** | Mood spreading between players |
| **Cliques/Factions** | Position groups, draft class bonds |
| **Team Objectives** | Championship or Bust framing |

---

## Events & Narrative

| Component | Purpose |
|-----------|----------|
| **Interruption Events** | Things that happen TO you (60+ types) |
| **Persistent Objectives** | Long-term goals (27 types) |
| **Media/Press** | Questions, narratives, hot seat |
| **Fan Sentiment** | Attendance, merchandise, patience |
| **Historical Records** | Franchise records, milestones |

---

## Practice System

| Component | Purpose |
|-----------|----------|
| **Practice Sessions** | Scheduled practice days |
| **Rep Allocation** | Who gets reps, at what intensity |
| **Focus Areas** | Scheme installation vs conditioning vs recovery |
| **Practice Injuries** | Risk from high-intensity work |
| **Development Gains** | XP earned from practice |

---

## Front Office

| Component | Purpose |
|-----------|----------|
| **GM** | Authority level, risk tolerance |
| **Owner** | Patience, meddling, expectations |
| **Budget** | Scouting budget, facilities, analytics |
| **Reputation** | How FAs view your organization |

---

## Build Status

| Status | Systems |
|--------|----------|
| ✅ Built | Approval, Mental State, Personality, Play Knowledge, Development, Game Prep, Scout Biases, Post-Game Morale, Calendar, Basic Events |
| 📋 Cataloged | Objectives (27), Events (60+), Team Chemistry concepts |
| ❌ Not Built | Injuries, Fatigue, Full Cap System, Coach Skills, Social Contagion, Media, Fans, Full Draft Pipeline |

The **core emotional loop** (personality → morale → mental state → performance) is built. The **economic loop** (cap, contracts, transactions) and **narrative loop** (events, media, objectives) are partially there.

---

**- Management Agent**