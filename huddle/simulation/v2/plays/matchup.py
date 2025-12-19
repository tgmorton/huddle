"""Matchup testing - run play concepts against defensive schemes.

Provides utilities to set up and run matchups between offensive
concepts and defensive coverages for testing and tuning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple

from .concepts import PlayConcept, ReceiverPosition, ReceiverAlignment, CONCEPT_LIBRARY
from .schemes import DefensiveScheme, DefenderPosition, SCHEME_LIBRARY
from .routes import RouteType, ROUTE_LIBRARY
from ..systems.coverage import CoverageType, ZoneType


@dataclass
class MatchupConfig:
    """Configuration for a play-vs-coverage matchup.

    This is the data structure needed to initialize the v2 simulation
    with a specific concept against a specific scheme.
    """
    # Concept info
    concept_name: str
    concept: PlayConcept

    # Scheme info
    scheme_name: str
    scheme: DefensiveScheme

    # Derived receiver configs (ready for simulation)
    receivers: List[Dict]  # [{position, x, y, route_type, ...}]

    # Derived defender configs (ready for simulation)
    defenders: List[Dict]  # [{position, x, y, coverage_type, zone_type, man_target, ...}]


def create_matchup(concept_name: str, scheme_name: str) -> Optional[MatchupConfig]:
    """Create a matchup configuration from concept and scheme names.

    Args:
        concept_name: Name of offensive concept (e.g., "four_verts")
        scheme_name: Name of defensive scheme (e.g., "cover_2")

    Returns:
        MatchupConfig ready for simulation, or None if not found
    """
    concept = CONCEPT_LIBRARY.get(concept_name.lower())
    scheme = SCHEME_LIBRARY.get(scheme_name.lower().replace(" ", "_"))

    if not concept or not scheme:
        return None

    # Build receiver configs
    receivers = []
    for i, (alignment, route_assign) in enumerate(zip(concept.alignments, concept.routes)):
        route_def = route_assign.get_route()
        receivers.append({
            "id": f"wr{i+1}",
            "name": f"{alignment.position.value.upper()}",
            "position": alignment.position.value,
            "x": alignment.x,
            "y": alignment.y,
            "route_type": route_assign.route_type.value,
            "route_name": route_def.name,
            "is_left_side": alignment.is_left_side,
            "read_order": route_assign.read_order,
            "hot_route": route_assign.hot_route,
        })

    # Build defender configs
    defenders = []
    for i, (alignment, assign) in enumerate(zip(scheme.alignments, scheme.assignments)):
        # Match defenders to receivers for man coverage
        man_target_id = None
        if assign.is_man and assign.receiver_key:
            man_target_id = _match_receiver_key(assign.receiver_key, receivers)

        defenders.append({
            "id": f"db{i+1}",
            "name": f"{alignment.position.value.upper()}",
            "position": alignment.position.value,
            "x": alignment.x,
            "y": alignment.y,
            "coverage_type": assign.coverage_type.value,
            "zone_type": assign.zone_type.value if assign.zone_type else None,
            "man_target_id": man_target_id,
            "technique": assign.technique,
        })

    return MatchupConfig(
        concept_name=concept_name,
        concept=concept,
        scheme_name=scheme_name,
        scheme=scheme,
        receivers=receivers,
        defenders=defenders,
    )


def _match_receiver_key(key: str, receivers: List[Dict]) -> Optional[str]:
    """Match a receiver key (like "#1_left") to an actual receiver ID."""
    key = key.lower()

    if key == "#1_left":
        # Leftmost receiver
        left_receivers = [r for r in receivers if r["x"] < 0]
        if left_receivers:
            leftmost = min(left_receivers, key=lambda r: r["x"])
            return leftmost["id"]

    elif key == "#1_right":
        # Rightmost receiver
        right_receivers = [r for r in receivers if r["x"] > 0]
        if right_receivers:
            rightmost = max(right_receivers, key=lambda r: r["x"])
            return rightmost["id"]

    elif key == "slot":
        # Slot receiver (closest to center, not on outside)
        slot_receivers = [r for r in receivers if -15 < r["x"] < 15]
        if slot_receivers:
            return min(slot_receivers, key=lambda r: abs(r["x"]))["id"]

    elif key == "te":
        # Tight end position
        for r in receivers:
            if r["position"] == "y":
                return r["id"]

    elif key == "rb":
        # Running back
        for r in receivers:
            if r["position"] == "rb":
                return r["id"]

    # Fallback: first receiver
    return receivers[0]["id"] if receivers else None


def list_matchups() -> List[Tuple[str, str]]:
    """List all possible concept vs scheme matchups."""
    matchups = []
    for concept_name in CONCEPT_LIBRARY:
        for scheme_name in SCHEME_LIBRARY:
            matchups.append((concept_name, scheme_name))
    return matchups


def get_favorable_matchups(concept_name: str) -> List[str]:
    """Get schemes that the concept is designed to beat."""
    concept = CONCEPT_LIBRARY.get(concept_name.lower())
    if not concept:
        return []

    favorable = []
    for scheme_name, scheme in SCHEME_LIBRARY.items():
        # Check if concept beats this scheme's weaknesses
        for beater in concept.coverage_beaters:
            if beater.lower() in scheme.scheme_type.value.lower():
                favorable.append(scheme_name)
                break
            # Also check weaknesses list
            for weakness in scheme.weaknesses:
                if beater.lower() in weakness.lower():
                    favorable.append(scheme_name)
                    break

    return list(set(favorable))


def get_unfavorable_matchups(concept_name: str) -> List[str]:
    """Get schemes that should stop the concept."""
    concept = CONCEPT_LIBRARY.get(concept_name.lower())
    if not concept:
        return []

    unfavorable = []
    for scheme_name, scheme in SCHEME_LIBRARY.items():
        # Check if scheme's strengths counter the concept
        for strength in scheme.strengths:
            if any(strength.lower() in beater.lower() for beater in concept.coverage_beaters):
                continue  # This is a favorable matchup
            # If scheme is strong against something the concept relies on
            # This is a simplistic check - would need more metadata

        # For now, just return schemes NOT in favorable list
        if scheme_name not in get_favorable_matchups(concept_name):
            unfavorable.append(scheme_name)

    return unfavorable


def describe_matchup(concept_name: str, scheme_name: str) -> str:
    """Get a description of a specific matchup."""
    config = create_matchup(concept_name, scheme_name)
    if not config:
        return f"Matchup not found: {concept_name} vs {scheme_name}"

    lines = [
        f"=== {config.concept.name} vs {config.scheme.name} ===",
        "",
        f"Timing: {config.concept.timing}",
        f"Concept beats: {', '.join(config.concept.coverage_beaters)}",
        f"Scheme weak to: {', '.join(config.scheme.weaknesses)}",
        "",
        "Receivers:",
    ]
    for r in config.receivers:
        lines.append(f"  {r['name']}: {r['route_name']} at ({r['x']:+.0f}, {r['y']:.0f})")

    lines.append("")
    lines.append("Defenders:")
    for d in config.defenders:
        if d['coverage_type'] == 'man':
            target = d['man_target_id'] or "?"
            lines.append(f"  {d['name']}: MAN on {target} at ({d['x']:+.0f}, {d['y']:.0f})")
        else:
            zone = d['zone_type'] or "none"
            lines.append(f"  {d['name']}: ZONE {zone} at ({d['x']:+.0f}, {d['y']:.0f})")

    # Predict outcome
    lines.append("")
    is_favorable = scheme_name in get_favorable_matchups(concept_name)
    if is_favorable:
        lines.append("PREDICTION: Favorable for offense (concept designed to beat this coverage)")
    else:
        lines.append("PREDICTION: Defensive advantage (coverage not in concept's beaters)")

    return "\n".join(lines)


# Quick test matchups for common scenarios
CLASSIC_MATCHUPS = [
    ("four_verts", "cover_2"),      # Classic Cover 2 beater
    ("mesh", "cover_1"),            # Mesh vs man
    ("flood", "cover_3"),           # Flood vs Cover 3
    ("smash", "cover_2"),           # Smash vs Cover 2
    ("stick", "cover_3"),           # Stick vs zone
    ("slant_flat", "cover_0"),      # Quick game vs blitz
    ("curl_flat", "cover_4"),       # Curl-flat vs quarters
    ("post_wheel", "cover_3"),      # Deep shot vs single high
]
