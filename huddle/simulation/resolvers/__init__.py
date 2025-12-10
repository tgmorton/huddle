"""Play resolvers for simulation."""

from huddle.simulation.resolvers.base import DriveResolver, PlayResolver
from huddle.simulation.resolvers.statistical import StatisticalPlayResolver

__all__ = [
    "DriveResolver",
    "PlayResolver",
    "StatisticalPlayResolver",
]
