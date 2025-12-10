"""
Attribute projections and uncertainty.

Handles the "fog of war" aspect of scouting where teams see projected
values with uncertainty ranges instead of true attribute values.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional
from enum import Enum
import random

from huddle.core.scouting.stages import (
    ScoutingStage,
    ScoutingLevel,
    get_attributes_for_stage,
)

if TYPE_CHECKING:
    from huddle.core.attributes.registry import PlayerAttributes


class ScoutingAccuracy(Enum):
    """
    Accuracy tiers for scouted attributes.

    Determines how much variance is applied to projections.
    """
    # Very uncertain - could be way off
    LOW = "low"
    # Moderate confidence
    MEDIUM = "medium"
    # Pretty accurate
    HIGH = "high"
    # True value known
    EXACT = "exact"


# Variance ranges (standard deviation) by accuracy level
ACCURACY_VARIANCE: dict[ScoutingAccuracy, int] = {
    ScoutingAccuracy.LOW: 12,  # +/- 12 points typical
    ScoutingAccuracy.MEDIUM: 7,  # +/- 7 points typical
    ScoutingAccuracy.HIGH: 3,  # +/- 3 points typical
    ScoutingAccuracy.EXACT: 0,  # No variance
}

# Scout level affects base accuracy
SCOUT_LEVEL_ACCURACY: dict[ScoutingLevel, ScoutingAccuracy] = {
    ScoutingLevel.ROOKIE: ScoutingAccuracy.LOW,
    ScoutingLevel.AVERAGE: ScoutingAccuracy.MEDIUM,
    ScoutingLevel.EXPERIENCED: ScoutingAccuracy.HIGH,
    ScoutingLevel.ELITE: ScoutingAccuracy.HIGH,  # Still some variance, but minimal
}


@dataclass
class ScoutedAttribute:
    """
    A single scouted attribute with projection and uncertainty.

    Represents what a team "knows" about an attribute based on scouting.
    """
    name: str
    projected_value: int  # Team's best estimate
    accuracy: ScoutingAccuracy
    true_value: Optional[int] = None  # Only set if revealed
    min_estimate: int = 0  # Low end of confidence range
    max_estimate: int = 99  # High end of confidence range

    @property
    def is_revealed(self) -> bool:
        """True if the exact value is known."""
        return self.true_value is not None

    @property
    def confidence_range(self) -> int:
        """Size of the confidence interval."""
        return self.max_estimate - self.min_estimate

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "projected_value": self.projected_value,
            "accuracy": self.accuracy.value,
            "true_value": self.true_value,
            "min_estimate": self.min_estimate,
            "max_estimate": self.max_estimate,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScoutedAttribute":
        return cls(
            name=data["name"],
            projected_value=data["projected_value"],
            accuracy=ScoutingAccuracy(data["accuracy"]),
            true_value=data.get("true_value"),
            min_estimate=data.get("min_estimate", 0),
            max_estimate=data.get("max_estimate", 99),
        )


@dataclass
class PlayerProjection:
    """
    A team's complete projection of a player's attributes.

    Contains all scouted information about a player from one team's perspective.
    Different teams may have different projections for the same player.
    """
    player_id: str
    scouting_stage: ScoutingStage
    scout_level: ScoutingLevel
    attributes: dict[str, ScoutedAttribute] = field(default_factory=dict)

    def get_projected_value(self, attr_name: str) -> int:
        """Get the projected value for an attribute."""
        if attr_name in self.attributes:
            return self.attributes[attr_name].projected_value
        return 50  # Unknown attributes default to average

    def get_accuracy(self, attr_name: str) -> ScoutingAccuracy:
        """Get the accuracy level for an attribute projection."""
        if attr_name in self.attributes:
            return self.attributes[attr_name].accuracy
        return ScoutingAccuracy.LOW

    def is_revealed(self, attr_name: str) -> bool:
        """Check if an attribute's true value is known."""
        if attr_name in self.attributes:
            return self.attributes[attr_name].is_revealed
        return False

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "scouting_stage": self.scouting_stage.name,
            "scout_level": self.scout_level.value,
            "attributes": {
                name: attr.to_dict() for name, attr in self.attributes.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerProjection":
        return cls(
            player_id=data["player_id"],
            scouting_stage=ScoutingStage[data["scouting_stage"]],
            scout_level=ScoutingLevel(data["scout_level"]),
            attributes={
                name: ScoutedAttribute.from_dict(attr_data)
                for name, attr_data in data.get("attributes", {}).items()
            },
        )


def generate_projection(
    true_value: int,
    accuracy: ScoutingAccuracy,
    scout_level: ScoutingLevel,
) -> tuple[int, int, int]:
    """
    Generate a projected value with confidence range.

    Args:
        true_value: The actual attribute value
        accuracy: Base accuracy from scouting stage
        scout_level: Scout quality affects variance

    Returns:
        (projected_value, min_estimate, max_estimate)
    """
    if accuracy == ScoutingAccuracy.EXACT:
        return (true_value, true_value, true_value)

    # Base variance from accuracy level
    base_variance = ACCURACY_VARIANCE[accuracy]

    # Scout level modifies variance
    level_modifier = {
        ScoutingLevel.ROOKIE: 1.3,  # 30% more variance
        ScoutingLevel.AVERAGE: 1.0,
        ScoutingLevel.EXPERIENCED: 0.7,  # 30% less variance
        ScoutingLevel.ELITE: 0.5,  # 50% less variance
    }
    variance = int(base_variance * level_modifier[scout_level])

    # Generate projection with some noise
    noise = random.gauss(0, variance / 2)
    projected = int(true_value + noise)
    projected = max(1, min(99, projected))

    # Confidence range based on variance
    min_est = max(1, projected - variance)
    max_est = min(99, projected + variance)

    return (projected, min_est, max_est)


def generate_initial_projection(
    true_attributes: "PlayerAttributes",
    player_id: str,
    scout_level: ScoutingLevel = ScoutingLevel.AVERAGE,
) -> PlayerProjection:
    """
    Generate initial projections for an unscouted player.

    All attributes start with low accuracy estimates based on
    league-wide baselines and rumors.

    Args:
        true_attributes: The player's actual attribute values
        player_id: ID of the player being projected
        scout_level: Quality of the scout making projections

    Returns:
        PlayerProjection with low-accuracy estimates for all attributes
    """
    projection = PlayerProjection(
        player_id=player_id,
        scouting_stage=ScoutingStage.UNKNOWN,
        scout_level=scout_level,
    )

    # Generate low-accuracy estimates for all attributes
    for attr_name in true_attributes._values.keys():
        true_value = true_attributes.get(attr_name)
        proj_value, min_est, max_est = generate_projection(
            true_value,
            ScoutingAccuracy.LOW,
            scout_level,
        )
        projection.attributes[attr_name] = ScoutedAttribute(
            name=attr_name,
            projected_value=proj_value,
            accuracy=ScoutingAccuracy.LOW,
            min_estimate=min_est,
            max_estimate=max_est,
        )

    return projection


def refine_projection(
    projection: PlayerProjection,
    true_attributes: "PlayerAttributes",
    new_stage: ScoutingStage,
) -> PlayerProjection:
    """
    Refine projections based on advancing scouting stage.

    Attributes revealed at the new stage get improved accuracy.
    Previously revealed attributes may also get refinement.

    Args:
        projection: Current player projection
        true_attributes: The player's actual attribute values
        new_stage: The new scouting stage reached

    Returns:
        Updated PlayerProjection with refined estimates
    """
    projection.scouting_stage = new_stage

    # Get attributes that should be visible at this stage
    visible_attrs = set(get_attributes_for_stage(new_stage))

    for attr_name in visible_attrs:
        true_value = true_attributes.get(attr_name)

        # Determine accuracy based on scouting progress
        if new_stage == ScoutingStage.COMPLETE:
            accuracy = ScoutingAccuracy.EXACT
        elif new_stage == ScoutingStage.ADVANCED:
            accuracy = ScoutingAccuracy.HIGH
        elif new_stage == ScoutingStage.INTERMEDIATE:
            accuracy = ScoutingAccuracy.MEDIUM
        else:
            accuracy = ScoutingAccuracy.LOW

        proj_value, min_est, max_est = generate_projection(
            true_value,
            accuracy,
            projection.scout_level,
        )

        projection.attributes[attr_name] = ScoutedAttribute(
            name=attr_name,
            projected_value=proj_value,
            accuracy=accuracy,
            true_value=true_value if accuracy == ScoutingAccuracy.EXACT else None,
            min_estimate=min_est,
            max_estimate=max_est,
        )

    return projection


def reveal_attribute(
    projection: PlayerProjection,
    attr_name: str,
    true_value: int,
) -> None:
    """
    Reveal the true value of a specific attribute.

    Used for special reveals like private workouts or medical reports.

    Args:
        projection: The projection to update
        attr_name: Name of the attribute to reveal
        true_value: The actual attribute value
    """
    projection.attributes[attr_name] = ScoutedAttribute(
        name=attr_name,
        projected_value=true_value,
        accuracy=ScoutingAccuracy.EXACT,
        true_value=true_value,
        min_estimate=true_value,
        max_estimate=true_value,
    )
