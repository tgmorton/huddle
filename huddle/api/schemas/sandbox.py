"""Pydantic schemas for sandbox simulation API."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class SandboxPlayerSchema(BaseModel):
    """Schema for a sandbox player."""

    id: Optional[str] = None
    name: str = "Player"
    role: Literal["blocker", "rusher"] = "blocker"
    strength: int = Field(default=75, ge=0, le=99)
    speed: int = Field(default=75, ge=0, le=99)
    agility: int = Field(default=75, ge=0, le=99)
    pass_block: int = Field(default=75, ge=0, le=99)
    awareness: int = Field(default=75, ge=0, le=99)
    block_shedding: int = Field(default=75, ge=0, le=99)
    power_moves: int = Field(default=75, ge=0, le=99)
    finesse_moves: int = Field(default=75, ge=0, le=99)


class Position2DSchema(BaseModel):
    """2D position on the field."""

    x: float = 0.0
    y: float = 0.0


class CreateSessionRequest(BaseModel):
    """Request to create a new sandbox session."""

    blocker: Optional[SandboxPlayerSchema] = None
    rusher: Optional[SandboxPlayerSchema] = None
    tick_rate_ms: int = Field(default=100, ge=50, le=500)
    max_ticks: int = Field(default=50, ge=10, le=100)
    qb_zone_depth: float = Field(default=7.0, ge=3.0, le=10.0)


class SessionResponse(BaseModel):
    """Response containing session information."""

    session_id: str
    blocker: SandboxPlayerSchema
    rusher: SandboxPlayerSchema
    tick_rate_ms: int
    max_ticks: int
    qb_zone_depth: float
    current_tick: int
    is_running: bool
    is_complete: bool
    blocker_position: Position2DSchema
    rusher_position: Position2DSchema
    outcome: str
    stats: dict


class TickResultSchema(BaseModel):
    """Schema for a tick result."""

    tick_number: int
    timestamp_ms: int
    blocker_position: Position2DSchema
    rusher_position: Position2DSchema
    rusher_technique: str
    blocker_technique: str
    rusher_score: float
    blocker_score: float
    margin: float
    movement: float
    matchup_state: str
    outcome: str
    rusher_depth: float
    engagement_duration_ms: int


class UpdatePlayerRequest(BaseModel):
    """Request to update a player's attributes."""

    role: Literal["blocker", "rusher"]
    player: SandboxPlayerSchema


class SetTickRateRequest(BaseModel):
    """Request to change tick rate."""

    tick_rate_ms: int = Field(ge=50, le=500)


# WebSocket message types

class WSMessageBase(BaseModel):
    """Base WebSocket message."""

    type: str


class StartSimulationMessage(WSMessageBase):
    """Client message to start simulation."""

    type: Literal["start_simulation"] = "start_simulation"


class PauseSimulationMessage(WSMessageBase):
    """Client message to pause simulation."""

    type: Literal["pause_simulation"] = "pause_simulation"


class ResumeSimulationMessage(WSMessageBase):
    """Client message to resume simulation."""

    type: Literal["resume_simulation"] = "resume_simulation"


class ResetSimulationMessage(WSMessageBase):
    """Client message to reset simulation."""

    type: Literal["reset_simulation"] = "reset_simulation"


class UpdatePlayerMessage(WSMessageBase):
    """Client message to update player attributes."""

    type: Literal["update_player"] = "update_player"
    role: Literal["blocker", "rusher"]
    player: SandboxPlayerSchema


class SetTickRateMessage(WSMessageBase):
    """Client message to set tick rate."""

    type: Literal["set_tick_rate"] = "set_tick_rate"
    tick_rate_ms: int = Field(ge=50, le=500)


class RequestSyncMessage(WSMessageBase):
    """Client message to request state sync."""

    type: Literal["request_sync"] = "request_sync"


# Server -> Client messages

class TickUpdateMessage(WSMessageBase):
    """Server message with tick update."""

    type: Literal["tick_update"] = "tick_update"
    payload: TickResultSchema


class SimulationCompleteMessage(WSMessageBase):
    """Server message when simulation completes."""

    type: Literal["simulation_complete"] = "simulation_complete"
    payload: SessionResponse


class StateSyncMessage(WSMessageBase):
    """Server message with full state sync."""

    type: Literal["state_sync"] = "state_sync"
    payload: SessionResponse


class ErrorMessage(WSMessageBase):
    """Server message for errors."""

    type: Literal["error"] = "error"
    message: str
    code: str = "UNKNOWN_ERROR"
