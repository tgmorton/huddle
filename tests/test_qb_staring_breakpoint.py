"""Test QB Staring Down First Read fix and Break Point Throw Lead.

Tests from behavior_tree_agent messages:
1. QB Staring Down Fix - adds minimum pocket time (0.4s) and minimum separation (2.0yd)
   for anticipation throws to prevent QB from instantly locking onto first read
2. Break Point Throw Lead - QB throws to break_point for pre-break receivers
   instead of extrapolating current velocity (which misses by 2-4 yards)
"""

import pytest
from huddle.simulation.v2.ai.qb_brain import (
    _can_throw_anticipation,
    _calculate_throw_lead,
    ReceiverEval,
    ReceiverStatus,
    PressureLevel,
)
from huddle.simulation.v2.core.vec2 import Vec2


# =============================================================================
# QB Staring Down First Read Fix Tests
# =============================================================================

class TestQBStaringDownFix:
    """Tests for minimum pocket time and separation requirements."""

    def test_anticipation_blocked_too_early(self):
        """QB should NOT throw anticipation before 0.4s in pocket."""
        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(10, 25),
            velocity=Vec2(0, 8),
            separation=3.0,  # Good separation
            status=ReceiverStatus.WINDOW,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="stem",
            is_hot=False,
            read_order=1,
            defender_trailing=True,  # Defender behind
            pre_break=True,
            detection_quality=1.0,
        )

        # At 0.2s - should be blocked (too early)
        can_anticipate, reason = _can_throw_anticipation(
            accuracy=92,
            receiver=receiver,
            pressure=PressureLevel.CLEAN,
            time_in_pocket=0.2,
        )

        assert can_anticipate is False
        assert "too early" in reason.lower() or "0.4s" in reason

    def test_anticipation_allowed_after_minimum_time(self):
        """QB CAN throw anticipation after 0.4s pocket time."""
        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(10, 25),
            velocity=Vec2(0, 8),
            separation=3.0,  # Good separation
            status=ReceiverStatus.WINDOW,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="stem",
            is_hot=False,
            read_order=1,
            defender_trailing=True,
            pre_break=True,
            detection_quality=1.0,
        )

        # At 0.5s - should be allowed (past minimum)
        can_anticipate, reason = _can_throw_anticipation(
            accuracy=92,
            receiver=receiver,
            pressure=PressureLevel.CLEAN,
            time_in_pocket=0.5,
        )

        assert can_anticipate is True
        assert "elite accuracy" in reason.lower() or "anticipation" in reason.lower()

    def test_anticipation_blocked_tight_separation(self):
        """QB should NOT throw anticipation with < 2.0yd separation."""
        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(10, 25),
            velocity=Vec2(0, 8),
            separation=1.5,  # Too tight!
            status=ReceiverStatus.CONTESTED,
            nearest_defender_id="CB1",
            defender_closing_speed=1.0,
            route_phase="stem",
            is_hot=False,
            read_order=1,
            defender_trailing=True,
            pre_break=True,
            detection_quality=1.0,
        )

        # Even with good pocket time, separation is too tight
        can_anticipate, reason = _can_throw_anticipation(
            accuracy=92,
            receiver=receiver,
            pressure=PressureLevel.CLEAN,
            time_in_pocket=0.6,
        )

        assert can_anticipate is False
        assert "separation" in reason.lower() or "tight" in reason.lower()

    def test_anticipation_allowed_good_separation(self):
        """QB CAN throw anticipation with >= 2.0yd separation."""
        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(10, 25),
            velocity=Vec2(0, 8),
            separation=2.5,  # Good separation
            status=ReceiverStatus.WINDOW,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="stem",
            is_hot=False,
            read_order=1,
            defender_trailing=True,
            pre_break=True,
            detection_quality=1.0,
        )

        can_anticipate, reason = _can_throw_anticipation(
            accuracy=92,
            receiver=receiver,
            pressure=PressureLevel.CLEAN,
            time_in_pocket=0.6,
        )

        assert can_anticipate is True

    def test_anticipation_boundary_conditions(self):
        """Test exact boundary at 0.4s and 2.0yd."""
        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(10, 25),
            velocity=Vec2(0, 8),
            separation=2.0,  # Exactly at boundary
            status=ReceiverStatus.WINDOW,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="stem",
            is_hot=False,
            read_order=1,
            defender_trailing=True,
            pre_break=True,
            detection_quality=1.0,
        )

        # At exactly 0.4s - should be ALLOWED (0.4s is the minimum, not below)
        # Implementation: if time_in_pocket < 0.4 means >= 0.4 is OK
        can_anticipate_at_min, _ = _can_throw_anticipation(
            accuracy=92,
            receiver=receiver,
            pressure=PressureLevel.CLEAN,
            time_in_pocket=0.4,
        )

        # At 0.39s - should be blocked (below minimum)
        can_anticipate_below, _ = _can_throw_anticipation(
            accuracy=92,
            receiver=receiver,
            pressure=PressureLevel.CLEAN,
            time_in_pocket=0.39,
        )

        # At exactly 2.0yd separation - should be blocked (< 2.0 means 2.0 is blocked)
        receiver_boundary = ReceiverEval(
            player_id="WR1",
            position=Vec2(10, 25),
            velocity=Vec2(0, 8),
            separation=1.99,  # Just under 2.0
            status=ReceiverStatus.WINDOW,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="stem",
            is_hot=False,
            read_order=1,
            defender_trailing=True,
            pre_break=True,
            detection_quality=1.0,
        )

        can_anticipate_tight, _ = _can_throw_anticipation(
            accuracy=92,
            receiver=receiver_boundary,
            pressure=PressureLevel.CLEAN,
            time_in_pocket=0.5,
        )

        assert can_anticipate_tight is False
        # 0.4s is the minimum threshold (>= 0.4 is allowed)
        assert can_anticipate_at_min is True
        assert can_anticipate_below is False


# =============================================================================
# Break Point Throw Lead Tests
# =============================================================================

class TestBreakPointThrowLead:
    """Tests for throwing to break_point for pre-break receivers."""

    def test_throw_to_break_point_pre_break(self):
        """QB should throw to break_point for pre-break receivers."""
        qb_pos = Vec2(0, 55)
        break_point = Vec2(15, 40)  # Where receiver will cut

        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(10, 45),  # Current position
            velocity=Vec2(3, -5),   # Moving toward sideline and downfield
            separation=3.0,
            status=ReceiverStatus.WINDOW,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="stem",
            is_hot=False,
            read_order=1,
            pre_break=True,  # KEY: receiver is pre-break
            detection_quality=1.0,
            break_point=break_point,  # KEY: break point is known
        )

        lead_pos = _calculate_throw_lead(qb_pos, receiver, throw_power=80)

        # Should throw to break_point with YAC lead past it in route direction
        # Since route_direction not set, defaults to vertical (0, 1)
        # So lead should be at break_point.y + YAC_LEAD (1.5 yards)
        assert lead_pos.x == break_point.x  # X unchanged for vertical route
        assert lead_pos.y > break_point.y  # Y is past break point
        assert lead_pos.y < break_point.y + 2.0  # But not too far

    def test_no_break_point_uses_actual_velocity(self):
        """Without break_point, use actual velocity direction for lead."""
        qb_pos = Vec2(0, 55)

        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(10, 45),
            velocity=Vec2(0, -7),  # Moving downfield at 7 yd/s
            separation=3.0,
            status=ReceiverStatus.OPEN,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="stem",
            is_hot=False,
            read_order=1,
            pre_break=True,
            detection_quality=1.0,
            break_point=None,  # No break point (like GO route)
            route_direction="vertical",
        )

        lead_pos = _calculate_throw_lead(qb_pos, receiver, throw_power=80)

        # Should lead in velocity direction (downfield = negative Y)
        assert lead_pos.y < receiver.position.y, \
            f"Expected lead downfield, got {lead_pos.y} vs receiver at {receiver.position.y}"
        # X should stay near current position
        assert abs(lead_pos.x - receiver.position.x) < 1.0

    def test_post_break_sitting_route_no_lead(self):
        """Post-break sitting routes (hitch, curl) get no lead."""
        qb_pos = Vec2(0, 55)

        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(10, 42),
            velocity=Vec2(0.5, 0),  # Barely moving (settled)
            separation=3.0,
            status=ReceiverStatus.OPEN,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="post_break",  # Past break
            is_hot=False,
            read_order=1,
            pre_break=False,
            detection_quality=1.0,
            break_point=None,
        )

        lead_pos = _calculate_throw_lead(qb_pos, receiver, throw_power=80)

        # Sitting route - throw right at them (lead_factor = 0)
        assert abs(lead_pos.x - receiver.position.x) < 0.5
        assert abs(lead_pos.y - receiver.position.y) < 0.5

    def test_post_break_moving_route_full_lead(self):
        """Post-break moving routes (go, post) get full lead."""
        qb_pos = Vec2(0, 55)

        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(10, 30),
            velocity=Vec2(0, -10),  # Moving downfield fast
            separation=4.0,
            status=ReceiverStatus.OPEN,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="post_break",
            is_hot=False,
            read_order=1,
            pre_break=False,
            detection_quality=1.0,
            break_point=None,
        )

        lead_pos = _calculate_throw_lead(qb_pos, receiver, throw_power=80)

        # Moving post-break - full lead (lead_factor = 1.0)
        # Lead should project receiver position based on ball flight
        assert lead_pos.y < receiver.position.y  # Ahead of current position (downfield)

    def test_break_point_slant_route(self):
        """Slant route should throw to break point with YAC lead past it."""
        qb_pos = Vec2(0, 55)

        # Receiver running vertically, about to break inside
        break_point = Vec2(5, 40)  # Where the slant will break to

        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(-5, 48),  # Currently outside
            velocity=Vec2(0, -6),   # Running straight ahead (pre-break)
            separation=2.5,
            status=ReceiverStatus.WINDOW,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="stem",
            is_hot=False,
            read_order=1,
            pre_break=True,
            detection_quality=1.0,
            break_point=break_point,
        )

        lead_pos = _calculate_throw_lead(qb_pos, receiver, throw_power=85)

        # Should throw at/near break_point X (inside), not straight ahead
        assert lead_pos.x == break_point.x
        # Y should be PAST break point for YAC (catch in stride)
        assert lead_pos.y > break_point.y
        assert lead_pos.y < break_point.y + 2.0  # But not too far
        # Verify we DIDN'T just extrapolate velocity (which would put ball at -5, 42)
        assert lead_pos.x != receiver.position.x

    def test_break_point_out_route(self):
        """Out route should throw to break point toward sideline with YAC lead."""
        qb_pos = Vec2(0, 55)

        # Receiver running straight, about to break outside
        break_point = Vec2(20, 42)  # Break point toward sideline

        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(8, 47),   # Current position
            velocity=Vec2(0, -5),   # Running straight ahead
            separation=3.0,
            status=ReceiverStatus.OPEN,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="stem",
            is_hot=False,
            read_order=1,
            pre_break=True,
            detection_quality=1.0,
            break_point=break_point,
        )

        lead_pos = _calculate_throw_lead(qb_pos, receiver, throw_power=80)

        # Should throw at/near break_point X (outside), with YAC lead past in Y
        assert lead_pos.x == break_point.x
        # Y should be PAST break point for YAC (catch in stride)
        assert lead_pos.y > break_point.y
        assert lead_pos.y < break_point.y + 2.0  # But not too far


# =============================================================================
# 4 Verts / Close-to-Break Tests
# =============================================================================

class TestCloseToBreakThrows:
    """Tests for receivers close to their break point (like 4 Verts)."""

    def test_receiver_close_to_break_gets_lead_past_it(self):
        """When receiver is close to break, throw PAST the break point.

        This is the 4 Verts scenario: receiver running a go route with a
        subtle speed cut, almost at the break. Ball should go well past
        the break so receiver catches in stride.
        """
        qb_pos = Vec2(0, 55)
        break_point = Vec2(10, 32)  # Break point 23 yards downfield

        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(10, 33),  # Only 1 yard from break!
            velocity=Vec2(0, -7),   # Running 7 yd/s downfield
            separation=3.0,
            status=ReceiverStatus.OPEN,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="stem",
            is_hot=False,
            read_order=1,
            pre_break=True,
            detection_quality=1.0,
            break_point=break_point,
            route_direction="",  # Vertical (default)
        )

        lead_pos = _calculate_throw_lead(qb_pos, receiver, throw_power=85)

        # Receiver is 1 yard from break, running 7 yd/s
        # Time to break = 1/7 = 0.14 seconds
        # Ball flight to break point (23 yards) at ~77fps = 0.30 seconds
        # Receiver reaches break 0.16s before ball - has moved 1+ yards past break

        # Y should be past break point (receiver + YAC buffer)
        assert lead_pos.y > break_point.y + 1.5, \
            f"Expected lead past break, got {lead_pos.y} vs break at {break_point.y}"

        # X should be at break point (vertical route)
        assert abs(lead_pos.x - break_point.x) < 0.5

    def test_receiver_far_from_break_throws_to_break(self):
        """When receiver is far from break, throw to break point.

        Ball arrives at break before receiver, so throw there with YAC lead.
        """
        qb_pos = Vec2(0, 55)
        break_point = Vec2(10, 35)  # Break point

        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(10, 50),  # 15 yards from break
            velocity=Vec2(0, -6),   # Running 6 yd/s downfield
            separation=3.0,
            status=ReceiverStatus.WINDOW,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="stem",
            is_hot=False,
            read_order=1,
            pre_break=True,
            detection_quality=1.0,
            break_point=break_point,
            route_direction="",  # Vertical
        )

        lead_pos = _calculate_throw_lead(qb_pos, receiver, throw_power=80)

        # Receiver is 15 yards from break at 6 yd/s = 2.5 seconds
        # Ball flight to break (20 yards) = ~0.35 seconds
        # Ball arrives WAY before receiver - throw to break with small lead

        # X at break point
        assert abs(lead_pos.x - break_point.x) < 0.5

        # Y just past break point (YAC buffer ~1 yard, not 5+)
        assert lead_pos.y > break_point.y
        assert lead_pos.y < break_point.y + 3.0, \
            f"Expected lead near break, got {lead_pos.y} vs break at {break_point.y}"

    def test_four_verts_seam_route(self):
        """Seam route in 4 Verts - receiver splits safeties, needs lead deep."""
        qb_pos = Vec2(0, 55)
        break_point = Vec2(5, 30)  # Seam route break (speed cut)

        receiver = ReceiverEval(
            player_id="TE1",
            position=Vec2(5, 33),  # 3 yards from break
            velocity=Vec2(0, -6.5),  # Running seam
            separation=2.0,
            status=ReceiverStatus.WINDOW,
            nearest_defender_id="FS1",
            defender_closing_speed=1.0,
            route_phase="stem",
            is_hot=False,
            read_order=2,
            pre_break=True,
            detection_quality=1.0,
            break_point=break_point,
            route_direction="",  # Vertical
        )

        lead_pos = _calculate_throw_lead(qb_pos, receiver, throw_power=82)

        # Should throw past break for catch in stride
        assert lead_pos.y > break_point.y, "Seam route needs lead past break"
        # X stays on the seam
        assert abs(lead_pos.x - break_point.x) < 1.0

    def test_four_verts_go_route_no_break_point(self):
        """GO route in 4 Verts - no break point, use velocity for lead.

        GO routes don't have a defined break point (they just keep running).
        The QB should lead based on receiver's actual velocity.
        """
        qb_pos = Vec2(0, 55)

        # Receiver running GO route - 10 yards downfield, running at full speed
        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(15, 45),  # 10 yards from QB
            velocity=Vec2(0, -7.5),  # Running downfield at 7.5 yd/s
            separation=2.5,
            status=ReceiverStatus.WINDOW,
            nearest_defender_id="CB1",
            defender_closing_speed=0.5,
            route_phase="stem",
            is_hot=False,
            read_order=1,
            pre_break=True,
            detection_quality=1.0,
            break_point=None,  # GO routes have no break!
            route_direction="vertical",
        )

        lead_pos = _calculate_throw_lead(qb_pos, receiver, throw_power=85)

        # Should lead DOWNFIELD (negative Y) based on velocity
        assert lead_pos.y < receiver.position.y, \
            f"GO route needs downfield lead, got {lead_pos.y} vs receiver at {receiver.position.y}"

        # Lead should be significant for deep ball
        lead_amount = receiver.position.y - lead_pos.y
        assert lead_amount > 1.5, \
            f"Expected significant lead for deep ball, got {lead_amount} yards"

        # X should stay on the route line
        assert abs(lead_pos.x - receiver.position.x) < 1.0

    def test_early_throw_receiver_just_off_los(self):
        """Early throw when receiver just released off LOS.

        If receiver is barely moving (just off the line), QB should still
        lead in the route direction, not throw behind them.

        Coordinate system: +Y = downfield
        """
        qb_pos = Vec2(0, 55)  # QB behind LOS

        # Receiver just released, barely moving yet but heading downfield
        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(12, 57),  # 2 yards downfield from LOS
            velocity=Vec2(0, 1.5),  # Just starting to accelerate downfield (+Y)
            separation=4.0,
            status=ReceiverStatus.OPEN,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="stem",
            is_hot=True,  # Hot route - quick throw
            read_order=1,
            pre_break=True,
            detection_quality=1.0,
            break_point=None,
            route_direction="vertical",
        )

        lead_pos = _calculate_throw_lead(qb_pos, receiver, throw_power=75)

        # Even with slow receiver, should lead downfield (+Y)
        # not throw behind them
        assert lead_pos.y >= receiver.position.y, \
            f"Should lead downfield, got {lead_pos.y} vs {receiver.position.y}"

    def test_mesh_post_break_receiver_not_thrown_behind(self):
        """Mesh crossing route - receiver past break should NOT get throw to break point.

        On mesh, receivers cross past their break points. If QB throws after
        the break, should lead based on velocity, not throw back to break point.
        """
        qb_pos = Vec2(0, 55)

        # Left slot has crossed past their break point, now heading right
        # Break was at (-5, 52), receiver is now at (0, 51) heading toward (+5, 50)
        break_point = Vec2(-5, 52)  # Where they broke (behind them now!)

        receiver = ReceiverEval(
            player_id="SLOT_L",
            position=Vec2(0, 51),  # Past the break, crossing middle
            velocity=Vec2(6, -1),  # Moving right and slightly downfield
            separation=3.0,
            status=ReceiverStatus.OPEN,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="post_break",  # KEY: past the break!
            is_hot=True,
            read_order=1,
            pre_break=False,  # KEY: NOT pre-break
            detection_quality=1.0,
            break_point=break_point,  # This is BEHIND them
            route_direction="inside",
        )

        lead_pos = _calculate_throw_lead(qb_pos, receiver, throw_power=80)

        # Should NOT throw back to break point at x=-5!
        # Should lead based on velocity (heading toward positive X)
        assert lead_pos.x > receiver.position.x, \
            f"Should lead ahead of post-break receiver, got x={lead_pos.x} vs receiver at x={receiver.position.x}"
        assert lead_pos.x > break_point.x + 3, \
            f"Should NOT throw back to break point at x={break_point.x}, got x={lead_pos.x}"


# =============================================================================
# Integration Tests
# =============================================================================

class TestStaringAndBreakPointIntegration:
    """Integration tests combining both fixes."""

    def test_elite_qb_anticipation_to_break_point(self):
        """Elite QB can anticipate to break point after minimum time."""
        qb_pos = Vec2(0, 55)
        break_point = Vec2(12, 38)

        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(5, 45),
            velocity=Vec2(3, -5),
            separation=2.5,  # Above 2.0yd minimum
            status=ReceiverStatus.WINDOW,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="stem",
            is_hot=False,
            read_order=1,
            defender_trailing=True,
            pre_break=True,
            detection_quality=1.0,
            break_point=break_point,
        )

        # Check anticipation is allowed
        can_anticipate, reason = _can_throw_anticipation(
            accuracy=92,
            receiver=receiver,
            pressure=PressureLevel.CLEAN,
            time_in_pocket=0.5,  # Above 0.4s minimum
        )

        assert can_anticipate is True

        # Check throw goes to break point with YAC lead past it
        lead_pos = _calculate_throw_lead(qb_pos, receiver, throw_power=85)
        assert lead_pos.x == break_point.x  # X at break point
        # Y is past break point for YAC
        assert lead_pos.y > break_point.y
        assert lead_pos.y < break_point.y + 2.0

    def test_low_accuracy_qb_waits_for_open(self):
        """Low accuracy QB must wait for receiver to be open."""
        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(10, 45),
            velocity=Vec2(0, 8),
            separation=3.0,
            status=ReceiverStatus.WINDOW,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="stem",
            is_hot=False,
            read_order=1,
            defender_trailing=True,
            pre_break=True,
            detection_quality=1.0,
        )

        # Low accuracy QB (68) cannot anticipate even with good time/separation
        can_anticipate, reason = _can_throw_anticipation(
            accuracy=68,
            receiver=receiver,
            pressure=PressureLevel.CLEAN,
            time_in_pocket=0.8,
        )

        assert can_anticipate is False
        assert "accuracy" in reason.lower()


# =============================================================================
# Settling Route Tests (Curl, Hitch, Comeback)
# =============================================================================

class TestSettlingRoutes:
    """Tests for settling routes where receiver stops at settle_point."""

    def test_curl_pre_break_throws_on_stem_not_settle(self):
        """Curl route pre-break should NOT throw to settle point.

        When receiver is still on the stem (pre-break), the settle point is
        FAR away because they have to go past it and curl back. The throw
        should go to where they'll be on the stem, not to the settle point.
        """
        qb_pos = Vec2(0, 55)  # QB at LOS

        # Curl route: stem to 12 yards, break, curl back to settle at 10 yards
        settle_point = Vec2(17, 62)  # Where they'll eventually stop
        break_point = Vec2(17, 64)   # Where they break (past settle!)

        # Receiver is early in stem - 5 yards from LOS, running upfield
        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(20, 57),   # Just 2 yards past LOS
            velocity=Vec2(-0.5, 6),  # Running upfield on stem, slight inside drift
            separation=4.0,
            status=ReceiverStatus.OPEN,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="stem",
            is_hot=False,
            read_order=1,
            pre_break=True,          # KEY: still on stem!
            detection_quality=1.0,
            break_point=break_point,
            route_direction="inside",
            route_settles=True,      # KEY: this is a settling route
            settle_point=settle_point,
        )

        lead_pos = _calculate_throw_lead(qb_pos, receiver, throw_power=80)

        # Should NOT throw to settle point (which is at y=62)
        # Should throw somewhere between receiver (y=57) and break point (y=64)
        # based on receiver's current stem direction
        assert lead_pos.y < settle_point.y + 1, \
            f"Should NOT throw past settle point, got y={lead_pos.y}, settle at y={settle_point.y}"

        # Should lead in receiver's velocity direction (upfield)
        assert lead_pos.y > receiver.position.y, \
            f"Should lead upfield on stem, got y={lead_pos.y} vs receiver at y={receiver.position.y}"

    def test_curl_post_break_throws_to_settle(self):
        """Curl route post-break should throw to settle point.

        After the break, receiver is curling back to settle. Now it's
        appropriate to throw to the settle point.
        """
        qb_pos = Vec2(0, 55)

        settle_point = Vec2(17, 62)
        break_point = Vec2(17, 64)

        # Receiver has broken and is curling back toward settle
        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(17, 63),   # Just past break, curling back
            velocity=Vec2(0, -2),    # Moving back toward settle
            separation=3.0,
            status=ReceiverStatus.OPEN,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="post_break",
            is_hot=False,
            read_order=1,
            pre_break=False,         # KEY: past break!
            detection_quality=1.0,
            break_point=break_point,
            route_direction="inside",
            route_settles=True,
            settle_point=settle_point,
        )

        lead_pos = _calculate_throw_lead(qb_pos, receiver, throw_power=80)

        # Should throw near settle point (receiver is close to it)
        dist_to_settle = lead_pos.distance_to(settle_point)
        assert dist_to_settle < 2.0, \
            f"Post-break should throw near settle, got {dist_to_settle} yards away"

    def test_hitch_route_timing(self):
        """Hitch route (short curl) pre-break should throw on stem."""
        qb_pos = Vec2(0, 55)

        # Hitch route: quick 5-yard stem, stop
        settle_point = Vec2(15, 60)  # 5 yards from LOS
        break_point = Vec2(15, 60)   # Same as settle for hitch

        # Receiver just off LOS
        receiver = ReceiverEval(
            player_id="WR1",
            position=Vec2(15, 57),   # 2 yards into route
            velocity=Vec2(0, 6),     # Running upfield
            separation=5.0,
            status=ReceiverStatus.OPEN,
            nearest_defender_id="CB1",
            defender_closing_speed=0,
            route_phase="stem",
            is_hot=True,
            read_order=1,
            pre_break=True,
            detection_quality=1.0,
            break_point=break_point,
            route_direction="",
            route_settles=True,
            settle_point=settle_point,
        )

        lead_pos = _calculate_throw_lead(qb_pos, receiver, throw_power=75)

        # Should lead on stem toward break/settle point
        assert lead_pos.y > receiver.position.y, "Should lead upfield on stem"
        # Should not overshoot the settle point
        assert lead_pos.y <= settle_point.y + 0.5, \
            f"Should not overshoot settle, got y={lead_pos.y}, settle at y={settle_point.y}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
