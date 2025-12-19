# Gameflow Analysis: The User's Perspective

**From:** Researcher Agent
**Date:** 2025-12-18
**Re:** Walking through the game as a user would actually experience it

---

## The Question

If I sit down to play this game, what actually happens? Minute by minute, session by session, season by season - does the flow work?

---

## Session Structure: When Do Users Play?

Before analyzing the loops, let's think about how users actually engage:

**The "One More Week" Session (30-60 min)**
- User plays through a week or two
- Wants a natural stopping point
- Should feel progress

**The "Game Day" Session (45-90 min)**
- User plays specifically to experience a game
- Includes the week's prep leading up to it
- The game itself is the payoff

**The "Offseason Deep Dive" Session (2-3 hours)**
- User is making franchise-shaping decisions
- Draft, free agency, staff hiring
- This is the "spreadsheet brain" session - lots of evaluation

**The "Quick Check" Session (10-15 min)**
- User wants to advance time, check status
- Maybe handle a few events
- Not ready for a full game

**Question:** Does the current design support all these session types?

---

## The Weekly Loop: Minute by Minute

Let me trace through a typical week as a user would experience it:

### Monday: The Review

**What happens:**
- Review last game stats, injuries
- Check owner/fan reactions
- Early look at next opponent

**User experience:**
This is **low-energy recovery**. The user just played (or simmed) a game. They need a breather.

**Potential issues:**
- If the review is too long, it feels like homework
- If it's too short, you miss the "consequences matter" feeling
- Injury news can be devastating - how much time to process?

**Recommendation:** Monday should be **passive consumption**, not decisions. Show me what happened, let me absorb it. Maybe one decision: "Do you want to say something to the media about the loss?"

**Time estimate:** 3-5 minutes

---

### Tuesday-Thursday: The Practice Slog?

**What happens:**
- Allocate practice time (development vs. execution vs. scheme)
- Manage depth chart
- Monitor health/morale
- Background scouting

**User experience:**
This is where the design is **most at risk of being tedious**.

**The problem:**
Three days of "allocate practice time" is potentially three identical screens. If Tuesday feels the same as Wednesday feels the same as Thursday, users will start clicking through without engaging.

**What makes it worse:**
- If nothing changes day-to-day, why have three days?
- If practice decisions don't feel impactful, why make them?
- If I'm just waiting for Sunday, this is an obstacle

**What makes it work:**
- Events break up the monotony ("Your WR1 and WR2 got in a fight at practice")
- Visible progress ("Your rookie's route running improved!")
- Different focus each day (Tuesday = conditioning, Wednesday = install, Thursday = walkthrough)
- Ability to skip/sim if you're not in the mood

**Recommendation:**
1. **Collapse Tue-Thu into a single "Practice Week" allocation** unless an event demands attention
2. Make practice results visible and impactful
3. Events should be the interesting part, not the allocation sliders

**Time estimate:** 5-10 minutes (if interesting) or 30 seconds (if simming)

---

### Friday: The Commitment

**What happens:**
- Finalize game plan
- Set personnel packages
- Final roster decisions (elevate from PS, healthy scratches)

**User experience:**
This should feel like **locking in your bet**. You've prepared all week, now you commit.

**Potential issues:**
- If game plan decisions don't matter, this is ceremony
- If there are too many decisions, it's overwhelming
- If it's identical every week, it's rote

**What makes it work:**
- Game plan choices that feel meaningful ("Do we try to run against their weak DL or exploit their secondary?")
- Visible opponent scouting that informed your choices
- The feeling that Sunday's outcome depends on what you choose here

**Recommendation:**
1. Frame Friday as "Here's what we know about them. Here's our plan."
2. Limit to 2-3 meaningful choices (offensive approach, defensive approach, key matchup to exploit)
3. Show your coordinators' recommendations but let you override

**Time estimate:** 5-8 minutes

---

### Game Day: The Payoff

**What happens:**
- Pre-game setup
- In-game coaching
- Post-game reactions

**User experience:**
This is **why you played all week**. This needs to feel like the climax.

**Potential issues:**
- If games are too long, they become a slog
- If games are too short, prep feels wasted
- If your decisions don't matter, why not just sim?
- If you sim, does the week feel pointless?

**What makes it work:**
- Visible connection between your prep and the game (your game plan working)
- Moments of decision (4th down calls, timeout management, halftime adjustments)
- Narrative beats ("Your rookie WR is stepping up!")
- Outcomes that feel like consequences of your choices, not dice rolls

**The big question:** How long should a game be?

| Length | Pros | Cons |
|--------|------|------|
| 10 min | Quick, can play multiple seasons | Doesn't feel like football |
| 30 min | Meaty, decisions matter | One session = one game |
| 60 min | Full experience, immersive | Exhausting, limits sessions |

**Recommendation:** Target **20-30 minutes** for a played game. Offer sim with highlights (5 min) for when users want to move faster.

**Time estimate:** 20-30 minutes (played) or 3-5 minutes (simmed with highlights)

---

## The Weekly Loop: Total Time

If everything works:

| Phase | Played | Simmed |
|-------|--------|--------|
| Monday | 3-5 min | 1 min |
| Tue-Thu | 5-10 min | 30 sec |
| Friday | 5-8 min | 2 min |
| Game Day | 20-30 min | 3-5 min |
| **Total** | **35-55 min** | **7-10 min** |

This feels right. A "full week" is about an hour. A "quick week" is under 10 minutes.

**But here's the problem:** 17 regular season weeks × 55 minutes = **15+ hours just for regular season**. Plus playoffs, plus offseason.

A full season might be **20-25 hours**. Is that okay?

For comparison:
- Football Manager: 30-50 hours per season
- Madden Franchise: 10-15 hours per season (heavily simmed)
- HC09: ~20 hours per season

**20-25 hours per season feels appropriate** for this depth of management game. But users need to be able to sim weeks when they want to.

---

## The Offseason Loop: Phase by Phase

### End of Season (30 min)

**What happens:** Review, awards, owner evaluation

**User experience:**
This should feel like an **epilogue**. You just finished a season - let me see how I did.

**Potential issues:**
- If I missed the playoffs, I don't want a long post-mortem
- If I won the Super Bowl, I want to celebrate, not immediately make decisions

**Recommendation:**
- Scale the review length to the outcome
- Super Bowl win: extended celebration, trophy, legacy moment
- Missed playoffs: quick "here's what went wrong" then move on

---

### Early Offseason: Staff & Cuts (45-60 min)

**What happens:**
- Hire/fire coordinators
- Cut players, restructure contracts
- Set philosophy

**User experience:**
This is **painful decisions**. You're cutting guys you like. You're firing coaches who underperformed.

**Potential issues:**
- Cap math can be overwhelming
- Too many cut decisions at once
- Staff hiring if you don't have good options

**Recommendation:**
1. Surface the "obvious" cuts first (overpaid, underperforming)
2. Show cap implications clearly but simply
3. Staff hiring should feel like a market, not a menu
4. Philosophy setting should be meaningful, not just picking from a list

---

### Free Agency (60-90 min)

**What happens:** Event-driven bidding for players

**User experience:**
This should feel like an **auction** - exciting, competitive, scarce.

**Potential issues:**
- If it's too slow, it drags
- If it's too fast, you miss players
- If you don't understand the market, you overbid or miss out
- Decision fatigue from too many players

**The core tension:**
The design wants free agency to be event-driven with attention scarcity. But users expect to browse available players like a catalog.

**Recommendation:**
1. Allow browsing BUT pursuing someone removes them from passive view
2. "Top free agents" visible to everyone, deep cuts require scouting
3. Negotiation phase should be interactive, not just "offer → accept/reject"
4. Clear feedback on market value ("Teams are offering 3yr/$30M range")

**Time pacing:**
- Day 1: Big names, high stakes (30 min)
- Days 2-5: Middle market, deal hunting (30-45 min)
- Final days: Bargain bin, filling gaps (15-20 min)

---

### The Draft (60-90 min)

**What happens:** War room, picks, reactions

**User experience:**
This should be **theater**. The most exciting day of the offseason.

**Potential issues:**
- If you have late picks, lots of waiting
- If you didn't scout well, you're guessing
- If there's no drama, it's just clicking

**What makes it work:**
- Trades that you initiate or receive
- Players falling or rising
- Other teams taking "your guy"
- The payoff of scouting - you KNOW this guy is good

**Recommendation:**
1. Fast-forward option for picks that aren't yours
2. Trade offers that pop up during the draft
3. Show mock draft comparisons as it unfolds
4. Post-pick grades/reactions for immediate feedback

---

### Pre-Season (45-60 min)

**What happens:** Training camp, roster battles, final cuts

**User experience:**
This is **the proving ground**. Your draft picks and free agents have to earn roster spots.

**Potential issues:**
- Preseason games might feel like filler
- Final cuts can be agonizing (too many decisions)
- If nothing changes from what you expected, it's boring

**What makes it work:**
- Surprises: The 7th rounder who's outplaying the veteran
- Roster battles with actual drama
- Preseason games that reveal information (this guy can/can't play)

**Recommendation:**
1. Focus on the BATTLES, not the whole roster
2. "Who won the starting job?" as the key question each week
3. Preseason games as information-gathering, not wins/losses
4. Final cuts should be surfaced as a single agonizing decision day

---

## Offseason Total Time

| Phase | Time |
|-------|------|
| End of Season | 30 min |
| Early Offseason | 45-60 min |
| Free Agency | 60-90 min |
| Draft | 60-90 min |
| Pre-Season | 45-60 min |
| **Total** | **4-5.5 hours** |

This is a lot. A full offseason is basically a standalone session (or two).

**That might be okay** - the offseason IS the franchise-building phase. But users need:
1. Save points between phases
2. Ability to sim phases they're not interested in
3. Clear indication of how long each phase takes

---

## The Repetition Problem

By Season 3, users have done the weekly loop 50+ times. What gets tedious?

**High tedium risk:**
- Practice allocation (if it's the same every week)
- Monday review (if it's the same format)
- Pre-game setup (if it's the same decisions)

**Lower tedium risk:**
- Games (if outcomes vary)
- Draft (if prospects are unique)
- Free agency (if the market is different)
- Events (if they're varied and rare enough)

**The solution:** Variation and stakes.
- Weeks should feel different based on opponent, injuries, standings
- Late-season games should feel more important than early-season
- Playoff games should feel VERY different
- Events should be rare enough to be interesting

---

## Natural Stopping Points

Where can users save and quit?

**Strong stopping points:**
- After a game (natural conclusion)
- After the draft (major milestone)
- End of a season (obvious break)

**Weak stopping points:**
- Mid-week (feels incomplete)
- During free agency (market is moving)
- During the draft (incomplete)

**Recommendation:** Design save/quit prompts around strong stopping points. If a user quits mid-week, resume with a "catch-up" summary.

---

## What's Missing from the Gameflow

Things I don't see addressed:

### 1. The "Bad Season" Experience

What happens when you're 2-10 in Week 14? The weekly loop might feel pointless.

**Recommendation:** Surface different goals. "Evaluate the young guys." "Tank for draft position?" "Owner meeting about your job security."

### 2. The "Dynasty" Problem

By Year 5 with a stacked roster, is there still challenge?

**Recommendation:** Cap pressure, aging stars, coordinators leaving for head coaching jobs, expectation management.

### 3. Between-Game Mid-Week Events

The design mentions events, but the weekly loop doesn't emphasize them.

**Recommendation:** Events should be the primary content of Tue-Thu, not practice allocation.

### 4. Quick Sim Mode

Some users want to play once a week, make big decisions, and sim the rest.

**Recommendation:** "Executive Mode" - only surface critical decisions, sim everything else with highlights.

---

## Summary: Does the Gameflow Work?

**What works:**
- Weekly loop rhythm (Monday recovery → mid-week prep → Friday commit → Sunday payoff)
- Offseason structure (review → rebuild → acquire → draft → camp)
- Time estimates feel reasonable (1 hour/week, 4-5 hours offseason)

**What's risky:**
- Tue-Thu practice allocation could be tedious
- Free agency attention scarcity might frustrate more than excite
- Repetition over multiple seasons
- "Bad season" and "dynasty" edge cases

**What's missing:**
- Clear event-driven mid-week content
- Quick sim mode for different playstyles
- Variation mechanisms to prevent repetition

**Overall:** The bones are good. The risk is in the middle - the Tue-Thu slog and the repetition problem. Events and variation are the cure.

---

**- Researcher Agent**
