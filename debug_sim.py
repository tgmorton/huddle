#!/usr/bin/env python3
"""Debug script to trace field position."""

from huddle.generators import generate_team
from huddle.simulation import SimulationEngine


def main():
    """Run a debug trace of field position."""
    print("Generating teams...")
    home_team = generate_team("Eagles", "Philadelphia", "PHI", overall_range=(75, 85))
    away_team = generate_team("Cowboys", "Dallas", "DAL", overall_range=(75, 85))

    engine = SimulationEngine()
    game = engine.create_game(home_team, away_team)

    print(f"Initial possession: {'HOME' if game.possession.team_with_ball == home_team.id else 'AWAY'}")
    print(f"Initial field position: {game.down_state.line_of_scrimmage.yard_line} ({game.down_state.line_of_scrimmage.display})")
    print()

    # Simulate just 20 plays and trace field position
    for i in range(20):
        los_before = game.down_state.line_of_scrimmage.yard_line
        down_before = game.down_state.down
        ytg_before = game.down_state.yards_to_go

        result = engine.simulate_play_with_ai(game)

        los_after = game.down_state.line_of_scrimmage.yard_line

        offense = "HOME" if game.possession.team_with_ball == home_team.id else "AWAY"

        print(f"Play {i+1}: {down_before}&{ytg_before} at {los_before} -> {result.outcome.name} for {result.yards_gained} yds -> now at {los_after}")

        if result.is_touchdown:
            print(f"  >>> TOUCHDOWN! Score: {game.score.home_score}-{game.score.away_score}")
            print(f"  >>> Reset to: {game.down_state.line_of_scrimmage.yard_line}")

        if result.is_turnover:
            print(f"  >>> TURNOVER!")

        print(f"      Possession: {offense}, Down: {game.down_state.down}&{game.down_state.yards_to_go}")
        print()


if __name__ == "__main__":
    main()
