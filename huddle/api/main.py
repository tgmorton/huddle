"""FastAPI application for Huddle football simulator."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from huddle.api.routers import (
    games_router,
    pocket_router,
    routes_router,
    team_routes_router,
    play_sim_router,
    integrated_sim_router,
    sandbox_router,
    sandbox_websocket_router,
    teams_router,
    websocket_router,
    management_router,
    management_websocket_router,
    v2_sim_router,
    agentmail_router,
    agentmail_websocket_router,
    portraits_router,
    history_router,
    free_agency_router,
    position_plan_router,
    coach_mode_router,
)
from huddle.api.routers.admin import router as admin_router
from huddle.api.routers.arms_prototype import router as arms_prototype_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    print("Huddle API starting up...")
    yield
    # Shutdown
    print("Huddle API shutting down...")
    # Clean up any active game sessions
    from huddle.api.services.session_manager import session_manager

    for game_id in session_manager.active_sessions:
        session_manager.remove_session(game_id)

    # Clean up any active management sessions
    from huddle.api.services.management_service import management_session_manager

    await management_session_manager.cleanup_all()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Huddle API",
        description="American Football Simulator API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Configure CORS for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # Vite dev server
            "http://localhost:5173",  # Alternative Vite port
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "tauri://localhost",  # Tauri app
            "https://tauri.localhost",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(games_router, prefix="/api/v1")
    app.include_router(teams_router, prefix="/api/v1")
    app.include_router(sandbox_router, prefix="/api/v1")
    app.include_router(pocket_router, prefix="/api/v1")
    app.include_router(routes_router, prefix="/api/v1")
    app.include_router(team_routes_router, prefix="/api/v1")
    app.include_router(play_sim_router, prefix="/api/v1")
    app.include_router(integrated_sim_router, prefix="/api/v1")
    app.include_router(management_router, prefix="/api/v1/management")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(v2_sim_router, prefix="/api/v1")
    app.include_router(agentmail_router, prefix="/api/v1")  # Agent communication
    app.include_router(portraits_router, prefix="/api/v1")  # Player portraits
    app.include_router(history_router, prefix="/api/v1")  # Historical simulation explorer
    app.include_router(free_agency_router, prefix="/api/v1")  # Free agency bidding
    app.include_router(position_plan_router, prefix="/api/v1")  # HC09-style position planning
    app.include_router(arms_prototype_router, prefix="/api/v1")  # Arms prototype visualization
    app.include_router(coach_mode_router, prefix="/api/v1")  # Coach mode game interface
    app.include_router(websocket_router)
    app.include_router(sandbox_websocket_router)
    app.include_router(management_websocket_router)
    app.include_router(agentmail_websocket_router)

    return app


# Create app instance
app = create_app()


@app.get("/")
async def root() -> dict:
    """Root endpoint - API info."""
    return {
        "name": "Huddle API",
        "version": "0.1.0",
        "description": "American Football Simulator",
        "docs": "/docs",
    }


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    from huddle.api.services.session_manager import session_manager
    from huddle.api.services.management_service import management_session_manager

    return {
        "status": "healthy",
        "active_games": len(session_manager.active_sessions),
        "active_franchises": len(management_session_manager.active_sessions),
    }


def run_api(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    """Run the API server."""
    uvicorn.run(
        "huddle.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    run_api(reload=True)
