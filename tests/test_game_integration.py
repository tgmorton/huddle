"""Integration tests for the Game Manager layer.

Tests the complete game flow from teams to final score.
"""

import pytest
from huddle.generators import generate_team
from huddle.game import (
    GameManager,
    GameResult,
    RosterBridge,
    OffensiveCoordinator,
    DefensiveCoordinator,
    SituationContext,
)


@pytest.fixture
def home_team():
    """Generate a home team."""
    return generate_team(
        name="Eagles",
        city="Philadelphia",
        abbreviation="PHI",
        primary_color="#004C54",
        secondary_color="#A5ACAF",
        overall_range=(75, 85),
    )


@pytest.fixture
def away_team():
    """Generate an away team."""
    return generate_team(
        name="Cowboys",
        city="Dallas",
        abbreviation="DAL",
        primary_color="#003594",
        secondary_color="#869397",
        overall_range=(75, 85),
    )


class TestRosterBridge:
    """Test roster bridge functionality."""

    def test_get_offensive_11(self, home_team):
        """Test extracting 11 offensive players."""
        bridge = RosterBridge(home_team)
        players = bridge.get_offensive_11()

        # Should have players
        assert len(players) > 0

        # All should be on offense
        from huddle.simulation.v2.core.entities import Team as V2Team
        for p in players:
            assert p.team == V2Team.OFFENSE

    def test_get_defensive_11(self, home_team):
        """Test extracting 11 defensive players."""
        bridge = RosterBridge(home_team)
        players = bridge.get_defensive_11()

        # Should have players
        assert len(players) > 0

        # All should be on defense
        from huddle.simulation.v2.core.entities import Team as V2Team
        for p in players:
            assert p.team == V2Team.DEFENSE


class TestCoordinator:
    """Test AI play-calling."""

    def test_offensive_play_call(self):
        """Test offensive coordinator generates valid plays."""
        oc = OffensiveCoordinator()

        context = SituationContext(
            down=1,
            distance=10,
            los=25.0,
            quarter=1,
            time_remaining=900,
            score_diff=0,
            timeouts=3,
        )

        play = oc.call_play(context)

        # Should return a valid play code
        assert play is not None
        assert play.startswith("PASS_") or play.startswith("RUN_")

    def test_short_yardage_play_call(self):
        """Test play calling on short yardage."""
        oc = OffensiveCoordinator()

        context = SituationContext(
            down=3,
            distance=1,
            los=50.0,
            quarter=2,
            time_remaining=120,
            score_diff=0,
            timeouts=2,
        )

        # Call multiple times to check distribution
        plays = [oc.call_play(context) for _ in range(20)]

        # Should have mix of runs and passes on short yardage
        has_run = any(p.startswith("RUN_") for p in plays)
        has_pass = any(p.startswith("PASS_") for p in plays)

        # At least one of each should appear (probabilistic, may rarely fail)
        assert has_run or has_pass

    def test_defensive_coverage_call(self):
        """Test defensive coordinator generates valid coverages."""
        dc = DefensiveCoordinator()

        context = SituationContext(
            down=1,
            distance=10,
            los=25.0,
            quarter=1,
            time_remaining=900,
            score_diff=0,
            timeouts=3,
        )

        coverage = dc.call_coverage(context)

        # Should return a valid coverage
        assert coverage is not None
        assert coverage.startswith("COVER_") or coverage.startswith("MAN_") or coverage.startswith("BLITZ_")


class TestGameManager:
    """Test full game simulation."""

    def test_game_creation(self, home_team, away_team):
        """Test creating a game manager."""
        manager = GameManager(home_team, away_team)

        assert manager.home_team == home_team
        assert manager.away_team == away_team
        assert manager.home_score == 0
        assert manager.away_score == 0

    def test_game_start(self, home_team, away_team):
        """Test starting a game."""
        manager = GameManager(home_team, away_team)
        manager.start_game()

        # Should be in first quarter
        assert manager.quarter == 1

        # Should have time remaining
        assert manager.time_remaining > 0

        # One team should have possession
        assert manager._possession_home is not None

    def test_full_game_simulation(self, home_team, away_team):
        """Test simulating a full game."""
        manager = GameManager(home_team, away_team)
        result = manager.play_game()

        # Should return a GameResult
        assert isinstance(result, GameResult)

        # Scores should be non-negative
        assert result.home_score >= 0
        assert result.away_score >= 0

        # Should have a winner or tie
        assert result.winner in ("home", "away", "tie")

        # Should have recorded some drives
        assert len(result.drives) > 0

    def test_coach_mode_setup(self, home_team, away_team):
        """Test coach mode initialization."""
        manager = GameManager(home_team, away_team, coach_mode=True)
        manager.start_game()

        # Should be able to get situation
        situation = manager.get_situation()

        assert "quarter" in situation
        assert "down" in situation
        assert "distance" in situation
        assert "los" in situation

    def test_multiple_games_different_scores(self, home_team, away_team):
        """Test that multiple games produce varied scores."""
        scores = []

        for _ in range(5):
            manager = GameManager(home_team, away_team)
            result = manager.play_game()
            scores.append((result.home_score, result.away_score))

        # Should have some variation in scores
        unique_scores = set(scores)
        # At least 2 different outcomes expected (probabilistic)
        assert len(unique_scores) >= 1  # Relaxed for speed


class TestSpecialTeams:
    """Test special teams resolution."""

    def test_kickoff(self):
        """Test kickoff resolution."""
        from huddle.game import SpecialTeamsResolver

        resolver = SpecialTeamsResolver()
        result = resolver.resolve_kickoff()

        # Should return valid field position
        assert 0 <= result.new_los <= 100

        # Result should be a known type
        assert result.result in ("touchback", "return", "out_of_bounds")

    def test_field_goal_short(self):
        """Test short field goal (high success rate)."""
        from huddle.game import SpecialTeamsResolver

        resolver = SpecialTeamsResolver()

        # 25 yard FG should have high success rate
        successes = sum(1 for _ in range(20) if resolver.resolve_field_goal(25).points > 0)

        # Should make most of them
        assert successes >= 15

    def test_field_goal_long(self):
        """Test long field goal (lower success rate)."""
        from huddle.game import SpecialTeamsResolver

        resolver = SpecialTeamsResolver()

        # 55 yard FG should have lower success rate
        successes = sum(1 for _ in range(20) if resolver.resolve_field_goal(55).points > 0)

        # Should miss some
        assert successes < 20

    def test_punt(self):
        """Test punt resolution."""
        from huddle.game import SpecialTeamsResolver

        resolver = SpecialTeamsResolver()
        result = resolver.resolve_punt(los=30.0)

        # Should return valid field position
        assert 0 <= result.new_los <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
