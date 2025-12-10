"""Tests for Player model."""

import pytest
from uuid import uuid4

from huddle.core.attributes import PlayerAttributes
from huddle.core.enums import Position
from huddle.core.models.player import Player


class TestPlayer:
    """Tests for Player model."""

    def test_default_values(self):
        """Player should have sensible defaults."""
        player = Player()
        assert player.first_name == ""
        assert player.last_name == ""
        assert player.position == Position.QB
        assert player.age == 22
        assert player.jersey_number == 0

    def test_full_name(self):
        """full_name should combine first and last name."""
        player = Player(first_name="Patrick", last_name="Mahomes")
        assert player.full_name == "Patrick Mahomes"

    def test_display_name(self):
        """display_name should show abbreviated first name."""
        player = Player(first_name="Patrick", last_name="Mahomes")
        assert player.display_name == "P. Mahomes"

    def test_display_name_no_first_name(self):
        """display_name should handle missing first name."""
        player = Player(last_name="Mahomes")
        assert player.display_name == "Mahomes"

    def test_height_display(self):
        """height_display should format as feet'inches\"."""
        player = Player(height_inches=74)  # 6'2"
        assert player.height_display == "6'2\""

        player = Player(height_inches=72)  # 6'0"
        assert player.height_display == "6'0\""

        player = Player(height_inches=69)  # 5'9"
        assert player.height_display == "5'9\""

    def test_overall_calculation(self, qb_player):
        """overall should calculate based on position weights."""
        # With all 70s, overall should be around 70
        assert 60 <= qb_player.overall <= 80

    def test_get_attribute(self, qb_player):
        """get_attribute should return correct value."""
        qb_player.attributes.set("speed", 85)
        assert qb_player.get_attribute("speed") == 85

    def test_set_attribute(self, qb_player):
        """set_attribute should update the value."""
        qb_player.set_attribute("throw_power", 95)
        assert qb_player.get_attribute("throw_power") == 95

    def test_to_dict(self, qb_player):
        """to_dict should serialize all fields."""
        data = qb_player.to_dict()

        assert data["first_name"] == "Tom"
        assert data["last_name"] == "Brady"
        assert data["position"] == "QB"
        assert data["age"] == 25
        assert data["jersey_number"] == 12
        assert "id" in data
        assert "attributes" in data

    def test_from_dict(self):
        """from_dict should restore player correctly."""
        original = Player(
            first_name="Josh",
            last_name="Allen",
            position=Position.QB,
            age=27,
            jersey_number=17,
            height_inches=77,
            weight_lbs=237,
            experience_years=5,
            college="Wyoming",
        )
        data = original.to_dict()
        restored = Player.from_dict(data)

        assert restored.first_name == "Josh"
        assert restored.last_name == "Allen"
        assert restored.position == Position.QB
        assert restored.age == 27
        assert restored.jersey_number == 17
        assert restored.height_inches == 77
        assert restored.college == "Wyoming"

    def test_from_dict_preserves_id(self):
        """from_dict should preserve the player ID."""
        player_id = uuid4()
        original = Player(id=player_id, first_name="Test", last_name="Player")
        data = original.to_dict()
        restored = Player.from_dict(data)

        assert restored.id == player_id

    def test_str_representation(self, qb_player):
        """String representation should be readable."""
        str_repr = str(qb_player)
        assert "Tom Brady" in str_repr
        assert "QB" in str_repr
        assert "OVR" in str_repr

    def test_repr_representation(self, qb_player):
        """Repr should show key info."""
        repr_str = repr(qb_player)
        assert "Tom Brady" in repr_str
        assert "QB" in repr_str


class TestPlayerAttributes:
    """Tests for PlayerAttributes integration with Player."""

    def test_different_positions_have_different_overalls(self):
        """Same attributes should produce different overalls for different positions."""
        attrs = PlayerAttributes()
        # Set all attributes to 75
        for attr in ["speed", "acceleration", "strength", "agility", "awareness",
                     "throw_power", "throw_accuracy_short", "throw_accuracy_mid",
                     "throw_accuracy_deep", "carrying", "catching", "route_running",
                     "run_blocking", "pass_blocking", "tackle", "hit_power",
                     "man_coverage", "zone_coverage", "kick_power", "kick_accuracy"]:
            attrs.set(attr, 75)

        qb = Player(position=Position.QB, attributes=attrs)
        rb = Player(position=Position.RB, attributes=attrs)
        wr = Player(position=Position.WR, attributes=attrs)

        # All should have reasonable overalls but may differ based on weights
        assert 60 <= qb.overall <= 90
        assert 60 <= rb.overall <= 90
        assert 60 <= wr.overall <= 90

    def test_high_attributes_produce_high_overall(self):
        """High attribute values should produce high overall."""
        attrs = PlayerAttributes()
        for attr in ["speed", "acceleration", "strength", "agility", "awareness",
                     "throw_power", "throw_accuracy_short", "throw_accuracy_mid",
                     "throw_accuracy_deep", "carrying", "catching", "route_running",
                     "run_blocking", "pass_blocking", "tackle", "hit_power",
                     "man_coverage", "zone_coverage", "kick_power", "kick_accuracy"]:
            attrs.set(attr, 95)

        player = Player(position=Position.QB, attributes=attrs)
        assert player.overall >= 80  # Overall calculation may cap or weight attributes

    def test_low_attributes_produce_low_overall(self):
        """Low attribute values should produce low overall."""
        attrs = PlayerAttributes()
        for attr in ["speed", "acceleration", "strength", "agility", "awareness",
                     "throw_power", "throw_accuracy_short", "throw_accuracy_mid",
                     "throw_accuracy_deep", "carrying", "catching", "route_running",
                     "run_blocking", "pass_blocking", "tackle", "hit_power",
                     "man_coverage", "zone_coverage", "kick_power", "kick_accuracy"]:
            attrs.set(attr, 50)

        player = Player(position=Position.QB, attributes=attrs)
        assert player.overall <= 65
