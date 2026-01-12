#!/usr/bin/env python3
"""
Test script for graph sync using historical season generation.

This script:
1. Generates a league with historical seasons
2. Syncs the data to Neo4j
3. Tests the exploration tools
4. Generates sample context cards

Prerequisites:
- Neo4j running: docker compose up -d neo4j
- Environment: GRAPH_ENABLED=true

Usage:
    GRAPH_ENABLED=true python scripts/test_graph_sync.py
"""

import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from huddle.graph.config import is_graph_enabled, set_graph_enabled
from huddle.graph.connection import get_graph
from huddle.graph.schema import init_schema, get_stats
from huddle.graph.sync import full_sync, sync_all_computed_properties
from huddle.graph.sync.historical import HistoricalGraphSync, sync_historical_simulation
from huddle.graph.explore import (
    explore,
    GraphTraversal,
    get_player_context,
    get_team_context,
    get_matchup_context,
    search_players,
    ContextGenerator,
    get_game_context_queue,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def generate_test_league():
    """Generate a test league with historical simulation.

    Returns:
        tuple: (SimulationResult, League) - result for historical sync, league for exploration
    """
    from huddle.generators.league import generate_league
    from huddle.core.simulation.historical_sim import HistoricalSimulator, SimulationConfig
    from huddle.core.league.league import League
    from huddle.core.league.nfl_data import NFL_TEAMS
    from huddle.core.models.team import Team

    logger.info("Generating test league with 4 seasons of history...")

    config = SimulationConfig(
        years_to_simulate=4,
        target_season=2024,
        verbose=True,
        progress_callback=lambda msg: logger.info(f"  {msg}"),
    )

    try:
        # Use NFL teams for proper division/conference structure
        sim = HistoricalSimulator.create_with_nfl_teams(config)
        result = sim.run()

        logger.info(f"Historical simulation complete:")
        logger.info(f"  Seasons simulated: {result.seasons_simulated}")
        logger.info(f"  Total transactions: {len(result.transaction_log.transactions)}")

        # Also build League object for exploration tests
        league = League(current_season=config.target_season)

        for team_id, team_state in result.teams.items():
            # Look up NFL team data
            nfl_data = NFL_TEAMS.get(team_id)
            if nfl_data:
                team = Team(
                    name=nfl_data.name,
                    abbreviation=nfl_data.abbreviation,
                    city=nfl_data.city,
                )
            else:
                team = Team(
                    name=team_state.team_name,
                    abbreviation=team_id,
                    city="City",
                )

            # Add players to roster
            for player in team_state.roster:
                team.roster.add_player(player)

            league.teams[team.abbreviation] = team

        logger.info(f"Built league with {len(league.teams)} teams, {sum(len(t.roster.players) for t in league.teams.values())} players")
        return result, league

    except Exception as e:
        logger.warning(f"Historical simulation failed: {e}")
        import traceback
        traceback.print_exc()
        logger.info("Falling back to simple league generator...")
        return None, generate_league()


def test_graph_connection():
    """Test Neo4j connection."""
    logger.info("Testing graph connection...")

    graph = get_graph()
    health = graph.health_check()

    if health.get("healthy"):
        logger.info(f"Neo4j connected: {health}")
        return True
    else:
        logger.error(f"Neo4j not healthy: {health}")
        return False


def test_full_sync(sim_result, league):
    """Test full sync of a league with historical data."""
    logger.info("Testing historical sync...")

    if sim_result:
        # Use historical sync which processes transactions for proper season tracking
        # clear_first=False because we already cleared at script start
        result = sync_historical_simulation(sim_result, clear_first=False)
    else:
        # Fallback to basic sync
        from huddle.graph.sync.base import full_sync
        result = full_sync(league)

    logger.info(f"Sync result: {result}")
    logger.info(f"  Nodes created: {result.nodes_created}")
    logger.info(f"  Relationships created: {result.relationships_created}")
    logger.info(f"  Errors: {result.errors}")

    return result.success


def test_computed_properties(league):
    """Test computed property sync."""
    logger.info("Testing computed properties...")

    from huddle.graph.sync.computed import sync_all_computed_properties

    result = sync_all_computed_properties(league)

    logger.info(f"Computed properties result: {result}")
    return result.success


def test_season_tracking():
    """Test that PLAYS_FOR relationships have proper season tracking."""
    logger.info("\n--- Testing Season Tracking ---")

    graph = get_graph()

    # Check PLAYS_FOR relationships have season data
    result = graph.run_query("""
    MATCH (p:Player)-[r:PLAYS_FOR]->(t:Team)
    WHERE r.from_season IS NOT NULL
    WITH r.from_season as from_s, r.to_season as to_s, r.is_current as current
    RETURN
        count(*) as total,
        sum(CASE WHEN current = true THEN 1 ELSE 0 END) as current_count,
        sum(CASE WHEN to_s IS NOT NULL THEN 1 ELSE 0 END) as historical_count,
        min(from_s) as earliest_season,
        max(from_s) as latest_season
    """)

    if result:
        row = result[0]
        logger.info(f"  Total PLAYS_FOR relationships: {row['total']}")
        logger.info(f"  Current (active): {row['current_count']}")
        logger.info(f"  Historical (ended): {row['historical_count']}")
        logger.info(f"  Season range: {row['earliest_season']} - {row['latest_season']}")

    # Find players who played for multiple teams
    result = graph.run_query("""
    MATCH (p:Player)-[r:PLAYS_FOR]->(t:Team)
    WITH p, count(t) as team_count, collect(t.abbr) as teams
    WHERE team_count > 1
    RETURN p.name as name, p.position as position, team_count, teams
    ORDER BY team_count DESC
    LIMIT 10
    """)

    logger.info(f"\n  Players with multiple teams:")
    if result:
        for row in result:
            logger.info(f"    {row['name']} ({row['position']}): {row['team_count']} teams - {row['teams']}")
    else:
        logger.info("    None found (all players stayed with one team)")

    # Show sample player career timeline
    result = graph.run_query("""
    MATCH (p:Player)-[r:PLAYS_FOR]->(t:Team)
    WITH p, collect({team: t.abbr, from: r.from_season, to: r.to_season, current: r.is_current}) as stints
    WHERE size(stints) > 1
    RETURN p.name as name, p.position as pos, stints
    LIMIT 3
    """)

    if result:
        logger.info(f"\n  Sample career timelines:")
        for row in result:
            logger.info(f"    {row['name']} ({row['pos']}):")
            for stint in row['stints']:
                end = "present" if stint.get('current') else str(stint.get('to'))
                logger.info(f"      {stint['team']}: {stint['from']} - {end}")


def test_exploration():
    """Test graph exploration tools."""
    logger.info("Testing exploration tools...")

    traversal = GraphTraversal()

    # Test exploring a team
    logger.info("\n--- Exploring Teams ---")
    team = traversal.explore("team", "PHI")
    if team:
        logger.info(f"Found team: {team}")
        logger.info(f"  Properties: {team.properties}")

        # Follow relationships
        players = team.follow("PLAYS_FOR", direction="incoming", limit=5)
        logger.info(f"  Top players: {players}")

        division = team.follow("IN_DIVISION")
        logger.info(f"  Division: {division}")
    else:
        logger.warning("Team PHI not found")

    # Test exploring a player
    logger.info("\n--- Exploring Players ---")
    result = search_players(position="QB", limit=3)
    if result.success:
        logger.info(f"Search result: {result.summary}")
        for p in result.data.get("players", []):
            logger.info(f"  QB: {p.get('name')} ({p.get('overall')} OVR)")

            # Explore one player in detail
            player_result = get_player_context(p.get("name", p.get("id")))
            if player_result.success:
                logger.info(f"    Team: {player_result.data.get('team', {}).get('properties', {}).get('name', 'Unknown')}")
                logger.info(f"    Career: {player_result.data.get('career_phase', {})}")
    else:
        logger.warning(f"Search failed: {result.summary}")

    # Test matchup context
    logger.info("\n--- Matchup Context ---")
    matchup = get_matchup_context("PHI", "DAL")
    if matchup.success:
        logger.info(f"Matchup: {matchup.summary}")
    else:
        logger.info(f"Matchup not found: {matchup.summary}")


def test_context_generation():
    """Test context card generation."""
    logger.info("Testing context generation...")

    generator = ContextGenerator()

    # Generate player context
    logger.info("\n--- Player Context Cards ---")
    cards = generator.generate_team_context("PHI")
    for card in cards:
        logger.info(f"  [{card.type.value}] {card.topic}: {card.content}")

    # Generate matchup context
    logger.info("\n--- Matchup Context Cards ---")
    cards = generator.generate_matchup_context("PHI", "DAL")
    for card in cards:
        logger.info(f"  [{card.type.value}] {card.topic}: {card.content}")

    # Get from queue
    queue = get_game_context_queue()
    relevant = queue.get_relevant(limit=5)
    logger.info(f"\nTop {len(relevant)} context cards in queue:")
    for card in relevant:
        logger.info(f"  [{card.relevance:.2f}] {card.topic}")


def test_graph_stats():
    """Print graph statistics."""
    logger.info("Graph statistics...")

    stats = get_stats()

    if "error" in stats:
        logger.error(f"Could not get stats: {stats}")
        return

    logger.info(f"Total nodes: {stats.get('total_nodes', 0)}")
    logger.info(f"Total relationships: {stats.get('total_relationships', 0)}")

    logger.info("Nodes by label:")
    for label, count in stats.get("nodes_by_label", {}).items():
        logger.info(f"  {label}: {count}")

    logger.info("Relationships by type:")
    for rel_type, count in stats.get("relationships_by_type", {}).items():
        logger.info(f"  {rel_type}: {count}")


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Graph Sync Test Script")
    logger.info("=" * 60)

    # Check if graph is enabled
    if not is_graph_enabled():
        logger.warning("Graph is disabled. Set GRAPH_ENABLED=true")
        logger.info("Enabling graph for this test...")
        set_graph_enabled(True)

    # Test connection
    if not test_graph_connection():
        logger.error("Cannot connect to Neo4j. Is it running?")
        logger.info("Start with: docker compose up -d neo4j")
        return 1

    # Clear graph and initialize schema
    logger.info("\nClearing graph and initializing schema...")
    graph = get_graph()
    graph.clear_all(confirm=True)
    init_schema()

    # Generate and sync league
    sim_result, league = generate_test_league()

    logger.info(f"\nLeague generated with {len(league.teams)} teams")

    if not test_full_sync(sim_result, league):
        logger.error("Full sync failed")
        return 1

    # Test computed properties
    test_computed_properties(league)

    # Test season tracking
    test_season_tracking()

    # Test exploration
    test_exploration()

    # Test context generation
    test_context_generation()

    # Print stats
    test_graph_stats()

    logger.info("\n" + "=" * 60)
    logger.info("All tests completed!")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("1. Open Neo4j Browser: http://localhost:7474")
    logger.info("2. Login with neo4j/huddlegraph")
    logger.info("3. Try: MATCH (n) RETURN n LIMIT 50")
    logger.info("4. Try: MATCH (p:Player)-[:PLAYS_FOR]->(t:Team) RETURN p, t LIMIT 20")

    return 0


if __name__ == "__main__":
    sys.exit(main())
