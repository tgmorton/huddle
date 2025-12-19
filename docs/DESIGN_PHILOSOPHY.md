# Huddle: Design Philosophy & Principles

> A football management game isn't about optimizing spreadsheets. It's about making decisions with incomplete information, living with consequences that compound, and feeling the weight of being the person who has to choose.

This document captures the core design philosophy for Huddle, derived from deep analysis of what made NFL Head Coach 09 compelling and how we can honor that legacy while building something new.

---

## Core Identity

Huddle is a **football management simulation** where you experience the life of an NFL head coach. You don't just manage a roster—you inherit a franchise, define its identity, navigate competing stakeholders, and live with decisions that echo across seasons.

The game should feel like **grasping at the few things you can control, like trying to blow on the sails of a ship to move it.** You can't control everything. You can't please everyone. But the decisions you *can* make should feel weighty, consequential, and yours.

---

## The Seven Design Pillars

### 1. Identity and Philosophy

**You define who your team is. That choice filters everything.**

Before you make roster moves, before free agency, before the draft—you declare your team's identity. Run-heavy or pass-first? Aggressive defense or bend-don't-break? Development-focused or win-now?

This isn't just a settings menu. Your philosophy:
- **Reframes how you evaluate players.** A power running back looks different to a spread offense than a ground-and-pound team. Overalls should shift based on scheme fit.
- **Creates your "needs."** Your identity tells you what's missing, not just what positions are weak.
- **May conflict with your coordinators.** If you give up philosophy control in a hiring negotiation, you now see your roster through *their* eyes, not yours.

**Design implications:**
- Early-season "identity phase" where you commit to team philosophy
- Player ratings that shift based on scheme fit (not just raw talent)
- Tension between your vision and your staff's vision
- Consequences for changing philosophy mid-stream (playbook learning resets, player fit changes)

---

### 2. Scarcity of Attention

**Everything is scarce. Every choice is a tradeoff.**

Time. Reps. Roster spots. Scouting resources. Cap space. Your own attention as a player. The game is fundamentally about **allocation under constraint**.

This manifests everywhere:
- **Practice:** Do you focus on developing the rookie or perfecting execution for Sunday? Learning new plays or mastering existing ones?
- **Scouting:** Do you cast a wide net across small schools for hidden gems, or focus on known commodities from big programs?
- **Free agency:** You can only pursue so many players. Committing to one negotiation means not pursuing another.
- **Roster spots:** Keeping a high-potential project means cutting someone else. What if you're wrong?

**Design implications:**
- Practice as resource allocation (reps are finite, time is finite)
- Scouting as a funnel (breadth vs. depth, general coverage vs. targeted workouts)
- Free agency as an event stream with limited attention, not a catalog to browse
- Every "yes" should implicitly be a "no" to something else

---

### 3. Competing Stakeholders

**Everyone wants something. You can't please everyone.**

You are not an optimizer in a vacuum. You're a coach surrounded by people with opinions, demands, and feelings:

- **Players** want playing time, money, respect, and roles that fit their abilities
- **Coordinators** have their own philosophies and may disagree with your decisions
- **The owner** has goals that may conflict with good football (win a rivalry game, make the playoffs, sign a splash free agent)
- **Fans** react to your decisions in real-time
- **The media** has narratives about your tenure

Every decision makes someone happy and someone unhappy. Give the rookie reps? The veteran is upset. Sign the expensive free agent? The owner is thrilled but the cap is strained. Fire the underperforming coordinator? Maybe he was popular in the locker room.

**Design implications:**
- Visible stakeholder reactions to decisions
- Owner goals that sometimes conflict with optimal team-building
- Player morale and chemistry systems that respond to decisions
- The feeling that you're navigating relationships, not just managing numbers

---

### 4. Information as Currency

**You never have complete information. Form opinions anyway.**

Uncertainty is not a bug—it's the game. You're not reading spreadsheets; you're forming judgments with incomplete data and betting on your own evaluation.

**Scouting should deliver impressions, not stats:**
- "Big arm" means something different than "Throw Power: 94"
- Scouts can be wrong. Their assessments are interpretations, not facts.
- The player's job is to develop opinions and then live with being right or wrong

**Other teams are opaque:**
- What do they want in a trade? You're guessing.
- Who are they targeting in the draft? You're reading signals.
- Who else is bidding on this free agent? You're competing blind.

**Player potential is uncertain:**
- You might cut someone who becomes a star elsewhere
- You might invest in a "high ceiling" player who never develops
- The game should remember and show you the outcomes of your bets

**Design implications:**
- Scouting reports use qualitative descriptors, not precise ratings (at least initially)
- Scout accuracy varies; disagreement between scouts is signal, not noise
- Draft prospects have "fog" that lifts based on scouting investment
- A robust system for tracking what happened to players you cut, passed on, or traded

---

### 5. Consequences That Compound

**Decisions echo across seasons. The game has memory.**

This is not a single-season experience. The joy of a late-round pick becoming a star only lands if you remember drafting him. The pain of a bad contract only matters if you can't escape it for years.

**Bad decisions should haunt you:**
- The running back you overpaid who's now injured and untradeable, eating cap while young players ride the bench
- The coordinator you gave too much control who won't start your promising rookie
- The draft pick you reached for who busted while the guy you passed on became All-Pro

**Good decisions should compound:**
- The late-round gem you believed in when nobody else did
- The depth piece you kept specifically for a role, who shows up in exactly that situation
- The contract structured to give you flexibility that pays off two years later

**Design implications:**
- Multi-season career mode as the default experience
- Clear feedback when past decisions play out (notifications when cut players succeed/fail elsewhere)
- Cap consequences that span years (dead money, restructures, backloaded deals)
- Story continuity—the game should surface "remember when you drafted him in the 6th round?"

---

### 6. Narrative Everywhere

**Players are people with stories, not stat bundles.**

The game should constantly generate small narratives that make your franchise feel alive:

**Draft day:**
- Picks come with media reactions ("Schefter thinks this is a reach")
- Fan polls show approval ratings
- Backstories about the player's college career, personality, journey

**During the season:**
- Stories emerge about prospects during the college season ("This QB just threw 5 TDs against a ranked opponent")
- Injury crises create "next man up" narratives
- Rivalries matter—beating your rival means more than beating a random team

**Across seasons:**
- Players you developed become veterans who mentor rookies
- Former players become coaches, scouts, or media personalities
- Your coaching tree grows as assistants get hired elsewhere

**Design implications:**
- Generated news stories and media coverage
- Player personalities that affect how they respond to situations
- Reactive commentary on your decisions (not just stats, but narrative framing)
- Long-term story tracking (draft pick arcs, career progressions, rivalry histories)

---

### 7. Earned Participation

**Your investment demands you see it through.**

You could simulate games. But you won't want to—because the time you invested in the week creates emotional stakes that demand resolution.

**Why simming feels wrong:**
- A simulated loss feels like the game screwed you
- A played loss feels like *you* failed
- The practice decisions, roster tweaks, and game planning you did all week deserve to be tested

**The week should build toward the game:**
- Monday: Recover from last game, check injuries, early scouting
- Tuesday-Thursday: Practice decisions, development focus, scheme installation
- Friday: Final roster decisions, game plan finalization
- Sunday: The test

**In-game coaching should feel different from Madden:**
- Slower pacing, more deliberate
- You're calling plays but also managing timeouts, challenges, personnel packages
- Halftime adjustments matter
- Pulling a struggling starter is a decision with consequences beyond this game

**Design implications:**
- Clear weekly rhythm with distinct phases
- Practice and preparation that visibly affects game performance
- In-game coaching mode that feels like coaching, not playing
- Simulation as an option but not the expected path

---

## The Core Loops

### Weekly Loop (During Season)

```
Monday
├── Review previous game (stats, injuries, player performance)
├── Check owner/fan reactions
└── Early look at next opponent

Tuesday-Thursday
├── Allocate practice time (development vs. execution vs. scheme learning)
├── Manage depth chart
├── Monitor player health and morale
└── Scout upcoming draft class (during season, background activity)

Friday
├── Finalize game plan
├── Set personnel packages
└── Make final roster decisions (elevate from practice squad, healthy scratches)

Game Day
├── Pre-game (starting lineup, captain selection, coin toss)
├── In-game (play calling, timeouts, challenges, halftime adjustments)
└── Post-game (reactions, press conference, injury updates)
```

### Offseason Loop

```
End of Season
├── Season review (stats, achievements, failures)
├── Award ceremonies (Pro Bowl, All-Pro, MVP, Coach of the Year)
├── Owner evaluation and contract status
└── Staff evaluation

Early Offseason
├── Coaching staff decisions (fire/hire coordinators, position coaches)
├── Contract decisions (cut candidates, restructure candidates)
├── Set team philosophy for upcoming year
└── Scouting combine preparation

Free Agency
├── Event-driven player availability (players pop up, you decide to pursue or pass)
├── Competitive bidding against other teams
├── Limited negotiation windows (can't pursue everyone)
└── Contract negotiations with personality dynamics

Draft
├── Final prospect evaluations
├── War room draft day (trade up/down, read other teams, make picks)
├── Post-pick media and fan reactions
├── Rookie contract negotiations

Pre-Season
├── Training camp (roster battles, depth chart formation)
├── Preseason games (evaluate bubble players)
├── Final cuts
└── Set opening week depth chart
```

---

## Key Systems

### Playbook Learning

Every player has a learning level for every play in the playbook:
- **Unknown** → **Familiar** → **Learned** → **Mastered**

**Effects of low learning:**
- Wrong routes, missed assignments, bad blocking
- QB-WR timing off
- Penalties from confusion

**Implications:**
- Installing a new playbook is a *cost*—your team starts near zero
- Practice time must be allocated to scheme learning
- There's a tangible "click" when your starters master the system
- Veteran free agents may already know common schemes; rookies are blank slates

### Staff Hiring and Control Tradeoffs

Hiring a coordinator isn't just finding the best ratings. It's a negotiation:

**What you might give up:**
- Position philosophy control (their preferences change how you see player ratings)
- Depth chart control (they choose starters; you might disagree)
- Play calling in-game (they call plays; you can override but it costs relationship)

**Why you'd give things up:**
- Better coordinators demand more control
- A great DC who controls the depth chart might be worth more than a mediocre DC you fully control

**Living with delegation:**
- When you give up QB philosophy, you see your QBs through their lens
- When they control the depth chart, your promising rookie might ride the bench
- Firing them to regain control has its own costs (staff morale, learning reset)

### Scouting Funnel

Scouting resources are limited. You allocate across a funnel:

**Regular Season (background scouting):**
- Choose coverage focus: big schools (more known commodities) vs. small schools (hidden gems)
- Broader coverage means shallower knowledge
- Stories emerge about prospects ("This RB just broke the single-game rushing record")

**Combine:**
- Measurables revealed
- Request private workouts (targeted investment in specific players)
- Limited workout slots—choose wisely

**Pre-Draft:**
- Invite prospects to interviews (very limited slots)
- Interviews reveal personality, learning ability, intangibles
- This is how you find late-round steals—confirm your hunches

**Draft Day:**
- Your preparation determines your confidence
- Well-scouted players: you know what you're getting
- Poorly-scouted players: you're guessing

### Free Agency as Auction

Free agency is not a shopping catalog. It's a competitive event stream:

**Event-driven availability:**
- Players "become available" as events during the FA period
- You decide: pursue or pass?
- Pursuing commits your attention (limited bandwidth)

**Competitive bidding:**
- Other teams bid on the same players
- Each bid raises the floor for negotiation
- You can get "trapped" in a bidding war, winning the right to negotiate a bad contract

**Limited time:**
- You can't pursue everyone
- While you're negotiating with one player, others are signing elsewhere
- FOMO is a feature, not a bug

**Personality in negotiation:**
- Player personalities affect what they want (money vs. role vs. location vs. winning)
- Your coach personality creates compatibility or friction
- A good match can mean a discount; a bad match means overpaying or losing them

### Contracts and Cap Consequences

The salary cap should create *drama*, not just math:

**Bad contracts should hurt:**
- Dead money when you cut someone
- Can't escape a bad deal for years
- A player eating cap while young players are ready to start

**Good contracts should feel smart:**
- Backloaded deals that give you flexibility
- Restructures that create short-term space with long-term cost
- Team-friendly deals with players who wanted to be there

**Cap management as ongoing tension:**
- Can't just sign everyone you want
- Sometimes you have to let a good player walk
- Rebuilding means eating bad contracts to reset

---

## The Emotional Architecture

The game should regularly create these feelings:

**Anxiety:** "What if someone better comes along?" "What if I'm wrong about this prospect?"

**Tension:** "I can only pursue three free agents and I want five." "My coordinator won't start my guy."

**Vindication:** "I believed in him when no one else did, and he just made the Pro Bowl."

**Regret:** "I cut that guy and now he's starting for our rival."

**Pride:** "I built this. That offensive line I assembled over three years just dominated."

**Pressure:** "The owner wants playoffs. I'm not sure this roster can do it. But I have to try."

**Emergence:** "My young QB and WR finally clicked. You can see it on the field."

**Haunting:** "That contract I signed three years ago is still killing us."

---

## What We're Not Building

To stay focused, some explicit non-goals:

- **Not a Madden competitor.** The on-field gameplay serves the management fantasy, not the other way around.
- **Not a stat optimization puzzle.** If you can "solve" the game by min-maxing, we've failed.
- **Not a fast experience.** Rushing through should feel wrong. The pacing is part of the feel.
- **Not a game where you control everything.** Delegation, uncertainty, and competing stakeholders are features.
- **Not a game where the "right answer" is obvious.** Reasonable people should disagree about decisions.

---

## Technical Implications

These design principles suggest several technical requirements:

### State Persistence
- Multi-season career state with full history
- Player career tracking (even after they leave your team)
- Decision history for callback narratives

### Event System
- Rich event bus for stakeholder reactions
- Event-driven free agency and news generation
- Narrative events that reference past decisions

### Simulation Depth
- Playbook learning per-player, per-play
- Staff philosophy affecting player evaluation
- Chemistry and morale systems

### UI/UX
- Player notes and clipboard system (track your own interests)
- Clear weekly/seasonal rhythm in navigation
- Stakeholder reaction visibility
- Historical decision review

### AI Systems
- Other teams as actors with agendas (not just difficulty modifiers)
- Personality-driven negotiation
- Coordinator AI that makes decisions you might disagree with

---

## The North Star

When making design decisions, ask:

> "Does this create a moment where the player has to make a hard choice, live with the consequences, and feel something about the outcome?"

If yes, we're on the right track. If no, reconsider whether it's necessary.

---

## Appendix: Inspiration from NFL Head Coach 09

HC09 got many things right that modern sports games have abandoned:

- **The coaching staff mattered.** Your coordinators had real impact, real personalities, and real demands.
- **Scouting was fog, not data.** You formed opinions with incomplete information.
- **Free agency was competitive.** Other teams were actors, not just obstacles.
- **The draft was theater.** Picks came with reactions, stories, and stakes.
- **Decisions haunted you.** Bad contracts, bad cuts, bad picks—you lived with them.
- **You couldn't please everyone.** The owner, the players, the fans—someone was always unhappy.
- **The game was slow.** And that slowness created weight.

We're not making HC09 again. But we're honoring what it understood about the fantasy of being a coach: **you're responsible, you're accountable, and your decisions matter.**
