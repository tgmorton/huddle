# League Generation Analysis: Creating Coherent Team Histories

## The Problem

When generating a new league, we want teams to feel "lived in" - not just random collections of players, but rosters that reflect:

- **Draft history**: Rookies on rookie deals, 2nd-year players, etc.
- **Contract distribution**: Mix of rookie contracts, extensions, veteran signings
- **Age curves**: Teams have players at different career stages
- **Cap situations**: Some teams in cap hell, others with space
- **Asset balance**: If Team A has extra picks, Team B gave them up
- **Team status coherence**: A "dynasty" team should have the roster of a dynasty

Currently, we generate players and assign them to teams, but this creates unrealistic states:
- No contract history
- No transaction trail
- No draft pick ownership variations
- No dead money from past moves

---

## Approaches

### Approach A: Full Historical Simulation

**Concept**: Start the simulation 4-5 years in the past and run it forward.

```
Year -4: Generate rookie class, run draft, simulate season
Year -3: Free agency, draft, simulate season
Year -2: Free agency, draft, simulate season
Year -1: Free agency, draft, simulate season
Year 0:  Present day - league is ready for player
```

**Pros**:
- Most realistic - every player/pick/contract has real history
- Team statuses emerge naturally from performance
- Trade/pick balance is automatic
- Dead money accumulates realistically

**Cons**:
- Requires ALL systems to work autonomously:
  - AI draft decisions
  - AI free agency decisions
  - AI trade decisions
  - AI roster management (cuts, IR, etc.)
  - Full game simulation for standings
- Takes significant compute time
- Harder to control outcomes (might not get interesting league variety)

**Required Systems**:
1. Autonomous draft AI
2. Autonomous free agency AI
3. Autonomous trade AI
4. Autonomous roster management AI
5. Game simulation (at least results, not play-by-play)
6. Contract negotiation AI
7. Injury/retirement system

### Approach B: Synthetic History Generation

**Concept**: Generate the end state directly, but with constraints that ensure coherence.

```python
def generate_league():
    # 1. Assign team statuses first
    team_statuses = distribute_statuses()  # 2 dynasties, 6 contenders, etc.

    # 2. Generate players with age distribution
    for team in teams:
        roster = generate_roster_for_status(team.status)
        # Status determines age distribution, talent level, etc.

    # 3. Assign contracts based on player age/overall
    for player in all_players:
        player.contract = infer_contract(player.age, player.overall, player.team.status)

    # 4. Create synthetic transaction history
    balance_draft_picks()  # Ensure picks sum to zero
    create_trade_history()  # Generate believable trade chains

    # 5. Calculate dead money from inferred transactions
    calculate_dead_money()
```

**Pros**:
- Fast - no simulation required
- More control over league composition
- Can guarantee interesting variety (at least one dynasty, one rebuild, etc.)
- Fewer required systems

**Cons**:
- Less realistic - players have no actual game history
- Hard to get all the details right (why does this team have 3 first-round picks?)
- "Seams" might show if examined closely
- Doesn't stress-test the actual AI systems

**Required Systems**:
1. Roster composition templates per status
2. Contract inference from player attributes
3. Draft pick balancing algorithm
4. Transaction history generator
5. Dead money calculator

### Approach C: Hybrid - Generate Then Simulate

**Concept**: Generate reasonable starting rosters, then simulate 1-2 seasons to create natural churn.

```python
def generate_league():
    # 1. Generate rosters with basic constraints
    rosters = generate_initial_rosters()

    # 2. Simulate 1-2 seasons (lighter weight than full sim)
    for season in range(2):
        simulate_season_results()  # Win/loss only
        run_offseason_ai()         # Cuts, FA, draft

    # 3. Now we have some real history
    return league
```

**Pros**:
- Gets some realism without 4+ year simulation
- Natural roster churn (bad players get cut)
- Tests AI systems with real usage
- Creates actual transaction history

**Cons**:
- Still requires autonomous AI systems
- 1-2 years might not be enough for full realism
- Still need game simulation of some kind

---

## Required Systems Analysis

Working backwards from what we need, here are the systems required for autonomous league operation:

### Tier 1: Essential for Any Approach

| System | Current State | Gap |
|--------|--------------|-----|
| Player Generation | ✅ Complete | None |
| Contract Structure | ✅ Basic exists | Need term/year tracking |
| Salary Cap | ✅ TeamFinancials exists | Need per-player cap hits |
| Team Status | ✅ Just implemented | Need integration with AI |

### Tier 2: Required for Approach B (Synthetic)

| System | Current State | Gap |
|--------|--------------|-----|
| Roster Templates | ❌ Missing | Need composition rules per status |
| Contract Inference | ❌ Missing | Derive contract from age/overall |
| Pick Balancing | ❌ Missing | Ensure picks are zero-sum |
| Transaction Generator | ❌ Missing | Create believable trade chains |

### Tier 3: Required for Approach A/C (Simulation)

| System | Current State | Gap |
|--------|--------------|-----|
| Draft AI | ❌ Missing | Pick selection logic |
| Free Agency AI | ❌ Missing | Signing decisions |
| Trade AI | ❌ Missing | Propose/evaluate trades |
| Roster Management AI | ❌ Missing | Cuts, practice squad, IR |
| Game Simulation | 🟡 V2 Sim exists | Need season-level abstraction |
| Contract Negotiation | ❌ Missing | Extension/FA offers |

---

## Detailed System Requirements

### 1. Contract System (Enhanced)

Current: Basic contract exists
Needed: Full NFL-style contracts

```python
@dataclass
class Contract:
    player_id: str
    team_id: str

    # Term
    total_years: int
    current_year: int  # 1-indexed

    # Money
    total_value: int           # Total contract value
    guaranteed: int            # Total guaranteed money
    signing_bonus: int         # Prorated over contract
    base_salaries: list[int]   # Per-year base
    roster_bonuses: list[int]  # Per-year roster bonus

    # Options
    team_option_year: Optional[int]  # 5th year option
    player_option_year: Optional[int]
    void_years: int                   # For cap manipulation

    # Status
    contract_type: ContractType  # ROOKIE, VETERAN, EXTENSION, FRANCHISE_TAG

    def cap_hit(self, year: int) -> int:
        """Calculate cap hit for a given year."""
        prorated_bonus = self.signing_bonus // self.total_years
        return self.base_salaries[year-1] + prorated_bonus + self.roster_bonuses[year-1]

    def dead_money_if_cut(self, year: int) -> int:
        """Remaining prorated bonus if cut at year."""
        remaining_years = self.total_years - year + 1
        return (self.signing_bonus // self.total_years) * remaining_years
```

### 2. Draft Pick Tracking

```python
@dataclass
class DraftPick:
    original_team_id: str  # Who originally owned it
    current_team_id: str   # Who owns it now
    year: int              # Draft year
    round: int             # 1-7

    # Conditions (for conditional picks)
    conditions: Optional[str]  # "Top 10 protected"

    # After draft
    player_id: Optional[str]   # Who was selected
    pick_number: Optional[int] # Actual pick number

@dataclass
class DraftPickInventory:
    """Track all pick ownership for a team."""
    team_id: str

    # Own picks (may have been traded away)
    own_picks: dict[tuple[int, int], bool]  # (year, round) -> still owned

    # Acquired picks
    acquired_picks: list[DraftPick]

    def get_picks_for_year(self, year: int) -> list[DraftPick]:
        """Get all picks team has for a year."""
        ...
```

### 3. Transaction Log

```python
class TransactionType(Enum):
    DRAFT = auto()
    TRADE = auto()
    FREE_AGENT_SIGNING = auto()
    EXTENSION = auto()
    CUT = auto()
    WAIVER_CLAIM = auto()
    PRACTICE_SQUAD = auto()
    IR_PLACEMENT = auto()
    IR_RETURN = auto()
    RETIREMENT = auto()

@dataclass
class Transaction:
    transaction_id: str
    transaction_type: TransactionType
    date: datetime
    season: int
    week: int

    # Parties
    team_id: str
    player_id: Optional[str]
    other_team_id: Optional[str]  # For trades

    # Details
    contract: Optional[Contract]
    picks_sent: list[DraftPick]
    picks_received: list[DraftPick]
    players_sent: list[str]
    players_received: list[str]

    # Cap implications
    cap_hit: int
    dead_money: int

    notes: str
```

### 4. Draft AI

```python
class DraftAI:
    def select_player(
        self,
        team: Team,
        available_players: list[Player],
        current_pick: int,
        team_needs: dict[str, float],
    ) -> Player:
        """
        Select a player based on team philosophy and needs.

        Factors:
        - Team status (rebuilding = swing for upside)
        - Team needs by position
        - Best player available vs need
        - Trade down opportunities
        """

    def evaluate_trade_up(
        self,
        team: Team,
        target_pick: int,
        target_player: Player,
    ) -> Optional[TradeOffer]:
        """Should we trade up for this player?"""

    def evaluate_trade_down(
        self,
        team: Team,
        current_pick: int,
        offers: list[TradeOffer],
    ) -> Optional[TradeOffer]:
        """Should we accept a trade down?"""
```

### 5. Free Agency AI

```python
class FreeAgencyAI:
    def rank_free_agents(
        self,
        team: Team,
        available_fas: list[Player],
    ) -> list[tuple[Player, int]]:
        """Rank FAs by priority and max offer."""

    def make_offer(
        self,
        team: Team,
        player: Player,
        competing_offers: list[Contract],
    ) -> Optional[Contract]:
        """Generate contract offer for a free agent."""

    def evaluate_offer(
        self,
        team: Team,
        player: Player,
        offer: Contract,
    ) -> bool:
        """Should team match this offer for own player?"""
```

### 6. Trade AI

```python
class TradeAI:
    def identify_trade_candidates(
        self,
        team: Team,
    ) -> list[Player]:
        """Which players should we shop?"""

    def evaluate_trade(
        self,
        team: Team,
        sending: list[Player | DraftPick],
        receiving: list[Player | DraftPick],
    ) -> float:
        """Rate trade value (-1 to 1, 0 = fair)."""

    def generate_trade_proposals(
        self,
        team: Team,
        target_player: Player,
    ) -> list[TradeProposal]:
        """Generate offers for a target player."""
```

### 7. Roster Management AI

```python
class RosterAI:
    def make_cuts(
        self,
        team: Team,
        roster_limit: int,
    ) -> list[Player]:
        """Decide who to cut to get under roster limit."""

    def manage_practice_squad(
        self,
        team: Team,
        waiver_wire: list[Player],
    ) -> list[Player]:
        """Who to sign to practice squad?"""

    def ir_decisions(
        self,
        team: Team,
        injured_players: list[tuple[Player, Injury]],
    ) -> list[tuple[Player, str]]:
        """(player, action) - 'ir', 'keep', 'cut'"""
```

---

## Recommended Approach

Given the current state of the codebase, I recommend **Approach B (Synthetic History)** as the starting point, with a path to **Approach C (Hybrid)** as AI systems mature.

### Phase 1: Synthetic History (Now)

1. **Implement roster composition templates** based on TeamStatus
2. **Add contract inference** - derive reasonable contracts from player attributes
3. **Balance draft picks** across the league (zero-sum)
4. **Generate plausible transaction summaries** (not full log, just key moves)
5. **Calculate dead money** from inferred cuts/trades

This gives us playable leagues quickly without full AI.

### Phase 2: AI Foundation (Next)

1. Build Draft AI (most constrained decision space)
2. Build basic Roster Management AI (cuts for roster limits)
3. Build simple Trade AI (accept/reject only, not propose)

### Phase 3: Full Autonomy (Later)

1. Free Agency AI with market dynamics
2. Trade proposal generation
3. Multi-year strategic planning
4. Full historical simulation capability

---

## Roster Composition Templates

For Approach B, here are realistic roster compositions by team status:

### Dynasty Team
- **Age Distribution**: Slightly older (27-30 core)
- **Contract Mix**: Heavy on extensions, 2-3 big contracts
- **Draft Capital**: Often missing picks (traded for veterans)
- **Dead Money**: Low-moderate (managed well)
- **Rookie Starters**: 1-2 (drafting depth, not starters)
- **Key Players**: Elite QB, 2-3 All-Pro level players

### Contending Team
- **Age Distribution**: Prime years (25-29 core)
- **Contract Mix**: 2-3 big deals, some value contracts
- **Draft Capital**: Normal to slightly less
- **Dead Money**: Low
- **Rookie Starters**: 2-3
- **Key Players**: Good QB, 1-2 stars, solid depth

### Window Closing
- **Age Distribution**: Older (28-32 core)
- **Contract Mix**: Several aging big contracts
- **Draft Capital**: Often traded away future picks
- **Dead Money**: Moderate (past moves catching up)
- **Rookie Starters**: 1-2 (haven't developed young talent)
- **Key Players**: Declining star(s), mediocre QB or aging QB

### Rebuilding
- **Age Distribution**: Young (23-26 core)
- **Contract Mix**: Mostly rookie deals, few veterans
- **Draft Capital**: Extra picks from trades
- **Dead Money**: High initially (dumped contracts), declining
- **Rookie Starters**: 5-7
- **Key Players**: 1-2 young building blocks, no QB or young QB

### Emerging
- **Age Distribution**: Young (24-27 core)
- **Contract Mix**: Rookie deals, starting to extend young stars
- **Draft Capital**: Normal
- **Dead Money**: Low
- **Rookie Starters**: 4-5
- **Key Players**: Promising young QB, 2-3 ascending players

### Stuck in Middle
- **Age Distribution**: Mixed (26-29)
- **Contract Mix**: Some bad contracts, some value
- **Draft Capital**: Normal
- **Dead Money**: Moderate
- **Rookie Starters**: 2-3
- **Key Players**: One decent player, inconsistent QB

### Mismanaged
- **Age Distribution**: Awkward (aging vets + raw rookies, no middle)
- **Contract Mix**: Several bad contracts
- **Draft Capital**: Often traded away picks
- **Dead Money**: Very high
- **Rookie Starters**: 3-5 (forced by cuts/departures)
- **Key Players**: Possibly none, or one overpaid player

---

## Draft Pick Balance Algorithm

For synthetic history, picks traded away must equal picks acquired league-wide.

```python
def balance_draft_picks(teams: list[Team], years: int = 3):
    """
    Ensure draft pick trades are zero-sum across league.

    Algorithm:
    1. Determine which teams should have extra/fewer picks (by status)
    2. Create trade chains that balance
    3. Assign to teams
    """

    # Status -> expected pick delta
    PICK_DELTAS = {
        TeamStatus.DYNASTY: -2,      # Traded picks for veterans
        TeamStatus.CONTENDING: -1,   # Slight deficit
        TeamStatus.WINDOW_CLOSING: -3,  # Mortgaged future
        TeamStatus.REBUILDING: +4,   # Accumulated picks
        TeamStatus.EMERGING: +1,     # Still have some extra
        TeamStatus.STUCK_IN_MIDDLE: 0,
        TeamStatus.MISMANAGED: -1,   # Bad trades
    }

    # Assign deltas and balance
    deltas = [PICK_DELTAS[t.status.current_status] for t in teams]

    # Adjust to sum to zero
    total = sum(deltas)
    if total != 0:
        # Distribute excess/deficit
        adjustment = -total // len(teams)
        for i in range(abs(total) % len(teams)):
            deltas[i] += 1 if total < 0 else -1

    # Create trade chains
    givers = [(t, d) for t, d in zip(teams, deltas) if d < 0]
    takers = [(t, d) for t, d in zip(teams, deltas) if d > 0]

    trades = []
    for giver, give_amount in givers:
        for _ in range(abs(give_amount)):
            # Find a taker
            taker, take_amount = takers[0]
            trades.append(create_pick_trade(giver, taker, year=random.choice(years)))
            takers[0] = (taker, take_amount - 1)
            if takers[0][1] == 0:
                takers.pop(0)

    return trades
```

---

## Summary

To generate leagues with coherent history, we need to either:

1. **Simulate it** (most realistic, most work)
2. **Synthesize it** (faster, requires templates and balancing)
3. **Hybrid** (generate + short simulation)

The key missing systems are:
- Enhanced contract tracking with cap hits
- Draft pick ownership tracking
- Transaction logging
- AI decision-making for drafts, free agency, trades, roster management

I recommend starting with **synthetic history generation** (Approach B) because:
- It can be implemented now without full AI
- It provides good-enough realism for initial gameplay
- It creates the data structures needed for full simulation later
- The templates can inform AI development

The AI systems can then be built incrementally, eventually enabling full historical simulation.
