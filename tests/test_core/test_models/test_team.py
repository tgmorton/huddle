"""Tests for Team, Roster, and DepthChart models."""

import pytest
from uuid import uuid4

from huddle.core.enums import Position
from huddle.core.models.player import Player
from huddle.core.models.team import DepthChart, Roster, Team


class TestDepthChart:
    """Tests for DepthChart."""

    def test_set_and_get(self):
        """set and get should work correctly."""
        chart = DepthChart()
        player_id = uuid4()

        chart.set("QB1", player_id)
        assert chart.get("QB1") == player_id

    def test_get_empty_slot(self):
        """get should return None for empty slot."""
        chart = DepthChart()
        assert chart.get("QB1") is None

    def test_get_starter(self):
        """get_starter should return depth 1 player."""
        chart = DepthChart()
        qb1_id = uuid4()
        qb2_id = uuid4()

        chart.set("QB1", qb1_id)
        chart.set("QB2", qb2_id)

        assert chart.get_starter("QB") == qb1_id

    def test_get_all_at_position(self):
        """get_all_at_position should return all players in order."""
        chart = DepthChart()
        wr1 = uuid4()
        wr2 = uuid4()
        wr3 = uuid4()

        chart.set("WR1", wr1)
        chart.set("WR2", wr2)
        chart.set("WR3", wr3)

        all_wrs = chart.get_all_at_position("WR")
        assert all_wrs == [wr1, wr2, wr3]

    def test_get_all_at_position_empty(self):
        """get_all_at_position should return empty list for no players."""
        chart = DepthChart()
        assert chart.get_all_at_position("TE") == []

    def test_get_starters_offense(self):
        """get_starters should return offensive starters."""
        chart = DepthChart()
        qb = uuid4()
        rb = uuid4()
        wr = uuid4()

        chart.set("QB1", qb)
        chart.set("RB1", rb)
        chart.set("WR1", wr)

        starters = chart.get_starters("offense")
        assert starters["QB1"] == qb
        assert starters["RB1"] == rb
        assert starters["WR1"] == wr

    def test_get_starters_defense(self):
        """get_starters should return defensive starters."""
        chart = DepthChart()
        de = uuid4()
        mlb = uuid4()
        cb = uuid4()

        chart.set("DE1", de)
        chart.set("MLB1", mlb)
        chart.set("CB1", cb)

        starters = chart.get_starters("defense")
        assert starters["DE1"] == de
        assert starters["MLB1"] == mlb
        assert starters["CB1"] == cb

    def test_to_dict_from_dict(self):
        """Serialization round-trip should preserve data."""
        chart = DepthChart()
        qb = uuid4()
        rb = uuid4()

        chart.set("QB1", qb)
        chart.set("RB1", rb)

        data = chart.to_dict()
        restored = DepthChart.from_dict(data)

        assert restored.get("QB1") == qb
        assert restored.get("RB1") == rb


class TestRoster:
    """Tests for Roster."""

    def test_add_player(self):
        """add_player should add to roster."""
        roster = Roster()
        player = Player(first_name="Test", last_name="Player")

        roster.add_player(player)
        assert roster.get_player(player.id) == player

    def test_remove_player(self):
        """remove_player should remove from roster."""
        roster = Roster()
        player = Player(first_name="Test", last_name="Player")

        roster.add_player(player)
        removed = roster.remove_player(player.id)

        assert removed == player
        assert roster.get_player(player.id) is None

    def test_remove_nonexistent_player(self):
        """remove_player should return None for nonexistent player."""
        roster = Roster()
        result = roster.remove_player(uuid4())
        assert result is None

    def test_get_starter(self):
        """get_starter should return player at depth chart slot."""
        roster = Roster()
        qb = Player(first_name="Joe", last_name="Burrow", position=Position.QB)

        roster.add_player(qb)
        roster.depth_chart.set("QB1", qb.id)

        assert roster.get_starter("QB1") == qb

    def test_get_starter_empty(self):
        """get_starter should return None for empty slot."""
        roster = Roster()
        assert roster.get_starter("QB1") is None

    def test_get_players_by_position(self):
        """get_players_by_position should filter correctly."""
        roster = Roster()
        wr1 = Player(first_name="Ja'Marr", last_name="Chase", position=Position.WR)
        wr2 = Player(first_name="Tee", last_name="Higgins", position=Position.WR)
        rb = Player(first_name="Joe", last_name="Mixon", position=Position.RB)

        roster.add_player(wr1)
        roster.add_player(wr2)
        roster.add_player(rb)

        wrs = roster.get_players_by_position(Position.WR)
        assert len(wrs) == 2
        assert wr1 in wrs
        assert wr2 in wrs
        assert rb not in wrs

    def test_get_offensive_starters(self, basic_roster):
        """get_offensive_starters should return starter players."""
        starters = basic_roster.get_offensive_starters()

        assert "QB1" in starters
        assert "RB1" in starters
        assert "WR1" in starters
        assert starters["QB1"].position == Position.QB

    def test_size(self):
        """size should return number of players."""
        roster = Roster()
        assert roster.size == 0

        roster.add_player(Player(first_name="A", last_name="Player"))
        assert roster.size == 1

        roster.add_player(Player(first_name="B", last_name="Player"))
        assert roster.size == 2

    def test_to_dict_from_dict(self, basic_roster):
        """Serialization round-trip should preserve roster."""
        data = basic_roster.to_dict()
        restored = Roster.from_dict(data)

        assert restored.size == basic_roster.size
        assert restored.get_starter("QB1") is not None
        assert restored.get_starter("QB1").position == Position.QB


class TestTeam:
    """Tests for Team."""

    def test_default_values(self):
        """Team should have sensible defaults."""
        team = Team()
        assert team.name == ""
        assert team.abbreviation == ""
        assert team.run_tendency == 0.5
        assert team.aggression == 0.5

    def test_full_name(self):
        """full_name should combine city and name."""
        team = Team(city="Philadelphia", name="Eagles")
        assert team.full_name == "Philadelphia Eagles"

    def test_get_starter(self, home_team):
        """get_starter should delegate to roster."""
        qb = home_team.get_starter("QB1")
        assert qb is not None
        assert qb.position == Position.QB

    def test_get_qb(self, home_team):
        """get_qb should return starting QB."""
        qb = home_team.get_qb()
        assert qb is not None
        assert qb.position == Position.QB

    def test_get_rb(self, home_team):
        """get_rb should return starting RB."""
        rb = home_team.get_rb()
        assert rb is not None
        assert rb.position == Position.RB

    def test_calculate_offense_rating(self, home_team):
        """calculate_offense_rating should return average of starters."""
        rating = home_team.calculate_offense_rating()
        # With default 70 attributes, should be around 70
        assert 50 <= rating <= 90

    def test_calculate_offense_rating_empty_roster(self, empty_team):
        """calculate_offense_rating should return 50 for empty roster."""
        rating = empty_team.calculate_offense_rating()
        assert rating == 50

    def test_calculate_defense_rating(self, home_team):
        """calculate_defense_rating should work (may be 50 if no defensive starters)."""
        rating = home_team.calculate_defense_rating()
        # Our basic roster doesn't have defensive starters
        assert rating == 50

    def test_to_dict(self, home_team):
        """to_dict should serialize all fields."""
        data = home_team.to_dict()

        assert data["name"] == "Eagles"
        assert data["abbreviation"] == "PHI"
        assert data["city"] == "Philadelphia"
        assert "roster" in data
        assert "primary_color" in data
        assert "run_tendency" in data

    def test_from_dict(self, home_team):
        """from_dict should restore team correctly."""
        data = home_team.to_dict()
        restored = Team.from_dict(data)

        assert restored.name == "Eagles"
        assert restored.abbreviation == "PHI"
        assert restored.city == "Philadelphia"
        assert restored.run_tendency == home_team.run_tendency
        assert restored.roster.size == home_team.roster.size

    def test_from_dict_preserves_id(self):
        """from_dict should preserve team ID."""
        team_id = uuid4()
        original = Team(id=team_id, name="Test", abbreviation="TST")
        data = original.to_dict()
        restored = Team.from_dict(data)

        assert restored.id == team_id

    def test_str_representation(self, home_team):
        """String representation should show full name."""
        str_repr = str(home_team)
        assert "Philadelphia Eagles" in str_repr
        assert "PHI" in str_repr

    def test_repr_representation(self, home_team):
        """Repr should show key info."""
        repr_str = repr(home_team)
        assert "Philadelphia Eagles" in repr_str
        assert "PHI" in repr_str


class TestTeamTendencies:
    """Tests for team AI tendencies."""

    def test_run_tendency_range(self):
        """run_tendency should be valid."""
        team = Team(run_tendency=0.7)
        assert 0.0 <= team.run_tendency <= 1.0

    def test_aggression_range(self):
        """aggression should be valid."""
        team = Team(aggression=0.8)
        assert 0.0 <= team.aggression <= 1.0

    def test_blitz_tendency_range(self):
        """blitz_tendency should be valid."""
        team = Team(blitz_tendency=0.4)
        assert 0.0 <= team.blitz_tendency <= 1.0

    def test_tendencies_preserved_in_serialization(self):
        """Tendencies should survive serialization."""
        original = Team(
            name="Aggressive Team",
            run_tendency=0.3,
            aggression=0.9,
            blitz_tendency=0.6,
        )
        data = original.to_dict()
        restored = Team.from_dict(data)

        assert restored.run_tendency == 0.3
        assert restored.aggression == 0.9
        assert restored.blitz_tendency == 0.6
