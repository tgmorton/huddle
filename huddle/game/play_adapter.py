"""Play Adapter - Convert playbook plays to V2 PlayConfig.

Bridges the gap between:
- Playbook layer: PlayCode, PlayCategory (high-level play identifiers)
- Simulation layer: PlayConfig (routes, coverages, timings)

This module handles:
1. Mapping PlayCodes to V2 route configurations
2. Setting appropriate timing (dropback type, throw windows)
3. Configuring run concepts for ground plays
4. Building defense configurations from coverage calls
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional

from huddle.core.playbook.play_codes import PlayCode, PlayCategory, get_play
from huddle.simulation.v2.orchestrator import PlayConfig, DropbackType
from huddle.simulation.v2.plays.routes import RouteType

if TYPE_CHECKING:
    from huddle.simulation.v2.core.entities import Player as V2Player


# =============================================================================
# Play to Route Mapping
# =============================================================================

# Map offensive play codes to route configurations
# Routes are assigned to position slots: WR1 (X), WR2 (Z), WR3 (slot), TE1, RB1
PLAY_ROUTE_MAP: Dict[str, Dict[str, str]] = {
    # Quick passing game
    "PASS_SLANT": {
        "WR1": "slant",
        "WR2": "slant",
        "WR3": "drag",
        "TE1": "flat",
    },
    "PASS_QUICK_OUT": {
        "WR1": "quick_out",
        "WR2": "quick_out",
        "WR3": "slant",
        "TE1": "hitch",
    },
    "PASS_HITCH": {
        "WR1": "hitch",
        "WR2": "hitch",
        "WR3": "hitch",
        "TE1": "flat",
    },
    # Intermediate
    "PASS_CURL": {
        "WR1": "curl",
        "WR2": "curl",
        "WR3": "drag",
        "TE1": "curl",
    },
    "PASS_DIG": {
        "WR1": "dig",
        "WR2": "post",
        "WR3": "drag",
        "TE1": "seam",
    },
    "PASS_COMEBACK": {
        "WR1": "comeback",
        "WR2": "comeback",
        "WR3": "drag",
        "TE1": "out",
    },
    "PASS_CROSSER": {
        "WR1": "cross",
        "WR2": "dig",
        "WR3": "cross",
        "TE1": "drag",
    },
    # Deep passing
    "PASS_FOUR_VERTS": {
        "WR1": "go",
        "WR2": "go",
        "WR3": "seam",
        "TE1": "seam",
    },
    "PASS_POST": {
        "WR1": "post",
        "WR2": "go",
        "WR3": "dig",
        "TE1": "seam",
    },
    "PASS_CORNER": {
        "WR1": "corner",
        "WR2": "corner",
        "WR3": "drag",
        "TE1": "flat",
    },
    "PASS_DOUBLE_MOVE": {
        "WR1": "double_move",
        "WR2": "post",
        "WR3": "drag",
        "TE1": "seam",
    },
    # Concepts
    "PASS_MESH": {
        "WR1": "drag",
        "WR2": "drag",
        "WR3": "out",
        "TE1": "seam",
    },
    "PASS_FLOOD": {
        "WR1": "corner",
        "WR2": "out",
        "WR3": "flat",
        "TE1": "corner",
    },
    "PASS_SMASH": {
        "WR1": "hitch",
        "WR2": "corner",
        "WR3": "drag",
        "TE1": "seam",
    },
    "PASS_LEVELS": {
        "WR1": "dig",
        "WR2": "in",
        "WR3": "flat",
        "TE1": "seam",
    },
    "PASS_SAIL": {
        "WR1": "go",
        "WR2": "corner",
        "WR3": "out",
        "TE1": "flat",
    },
    # Screens
    "PASS_SCREEN_RB": {
        "WR1": "go",
        "WR2": "go",
        "RB1": "screen",
        "TE1": "block",
    },
    "PASS_SCREEN_WR": {
        "WR1": "screen",
        "WR2": "go",
        "WR3": "drag",
        "TE1": "block",
    },
    # Play action
    "PASS_PLAY_ACTION": {
        "WR1": "post",
        "WR2": "go",
        "WR3": "drag",
        "TE1": "seam",
    },
    "PASS_BOOTLEG": {
        "WR1": "corner",
        "WR2": "drag",
        "WR3": "flat",
        "TE1": "out",
    },
}

# Map offensive play codes to run concepts
PLAY_RUN_MAP: Dict[str, str] = {
    "RUN_INSIDE_ZONE": "inside_zone",
    "RUN_OUTSIDE_ZONE": "outside_zone",
    "RUN_POWER": "power",
    "RUN_COUNTER": "counter",
    "RUN_DRAW": "draw",
    "RUN_TRAP": "trap",
    "RUN_SWEEP": "sweep",
    "RUN_OPTION": "option",
    "RUN_QB_SNEAK": "qb_sneak",
}

# Map play codes to dropback types
PLAY_DROPBACK_MAP: Dict[str, DropbackType] = {
    # Quick game = 3-step
    "PASS_SLANT": DropbackType.QUICK,
    "PASS_QUICK_OUT": DropbackType.QUICK,
    "PASS_HITCH": DropbackType.QUICK,
    "PASS_SCREEN_RB": DropbackType.QUICK,
    "PASS_SCREEN_WR": DropbackType.QUICK,
    # Intermediate = 5-step
    "PASS_CURL": DropbackType.STANDARD,
    "PASS_DIG": DropbackType.STANDARD,
    "PASS_COMEBACK": DropbackType.STANDARD,
    "PASS_CROSSER": DropbackType.STANDARD,
    "PASS_MESH": DropbackType.STANDARD,
    "PASS_SMASH": DropbackType.STANDARD,
    # Deep = 7-step
    "PASS_FOUR_VERTS": DropbackType.DEEP,
    "PASS_POST": DropbackType.DEEP,
    "PASS_CORNER": DropbackType.DEEP,
    "PASS_DOUBLE_MOVE": DropbackType.DEEP,
    "PASS_FLOOD": DropbackType.DEEP,
    "PASS_LEVELS": DropbackType.DEEP,
    "PASS_SAIL": DropbackType.DEEP,
    # Play action uses deep timing
    "PASS_PLAY_ACTION": DropbackType.DEEP,
    "PASS_BOOTLEG": DropbackType.STANDARD,
}


# =============================================================================
# Defense Coverage Mapping
# =============================================================================

# Map defensive play codes to coverage configurations
DEFENSE_COVERAGE_MAP: Dict[str, Dict[str, str]] = {
    # Man coverages
    "COVER_0": {
        "CB1": "man:WR1",
        "CB2": "man:WR2",
        "SS1": "man:TE1",
        "OLB1": "man:RB1",
        "OLB2": "man:WR3",
    },
    "COVER_1": {
        "CB1": "man:WR1",
        "CB2": "man:WR2",
        "SS1": "man:TE1",
        "OLB1": "man:RB1",
        "FS1": "deep_middle",  # Free safety
    },
    "MAN_PRESS": {
        "CB1": "man:WR1",
        "CB2": "man:WR2",
        "SS1": "man:TE1",
        "OLB1": "man:WR3",
        "FS1": "deep_middle",
    },
    "MAN_OFF": {
        "CB1": "man:WR1",
        "CB2": "man:WR2",
        "SS1": "man:TE1",
        "FS1": "deep_middle",
    },
    # Zone coverages
    "COVER_2": {
        "CB1": "flat_left",
        "CB2": "flat_right",
        "FS1": "deep_half_left",
        "SS1": "deep_half_right",
        "MLB1": "hook_middle",
        "OLB1": "curl_left",
        "OLB2": "curl_right",
    },
    "COVER_3": {
        "CB1": "deep_third_left",
        "CB2": "deep_third_right",
        "FS1": "deep_third_middle",
        "SS1": "hook_curl",
        "MLB1": "hook_middle",
        "OLB1": "flat_left",
        "OLB2": "flat_right",
    },
    "COVER_4": {
        "CB1": "quarter_left_outside",
        "CB2": "quarter_right_outside",
        "FS1": "quarter_left_inside",
        "SS1": "quarter_right_inside",
        "MLB1": "hook_middle",
        "OLB1": "curl_left",
        "OLB2": "curl_right",
    },
}


# =============================================================================
# Play Adapter
# =============================================================================

@dataclass
class PlayAdapter:
    """Adapter for converting playbook plays to V2 PlayConfig.

    Attributes:
        offense: List of offensive V2 Players (for ID lookup)
        defense: List of defensive V2 Players (for ID lookup)
    """

    offense: List["V2Player"]
    defense: List["V2Player"]

    def build_offensive_config(
        self,
        play_code: str,
        shotgun: bool = True,
    ) -> PlayConfig:
        """Build a PlayConfig for an offensive play.

        Args:
            play_code: PlayCode identifier (e.g., "PASS_SLANT", "RUN_POWER")
            shotgun: Whether QB is in shotgun (affects dropback)

        Returns:
            PlayConfig ready for orchestrator.setup_play()
        """
        play = get_play(play_code)
        if not play:
            # Default to a simple hitch if unknown
            play_code = "PASS_HITCH"

        # Check if run or pass
        if play_code.startswith("RUN_"):
            return self._build_run_config(play_code, shotgun)
        else:
            return self._build_pass_config(play_code, shotgun)

    def _build_pass_config(self, play_code: str, shotgun: bool) -> PlayConfig:
        """Build a pass play configuration."""
        # Get route assignments
        route_map = PLAY_ROUTE_MAP.get(play_code, {})

        # Map slot names to player IDs
        routes: Dict[str, str] = {}
        for slot, route_name in route_map.items():
            player = self._find_player_by_slot(self.offense, slot)
            if player and route_name != "block":
                routes[player.id] = route_name

        # Get dropback type
        dropback = PLAY_DROPBACK_MAP.get(play_code, DropbackType.STANDARD)
        if shotgun:
            dropback = DropbackType.SHOTGUN

        return PlayConfig(
            routes=routes,
            dropback_type=dropback,
            is_run_play=False,
            max_duration=8.0,
        )

    def _build_run_config(self, play_code: str, shotgun: bool) -> PlayConfig:
        """Build a run play configuration."""
        # Get run concept
        run_concept = PLAY_RUN_MAP.get(play_code, "inside_zone")

        # Determine run direction from concept
        run_direction = "inside_right"  # Default
        if "outside" in run_concept or "sweep" in run_concept:
            run_direction = "outside_right"

        # Find RB for ball carrier
        rb = self._find_player_by_slot(self.offense, "RB1")
        ball_carrier_id = rb.id if rb else None

        return PlayConfig(
            is_run_play=True,
            run_concept=run_concept,
            run_direction=run_direction,
            ball_carrier_id=ball_carrier_id,
            handoff_timing=0.6,
            dropback_type=DropbackType.SHOTGUN if shotgun else DropbackType.QUICK,
            max_duration=10.0,
        )

    def build_defensive_config(
        self,
        play_code: str,
    ) -> tuple[Dict[str, str], Dict[str, str]]:
        """Build coverage assignments for a defensive play.

        Args:
            play_code: Defensive PlayCode (e.g., "COVER_3", "MAN_PRESS")

        Returns:
            Tuple of (man_assignments, zone_assignments)
        """
        coverage_map = DEFENSE_COVERAGE_MAP.get(play_code, {})

        man_assignments: Dict[str, str] = {}
        zone_assignments: Dict[str, str] = {}

        for slot, assignment in coverage_map.items():
            defender = self._find_player_by_slot(self.defense, slot)
            if not defender:
                continue

            if assignment.startswith("man:"):
                # Man coverage - need to find target player
                target_slot = assignment.replace("man:", "")
                target = self._find_player_by_slot(self.offense, target_slot)
                if target:
                    man_assignments[defender.id] = target.id
            else:
                # Zone coverage
                zone_assignments[defender.id] = assignment

        return man_assignments, zone_assignments

    def _find_player_by_slot(
        self,
        players: List["V2Player"],
        slot: str,
    ) -> Optional["V2Player"]:
        """Find a player by their position slot (e.g., 'WR1', 'CB2')."""
        for player in players:
            if player.position_slot == slot:
                return player
        return None


# =============================================================================
# Convenience Function
# =============================================================================

def build_play_config(
    offense: List["V2Player"],
    defense: List["V2Player"],
    offensive_play: str,
    defensive_play: str = "COVER_3",
    shotgun: bool = True,
) -> PlayConfig:
    """Build a complete PlayConfig for a play matchup.

    Convenience function that creates adapter and builds config.

    Args:
        offense: Offensive V2 Players
        defense: Defensive V2 Players
        offensive_play: Offensive PlayCode
        defensive_play: Defensive PlayCode
        shotgun: Whether QB in shotgun

    Returns:
        PlayConfig with routes and coverage assignments
    """
    adapter = PlayAdapter(offense, defense)

    # Build offensive config
    config = adapter.build_offensive_config(offensive_play, shotgun)

    # Add defensive assignments
    man_assignments, zone_assignments = adapter.build_defensive_config(defensive_play)
    config.man_assignments = man_assignments
    config.zone_assignments = zone_assignments

    return config
