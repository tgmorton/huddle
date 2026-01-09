"""Entry point for huddle package."""

import argparse


def main() -> None:
    """Main entry point for the Huddle application."""
    parser = argparse.ArgumentParser(
        description="Huddle - American Football Simulator",
        prog="huddle",
    )
    parser.add_argument(
        "--home",
        type=str,
        default="Eagles",
        help="Home team name (default: Eagles)",
    )
    parser.add_argument(
        "--away",
        type=str,
        default="Cowboys",
        help="Away team name (default: Cowboys)",
    )

    args = parser.parse_args()

    from huddle.generators import generate_team
    from huddle.simulation import SimulationEngine

    print("Huddle - American Football Simulator")
    print("=" * 50)

    home_team = generate_team(args.home, "City", "HOM", overall_range=(75, 85))
    away_team = generate_team(args.away, "Town", "AWY", overall_range=(75, 85))

    print(f"Home: {home_team.full_name}")
    print(f"Away: {away_team.full_name}")
    print()

    engine = SimulationEngine()
    game = engine.create_game(home_team, away_team)
    engine.simulate_game(game)

    print()
    print(f"Final Score: {away_team.abbreviation} {game.score.away_score} - {home_team.abbreviation} {game.score.home_score}")


if __name__ == "__main__":
    main()
