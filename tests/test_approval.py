"""Tests for the player approval system."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from huddle.core.enums import Position
from huddle.core.attributes import PlayerAttributes
from huddle.core.models.player import Player
from huddle.core.approval import (
    APPROVAL_MOTIVATED,
    APPROVAL_NEUTRAL,
    APPROVAL_UNHAPPY,
    APPROVAL_DISGRUNTLED,
    BASELINE_APPROVAL,
    PERFORMANCE_MOTIVATED,
    PERFORMANCE_NEUTRAL,
    PERFORMANCE_UNHAPPY,
    PERFORMANCE_DISGRUNTLED,
    ApprovalEvent,
    PlayerApproval,
    calculate_approval_change,
    apply_approval_event,
    get_depth_chart_event,
    create_player_approval,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def motivated_player() -> Player:
    """Create a highly motivated player (80+ approval)."""
    attrs = PlayerAttributes()
    attrs.set("speed", 85)
    player = Player(
        id=uuid4(),
        first_name="Motivated",
        last_name="Player",
        position=Position.WR,
        attributes=attrs,
        age=25,
    )
    player.approval = PlayerApproval(
        player_id=player.id,
        approval=85.0,
    )
    return player


@pytest.fixture
def neutral_player() -> Player:
    """Create a neutral player (50 approval)."""
    attrs = PlayerAttributes()
    attrs.set("speed", 80)
    player = Player(
        id=uuid4(),
        first_name="Neutral",
        last_name="Player",
        position=Position.RB,
        attributes=attrs,
        age=26,
    )
    player.approval = PlayerApproval(
        player_id=player.id,
        approval=50.0,
    )
    return player


@pytest.fixture
def unhappy_player() -> Player:
    """Create an unhappy player (35 approval)."""
    attrs = PlayerAttributes()
    attrs.set("speed", 88)
    player = Player(
        id=uuid4(),
        first_name="Unhappy",
        last_name="Player",
        position=Position.CB,
        attributes=attrs,
        age=28,
    )
    player.approval = PlayerApproval(
        player_id=player.id,
        approval=35.0,
    )
    return player


@pytest.fixture
def disgruntled_player() -> Player:
    """Create a disgruntled player (20 approval)."""
    attrs = PlayerAttributes()
    attrs.set("speed", 90)
    player = Player(
        id=uuid4(),
        first_name="Disgruntled",
        last_name="Player",
        position=Position.DE,
        attributes=attrs,
        age=30,
    )
    player.approval = PlayerApproval(
        player_id=player.id,
        approval=20.0,
    )
    return player


@pytest.fixture
def player_with_personality() -> Player:
    """Create a player with personality traits."""
    from huddle.core.personality import PersonalityProfile, ArchetypeType, Trait

    attrs = PlayerAttributes()
    attrs.set("speed", 82)
    player = Player(
        id=uuid4(),
        first_name="Personality",
        last_name="Test",
        position=Position.QB,
        attributes=attrs,
        age=24,
    )
    # Create a sensitive personality (HEADLINER is dramatic/impulsive)
    player.personality = PersonalityProfile(
        archetype=ArchetypeType.HEADLINER,
        traits={
            Trait.SENSITIVE: 0.9,
            Trait.AMBITIOUS: 0.8,
            Trait.COMPETITIVE: 0.7,
            Trait.DRAMATIC: 0.85,
        }
    )
    player.approval = PlayerApproval(player_id=player.id)
    return player


# =============================================================================
# PlayerApproval Basic Tests
# =============================================================================

class TestPlayerApproval:
    """Test PlayerApproval dataclass."""

    def test_default_approval_is_baseline(self):
        """New approval starts at baseline (50)."""
        approval = PlayerApproval(player_id=uuid4())
        assert approval.approval == BASELINE_APPROVAL
        assert approval.approval == 50.0

    def test_approval_clamped_on_init(self):
        """Approval is clamped to 0-100 on initialization."""
        approval_low = PlayerApproval(player_id=uuid4(), approval=-10.0)
        assert approval_low.approval == 0.0

        approval_high = PlayerApproval(player_id=uuid4(), approval=150.0)
        assert approval_high.approval == 100.0

    def test_default_trend_is_zero(self):
        """New approval has no trend."""
        approval = PlayerApproval(player_id=uuid4())
        assert approval.trend == 0.0

    def test_default_grievances_empty(self):
        """New approval has no grievances."""
        approval = PlayerApproval(player_id=uuid4())
        assert approval.grievances == []


# =============================================================================
# Performance Modifier Tests
# =============================================================================

class TestPerformanceModifier:
    """Test performance modifier based on approval."""

    def test_motivated_gets_bonus(self, motivated_player):
        """Motivated players (80+) get +5%."""
        modifier = motivated_player.get_performance_modifier()
        assert modifier == PERFORMANCE_MOTIVATED
        assert modifier == 1.05

    def test_neutral_no_modifier(self, neutral_player):
        """Neutral players (50-79) get no modifier."""
        modifier = neutral_player.get_performance_modifier()
        assert modifier == PERFORMANCE_NEUTRAL
        assert modifier == 1.0

    def test_unhappy_gets_penalty(self, unhappy_player):
        """Unhappy players (30-49) get -3%."""
        modifier = unhappy_player.get_performance_modifier()
        assert modifier == PERFORMANCE_UNHAPPY
        assert modifier == 0.97

    def test_disgruntled_gets_heavy_penalty(self, disgruntled_player):
        """Disgruntled players (<30) get -8%."""
        modifier = disgruntled_player.get_performance_modifier()
        assert modifier == PERFORMANCE_DISGRUNTLED
        assert modifier == 0.92

    def test_player_without_approval_returns_default(self):
        """Player without approval tracking returns 1.0."""
        player = Player(position=Position.WR)
        assert player.approval is None
        assert player.get_performance_modifier() == 1.0


# =============================================================================
# Mood Description Tests
# =============================================================================

class TestMoodDescription:
    """Test mood descriptions at different approval levels."""

    def test_motivated_mood(self, motivated_player):
        """High approval = motivated."""
        assert motivated_player.approval.get_mood_description() == "Motivated"

    def test_content_mood(self):
        """60-79 approval = content."""
        approval = PlayerApproval(player_id=uuid4(), approval=65.0)
        assert approval.get_mood_description() == "Content"

    def test_neutral_mood(self, neutral_player):
        """50-59 approval = neutral."""
        assert neutral_player.approval.get_mood_description() == "Neutral"

    def test_unhappy_mood(self, unhappy_player):
        """40-49 approval = unhappy."""
        approval = PlayerApproval(player_id=uuid4(), approval=45.0)
        assert approval.get_mood_description() == "Unhappy"

    def test_frustrated_mood(self):
        """25-39 approval = frustrated."""
        approval = PlayerApproval(player_id=uuid4(), approval=30.0)
        assert approval.get_mood_description() == "Frustrated"

    def test_disgruntled_mood(self, disgruntled_player):
        """<25 approval = disgruntled."""
        assert disgruntled_player.approval.get_mood_description() == "Disgruntled"


# =============================================================================
# Trade & Holdout Risk Tests
# =============================================================================

class TestTradeAndHoldout:
    """Test trade candidate and holdout risk flags."""

    def test_motivated_not_trade_candidate(self, motivated_player):
        """Motivated players don't want trades."""
        assert motivated_player.is_unhappy() is False
        assert motivated_player.approval.is_trade_candidate() is False

    def test_unhappy_is_trade_candidate(self, unhappy_player):
        """Unhappy players may want trades."""
        assert unhappy_player.is_unhappy() is True
        assert unhappy_player.approval.is_trade_candidate() is True

    def test_unhappy_not_holdout_risk(self, unhappy_player):
        """Unhappy players won't hold out (too high)."""
        assert unhappy_player.approval.is_holdout_risk() is False

    def test_disgruntled_is_holdout_risk(self, disgruntled_player):
        """Disgruntled players may hold out."""
        assert disgruntled_player.is_disgruntled() is True
        assert disgruntled_player.approval.is_holdout_risk() is True


# =============================================================================
# Apply Change Tests
# =============================================================================

class TestApplyChange:
    """Test applying approval changes."""

    def test_positive_change(self, neutral_player):
        """Positive changes increase approval."""
        initial = neutral_player.approval.approval
        neutral_player.approval.apply_change(10.0)
        assert neutral_player.approval.approval == initial + 10.0

    def test_negative_change(self, neutral_player):
        """Negative changes decrease approval."""
        initial = neutral_player.approval.approval
        neutral_player.approval.apply_change(-15.0)
        assert neutral_player.approval.approval == initial - 15.0

    def test_change_capped_at_100(self, motivated_player):
        """Approval can't exceed 100."""
        motivated_player.approval.apply_change(50.0)
        assert motivated_player.approval.approval == 100.0

    def test_change_capped_at_0(self, disgruntled_player):
        """Approval can't go below 0."""
        disgruntled_player.approval.apply_change(-50.0)
        assert disgruntled_player.approval.approval == 0.0

    def test_change_updates_trend(self, neutral_player):
        """Changes update the trend tracker."""
        neutral_player.approval.apply_change(10.0)
        assert neutral_player.approval.trend > 0  # Positive trend

        neutral_player.approval.apply_change(-15.0)
        # Trend should shift negative (exponential moving average)
        assert neutral_player.approval.trend < 10.0  # No longer as positive

    def test_negative_change_records_grievance(self, neutral_player):
        """Large negative changes record grievances."""
        neutral_player.approval.apply_change(-15.0, reason="Benched")
        assert "Benched" in neutral_player.approval.grievances

    def test_small_negative_no_grievance(self, neutral_player):
        """Small negative changes don't record grievances."""
        neutral_player.approval.apply_change(-5.0, reason="Minor issue")
        assert "Minor issue" not in neutral_player.approval.grievances

    def test_grievances_limited_to_five(self, neutral_player):
        """Only the last 5 grievances are kept."""
        for i in range(10):
            neutral_player.approval.apply_change(-15.0, reason=f"Issue {i}")
        assert len(neutral_player.approval.grievances) == 5
        assert "Issue 9" in neutral_player.approval.grievances
        assert "Issue 0" not in neutral_player.approval.grievances


# =============================================================================
# Weekly Drift Tests
# =============================================================================

class TestWeeklyDrift:
    """Test weekly approval drift toward baseline."""

    def test_high_approval_drifts_down(self, motivated_player):
        """High approval slowly drifts down."""
        initial = motivated_player.approval.approval
        motivated_player.approval.apply_weekly_drift()
        assert motivated_player.approval.approval < initial

    def test_low_approval_drifts_up(self, disgruntled_player):
        """Low approval slowly drifts up."""
        initial = disgruntled_player.approval.approval
        disgruntled_player.approval.apply_weekly_drift()
        assert disgruntled_player.approval.approval > initial

    def test_baseline_stays_stable(self, neutral_player):
        """Baseline approval has minimal drift."""
        initial = neutral_player.approval.approval
        neutral_player.approval.apply_weekly_drift()
        # Should be very close to 50
        assert abs(neutral_player.approval.approval - 50.0) < 1.0

    def test_winning_helps_drift(self, unhappy_player):
        """Winning team gets positive drift boost."""
        unhappy_player.approval.approval = 40.0
        initial = unhappy_player.approval.approval
        unhappy_player.approval.apply_weekly_drift(team_winning=True)
        new_approval = unhappy_player.approval.approval

        # Reset and compare to neutral drift
        unhappy_player.approval.approval = 40.0
        unhappy_player.approval.apply_weekly_drift(team_winning=False)
        neutral_drift = unhappy_player.approval.approval

        # Winning should result in higher approval
        assert new_approval > neutral_drift

    def test_losing_hurts_drift(self, motivated_player):
        """Losing team gets negative drift."""
        initial = motivated_player.approval.approval
        motivated_player.approval.apply_weekly_drift(team_losing=True)
        assert motivated_player.approval.approval < initial - 1.0  # Extra penalty


# =============================================================================
# Depth Chart Event Tests
# =============================================================================

class TestDepthChartEvent:
    """Test depth chart change event detection."""

    def test_no_change_no_event(self):
        """Same depth = no event."""
        event = get_depth_chart_event(2, 2)
        assert event is None

    def test_promoted_to_starter(self):
        """Backup to starter = PROMOTED_STARTER."""
        event = get_depth_chart_event(2, 1)
        assert event == ApprovalEvent.PROMOTED_STARTER

    def test_promoted_backup(self):
        """Third string to backup = PROMOTED_BACKUP."""
        event = get_depth_chart_event(3, 2)
        assert event == ApprovalEvent.PROMOTED_BACKUP

    def test_demoted_from_starter(self):
        """Starter to backup = DEMOTED_BACKUP."""
        event = get_depth_chart_event(1, 2)
        assert event == ApprovalEvent.DEMOTED_BACKUP

    def test_demoted_deep(self):
        """Demoted to 3rd string or worse = DEMOTED_DEEP."""
        event = get_depth_chart_event(2, 3)
        assert event == ApprovalEvent.DEMOTED_DEEP


# =============================================================================
# Calculate Approval Change Tests
# =============================================================================

class TestCalculateApprovalChange:
    """Test approval change calculation with personality modifiers."""

    def test_base_impact_without_personality(self, neutral_player):
        """Without personality, base impact is used."""
        neutral_player.personality = None
        change = calculate_approval_change(neutral_player, ApprovalEvent.PROMOTED_STARTER)
        # Base impact for PROMOTED_STARTER is +15
        assert change == pytest.approx(15.0, rel=0.01)

    def test_sensitive_player_reacts_more(self, player_with_personality):
        """Sensitive players react more strongly to negative events."""
        # Demotion with sensitive personality
        change = calculate_approval_change(player_with_personality, ApprovalEvent.DEMOTED_BACKUP)
        # Base is -12, sensitive should amplify it
        assert change < -12.0  # More negative

    def test_veteran_demotion_hurts_more(self, unhappy_player):
        """Veterans take demotions harder."""
        unhappy_player.age = 30
        unhappy_player.personality = None  # Remove personality for clean test
        change = calculate_approval_change(unhappy_player, ApprovalEvent.DEMOTED_BACKUP)
        # Base is -12, veteran multiplier is 1.3
        assert change == pytest.approx(-12.0 * 1.3, rel=0.01)


# =============================================================================
# Apply Approval Event Tests
# =============================================================================

class TestApplyApprovalEvent:
    """Test applying approval events to players."""

    def test_creates_approval_if_missing(self):
        """Creates PlayerApproval if player doesn't have one."""
        player = Player(position=Position.WR)
        assert player.approval is None

        apply_approval_event(player, ApprovalEvent.WIN)

        assert player.approval is not None
        assert player.approval.approval != 50.0  # Changed from default

    def test_promotion_increases_approval(self, neutral_player):
        """Promotion events increase approval."""
        initial = neutral_player.approval.approval
        apply_approval_event(neutral_player, ApprovalEvent.PROMOTED_STARTER)
        assert neutral_player.approval.approval > initial

    def test_demotion_decreases_approval(self, neutral_player):
        """Demotion events decrease approval."""
        initial = neutral_player.approval.approval
        apply_approval_event(neutral_player, ApprovalEvent.DEMOTED_BACKUP)
        assert neutral_player.approval.approval < initial

    def test_win_helps_approval(self, neutral_player):
        """Winning increases approval."""
        initial = neutral_player.approval.approval
        apply_approval_event(neutral_player, ApprovalEvent.WIN)
        assert neutral_player.approval.approval > initial

    def test_loss_hurts_approval(self, neutral_player):
        """Losing decreases approval."""
        initial = neutral_player.approval.approval
        apply_approval_event(neutral_player, ApprovalEvent.LOSS)
        assert neutral_player.approval.approval < initial


# =============================================================================
# Serialization Tests
# =============================================================================

class TestSerialization:
    """Test to_dict and from_dict."""

    def test_to_dict(self, motivated_player):
        """Test conversion to dictionary."""
        motivated_player.approval.grievances = ["Benched", "Cut from play"]
        data = motivated_player.approval.to_dict()

        assert data["player_id"] == str(motivated_player.id)
        assert data["approval"] == 85.0
        assert data["grievances"] == ["Benched", "Cut from play"]

    def test_from_dict(self, motivated_player):
        """Test restoration from dictionary."""
        data = motivated_player.approval.to_dict()
        restored = PlayerApproval.from_dict(data)

        assert restored.player_id == motivated_player.approval.player_id
        assert restored.approval == motivated_player.approval.approval
        assert restored.trend == motivated_player.approval.trend

    def test_round_trip(self, unhappy_player):
        """Test full serialization round trip."""
        unhappy_player.approval.apply_change(-5.0, reason="Lost starting job")
        data = unhappy_player.approval.to_dict()
        restored = PlayerApproval.from_dict(data)

        assert restored.get_mood_description() == unhappy_player.approval.get_mood_description()
        assert restored.is_trade_candidate() == unhappy_player.approval.is_trade_candidate()

    def test_player_serialization_includes_approval(self, neutral_player):
        """Player serialization includes approval."""
        data = neutral_player.to_dict()
        assert "approval" in data

        restored = Player.from_dict(data)
        assert restored.approval is not None
        assert restored.approval.approval == neutral_player.approval.approval


# =============================================================================
# Player Integration Tests
# =============================================================================

class TestPlayerIntegration:
    """Test Player class integration with approval."""

    def test_player_get_approval_rating(self, motivated_player):
        """Player.get_approval_rating() works."""
        assert motivated_player.get_approval_rating() == 85.0

    def test_player_without_approval_defaults(self):
        """Player without approval returns default rating."""
        player = Player(position=Position.QB)
        assert player.get_approval_rating() == 50.0

    def test_player_is_unhappy(self, unhappy_player):
        """Player.is_unhappy() works."""
        assert unhappy_player.is_unhappy() is True

    def test_player_is_disgruntled(self, disgruntled_player):
        """Player.is_disgruntled() works."""
        assert disgruntled_player.is_disgruntled() is True


# =============================================================================
# Create Player Approval Tests
# =============================================================================

class TestCreatePlayerApproval:
    """Test create_player_approval helper."""

    def test_creates_with_default_approval(self):
        """Creates approval with default baseline."""
        player_id = uuid4()
        approval = create_player_approval(player_id)

        assert approval.player_id == player_id
        assert approval.approval == BASELINE_APPROVAL
        assert approval.last_updated is not None

    def test_creates_with_custom_approval(self):
        """Creates approval with custom initial value."""
        player_id = uuid4()
        approval = create_player_approval(player_id, initial_approval=75.0)

        assert approval.approval == 75.0


# =============================================================================
# Post-Game Morale Event Tests
# =============================================================================

class TestGamePerformanceEvents:
    """Test game performance events and their impacts."""

    def test_big_play_hero_positive_impact(self, neutral_player):
        """BIG_PLAY_HERO has positive impact."""
        from huddle.core.approval import EVENT_IMPACTS
        assert EVENT_IMPACTS[ApprovalEvent.BIG_PLAY_HERO] > 0

        initial = neutral_player.approval.approval
        apply_approval_event(neutral_player, ApprovalEvent.BIG_PLAY_HERO)
        assert neutral_player.approval.approval > initial

    def test_costly_turnover_negative_impact(self, neutral_player):
        """COSTLY_TURNOVER has negative impact."""
        from huddle.core.approval import EVENT_IMPACTS
        assert EVENT_IMPACTS[ApprovalEvent.COSTLY_TURNOVER] < 0

        initial = neutral_player.approval.approval
        apply_approval_event(neutral_player, ApprovalEvent.COSTLY_TURNOVER)
        assert neutral_player.approval.approval < initial

    def test_game_winning_drive_is_biggest_positive(self, neutral_player):
        """GAME_WINNING_DRIVE is the biggest positive individual event."""
        from huddle.core.approval import EVENT_IMPACTS, GAME_PERFORMANCE_EVENTS

        game_perf_impacts = {
            e: v for e, v in EVENT_IMPACTS.items()
            if e in GAME_PERFORMANCE_EVENTS
        }
        max_positive = max(v for v in game_perf_impacts.values())
        assert EVENT_IMPACTS[ApprovalEvent.GAME_WINNING_DRIVE] == max_positive

    def test_all_game_events_have_impacts(self):
        """All game performance events have defined impacts."""
        from huddle.core.approval import EVENT_IMPACTS, GAME_PERFORMANCE_EVENTS

        for event in GAME_PERFORMANCE_EVENTS:
            assert event in EVENT_IMPACTS
            assert EVENT_IMPACTS[event] != 0


class TestDramaticPersonalityModifier:
    """Test DRAMATIC personality affects game events more strongly."""

    @pytest.fixture
    def dramatic_player(self) -> Player:
        """Create a player with high DRAMATIC trait."""
        from huddle.core.personality import PersonalityProfile, ArchetypeType, Trait

        attrs = PlayerAttributes()
        player = Player(
            id=uuid4(),
            first_name="Drama",
            last_name="Queen",
            position=Position.WR,
            attributes=attrs,
            age=25,
        )
        player.personality = PersonalityProfile(
            archetype=ArchetypeType.HEADLINER,
            traits={
                Trait.DRAMATIC: 0.95,  # Very dramatic
            }
        )
        player.approval = PlayerApproval(player_id=player.id)
        return player

    @pytest.fixture
    def stoic_player(self) -> Player:
        """Create a player with high LEVEL_HEADED trait."""
        from huddle.core.personality import PersonalityProfile, ArchetypeType, Trait

        attrs = PlayerAttributes()
        player = Player(
            id=uuid4(),
            first_name="Cool",
            last_name="Cucumber",
            position=Position.MLB,  # Middle linebacker
            attributes=attrs,
            age=27,
        )
        player.personality = PersonalityProfile(
            archetype=ArchetypeType.STOIC,
            traits={
                Trait.LEVEL_HEADED: 0.95,  # Very steady
            }
        )
        player.approval = PlayerApproval(player_id=player.id)
        return player

    def test_dramatic_player_feels_positive_more(self, dramatic_player, neutral_player):
        """DRAMATIC players feel positive game events more intensely."""
        neutral_player.personality = None  # No personality

        dramatic_change = calculate_approval_change(
            dramatic_player, ApprovalEvent.BIG_PLAY_HERO
        )
        neutral_change = calculate_approval_change(
            neutral_player, ApprovalEvent.BIG_PLAY_HERO
        )

        # Dramatic player should feel it more strongly
        assert abs(dramatic_change) > abs(neutral_change)

    def test_dramatic_player_feels_negative_more(self, dramatic_player, neutral_player):
        """DRAMATIC players feel negative game events more intensely."""
        neutral_player.personality = None

        dramatic_change = calculate_approval_change(
            dramatic_player, ApprovalEvent.COSTLY_TURNOVER
        )
        neutral_change = calculate_approval_change(
            neutral_player, ApprovalEvent.COSTLY_TURNOVER
        )

        # Dramatic player should feel it more strongly (more negative)
        assert dramatic_change < neutral_change

    def test_level_headed_player_dampened(self, stoic_player, neutral_player):
        """LEVEL_HEADED players have dampened reactions to game events."""
        neutral_player.personality = None

        stoic_change = calculate_approval_change(
            stoic_player, ApprovalEvent.COSTLY_TURNOVER
        )
        neutral_change = calculate_approval_change(
            neutral_player, ApprovalEvent.COSTLY_TURNOVER
        )

        # Stoic player should react less strongly
        assert abs(stoic_change) < abs(neutral_change)


class TestDetermineGameAftermathEvent:
    """Test determine_game_aftermath_event helper."""

    def test_close_win_returns_win(self):
        """Close win (< 7 pts) returns basic WIN."""
        from huddle.core.approval import determine_game_aftermath_event

        event = determine_game_aftermath_event(score_diff=3)
        assert event == ApprovalEvent.WIN

    def test_moderate_win_returns_big_win(self):
        """Moderate win (7-20 pts) returns BIG_WIN."""
        from huddle.core.approval import determine_game_aftermath_event

        event = determine_game_aftermath_event(score_diff=14)
        assert event == ApprovalEvent.BIG_WIN

    def test_blowout_win_returns_blowout(self):
        """Blowout win (21+ pts) returns BLOWOUT_WIN."""
        from huddle.core.approval import determine_game_aftermath_event

        event = determine_game_aftermath_event(score_diff=28)
        assert event == ApprovalEvent.BLOWOUT_WIN

    def test_close_loss_returns_loss(self):
        """Close loss (< 7 pts) returns basic LOSS."""
        from huddle.core.approval import determine_game_aftermath_event

        event = determine_game_aftermath_event(score_diff=-3)
        assert event == ApprovalEvent.LOSS

    def test_moderate_loss_returns_tough_loss(self):
        """Moderate loss (7-20 pts) returns TOUGH_LOSS."""
        from huddle.core.approval import determine_game_aftermath_event

        event = determine_game_aftermath_event(score_diff=-14)
        assert event == ApprovalEvent.TOUGH_LOSS

    def test_blowout_loss_returns_blowout(self):
        """Blowout loss (21+ pts) returns BLOWOUT_LOSS."""
        from huddle.core.approval import determine_game_aftermath_event

        event = determine_game_aftermath_event(score_diff=-28)
        assert event == ApprovalEvent.BLOWOUT_LOSS

    def test_playoff_win_returns_advancement(self):
        """Playoff win returns PLAYOFF_ADVANCEMENT."""
        from huddle.core.approval import determine_game_aftermath_event

        event = determine_game_aftermath_event(score_diff=7, is_playoff=True)
        assert event == ApprovalEvent.PLAYOFF_ADVANCEMENT

    def test_elimination_overrides_score(self):
        """Elimination flag overrides any score differential."""
        from huddle.core.approval import determine_game_aftermath_event

        event = determine_game_aftermath_event(score_diff=-3, is_elimination=True)
        assert event == ApprovalEvent.PLAYOFF_ELIMINATION

    def test_division_clinch_overrides_regular_win(self):
        """Division clinch flag overrides regular win."""
        from huddle.core.approval import determine_game_aftermath_event

        event = determine_game_aftermath_event(score_diff=14, is_division_clinch=True)
        assert event == ApprovalEvent.DIVISION_CLINCH


class TestApplyPostGameMorale:
    """Test apply_post_game_morale helper."""

    def test_win_improves_all_approvals(self, neutral_player, motivated_player):
        """Winning improves all player approvals."""
        from huddle.core.approval import apply_post_game_morale

        players = [neutral_player, motivated_player]
        initial_neutral = neutral_player.approval.approval
        initial_motivated = motivated_player.approval.approval

        apply_post_game_morale(players, score_diff=14)

        assert neutral_player.approval.approval > initial_neutral
        assert motivated_player.approval.approval >= initial_motivated  # May cap at 100

    def test_loss_hurts_all_approvals(self, neutral_player, motivated_player):
        """Losing hurts all player approvals."""
        from huddle.core.approval import apply_post_game_morale

        players = [neutral_player, motivated_player]
        initial_neutral = neutral_player.approval.approval
        initial_motivated = motivated_player.approval.approval

        apply_post_game_morale(players, score_diff=-14)

        assert neutral_player.approval.approval < initial_neutral
        assert motivated_player.approval.approval < initial_motivated

    def test_individual_performances_applied(self, neutral_player):
        """Individual performances are applied on top of team event."""
        from huddle.core.approval import apply_post_game_morale

        # Create second player at same approval level for fair comparison
        attrs = PlayerAttributes()
        comparison_player = Player(
            id=uuid4(),
            first_name="Compare",
            last_name="Player",
            position=Position.RB,
            attributes=attrs,
            age=25,
        )
        comparison_player.approval = PlayerApproval(
            player_id=comparison_player.id,
            approval=50.0,  # Same as neutral_player
        )

        players = [neutral_player, comparison_player]

        # Even in a loss, a big play hero should get a bump
        apply_post_game_morale(
            players,
            score_diff=-7,  # Loss (TOUGH_LOSS = -7)
            individual_performances={
                neutral_player.id: ApprovalEvent.BIG_PLAY_HERO  # +12 bonus
            }
        )

        # Neutral player gets loss penalty PLUS hero bonus
        # Comparison player only gets loss penalty
        # So neutral player should be higher
        assert neutral_player.approval.approval > comparison_player.approval.approval

    def test_returns_final_approval_values(self, neutral_player):
        """Returns dict of player_id -> final approval."""
        from huddle.core.approval import apply_post_game_morale

        players = [neutral_player]
        results = apply_post_game_morale(players, score_diff=7)

        assert neutral_player.id in results
        assert results[neutral_player.id] == neutral_player.approval.approval


class TestGetIndividualPerformanceEvents:
    """Test get_individual_performance_events helper."""

    def test_touchdown_gets_celebration(self):
        """Scoring a touchdown gets TD_CELEBRATION event."""
        from huddle.core.approval import get_individual_performance_events

        player_id = uuid4()
        stats = {player_id: {"touchdowns": 1}}
        events = get_individual_performance_events(stats)

        assert player_id in events
        assert ApprovalEvent.TD_CELEBRATION in events[player_id]

    def test_multiple_tds_gets_hero(self):
        """3+ touchdowns gets both CELEBRATION and HERO."""
        from huddle.core.approval import get_individual_performance_events

        player_id = uuid4()
        stats = {player_id: {"touchdowns": 3}}
        events = get_individual_performance_events(stats)

        assert ApprovalEvent.TD_CELEBRATION in events[player_id]
        assert ApprovalEvent.BIG_PLAY_HERO in events[player_id]

    def test_turnover_gets_costly(self):
        """Turnover gets COSTLY_TURNOVER event."""
        from huddle.core.approval import get_individual_performance_events

        player_id = uuid4()
        stats = {player_id: {"turnovers": 1}}
        events = get_individual_performance_events(stats)

        assert ApprovalEvent.COSTLY_TURNOVER in events[player_id]

    def test_game_winning_drive_gets_event(self):
        """Game winning drive flag gets event."""
        from huddle.core.approval import get_individual_performance_events

        player_id = uuid4()
        stats = {player_id: {"game_winning_drive": True}}
        events = get_individual_performance_events(stats)

        assert ApprovalEvent.GAME_WINNING_DRIVE in events[player_id]

    def test_drops_get_critical_drop(self):
        """Drops get CRITICAL_DROP event."""
        from huddle.core.approval import get_individual_performance_events

        player_id = uuid4()
        stats = {player_id: {"drops": 1}}
        events = get_individual_performance_events(stats)

        assert ApprovalEvent.CRITICAL_DROP in events[player_id]

    def test_blown_assignments_get_event(self):
        """Multiple blown plays get BLOWN_ASSIGNMENT event."""
        from huddle.core.approval import get_individual_performance_events

        player_id = uuid4()
        stats = {player_id: {"blown_plays": 2}}
        events = get_individual_performance_events(stats)

        assert ApprovalEvent.BLOWN_ASSIGNMENT in events[player_id]

    def test_no_stats_no_events(self):
        """Player with no notable stats gets no events."""
        from huddle.core.approval import get_individual_performance_events

        player_id = uuid4()
        stats = {player_id: {"touchdowns": 0, "turnovers": 0}}
        events = get_individual_performance_events(stats)

        assert player_id not in events


class TestTeamWideEvents:
    """Test team-wide event constants."""

    def test_team_wide_events_defined(self):
        """All team-wide events are defined."""
        from huddle.core.approval import TEAM_WIDE_EVENTS

        expected_events = {
            ApprovalEvent.BIG_WIN,
            ApprovalEvent.TOUGH_LOSS,
            ApprovalEvent.PLAYOFF_ELIMINATION,
            ApprovalEvent.PLAYOFF_ADVANCEMENT,
            ApprovalEvent.DIVISION_CLINCH,
            ApprovalEvent.BLOWOUT_WIN,
            ApprovalEvent.BLOWOUT_LOSS,
        }

        assert TEAM_WIDE_EVENTS == expected_events

    def test_game_performance_events_are_individual(self):
        """Game performance events are separate from team-wide."""
        from huddle.core.approval import GAME_PERFORMANCE_EVENTS, TEAM_WIDE_EVENTS

        # No overlap between individual and team events
        assert GAME_PERFORMANCE_EVENTS.isdisjoint(TEAM_WIDE_EVENTS)
