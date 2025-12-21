"""Test suite for blocking behavior verification.

Tests are organized in tiers:
- Tier 1: Atomic behaviors (1v1 isolated)
- Tier 2: Assignment behaviors (1v1 with blocking assignments)
- Tier 3: Multi-player interactions (2-3 players)
- Tier 4: Full line play (5v4)

Each test verifies specific blocking mechanics work correctly.
Run with: pytest tests/test_blocking_behaviors.py -v
"""

import pytest
from typing import List, Optional

from huddle.simulation.v2.orchestrator import Orchestrator, PlayConfig, DropbackType
from huddle.simulation.v2.core.entities import Player, Team, Position, PlayerAttributes
from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.ai.qb_brain import qb_brain
from huddle.simulation.v2.ai.ol_brain import ol_brain
from huddle.simulation.v2.ai.dl_brain import dl_brain
from huddle.simulation.v2.ai.ballcarrier_brain import ballcarrier_brain
from huddle.simulation.v2.plays.run_concepts import get_run_concept


# =============================================================================
# Fixtures
# =============================================================================

def make_player(name: str, pos: Position, team: Team, x: float, y: float, **attrs) -> Player:
    """Create a player with specified attributes."""
    default_attrs = {
        'speed': 75, 'acceleration': 75, 'strength': 75, 'awareness': 75,
        'block_power': 75, 'block_finesse': 75, 'pass_rush': 75, 'agility': 75,
        'tackling': 75,
    }
    default_attrs.update(attrs)
    return Player(
        id=name.lower(), name=name, team=team, position=pos, pos=Vec2(x, y),
        attributes=PlayerAttributes(**default_attrs)
    )


def setup_orchestrator(
    offense: List[Player],
    defense: List[Player],
    run_concept: Optional[str] = None,
    is_run_play: bool = True,
    duration: float = 3.0,
) -> Orchestrator:
    """Set up an orchestrator for testing."""
    orch = Orchestrator()

    # Register brains
    for p in offense:
        if p.position == Position.QB:
            orch.register_brain(p.id, qb_brain)
        elif p.position in (Position.LT, Position.LG, Position.C, Position.RG, Position.RT):
            orch.register_brain(p.id, ol_brain)
        elif p.position == Position.RB:
            orch.register_brain(p.id, ballcarrier_brain)

    for p in defense:
        if p.position in (Position.DE, Position.DT, Position.NT):
            orch.register_brain(p.id, dl_brain)

    orch.register_brain('ballcarrier', ballcarrier_brain)

    # Get run concept
    concept = None
    if run_concept:
        concept = get_run_concept(run_concept)
    if not concept and is_run_play:
        concept = get_run_concept('inside_zone_right')

    # Build config
    config = PlayConfig(
        routes={},
        man_assignments={},
        zone_assignments={},
        max_duration=duration + 1.0,
        dropback_type=DropbackType.SHOTGUN,
        is_run_play=is_run_play,
        run_concept=concept.name.lower().replace(' ', '_') if concept else None,
        handoff_timing=concept.handoff_timing if concept else 0.3,
        ball_carrier_id='rb',
    )

    orch.setup_play(offense, defense, config)
    orch._do_pre_snap_reads()
    orch._do_snap()

    return orch


def run_ticks(orch: Orchestrator, num_ticks: int = 20) -> float:
    """Run simulation for specified number of ticks. Returns elapsed time."""
    for _ in range(num_ticks):
        dt = orch.clock.tick()
        orch._update_tick(dt)
    return orch.clock.current_time


# =============================================================================
# TIER 1: Atomic Behaviors (1v1)
# =============================================================================

class TestTier1AtomicBehaviors:
    """Tier 1: Basic 1v1 behaviors."""

    def test_1_1_ol_fires_off_at_snap(self):
        """Test 1.1: OL fires off at snap (no DL).

        Single OL should step from y=-0.5 toward y=0 in the first 0.2s.
        """
        offense = [make_player('LG', Position.LG, Team.OFFENSE, -1.5, -0.5)]
        defense = []

        orch = setup_orchestrator(offense, defense)
        lg = offense[0]

        initial_y = lg.pos.y
        assert initial_y == pytest.approx(-0.5, abs=0.1), "LG should start at y=-0.5"

        # Run 4 ticks (0.2s)
        run_ticks(orch, 4)

        # OL should have moved toward LOS
        assert lg.pos.y > initial_y, "LG should have moved forward"
        assert lg.pos.y >= -0.25, f"LG should be near LOS, got y={lg.pos.y}"

        # X position should stay in gap
        assert -2.5 < lg.pos.x < -0.5, f"LG should stay in gap, got x={lg.pos.x}"

    def test_1_2_dl_holds_gap_on_run(self):
        """Test 1.2: DL holds gap position on run play.

        Single DL should hold their x-position and move toward LOS.
        """
        offense = [make_player('RB', Position.RB, Team.OFFENSE, 0, -4)]
        defense = [make_player('DT', Position.DT, Team.DEFENSE, 1.5, 0.5)]

        orch = setup_orchestrator(offense, defense)
        dt = defense[0]

        initial_x = dt.pos.x
        initial_y = dt.pos.y

        # Run 10 ticks (0.5s)
        run_ticks(orch, 10)

        # DL should hold x-position (not run to preset gap)
        assert dt.pos.x == pytest.approx(initial_x, abs=0.5), \
            f"DT should hold x={initial_x}, got x={dt.pos.x}"

        # DL should move toward LOS (y toward 0.5)
        assert dt.pos.y <= initial_y + 0.5, \
            f"DT should stay near LOS, got y={dt.pos.y}"

    def test_1_3_basic_engagement(self):
        """Test 1.3: Basic 1v1 engagement.

        1 OL head-up on 1 DL - they should meet at LOS with minimal movement.
        """
        offense = [make_player('LG', Position.LG, Team.OFFENSE, -1.5, -0.5)]
        defense = [make_player('DT', Position.DT, Team.DEFENSE, -1.5, 0.5)]

        orch = setup_orchestrator(offense, defense)
        lg = offense[0]
        dt = defense[0]

        # Run 20 ticks (1.0s)
        run_ticks(orch, 20)

        # Both should be near LOS (y ~ 0)
        assert -0.5 < lg.pos.y < 1.0, f"LG should be near LOS, got y={lg.pos.y}"
        assert -0.5 < dt.pos.y < 1.5, f"DT should be near LOS, got y={dt.pos.y}"

        # They should be close together (engaged)
        dist = lg.pos.distance_to(dt.pos)
        assert dist < 2.0, f"Players should be engaged, dist={dist}"

        # Check engagement exists in resolver
        if hasattr(orch, 'block_resolver') and orch.block_resolver:
            engagement = orch.block_resolver.get_engagement_for_player('lg')
            assert engagement is not None, "Engagement should exist"

    def test_1_4_ol_wins_engagement(self):
        """Test 1.4: OL wins engagement (high block_power).

        Strong OL vs weak DL - OL should gain positive leverage.
        """
        offense = [make_player('LG', Position.LG, Team.OFFENSE, -1.5, -0.5,
                               block_power=90, strength=90)]
        defense = [make_player('DT', Position.DT, Team.DEFENSE, -1.5, 0.5,
                               strength=60, pass_rush=60)]

        orch = setup_orchestrator(offense, defense)
        lg = offense[0]
        dt = defense[0]

        # Run 30 ticks (1.5s)
        run_ticks(orch, 30)

        # Both should be near LOS (engaged)
        assert lg.pos.distance_to(dt.pos) < 2.0, "LG and DT should be engaged"

        # Check leverage is positive or neutral (OL at least holding)
        if hasattr(orch, 'block_resolver') and orch.block_resolver:
            engagement = orch.block_resolver.get_engagement_for_player('lg')
            if engagement:
                # OL with 90 block vs DL with 60 should be winning
                assert engagement.leverage >= -0.3, \
                    f"OL should be winning or neutral, leverage={engagement.leverage}"
                # Shed progress should be low (OL is sustaining block)
                assert engagement.shed_progress < 0.5, \
                    f"DL shouldn't be close to shedding, shed={engagement.shed_progress}"

    def test_1_5_dl_wins_engagement(self):
        """Test 1.5: DL wins engagement.

        Strong DL vs weak OL - DL should gain negative leverage and shed progress.
        """
        offense = [make_player('LG', Position.LG, Team.OFFENSE, -1.5, -0.5,
                               block_power=60, strength=60)]
        defense = [make_player('DT', Position.DT, Team.DEFENSE, -1.5, 0.5,
                               strength=90, pass_rush=90)]

        orch = setup_orchestrator(offense, defense)
        lg = offense[0]
        dt = defense[0]

        initial_lg_y = lg.pos.y

        # Run 30 ticks (1.5s)
        run_ticks(orch, 30)

        # Check that DL is making progress
        if hasattr(orch, 'block_resolver') and orch.block_resolver:
            engagement = orch.block_resolver.get_engagement_for_player('lg')
            if engagement:
                # DL should have negative leverage or high shed progress
                assert engagement.leverage <= 0.2 or engagement.shed_progress > 0.1, \
                    f"DL should be winning, leverage={engagement.leverage}, shed={engagement.shed_progress}"

    def test_1_6_dl_sheds_block(self):
        """Test 1.6: DL sheds block (dominant DL over time).

        Very strong DL should eventually gain leverage and make shed progress.
        """
        offense = [
            make_player('LG', Position.LG, Team.OFFENSE, -1.5, -0.5,
                        block_power=50, strength=50),
            make_player('RB', Position.RB, Team.OFFENSE, 0, -4.0),  # Need RB for run play
        ]
        defense = [make_player('DT', Position.DT, Team.DEFENSE, -1.5, 0.5,
                               strength=99, pass_rush=99)]

        orch = setup_orchestrator(offense, defense, duration=3.0)

        # Run 40 ticks (2.0s)
        run_ticks(orch, 40)

        # Check that engagement exists and DL has some advantage
        if hasattr(orch, 'block_resolver') and orch.block_resolver:
            engagement = orch.block_resolver.get_engagement_for_player('lg')
            if engagement:
                # With 99 vs 50 attributes, DL should have negative leverage
                # or some shed progress
                assert engagement.leverage <= 0.2 or engagement.shed_progress > 0.1, \
                    f"DL should have advantage: leverage={engagement.leverage}, shed={engagement.shed_progress}"


# =============================================================================
# TIER 2: Assignment Behaviors
# =============================================================================

class TestTier2AssignmentBehaviors:
    """Tier 2: Blocking assignment behaviors."""

    def test_2_1_zone_step(self):
        """Test 2.1: Zone step assignment.

        OL with zone_step should engage DL in their gap.
        """
        offense = [
            make_player('LG', Position.LG, Team.OFFENSE, -1.5, -0.5),
            make_player('C', Position.C, Team.OFFENSE, 0, -0.5),
            make_player('RG', Position.RG, Team.OFFENSE, 1.5, -0.5),
        ]
        defense = [
            make_player('DT', Position.DT, Team.DEFENSE, -1.0, 0.5),
        ]

        orch = setup_orchestrator(offense, defense, run_concept='inside_zone_right')
        lg = offense[0]
        dt = defense[0]

        # Run 20 ticks (1.0s)
        run_ticks(orch, 20)

        # LG should have engaged DT (DT is in LG's gap: -2.25 to -0.75)
        dist = lg.pos.distance_to(dt.pos)
        assert dist < 2.5, f"LG should be near DT, dist={dist}"

        # LG should not have run far from starting position
        assert -3.0 < lg.pos.x < 0.5, f"LG should stay near gap, x={lg.pos.x}"

    def test_2_2_cutoff(self):
        """Test 2.2: Cutoff assignment.

        Backside OL should seal DL to prevent pursuit.
        """
        offense = [
            make_player('LT', Position.LT, Team.OFFENSE, -3.0, -0.5),
            make_player('LG', Position.LG, Team.OFFENSE, -1.5, -0.5),
        ]
        defense = [
            make_player('DE', Position.DE, Team.DEFENSE, -3.0, 0.5),
        ]

        orch = setup_orchestrator(offense, defense, run_concept='inside_zone_right')
        lt = offense[0]
        de = defense[0]

        # LT should get cutoff assignment (backside)
        # Run 20 ticks (1.0s)
        run_ticks(orch, 20)

        # LT should be blocking DE
        dist = lt.pos.distance_to(de.pos)
        assert dist < 2.5, f"LT should be blocking DE, dist={dist}"

        # LT should stay in gap area
        assert lt.pos.x < -1.5, f"LT should stay on left side, x={lt.pos.x}"

    def test_2_4_base_block(self):
        """Test 2.4: Base block assignment.

        OL should engage and sustain 1-on-1 block.
        """
        offense = [
            make_player('RG', Position.RG, Team.OFFENSE, 1.5, -0.5),
        ]
        defense = [
            make_player('DT', Position.DT, Team.DEFENSE, 1.5, 0.5),
        ]

        orch = setup_orchestrator(offense, defense)
        rg = offense[0]
        dt = defense[0]

        # Run 30 ticks (1.5s)
        run_ticks(orch, 30)

        # RG should be engaged with DT
        dist = rg.pos.distance_to(dt.pos)
        assert dist < 2.0, f"RG should be engaged with DT, dist={dist}"

        # Both should be near LOS
        assert rg.pos.y > -1.0, f"RG should be near LOS, y={rg.pos.y}"
        assert dt.pos.y < 2.0, f"DT should be near LOS, y={dt.pos.y}"


# =============================================================================
# TIER 3: Multi-Player Interactions
# =============================================================================

class TestTier3MultiPlayer:
    """Tier 3: Multi-player blocking interactions."""

    def test_3_1_combo_block(self):
        """Test 3.1: Combo block.

        LG + C should combo on DT, potentially with one climbing to LB.
        """
        offense = [
            make_player('LG', Position.LG, Team.OFFENSE, -1.5, -0.5),
            make_player('C', Position.C, Team.OFFENSE, 0, -0.5),
        ]
        defense = [
            make_player('DT', Position.DT, Team.DEFENSE, -0.75, 0.5),
            make_player('MLB', Position.MLB, Team.DEFENSE, 0, 4.0),
        ]

        orch = setup_orchestrator(offense, defense, run_concept='inside_zone_right')
        lg = offense[0]
        c = offense[1]
        dt = defense[0]

        # Run 20 ticks (1.0s)
        run_ticks(orch, 20)

        # At least one OL should be near DT
        lg_dist = lg.pos.distance_to(dt.pos)
        c_dist = c.pos.distance_to(dt.pos)
        min_dist = min(lg_dist, c_dist)

        assert min_dist < 2.5, f"At least one OL should be blocking DT, min_dist={min_dist}"

    def test_3_3_gap_integrity(self):
        """Test 3.3: Gap integrity.

        2 OL vs 2 DL head-up - each should block their man, gaps maintained.
        """
        offense = [
            make_player('LG', Position.LG, Team.OFFENSE, -1.5, -0.5),
            make_player('RG', Position.RG, Team.OFFENSE, 1.5, -0.5),
        ]
        defense = [
            make_player('LDT', Position.DT, Team.DEFENSE, -1.5, 0.5),
            make_player('RDT', Position.DT, Team.DEFENSE, 1.5, 0.5),
        ]

        orch = setup_orchestrator(offense, defense)
        lg = offense[0]
        rg = offense[1]
        ldt = defense[0]
        rdt = defense[1]

        # Run 20 ticks (1.0s)
        run_ticks(orch, 20)

        # LG should be blocking LDT (not RDT)
        lg_to_ldt = lg.pos.distance_to(ldt.pos)
        lg_to_rdt = lg.pos.distance_to(rdt.pos)
        assert lg_to_ldt < lg_to_rdt, \
            f"LG should be blocking LDT, not RDT (lg_to_ldt={lg_to_ldt}, lg_to_rdt={lg_to_rdt})"

        # RG should be blocking RDT (not LDT)
        rg_to_rdt = rg.pos.distance_to(rdt.pos)
        rg_to_ldt = rg.pos.distance_to(ldt.pos)
        assert rg_to_rdt < rg_to_ldt, \
            f"RG should be blocking RDT, not LDT (rg_to_rdt={rg_to_rdt}, rg_to_ldt={rg_to_ldt})"

    def test_3_4_uncovered_ol(self):
        """Test 3.4: Uncovered OL behavior.

        3 OL, 1 DL (center) - uncovered OL should hold position or climb.
        """
        offense = [
            make_player('LG', Position.LG, Team.OFFENSE, -1.5, -0.5),
            make_player('C', Position.C, Team.OFFENSE, 0, -0.5),
            make_player('RG', Position.RG, Team.OFFENSE, 1.5, -0.5),
        ]
        defense = [
            make_player('NT', Position.NT, Team.DEFENSE, 0, 0.5),  # Only center covered
        ]

        orch = setup_orchestrator(offense, defense)
        lg = offense[0]
        c = offense[1]
        rg = offense[2]

        initial_lg_x = lg.pos.x
        initial_rg_x = rg.pos.x

        # Run 20 ticks (1.0s)
        run_ticks(orch, 20)

        # Uncovered OL (LG, RG) should hold their gaps, not chase NT
        assert -3.0 < lg.pos.x < 0, f"LG should stay in gap, x={lg.pos.x}"
        assert 0 < rg.pos.x < 3.0, f"RG should stay in gap, x={rg.pos.x}"

        # LG and RG should NOT both run to center to block NT
        lg_to_nt = lg.pos.distance_to(defense[0].pos)
        rg_to_nt = rg.pos.distance_to(defense[0].pos)
        # At most one should be very close
        both_close = lg_to_nt < 1.5 and rg_to_nt < 1.5
        assert not both_close, "Both LG and RG should not be blocking NT - one should hold gap"


# =============================================================================
# TIER 4: Full Line Play
# =============================================================================

class TestTier4FullLine:
    """Tier 4: Full 5v4 line play."""

    def test_4_1_head_up_defense(self):
        """Test 4.1: 4 DL head-up on OL.

        Should result in clean 1-on-1 matchups with gaps maintained.
        """
        offense = [
            make_player('QB', Position.QB, Team.OFFENSE, 0, -3.5),
            make_player('RB', Position.RB, Team.OFFENSE, -0.5, -4.5),
            make_player('LT', Position.LT, Team.OFFENSE, -3.0, -0.5),
            make_player('LG', Position.LG, Team.OFFENSE, -1.5, -0.5),
            make_player('C', Position.C, Team.OFFENSE, 0, -0.5),
            make_player('RG', Position.RG, Team.OFFENSE, 1.5, -0.5),
            make_player('RT', Position.RT, Team.OFFENSE, 3.0, -0.5),
        ]
        defense = [
            make_player('LDE', Position.DE, Team.DEFENSE, -3.0, 0.5),
            make_player('LDT', Position.DT, Team.DEFENSE, -1.5, 0.5),
            make_player('RDT', Position.DT, Team.DEFENSE, 1.5, 0.5),
            make_player('RDE', Position.DE, Team.DEFENSE, 3.0, 0.5),
        ]

        orch = setup_orchestrator(offense, defense, run_concept='inside_zone_right')

        # Get OL and DL
        lt = next(p for p in offense if p.position == Position.LT)
        lg = next(p for p in offense if p.position == Position.LG)
        c = next(p for p in offense if p.position == Position.C)
        rg = next(p for p in offense if p.position == Position.RG)
        rt = next(p for p in offense if p.position == Position.RT)

        lde = next(p for p in defense if p.name == 'LDE')
        ldt = next(p for p in defense if p.name == 'LDT')
        rdt = next(p for p in defense if p.name == 'RDT')
        rde = next(p for p in defense if p.name == 'RDE')

        # Run 30 ticks (1.5s)
        run_ticks(orch, 30)

        # Verify each OL is blocking their man (closest DL)
        # LT should block LDE
        assert lt.pos.distance_to(lde.pos) < lt.pos.distance_to(rde.pos), \
            "LT should be blocking LDE"

        # LG should block LDT
        assert lg.pos.distance_to(ldt.pos) < lg.pos.distance_to(rdt.pos), \
            "LG should be blocking LDT"

        # RG should block RDT
        assert rg.pos.distance_to(rdt.pos) < rg.pos.distance_to(ldt.pos), \
            "RG should be blocking RDT"

        # RT should block RDE
        assert rt.pos.distance_to(rde.pos) < rt.pos.distance_to(lde.pos), \
            "RT should be blocking RDE"

        # C should be uncovered (no DL in A gap)
        # C should hold position or climb, not run to block a covered DL
        assert -2.0 < c.pos.x < 2.0, f"C should stay centered, x={c.pos.x}"

    def test_4_2_gaps_maintained(self):
        """Test 4.2: Gaps are maintained during blocking.

        OL should not spread too wide - they should stay in their general area.
        Note: Combo blocks may cause adjacent OL to converge on same target.
        """
        offense = [
            make_player('QB', Position.QB, Team.OFFENSE, 0, -3.5),
            make_player('RB', Position.RB, Team.OFFENSE, -0.5, -4.5),
            make_player('LT', Position.LT, Team.OFFENSE, -3.0, -0.5),
            make_player('LG', Position.LG, Team.OFFENSE, -1.5, -0.5),
            make_player('C', Position.C, Team.OFFENSE, 0, -0.5),
            make_player('RG', Position.RG, Team.OFFENSE, 1.5, -0.5),
            make_player('RT', Position.RT, Team.OFFENSE, 3.0, -0.5),
        ]
        defense = [
            make_player('LDE', Position.DE, Team.DEFENSE, -3.0, 0.5),
            make_player('LDT', Position.DT, Team.DEFENSE, -1.5, 0.5),
            make_player('RDT', Position.DT, Team.DEFENSE, 1.5, 0.5),
            make_player('RDE', Position.DE, Team.DEFENSE, 3.0, 0.5),
        ]

        orch = setup_orchestrator(offense, defense, run_concept='inside_zone_right')

        lt = next(p for p in offense if p.position == Position.LT)
        lg = next(p for p in offense if p.position == Position.LG)
        c = next(p for p in offense if p.position == Position.C)
        rg = next(p for p in offense if p.position == Position.RG)
        rt = next(p for p in offense if p.position == Position.RT)

        # Run 20 ticks (1.0s) - shorter to stay in blocking phase
        run_ticks(orch, 20)

        # All OL should be near the LOS (moved forward from y=-0.5)
        for player, name in [(lt, 'LT'), (lg, 'LG'), (c, 'C'), (rg, 'RG'), (rt, 'RT')]:
            assert player.pos.y > -1.0, f"{name} should have moved toward LOS, y={player.pos.y}"

        # No OL should move more than 2 yards from their starting x position
        # (Allows for some convergence during combo blocks)
        assert abs(lt.pos.x - (-3.0)) < 2.0, f"LT drifted too far: x={lt.pos.x}"
        assert abs(lg.pos.x - (-1.5)) < 2.5, f"LG drifted too far: x={lg.pos.x}"
        assert abs(c.pos.x - 0.0) < 2.5, f"C drifted too far: x={c.pos.x}"
        assert abs(rg.pos.x - 1.5) < 2.0, f"RG drifted too far: x={rg.pos.x}"
        assert abs(rt.pos.x - 3.0) < 2.0, f"RT drifted too far: x={rt.pos.x}"

        # LT should stay on left side, RT on right side
        assert lt.pos.x < 0, f"LT should be on left side, x={lt.pos.x}"
        assert rt.pos.x > 0, f"RT should be on right side, x={rt.pos.x}"


# =============================================================================
# TIER 5: Block Direction & Wash
# =============================================================================

class TestTier5BlockDirection:
    """Tier 5: Block direction determines push/wash direction."""

    def test_5_1_slide_left_directions(self):
        """Test 5.1: Slide left protection sets correct block directions.

        Left side OL (LT, LG, C) should push left, right side (RG, RT) push straight.
        """
        from huddle.simulation.v2.resolution.blocking import BlockType

        offense = [
            make_player('LT', Position.LT, Team.OFFENSE, -6, -0.5),
            make_player('LG', Position.LG, Team.OFFENSE, -3, -0.5),
            make_player('C', Position.C, Team.OFFENSE, 0, -0.5),
            make_player('RG', Position.RG, Team.OFFENSE, 3, -0.5),
            make_player('RT', Position.RT, Team.OFFENSE, 6, -0.5),
        ]
        defense = []

        orch = setup_orchestrator(offense, defense, is_run_play=False)
        orch._protection_call = "slide_left"

        # Check block directions
        lt = offense[0]
        lg = offense[1]
        c = offense[2]
        rg = offense[3]
        rt = offense[4]

        assert orch._get_block_direction_for_ol(lt, BlockType.PASS_PRO) == "left"
        assert orch._get_block_direction_for_ol(lg, BlockType.PASS_PRO) == "left"
        assert orch._get_block_direction_for_ol(c, BlockType.PASS_PRO) == "left"
        assert orch._get_block_direction_for_ol(rg, BlockType.PASS_PRO) == "straight"
        assert orch._get_block_direction_for_ol(rt, BlockType.PASS_PRO) == "straight"

    def test_5_2_slide_right_directions(self):
        """Test 5.2: Slide right protection sets correct block directions.

        Right side OL (RG, RT, C) should push right, left side (LT, LG) push straight.
        """
        from huddle.simulation.v2.resolution.blocking import BlockType

        offense = [
            make_player('LT', Position.LT, Team.OFFENSE, -6, -0.5),
            make_player('LG', Position.LG, Team.OFFENSE, -3, -0.5),
            make_player('C', Position.C, Team.OFFENSE, 0, -0.5),
            make_player('RG', Position.RG, Team.OFFENSE, 3, -0.5),
            make_player('RT', Position.RT, Team.OFFENSE, 6, -0.5),
        ]
        defense = []

        orch = setup_orchestrator(offense, defense, is_run_play=False)
        orch._protection_call = "slide_right"

        lt = offense[0]
        lg = offense[1]
        c = offense[2]
        rg = offense[3]
        rt = offense[4]

        assert orch._get_block_direction_for_ol(lt, BlockType.PASS_PRO) == "straight"
        assert orch._get_block_direction_for_ol(lg, BlockType.PASS_PRO) == "straight"
        assert orch._get_block_direction_for_ol(c, BlockType.PASS_PRO) == "right"
        assert orch._get_block_direction_for_ol(rg, BlockType.PASS_PRO) == "right"
        assert orch._get_block_direction_for_ol(rt, BlockType.PASS_PRO) == "right"

    def test_5_3_zone_right_directions(self):
        """Test 5.3: Zone right run sets playside block directions.

        Zone step and combo assignments should push right (playside).
        """
        from huddle.simulation.v2.resolution.blocking import BlockType

        offense = [
            make_player('LT', Position.LT, Team.OFFENSE, -6, -0.5),
            make_player('LG', Position.LG, Team.OFFENSE, -3, -0.5),
            make_player('C', Position.C, Team.OFFENSE, 0, -0.5),
            make_player('RG', Position.RG, Team.OFFENSE, 3, -0.5),
            make_player('RT', Position.RT, Team.OFFENSE, 6, -0.5),
            make_player('RB', Position.RB, Team.OFFENSE, 0, -4),
        ]
        defense = []

        orch = setup_orchestrator(offense, defense, run_concept='inside_zone_right')

        lg = offense[1]
        c = offense[2]
        rg = offense[3]
        rt = offense[4]

        # Zone step and combo should push right
        assert orch._get_block_direction_for_ol(lg, BlockType.RUN_BLOCK) == "right"
        assert orch._get_block_direction_for_ol(c, BlockType.RUN_BLOCK) == "right"
        assert orch._get_block_direction_for_ol(rg, BlockType.RUN_BLOCK) == "right"
        assert orch._get_block_direction_for_ol(rt, BlockType.RUN_BLOCK) == "right"

    def test_5_4_power_left_down_blocks(self):
        """Test 5.4: Power left down blocks push away from play.

        Down blocks should push DL to the RIGHT (away from left-side run).
        """
        from huddle.simulation.v2.resolution.blocking import BlockType

        offense = [
            make_player('LT', Position.LT, Team.OFFENSE, -6, -0.5),
            make_player('LG', Position.LG, Team.OFFENSE, -3, -0.5),
            make_player('C', Position.C, Team.OFFENSE, 0, -0.5),
            make_player('RG', Position.RG, Team.OFFENSE, 3, -0.5),
            make_player('RT', Position.RT, Team.OFFENSE, 6, -0.5),
            make_player('RB', Position.RB, Team.OFFENSE, 0, -4),
        ]
        defense = []

        orch = setup_orchestrator(offense, defense, run_concept='power_left')

        lt = offense[0]
        lg = offense[1]

        # Down blocks push RIGHT (away from left-side play)
        assert orch._get_block_direction_for_ol(lt, BlockType.RUN_BLOCK) == "right"
        assert orch._get_block_direction_for_ol(lg, BlockType.RUN_BLOCK) == "right"

    def test_5_5_wash_creates_lateral_movement(self):
        """Test 5.5: Block direction creates lateral DL movement.

        When OL is winning, DL should be pushed in the block direction.
        """
        from huddle.simulation.v2.resolution.blocking import BlockResolver, BlockType

        resolver = BlockResolver()

        # Create strong OL
        ol = make_player('RG', Position.RG, Team.OFFENSE, 0, 0, block_power=85)
        ol.is_engaged = True

        # Create weaker DL
        dl = make_player('DT', Position.DT, Team.DEFENSE, 0, 0.5, pass_rush=70)
        dl.is_engaged = True

        initial_dl_x = dl.pos.x

        # Run blocking with "right" direction
        for tick in range(20):
            result = resolver.resolve(
                ol, dl, 'drive', 'attack',
                BlockType.RUN_BLOCK, 0.1,
                tick=tick, time=tick * 0.1,
                block_direction="right",
            )
            if result.dl_new_pos:
                dl.pos = result.dl_new_pos
            if result.ol_new_pos:
                ol.pos = result.ol_new_pos

        # DL should have moved right
        assert dl.pos.x > initial_dl_x + 0.3, \
            f"DL should be washed right, moved {dl.pos.x - initial_dl_x:.2f} yards"

    def test_5_6_no_wash_when_straight(self):
        """Test 5.6: No lateral wash when block direction is straight.

        DL should not move laterally when block_direction is 'straight'.
        """
        from huddle.simulation.v2.resolution.blocking import BlockResolver, BlockType

        resolver = BlockResolver()

        ol = make_player('RG', Position.RG, Team.OFFENSE, 0, 0, block_power=85)
        ol.is_engaged = True

        dl = make_player('DT', Position.DT, Team.DEFENSE, 0, 0.5, pass_rush=70)
        dl.is_engaged = True

        initial_dl_x = dl.pos.x

        # Run blocking with "straight" direction
        for tick in range(20):
            result = resolver.resolve(
                ol, dl, 'drive', 'attack',
                BlockType.RUN_BLOCK, 0.1,
                tick=tick, time=tick * 0.1,
                block_direction="straight",
            )
            if result.dl_new_pos:
                dl.pos = result.dl_new_pos
            if result.ol_new_pos:
                ol.pos = result.ol_new_pos

        # DL should NOT have moved much laterally
        assert abs(dl.pos.x - initial_dl_x) < 0.3, \
            f"DL should not be washed laterally, moved {abs(dl.pos.x - initial_dl_x):.2f} yards"


# =============================================================================
# TIER 6: Protection Call Integration
# =============================================================================

class TestTier6ProtectionCall:
    """Tier 6: Center makes protection call, OL coordinate."""

    def test_6_1_center_makes_call(self):
        """Test 6.1: Center identifies MIKE and makes protection call."""
        from huddle.simulation.v2.ai.ol_brain import ol_brain, _protection_call, _reset_protection_call

        _reset_protection_call()

        offense = [
            make_player('C', Position.C, Team.OFFENSE, 0, -0.5),
        ]
        defense = [
            make_player('MLB', Position.MLB, Team.DEFENSE, 0, 4),
            make_player('OLB', Position.OLB, Team.DEFENSE, -4, 2),  # Blitz threat from left
        ]

        orch = setup_orchestrator(offense, defense, is_run_play=False)

        c = offense[0]
        c_world = orch._build_world_state(c, 0.05)

        # Run center's brain - should make protection call
        decision = ol_brain(c_world)

        # Check that protection call was made
        from huddle.simulation.v2.ai.ol_brain import _get_protection_call
        call = _get_protection_call()

        assert call is not None, "Center should have made protection call"
        assert call.mike_id is not None, "MIKE should be identified"

    def test_6_2_slide_direction_passed_to_worldstate(self):
        """Test 6.2: Slide direction is available in WorldState."""
        offense = [
            make_player('LG', Position.LG, Team.OFFENSE, -3, -0.5),
        ]
        defense = []

        orch = setup_orchestrator(offense, defense, is_run_play=False)
        orch._protection_call = "slide_left"

        lg = offense[0]
        world = orch._build_world_state(lg, 0.05)

        assert world.slide_direction == "left", \
            f"WorldState should have slide_direction='left', got '{world.slide_direction}'"

    def test_6_3_no_slide_when_no_call(self):
        """Test 6.3: No slide direction when no protection call."""
        offense = [
            make_player('LG', Position.LG, Team.OFFENSE, -3, -0.5),
        ]
        defense = []

        orch = setup_orchestrator(offense, defense, is_run_play=False)
        orch._protection_call = ""  # No call

        lg = offense[0]
        world = orch._build_world_state(lg, 0.05)

        assert world.slide_direction == "", \
            f"WorldState should have empty slide_direction, got '{world.slide_direction}'"


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
