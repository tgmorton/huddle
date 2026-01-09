"""Roster Bridge - Convert management players to V2 simulation players.

Bridges the gap between:
- Management layer: Team, Roster, DepthChart, core.models.Player
- Simulation layer: v2.core.entities.Player, PlayerAttributes

This module handles:
1. Extracting starters from depth charts
2. Converting core Player attributes to v2 PlayerAttributes
3. Positioning players at formation alignments
4. Creating v2 Player objects ready for orchestrator.setup_play()
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from huddle.core.enums import Position as CorePosition
from huddle.simulation.v2.core.entities import (
    Player as V2Player,
    PlayerAttributes as V2Attributes,
    Position as V2Position,
    Team as V2Team,
)
from huddle.simulation.v2.core.vec2 import Vec2

if TYPE_CHECKING:
    from huddle.core.models.player import Player as CorePlayer
    from huddle.core.models.team import Team


# =============================================================================
# Position Mapping
# =============================================================================

# Map core.enums.Position to v2.core.entities.Position
POSITION_MAP: Dict[CorePosition, V2Position] = {
    # Offense
    CorePosition.QB: V2Position.QB,
    CorePosition.RB: V2Position.RB,
    CorePosition.FB: V2Position.FB,
    CorePosition.WR: V2Position.WR,
    CorePosition.TE: V2Position.TE,
    CorePosition.LT: V2Position.LT,
    CorePosition.LG: V2Position.LG,
    CorePosition.C: V2Position.C,
    CorePosition.RG: V2Position.RG,
    CorePosition.RT: V2Position.RT,
    # Defense
    CorePosition.DT: V2Position.DT,
    CorePosition.DE: V2Position.DE,
    CorePosition.NT: V2Position.NT,
    CorePosition.MLB: V2Position.MLB,
    CorePosition.OLB: V2Position.OLB,
    CorePosition.ILB: V2Position.ILB,
    CorePosition.CB: V2Position.CB,
    CorePosition.FS: V2Position.FS,
    CorePosition.SS: V2Position.SS,
}


# =============================================================================
# Formation Alignments
# =============================================================================

# Standard offensive alignments (x, y) where y=0 is LOS
# Coordinates in yards from center
OFFENSIVE_ALIGNMENTS: Dict[str, Vec2] = {
    # Offensive line
    "LT1": Vec2(-6.0, 0.0),
    "LG1": Vec2(-3.0, 0.0),
    "C1": Vec2(0.0, 0.0),
    "RG1": Vec2(3.0, 0.0),
    "RT1": Vec2(6.0, 0.0),
    # Skill positions - Singleback base
    "QB1": Vec2(0.0, -5.0),  # Under center would be -1, shotgun is -5
    "RB1": Vec2(0.0, -7.0),  # Behind QB
    "FB1": Vec2(0.0, -3.0),  # In front of RB (if present)
    "WR1": Vec2(-25.0, 0.0),  # X receiver (split end)
    "WR2": Vec2(22.0, -1.0),  # Z receiver (flanker, off line)
    "WR3": Vec2(-8.0, -1.0),  # Slot left
    "TE1": Vec2(8.0, 0.0),  # Tight end (on line)
}

# Standard defensive alignments (vs 11 personnel)
DEFENSIVE_ALIGNMENTS: Dict[str, Vec2] = {
    # Defensive line (4-3 base)
    "DE1": Vec2(-7.0, 1.0),  # Left DE
    "DE2": Vec2(7.0, 1.0),   # Right DE
    "DT1": Vec2(-2.0, 1.0),  # Left DT / 1-tech
    "DT2": Vec2(2.0, 1.0),   # Right DT / 3-tech
    # Linebackers
    "MLB1": Vec2(0.0, 5.0),  # Mike
    "OLB1": Vec2(-10.0, 5.0),  # Will (weak side)
    "OLB2": Vec2(10.0, 5.0),   # Sam (strong side)
    # Secondary
    "CB1": Vec2(-24.0, 7.0),  # Left CB (press alignment)
    "CB2": Vec2(21.0, 7.0),   # Right CB
    "FS1": Vec2(0.0, 15.0),   # Free safety (center field)
    "SS1": Vec2(8.0, 10.0),   # Strong safety
}


# =============================================================================
# Attribute Mapping
# =============================================================================

def convert_attributes(core_player: "CorePlayer") -> V2Attributes:
    """Convert core player attributes to V2 simulation attributes.

    The v2 PlayerAttributes has a specific set of fields. We map from
    the core attribute system which uses a dictionary.

    Args:
        core_player: Player from management layer

    Returns:
        V2 PlayerAttributes for simulation
    """
    attrs = core_player.attributes

    return V2Attributes(
        # Physical
        speed=attrs.get("speed", 75),
        acceleration=attrs.get("acceleration", 75),
        agility=attrs.get("agility", 75),
        strength=attrs.get("strength", 75),
        # Mental
        awareness=attrs.get("awareness", 75),
        vision=attrs.get("vision", 75),
        play_recognition=attrs.get("play_recognition", 75),
        # Position-specific
        route_running=attrs.get("route_running", 75),
        catching=attrs.get("catching", 75),
        throw_power=attrs.get("throw_power", 75),
        throw_accuracy=attrs.get("throw_accuracy", 75),
        tackling=attrs.get("tackling", 75),
        man_coverage=attrs.get("man_coverage", 75),
        zone_coverage=attrs.get("zone_coverage", 75),
        press=attrs.get("press", 75),
        block_power=attrs.get("block_power", 75),
        block_finesse=attrs.get("block_finesse", 75),
        pass_rush=attrs.get("pass_rush", 75),
        elusiveness=attrs.get("elusiveness", 75),
    )


# =============================================================================
# Player Conversion
# =============================================================================

def convert_player(
    core_player: "CorePlayer",
    slot: str,
    alignment: Vec2,
    team: V2Team,
    los_y: float = 0.0,
) -> V2Player:
    """Convert a core Player to a V2 simulation Player.

    Args:
        core_player: Player from management layer
        slot: Depth chart slot (e.g., "QB1", "WR2")
        alignment: Pre-snap position (formation-relative, LOS at y=0)
        team: V2 team enum (OFFENSE or DEFENSE)
        los_y: Line of scrimmage Y position in field coordinates

    Returns:
        V2 Player ready for simulation
    """
    # Map position
    v2_position = POSITION_MAP.get(core_player.position, V2Position.WR)

    # Create unique ID (use core player's UUID as string)
    player_id = str(core_player.id)

    # Build display name
    name = core_player.display_name or f"#{core_player.jersey_number}"

    # Translate alignment to field coordinates
    # Formation alignment is relative to LOS at y=0
    # Add los_y to get actual field position
    field_pos = Vec2(alignment.x, alignment.y + los_y)

    return V2Player(
        id=player_id,
        name=name,
        team=team,
        position=v2_position,
        position_slot=slot,
        pos=field_pos,
        velocity=Vec2.zero(),
        facing=Vec2.up() if team == V2Team.OFFENSE else Vec2.down(),
        attributes=convert_attributes(core_player),
        weight=float(core_player.weight_lbs),
        height=core_player.height_inches / 36.0,  # Convert to yards
    )


# =============================================================================
# Roster Bridge
# =============================================================================

@dataclass
class RosterBridge:
    """Bridge between management Team and V2 simulation players.

    Holds references to the core Team and provides methods to extract
    and convert players for simulation.

    Attributes:
        team: The management-layer Team
        player_cache: Cache of converted V2 players by slot
    """

    team: "Team"
    _player_cache: Dict[str, V2Player] = None

    def __post_init__(self):
        self._player_cache = {}

    def get_offensive_11(self, formation: str = "singleback", los_y: float = 0.0) -> List[V2Player]:
        """Get 11 offensive players for simulation.

        Extracts starters from depth chart, converts to V2 players,
        and positions at formation alignments translated to field coordinates.

        Args:
            formation: Formation name (affects alignments)
            los_y: Line of scrimmage Y position in field coordinates

        Returns:
            List of 11 V2 Players ready for setup_play()
        """
        players = []

        # Get starters from depth chart
        starters = self.team.roster.get_offensive_starters()

        # Standard 11 personnel slots (no FB)
        standard_slots = ["QB1", "RB1", "WR1", "WR2", "WR3", "TE1", "LT1", "LG1", "C1", "RG1", "RT1"]

        # Convert each starter (limit to 11)
        for slot in standard_slots:
            if slot in starters:
                core_player = starters[slot]
                alignment = OFFENSIVE_ALIGNMENTS.get(slot, Vec2.zero())
                v2_player = convert_player(
                    core_player, slot, alignment, V2Team.OFFENSE, los_y
                )
                players.append(v2_player)
                self._player_cache[slot] = v2_player

        return players[:11]  # Ensure max 11

    def get_defensive_11(self, scheme: str = "4-3", los_y: float = 0.0) -> List[V2Player]:
        """Get 11 defensive players for simulation.

        Args:
            scheme: Defensive scheme (affects alignments)
            los_y: Line of scrimmage Y position in field coordinates

        Returns:
            List of 11 V2 Players ready for setup_play()
        """
        players = []

        # Get starters from depth chart
        starters = self.team.roster.get_defensive_starters()

        # Convert each starter
        for slot, core_player in starters.items():
            alignment = DEFENSIVE_ALIGNMENTS.get(slot, Vec2.zero())
            v2_player = convert_player(
                core_player, slot, alignment, V2Team.DEFENSE, los_y
            )
            players.append(v2_player)
            self._player_cache[slot] = v2_player

        return players[:11]  # Ensure max 11

    def get_player_by_slot(self, slot: str) -> Optional[V2Player]:
        """Get a converted player by their depth chart slot."""
        return self._player_cache.get(slot)

    def get_core_player_by_slot(self, slot: str) -> Optional["CorePlayer"]:
        """Get the original core player by slot."""
        return self.team.roster.get_starter(slot)

    def get_qb(self) -> Optional[V2Player]:
        """Get the starting QB as a V2 player."""
        return self._player_cache.get("QB1")

    def get_rb(self) -> Optional[V2Player]:
        """Get the starting RB as a V2 player."""
        return self._player_cache.get("RB1")


# =============================================================================
# Convenience Functions
# =============================================================================

def get_offensive_11(team: "Team", formation: str = "singleback", los_y: float = 0.0) -> List[V2Player]:
    """Get 11 offensive players for a team.

    Convenience function that creates a RosterBridge and extracts players.

    Args:
        team: Management-layer Team
        formation: Formation name
        los_y: Line of scrimmage Y position in field coordinates

    Returns:
        List of 11 V2 Players
    """
    bridge = RosterBridge(team)
    return bridge.get_offensive_11(formation, los_y)


def get_defensive_11(team: "Team", scheme: str = "4-3", los_y: float = 0.0) -> List[V2Player]:
    """Get 11 defensive players for a team.

    Args:
        team: Management-layer Team
        scheme: Defensive scheme
        los_y: Line of scrimmage Y position in field coordinates

    Returns:
        List of 11 V2 Players
    """
    bridge = RosterBridge(team)
    return bridge.get_defensive_11(scheme, los_y)
