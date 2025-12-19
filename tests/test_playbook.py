"""Tests for the HC09-style play knowledge system."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from huddle.core.enums import Position
from huddle.core.attributes import PlayerAttributes
from huddle.core.models.player import Player
from huddle.core.playbook import (
    PlayCategory,
    PlayCode,
    MasteryLevel,
    PlayMastery,
    PlayerPlayKnowledge,
    Playbook,
    OFFENSIVE_PLAYS,
    DEFENSIVE_PLAYS,
    ALL_PLAYS,
    get_play,
    get_plays_for_position,
    calculate_learning_rate,
    apply_practice_rep,
    apply_decay,
    apply_game_rep,
    practice_plays,
    get_team_play_readiness,
    estimate_reps_to_learn,
    BASE_LEARNING_RATE,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def smart_player() -> Player:
    """Create a player with high learning attribute."""
    attrs = PlayerAttributes()
    attrs.set("learning", 90)
    attrs.set("awareness", 75)
    return Player(
        id=uuid4(),
        first_name="Smart",
        last_name="Player",
        position=Position.QB,
        attributes=attrs,
        age=24,
    )


@pytest.fixture
def average_player() -> Player:
    """Create a player with average learning attribute."""
    attrs = PlayerAttributes()
    attrs.set("learning", 50)
    attrs.set("awareness", 70)
    return Player(
        id=uuid4(),
        first_name="Average",
        last_name="Player",
        position=Position.RB,
        attributes=attrs,
        age=26,
    )


@pytest.fixture
def slow_learner() -> Player:
    """Create a player with low learning attribute."""
    attrs = PlayerAttributes()
    attrs.set("learning", 30)
    attrs.set("awareness", 65)
    return Player(
        id=uuid4(),
        first_name="Slow",
        last_name="Learner",
        position=Position.WR,
        attributes=attrs,
        age=28,
    )


# =============================================================================
# Play Code Tests
# =============================================================================

class TestPlayCodes:
    """Test play code definitions and registry."""

    def test_offensive_plays_exist(self):
        """Verify offensive plays are defined."""
        assert len(OFFENSIVE_PLAYS) >= 20
        assert "RUN_POWER" in OFFENSIVE_PLAYS
        assert "PASS_MESH" in OFFENSIVE_PLAYS

    def test_defensive_plays_exist(self):
        """Verify defensive plays are defined."""
        assert len(DEFENSIVE_PLAYS) >= 10
        assert "COVER_2" in DEFENSIVE_PLAYS
        assert "COVER_3" in DEFENSIVE_PLAYS

    def test_all_plays_combined(self):
        """ALL_PLAYS should contain both offensive and defensive."""
        assert len(ALL_PLAYS) == len(OFFENSIVE_PLAYS) + len(DEFENSIVE_PLAYS)
        assert "RUN_POWER" in ALL_PLAYS
        assert "COVER_2" in ALL_PLAYS

    def test_get_play(self):
        """Test get_play helper function."""
        play = get_play("RUN_POWER")
        assert play is not None
        assert play.code == "RUN_POWER"
        assert play.category == PlayCategory.RUN

        # Non-existent play
        assert get_play("FAKE_PLAY") is None

    def test_play_has_positions_involved(self):
        """Each play should define which positions are involved."""
        play = get_play("RUN_POWER")
        assert "QB" in play.positions_involved
        assert "RB" in play.positions_involved
        # WR typically not involved in run blocking
        # (depends on implementation)

    def test_play_complexity_range(self):
        """Play complexity should be 1-5."""
        for play in ALL_PLAYS.values():
            assert 1 <= play.complexity <= 5

    def test_get_plays_for_position(self):
        """Test filtering plays by position."""
        qb_plays = get_plays_for_position("QB")
        assert len(qb_plays) > 0
        # QB should be involved in all offensive plays
        for play in qb_plays:
            assert "QB" in play.positions_involved


# =============================================================================
# Play Mastery Tests
# =============================================================================

class TestPlayMastery:
    """Test individual play mastery tracking."""

    def test_default_mastery_is_unlearned(self):
        """New mastery starts as unlearned."""
        mastery = PlayMastery(play_code="RUN_POWER")
        assert mastery.level == MasteryLevel.UNLEARNED
        assert mastery.progress == 0.0
        assert mastery.reps == 0

    def test_execution_modifier_unlearned(self):
        """Unlearned plays have penalty."""
        mastery = PlayMastery(play_code="RUN_POWER")
        assert mastery.get_execution_modifier() == 0.85

    def test_execution_modifier_learned(self):
        """Learned plays have no modifier."""
        mastery = PlayMastery(play_code="RUN_POWER", level=MasteryLevel.LEARNED)
        assert mastery.get_execution_modifier() == 1.0

    def test_execution_modifier_mastered(self):
        """Mastered plays have bonus."""
        mastery = PlayMastery(play_code="RUN_POWER", level=MasteryLevel.MASTERED)
        assert mastery.get_execution_modifier() == 1.10

    def test_serialization(self):
        """Test to_dict and from_dict."""
        mastery = PlayMastery(
            play_code="PASS_MESH",
            level=MasteryLevel.LEARNED,
            progress=0.5,
            reps=15,
            game_reps=3,
        )
        data = mastery.to_dict()
        restored = PlayMastery.from_dict(data)

        assert restored.play_code == mastery.play_code
        assert restored.level == mastery.level
        assert restored.progress == mastery.progress
        assert restored.reps == mastery.reps
        assert restored.game_reps == mastery.game_reps


# =============================================================================
# Player Play Knowledge Tests
# =============================================================================

class TestPlayerPlayKnowledge:
    """Test player's knowledge of multiple plays."""

    def test_empty_knowledge(self):
        """New knowledge starts empty."""
        knowledge = PlayerPlayKnowledge(player_id=uuid4())
        assert len(knowledge.plays) == 0

    def test_get_mastery_creates_if_missing(self):
        """get_mastery creates new mastery if not exists."""
        knowledge = PlayerPlayKnowledge(player_id=uuid4())
        mastery = knowledge.get_mastery("RUN_POWER")

        assert mastery.play_code == "RUN_POWER"
        assert mastery.level == MasteryLevel.UNLEARNED
        assert "RUN_POWER" in knowledge.plays

    def test_get_execution_modifier(self):
        """Test getting execution modifier for a play."""
        knowledge = PlayerPlayKnowledge(player_id=uuid4())

        # Unlearned
        assert knowledge.get_execution_modifier("RUN_POWER") == 0.85

        # Set to learned
        knowledge.plays["RUN_POWER"] = PlayMastery(
            play_code="RUN_POWER",
            level=MasteryLevel.LEARNED
        )
        assert knowledge.get_execution_modifier("RUN_POWER") == 1.0

    def test_serialization(self):
        """Test to_dict and from_dict."""
        player_id = uuid4()
        knowledge = PlayerPlayKnowledge(player_id=player_id)
        knowledge.get_mastery("RUN_POWER")
        knowledge.plays["RUN_POWER"].level = MasteryLevel.LEARNED

        data = knowledge.to_dict()
        restored = PlayerPlayKnowledge.from_dict(data)

        assert restored.player_id == player_id
        assert "RUN_POWER" in restored.plays
        assert restored.plays["RUN_POWER"].level == MasteryLevel.LEARNED


# =============================================================================
# Learning Rate Tests
# =============================================================================

class TestLearningRate:
    """Test learning rate calculation."""

    def test_average_player_baseline(self, average_player):
        """Average player (50 learning) on complexity 3 = base rate."""
        rate = calculate_learning_rate(average_player, 3)
        assert rate == pytest.approx(BASE_LEARNING_RATE, rel=0.01)

    def test_smart_player_learns_faster(self, smart_player, average_player):
        """High learning attribute = faster learning."""
        smart_rate = calculate_learning_rate(smart_player, 3)
        avg_rate = calculate_learning_rate(average_player, 3)

        assert smart_rate > avg_rate
        # 90/50 = 1.8x faster
        assert smart_rate == pytest.approx(avg_rate * 1.8, rel=0.01)

    def test_slow_learner_is_slower(self, slow_learner, average_player):
        """Low learning attribute = slower learning."""
        slow_rate = calculate_learning_rate(slow_learner, 3)
        avg_rate = calculate_learning_rate(average_player, 3)

        assert slow_rate < avg_rate
        # 30/50 = 0.6x rate
        assert slow_rate == pytest.approx(avg_rate * 0.6, rel=0.01)

    def test_simple_plays_learn_faster(self, average_player):
        """Low complexity plays are learned faster."""
        easy_rate = calculate_learning_rate(average_player, 1)
        hard_rate = calculate_learning_rate(average_player, 5)

        assert easy_rate > hard_rate

    def test_complex_plays_learn_slower(self, average_player):
        """High complexity plays take longer to learn."""
        medium_rate = calculate_learning_rate(average_player, 3)
        hard_rate = calculate_learning_rate(average_player, 5)

        assert hard_rate < medium_rate


# =============================================================================
# Practice Rep Tests
# =============================================================================

class TestPracticeRep:
    """Test applying practice reps."""

    def test_practice_increases_progress(self, average_player):
        """Practice reps increase mastery progress."""
        mastery = PlayMastery(play_code="RUN_POWER")
        initial_progress = mastery.progress

        apply_practice_rep(average_player, mastery, 3)

        assert mastery.progress > initial_progress
        assert mastery.reps == 1
        assert mastery.last_practiced is not None

    def test_enough_practice_advances_tier(self, smart_player):
        """Enough reps advances from UNLEARNED to LEARNED."""
        mastery = PlayMastery(play_code="RUN_POWER")

        # Apply many reps until learned
        for _ in range(20):
            advanced = apply_practice_rep(smart_player, mastery, 3)
            if advanced:
                break

        assert mastery.level == MasteryLevel.LEARNED

    def test_can_reach_mastered(self, smart_player):
        """Can progress from LEARNED to MASTERED."""
        mastery = PlayMastery(
            play_code="RUN_POWER",
            level=MasteryLevel.LEARNED,
            progress=0.0
        )

        # Apply many reps until mastered
        for _ in range(30):
            advanced = apply_practice_rep(smart_player, mastery, 3)
            if mastery.level == MasteryLevel.MASTERED:
                break

        assert mastery.level == MasteryLevel.MASTERED

    def test_mastered_stays_mastered(self, average_player):
        """Already mastered plays don't change level."""
        mastery = PlayMastery(
            play_code="RUN_POWER",
            level=MasteryLevel.MASTERED,
            progress=1.0
        )

        advanced = apply_practice_rep(average_player, mastery, 3)

        assert not advanced
        assert mastery.level == MasteryLevel.MASTERED
        assert mastery.reps == 1  # Still counts reps


# =============================================================================
# Decay Tests
# =============================================================================

class TestDecay:
    """Test knowledge decay over time."""

    def test_unlearned_doesnt_decay(self, average_player):
        """Unlearned plays can't decay further."""
        mastery = PlayMastery(play_code="RUN_POWER")

        dropped = apply_decay(average_player, mastery)

        assert not dropped
        assert mastery.level == MasteryLevel.UNLEARNED

    def test_learned_decays_over_time(self, average_player):
        """Learned plays decay if not practiced."""
        past_time = datetime.now() - timedelta(days=14)
        mastery = PlayMastery(
            play_code="RUN_POWER",
            level=MasteryLevel.LEARNED,
            progress=0.5,
            last_practiced=past_time,
        )

        dropped = apply_decay(average_player, mastery)

        assert mastery.progress < 0.5  # Progress decreased

    def test_severe_decay_drops_tier(self, slow_learner):
        """Long neglect can drop player a tier."""
        past_time = datetime.now() - timedelta(days=60)
        mastery = PlayMastery(
            play_code="RUN_POWER",
            level=MasteryLevel.LEARNED,
            progress=0.1,  # Already low
            last_practiced=past_time,
        )

        dropped = apply_decay(slow_learner, mastery)

        # Slow learner forgets faster
        assert dropped or mastery.progress < 0

    def test_game_reps_slow_decay(self, average_player):
        """Game reps reduce decay rate."""
        past_time = datetime.now() - timedelta(days=14)

        # Without game reps
        mastery_no_games = PlayMastery(
            play_code="RUN_POWER",
            level=MasteryLevel.LEARNED,
            progress=0.5,
            last_practiced=past_time,
            game_reps=0,
        )

        # With game reps
        mastery_with_games = PlayMastery(
            play_code="RUN_POWER",
            level=MasteryLevel.LEARNED,
            progress=0.5,
            last_practiced=past_time,
            game_reps=10,
        )

        apply_decay(average_player, mastery_no_games)
        apply_decay(average_player, mastery_with_games)

        # With game reps should have less decay
        assert mastery_with_games.progress > mastery_no_games.progress


# =============================================================================
# Game Rep Tests
# =============================================================================

class TestGameRep:
    """Test recording game reps."""

    def test_game_rep_increments_counter(self):
        """apply_game_rep increments game_reps counter."""
        mastery = PlayMastery(play_code="RUN_POWER")
        assert mastery.game_reps == 0

        apply_game_rep(mastery)
        assert mastery.game_reps == 1

        apply_game_rep(mastery)
        assert mastery.game_reps == 2


# =============================================================================
# Batch Practice Tests
# =============================================================================

class TestPracticePlays:
    """Test practicing multiple plays at once."""

    def test_practice_multiple_plays(self, average_player):
        """Can practice multiple plays in one session."""
        knowledge = PlayerPlayKnowledge(player_id=average_player.id)
        play_codes = ["RUN_POWER", "PASS_MESH", "RUN_INSIDE_ZONE"]

        advancements = practice_plays(
            average_player,
            knowledge,
            play_codes,
            reps_per_play=5,
        )

        # All plays should have been practiced
        for code in play_codes:
            assert code in knowledge.plays
            assert knowledge.plays[code].reps >= 5


# =============================================================================
# Team Play Readiness Tests
# =============================================================================

class TestTeamPlayReadiness:
    """Test calculating team readiness for a play."""

    def test_unlearned_team_low_readiness(self, average_player):
        """Team with unlearned plays has low readiness."""
        knowledge_map = {
            str(average_player.id): PlayerPlayKnowledge(player_id=average_player.id)
        }

        readiness = get_team_play_readiness(
            [average_player],
            "RUN_POWER",
            knowledge_map,
        )

        assert readiness < 1.0  # Below normal

    def test_mastered_team_high_readiness(self, average_player):
        """Team with mastered plays has high readiness."""
        knowledge = PlayerPlayKnowledge(player_id=average_player.id)
        knowledge.plays["RUN_POWER"] = PlayMastery(
            play_code="RUN_POWER",
            level=MasteryLevel.MASTERED,
        )
        knowledge_map = {str(average_player.id): knowledge}

        readiness = get_team_play_readiness(
            [average_player],
            "RUN_POWER",
            knowledge_map,
        )

        assert readiness > 1.0  # Above normal (1.1)


# =============================================================================
# Estimate Reps Tests
# =============================================================================

class TestEstimateReps:
    """Test estimating reps needed to learn."""

    def test_estimate_reps_to_learn(self, average_player, smart_player):
        """Can estimate reps needed to learn a play."""
        avg_reps = estimate_reps_to_learn(average_player, "RUN_POWER")
        smart_reps = estimate_reps_to_learn(smart_player, "RUN_POWER")

        assert avg_reps > 0
        assert smart_reps > 0
        assert smart_reps < avg_reps  # Smart player needs fewer reps


# =============================================================================
# Playbook Tests
# =============================================================================

class TestPlaybook:
    """Test team playbook management."""

    def test_default_playbook_has_plays(self):
        """Default playbook comes with standard plays."""
        playbook = Playbook.default(uuid4())

        assert len(playbook.offensive_plays) > 0
        assert len(playbook.defensive_plays) > 0

    def test_playbook_serialization(self):
        """Test to_dict and from_dict."""
        team_id = uuid4()
        playbook = Playbook.default(team_id)

        data = playbook.to_dict()
        restored = Playbook.from_dict(data)

        assert restored.team_id == team_id
        assert restored.offensive_plays == playbook.offensive_plays
        assert restored.defensive_plays == playbook.defensive_plays
