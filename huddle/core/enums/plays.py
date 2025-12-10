"""Play type definitions and outcomes."""

from enum import Enum, auto


class PenaltyType(Enum):
    """Types of penalties that can occur during a play."""

    # Pre-snap (offense)
    FALSE_START = auto()  # 5 yards
    ILLEGAL_FORMATION = auto()  # 5 yards
    DELAY_OF_GAME = auto()  # 5 yards

    # Pre-snap (defense)
    ENCROACHMENT = auto()  # 5 yards
    NEUTRAL_ZONE_INFRACTION = auto()  # 5 yards
    OFFSIDES = auto()  # 5 yards

    # During play (offense)
    HOLDING_OFFENSE = auto()  # 10 yards
    OFFENSIVE_PASS_INTERFERENCE = auto()  # 10 yards, loss of down
    ILLEGAL_USE_OF_HANDS = auto()  # 10 yards
    ILLEGAL_BLOCK_IN_BACK = auto()  # 10 yards
    INELIGIBLE_RECEIVER = auto()  # 5 yards

    # During play (defense)
    HOLDING_DEFENSE = auto()  # 5 yards, auto first down
    DEFENSIVE_PASS_INTERFERENCE = auto()  # Spot foul, auto first down
    ROUGHING_THE_PASSER = auto()  # 15 yards, auto first down
    UNNECESSARY_ROUGHNESS = auto()  # 15 yards
    FACEMASK = auto()  # 15 yards

    @property
    def yards(self) -> int:
        """Get yardage penalty for this penalty type."""
        # Note: DPI is spot foul, handled separately
        penalty_yards = {
            PenaltyType.FALSE_START: 5,
            PenaltyType.ILLEGAL_FORMATION: 5,
            PenaltyType.DELAY_OF_GAME: 5,
            PenaltyType.ENCROACHMENT: 5,
            PenaltyType.NEUTRAL_ZONE_INFRACTION: 5,
            PenaltyType.OFFSIDES: 5,
            PenaltyType.HOLDING_OFFENSE: 10,
            PenaltyType.OFFENSIVE_PASS_INTERFERENCE: 10,
            PenaltyType.ILLEGAL_USE_OF_HANDS: 10,
            PenaltyType.ILLEGAL_BLOCK_IN_BACK: 10,
            PenaltyType.INELIGIBLE_RECEIVER: 5,
            PenaltyType.HOLDING_DEFENSE: 5,
            PenaltyType.DEFENSIVE_PASS_INTERFERENCE: 0,  # Spot foul
            PenaltyType.ROUGHING_THE_PASSER: 15,
            PenaltyType.UNNECESSARY_ROUGHNESS: 15,
            PenaltyType.FACEMASK: 15,
        }
        return penalty_yards.get(self, 5)

    @property
    def is_on_offense(self) -> bool:
        """Check if this penalty is on the offense."""
        return self in {
            PenaltyType.FALSE_START,
            PenaltyType.ILLEGAL_FORMATION,
            PenaltyType.DELAY_OF_GAME,
            PenaltyType.HOLDING_OFFENSE,
            PenaltyType.OFFENSIVE_PASS_INTERFERENCE,
            PenaltyType.ILLEGAL_USE_OF_HANDS,
            PenaltyType.ILLEGAL_BLOCK_IN_BACK,
            PenaltyType.INELIGIBLE_RECEIVER,
        }

    @property
    def is_pre_snap(self) -> bool:
        """Check if this penalty is called before the snap."""
        return self in {
            PenaltyType.FALSE_START,
            PenaltyType.ILLEGAL_FORMATION,
            PenaltyType.DELAY_OF_GAME,
            PenaltyType.ENCROACHMENT,
            PenaltyType.NEUTRAL_ZONE_INFRACTION,
            PenaltyType.OFFSIDES,
        }

    @property
    def is_automatic_first_down(self) -> bool:
        """Check if this penalty results in automatic first down."""
        return self in {
            PenaltyType.HOLDING_DEFENSE,
            PenaltyType.DEFENSIVE_PASS_INTERFERENCE,
            PenaltyType.ROUGHING_THE_PASSER,
        }

    @property
    def is_loss_of_down(self) -> bool:
        """Check if this penalty results in loss of down."""
        return self in {
            PenaltyType.OFFENSIVE_PASS_INTERFERENCE,
        }


class PersonnelPackage(Enum):
    """Offensive personnel packages (RB count + TE count notation)."""

    ELEVEN = "11"  # 1 RB, 1 TE, 3 WR (most common passing)
    TWELVE = "12"  # 1 RB, 2 TE, 2 WR (balanced)
    TWENTY_ONE = "21"  # 2 RB, 1 TE, 2 WR (power running)
    TWENTY_TWO = "22"  # 2 RB, 2 TE, 1 WR (goal line / short yardage)
    TEN = "10"  # 1 RB, 0 TE, 4 WR (spread / passing)
    THIRTEEN = "13"  # 1 RB, 3 TE, 1 WR (jumbo / goal line)
    EMPTY = "00"  # 0 RB, 1 TE, 4 WR (empty backfield)

    @property
    def rb_count(self) -> int:
        """Number of running backs in this package."""
        return int(self.value[0])

    @property
    def te_count(self) -> int:
        """Number of tight ends in this package."""
        return int(self.value[1])

    @property
    def wr_count(self) -> int:
        """Number of wide receivers (5 skill players minus RB and TE)."""
        return 5 - self.rb_count - self.te_count

    def get_depth_slots(self) -> list[str]:
        """Get the depth chart slots needed for this personnel package."""
        slots = ["QB1"]

        # Add RBs
        for i in range(1, self.rb_count + 1):
            slots.append(f"RB{i}")

        # Add TEs
        for i in range(1, self.te_count + 1):
            slots.append(f"TE{i}")

        # Add WRs
        for i in range(1, self.wr_count + 1):
            slots.append(f"WR{i}")

        return slots


class Formation(Enum):
    """Offensive formations affecting play execution."""

    SHOTGUN = "Shotgun"
    SINGLEBACK = "Singleback"
    I_FORM = "I-Form"
    PISTOL = "Pistol"
    SPREAD = "Spread"
    GOAL_LINE = "Goal Line"
    EMPTY = "Empty"
    UNDER_CENTER = "Under Center"

    @property
    def pass_modifier(self) -> float:
        """Modifier applied to pass completion probability."""
        modifiers = {
            Formation.SHOTGUN: 1.08,  # Better passing
            Formation.SINGLEBACK: 1.0,  # Neutral
            Formation.I_FORM: 0.92,  # Run-oriented
            Formation.PISTOL: 1.03,  # Slightly better passing
            Formation.SPREAD: 1.10,  # Best passing
            Formation.GOAL_LINE: 0.80,  # Very run-oriented
            Formation.EMPTY: 1.12,  # Maximum passing
            Formation.UNDER_CENTER: 0.95,  # Slightly run-oriented
        }
        return modifiers.get(self, 1.0)

    @property
    def run_modifier(self) -> float:
        """Modifier applied to run success probability."""
        modifiers = {
            Formation.SHOTGUN: 0.90,  # Worse running
            Formation.SINGLEBACK: 1.0,  # Neutral
            Formation.I_FORM: 1.12,  # Great running (lead blocker)
            Formation.PISTOL: 0.98,  # Slightly worse running
            Formation.SPREAD: 0.85,  # Worst running
            Formation.GOAL_LINE: 1.15,  # Best running (power)
            Formation.EMPTY: 0.70,  # No RB for handoff
            Formation.UNDER_CENTER: 1.08,  # Good running
        }
        return modifiers.get(self, 1.0)

    @property
    def is_pass_oriented(self) -> bool:
        """Check if this formation favors passing."""
        return self.pass_modifier > 1.0

    @property
    def is_run_oriented(self) -> bool:
        """Check if this formation favors running."""
        return self.run_modifier > 1.0


class PlayType(Enum):
    """Top-level play categories."""

    RUN = auto()
    PASS = auto()
    PUNT = auto()
    FIELD_GOAL = auto()
    KICKOFF = auto()
    EXTRA_POINT = auto()
    TWO_POINT = auto()


class RunType(Enum):
    """Run play subcategories."""

    INSIDE = auto()  # Between the tackles (A/B gaps)
    OUTSIDE = auto()  # Sweeps, tosses, pitches
    DRAW = auto()  # Delayed handoff, fake pass action
    OPTION = auto()  # QB option plays
    QB_SNEAK = auto()  # Short yardage QB run
    QB_SCRAMBLE = auto()  # Broken play QB run


class PassType(Enum):
    """Pass play subcategories by depth."""

    SCREEN = auto()  # Behind line of scrimmage
    SHORT = auto()  # 0-10 yards
    MEDIUM = auto()  # 10-20 yards
    DEEP = auto()  # 20+ yards
    HAIL_MARY = auto()  # Desperation deep pass


class DefensiveScheme(Enum):
    """Basic defensive alignments and coverages."""

    # Zone coverages
    COVER_0 = auto()  # No deep safety, man-to-man with blitz
    COVER_1 = auto()  # Single high safety, man underneath
    COVER_2 = auto()  # Two deep safeties, zone underneath
    COVER_3 = auto()  # Three deep zones
    COVER_4 = auto()  # Four deep zones (prevent)

    # Man coverages
    MAN_PRESS = auto()  # Man coverage with press at line
    MAN_OFF = auto()  # Man coverage with cushion

    # Blitz packages
    BLITZ_4 = auto()  # Four-man rush
    BLITZ_5 = auto()  # Five-man rush
    BLITZ_6 = auto()  # Six-man rush (all-out blitz)


class PlayOutcome(Enum):
    """Possible outcomes of a play."""

    # Passing outcomes
    COMPLETE = auto()  # Pass completed
    INCOMPLETE = auto()  # Pass incomplete
    INTERCEPTION = auto()  # Pass intercepted
    SACK = auto()  # QB sacked

    # Rushing outcomes
    RUSH = auto()  # Normal rushing play
    FUMBLE = auto()  # Ball carrier fumbled
    FUMBLE_LOST = auto()  # Fumble lost to defense

    # Scoring outcomes
    TOUCHDOWN = auto()
    FIELD_GOAL_GOOD = auto()
    FIELD_GOAL_MISSED = auto()
    SAFETY = auto()
    EXTRA_POINT_GOOD = auto()
    EXTRA_POINT_MISSED = auto()
    TWO_POINT_GOOD = auto()
    TWO_POINT_FAILED = auto()

    # Special teams
    PUNT_RESULT = auto()
    KICKOFF_RESULT = auto()
    TOUCHBACK = auto()

    # Penalties
    PENALTY_OFFENSE = auto()
    PENALTY_DEFENSE = auto()

    @property
    def is_turnover(self) -> bool:
        """Check if this outcome results in a turnover."""
        return self in {
            PlayOutcome.INTERCEPTION,
            PlayOutcome.FUMBLE_LOST,
        }

    @property
    def is_scoring(self) -> bool:
        """Check if this outcome results in points."""
        return self in {
            PlayOutcome.TOUCHDOWN,
            PlayOutcome.FIELD_GOAL_GOOD,
            PlayOutcome.SAFETY,
            PlayOutcome.EXTRA_POINT_GOOD,
            PlayOutcome.TWO_POINT_GOOD,
        }

    @property
    def points(self) -> int:
        """Get points scored for this outcome (0 if non-scoring)."""
        scoring_map = {
            PlayOutcome.TOUCHDOWN: 6,
            PlayOutcome.FIELD_GOAL_GOOD: 3,
            PlayOutcome.SAFETY: 2,
            PlayOutcome.EXTRA_POINT_GOOD: 1,
            PlayOutcome.TWO_POINT_GOOD: 2,
        }
        return scoring_map.get(self, 0)
