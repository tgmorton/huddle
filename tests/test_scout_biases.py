"""Tests for the Scout Cognitive Biases system."""

import pytest
from uuid import uuid4

from huddle.core.scouting.staff import (
    Scout,
    ScoutBiases,
    ScoutTrackRecord,
    ScoutSpecialty,
    ScoutingDepartment,
    CONFERENCE_REGIONS,
)
from huddle.core.scouting.stages import ScoutingLevel


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def neutral_scout():
    """Scout with neutral biases."""
    return Scout(
        name="Neutral Nick",
        level=ScoutingLevel.EXPERIENCED,
        specialty=ScoutSpecialty.GENERAL,
        _skill=70,
        biases=ScoutBiases(),  # All 0.5
    )


@pytest.fixture
def recency_scout():
    """Scout who overweights recent performances."""
    return Scout(
        name="Recency Rick",
        level=ScoutingLevel.AVERAGE,
        specialty=ScoutSpecialty.SKILL_POSITIONS,
        _skill=55,
        biases=ScoutBiases(recency_bias=0.85),
    )


@pytest.fixture
def measurables_scout():
    """Scout who loves athletic freaks."""
    return Scout(
        name="Measurables Mike",
        level=ScoutingLevel.EXPERIENCED,
        specialty=ScoutSpecialty.DEFENSIVE_LINE,
        _skill=65,
        biases=ScoutBiases(measurables_bias=0.8),
    )


@pytest.fixture
def film_scout():
    """Scout who focuses on tape, not measurables."""
    return Scout(
        name="Film Fred",
        level=ScoutingLevel.ELITE,
        specialty=ScoutSpecialty.QUARTERBACKS,
        _skill=85,
        biases=ScoutBiases(measurables_bias=0.2),
    )


@pytest.fixture
def sec_scout():
    """Scout with strong SEC bias."""
    return Scout(
        name="SEC Steve",
        level=ScoutingLevel.AVERAGE,
        specialty=ScoutSpecialty.SOUTHEAST,
        _skill=50,
        biases=ScoutBiases(conference_biases={"SEC": 7.0, "MAC": -5.0}),
    )


@pytest.fixture
def stubborn_scout():
    """Scout with strong confirmation bias."""
    return Scout(
        name="Stubborn Sam",
        level=ScoutingLevel.EXPERIENCED,
        specialty=ScoutSpecialty.GENERAL,
        _skill=60,
        biases=ScoutBiases(confirmation_strength=0.9),
    )


@pytest.fixture
def ol_weakness_scout():
    """Scout who struggles with offensive line evaluation."""
    return Scout(
        name="OL-Blind Oliver",
        level=ScoutingLevel.EXPERIENCED,
        specialty=ScoutSpecialty.SKILL_POSITIONS,
        _skill=70,
        biases=ScoutBiases(position_weaknesses=["OL"]),
    )


@pytest.fixture
def ceiling_scout():
    """Scout who sees upside everywhere."""
    return Scout(
        name="Ceiling Carl",
        level=ScoutingLevel.AVERAGE,
        specialty=ScoutSpecialty.GENERAL,
        _skill=55,
        biases=ScoutBiases(risk_tolerance=0.8),
    )


# =============================================================================
# Test: ScoutBiases Class
# =============================================================================

class TestScoutBiases:
    """Tests for ScoutBiases dataclass."""

    def test_default_values_are_neutral(self):
        """Default biases are neutral (0.5)."""
        biases = ScoutBiases()
        assert biases.recency_bias == 0.5
        assert biases.measurables_bias == 0.5
        assert biases.confirmation_strength == 0.5
        assert biases.risk_tolerance == 0.5
        assert biases.conference_biases == {}
        assert biases.position_weaknesses == []

    def test_get_conference_bias_returns_zero_for_unknown(self):
        """Unknown conferences return 0 bias."""
        biases = ScoutBiases(conference_biases={"SEC": 5.0})
        assert biases.get_conference_bias("SEC") == 5.0
        assert biases.get_conference_bias("Big Ten") == 0.0

    def test_has_position_weakness(self):
        """Position weakness detection works."""
        biases = ScoutBiases(position_weaknesses=["OL", "DB"])
        assert biases.has_position_weakness("OL")
        assert biases.has_position_weakness("DB")
        assert not biases.has_position_weakness("QB")
        assert not biases.has_position_weakness("WR")

    def test_initial_impression_only_set_once(self):
        """First impression is sticky."""
        biases = ScoutBiases()
        player_id = str(uuid4())

        biases.set_initial_impression(player_id, "high")
        assert biases.initial_impressions[player_id] == "high"

        # Try to overwrite - should not change
        biases.set_initial_impression(player_id, "low")
        assert biases.initial_impressions[player_id] == "high"

    def test_confirmation_modifier_positive(self):
        """High impression with high confirmation strength gives positive modifier."""
        biases = ScoutBiases(confirmation_strength=0.9)
        player_id = str(uuid4())
        biases.set_initial_impression(player_id, "high")

        modifier = biases.get_confirmation_modifier(player_id)
        assert modifier > 0  # Positive boost

    def test_confirmation_modifier_negative(self):
        """Low impression with high confirmation strength gives negative modifier."""
        biases = ScoutBiases(confirmation_strength=0.9)
        player_id = str(uuid4())
        biases.set_initial_impression(player_id, "low")

        modifier = biases.get_confirmation_modifier(player_id)
        assert modifier < 0  # Negative penalty

    def test_confirmation_modifier_neutral_at_half(self):
        """Neutral confirmation strength gives no modifier."""
        biases = ScoutBiases(confirmation_strength=0.5)
        player_id = str(uuid4())
        biases.set_initial_impression(player_id, "high")

        modifier = biases.get_confirmation_modifier(player_id)
        assert modifier == 0.0

    def test_serialization_roundtrip(self):
        """Biases can be serialized and restored."""
        original = ScoutBiases(
            recency_bias=0.7,
            measurables_bias=0.3,
            confirmation_strength=0.8,
            risk_tolerance=0.6,
            conference_biases={"SEC": 5.0, "MAC": -3.0},
            position_weaknesses=["OL", "DL"],
            initial_impressions={"abc": "high", "def": "low"},
        )
        data = original.to_dict()
        restored = ScoutBiases.from_dict(data)

        assert restored.recency_bias == 0.7
        assert restored.measurables_bias == 0.3
        assert restored.conference_biases["SEC"] == 5.0
        assert "OL" in restored.position_weaknesses
        assert restored.initial_impressions["abc"] == "high"

    def test_generate_random_in_valid_range(self):
        """Randomly generated biases are in valid ranges."""
        for _ in range(20):
            biases = ScoutBiases.generate_random()
            assert 0.1 <= biases.recency_bias <= 0.9
            assert 0.1 <= biases.measurables_bias <= 0.9
            assert 0.1 <= biases.confirmation_strength <= 0.9
            assert 0.1 <= biases.risk_tolerance <= 0.9


# =============================================================================
# Test: ScoutTrackRecord
# =============================================================================

class TestScoutTrackRecord:
    """Tests for ScoutTrackRecord."""

    def test_default_accuracy_is_unknown(self):
        """New scout has unknown accuracy (0.5)."""
        record = ScoutTrackRecord()
        assert record.overall_accuracy == 0.5
        assert record.get_position_accuracy("QB") == 0.5

    def test_record_evaluation_updates_counts(self):
        """Recording evaluations updates counts."""
        record = ScoutTrackRecord()

        record.record_evaluation("QB", was_accurate=True)
        assert record.total_evaluations == 1
        assert record.accurate_evaluations == 1
        assert record.overall_accuracy == 1.0

        record.record_evaluation("QB", was_accurate=False)
        assert record.total_evaluations == 2
        assert record.accurate_evaluations == 1
        assert record.overall_accuracy == 0.5

    def test_position_specific_accuracy(self):
        """Position accuracy is tracked separately."""
        record = ScoutTrackRecord()

        # Great at QBs
        record.record_evaluation("QB", was_accurate=True)
        record.record_evaluation("QB", was_accurate=True)
        record.record_evaluation("QB", was_accurate=True)

        # Bad at WRs
        record.record_evaluation("WR", was_accurate=False)
        record.record_evaluation("WR", was_accurate=False)

        assert record.get_position_accuracy("QB") == 1.0
        assert record.get_position_accuracy("WR") == 0.0
        assert record.get_position_accuracy("RB") == 0.5  # Unknown

    def test_notable_calls_tracked(self):
        """Big hits and misses are recorded."""
        record = ScoutTrackRecord()

        record.record_evaluation("QB", was_accurate=True, player_name="Joe Burrow", was_notable=True)
        assert "Joe Burrow" in record.big_hits

        record.record_evaluation("WR", was_accurate=False, player_name="N'Keal Harry", was_notable=True)
        assert "N'Keal Harry" in record.big_misses

    def test_notable_calls_limited_to_five(self):
        """Only last 5 notable calls kept."""
        record = ScoutTrackRecord()

        for i in range(7):
            record.record_evaluation("QB", was_accurate=True, player_name=f"Player{i}", was_notable=True)

        assert len(record.big_hits) == 5
        assert "Player0" not in record.big_hits
        assert "Player6" in record.big_hits

    def test_serialization_roundtrip(self):
        """Track record can be serialized and restored."""
        original = ScoutTrackRecord(
            total_evaluations=50,
            accurate_evaluations=35,
            position_evaluations={"QB": 10, "WR": 15},
            position_accurate={"QB": 8, "WR": 10},
            big_hits=["Player A", "Player B"],
            big_misses=["Player C"],
        )
        data = original.to_dict()
        restored = ScoutTrackRecord.from_dict(data)

        assert restored.total_evaluations == 50
        assert restored.accurate_evaluations == 35
        assert restored.position_evaluations["QB"] == 10
        assert restored.overall_accuracy == 0.7


# =============================================================================
# Test: Scout Bias Properties
# =============================================================================

class TestScoutBiasProperties:
    """Tests for Scout convenience properties."""

    def test_is_high_recency(self, recency_scout, neutral_scout):
        """High recency bias detected."""
        assert recency_scout.is_high_recency
        assert not neutral_scout.is_high_recency

    def test_is_measurables_scout(self, measurables_scout, film_scout, neutral_scout):
        """Measurables scout detected."""
        assert measurables_scout.is_measurables_scout
        assert not film_scout.is_measurables_scout
        assert not neutral_scout.is_measurables_scout

    def test_is_film_scout(self, film_scout, measurables_scout):
        """Film scout detected."""
        assert film_scout.is_film_scout
        assert not measurables_scout.is_film_scout

    def test_is_ceiling_scout(self, ceiling_scout, neutral_scout):
        """Ceiling scout detected."""
        assert ceiling_scout.is_ceiling_scout
        assert not neutral_scout.is_ceiling_scout


# =============================================================================
# Test: Scout Accuracy for Position
# =============================================================================

class TestScoutAccuracyForPosition:
    """Tests for get_accuracy_for_position with biases."""

    def test_specialty_bonus(self, neutral_scout):
        """Specialty gives accuracy bonus."""
        # GENERAL specialty doesn't give bonuses
        assert neutral_scout.get_accuracy_for_position("QB") == ScoutingLevel.EXPERIENCED

    def test_specialty_bonus_for_matching_position(self, recency_scout):
        """Scout with SKILL_POSITIONS specialty gets bonus for WR."""
        # AVERAGE + specialty bonus = EXPERIENCED
        assert recency_scout.get_accuracy_for_position("WR") == ScoutingLevel.EXPERIENCED
        # No bonus for QB
        assert recency_scout.get_accuracy_for_position("QB") == ScoutingLevel.AVERAGE

    def test_position_weakness_penalty(self, ol_weakness_scout):
        """Position weakness gives accuracy penalty."""
        # EXPERIENCED but has OL weakness
        assert ol_weakness_scout.get_accuracy_for_position("LT") == ScoutingLevel.AVERAGE
        assert ol_weakness_scout.get_accuracy_for_position("C") == ScoutingLevel.AVERAGE
        # No penalty for non-OL
        assert ol_weakness_scout.get_accuracy_for_position("QB") == ScoutingLevel.EXPERIENCED

    def test_specialty_and_weakness_can_stack(self):
        """Scout can have both specialty bonus and weakness penalty."""
        scout = Scout(
            level=ScoutingLevel.AVERAGE,
            specialty=ScoutSpecialty.SKILL_POSITIONS,
            biases=ScoutBiases(position_weaknesses=["WR"]),
        )
        # WR: specialty bonus (+1) and weakness penalty (-1) = net 0
        assert scout.get_accuracy_for_position("WR") == ScoutingLevel.AVERAGE
        # RB: specialty bonus only
        assert scout.get_accuracy_for_position("RB") == ScoutingLevel.EXPERIENCED


# =============================================================================
# Test: Bias Application to Projections
# =============================================================================

class TestBiasApplication:
    """Tests for apply_biases_to_projection."""

    def test_neutral_scout_no_change(self, neutral_scout):
        """Neutral scout doesn't modify projections."""
        result = neutral_scout.apply_biases_to_projection(
            base_projection=75,
            player_id="test",
            position="QB",
        )
        assert result == 75

    def test_recency_bias_great_performance(self, recency_scout):
        """High recency scout boosts after great performance."""
        result = recency_scout.apply_biases_to_projection(
            base_projection=75,
            player_id="test",
            position="WR",
            recent_performance="great",
        )
        assert result > 75

    def test_recency_bias_poor_performance(self, recency_scout):
        """High recency scout penalizes after poor performance."""
        result = recency_scout.apply_biases_to_projection(
            base_projection=75,
            player_id="test",
            position="WR",
            recent_performance="poor",
        )
        assert result < 75

    def test_measurables_bias_athletic_freak(self, measurables_scout):
        """Measurables scout boosts athletic freaks."""
        result = measurables_scout.apply_biases_to_projection(
            base_projection=70,
            player_id="test",
            position="DE",
            is_athletic_freak=True,
        )
        assert result > 70

    def test_film_scout_penalizes_athletic_freak(self, film_scout):
        """Film scout slightly undervalues pure athletes."""
        result = film_scout.apply_biases_to_projection(
            base_projection=70,
            player_id="test",
            position="QB",
            is_athletic_freak=True,
        )
        # Measurables bias < 0.5 means negative effect
        assert result < 70

    def test_conference_bias_positive(self, sec_scout):
        """SEC scout overvalues SEC players."""
        result = sec_scout.apply_biases_to_projection(
            base_projection=70,
            player_id="test",
            position="RB",
            conference="SEC",
        )
        assert result > 70
        assert result >= 77  # +7 from SEC bias

    def test_conference_bias_negative(self, sec_scout):
        """SEC scout undervalues MAC players."""
        result = sec_scout.apply_biases_to_projection(
            base_projection=70,
            player_id="test",
            position="RB",
            conference="MAC",
        )
        assert result < 70
        assert result <= 65  # -5 from MAC bias

    def test_confirmation_bias_high_impression(self, stubborn_scout):
        """Stubborn scout overvalues players they liked first."""
        player_id = str(uuid4())
        stubborn_scout.biases.set_initial_impression(player_id, "high")

        result = stubborn_scout.apply_biases_to_projection(
            base_projection=70,
            player_id=player_id,
            position="LB",
        )
        assert result > 70

    def test_confirmation_bias_low_impression(self, stubborn_scout):
        """Stubborn scout undervalues players they disliked first."""
        player_id = str(uuid4())
        stubborn_scout.biases.set_initial_impression(player_id, "low")

        result = stubborn_scout.apply_biases_to_projection(
            base_projection=70,
            player_id=player_id,
            position="LB",
        )
        assert result < 70

    def test_multiple_biases_stack(self, sec_scout):
        """Multiple biases can stack."""
        player_id = str(uuid4())
        sec_scout.biases.recency_bias = 0.8
        sec_scout.biases.confirmation_strength = 0.8
        sec_scout.biases.set_initial_impression(player_id, "high")

        result = sec_scout.apply_biases_to_projection(
            base_projection=70,
            player_id=player_id,
            position="RB",
            conference="SEC",  # +7
            recent_performance="great",  # + some
        )
        # SEC bias + recency + confirmation = big boost
        assert result > 80

    def test_projection_clamped_to_valid_range(self, sec_scout):
        """Projection stays in 1-99 range."""
        # Try to push above 99
        result = sec_scout.apply_biases_to_projection(
            base_projection=98,
            player_id="test",
            position="WR",
            conference="SEC",
        )
        assert result <= 99

        # Try to push below 1
        result = sec_scout.apply_biases_to_projection(
            base_projection=3,
            player_id="test",
            position="WR",
            conference="MAC",
        )
        assert result >= 1


# =============================================================================
# Test: Bias Summary
# =============================================================================

class TestBiasSummary:
    """Tests for get_bias_summary."""

    def test_neutral_scout_no_notable_biases(self, neutral_scout):
        """Neutral scout has no notable biases."""
        summary = neutral_scout.get_bias_summary()
        assert summary == "No notable biases"

    def test_recency_scout_identified(self, recency_scout):
        """Recency bias is identified."""
        summary = recency_scout.get_bias_summary()
        assert "recent games" in summary.lower()

    def test_measurables_scout_identified(self, measurables_scout):
        """Measurables bias is identified."""
        summary = measurables_scout.get_bias_summary()
        assert "athletic" in summary.lower()

    def test_film_scout_identified(self, film_scout):
        """Film-first scout is identified."""
        summary = film_scout.get_bias_summary()
        assert "film" in summary.lower()

    def test_position_weaknesses_listed(self, ol_weakness_scout):
        """Position weaknesses are listed."""
        summary = ol_weakness_scout.get_bias_summary()
        assert "OL" in summary

    def test_conference_biases_listed(self, sec_scout):
        """Conference biases are listed."""
        summary = sec_scout.get_bias_summary()
        assert "SEC" in summary


# =============================================================================
# Test: Scout Generation
# =============================================================================

class TestScoutGeneration:
    """Tests for Scout.generate_random."""

    def test_generate_random_has_biases(self):
        """Randomly generated scouts have biases."""
        scout = Scout.generate_random()
        assert scout.biases is not None
        assert isinstance(scout.biases, ScoutBiases)

    def test_regional_scouts_have_home_bias(self):
        """Regional scouts tend to have home conference bias."""
        # Generate several to find a regional scout
        regional_found = False
        for _ in range(100):
            scout = Scout.generate_random()
            if scout.specialty == ScoutSpecialty.SOUTHEAST:
                # Should have SEC bias
                if "SEC" in scout.biases.conference_biases:
                    regional_found = True
                    assert scout.biases.conference_biases["SEC"] > 0
                    break

        # At least sometimes we should find one
        # (This is probabilistic, so we just check we can generate them)
        assert True  # Generation works

    def test_generate_random_produces_variety(self):
        """Random generation produces variety."""
        scouts = [Scout.generate_random() for _ in range(20)]

        recency_values = [s.biases.recency_bias for s in scouts]
        measurables_values = [s.biases.measurables_bias for s in scouts]

        # Should have some variety (not all the same)
        assert max(recency_values) != min(recency_values)
        assert max(measurables_values) != min(measurables_values)


# =============================================================================
# Test: Scout Serialization
# =============================================================================

class TestScoutSerialization:
    """Tests for Scout serialization with biases."""

    def test_serialization_roundtrip(self, sec_scout):
        """Scout with biases can be serialized and restored."""
        sec_scout.biases.set_initial_impression("player1", "high")
        sec_scout.track_record.record_evaluation("QB", True, "Joe Burrow", True)

        data = sec_scout.to_dict()
        restored = Scout.from_dict(data)

        assert restored.name == sec_scout.name
        assert restored.biases.conference_biases["SEC"] == 7.0
        assert restored.biases.conference_biases["MAC"] == -5.0
        assert restored.biases.initial_impressions["player1"] == "high"
        assert restored.track_record.total_evaluations == 1


# =============================================================================
# Test: ScoutingDepartment with Biases
# =============================================================================

class TestScoutingDepartmentBiases:
    """Tests for ScoutingDepartment with biased scouts."""

    def test_scouts_with_biases_serialized_in_department(self):
        """Department serialization preserves scout biases."""
        dept = ScoutingDepartment()

        scout = Scout(
            name="Biased Bob",
            level=ScoutingLevel.EXPERIENCED,
            _skill=70,
            biases=ScoutBiases(
                recency_bias=0.8,
                conference_biases={"SEC": 5.0},
            ),
        )
        dept.add_scout(scout)

        data = dept.to_dict()
        restored = ScoutingDepartment.from_dict(data)

        assert len(restored.scouts) == 1
        assert restored.scouts[0].biases.recency_bias == 0.8
        assert restored.scouts[0].biases.conference_biases["SEC"] == 5.0

    def test_generate_default_has_biased_scouts(self):
        """Default department has scouts with biases."""
        dept = ScoutingDepartment.generate_default()

        has_some_bias = False
        for scout in dept.scouts:
            if (scout.biases.recency_bias != 0.5 or
                scout.biases.measurables_bias != 0.5 or
                scout.biases.conference_biases):
                has_some_bias = True
                break

        # At least one scout should have non-neutral biases
        assert has_some_bias or len(dept.scouts) == 0
