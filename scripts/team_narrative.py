#!/usr/bin/env python3
"""
Generate a detailed narrative of one team's offseason decision-making.

Captures:
- Initial roster assessment and position plan
- Every FA they considered, why they passed or bid
- Every FA they won or lost
- Their draft board going in
- Each pick decision and reasoning
- Final assessment
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
from uuid import uuid4

from huddle.core.simulation.historical_sim import HistoricalSimulator, SimulationConfig, get_nfl_team_data
from huddle.core.calendar import create_calendar_for_season
from huddle.generators.player import generate_player
from huddle.core.ai.position_planner import (
    AcquisitionPath,
    should_pursue_fa,
    get_draft_target,
    DraftProspect,
)
from huddle.core.ai import calculate_team_needs, DraftAI, FreeAgencyAI
from huddle.core.contracts.market_value import calculate_market_value
from huddle.core.enums.positions import Position


def print_section(title: str):
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)


def print_subsection(title: str):
    print(f"\n--- {title} ---")


def run_narrative():
    random.seed(42)  # For reproducibility

    # Setup
    config = SimulationConfig(
        verbose=False,
        draft_rounds=7,
    )

    def player_generator(position, age=None, experience_years=None):
        return generate_player(
            position=position,
            age=age or random.randint(22, 32),
            experience_years=experience_years,
        )

    team_data = get_nfl_team_data()

    # Initialize simulator
    sim = HistoricalSimulator(config, player_generator, team_data)
    start_season = 2023

    # Initialize league
    sim._initialize_league(start_season)
    sim.current_calendar = create_calendar_for_season(start_season)

    # Set some teams to have specific statuses for more interesting narratives
    # Find a team that could be rebuilding
    team_list = list(sim.teams.keys())

    # Pick the Bears - classic rebuilding story
    FOCUS_TEAM_ID = "bears"
    focus_team = sim.teams[FOCUS_TEAM_ID]

    # Give them a bad record to get a high pick
    focus_team.wins = 4
    focus_team.losses = 13
    focus_team.win_pct = 4/17

    # Create position plans
    sim._create_position_plans(start_season)

    print_section("CHICAGO BEARS OFFSEASON NARRATIVE - 2023")
    print(f"\nTeam Status: {focus_team.status.current_status.value}")
    print(f"Record: {focus_team.wins}-{focus_team.losses}")
    print(f"GM Archetype: {focus_team.gm_archetype.value if focus_team.gm_archetype else 'Unknown'}")

    # ========================================================================
    # PART 1: INITIAL ASSESSMENT
    # ========================================================================
    print_section("PART 1: INITIAL ROSTER ASSESSMENT")

    plan = focus_team.position_plan
    needs = calculate_team_needs(focus_team.roster)

    print("\nCurrent Roster Snapshot:")
    print(f"  Total Players: {len(focus_team.roster)}")
    print(f"  Salary Cap Space: ${focus_team.cap_space:,.0f}")

    # Show starters by position
    starters = {}
    for player in focus_team.roster:
        pos = player.position.value
        if pos not in starters or player.overall > starters[pos].overall:
            starters[pos] = player

    print("\nCurrent Starters (by overall):")
    for pos in ["QB", "RB", "WR", "LT", "DE", "CB"]:
        if pos in starters:
            p = starters[pos]
            print(f"  {pos}: {p.full_name} ({p.overall} OVR, Age {p.age})")

    print_subsection("Position Needs Analysis")
    print("\nThe front office has identified these needs:")

    # Sort by need score
    sorted_needs = sorted(
        plan.needs.items(),
        key=lambda x: x[1].need_score,
        reverse=True
    )

    for pos, need in sorted_needs[:8]:
        path_name = need.acquisition_path.value.replace("_", " ").title()
        print(f"  {pos}: Need={need.need_score:.2f}, Current Starter={need.current_starter_overall} OVR")
        print(f"       Strategy: {path_name}")

    print_subsection("The Plan")

    # Categorize positions by strategy
    fa_targets = [pos for pos, need in plan.needs.items()
                  if need.acquisition_path == AcquisitionPath.FREE_AGENCY]
    draft_early = [pos for pos, need in plan.needs.items()
                   if need.acquisition_path == AcquisitionPath.DRAFT_EARLY]
    draft_mid = [pos for pos, need in plan.needs.items()
                 if need.acquisition_path == AcquisitionPath.DRAFT_MID]
    keep_current = [pos for pos, need in plan.needs.items()
                    if need.acquisition_path == AcquisitionPath.KEEP_CURRENT]

    print(f"\nFA Targets: {', '.join(fa_targets) if fa_targets else 'None'}")
    print(f"Draft Early (Rd 1-2): {', '.join(draft_early) if draft_early else 'None'}")
    print(f"Draft Mid (Rd 3-4): {', '.join(draft_mid) if draft_mid else 'None'}")
    print(f"Keep Current: {', '.join(keep_current[:5]) if keep_current else 'None'}...")

    print(f"\nDraft Board Size: {len(plan.draft_board)} prospects")
    if plan.draft_board:
        print("Top 5 Draft Targets:")
        for i, prospect in enumerate(plan.draft_board[:5]):
            print(f"  {i+1}. {prospect.name} ({prospect.position}) - Grade {prospect.grade:.0f}")

    # ========================================================================
    # PART 2: FREE AGENCY
    # ========================================================================
    print_section("PART 2: FREE AGENCY PERIOD")

    # Track FA events for narrative
    fa_events = []
    bears_signings = []
    bears_missed = []
    bears_passed = []

    # Collect free agents
    free_agents = []
    for team in sim.teams.values():
        expiring = [
            p for p in team.roster
            if str(p.id) in team.contracts and
            team.contracts[str(p.id)].is_expiring()
        ]
        for player in expiring:
            if random.random() < 0.35:
                free_agents.append((player, team.team_id))

    free_agents.sort(key=lambda x: x[0].overall, reverse=True)

    print(f"\n{len(free_agents)} players hit the open market.")
    print("Monitoring Bears' activity...\n")

    min_roster = 45
    min_salary = 900

    for player, old_team_id in free_agents:
        market = calculate_market_value(player)

        # Check if Bears are interested
        roster_spots_needed = max(0, min_roster - len(focus_team.roster))
        cap_reserve = roster_spots_needed * min_salary
        available_for_fa = focus_team.cap_space - cap_reserve

        if available_for_fa < market.cap_hit_year1:
            # Bears can't afford
            continue

        # Check position plan
        pursue, aggression = should_pursue_fa(plan, {
            'position': player.position.value,
            'player_id': str(player.id),
            'overall': player.overall,
        })

        if not pursue:
            bears_passed.append({
                'player': player,
                'reason': f"Plan says {plan.needs.get(player.position.value, {}).acquisition_path.value if player.position.value in plan.needs else 'not a need'}"
            })
            continue

        # Bears are interested!
        needs_obj = calculate_team_needs(focus_team.roster)
        fa_ai = FreeAgencyAI(
            team_id=focus_team.team_id,
            team_identity=focus_team.identity,
            team_status=focus_team.status,
            cap_space=available_for_fa,
            team_needs={p: needs_obj.get_need(p) for p in [
                "QB", "RB", "WR", "TE", "LT", "LG", "C", "RG", "RT",
                "DE", "DT", "OLB", "ILB", "CB", "FS", "SS"
            ]},
            gm_archetype=focus_team.gm_archetype,
        )

        evaluation = fa_ai.evaluate_free_agent(player)

        # Count other interested teams (simplified)
        other_interested = random.randint(2, 6)

        # Simulate if Bears win the bidding (based on aggression and competition)
        bears_bid_strength = aggression * evaluation.priority * random.uniform(0.8, 1.2)
        other_max_bid = max(random.uniform(0.3, 0.9) for _ in range(other_interested))

        if bears_bid_strength > other_max_bid:
            # Bears win!
            bears_signings.append({
                'player': player,
                'aggression': aggression,
                'priority': evaluation.priority,
                'market_value': market.total_value,
                'competing_teams': other_interested,
            })
        else:
            # Bears lost out
            bears_missed.append({
                'player': player,
                'aggression': aggression,
                'priority': evaluation.priority,
                'reason': f"Outbid by {other_interested} other teams"
            })

    # Print FA narrative
    print_subsection("Players Bears Passed On (Per The Plan)")
    if bears_passed:
        for item in bears_passed[:5]:
            p = item['player']
            print(f"  {p.full_name} ({p.position.value}, {p.overall} OVR)")
            print(f"    Reason: {item['reason']}")
    else:
        print("  None tracked")

    print_subsection("Bidding Wars Bears Participated In")
    for item in bears_signings + bears_missed:
        p = item['player']
        agg = item['aggression']
        pri = item['priority']
        won = item in bears_signings

        print(f"\n  {p.full_name} ({p.position.value}, {p.overall} OVR)")
        print(f"    Bears Interest: Priority={pri:.2f}, Aggression={agg:.2f}")
        if won:
            print(f"    RESULT: SIGNED - ${item['market_value']:,} (beat {item['competing_teams']} teams)")
        else:
            print(f"    RESULT: LOST - {item['reason']}")

    print_subsection("Free Agency Summary")
    print(f"\nBears made {len(bears_signings)} signings:")
    for item in bears_signings:
        p = item['player']
        print(f"  - {p.full_name} ({p.position.value}, {p.overall} OVR) - ${item['market_value']:,}")

    if not bears_signings:
        print("  (No signings made)")

    # Update the plan with signings for draft
    from huddle.core.ai.position_planner import update_plan_after_fa
    for item in bears_signings:
        update_plan_after_fa(plan, {
            'position': item['player'].position.value,
            'player_id': str(item['player'].id),
            'overall': item['player'].overall,
            'contract_value': item['market_value'],
        })

    # ========================================================================
    # PART 3: THE DRAFT
    # ========================================================================
    print_section("PART 3: THE NFL DRAFT")

    # Generate draft class
    DRAFT_CLASS_COUNTS = {
        "QB": 8, "RB": 10, "WR": 16, "TE": 8,
        "LT": 5, "LG": 5, "C": 4, "RG": 5, "RT": 5,
        "DE": 10, "DT": 8, "OLB": 8, "ILB": 6, "MLB": 4,
        "CB": 14, "FS": 6, "SS": 6,
    }
    draft_class = []
    for position_str, count in DRAFT_CLASS_COUNTS.items():
        pos = Position(position_str)
        for _ in range(count):
            player = generate_player(
                position=pos,
                age=random.randint(21, 23),
            )
            draft_class.append(player)

    draft_class.sort(key=lambda p: p.overall, reverse=True)

    # Bears should be picking early (4-13 win team)
    # For narrative, let's say they have pick #3
    bears_pick = 3

    print(f"\nBears hold pick #{bears_pick} in the first round.")
    print("\nUpdated Draft Board (after FA adjustments):")
    for i, prospect in enumerate(plan.draft_board[:10]):
        print(f"  {i+1}. {prospect.name} ({prospect.position}) - Grade {prospect.grade:.0f}")

    # Simulate the draft
    available = list(draft_class)
    bears_picks = []

    # Simulate picks 1-2 by other teams
    print_subsection("Pre-Bears Picks")
    for pick_num in range(1, bears_pick):
        if available:
            selected = available[0]  # BPA
            print(f"  Pick #{pick_num}: {selected.full_name} ({selected.position.value}, {selected.overall} OVR)")
            available.remove(selected)

    # Bears picks
    print_subsection("Bears Draft Selections")

    # Simulate 7 rounds, Bears pick once per round
    bears_pick_numbers = [bears_pick + (32 * i) for i in range(7)]  # Simplified

    for round_num, pick_num in enumerate(bears_pick_numbers, 1):
        if not available:
            break

        print(f"\n  Round {round_num} - Pick #{pick_num}")

        # Get draft target from plan
        current_round = round_num
        available_prospects = [
            DraftProspect(
                player_id=str(p.id),
                name=p.full_name,
                position=p.position.value,
                grade=p.overall,
                projected_round=current_round,
                projected_pick=pick_num,
            )
            for p in available
        ]

        target = get_draft_target(plan, available_prospects)

        if target:
            selected = next((p for p in available if str(p.id) == str(target.player_id)), None)
            source = "PLAN TARGET"
        else:
            # Fall back to BPA
            selected = available[0]
            source = "BPA (no plan target available)"

        if selected:
            need_at_pos = plan.needs.get(selected.position.value)
            was_planned = need_at_pos and need_at_pos.acquisition_path in [
                AcquisitionPath.DRAFT_EARLY,
                AcquisitionPath.DRAFT_MID,
                AcquisitionPath.DRAFT_LATE,
            ]

            print(f"    Selection: {selected.full_name} ({selected.position.value}, {selected.overall} OVR)")
            print(f"    Source: {source}")
            if was_planned:
                print(f"    Plan Match: Yes - {selected.position.value} was planned as {need_at_pos.acquisition_path.value}")
            else:
                print(f"    Plan Match: No - went BPA or filled unexpected need")

            # Show alternatives considered
            top_3 = available[:3]
            if len(top_3) > 1:
                print(f"    Other Options: {', '.join([f'{p.full_name} ({p.position.value})' for p in top_3 if p != selected][:2])}")

            bears_picks.append({
                'round': round_num,
                'pick': pick_num,
                'player': selected,
                'source': source,
                'was_planned': was_planned,
            })

            available.remove(selected)

            # Update plan
            from huddle.core.ai.position_planner import update_plan_after_draft
            update_plan_after_draft(plan, {
                'position': selected.position.value,
                'player_id': str(selected.id),
                'overall': selected.overall,
                'round': round_num,
                'pick': pick_num,
            })

            # Simulate other picks until Bears' next pick
            picks_until_next = 31  # Rest of round
            for _ in range(min(picks_until_next, len(available))):
                if available:
                    available.pop(0)  # Other teams take players

    # ========================================================================
    # PART 4: ASSESSMENT
    # ========================================================================
    print_section("PART 4: OFFSEASON ASSESSMENT")

    print_subsection("Draft Haul")
    planned_hits = sum(1 for p in bears_picks if p['was_planned'])
    print(f"\nTotal Picks: {len(bears_picks)}")
    print(f"Plan-Aligned Picks: {planned_hits}/{len(bears_picks)}")

    print("\nRound-by-Round:")
    for pick in bears_picks:
        p = pick['player']
        marker = "✓" if pick['was_planned'] else "○"
        print(f"  {marker} Rd {pick['round']}: {p.full_name} ({p.position.value}, {p.overall} OVR)")

    print_subsection("What Worked")
    worked = []
    if planned_hits >= 3:
        worked.append("- Stuck to the plan: The Bears successfully targeted positions they identified as draft priorities")
    if bears_signings:
        worked.append(f"- FA execution: Landed {len(bears_signings)} FA target(s) at planned positions")
    if any(p['player'].overall >= 75 for p in bears_picks[:2]):
        worked.append("- Early round value: Found high-grade talent with premium picks")

    for item in worked:
        print(item)
    if not worked:
        print("- Nothing particularly notable went according to plan")

    print_subsection("What Didn't Work")
    issues = []
    if planned_hits < 3:
        issues.append("- Forced off the plan: Best available at plan positions weren't there when Bears picked")
    if len(bears_missed) > 2:
        issues.append(f"- FA competition: Lost {len(bears_missed)} bidding wars, had to adjust")
    if any(not p['was_planned'] for p in bears_picks[:2]):
        issues.append("- Early pick improvisation: Went BPA instead of targeting plan positions in premium rounds")

    for item in issues:
        print(item)
    if not issues:
        print("- Smooth offseason overall")

    print_subsection("Realism Assessment")

    print("\n✓ REALISTIC:")
    print("  - Teams following a cohesive position plan (FA + Draft integrated)")
    print("  - Aggression levels varying by how much team wanted position via FA")
    print("  - Draft board adjusting after FA signings (positions filled)")
    print("  - BPA fallback when plan targets aren't available")

    print("\n✗ NEEDS WORK:")
    print("  - Trade-ups not simulated (team should trade up for elite prospect at need)")
    print("  - Competition intensity feels abstract (real FA has leaked offers, leverage)")
    print("  - No consideration of scheme fit beyond archetype (would affect priority)")
    print("  - Player visits/interviews not modeled (affects real draft boards)")
    print("  - No salary negotiation (teams sometimes walk away from high prices)")

    print_subsection("Final Roster Situation")

    # Count positions filled
    positions_addressed = set()
    for s in bears_signings:
        positions_addressed.add(s['player'].position.value)
    for p in bears_picks:
        positions_addressed.add(p['player'].position.value)

    original_needs = [pos for pos, need in sorted_needs[:5]]
    needs_addressed = [pos for pos in original_needs if pos in positions_addressed]
    needs_remaining = [pos for pos in original_needs if pos not in positions_addressed]

    print(f"\nTop Needs Addressed: {', '.join(needs_addressed) if needs_addressed else 'None'}")
    print(f"Top Needs Remaining: {', '.join(needs_remaining) if needs_remaining else 'None'}")

    print("\n" + "="*70)
    print(" END OF NARRATIVE")
    print("="*70)


if __name__ == "__main__":
    run_narrative()
