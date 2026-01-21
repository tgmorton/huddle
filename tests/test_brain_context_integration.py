"""Brain/Context Integration Tests.

Tests that verify:
1. Each brain receives the correct context type
2. BallcarrierContextBase inheritance works (WR, RB, QB can become ballcarriers)
3. All brains return valid BrainDecision outputs
4. Context fields are properly populated and accessible

This test matrix ensures the brain/context contract is maintained.
"""

import pytest
from dataclasses import dataclass
from typing import Optional

from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.core.entities import (
    Player,
    Team,
    Position,
    PlayerAttributes,
    Ball,
    BallState,
    PlayerPlayState,
)
from huddle.simulation.v2.core.contexts import (
    WorldStateBase,
    BallcarrierContextBase,
    QBContext,
    WRContext,
    RBContext,
    OLContext,
    DLContext,
    LBContext,
    DBContext,
    BallcarrierContext,
)
from huddle.simulation.v2.orchestrator import BrainDecision
from huddle.simulation.v2.ai.qb_brain import qb_brain
from huddle.simulation.v2.ai.receiver_brain import receiver_brain
from huddle.simulation.v2.ai.ballcarrier_brain import ballcarrier_brain
from huddle.simulation.v2.ai.ol_brain import ol_brain
from huddle.simulation.v2.ai.dl_brain import dl_brain
from huddle.simulation.v2.ai.lb_brain import lb_brain
from huddle.simulation.v2.ai.db_brain import db_brain
from huddle.simulation.v2.ai.rusher_brain import rusher_brain
from huddle.simulation.v2.core.variance import (
    set_config,
    VarianceConfig,
    SimulationMode,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def deterministic_mode():
    """Set deterministic mode for predictable tests."""
    set_config(VarianceConfig(mode=SimulationMode.DETERMINISTIC))
    yield
    set_config(VarianceConfig(mode=SimulationMode.REALISTIC))


@pytest.fixture
def mock_qb():
    """Create a mock QB player."""
    return Player(
        id="QB1",
        name="Test QB",
        team=Team.OFFENSE,
        position=Position.QB,
        pos=Vec2(0, -5),
        has_ball=True,
        attributes=PlayerAttributes(
            throw_power=85,
            throw_accuracy=85,
            speed=75,
            acceleration=78,
            poise=80,
            decision_making=82,
            anticipation=80,
        ),
    )


@pytest.fixture
def mock_wr():
    """Create a mock WR player."""
    return Player(
        id="WR1",
        name="Test WR",
        team=Team.OFFENSE,
        position=Position.WR,
        pos=Vec2(20, 0),
        has_ball=False,
        attributes=PlayerAttributes(
            speed=90,
            acceleration=88,
            agility=86,
            route_running=85,
            catching=85,
        ),
    )


@pytest.fixture
def mock_rb():
    """Create a mock RB player."""
    return Player(
        id="RB1",
        name="Test RB",
        team=Team.OFFENSE,
        position=Position.RB,
        pos=Vec2(-2, -3),
        has_ball=False,
        attributes=PlayerAttributes(
            speed=88,
            acceleration=90,
            agility=88,
            elusiveness=85,
            strength=80,
            vision=82,
        ),
    )


@pytest.fixture
def mock_ol():
    """Create a mock OL player."""
    return Player(
        id="LT1",
        name="Test LT",
        team=Team.OFFENSE,
        position=Position.LT,
        pos=Vec2(-6, 0),
        has_ball=False,
        attributes=PlayerAttributes(
            strength=85,
            block_power=84,
            block_finesse=83,
            awareness=75,
        ),
    )


@pytest.fixture
def mock_dl():
    """Create a mock DL player."""
    return Player(
        id="DE1",
        name="Test DE",
        team=Team.DEFENSE,
        position=Position.DE,
        pos=Vec2(-5, 1),
        has_ball=False,
        attributes=PlayerAttributes(
            speed=82,
            acceleration=85,
            strength=88,
            pass_rush=85,
            awareness=78,
        ),
    )


@pytest.fixture
def mock_lb():
    """Create a mock LB player."""
    return Player(
        id="MLB1",
        name="Test MLB",
        team=Team.DEFENSE,
        position=Position.MLB,
        pos=Vec2(0, -5),
        has_ball=False,
        attributes=PlayerAttributes(
            speed=82,
            acceleration=84,
            tackling=85,
            play_recognition=80,
            zone_coverage=75,
            awareness=82,
        ),
    )


@pytest.fixture
def mock_cb():
    """Create a mock CB player."""
    return Player(
        id="CB1",
        name="Test CB",
        team=Team.DEFENSE,
        position=Position.CB,
        pos=Vec2(22, 7),
        has_ball=False,
        attributes=PlayerAttributes(
            speed=92,
            acceleration=90,
            agility=88,
            man_coverage=84,
            zone_coverage=80,
            play_recognition=78,
        ),
    )


@pytest.fixture
def mock_ball():
    """Create a mock ball in held state."""
    ball = Ball()
    ball.state = BallState.HELD
    ball.carrier_id = "QB1"
    ball.pos = Vec2(0, -5)
    return ball


@pytest.fixture
def mock_ball_view(mock_ball):
    """Create a ball view compatible with contexts."""
    @dataclass
    class BallView:
        state: BallState = BallState.HELD
        pos: Vec2 = None
        carrier_id: Optional[str] = None
        target_pos: Optional[Vec2] = None

        @property
        def is_in_flight(self) -> bool:
            return self.state == BallState.IN_FLIGHT

        @property
        def is_held(self) -> bool:
            return self.state == BallState.HELD

        @property
        def is_dead(self) -> bool:
            return self.state == BallState.DEAD

    return BallView(
        state=mock_ball.state,
        pos=mock_ball.pos,
        carrier_id=mock_ball.carrier_id,
    )


def make_player_view(player: Player):
    """Create a player view for context population."""
    @dataclass
    class PlayerView:
        id: str
        pos: Vec2
        velocity: Vec2
        position: Position
        has_ball: bool
        team: Team
        attributes: PlayerAttributes
        facing: Vec2 = None
        distance: float = 0.0
        # Speed attribute directly exposed for brain access
        speed: int = 75
        acceleration: int = 75

    return PlayerView(
        id=player.id,
        pos=player.pos,
        velocity=getattr(player, 'velocity', Vec2(0, 0)),
        position=player.position,
        has_ball=player.has_ball,
        team=player.team,
        attributes=player.attributes,
        facing=Vec2(0, 1),
        distance=10.0,
        speed=player.attributes.speed,
        acceleration=player.attributes.acceleration,
    )


# =============================================================================
# Context Type Tests
# =============================================================================

class TestContextTypeMatching:
    """Verify each brain receives the correct context type."""

    def test_qb_brain_accepts_qb_context(self, mock_qb, mock_ball_view, mock_wr):
        """QB brain should accept QBContext."""
        ctx = QBContext(
            me=mock_qb,
            ball=mock_ball_view,
            teammates=[make_player_view(mock_wr)],
            opponents=[],
            time_since_snap=0.5,
            los_y=0.0,
            dropback_depth=7.0,
            qb_is_set=False,
        )

        decision = qb_brain(ctx)
        assert isinstance(decision, BrainDecision)

    def test_receiver_brain_accepts_wr_context(self, mock_wr, mock_ball_view):
        """Receiver brain should accept WRContext."""
        ctx = WRContext(
            me=mock_wr,
            ball=mock_ball_view,
            teammates=[],
            opponents=[],
            time_since_snap=0.5,
            los_y=0.0,
            route_target=Vec2(20, 10),
            route_phase="stem",
        )

        decision = receiver_brain(ctx)
        assert isinstance(decision, BrainDecision)

    def test_receiver_brain_accepts_rb_context(self, mock_rb, mock_ball_view):
        """Receiver brain should accept RBContext for pass-catching backs."""
        # Note: RBContext doesn't have route_target, but receiver_brain
        # handles this via getattr with defaults for route fields
        ctx = RBContext(
            me=mock_rb,
            ball=mock_ball_view,
            teammates=[],
            opponents=[],
            time_since_snap=0.5,
            los_y=0.0,
            run_path=[Vec2(5, 3)],  # RB uses run_path
            is_run_play=False,  # Pass play - RB running check-down
        )

        decision = receiver_brain(ctx)
        assert isinstance(decision, BrainDecision)

    def test_ol_brain_accepts_ol_context(self, mock_ol, mock_ball_view, mock_dl):
        """OL brain should accept OLContext."""
        ctx = OLContext(
            me=mock_ol,
            ball=mock_ball_view,
            teammates=[],
            opponents=[make_player_view(mock_dl)],
            time_since_snap=0.5,
            los_y=0.0,
            is_run_play=False,
            slide_direction="left",
        )

        decision = ol_brain(ctx)
        assert isinstance(decision, BrainDecision)

    def test_dl_brain_accepts_dl_context(self, mock_dl, mock_ball_view, mock_ol):
        """DL brain should accept DLContext."""
        ctx = DLContext(
            me=mock_dl,
            ball=mock_ball_view,
            teammates=[],
            opponents=[make_player_view(mock_ol)],
            time_since_snap=0.5,
            los_y=0.0,
            is_run_play=False,
        )

        decision = dl_brain(ctx)
        assert isinstance(decision, BrainDecision)

    def test_lb_brain_accepts_lb_context(self, mock_lb, mock_ball_view, mock_qb):
        """LB brain should accept LBContext."""
        ctx = LBContext(
            me=mock_lb,
            ball=mock_ball_view,
            teammates=[],
            opponents=[make_player_view(mock_qb)],
            time_since_snap=0.5,
            los_y=0.0,
            is_run_play=False,
        )

        decision = lb_brain(ctx)
        assert isinstance(decision, BrainDecision)

    def test_db_brain_accepts_db_context(self, mock_cb, mock_ball_view, mock_wr):
        """DB brain should accept DBContext."""
        ctx = DBContext(
            me=mock_cb,
            ball=mock_ball_view,
            teammates=[],
            opponents=[make_player_view(mock_wr)],
            time_since_snap=0.5,
            los_y=0.0,
            is_run_play=False,
            target_id="WR1",
            assignment="man",
        )

        decision = db_brain(ctx)
        assert isinstance(decision, BrainDecision)

    def test_rusher_brain_accepts_rb_context(self, mock_rb, mock_ball_view):
        """Rusher brain should accept RBContext."""
        ctx = RBContext(
            me=mock_rb,
            ball=mock_ball_view,
            teammates=[],
            opponents=[],
            time_since_snap=0.3,
            los_y=0.0,
            is_run_play=True,
            run_aiming_point="b_right",
            run_play_side="right",
            run_mesh_depth=4.0,
        )

        decision = rusher_brain(ctx)
        assert isinstance(decision, BrainDecision)


# =============================================================================
# BallcarrierContextBase Inheritance Tests
# =============================================================================

class TestBallcarrierContextInheritance:
    """Verify BallcarrierContextBase inheritance for position transitions."""

    def test_wr_context_is_ballcarrier_base(self, mock_wr):
        """WRContext should inherit from BallcarrierContextBase."""
        ctx = WRContext(me=mock_wr)
        assert isinstance(ctx, BallcarrierContextBase)
        assert hasattr(ctx, 'run_aiming_point')
        assert hasattr(ctx, 'run_play_side')
        assert hasattr(ctx, 'has_shed_immunity')

    def test_rb_context_is_ballcarrier_base(self, mock_rb):
        """RBContext should inherit from BallcarrierContextBase."""
        ctx = RBContext(me=mock_rb)
        assert isinstance(ctx, BallcarrierContextBase)
        assert hasattr(ctx, 'run_aiming_point')
        assert hasattr(ctx, 'run_play_side')
        assert hasattr(ctx, 'has_shed_immunity')

    def test_qb_context_is_ballcarrier_base(self, mock_qb):
        """QBContext should inherit from BallcarrierContextBase."""
        ctx = QBContext(me=mock_qb)
        assert isinstance(ctx, BallcarrierContextBase)
        assert hasattr(ctx, 'run_aiming_point')
        assert hasattr(ctx, 'run_play_side')
        assert hasattr(ctx, 'has_shed_immunity')

    def test_ballcarrier_brain_accepts_wr_context(self, mock_wr, mock_ball_view, mock_cb):
        """Ballcarrier brain should accept WRContext (after catch)."""
        mock_wr.has_ball = True
        mock_ball_view.carrier_id = "WR1"

        ctx = WRContext(
            me=mock_wr,
            ball=mock_ball_view,
            teammates=[],
            opponents=[make_player_view(mock_cb)],
            threats=[make_player_view(mock_cb)],
            time_since_snap=2.0,
            los_y=0.0,
            run_play_side="right",
        )

        decision = ballcarrier_brain(ctx)
        assert isinstance(decision, BrainDecision)

    def test_ballcarrier_brain_accepts_rb_context(self, mock_rb, mock_ball_view, mock_lb):
        """Ballcarrier brain should accept RBContext (on run plays)."""
        mock_rb.has_ball = True
        mock_ball_view.carrier_id = "RB1"

        ctx = RBContext(
            me=mock_rb,
            ball=mock_ball_view,
            teammates=[],
            opponents=[make_player_view(mock_lb)],
            threats=[make_player_view(mock_lb)],
            time_since_snap=1.0,
            los_y=0.0,
            is_run_play=True,
            run_aiming_point="b_right",
            run_play_side="right",
        )

        decision = ballcarrier_brain(ctx)
        assert isinstance(decision, BrainDecision)

    def test_ballcarrier_brain_accepts_qb_context(self, mock_qb, mock_ball_view, mock_dl):
        """Ballcarrier brain should accept QBContext (on scrambles)."""
        ctx = QBContext(
            me=mock_qb,
            ball=mock_ball_view,
            teammates=[],
            opponents=[make_player_view(mock_dl)],
            threats=[make_player_view(mock_dl)],
            time_since_snap=3.0,
            los_y=0.0,
            run_play_side="right",
        )

        decision = ballcarrier_brain(ctx)
        assert isinstance(decision, BrainDecision)


# =============================================================================
# Context Field Accessibility Tests
# =============================================================================

class TestContextFieldAccessibility:
    """Verify context fields are accessible as expected."""

    def test_qb_context_dropback_fields(self, mock_qb):
        """QBContext should have dropback-specific fields."""
        ctx = QBContext(
            me=mock_qb,
            dropback_depth=7.0,
            dropback_target_pos=Vec2(0, -7),
            qb_is_set=True,
            qb_set_time=0.8,
        )

        assert ctx.dropback_depth == 7.0
        assert ctx.dropback_target_pos == Vec2(0, -7)
        assert ctx.qb_is_set is True
        assert ctx.qb_set_time == 0.8

    def test_wr_context_route_fields(self, mock_wr):
        """WRContext should have route-specific fields."""
        ctx = WRContext(
            me=mock_wr,
            route_target=Vec2(20, 15),
            route_phase="break",
            at_route_break=True,
            route_settles=False,
        )

        assert ctx.route_target == Vec2(20, 15)
        assert ctx.route_phase == "break"
        assert ctx.at_route_break is True
        assert ctx.route_settles is False

    def test_rb_context_run_fields(self, mock_rb):
        """RBContext should have run-specific fields."""
        ctx = RBContext(
            me=mock_rb,
            run_aiming_point="a_left",
            run_play_side="left",
            run_mesh_depth=4.5,
            run_path=[Vec2(0, -3), Vec2(-2, 0)],
        )

        assert ctx.run_aiming_point == "a_left"
        assert ctx.run_play_side == "left"
        assert ctx.run_mesh_depth == 4.5
        assert len(ctx.run_path) == 2

    def test_ol_context_blocking_fields(self, mock_ol):
        """OLContext should have blocking-specific fields."""
        ctx = OLContext(
            me=mock_ol,
            is_run_play=True,
            run_play_side="right",
            run_blocking_assignment="zone_step",
            slide_direction="left",
        )

        assert ctx.is_run_play is True
        assert ctx.run_play_side == "right"
        assert ctx.run_blocking_assignment == "zone_step"
        assert ctx.slide_direction == "left"

    def test_dl_context_shed_fields(self, mock_dl):
        """DLContext should have shed immunity field."""
        ctx = DLContext(
            me=mock_dl,
            has_shed_immunity=True,
        )

        assert ctx.has_shed_immunity is True

    def test_base_context_situational_fields(self, mock_qb):
        """All contexts should have situational fields from base."""
        ctx = WorldStateBase(
            me=mock_qb,
            down=3,
            distance=7.5,
            los_y=35.0,
            is_run_play=False,
        )

        assert ctx.down == 3
        assert ctx.distance == 7.5
        assert ctx.los_y == 35.0
        assert ctx.is_run_play is False


# =============================================================================
# Play State Tests
# =============================================================================

class TestPlayStateInContext:
    """Verify play state is correctly passed through context."""

    def test_context_includes_play_state(self, mock_qb):
        """Context should include play_state field."""
        ctx = QBContext(
            me=mock_qb,
            play_state=PlayerPlayState.IN_DROPBACK,
            time_in_state=0.3,
        )

        assert ctx.play_state == PlayerPlayState.IN_DROPBACK
        assert ctx.time_in_state == 0.3

    def test_all_play_states_valid_in_context(self, mock_qb):
        """All PlayerPlayState values should be valid in context."""
        states_to_test = [
            PlayerPlayState.SETUP,
            PlayerPlayState.IN_DROPBACK,
            PlayerPlayState.IN_POCKET,
            PlayerPlayState.SCRAMBLING,
            PlayerPlayState.BALLCARRIER,
            PlayerPlayState.DOWN,
        ]

        for state in states_to_test:
            ctx = QBContext(me=mock_qb, play_state=state)
            assert ctx.play_state == state


# =============================================================================
# Brain Decision Validation Tests
# =============================================================================

class TestBrainDecisionValidity:
    """Verify brains return valid decisions with required fields."""

    def test_decision_has_intent_or_action(self, mock_qb, mock_ball_view, mock_wr):
        """Every brain decision should have either intent or action."""
        ctx = QBContext(
            me=mock_qb,
            ball=mock_ball_view,
            teammates=[make_player_view(mock_wr)],
            opponents=[],
            time_since_snap=0.5,
            los_y=0.0,
        )

        decision = qb_brain(ctx)

        # Should have at least intent or action
        has_intent = bool(decision.intent)
        has_action = decision.action is not None
        has_move = decision.move_target is not None

        assert has_intent or has_action or has_move, \
            f"Decision should have intent/action/move: {decision}"

    def test_movement_decision_has_valid_target(self, mock_lb, mock_ball_view, mock_qb):
        """Movement decisions should have valid Vec2 target."""
        ctx = LBContext(
            me=mock_lb,
            ball=mock_ball_view,
            teammates=[],
            opponents=[make_player_view(mock_qb)],
            time_since_snap=0.5,
            los_y=0.0,
            is_run_play=False,
        )

        decision = lb_brain(ctx)

        if decision.move_target is not None:
            assert isinstance(decision.move_target, Vec2), \
                f"move_target should be Vec2, got {type(decision.move_target)}"

    def test_decision_has_reasoning(self, mock_dl, mock_ball_view, mock_ol):
        """Decisions should include reasoning for debugging."""
        ctx = DLContext(
            me=mock_dl,
            ball=mock_ball_view,
            teammates=[],
            opponents=[make_player_view(mock_ol)],
            time_since_snap=0.5,
            los_y=0.0,
        )

        decision = dl_brain(ctx)

        # Reasoning is helpful for debugging but not strictly required
        # Just verify it's a string
        assert isinstance(decision.reasoning, str)


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Test edge cases and unusual situations."""

    def test_empty_opponents_list(self, mock_qb, mock_ball_view):
        """Brains should handle empty opponents list."""
        ctx = QBContext(
            me=mock_qb,
            ball=mock_ball_view,
            teammates=[],
            opponents=[],
            time_since_snap=0.5,
            los_y=0.0,
        )

        # Should not raise
        decision = qb_brain(ctx)
        assert isinstance(decision, BrainDecision)

    def test_empty_teammates_list(self, mock_dl, mock_ball_view):
        """Brains should handle empty teammates list."""
        ctx = DLContext(
            me=mock_dl,
            ball=mock_ball_view,
            teammates=[],
            opponents=[],
            time_since_snap=0.5,
            los_y=0.0,
        )

        decision = dl_brain(ctx)
        assert isinstance(decision, BrainDecision)

    def test_zero_time_since_snap(self, mock_ol, mock_ball_view):
        """Brains should handle t=0 (snap moment)."""
        ctx = OLContext(
            me=mock_ol,
            ball=mock_ball_view,
            teammates=[],
            opponents=[],
            time_since_snap=0.0,
            los_y=0.0,
        )

        decision = ol_brain(ctx)
        assert isinstance(decision, BrainDecision)

    def test_very_late_in_play(self, mock_cb, mock_ball_view, mock_wr):
        """Brains should handle late-play scenarios."""
        ctx = DBContext(
            me=mock_cb,
            ball=mock_ball_view,
            teammates=[],
            opponents=[make_player_view(mock_wr)],
            time_since_snap=8.0,  # Very late in play
            los_y=0.0,
            target_id="WR1",
            assignment="man",
        )

        decision = db_brain(ctx)
        assert isinstance(decision, BrainDecision)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
