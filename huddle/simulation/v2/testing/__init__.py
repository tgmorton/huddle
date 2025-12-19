"""Testing infrastructure for v2 simulation.

Two types of testing:

1. Unit tests (pytest) - verify logic correctness
2. Scenario runners - produce logs/stats for behavioral assessment

The scenario runners output detailed logs that can be analyzed by
humans or AI to assess whether behavior "looks right" from a football
perspective.
"""

from .scenario import Scenario, ScenarioResult
from .logger import PlayLogger, TickLog
from .stats import PlayStats, aggregate_stats

__all__ = [
    "Scenario",
    "ScenarioResult",
    "PlayLogger",
    "TickLog",
    "PlayStats",
    "aggregate_stats",
]
