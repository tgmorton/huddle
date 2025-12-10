#!/usr/bin/env python3
"""Debug script to trace what's happening."""

from huddle.core.enums import PlayOutcome
from huddle.generators import generate_team
from huddle.simulation import SimulationEngine


def main():
    """Run a debug trace."""
    home_team = generate_team("Eagles", "Philadelphia", "PHI", overall_range=(75, 85))
    away_team = generate_team("Cowboys", "Dallas", "DAL", overall_range=(75, 85))

    engine = SimulationEngine()
    game = engine.create_game(home_team, away_team)

    print(f"Initial: {game.down_state.down}&{game.down_state.yards_to_go} at {game.down_state.line_of_scrimmage.display}")
    print()

    # Simulate 30 plays and show each one
    for i in range(30):
        down_before = game.down_state.down
        ytg_before = game.down_state.yards_to_go
        los_before = game.down_state.line_of_scrimmage.display
        poss_before = "HOME" if game.possession.team_with_ball == home_team.id else "AWAY"

        result = engine.simulate_play_with_ai(game)

        down_after = game.down_state.down
        ytg_after = game.down_state.yards_to_go
        los_after = game.down_state.line_of_scrimmage.display
        poss_after = "HOME" if game.possession.team_with_ball == home_team.id else "AWAY"

        clock_info = f"Q{game.clock.quarter} {game.clock.display}"
        clock_stop = f" [CLOCK STOP: {result.clock_stop_reason}]" if result.clock_stopped else ""

        print(f"Play {i+1}: ({clock_info})")
        print(f"  BEFORE: {poss_before} ball, {down_before}&{ytg_before} at {los_before}")
        print(f"  RESULT: {result.outcome.name} for {result.yards_gained} yds - {result.description}{clock_stop}")
        print(f"  AFTER:  {poss_after} ball, {down_after}&{ytg_after} at {los_after}")
        print()


if __name__ == "__main__":
    main()
