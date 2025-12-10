"""Base interfaces for play resolution."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from huddle.core.models.game import GameState
    from huddle.core.models.play import DefensiveCall, DriveResult, PlayCall, PlayResult
    from huddle.core.models.team import Team


class PlayResolver(ABC):
    """
    Protocol for play resolution strategies.

    Implementations determine how individual plays are simulated.
    Different resolvers can use different approaches:
    - Statistical (probability-based)
    - Physics (movement simulation)
    - Hybrid

    All resolvers share the same interface, allowing the engine
    to swap between them transparently.
    """

    @abstractmethod
    def resolve_play(
        self,
        game_state: "GameState",
        offensive_team: "Team",
        defensive_team: "Team",
        offensive_call: "PlayCall",
        defensive_call: "DefensiveCall",
    ) -> "PlayResult":
        """
        Simulate a single play and return the result.

        Args:
            game_state: Current game state (read-only, don't modify)
            offensive_team: Team on offense with roster
            defensive_team: Team on defense with roster
            offensive_call: The play called by offense
            defensive_call: The defensive alignment/call

        Returns:
            PlayResult containing outcome, yards, attributions, etc.
        """
        ...


class DriveResolver(ABC):
    """
    Protocol for drive-level simulation.

    Used for fast/abstract simulation mode where entire drives
    are simulated as single units based on team ratings.
    """

    @abstractmethod
    def resolve_drive(
        self,
        game_state: "GameState",
        offensive_team: "Team",
        defensive_team: "Team",
    ) -> "DriveResult":
        """
        Simulate an entire drive and return the result.

        Args:
            game_state: Current game state (read-only, don't modify)
            offensive_team: Team on offense
            defensive_team: Team on defense

        Returns:
            DriveResult containing plays, yards, outcome, points
        """
        ...
