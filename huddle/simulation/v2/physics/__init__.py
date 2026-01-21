"""Physics layer - movement, bodies, and spatial reasoning."""

from .movement import MovementProfile, MovementSolver, MovementResult
from .body import BodyModel
from .spatial import SphereOfInfluence, ConeOfInfluence, Influence
from .calibration import (
    NGSCalibration,
    RecoveryState,
    get_calibration,
    get_calibration_for_position_enum,
)
from .ball_flight import (
    calculate_critical_spin,
    calculate_spin_rate,
    calculate_drag_factor,
    calculate_lateral_drift,
    is_spiral_stable,
    get_initial_orientation,
    orientation_at_progress,
    DRAG_COEFFICIENT,
    STABILITY_CONSTANT,
    SPIN_RATES,
)

__all__ = [
    # Movement
    "MovementProfile",
    "MovementSolver",
    "MovementResult",
    # NGS Calibration
    "NGSCalibration",
    "RecoveryState",
    "get_calibration",
    "get_calibration_for_position_enum",
    # Bodies
    "BodyModel",
    # Spatial
    "SphereOfInfluence",
    "ConeOfInfluence",
    "Influence",
    # Ball flight physics
    "calculate_critical_spin",
    "calculate_spin_rate",
    "calculate_drag_factor",
    "calculate_lateral_drift",
    "is_spiral_stable",
    "get_initial_orientation",
    "orientation_at_progress",
    "DRAG_COEFFICIENT",
    "STABILITY_CONSTANT",
    "SPIN_RATES",
]
