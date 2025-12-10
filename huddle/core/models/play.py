"""Play call and result models."""

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from huddle.core.enums import (
    DefensiveScheme,
    Formation,
    PassType,
    PersonnelPackage,
    PlayOutcome,
    PlayType,
    RunType,
)


@dataclass
class PlayCall:
    """
    Represents an offensive play call (before execution).

    This is the interface for the playcalling system. Starts simple
    with play type and subcategory, but has fields for future expansion
    to full playbook with formations and routes.
    """

    play_type: PlayType

    # Subcategory (one of these will be set based on play_type)
    run_type: Optional[RunType] = None
    pass_type: Optional[PassType] = None

    # Formation and personnel package
    formation: Optional[Formation] = None
    personnel: Optional[PersonnelPackage] = None

    # Future expansion: specific route concepts
    route_concept: Optional[str] = None  # "Mesh", "Flood", "Four Verts", etc.

    # Target selection (can be set by play caller or determined by resolver)
    primary_target_slot: Optional[str] = None  # "WR1", "TE1", etc.
    ball_carrier_slot: Optional[str] = None  # For run plays

    @classmethod
    def run(
        cls,
        run_type: RunType,
        formation: Optional[Formation] = None,
        personnel: Optional[PersonnelPackage] = None,
    ) -> "PlayCall":
        """Create a run play call."""
        return cls(
            play_type=PlayType.RUN,
            run_type=run_type,
            formation=formation or Formation.SINGLEBACK,
            personnel=personnel or PersonnelPackage.TWELVE,
        )

    @classmethod
    def pass_play(
        cls,
        pass_type: PassType,
        formation: Optional[Formation] = None,
        personnel: Optional[PersonnelPackage] = None,
    ) -> "PlayCall":
        """Create a pass play call."""
        return cls(
            play_type=PlayType.PASS,
            pass_type=pass_type,
            formation=formation or Formation.SHOTGUN,
            personnel=personnel or PersonnelPackage.ELEVEN,
        )

    @classmethod
    def punt(cls) -> "PlayCall":
        """Create a punt play call."""
        return cls(play_type=PlayType.PUNT)

    @classmethod
    def field_goal(cls) -> "PlayCall":
        """Create a field goal play call."""
        return cls(play_type=PlayType.FIELD_GOAL)

    @classmethod
    def kickoff(cls) -> "PlayCall":
        """Create a kickoff play call."""
        return cls(play_type=PlayType.KICKOFF)

    @classmethod
    def extra_point(cls) -> "PlayCall":
        """Create an extra point (PAT) play call."""
        return cls(play_type=PlayType.EXTRA_POINT)

    @classmethod
    def two_point(cls, pass_type: Optional[PassType] = None, run_type: Optional[RunType] = None) -> "PlayCall":
        """Create a two-point conversion play call."""
        return cls(play_type=PlayType.TWO_POINT, pass_type=pass_type, run_type=run_type)

    @property
    def is_run(self) -> bool:
        """Check if this is a run play."""
        return self.play_type == PlayType.RUN

    @property
    def is_pass(self) -> bool:
        """Check if this is a pass play."""
        return self.play_type == PlayType.PASS

    @property
    def display(self) -> str:
        """Human-readable play call description."""
        if self.play_type == PlayType.RUN and self.run_type:
            return f"Run {self.run_type.name.title()}"
        elif self.play_type == PlayType.PASS and self.pass_type:
            return f"Pass {self.pass_type.name.title()}"
        else:
            return self.play_type.name.title().replace("_", " ")

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "play_type": self.play_type.name,
            "run_type": self.run_type.name if self.run_type else None,
            "pass_type": self.pass_type.name if self.pass_type else None,
            "formation": self.formation.name if self.formation else None,
            "personnel": self.personnel.value if self.personnel else None,
            "route_concept": self.route_concept,
            "primary_target_slot": self.primary_target_slot,
            "ball_carrier_slot": self.ball_carrier_slot,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayCall":
        """Create from dictionary."""
        # Handle personnel by value (e.g., "11", "12")
        personnel = None
        if data.get("personnel"):
            personnel_val = data["personnel"]
            for pkg in PersonnelPackage:
                if pkg.value == personnel_val:
                    personnel = pkg
                    break

        return cls(
            play_type=PlayType[data["play_type"]],
            run_type=RunType[data["run_type"]] if data.get("run_type") else None,
            pass_type=PassType[data["pass_type"]] if data.get("pass_type") else None,
            formation=Formation[data["formation"]] if data.get("formation") else None,
            personnel=personnel,
            route_concept=data.get("route_concept"),
            primary_target_slot=data.get("primary_target_slot"),
            ball_carrier_slot=data.get("ball_carrier_slot"),
        )


@dataclass
class DefensiveCall:
    """
    Represents a defensive play call.

    Determines coverage scheme and blitz packages.
    """

    scheme: DefensiveScheme = DefensiveScheme.COVER_3
    blitz_count: int = 4  # Number of pass rushers (standard is 4)

    # Future expansion: specific coverage assignments
    coverage_assignments: dict[str, str] = field(default_factory=dict)  # slot -> assignment

    @classmethod
    def cover_2(cls) -> "DefensiveCall":
        """Create Cover 2 zone defense."""
        return cls(scheme=DefensiveScheme.COVER_2)

    @classmethod
    def cover_3(cls) -> "DefensiveCall":
        """Create Cover 3 zone defense."""
        return cls(scheme=DefensiveScheme.COVER_3)

    @classmethod
    def man(cls, press: bool = False) -> "DefensiveCall":
        """Create man coverage defense."""
        scheme = DefensiveScheme.MAN_PRESS if press else DefensiveScheme.MAN_OFF
        return cls(scheme=scheme)

    @classmethod
    def blitz(cls, rushers: int = 5) -> "DefensiveCall":
        """Create blitz defense."""
        scheme_map = {5: DefensiveScheme.BLITZ_5, 6: DefensiveScheme.BLITZ_6}
        scheme = scheme_map.get(rushers, DefensiveScheme.BLITZ_5)
        return cls(scheme=scheme, blitz_count=rushers)

    @property
    def is_blitz(self) -> bool:
        """Check if this is a blitz call."""
        return self.blitz_count > 4

    @property
    def is_zone(self) -> bool:
        """Check if this is zone coverage."""
        return self.scheme in {
            DefensiveScheme.COVER_0,
            DefensiveScheme.COVER_1,
            DefensiveScheme.COVER_2,
            DefensiveScheme.COVER_3,
            DefensiveScheme.COVER_4,
        }

    @property
    def display(self) -> str:
        """Human-readable defensive call."""
        if self.is_blitz:
            return f"{self.scheme.name.replace('_', ' ').title()} ({self.blitz_count} rush)"
        return self.scheme.name.replace("_", " ").title()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "scheme": self.scheme.name,
            "blitz_count": self.blitz_count,
            "coverage_assignments": self.coverage_assignments,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DefensiveCall":
        """Create from dictionary."""
        return cls(
            scheme=DefensiveScheme[data.get("scheme", "COVER_3")],
            blitz_count=data.get("blitz_count", 4),
            coverage_assignments=data.get("coverage_assignments", {}),
        )


@dataclass
class PlayResult:
    """
    Result of a simulated play.

    Contains all information needed for logging, statistics, and state updates.
    This is what the simulation engine produces after resolving a play.
    """

    # What was called
    play_call: PlayCall
    defensive_call: DefensiveCall

    # Core outcome
    outcome: PlayOutcome
    yards_gained: int = 0

    # Time consumed
    time_elapsed_seconds: int = 0

    # Player attributions (for statistics) - using player IDs
    passer_id: Optional[UUID] = None
    receiver_id: Optional[UUID] = None
    rusher_id: Optional[UUID] = None
    tackler_id: Optional[UUID] = None
    interceptor_id: Optional[UUID] = None
    fumble_forced_by_id: Optional[UUID] = None
    fumble_recovered_by_id: Optional[UUID] = None

    # Result flags
    is_first_down: bool = False
    is_touchdown: bool = False
    is_turnover: bool = False
    is_sack: bool = False
    is_safety: bool = False

    # Clock management
    clock_stopped: bool = False  # Did clock stop after this play?
    clock_stop_reason: Optional[str] = None  # "incomplete", "out_of_bounds", "penalty", etc.

    # Scoring
    points_scored: int = 0

    # Penalty info (if applicable)
    penalty_on_offense: bool = False
    penalty_yards: int = 0
    penalty_type: Optional[str] = None
    penalty_declined: bool = False

    # Narrative text for game log
    description: str = ""

    @property
    def display(self) -> str:
        """Short display of play result."""
        if self.is_touchdown:
            return f"TOUCHDOWN! {self.yards_gained} yards"
        elif self.is_turnover:
            return f"TURNOVER: {self.outcome.name}"
        elif self.is_sack:
            return f"SACK: {abs(self.yards_gained)} yard loss"
        elif self.outcome == PlayOutcome.INCOMPLETE:
            return "Incomplete pass"
        elif self.outcome == PlayOutcome.COMPLETE:
            return f"Complete for {self.yards_gained} yards"
        elif self.outcome == PlayOutcome.RUSH:
            if self.yards_gained >= 0:
                return f"Rush for {self.yards_gained} yards"
            else:
                return f"Rush for {self.yards_gained} yards (loss)"
        else:
            return f"{self.outcome.name}: {self.yards_gained} yards"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "play_call": self.play_call.to_dict(),
            "defensive_call": self.defensive_call.to_dict(),
            "outcome": self.outcome.name,
            "yards_gained": self.yards_gained,
            "time_elapsed_seconds": self.time_elapsed_seconds,
            "passer_id": str(self.passer_id) if self.passer_id else None,
            "receiver_id": str(self.receiver_id) if self.receiver_id else None,
            "rusher_id": str(self.rusher_id) if self.rusher_id else None,
            "tackler_id": str(self.tackler_id) if self.tackler_id else None,
            "interceptor_id": str(self.interceptor_id) if self.interceptor_id else None,
            "fumble_forced_by_id": str(self.fumble_forced_by_id)
            if self.fumble_forced_by_id
            else None,
            "fumble_recovered_by_id": str(self.fumble_recovered_by_id)
            if self.fumble_recovered_by_id
            else None,
            "is_first_down": self.is_first_down,
            "is_touchdown": self.is_touchdown,
            "is_turnover": self.is_turnover,
            "is_sack": self.is_sack,
            "is_safety": self.is_safety,
            "clock_stopped": self.clock_stopped,
            "clock_stop_reason": self.clock_stop_reason,
            "points_scored": self.points_scored,
            "penalty_on_offense": self.penalty_on_offense,
            "penalty_yards": self.penalty_yards,
            "penalty_type": self.penalty_type,
            "penalty_declined": self.penalty_declined,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayResult":
        """Create from dictionary."""
        return cls(
            play_call=PlayCall.from_dict(data["play_call"]),
            defensive_call=DefensiveCall.from_dict(data["defensive_call"]),
            outcome=PlayOutcome[data["outcome"]],
            yards_gained=data.get("yards_gained", 0),
            time_elapsed_seconds=data.get("time_elapsed_seconds", 0),
            passer_id=UUID(data["passer_id"]) if data.get("passer_id") else None,
            receiver_id=UUID(data["receiver_id"]) if data.get("receiver_id") else None,
            rusher_id=UUID(data["rusher_id"]) if data.get("rusher_id") else None,
            tackler_id=UUID(data["tackler_id"]) if data.get("tackler_id") else None,
            interceptor_id=UUID(data["interceptor_id"]) if data.get("interceptor_id") else None,
            fumble_forced_by_id=UUID(data["fumble_forced_by_id"])
            if data.get("fumble_forced_by_id")
            else None,
            fumble_recovered_by_id=UUID(data["fumble_recovered_by_id"])
            if data.get("fumble_recovered_by_id")
            else None,
            is_first_down=data.get("is_first_down", False),
            is_touchdown=data.get("is_touchdown", False),
            is_turnover=data.get("is_turnover", False),
            is_sack=data.get("is_sack", False),
            is_safety=data.get("is_safety", False),
            clock_stopped=data.get("clock_stopped", False),
            clock_stop_reason=data.get("clock_stop_reason"),
            points_scored=data.get("points_scored", 0),
            penalty_on_offense=data.get("penalty_on_offense", False),
            penalty_yards=data.get("penalty_yards", 0),
            penalty_type=data.get("penalty_type"),
            penalty_declined=data.get("penalty_declined", False),
            description=data.get("description", ""),
        )


@dataclass
class DriveResult:
    """
    Result of a complete drive (for fast/abstract simulation).

    Aggregates multiple plays into a single outcome for quick simulation.
    """

    starting_yard_line: int  # 0-100 scale
    ending_yard_line: int
    plays: int = 0
    total_yards: int = 0
    time_elapsed_seconds: int = 0

    # Drive outcome
    result: str = ""  # "TD", "FG", "FG_MISS", "PUNT", "TURNOVER", "DOWNS", "END_HALF"
    points: int = 0

    # Key plays (optional, for narrative)
    big_plays: list[str] = field(default_factory=list)  # Descriptions of notable plays

    @property
    def display(self) -> str:
        """Human-readable drive summary."""
        if self.result == "TD":
            return f"TOUCHDOWN DRIVE: {self.plays} plays, {self.total_yards} yards"
        elif self.result == "FG":
            return f"FIELD GOAL: {self.plays} plays, {self.total_yards} yards"
        elif self.result == "PUNT":
            return f"PUNT: {self.plays} plays, {self.total_yards} yards"
        elif self.result == "TURNOVER":
            return f"TURNOVER: {self.plays} plays, {self.total_yards} yards"
        else:
            return f"{self.result}: {self.plays} plays, {self.total_yards} yards"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "starting_yard_line": self.starting_yard_line,
            "ending_yard_line": self.ending_yard_line,
            "plays": self.plays,
            "total_yards": self.total_yards,
            "time_elapsed_seconds": self.time_elapsed_seconds,
            "result": self.result,
            "points": self.points,
            "big_plays": self.big_plays,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DriveResult":
        """Create from dictionary."""
        return cls(
            starting_yard_line=data.get("starting_yard_line", 25),
            ending_yard_line=data.get("ending_yard_line", 25),
            plays=data.get("plays", 0),
            total_yards=data.get("total_yards", 0),
            time_elapsed_seconds=data.get("time_elapsed_seconds", 0),
            result=data.get("result", ""),
            points=data.get("points", 0),
            big_plays=data.get("big_plays", []),
        )
