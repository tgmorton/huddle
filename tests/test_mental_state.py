"""Tests for the Inner Weather mental state system."""

import pytest
from uuid import uuid4

from huddle.core.mental_state import (
    WeeklyMentalState,
    PlayerGameState,
    build_weekly_mental_state,
    prepare_player_for_game,
    DEFAULT_CONFIDENCE,
    MIN_CONFIDENCE,
    MAX_CONFIDENCE,
    MORALE_CONFIDENCE_WEIGHT,
    clamp,
)
from huddle.core.models.player import Player
from huddle.core.enums import Position
from huddle.core.personality import PersonalityProfile, Trait
from huddle.core.personality.archetypes import ArchetypeType
from huddle.core.approval import PlayerApproval


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def player_id():
    """Generate a player ID."""
    return uuid4()


@pytest.fixture
def basic_player():
    """Create a basic player without personality."""
    return Player(
        first_name="John",
        last_name="Smith",
        position=Position.QB,
        age=25,
        experience_years=3,
    )


@pytest.fixture
def steady_personality():
    """Create a level-headed personality (steady, recovers fast)."""
    return PersonalityProfile(
        archetype=ArchetypeType.STOIC,
        traits={
            Trait.LEVEL_HEADED: 0.85,  # Strong
            Trait.PATIENT: 0.75,  # Strong
            Trait.DRIVEN: 0.6,  # Moderate
        }
    )


@pytest.fixture
def volatile_personality():
    """Create a dramatic personality (swings wildly, recovers slowly)."""
    return PersonalityProfile(
        archetype=ArchetypeType.HEADLINER,
        traits={
            Trait.DRAMATIC: 0.9,  # Very strong
            Trait.IMPULSIVE: 0.8,  # Strong
            Trait.SENSITIVE: 0.75,  # Strong
        }
    )


@pytest.fixture
def clutch_personality():
    """Create a competitive personality (rises to pressure)."""
    return PersonalityProfile(
        archetype=ArchetypeType.TITAN,  # Aggressive, competitive type
        traits={
            Trait.COMPETITIVE: 0.9,  # Very strong
            Trait.DRIVEN: 0.85,  # Strong
            Trait.AGGRESSIVE: 0.7,  # Moderate-strong
        }
    )


@pytest.fixture
def player_with_steady_personality(steady_personality):
    """Create a player with steady personality."""
    return Player(
        first_name="Tom",
        last_name="Steady",
        position=Position.QB,
        age=32,
        experience_years=10,
        personality=steady_personality,
    )


@pytest.fixture
def player_with_volatile_personality(volatile_personality):
    """Create a player with volatile personality."""
    return Player(
        first_name="Drama",
        last_name="King",
        position=Position.WR,
        age=24,
        experience_years=2,
        personality=volatile_personality,
    )


@pytest.fixture
def player_with_high_morale(steady_personality):
    """Create a player with high morale."""
    player = Player(
        first_name="Happy",
        last_name="Player",
        position=Position.RB,
        age=26,
        experience_years=4,
        personality=steady_personality,
    )
    player.approval = PlayerApproval(
        player_id=player.id,
        approval=85.0,
        trend=5.0,
    )
    return player


@pytest.fixture
def player_with_low_morale(volatile_personality):
    """Create a player with low morale."""
    player = Player(
        first_name="Unhappy",
        last_name="Player",
        position=Position.CB,
        age=28,
        experience_years=6,
        personality=volatile_personality,
    )
    player.approval = PlayerApproval(
        player_id=player.id,
        approval=25.0,
        trend=-3.0,
        grievances=["Lost starting job", "Contract dispute"],
    )
    return player


# =============================================================================
# Test: clamp helper
# =============================================================================

class TestClamp:
    """Tests for the clamp utility function."""

    def test_clamp_within_bounds(self):
        """Value within bounds is unchanged."""
        assert clamp(50.0, 0.0, 100.0) == 50.0

    def test_clamp_below_minimum(self):
        """Value below minimum returns minimum."""
        assert clamp(-10.0, 0.0, 100.0) == 0.0

    def test_clamp_above_maximum(self):
        """Value above maximum returns maximum."""
        assert clamp(150.0, 0.0, 100.0) == 100.0

    def test_clamp_at_bounds(self):
        """Values at bounds are unchanged."""
        assert clamp(0.0, 0.0, 100.0) == 0.0
        assert clamp(100.0, 0.0, 100.0) == 100.0


# =============================================================================
# Test: PersonalityProfile Inner Weather Methods
# =============================================================================

class TestPersonalityInnerWeather:
    """Tests for personality-based mental state properties."""

    def test_confidence_volatility_level_headed_reduces(self, steady_personality):
        """Level-headed players have reduced volatility."""
        volatility = steady_personality.get_confidence_volatility()
        assert volatility < 1.0
        # Level-headed (0.7x) + patient (0.85x) = significantly reduced
        assert volatility < 0.7

    def test_confidence_volatility_dramatic_increases(self, volatile_personality):
        """Dramatic players have increased volatility."""
        volatility = volatile_personality.get_confidence_volatility()
        assert volatility > 1.0
        # Dramatic (1.35x) + impulsive (1.15x) + sensitive (1.1x) = high
        assert volatility > 1.3

    def test_confidence_volatility_clamped(self):
        """Volatility is clamped to reasonable range."""
        # Create extreme personality
        extreme = PersonalityProfile(
            archetype=ArchetypeType.HEADLINER,
            traits={
                Trait.DRAMATIC: 1.0,
                Trait.IMPULSIVE: 1.0,
                Trait.SENSITIVE: 1.0,
            }
        )
        volatility = extreme.get_confidence_volatility()
        assert 0.4 <= volatility <= 1.6

    def test_pressure_response_competitive_positive(self, clutch_personality):
        """Competitive players have positive pressure response."""
        response = clutch_personality.get_pressure_response()
        assert response > 0.0
        # Competitive + driven + aggressive = high positive
        assert response > 0.2

    def test_pressure_response_sensitive_negative(self, volatile_personality):
        """Sensitive players have negative pressure response."""
        response = volatile_personality.get_pressure_response()
        assert response < 0.0

    def test_pressure_response_clamped(self):
        """Pressure response is clamped to range."""
        extreme = PersonalityProfile(
            archetype=ArchetypeType.TITAN,  # Aggressive, competitive type
            traits={
                Trait.COMPETITIVE: 1.0,
                Trait.DRIVEN: 1.0,
                Trait.AGGRESSIVE: 1.0,
            }
        )
        response = extreme.get_pressure_response()
        assert -0.4 <= response <= 0.4

    def test_baseline_confidence_modifier_driven_positive(self, clutch_personality):
        """Driven/competitive players have positive baseline modifier."""
        modifier = clutch_personality.get_baseline_confidence_modifier()
        assert modifier > 0.0

    def test_baseline_confidence_modifier_sensitive_negative(self, volatile_personality):
        """Sensitive players have negative baseline modifier."""
        modifier = volatile_personality.get_baseline_confidence_modifier()
        assert modifier < 0.0

    def test_confidence_recovery_rate_level_headed_fast(self, steady_personality):
        """Level-headed players recover confidence faster."""
        rate = steady_personality.get_confidence_recovery_rate()
        assert rate > 1.0

    def test_confidence_recovery_rate_sensitive_slow(self, volatile_personality):
        """Sensitive/dramatic players recover confidence slower."""
        rate = volatile_personality.get_confidence_recovery_rate()
        assert rate < 1.0


# =============================================================================
# Test: WeeklyMentalState
# =============================================================================

class TestWeeklyMentalState:
    """Tests for the WeeklyMentalState dataclass."""

    def test_default_values(self, player_id):
        """Default values are sensible."""
        state = WeeklyMentalState(player_id=player_id)
        assert state.morale == 50.0
        assert state.morale_trend == 0.0
        assert state.grievances == []
        assert state.opponent_familiarity == 0.0
        assert state.scheme_familiarity == 0.5
        assert state.fatigue_baseline == 0.0
        assert state.injury_limitations == []

    def test_starting_confidence_default(self, player_id):
        """Default starting confidence is around 50."""
        state = WeeklyMentalState(player_id=player_id)
        starting = state.get_starting_confidence()
        assert 45.0 <= starting <= 55.0

    def test_starting_confidence_high_morale(self, player_id):
        """High morale increases starting confidence."""
        state = WeeklyMentalState(player_id=player_id, morale=80.0)
        starting = state.get_starting_confidence()
        # (80-50) * 0.4 = +12 contribution
        assert starting > 55.0

    def test_starting_confidence_low_morale(self, player_id):
        """Low morale decreases starting confidence."""
        state = WeeklyMentalState(player_id=player_id, morale=20.0)
        starting = state.get_starting_confidence()
        # (20-50) * 0.4 = -12 contribution
        assert starting < 45.0

    def test_starting_confidence_with_personality(self, player_id, clutch_personality):
        """Personality affects starting confidence."""
        state = WeeklyMentalState(player_id=player_id, morale=50.0)
        starting = state.get_starting_confidence(clutch_personality)
        # Driven + competitive = positive modifier
        assert starting > 50.0

    def test_starting_confidence_preparation_bonus(self, player_id):
        """Opponent familiarity adds to starting confidence."""
        state = WeeklyMentalState(
            player_id=player_id,
            opponent_familiarity=1.0,  # Max prep
        )
        starting = state.get_starting_confidence()
        # 1.0 * 5.0 = +5 contribution
        assert starting > 50.0

    def test_starting_confidence_scheme_familiarity(self, player_id):
        """Scheme familiarity affects starting confidence."""
        # High familiarity
        high_scheme = WeeklyMentalState(
            player_id=player_id,
            scheme_familiarity=1.0,
        )
        # Low familiarity
        low_scheme = WeeklyMentalState(
            player_id=player_id,
            scheme_familiarity=0.0,
        )
        high_start = high_scheme.get_starting_confidence()
        low_start = low_scheme.get_starting_confidence()
        assert high_start > low_start

    def test_starting_confidence_clamped(self, player_id, clutch_personality):
        """Starting confidence is clamped to 20-80."""
        # Try to get very high
        high = WeeklyMentalState(
            player_id=player_id,
            morale=100.0,
            opponent_familiarity=1.0,
            scheme_familiarity=1.0,
        )
        # Try to get very low
        low = WeeklyMentalState(
            player_id=player_id,
            morale=0.0,
            scheme_familiarity=0.0,
            fatigue_baseline=1.0,
        )
        assert 20.0 <= high.get_starting_confidence(clutch_personality) <= 80.0
        assert 20.0 <= low.get_starting_confidence() <= 80.0

    def test_confidence_bounds_default(self, player_id):
        """Default confidence bounds are reasonable."""
        state = WeeklyMentalState(player_id=player_id)
        floor, ceiling = state.get_confidence_bounds()
        assert floor < 50.0
        assert ceiling > 50.0
        assert floor >= 5.0
        assert ceiling <= 95.0

    def test_confidence_bounds_level_headed(self, player_id, steady_personality):
        """Level-headed players have narrower bounds."""
        state = WeeklyMentalState(player_id=player_id)
        default_floor, default_ceiling = state.get_confidence_bounds()
        steady_floor, steady_ceiling = state.get_confidence_bounds(steady_personality)
        # Narrower range (higher floor, lower ceiling)
        assert steady_floor > default_floor
        assert steady_ceiling < default_ceiling

    def test_confidence_bounds_volatile(self, player_id, volatile_personality):
        """Volatile players have wider bounds."""
        state = WeeklyMentalState(player_id=player_id)
        default_floor, default_ceiling = state.get_confidence_bounds()
        volatile_floor, volatile_ceiling = state.get_confidence_bounds(volatile_personality)
        # Wider range (lower floor, higher ceiling)
        assert volatile_floor < default_floor
        assert volatile_ceiling > default_ceiling

    def test_resilience_modifier_default(self, player_id):
        """Default resilience is 1.0."""
        state = WeeklyMentalState(player_id=player_id, morale=50.0)
        resilience = state.get_resilience_modifier()
        assert 0.95 <= resilience <= 1.05

    def test_resilience_high_morale(self, player_id):
        """High morale increases resilience."""
        state = WeeklyMentalState(player_id=player_id, morale=85.0)
        resilience = state.get_resilience_modifier()
        assert resilience > 1.0

    def test_resilience_low_morale(self, player_id):
        """Low morale decreases resilience."""
        state = WeeklyMentalState(player_id=player_id, morale=30.0)
        resilience = state.get_resilience_modifier()
        assert resilience < 1.0

    def test_resilience_with_personality(self, player_id, steady_personality):
        """Level-headed personality improves resilience."""
        state = WeeklyMentalState(player_id=player_id, morale=50.0)
        default_resilience = state.get_resilience_modifier()
        steady_resilience = state.get_resilience_modifier(steady_personality)
        assert steady_resilience > default_resilience

    def test_resilience_fatigue_penalty(self, player_id):
        """Fatigue reduces resilience."""
        fresh = WeeklyMentalState(player_id=player_id, fatigue_baseline=0.0)
        tired = WeeklyMentalState(player_id=player_id, fatigue_baseline=0.8)
        assert tired.get_resilience_modifier() < fresh.get_resilience_modifier()

    def test_to_dict(self, player_id):
        """Serialization includes all fields."""
        state = WeeklyMentalState(
            player_id=player_id,
            morale=75.0,
            morale_trend=2.0,
            grievances=["Wants more targets"],
            opponent_familiarity=0.8,
            scheme_familiarity=0.7,
            fatigue_baseline=0.1,
            injury_limitations=["Ankle soreness"],
        )
        data = state.to_dict()
        assert data["player_id"] == str(player_id)
        assert data["morale"] == 75.0
        assert data["morale_trend"] == 2.0
        assert data["grievances"] == ["Wants more targets"]
        assert data["opponent_familiarity"] == 0.8
        assert data["scheme_familiarity"] == 0.7
        assert data["fatigue_baseline"] == 0.1
        assert data["injury_limitations"] == ["Ankle soreness"]

    def test_from_dict(self, player_id):
        """Deserialization restores all fields."""
        data = {
            "player_id": str(player_id),
            "morale": 65.0,
            "morale_trend": -1.0,
            "grievances": ["Lost starting job"],
            "opponent_familiarity": 0.5,
            "scheme_familiarity": 0.6,
            "fatigue_baseline": 0.2,
            "injury_limitations": ["Hamstring"],
        }
        state = WeeklyMentalState.from_dict(data)
        assert state.player_id == player_id
        assert state.morale == 65.0
        assert state.morale_trend == -1.0
        assert state.grievances == ["Lost starting job"]
        assert state.opponent_familiarity == 0.5
        assert state.scheme_familiarity == 0.6
        assert state.fatigue_baseline == 0.2
        assert state.injury_limitations == ["Hamstring"]


# =============================================================================
# Test: PlayerGameState
# =============================================================================

class TestPlayerGameState:
    """Tests for the PlayerGameState handoff structure."""

    def test_default_values(self, player_id):
        """Default values are sensible."""
        state = PlayerGameState(player_id=player_id)
        assert state.experience_years == 0
        assert state.cognitive_capacity == 50
        assert state.confidence_volatility == 1.0
        assert state.pressure_response == 0.0
        assert state.confidence_recovery_rate == 1.0
        assert state.starting_confidence == 50.0
        assert state.confidence_floor == 15.0
        assert state.confidence_ceiling == 85.0
        assert state.resilience_modifier == 1.0
        assert state.opponent_familiarity == 0.0
        assert state.scheme_familiarity == 0.5
        assert state.fatigue_baseline == 0.0
        assert state.injury_limitations == []
        assert state.current_morale == 50.0
        assert state.morale_trend == 0.0

    def test_to_dict(self, player_id):
        """Serialization includes all fields."""
        state = PlayerGameState(
            player_id=player_id,
            experience_years=8,
            cognitive_capacity=75,
            confidence_volatility=0.8,
            pressure_response=0.2,
            confidence_recovery_rate=1.2,
            starting_confidence=62.0,
            confidence_floor=25.0,
            confidence_ceiling=75.0,
            resilience_modifier=1.1,
            opponent_familiarity=0.7,
            scheme_familiarity=0.85,
            fatigue_baseline=0.1,
            injury_limitations=["Shoulder"],
            current_morale=70.0,
            morale_trend=3.0,
        )
        data = state.to_dict()
        assert data["player_id"] == str(player_id)
        assert data["experience_years"] == 8
        assert data["cognitive_capacity"] == 75
        assert data["confidence_volatility"] == 0.8
        assert data["pressure_response"] == 0.2
        assert data["confidence_recovery_rate"] == 1.2
        assert data["starting_confidence"] == 62.0
        assert data["confidence_floor"] == 25.0
        assert data["confidence_ceiling"] == 75.0
        assert data["resilience_modifier"] == 1.1
        assert data["opponent_familiarity"] == 0.7
        assert data["scheme_familiarity"] == 0.85
        assert data["fatigue_baseline"] == 0.1
        assert data["injury_limitations"] == ["Shoulder"]
        assert data["current_morale"] == 70.0
        assert data["morale_trend"] == 3.0

    def test_from_dict(self, player_id):
        """Deserialization restores all fields."""
        data = {
            "player_id": str(player_id),
            "experience_years": 5,
            "cognitive_capacity": 60,
            "confidence_volatility": 1.2,
            "pressure_response": -0.1,
            "confidence_recovery_rate": 0.9,
            "starting_confidence": 45.0,
            "confidence_floor": 20.0,
            "confidence_ceiling": 80.0,
            "resilience_modifier": 0.85,
            "opponent_familiarity": 0.3,
            "scheme_familiarity": 0.4,
            "fatigue_baseline": 0.25,
            "injury_limitations": ["Knee"],
            "current_morale": 35.0,
            "morale_trend": -2.0,
        }
        state = PlayerGameState.from_dict(data)
        assert state.player_id == player_id
        assert state.experience_years == 5
        assert state.cognitive_capacity == 60
        assert state.confidence_volatility == 1.2
        assert state.pressure_response == -0.1
        assert state.confidence_recovery_rate == 0.9
        assert state.starting_confidence == 45.0
        assert state.confidence_floor == 20.0
        assert state.confidence_ceiling == 80.0
        assert state.resilience_modifier == 0.85
        assert state.opponent_familiarity == 0.3
        assert state.scheme_familiarity == 0.4
        assert state.fatigue_baseline == 0.25
        assert state.injury_limitations == ["Knee"]
        assert state.current_morale == 35.0
        assert state.morale_trend == -2.0

    def test_roundtrip(self, player_id):
        """Round-trip serialization preserves data."""
        original = PlayerGameState(
            player_id=player_id,
            experience_years=12,
            cognitive_capacity=85,
            confidence_volatility=0.6,
            pressure_response=0.3,
            confidence_recovery_rate=1.4,
            starting_confidence=70.0,
            confidence_floor=30.0,
            confidence_ceiling=70.0,
            resilience_modifier=1.3,
            opponent_familiarity=1.0,
            scheme_familiarity=0.95,
            fatigue_baseline=0.0,
            injury_limitations=[],
            current_morale=90.0,
            morale_trend=5.0,
        )
        data = original.to_dict()
        restored = PlayerGameState.from_dict(data)
        assert restored.player_id == original.player_id
        assert restored.starting_confidence == original.starting_confidence
        assert restored.confidence_volatility == original.confidence_volatility


# =============================================================================
# Test: Helper Functions
# =============================================================================

class TestBuildWeeklyMentalState:
    """Tests for build_weekly_mental_state helper."""

    def test_basic_player(self, basic_player):
        """Works with basic player without approval."""
        state = build_weekly_mental_state(basic_player)
        assert state.player_id == basic_player.id
        assert state.morale == 50.0  # Default
        assert state.grievances == []

    def test_player_with_approval(self, player_with_high_morale):
        """Pulls morale from approval system."""
        state = build_weekly_mental_state(player_with_high_morale)
        assert state.morale == 85.0
        assert state.morale_trend == 5.0

    def test_player_with_grievances(self, player_with_low_morale):
        """Copies grievances from approval."""
        state = build_weekly_mental_state(player_with_low_morale)
        assert state.morale == 25.0
        assert "Lost starting job" in state.grievances
        assert "Contract dispute" in state.grievances


class TestPreparePlayerForGame:
    """Tests for prepare_player_for_game helper."""

    def test_basic_player(self, basic_player):
        """Works with basic player."""
        game_state = prepare_player_for_game(basic_player)
        assert game_state.player_id == basic_player.id
        assert game_state.experience_years == 3
        assert game_state.confidence_volatility == 1.0  # Default
        assert game_state.pressure_response == 0.0  # Default

    def test_veteran_player(self, player_with_steady_personality):
        """Veteran with personality has full package."""
        game_state = prepare_player_for_game(player_with_steady_personality)
        assert game_state.experience_years == 10
        assert game_state.confidence_volatility < 1.0  # Steady
        assert game_state.confidence_recovery_rate > 1.0  # Fast recovery

    def test_volatile_player(self, player_with_volatile_personality):
        """Volatile personality reflected in game state."""
        game_state = prepare_player_for_game(player_with_volatile_personality)
        assert game_state.confidence_volatility > 1.0  # High swings
        assert game_state.confidence_recovery_rate < 1.0  # Slow recovery

    def test_high_morale_player(self, player_with_high_morale):
        """High morale affects starting confidence."""
        game_state = prepare_player_for_game(player_with_high_morale)
        assert game_state.starting_confidence > 50.0
        assert game_state.current_morale == 85.0
        assert game_state.resilience_modifier > 1.0

    def test_low_morale_player(self, player_with_low_morale):
        """Low morale affects starting confidence."""
        game_state = prepare_player_for_game(player_with_low_morale)
        assert game_state.starting_confidence < 50.0
        assert game_state.current_morale == 25.0
        assert game_state.resilience_modifier < 1.0


# =============================================================================
# Test: Player Helper Methods
# =============================================================================

class TestPlayerMentalStateHelpers:
    """Tests for Player mental state helper methods."""

    def test_get_weekly_mental_state(self, player_with_high_morale):
        """Player can generate weekly mental state."""
        state = player_with_high_morale.get_weekly_mental_state()
        assert state.player_id == player_with_high_morale.id
        assert state.morale == 85.0

    def test_prepare_for_game(self, player_with_steady_personality):
        """Player can generate game state package."""
        game_state = player_with_steady_personality.prepare_for_game()
        assert game_state.player_id == player_with_steady_personality.id
        assert game_state.confidence_volatility < 1.0

    def test_get_confidence_volatility_no_personality(self, basic_player):
        """Returns 1.0 without personality."""
        assert basic_player.get_confidence_volatility() == 1.0

    def test_get_confidence_volatility_with_personality(self, player_with_volatile_personality):
        """Returns personality-based volatility."""
        volatility = player_with_volatile_personality.get_confidence_volatility()
        assert volatility > 1.0

    def test_get_pressure_response_no_personality(self, basic_player):
        """Returns 0.0 without personality."""
        assert basic_player.get_pressure_response() == 0.0

    def test_get_pressure_response_with_personality(self, player_with_steady_personality):
        """Returns personality-based pressure response."""
        # Steady personality has level-headed, not necessarily positive pressure
        response = player_with_steady_personality.get_pressure_response()
        # Should be defined (not necessarily positive or negative)
        assert -0.4 <= response <= 0.4

    def test_get_morale_no_approval(self, basic_player):
        """Returns 50.0 without approval tracking."""
        assert basic_player.get_morale() == 50.0

    def test_get_morale_with_approval(self, player_with_high_morale):
        """Returns approval rating as morale."""
        assert player_with_high_morale.get_morale() == 85.0

    def test_get_cognitive_capacity(self, basic_player):
        """Returns awareness attribute."""
        basic_player.attributes.set("awareness", 75)
        assert basic_player.get_cognitive_capacity() == 75

    def test_get_cognitive_capacity_default(self, basic_player):
        """Returns 50 if awareness not set."""
        # PlayerAttributes defaults to 50 for missing attributes
        assert basic_player.get_cognitive_capacity() == 50


# =============================================================================
# Test: Integration Scenarios
# =============================================================================

class TestInnerWeatherIntegration:
    """Integration tests for full Inner Weather flow."""

    def test_steady_veteran_game_prep(self, player_with_steady_personality):
        """Steady veteran has predictable game state."""
        game_state = player_with_steady_personality.prepare_for_game()

        # Steady personality traits
        assert game_state.confidence_volatility < 0.8
        assert game_state.confidence_recovery_rate > 1.1

        # Veteran experience
        assert game_state.experience_years == 10

        # Narrower bounds (stays even-keeled)
        assert game_state.confidence_ceiling - game_state.confidence_floor < 60

    def test_volatile_rookie_game_prep(self, player_with_volatile_personality):
        """Volatile rookie has extreme game state."""
        game_state = player_with_volatile_personality.prepare_for_game()

        # Volatile personality traits
        assert game_state.confidence_volatility > 1.3
        assert game_state.confidence_recovery_rate < 0.8

        # Limited experience
        assert game_state.experience_years == 2

        # Wider bounds (swings wildly)
        assert game_state.confidence_ceiling - game_state.confidence_floor > 50

    def test_high_morale_boosts_everything(self, player_with_high_morale):
        """High morale player has positive game state."""
        game_state = player_with_high_morale.prepare_for_game()

        assert game_state.starting_confidence > 55.0
        assert game_state.resilience_modifier > 1.0
        assert game_state.current_morale > 80.0

    def test_low_morale_hurts_everything(self, player_with_low_morale):
        """Low morale player has negative game state."""
        game_state = player_with_low_morale.prepare_for_game()

        assert game_state.starting_confidence < 45.0
        assert game_state.resilience_modifier < 0.8
        assert game_state.current_morale < 30.0

    def test_complete_roundtrip(self, player_with_high_morale):
        """Full roundtrip: player → game state → dict → game state."""
        # Generate game state
        original = player_with_high_morale.prepare_for_game()

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = PlayerGameState.from_dict(data)

        # Verify key fields
        assert restored.player_id == original.player_id
        assert restored.starting_confidence == original.starting_confidence
        assert restored.confidence_volatility == original.confidence_volatility
        assert restored.current_morale == original.current_morale
        assert restored.resilience_modifier == original.resilience_modifier
