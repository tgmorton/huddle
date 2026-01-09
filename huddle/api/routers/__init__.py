"""API routers for different resource types."""

from huddle.api.routers.games import router as games_router
from huddle.api.routers.pocket import router as pocket_router
from huddle.api.routers.routes import router as routes_router
from huddle.api.routers.team_routes import router as team_routes_router
from huddle.api.routers.sandbox import router as sandbox_router
from huddle.api.routers.sandbox_websocket import router as sandbox_websocket_router
from huddle.api.routers.teams import router as teams_router
from huddle.api.routers.websocket import router as websocket_router
from huddle.api.routers.management import router as management_router
from huddle.api.routers.management_websocket import router as management_websocket_router
from huddle.api.routers.play_sim import router as play_sim_router
from huddle.api.routers.integrated_sim import router as integrated_sim_router
from huddle.api.routers.v2_sim import router as v2_sim_router
from huddle.api.routers.agentmail import router as agentmail_router
from huddle.api.routers.agentmail_websocket import router as agentmail_websocket_router
from huddle.api.routers.portraits import router as portraits_router
from huddle.api.routers.history import router as history_router
from huddle.api.routers.free_agency import router as free_agency_router
from huddle.api.routers.position_plan import router as position_plan_router
from huddle.api.routers.coach_mode import router as coach_mode_router

__all__ = [
    "games_router",
    "teams_router",
    "websocket_router",
    "sandbox_router",
    "sandbox_websocket_router",
    "pocket_router",
    "routes_router",
    "team_routes_router",
    "management_router",
    "management_websocket_router",
    "play_sim_router",
    "integrated_sim_router",
    "v2_sim_router",
    "agentmail_router",
    "agentmail_websocket_router",
    "portraits_router",
    "history_router",
    "free_agency_router",
    "position_plan_router",
    "coach_mode_router",
]
