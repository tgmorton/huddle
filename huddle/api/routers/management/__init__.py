"""
Management API Router - Combined Sub-Routers.

This module combines all management sub-routers into a single router
that can be mounted in the main FastAPI application.

Sub-routers:
- franchise: Core CRUD, time controls, state management
- contracts: Financials, restructure, cut operations
- free_agency: Free agent listing, negotiations, auctions
- draft: Prospects, scouting, draft board
- practice: Practice allocation, mastery, development
- game: Game simulation
- clipboard: Events, drawer, journal
"""

from fastapi import APIRouter

from .franchise import router as franchise_router
from .contracts import router as contracts_router
from .free_agency import router as free_agency_router
from .draft import router as draft_router
from .practice import router as practice_router
from .game import router as game_router
from .clipboard import router as clipboard_router

# Create the combined router
router = APIRouter()

# Include all sub-routers
# Each sub-router already has appropriate tags set
router.include_router(franchise_router)
router.include_router(contracts_router)
router.include_router(free_agency_router)
router.include_router(draft_router)
router.include_router(practice_router)
router.include_router(game_router)
router.include_router(clipboard_router)

# Re-export for convenience
__all__ = [
    "router",
    "franchise_router",
    "contracts_router",
    "free_agency_router",
    "draft_router",
    "practice_router",
    "game_router",
    "clipboard_router",
]
