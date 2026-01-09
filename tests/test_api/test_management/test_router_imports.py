"""
Baseline tests for management router imports.

These tests verify the router structure is correct after refactoring to sub-routers.

Note: The combined router no longer has a /management prefix - that's added when
mounting in main.py. The sub-routers use paths like /franchise/{franchise_id}.
"""

import pytest


class TestRouterImports:
    """Test that all router imports work correctly."""

    def test_management_router_imports(self):
        """Test that the main management router can be imported."""
        from huddle.api.routers.management import router

        assert router is not None
        # Note: prefix is applied in main.py, not on the router itself
        assert router.prefix == ""

    def test_management_router_has_routes(self):
        """Test that the management router has expected routes."""
        from huddle.api.routers.management import router

        # Get all route paths (no prefix since that's added by main.py)
        paths = [route.path for route in router.routes]

        # Check core franchise routes exist (without /management prefix)
        assert "/franchise" in paths or "/franchise/connect" in paths
        assert "/franchise/{franchise_id}" in paths

    def test_management_schemas_import(self):
        """Test that management schemas can be imported."""
        from huddle.api.schemas.management import (
            CreateFranchiseRequest,
            FranchiseCreatedResponse,
            LeagueStateResponse,
            CalendarStateResponse,
            EventQueueResponse,
            ManagementEventResponse,
        )

        assert CreateFranchiseRequest is not None
        assert FranchiseCreatedResponse is not None
        assert LeagueStateResponse is not None

    def test_management_service_imports(self):
        """Test that management service can be imported."""
        from huddle.api.services.management_service import (
            ManagementService,
            ManagementSession,
            ManagementSessionManager,
            management_session_manager,
        )

        assert ManagementService is not None
        assert ManagementSession is not None
        assert ManagementSessionManager is not None
        assert management_session_manager is not None

    def test_management_enums_import(self):
        """Test that management enums can be imported."""
        from huddle.management import (
            SeasonPhase,
            TimeSpeed,
            ClipboardTab,
        )

        assert SeasonPhase.TRAINING_CAMP is not None
        assert TimeSpeed.NORMAL is not None
        assert ClipboardTab.EVENTS is not None


class TestRouterEndpoints:
    """Test that router has all expected endpoints."""

    def test_franchise_endpoints_exist(self):
        """Test franchise CRUD endpoints exist."""
        from huddle.api.routers.management import router
        from collections import defaultdict

        # Aggregate all methods per path
        paths = defaultdict(set)
        for route in router.routes:
            for method in route.methods:
                paths[route.path].add(method)

        # POST /franchise (or /franchise/connect)
        assert "/franchise" in paths or "/franchise/connect" in paths

        # GET /franchise/{franchise_id}
        assert "/franchise/{franchise_id}" in paths
        assert "GET" in paths["/franchise/{franchise_id}"]

        # DELETE /franchise/{franchise_id}
        assert "DELETE" in paths["/franchise/{franchise_id}"]

    def test_time_control_endpoints_exist(self):
        """Test time control endpoints exist."""
        from huddle.api.routers.management import router

        paths = {route.path: route.methods for route in router.routes}

        assert "/franchise/{franchise_id}/pause" in paths
        assert "/franchise/{franchise_id}/play" in paths
        assert "/franchise/{franchise_id}/speed" in paths

    def test_event_endpoints_exist(self):
        """Test event endpoints exist."""
        from huddle.api.routers.management import router

        paths = {route.path: route.methods for route in router.routes}

        assert "/franchise/{franchise_id}/events" in paths
        assert "/franchise/{franchise_id}/events/attend" in paths
        assert "/franchise/{franchise_id}/events/dismiss" in paths

    def test_financial_endpoints_exist(self):
        """Test financial endpoints exist."""
        from huddle.api.routers.management import router

        paths = {route.path: route.methods for route in router.routes}

        assert "/franchise/{franchise_id}/financials" in paths
        assert "/franchise/{franchise_id}/contracts" in paths
        assert "/franchise/{franchise_id}/free-agents" in paths

    def test_draft_endpoints_exist(self):
        """Test draft endpoints exist."""
        from huddle.api.routers.management import router

        paths = {route.path: route.methods for route in router.routes}

        assert "/franchise/{franchise_id}/draft-prospects" in paths
        assert "/franchise/{franchise_id}/draft-board" in paths

    def test_practice_endpoints_exist(self):
        """Test practice endpoints exist."""
        from huddle.api.routers.management import router

        paths = {route.path: route.methods for route in router.routes}

        assert "/franchise/{franchise_id}/run-practice" in paths
        assert "/franchise/{franchise_id}/playbook-mastery" in paths
        assert "/franchise/{franchise_id}/development" in paths

    def test_game_endpoints_exist(self):
        """Test game simulation endpoints exist."""
        from huddle.api.routers.management import router

        paths = {route.path: route.methods for route in router.routes}

        assert "/franchise/{franchise_id}/sim-game" in paths

    def test_negotiation_endpoints_exist(self):
        """Test negotiation endpoints exist."""
        from huddle.api.routers.management import router

        paths = {route.path: route.methods for route in router.routes}

        assert "/franchise/{franchise_id}/negotiations/start" in paths
        assert "/franchise/{franchise_id}/negotiations/active" in paths

    def test_auction_endpoints_exist(self):
        """Test auction endpoints exist."""
        from huddle.api.routers.management import router

        paths = {route.path: route.methods for route in router.routes}

        assert "/franchise/{franchise_id}/free-agency/auction/start" in paths
        assert "/franchise/{franchise_id}/free-agency/auctions/active" in paths


class TestRouterTags:
    """Test router tags are set correctly."""

    def test_sub_routers_have_tags(self):
        """Test sub-routers have correct tags."""
        from huddle.api.routers.management import (
            franchise_router,
            contracts_router,
            free_agency_router,
            draft_router,
            practice_router,
            game_router,
            clipboard_router,
        )

        assert "franchise" in franchise_router.tags
        assert "contracts" in contracts_router.tags
        assert "free-agency" in free_agency_router.tags
        assert "draft" in draft_router.tags
        assert "practice" in practice_router.tags
        assert "game" in game_router.tags
        assert "clipboard" in clipboard_router.tags
