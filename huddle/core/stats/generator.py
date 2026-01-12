"""
Correlated game stats generator.

Generates realistic, correlated game statistics without play-by-play simulation.
Uses NFL distributions from research data to produce believable box scores.
"""

import random
from dataclasses import dataclass
from typing import Optional
from uuid import UUID, uuid4

from huddle.core.models.stats import (
    GameLog,
    PlayerGameStats,
    TeamGameStats,
    PassingStats,
    RushingStats,
    ReceivingStats,
    DefensiveStats,
)
from huddle.core.models.team import Team
from huddle.core.models.player import Player


@dataclass
class GameContext:
    """Context for generating a game's stats."""

    week: int
    home_team: Team
    away_team: Optional[Team]  # May be None or have empty roster
    home_score: int
    away_score: int
    is_playoff: bool = False


# NFL statistical distributions from research/exports/game_flow_model.json
NFL_PASS_RATE = 0.583
NFL_YARDS_PER_ATTEMPT = 7.0
NFL_YARDS_PER_CARRY = 4.3
NFL_COMPLETION_RATE = 0.65
NFL_INT_RATE = 0.025
NFL_FUMBLE_RATE = 0.01
NFL_POINTS_PER_TEAM = 22.9
NFL_TURNOVERS_PER_GAME = 3.45

# Target share distributions
TARGET_SHARES = {
    "WR1": 0.25,
    "WR2": 0.18,
    "WR3": 0.12,
    "TE1": 0.15,
    "RB1": 0.12,
    "RB2": 0.08,
    "OTHER": 0.10,
}

# Rush attempt distributions
RUSH_SHARES = {
    "RB1": 0.60,
    "RB2": 0.25,
    "QB": 0.08,
    "WR": 0.02,
    "OTHER": 0.05,
}


def _gauss_bounded(mean: float, std: float, min_val: float, max_val: float) -> float:
    """Generate gaussian value bounded to a range."""
    return max(min_val, min(max_val, random.gauss(mean, std)))


def _get_attribute(player: Optional[Player], attr: str, default: int = 50) -> int:
    """Safely get player attribute with default."""
    if player is None:
        return default
    return player.attributes.get(attr, default)


class CorrelatedStatsGenerator:
    """Generates realistic, correlated game statistics."""

    def generate(self, ctx: GameContext) -> GameLog:
        """Generate complete GameLog with correlated player stats."""
        game_id = uuid4()

        # Generate team stats
        home_team_stats = self._generate_team_stats(ctx.home_score, is_home=True)
        away_team_stats = self._generate_team_stats(ctx.away_score, is_home=False)

        # Generate player stats
        player_stats: dict[str, PlayerGameStats] = {}

        # Home team player stats
        if ctx.home_team and ctx.home_team.roster.size > 0:
            home_player_stats = self._generate_player_stats(
                ctx.home_team, home_team_stats
            )
            player_stats.update(home_player_stats)
        else:
            home_abbr = ctx.home_team.abbreviation if ctx.home_team else "HOME"
            player_stats.update(
                self._generate_synthetic_stats(home_abbr, home_team_stats)
            )

        # Away team player stats
        if ctx.away_team and ctx.away_team.roster.size > 0:
            away_player_stats = self._generate_player_stats(
                ctx.away_team, away_team_stats
            )
            player_stats.update(away_player_stats)
        else:
            away_abbr = ctx.away_team.abbreviation if ctx.away_team else "AWAY"
            player_stats.update(
                self._generate_synthetic_stats(away_abbr, away_team_stats)
            )

        return GameLog(
            game_id=game_id,
            week=ctx.week,
            home_team_abbr=ctx.home_team.abbreviation if ctx.home_team else "HOME",
            away_team_abbr=ctx.away_team.abbreviation if ctx.away_team else "AWAY",
            home_score=ctx.home_score,
            away_score=ctx.away_score,
            home_stats=home_team_stats,
            away_stats=away_team_stats,
            player_stats=player_stats,
            is_playoff=ctx.is_playoff,
        )

    def _generate_team_stats(self, score: int, is_home: bool) -> TeamGameStats:
        """Generate team-level stats correlated with score."""
        # Derive total yards from score
        # NFL avg: ~345 yards per team, ~23 points per team = ~15 yards per point
        yards_per_point = _gauss_bounded(15.0, 2.5, 10.0, 20.0)
        total_yards = int(score * yards_per_point)

        # Split pass/rush based on NFL average
        pass_pct = _gauss_bounded(NFL_PASS_RATE, 0.08, 0.40, 0.75)
        passing_yards = int(total_yards * pass_pct)
        rushing_yards = total_yards - passing_yards

        # Calculate first downs (roughly 1 per 10 yards)
        first_downs = max(5, int(total_yards / 10) + random.randint(-3, 3))

        # Scoring breakdown
        touchdowns = score // 7
        remaining = score - (touchdowns * 7)
        field_goals = remaining // 3

        # Third down conversion
        third_down_attempts = random.randint(10, 18)
        third_down_conversions = int(
            third_down_attempts * _gauss_bounded(0.40, 0.10, 0.20, 0.65)
        )

        # Turnovers (from NFL avg 1.7 per team per game)
        turnovers = max(0, int(_gauss_bounded(1.7, 1.0, 0, 5)))

        # Time of possession (more yards = more TOP typically)
        base_top = 1800  # 30 minutes per team baseline
        top_modifier = (total_yards - 300) / 10  # +/- based on yards
        top_seconds = int(base_top + top_modifier + random.randint(-120, 120))
        top_seconds = max(1200, min(2400, top_seconds))  # 20-40 min range

        # Penalties
        penalties = random.randint(4, 12)
        penalty_yards = penalties * random.randint(5, 12)

        team_abbr = "HOME" if is_home else "AWAY"

        return TeamGameStats(
            team_abbr=team_abbr,
            total_yards=total_yards,
            passing_yards=passing_yards,
            rushing_yards=rushing_yards,
            first_downs=first_downs,
            third_down_attempts=third_down_attempts,
            third_down_conversions=third_down_conversions,
            fourth_down_attempts=random.randint(0, 3),
            fourth_down_conversions=random.randint(0, 2),
            turnovers=turnovers,
            penalties=penalties,
            penalty_yards=penalty_yards,
            time_of_possession_seconds=top_seconds,
            points=score,
            touchdowns=touchdowns,
            field_goals=field_goals,
        )

    def _generate_player_stats(
        self, team: Team, team_stats: TeamGameStats
    ) -> dict[str, PlayerGameStats]:
        """Generate individual player stats for a team with roster."""
        player_stats: dict[str, PlayerGameStats] = {}

        # Get starters from depth chart
        off_starters = team.roster.get_offensive_starters()
        def_starters = team.roster.get_defensive_starters()

        # Get key players by position
        qb = off_starters.get("QB1")
        rb1 = off_starters.get("RB1")
        rb2 = off_starters.get("RB2")
        wr1 = off_starters.get("WR1")
        wr2 = off_starters.get("WR2")
        wr3 = off_starters.get("WR3")
        te1 = off_starters.get("TE1")

        # --- PASSING STATS (QB) ---
        if qb:
            passing = self._generate_passing_stats(qb, team_stats)
            qb_rushing = self._generate_qb_rushing(qb, team_stats)
            player_stats[str(qb.id)] = PlayerGameStats(
                player_id=qb.id,
                player_name=qb.full_name,
                team_abbr=team.abbreviation,
                position="QB",
                passing=passing,
                rushing=qb_rushing,
            )

        # --- RUSHING STATS ---
        remaining_rush_yards = team_stats.rushing_yards
        remaining_rush_attempts = max(
            15, int(team_stats.rushing_yards / NFL_YARDS_PER_CARRY)
        )

        # RB1
        if rb1:
            rb1_yards = int(remaining_rush_yards * RUSH_SHARES["RB1"])
            rb1_attempts = int(remaining_rush_attempts * RUSH_SHARES["RB1"])
            rb1_rushing = self._generate_rushing_stats(
                rb1, rb1_yards, rb1_attempts, team_stats
            )
            rb1_receiving = self._generate_receiving_stats(
                rb1, team_stats, TARGET_SHARES["RB1"]
            )
            player_stats[str(rb1.id)] = PlayerGameStats(
                player_id=rb1.id,
                player_name=rb1.full_name,
                team_abbr=team.abbreviation,
                position="RB",
                rushing=rb1_rushing,
                receiving=rb1_receiving,
            )
            remaining_rush_yards -= rb1_yards
            remaining_rush_attempts -= rb1_attempts

        # RB2
        if rb2:
            rb2_yards = int(remaining_rush_yards * 0.7)  # Most of remaining
            rb2_attempts = int(remaining_rush_attempts * 0.7)
            rb2_rushing = self._generate_rushing_stats(
                rb2, rb2_yards, rb2_attempts, team_stats
            )
            rb2_receiving = self._generate_receiving_stats(
                rb2, team_stats, TARGET_SHARES["RB2"]
            )
            player_stats[str(rb2.id)] = PlayerGameStats(
                player_id=rb2.id,
                player_name=rb2.full_name,
                team_abbr=team.abbreviation,
                position="RB",
                rushing=rb2_rushing,
                receiving=rb2_receiving,
            )

        # --- RECEIVING STATS ---
        receivers = [
            (wr1, "WR", TARGET_SHARES["WR1"]),
            (wr2, "WR", TARGET_SHARES["WR2"]),
            (wr3, "WR", TARGET_SHARES["WR3"]),
            (te1, "TE", TARGET_SHARES["TE1"]),
        ]

        for receiver, pos, share in receivers:
            if receiver and str(receiver.id) not in player_stats:
                receiving = self._generate_receiving_stats(receiver, team_stats, share)
                player_stats[str(receiver.id)] = PlayerGameStats(
                    player_id=receiver.id,
                    player_name=receiver.full_name,
                    team_abbr=team.abbreviation,
                    position=pos,
                    receiving=receiving,
                )

        # --- DEFENSIVE STATS ---
        for slot, defender in def_starters.items():
            if defender and str(defender.id) not in player_stats:
                defense = self._generate_defensive_stats(defender, slot)
                player_stats[str(defender.id)] = PlayerGameStats(
                    player_id=defender.id,
                    player_name=defender.full_name,
                    team_abbr=team.abbreviation,
                    position=defender.position,
                    defense=defense,
                )

        return player_stats

    def _generate_passing_stats(
        self, qb: Player, team_stats: TeamGameStats
    ) -> PassingStats:
        """Generate QB passing stats based on attributes and team performance."""
        # Calculate attempts from yards and YPA
        base_ypa = NFL_YARDS_PER_ATTEMPT
        throw_acc = _get_attribute(qb, "throw_accuracy_short", 70)
        ypa_modifier = (throw_acc - 70) / 100  # +/- based on accuracy
        actual_ypa = base_ypa + ypa_modifier

        attempts = max(20, int(team_stats.passing_yards / actual_ypa))
        attempts = int(_gauss_bounded(attempts, 5, 15, 55))

        # Completion rate based on accuracy
        base_comp = NFL_COMPLETION_RATE
        comp_modifier = (throw_acc - 70) / 200  # +/- 0.15 for range 20-120
        comp_rate = _gauss_bounded(base_comp + comp_modifier, 0.06, 0.45, 0.80)

        completions = int(attempts * comp_rate)
        yards = team_stats.passing_yards

        # TDs (roughly 1 per 40 passing yards for good games)
        td_rate = yards / 50 if yards > 100 else yards / 70
        touchdowns = max(0, int(_gauss_bounded(td_rate, 0.8, 0, 6)))

        # INTs based on turnovers and decision making
        decision = _get_attribute(qb, "decision_making", 70)
        int_rate = NFL_INT_RATE * (1 + (70 - decision) / 100)
        interceptions = max(
            0, min(team_stats.turnovers, int(_gauss_bounded(int_rate * attempts, 0.8, 0, 4)))
        )

        # Sacks (2-5 per game typically)
        sacks = random.randint(1, 5)
        sack_yards = sacks * random.randint(5, 12)

        # Longest pass
        longest = max(15, int(_gauss_bounded(yards / 8, 10, 10, 75)))

        return PassingStats(
            attempts=attempts,
            completions=completions,
            yards=yards,
            touchdowns=touchdowns,
            interceptions=interceptions,
            sacks=sacks,
            sack_yards=sack_yards,
            longest=longest,
        )

    def _generate_qb_rushing(
        self, qb: Player, team_stats: TeamGameStats
    ) -> RushingStats:
        """Generate QB scramble/rushing stats."""
        speed = _get_attribute(qb, "speed", 60)

        # Mobile QBs rush more
        if speed > 75:
            attempts = random.randint(4, 10)
            yards = int(attempts * _gauss_bounded(5.0, 2.0, -2, 15))
        else:
            attempts = random.randint(1, 4)
            yards = int(attempts * _gauss_bounded(2.0, 3.0, -5, 10))

        touchdowns = 1 if yards > 30 and random.random() < 0.3 else 0

        return RushingStats(
            attempts=attempts,
            yards=max(-10, yards),  # Allow negative (sack-like scrambles)
            touchdowns=touchdowns,
            longest=max(0, yards) if attempts > 0 else 0,
        )

    def _generate_rushing_stats(
        self,
        rb: Player,
        target_yards: int,
        target_attempts: int,
        team_stats: TeamGameStats,
    ) -> RushingStats:
        """Generate RB rushing stats."""
        # Add variance to targets
        yards = int(_gauss_bounded(target_yards, target_yards * 0.2, 0, target_yards * 2))
        attempts = max(1, int(_gauss_bounded(target_attempts, 3, 1, target_attempts + 10)))

        # TDs based on yards and goal line work
        td_chance = yards / 100  # ~1 TD per 100 yards
        touchdowns = max(0, int(_gauss_bounded(td_chance, 0.5, 0, 3)))

        # Fumbles rare
        fumbles = 1 if random.random() < NFL_FUMBLE_RATE * attempts else 0
        fumbles_lost = fumbles if random.random() < 0.5 else 0

        longest = max(1, int(_gauss_bounded(yards / 4, 5, 1, min(yards, 80))))

        return RushingStats(
            attempts=attempts,
            yards=yards,
            touchdowns=touchdowns,
            fumbles=fumbles,
            fumbles_lost=fumbles_lost,
            longest=longest,
        )

    def _generate_receiving_stats(
        self, receiver: Player, team_stats: TeamGameStats, target_share: float
    ) -> ReceivingStats:
        """Generate receiver stats based on target share."""
        # Calculate targets from team passing
        total_targets = int(team_stats.passing_yards / 6)  # Rough estimate
        targets = max(1, int(total_targets * target_share))
        targets = int(_gauss_bounded(targets, 2, 1, targets + 5))

        # Catch rate based on catching attribute
        catching = _get_attribute(receiver, "catching", 70)
        base_catch_rate = 0.65
        catch_modifier = (catching - 70) / 200
        catch_rate = _gauss_bounded(base_catch_rate + catch_modifier, 0.10, 0.40, 0.90)

        receptions = max(0, int(targets * catch_rate))

        # Yards per reception
        yards_per_rec = _gauss_bounded(12.0, 4.0, 5.0, 25.0)
        yards = int(receptions * yards_per_rec)

        # TDs based on yards
        td_chance = yards / 80
        touchdowns = max(0, int(_gauss_bounded(td_chance, 0.5, 0, 2)))

        longest = max(0, int(_gauss_bounded(yards / 3, 8, 0, min(yards, 75)))) if yards > 0 else 0

        return ReceivingStats(
            targets=targets,
            receptions=receptions,
            yards=yards,
            touchdowns=touchdowns,
            longest=longest,
        )

    def _generate_defensive_stats(
        self, defender: Player, slot: str
    ) -> DefensiveStats:
        """Generate defensive player stats."""
        # Base tackle expectations by position
        tackle_base = {
            "MLB1": 8,
            "MLB2": 6,
            "LOLB1": 5,
            "ROLB1": 5,
            "SS1": 5,
            "FS1": 4,
            "CB1": 4,
            "CB2": 4,
            "LE1": 3,
            "RE1": 3,
            "DT1": 3,
            "DT2": 2,
        }
        base = tackle_base.get(slot, 3)
        tackles = max(0, int(_gauss_bounded(base, 2, 0, base + 6)))

        # TFLs rare
        tackles_for_loss = 1 if random.random() < 0.15 else 0

        # Sacks for edge/DL
        sacks = 0.0
        if slot in ["LE1", "RE1", "LOLB1", "ROLB1", "DT1"]:
            if random.random() < 0.20:  # 20% chance of at least half sack
                sacks = 0.5 if random.random() < 0.5 else 1.0

        # INTs for DBs
        interceptions = 0
        if slot in ["CB1", "CB2", "SS1", "FS1"]:
            if random.random() < 0.05:  # 5% chance
                interceptions = 1

        # Passes defended for DBs
        passes_defended = 0
        if slot in ["CB1", "CB2", "SS1", "FS1"]:
            passes_defended = random.randint(0, 2)

        return DefensiveStats(
            tackles=tackles,
            tackles_for_loss=tackles_for_loss,
            sacks=sacks,
            interceptions=interceptions,
            passes_defended=passes_defended,
        )

    def _generate_synthetic_stats(
        self, team_abbr: str, team_stats: TeamGameStats
    ) -> dict[str, PlayerGameStats]:
        """Generate placeholder stats for teams without rosters."""
        player_stats: dict[str, PlayerGameStats] = {}

        # Synthetic QB
        qb_id = uuid4()
        qb_attempts = max(20, int(team_stats.passing_yards / 7))
        qb_completions = int(qb_attempts * 0.65)
        player_stats[str(qb_id)] = PlayerGameStats(
            player_id=qb_id,
            player_name=f"QB #{random.randint(1, 19)}",
            team_abbr=team_abbr,
            position="QB",
            passing=PassingStats(
                attempts=qb_attempts,
                completions=qb_completions,
                yards=team_stats.passing_yards,
                touchdowns=team_stats.touchdowns // 2,
                interceptions=min(2, team_stats.turnovers),
            ),
        )

        # Synthetic RB
        rb_id = uuid4()
        rb_attempts = max(10, int(team_stats.rushing_yards / 4.3))
        player_stats[str(rb_id)] = PlayerGameStats(
            player_id=rb_id,
            player_name=f"RB #{random.randint(20, 39)}",
            team_abbr=team_abbr,
            position="RB",
            rushing=RushingStats(
                attempts=rb_attempts,
                yards=team_stats.rushing_yards,
                touchdowns=max(0, team_stats.touchdowns - team_stats.touchdowns // 2),
            ),
        )

        # Synthetic WR
        wr_id = uuid4()
        player_stats[str(wr_id)] = PlayerGameStats(
            player_id=wr_id,
            player_name=f"WR #{random.randint(80, 89)}",
            team_abbr=team_abbr,
            position="WR",
            receiving=ReceivingStats(
                targets=random.randint(6, 12),
                receptions=random.randint(4, 8),
                yards=int(team_stats.passing_yards * 0.35),
                touchdowns=random.randint(0, 2),
            ),
        )

        return player_stats


def select_mvp(game_log: GameLog, winning_team_abbr: Optional[str]) -> Optional[dict]:
    """Select game MVP from player stats."""
    if not winning_team_abbr:
        return None

    best_player = None
    best_value = 0

    for player_id, stats in game_log.player_stats.items():
        if stats.team_abbr != winning_team_abbr:
            continue

        # Calculate value score
        value = 0
        if stats.passing.yards > 0:
            value += stats.passing.yards / 10 + stats.passing.touchdowns * 20
        if stats.rushing.yards > 0:
            value += stats.rushing.yards / 5 + stats.rushing.touchdowns * 15
        if stats.receiving.yards > 0:
            value += stats.receiving.yards / 5 + stats.receiving.touchdowns * 15
        if stats.defense.tackles > 0:
            value += stats.defense.tackles * 2 + stats.defense.sacks * 10

        if value > best_value:
            best_value = value
            best_player = stats

    if not best_player:
        return None

    # Build stat line
    stat_line = ""
    if best_player.passing.yards > 50:
        stat_line = f"{best_player.passing.completions}/{best_player.passing.attempts}, {best_player.passing.yards} yds, {best_player.passing.touchdowns} TD"
    elif best_player.rushing.yards > 20:
        stat_line = f"{best_player.rushing.attempts} car, {best_player.rushing.yards} yds, {best_player.rushing.touchdowns} TD"
    elif best_player.receiving.yards > 20:
        stat_line = f"{best_player.receiving.receptions} rec, {best_player.receiving.yards} yds, {best_player.receiving.touchdowns} TD"
    else:
        stat_line = f"{best_player.defense.tackles} tackles"

    return {
        "player_id": str(best_player.player_id),
        "name": best_player.player_name,
        "position": best_player.position,
        "stat_line": stat_line,
    }
