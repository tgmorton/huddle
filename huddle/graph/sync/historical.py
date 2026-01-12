"""
Historical sync module for graph database.

Syncs data from historical simulation with proper season tracking.
Handles the PLAYS_FOR relationship lifecycle:
- from_season: When player joined team
- to_season: When player left (None if current)

Usage:
    from huddle.graph.sync.historical import HistoricalGraphSync

    # During simulation
    sync = HistoricalGraphSync()

    # After each season in simulator:
    sync.sync_season_end(season, teams, transaction_log)

    # Or process entire simulation result at once:
    sync.sync_simulation_result(result)
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime

from huddle.graph.connection import get_graph, GraphConnection, is_graph_enabled
from huddle.graph.schema import init_schema, NodeLabels, RelTypes
from huddle.graph.sync.base import SyncResult, sync_entity, sync_entity_by_key

logger = logging.getLogger(__name__)


@dataclass
class PlayerTeamHistory:
    """Tracks a player's team history across seasons."""
    player_id: str
    team_id: str
    from_season: int
    to_season: Optional[int] = None  # None means current


class HistoricalGraphSync:
    """
    Handles syncing historical simulation data to the graph.

    Tracks player-team relationships across seasons, properly closing
    old relationships when players change teams.
    """

    def __init__(self, graph: Optional[GraphConnection] = None):
        self.graph = graph or get_graph()
        # Track current player->team mappings
        # player_id -> (team_id, from_season)
        self._current_teams: dict[str, tuple[str, int]] = {}

    def sync_simulation_result(
        self,
        result: Any,  # SimulationResult
        clear_first: bool = True,
    ) -> SyncResult:
        """
        Sync an entire SimulationResult to the graph.

        Processes the transaction log to build complete player history.

        Args:
            result: SimulationResult from HistoricalSimulator
            clear_first: If True, clears graph before syncing

        Returns:
            SyncResult with operation stats
        """
        if not is_graph_enabled():
            return SyncResult(success=True)

        start = datetime.now()
        logger.info("Starting historical graph sync...")

        if clear_first:
            logger.info("Clearing existing graph data...")
            self.graph.clear_all(confirm=True)
            # Initialize schema after clear
            init_schema(self.graph)

        total_result = SyncResult(success=True)

        # 1. Sync organizational structure
        logger.info("Syncing NFL structure...")
        r = self._sync_nfl_structure()
        total_result = total_result + r

        # 2. Sync teams
        logger.info(f"Syncing {len(result.teams)} teams...")
        for team_id, team_state in result.teams.items():
            r = self._sync_team_state(team_state)
            total_result = total_result + r

        # 3. Process transaction log to build player histories
        logger.info(f"Processing {len(result.transaction_log.transactions)} transactions...")
        player_histories = self._build_player_histories(result.transaction_log)

        # 4. Sync all players with their histories
        all_players = {}
        for team_state in result.teams.values():
            for player in team_state.roster:
                all_players[str(player.id)] = player

        logger.info(f"Syncing {len(all_players)} players...")
        for player_id, player in all_players.items():
            history = player_histories.get(player_id, [])
            r = self._sync_player_with_history(player, history)
            total_result = total_result + r

        # 5. Sync season standings
        logger.info(f"Syncing {len(result.season_standings)} season standings...")
        for season, standings in result.season_standings.items():
            r = self._sync_season_standings(season, standings)
            total_result = total_result + r

        duration = (datetime.now() - start).total_seconds() * 1000
        total_result.duration_ms = duration

        logger.info(
            f"Historical sync complete: {total_result.nodes_created} nodes, "
            f"{total_result.relationships_created} relationships, "
            f"{len(total_result.errors)} errors, {duration:.0f}ms"
        )

        return total_result

    def sync_season_end(
        self,
        season: int,
        teams: dict[str, Any],  # team_id -> TeamState
        transaction_log: Any,
    ) -> SyncResult:
        """
        Sync state at the end of a season.

        Call this from the simulator's progress_callback after each season.

        Args:
            season: The season that just completed
            teams: Current team states
            transaction_log: Transaction log with all moves

        Returns:
            SyncResult
        """
        if not is_graph_enabled():
            return SyncResult(success=True)

        result = SyncResult(success=True)

        # Process transactions from this season to update PLAYS_FOR relationships
        season_transactions = transaction_log.get_by_season(season)

        for txn in season_transactions:
            if txn.transaction_type.name in ("DRAFT_SELECTION", "FA_SIGNING", "WAIVER_CLAIM"):
                # Player joined a team
                if txn.player_id:
                    r = self._handle_player_joins_team(
                        txn.player_id,
                        txn.team_id,
                        season,
                    )
                    result = result + r

            elif txn.transaction_type.name in ("CUT", "CUT_JUNE1"):
                # Player left team (no new team)
                if txn.player_id:
                    r = self._handle_player_leaves_team(
                        txn.player_id,
                        txn.team_id,
                        season,
                    )
                    result = result + r

            elif txn.transaction_type.name == "TRADE":
                # Player changed teams
                if txn.player_id:
                    # Left old team
                    r = self._handle_player_leaves_team(
                        txn.player_id,
                        txn.team_id,
                        season,
                    )
                    result = result + r
                    # Joined new team
                    if txn.other_team_id:
                        r = self._handle_player_joins_team(
                            txn.player_id,
                            txn.other_team_id,
                            season,
                        )
                        result = result + r

        return result

    def _sync_nfl_structure(self) -> SyncResult:
        """Sync NFL organizational structure."""
        result = SyncResult(success=True)

        # Conferences
        for conf in ["AFC", "NFC"]:
            r = sync_entity_by_key(
                NodeLabels.CONFERENCE, "name", conf,
                {"name": conf},
                self.graph
            )
            result = result + r

        # Divisions
        divisions = {
            "AFC East": "AFC", "AFC North": "AFC", "AFC South": "AFC", "AFC West": "AFC",
            "NFC East": "NFC", "NFC North": "NFC", "NFC South": "NFC", "NFC West": "NFC",
        }

        for div_name, conf_name in divisions.items():
            r = sync_entity_by_key(
                NodeLabels.DIVISION, "name", div_name,
                {"name": div_name},
                self.graph
            )
            result = result + r

            # Division -> Conference relationship
            r = self._sync_relationship_by_names(
                NodeLabels.DIVISION, div_name,
                RelTypes.IN_CONFERENCE,
                NodeLabels.CONFERENCE, conf_name,
            )
            result = result + r

        return result

    def _sync_team_state(self, team_state: Any) -> SyncResult:
        """Sync a TeamState to the graph."""
        from huddle.core.league.nfl_data import NFL_TEAMS

        abbr = team_state.team_id
        nfl_data = NFL_TEAMS.get(abbr)

        properties = {
            "abbr": abbr,
            "name": team_state.team_name,
            "wins": team_state.wins,
            "losses": team_state.losses,
            "made_playoffs": team_state.made_playoffs,
            "won_championship": team_state.won_championship,
        }

        if nfl_data:
            properties["city"] = nfl_data.city

        if team_state.status:
            properties["status"] = team_state.status.current_status.name

        result = sync_entity_by_key(
            NodeLabels.TEAM, "abbr", abbr,
            properties,
            self.graph
        )

        # Team -> Division relationship
        if nfl_data and nfl_data.division:
            div_name = nfl_data.division.value
            r = self._sync_relationship_by_names(
                NodeLabels.TEAM, abbr,
                RelTypes.IN_DIVISION,
                NodeLabels.DIVISION, div_name,
                from_key="abbr",
            )
            result = result + r

        return result

    def _build_player_histories(
        self,
        transaction_log: Any,
    ) -> dict[str, list[PlayerTeamHistory]]:
        """
        Build complete player histories from transaction log.

        Returns dict of player_id -> list of PlayerTeamHistory entries.
        """
        histories: dict[str, list[PlayerTeamHistory]] = {}
        current_teams: dict[str, tuple[str, int]] = {}  # player_id -> (team_id, from_season)

        # Sort transactions by date
        sorted_txns = sorted(
            transaction_log.transactions,
            key=lambda t: (t.season, t.transaction_date)
        )

        for txn in sorted_txns:
            player_id = txn.player_id
            if not player_id:
                continue

            if txn.transaction_type.name in ("DRAFT_SELECTION", "FA_SIGNING", "WAIVER_CLAIM", "PS_SIGN"):
                # Player joins team
                if player_id in current_teams:
                    # Close out previous stint
                    old_team_id, from_season = current_teams[player_id]
                    if player_id not in histories:
                        histories[player_id] = []
                    histories[player_id].append(PlayerTeamHistory(
                        player_id=player_id,
                        team_id=old_team_id,
                        from_season=from_season,
                        to_season=txn.season - 1,  # Left at end of previous season
                    ))

                # Start new stint
                current_teams[player_id] = (txn.team_id, txn.season)

            elif txn.transaction_type.name in ("CUT", "CUT_JUNE1", "RETIREMENT"):
                # Player leaves team
                if player_id in current_teams:
                    old_team_id, from_season = current_teams[player_id]
                    if player_id not in histories:
                        histories[player_id] = []
                    histories[player_id].append(PlayerTeamHistory(
                        player_id=player_id,
                        team_id=old_team_id,
                        from_season=from_season,
                        to_season=txn.season,
                    ))
                    del current_teams[player_id]

            elif txn.transaction_type.name == "TRADE":
                # Player changes teams
                if player_id in current_teams:
                    old_team_id, from_season = current_teams[player_id]
                    if player_id not in histories:
                        histories[player_id] = []
                    histories[player_id].append(PlayerTeamHistory(
                        player_id=player_id,
                        team_id=old_team_id,
                        from_season=from_season,
                        to_season=txn.season,
                    ))

                # Start with new team
                if txn.other_team_id:
                    current_teams[player_id] = (txn.other_team_id, txn.season)

        # Close out current team assignments (still active)
        for player_id, (team_id, from_season) in current_teams.items():
            if player_id not in histories:
                histories[player_id] = []
            histories[player_id].append(PlayerTeamHistory(
                player_id=player_id,
                team_id=team_id,
                from_season=from_season,
                to_season=None,  # Still active
            ))

        return histories

    def _sync_player_with_history(
        self,
        player: Any,
        history: list[PlayerTeamHistory],
    ) -> SyncResult:
        """Sync a player and all their team history."""
        properties = {
            "name": player.full_name,
            "position": player.position.value if hasattr(player.position, "value") else str(player.position),
            "age": player.age,
            "experience": player.experience_years,
            "overall": player.overall,
            "potential": player.potential,
        }

        if hasattr(player, "personality") and player.personality:
            if hasattr(player.personality, "archetype") and player.personality.archetype:
                properties["personality_archetype"] = player.personality.archetype.value

        result = sync_entity(NodeLabels.PLAYER, player.id, properties, self.graph)

        # Create PLAYS_FOR relationships for each team stint
        for stint in history:
            rel_props = {
                "from_season": stint.from_season,
            }
            if stint.to_season is not None:
                rel_props["to_season"] = stint.to_season
            else:
                rel_props["is_current"] = True

            r = self._sync_plays_for(
                str(player.id),
                stint.team_id,
                rel_props,
            )
            result = result + r

        return result

    def _sync_plays_for(
        self,
        player_id: str,
        team_abbr: str,
        properties: dict,
    ) -> SyncResult:
        """Sync a PLAYS_FOR relationship with season tracking."""
        try:
            # Use MERGE with from_season to allow multiple stints
            query = """
            MATCH (p:Player {id: $player_id})
            MATCH (t:Team {abbr: $team_abbr})
            MERGE (p)-[r:PLAYS_FOR {from_season: $from_season}]->(t)
            SET r += $properties
            RETURN r
            """

            params = {
                "player_id": player_id,
                "team_abbr": team_abbr,
                "from_season": properties["from_season"],
                "properties": properties,
            }

            self.graph.run_write(query, params)
            return SyncResult(success=True, relationships_created=1)

        except Exception as e:
            logger.error(f"Failed to sync PLAYS_FOR: {e}")
            return SyncResult(success=False, errors=[str(e)])

    def _sync_season_standings(
        self,
        season: int,
        standings: list,
    ) -> SyncResult:
        """Sync season standings (SeasonSnapshot objects)."""
        result = SyncResult(success=True)

        # Create Season node
        r = sync_entity_by_key(
            NodeLabels.SEASON, "year", str(season),
            {"year": season},
            self.graph
        )
        result = result + r

        # Create standings relationships for each team
        for i, snapshot in enumerate(standings):
            try:
                query = """
                MATCH (t:Team {abbr: $team_id})
                MATCH (s:Season {year: $season})
                MERGE (t)-[r:SEASON_RECORD {season: $season}]->(s)
                SET r.wins = $wins,
                    r.losses = $losses,
                    r.standing = $standing,
                    r.made_playoffs = $made_playoffs,
                    r.won_championship = $won_championship
                RETURN r
                """

                params = {
                    "team_id": snapshot.team_id,
                    "season": season,
                    "wins": snapshot.wins,
                    "losses": snapshot.losses,
                    "standing": i + 1,
                    "made_playoffs": snapshot.made_playoffs,
                    "won_championship": snapshot.won_championship,
                }

                self.graph.run_write(query, params)
                result.relationships_created += 1

            except Exception as e:
                result.errors.append(str(e))

        return result

    def _handle_player_joins_team(
        self,
        player_id: str,
        team_id: str,
        season: int,
    ) -> SyncResult:
        """Handle a player joining a team mid-simulation."""
        # Check if player already has a current team
        if player_id in self._current_teams:
            old_team, from_season = self._current_teams[player_id]
            # Close out old relationship
            self._close_plays_for(player_id, old_team, season - 1)

        # Track new team
        self._current_teams[player_id] = (team_id, season)

        # Create new PLAYS_FOR
        return self._sync_plays_for(
            player_id,
            team_id,
            {"from_season": season, "is_current": True},
        )

    def _handle_player_leaves_team(
        self,
        player_id: str,
        team_id: str,
        season: int,
    ) -> SyncResult:
        """Handle a player leaving a team."""
        if player_id in self._current_teams:
            del self._current_teams[player_id]

        return self._close_plays_for(player_id, team_id, season)

    def _close_plays_for(
        self,
        player_id: str,
        team_abbr: str,
        to_season: int,
    ) -> SyncResult:
        """Close out a PLAYS_FOR relationship."""
        try:
            query = """
            MATCH (p:Player {id: $player_id})-[r:PLAYS_FOR]->(t:Team {abbr: $team_abbr})
            WHERE r.is_current = true
            SET r.to_season = $to_season,
                r.is_current = false
            RETURN r
            """

            self.graph.run_write(query, {
                "player_id": player_id,
                "team_abbr": team_abbr,
                "to_season": to_season,
            })

            return SyncResult(success=True)

        except Exception as e:
            logger.error(f"Failed to close PLAYS_FOR: {e}")
            return SyncResult(success=False, errors=[str(e)])

    def _sync_relationship_by_names(
        self,
        from_label: str,
        from_value: str,
        rel_type: str,
        to_label: str,
        to_value: str,
        from_key: str = "name",
        to_key: str = "name",
    ) -> SyncResult:
        """Sync a relationship using name-based lookups."""
        try:
            query = f"""
            MATCH (a:{from_label} {{{from_key}: $from_value}})
            MATCH (b:{to_label} {{{to_key}: $to_value}})
            MERGE (a)-[r:{rel_type}]->(b)
            RETURN r
            """

            self.graph.run_write(query, {
                "from_value": from_value,
                "to_value": to_value,
            })

            return SyncResult(success=True, relationships_created=1)

        except Exception as e:
            logger.error(f"Failed to sync relationship: {e}")
            return SyncResult(success=False, errors=[str(e)])


def sync_historical_simulation(
    result: Any,  # SimulationResult
    clear_first: bool = True,
) -> SyncResult:
    """
    Convenience function to sync a SimulationResult to the graph.

    Args:
        result: SimulationResult from HistoricalSimulator
        clear_first: If True, clears graph before syncing

    Returns:
        SyncResult
    """
    sync = HistoricalGraphSync()
    return sync.sync_simulation_result(result, clear_first=clear_first)
