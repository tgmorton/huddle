# Gameplay Fundamentals Audit (Pass/Run/Pass Rush)

This report is a mechanics-level audit of the V2 simulation system, focused on
pass game timing, run game lanes, and pass rush/pocket dynamics. The intent is
to go beyond broad architecture and highlight concrete gameplay fundamentals.

## Pass Game Fundamentals

1) Window timing is modeled in the QB brain but not enforced at catch resolution.
- QB projections use separation at ball arrival time.
- Catch resolution only uses distance to landing point and defender rating.
- Result: throws can resolve in ways that contradict the QB's timing-based logic.

2) DB decision-making does not influence catch outcomes.
- DBs decide "play ball" vs "play receiver."
- Catch resolution ignores that choice and uses only distance + coverage rating.
- Result: DB tactical decisions do not change completion/INT/deflection odds.

3) Pressure affects decisions but not throw execution.
- QB brain narrows choices under pressure.
- Passing system does not degrade accuracy/velocity with pressure.
- Result: pressure impacts whether a throw happens, not the quality of the throw.

4) Ball tracking is position-based, not time-based.
- Defenders rally to flight target after a fixed reaction delay.
- No ETA-based check to see if they can reach the catch point in time.
- Result: deep throws can be contested unrealistically.

Suggested mechanics fixes:
- Add arrival-time race (WR ETA vs DB ETA) to drive catch/INT probabilities.
- Incorporate DB "play ball" vs "play receiver" into catch resolution.
- Apply pressure modifiers to throw accuracy and velocity.
- Limit defender influence by ETA to the catch point.

## Run Game Fundamentals

1) Ballcarrier pathing is defender-centric, not block-centric.
- Ballcarrier brain samples holes by clearance to defenders.
- OL/DL engagement outcomes do not feed lane quality.
- Result: blocking outcomes do not meaningfully shape run lanes.

2) Holes are static samples, not dynamic lanes.
- Hole evaluation checks a fixed point 5 yards ahead.
- No lane stability window based on block leverage or shed progress.
- Result: runs lack "press and cut" timing that feels like real zone runs.

3) Run concept intent is weakly enforced.
- Designed hole bias exists but does not set timing/commit rules.
- Result: backs can cut too early or ignore the designed track.

4) Second-level fits are treated as point threats.
- LBs are threats, not leverage walls.
- Result: lanes can look open even when a LB has inside leverage.

Suggested mechanics fixes:
- Feed OL/DL leverage + wash direction into lane scoring.
- Add lane stability windows (close lanes as shed progresses).
- Add press-then-cut timing rules for zone runs.
- Model LB fits as leverage walls, not just point threats.

## Pass Rush and Pocket Fundamentals

1) Sacks are proximity-based, not pocket-based.
- Sack logic triggers when an unengaged defender is within 2.5 yards.
- There is no pocket geometry or collapse model.
- Result: sacks feel binary rather than cumulative.

2) QB is effectively protected in pocket.
- Tackle checks skip QB while in DEVELOPMENT phase.
- Result: pocket feels "safe" until a sack roll fires.

3) Quick beat drives most pass rush variance.
- Quick beat sheds create sudden pressure spikes.
- No gradual pocket collapse tied to block leverage.
- Result: pressure swings rather than builds.

4) No lateral pocket constraints on QB movement.
- QB holds position; no shrinking pocket or forced movement.
- Result: no climb/slide/escape behavior unless explicitly added.

Suggested mechanics fixes:
- Create a pocket shape and shrink it based on DL leverage and shed progress.
- Add pressure accumulation to degrade throw quality and timing.
- Gate sacks by collapse threshold plus distance, not just proximity.
- Introduce escape lanes when edges win to drive realistic QB movement.

## Summary

The core loop and AI separation are strong, but the game feel is limited by
missing couplings between:
- QB decision timing and actual catch outcomes
- DB tactical choices and contest probabilities
- Blocking outcomes and run lane quality
- Pass rush leverage and pocket geometry

The fastest path to improved feel is to tie resolution math to the same
timing and leverage signals already calculated in the brains and blockers.
