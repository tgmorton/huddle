#!/usr/bin/env python3
"""Demo script to test the football simulation."""

from pathlib import Path

from huddle.core.enums import PlayOutcome
from huddle.events import EventBus, PlayCompletedEvent, ScoringEvent, TurnoverEvent, GameEndEvent
from huddle.generators import generate_team
from huddle.logging import GameLog, MarkdownGameWriter
from huddle.simulation import SimulationEngine


def main():
    """Run a demo game simulation."""
    print("=" * 60)
    print("HUDDLE - American Football Simulator Demo")
    print("=" * 60)
    print()

    # Generate two teams
    print("Generating teams...")
    home_team = generate_team("Eagles", "Philadelphia", "PHI", overall_range=(75, 85))
    away_team = generate_team("Cowboys", "Dallas", "DAL", overall_range=(75, 85))

    print(f"Home: {home_team.full_name} ({home_team.abbreviation})")
    print(f"  QB: {home_team.get_qb()}")
    print(f"  RB: {home_team.get_rb()}")
    print(f"  Offense Rating: {home_team.calculate_offense_rating()}")
    print(f"  Defense Rating: {home_team.calculate_defense_rating()}")
    print()

    print(f"Away: {away_team.full_name} ({away_team.abbreviation})")
    print(f"  QB: {away_team.get_qb()}")
    print(f"  RB: {away_team.get_rb()}")
    print(f"  Offense Rating: {away_team.calculate_offense_rating()}")
    print(f"  Defense Rating: {away_team.calculate_defense_rating()}")
    print()

    # Set up event handlers
    event_bus = EventBus()

    stats = {
        "plays": 0,
        "tds": 0,
        "fgs": 0,
        "punts": 0,
        "turnovers": 0,
        "three_and_outs": 0,
    }

    def on_play(event: PlayCompletedEvent):
        stats["plays"] += 1
        result = event.result

        # Show key plays
        show = (
            stats["plays"] <= 15  # First 15 plays
            or result.is_touchdown
            or result.is_turnover
            or result.outcome == PlayOutcome.PUNT_RESULT
            or result.outcome in (PlayOutcome.FIELD_GOAL_GOOD, PlayOutcome.FIELD_GOAL_MISSED)
        )

        if show:
            print(f"Q{event.quarter} {event.time_remaining} | {event.down}&{event.yards_to_go} at {event.field_position} | {result.description}")

        if result.outcome == PlayOutcome.PUNT_RESULT:
            stats["punts"] += 1

    def on_scoring(event: ScoringEvent):
        if event.scoring_type == "TD":
            stats["tds"] += 1
        elif event.scoring_type == "FG":
            stats["fgs"] += 1
        print(f"  >>> SCORE: {event.scoring_type} - Now {event.home_score}-{event.away_score}")

    def on_turnover(event: TurnoverEvent):
        stats["turnovers"] += 1
        print(f"  >>> TURNOVER: {event.turnover_type}")

    def on_game_end(event: GameEndEvent):
        print()
        print("=" * 60)
        print("FINAL SCORE")
        print("=" * 60)
        print(f"{away_team.abbreviation} {event.final_away_score} @ {home_team.abbreviation} {event.final_home_score}")

    event_bus.subscribe(PlayCompletedEvent, on_play)
    event_bus.subscribe(ScoringEvent, on_scoring)
    event_bus.subscribe(TurnoverEvent, on_turnover)
    event_bus.subscribe(GameEndEvent, on_game_end)

    # Set up game log for markdown output
    game_log = GameLog(
        home_abbrev=home_team.abbreviation,
        away_abbrev=away_team.abbreviation,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
    )
    game_log.connect_to_event_bus(event_bus)

    # Create and run simulation
    print("-" * 60)
    print("GAME START")
    print("-" * 60)

    engine = SimulationEngine(event_bus=event_bus)
    game = engine.create_game(home_team, away_team)

    # Set initial possession for game log
    game_log.set_possession(game.possession.team_with_ball == home_team.id)

    receiving_team = home_team if game.possession.team_with_ball == home_team.id else away_team
    print(f"{receiving_team.abbreviation} receives the opening kickoff")
    print()

    # Simulate the full game
    engine.simulate_game(game)

    print()
    print("-" * 60)
    print("GAME STATS")
    print("-" * 60)
    print(f"Total plays: {stats['plays']}")
    print(f"Touchdowns: {stats['tds']}")
    print(f"Field Goals: {stats['fgs']}")
    print(f"Punts: {stats['punts']}")
    print(f"Turnovers: {stats['turnovers']}")

    # Write markdown summary
    writer = MarkdownGameWriter()
    output_path = Path("game_summary.md")
    writer.write_game_summary(game, game_log, home_team, away_team, output_path)
    print()
    print(f"Game summary written to: {output_path}")


if __name__ == "__main__":
    main()
