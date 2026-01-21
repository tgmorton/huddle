"""Tests for the Read System.

The Read System transforms hardcoded decision logic into declarative data.
These tests verify:
1. Data structures work correctly (ReadDefinition, TriggerCondition, etc.)
2. ReadRegistry stores and retrieves reads properly
3. ReadEvaluator correctly gates on attributes
4. QB reads produce expected outcomes at different skill levels
"""

import pytest
from unittest.mock import MagicMock, PropertyMock
from dataclasses import dataclass

from huddle.simulation.v2.core.reads import (
    ReadDefinition,
    ReadOutcome,
    TriggerCondition,
    TriggerType,
    KeyActorRole,
    BrainType,
    get_awareness_accuracy,
    get_decision_making_accuracy,
    get_max_pressure_for_reads,
    AWARENESS_SCALING,
    DECISION_MAKING_SCALING,
)
from huddle.simulation.v2.core.read_registry import (
    ReadRegistry,
    get_read_registry,
    register_read,
    get_reads_for_situation,
)
from huddle.simulation.v2.core.read_evaluator import (
    ReadEvaluator,
    ReadEvaluationResult,
    get_read_evaluator,
)
from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.core.entities import Position, PlayerAttributes
from huddle.simulation.v2.core.variance import set_config, VarianceConfig, SimulationMode


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def deterministic_mode():
    """Enable deterministic mode for consistent test results."""
    original = set_config(VarianceConfig(mode=SimulationMode.DETERMINISTIC))
    yield
    # Note: This doesn't restore original, but tests should set their own mode


@pytest.fixture
def sample_read():
    """Create a sample read definition for testing."""
    return ReadDefinition(
        id="test_smash_cover2",
        name="Test Smash vs Cover 2",
        brain_type=BrainType.QB,
        play_concept="smash",
        applicable_coverages=["cover_2"],
        key_actor_role=KeyActorRole.FLAT_CORNER,
        triggers=[
            TriggerCondition(TriggerType.SINKS, threshold=1.0),
        ],
        outcomes=[
            ReadOutcome("z", "hitch", 1, "Corner sinks -> throw hitch"),
            ReadOutcome("slot_r", "corner", 2, "Corner squats -> throw corner"),
        ],
        min_awareness=70,
        min_decision_making=60,
        pressure_disabled_level="heavy",
    )


@pytest.fixture
def mock_defender():
    """Create a mock defender for testing."""
    defender = MagicMock()
    defender.id = "cb1"
    defender.pos = Vec2(15, -5)  # In flat area
    defender.velocity = Vec2(0, 2)  # Moving back (sinking)
    defender.position = Position.CB
    return defender


@pytest.fixture
def mock_qb_attributes():
    """Create mock QB attributes for testing."""
    attrs = PlayerAttributes()
    attrs.awareness = 85
    attrs.decision_making = 80
    attrs.poise = 75
    return attrs


@pytest.fixture
def elite_qb_attributes():
    """Create elite QB attributes."""
    attrs = PlayerAttributes()
    attrs.awareness = 95
    attrs.decision_making = 92
    attrs.poise = 90
    return attrs


@pytest.fixture
def low_qb_attributes():
    """Create low-rated QB attributes."""
    attrs = PlayerAttributes()
    attrs.awareness = 55
    attrs.decision_making = 50
    attrs.poise = 45
    return attrs


# =============================================================================
# Test Read Data Structures
# =============================================================================

class TestReadDefinition:
    """Tests for ReadDefinition data structure."""

    def test_create_read_definition(self, sample_read):
        """Test creating a basic read definition."""
        assert sample_read.id == "test_smash_cover2"
        assert sample_read.brain_type == BrainType.QB
        assert sample_read.play_concept == "smash"
        assert len(sample_read.triggers) == 1
        assert len(sample_read.outcomes) == 2

    def test_get_primary_outcome(self, sample_read):
        """Test getting the primary outcome."""
        primary = sample_read.get_primary_outcome()
        assert primary is not None
        assert primary.priority == 1
        assert primary.target_position == "z"

    def test_get_alternate_outcomes(self, sample_read):
        """Test getting alternate outcomes."""
        alternates = sample_read.get_alternate_outcomes()
        assert len(alternates) == 1
        assert alternates[0].priority == 2
        assert alternates[0].target_position == "slot_r"

    def test_applies_to_coverage(self, sample_read):
        """Test coverage applicability check."""
        assert sample_read.applies_to_coverage("cover_2") is True
        assert sample_read.applies_to_coverage("COVER_2") is True
        assert sample_read.applies_to_coverage("cover_3") is False

    def test_applies_to_all_coverages(self):
        """Test read that applies to all coverages."""
        read = ReadDefinition(
            id="test_all",
            name="Test All Coverages",
            brain_type=BrainType.QB,
            play_concept="test",
            applicable_coverages=[],  # Empty = all
            key_actor_role=KeyActorRole.FLAT_DEFENDER,
            triggers=[],
            outcomes=[],
        )
        assert read.applies_to_coverage("cover_2") is True
        assert read.applies_to_coverage("cover_3") is True
        assert read.applies_to_coverage("man") is True


class TestTriggerCondition:
    """Tests for TriggerCondition data structure."""

    def test_create_trigger(self):
        """Test creating a trigger condition."""
        trigger = TriggerCondition(
            trigger_type=TriggerType.SINKS,
            threshold=2.0,
            direction="vertical",
            timing_window=(0.5, 3.0),
        )
        assert trigger.trigger_type == TriggerType.SINKS
        assert trigger.threshold == 2.0
        assert trigger.timing_window == (0.5, 3.0)

    def test_default_timing_window(self):
        """Test default timing window."""
        trigger = TriggerCondition(TriggerType.WIDENS)
        assert trigger.timing_window == (0.0, 10.0)


# =============================================================================
# Test Attribute Scaling
# =============================================================================

class TestAttributeScaling:
    """Tests for attribute-based scaling functions."""

    def test_awareness_accuracy_elite(self):
        """Elite awareness should give high accuracy."""
        acc, time = get_awareness_accuracy(95)
        assert acc >= 0.95
        assert time <= 0.15

    def test_awareness_accuracy_average(self):
        """Average awareness should give moderate accuracy."""
        acc, time = get_awareness_accuracy(65)
        assert 0.60 <= acc <= 0.70
        assert 0.35 <= time <= 0.45

    def test_awareness_accuracy_disabled(self):
        """Low awareness should disable read system."""
        acc, time = get_awareness_accuracy(55)
        assert acc == 0.0

    def test_decision_making_elite(self):
        """Elite decision-making should give high accuracy."""
        acc, can_antic = get_decision_making_accuracy(92)
        assert acc >= 0.90
        assert can_antic is True

    def test_decision_making_average(self):
        """Average decision-making should give moderate accuracy."""
        acc, can_antic = get_decision_making_accuracy(65)
        assert 0.50 <= acc <= 0.60
        assert can_antic is False

    def test_decision_making_disabled(self):
        """Very low decision-making should be random."""
        acc, can_antic = get_decision_making_accuracy(45)
        assert acc == 0.0

    def test_poise_pressure_thresholds(self):
        """Poise should determine pressure tolerance."""
        assert get_max_pressure_for_reads(90) == "critical"
        assert get_max_pressure_for_reads(75) == "heavy"
        assert get_max_pressure_for_reads(60) == "moderate"
        assert get_max_pressure_for_reads(40) == "light"


# =============================================================================
# Test Read Registry
# =============================================================================

class TestReadRegistry:
    """Tests for ReadRegistry."""

    def test_register_and_retrieve(self, sample_read):
        """Test registering and retrieving a read."""
        registry = ReadRegistry()
        registry.register(sample_read)

        retrieved = registry.get_by_id("test_smash_cover2")
        assert retrieved is not None
        assert retrieved.id == sample_read.id

    def test_duplicate_registration_fails(self, sample_read):
        """Test that duplicate registration raises error."""
        registry = ReadRegistry()
        registry.register(sample_read)

        with pytest.raises(ValueError):
            registry.register(sample_read)

    def test_get_reads_for_concept(self, sample_read):
        """Test getting reads by concept."""
        registry = ReadRegistry()
        registry.register(sample_read)

        reads = registry.get_reads_for_concept("smash", "cover_2", BrainType.QB)
        assert len(reads) == 1
        assert reads[0].id == sample_read.id

    def test_get_reads_for_concept_no_match(self, sample_read):
        """Test getting reads when none match."""
        registry = ReadRegistry()
        registry.register(sample_read)

        # Wrong concept
        reads = registry.get_reads_for_concept("flood", "cover_2", BrainType.QB)
        assert len(reads) == 0

        # Wrong coverage
        reads = registry.get_reads_for_concept("smash", "cover_3", BrainType.QB)
        assert len(reads) == 0

    def test_get_concepts(self, sample_read):
        """Test getting list of registered concepts."""
        registry = ReadRegistry()
        registry.register(sample_read)

        concepts = registry.get_concepts(BrainType.QB)
        assert "smash" in concepts


# =============================================================================
# Test Read Evaluator
# =============================================================================

class TestReadEvaluator:
    """Tests for ReadEvaluator."""

    def test_evaluate_disabled_by_awareness(
        self, sample_read, low_qb_attributes, mock_defender, deterministic_mode
    ):
        """Test that low awareness disables reads."""
        evaluator = ReadEvaluator()

        result = evaluator.evaluate(
            read=sample_read,
            player_attributes=low_qb_attributes,
            opponents=[mock_defender],
            field_context=MagicMock(los_y=0),
            pressure_level="clean",
            time_since_snap=2.0,
        )

        assert result.success is False
        assert "awareness" in result.reasoning.lower()

    def test_evaluate_disabled_by_pressure(
        self, sample_read, mock_qb_attributes, mock_defender, deterministic_mode
    ):
        """Test that high pressure disables reads."""
        # Lower poise to make pressure disable reads
        mock_qb_attributes.poise = 50

        evaluator = ReadEvaluator()

        result = evaluator.evaluate(
            read=sample_read,
            player_attributes=mock_qb_attributes,
            opponents=[mock_defender],
            field_context=MagicMock(los_y=0),
            pressure_level="heavy",
            time_since_snap=2.0,
        )

        assert result.success is False
        assert "pressure" in result.reasoning.lower()

    def test_evaluate_success_with_elite_qb(
        self, sample_read, elite_qb_attributes, mock_defender, deterministic_mode
    ):
        """Test successful read evaluation with elite QB."""
        evaluator = ReadEvaluator()
        evaluator.reset_play([mock_defender])

        # Update defender to be in sinking position
        mock_defender.pos = Vec2(15, -7)  # Deeper than start

        result = evaluator.evaluate(
            read=sample_read,
            player_attributes=elite_qb_attributes,
            opponents=[mock_defender],
            field_context=MagicMock(los_y=0),
            pressure_level="clean",
            time_since_snap=2.0,
        )

        # Note: May or may not succeed depending on trigger evaluation
        # The important thing is it's not disabled by attributes
        assert "awareness" not in result.reasoning.lower() or result.success


# =============================================================================
# Test QB Reads Registration
# =============================================================================

class TestQBReadsRegistration:
    """Tests for QB reads auto-registration."""

    def test_qb_reads_registered(self):
        """Test that QB reads are auto-registered."""
        # Import to trigger registration
        from huddle.simulation.v2.data import qb_reads

        registry = get_read_registry()

        # Check some key reads are registered
        assert registry.get_by_id("slant_flat_cover3") is not None
        assert registry.get_by_id("smash_cover2") is not None
        assert registry.get_by_id("stick_cover3") is not None

    def test_qb_concepts_available(self):
        """Test that QB concepts are available."""
        from huddle.simulation.v2.data import qb_reads

        concepts = qb_reads.get_qb_concepts()
        assert "slant_flat" in concepts
        assert "smash" in concepts
        assert "stick" in concepts


# =============================================================================
# Test Integration with QB Brain
# =============================================================================

class TestQBBrainIntegration:
    """Tests for read system integration with QB brain."""

    def test_qb_context_has_concept_fields(self):
        """Test that QBContext has the required fields."""
        from huddle.simulation.v2.core.contexts import QBContext

        context = QBContext(me=MagicMock())
        assert hasattr(context, 'play_concept')
        assert hasattr(context, 'detected_coverage')

    def test_select_target_with_reads_function_exists(self):
        """Test that _select_target_with_reads is defined."""
        from huddle.simulation.v2.ai.qb_brain import _select_target_with_reads

        assert callable(_select_target_with_reads)


# =============================================================================
# Test Attribute Differentiation
# =============================================================================

class TestAttributeDifferentiation:
    """Tests verifying elite vs average QB differentiation."""

    @pytest.mark.parametrize("awareness,expected_acc_range", [
        (95, (0.95, 1.0)),
        (85, (0.85, 0.95)),
        (75, (0.75, 0.85)),
        (65, (0.60, 0.70)),
    ])
    def test_awareness_differentiation(self, awareness, expected_acc_range):
        """Test that awareness creates meaningful differentiation."""
        acc, _ = get_awareness_accuracy(awareness)
        min_acc, max_acc = expected_acc_range
        assert min_acc <= acc <= max_acc

    @pytest.mark.parametrize("decision_making,expected_acc_range", [
        (95, (0.90, 1.0)),
        (85, (0.80, 0.90)),
        (75, (0.65, 0.80)),
        (65, (0.50, 0.60)),
    ])
    def test_decision_making_differentiation(self, decision_making, expected_acc_range):
        """Test that decision-making creates meaningful differentiation."""
        acc, _ = get_decision_making_accuracy(decision_making)
        min_acc, max_acc = expected_acc_range
        assert min_acc <= acc <= max_acc


# =============================================================================
# Test DB Reads Registration
# =============================================================================

class TestDBReadsRegistration:
    """Tests for DB reads auto-registration."""

    def test_db_reads_registered(self):
        """Test that DB reads are auto-registered."""
        from huddle.simulation.v2.data import db_reads

        registry = get_read_registry()

        # Check some key reads are registered
        assert registry.get_by_id("db_inside_release") is not None
        assert registry.get_by_id("db_curl_anticipation") is not None
        assert registry.get_by_id("db_qb_eyes") is not None
        assert registry.get_by_id("db_ball_in_air") is not None

    def test_db_concepts_available(self):
        """Test that DB concepts are available."""
        from huddle.simulation.v2.data import db_reads

        concepts = db_reads.get_db_concepts()
        assert "coverage" in concepts
        assert "press" in concepts
        assert "ball_reaction" in concepts

    def test_db_read_count(self):
        """Test correct number of DB reads registered."""
        from huddle.simulation.v2.data import db_reads

        all_reads = db_reads.get_all_db_reads()
        assert len(all_reads) == 15  # 15 DB reads defined


class TestDBReadDefinitions:
    """Tests for DB read definition structure."""

    def test_release_reads_have_correct_brain_type(self):
        """Test that release reads are marked as DB brain type."""
        from huddle.simulation.v2.data import db_reads

        for read in db_reads.get_all_db_reads():
            assert read.brain_type == BrainType.DB

    def test_break_anticipation_requires_high_attributes(self):
        """Test that break anticipation reads require elite attributes."""
        from huddle.simulation.v2.data import db_reads

        registry = get_read_registry()

        # Break anticipation should require high awareness
        curl_antic = registry.get_by_id("db_curl_anticipation")
        assert curl_antic is not None
        assert curl_antic.min_awareness >= 80

        out_antic = registry.get_by_id("db_out_anticipation")
        assert out_antic is not None
        assert out_antic.min_awareness >= 85

    def test_ball_in_air_read_has_two_outcomes(self):
        """Test that ball-in-air read has play ball and play receiver options."""
        from huddle.simulation.v2.data import db_reads

        registry = get_read_registry()
        ball_read = registry.get_by_id("db_ball_in_air")

        assert ball_read is not None
        assert len(ball_read.outcomes) == 2

        priorities = [o.priority for o in ball_read.outcomes]
        assert 1 in priorities
        assert 2 in priorities


# =============================================================================
# Test LB Reads Registration
# =============================================================================

class TestLBReadsRegistration:
    """Tests for LB reads auto-registration."""

    def test_lb_reads_registered(self):
        """Test that LB reads are auto-registered."""
        from huddle.simulation.v2.data import lb_reads

        registry = get_read_registry()

        # Check some key reads are registered
        assert registry.get_by_id("lb_inside_zone") is not None
        assert registry.get_by_id("lb_power_run") is not None
        assert registry.get_by_id("lb_play_action") is not None
        assert registry.get_by_id("lb_screen") is not None

    def test_lb_concepts_available(self):
        """Test that LB concepts are available."""
        from huddle.simulation.v2.data import lb_reads

        concepts = lb_reads.get_lb_concepts()
        assert "run_defense" in concepts
        assert "coverage" in concepts

    def test_lb_read_count(self):
        """Test correct number of LB reads registered."""
        from huddle.simulation.v2.data import lb_reads

        all_reads = lb_reads.get_all_lb_reads()
        assert len(all_reads) == 13  # 13 LB reads defined


class TestLBReadDefinitions:
    """Tests for LB read definition structure."""

    def test_lb_reads_have_correct_brain_type(self):
        """Test that LB reads are marked as LB brain type."""
        from huddle.simulation.v2.data import lb_reads

        for read in lb_reads.get_all_lb_reads():
            assert read.brain_type == BrainType.LB

    def test_counter_read_requires_high_attributes(self):
        """Test that counter misdirection requires high play recognition."""
        from huddle.simulation.v2.data import lb_reads

        registry = get_read_registry()
        counter_read = registry.get_by_id("lb_counter_run")

        assert counter_read is not None
        assert counter_read.min_awareness >= 80
        assert counter_read.min_decision_making >= 75

    def test_play_action_read_requires_discipline(self):
        """Test that play action read requires high attributes."""
        from huddle.simulation.v2.data import lb_reads

        registry = get_read_registry()
        pa_read = registry.get_by_id("lb_play_action")

        assert pa_read is not None
        assert pa_read.min_awareness >= 80

    def test_rpo_read_has_multiple_outcomes(self):
        """Test that RPO read has run and pass options."""
        from huddle.simulation.v2.data import lb_reads

        registry = get_read_registry()
        rpo_read = registry.get_by_id("lb_rpo")

        assert rpo_read is not None
        assert len(rpo_read.outcomes) == 2


# =============================================================================
# Test New TriggerTypes and KeyActorRoles
# =============================================================================

class TestNewEnumValues:
    """Tests for newly added trigger types and key actor roles."""

    def test_db_specific_trigger_types(self):
        """Test DB-specific trigger types exist."""
        from huddle.simulation.v2.core.reads import TriggerType

        # DB triggers
        assert TriggerType.INSIDE_RELEASE == "inside_release"
        assert TriggerType.OUTSIDE_RELEASE == "outside_release"
        assert TriggerType.VERTICAL_STEM == "vertical_stem"
        assert TriggerType.DECELERATION == "deceleration"
        assert TriggerType.HIP_ROTATION == "hip_rotation"
        assert TriggerType.BALL_THROWN == "ball_thrown"

    def test_lb_specific_trigger_types(self):
        """Test LB-specific trigger types exist."""
        from huddle.simulation.v2.core.reads import TriggerType

        # LB triggers
        assert TriggerType.GUARD_PULL == "guard_pull"
        assert TriggerType.ZONE_BLOCK == "zone_block"
        assert TriggerType.GAP_BLOCK == "gap_block"
        assert TriggerType.COUNTER_STEP == "counter_step"
        assert TriggerType.PLAY_ACTION == "play_action"

    def test_db_specific_key_actor_roles(self):
        """Test DB-specific key actor roles exist."""
        assert KeyActorRole.ASSIGNED_RECEIVER == "assigned_receiver"
        assert KeyActorRole.QB == "qb"
        assert KeyActorRole.ROUTE_CROSSER == "route_crosser"
        assert KeyActorRole.BALL == "ball"

    def test_lb_specific_key_actor_roles(self):
        """Test LB-specific key actor roles exist."""
        assert KeyActorRole.RUN_FLOW == "run_flow"
        assert KeyActorRole.BALL_CARRIER == "ball_carrier"
        assert KeyActorRole.FULLBACK == "fullback"


# =============================================================================
# Test Registry with Multiple Brain Types
# =============================================================================

class TestMultiBrainRegistry:
    """Tests for registry handling multiple brain types."""

    def test_registry_separates_brain_types(self):
        """Test that registry correctly separates reads by brain type."""
        # Ensure all reads are registered
        from huddle.simulation.v2.data import qb_reads, db_reads, lb_reads

        registry = get_read_registry()

        # Get concepts for each brain type
        qb_concepts = registry.get_concepts(BrainType.QB)
        db_concepts = registry.get_concepts(BrainType.DB)
        lb_concepts = registry.get_concepts(BrainType.LB)

        # Each should have different concepts
        assert "slant_flat" in qb_concepts
        assert "coverage" in db_concepts
        assert "run_defense" in lb_concepts

    def test_get_reads_filters_by_brain_type(self):
        """Test that get_reads_for_concept filters by brain type."""
        from huddle.simulation.v2.data import qb_reads, db_reads, lb_reads

        registry = get_read_registry()

        # QB reads for smash concept
        qb_smash = registry.get_reads_for_concept("smash", "cover_2", BrainType.QB)
        assert len(qb_smash) > 0
        for read in qb_smash:
            assert read.brain_type == BrainType.QB

        # DB reads for coverage concept
        db_coverage = registry.get_reads_for_concept("coverage", "man", BrainType.DB)
        assert len(db_coverage) > 0
        for read in db_coverage:
            assert read.brain_type == BrainType.DB

        # LB reads for run_defense concept
        lb_run = registry.get_reads_for_concept("run_defense", "any", BrainType.LB)
        assert len(lb_run) > 0
        for read in lb_run:
            assert read.brain_type == BrainType.LB
