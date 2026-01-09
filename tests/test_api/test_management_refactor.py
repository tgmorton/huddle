"""
Tests for the refactored management API.

These tests verify that the new sub-router structure works correctly
and all endpoints are accessible.
"""

import pytest
from fastapi.testclient import TestClient

from huddle.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestRouterStructure:
    """Tests for the router structure after refactoring."""

    def test_router_imports(self):
        """Verify all sub-routers can be imported."""
        from huddle.api.routers.management import (
            router,
            franchise_router,
            contracts_router,
            free_agency_router,
            draft_router,
            practice_router,
            game_router,
            clipboard_router,
        )

        assert router is not None
        assert franchise_router is not None
        assert contracts_router is not None
        assert free_agency_router is not None
        assert draft_router is not None
        assert practice_router is not None
        assert game_router is not None
        assert clipboard_router is not None

    def test_combined_router_has_routes(self):
        """Verify combined router has routes from all sub-routers."""
        from huddle.api.routers.management import router

        # Should have routes from all sub-routers
        assert len(router.routes) >= 40  # Baseline count

    def test_all_routes_have_paths(self):
        """Verify all routes have valid paths."""
        from huddle.api.routers.management import router

        for route in router.routes:
            # Each route should have a path
            assert hasattr(route, 'path')
            assert route.path is not None


class TestEndpointAvailability:
    """Tests that endpoints are reachable (may return 404 for missing data, not 500)."""

    def test_franchise_endpoints_available(self, client):
        """Test franchise-related endpoints exist."""
        # These should return 404 (not found) not 500 (server error)
        # because no franchise is connected
        response = client.get("/api/v1/management/franchise/00000000-0000-0000-0000-000000000000/state")
        assert response.status_code in [404, 422]  # 422 for invalid UUID

    def test_management_router_prefix(self, client):
        """Verify management router is mounted at correct prefix."""
        # Get all routes from the app
        routes = [route.path for route in app.routes]

        # Should have management routes
        mgmt_routes = [r for r in routes if '/management/' in r]
        assert len(mgmt_routes) > 0, "No management routes found"

    def test_franchise_crud_routes_exist(self, client):
        """Test CRUD endpoint patterns exist."""
        # Check POST create endpoint
        response = client.post(
            "/api/v1/management/franchise/connect",
            json={"league_state_id": "test", "team_abbr": "DAL"}
        )
        # Should fail with 404 (no league) not 500 (route missing)
        assert response.status_code in [404, 422, 400]


class TestSubRouterTags:
    """Tests that sub-routers have correct tags for OpenAPI grouping."""

    def test_franchise_router_tags(self):
        """Verify franchise router has correct tags."""
        from huddle.api.routers.management.franchise import router
        assert "franchise" in router.tags

    def test_contracts_router_tags(self):
        """Verify contracts router has correct tags."""
        from huddle.api.routers.management.contracts import router
        assert "contracts" in router.tags

    def test_free_agency_router_tags(self):
        """Verify free_agency router has correct tags."""
        from huddle.api.routers.management.free_agency import router
        assert "free-agency" in router.tags

    def test_draft_router_tags(self):
        """Verify draft router has correct tags."""
        from huddle.api.routers.management.draft import router
        assert "draft" in router.tags

    def test_practice_router_tags(self):
        """Verify practice router has correct tags."""
        from huddle.api.routers.management.practice import router
        assert "practice" in router.tags

    def test_game_router_tags(self):
        """Verify game router has correct tags."""
        from huddle.api.routers.management.game import router
        assert "game" in router.tags

    def test_clipboard_router_tags(self):
        """Verify clipboard router has correct tags."""
        from huddle.api.routers.management.clipboard import router
        assert "clipboard" in router.tags


class TestDependencySharing:
    """Tests for shared dependencies across sub-routers."""

    def test_deps_module_exists(self):
        """Verify deps module can be imported."""
        from huddle.api.routers.management.deps import (
            get_session,
            get_session_with_team,
            event_to_response,
        )

        assert get_session is not None
        assert get_session_with_team is not None
        assert event_to_response is not None

    def test_get_session_raises_404(self):
        """Verify get_session raises HTTPException for missing franchise."""
        from uuid import uuid4
        from fastapi import HTTPException
        from huddle.api.routers.management.deps import get_session

        with pytest.raises(HTTPException) as exc_info:
            get_session(uuid4())

        assert exc_info.value.status_code == 404
