"""Teams API router - REST endpoints for team management."""

import random
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from huddle.api.schemas.team import StarterInfoSchema, TeamSchema, TeamSummarySchema
from huddle.generators import generate_team

router = APIRouter(prefix="/teams", tags=["teams"])

# In-memory team storage for now (will be replaced by SQLite)
_teams_cache: dict[UUID, Any] = {}

# Sample NFL teams for random generation
NFL_TEAMS = [
    ("Eagles", "Philadelphia", "PHI", "#004C54", "#A5ACAF"),
    ("Cowboys", "Dallas", "DAL", "#003594", "#869397"),
    ("Giants", "New York", "NYG", "#0B2265", "#A71930"),
    ("Commanders", "Washington", "WAS", "#5A1414", "#FFB612"),
    ("Patriots", "New England", "NE", "#002244", "#C60C30"),
    ("Bills", "Buffalo", "BUF", "#00338D", "#C60C30"),
    ("Dolphins", "Miami", "MIA", "#008E97", "#FC4C02"),
    ("Jets", "New York", "NYJ", "#125740", "#FFFFFF"),
    ("Chiefs", "Kansas City", "KC", "#E31837", "#FFB612"),
    ("Raiders", "Las Vegas", "LV", "#000000", "#A5ACAF"),
    ("Broncos", "Denver", "DEN", "#FB4F14", "#002244"),
    ("Chargers", "Los Angeles", "LAC", "#0080C6", "#FFC20E"),
]


@router.post("", response_model=TeamSchema, status_code=status.HTTP_201_CREATED)
async def create_random_team() -> TeamSchema:
    """Generate a new random team."""
    team_data = random.choice(NFL_TEAMS)
    team = generate_team(
        name=team_data[0],
        city=team_data[1],
        abbreviation=team_data[2],
        primary_color=team_data[3],
        secondary_color=team_data[4],
        overall_range=(70, 85),
    )

    # Cache the team
    _teams_cache[team.id] = team

    return TeamSchema.from_model(team)


@router.get("", response_model=list[TeamSummarySchema])
async def list_teams() -> list[TeamSummarySchema]:
    """List all teams."""
    return [TeamSummarySchema.from_model(team) for team in _teams_cache.values()]


@router.get("/{team_id}", response_model=TeamSchema)
async def get_team(team_id: UUID) -> TeamSchema:
    """Get a team by ID."""
    team = _teams_cache.get(team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team {team_id} not found",
        )

    return TeamSchema.from_model(team)


@router.get("/{team_id}/starters", response_model=StarterInfoSchema)
async def get_team_starters(team_id: UUID) -> StarterInfoSchema:
    """Get a team's starting lineup."""
    team = _teams_cache.get(team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team {team_id} not found",
        )

    return StarterInfoSchema.from_team(team)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(team_id: UUID) -> None:
    """Delete a team."""
    if team_id not in _teams_cache:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team {team_id} not found",
        )

    del _teams_cache[team_id]
