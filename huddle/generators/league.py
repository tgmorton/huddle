"""
League Generation.

This module provides functions to generate a complete 32-team NFL league
with all rosters, standings, schedule, and optional free agent/draft pools.
"""

import random
from typing import Optional

import pulp

from huddle.core.league import (
    League,
    TeamStanding,
    ScheduledGame,
    Conference,
    Division,
    NFL_TEAMS,
    DIVISIONS_BY_CONFERENCE,
    get_teams_in_division,
)
from huddle.core.models.team import Team
from huddle.core.models.team_identity import (
    TeamIdentity,
    create_identity_air_raid,
    create_identity_balanced,
    create_identity_defensive,
    create_identity_power_run,
    create_identity_west_coast,
    create_random_identity,
)
from huddle.generators.player import (
    generate_team,
    generate_draft_class,
    generate_player,
)
from huddle.core.enums import Position
from huddle.core.contracts.market_value import generate_roster_contracts


# Map default identities from nfl_data to identity creators
IDENTITY_CREATORS = {
    "power_run": create_identity_power_run,
    "air_raid": create_identity_air_raid,
    "west_coast": create_identity_west_coast,
    "defensive": create_identity_defensive,
    "balanced": create_identity_balanced,
}


def generate_nfl_team(
    abbreviation: str,
    overall_range: tuple[int, int] = (70, 85),
    identity: Optional[TeamIdentity] = None,
) -> Team:
    """
    Generate a team based on official NFL team data.

    Args:
        abbreviation: Team abbreviation (e.g., "NE", "KC")
        overall_range: Range for player overall ratings
        identity: Optional team identity override

    Returns:
        Generated Team with 53-player roster

    Raises:
        ValueError: If abbreviation is not a valid NFL team
    """
    nfl_data = NFL_TEAMS.get(abbreviation)
    if nfl_data is None:
        raise ValueError(f"Unknown NFL team abbreviation: {abbreviation}")

    # Create identity based on team's default if not provided
    if identity is None:
        creator = IDENTITY_CREATORS.get(nfl_data.default_identity, create_random_identity)
        identity = creator()

    team = generate_team(
        name=nfl_data.name,
        city=nfl_data.city,
        abbreviation=nfl_data.abbreviation,
        overall_range=overall_range,
        primary_color=nfl_data.primary_color,
        secondary_color=nfl_data.secondary_color,
        identity=identity,
    )

    # Assign contracts to all players and calculate financials
    generate_roster_contracts(team.roster)
    team.recalculate_financials()

    return team


def generate_league(
    season: int = 2024,
    name: str = "NFL",
    overall_range: tuple[int, int] = (68, 88),
    parity_mode: bool = False,
    include_draft_class: bool = True,
    include_free_agents: bool = True,
    num_free_agents: int = 150,
) -> League:
    """
    Generate a complete 32-team NFL league.

    Creates all teams with full rosters, initialized standings,
    and optionally a draft class and free agent pool.

    Args:
        season: Starting season year
        name: League name
        overall_range: Base range for player ratings (70, 85)
        parity_mode: If True, all teams have similar ratings
        include_draft_class: Generate a draft class
        include_free_agents: Generate a free agent pool
        num_free_agents: Number of free agents to generate

    Returns:
        Fully populated League object
    """
    league = League(
        name=name,
        current_season=season,
        current_week=0,
    )

    # Generate all 32 teams
    for abbr in NFL_TEAMS.keys():
        # Vary team strength unless parity mode
        if parity_mode:
            team_range = overall_range
        else:
            # Random variation: some teams are better than others
            strength_mod = random.gauss(0, 4)
            team_range = (
                max(60, int(overall_range[0] + strength_mod)),
                min(95, int(overall_range[1] + strength_mod)),
            )

        team = generate_nfl_team(abbr, overall_range=team_range)
        league.teams[abbr] = team

        # Initialize standings
        league.standings[abbr] = TeamStanding(
            team_id=team.id,
            abbreviation=abbr,
        )

    # Generate draft class
    if include_draft_class:
        league.draft_class = generate_draft_class(season + 1)

    # Generate free agents
    if include_free_agents:
        league.free_agents = _generate_free_agent_pool(num_free_agents)

    # Set initial draft order (reverse alphabetical as placeholder)
    league.draft_order = sorted(NFL_TEAMS.keys())

    return league


def generate_league_with_schedule(
    season: int = 2024,
    **kwargs,
) -> League:
    """
    Generate a complete league with a full 18-week schedule.

    See generate_league() for base parameters.

    Returns:
        League with schedule generated
    """
    league = generate_league(season=season, **kwargs)
    league.schedule = generate_nfl_schedule(season, list(NFL_TEAMS.keys()))
    return league


def _generate_free_agent_pool(num_players: int = 150) -> list:
    """
    Generate a pool of free agents.

    Free agents are typically:
    - Older players released from teams
    - Young players who didn't make rosters
    - Mid-tier talent

    Args:
        num_players: Number of free agents to generate

    Returns:
        List of free agent players
    """
    free_agents = []

    # Position distribution for free agents
    # More skill positions, fewer specialists
    position_weights = {
        Position.QB: 8,
        Position.RB: 15,
        Position.FB: 3,
        Position.WR: 20,
        Position.TE: 10,
        Position.LT: 5,
        Position.LG: 5,
        Position.C: 4,
        Position.RG: 5,
        Position.RT: 5,
        Position.DE: 12,
        Position.DT: 8,
        Position.NT: 3,
        Position.MLB: 8,
        Position.ILB: 6,
        Position.OLB: 10,
        Position.CB: 15,
        Position.FS: 6,
        Position.SS: 6,
        Position.K: 2,
        Position.P: 2,
        Position.LS: 1,
    }

    positions = list(position_weights.keys())
    weights = list(position_weights.values())

    for _ in range(num_players):
        position = random.choices(positions, weights=weights)[0]

        # Free agents tend to be lower rated or older
        age_type = random.choice(["young", "prime", "veteran", "washed"])

        if age_type == "young":
            # Young players who didn't make rosters
            age = random.randint(22, 24)
            overall_target = random.randint(58, 68)
            potential_mod = random.uniform(5, 15)  # High upside
        elif age_type == "prime":
            # Prime age players between teams
            age = random.randint(25, 29)
            overall_target = random.randint(65, 75)
            potential_mod = random.uniform(0, 5)
        elif age_type == "veteran":
            # Experienced veterans
            age = random.randint(30, 33)
            overall_target = random.randint(68, 78)
            potential_mod = random.uniform(-5, 0)  # Limited upside
        else:  # washed
            # Older players at end of career
            age = random.randint(33, 38)
            overall_target = random.randint(55, 68)
            potential_mod = -10  # Declining

        player = generate_player(
            position=position,
            overall_target=overall_target,
            age=age,
            potential_modifier=potential_mod,
            experience_years=max(0, age - 22),
            years_on_team=0,  # Free agents have 0 tenure
        )
        free_agents.append(player)

    return free_agents


def generate_nfl_schedule(
    season: int,
    team_abbrs: list[str],
) -> list[ScheduledGame]:
    """
    Generate a full NFL regular season schedule (18 weeks, 17 games per team).

    Uses Integer Programming (PuLP) to guarantee a valid schedule.

    NFL Schedule Rules:
    - 17 games per team over 18 weeks (1 bye week per team)
    - 6 division games (home/away vs each division rival)
    - 4 games vs a same-conference division (rotating yearly)
    - 4 games vs an opposite-conference division (rotating yearly)
    - 3 games vs same-place finishers from other divisions

    Args:
        season: Season year
        team_abbrs: List of team abbreviations

    Returns:
        List of ScheduledGame objects (272 games total)
    """
    # Step 1: Generate all matchups
    matchups = _generate_matchups(season, team_abbrs)

    # Step 2: Use Integer Programming to assign matchups to weeks
    schedule = _assign_weeks_ip(matchups, team_abbrs)

    return schedule


def _generate_matchups(season: int, team_abbrs: list[str]) -> list[dict]:
    """
    Generate all 272 matchups for the NFL season.

    Returns list of dicts with keys: home, away, is_div, is_conf
    """
    matchups: list[dict] = []
    team_game_count: dict[str, int] = {abbr: 0 for abbr in team_abbrs}
    team_home_count: dict[str, int] = {abbr: 0 for abbr in team_abbrs}
    played_matchups: set[tuple[str, str]] = set()

    def add_matchup(team1: str, team2: str, team1_home: bool, is_div: bool = False, is_conf: bool = False):
        """Add a matchup between two teams."""
        if team1_home:
            home, away = team1, team2
        else:
            home, away = team2, team1

        matchups.append({
            'home': home,
            'away': away,
            'is_div': is_div,
            'is_conf': is_conf,
        })
        team_game_count[team1] += 1
        team_game_count[team2] += 1
        team_home_count[home] += 1
        played_matchups.add(tuple(sorted([team1, team2])))

    def has_matchup(team1: str, team2: str) -> bool:
        return tuple(sorted([team1, team2])) in played_matchups

    # 1. DIVISION GAMES (6 per team - 2 vs each of 3 rivals)
    for conf in [Conference.AFC, Conference.NFC]:
        for division in DIVISIONS_BY_CONFERENCE[conf]:
            teams_in_div = [t.abbreviation for t in get_teams_in_division(division)]

            for i, team1 in enumerate(teams_in_div):
                for team2 in teams_in_div[i + 1:]:
                    add_matchup(team1, team2, team1_home=True, is_div=True, is_conf=True)
                    add_matchup(team1, team2, team1_home=False, is_div=True, is_conf=True)

    # 2. INTRA-CONFERENCE GAMES (4 per team vs another division)
    afc_divs = list(DIVISIONS_BY_CONFERENCE[Conference.AFC])
    nfc_divs = list(DIVISIONS_BY_CONFERENCE[Conference.NFC])
    rotation = season % 3

    pairing_schemes = [
        [(0, 1), (2, 3)],
        [(0, 2), (1, 3)],
        [(0, 3), (1, 2)],
    ]
    intra_pairings = pairing_schemes[rotation]

    for conf, divs in [(Conference.AFC, afc_divs), (Conference.NFC, nfc_divs)]:
        for idx1, idx2 in intra_pairings:
            div1, div2 = divs[idx1], divs[idx2]
            teams1 = [t.abbreviation for t in get_teams_in_division(div1)]
            teams2 = [t.abbreviation for t in get_teams_in_division(div2)]

            for j, team in enumerate(teams1):
                for k, opp in enumerate(teams2):
                    if not has_matchup(team, opp):
                        team_home = (j + k) % 2 == 0
                        add_matchup(team, opp, team1_home=team_home, is_conf=True)

    # 3. INTER-CONFERENCE GAMES (4 per team vs opposite conference division)
    inter_pairings = [(i, (i + rotation) % 4) for i in range(4)]

    for afc_idx, nfc_idx in inter_pairings:
        afc_div = afc_divs[afc_idx]
        nfc_div = nfc_divs[nfc_idx]

        afc_teams = [t.abbreviation for t in get_teams_in_division(afc_div)]
        nfc_teams = [t.abbreviation for t in get_teams_in_division(nfc_div)]

        for j, afc_team in enumerate(afc_teams):
            for k, nfc_team in enumerate(nfc_teams):
                if not has_matchup(afc_team, nfc_team):
                    afc_home = (j + k) % 2 == 0
                    add_matchup(afc_team, nfc_team, team1_home=afc_home)

    # 4. REMAINING GAMES (fill to 17 per team)
    for team in team_abbrs:
        while team_game_count[team] < 17:
            team_conf = NFL_TEAMS[team].division.conference
            available = [
                opp for opp in team_abbrs
                if opp != team
                and not has_matchup(team, opp)
                and team_game_count[opp] < 17
            ]

            if not available:
                break

            available.sort(key=lambda x: (
                0 if NFL_TEAMS[x].division.conference == team_conf else 1,
                team_game_count[x]
            ))
            opp = available[0]

            team_home = team_home_count[team] < 9
            opp_conf = NFL_TEAMS[opp].division.conference
            is_conf = team_conf == opp_conf

            add_matchup(team, opp, team1_home=team_home, is_conf=is_conf)

    return matchups


def _assign_weeks_ip(matchups: list[dict], team_abbrs: list[str]) -> list[ScheduledGame]:
    """
    Assign matchups to weeks using Integer Programming.

    This guarantees finding a valid schedule if one exists.

    Decision variables:
        x[g, w] = 1 if game g is played in week w, 0 otherwise

    Constraints:
        1. Each game is played exactly once
        2. Each team plays at most once per week
        3. Each team plays exactly 17 games total

    Args:
        matchups: List of matchup dicts
        team_abbrs: List of team abbreviations

    Returns:
        List of ScheduledGame objects
    """
    num_games = len(matchups)
    weeks = list(range(1, 19))  # Weeks 1-18

    # Create the LP problem
    prob = pulp.LpProblem("NFL_Schedule", pulp.LpMinimize)

    # Decision variables: x[g, w] = 1 if game g is in week w
    x = pulp.LpVariable.dicts(
        "game",
        ((g, w) for g in range(num_games) for w in weeks),
        cat='Binary'
    )

    # Objective: minimize total variance in games per week (for balance)
    # We use a dummy objective since we just need feasibility
    prob += 0, "Dummy_Objective"

    # Constraint 1: Each game is played exactly once
    for g in range(num_games):
        prob += (
            pulp.lpSum(x[g, w] for w in weeks) == 1,
            f"Game_{g}_played_once"
        )

    # Constraint 2: Each team plays at most 1 game per week
    # Build team-to-games mapping
    team_games: dict[str, list[int]] = {abbr: [] for abbr in team_abbrs}
    for g, m in enumerate(matchups):
        team_games[m['home']].append(g)
        team_games[m['away']].append(g)

    for team in team_abbrs:
        for w in weeks:
            prob += (
                pulp.lpSum(x[g, w] for g in team_games[team]) <= 1,
                f"Team_{team}_week_{w}_max_one"
            )

    # Constraint 3: Balance games per week (14-16 games per week)
    for w in weeks:
        prob += (
            pulp.lpSum(x[g, w] for g in range(num_games)) >= 14,
            f"Week_{w}_min_games"
        )
        prob += (
            pulp.lpSum(x[g, w] for g in range(num_games)) <= 16,
            f"Week_{w}_max_games"
        )

    # Constraint 4: No bye weeks in first 4 or last 3 weeks
    for team in team_abbrs:
        for w in [1, 2, 3, 4, 16, 17, 18]:
            prob += (
                pulp.lpSum(x[g, w] for g in team_games[team]) >= 1,
                f"Team_{team}_no_bye_week_{w}"
            )

    # Solve the problem
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    if prob.status != pulp.LpStatusOptimal:
        # Fallback: relax some constraints and try again
        prob2 = pulp.LpProblem("NFL_Schedule_Relaxed", pulp.LpMinimize)

        x2 = pulp.LpVariable.dicts(
            "game",
            ((g, w) for g in range(num_games) for w in weeks),
            cat='Binary'
        )

        prob2 += 0, "Dummy_Objective"

        # Each game played exactly once
        for g in range(num_games):
            prob2 += pulp.lpSum(x2[g, w] for w in weeks) == 1

        # Each team plays at most 1 game per week
        for team in team_abbrs:
            for w in weeks:
                prob2 += pulp.lpSum(x2[g, w] for g in team_games[team]) <= 1

        prob2.solve(pulp.PULP_CBC_CMD(msg=0))

        if prob2.status != pulp.LpStatusOptimal:
            raise RuntimeError("Could not find valid NFL schedule")

        x = x2

    # Extract solution
    schedule: list[ScheduledGame] = []
    for g, m in enumerate(matchups):
        for w in weeks:
            if pulp.value(x[g, w]) == 1:
                game = ScheduledGame(
                    week=w,
                    home_team_abbr=m['home'],
                    away_team_abbr=m['away'],
                    is_divisional=m['is_div'],
                    is_conference=m['is_conf'],
                )
                schedule.append(game)
                break

    # Sort by week
    schedule.sort(key=lambda g: (g.week, g.home_team_abbr))

    return schedule


def generate_preseason_league(
    num_teams: int = 4,
    team_names: Optional[list[tuple[str, str, str]]] = None,
) -> League:
    """
    Generate a small league for testing/preseason.

    Args:
        num_teams: Number of teams (default 4)
        team_names: Optional list of (name, city, abbr) tuples

    Returns:
        Small League for testing
    """
    league = League(
        name="Preseason League",
        current_season=2024,
    )

    # Default team names if not provided
    if team_names is None:
        team_names = [
            ("Eagles", "Philadelphia", "PHI"),
            ("Cowboys", "Dallas", "DAL"),
            ("Giants", "New York", "NYG"),
            ("Commanders", "Washington", "WAS"),
        ][:num_teams]

    for name, city, abbr in team_names:
        team = generate_team(
            name=name,
            city=city,
            abbreviation=abbr,
            overall_range=(70, 85),
        )
        league.teams[abbr] = team
        league.standings[abbr] = TeamStanding(
            team_id=team.id,
            abbreviation=abbr,
        )

    return league
