"""Player and team generation."""

import random
from typing import Optional

from huddle.core.attributes import PlayerAttributes
from huddle.core.enums import Position
from huddle.core.models.player import Player
from huddle.core.models.team import Team
from huddle.core.models.team_identity import TeamIdentity, create_random_identity
from huddle.core.models.tendencies import TeamTendencies, OffensiveScheme, DefensiveScheme
from huddle.generators.potential import generate_all_potentials
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
from huddle.core.philosophy.evaluation import PHILOSOPHY_ATTRIBUTE_WEIGHTS


# Position to philosophy enum mapping for archetype assignment
POSITION_TO_PHILOSOPHY_ENUM = {
    "QB": QBPhilosophy,
    "RB": RBPhilosophy,
    "FB": RBPhilosophy,  # FBs use RB philosophies
    "WR": WRPhilosophy,
    "TE": TEPhilosophy,
    "LT": OLPhilosophy,
    "LG": OLPhilosophy,
    "C": OLPhilosophy,
    "RG": OLPhilosophy,
    "RT": OLPhilosophy,
    "DE": DLPhilosophy,
    "DT": DLPhilosophy,
    "NT": DLPhilosophy,
    "MLB": LBPhilosophy,
    "OLB": LBPhilosophy,
    "ILB": LBPhilosophy,
    "CB": CBPhilosophy,
    "FS": FSPhilosophy,
    "SS": SSPhilosophy,
}

# Sample names for generation
FIRST_NAMES = [
    "James", "John", "Michael", "David", "Chris", "Matt", "Josh", "Ryan",
    "Tyler", "Brandon", "Justin", "Marcus", "Antonio", "DeShawn", "Malik",
    "Jamal", "Terrell", "Andre", "Darius", "Lamar", "Patrick", "Tom",
    "Aaron", "Derek", "Russell", "Cam", "Kyler", "Trevor", "Justin", "Tua",
    "Cooper", "Chase", "Ja'Marr", "Tyreek", "Davante", "Stefon", "CeeDee",
    "Travis", "George", "Mark", "Derrick", "Dalvin", "Alvin", "Nick",
]

LAST_NAMES = [
    "Johnson", "Williams", "Brown", "Jones", "Davis", "Miller", "Wilson",
    "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris",
    "Martin", "Thompson", "Robinson", "Clark", "Lewis", "Walker", "Hall",
    "Allen", "Young", "King", "Wright", "Hill", "Scott", "Green", "Adams",
    "Baker", "Nelson", "Carter", "Mitchell", "Mahomes", "Brady", "Rodgers",
    "Wilson", "Murray", "Herbert", "Burrow", "Lawrence", "Fields", "Lance",
]

# Sample colleges for player generation
COLLEGES = [
    # Power 5
    "Alabama", "Georgia", "Ohio State", "Michigan", "Clemson", "LSU",
    "Texas", "USC", "Oklahoma", "Oregon", "Penn State", "Notre Dame",
    "Florida", "Tennessee", "Auburn", "Miami", "Florida State", "Wisconsin",
    "Texas A&M", "UCLA", "Stanford", "Washington", "Michigan State", "Iowa",
    "Nebraska", "Oklahoma State", "TCU", "Baylor", "Kansas State", "Ole Miss",
    "Arkansas", "South Carolina", "Kentucky", "Missouri", "Mississippi State",
    "Virginia Tech", "North Carolina", "NC State", "Duke", "Pittsburgh",
    "Syracuse", "Boston College", "Louisville", "Wake Forest", "Colorado",
    "Arizona State", "Utah", "Arizona", "California", "Oregon State",
    # Group of 5 / Mid-Major
    "Cincinnati", "UCF", "Houston", "Memphis", "SMU", "Tulane", "Boise State",
    "San Diego State", "Fresno State", "UNLV", "Air Force", "Colorado State",
    "Appalachian State", "Coastal Carolina", "Marshall", "James Madison",
    "Liberty", "Troy", "South Alabama", "Louisiana", "UTSA", "North Texas",
    "Western Kentucky", "Toledo", "NIU", "Eastern Michigan", "Buffalo",
    # FCS / Small School
    "North Dakota State", "South Dakota State", "Montana", "Montana State",
    "Sacramento State", "Eastern Washington", "Weber State", "UC Davis",
    "Delaware", "Villanova", "New Hampshire", "Maine", "Rhode Island",
]

# Iconic jersey numbers by position that players might prefer
ICONIC_NUMBERS: dict[Position, list[int]] = {
    Position.QB: [12, 7, 9, 4, 10, 8, 3, 1, 5, 18],  # Brady, Elway, Brees, Favre, etc.
    Position.RB: [21, 28, 34, 26, 22, 32, 25, 20, 27, 23],  # Sanders, Peterson, Payton, etc.
    Position.FB: [44, 45, 32, 33, 40, 42, 38, 46, 30, 35],
    Position.WR: [80, 84, 81, 88, 85, 13, 18, 11, 17, 14],  # Rice, Moss, TO, etc.
    Position.TE: [87, 88, 81, 85, 82, 84, 89, 86, 80, 83],  # Gronk, Gonzalez, etc.
    Position.LT: [71, 72, 77, 76, 78, 70, 74, 79, 75, 73],
    Position.LG: [66, 67, 62, 64, 68, 61, 63, 65, 69, 60],
    Position.C: [52, 57, 55, 53, 51, 56, 54, 58, 59, 50],
    Position.RG: [66, 67, 62, 64, 68, 61, 63, 65, 69, 60],
    Position.RT: [71, 72, 77, 76, 78, 70, 74, 79, 75, 73],
    Position.DE: [99, 91, 97, 93, 90, 98, 95, 94, 92, 96],  # Watt, etc.
    Position.DT: [93, 97, 99, 98, 90, 92, 94, 95, 91, 96],  # Sapp, etc.
    Position.NT: [92, 98, 93, 97, 90, 94, 95, 99, 91, 96],
    Position.MLB: [52, 55, 54, 50, 56, 51, 53, 58, 59, 57],  # Lewis, Willis, etc.
    Position.ILB: [52, 55, 54, 50, 56, 51, 53, 58, 59, 57],
    Position.OLB: [55, 56, 52, 58, 59, 54, 51, 50, 53, 57],  # Brooks, etc.
    Position.CB: [24, 21, 26, 23, 22, 20, 29, 25, 27, 31],  # Revis, Sanders, etc.
    Position.FS: [21, 20, 29, 27, 32, 36, 22, 24, 25, 31],  # Taylor, Reed, etc.
    Position.SS: [42, 43, 31, 36, 37, 38, 27, 30, 33, 41],  # Polamalu, etc.
    Position.K: [3, 4, 1, 5, 6, 9, 2, 7, 8, 11],
    Position.P: [4, 6, 1, 5, 9, 3, 7, 8, 2, 17],
    Position.LS: [48, 47, 46, 45, 44, 49, 43, 42, 41, 40],
}

# Position-specific attribute templates (mean, std_dev)
# These define the baseline for each position's key attributes
# Values calibrated to real NFL combine data and player measurements
POSITION_TEMPLATES: dict[Position, dict[str, tuple[int, int]]] = {
    Position.QB: {
        # Physical - QBs vary widely (Lamar vs Brady)
        "speed": (65, 12),  # Avg ~4.85 forty, huge variance
        "acceleration": (67, 10),
        "agility": (68, 10),
        "strength": (58, 8),
        "stamina": (78, 8),
        "jumping": (62, 10),
        # Passing
        "throw_power": (82, 8),
        "throw_accuracy_short": (80, 8),
        "throw_accuracy_med": (76, 10),
        "throw_accuracy_deep": (70, 12),
        "throw_on_run": (68, 12),
        "play_action": (75, 10),
        # Rushing (for scrambling)
        "carrying": (62, 10),
        "elusiveness": (62, 12),
        "ball_carrier_vision": (58, 10),
        # Mental
        "awareness": (78, 10),
        "learning": (75, 12),
        "poise": (78, 10),  # Staying calm under pressure
        "anticipation": (76, 10),  # Reading defenses pre-snap
        "decision_making": (77, 10),  # Making smart choices
        "aggressiveness": (55, 12),  # QBs generally not super aggressive
    },
    Position.RB: {
        # Physical - RBs are fast but not CB fast (~4.45-4.55 forty)
        "speed": (84, 5),
        "acceleration": (85, 5),
        "agility": (83, 5),
        "strength": (72, 8),
        "stamina": (82, 8),
        "jumping": (75, 10),
        # Rushing
        "carrying": (85, 6),
        "trucking": (75, 10),
        "elusiveness": (82, 8),
        "break_tackle": (78, 8),
        "ball_carrier_vision": (80, 8),
        "spin_move": (75, 10),
        "juke_move": (78, 10),
        "stiff_arm": (72, 10),
        # Receiving
        "catching": (70, 10),
        "route_running": (65, 12),
        # Blocking
        "pass_block": (55, 12),
        # Special teams
        "kick_return": (70, 12),
        # Mental
        "awareness": (72, 10),
        "learning": (70, 10),
    },
    Position.FB: {
        # Physical - FBs are slower power backs (~4.75-5.0 forty)
        "speed": (66, 6),
        "acceleration": (70, 6),
        "agility": (66, 8),
        "strength": (82, 6),
        "stamina": (80, 8),
        # Rushing
        "carrying": (68, 10),
        "trucking": (82, 8),
        "break_tackle": (78, 8),
        "ball_carrier_vision": (65, 10),
        # Blocking
        "run_block": (82, 8),
        "pass_block": (72, 10),
        "impact_blocking": (80, 8),
        # Receiving
        "catching": (65, 12),
        # Mental
        "awareness": (72, 10),
        "learning": (68, 10),
    },
    Position.WR: {
        # Physical - WRs are fast (~4.40-4.55 forty)
        "speed": (86, 5),
        "acceleration": (85, 5),
        "agility": (84, 5),
        "strength": (58, 10),
        "stamina": (78, 8),
        "jumping": (80, 10),
        # Receiving
        "catching": (82, 6),
        "route_running": (80, 8),
        "release": (78, 8),
        "catch_in_traffic": (75, 10),
        "spectacular_catch": (72, 12),
        # Rushing (after catch)
        "elusiveness": (75, 10),
        "break_tackle": (62, 12),
        "juke_move": (72, 10),
        # Special teams
        "kick_return": (72, 12),
        # Mental
        "awareness": (72, 10),
        "learning": (72, 10),
    },
    Position.TE: {
        # Physical - TEs are big and moderately fast (~4.65-4.85 forty)
        "speed": (72, 6),
        "acceleration": (73, 6),
        "agility": (70, 8),
        "strength": (78, 8),
        "stamina": (78, 8),
        "jumping": (75, 10),
        # Receiving
        "catching": (78, 8),
        "route_running": (70, 10),
        "catch_in_traffic": (78, 8),
        "release": (68, 10),
        # Rushing
        "break_tackle": (72, 8),
        "stiff_arm": (70, 10),
        # Blocking
        "run_block": (72, 10),
        "pass_block": (68, 10),
        "impact_blocking": (70, 10),
        # Mental
        "awareness": (72, 10),
        "learning": (70, 10),
    },
    Position.LT: {
        # Physical
        "speed": (55, 8),
        "acceleration": (58, 8),
        "agility": (60, 8),
        "strength": (88, 6),
        "stamina": (82, 6),
        # Blocking
        "pass_block": (85, 8),
        "run_block": (80, 8),
        "impact_blocking": (72, 10),
        # Mental
        "awareness": (75, 10),
        "learning": (70, 10),
    },
    Position.LG: {
        # Physical
        "speed": (50, 8),
        "acceleration": (55, 8),
        "agility": (58, 8),
        "strength": (90, 5),
        "stamina": (82, 6),
        # Blocking
        "pass_block": (80, 8),
        "run_block": (88, 6),
        "impact_blocking": (78, 8),
        # Mental
        "awareness": (72, 10),
        "learning": (68, 10),
    },
    Position.C: {
        # Physical
        "speed": (48, 6),
        "acceleration": (52, 6),
        "agility": (55, 8),
        "strength": (85, 6),
        "stamina": (85, 5),
        # Blocking
        "pass_block": (82, 8),
        "run_block": (82, 8),
        "impact_blocking": (75, 8),
        # Mental (centers make line calls)
        "awareness": (82, 8),
        "learning": (78, 8),
    },
    Position.RG: {
        # Physical
        "speed": (50, 8),
        "acceleration": (55, 8),
        "agility": (58, 8),
        "strength": (90, 5),
        "stamina": (82, 6),
        # Blocking
        "pass_block": (80, 8),
        "run_block": (88, 6),
        "impact_blocking": (78, 8),
        # Mental
        "awareness": (72, 10),
        "learning": (68, 10),
    },
    Position.RT: {
        # Physical
        "speed": (54, 8),
        "acceleration": (57, 8),
        "agility": (58, 8),
        "strength": (86, 6),
        "stamina": (82, 6),
        # Blocking
        "pass_block": (82, 8),
        "run_block": (82, 8),
        "impact_blocking": (72, 10),
        # Mental
        "awareness": (75, 10),
        "learning": (70, 10),
    },
    Position.DE: {
        # Physical - DEs are big, strong, moderately athletic (~4.70-4.95 forty)
        "speed": (70, 5),  # Lowered from 78 - DEs avg ~4.75 forty
        "acceleration": (72, 5),
        "agility": (70, 6),
        "strength": (84, 6),  # Strong - need to bull rush
        "stamina": (78, 8),
        # Defense - Pass Rush
        "block_shedding": (80, 8),
        "finesse_moves": (76, 10),
        "power_moves": (78, 10),
        # Defense - Tackling
        "tackle": (76, 8),
        "pursuit": (78, 8),
        "hit_power": (78, 10),
        # Mental
        "play_recognition": (72, 10),
        "awareness": (70, 10),
        "learning": (68, 10),
    },
    Position.DT: {
        # Physical - DTs are massive and slow (~4.95-5.25 forty)
        "speed": (56, 6),
        "acceleration": (58, 6),
        "agility": (54, 8),
        "strength": (92, 5),  # Very strong
        "stamina": (72, 8),
        # Defense
        "block_shedding": (84, 6),
        "power_moves": (82, 8),
        "finesse_moves": (62, 12),
        "tackle": (76, 8),
        "pursuit": (62, 10),
        "hit_power": (80, 8),
        # Mental
        "play_recognition": (70, 10),
        "awareness": (68, 10),
        "learning": (65, 10),
    },
    Position.NT: {
        # Physical - NTs are the biggest/slowest (~5.10-5.40 forty)
        "speed": (48, 6),
        "acceleration": (50, 6),
        "agility": (46, 8),
        "strength": (95, 4),  # Strongest position
        "stamina": (70, 10),
        # Defense
        "block_shedding": (86, 5),
        "power_moves": (85, 6),
        "tackle": (76, 8),
        "pursuit": (52, 12),
        "hit_power": (82, 8),
        # Mental
        "play_recognition": (68, 10),
        "awareness": (65, 10),
        "learning": (62, 10),
    },
    Position.MLB: {
        # Physical - MLBs are thumpers, not speedsters (~4.65-4.85 forty)
        "speed": (73, 5),  # Lowered from 78
        "acceleration": (75, 5),
        "agility": (72, 6),
        "strength": (80, 8),
        "stamina": (82, 6),
        "jumping": (72, 10),
        # Defense - Tackling
        "tackle": (86, 5),
        "pursuit": (82, 6),
        "hit_power": (80, 8),
        "block_shedding": (76, 8),
        # Defense - Coverage
        "zone_coverage": (70, 10),
        "man_coverage": (62, 12),
        # Mental (MLBs make defensive calls)
        "play_recognition": (82, 8),
        "awareness": (80, 8),
        "learning": (75, 10),
    },
    Position.ILB: {
        # Physical - ILBs slightly faster than MLB for coverage (~4.60-4.80 forty)
        "speed": (75, 5),  # Lowered from 80
        "acceleration": (77, 5),
        "agility": (74, 6),
        "strength": (76, 8),
        "stamina": (82, 6),
        "jumping": (72, 10),
        # Defense
        "tackle": (84, 6),
        "pursuit": (82, 6),
        "hit_power": (76, 8),
        "block_shedding": (72, 10),
        "zone_coverage": (73, 10),
        "man_coverage": (66, 12),
        # Mental
        "play_recognition": (78, 8),
        "awareness": (75, 10),
        "learning": (72, 10),
    },
    Position.OLB: {
        # Physical - OLBs are more athletic, edge rushers (~4.55-4.75 forty)
        "speed": (77, 5),  # Lowered from 82
        "acceleration": (79, 5),
        "agility": (76, 6),
        "strength": (76, 8),
        "stamina": (80, 8),
        "jumping": (75, 10),
        # Defense
        "tackle": (80, 6),
        "pursuit": (82, 6),
        "finesse_moves": (72, 10),
        "power_moves": (68, 12),
        "block_shedding": (70, 10),
        "zone_coverage": (68, 10),
        "man_coverage": (62, 10),
        "hit_power": (75, 10),
        # Mental
        "play_recognition": (75, 10),
        "awareness": (72, 10),
        "learning": (70, 10),
    },
    Position.CB: {
        # Physical - CBs are the fastest defenders (~4.35-4.50 forty)
        "speed": (88, 4),  # Lowered from 92 - still fastest
        "acceleration": (87, 4),
        "agility": (86, 5),
        "strength": (56, 10),
        "stamina": (80, 8),
        "jumping": (82, 8),
        # Defense - Coverage
        "man_coverage": (82, 6),
        "zone_coverage": (78, 8),
        "press": (76, 10),
        # Defense - Tackling (CBs are weaker tacklers)
        "tackle": (62, 10),
        "pursuit": (75, 8),
        "hit_power": (52, 12),
        # Special teams
        "kick_return": (75, 12),
        # Mental
        "play_recognition": (75, 10),
        "awareness": (75, 10),
        "learning": (72, 10),
    },
    Position.FS: {
        # Physical - FS are fast, rangey (~4.45-4.60 forty)
        "speed": (84, 5),  # Lowered from 90
        "acceleration": (83, 5),
        "agility": (82, 6),
        "strength": (62, 10),
        "stamina": (82, 6),
        "jumping": (80, 10),
        # Defense - Coverage
        "zone_coverage": (82, 6),
        "man_coverage": (70, 10),
        # Defense - Tackling
        "tackle": (70, 8),
        "pursuit": (78, 8),
        "hit_power": (68, 10),
        # Mental
        "play_recognition": (82, 8),
        "awareness": (80, 8),
        "learning": (75, 10),
    },
    Position.SS: {
        # Physical - SS are bigger, hit harder than FS (~4.50-4.65 forty)
        "speed": (80, 5),  # Lowered from 85
        "acceleration": (80, 5),
        "agility": (78, 6),
        "strength": (74, 8),
        "stamina": (82, 6),
        "jumping": (78, 10),
        # Defense - Coverage
        "zone_coverage": (76, 8),
        "man_coverage": (68, 10),
        # Defense - Tackling
        "tackle": (80, 6),
        "pursuit": (78, 8),
        "hit_power": (80, 8),
        # Mental
        "play_recognition": (78, 8),
        "awareness": (75, 10),
        "learning": (72, 10),
    },
    Position.K: {
        # Physical - Kickers are leg specialists, not athletes (~5.0+ forty)
        "speed": (48, 8),
        "acceleration": (50, 8),
        "strength": (55, 10),
        "stamina": (70, 10),
        # Special Teams - the only stats that matter
        "kick_power": (82, 8),
        "kick_accuracy": (82, 8),
        # Mental (pressure situations)
        "awareness": (75, 12),
        "learning": (70, 10),
    },
    Position.P: {
        # Physical - Punters slightly more athletic than kickers
        "speed": (52, 8),
        "acceleration": (54, 8),
        "strength": (58, 10),
        "stamina": (70, 10),
        # Special Teams
        "kick_power": (85, 6),
        "kick_accuracy": (72, 10),
        # Mental
        "awareness": (72, 12),
        "learning": (68, 10),
    },
    Position.LS: {
        # Long Snapper - the most specialized position
        "speed": (48, 6),
        "acceleration": (50, 6),
        "strength": (70, 10),
        "stamina": (75, 10),
        "awareness": (80, 8),
        "learning": (75, 10),
    },
}

# Physical measurements by position (height_inches, weight_lbs)
POSITION_PHYSICALS: dict[Position, tuple[tuple[int, int], tuple[int, int]]] = {
    Position.QB: ((73, 3), (215, 15)),
    Position.RB: ((69, 3), (210, 20)),
    Position.FB: ((71, 2), (245, 15)),
    Position.WR: ((72, 4), (195, 20)),
    Position.TE: ((76, 2), (250, 15)),
    Position.LT: ((77, 2), (310, 20)),
    Position.LG: ((75, 2), (315, 20)),
    Position.C: ((74, 2), (305, 15)),
    Position.RG: ((75, 2), (315, 20)),
    Position.RT: ((77, 2), (315, 20)),
    Position.DE: ((76, 3), (270, 20)),
    Position.DT: ((74, 3), (305, 25)),
    Position.NT: ((73, 2), (330, 25)),
    Position.MLB: ((73, 2), (245, 15)),
    Position.ILB: ((73, 2), (240, 15)),
    Position.OLB: ((74, 2), (240, 15)),
    Position.CB: ((71, 3), (190, 15)),
    Position.FS: ((72, 3), (200, 15)),
    Position.SS: ((72, 2), (210, 15)),
    Position.K: ((71, 3), (190, 20)),
    Position.P: ((73, 3), (210, 20)),
    Position.LS: ((72, 2), (245, 15)),
}


def _generate_jersey_preferences(position: Position) -> list[int]:
    """Generate a list of preferred jersey numbers for a position."""
    iconic = ICONIC_NUMBERS.get(position, list(range(1, 100)))

    # Pick 3-5 preferred numbers from iconic list with some randomization
    num_preferences = random.randint(3, 5)
    preferences = []

    # First preference is often from top iconic numbers
    if random.random() < 0.7:  # 70% chance to prefer iconic number first
        preferences.append(random.choice(iconic[:5]))
    else:
        preferences.append(random.choice(iconic))

    # Fill remaining preferences
    while len(preferences) < num_preferences:
        num = random.choice(iconic)
        if num not in preferences:
            preferences.append(num)

    return preferences


def generate_player(
    position: Position,
    overall_target: Optional[int] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    team_identity: Optional[TeamIdentity] = None,
    age: Optional[int] = None,
    potential_modifier: float = 0.0,
    experience_years: Optional[int] = None,
    years_on_team: Optional[int] = None,
    college: Optional[str] = None,
) -> Player:
    """
    Generate a random player at a position.

    Args:
        position: Position to generate
        overall_target: Target overall rating (randomized if None)
        first_name: Specific first name (random if None)
        last_name: Specific last name (random if None)
        team_identity: Optional team identity for scheme-specific tuning
        age: Specific age (random 22-32 if None)
        potential_modifier: Modifier to potential (-10 to +10)
        experience_years: NFL experience (derived from age if None)
        years_on_team: Tenure with current team (defaults to experience)
        college: College attended (random if None)

    Returns:
        Generated Player
    """
    # Generate name
    fname = first_name or random.choice(FIRST_NAMES)
    lname = last_name or random.choice(LAST_NAMES)

    # Determine overall modifier
    if overall_target is None:
        overall_target = random.randint(65, 90)

    # Apply team identity position boost
    if team_identity:
        position_boost = team_identity.get_position_boost(position.name)
        overall_target = int(overall_target + position_boost)
        overall_target = max(55, min(99, overall_target))

    overall_mod = (overall_target - 75) / 25  # -0.4 to +0.6

    # Get team identity attribute emphasis
    attr_emphasis = {}
    if team_identity:
        attr_emphasis = team_identity.get_attribute_emphasis(position.name)

    # Generate attributes
    attrs = PlayerAttributes()
    template = POSITION_TEMPLATES.get(position, {})

    for attr_name, (mean, std) in template.items():
        # Adjust mean by overall modifier
        adjusted_mean = mean + (overall_mod * 15)

        # Apply team identity emphasis
        emphasis = attr_emphasis.get(attr_name, 1.0)
        adjusted_mean = adjusted_mean * emphasis

        value = int(random.gauss(adjusted_mean, std))
        value = max(40, min(99, value))
        attrs.set(attr_name, value)

    # Generate POTENTIAL (the ceiling) - NFL HC09 "Big Three" meta attribute
    # Potential is typically higher than current overall, with variance
    base_potential = overall_target + random.randint(5, 15) + int(potential_modifier)
    # Young players tend to have higher potential gap
    potential_variance = random.gauss(0, 5)
    potential = int(base_potential + potential_variance)
    potential = max(overall_target, min(99, potential))  # At least current overall
    attrs.set("potential", potential)

    # Generate LEARNING (playbook mastery speed) - NFL HC09 "Big Three"
    # Correlated with awareness but has its own variance
    base_learning = attrs.get("awareness", 70) + random.randint(-10, 10)
    learning = int(random.gauss(base_learning, 8))
    learning = max(40, min(99, learning))
    attrs.set("learning", learning)

    # Generate DURABILITY attributes (for wear & tear system)
    _generate_durability_attrs(attrs)

    # Generate physicals using calibrated data
    from huddle.generators.calibration import generate_weight

    height_params, _ = POSITION_PHYSICALS.get(
        position, ((72, 3), (215, 20))
    )
    height = int(random.gauss(height_params[0], height_params[1]))
    # Use calibrated weight from NFL combine data
    weight = generate_weight(position.value)

    # Age and experience
    player_age = age if age is not None else random.randint(22, 32)

    # Calculate experience if not provided
    if experience_years is not None:
        exp = experience_years
    else:
        # Experience based on age (entered league at 21-23)
        max_exp = player_age - 21
        exp = min(max_exp, random.randint(0, max(0, max_exp)))

    # Team tenure (defaults to full experience for new team generation)
    tenure = years_on_team if years_on_team is not None else exp

    # Adjust potential based on age (older players have less upside)
    if player_age > 28:
        age_penalty = (player_age - 28) * 2
        current_potential = attrs.get("potential", 75)
        attrs.set("potential", max(overall_target, current_potential - age_penalty))

    # Jersey preferences
    jersey_prefs = _generate_jersey_preferences(position)

    # College (weighted toward Power 5)
    player_college = college
    if player_college is None:
        if random.random() < 0.75:  # 75% from Power 5 (first 50 in list)
            player_college = random.choice(COLLEGES[:50])
        else:
            player_college = random.choice(COLLEGES)

    player = Player(
        first_name=fname,
        last_name=lname,
        position=position,
        attributes=attrs,
        age=player_age,
        height_inches=height,
        weight_lbs=weight,
        jersey_number=0,  # Will be assigned when added to roster
        preferred_jersey_numbers=jersey_prefs,
        experience_years=exp,
        years_on_team=tenure,
        college=player_college,
    )

    # Assign HC09-style archetype based on attribute profile
    player.player_archetype = _assign_archetype(player)

    return player


def _generate_durability_attrs(attrs: PlayerAttributes) -> None:
    """Generate durability attributes for wear & tear system."""
    # Base toughness (overall durability)
    base_toughness = random.gauss(75, 12)
    attrs.set("toughness", int(max(40, min(99, base_toughness))))

    # Individual body part durability
    # Each has independent variance but correlated with base toughness
    body_parts = [
        "head_durability",
        "torso_durability",
        "left_arm_durability",
        "right_arm_durability",
        "left_leg_durability",
        "right_leg_durability",
    ]

    for part in body_parts:
        # Correlated with toughness but with individual variance
        part_durability = base_toughness + random.gauss(0, 10)
        attrs.set(part, int(max(40, min(99, part_durability))))

    # Injury resistance (general, from original system)
    injury_resistance = base_toughness + random.gauss(0, 8)
    attrs.set("injury", int(max(40, min(99, injury_resistance))))


def _assign_archetype(player: Player) -> Optional[str]:
    """
    Assign the best-fit archetype to a player based on their attributes.

    HC09-style archetype assignment: analyzes a player's attributes
    and determines which positional philosophy (archetype) they best fit.

    For example, a RB with high speed/acceleration gets "speed" archetype,
    while one with high trucking/strength gets "power" archetype.

    Args:
        player: The player to assign an archetype to

    Returns:
        The archetype value (e.g., "power", "speed", "mobile") or None
    """
    position = player.position.value

    # Get the philosophy enum for this position
    philosophy_enum = POSITION_TO_PHILOSOPHY_ENUM.get(position)
    if not philosophy_enum:
        return None

    best_archetype = None
    best_fit_score = -1

    # Test each philosophy value for this position
    for philosophy in philosophy_enum:
        archetype_value = philosophy.value
        weights = PHILOSOPHY_ATTRIBUTE_WEIGHTS.get(archetype_value, {})

        if not weights:
            continue

        # Calculate fit score: sum(attribute_value * weight)
        fit_score = 0.0
        for attr_name, weight in weights.items():
            attr_value = player.attributes.get(attr_name, 50)
            fit_score += attr_value * weight

        if fit_score > best_fit_score:
            best_fit_score = fit_score
            best_archetype = archetype_value

    return best_archetype


def _get_jersey_number(position: Position) -> int:
    """Get a position-appropriate jersey number."""
    ranges = {
        Position.QB: (1, 19),
        Position.RB: (20, 49),
        Position.FB: (30, 49),
        Position.WR: (10, 19),  # Can also use 80-89
        Position.TE: (80, 89),
        Position.LT: (70, 79),
        Position.LG: (60, 69),
        Position.C: (50, 59),
        Position.RG: (60, 69),
        Position.RT: (70, 79),
        Position.DE: (90, 99),
        Position.DT: (90, 99),
        Position.NT: (90, 99),
        Position.MLB: (50, 59),
        Position.ILB: (50, 59),
        Position.OLB: (50, 59),
        Position.CB: (20, 39),
        Position.FS: (20, 39),
        Position.SS: (40, 49),
        Position.K: (1, 9),
        Position.P: (1, 9),
        Position.LS: (40, 49),
    }
    low, high = ranges.get(position, (1, 99))
    return random.randint(low, high)


def generate_rookie(
    position: Position,
    overall_target: Optional[int] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    college: Optional[str] = None,
    draft_round: Optional[int] = None,
    draft_pick: Optional[int] = None,
    draft_year: Optional[int] = None,
    team_identity: Optional[TeamIdentity] = None,
) -> Player:
    """
    Generate a rookie player (fresh out of college).

    Rookies have:
    - Age 21-23
    - 0 years NFL experience
    - 0 years on team
    - Higher potential variance (boom or bust)
    - Draft information

    Args:
        position: Position to generate
        overall_target: Target overall (if None, varies by draft round)
        first_name: Specific first name
        last_name: Specific last name
        college: College attended
        draft_round: Round drafted (1-7, affects expected overall)
        draft_pick: Overall pick number
        draft_year: Year drafted
        team_identity: Team identity for scheme-specific tuning

    Returns:
        Generated rookie Player
    """
    # Rookie age distribution (most are 21-22, few 23)
    age_weights = [(21, 0.3), (22, 0.5), (23, 0.2)]
    ages, weights = zip(*age_weights)
    rookie_age = random.choices(ages, weights=weights)[0]

    # If no overall target, base on draft round
    if overall_target is None:
        if draft_round is not None:
            # First rounders are higher rated
            round_overall_ranges = {
                1: (72, 82),  # First round: 72-82
                2: (68, 76),  # Second round: 68-76
                3: (65, 73),  # Third round: 65-73
                4: (62, 70),  # Fourth round: 62-70
                5: (58, 67),  # Fifth round: 58-67
                6: (55, 65),  # Sixth round: 55-65
                7: (52, 62),  # Seventh round: 52-62
            }
            low, high = round_overall_ranges.get(draft_round, (55, 70))
            overall_target = random.randint(low, high)
        else:
            overall_target = random.randint(60, 75)

    # Rookies have higher potential variance (sleepers and busts)
    # Roll for potential modifier: can be negative (bust) or very positive (sleeper)
    bust_chance = 0.15  # 15% chance of being a bust (low potential)
    sleeper_chance = 0.10  # 10% chance of being a sleeper (very high potential)

    roll = random.random()
    if roll < bust_chance:
        # Bust: potential is only slightly above current
        potential_mod = random.uniform(-5, 2)
    elif roll < bust_chance + sleeper_chance:
        # Sleeper: potential is much higher than current
        potential_mod = random.uniform(10, 20)
    else:
        # Normal: standard potential gap
        potential_mod = random.uniform(0, 10)

    # Generate the player
    player = generate_player(
        position=position,
        overall_target=overall_target,
        first_name=first_name,
        last_name=last_name,
        team_identity=team_identity,
        age=rookie_age,
        potential_modifier=potential_mod,
        experience_years=0,
        years_on_team=0,
        college=college,
    )

    # Set draft information
    player.draft_round = draft_round
    player.draft_pick = draft_pick
    player.draft_year = draft_year

    # Rookies typically get 4-year contracts with slotted rookie scale
    if draft_round:
        player.contract_years = 4
        player.contract_year_remaining = 4

        # Use calibrated rookie salary scale based on draft position
        # Values in thousands (so 5000 = $5M)
        if draft_round == 1:
            if draft_pick and draft_pick <= 5:
                # Top 5 picks get mega deals
                player.salary = random.randint(8000, 15000)
                player.signing_bonus = random.randint(20000, 35000)
            elif draft_pick and draft_pick <= 15:
                player.salary = random.randint(4000, 8000)
                player.signing_bonus = random.randint(10000, 20000)
            else:
                player.salary = random.randint(2500, 5000)
                player.signing_bonus = random.randint(5000, 12000)
        elif draft_round == 2:
            player.salary = random.randint(1500, 3000)
            player.signing_bonus = random.randint(2000, 5000)
        elif draft_round == 3:
            player.salary = random.randint(1000, 2000)
            player.signing_bonus = random.randint(800, 2500)
        elif draft_round == 4:
            player.salary = random.randint(900, 1500)
            player.signing_bonus = random.randint(400, 1200)
        elif draft_round == 5:
            player.salary = random.randint(850, 1200)
            player.signing_bonus = random.randint(200, 600)
        elif draft_round == 6:
            player.salary = random.randint(800, 1000)
            player.signing_bonus = random.randint(100, 400)
        else:
            player.salary = random.randint(750, 950)  # 7th round / UDFA
            player.signing_bonus = random.randint(50, 200)

        player.signing_bonus_remaining = player.signing_bonus

    return player


def generate_draft_class(
    year: int,
    num_players: int = 260,
    team_identity: Optional[TeamIdentity] = None,
) -> list[Player]:
    """
    Generate a full draft class of rookies.

    Creates a realistic draft class with:
    - Clear tiers matching real NFL draft quality distribution
    - Gaussian variance within each tier
    - Position scarcity (elite QBs/LTs are rare)
    - Boom/bust variance (hidden gems and overdrafted busts)

    Real draft quality distribution:
    - Round 1 (~32): Elite talents, immediate starters
    - Rounds 2-3 (~64): Good starters, day-1 contributors
    - Rounds 4-5 (~64): Depth, special teamers, projects
    - Rounds 6-7 (~64): Long shots, camp bodies
    - UDFAs (~100+): Practice squad hopefuls

    Args:
        year: Draft year
        num_players: Number of players to generate
        team_identity: Optional team identity for filtering

    Returns:
        List of draft-eligible players (not yet assigned to teams)
    """
    draft_class = []

    # Draft tiers with Gaussian parameters
    # (tier_name, % of class, current_mean, current_std, potential_mean, potential_std)
    draft_tiers = [
        ("elite",       0.05, 76, 4, 90, 4),   # ~13 players - true 1st rounders
        ("day1",        0.08, 70, 4, 84, 4),   # ~20 players - late 1st / early 2nd
        ("day2",        0.15, 64, 4, 78, 5),   # ~40 players - rounds 2-3
        ("day3_early",  0.20, 57, 5, 70, 5),   # ~50 players - rounds 4-5
        ("day3_late",   0.25, 50, 5, 62, 6),   # ~65 players - rounds 6-7
        ("udfa",        0.27, 44, 5, 55, 6),   # ~70 players - undrafted free agents
    ]

    # Position distribution - how many of each position to generate
    # (position, count, max_elite)
    # max_elite = cap on how many can be in top 2 tiers
    position_counts = [
        (Position.QB, 16, 3),
        (Position.RB, 22, 4),
        (Position.FB, 4, 1),
        (Position.WR, 32, 5),
        (Position.TE, 14, 3),
        (Position.LT, 14, 3),
        (Position.LG, 10, 2),
        (Position.C, 8, 2),
        (Position.RG, 10, 2),
        (Position.RT, 10, 2),
        (Position.DE, 24, 4),
        (Position.DT, 16, 3),
        (Position.NT, 4, 1),
        (Position.MLB, 12, 2),
        (Position.ILB, 8, 2),
        (Position.OLB, 16, 3),
        (Position.CB, 26, 4),
        (Position.FS, 10, 2),
        (Position.SS, 10, 2),
        (Position.K, 4, 1),
        (Position.P, 4, 1),
        (Position.LS, 2, 0),
    ]

    for position, count, max_elite in position_counts:
        elite_count = 0

        for i in range(count):
            # Calculate which tier this player falls into based on position in list
            tier_roll = i / count  # 0.0 to ~1.0

            # Find appropriate tier
            cumulative = 0
            selected_tier = draft_tiers[-1]  # Default to UDFA
            for tier in draft_tiers:
                tier_name, pct, curr_mean, curr_std, pot_mean, pot_std = tier
                cumulative += pct
                if tier_roll < cumulative:
                    # Check elite cap
                    if tier_name in ("elite", "day1") and elite_count >= max_elite:
                        continue  # Skip to next tier
                    selected_tier = tier
                    if tier_name in ("elite", "day1"):
                        elite_count += 1
                    break

            tier_name, _, curr_mean, curr_std, pot_mean, pot_std = selected_tier

            # Generate ratings with Gaussian distribution
            current_overall = int(random.gauss(curr_mean, curr_std))
            potential = int(random.gauss(pot_mean, pot_std))

            # Clamp values
            current_overall = max(38, min(88, current_overall))
            potential = max(current_overall, min(99, potential))

            # Add boom/bust variance (8% hidden gems, 7% busts)
            roll = random.random()
            if roll < 0.08:
                # Hidden gem - much higher potential than tier suggests
                potential = min(99, potential + random.randint(10, 18))
            elif roll < 0.15:
                # Bust - potential barely above current
                potential = max(current_overall, min(current_overall + 5, potential - 8))

            # Generate the prospect
            rookie = _generate_draft_prospect(
                position=position,
                current_overall=current_overall,
                potential=potential,
                draft_year=year,
                tier_name=tier_name,
                team_identity=team_identity,
            )
            draft_class.append(rookie)

    # Sort by weighted combination of current + potential
    draft_class.sort(
        key=lambda p: (p.overall * 0.6 + p.potential * 0.4),
        reverse=True
    )

    return draft_class


def _generate_draft_prospect(
    position: Position,
    current_overall: int,
    potential: int,
    draft_year: int,
    tier_name: str = "day3_late",
    team_identity: Optional[TeamIdentity] = None,
) -> Player:
    """
    Generate a draft prospect with specific overall and potential targets.

    The tier_name is used to generate a "media grade" (projected_draft_round)
    that represents consensus opinion. This can diverge from actual ability
    to create busts (overrated) and gems (underrated).

    Per-attribute potentials are generated based on:
    - Growth category (physical attributes have lower ceilings)
    - Draft tier (elite prospects have higher ceilings overall)
    - Bust/gem status (affects perceived vs actual potential)
    """
    # Rookie age distribution
    age = random.choices([21, 22, 23], weights=[0.3, 0.5, 0.2])[0]

    # Calculate potential modifier to hit our target
    potential_mod = potential - current_overall

    # Generate player
    player = generate_player(
        position=position,
        overall_target=current_overall,
        team_identity=team_identity,
        age=age,
        potential_modifier=potential_mod,
        experience_years=0,
        years_on_team=0,
    )

    # Override potential to hit exact target (generate_player adds variance)
    player.attributes["potential"] = potential
    player.draft_year = draft_year

    # ==========================================================================
    # Generate Media Grade (projected_draft_round)
    # This is the CONSENSUS opinion, which can be wrong!
    # ==========================================================================

    # Base projection from tier
    tier_to_round = {
        "elite": 1,
        "day1": 1,       # Late 1st
        "day2": 2,       # Rounds 2-3
        "day3_early": 4, # Rounds 4-5
        "day3_late": 6,  # Rounds 6-7
        "udfa": None,    # Undrafted
    }
    base_round = tier_to_round.get(tier_name, 6)

    # Add variance to media perception
    # 15% chance of significant over/under rating (busts and gems)
    perception_roll = random.random()

    # Track bust/gem status for potential generation
    is_bust = False
    is_gem = False

    if base_round is not None:
        if perception_roll < 0.08:
            # BUST: Media overrates this player by 1-3 rounds
            # They look the part but won't pan out
            media_round = max(1, base_round - random.randint(1, 3))
            is_bust = True
        elif perception_roll < 0.15:
            # GEM: Media underrates this player by 1-3 rounds
            # Doesn't have the "look" but is actually good
            media_round = min(7, base_round + random.randint(1, 3))
            is_gem = True
        else:
            # Normal variance: +/- 1 round
            media_round = max(1, min(7, base_round + random.randint(-1, 1)))

        player.projected_draft_round = media_round
    else:
        # UDFA - 20% chance media sees them as late-round pick
        if random.random() < 0.20:
            player.projected_draft_round = random.randint(6, 7)
        else:
            player.projected_draft_round = None  # Undrafted projection

    # ==========================================================================
    # Generate Per-Attribute Potentials
    # Physical attributes have lower ceilings (genetics-limited)
    # Mental/technique attributes have higher ceilings (trainable)
    # ==========================================================================

    # Get current attributes as dict (excluding potential keys)
    current_attrs = {
        k: v for k, v in player.attributes._values.items()
        if not k.endswith("_potential") and k != "potential"
    }

    # Generate actual and perceived potentials
    actual_potentials, perceived_potentials = generate_all_potentials(
        attributes=current_attrs,
        tier=tier_name,
        is_bust=is_bust,
        is_gem=is_gem,
        scouted_percentage=0,  # Prospects start unscouted
    )

    # Store actual potentials in attributes (these are the true ceilings)
    for key, value in actual_potentials.items():
        player.attributes._values[key] = value

    # Store perceived potentials for scouting system (media/scout estimates)
    player.perceived_potentials = perceived_potentials

    # Contract details set when actually drafted - based on:
    # 1. Actual draft pick position (NFL slotted rookie scale)
    # 2. Character traits (holdouts, negotiations)
    # 3. The negotiation process
    # Leave as None for prospects
    player.contract_years = None
    player.contract_year_remaining = None
    player.salary = None
    player.signing_bonus = None
    player.signing_bonus_remaining = None

    # Generate combine measurables using calibrated data from NFL combine
    from huddle.generators.calibration import (
        generate_forty_time,
        generate_bench_reps,
        generate_vertical,
        generate_broad_jump,
    )

    pos = player.position.value

    # Use calibrated NFL combine data with position-specific distributions
    player.forty_yard_dash = generate_forty_time(pos)
    player.bench_press_reps = generate_bench_reps(pos)
    player.vertical_jump = generate_vertical(pos)
    player.broad_jump = generate_broad_jump(pos)

    return player


# Team colors for known team names (primary, secondary)
TEAM_COLORS: dict[str, tuple[str, str]] = {
    "Eagles": ("#004C54", "#A5ACAF"),
    "Cowboys": ("#003594", "#869397"),
    "Giants": ("#0B2265", "#A71930"),
    "Commanders": ("#5A1414", "#FFB612"),
    "Patriots": ("#002244", "#C60C30"),
    "Bills": ("#00338D", "#C60C30"),
    "Jets": ("#125740", "#FFFFFF"),
    "Dolphins": ("#008E97", "#F58220"),
    "Ravens": ("#241773", "#9E7C0C"),
    "Steelers": ("#FFB612", "#101820"),
    "Browns": ("#FF3C00", "#311D00"),
    "Bengals": ("#FB4F14", "#000000"),
    "Chiefs": ("#E31837", "#FFB81C"),
    "Raiders": ("#A5ACAF", "#000000"),
    "Chargers": ("#0080C6", "#FFC20E"),
    "Broncos": ("#FB4F14", "#002244"),
    "Texans": ("#03202F", "#A71930"),
    "Titans": ("#0C2340", "#4B92DB"),
    "Colts": ("#002C5F", "#A2AAAD"),
    "Jaguars": ("#006778", "#9F792C"),
    "Packers": ("#203731", "#FFB612"),
    "Bears": ("#0B162A", "#C83803"),
    "Vikings": ("#4F2683", "#FFC62F"),
    "Lions": ("#0076B6", "#B0B7BC"),
    "49ers": ("#AA0000", "#B3995D"),
    "Seahawks": ("#002244", "#69BE28"),
    "Rams": ("#003594", "#FFA300"),
    "Cardinals": ("#97233F", "#000000"),
    "Saints": ("#D3BC8D", "#101820"),
    "Falcons": ("#A71930", "#000000"),
    "Panthers": ("#0085CA", "#101820"),
    "Buccaneers": ("#D50A0A", "#FF7900"),
}


def _create_tendencies_from_identity(identity: TeamIdentity) -> TeamTendencies:
    """
    Create TeamTendencies from a TeamIdentity.

    Maps the gameplay-focused identity to full AI decision-making tendencies.
    """
    # Map identity offense style to scheme
    offense_scheme_map = {
        "power_run": OffensiveScheme.POWER_RUN,
        "air_raid": OffensiveScheme.AIR_RAID,
        "west_coast": OffensiveScheme.WEST_COAST,
        "spread": OffensiveScheme.SPREAD,
        "rpo": OffensiveScheme.RPO_HEAVY,
    }

    # Map identity defense style to scheme
    defense_scheme_map = {
        "aggressive": DefensiveScheme.BLITZ_HEAVY,
        "conservative": DefensiveScheme.TAMPA_TWO,
        "balanced": DefensiveScheme.FOUR_THREE,
        "3-4": DefensiveScheme.THREE_FOUR,
        "4-3": DefensiveScheme.FOUR_THREE,
    }

    # Determine schemes from identity
    # TeamIdentity has offense_style and defense_style as strings or may not have them
    offense_style = getattr(identity, 'offense_style', 'balanced')
    defense_style = getattr(identity, 'defense_style', 'balanced')

    offensive_scheme = offense_scheme_map.get(offense_style, OffensiveScheme.PRO_STYLE)
    defensive_scheme = defense_scheme_map.get(defense_style, DefensiveScheme.FOUR_THREE)

    # Generate random AI decision-making tendencies
    tendencies = TeamTendencies.generate_random()

    # Override gameplay tendencies from identity
    tendencies.run_tendency = identity.run_tendency
    tendencies.aggression = identity.aggression
    tendencies.blitz_tendency = identity.blitz_tendency
    tendencies.offensive_scheme = offensive_scheme
    tendencies.defensive_scheme = defensive_scheme

    return tendencies


def generate_team(
    name: str,
    city: str,
    abbreviation: str,
    overall_range: tuple[int, int] = (70, 85),
    primary_color: Optional[str] = None,
    secondary_color: Optional[str] = None,
    identity: Optional[TeamIdentity] = None,
) -> Team:
    """
    Generate a complete team with full 53-player roster.

    Args:
        name: Team name (e.g., "Patriots")
        city: Team city (e.g., "New England")
        abbreviation: Team abbreviation (e.g., "NE")
        overall_range: Range of overall ratings for players
        primary_color: Optional hex color override
        secondary_color: Optional hex color override
        identity: Optional team identity for scheme-specific generation

    Returns:
        Generated Team with full 53-player roster
    """
    # Get colors from known teams or use defaults
    if primary_color is None or secondary_color is None:
        default_colors = TEAM_COLORS.get(name, ("#003087", "#FFFFFF"))
        primary_color = primary_color or default_colors[0]
        secondary_color = secondary_color or default_colors[1]

    # Generate team identity if not provided
    if identity is None:
        identity = create_random_identity()

    # Create tendencies from identity + random AI behaviors
    tendencies = _create_tendencies_from_identity(identity)

    team = Team(
        name=name,
        city=city,
        abbreviation=abbreviation,
        primary_color=primary_color,
        secondary_color=secondary_color,
        tendencies=tendencies,
    )

    # Full 53-player roster depth chart
    # Format: slot -> (Position, depth_level where 1=starter)
    # depth_level affects overall target: starters get +5, backups get progressively lower
    roster_slots: dict[str, tuple[Position, int]] = {
        # Quarterbacks (3)
        "QB1": (Position.QB, 1),
        "QB2": (Position.QB, 2),
        "QB3": (Position.QB, 3),
        # Running Backs (4)
        "RB1": (Position.RB, 1),
        "RB2": (Position.RB, 2),
        "RB3": (Position.RB, 3),
        "RB4": (Position.RB, 3),
        "FB1": (Position.FB, 1),
        # Wide Receivers (6)
        "WR1": (Position.WR, 1),
        "WR2": (Position.WR, 1),  # WR2 is also a starter-quality player
        "WR3": (Position.WR, 2),
        "WR4": (Position.WR, 2),
        "WR5": (Position.WR, 3),
        "WR6": (Position.WR, 3),
        # Tight Ends (3)
        "TE1": (Position.TE, 1),
        "TE2": (Position.TE, 2),
        "TE3": (Position.TE, 3),
        # Offensive Line (9)
        "LT1": (Position.LT, 1),
        "LT2": (Position.LT, 2),
        "LG1": (Position.LG, 1),
        "LG2": (Position.LG, 2),
        "C1": (Position.C, 1),
        "C2": (Position.C, 2),
        "RG1": (Position.RG, 1),
        "RG2": (Position.RG, 2),
        "RT1": (Position.RT, 1),
        "RT2": (Position.RT, 2),
        # Defensive Line (6) - varies by scheme
        "DE1": (Position.DE, 1),
        "DE2": (Position.DE, 1),
        "DE3": (Position.DE, 2),
        "DT1": (Position.DT, 1),
        "DT2": (Position.DT, 2),
        "NT1": (Position.NT, 1),
        # Linebackers (7)
        "MLB1": (Position.MLB, 1),
        "MLB2": (Position.MLB, 2),
        "OLB1": (Position.OLB, 1),
        "OLB2": (Position.OLB, 1),
        "OLB3": (Position.OLB, 2),
        "ILB1": (Position.ILB, 1),
        "ILB2": (Position.ILB, 2),
        # Defensive Backs (10)
        "CB1": (Position.CB, 1),
        "CB2": (Position.CB, 1),
        "CB3": (Position.CB, 2),
        "CB4": (Position.CB, 2),
        "CB5": (Position.CB, 3),
        "CB6": (Position.CB, 3),
        "FS1": (Position.FS, 1),
        "FS2": (Position.FS, 2),
        "SS1": (Position.SS, 1),
        "SS2": (Position.SS, 2),
        # Special Teams (3)
        "K1": (Position.K, 1),
        "P1": (Position.P, 1),
        "LS1": (Position.LS, 1),
    }

    for slot, (position, depth) in roster_slots.items():
        # Calculate target overall based on depth
        if depth == 1:
            # Starters: top of range
            target_ovr = random.randint(overall_range[0] + 5, overall_range[1])
        elif depth == 2:
            # Backups: middle of range
            target_ovr = random.randint(overall_range[0], overall_range[1] - 5)
        else:
            # Third string: bottom of range
            target_ovr = random.randint(overall_range[0] - 5, overall_range[1] - 10)

        target_ovr = max(55, min(99, target_ovr))

        # Young players on bottom of depth chart tend to have higher potential
        potential_mod = 0.0
        if depth >= 2:
            potential_mod = random.uniform(0, 5)  # Developmental players

        # Generate player with team identity
        player = generate_player(
            position,
            overall_target=target_ovr,
            team_identity=identity,
            potential_modifier=potential_mod,
        )
        team.roster.add_player(player)
        team.roster.depth_chart.set(slot, player.id)

    return team


def generate_team_with_identity(
    name: str,
    city: str,
    abbreviation: str,
    identity_type: str = "balanced",
    overall_range: tuple[int, int] = (70, 85),
) -> Team:
    """
    Generate a team with a specific identity type.

    Args:
        name: Team name
        city: Team city
        abbreviation: Team abbreviation
        identity_type: One of "power_run", "air_raid", "west_coast", "defensive", "balanced", "random"
        overall_range: Range for player ratings

    Returns:
        Generated Team with identity-specific roster
    """
    from huddle.core.models.team_identity import (
        create_identity_air_raid,
        create_identity_balanced,
        create_identity_defensive,
        create_identity_power_run,
        create_identity_west_coast,
        create_random_identity,
    )

    identity_creators = {
        "power_run": create_identity_power_run,
        "air_raid": create_identity_air_raid,
        "west_coast": create_identity_west_coast,
        "defensive": create_identity_defensive,
        "balanced": create_identity_balanced,
        "random": create_random_identity,
    }

    creator = identity_creators.get(identity_type, create_random_identity)
    identity = creator()

    return generate_team(
        name=name,
        city=city,
        abbreviation=abbreviation,
        overall_range=overall_range,
        identity=identity,
    )


def assign_veteran_contract(player: Player) -> None:
    """
    Assign a calibrated contract to a veteran player based on position and overall.

    Uses NFL contract data to determine appropriate market value.
    Modifies player in place.
    """
    from huddle.generators.calibration import calculate_contract_value

    contract = calculate_contract_value(
        position=player.position.value,
        overall=player.overall,
        age=player.age,
    )

    # Contract values are in millions, we store in thousands
    player.salary = int(contract["apy_millions"] * 1000)
    player.contract_years = contract["years"]
    player.contract_year_remaining = contract["years"]

    # Signing bonus is total guaranteed spread across years
    total_guaranteed = contract["guaranteed_millions"] * 1000
    player.signing_bonus = int(total_guaranteed)
    player.signing_bonus_remaining = int(total_guaranteed / contract["years"])


def assign_contracts_to_roster(roster) -> None:
    """
    Assign calibrated contracts to all players on a roster.

    Players without contracts (or with expired contracts) get new ones.
    """
    for player in roster.players.values():
        if player.salary is None or player.salary == 0:
            assign_veteran_contract(player)
