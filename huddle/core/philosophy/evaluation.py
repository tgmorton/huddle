"""
Philosophy-based player evaluation.

This module calculates team-specific OVR ratings based on each team's
positional philosophies. The same player may have vastly different
OVR ratings across teams based on what attributes each team values.

Inspired by NFL Head Coach 09's evaluation system.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
import random

from huddle.core.philosophy.positions import (
    QBPhilosophy,
    RBPhilosophy,
    WRPhilosophy,
    TEPhilosophy,
    OLPhilosophy,
    DLPhilosophy,
    LBPhilosophy,
    CBPhilosophy,
    FSPhilosophy,
    SSPhilosophy,
)

if TYPE_CHECKING:
    from huddle.core.attributes.registry import PlayerAttributes


# ============================================================================
# Philosophy -> Attribute Weight Mappings
# ============================================================================
# Each philosophy defines which attributes matter most (weights sum to ~1.0)
# Higher weight = more important for OVR calculation under this philosophy

PHILOSOPHY_ATTRIBUTE_WEIGHTS: dict[str, dict[str, float]] = {
    # ========== QB PHILOSOPHIES ==========
    QBPhilosophy.STRONG_ARM.value: {
        "throw_power": 0.35,
        "strength": 0.15,
        "elusiveness": 0.15,
        "throw_accuracy_deep": 0.20,
        "throw_accuracy_med": 0.15,
    },
    QBPhilosophy.PURE_PASSER.value: {
        "throw_power": 0.20,
        "throw_accuracy_short": 0.25,
        "throw_accuracy_med": 0.25,
        "throw_accuracy_deep": 0.15,
        "awareness": 0.15,
    },
    QBPhilosophy.FIELD_GENERAL.value: {
        "learning": 0.20,
        "awareness": 0.30,
        "throw_accuracy_short": 0.20,
        "throw_accuracy_med": 0.20,
        "play_action": 0.10,
    },
    QBPhilosophy.MOBILE.value: {
        "speed": 0.25,
        "acceleration": 0.20,
        "agility": 0.15,
        "elusiveness": 0.20,
        "throw_on_run": 0.20,
    },

    # ========== RB PHILOSOPHIES ==========
    RBPhilosophy.POWER.value: {
        "trucking": 0.30,
        "stiff_arm": 0.20,
        "break_tackle": 0.25,
        "strength": 0.15,
        "carrying": 0.10,
    },
    RBPhilosophy.RECEIVING.value: {
        "catching": 0.30,
        "awareness": 0.15,
        "carrying": 0.15,
        "catch_in_traffic": 0.20,
        "route_running": 0.20,
    },
    RBPhilosophy.MOVES.value: {
        "juke_move": 0.30,
        "spin_move": 0.25,
        "elusiveness": 0.30,
        "agility": 0.15,
    },
    RBPhilosophy.SPEED.value: {
        "speed": 0.35,
        "acceleration": 0.30,
        "agility": 0.20,
        "elusiveness": 0.15,
    },
    RBPhilosophy.WORKHORSE.value: {
        "stamina": 0.25,
        "toughness": 0.25,
        "injury": 0.20,
        "strength": 0.15,
        "carrying": 0.15,
    },

    # ========== WR PHILOSOPHIES ==========
    WRPhilosophy.STRONG.value: {
        "strength": 0.25,
        "catch_in_traffic": 0.30,
        "catching": 0.25,
        "break_tackle": 0.20,
    },
    WRPhilosophy.TALL.value: {
        "jumping": 0.30,
        "spectacular_catch": 0.30,
        "catch_in_traffic": 0.25,
        "catching": 0.15,
    },
    WRPhilosophy.QUICK.value: {
        "route_running": 0.35,
        "release": 0.25,
        "agility": 0.25,
        "catching": 0.15,
    },
    WRPhilosophy.SPEED.value: {
        "speed": 0.35,
        "acceleration": 0.25,
        "spectacular_catch": 0.20,
        "catching": 0.20,
    },

    # ========== TE PHILOSOPHIES ==========
    TEPhilosophy.SOFT_HANDS.value: {
        "catching": 0.35,
        "catch_in_traffic": 0.30,
        "route_running": 0.25,
        "awareness": 0.10,
    },
    TEPhilosophy.PLAYMAKER.value: {
        "speed": 0.25,
        "agility": 0.20,
        "catching": 0.25,
        "route_running": 0.20,
        "elusiveness": 0.10,
    },
    TEPhilosophy.BLOCKER.value: {
        "run_block": 0.35,
        "pass_block": 0.30,
        "strength": 0.25,
        "impact_blocking": 0.10,
    },

    # ========== OL PHILOSOPHIES ==========
    OLPhilosophy.ZONE_BLOCKING.value: {
        "agility": 0.25,
        "speed": 0.15,
        "run_block": 0.30,
        "awareness": 0.20,
        "stamina": 0.10,
    },
    OLPhilosophy.RUN_BLOCK.value: {
        "strength": 0.30,
        "run_block": 0.35,
        "impact_blocking": 0.20,
        "pass_block": 0.15,
    },
    OLPhilosophy.PASS_BLOCK.value: {
        "pass_block": 0.40,
        "awareness": 0.25,
        "strength": 0.20,
        "agility": 0.15,
    },

    # ========== DL PHILOSOPHIES ==========
    DLPhilosophy.ONE_GAP.value: {
        "finesse_moves": 0.30,
        "speed": 0.20,
        "acceleration": 0.20,
        "block_shedding": 0.20,
        "pursuit": 0.10,
    },
    DLPhilosophy.RUN_STOPPER.value: {
        "strength": 0.30,
        "block_shedding": 0.30,
        "tackle": 0.25,
        "power_moves": 0.15,
    },
    DLPhilosophy.VERSATILE.value: {
        "power_moves": 0.25,
        "finesse_moves": 0.25,
        "block_shedding": 0.25,
        "strength": 0.15,
        "tackle": 0.10,
    },

    # ========== LB PHILOSOPHIES ==========
    LBPhilosophy.COVERAGE.value: {
        "zone_coverage": 0.30,
        "man_coverage": 0.25,
        "speed": 0.25,
        "awareness": 0.20,
    },
    LBPhilosophy.RUN_STOPPER.value: {
        "tackle": 0.30,
        "block_shedding": 0.25,
        "strength": 0.20,
        "hit_power": 0.15,
        "pursuit": 0.10,
    },
    LBPhilosophy.BLITZER.value: {
        "pursuit": 0.25,
        "speed": 0.25,
        "finesse_moves": 0.20,
        "hit_power": 0.20,
        "acceleration": 0.10,
    },

    # ========== CB PHILOSOPHIES ==========
    CBPhilosophy.COVER_2.value: {
        "zone_coverage": 0.35,
        "speed": 0.25,
        "play_recognition": 0.20,
        "awareness": 0.20,
    },
    CBPhilosophy.MAN_COVERAGE.value: {
        "man_coverage": 0.35,
        "speed": 0.25,
        "agility": 0.20,
        "press": 0.20,
    },
    CBPhilosophy.PRESS_RUN_SUPPORT.value: {
        "press": 0.30,
        "tackle": 0.25,
        "strength": 0.20,
        "hit_power": 0.15,
        "man_coverage": 0.10,
    },

    # ========== FS PHILOSOPHIES ==========
    FSPhilosophy.CENTERFIELDER.value: {
        "zone_coverage": 0.35,
        "speed": 0.25,
        "play_recognition": 0.20,
        "awareness": 0.20,
    },
    FSPhilosophy.MAN_COVERAGE.value: {
        "man_coverage": 0.35,
        "speed": 0.30,
        "agility": 0.20,
        "tackle": 0.15,
    },
    FSPhilosophy.RUN_STOPPER.value: {
        "tackle": 0.30,
        "hit_power": 0.25,
        "strength": 0.20,
        "pursuit": 0.15,
        "speed": 0.10,
    },

    # ========== SS PHILOSOPHIES ==========
    SSPhilosophy.COVERAGE.value: {
        "zone_coverage": 0.30,
        "man_coverage": 0.25,
        "speed": 0.25,
        "awareness": 0.20,
    },
    SSPhilosophy.SMART_PRODUCTIVE.value: {
        "awareness": 0.25,
        "play_recognition": 0.25,
        "tackle": 0.20,
        "zone_coverage": 0.20,
        "speed": 0.10,
    },
    SSPhilosophy.BIG_HITTER.value: {
        "hit_power": 0.35,
        "tackle": 0.25,
        "strength": 0.20,
        "pursuit": 0.20,
    },
}


@dataclass
class TeamPhilosophies:
    """
    A team's complete set of positional philosophies.

    Determines how the team evaluates players at each position.
    """

    qb: QBPhilosophy = QBPhilosophy.PURE_PASSER
    rb: RBPhilosophy = RBPhilosophy.SPEED
    wr: WRPhilosophy = WRPhilosophy.SPEED
    te: TEPhilosophy = TEPhilosophy.SOFT_HANDS
    ol: OLPhilosophy = OLPhilosophy.PASS_BLOCK
    dl: DLPhilosophy = DLPhilosophy.VERSATILE
    lb: LBPhilosophy = LBPhilosophy.COVERAGE
    cb: CBPhilosophy = CBPhilosophy.MAN_COVERAGE
    fs: FSPhilosophy = FSPhilosophy.CENTERFIELDER
    ss: SSPhilosophy = SSPhilosophy.COVERAGE

    def get_philosophy_for_position(self, position: str) -> str:
        """Get the philosophy value string for a position."""
        pos_map = {
            "QB": self.qb.value,
            "RB": self.rb.value,
            "FB": self.rb.value,  # FBs evaluated as RBs
            "WR": self.wr.value,
            "TE": self.te.value,
            "LT": self.ol.value,
            "LG": self.ol.value,
            "C": self.ol.value,
            "RG": self.ol.value,
            "RT": self.ol.value,
            "DE": self.dl.value,
            "DT": self.dl.value,
            "NT": self.dl.value,
            "MLB": self.lb.value,
            "OLB": self.lb.value,
            "ILB": self.lb.value,
            "CB": self.cb.value,
            "FS": self.fs.value,
            "SS": self.ss.value,
        }
        return pos_map.get(position, "")

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "qb": self.qb.value,
            "rb": self.rb.value,
            "wr": self.wr.value,
            "te": self.te.value,
            "ol": self.ol.value,
            "dl": self.dl.value,
            "lb": self.lb.value,
            "cb": self.cb.value,
            "fs": self.fs.value,
            "ss": self.ss.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TeamPhilosophies":
        """Create from dictionary."""
        return cls(
            qb=QBPhilosophy(data.get("qb", "pure_passer")),
            rb=RBPhilosophy(data.get("rb", "speed")),
            wr=WRPhilosophy(data.get("wr", "speed")),
            te=TEPhilosophy(data.get("te", "soft_hands")),
            ol=OLPhilosophy(data.get("ol", "pass_block")),
            dl=DLPhilosophy(data.get("dl", "versatile")),
            lb=LBPhilosophy(data.get("lb", "coverage")),
            cb=CBPhilosophy(data.get("cb", "man_coverage")),
            fs=FSPhilosophy(data.get("fs", "centerfielder")),
            ss=SSPhilosophy(data.get("ss", "coverage")),
        )

    @classmethod
    def generate_random(cls) -> "TeamPhilosophies":
        """Generate random philosophies for a team."""
        return cls(
            qb=random.choice(list(QBPhilosophy)),
            rb=random.choice(list(RBPhilosophy)),
            wr=random.choice(list(WRPhilosophy)),
            te=random.choice(list(TEPhilosophy)),
            ol=random.choice(list(OLPhilosophy)),
            dl=random.choice(list(DLPhilosophy)),
            lb=random.choice(list(LBPhilosophy)),
            cb=random.choice(list(CBPhilosophy)),
            fs=random.choice(list(FSPhilosophy)),
            ss=random.choice(list(SSPhilosophy)),
        )


def get_philosophy_weights(philosophy: str) -> dict[str, float]:
    """
    Get the attribute weights for a philosophy.

    Args:
        philosophy: The philosophy value string (e.g., "strong_arm", "power")

    Returns:
        Dictionary mapping attribute names to weights (0.0-1.0)
    """
    return PHILOSOPHY_ATTRIBUTE_WEIGHTS.get(philosophy, {})


def calculate_philosophy_overall(
    attributes: "PlayerAttributes",
    position: str,
    philosophies: TeamPhilosophies,
) -> int:
    """
    Calculate a player's OVR according to a team's philosophy.

    This is the core function for team-specific player evaluation.
    The same player will have different OVR values for different teams
    based on what attributes each team's philosophy emphasizes.

    Args:
        attributes: The player's attribute values
        position: The player's position (e.g., "QB", "RB", "WR")
        philosophies: The team's positional philosophies

    Returns:
        Overall rating (0-99) according to this team's evaluation
    """
    philosophy = philosophies.get_philosophy_for_position(position)
    weights = get_philosophy_weights(philosophy)

    if not weights:
        # Fallback to generic position-based calculation
        return attributes.calculate_overall(position)

    total_weight = 0.0
    weighted_sum = 0.0

    for attr_name, weight in weights.items():
        value = attributes.get(attr_name, 50)
        weighted_sum += value * weight
        total_weight += weight

    if total_weight == 0:
        return 50

    return int(weighted_sum / total_weight)


def calculate_philosophy_difference(
    attributes: "PlayerAttributes",
    position: str,
    team_philosophies: TeamPhilosophies,
) -> int:
    """
    Calculate how much a team's philosophy affects their view of a player.

    Positive = team values player MORE than generic OVR
    Negative = team values player LESS than generic OVR

    Useful for showing "scheme fit" bonuses/penalties.

    Args:
        attributes: The player's attribute values
        position: The player's position
        team_philosophies: The team's positional philosophies

    Returns:
        Difference between team OVR and generic OVR (-50 to +50 range typical)
    """
    generic_ovr = attributes.calculate_overall(position)
    team_ovr = calculate_philosophy_overall(attributes, position, team_philosophies)
    return team_ovr - generic_ovr


def get_scheme_fit_label(difference: int) -> str:
    """
    Get a human-readable label for scheme fit.

    Args:
        difference: Result from calculate_philosophy_difference()

    Returns:
        Scheme fit label string
    """
    if difference >= 8:
        return "Perfect Fit"
    elif difference >= 4:
        return "Great Fit"
    elif difference >= 1:
        return "Good Fit"
    elif difference >= -2:
        return "Average Fit"
    elif difference >= -5:
        return "Poor Fit"
    else:
        return "Scheme Mismatch"


def calculate_scheme_fit_overall(
    player,
    offensive_scheme=None,
    defensive_scheme=None,
) -> int:
    """
    Calculate a player's OVR adjusted for scheme fit (HC09-style).

    This is the main function for AI draft/trade evaluation. It uses the
    player's archetype and the team's scheme to determine fit bonuses/penalties.

    A Power RB might be 88 OVR to their archetype weights, but:
    - +5 OVR to a Power Run team (perfect fit)
    - -3 OVR to a Zone Run team (scheme mismatch)

    Args:
        player: The Player object with player_archetype set
        offensive_scheme: Optional OffensiveScheme enum value
        defensive_scheme: Optional DefensiveScheme enum value

    Returns:
        Scheme-adjusted OVR rating
    """
    from huddle.core.models.team_identity import (
        OFFENSIVE_SCHEME_ARCHETYPE_PREFERENCES,
        DEFENSIVE_SCHEME_ARCHETYPE_PREFERENCES,
    )

    # Start with the player's archetype-based OVR
    base_ovr = player.archetype_overall

    if not player.player_archetype:
        return base_ovr

    position = player.position.value
    archetype = player.player_archetype

    # Determine which scheme preferences to check based on position
    is_offensive = position in ["QB", "RB", "FB", "WR", "TE", "LT", "LG", "C", "RG", "RT"]
    is_defensive = position in ["DE", "DT", "NT", "MLB", "ILB", "OLB", "CB", "FS", "SS"]

    # Normalize position groups for lookup
    # OL positions all map to "OL" in the preferences
    position_lookup = position
    if position in ["LT", "LG", "C", "RG", "RT"]:
        position_lookup = "OL"
    elif position in ["DE", "DT", "NT"]:
        position_lookup = "DL"
    elif position in ["MLB", "ILB", "OLB"]:
        position_lookup = "LB"

    scheme_bonus = 0

    # Check offensive scheme fit
    if is_offensive and offensive_scheme:
        prefs = OFFENSIVE_SCHEME_ARCHETYPE_PREFERENCES.get(offensive_scheme, {})
        preferred_archetypes = prefs.get(position_lookup, [])

        if archetype in preferred_archetypes:
            # Perfect fit - bonus based on position in preference list
            # First preference = +5, second = +3
            idx = preferred_archetypes.index(archetype)
            scheme_bonus = 5 - (idx * 2)
            scheme_bonus = max(scheme_bonus, 2)  # Minimum +2 for any match
        elif preferred_archetypes:
            # Scheme has preferences but player doesn't match
            scheme_bonus = -3

    # Check defensive scheme fit
    if is_defensive and defensive_scheme:
        prefs = DEFENSIVE_SCHEME_ARCHETYPE_PREFERENCES.get(defensive_scheme, {})
        preferred_archetypes = prefs.get(position_lookup, [])

        if archetype in preferred_archetypes:
            idx = preferred_archetypes.index(archetype)
            scheme_bonus = 5 - (idx * 2)
            scheme_bonus = max(scheme_bonus, 2)
        elif preferred_archetypes:
            scheme_bonus = -3

    # Apply bonus and clamp to valid range
    adjusted_ovr = base_ovr + scheme_bonus
    return max(40, min(99, adjusted_ovr))


def get_scheme_fit_bonus(
    player,
    offensive_scheme=None,
    defensive_scheme=None,
) -> int:
    """
    Get just the scheme fit bonus/penalty without the full OVR.

    Useful for displaying scheme fit information to the user.

    Args:
        player: The Player object
        offensive_scheme: Optional OffensiveScheme enum value
        defensive_scheme: Optional DefensiveScheme enum value

    Returns:
        Scheme fit bonus (-3 to +5 typically)
    """
    base_ovr = player.archetype_overall
    scheme_ovr = calculate_scheme_fit_overall(player, offensive_scheme, defensive_scheme)
    return scheme_ovr - base_ovr
