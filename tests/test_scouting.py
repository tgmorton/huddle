"""Tests for the scouting system."""

import pytest
from uuid import uuid4

from huddle.core.scouting import (
    # Stages
    ScoutingStage,
    ScoutingLevel,
    STAGE_REQUIREMENTS,
    get_attributes_for_stage,
    calculate_scouting_cost,
    get_next_stage,
    # Projections
    ScoutingAccuracy,
    ScoutedAttribute,
    PlayerProjection,
    generate_initial_projection,
    refine_projection,
    reveal_attribute,
    # Reports
    ScoutingReport,
    ScoutingGrade,
    create_scouting_report,
    grade_to_range,
    # Staff
    Scout,
    ScoutSpecialty,
    ScoutingDepartment,
    SPECIALTY_POSITIONS,
)
from huddle.core.attributes.registry import PlayerAttributes


class TestScoutingStages:
    """Test scouting stage progression."""

    def test_stage_ordering(self):
        stages = list(ScoutingStage)
        assert stages[0] == ScoutingStage.UNKNOWN
        assert stages[-1] == ScoutingStage.COMPLETE

    def test_get_attributes_for_stage_cumulative(self):
        """Each stage should include all previous stage attributes."""
        unknown_attrs = set(get_attributes_for_stage(ScoutingStage.UNKNOWN))
        basic_attrs = set(get_attributes_for_stage(ScoutingStage.BASIC))
        intermediate_attrs = set(get_attributes_for_stage(ScoutingStage.INTERMEDIATE))
        complete_attrs = set(get_attributes_for_stage(ScoutingStage.COMPLETE))

        assert len(unknown_attrs) == 0
        assert basic_attrs.issuperset(unknown_attrs)
        assert intermediate_attrs.issuperset(basic_attrs)
        assert complete_attrs.issuperset(intermediate_attrs)

    def test_basic_stage_reveals_physical(self):
        """BASIC stage should reveal physical attributes."""
        basic_attrs = get_attributes_for_stage(ScoutingStage.BASIC)
        assert "speed" in basic_attrs
        assert "acceleration" in basic_attrs
        assert "strength" in basic_attrs

    def test_complete_stage_reveals_potential(self):
        """COMPLETE stage should reveal potential."""
        complete_attrs = get_attributes_for_stage(ScoutingStage.COMPLETE)
        assert "potential" in complete_attrs

    def test_scouting_cost_calculation(self):
        """Test cost calculations between stages."""
        # Cost from UNKNOWN to COMPLETE
        total = calculate_scouting_cost(ScoutingStage.UNKNOWN, ScoutingStage.COMPLETE)
        assert total > 0

        # Cost to same stage should be 0
        same = calculate_scouting_cost(ScoutingStage.BASIC, ScoutingStage.BASIC)
        assert same == 0

        # Cost backwards should be 0
        backwards = calculate_scouting_cost(ScoutingStage.COMPLETE, ScoutingStage.BASIC)
        assert backwards == 0

    def test_get_next_stage(self):
        assert get_next_stage(ScoutingStage.UNKNOWN) == ScoutingStage.BASIC
        assert get_next_stage(ScoutingStage.BASIC) == ScoutingStage.INTERMEDIATE
        assert get_next_stage(ScoutingStage.COMPLETE) is None


class TestScoutedAttribute:
    """Test the ScoutedAttribute class."""

    def test_unrevealed_attribute(self):
        attr = ScoutedAttribute(
            name="speed",
            projected_value=85,
            accuracy=ScoutingAccuracy.MEDIUM,
            min_estimate=78,
            max_estimate=92,
        )
        assert not attr.is_revealed
        assert attr.confidence_range == 14

    def test_revealed_attribute(self):
        attr = ScoutedAttribute(
            name="speed",
            projected_value=88,
            accuracy=ScoutingAccuracy.EXACT,
            true_value=88,
            min_estimate=88,
            max_estimate=88,
        )
        assert attr.is_revealed
        assert attr.confidence_range == 0

    def test_serialization(self):
        attr = ScoutedAttribute(
            name="speed",
            projected_value=85,
            accuracy=ScoutingAccuracy.HIGH,
            min_estimate=82,
            max_estimate=88,
        )
        data = attr.to_dict()
        restored = ScoutedAttribute.from_dict(data)

        assert restored.name == attr.name
        assert restored.projected_value == attr.projected_value
        assert restored.accuracy == attr.accuracy


class TestPlayerProjection:
    """Test player projections."""

    def test_generate_initial_projection(self):
        """Initial projection should create estimates for all attributes."""
        attrs = PlayerAttributes()
        attrs.set("speed", 90)
        attrs.set("acceleration", 85)
        attrs.set("potential", 95)

        projection = generate_initial_projection(attrs, "player-123")

        assert projection.player_id == "player-123"
        assert projection.scouting_stage == ScoutingStage.UNKNOWN
        assert "speed" in projection.attributes
        assert "potential" in projection.attributes
        # Initial projection should not reveal true values
        assert not projection.is_revealed("speed")
        assert not projection.is_revealed("potential")

    def test_refine_projection(self):
        """Refining projection should improve accuracy."""
        attrs = PlayerAttributes()
        attrs.set("speed", 90)
        attrs.set("potential", 95)

        projection = generate_initial_projection(attrs, "player-123")
        initial_accuracy = projection.get_accuracy("speed")

        # Advance to BASIC
        projection = refine_projection(projection, attrs, ScoutingStage.BASIC)
        assert projection.scouting_stage == ScoutingStage.BASIC

        # Advance to COMPLETE
        projection = refine_projection(projection, attrs, ScoutingStage.COMPLETE)
        assert projection.scouting_stage == ScoutingStage.COMPLETE
        assert projection.is_revealed("speed")
        assert projection.is_revealed("potential")
        assert projection.get_projected_value("speed") == 90
        assert projection.get_projected_value("potential") == 95

    def test_reveal_attribute(self):
        """Manually revealing an attribute should set exact values."""
        projection = PlayerProjection(
            player_id="player-123",
            scouting_stage=ScoutingStage.BASIC,
            scout_level=ScoutingLevel.AVERAGE,
        )

        reveal_attribute(projection, "potential", 92)

        assert projection.is_revealed("potential")
        assert projection.get_projected_value("potential") == 92
        assert projection.get_accuracy("potential") == ScoutingAccuracy.EXACT

    def test_projection_serialization(self):
        attrs = PlayerAttributes()
        attrs.set("speed", 90)

        projection = generate_initial_projection(attrs, "player-123")
        data = projection.to_dict()
        restored = PlayerProjection.from_dict(data)

        assert restored.player_id == projection.player_id
        assert restored.scouting_stage == projection.scouting_stage
        assert "speed" in restored.attributes


class TestScoutingGrades:
    """Test letter grade system."""

    def test_grade_to_range(self):
        min_val, max_val = grade_to_range(ScoutingGrade.A_PLUS)
        assert min_val == 90
        assert max_val == 99

        min_val, max_val = grade_to_range(ScoutingGrade.C)
        assert min_val == 55
        assert max_val == 59

    def test_high_value_gets_high_grade(self):
        from huddle.core.scouting.report import value_to_grade

        grade = value_to_grade(95, ScoutingAccuracy.EXACT)
        assert grade == ScoutingGrade.A_PLUS

        grade = value_to_grade(72, ScoutingAccuracy.EXACT)
        assert grade == ScoutingGrade.B


class TestScoutingReport:
    """Test scouting report generation."""

    def test_create_scouting_report(self):
        attrs = PlayerAttributes()
        attrs.set("speed", 92)
        attrs.set("acceleration", 88)
        attrs.set("trucking", 75)
        attrs.set("potential", 95)

        projection = generate_initial_projection(attrs, "player-123")
        projection = refine_projection(projection, attrs, ScoutingStage.COMPLETE)

        report = create_scouting_report(
            projection,
            player_name="Marcus Johnson",
            position="RB",
            age=22,
        )

        assert report.player_name == "Marcus Johnson"
        assert report.position == "RB"
        assert report.age == 22
        assert report.stage == ScoutingStage.COMPLETE
        assert report.overall_confidence == "Very High"

    def test_report_with_philosophies(self):
        from huddle.core.philosophy import TeamPhilosophies, RBPhilosophy

        attrs = PlayerAttributes()
        attrs.set("speed", 95)
        attrs.set("acceleration", 92)
        attrs.set("trucking", 60)

        projection = generate_initial_projection(attrs, "player-123")
        projection = refine_projection(projection, attrs, ScoutingStage.COMPLETE)

        philosophies = TeamPhilosophies(rb=RBPhilosophy.SPEED)
        report = create_scouting_report(
            projection,
            player_name="Speed Demon",
            position="RB",
            age=22,
            team_philosophies=philosophies,
        )

        # Should show positive scheme fit for speed back
        assert report.scheme_fit != "Unknown"
        assert report.scheme_fit_delta != 0


class TestScout:
    """Test individual scouts."""

    def test_scout_creation(self):
        scout = Scout(
            name="John Smith",
            level=ScoutingLevel.EXPERIENCED,
            specialty=ScoutSpecialty.QUARTERBACKS,
        )
        assert scout.name == "John Smith"
        assert scout.level == ScoutingLevel.EXPERIENCED
        assert scout.specialty == ScoutSpecialty.QUARTERBACKS

    def test_specialty_accuracy_bonus(self):
        scout = Scout(
            level=ScoutingLevel.AVERAGE,
            specialty=ScoutSpecialty.QUARTERBACKS,
        )

        # Should get bonus for QB position
        qb_accuracy = scout.get_accuracy_for_position("QB")
        # Should not get bonus for RB position
        rb_accuracy = scout.get_accuracy_for_position("RB")

        # QB should be higher (more experienced) due to specialty
        assert qb_accuracy.value != rb_accuracy.value or qb_accuracy == ScoutingLevel.EXPERIENCED

    def test_generate_random_scout(self):
        scout = Scout.generate_random()
        assert scout.name  # Should have a name
        assert scout.level in list(ScoutingLevel)
        assert scout.specialty in list(ScoutSpecialty)

    def test_scout_serialization(self):
        scout = Scout(
            name="Mike Johnson",
            level=ScoutingLevel.ELITE,
            specialty=ScoutSpecialty.SECONDARY,
            experience_years=15,
        )
        data = scout.to_dict()
        restored = Scout.from_dict(data)

        assert restored.name == scout.name
        assert restored.level == scout.level
        assert restored.specialty == scout.specialty
        assert restored.experience_years == scout.experience_years


class TestScoutingDepartment:
    """Test the scouting department."""

    def test_department_creation(self):
        dept = ScoutingDepartment()
        assert len(dept.scouts) == 0
        assert dept.budget == 100
        assert dept.remaining_budget == 100

    def test_add_and_remove_scout(self):
        dept = ScoutingDepartment()
        scout = Scout(name="Test Scout", level=ScoutingLevel.AVERAGE)
        dept.add_scout(scout)

        assert len(dept.scouts) == 1

        removed = dept.remove_scout(scout.id)
        assert removed == scout
        assert len(dept.scouts) == 0

    def test_budget_spending(self):
        dept = ScoutingDepartment(budget=100)

        assert dept.spend_budget(30)
        assert dept.remaining_budget == 70

        assert not dept.spend_budget(80)  # Not enough
        assert dept.remaining_budget == 70

        dept.reset_budget()
        assert dept.remaining_budget == 100

    def test_get_scout_for_position(self):
        dept = ScoutingDepartment()
        qb_scout = Scout(
            name="QB Expert",
            level=ScoutingLevel.ELITE,
            specialty=ScoutSpecialty.QUARTERBACKS,
            _skill=90,
        )
        general_scout = Scout(
            name="General",
            level=ScoutingLevel.AVERAGE,
            specialty=ScoutSpecialty.GENERAL,
            _skill=50,
        )
        dept.add_scout(qb_scout)
        dept.add_scout(general_scout)

        # Should pick QB expert for QBs
        best = dept.get_scout_for_position("QB")
        assert best == qb_scout

    def test_generate_default_department(self):
        dept = ScoutingDepartment.generate_default()
        assert len(dept.scouts) >= 3  # Should have at least 3 scouts
        assert dept.budget > 0

    def test_department_serialization(self):
        dept = ScoutingDepartment.generate_default()
        data = dept.to_dict()
        restored = ScoutingDepartment.from_dict(data)

        assert len(restored.scouts) == len(dept.scouts)
        assert restored.budget == dept.budget


class TestSpecialtyPositions:
    """Test position specialty mappings."""

    def test_all_positions_covered(self):
        """Verify key positions have specialists."""
        all_covered = set()
        for positions in SPECIALTY_POSITIONS.values():
            all_covered.update(positions)

        # Check key positions are covered
        assert "QB" in all_covered
        assert "RB" in all_covered
        assert "WR" in all_covered
        assert "CB" in all_covered
        assert "MLB" in all_covered

    def test_specialty_position_lists(self):
        assert "QB" in SPECIALTY_POSITIONS[ScoutSpecialty.QUARTERBACKS]
        assert "CB" in SPECIALTY_POSITIONS[ScoutSpecialty.SECONDARY]
        assert "FS" in SPECIALTY_POSITIONS[ScoutSpecialty.SECONDARY]
        assert "LT" in SPECIALTY_POSITIONS[ScoutSpecialty.OFFENSIVE_LINE]
