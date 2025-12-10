"""Player and team generation."""

import random
from typing import Optional

from huddle.core.attributes import PlayerAttributes
from huddle.core.enums import Position
from huddle.core.models.player import Player
from huddle.core.models.team import Team
from huddle.core.models.team_identity import TeamIdentity, create_random_identity
from huddle.core.models.tendencies import TeamTendencies, OffensiveScheme, DefensiveScheme

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
POSITION_TEMPLATES: dict[Position, dict[str, tuple[int, int]]] = {
    Position.QB: {
        # Physical
        "speed": (70, 10),
        "acceleration": (72, 8),
        "agility": (70, 10),
        "strength": (60, 8),
        "stamina": (80, 8),
        "jumping": (65, 10),
        # Passing
        "throw_power": (85, 8),
        "throw_accuracy_short": (82, 8),
        "throw_accuracy_med": (78, 10),
        "throw_accuracy_deep": (72, 12),
        "throw_on_run": (70, 12),
        "play_action": (75, 10),
        # Rushing (for scrambling)
        "carrying": (65, 10),
        "elusiveness": (65, 12),
        "ball_carrier_vision": (60, 10),
        # Mental
        "awareness": (80, 10),
        "learning": (75, 12),
    },
    Position.RB: {
        # Physical
        "speed": (88, 6),
        "acceleration": (88, 5),
        "agility": (85, 6),
        "strength": (70, 8),
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
        # Physical
        "speed": (72, 8),
        "acceleration": (75, 8),
        "agility": (70, 8),
        "strength": (82, 6),
        "stamina": (80, 8),
        # Rushing
        "carrying": (70, 10),
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
        # Physical
        "speed": (90, 5),
        "acceleration": (88, 5),
        "agility": (85, 6),
        "strength": (60, 10),
        "stamina": (78, 8),
        "jumping": (80, 10),
        # Receiving
        "catching": (85, 6),
        "route_running": (82, 8),
        "release": (78, 8),
        "catch_in_traffic": (75, 10),
        "spectacular_catch": (72, 12),
        # Rushing (after catch)
        "elusiveness": (75, 10),
        "break_tackle": (65, 12),
        "juke_move": (72, 10),
        # Special teams
        "kick_return": (72, 12),
        # Mental
        "awareness": (72, 10),
        "learning": (72, 10),
    },
    Position.TE: {
        # Physical
        "speed": (80, 6),
        "acceleration": (78, 6),
        "agility": (72, 8),
        "strength": (78, 8),
        "stamina": (78, 8),
        "jumping": (75, 10),
        # Receiving
        "catching": (80, 8),
        "route_running": (72, 10),
        "catch_in_traffic": (78, 8),
        "release": (70, 10),
        # Rushing
        "break_tackle": (72, 8),
        "stiff_arm": (70, 10),
        # Blocking
        "run_block": (70, 10),
        "pass_block": (65, 10),
        "impact_blocking": (68, 10),
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
        # Physical
        "speed": (78, 6),
        "acceleration": (80, 6),
        "agility": (75, 8),
        "strength": (82, 8),
        "stamina": (78, 8),
        # Defense - Pass Rush
        "block_shedding": (82, 8),
        "finesse_moves": (78, 10),
        "power_moves": (78, 10),
        # Defense - Tackling
        "tackle": (75, 8),
        "pursuit": (80, 8),
        "hit_power": (75, 10),
        # Mental
        "play_recognition": (72, 10),
        "awareness": (70, 10),
        "learning": (68, 10),
    },
    Position.DT: {
        # Physical
        "speed": (55, 8),
        "acceleration": (60, 8),
        "agility": (55, 10),
        "strength": (92, 5),
        "stamina": (75, 8),
        # Defense
        "block_shedding": (85, 6),
        "power_moves": (82, 8),
        "finesse_moves": (65, 12),
        "tackle": (78, 8),
        "pursuit": (65, 10),
        "hit_power": (80, 8),
        # Mental
        "play_recognition": (70, 10),
        "awareness": (68, 10),
        "learning": (65, 10),
    },
    Position.NT: {
        # Physical (even bigger/stronger than DT)
        "speed": (48, 8),
        "acceleration": (52, 8),
        "agility": (48, 10),
        "strength": (95, 4),
        "stamina": (72, 10),
        # Defense
        "block_shedding": (88, 5),
        "power_moves": (85, 6),
        "tackle": (78, 8),
        "pursuit": (55, 12),
        "hit_power": (82, 8),
        # Mental
        "play_recognition": (68, 10),
        "awareness": (65, 10),
        "learning": (62, 10),
    },
    Position.MLB: {
        # Physical
        "speed": (78, 6),
        "acceleration": (80, 6),
        "agility": (75, 8),
        "strength": (80, 8),
        "stamina": (82, 6),
        "jumping": (72, 10),
        # Defense - Tackling
        "tackle": (88, 5),
        "pursuit": (85, 6),
        "hit_power": (80, 8),
        "block_shedding": (75, 8),
        # Defense - Coverage
        "zone_coverage": (72, 10),
        "man_coverage": (65, 12),
        # Mental (MLBs make defensive calls)
        "play_recognition": (82, 8),
        "awareness": (80, 8),
        "learning": (75, 10),
    },
    Position.ILB: {
        # Physical
        "speed": (80, 6),
        "acceleration": (82, 6),
        "agility": (78, 8),
        "strength": (78, 8),
        "stamina": (82, 6),
        "jumping": (72, 10),
        # Defense
        "tackle": (85, 6),
        "pursuit": (85, 6),
        "hit_power": (78, 8),
        "block_shedding": (72, 10),
        "zone_coverage": (75, 10),
        "man_coverage": (68, 12),
        # Mental
        "play_recognition": (78, 8),
        "awareness": (75, 10),
        "learning": (72, 10),
    },
    Position.OLB: {
        # Physical
        "speed": (82, 6),
        "acceleration": (84, 6),
        "agility": (80, 8),
        "strength": (75, 8),
        "stamina": (80, 8),
        "jumping": (75, 10),
        # Defense
        "tackle": (82, 6),
        "pursuit": (85, 6),
        "finesse_moves": (72, 10),
        "power_moves": (68, 12),
        "block_shedding": (70, 10),
        "zone_coverage": (70, 10),
        "man_coverage": (65, 10),
        "hit_power": (75, 10),
        # Mental
        "play_recognition": (75, 10),
        "awareness": (72, 10),
        "learning": (70, 10),
    },
    Position.CB: {
        # Physical
        "speed": (92, 4),
        "acceleration": (90, 4),
        "agility": (88, 5),
        "strength": (60, 10),
        "stamina": (80, 8),
        "jumping": (82, 8),
        # Defense - Coverage
        "man_coverage": (85, 6),
        "zone_coverage": (80, 8),
        "press": (78, 10),
        # Defense - Tackling
        "tackle": (65, 10),
        "pursuit": (75, 8),
        "hit_power": (55, 12),
        # Special teams
        "kick_return": (75, 12),
        # Mental
        "play_recognition": (75, 10),
        "awareness": (75, 10),
        "learning": (72, 10),
    },
    Position.FS: {
        # Physical
        "speed": (90, 5),
        "acceleration": (88, 5),
        "agility": (85, 6),
        "strength": (65, 10),
        "stamina": (82, 6),
        "jumping": (80, 10),
        # Defense - Coverage
        "zone_coverage": (85, 6),
        "man_coverage": (72, 10),
        # Defense - Tackling
        "tackle": (72, 8),
        "pursuit": (80, 8),
        "hit_power": (70, 10),
        # Mental
        "play_recognition": (82, 8),
        "awareness": (80, 8),
        "learning": (75, 10),
    },
    Position.SS: {
        # Physical
        "speed": (85, 6),
        "acceleration": (85, 6),
        "agility": (82, 8),
        "strength": (75, 8),
        "stamina": (82, 6),
        "jumping": (78, 10),
        # Defense - Coverage
        "zone_coverage": (78, 8),
        "man_coverage": (72, 10),
        # Defense - Tackling
        "tackle": (82, 6),
        "pursuit": (80, 8),
        "hit_power": (82, 8),
        # Mental
        "play_recognition": (78, 8),
        "awareness": (75, 10),
        "learning": (72, 10),
    },
    Position.K: {
        # Physical (kickers are athletes too!)
        "speed": (60, 10),
        "acceleration": (62, 10),
        "strength": (60, 12),
        "stamina": (70, 10),
        # Special Teams
        "kick_power": (85, 8),
        "kick_accuracy": (85, 8),
        # Mental (pressure situations)
        "awareness": (75, 12),
        "learning": (70, 10),
    },
    Position.P: {
        # Physical
        "speed": (62, 10),
        "acceleration": (64, 10),
        "strength": (65, 10),
        "stamina": (70, 10),
        # Special Teams
        "kick_power": (88, 6),
        "kick_accuracy": (75, 10),
        # Mental
        "awareness": (72, 12),
        "learning": (68, 10),
    },
    Position.LS: {
        # Long Snapper
        "speed": (55, 8),
        "strength": (72, 10),
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

    # Generate physicals
    height_params, weight_params = POSITION_PHYSICALS.get(
        position, ((72, 3), (215, 20))
    )
    height = int(random.gauss(height_params[0], height_params[1]))
    weight = int(random.gauss(weight_params[0], weight_params[1]))

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

    return Player(
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

    # Rookies typically get 4-year contracts
    if draft_round:
        player.contract_years = 4
        player.contract_year_remaining = 4
        # Rookie salary based on draft position (simplified)
        if draft_round == 1:
            player.salary = random.randint(5000, 15000)  # $5M-15M
            player.signing_bonus = random.randint(10000, 30000)  # $10M-30M bonus
        elif draft_round == 2:
            player.salary = random.randint(2000, 5000)
            player.signing_bonus = random.randint(3000, 8000)
        elif draft_round <= 4:
            player.salary = random.randint(1000, 2500)
            player.signing_bonus = random.randint(500, 3000)
        else:
            player.salary = random.randint(800, 1200)  # League minimum range
            player.signing_bonus = random.randint(100, 500)

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
    - Clear tiers (elite prospects, solid starters, depth players)
    - Position scarcity (elite QBs/LTs are rare)
    - Boom/bust variance (hidden gems and overdrafted busts)
    - Realistic position distribution

    Args:
        year: Draft year
        num_players: Number of players to generate
        team_identity: Optional team identity for filtering

    Returns:
        List of draft-eligible players (not yet assigned to teams)
    """
    draft_class = []

    # Position distribution with target counts and elite prospect slots
    # (position, total_count, elite_slots, premium_position)
    # Elite slots = how many can be 85+ potential franchise players
    position_config = [
        (Position.QB, 16, 2, True),      # 2 franchise QBs per class max
        (Position.RB, 22, 3, False),     # RBs can be elite
        (Position.FB, 4, 0, False),      # FBs rarely elite
        (Position.WR, 32, 4, False),     # Several elite WR prospects
        (Position.TE, 14, 2, False),     # 1-2 elite TEs
        (Position.LT, 14, 2, True),      # Premium position - elite LTs rare
        (Position.LG, 10, 1, False),
        (Position.C, 8, 1, False),
        (Position.RG, 10, 1, False),
        (Position.RT, 10, 1, False),
        (Position.DE, 24, 3, True),      # Edge rushers premium
        (Position.DT, 16, 2, False),
        (Position.NT, 4, 1, False),
        (Position.MLB, 12, 2, False),
        (Position.ILB, 8, 1, False),
        (Position.OLB, 16, 2, False),
        (Position.CB, 26, 3, True),      # Corners are premium
        (Position.FS, 10, 1, False),
        (Position.SS, 10, 1, False),
        (Position.K, 4, 1, False),
        (Position.P, 4, 1, False),
        (Position.LS, 2, 0, False),
    ]

    for position, count, elite_slots, is_premium in position_config:
        for i in range(count):
            # Determine prospect tier
            if i < elite_slots:
                # Elite tier: potential 88-99, current 78-88
                tier = "elite"
                potential = random.randint(88, 99)
                # Current overall is lower - they haven't developed yet
                current_overall = random.randint(max(70, potential - 18), potential - 5)
            elif i < elite_slots + int(count * 0.25):
                # Starter tier: potential 80-90, current 72-82
                tier = "starter"
                potential = random.randint(80, 90)
                current_overall = random.randint(max(68, potential - 15), potential - 3)
            elif i < int(count * 0.6):
                # Solid tier: potential 72-82, current 65-75
                tier = "solid"
                potential = random.randint(72, 82)
                current_overall = random.randint(max(62, potential - 12), potential - 2)
            else:
                # Depth tier: potential 60-75, current 55-68
                tier = "depth"
                potential = random.randint(60, 75)
                current_overall = random.randint(max(52, potential - 15), potential)

            # Add boom/bust variance
            roll = random.random()
            if roll < 0.08:
                # Hidden gem - low current but very high potential (8% chance)
                potential = min(99, potential + random.randint(8, 15))
            elif roll < 0.15:
                # Bust - looks good but low ceiling (7% chance)
                potential = max(55, current_overall + random.randint(-3, 5))

            # Premium positions get slight boost to make them more valuable
            if is_premium and tier == "elite":
                current_overall = min(92, current_overall + random.randint(0, 3))

            # Generate the rookie with our calculated ratings
            rookie = _generate_draft_prospect(
                position=position,
                current_overall=current_overall,
                potential=potential,
                draft_year=year,
                team_identity=team_identity,
            )
            draft_class.append(rookie)

    # Sort by a combination of current overall and potential (scouts see both)
    # Weight current slightly more since that's what they'll contribute immediately
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
    team_identity: Optional[TeamIdentity] = None,
) -> Player:
    """Generate a draft prospect with specific overall and potential targets."""
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

    # Rookie contract
    player.contract_years = 4
    player.contract_year_remaining = 4

    # Salary based on projected draft position (using overall as proxy)
    if current_overall >= 80:
        player.salary = random.randint(5000, 15000)
        player.signing_bonus = random.randint(10000, 30000)
    elif current_overall >= 72:
        player.salary = random.randint(2000, 5000)
        player.signing_bonus = random.randint(3000, 8000)
    elif current_overall >= 65:
        player.salary = random.randint(1000, 2500)
        player.signing_bonus = random.randint(500, 3000)
    else:
        player.salary = random.randint(800, 1200)
        player.signing_bonus = random.randint(100, 500)

    player.signing_bonus_remaining = player.signing_bonus

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
