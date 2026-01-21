"""Complete NFL Playbook Catalogue.

Comprehensive catalogue of pass concepts, routes, and run plays
organized by category with full descriptions, route combinations,
coverage beaters, and read progressions.

This builds on the existing routes.py and concepts.py but provides
a complete catalogue suitable for a full playbook implementation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Optional, Any
from pathlib import Path


# =============================================================================
# Route Tree (Standard 0-9 numbering)
# =============================================================================

ROUTE_TREE = {
    0: {
        "name": "Hitch",
        "depth": 5,
        "direction": "stop",
        "description": "Run 5 yards, stop and turn back to QB",
        "timing": "quick",
        "settles": True,
    },
    1: {
        "name": "Flat",
        "depth": 2,
        "direction": "outside",
        "description": "Release to the flat area, stay shallow",
        "timing": "quick",
        "settles": True,
    },
    2: {
        "name": "Slant",
        "depth": 5,
        "direction": "inside",
        "description": "3-step release, break sharply inside at 45 degrees",
        "timing": "quick",
        "settles": False,
    },
    3: {
        "name": "Comeback",
        "depth": 15,
        "direction": "outside",
        "description": "Push vertical 15 yards, plant and come back to sideline",
        "timing": "deep",
        "settles": True,
    },
    4: {
        "name": "Curl",
        "depth": 12,
        "direction": "inside",
        "description": "Push vertical 12 yards, curl back inside toward QB",
        "timing": "intermediate",
        "settles": True,
    },
    5: {
        "name": "Out",
        "depth": 12,
        "direction": "outside",
        "description": "Push vertical 12 yards, break hard to sideline",
        "timing": "intermediate",
        "settles": False,
    },
    6: {
        "name": "Dig/In",
        "depth": 12,
        "direction": "inside",
        "description": "Push vertical 12 yards, break sharply inside across field",
        "timing": "intermediate",
        "settles": False,
    },
    7: {
        "name": "Corner",
        "depth": 15,
        "direction": "outside",
        "description": "Push vertical 12 yards, break to corner/pylon at 45 degrees",
        "timing": "deep",
        "settles": False,
    },
    8: {
        "name": "Post",
        "depth": 15,
        "direction": "inside",
        "description": "Push vertical 12 yards, break inside toward goalpost at 45 degrees",
        "timing": "deep",
        "settles": False,
    },
    9: {
        "name": "Go/Fade",
        "depth": 30,
        "direction": "vertical",
        "description": "Straight vertical route, beat defender deep",
        "timing": "deep",
        "settles": False,
    },
}

# Additional routes not in the standard tree
ADDITIONAL_ROUTES = {
    "drag": {
        "name": "Drag",
        "depth": 3,
        "direction": "inside",
        "description": "Shallow crossing route at 3-5 yards, run across formation",
        "timing": "quick",
        "settles": False,
    },
    "seam": {
        "name": "Seam",
        "depth": 20,
        "direction": "vertical",
        "description": "Vertical route up the hash marks, split the safeties",
        "timing": "deep",
        "settles": False,
    },
    "wheel": {
        "name": "Wheel",
        "depth": 20,
        "direction": "outside",
        "description": "Release to flat, then turn upfield along sideline",
        "timing": "deep",
        "settles": False,
    },
    "angle": {
        "name": "Angle",
        "depth": 6,
        "direction": "inside",
        "description": "Release outside, then break back inside at angle",
        "timing": "quick",
        "settles": False,
    },
    "whip": {
        "name": "Whip",
        "depth": 6,
        "direction": "outside",
        "description": "Release inside, whip back outside quickly",
        "timing": "quick",
        "settles": False,
    },
    "pivot": {
        "name": "Pivot",
        "depth": 5,
        "direction": "outside",
        "description": "Short out route, pivot back inside",
        "timing": "quick",
        "settles": True,
    },
    "stick": {
        "name": "Stick",
        "depth": 6,
        "direction": "inside",
        "description": "6-yard hitch settling in zone hole, like a short curl",
        "timing": "quick",
        "settles": True,
    },
    "sail": {
        "name": "Sail",
        "depth": 18,
        "direction": "outside",
        "description": "Deep out route, pushing to 18 yards before breaking out",
        "timing": "deep",
        "settles": False,
    },
    "over": {
        "name": "Over",
        "depth": 15,
        "direction": "inside",
        "description": "Deep crossing route at 15 yards, run all the way across",
        "timing": "intermediate",
        "settles": False,
    },
    "under": {
        "name": "Under",
        "depth": 8,
        "direction": "inside",
        "description": "Medium crossing route at 8 yards, underneath coverage",
        "timing": "intermediate",
        "settles": False,
    },
    "option": {
        "name": "Option",
        "depth": 8,
        "direction": "varies",
        "description": "Read coverage, break inside vs man or sit vs zone",
        "timing": "intermediate",
        "settles": True,
    },
    "sluggo": {
        "name": "Sluggo",
        "depth": 20,
        "direction": "vertical",
        "description": "Fake slant, then go vertical (slant-and-go)",
        "timing": "deep",
        "settles": False,
    },
    "post_corner": {
        "name": "Post-Corner",
        "depth": 22,
        "direction": "outside",
        "description": "Fake post break, then break to corner",
        "timing": "deep",
        "settles": False,
    },
    "out_and_up": {
        "name": "Out-and-Up",
        "depth": 22,
        "direction": "vertical",
        "description": "Fake out route, then go vertical",
        "timing": "deep",
        "settles": False,
    },
    "bubble": {
        "name": "Bubble",
        "depth": 0,
        "direction": "outside",
        "description": "Immediate bubble behind LOS toward sideline",
        "timing": "quick",
        "settles": False,
    },
    "quick_out": {
        "name": "Quick Out",
        "depth": 3,
        "direction": "outside",
        "description": "3-step out route, immediate break to sideline",
        "timing": "quick",
        "settles": False,
    },
    "speed_out": {
        "name": "Speed Out",
        "depth": 5,
        "direction": "outside",
        "description": "Fast 5-yard out, get to sideline quickly",
        "timing": "quick",
        "settles": False,
    },
    "texas": {
        "name": "Texas",
        "depth": 8,
        "direction": "outside",
        "description": "RB angle route - release inside, break to flat",
        "timing": "intermediate",
        "settles": False,
    },
    "arrow": {
        "name": "Arrow",
        "depth": 3,
        "direction": "outside",
        "description": "RB immediate release to flat at 45-degree angle",
        "timing": "quick",
        "settles": False,
    },
    "swing": {
        "name": "Swing",
        "depth": 2,
        "direction": "outside",
        "description": "RB swing to flat, get width before depth",
        "timing": "quick",
        "settles": False,
    },
    "screen": {
        "name": "Screen",
        "depth": -2,
        "direction": "varies",
        "description": "Let rushers by, receive ball behind LOS with blockers",
        "timing": "delayed",
        "settles": True,
    },
}


# =============================================================================
# Pass Concept Definitions
# =============================================================================

@dataclass
class RouteCombination:
    """A receiver's route in a concept."""
    position: str  # X, Z, Slot, TE, RB
    route: str  # Route name
    read_order: int  # 1 = first read
    hot: bool = False  # Hot route vs blitz
    notes: str = ""


@dataclass
class PassConcept:
    """A complete pass concept."""
    name: str
    category: str  # quick, dropback, deep, play_action, screen, rpo
    description: str
    routes: List[RouteCombination]
    coverage_beaters: List[str]  # cover_0, cover_1, cover_2, cover_3, cover_4, man, zone
    timing: str  # quick (1-3 step), intermediate (5 step), deep (7 step)
    key_read: str  # What defender to read
    formation_fit: List[str]  # What formations work well

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "routes": [
                {
                    "position": r.position,
                    "route": r.route,
                    "read_order": r.read_order,
                    "hot": r.hot,
                    "notes": r.notes,
                }
                for r in self.routes
            ],
            "coverage_beaters": self.coverage_beaters,
            "timing": self.timing,
            "key_read": self.key_read,
            "formation_fit": self.formation_fit,
        }


# =============================================================================
# Quick Game Concepts (1-3 step drop)
# =============================================================================

QUICK_GAME_CONCEPTS = [
    PassConcept(
        name="Slant-Flat",
        category="quick",
        description="Horizontal stretch on flat defender. If he widens to flat, throw slant. "
                    "If he jumps slant, throw flat. Simple 2-man read.",
        routes=[
            RouteCombination("X", "go", 4, notes="Clear out"),
            RouteCombination("Slot_L", "slant", 1, hot=True, notes="Primary vs man"),
            RouteCombination("Slot_R", "flat", 2, hot=True, notes="Primary vs zone"),
            RouteCombination("Z", "go", 4, notes="Clear out"),
        ],
        coverage_beaters=["cover_3", "cover_2", "man"],
        timing="quick",
        key_read="Flat defender (nickel/OLB)",
        formation_fit=["shotgun", "spread", "trips"],
    ),
    PassConcept(
        name="Stick",
        category="quick",
        description="3-level quick read. Stick route at 6 yards settles in zone hole. "
                    "Flat underneath, corner deep. Read flat defender high to low.",
        routes=[
            RouteCombination("X", "corner", 3, notes="Deep shot if single high"),
            RouteCombination("Slot_L", "stick", 1, notes="Settle in zone hole"),
            RouteCombination("Slot_R", "flat", 2, hot=True, notes="Check down"),
            RouteCombination("Z", "go", 4, notes="Clear out"),
        ],
        coverage_beaters=["cover_3", "cover_2", "zone"],
        timing="quick",
        key_read="Flat defender - if he squats on stick, throw flat",
        formation_fit=["shotgun", "trips", "spread"],
    ),
    PassConcept(
        name="Quick Out",
        category="quick",
        description="Fast 3-step out to the sideline. Good vs soft coverage. "
                    "Must throw with anticipation before break.",
        routes=[
            RouteCombination("X", "quick_out", 1, notes="Throw before break"),
            RouteCombination("Slot_L", "slant", 2, hot=True, notes="Hot vs blitz"),
            RouteCombination("Z", "hitch", 3, notes="Backside option"),
        ],
        coverage_beaters=["cover_3", "soft_zone"],
        timing="quick",
        key_read="Corner alignment - only throw if off coverage",
        formation_fit=["shotgun", "spread", "twins"],
    ),
    PassConcept(
        name="Hitch-Seam",
        category="quick",
        description="Outside hitches with seam route up the middle. "
                    "Attacks cover 2 hole between safety and corner.",
        routes=[
            RouteCombination("X", "hitch", 2, notes="Sit at 5 yards"),
            RouteCombination("Slot_L", "seam", 1, notes="Split safeties"),
            RouteCombination("Slot_R", "seam", 1, notes="Split safeties"),
            RouteCombination("Z", "hitch", 2, notes="Sit at 5 yards"),
        ],
        coverage_beaters=["cover_2", "cover_4"],
        timing="quick",
        key_read="Safety depth and leverage",
        formation_fit=["shotgun", "spread"],
    ),
    PassConcept(
        name="Double Slants",
        category="quick",
        description="Two slants from same side. First slant clears, second sits behind. "
                    "Excellent vs man coverage.",
        routes=[
            RouteCombination("X", "slant", 1, hot=True, notes="Get inside leverage"),
            RouteCombination("Slot_L", "slant", 2, notes="Trail behind X"),
            RouteCombination("Z", "go", 3, notes="Clear out safety"),
        ],
        coverage_beaters=["man", "cover_1", "cover_0"],
        timing="quick",
        key_read="LB depth - throw over or under",
        formation_fit=["shotgun", "trips", "bunch"],
    ),
    PassConcept(
        name="Snag",
        category="quick",
        description="Triangle concept with corner, stick/snag, and flat. "
                    "Creates 3-on-2 to one side of field.",
        routes=[
            RouteCombination("X", "corner", 1, notes="Deep option vs single high"),
            RouteCombination("Slot_L", "stick", 2, notes="Settle in zone hole"),
            RouteCombination("TE", "flat", 3, notes="Under the LB"),
            RouteCombination("Z", "go", 4, notes="Clear out backside"),
        ],
        coverage_beaters=["cover_3", "cover_2", "zone"],
        timing="quick",
        key_read="Corner - high/low read on flat defender",
        formation_fit=["shotgun", "trips", "bunch"],
    ),
    PassConcept(
        name="Bubble Screen",
        category="quick",
        description="Immediate bubble to slot receiver. Blockers in front. "
                    "Numbers game in space.",
        routes=[
            RouteCombination("X", "block", 99, notes="Stalk block corner"),
            RouteCombination("Slot_L", "bubble", 1, hot=True, notes="Catch and run"),
            RouteCombination("Z", "block", 99, notes="Block backside"),
        ],
        coverage_beaters=["zone", "soft_coverage"],
        timing="quick",
        key_read="Box count - need numbers advantage",
        formation_fit=["shotgun", "spread", "trips"],
    ),
    PassConcept(
        name="Now Screen",
        category="quick",
        description="WR screen to outside receiver. OL releases to block. "
                    "Quick hitter to get playmaker in space.",
        routes=[
            RouteCombination("X", "screen", 1, notes="Catch behind LOS"),
            RouteCombination("Slot_L", "block", 99, notes="Block corner"),
            RouteCombination("Z", "go", 3, notes="Clear out or block"),
        ],
        coverage_beaters=["aggressive_man", "blitz"],
        timing="quick",
        key_read="DE - need to get ball out before pressure",
        formation_fit=["shotgun", "spread"],
    ),
]

# =============================================================================
# Dropback Concepts (5-step drop)
# =============================================================================

DROPBACK_CONCEPTS = [
    PassConcept(
        name="Mesh",
        category="dropback",
        description="Two receivers cross at 5-6 yards going opposite directions. "
                    "Creates natural picks vs man coverage. Devastating vs man.",
        routes=[
            RouteCombination("X", "corner", 3, notes="Clear out, deep option"),
            RouteCombination("Slot_L", "drag", 1, hot=True, notes="Cross left to right"),
            RouteCombination("Slot_R", "drag", 2, hot=True, notes="Cross right to left"),
            RouteCombination("Z", "corner", 3, notes="Clear out, deep option"),
        ],
        coverage_beaters=["man", "cover_1", "cover_0"],
        timing="intermediate",
        key_read="LB level - throw to open crosser",
        formation_fit=["shotgun", "spread", "empty"],
    ),
    PassConcept(
        name="Smash",
        category="dropback",
        description="High-low on the corner. Outside hitch, inside corner route. "
                    "Classic cover 2 beater - attacks the hole.",
        routes=[
            RouteCombination("X", "hitch", 2, notes="Sit at 5, draw corner down"),
            RouteCombination("Slot_L", "corner", 1, notes="Over the top of hitch"),
            RouteCombination("Slot_R", "corner", 1, notes="Over the top"),
            RouteCombination("Z", "hitch", 2, notes="Draw corner down"),
        ],
        coverage_beaters=["cover_2", "cover_4"],
        timing="intermediate",
        key_read="Corner - if sits on hitch, throw corner. If bails, throw hitch.",
        formation_fit=["shotgun", "spread", "twins"],
    ),
    PassConcept(
        name="Curl-Flat",
        category="dropback",
        description="Outside curl at 12 yards, inside flat. Horizontal stretch "
                    "on flat defender, deeper developing than slant-flat.",
        routes=[
            RouteCombination("X", "curl", 1, notes="Find soft spot in zone"),
            RouteCombination("Slot_L", "flat", 2, notes="Stretch underneath"),
            RouteCombination("Slot_R", "flat", 2, notes="Stretch underneath"),
            RouteCombination("Z", "curl", 1, notes="Find soft spot"),
        ],
        coverage_beaters=["cover_3", "zone"],
        timing="intermediate",
        key_read="Flat defender - same as slant-flat but deeper",
        formation_fit=["shotgun", "spread", "pro"],
    ),
    PassConcept(
        name="Flood",
        category="dropback",
        description="3 receivers to one side at different depths - flat, out, corner. "
                    "Overloads zone with 3 vs 2.",
        routes=[
            RouteCombination("X", "post", 4, notes="Backside clear out"),
            RouteCombination("Slot_R", "flat", 3, hot=True, notes="Low option"),
            RouteCombination("Z", "out", 2, notes="Middle level"),
            RouteCombination("TE", "corner", 1, notes="High option"),
        ],
        coverage_beaters=["cover_3", "cover_1", "zone"],
        timing="intermediate",
        key_read="Safety rotation - read high to low",
        formation_fit=["trips", "shotgun"],
    ),
    PassConcept(
        name="Drive",
        category="dropback",
        description="Dig route at 12-15 yards with drag underneath. Vertical stretch "
                    "on hook defenders. High-low read.",
        routes=[
            RouteCombination("X", "dig", 1, notes="Find window at 12-15"),
            RouteCombination("Slot_L", "drag", 2, hot=True, notes="Shallow cross"),
            RouteCombination("Slot_R", "flat", 3, notes="Check down"),
            RouteCombination("Z", "curl", 4, notes="Backside option"),
        ],
        coverage_beaters=["cover_2", "cover_3", "zone"],
        timing="intermediate",
        key_read="Hook/curl defender - if he drops, throw drag. If he sits, throw dig.",
        formation_fit=["shotgun", "spread", "trips"],
    ),
    PassConcept(
        name="Levels",
        category="dropback",
        description="Dig route with two shorter in-routes at different depths. "
                    "Creates horizontal and vertical stress.",
        routes=[
            RouteCombination("X", "dig", 1, notes="Deepest crosser at 15"),
            RouteCombination("Slot_L", "under", 2, notes="Medium crosser at 8"),
            RouteCombination("Slot_R", "drag", 3, notes="Shallow at 3-5"),
            RouteCombination("Z", "go", 4, notes="Clear out"),
        ],
        coverage_beaters=["zone", "cover_3", "cover_2"],
        timing="intermediate",
        key_read="Work high to low - find open level",
        formation_fit=["shotgun", "spread", "trips"],
    ),
    PassConcept(
        name="Shallow Cross",
        category="dropback",
        description="Shallow crossing route from one side, dig from opposite. "
                    "Hi-lo on zone defenders with crossers going opposite directions.",
        routes=[
            RouteCombination("X", "dig", 1, notes="Deep crosser"),
            RouteCombination("Slot_L", "drag", 2, hot=True, notes="Shallow crosser opposite"),
            RouteCombination("Z", "go", 3, notes="Clear out safety"),
            RouteCombination("RB", "flat", 4, notes="Check down"),
        ],
        coverage_beaters=["zone", "cover_3", "cover_4"],
        timing="intermediate",
        key_read="Middle linebacker - which level opens",
        formation_fit=["shotgun", "spread"],
    ),
    PassConcept(
        name="Spacing",
        category="dropback",
        description="5 receivers at same depth (~5 yards) spread horizontally. "
                    "Impossible math for zone - more receivers than defenders.",
        routes=[
            RouteCombination("X", "hitch", 2, notes="Far left"),
            RouteCombination("Slot_L", "hitch", 1, notes="Left slot"),
            RouteCombination("TE", "hitch", 1, notes="Center"),
            RouteCombination("Slot_R", "hitch", 1, notes="Right slot"),
            RouteCombination("Z", "hitch", 2, notes="Far right"),
        ],
        coverage_beaters=["zone", "cover_2", "cover_3"],
        timing="intermediate",
        key_read="Find the void - throw to open grass",
        formation_fit=["empty", "spread"],
    ),
    PassConcept(
        name="Y-Cross",
        category="dropback",
        description="TE runs deep cross at 15 yards. Outside receivers clear out. "
                    "Gets athletic TE matched on linebacker.",
        routes=[
            RouteCombination("X", "go", 3, notes="Clear out"),
            RouteCombination("TE", "over", 1, notes="Deep cross at 15"),
            RouteCombination("Slot_R", "drag", 2, hot=True, notes="Shallow option"),
            RouteCombination("Z", "go", 3, notes="Clear out"),
        ],
        coverage_beaters=["man", "cover_1", "cover_3"],
        timing="intermediate",
        key_read="Safety help - throw away from help",
        formation_fit=["shotgun", "12_personnel", "spread"],
    ),
    PassConcept(
        name="Dagger",
        category="dropback",
        description="Slot runs seam/go, outside runs dig behind it. Seam clears "
                    "the safety, dig comes open underneath.",
        routes=[
            RouteCombination("X", "dig", 1, notes="Primary - behind seam"),
            RouteCombination("Slot_L", "seam", 2, notes="Clear out safety"),
            RouteCombination("Slot_R", "drag", 3, notes="Under option"),
            RouteCombination("Z", "curl", 4, notes="Backside"),
        ],
        coverage_beaters=["cover_3", "cover_1", "single_high"],
        timing="intermediate",
        key_read="Safety - if bites on seam, throw dig",
        formation_fit=["shotgun", "spread", "trips"],
    ),
    PassConcept(
        name="China",
        category="dropback",
        description="TE runs angle route (out then in), RB runs wheel. "
                    "Creates traffic and matchup problems.",
        routes=[
            RouteCombination("X", "go", 3, notes="Clear out"),
            RouteCombination("TE", "angle", 1, notes="Out-and-in at 6 yards"),
            RouteCombination("RB", "wheel", 2, notes="Swing then vertical"),
            RouteCombination("Z", "dig", 4, notes="Backside option"),
        ],
        coverage_beaters=["man", "cover_1", "cover_3"],
        timing="intermediate",
        key_read="LB covering RB - wheel beats inside leverage",
        formation_fit=["shotgun", "11_personnel", "12_personnel"],
    ),
    PassConcept(
        name="Scissors",
        category="dropback",
        description="Inside receiver runs corner, outside runs post. Routes cross, "
                    "creating confusion for defenders.",
        routes=[
            RouteCombination("X", "post", 1, notes="Inside break"),
            RouteCombination("Slot_L", "corner", 2, notes="Outside break"),
            RouteCombination("Z", "curl", 3, notes="Backside option"),
            RouteCombination("RB", "flat", 4, notes="Check down"),
        ],
        coverage_beaters=["cover_2", "cover_4", "man"],
        timing="intermediate",
        key_read="Safety leverage - throw away from help",
        formation_fit=["shotgun", "spread", "twins"],
    ),
    PassConcept(
        name="Sail",
        category="dropback",
        description="Deep out at 18 yards with go and flat. 3-level stretch "
                    "to the sideline, stresses corner.",
        routes=[
            RouteCombination("X", "go", 2, notes="Clear out deep"),
            RouteCombination("Slot_L", "sail", 1, notes="Deep out at 18"),
            RouteCombination("RB", "flat", 3, notes="Underneath"),
            RouteCombination("Z", "dig", 4, notes="Backside option"),
        ],
        coverage_beaters=["cover_3", "zone"],
        timing="intermediate",
        key_read="Corner - 3-level read high to low",
        formation_fit=["shotgun", "trips", "spread"],
    ),
]

# =============================================================================
# Deep Shot Concepts (7-step drop)
# =============================================================================

DEEP_CONCEPTS = [
    PassConcept(
        name="Four Verts",
        category="deep",
        description="4 receivers run vertical routes. Slots split safeties. "
                    "Classic cover 2 beater - forces safety to choose.",
        routes=[
            RouteCombination("X", "go", 2, notes="Outside release"),
            RouteCombination("Slot_L", "seam", 1, notes="Split safeties"),
            RouteCombination("Slot_R", "seam", 1, notes="Split safeties"),
            RouteCombination("Z", "go", 2, notes="Outside release"),
        ],
        coverage_beaters=["cover_2", "cover_4"],
        timing="deep",
        key_read="Safeties - throw away from help",
        formation_fit=["shotgun", "spread", "empty"],
    ),
    PassConcept(
        name="Post-Wheel",
        category="deep",
        description="Deep post with wheel from backfield. Single-high safety must "
                    "choose which to help on.",
        routes=[
            RouteCombination("X", "post", 1, notes="Attack middle"),
            RouteCombination("Slot_L", "drag", 3, notes="Underneath option"),
            RouteCombination("RB", "wheel", 2, notes="Late developing deep"),
            RouteCombination("Z", "go", 4, notes="Clear out"),
        ],
        coverage_beaters=["cover_3", "cover_1", "single_high"],
        timing="deep",
        key_read="Free safety - throw opposite his movement",
        formation_fit=["shotgun", "11_personnel"],
    ),
    PassConcept(
        name="Mills/Anchor",
        category="deep",
        description="Outside runs post, slot runs dig underneath. Safety bites on "
                    "dig, post comes open behind.",
        routes=[
            RouteCombination("X", "post", 1, notes="Behind the dig"),
            RouteCombination("Slot_L", "dig", 2, notes="Hold safety"),
            RouteCombination("Slot_R", "drag", 3, notes="Underneath"),
            RouteCombination("Z", "go", 4, notes="Clear out"),
        ],
        coverage_beaters=["cover_3", "cover_1", "single_high"],
        timing="deep",
        key_read="Safety - if bites on dig, throw post",
        formation_fit=["shotgun", "spread", "trips"],
    ),
    PassConcept(
        name="Double Post",
        category="deep",
        description="Two posts from different releases. Creates traffic in middle "
                    "of field, hard to defend with single high.",
        routes=[
            RouteCombination("X", "post", 1, notes="Primary"),
            RouteCombination("Slot_L", "post", 2, notes="Secondary - different angle"),
            RouteCombination("Z", "curl", 3, notes="Backside option"),
            RouteCombination("RB", "flat", 4, notes="Check down"),
        ],
        coverage_beaters=["cover_1", "cover_3", "single_high"],
        timing="deep",
        key_read="Safety can't help both - throw open post",
        formation_fit=["shotgun", "spread"],
    ),
    PassConcept(
        name="Post-Corner",
        category="deep",
        description="Outside runs corner, inside runs post. High-low on safety. "
                    "Puts safety in impossible conflict.",
        routes=[
            RouteCombination("X", "corner", 1, notes="Outside deep shot"),
            RouteCombination("Slot_L", "post", 2, notes="Inside deep shot"),
            RouteCombination("Z", "dig", 3, notes="Intermediate option"),
            RouteCombination("RB", "flat", 4, notes="Check down"),
        ],
        coverage_beaters=["cover_2", "cover_3"],
        timing="deep",
        key_read="Safety rotation - throw opposite",
        formation_fit=["shotgun", "spread", "twins"],
    ),
    PassConcept(
        name="Slot Fade",
        category="deep",
        description="Slot receiver runs fade with outside release. Gets speed "
                    "player on LB or safety mismatch.",
        routes=[
            RouteCombination("X", "dig", 2, notes="Intermediate option"),
            RouteCombination("Slot_L", "go", 1, notes="Fade with outside release"),
            RouteCombination("Z", "curl", 3, notes="Backside"),
            RouteCombination("RB", "flat", 4, notes="Check down"),
        ],
        coverage_beaters=["man", "cover_1", "mismatch"],
        timing="deep",
        key_read="Matchup - throw if slot beats his man",
        formation_fit=["shotgun", "trips", "spread"],
    ),
    PassConcept(
        name="Hank",
        category="deep",
        description="Deep comeback at 18 yards paired with go route. "
                    "Corner must commit - either give up comeback or go.",
        routes=[
            RouteCombination("X", "go", 2, notes="Clear out or TD"),
            RouteCombination("Slot_L", "comeback", 1, notes="18-yard comeback"),
            RouteCombination("Z", "dig", 3, notes="Intermediate"),
            RouteCombination("RB", "flat", 4, notes="Check down"),
        ],
        coverage_beaters=["cover_3", "cover_1"],
        timing="deep",
        key_read="Corner - if trails X, throw comeback",
        formation_fit=["shotgun", "spread"],
    ),
]

# =============================================================================
# Play Action Concepts
# =============================================================================

PLAY_ACTION_CONCEPTS = [
    PassConcept(
        name="PA Boot",
        category="play_action",
        description="Fake inside run, QB boots to opposite flat. TE drags across, "
                    "outside receiver runs comeback. Classic play action.",
        routes=[
            RouteCombination("X", "comeback", 1, notes="Deep option"),
            RouteCombination("TE", "drag", 2, notes="Cross to boot side"),
            RouteCombination("Z", "go", 3, notes="Clear out"),
            RouteCombination("RB", "fake", 99, notes="Fake inside zone"),
        ],
        coverage_beaters=["cover_3", "aggressive_run_defense"],
        timing="intermediate",
        key_read="LB flow - if they bite on run, TE opens",
        formation_fit=["singleback", "shotgun", "pro"],
    ),
    PassConcept(
        name="PA Deep Cross",
        category="play_action",
        description="Fake run, deep crossing route. LBs freeze on run fake, "
                    "crosser runs behind them.",
        routes=[
            RouteCombination("X", "over", 1, notes="Deep cross at 15"),
            RouteCombination("Slot_L", "drag", 2, notes="Shallow option"),
            RouteCombination("Z", "go", 3, notes="Clear out"),
            RouteCombination("RB", "fake", 99, notes="Fake power"),
        ],
        coverage_beaters=["man", "cover_1", "aggressive_run"],
        timing="deep",
        key_read="LBs - cross opens if they bite",
        formation_fit=["singleback", "i_form", "shotgun"],
    ),
    PassConcept(
        name="PA Post",
        category="play_action",
        description="Fake run, throw deep post. Safety should bite on run, "
                    "post runs behind him.",
        routes=[
            RouteCombination("X", "post", 1, notes="Deep shot"),
            RouteCombination("Slot_L", "drag", 2, notes="Intermediate"),
            RouteCombination("Z", "curl", 3, notes="Backside option"),
            RouteCombination("RB", "fake", 99, notes="Fake inside zone"),
        ],
        coverage_beaters=["cover_1", "cover_3", "single_high"],
        timing="deep",
        key_read="Safety - if bites on run, post is open",
        formation_fit=["singleback", "shotgun", "pro"],
    ),
    PassConcept(
        name="PA Corner",
        category="play_action",
        description="Fake run, throw corner route. Great against cover 2 - "
                    "corner bites, safety is late.",
        routes=[
            RouteCombination("X", "corner", 1, notes="Deep shot to corner"),
            RouteCombination("TE", "drag", 2, notes="Underneath option"),
            RouteCombination("Z", "go", 3, notes="Clear out safety"),
            RouteCombination("RB", "fake", 99, notes="Fake outside zone"),
        ],
        coverage_beaters=["cover_2", "cover_4"],
        timing="deep",
        key_read="Corner - run fake should pull him up",
        formation_fit=["singleback", "shotgun", "twins"],
    ),
    PassConcept(
        name="PA Flood",
        category="play_action",
        description="Fake run, flood to play side. 3-level stretch - flat, "
                    "out, corner. Defense flowing to run opens flood.",
        routes=[
            RouteCombination("X", "post", 4, notes="Backside shot"),
            RouteCombination("TE", "flat", 3, notes="Low option"),
            RouteCombination("Slot_R", "out", 2, notes="Middle level"),
            RouteCombination("Z", "corner", 1, notes="High option"),
            RouteCombination("RB", "fake", 99, notes="Fake power"),
        ],
        coverage_beaters=["cover_3", "zone", "run_aggressive"],
        timing="intermediate",
        key_read="Read high to low after run fake",
        formation_fit=["singleback", "shotgun", "trips"],
    ),
    PassConcept(
        name="PA Wheel",
        category="play_action",
        description="Fake run to RB, RB releases on wheel. Linebackers frozen, "
                    "RB runs past them.",
        routes=[
            RouteCombination("X", "post", 2, notes="Deep option"),
            RouteCombination("Slot_L", "drag", 3, notes="Underneath"),
            RouteCombination("Z", "go", 4, notes="Clear out"),
            RouteCombination("RB", "wheel", 1, notes="Fake then wheel"),
        ],
        coverage_beaters=["man", "cover_3", "lb_mismatch"],
        timing="deep",
        key_read="LB covering RB - wheel beats man coverage",
        formation_fit=["singleback", "shotgun", "11_personnel"],
    ),
]

# =============================================================================
# Screen Concepts
# =============================================================================

SCREEN_CONCEPTS = [
    PassConcept(
        name="RB Screen",
        category="screen",
        description="Classic running back screen. Let rushers through, throw behind them. "
                    "OL releases to block downfield.",
        routes=[
            RouteCombination("X", "go", 3, notes="Clear out"),
            RouteCombination("RB", "screen", 1, notes="Catch behind LOS"),
            RouteCombination("Z", "go", 3, notes="Clear out"),
        ],
        coverage_beaters=["blitz", "aggressive_pass_rush"],
        timing="delayed",
        key_read="DL - let them through, throw behind",
        formation_fit=["shotgun", "singleback", "pro"],
    ),
    PassConcept(
        name="Tunnel Screen",
        category="screen",
        description="WR screen where inside receivers block, ball to slot. "
                    "Tunnel created between blockers.",
        routes=[
            RouteCombination("X", "block", 99, notes="Block corner"),
            RouteCombination("Slot_L", "screen", 1, notes="Catch and run"),
            RouteCombination("Z", "block", 99, notes="Block safety"),
        ],
        coverage_beaters=["zone", "soft_coverage"],
        timing="quick",
        key_read="Numbers in box - need advantage",
        formation_fit=["shotgun", "trips", "spread"],
    ),
    PassConcept(
        name="Slow Screen",
        category="screen",
        description="Delayed screen to RB. QB holds ball longer, lets rush develop. "
                    "More time for blockers to get downfield.",
        routes=[
            RouteCombination("X", "go", 3, notes="Clear out"),
            RouteCombination("RB", "screen", 1, notes="Wait for blocks"),
            RouteCombination("Z", "go", 3, notes="Clear out"),
        ],
        coverage_beaters=["aggressive_rush", "blitz"],
        timing="delayed",
        key_read="Protection - need time for screen to develop",
        formation_fit=["shotgun", "singleback"],
    ),
    PassConcept(
        name="Jailbreak Screen",
        category="screen",
        description="Entire OL releases immediately. Quick throw to RB "
                    "with wall of blockers in front.",
        routes=[
            RouteCombination("X", "go", 3, notes="Clear out"),
            RouteCombination("RB", "screen", 1, notes="Catch with blockers"),
            RouteCombination("Z", "go", 3, notes="Clear out"),
        ],
        coverage_beaters=["zone", "soft_coverage"],
        timing="quick",
        key_read="Immediate throw - no read needed",
        formation_fit=["shotgun", "spread"],
    ),
    PassConcept(
        name="Middle Screen",
        category="screen",
        description="Screen up the middle to RB or TE. G and C release "
                    "to lead block through A gap.",
        routes=[
            RouteCombination("X", "go", 3, notes="Clear out"),
            RouteCombination("TE", "screen", 1, notes="Middle of field"),
            RouteCombination("Z", "go", 3, notes="Clear out"),
        ],
        coverage_beaters=["wide_9", "edge_rush"],
        timing="delayed",
        key_read="Interior DL - throw behind them",
        formation_fit=["shotgun", "12_personnel"],
    ),
]

# =============================================================================
# RPO Concepts
# =============================================================================

RPO_CONCEPTS = [
    PassConcept(
        name="RPO Slant",
        category="rpo",
        description="Inside zone run with slant read. QB reads backside LB - "
                    "if he flows to run, throw slant behind him.",
        routes=[
            RouteCombination("X", "slant", 1, notes="Quick slant"),
            RouteCombination("Slot_L", "block", 99, notes="Block or release late"),
            RouteCombination("Z", "go", 3, notes="Clear out"),
            RouteCombination("RB", "inside_zone", 2, notes="Run option"),
        ],
        coverage_beaters=["aggressive_lb_play"],
        timing="quick",
        key_read="Backside LB - if flows to run, throw slant",
        formation_fit=["shotgun", "spread"],
    ),
    PassConcept(
        name="RPO Bubble",
        category="rpo",
        description="Inside zone run with bubble read. QB reads flat defender - "
                    "if he crashes to box, throw bubble.",
        routes=[
            RouteCombination("X", "block", 99, notes="Block corner"),
            RouteCombination("Slot_L", "bubble", 1, notes="Bubble option"),
            RouteCombination("Z", "go", 3, notes="Clear out"),
            RouteCombination("RB", "inside_zone", 2, notes="Run option"),
        ],
        coverage_beaters=["run_aggressive", "loaded_box"],
        timing="quick",
        key_read="Slot defender - if crashes, throw bubble",
        formation_fit=["shotgun", "trips", "spread"],
    ),
    PassConcept(
        name="RPO Glance",
        category="rpo",
        description="Run with glance/peek route. Receiver runs quick in at 3 yards. "
                    "QB reads near LB.",
        routes=[
            RouteCombination("X", "go", 3, notes="Clear out"),
            RouteCombination("Slot_L", "slant", 1, notes="Quick peek route"),
            RouteCombination("Z", "hitch", 2, notes="Backside option"),
            RouteCombination("RB", "inside_zone", 2, notes="Run option"),
        ],
        coverage_beaters=["aggressive_lb"],
        timing="quick",
        key_read="Playside LB - throw if he steps up",
        formation_fit=["shotgun", "spread"],
    ),
    PassConcept(
        name="RPO Pop",
        category="rpo",
        description="Run with TE pop pass. TE blocks then releases to flat. "
                    "QB reads end man on LOS.",
        routes=[
            RouteCombination("X", "go", 3, notes="Clear out"),
            RouteCombination("TE", "flat", 1, notes="Pop pass option"),
            RouteCombination("Z", "go", 3, notes="Clear out"),
            RouteCombination("RB", "power", 2, notes="Run option"),
        ],
        coverage_beaters=["aggressive_de", "run_aggressive"],
        timing="quick",
        key_read="DE - if crashes, throw pop",
        formation_fit=["shotgun", "12_personnel"],
    ),
    PassConcept(
        name="RPO Stick",
        category="rpo",
        description="Zone run with stick route. More advanced RPO, gives time "
                    "for stick to develop.",
        routes=[
            RouteCombination("X", "go", 3, notes="Clear out"),
            RouteCombination("Slot_L", "stick", 1, notes="Settle in zone hole"),
            RouteCombination("TE", "flat", 2, notes="Under option"),
            RouteCombination("RB", "inside_zone", 3, notes="Run option"),
        ],
        coverage_beaters=["zone", "soft_coverage"],
        timing="quick",
        key_read="LB - if flows to run, throw stick",
        formation_fit=["shotgun", "11_personnel", "spread"],
    ),
]


# =============================================================================
# Run Concepts (expanding existing)
# =============================================================================

@dataclass
class RunConcept:
    """A complete run concept definition."""
    name: str
    scheme: str  # zone, gap, counter, draw, option
    description: str
    blocking_rules: Dict[str, str]  # Position: assignment
    ball_carrier_path: str
    aiming_point: str  # A_gap, B_gap, C_gap, edge
    timing: str  # quick, normal, delayed
    best_against: List[str]  # What defenses it beats

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "scheme": self.scheme,
            "description": self.description,
            "blocking_rules": self.blocking_rules,
            "ball_carrier_path": self.ball_carrier_path,
            "aiming_point": self.aiming_point,
            "timing": self.timing,
            "best_against": self.best_against,
        }


RUN_CONCEPTS_EXTENDED = [
    RunConcept(
        name="Inside Zone",
        scheme="zone",
        description="Base zone run between the tackles. OL takes zone steps, creates combos, "
                    "climbs to LBs. RB reads blocks and finds the hole - can bang, bend, or bounce.",
        blocking_rules={
            "LT": "Zone step, combo to backside LB",
            "LG": "Zone step, combo with C",
            "C": "Zone step, combo with guard",
            "RG": "Zone step playside",
            "RT": "Zone step, reach",
        },
        ball_carrier_path="Press A-gap, read first down lineman",
        aiming_point="A_gap",
        timing="quick",
        best_against=["4-3", "over_front", "even_front"],
    ),
    RunConcept(
        name="Outside Zone (Stretch)",
        scheme="zone",
        description="Zone run designed to get to the edge. OL reach blocks, stretches defense "
                    "horizontally. RB presses C-gap, can cut back if defense overruns.",
        blocking_rules={
            "LT": "Reach, get outside shoulder",
            "LG": "Reach, overtake",
            "C": "Reach, cutoff",
            "RG": "Reach",
            "RT": "Reach, pin defender",
        },
        ball_carrier_path="Press outside, cutback if over-pursuit",
        aiming_point="C_gap",
        timing="normal",
        best_against=["aggressive_front", "penetrating_dl"],
    ),
    RunConcept(
        name="Power",
        scheme="gap",
        description="Gap scheme with pulling guard. Playside blocks down, backside guard "
                    "pulls to kick out EMOL. Physical, downhill running.",
        blocking_rules={
            "LT": "Cutoff backside",
            "LG": "Pull, kick out EMOL",
            "C": "Block back, reach",
            "RG": "Down block",
            "RT": "Down block, combo to LB",
        },
        ball_carrier_path="Follow pulling guard through B-gap",
        aiming_point="B_gap",
        timing="normal",
        best_against=["odd_front", "3-4", "undersized_dl"],
    ),
    RunConcept(
        name="Counter",
        scheme="counter",
        description="Misdirection run. RB takes counter step away, then cuts back. "
                    "Two pullers (G and T) lead to playside. Slow developing but explosive.",
        blocking_rules={
            "LT": "Pull, wrap to LB",
            "LG": "Pull, kick out EMOL",
            "C": "Block back",
            "RG": "Down block",
            "RT": "Down block",
        },
        ball_carrier_path="Counter step, follow pullers",
        aiming_point="B_gap",
        timing="delayed",
        best_against=["aggressive_lb", "fast_flowing_defense"],
    ),
    RunConcept(
        name="Duo",
        scheme="gap",
        description="Power without a puller. Double teams at point of attack, "
                    "RB reads daylight. Physical, downhill, quick-hitting.",
        blocking_rules={
            "LT": "Base block",
            "LG": "Combo to backside LB",
            "C": "Combo with guard",
            "RG": "Double team, drive defender",
            "RT": "Double team",
        },
        ball_carrier_path="Downhill through double team",
        aiming_point="A_gap",
        timing="quick",
        best_against=["light_box", "two_high_safety"],
    ),
    RunConcept(
        name="Iso",
        scheme="gap",
        description="Isolation run - FB leads and kicks out LB. Simple, physical. "
                    "RB follows FB through A-gap.",
        blocking_rules={
            "LT": "Base block",
            "LG": "Combo, climb to backside LB",
            "C": "Block playside DT",
            "RG": "Block playside DT/DE",
            "RT": "Base block",
            "FB": "Lead block on MIKE",
        },
        ball_carrier_path="Follow FB through A-gap",
        aiming_point="A_gap",
        timing="quick",
        best_against=["3-4", "one_gap_dl"],
    ),
    RunConcept(
        name="Trap",
        scheme="gap",
        description="Let DL penetrate, trap him with pulling guard. Works against "
                    "aggressive, penetrating defenders.",
        blocking_rules={
            "LT": "Cutoff",
            "LG": "Pull, trap penetrating DL",
            "C": "Block playside, let DL through",
            "RG": "Skip pull, lead to LB",
            "RT": "Base block",
        },
        ball_carrier_path="Follow trapper through hole",
        aiming_point="A_gap",
        timing="quick",
        best_against=["penetrating_dl", "aggressive_dt"],
    ),
    RunConcept(
        name="Sweep",
        scheme="gap",
        description="Perimeter run with pulling linemen. G and T pull to lead. "
                    "Speed play designed to get outside.",
        blocking_rules={
            "LT": "Cutoff",
            "LG": "Pull, lead to corner",
            "C": "Cutoff",
            "RG": "Pull, kick out",
            "RT": "Hinge, protect edge",
        },
        ball_carrier_path="Get width, turn corner",
        aiming_point="edge",
        timing="normal",
        best_against=["slow_lb", "undersized_secondary"],
    ),
    RunConcept(
        name="Toss",
        scheme="gap",
        description="Pitch play to get outside quickly. QB pitches to RB heading to perimeter. "
                    "Pullers lead the way.",
        blocking_rules={
            "LT": "Cutoff",
            "LG": "Pull and lead",
            "C": "Pull and lead",
            "RG": "Reach",
            "RT": "Reach",
        },
        ball_carrier_path="Catch pitch, get to edge",
        aiming_point="edge",
        timing="quick",
        best_against=["slow_defense", "bad_tackling"],
    ),
    RunConcept(
        name="Draw",
        scheme="draw",
        description="Delayed run. OL shows pass protection, then blocks. "
                    "RB waits for DL to commit to pass rush.",
        blocking_rules={
            "LT": "Pass set, then engage",
            "LG": "Pass set, then engage",
            "C": "Pass set, then block",
            "RG": "Pass set, then engage",
            "RT": "Pass set, then engage",
        },
        ball_carrier_path="Wait, then attack opening",
        aiming_point="A_gap",
        timing="delayed",
        best_against=["aggressive_pass_rush", "speed_rusher"],
    ),
    RunConcept(
        name="Dive",
        scheme="gap",
        description="Quick-hitting A-gap run. Fast mesh, immediate handoff. "
                    "Good for short yardage.",
        blocking_rules={
            "LT": "Base",
            "LG": "Combo with C",
            "C": "Combo with G",
            "RG": "Base",
            "RT": "Base",
        },
        ball_carrier_path="Hit the hole immediately",
        aiming_point="A_gap",
        timing="quick",
        best_against=["any", "short_yardage"],
    ),
    RunConcept(
        name="QB Draw",
        scheme="draw",
        description="Draw run for QB. Sell pass, then QB runs. "
                    "Works against aggressive pass rushers.",
        blocking_rules={
            "LT": "Pass set, cut block late",
            "LG": "Pass set, then engage",
            "C": "Pass set, create lane",
            "RG": "Pass set, then engage",
            "RT": "Pass set, cut block late",
        },
        ball_carrier_path="QB attacks lane after rushers commit",
        aiming_point="A_gap",
        timing="delayed",
        best_against=["aggressive_edge", "contain_breaks"],
    ),
    RunConcept(
        name="Read Option",
        scheme="option",
        description="Zone run with read. QB reads unblocked DE - give to RB if DE crashes, "
                    "keep if DE stays home.",
        blocking_rules={
            "LT": "Zone, leave DE unblocked",
            "LG": "Zone",
            "C": "Zone",
            "RG": "Zone",
            "RT": "Zone",
        },
        ball_carrier_path="RB runs zone, QB reads DE",
        aiming_point="A_gap",
        timing="quick",
        best_against=["aggressive_de", "undisciplined_defense"],
    ),
    RunConcept(
        name="Speed Option",
        scheme="option",
        description="Perimeter option. QB and RB attack edge, QB reads pitch key. "
                    "Quick-hitting option to get outside.",
        blocking_rules={
            "LT": "Release to LB",
            "LG": "Release to LB",
            "C": "Block DT",
            "RG": "Pull, lead",
            "RT": "Arc block",
        },
        ball_carrier_path="Attack edge, pitch if defender takes QB",
        aiming_point="edge",
        timing="quick",
        best_against=["slow_secondary", "undisciplined_de"],
    ),
    RunConcept(
        name="QB Power",
        scheme="gap",
        description="Power run with QB as ball carrier. Good for mobile QBs "
                    "near goal line or short yardage.",
        blocking_rules={
            "LT": "Cutoff",
            "LG": "Pull, lead through hole",
            "C": "Block back",
            "RG": "Down block",
            "RT": "Down block",
        },
        ball_carrier_path="QB follows puller through B-gap",
        aiming_point="B_gap",
        timing="normal",
        best_against=["light_box", "spread_defense"],
    ),
]


# =============================================================================
# Playbook Organization
# =============================================================================

@dataclass
class Playbook:
    """A complete playbook organized by category."""
    name: str
    style: str  # west_coast, air_raid, spread, pro, power_run
    pass_concepts: Dict[str, List[PassConcept]]
    run_concepts: List[RunConcept]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "style": self.style,
            "pass_concepts": {
                category: [c.to_dict() for c in concepts]
                for category, concepts in self.pass_concepts.items()
            },
            "run_concepts": [c.to_dict() for c in self.run_concepts],
            "summary": {
                "total_pass_concepts": sum(len(c) for c in self.pass_concepts.values()),
                "total_run_concepts": len(self.run_concepts),
                "categories": list(self.pass_concepts.keys()),
            },
        }


def create_complete_playbook() -> Playbook:
    """Create a complete playbook with all concepts."""
    return Playbook(
        name="Complete NFL Playbook",
        style="balanced",
        pass_concepts={
            "quick_game": QUICK_GAME_CONCEPTS,
            "dropback": DROPBACK_CONCEPTS,
            "deep_shots": DEEP_CONCEPTS,
            "play_action": PLAY_ACTION_CONCEPTS,
            "screens": SCREEN_CONCEPTS,
            "rpo": RPO_CONCEPTS,
        },
        run_concepts=RUN_CONCEPTS_EXTENDED,
    )


# =============================================================================
# Export Functions
# =============================================================================

def export_playbook_catalogue():
    """Export complete playbook catalogue to JSON."""
    playbook = create_complete_playbook()

    # Build complete catalogue
    catalogue = {
        "route_tree": ROUTE_TREE,
        "additional_routes": ADDITIONAL_ROUTES,
        "playbook": playbook.to_dict(),
    }

    # Export
    output_dir = Path(__file__).parent.parent / "exports"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "playbook_catalogue.json"
    with open(output_file, "w") as f:
        json.dump(catalogue, f, indent=2)

    print(f"Exported playbook catalogue to {output_file}")

    # Print summary
    print("\n=== Playbook Catalogue Summary ===")
    print(f"Route Tree: 10 standard routes (0-9)")
    print(f"Additional Routes: {len(ADDITIONAL_ROUTES)} specialized routes")
    print(f"\nPass Concepts by Category:")
    for category, concepts in playbook.pass_concepts.items():
        print(f"  {category}: {len(concepts)} concepts")
    print(f"\nRun Concepts: {len(playbook.run_concepts)} concepts")
    print(f"\nTotal: {sum(len(c) for c in playbook.pass_concepts.values())} pass + {len(playbook.run_concepts)} run = {sum(len(c) for c in playbook.pass_concepts.values()) + len(playbook.run_concepts)} plays")

    return catalogue


if __name__ == "__main__":
    export_playbook_catalogue()
