"""Pydantic schemas for team-related models."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class PlayerSchema(BaseModel):
    """Player information."""

    id: str
    first_name: str
    last_name: str
    position: str
    overall: int = 0

    # Physical info
    age: int
    height_inches: int
    weight_lbs: int
    jersey_number: int

    # Display properties
    full_name: str = ""
    display_name: str = ""
    height_display: str = ""

    # Career info
    experience_years: int = 0
    college: Optional[str] = None

    # Attributes (flattened for easy access)
    attributes: dict = {}

    @classmethod
    def from_model(cls, player) -> "PlayerSchema":
        """Create from Player model."""
        return cls(
            id=str(player.id),
            first_name=player.first_name,
            last_name=player.last_name,
            position=player.position.value,
            overall=player.overall,
            age=player.age,
            height_inches=player.height_inches,
            weight_lbs=player.weight_lbs,
            jersey_number=player.jersey_number,
            full_name=player.full_name,
            display_name=player.display_name,
            height_display=player.height_display,
            experience_years=player.experience_years,
            college=player.college,
            attributes=player.attributes.to_dict(),
        )


class RosterSchema(BaseModel):
    """Team roster."""

    players: list[PlayerSchema]
    depth_chart: dict[str, str]  # slot -> player_id
    size: int = 0

    @classmethod
    def from_model(cls, roster) -> "RosterSchema":
        """Create from Roster model."""
        return cls(
            players=[PlayerSchema.from_model(p) for p in roster.players.values()],
            depth_chart={slot: str(pid) for slot, pid in roster.depth_chart.slots.items()},
            size=roster.size,
        )


class TeamSummarySchema(BaseModel):
    """Summarized team info (without full roster)."""

    id: str
    name: str
    abbreviation: str
    city: str
    full_name: str = ""
    primary_color: str = "#000000"
    secondary_color: str = "#FFFFFF"
    offense_rating: int = 50
    defense_rating: int = 50

    @classmethod
    def from_model(cls, team) -> "TeamSummarySchema":
        """Create from Team model."""
        return cls(
            id=str(team.id),
            name=team.name,
            abbreviation=team.abbreviation,
            city=team.city,
            full_name=team.full_name,
            primary_color=team.primary_color,
            secondary_color=team.secondary_color,
            offense_rating=team.calculate_offense_rating(),
            defense_rating=team.calculate_defense_rating(),
        )


class TeamSchema(BaseModel):
    """Full team information with roster."""

    id: str
    name: str
    abbreviation: str
    city: str
    full_name: str = ""
    primary_color: str = "#000000"
    secondary_color: str = "#FFFFFF"
    roster: RosterSchema
    offense_rating: int = 50
    defense_rating: int = 50

    # AI tendencies
    run_tendency: float = 0.5
    aggression: float = 0.5
    blitz_tendency: float = 0.3

    @classmethod
    def from_model(cls, team) -> "TeamSchema":
        """Create from Team model."""
        return cls(
            id=str(team.id),
            name=team.name,
            abbreviation=team.abbreviation,
            city=team.city,
            full_name=team.full_name,
            primary_color=team.primary_color,
            secondary_color=team.secondary_color,
            roster=RosterSchema.from_model(team.roster),
            offense_rating=team.calculate_offense_rating(),
            defense_rating=team.calculate_defense_rating(),
            run_tendency=team.run_tendency,
            aggression=team.aggression,
            blitz_tendency=team.blitz_tendency,
        )


class StarterInfoSchema(BaseModel):
    """Key starter information for a team."""

    qb: Optional[PlayerSchema] = None
    rb: Optional[PlayerSchema] = None
    wr1: Optional[PlayerSchema] = None
    offensive_starters: dict[str, PlayerSchema] = {}
    defensive_starters: dict[str, PlayerSchema] = {}

    @classmethod
    def from_team(cls, team) -> "StarterInfoSchema":
        """Create from Team model."""
        qb = team.get_qb()
        rb = team.get_rb()
        wr1 = team.get_starter("WR1")

        off_starters = {
            slot: PlayerSchema.from_model(player)
            for slot, player in team.roster.get_offensive_starters().items()
        }
        def_starters = {
            slot: PlayerSchema.from_model(player)
            for slot, player in team.roster.get_defensive_starters().items()
        }

        return cls(
            qb=PlayerSchema.from_model(qb) if qb else None,
            rb=PlayerSchema.from_model(rb) if rb else None,
            wr1=PlayerSchema.from_model(wr1) if wr1 else None,
            offensive_starters=off_starters,
            defensive_starters=def_starters,
        )
