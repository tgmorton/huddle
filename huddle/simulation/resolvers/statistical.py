"""Statistical play resolver using probability-based simulation."""

import random
from typing import Optional

from huddle.core.enums import (
    DefensiveScheme,
    Formation,
    PassType,
    PenaltyType,
    PersonnelPackage,
    PlayOutcome,
    PlayType,
    RunType,
)
from huddle.core.models.field import FieldPosition
from huddle.core.models.game import GameState
from huddle.core.models.play import DefensiveCall, PlayCall, PlayResult
from huddle.core.models.player import Player
from huddle.core.models.team import Team
from huddle.simulation.resolvers.base import PlayResolver


class StatisticalPlayResolver(PlayResolver):
    """
    Play-by-play resolver using statistical/probability-based simulation.

    Player attributes affect outcomes through matchup calculations.
    This is the primary resolver for detailed simulation.
    """

    # Position-weighted stat attribution
    # Tackle probability weights by position (MLB/ILB lead in tackles)
    TACKLE_WEIGHTS = {
        "MLB1": 0.22, "MLB2": 0.10,
        "ILB1": 0.18, "ILB2": 0.08,
        "OLB1": 0.09, "OLB2": 0.07,
        "SS1": 0.07, "SS2": 0.03,
        "FS1": 0.05, "FS2": 0.02,
        "CB1": 0.03, "CB2": 0.03,
        "DE1": 0.015, "DE2": 0.015,
        "DT1": 0.01, "DT2": 0.01,
    }

    # Sack probability weights by position (Edge rushers dominate)
    SACK_WEIGHTS = {
        "DE1": 0.28, "DE2": 0.22,
        "OLB1": 0.16, "OLB2": 0.12,
        "DT1": 0.10, "DT2": 0.07,
        "MLB1": 0.03, "MLB2": 0.01,
        "CB1": 0.005, "SS1": 0.005,
    }

    # Interception probability weights by position (CBs and safeties)
    INT_WEIGHTS = {
        "CB1": 0.28, "CB2": 0.22,
        "FS1": 0.20, "FS2": 0.05,
        "SS1": 0.12, "SS2": 0.03,
        "MLB1": 0.06, "MLB2": 0.02,
        "OLB1": 0.01, "OLB2": 0.01,
    }

    # TFL (tackle for loss) weights - DL heavy
    TFL_WEIGHTS = {
        "DT1": 0.22, "DT2": 0.16,
        "DE1": 0.18, "DE2": 0.14,
        "MLB1": 0.10, "MLB2": 0.05,
        "OLB1": 0.07, "OLB2": 0.04,
        "SS1": 0.02, "CB1": 0.01, "CB2": 0.01,
    }

    # Rotation chance - probability of using a backup instead of starter
    ROTATION_CHANCE = 0.15

    # Base completion percentages by pass type (NFL averages ~65% overall)
    # These are base rates before attribute modifiers
    BASE_COMPLETION_RATES = {
        PassType.SCREEN: 0.72,
        PassType.SHORT: 0.58,
        PassType.MEDIUM: 0.42,
        PassType.DEEP: 0.28,
        PassType.HAIL_MARY: 0.06,
    }

    # Base yards gained distributions (mean, std_dev)
    # NFL average: ~5.5 yards per completion, ~4.0 yards per rush
    PASS_YARDS_DISTRIBUTION = {
        PassType.SCREEN: (1, 3),      # Often negative or short
        PassType.SHORT: (4, 2),       # Reliable short gains
        PassType.MEDIUM: (11, 3),     # 10-15 yard range
        PassType.DEEP: (22, 7),       # Big play potential
        PassType.HAIL_MARY: (35, 10),
    }

    RUN_YARDS_DISTRIBUTION = {
        RunType.INSIDE: (2.8, 2.2),   # Lots of 0-2 yard gains, occasional breakout
        RunType.OUTSIDE: (3.0, 3.0),  # More variance outside
        RunType.DRAW: (3.2, 2.5),
        RunType.OPTION: (3.5, 3.5),
        RunType.QB_SNEAK: (0.8, 0.6), # Short yardage
        RunType.QB_SCRAMBLE: (4.0, 4.0),
    }

    def resolve_play(
        self,
        game_state: GameState,
        offensive_team: Team,
        defensive_team: Team,
        offensive_call: PlayCall,
        defensive_call: DefensiveCall,
    ) -> PlayResult:
        """Resolve a play using statistical simulation."""
        if offensive_call.play_type == PlayType.PASS:
            return self._resolve_pass_play(
                game_state, offensive_team, defensive_team, offensive_call, defensive_call
            )
        elif offensive_call.play_type == PlayType.RUN:
            return self._resolve_run_play(
                game_state, offensive_team, defensive_team, offensive_call, defensive_call
            )
        elif offensive_call.play_type == PlayType.PUNT:
            return self._resolve_punt(game_state, offensive_team, offensive_call, defensive_call)
        elif offensive_call.play_type == PlayType.FIELD_GOAL:
            return self._resolve_field_goal(
                game_state, offensive_team, offensive_call, defensive_call
            )
        elif offensive_call.play_type == PlayType.KICKOFF:
            return self._resolve_kickoff(
                game_state, offensive_team, defensive_team, offensive_call, defensive_call
            )
        elif offensive_call.play_type == PlayType.EXTRA_POINT:
            return self._resolve_extra_point(
                game_state, offensive_team, offensive_call, defensive_call
            )
        elif offensive_call.play_type == PlayType.TWO_POINT:
            return self._resolve_two_point(
                game_state, offensive_team, defensive_team, offensive_call, defensive_call
            )
        else:
            # Default: treat as run
            return self._resolve_run_play(
                game_state, offensive_team, defensive_team, offensive_call, defensive_call
            )

    def _resolve_pass_play(
        self,
        game_state: GameState,
        offense: Team,
        defense: Team,
        call: PlayCall,
        def_call: DefensiveCall,
    ) -> PlayResult:
        """Resolve a passing play."""
        # Check for pre-snap penalty first
        pre_snap_penalty = self._check_pre_snap_penalty(offense, defense)
        if pre_snap_penalty:
            penalty_type, is_on_offense = pre_snap_penalty
            return self._create_penalty_result(call, def_call, penalty_type, is_on_offense, game_state)

        # Get key players based on personnel package
        qb = offense.get_starter("QB1")
        receivers = self._get_receivers(offense, call.personnel)
        pass_rushers = self._get_pass_rushers(defense)
        coverage_players = self._get_coverage_players(defense)

        if not qb or not receivers:
            return self._incomplete_pass(call, def_call, None)

        pass_type = call.pass_type or PassType.SHORT

        # Check for sack first
        sack_chance = self._calculate_sack_probability(offense, defense, def_call)
        if random.random() < sack_chance:
            return self._create_sack_result(game_state, call, def_call, qb, defense)

        # Select target
        target = self._select_target(receivers, pass_type, coverage_players)
        if not target:
            return self._incomplete_pass(call, def_call, qb)

        # Calculate completion probability with formation modifier
        completion_prob = self._calculate_completion_probability(
            qb, target, pass_type, def_call, coverage_players, call.formation
        )

        # Roll for completion
        roll = random.random()
        was_complete = roll < completion_prob

        # Check for penalty during play (may override result)
        play_penalty = self._check_pass_play_penalty(offense, defense, def_call, was_complete, pass_type)
        if play_penalty:
            penalty_type, is_on_offense, yards_to_target = play_penalty
            # Offensive penalty negates the play
            if is_on_offense:
                return self._create_penalty_result(call, def_call, penalty_type, True, game_state)
            # Defensive penalty - offense can decline if play was good
            # For now, always accept defensive penalties on incomplete passes
            if not was_complete or penalty_type.is_automatic_first_down:
                return self._create_penalty_result(call, def_call, penalty_type, False, game_state, yards_to_target)

        if was_complete:
            # Completion - calculate yards
            yards = self._calculate_pass_yards(pass_type, target, coverage_players, game_state)
            return self._create_completion_result(
                game_state, call, def_call, qb, target, yards, coverage_players
            )

        # Check for interception
        int_chance = self._calculate_interception_probability(
            qb, pass_type, def_call, coverage_players
        )
        if random.random() < int_chance:
            return self._create_interception_result(
                game_state, call, def_call, qb, defense
            )

        # Incomplete pass
        return self._incomplete_pass(call, def_call, qb)

    def _resolve_run_play(
        self,
        game_state: GameState,
        offense: Team,
        defense: Team,
        call: PlayCall,
        def_call: DefensiveCall,
    ) -> PlayResult:
        """Resolve a running play."""
        # Check for pre-snap penalty first
        pre_snap_penalty = self._check_pre_snap_penalty(offense, defense)
        if pre_snap_penalty:
            penalty_type, is_on_offense = pre_snap_penalty
            return self._create_penalty_result(call, def_call, penalty_type, is_on_offense, game_state)

        rb = offense.get_starter("RB1")
        if not rb:
            rb = offense.get_starter("QB1")  # QB scramble fallback

        if not rb:
            return self._create_minimal_run_result(call, def_call, 0)

        run_type = call.run_type or RunType.INSIDE

        # Calculate yards based on matchups
        ol_rating = self._calculate_oline_rating(offense)
        dl_rating = self._calculate_dline_rating(defense)
        line_advantage = (ol_rating - dl_rating) / 100  # -1 to +1

        # Base yards from distribution
        mean, std = self.RUN_YARDS_DISTRIBUTION.get(run_type, (4.0, 3.0))
        base_yards = random.gauss(mean, std)

        # Modify by matchups
        yards = base_yards + (line_advantage * 2)

        # Modify by RB attributes
        rb_mod = self._calculate_rb_modifier(rb, run_type)
        yards = yards * rb_mod

        # Apply formation modifier for run plays
        if call.formation:
            yards = yards * call.formation.run_modifier

        # Check for big play (breakaway) - rare event ~1-2% of runs
        speed = rb.get_attribute("speed")
        breakaway_chance = 0.012 * (speed / 99)
        if random.random() < breakaway_chance:
            yards += random.randint(8, 20)

        yards = int(max(-5, yards))

        # Check for safety (tackled in own end zone)
        current_los = game_state.down_state.line_of_scrimmage.yard_line
        if current_los + yards <= 0:
            tackler = self._select_tackler(defense, run_type)
            return self._create_safety_result(
                game_state, call, def_call, rb, tackler, yards, is_sack=False
            )

        # Check for penalty during play
        run_penalty = self._check_run_play_penalty(offense, defense)
        if run_penalty:
            penalty_type, is_on_offense = run_penalty
            # Offensive holding usually called when offense gains yards
            if is_on_offense and yards > 3:
                return self._create_penalty_result(call, def_call, penalty_type, True, game_state)
            # Defensive penalty on negative play - accept it
            if not is_on_offense and yards < 3:
                return self._create_penalty_result(call, def_call, penalty_type, False, game_state)

        # Check for fumble
        carrying = rb.get_attribute("carrying")
        fumble_chance = 0.015 * (100 - carrying) / 100
        is_fumble = random.random() < fumble_chance

        # Check for touchdown
        current_los = game_state.down_state.line_of_scrimmage.yard_line
        is_td = (current_los + yards) >= 100 and not is_fumble

        # Get tackler
        tackler = self._select_tackler(defense, run_type)

        # Handle fumble with possible return
        if is_fumble:
            return self._create_fumble_result(
                game_state, call, def_call, rb, yards, current_los, defense
            )

        # Check first down
        is_first_down = yards >= game_state.down_state.yards_to_go

        # Check if runner went out of bounds (~10% chance on outside runs, less on inside)
        if run_type in (RunType.OUTSIDE, RunType.OPTION):
            out_of_bounds_chance = 0.15
        else:
            out_of_bounds_chance = 0.05
        went_out_of_bounds = random.random() < out_of_bounds_chance

        # Generate description
        description = self._generate_run_description(rb, yards, is_td, False, tackler)
        if went_out_of_bounds and not is_td:
            description += " (out of bounds)"

        # Determine clock stoppage
        clock_stopped = is_td or went_out_of_bounds
        clock_stop_reason = None
        if is_td:
            clock_stop_reason = "touchdown"
        elif went_out_of_bounds:
            clock_stop_reason = "out_of_bounds"

        # Time elapsed is less if clock stops
        if clock_stopped:
            time_elapsed = random.randint(5, 12)
        else:
            time_elapsed = random.randint(25, 40)

        return PlayResult(
            play_call=call,
            defensive_call=def_call,
            outcome=PlayOutcome.TOUCHDOWN if is_td else PlayOutcome.RUSH,
            yards_gained=yards,
            time_elapsed_seconds=time_elapsed,
            rusher_id=rb.id,
            tackler_id=tackler.id if tackler else None,
            is_first_down=is_first_down and not is_td,
            is_touchdown=is_td,
            clock_stopped=clock_stopped,
            clock_stop_reason=clock_stop_reason,
            points_scored=6 if is_td else 0,
            description=description,
        )

    def _create_fumble_result(
        self,
        game_state: GameState,
        call: PlayCall,
        def_call: DefensiveCall,
        rusher: Player,
        yards_before_fumble: int,
        current_los: int,
        defense: Team,
    ) -> PlayResult:
        """Create a fumble result with possible defensive return."""
        # Fumble spot is where the runner was when fumble occurred
        fumble_spot = current_los + yards_before_fumble

        # Pick a defender to recover
        recoverer = self._select_tackler(defense, call.run_type or RunType.INSIDE)

        # Calculate return yards
        return_yards, is_return_td = self._calculate_turnover_return(
            recoverer, 0, fumble_spot  # turnover_spot=0 since fumble is at fumble_spot
        )

        if is_return_td:
            description = f"{rusher.display_name} rush for {yards_before_fumble} yards, FUMBLES!"
            if recoverer:
                description += f" {recoverer.display_name} recovers and returns for TOUCHDOWN!"
            else:
                description += " Returned for TOUCHDOWN!"

            return PlayResult(
                play_call=call,
                defensive_call=def_call,
                outcome=PlayOutcome.FUMBLE_LOST,
                yards_gained=yards_before_fumble + return_yards,
                time_elapsed_seconds=random.randint(10, 18),
                rusher_id=rusher.id,
                fumble_recovered_by_id=recoverer.id if recoverer else None,
                is_turnover=True,
                is_touchdown=True,
                points_scored=6,
                clock_stopped=True,
                clock_stop_reason="touchdown",
                description=description,
            )

        description = f"{rusher.display_name} rush for {yards_before_fumble} yards, FUMBLES!"
        if recoverer:
            description += f" Recovered by {recoverer.display_name}"
            if return_yards > 0:
                description += f", returned {return_yards} yards"

        return PlayResult(
            play_call=call,
            defensive_call=def_call,
            outcome=PlayOutcome.FUMBLE_LOST,
            yards_gained=yards_before_fumble + return_yards,
            time_elapsed_seconds=random.randint(8, 15),
            rusher_id=rusher.id,
            fumble_recovered_by_id=recoverer.id if recoverer else None,
            is_turnover=True,
            clock_stopped=True,
            clock_stop_reason="turnover",
            description=description,
        )

    def _resolve_punt(
        self,
        game_state: GameState,
        offense: Team,
        call: PlayCall,
        def_call: DefensiveCall,
    ) -> PlayResult:
        """Resolve a punt play."""
        punter = offense.get_starter("P1")
        kick_power = punter.get_attribute("kick_power") if punter else 70

        # Calculate punt distance
        base_distance = 35 + (kick_power - 50) * 0.3
        distance = int(base_distance + random.gauss(0, 5))
        distance = max(20, min(65, distance))

        # Net yards (considering return)
        return_yards = random.randint(0, 15)
        net_yards = distance - return_yards

        return PlayResult(
            play_call=call,
            defensive_call=def_call,
            outcome=PlayOutcome.PUNT_RESULT,
            yards_gained=-net_yards,  # Negative because possession changes
            time_elapsed_seconds=random.randint(8, 15),
            description=f"Punt for {distance} yards, {return_yards} yard return",
        )

    def _resolve_field_goal(
        self,
        game_state: GameState,
        offense: Team,
        call: PlayCall,
        def_call: DefensiveCall,
    ) -> PlayResult:
        """Resolve a field goal attempt."""
        kicker = offense.get_starter("K1")
        accuracy = kicker.get_attribute("kick_accuracy") if kicker else 70
        power = kicker.get_attribute("kick_power") if kicker else 70

        # Calculate distance
        los = game_state.down_state.line_of_scrimmage.yard_line
        distance = 100 - los + 17  # Add 17 for snap + hold

        # Calculate make probability
        # Base: 95% at 20 yards, drops off with distance
        if distance <= 30:
            base_prob = 0.95
        elif distance <= 40:
            base_prob = 0.85
        elif distance <= 50:
            base_prob = 0.70
        elif distance <= 55:
            base_prob = 0.50
        else:
            base_prob = 0.30

        # Modify by kicker attributes
        attr_mod = ((accuracy + power) / 2 - 50) / 100
        make_prob = base_prob + (attr_mod * 0.15)
        make_prob = max(0.05, min(0.99, make_prob))

        is_good = random.random() < make_prob

        return PlayResult(
            play_call=call,
            defensive_call=def_call,
            outcome=PlayOutcome.FIELD_GOAL_GOOD if is_good else PlayOutcome.FIELD_GOAL_MISSED,
            yards_gained=0,
            time_elapsed_seconds=random.randint(8, 15),
            points_scored=3 if is_good else 0,
            description=f"{distance} yard field goal {'GOOD' if is_good else 'NO GOOD'}",
        )

    # Helper methods

    def _get_receivers(
        self, team: Team, personnel: Optional[PersonnelPackage] = None
    ) -> list[Player]:
        """Get available receivers from team based on personnel package."""
        receivers = []

        if personnel:
            # Use personnel-specific slots
            depth_slots = personnel.get_depth_slots()
            for slot in depth_slots:
                # Skip QB - they're not a receiver
                if slot == "QB1":
                    continue
                if player := team.get_starter(slot):
                    receivers.append(player)
        else:
            # Default receiver slots
            for slot in ["WR1", "WR2", "WR3", "TE1", "RB1"]:
                if player := team.get_starter(slot):
                    receivers.append(player)

        return receivers

    def _get_pass_rushers(self, team: Team) -> list[Player]:
        """Get pass rushers from defense."""
        rushers = []
        for slot in ["DE1", "DE2", "DT1", "DT2", "OLB1", "OLB2"]:
            if player := team.get_starter(slot):
                rushers.append(player)
        return rushers

    def _get_coverage_players(self, team: Team) -> list[Player]:
        """Get coverage players from defense."""
        coverage = []
        for slot in ["CB1", "CB2", "FS1", "SS1", "MLB1"]:
            if player := team.get_starter(slot):
                coverage.append(player)
        return coverage

    def _calculate_sack_probability(
        self, offense: Team, defense: Team, def_call: DefensiveCall
    ) -> float:
        """Calculate probability of a sack."""
        # Base sack rate ~7% (NFL average is about 6-7%)
        base_rate = 0.07

        # Increase for blitzes
        if def_call.is_blitz:
            base_rate += 0.05 * (def_call.blitz_count - 4)

        # Modify by O-line vs D-line
        ol_rating = self._calculate_oline_rating(offense)
        dl_rating = self._calculate_dline_rating(defense)
        line_diff = (dl_rating - ol_rating) / 100

        return max(0.03, min(0.25, base_rate + line_diff * 0.12))

    def _calculate_completion_probability(
        self,
        qb: Player,
        target: Player,
        pass_type: PassType,
        def_call: DefensiveCall,
        coverage: list[Player],
        formation: Optional[Formation] = None,
    ) -> float:
        """Calculate probability of completion."""
        base_rate = self.BASE_COMPLETION_RATES.get(pass_type, 0.60)

        # QB accuracy modifier
        if pass_type == PassType.SHORT or pass_type == PassType.SCREEN:
            acc = qb.get_attribute("throw_accuracy_short")
        elif pass_type == PassType.MEDIUM:
            acc = qb.get_attribute("throw_accuracy_med")
        else:
            acc = qb.get_attribute("throw_accuracy_deep")

        qb_mod = (acc - 50) / 200  # ±25%

        # Receiver modifier
        catching = target.get_attribute("catching")
        route = target.get_attribute("route_running")
        rec_mod = ((catching + route) / 2 - 50) / 200

        # Coverage modifier
        if coverage:
            avg_coverage = sum(
                p.get_attribute("man_coverage") + p.get_attribute("zone_coverage")
                for p in coverage
            ) / (len(coverage) * 2)
            cov_mod = -(avg_coverage - 50) / 200
        else:
            cov_mod = 0

        # Apply formation modifier
        formation_mod = 1.0
        if formation:
            formation_mod = formation.pass_modifier

        raw_prob = base_rate + qb_mod + rec_mod + cov_mod
        return max(0.10, min(0.95, raw_prob * formation_mod))

    def _calculate_interception_probability(
        self,
        qb: Player,
        pass_type: PassType,
        def_call: DefensiveCall,
        coverage: list[Player],
    ) -> float:
        """Calculate probability of interception on incomplete pass."""
        # Base INT rate - this is conditional on incompletion
        # NFL INT rate is ~2.5% of attempts, ~6% of incompletions
        base_rate = 0.06

        # Deep passes more likely to be intercepted
        depth_mod = {
            PassType.SCREEN: -0.02,
            PassType.SHORT: 0,
            PassType.MEDIUM: 0.02,
            PassType.DEEP: 0.04,
            PassType.HAIL_MARY: 0.08,
        }.get(pass_type, 0)

        # QB decision making (awareness)
        awareness = qb.get_attribute("awareness")
        qb_mod = -(awareness - 50) / 500

        return max(0.02, min(0.18, base_rate + depth_mod + qb_mod))

    def _calculate_pass_yards(
        self,
        pass_type: PassType,
        receiver: Player,
        coverage: list[Player],
        game_state: GameState,
    ) -> int:
        """Calculate yards gained on completion."""
        mean, std = self.PASS_YARDS_DISTRIBUTION.get(pass_type, (10, 5))
        base_yards = random.gauss(mean, std)

        # YAC based on receiver speed/elusiveness (NFL avg YAC ~4-5 yards)
        speed = receiver.get_attribute("speed")
        elusiveness = receiver.get_attribute("elusiveness")
        yac = max(0, random.gauss(2, 1.5) * ((speed + elusiveness) / 150))

        yards = int(base_yards + yac)

        # Cap at goal line
        max_yards = game_state.down_state.line_of_scrimmage.yards_to_goal
        return max(-5, min(max_yards, yards))

    def _calculate_oline_rating(self, team: Team) -> int:
        """Calculate offensive line aggregate rating."""
        total = 0
        count = 0
        for slot in ["LT1", "LG1", "C1", "RG1", "RT1"]:
            if player := team.get_starter(slot):
                total += player.overall
                count += 1
        return total // count if count > 0 else 50

    def _calculate_dline_rating(self, team: Team) -> int:
        """Calculate defensive line aggregate rating."""
        total = 0
        count = 0
        for slot in ["DE1", "DE2", "DT1", "DT2"]:
            if player := team.get_starter(slot):
                total += player.overall
                count += 1
        return total // count if count > 0 else 50

    def _calculate_rb_modifier(self, rb: Player, run_type: RunType) -> float:
        """Calculate RB effectiveness modifier."""
        if run_type in (RunType.INSIDE, RunType.DRAW):
            # Power running
            trucking = rb.get_attribute("trucking")
            break_tackle = rb.get_attribute("break_tackle")
            key_attr = (trucking + break_tackle) / 2
        else:
            # Speed/finesse running
            speed = rb.get_attribute("speed")
            elusiveness = rb.get_attribute("elusiveness")
            key_attr = (speed + elusiveness) / 2

        return 0.75 + (key_attr / 200)  # 0.75 to 1.25

    def _select_target(
        self, receivers: list[Player], pass_type: PassType, coverage: list[Player]
    ) -> Optional[Player]:
        """Select a target receiver."""
        if not receivers:
            return None

        # Weight by route running and speed for the given pass type
        weights = []
        for rec in receivers:
            route = rec.get_attribute("route_running")
            if pass_type == PassType.DEEP:
                speed = rec.get_attribute("speed")
                weight = route * 0.5 + speed * 0.5
            elif pass_type == PassType.SCREEN:
                speed = rec.get_attribute("speed")
                weight = route * 0.3 + speed * 0.7
            else:
                catching = rec.get_attribute("catching")
                weight = route * 0.6 + catching * 0.4
            weights.append(max(1, weight))

        # Weighted random selection
        total = sum(weights)
        r = random.random() * total
        cumulative = 0
        for rec, weight in zip(receivers, weights):
            cumulative += weight
            if r <= cumulative:
                return rec
        return receivers[0]

    def _select_weighted_player(
        self,
        team: Team,
        weights: dict[str, float],
        attribute_name: Optional[str] = None,
        run_type: Optional[RunType] = None,
    ) -> Optional[Player]:
        """
        Select a player using position weights, modified by attributes.

        Args:
            team: Defensive team
            weights: Position slot -> base weight mapping
            attribute_name: Optional attribute to modify weights
            run_type: Optional run type to adjust weights

        Returns:
            Selected player or None
        """
        candidates = []
        adjusted_weights = []

        # Apply run type modifiers if applicable
        effective_weights = weights.copy()
        if run_type:
            if run_type in (RunType.INSIDE, RunType.DRAW):
                # Interior runs - boost DL and MLB
                for slot in ["DT1", "DT2", "MLB1", "MLB2", "ILB1", "ILB2"]:
                    if slot in effective_weights:
                        effective_weights[slot] *= 1.5
            else:
                # Outside runs - boost OLB, CB, safeties
                for slot in ["OLB1", "OLB2", "CB1", "CB2", "SS1", "FS1"]:
                    if slot in effective_weights:
                        effective_weights[slot] *= 1.5

        for slot, base_weight in effective_weights.items():
            # Check for rotation to backup
            if random.random() < self.ROTATION_CHANCE:
                # Try backup slot (e.g., "DE1" -> "DE2")
                position = slot.rstrip("0123456789")
                depth = int(slot[-1]) if slot[-1].isdigit() else 1
                backup_slot = f"{position}{depth + 1}"
                player = team.get_starter(backup_slot) or team.get_starter(slot)
            else:
                player = team.get_starter(slot)

            if player:
                weight = base_weight
                if attribute_name:
                    # Modify weight by player's attribute (50-99 range -> 0.8-1.2 modifier)
                    attr_value = player.get_attribute(attribute_name)
                    weight *= 0.8 + (attr_value / 250)
                candidates.append(player)
                adjusted_weights.append(weight)

        if not candidates:
            return None

        # Weighted random selection
        total = sum(adjusted_weights)
        if total == 0:
            return random.choice(candidates)

        r = random.random() * total
        cumulative = 0
        for player, weight in zip(candidates, adjusted_weights):
            cumulative += weight
            if r <= cumulative:
                return player

        return candidates[-1]

    def _select_tackler(self, defense: Team, run_type: RunType) -> Optional[Player]:
        """Select the player who makes the tackle using position weights."""
        return self._select_weighted_player(
            defense,
            self.TACKLE_WEIGHTS,
            attribute_name="tackle",
            run_type=run_type,
        )

    def _select_sacker(self, defense: Team) -> Optional[Player]:
        """Select player who gets the sack using position weights."""
        return self._select_weighted_player(
            defense,
            self.SACK_WEIGHTS,
            attribute_name="finesse_moves",
        )

    def _select_interceptor(self, defense: Team) -> Optional[Player]:
        """Select player who gets the interception using position weights."""
        return self._select_weighted_player(
            defense,
            self.INT_WEIGHTS,
            attribute_name="zone_coverage",
        )

    def _incomplete_pass(
        self, call: PlayCall, def_call: DefensiveCall, qb: Optional[Player]
    ) -> PlayResult:
        """Create an incomplete pass result."""
        return PlayResult(
            play_call=call,
            defensive_call=def_call,
            outcome=PlayOutcome.INCOMPLETE,
            yards_gained=0,
            time_elapsed_seconds=random.randint(5, 10),  # Clock stops on incomplete
            passer_id=qb.id if qb else None,
            clock_stopped=True,
            clock_stop_reason="incomplete",
            description="Pass incomplete",
        )

    def _create_sack_result(
        self,
        game_state: GameState,
        call: PlayCall,
        def_call: DefensiveCall,
        qb: Player,
        defense: Team,
    ) -> PlayResult:
        """Create a sack result."""
        yards_lost = random.randint(3, 10)
        sacker = self._select_sacker(defense)

        # Check for safety (sacked in own end zone)
        current_los = game_state.down_state.line_of_scrimmage.yard_line
        if current_los - yards_lost <= 0:
            return self._create_safety_result(
                game_state, call, def_call, qb, sacker, -yards_lost, is_sack=True
            )

        return PlayResult(
            play_call=call,
            defensive_call=def_call,
            outcome=PlayOutcome.SACK,
            yards_gained=-yards_lost,
            time_elapsed_seconds=random.randint(20, 35),
            passer_id=qb.id,
            tackler_id=sacker.id if sacker else None,
            is_sack=True,
            description=f"{qb.display_name} sacked for {yards_lost} yard loss",
        )

    def _create_completion_result(
        self,
        game_state: GameState,
        call: PlayCall,
        def_call: DefensiveCall,
        qb: Player,
        receiver: Player,
        yards: int,
        coverage: list[Player],
    ) -> PlayResult:
        """Create a pass completion result."""
        los = game_state.down_state.line_of_scrimmage.yard_line
        is_td = (los + yards) >= 100
        is_first_down = yards >= game_state.down_state.yards_to_go and not is_td

        tackler = coverage[0] if coverage else None

        # Check if receiver went out of bounds (~20% chance on sideline catches)
        went_out_of_bounds = random.random() < 0.20

        description = self._generate_pass_description(qb, receiver, yards, is_td)
        if went_out_of_bounds and not is_td:
            description += " (out of bounds)"

        # Clock stops on TD, first down (briefly), or out of bounds
        clock_stopped = is_td or went_out_of_bounds
        clock_stop_reason = None
        if is_td:
            clock_stop_reason = "touchdown"
        elif went_out_of_bounds:
            clock_stop_reason = "out_of_bounds"

        # Time elapsed is less if clock stops
        if clock_stopped:
            time_elapsed = random.randint(5, 12)
        else:
            time_elapsed = random.randint(25, 40)

        return PlayResult(
            play_call=call,
            defensive_call=def_call,
            outcome=PlayOutcome.TOUCHDOWN if is_td else PlayOutcome.COMPLETE,
            yards_gained=yards,
            time_elapsed_seconds=time_elapsed,
            passer_id=qb.id,
            receiver_id=receiver.id,
            tackler_id=tackler.id if tackler else None,
            is_first_down=is_first_down,
            is_touchdown=is_td,
            clock_stopped=clock_stopped,
            clock_stop_reason=clock_stop_reason,
            points_scored=6 if is_td else 0,
            description=description,
        )

    def _create_interception_result(
        self,
        game_state: GameState,
        call: PlayCall,
        def_call: DefensiveCall,
        qb: Player,
        defense: Team,
    ) -> PlayResult:
        """Create an interception result with possible return."""
        interceptor = self._select_interceptor(defense)
        pass_type = call.pass_type or PassType.SHORT

        # Calculate where interception occurred (yards downfield from LOS)
        int_spot = self._calculate_int_spot(pass_type)

        # Calculate return yards and check for TD
        current_los = game_state.down_state.line_of_scrimmage.yard_line
        return_yards, is_return_td = self._calculate_turnover_return(
            interceptor, int_spot, current_los
        )

        if is_return_td:
            description = f"{qb.display_name} INTERCEPTED"
            if interceptor:
                description += f" by {interceptor.display_name}"
            description += ", returned for TOUCHDOWN!"

            return PlayResult(
                play_call=call,
                defensive_call=def_call,
                outcome=PlayOutcome.INTERCEPTION,
                yards_gained=int_spot + return_yards,  # Total field position change
                time_elapsed_seconds=random.randint(10, 18),
                passer_id=qb.id,
                interceptor_id=interceptor.id if interceptor else None,
                is_turnover=True,
                is_touchdown=True,
                points_scored=6,
                clock_stopped=True,
                clock_stop_reason="touchdown",
                description=description,
            )

        description = f"{qb.display_name} INTERCEPTED"
        if interceptor:
            description += f" by {interceptor.display_name}"
        if return_yards > 0:
            description += f", returned {return_yards} yards"

        return PlayResult(
            play_call=call,
            defensive_call=def_call,
            outcome=PlayOutcome.INTERCEPTION,
            yards_gained=int_spot + return_yards,  # Used for field position calculation
            time_elapsed_seconds=random.randint(25, 35),
            passer_id=qb.id,
            interceptor_id=interceptor.id if interceptor else None,
            is_turnover=True,
            description=description,
        )

    def _calculate_int_spot(self, pass_type: PassType) -> int:
        """Calculate where interception occurs (yards downfield from LOS)."""
        depth_ranges = {
            PassType.SCREEN: (0, 3),
            PassType.SHORT: (3, 10),
            PassType.MEDIUM: (10, 20),
            PassType.DEEP: (20, 40),
            PassType.HAIL_MARY: (35, 50),
        }
        min_depth, max_depth = depth_ranges.get(pass_type, (5, 15))
        return random.randint(min_depth, max_depth)

    def _calculate_turnover_return(
        self,
        returner: Optional[Player],
        turnover_spot: int,
        current_los: int,
    ) -> tuple[int, bool]:
        """
        Calculate return yards on turnover and whether it's a TD.

        Args:
            returner: Player returning the ball
            turnover_spot: Yards downfield where turnover occurred
            current_los: Current line of scrimmage (offense's perspective)

        Returns:
            Tuple of (return_yards, is_touchdown)
        """
        if not returner:
            return 0, False

        # Position where turnover occurred (from offense's endzone)
        turnover_position = current_los + turnover_spot

        # Yards to opposing endzone (where returner wants to go)
        # Returner runs toward offense's original endzone (yard 0)
        yards_to_td = turnover_position

        # Base return is 0-20 yards, modified by speed
        speed = returner.get_attribute("speed")
        base_return = random.gauss(10, 8)
        return_yards = int(max(0, base_return * (speed / 85)))

        # Check for house call (about 1-2% of interceptions become pick-sixes)
        if return_yards >= yards_to_td:
            return_yards = yards_to_td
            return return_yards, True

        # Small chance of breaking a long return for TD
        if return_yards > 25 and random.random() < 0.12:
            return yards_to_td, True

        # Cap return at available distance
        return_yards = min(return_yards, yards_to_td - 1)
        return return_yards, False

    def _create_safety_result(
        self,
        game_state: GameState,
        call: PlayCall,
        def_call: DefensiveCall,
        ball_carrier: Player,
        tackler: Optional[Player],
        yards: int,
        is_sack: bool = False,
    ) -> PlayResult:
        """Create a safety result (ball carrier tackled in own end zone)."""
        if is_sack:
            description = f"{ball_carrier.display_name} sacked in the end zone! SAFETY!"
        else:
            description = f"{ball_carrier.display_name} tackled in the end zone! SAFETY!"

        return PlayResult(
            play_call=call,
            defensive_call=def_call,
            outcome=PlayOutcome.SAFETY,
            yards_gained=yards,
            time_elapsed_seconds=random.randint(5, 10),
            rusher_id=ball_carrier.id if not is_sack else None,
            passer_id=ball_carrier.id if is_sack else None,
            tackler_id=tackler.id if tackler else None,
            is_safety=True,
            is_sack=is_sack,
            clock_stopped=True,
            clock_stop_reason="safety",
            points_scored=2,  # Defense scores 2 points
            description=description,
        )

    def _create_minimal_run_result(
        self, call: PlayCall, def_call: DefensiveCall, yards: int
    ) -> PlayResult:
        """Create a minimal run result when no RB available."""
        return PlayResult(
            play_call=call,
            defensive_call=def_call,
            outcome=PlayOutcome.RUSH,
            yards_gained=yards,
            time_elapsed_seconds=random.randint(8, 15),
            description=f"Rush for {yards} yards",
        )

    def _generate_pass_description(
        self, qb: Player, receiver: Player, yards: int, is_td: bool
    ) -> str:
        """Generate narrative description for pass play."""
        if is_td:
            return f"{qb.display_name} pass complete to {receiver.display_name} for {yards} yards, TOUCHDOWN!"
        return f"{qb.display_name} pass complete to {receiver.display_name} for {yards} yards"

    def _generate_run_description(
        self,
        rb: Player,
        yards: int,
        is_td: bool,
        is_fumble: bool,
        tackler: Optional[Player],
    ) -> str:
        """Generate narrative description for run play."""
        if is_fumble:
            return f"{rb.display_name} rush for {yards} yards, FUMBLES! Recovered by defense"
        if is_td:
            return f"{rb.display_name} rush for {yards} yards, TOUCHDOWN!"
        if yards < 0:
            return f"{rb.display_name} rush for {yards} yards (loss)"

        desc = f"{rb.display_name} rush for {yards} yards"
        if tackler:
            desc += f", tackled by {tackler.display_name}"
        return desc

    def _resolve_kickoff(
        self,
        game_state: GameState,
        kicking_team: Team,
        receiving_team: Team,
        call: PlayCall,
        def_call: DefensiveCall,
    ) -> PlayResult:
        """Resolve a kickoff play."""
        kicker = kicking_team.get_starter("K1")
        kick_power = kicker.get_attribute("kick_power") if kicker else 70

        # Calculate kick distance (from own 35)
        base_distance = 60 + (kick_power - 50) * 0.3
        distance = int(base_distance + random.gauss(0, 5))
        distance = max(50, min(75, distance))

        # Determine if touchback (kick into end zone, ball at 25)
        # Kick from 35, end zone starts at 100, so kick of 65+ yards = touchback
        if distance >= 65:
            is_touchback = random.random() < 0.7  # 70% of deep kicks are touchbacks
        else:
            is_touchback = False

        if is_touchback:
            return_yards = 0
            starting_position = 25
            description = "Kickoff into the end zone, touchback"
            outcome = PlayOutcome.TOUCHBACK
        else:
            # Calculate return
            # Ball caught at (35 + distance - 100) yards from goal, capped
            catch_yard = max(0, 35 + distance - 100) if distance > 65 else (100 - (35 + distance))
            catch_yard = max(0, min(25, catch_yard))

            # Return yards
            returner = receiving_team.get_starter("WR3")  # Often WR3 or specialized returner
            speed = returner.get_attribute("speed") if returner else 75
            return_yards = int(random.gauss(22, 10) * (speed / 85))
            return_yards = max(0, min(50, return_yards))

            # Check for return TD (rare, ~0.5%)
            if return_yards > 45 and random.random() < 0.02:
                return_yards = 100 - catch_yard
                is_return_td = True
            else:
                is_return_td = False
                return_yards = min(return_yards, 100 - catch_yard - 1)

            starting_position = catch_yard + return_yards

            if is_return_td:
                description = f"Kickoff returned for a TOUCHDOWN!"
                outcome = PlayOutcome.TOUCHDOWN
            else:
                description = f"Kickoff returned {return_yards} yards to the {starting_position}"
                outcome = PlayOutcome.KICKOFF_RESULT

        return PlayResult(
            play_call=call,
            defensive_call=def_call,
            outcome=outcome,
            yards_gained=starting_position,  # Used for field position setup
            time_elapsed_seconds=random.randint(5, 12),
            is_touchdown=(outcome == PlayOutcome.TOUCHDOWN),
            points_scored=6 if outcome == PlayOutcome.TOUCHDOWN else 0,
            description=description,
        )

    def _resolve_extra_point(
        self,
        game_state: GameState,
        offense: Team,
        call: PlayCall,
        def_call: DefensiveCall,
    ) -> PlayResult:
        """Resolve an extra point attempt."""
        kicker = offense.get_starter("K1")
        accuracy = kicker.get_attribute("kick_accuracy") if kicker else 75

        # Extra point is ~33 yards (15 yard line + 18 yards)
        # NFL success rate is about 94%
        base_prob = 0.94
        attr_mod = (accuracy - 75) / 200
        make_prob = max(0.80, min(0.99, base_prob + attr_mod))

        is_good = random.random() < make_prob

        return PlayResult(
            play_call=call,
            defensive_call=def_call,
            outcome=PlayOutcome.EXTRA_POINT_GOOD if is_good else PlayOutcome.EXTRA_POINT_MISSED,
            yards_gained=0,
            time_elapsed_seconds=random.randint(5, 8),
            points_scored=1 if is_good else 0,
            description=f"Extra point {'GOOD' if is_good else 'NO GOOD'}",
        )

    def _resolve_two_point(
        self,
        game_state: GameState,
        offense: Team,
        defense: Team,
        call: PlayCall,
        def_call: DefensiveCall,
    ) -> PlayResult:
        """Resolve a two-point conversion attempt."""
        # Two-point conversions succeed about 48% of the time in NFL
        # Treat it like a short-yardage play from the 2

        # Determine if run or pass
        if call.run_type:
            rb = offense.get_starter("RB1")
            if rb:
                trucking = rb.get_attribute("trucking")
                break_tackle = rb.get_attribute("break_tackle")
                success_prob = 0.45 + ((trucking + break_tackle) / 2 - 50) / 200
            else:
                success_prob = 0.40
            is_pass = False
        else:
            qb = offense.get_starter("QB1")
            if qb:
                acc = qb.get_attribute("throw_accuracy_short")
                success_prob = 0.48 + (acc - 50) / 200
            else:
                success_prob = 0.45
            is_pass = True

        success = random.random() < success_prob

        if success:
            if is_pass:
                description = "Two-point conversion GOOD! Pass complete in the end zone"
            else:
                description = "Two-point conversion GOOD! Rushed into the end zone"
            outcome = PlayOutcome.TWO_POINT_GOOD
        else:
            if is_pass:
                description = "Two-point conversion FAILED. Pass incomplete"
            else:
                description = "Two-point conversion FAILED. Stopped short"
            outcome = PlayOutcome.TWO_POINT_FAILED

        return PlayResult(
            play_call=call,
            defensive_call=def_call,
            outcome=outcome,
            yards_gained=2 if success else 0,
            time_elapsed_seconds=random.randint(5, 10),
            points_scored=2 if success else 0,
            description=description,
        )

    # =========== PENALTY METHODS ===========

    def _check_pre_snap_penalty(
        self, offense: Team, defense: Team
    ) -> Optional[tuple[PenaltyType, bool]]:
        """
        Check for pre-snap penalty.

        Returns:
            Tuple of (PenaltyType, is_on_offense) or None if no penalty
        """
        # Overall pre-snap penalty rate: ~3% of plays
        if random.random() > 0.03:
            return None

        # 60% offensive, 40% defensive
        if random.random() < 0.60:
            # Offensive pre-snap penalty
            penalty_type = random.choices(
                [PenaltyType.FALSE_START, PenaltyType.DELAY_OF_GAME, PenaltyType.ILLEGAL_FORMATION],
                weights=[0.65, 0.25, 0.10]
            )[0]
            return (penalty_type, True)
        else:
            # Defensive pre-snap penalty
            penalty_type = random.choices(
                [PenaltyType.OFFSIDES, PenaltyType.ENCROACHMENT, PenaltyType.NEUTRAL_ZONE_INFRACTION],
                weights=[0.60, 0.25, 0.15]
            )[0]
            return (penalty_type, False)

    def _check_pass_play_penalty(
        self,
        offense: Team,
        defense: Team,
        def_call: DefensiveCall,
        was_complete: bool,
        pass_type: PassType,
    ) -> Optional[tuple[PenaltyType, bool, int]]:
        """
        Check for penalty during a pass play.

        Returns:
            Tuple of (PenaltyType, is_on_offense, yards_to_target) or None
        """
        # Base penalty rate ~5% of pass plays (after pre-snap check)
        if random.random() > 0.05:
            return None

        # Pass plays can have holding, PI, roughing passer, etc.
        # Distribution based on approximate NFL rates

        if random.random() < 0.40:
            # Offensive penalty
            penalty_type = random.choices(
                [PenaltyType.HOLDING_OFFENSE, PenaltyType.OFFENSIVE_PASS_INTERFERENCE,
                 PenaltyType.ILLEGAL_USE_OF_HANDS],
                weights=[0.70, 0.15, 0.15]
            )[0]
            return (penalty_type, True, 0)
        else:
            # Defensive penalty
            # DPI more common on deep passes and incomplete passes
            dpi_chance = 0.20
            if pass_type in (PassType.DEEP, PassType.HAIL_MARY):
                dpi_chance = 0.35
            if not was_complete:
                dpi_chance += 0.10

            # Man coverage and blitz increase holding
            holding_chance = 0.30
            if def_call.scheme in (DefensiveScheme.MAN_PRESS, DefensiveScheme.MAN_OFF):
                holding_chance = 0.40

            penalty_type = random.choices(
                [PenaltyType.DEFENSIVE_PASS_INTERFERENCE, PenaltyType.HOLDING_DEFENSE,
                 PenaltyType.ROUGHING_THE_PASSER, PenaltyType.FACEMASK],
                weights=[dpi_chance, holding_chance, 0.15, 0.10]
            )[0]

            # Calculate spot foul yards for DPI
            yards_to_target = 0
            if penalty_type == PenaltyType.DEFENSIVE_PASS_INTERFERENCE:
                if pass_type == PassType.SCREEN:
                    yards_to_target = random.randint(1, 5)
                elif pass_type == PassType.SHORT:
                    yards_to_target = random.randint(5, 12)
                elif pass_type == PassType.MEDIUM:
                    yards_to_target = random.randint(12, 22)
                elif pass_type == PassType.DEEP:
                    yards_to_target = random.randint(20, 40)
                else:
                    yards_to_target = random.randint(30, 50)

            return (penalty_type, False, yards_to_target)

    def _check_run_play_penalty(
        self, offense: Team, defense: Team
    ) -> Optional[tuple[PenaltyType, bool]]:
        """
        Check for penalty during a run play.

        Returns:
            Tuple of (PenaltyType, is_on_offense) or None
        """
        # Base penalty rate ~4% of run plays (after pre-snap check)
        if random.random() > 0.04:
            return None

        if random.random() < 0.55:
            # Offensive penalty - mostly holding
            penalty_type = random.choices(
                [PenaltyType.HOLDING_OFFENSE, PenaltyType.ILLEGAL_BLOCK_IN_BACK,
                 PenaltyType.ILLEGAL_USE_OF_HANDS],
                weights=[0.75, 0.15, 0.10]
            )[0]
            return (penalty_type, True)
        else:
            # Defensive penalty
            penalty_type = random.choices(
                [PenaltyType.HOLDING_DEFENSE, PenaltyType.FACEMASK,
                 PenaltyType.UNNECESSARY_ROUGHNESS],
                weights=[0.50, 0.30, 0.20]
            )[0]
            return (penalty_type, False)

    def _create_penalty_result(
        self,
        call: PlayCall,
        def_call: DefensiveCall,
        penalty_type: PenaltyType,
        is_on_offense: bool,
        game_state: GameState,
        yards_to_target: int = 0,
    ) -> PlayResult:
        """Create a PlayResult for a penalty."""
        # Calculate penalty yards
        if penalty_type == PenaltyType.DEFENSIVE_PASS_INTERFERENCE:
            penalty_yards = yards_to_target
        else:
            penalty_yards = penalty_type.yards

        # Cap penalty at goal line
        if not is_on_offense:
            # Defensive penalty - yards toward goal
            max_penalty = game_state.down_state.line_of_scrimmage.yards_to_goal
            penalty_yards = min(penalty_yards, max_penalty)
        else:
            # Offensive penalty - yards away from goal
            # Don't push team back past their own 1
            max_penalty = game_state.down_state.line_of_scrimmage.yard_line - 1
            penalty_yards = min(penalty_yards, max(1, max_penalty))

        # Format penalty name
        penalty_name = penalty_type.name.replace("_", " ").title()
        if is_on_offense:
            description = f"PENALTY: {penalty_name} on offense. {penalty_yards} yards."
        else:
            description = f"PENALTY: {penalty_name} on defense. {penalty_yards} yards."
            if penalty_type.is_automatic_first_down:
                description += " Automatic first down."

        outcome = PlayOutcome.PENALTY_OFFENSE if is_on_offense else PlayOutcome.PENALTY_DEFENSE

        return PlayResult(
            play_call=call,
            defensive_call=def_call,
            outcome=outcome,
            yards_gained=0,  # Actual yards gained is 0, penalty yards handled separately
            time_elapsed_seconds=random.randint(5, 15),  # Penalty stoppage
            clock_stopped=True,
            clock_stop_reason="penalty",
            penalty_on_offense=is_on_offense,
            penalty_yards=penalty_yards,
            penalty_type=penalty_type.name,
            description=description,
        )
