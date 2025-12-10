"""
NFL Team and League Structure Data.

This module contains the official NFL structure:
- 32 teams
- 2 conferences (AFC, NFC)
- 8 divisions (4 per conference)
- Team metadata (names, cities, abbreviations, colors)
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class Conference(Enum):
    """NFL Conferences."""
    AFC = "AFC"
    NFC = "NFC"


class Division(Enum):
    """NFL Divisions."""
    # AFC
    AFC_EAST = "AFC East"
    AFC_NORTH = "AFC North"
    AFC_SOUTH = "AFC South"
    AFC_WEST = "AFC West"
    # NFC
    NFC_EAST = "NFC East"
    NFC_NORTH = "NFC North"
    NFC_SOUTH = "NFC South"
    NFC_WEST = "NFC West"

    @property
    def conference(self) -> Conference:
        """Get the conference this division belongs to."""
        if self.name.startswith("AFC"):
            return Conference.AFC
        return Conference.NFC


@dataclass(frozen=True)
class NFLTeamData:
    """
    Static data for an NFL team.

    This is the "template" data - immutable information about each franchise.
    """
    name: str  # "Patriots"
    city: str  # "New England"
    abbreviation: str  # "NE"
    division: Division
    primary_color: str  # Hex color
    secondary_color: str
    stadium: str
    # Team identity tendencies (historical/default)
    default_identity: str = "balanced"  # power_run, air_raid, west_coast, defensive, balanced


# =============================================================================
# Official NFL Team Data (32 Teams)
# =============================================================================

NFL_TEAMS: dict[str, NFLTeamData] = {
    # =========================================================================
    # AFC EAST
    # =========================================================================
    "BUF": NFLTeamData(
        name="Bills",
        city="Buffalo",
        abbreviation="BUF",
        division=Division.AFC_EAST,
        primary_color="#00338D",
        secondary_color="#C60C30",
        stadium="Highmark Stadium",
        default_identity="balanced",
    ),
    "MIA": NFLTeamData(
        name="Dolphins",
        city="Miami",
        abbreviation="MIA",
        division=Division.AFC_EAST,
        primary_color="#008E97",
        secondary_color="#F58220",
        stadium="Hard Rock Stadium",
        default_identity="air_raid",
    ),
    "NE": NFLTeamData(
        name="Patriots",
        city="New England",
        abbreviation="NE",
        division=Division.AFC_EAST,
        primary_color="#002244",
        secondary_color="#C60C30",
        stadium="Gillette Stadium",
        default_identity="defensive",
    ),
    "NYJ": NFLTeamData(
        name="Jets",
        city="New York",
        abbreviation="NYJ",
        division=Division.AFC_EAST,
        primary_color="#125740",
        secondary_color="#000000",
        stadium="MetLife Stadium",
        default_identity="balanced",
    ),

    # =========================================================================
    # AFC NORTH
    # =========================================================================
    "BAL": NFLTeamData(
        name="Ravens",
        city="Baltimore",
        abbreviation="BAL",
        division=Division.AFC_NORTH,
        primary_color="#241773",
        secondary_color="#9E7C0C",
        stadium="M&T Bank Stadium",
        default_identity="power_run",
    ),
    "CIN": NFLTeamData(
        name="Bengals",
        city="Cincinnati",
        abbreviation="CIN",
        division=Division.AFC_NORTH,
        primary_color="#FB4F14",
        secondary_color="#000000",
        stadium="Paycor Stadium",
        default_identity="balanced",
    ),
    "CLE": NFLTeamData(
        name="Browns",
        city="Cleveland",
        abbreviation="CLE",
        division=Division.AFC_NORTH,
        primary_color="#FF3C00",
        secondary_color="#311D00",
        stadium="Cleveland Browns Stadium",
        default_identity="power_run",
    ),
    "PIT": NFLTeamData(
        name="Steelers",
        city="Pittsburgh",
        abbreviation="PIT",
        division=Division.AFC_NORTH,
        primary_color="#FFB612",
        secondary_color="#101820",
        stadium="Acrisure Stadium",
        default_identity="defensive",
    ),

    # =========================================================================
    # AFC SOUTH
    # =========================================================================
    "HOU": NFLTeamData(
        name="Texans",
        city="Houston",
        abbreviation="HOU",
        division=Division.AFC_SOUTH,
        primary_color="#03202F",
        secondary_color="#A71930",
        stadium="NRG Stadium",
        default_identity="balanced",
    ),
    "IND": NFLTeamData(
        name="Colts",
        city="Indianapolis",
        abbreviation="IND",
        division=Division.AFC_SOUTH,
        primary_color="#002C5F",
        secondary_color="#A2AAAD",
        stadium="Lucas Oil Stadium",
        default_identity="power_run",
    ),
    "JAX": NFLTeamData(
        name="Jaguars",
        city="Jacksonville",
        abbreviation="JAX",
        division=Division.AFC_SOUTH,
        primary_color="#006778",
        secondary_color="#9F792C",
        stadium="EverBank Stadium",
        default_identity="balanced",
    ),
    "TEN": NFLTeamData(
        name="Titans",
        city="Tennessee",
        abbreviation="TEN",
        division=Division.AFC_SOUTH,
        primary_color="#0C2340",
        secondary_color="#4B92DB",
        stadium="Nissan Stadium",
        default_identity="power_run",
    ),

    # =========================================================================
    # AFC WEST
    # =========================================================================
    "DEN": NFLTeamData(
        name="Broncos",
        city="Denver",
        abbreviation="DEN",
        division=Division.AFC_WEST,
        primary_color="#FB4F14",
        secondary_color="#002244",
        stadium="Empower Field at Mile High",
        default_identity="balanced",
    ),
    "KC": NFLTeamData(
        name="Chiefs",
        city="Kansas City",
        abbreviation="KC",
        division=Division.AFC_WEST,
        primary_color="#E31837",
        secondary_color="#FFB81C",
        stadium="GEHA Field at Arrowhead Stadium",
        default_identity="air_raid",
    ),
    "LV": NFLTeamData(
        name="Raiders",
        city="Las Vegas",
        abbreviation="LV",
        division=Division.AFC_WEST,
        primary_color="#A5ACAF",
        secondary_color="#000000",
        stadium="Allegiant Stadium",
        default_identity="balanced",
    ),
    "LAC": NFLTeamData(
        name="Chargers",
        city="Los Angeles",
        abbreviation="LAC",
        division=Division.AFC_WEST,
        primary_color="#0080C6",
        secondary_color="#FFC20E",
        stadium="SoFi Stadium",
        default_identity="west_coast",
    ),

    # =========================================================================
    # NFC EAST
    # =========================================================================
    "DAL": NFLTeamData(
        name="Cowboys",
        city="Dallas",
        abbreviation="DAL",
        division=Division.NFC_EAST,
        primary_color="#003594",
        secondary_color="#869397",
        stadium="AT&T Stadium",
        default_identity="balanced",
    ),
    "NYG": NFLTeamData(
        name="Giants",
        city="New York",
        abbreviation="NYG",
        division=Division.NFC_EAST,
        primary_color="#0B2265",
        secondary_color="#A71930",
        stadium="MetLife Stadium",
        default_identity="balanced",
    ),
    "PHI": NFLTeamData(
        name="Eagles",
        city="Philadelphia",
        abbreviation="PHI",
        division=Division.NFC_EAST,
        primary_color="#004C54",
        secondary_color="#A5ACAF",
        stadium="Lincoln Financial Field",
        default_identity="power_run",
    ),
    "WAS": NFLTeamData(
        name="Commanders",
        city="Washington",
        abbreviation="WAS",
        division=Division.NFC_EAST,
        primary_color="#5A1414",
        secondary_color="#FFB612",
        stadium="Northwest Stadium",
        default_identity="balanced",
    ),

    # =========================================================================
    # NFC NORTH
    # =========================================================================
    "CHI": NFLTeamData(
        name="Bears",
        city="Chicago",
        abbreviation="CHI",
        division=Division.NFC_NORTH,
        primary_color="#0B162A",
        secondary_color="#C83803",
        stadium="Soldier Field",
        default_identity="defensive",
    ),
    "DET": NFLTeamData(
        name="Lions",
        city="Detroit",
        abbreviation="DET",
        division=Division.NFC_NORTH,
        primary_color="#0076B6",
        secondary_color="#B0B7BC",
        stadium="Ford Field",
        default_identity="balanced",
    ),
    "GB": NFLTeamData(
        name="Packers",
        city="Green Bay",
        abbreviation="GB",
        division=Division.NFC_NORTH,
        primary_color="#203731",
        secondary_color="#FFB612",
        stadium="Lambeau Field",
        default_identity="west_coast",
    ),
    "MIN": NFLTeamData(
        name="Vikings",
        city="Minnesota",
        abbreviation="MIN",
        division=Division.NFC_NORTH,
        primary_color="#4F2683",
        secondary_color="#FFC62F",
        stadium="U.S. Bank Stadium",
        default_identity="balanced",
    ),

    # =========================================================================
    # NFC SOUTH
    # =========================================================================
    "ATL": NFLTeamData(
        name="Falcons",
        city="Atlanta",
        abbreviation="ATL",
        division=Division.NFC_SOUTH,
        primary_color="#A71930",
        secondary_color="#000000",
        stadium="Mercedes-Benz Stadium",
        default_identity="balanced",
    ),
    "CAR": NFLTeamData(
        name="Panthers",
        city="Carolina",
        abbreviation="CAR",
        division=Division.NFC_SOUTH,
        primary_color="#0085CA",
        secondary_color="#101820",
        stadium="Bank of America Stadium",
        default_identity="balanced",
    ),
    "NO": NFLTeamData(
        name="Saints",
        city="New Orleans",
        abbreviation="NO",
        division=Division.NFC_SOUTH,
        primary_color="#D3BC8D",
        secondary_color="#101820",
        stadium="Caesars Superdome",
        default_identity="west_coast",
    ),
    "TB": NFLTeamData(
        name="Buccaneers",
        city="Tampa Bay",
        abbreviation="TB",
        division=Division.NFC_SOUTH,
        primary_color="#D50A0A",
        secondary_color="#FF7900",
        stadium="Raymond James Stadium",
        default_identity="balanced",
    ),

    # =========================================================================
    # NFC WEST
    # =========================================================================
    "ARI": NFLTeamData(
        name="Cardinals",
        city="Arizona",
        abbreviation="ARI",
        division=Division.NFC_WEST,
        primary_color="#97233F",
        secondary_color="#000000",
        stadium="State Farm Stadium",
        default_identity="air_raid",
    ),
    "LAR": NFLTeamData(
        name="Rams",
        city="Los Angeles",
        abbreviation="LAR",
        division=Division.NFC_WEST,
        primary_color="#003594",
        secondary_color="#FFA300",
        stadium="SoFi Stadium",
        default_identity="west_coast",
    ),
    "SF": NFLTeamData(
        name="49ers",
        city="San Francisco",
        abbreviation="SF",
        division=Division.NFC_WEST,
        primary_color="#AA0000",
        secondary_color="#B3995D",
        stadium="Levi's Stadium",
        default_identity="west_coast",
    ),
    "SEA": NFLTeamData(
        name="Seahawks",
        city="Seattle",
        abbreviation="SEA",
        division=Division.NFC_WEST,
        primary_color="#002244",
        secondary_color="#69BE28",
        stadium="Lumen Field",
        default_identity="balanced",
    ),
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_teams_in_division(division: Division) -> list[NFLTeamData]:
    """Get all teams in a division."""
    return [t for t in NFL_TEAMS.values() if t.division == division]


def get_teams_in_conference(conference: Conference) -> list[NFLTeamData]:
    """Get all teams in a conference."""
    return [t for t in NFL_TEAMS.values() if t.division.conference == conference]


def get_division_rivals(abbreviation: str) -> list[NFLTeamData]:
    """Get division rivals for a team (not including the team itself)."""
    team = NFL_TEAMS.get(abbreviation)
    if not team:
        return []
    return [t for t in NFL_TEAMS.values()
            if t.division == team.division and t.abbreviation != abbreviation]


def get_team_by_name(name: str) -> Optional[NFLTeamData]:
    """Get team data by team name (e.g., 'Patriots')."""
    for team in NFL_TEAMS.values():
        if team.name.lower() == name.lower():
            return team
    return None


def get_team_by_city(city: str) -> list[NFLTeamData]:
    """Get teams by city (returns list since some cities have multiple teams)."""
    return [t for t in NFL_TEAMS.values() if t.city.lower() == city.lower()]


# Division groupings for easy iteration
DIVISIONS_BY_CONFERENCE: dict[Conference, list[Division]] = {
    Conference.AFC: [
        Division.AFC_EAST,
        Division.AFC_NORTH,
        Division.AFC_SOUTH,
        Division.AFC_WEST,
    ],
    Conference.NFC: [
        Division.NFC_EAST,
        Division.NFC_NORTH,
        Division.NFC_SOUTH,
        Division.NFC_WEST,
    ],
}


# Abbreviation lists for quick reference
AFC_TEAMS = ["BUF", "MIA", "NE", "NYJ", "BAL", "CIN", "CLE", "PIT",
             "HOU", "IND", "JAX", "TEN", "DEN", "KC", "LV", "LAC"]
NFC_TEAMS = ["DAL", "NYG", "PHI", "WAS", "CHI", "DET", "GB", "MIN",
             "ATL", "CAR", "NO", "TB", "ARI", "LAR", "SF", "SEA"]
ALL_TEAM_ABBREVIATIONS = AFC_TEAMS + NFC_TEAMS
