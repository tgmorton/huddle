"""Route running system.

Handles receiver route execution, from alignment to route completion.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

from ..core.vec2 import Vec2
from ..core.entities import Player
from ..core.clock import Clock
from ..core.events import EventBus, EventType
from ..physics.movement import MovementProfile, MovementSolver, MovementResult
from ..plays.routes import RouteDefinition, RouteWaypoint, RoutePhase


@dataclass
class RouteAssignment:
    """Receiver's route assignment.

    Combines a route definition with alignment and execution state.

    Attributes:
        player_id: Which player is running this route
        route: The route definition
        alignment: Starting position on the field
        is_left_side: Is receiver on left side of formation
        has_started: Has the route begun (post-snap)
        current_waypoint_idx: Current target waypoint
        phase: Current phase of route
    """
    player_id: str
    route: RouteDefinition
    alignment: Vec2
    is_left_side: bool = False
    read_order: int = 1  # QB read progression (1 = first read)

    # Runtime state
    has_started: bool = False
    current_waypoint_idx: int = 0
    phase: RoutePhase = RoutePhase.PRE_SNAP

    # Computed waypoints in field coordinates
    _field_waypoints: List[Vec2] = field(default_factory=list)

    def __post_init__(self):
        self._compute_field_waypoints()

    def _compute_field_waypoints(self):
        """Convert relative waypoints to field coordinates.

        Route waypoints use a convention where +X = "inside" (toward center).

        For a receiver on the RIGHT side (positive X alignment):
            - Inside = toward center = negative X direction
            - So we NEGATE route X to get field X

        For a receiver on the LEFT side (negative X alignment):
            - Inside = toward center = positive X direction
            - So route X stays as-is
        """
        self._field_waypoints = []

        for wp in self.route.waypoints:
            x_offset = wp.offset.x

            # Right side receivers: negate X (inside = toward 0 = negative direction)
            # Left side receivers: keep X as-is (inside = toward 0 = positive direction)
            if not self.is_left_side:
                x_offset = -x_offset

            field_pos = Vec2(
                self.alignment.x + x_offset,
                self.alignment.y + wp.offset.y,
            )
            self._field_waypoints.append(field_pos)

    @property
    def current_target(self) -> Optional[Vec2]:
        """Current waypoint target in field coordinates."""
        if self.current_waypoint_idx >= len(self._field_waypoints):
            return None
        return self._field_waypoints[self.current_waypoint_idx]

    @property
    def current_waypoint(self) -> Optional[RouteWaypoint]:
        """Current waypoint definition."""
        if self.current_waypoint_idx >= len(self.route.waypoints):
            return None
        return self.route.waypoints[self.current_waypoint_idx]

    @property
    def is_complete(self) -> bool:
        """Has receiver completed the route?"""
        return self.current_waypoint_idx >= len(self._field_waypoints)

    @property
    def is_at_break(self) -> bool:
        """Is receiver at the break point?"""
        wp = self.current_waypoint
        return wp is not None and wp.is_break

    @property
    def has_passed_break(self) -> bool:
        """Has receiver already passed the break point?

        Returns True if receiver's current waypoint index is beyond the break waypoint.
        """
        # Find the break waypoint index
        break_idx = None
        for i, wp in enumerate(self.route.waypoints):
            if wp.is_break:
                break_idx = i
                break

        if break_idx is None:
            # No break defined - always "pre-break" (use velocity for leading)
            return False

        # Receiver has passed break if current_waypoint_idx > break_idx
        return self.current_waypoint_idx > break_idx

    def advance_waypoint(self) -> bool:
        """Advance to next waypoint.

        Returns True if there was a waypoint to advance to.
        """
        if self.current_waypoint_idx < len(self.route.waypoints):
            # Update phase based on next waypoint
            next_idx = self.current_waypoint_idx + 1
            if next_idx < len(self.route.waypoints):
                self.phase = self.route.waypoints[next_idx].phase

            self.current_waypoint_idx += 1
            return True
        return False

    def get_break_point(self) -> Optional[Vec2]:
        """Get the break point position for this route.

        The break point is where the receiver makes their primary cut.
        For settling routes (curl, hitch), this is where they'll stop.

        Returns:
            Field position of break point, or None if no break defined.
        """
        for i, wp in enumerate(self.route.waypoints):
            if wp.is_break and i < len(self._field_waypoints):
                return self._field_waypoints[i]
        return None

    def get_final_position(self) -> Optional[Vec2]:
        """Get the final waypoint position for this route.

        Returns:
            Field position of final waypoint, or None if no waypoints.
        """
        if self._field_waypoints:
            return self._field_waypoints[-1]
        return None

    def get_settle_point(self) -> Optional[Vec2]:
        """Get the settle position for settling routes.

        For settling routes (curl, hitch, comeback), this is where the receiver
        actually STOPS - the FINAL waypoint, NOT the break point.

        The break point is where direction changes.
        The settle point is where the receiver comes to rest.

        Example for CURL:
        - Break point: (2, 12) - where receiver curls inside
        - Settle point: (3, 10) - where receiver stops

        Returns:
            Field position of settle point, or None if no waypoints.
        """
        return self.get_final_position()

    def describe_state(self) -> str:
        """Human-readable state description."""
        if not self.has_started:
            return f"Pre-snap at {self.alignment}"

        if self.is_complete:
            return f"Route complete ({self.route.name})"

        wp = self.current_waypoint
        target = self.current_target
        wp_num = self.current_waypoint_idx + 1
        total_wp = len(self.route.waypoints)

        parts = [
            f"Running {self.route.name} route",
            f"Phase: {self.phase.value}",
            f"Waypoint {wp_num}/{total_wp} → {target}",
        ]

        if wp and wp.is_break:
            parts.append("[AT BREAK POINT]")
        if wp and wp.look_for_ball:
            parts.append("[LOOKING FOR BALL]")

        return " | ".join(parts)


class RouteRunner:
    """System that executes route running for receivers.

    Handles:
    - Converting route definitions to field coordinates
    - Moving receivers along waypoints
    - Tracking route phase and progress
    - Logging receiver reasoning
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus
        self.solver = MovementSolver()
        self._assignments: dict[str, RouteAssignment] = {}
        self._profiles: dict[str, MovementProfile] = {}  # Store profiles for anticipation
        self._clock: Optional[Clock] = None  # Set during update

    def assign_route(
        self,
        player: Player,
        route: RouteDefinition,
        alignment: Vec2,
        is_left_side: bool = False,
    ) -> RouteAssignment:
        """Assign a route to a player.

        Args:
            player: The receiver
            route: Route definition to run
            alignment: Starting position
            is_left_side: Is receiver on left side of formation

        Returns:
            RouteAssignment tracking this route
        """
        assignment = RouteAssignment(
            player_id=player.id,
            route=route,
            alignment=alignment,
            is_left_side=is_left_side,
            read_order=player.read_order,  # From player's play call assignment
        )

        self._assignments[player.id] = assignment

        self._log(
            f"Route assigned to {player.name}: {route.name} from {alignment}",
            player,
        )

        return assignment

    def change_route(self, player_id: str, new_route_type: "RouteType") -> bool:
        """Change a player's route (hot route).

        Must be called before routes start (pre-snap).

        Args:
            player_id: The receiver's ID
            new_route_type: The new route to run

        Returns:
            True if route was changed, False if player not found or already started
        """
        from huddle.simulation.v2.plays.routes import get_route

        assignment = self._assignments.get(player_id)
        if not assignment:
            return False

        # Can't hot route after snap
        if assignment.has_started:
            return False

        # Get new route definition
        new_route = get_route(new_route_type)

        # Update assignment with new route
        old_route_name = assignment.route.name
        assignment.route = new_route
        assignment.waypoint_index = 0
        assignment.phase = RoutePhase.RELEASE

        # Log the change (no player object available here, just print)
        # Could emit an event instead for proper tracking

        return True

    def start_route(self, player_id: str, clock: Optional[Clock] = None) -> None:
        """Start route execution (on snap)."""
        if clock:
            self._clock = clock
        assignment = self._assignments.get(player_id)
        if assignment:
            assignment.has_started = True
            assignment.phase = RoutePhase.RELEASE
            self._emit_event(
                EventType.SNAP,
                player_id,
                description=f"Route started: {assignment.route.name}",
                phase="release",
            )

    def start_all_routes(self, clock: Optional[Clock] = None) -> None:
        """Start all assigned routes (on snap)."""
        for player_id in self._assignments:
            self.start_route(player_id, clock)

    def update(
        self,
        player: Player,
        profile: MovementProfile,
        dt: float,
        clock: Clock,
    ) -> tuple[MovementResult, str]:
        """Update receiver movement for one tick.

        Args:
            player: The receiver player
            profile: Player's movement profile
            dt: Time step
            clock: Simulation clock

        Returns:
            (MovementResult, reasoning_string)
        """
        self._clock = clock  # Store for event emission
        self._profiles[player.id] = profile  # Store for throw anticipation
        assignment = self._assignments.get(player.id)

        if assignment is None:
            # No route assigned, stand still
            return MovementResult(
                new_pos=player.pos,
                new_vel=Vec2.zero(),
            ), "No route assigned"

        if not assignment.has_started:
            # Pre-snap, stay at alignment
            return MovementResult(
                new_pos=player.pos,
                new_vel=Vec2.zero(),
            ), "Pre-snap, awaiting snap"

        if assignment.is_complete:
            # Route complete - behavior depends on route type
            if assignment.route.settles:
                # Settling routes (curl, hitch, comeback): stop at the spot
                if player.velocity.length() > 0.5:
                    # Gradually slow down
                    new_vel = player.velocity * 0.90
                    new_pos = player.pos + new_vel * dt
                    return MovementResult(
                        new_pos=new_pos,
                        new_vel=new_vel,
                        speed_after=new_vel.length(),
                    ), "Route complete, settling in place"
                else:
                    return MovementResult(
                        new_pos=player.pos,
                        new_vel=Vec2.zero(),
                    ), "Route complete, settled"
            else:
                # Non-settling routes (slant, go, in, post): keep running in same direction
                if player.velocity.length() > 0.1:
                    # Maintain current direction and speed
                    direction = player.velocity.normalized()
                    new_vel = direction * profile.max_speed
                    new_pos = player.pos + new_vel * dt
                    return MovementResult(
                        new_pos=new_pos,
                        new_vel=new_vel,
                        speed_after=new_vel.length(),
                        at_max_speed=True,
                    ), "Route complete, continuing in direction"
                else:
                    # Started from stop, use last waypoint direction
                    last_wp = assignment._field_waypoints[-1] if assignment._field_waypoints else None
                    prev_wp = assignment._field_waypoints[-2] if len(assignment._field_waypoints) >= 2 else None
                    if last_wp and prev_wp:
                        direction = (last_wp - prev_wp).normalized()
                        new_vel = direction * profile.max_speed
                        new_pos = player.pos + new_vel * dt
                        return MovementResult(
                            new_pos=new_pos,
                            new_vel=new_vel,
                            speed_after=new_vel.length(),
                        ), "Route complete, starting continuation"
                    return MovementResult(
                        new_pos=player.pos,
                        new_vel=Vec2.zero(),
                    ), "Route complete, no direction"

        # Get current waypoint
        target = assignment.current_target
        waypoint = assignment.current_waypoint

        if target is None:
            return MovementResult(
                new_pos=player.pos,
                new_vel=Vec2.zero(),
            ), "No target waypoint"

        # Determine max speed based on waypoint
        max_speed = profile.max_speed * waypoint.speed_factor

        # Move toward waypoint (pass agility for cut variance)
        agility = getattr(player.attributes, 'agility', None)
        result, arrived = self.solver.solve_with_arrival(
            current_pos=player.pos,
            current_vel=player.velocity,
            target_pos=target,
            profile=profile,
            dt=dt,
            arrival_threshold=0.5,
            max_speed_override=max_speed if max_speed < profile.max_speed else None,
            agility=agility,
        )

        # Build reasoning string
        reasoning_parts = []

        # Current phase
        reasoning_parts.append(f"Phase: {assignment.phase.value}")

        # What we're doing
        wp_idx = assignment.current_waypoint_idx + 1
        total_wps = len(assignment.route.waypoints)
        distance_to_target = player.pos.distance_to(target)
        reasoning_parts.append(f"Waypoint {wp_idx}/{total_wps}, {distance_to_target:.1f}yd to target")

        # Movement info
        if result.cut_occurred:
            reasoning_parts.append(f"Cut! Lost {(1 - result.speed_after/max(0.01, result.speed_before)):.0%} speed")

        if result.at_max_speed:
            reasoning_parts.append("At max speed")

        # Special waypoint states
        if waypoint.is_break:
            reasoning_parts.append("[BREAK POINT]")

        if waypoint.look_for_ball:
            reasoning_parts.append("[LOOKING FOR BALL]")

        reasoning = " | ".join(reasoning_parts)

        # Check if we arrived at waypoint
        if arrived:
            old_phase = assignment.phase

            # Emit break event if this was a break
            if waypoint.is_break:
                self._emit_event(
                    EventType.ROUTE_BREAK,
                    player.id,
                    description=f"Break at {target}",
                    depth=target.y,
                    route_name=assignment.route.name,
                )

            # Advance to next waypoint
            if assignment.advance_waypoint():
                self._log(
                    f"{player.name} reached waypoint {wp_idx}, advancing to {assignment.current_waypoint_idx + 1}",
                    player,
                )
                reasoning += f" → Advanced to waypoint {assignment.current_waypoint_idx + 1}"
            else:
                # Route complete
                assignment.phase = RoutePhase.COMPLETE
                self._emit_event(
                    EventType.ROUTE_COMPLETE,
                    player.id,
                    description=f"Completed {assignment.route.name} route",
                    route_name=assignment.route.name,
                )
                reasoning += " → Route COMPLETE"

        return result, reasoning

    def get_assignment(self, player_id: str) -> Optional[RouteAssignment]:
        """Get route assignment for a player."""
        return self._assignments.get(player_id)

    def check_waypoint_arrival(self, player: Player, arrival_threshold: float = 0.5) -> bool:
        """Check if player arrived at current waypoint and advance if so.

        This is used when a brain is controlling movement but we still need
        the route system to track progress through waypoints.

        Args:
            player: The receiver player
            arrival_threshold: Distance to consider "arrived" (yards)

        Returns:
            True if waypoint was advanced, False otherwise
        """
        assignment = self._assignments.get(player.id)
        if assignment is None or not assignment.has_started or assignment.is_complete:
            return False

        target = assignment.current_target
        if target is None:
            return False

        distance = player.pos.distance_to(target)

        if distance <= arrival_threshold:
            waypoint = assignment.current_waypoint

            # Emit break event if this was a break point
            if waypoint and waypoint.is_break:
                self._emit_event(
                    EventType.ROUTE_BREAK,
                    player.id,
                    description=f"Break at {target}",
                    depth=target.y,
                    route_name=assignment.route.name,
                )

            # Advance to next waypoint
            if assignment.advance_waypoint():
                self._log(
                    f"{player.name} reached waypoint, advancing to {assignment.current_waypoint_idx + 1}",
                    player,
                )
                return True
            else:
                # Route complete
                assignment.phase = RoutePhase.COMPLETE
                self._emit_event(
                    EventType.ROUTE_COMPLETE,
                    player.id,
                    description=f"Completed {assignment.route.name} route",
                    route_name=assignment.route.name,
                )
                return True

        return False

    def clear_assignments(self) -> None:
        """Clear all route assignments."""
        self._assignments.clear()

    def format_all_assignments(self) -> str:
        """Format all route assignments for logging."""
        if not self._assignments:
            return "No routes assigned"

        lines = ["Route Assignments:"]
        for player_id, assignment in self._assignments.items():
            lines.append(f"  {player_id}: {assignment.describe_state()}")
        return "\n".join(lines)

    def get_expected_velocity(self, player: Player, max_speed: float) -> Vec2:
        """Get expected velocity for a receiver based on their route.

        This is used for throw leading - if a receiver's route has completed
        but they should continue running, this returns their expected velocity
        (direction and speed) rather than their instantaneous velocity which
        might be temporarily low.

        Args:
            player: The receiver
            max_speed: Player's max speed

        Returns:
            Expected velocity vector
        """
        assignment = self._assignments.get(player.id)
        if assignment is None:
            return player.velocity

        # If route not complete or it's a settling route, use actual velocity
        if not assignment.is_complete or assignment.route.settles:
            return player.velocity

        # For non-settling routes that are complete, use direction of last segment at max speed
        if len(assignment._field_waypoints) >= 2:
            last_wp = assignment._field_waypoints[-1]
            prev_wp = assignment._field_waypoints[-2]
            direction = (last_wp - prev_wp).normalized()
            return direction * max_speed

        # Fallback to actual velocity
        return player.velocity

    def _estimate_decel_arrival_time(
        self,
        distance: float,
        initial_speed: float,
        deceleration: float,
    ) -> float:
        """Estimate time to travel distance while decelerating to stop.

        Uses kinematic equations:
        - Stopping distance: d_stop = v^2 / (2a)
        - If distance > d_stop: cruise at speed, then decelerate
        - If distance <= d_stop: decelerate immediately

        Args:
            distance: Distance to travel (yards)
            initial_speed: Current speed (yards/sec)
            deceleration: Deceleration rate (yards/sec^2)

        Returns:
            Time to reach destination and stop (seconds)
        """
        if initial_speed < 0.1 or distance < 0.1:
            return 0.0 if distance < 0.1 else float('inf')

        stopping_distance = (initial_speed ** 2) / (2 * deceleration)

        if distance <= stopping_distance:
            # Need to decelerate immediately to stop at target
            # Using: d = v*t - 0.5*a*t^2, solve for t
            # Quadratic: 0.5*a*t^2 - v*t + d = 0
            a = 0.5 * deceleration
            b = -initial_speed
            c = distance
            discriminant = b * b - 4 * a * c
            if discriminant < 0:
                return distance / initial_speed  # Fallback
            return (-b - math.sqrt(discriminant)) / (2 * a)
        else:
            # Cruise then decelerate
            cruise_dist = distance - stopping_distance
            cruise_time = cruise_dist / initial_speed
            decel_time = initial_speed / deceleration
            return cruise_time + decel_time

    def get_anticipated_throw_target(
        self,
        player: Player,
        thrower_pos: Vec2,
        ball_speed: float,
    ) -> tuple[Vec2, Vec2]:
        """Get anticipated target position and velocity for a throw.

        This is route-aware anticipation that models receiver deceleration:

        For SETTLING routes (curl, hitch, comeback):
        - Target is the SETTLE POINT (final waypoint), not the break point
        - If ball arrives AFTER receiver settles -> throw to settle point
        - If ball arrives BEFORE receiver settles -> return current pos/vel
          to let intercept calculation handle leading

        For CONTINUING routes (slant, go, post):
        - Return current position and velocity for intercept calculation
        - If route is complete, return route direction velocity

        Args:
            player: The receiver
            thrower_pos: QB position
            ball_speed: Ball velocity in yards/second

        Returns:
            Tuple of (target_position, expected_velocity_at_catch)
        """
        assignment = self._assignments.get(player.id)
        if assignment is None:
            # No route info - use current position and velocity
            return player.pos, player.velocity

        # For settling routes, anticipate the settle point
        if assignment.route.settles:
            # Get the SETTLE point (final waypoint), NOT the break point
            settle_point = assignment.get_settle_point()
            if settle_point is None:
                return player.pos, player.velocity

            dist_to_settle = player.pos.distance_to(settle_point)

            # Already at settle point - throw directly to current pos
            if dist_to_settle < 0.5:
                return player.pos, Vec2.zero()

            # Get movement profile for deceleration calculation
            profile = self._profiles.get(player.id)
            deceleration = profile.deceleration if profile else 15.0

            receiver_speed = player.velocity.length()
            if receiver_speed < 0.5:
                # Receiver barely moving - throw to current position
                return player.pos, Vec2.zero()

            # Estimate when receiver will reach settle point (with deceleration)
            time_to_settle = self._estimate_decel_arrival_time(
                dist_to_settle, receiver_speed, deceleration
            )

            # Ball flight time to settle point
            ball_flight_time = thrower_pos.distance_to(settle_point) / ball_speed

            if ball_flight_time >= time_to_settle:
                # Ball arrives AFTER receiver settles
                # Throw to settle point - receiver will be stationary there
                return settle_point, Vec2.zero()
            else:
                # Ball arrives BEFORE receiver settles
                # Return current pos/vel - let throw_ball's intercept calc handle it
                # This will lead the receiver to where they'll be when ball arrives
                return player.pos, player.velocity

        # For non-settling routes, anticipate based on route direction
        if assignment.is_complete:
            # Route complete but continues - get direction from last segment
            if len(assignment._field_waypoints) >= 2:
                last_wp = assignment._field_waypoints[-1]
                prev_wp = assignment._field_waypoints[-2]
                direction = (last_wp - prev_wp).normalized()
                # Player should continue at good speed
                profile = self._profiles.get(player.id)
                speed = profile.max_speed if profile else 6.5
                expected_vel = direction * speed
                return player.pos, expected_vel

        # Route in progress - use their current velocity for leading
        return player.pos, player.velocity

    # =========================================================================
    # Internal helpers
    # =========================================================================

    def _log(self, message: str, player: Optional[Player] = None) -> None:
        """Log a message (for now just print, can be enhanced)."""
        if player:
            player.set_decision("route_running", message)

    def _emit_event(
        self,
        event_type: EventType,
        player_id: str,
        description: str = "",
        **data,
    ) -> None:
        """Emit an event if event bus is available."""
        if self.event_bus:
            from ..core.events import Event
            tick = self._clock.tick_count if self._clock else 0
            time = self._clock.current_time if self._clock else 0.0
            event = Event(
                type=event_type,
                tick=tick,
                time=time,
                player_id=player_id,
                description=description,
                data=data,
            )
            self.event_bus.emit(event)
