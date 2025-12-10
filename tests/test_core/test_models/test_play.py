"""Tests for PlayCall, DefensiveCall, PlayResult, and DriveResult models."""

import pytest
from uuid import uuid4

from huddle.core.enums import (
    DefensiveScheme,
    Formation,
    PassType,
    PersonnelPackage,
    PlayOutcome,
    PlayType,
    RunType,
)
from huddle.core.models.play import DefensiveCall, DriveResult, PlayCall, PlayResult


class TestPlayCall:
    """Tests for PlayCall."""

    def test_run_factory(self):
        """run() should create run play call."""
        call = PlayCall.run(RunType.INSIDE)
        assert call.play_type == PlayType.RUN
        assert call.run_type == RunType.INSIDE
        assert call.pass_type is None

    def test_pass_factory(self):
        """pass_play() should create pass play call."""
        call = PlayCall.pass_play(PassType.DEEP)
        assert call.play_type == PlayType.PASS
        assert call.pass_type == PassType.DEEP
        assert call.run_type is None

    def test_punt_factory(self):
        """punt() should create punt play call."""
        call = PlayCall.punt()
        assert call.play_type == PlayType.PUNT

    def test_field_goal_factory(self):
        """field_goal() should create FG play call."""
        call = PlayCall.field_goal()
        assert call.play_type == PlayType.FIELD_GOAL

    def test_kickoff_factory(self):
        """kickoff() should create kickoff play call."""
        call = PlayCall.kickoff()
        assert call.play_type == PlayType.KICKOFF

    def test_extra_point_factory(self):
        """extra_point() should create PAT play call."""
        call = PlayCall.extra_point()
        assert call.play_type == PlayType.EXTRA_POINT

    def test_two_point_factory(self):
        """two_point() should create 2PT play call."""
        call = PlayCall.two_point(pass_type=PassType.SHORT)
        assert call.play_type == PlayType.TWO_POINT
        assert call.pass_type == PassType.SHORT

    def test_is_run(self):
        """is_run should return True for run plays."""
        run_call = PlayCall.run(RunType.OUTSIDE)
        pass_call = PlayCall.pass_play(PassType.SHORT)

        assert run_call.is_run is True
        assert pass_call.is_run is False

    def test_is_pass(self):
        """is_pass should return True for pass plays."""
        run_call = PlayCall.run(RunType.INSIDE)
        pass_call = PlayCall.pass_play(PassType.MEDIUM)

        assert run_call.is_pass is False
        assert pass_call.is_pass is True

    def test_display_run(self):
        """display should show run type."""
        call = PlayCall.run(RunType.INSIDE)
        assert "Run" in call.display
        assert "Inside" in call.display

    def test_display_pass(self):
        """display should show pass type."""
        call = PlayCall.pass_play(PassType.DEEP)
        assert "Pass" in call.display
        assert "Deep" in call.display

    def test_display_special_teams(self):
        """display should handle special teams plays."""
        punt = PlayCall.punt()
        assert "Punt" in punt.display

        fg = PlayCall.field_goal()
        assert "Field Goal" in fg.display

    def test_to_dict_from_dict_run(self):
        """Serialization round-trip for run play."""
        original = PlayCall.run(RunType.OUTSIDE, Formation.SHOTGUN, PersonnelPackage.ELEVEN)

        data = original.to_dict()
        restored = PlayCall.from_dict(data)

        assert restored.play_type == PlayType.RUN
        assert restored.run_type == RunType.OUTSIDE
        assert restored.formation == Formation.SHOTGUN
        assert restored.personnel == PersonnelPackage.ELEVEN

    def test_to_dict_from_dict_pass(self):
        """Serialization round-trip for pass play."""
        original = PlayCall.pass_play(PassType.MEDIUM)
        original.primary_target_slot = "WR1"

        data = original.to_dict()
        restored = PlayCall.from_dict(data)

        assert restored.play_type == PlayType.PASS
        assert restored.pass_type == PassType.MEDIUM
        assert restored.primary_target_slot == "WR1"


class TestDefensiveCall:
    """Tests for DefensiveCall."""

    def test_cover_2_factory(self):
        """cover_2() should create Cover 2 defense."""
        call = DefensiveCall.cover_2()
        assert call.scheme == DefensiveScheme.COVER_2
        assert call.blitz_count == 4

    def test_cover_3_factory(self):
        """cover_3() should create Cover 3 defense."""
        call = DefensiveCall.cover_3()
        assert call.scheme == DefensiveScheme.COVER_3

    def test_man_factory(self):
        """man() should create man coverage."""
        call = DefensiveCall.man()
        assert call.scheme == DefensiveScheme.MAN_OFF

        call_press = DefensiveCall.man(press=True)
        assert call_press.scheme == DefensiveScheme.MAN_PRESS

    def test_blitz_factory(self):
        """blitz() should create blitz defense."""
        call = DefensiveCall.blitz(5)
        assert call.scheme == DefensiveScheme.BLITZ_5
        assert call.blitz_count == 5

        call6 = DefensiveCall.blitz(6)
        assert call6.scheme == DefensiveScheme.BLITZ_6
        assert call6.blitz_count == 6

    def test_is_blitz(self):
        """is_blitz should return True when blitz_count > 4."""
        normal = DefensiveCall.cover_3()
        blitz = DefensiveCall.blitz(5)

        assert normal.is_blitz is False
        assert blitz.is_blitz is True

    def test_is_zone(self):
        """is_zone should return True for zone coverages."""
        cover2 = DefensiveCall.cover_2()
        cover3 = DefensiveCall.cover_3()
        man = DefensiveCall.man()

        assert cover2.is_zone is True
        assert cover3.is_zone is True
        assert man.is_zone is False

    def test_display(self):
        """display should format scheme name."""
        call = DefensiveCall.cover_3()
        assert "Cover 3" in call.display

        blitz = DefensiveCall.blitz(5)
        assert "Blitz" in blitz.display
        assert "5" in blitz.display

    def test_to_dict_from_dict(self):
        """Serialization round-trip."""
        original = DefensiveCall.blitz(6)
        data = original.to_dict()
        restored = DefensiveCall.from_dict(data)

        assert restored.scheme == DefensiveScheme.BLITZ_6
        assert restored.blitz_count == 6


class TestPlayResult:
    """Tests for PlayResult."""

    def test_display_touchdown(self, touchdown_play):
        """display should show TOUCHDOWN."""
        assert "TOUCHDOWN" in touchdown_play.display

    def test_display_turnover(self, interception_play):
        """display should show TURNOVER."""
        assert "TURNOVER" in interception_play.display

    def test_display_sack(self, sack_play):
        """display should show SACK."""
        assert "SACK" in sack_play.display

    def test_display_incomplete(self, incomplete_pass):
        """display should show incomplete."""
        assert "Incomplete" in incomplete_pass.display

    def test_display_complete(self, completed_pass):
        """display should show completion yards."""
        assert "Complete" in completed_pass.display
        assert "8" in completed_pass.display

    def test_display_rush(self, rushing_play):
        """display should show rush yards."""
        assert "Rush" in rushing_play.display
        assert "4" in rushing_play.display

    def test_display_rush_loss(self):
        """display should show loss for negative rush."""
        result = PlayResult(
            play_call=PlayCall.run(RunType.INSIDE),
            defensive_call=DefensiveCall.cover_3(),
            outcome=PlayOutcome.RUSH,
            yards_gained=-3,
        )
        display = result.display
        assert "loss" in display.lower()

    def test_to_dict_complete(self, completed_pass):
        """to_dict should serialize all fields."""
        data = completed_pass.to_dict()

        assert "play_call" in data
        assert "defensive_call" in data
        assert data["outcome"] == "COMPLETE"
        assert data["yards_gained"] == 8

    def test_to_dict_with_player_ids(self):
        """to_dict should handle player UUIDs."""
        passer = uuid4()
        receiver = uuid4()
        tackler = uuid4()

        result = PlayResult(
            play_call=PlayCall.pass_play(PassType.SHORT),
            defensive_call=DefensiveCall.cover_3(),
            outcome=PlayOutcome.COMPLETE,
            yards_gained=12,
            passer_id=passer,
            receiver_id=receiver,
            tackler_id=tackler,
        )
        data = result.to_dict()

        assert data["passer_id"] == str(passer)
        assert data["receiver_id"] == str(receiver)
        assert data["tackler_id"] == str(tackler)

    def test_from_dict(self, completed_pass):
        """from_dict should restore result."""
        data = completed_pass.to_dict()
        restored = PlayResult.from_dict(data)

        assert restored.outcome == PlayOutcome.COMPLETE
        assert restored.yards_gained == 8
        assert restored.play_call.play_type == PlayType.PASS

    def test_from_dict_with_player_ids(self):
        """from_dict should restore player UUIDs."""
        passer = uuid4()
        interceptor = uuid4()

        original = PlayResult(
            play_call=PlayCall.pass_play(PassType.DEEP),
            defensive_call=DefensiveCall.cover_3(),
            outcome=PlayOutcome.INTERCEPTION,
            passer_id=passer,
            interceptor_id=interceptor,
            is_turnover=True,
        )
        data = original.to_dict()
        restored = PlayResult.from_dict(data)

        assert restored.passer_id == passer
        assert restored.interceptor_id == interceptor
        assert restored.is_turnover is True


class TestPlayResultFlags:
    """Tests for PlayResult boolean flags."""

    def test_touchdown_flags(self, touchdown_play):
        """Touchdown should have correct flags."""
        assert touchdown_play.is_touchdown is True
        assert touchdown_play.is_turnover is False
        assert touchdown_play.points_scored == 6

    def test_interception_flags(self, interception_play):
        """Interception should have correct flags."""
        assert interception_play.is_turnover is True
        assert interception_play.is_touchdown is False

    def test_sack_flags(self, sack_play):
        """Sack should have correct flags."""
        assert sack_play.is_sack is True
        assert sack_play.yards_gained < 0

    def test_incomplete_clock_stopped(self, incomplete_pass):
        """Incomplete pass should stop clock."""
        assert incomplete_pass.clock_stopped is True
        assert incomplete_pass.clock_stop_reason == "incomplete"


class TestDriveResult:
    """Tests for DriveResult."""

    def test_default_values(self):
        """DriveResult should have sensible defaults."""
        drive = DriveResult(starting_yard_line=25, ending_yard_line=75)
        assert drive.plays == 0
        assert drive.total_yards == 0
        assert drive.result == ""

    def test_display_touchdown(self):
        """display should show touchdown drive."""
        drive = DriveResult(
            starting_yard_line=25,
            ending_yard_line=100,
            plays=8,
            total_yards=75,
            result="TD",
            points=7,
        )
        display = drive.display
        assert "TOUCHDOWN" in display
        assert "8 plays" in display
        assert "75 yards" in display

    def test_display_field_goal(self):
        """display should show field goal drive."""
        drive = DriveResult(
            starting_yard_line=25,
            ending_yard_line=70,
            plays=10,
            total_yards=45,
            result="FG",
            points=3,
        )
        display = drive.display
        assert "FIELD GOAL" in display

    def test_display_punt(self):
        """display should show punt drive."""
        drive = DriveResult(
            starting_yard_line=25,
            ending_yard_line=40,
            plays=3,
            total_yards=15,
            result="PUNT",
        )
        display = drive.display
        assert "PUNT" in display

    def test_display_turnover(self):
        """display should show turnover drive."""
        drive = DriveResult(
            starting_yard_line=25,
            ending_yard_line=35,
            plays=4,
            total_yards=10,
            result="TURNOVER",
        )
        display = drive.display
        assert "TURNOVER" in display

    def test_to_dict_from_dict(self):
        """Serialization round-trip."""
        original = DriveResult(
            starting_yard_line=20,
            ending_yard_line=100,
            plays=12,
            total_yards=80,
            time_elapsed_seconds=420,
            result="TD",
            points=7,
            big_plays=["45-yard pass", "12-yard TD run"],
        )
        data = original.to_dict()
        restored = DriveResult.from_dict(data)

        assert restored.starting_yard_line == 20
        assert restored.ending_yard_line == 100
        assert restored.plays == 12
        assert restored.total_yards == 80
        assert restored.result == "TD"
        assert restored.points == 7
        assert len(restored.big_plays) == 2


class TestFormation:
    """Tests for Formation enum."""

    def test_pass_modifier(self):
        """Formation should have pass_modifier property."""
        assert Formation.SHOTGUN.pass_modifier > 1.0  # Better passing
        assert Formation.GOAL_LINE.pass_modifier < 1.0  # Worse passing
        assert Formation.SINGLEBACK.pass_modifier == 1.0  # Neutral

    def test_run_modifier(self):
        """Formation should have run_modifier property."""
        assert Formation.I_FORM.run_modifier > 1.0  # Better running
        assert Formation.SPREAD.run_modifier < 1.0  # Worse running
        assert Formation.SINGLEBACK.run_modifier == 1.0  # Neutral

    def test_is_pass_oriented(self):
        """is_pass_oriented should return True for pass-oriented formations."""
        assert Formation.SHOTGUN.is_pass_oriented is True
        assert Formation.SPREAD.is_pass_oriented is True
        assert Formation.EMPTY.is_pass_oriented is True
        assert Formation.I_FORM.is_pass_oriented is False
        assert Formation.GOAL_LINE.is_pass_oriented is False

    def test_is_run_oriented(self):
        """is_run_oriented should return True for run-oriented formations."""
        assert Formation.I_FORM.is_run_oriented is True
        assert Formation.GOAL_LINE.is_run_oriented is True
        assert Formation.UNDER_CENTER.is_run_oriented is True
        assert Formation.SHOTGUN.is_run_oriented is False
        assert Formation.SPREAD.is_run_oriented is False


class TestPersonnelPackage:
    """Tests for PersonnelPackage enum."""

    def test_rb_count(self):
        """rb_count should return correct RB count."""
        assert PersonnelPackage.ELEVEN.rb_count == 1
        assert PersonnelPackage.TWELVE.rb_count == 1
        assert PersonnelPackage.TWENTY_ONE.rb_count == 2
        assert PersonnelPackage.TWENTY_TWO.rb_count == 2
        assert PersonnelPackage.EMPTY.rb_count == 0

    def test_te_count(self):
        """te_count should return correct TE count."""
        assert PersonnelPackage.ELEVEN.te_count == 1
        assert PersonnelPackage.TWELVE.te_count == 2
        assert PersonnelPackage.TWENTY_ONE.te_count == 1
        assert PersonnelPackage.TWENTY_TWO.te_count == 2
        assert PersonnelPackage.TEN.te_count == 0

    def test_wr_count(self):
        """wr_count should return correct WR count (5 - RB - TE)."""
        assert PersonnelPackage.ELEVEN.wr_count == 3  # 5 - 1 - 1
        assert PersonnelPackage.TWELVE.wr_count == 2  # 5 - 1 - 2
        assert PersonnelPackage.TWENTY_ONE.wr_count == 2  # 5 - 2 - 1
        assert PersonnelPackage.TWENTY_TWO.wr_count == 1  # 5 - 2 - 2
        assert PersonnelPackage.TEN.wr_count == 4  # 5 - 1 - 0

    def test_get_depth_slots(self):
        """get_depth_slots should return correct slot names."""
        slots = PersonnelPackage.ELEVEN.get_depth_slots()
        assert "QB1" in slots
        assert "RB1" in slots
        assert "TE1" in slots
        assert "WR1" in slots
        assert "WR2" in slots
        assert "WR3" in slots
        assert len(slots) == 6  # QB1 + 1 RB + 1 TE + 3 WR

        slots_22 = PersonnelPackage.TWENTY_TWO.get_depth_slots()
        assert "RB1" in slots_22
        assert "RB2" in slots_22
        assert "TE1" in slots_22
        assert "TE2" in slots_22
        assert "WR1" in slots_22
        assert len(slots_22) == 6  # QB1 + 2 RB + 2 TE + 1 WR


class TestPlayCallWithFormation:
    """Tests for PlayCall with Formation and PersonnelPackage."""

    def test_run_with_formation(self):
        """run() should accept formation and personnel."""
        call = PlayCall.run(RunType.INSIDE, Formation.I_FORM, PersonnelPackage.TWENTY_ONE)
        assert call.formation == Formation.I_FORM
        assert call.personnel == PersonnelPackage.TWENTY_ONE

    def test_run_default_formation(self):
        """run() should use default formation/personnel if not specified."""
        call = PlayCall.run(RunType.INSIDE)
        assert call.formation == Formation.SINGLEBACK
        assert call.personnel == PersonnelPackage.TWELVE

    def test_pass_with_formation(self):
        """pass_play() should accept formation and personnel."""
        call = PlayCall.pass_play(PassType.DEEP, Formation.SPREAD, PersonnelPackage.TEN)
        assert call.formation == Formation.SPREAD
        assert call.personnel == PersonnelPackage.TEN

    def test_pass_default_formation(self):
        """pass_play() should use default formation/personnel if not specified."""
        call = PlayCall.pass_play(PassType.SHORT)
        assert call.formation == Formation.SHOTGUN
        assert call.personnel == PersonnelPackage.ELEVEN

    def test_formation_serialization(self):
        """Formation and personnel should serialize correctly."""
        call = PlayCall.run(RunType.OUTSIDE, Formation.PISTOL, PersonnelPackage.TWELVE)
        data = call.to_dict()

        assert data["formation"] == "PISTOL"
        assert data["personnel"] == "12"

        restored = PlayCall.from_dict(data)
        assert restored.formation == Formation.PISTOL
        assert restored.personnel == PersonnelPackage.TWELVE
