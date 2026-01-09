"""
Demographics data for realistic player portrait generation.
"""

# Hair color by skin tone (percentages)
# Skin tones 0-7: 0=lightest (Scandinavian), 7=darkest
# White players: tones 0-2
# Black players: tones 3-7

HAIR_COLOR_BY_SKIN_TONE = {
    # White players (lighter skin tones)
    0: {  # Lightest / Scandinavian - highest blonde/red
        "black": 3.0,
        "dark_brown": 8.0,
        "brown": 6.0,
        "light_brown": 18.0,
        "blonde": 50.0,
        "auburn": 5.0,
        "red": 10.0,
    },
    1: {  # Scandinavian-ish
        "black": 5.0,
        "dark_brown": 12.0,
        "brown": 8.0,
        "light_brown": 15.0,
        "blonde": 48.0,
        "auburn": 5.0,
        "red": 7.0,
    },
    2: {  # White, less Scandinavian
        "black": 10.0,
        "dark_brown": 20.0,
        "brown": 12.0,
        "light_brown": 10.0,
        "blonde": 40.0,
        "auburn": 4.5,
        "red": 3.5,
    },
    # Black players (darker skin tones)
    3: {  # Transition / lightest Black
        "black": 70.0,
        "dark_brown": 14.0,
        "brown": 6.0,
        "light_brown": 2.0,
        "blonde": 3.0,
        "auburn": 3.5,
        "red": 1.5,
    },
    4: {
        "black": 75.0,
        "dark_brown": 12.0,
        "brown": 5.0,
        "light_brown": 1.0,
        "blonde": 2.0,
        "auburn": 3.5,
        "red": 1.5,
    },
    5: {
        "black": 78.0,
        "dark_brown": 11.0,
        "brown": 4.5,
        "light_brown": 0.7,
        "blonde": 1.8,
        "auburn": 2.5,
        "red": 1.5,
    },
    6: {
        "black": 80.0,
        "dark_brown": 10.0,
        "brown": 4.0,
        "light_brown": 0.5,
        "blonde": 1.5,
        "auburn": 2.5,
        "red": 1.5,
    },
    7: {  # Darkest
        "black": 82.0,
        "dark_brown": 9.0,
        "brown": 3.5,
        "light_brown": 0.3,
        "blonde": 1.2,
        "auburn": 2.5,
        "red": 1.5,
    },
}

# Age-related colors (applied separately based on age)
GRAY_HAIR_COLORS = ["gray", "silver", "white"]

# Styled/dyed colors (optional, player choice)
STYLED_HAIR_COLORS = ["platinum"]

# Gray/white hair probability by age
# Percentage chance of having significant gray/white
GRAY_HAIR_BY_AGE = {
    20: 0.0,
    25: 2.0,
    30: 10.0,
    35: 25.0,
    40: 50.0,
    45: 70.0,
    50: 85.0,
}

# NFL position demographics (percentage Black players)
# Source: NFL demographic studies, 2024
NFL_POSITION_DEMOGRAPHICS = {
    # Offense - Skill
    "QB": 40.0,           # Boosted for variety (real NFL ~30%)
    "RB": 85.0,
    "FB": 60.0,
    "WR": 80.0,
    "TE": 55.0,

    # Offense - Line (all variants)
    "LT": 40.0,
    "RT": 40.0,
    "LG": 40.0,
    "RG": 40.0,
    "C": 35.0,

    # Defense - Line
    "DE": 70.0,
    "DT": 75.0,
    "NT": 75.0,           # Similar to DT

    # Defense - Linebackers (all variants)
    "MLB": 65.0,
    "OLB": 65.0,
    "ILB": 65.0,

    # Defense - Secondary (all variants)
    "CB": 95.0,           # Very high - historically one of highest
    "FS": 70.0,
    "SS": 70.0,

    # Special Teams
    "K": 15.0,            # Boosted for variety (real NFL ~5%)
    "P": 15.0,            # Boosted for variety (real NFL ~5%)
    "LS": 15.0,
}

# NFL off-field leadership demographics (for reference)
# Source: NFL 2024 diversity report
NFL_LEADERSHIP_DEMOGRAPHICS = {
    "team_president": 3.0,    # Black
    "head_coach": 8.0,        # Black
    "general_manager": 10.0,  # Black
}

# Skin tone mapping (0-7 scale, lightest to darkest)
# 0 = lightest (Scandinavian), 7 = darkest
# White players: 0-2, Black players: 3-7
SKIN_TONE_RANGES = {
    "white": (0, 2),         # Lighter skin tones
    "scandinavian": (0, 1),  # Lightest, high blonde/red
    "black": (3, 7),         # Darker skin tones
    "hispanic": (2, 4),      # Mid-range
    "asian": (1, 3),         # Light-mid range
    "mixed": (1, 5),         # Wide range
}


def get_hair_color_weights(skin_tone: int, include_styled: bool = False) -> dict[str, float]:
    """Get hair color weights for random selection based on skin tone.

    Args:
        skin_tone: Skin tone index 0-7
        include_styled: If True, includes platinum as an option
    """
    # Clamp to valid range
    skin_tone = max(0, min(7, skin_tone))
    weights = dict(HAIR_COLOR_BY_SKIN_TONE[skin_tone])

    if include_styled:
        # Small chance of styled hair colors
        weights["platinum"] = 0.5

    return weights


def get_position_skin_tone_weights(position: str) -> dict[int, float]:
    """Get skin tone weights based on position demographics.

    Returns weights for skin tones 0-7 based on position's
    racial demographics.

    Scale: 0=lightest (white/Scandinavian), 7=darkest (Black)
    White players: 0-2, Black players: 3-7
    """
    black_pct = NFL_POSITION_DEMOGRAPHICS.get(position, 50.0)
    white_pct = 100.0 - black_pct

    # Distribute across skin tone ranges
    weights = {}

    # White player skin tones (0-2) - 3 tones
    for tone in range(3):
        weights[tone] = white_pct / 3.0

    # Black player skin tones (3-7) - 5 tones
    for tone in range(3, 8):
        weights[tone] = black_pct / 5.0

    return weights


def get_hair_color_for_player(skin_tone: int, age: int, include_styled: bool = False) -> dict[str, float]:
    """Get complete hair color weights for a player.

    Combines skin-tone-based natural colors with age-based gray probability.

    Args:
        skin_tone: Skin tone index 0-7
        age: Player age in years
        include_styled: If True, includes platinum as an option
    """
    import random

    weights = get_hair_color_weights(skin_tone, include_styled)

    # Check if player should have gray hair
    gray_prob = should_have_gray_hair(age)
    if random.random() * 100 < gray_prob:
        # Replace with gray variant
        # Older = more likely to be fully white vs just gray
        if age >= 45:
            weights = {"white": 40.0, "silver": 35.0, "gray": 25.0}
        elif age >= 35:
            weights = {"gray": 50.0, "silver": 30.0, "white": 20.0}
        else:
            weights = {"gray": 70.0, "silver": 25.0, "white": 5.0}

    return weights


def should_have_gray_hair(age: int) -> float:
    """Get probability of gray/white hair based on age."""
    # Find bracketing ages
    ages = sorted(GRAY_HAIR_BY_AGE.keys())

    if age <= ages[0]:
        return GRAY_HAIR_BY_AGE[ages[0]]
    if age >= ages[-1]:
        return GRAY_HAIR_BY_AGE[ages[-1]]

    # Interpolate
    for i, a in enumerate(ages[:-1]):
        if ages[i] <= age < ages[i + 1]:
            lower_age, upper_age = ages[i], ages[i + 1]
            lower_pct, upper_pct = GRAY_HAIR_BY_AGE[lower_age], GRAY_HAIR_BY_AGE[upper_age]
            t = (age - lower_age) / (upper_age - lower_age)
            return lower_pct + t * (upper_pct - lower_pct)

    return 0.0
