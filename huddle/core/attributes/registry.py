"""Attribute registry and player attribute container."""

from dataclasses import dataclass, field
from typing import Iterator, Optional

from huddle.core.attributes.base import (
    ALL_ATTRIBUTES,
    AttributeCategory,
    AttributeDefinition,
)


class AttributeRegistry:
    """
    Central registry for all attribute definitions.

    This is a singleton-style class that holds all registered attributes.
    Attributes are registered at module load time from base.py.
    Can be extended at runtime for different management levels.
    """

    _attributes: dict[str, AttributeDefinition] = {}
    _initialized: bool = False

    @classmethod
    def initialize(cls) -> None:
        """Initialize registry with default attributes."""
        if cls._initialized:
            return
        for attr in ALL_ATTRIBUTES:
            cls.register(attr)
        cls._initialized = True

    @classmethod
    def register(cls, attr_def: AttributeDefinition) -> None:
        """Register an attribute definition."""
        cls._attributes[attr_def.name] = attr_def

    @classmethod
    def get(cls, name: str) -> AttributeDefinition:
        """Get an attribute definition by name."""
        cls.initialize()
        if name not in cls._attributes:
            raise KeyError(f"Unknown attribute: {name}")
        return cls._attributes[name]

    @classmethod
    def get_all(cls) -> list[AttributeDefinition]:
        """Get all registered attributes."""
        cls.initialize()
        return list(cls._attributes.values())

    @classmethod
    def get_by_category(cls, category: AttributeCategory) -> list[AttributeDefinition]:
        """Get all attributes in a category."""
        cls.initialize()
        return [a for a in cls._attributes.values() if a.category == category]

    @classmethod
    def get_for_position(cls, position: str) -> list[AttributeDefinition]:
        """
        Get attributes relevant to a position, sorted by weight.

        Returns attributes that have a non-zero weight for the given position.
        """
        cls.initialize()
        relevant = [
            (a, a.position_weights.get(position, 0.0)) for a in cls._attributes.values()
        ]
        # Filter to only attributes with weight > 0, sorted by weight descending
        return [a for a, w in sorted(relevant, key=lambda x: -x[1]) if w > 0]

    @classmethod
    def get_position_weight(cls, attr_name: str, position: str) -> float:
        """Get the weight of an attribute for a specific position."""
        attr = cls.get(attr_name)
        return attr.position_weights.get(position, 0.0)


@dataclass
class PlayerAttributes:
    """
    Container for a player's attribute values.

    Uses a dictionary for flexibility - attributes can be added/removed
    without changing the class structure. This supports different
    management levels (high school, college, pro) having different
    attribute sets.
    """

    _values: dict[str, int] = field(default_factory=dict)

    def get(self, attr_name: str, default: int = 50) -> int:
        """Get an attribute value, defaulting to 50 if not set."""
        return self._values.get(attr_name, default)

    def set(self, attr_name: str, value: int) -> None:
        """Set an attribute value, clamping to valid range."""
        try:
            attr_def = AttributeRegistry.get(attr_name)
            self._values[attr_name] = attr_def.clamp(value)
        except KeyError:
            # Unknown attribute - store raw value
            self._values[attr_name] = max(0, min(99, value))

    def __getitem__(self, attr_name: str) -> int:
        """Allow dict-like access: attrs['speed']."""
        return self.get(attr_name)

    def __setitem__(self, attr_name: str, value: int) -> None:
        """Allow dict-like assignment: attrs['speed'] = 85."""
        self.set(attr_name, value)

    def __iter__(self) -> Iterator[str]:
        """Iterate over attribute names."""
        return iter(self._values)

    def __len__(self) -> int:
        """Number of set attributes."""
        return len(self._values)

    def items(self) -> Iterator[tuple[str, int]]:
        """Iterate over (name, value) pairs."""
        return iter(self._values.items())

    def calculate_overall(self, position: str) -> int:
        """
        Calculate overall rating based on position-weighted attributes.

        The overall is a weighted average of attributes that matter for
        the given position.
        """
        relevant_attrs = AttributeRegistry.get_for_position(position)
        if not relevant_attrs:
            # No position-specific weights, return average of all
            if self._values:
                return int(sum(self._values.values()) / len(self._values))
            return 50

        total_weight = 0.0
        weighted_sum = 0.0

        for attr_def in relevant_attrs:
            weight = attr_def.position_weights.get(position, 0.0)
            value = self.get(attr_def.name)
            weighted_sum += value * weight
            total_weight += weight

        if total_weight == 0:
            return 50

        return int(weighted_sum / total_weight)

    def get_potential(self, attr_name: str) -> Optional[int]:
        """
        Get potential ceiling for an attribute.

        Args:
            attr_name: The base attribute name (e.g., "speed", not "speed_potential")

        Returns:
            Potential ceiling value, or None if not set
        """
        return self._values.get(f"{attr_name}_potential")

    def set_potential(self, attr_name: str, value: int) -> None:
        """
        Set potential ceiling for an attribute.

        Args:
            attr_name: The base attribute name (e.g., "speed", not "speed_potential")
            value: Potential ceiling value (clamped to 0-99)
        """
        self._values[f"{attr_name}_potential"] = max(0, min(99, value))

    def get_growth_room(self, attr_name: str) -> int:
        """
        Get remaining growth room for an attribute.

        Args:
            attr_name: The base attribute name

        Returns:
            Difference between potential and current value, or 0 if no potential set
        """
        current = self.get(attr_name)
        potential = self.get_potential(attr_name)
        if potential is None:
            return 0
        return max(0, potential - current)

    def get_all_potentials(self) -> dict[str, int]:
        """
        Get all potential values.

        Returns:
            Dict of {attr_name: potential_value} (without _potential suffix in keys)
        """
        potentials = {}
        for key, value in self._values.items():
            if key.endswith("_potential"):
                base_name = key[:-10]  # Remove "_potential" suffix
                potentials[base_name] = value
        return potentials

    def to_dict(self) -> dict[str, int]:
        """Convert to plain dictionary for serialization."""
        return dict(self._values)

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> "PlayerAttributes":
        """Create from dictionary."""
        attrs = cls()
        for name, value in data.items():
            attrs.set(name, value)
        return attrs

    def copy(self) -> "PlayerAttributes":
        """Create a copy of these attributes."""
        return PlayerAttributes.from_dict(self._values.copy())


# Initialize registry on module load
AttributeRegistry.initialize()
