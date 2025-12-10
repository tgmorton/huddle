"""League structure and management."""

from huddle.core.league.nfl_data import (
    Conference,
    Division,
    NFLTeamData,
    NFL_TEAMS,
    DIVISIONS_BY_CONFERENCE,
    AFC_TEAMS,
    NFC_TEAMS,
    ALL_TEAM_ABBREVIATIONS,
    get_teams_in_division,
    get_teams_in_conference,
    get_division_rivals,
    get_team_by_name,
    get_team_by_city,
)
from huddle.core.league.league import (
    League,
    TeamStanding,
    ScheduledGame,
)

__all__ = [
    # NFL Data
    "Conference",
    "Division",
    "NFLTeamData",
    "NFL_TEAMS",
    "DIVISIONS_BY_CONFERENCE",
    "AFC_TEAMS",
    "NFC_TEAMS",
    "ALL_TEAM_ABBREVIATIONS",
    "get_teams_in_division",
    "get_teams_in_conference",
    "get_division_rivals",
    "get_team_by_name",
    "get_team_by_city",
    # League Container
    "League",
    "TeamStanding",
    "ScheduledGame",
]
