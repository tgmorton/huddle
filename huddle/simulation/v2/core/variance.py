"""Variance System - Human factors that create realistic unpredictability.

This module adds attribute-modulated noise to simulation systems.
Higher skill = tighter distributions (more consistent performance).

Three noise layers:
1. Recognition noise - How quickly/accurately players perceive situations
2. Execution noise - Motor variance in physical actions (cuts, throws, tackles)
3. Decision noise - Cognitive errors under pressure

Design philosophy:
- Physics stays deterministic (positions, collisions, trajectories)
- Human factors add variance (recognition, execution, decisions)
- All variance is attribute-modulated (skill reduces variance)
- Optional deterministic mode for film study/debugging
"""

from __future__ import annotations

import random
import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SimulationMode(str, Enum):
    """Simulation variance mode."""
    DETERMINISTIC = "deterministic"  # No variance - for film study, debugging
    REALISTIC = "realistic"          # Full variance - for gameplay


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class VarianceConfig:
    """Configuration for variance system."""
    mode: SimulationMode = SimulationMode.REALISTIC
    seed: Optional[int] = None  # For reproducible randomness

    # Layer multipliers (0 = disabled, 1 = normal, 2 = exaggerated)
    recognition_multiplier: float = 1.0
    execution_multiplier: float = 1.0
    decision_multiplier: float = 1.0

    # Inner Weather integration (future)
    pressure_affects_variance: bool = True
    fatigue_affects_variance: bool = True


# Global config (can be overridden per-orchestrator)
_config = VarianceConfig()


def set_config(config: VarianceConfig) -> None:
    """Set global variance configuration."""
    global _config
    _config = config
    if config.seed is not None:
        random.seed(config.seed)


def get_config() -> VarianceConfig:
    """Get current variance configuration."""
    return _config


def is_deterministic() -> bool:
    """Check if running in deterministic mode."""
    return _config.mode == SimulationMode.DETERMINISTIC


# =============================================================================
# Utility Functions
# =============================================================================

def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max."""
    return max(min_val, min(max_val, value))


def sigmoid_probability(
    x: float,
    center: float = 50.0,
    steepness: float = 0.1,
    min_prob: float = 0.05,
    max_prob: float = 0.95,
) -> float:
    """Calculate probability using a sigmoid curve.

    Creates an S-curve that provides better rating differentiation at extremes.
    Linear curves treat the difference between 99 and 100 the same as 50 and 51,
    but in reality elite players are in a class of their own.

    Args:
        x: Input value (typically a rating 0-100 or rating difference)
        center: The x value where probability is 50%
        steepness: How sharp the S-curve is (higher = sharper transition)
        min_prob: Minimum probability (floor)
        max_prob: Maximum probability (ceiling)

    Returns:
        Probability between min_prob and max_prob

    Examples:
        # Catch probability based on catch rating
        >>> sigmoid_probability(50, center=50, steepness=0.08)  # ~0.50
        >>> sigmoid_probability(90, center=50, steepness=0.08)  # ~0.95
        >>> sigmoid_probability(30, center=50, steepness=0.08)  # ~0.12

        # Win probability based on rating difference
        >>> sigmoid_probability(10, center=0, steepness=0.15)   # Attacker +10
        >>> sigmoid_probability(-10, center=0, steepness=0.15)  # Defender +10
    """
    # Calculate base sigmoid: 1 / (1 + e^(-k*(x-center)))
    exponent = -steepness * (x - center)
    # Clamp exponent to prevent overflow
    exponent = max(-50, min(50, exponent))
    base_prob = 1.0 / (1.0 + math.exp(exponent))

    # Scale to [min_prob, max_prob] range
    return min_prob + base_prob * (max_prob - min_prob)


def sigmoid_matchup_probability(
    attacker_rating: int,
    defender_rating: int,
    base_advantage: float = 0.0,
    steepness: float = 0.08,
    min_prob: float = 0.10,
    max_prob: float = 0.90,
) -> float:
    """Calculate probability for attacker winning a matchup.

    Used for catch contests, block battles, tackle attempts, etc.
    Better than linear formulas because it:
    - Respects that 99 vs 50 is nearly automatic
    - Provides meaningful differentiation at elite levels
    - Avoids unrealistic probabilities at extremes

    Args:
        attacker_rating: Attacker's relevant rating (0-100)
        defender_rating: Defender's relevant rating (0-100)
        base_advantage: Baseline advantage to attacker (e.g., 0.1 for home field)
        steepness: How much rating difference matters (0.05=gradual, 0.15=sharp)
        min_prob: Floor probability even for worst mismatch
        max_prob: Ceiling probability even for best mismatch

    Returns:
        Probability that attacker wins the contest

    Examples:
        # Catch contest: WR catch vs DB coverage
        >>> sigmoid_matchup_probability(90, 70)  # Elite WR vs average DB: ~0.75
        >>> sigmoid_matchup_probability(70, 90)  # Average WR vs elite DB: ~0.25
        >>> sigmoid_matchup_probability(80, 80)  # Even matchup: ~0.50

        # Block battle: OL block vs DL power
        >>> sigmoid_matchup_probability(85, 75, base_advantage=0.1)  # OL advantage
    """
    diff = (attacker_rating - defender_rating) + (base_advantage * 20)  # Scale advantage
    return sigmoid_probability(diff, center=0, steepness=steepness, min_prob=min_prob, max_prob=max_prob)


def attribute_to_factor(attribute: int, base: int = 75) -> float:
    """Convert 0-100 attribute to a factor around 1.0.

    Args:
        attribute: Player attribute (0-100)
        base: Baseline attribute (default 75 = average NFL player)

    Returns:
        Factor where 1.0 = average, <1.0 = better, >1.0 = worse
        Used to scale variance (higher skill = lower variance)
    """
    # Map 50-100 to factor of 1.5-0.5 (inverse relationship)
    # 50 attribute = 1.5x variance
    # 75 attribute = 1.0x variance
    # 100 attribute = 0.5x variance
    normalized = clamp((attribute - 50) / 50, 0, 1)
    return 1.5 - normalized  # 1.5 at 50, 0.5 at 100


# =============================================================================
# Layer 1: Recognition Noise
# =============================================================================

def recognition_delay(
    base_delay: float,
    awareness: int,
    pressure: float = 0.0,
    fatigue: float = 0.0,
) -> float:
    """Add variance to recognition/reaction delay.

    Args:
        base_delay: Base delay in seconds (e.g., 0.2 for DB read)
        awareness: Player awareness attribute (0-100)
        pressure: Inner Weather pressure (0-1), increases variance
        fatigue: Inner Weather fatigue (0-1), increases delay

    Returns:
        Actual delay with variance applied
    """
    if is_deterministic():
        return base_delay

    # Attribute factor (higher awareness = tighter variance)
    attr_factor = attribute_to_factor(awareness)

    # Pressure widens variance
    pressure_factor = 1.0 + (pressure * 0.5) if _config.pressure_affects_variance else 1.0

    # Fatigue increases base delay
    fatigue_factor = 1.0 + (fatigue * 0.3) if _config.fatigue_affects_variance else 1.0

    # Calculate variance (std dev as fraction of base)
    variance_pct = 0.15 * attr_factor * pressure_factor * _config.recognition_multiplier

    # Apply Gaussian noise
    noise = random.gauss(0, base_delay * variance_pct)

    # Apply fatigue to base
    adjusted_base = base_delay * fatigue_factor

    # Never go negative
    return max(0.05, adjusted_base + noise)


def recognition_accuracy(
    awareness: int,
    pressure: float = 0.0,
) -> float:
    """Get recognition accuracy factor (0-1).

    Higher = more accurate reads.
    Used for: coverage recognition, route anticipation, blitz pickup.

    Args:
        awareness: Player awareness attribute
        pressure: Inner Weather pressure

    Returns:
        Accuracy factor (0.7-1.0 typically)
    """
    if is_deterministic():
        return 1.0

    # Base accuracy from attribute
    base = 0.7 + (awareness / 100) * 0.3  # 0.7 to 1.0

    # Pressure reduces accuracy
    pressure_penalty = pressure * 0.15 if _config.pressure_affects_variance else 0

    # Small random variance
    noise = random.gauss(0, 0.05 * _config.recognition_multiplier)

    return clamp(base - pressure_penalty + noise, 0.5, 1.0)


# =============================================================================
# Layer 2: Execution Noise
# =============================================================================

def execution_timing(
    base_time: float,
    skill_attribute: int,
    fatigue: float = 0.0,
) -> float:
    """Add variance to execution timing (route breaks, cuts, releases).

    Args:
        base_time: Base time for action (seconds)
        skill_attribute: Relevant skill (route_running, agility, etc.)
        fatigue: Inner Weather fatigue

    Returns:
        Actual timing with variance
    """
    if is_deterministic():
        return base_time

    attr_factor = attribute_to_factor(skill_attribute)
    fatigue_factor = 1.0 + (fatigue * 0.2) if _config.fatigue_affects_variance else 1.0

    # Timing variance (std dev)
    variance_pct = 0.1 * attr_factor * fatigue_factor * _config.execution_multiplier

    noise = random.gauss(0, base_time * variance_pct)

    return max(0.01, base_time + noise)


def execution_precision(
    base_value: float,
    skill_attribute: int,
    fatigue: float = 0.0,
) -> float:
    """Add variance to execution precision (angles, positions, distances).

    Args:
        base_value: Base value (yards, degrees, etc.)
        skill_attribute: Relevant skill attribute
        fatigue: Inner Weather fatigue

    Returns:
        Value with variance applied
    """
    if is_deterministic():
        return base_value

    attr_factor = attribute_to_factor(skill_attribute)
    fatigue_factor = 1.0 + (fatigue * 0.25) if _config.fatigue_affects_variance else 1.0

    # Precision variance scales with value
    variance = abs(base_value) * 0.1 * attr_factor * fatigue_factor * _config.execution_multiplier

    noise = random.gauss(0, variance)

    return base_value + noise


def route_break_sharpness(
    base_sharpness: float,
    route_running: int,
    fatigue: float = 0.0,
) -> float:
    """Get route break sharpness with variance.

    Args:
        base_sharpness: Ideal sharpness (0-1, 1=perfect cut)
        route_running: Route running attribute
        fatigue: Inner Weather fatigue

    Returns:
        Actual sharpness (can exceed base for elite players)
    """
    if is_deterministic():
        return base_sharpness

    # Higher route running = tighter variance AND higher mean
    attr_factor = attribute_to_factor(route_running)
    skill_bonus = (route_running - 75) / 100  # -0.25 to +0.25

    fatigue_penalty = fatigue * 0.15 if _config.fatigue_affects_variance else 0

    variance = 0.15 * attr_factor * _config.execution_multiplier
    noise = random.gauss(0, variance)

    result = base_sharpness + skill_bonus + noise - fatigue_penalty

    return clamp(result, 0.3, 1.0)


def pursuit_angle_accuracy(
    awareness: int,
    tackle: int,
    fatigue: float = 0.0,
) -> float:
    """Get pursuit angle accuracy factor.

    Args:
        awareness: Awareness attribute (reading play)
        tackle: Tackle attribute (pursuit technique)
        fatigue: Inner Weather fatigue

    Returns:
        Accuracy factor (0.7-1.0), used to offset pursuit angle
    """
    if is_deterministic():
        return 1.0

    # Combined attribute
    combined = (awareness + tackle) / 2
    attr_factor = attribute_to_factor(int(combined))

    fatigue_penalty = fatigue * 0.1 if _config.fatigue_affects_variance else 0

    base = 0.85 + (combined - 75) / 250  # 0.75 to 0.95
    variance = 0.08 * attr_factor * _config.execution_multiplier
    noise = random.gauss(0, variance)

    return clamp(base + noise - fatigue_penalty, 0.6, 1.0)


# =============================================================================
# Layer 3: Decision Noise
# =============================================================================

def should_make_suboptimal_decision(
    awareness: int,
    pressure: float = 0.0,
    cognitive_load: float = 0.0,
) -> bool:
    """Check if player makes a suboptimal decision due to cognitive factors.

    Args:
        awareness: Awareness/IQ attribute
        pressure: Inner Weather pressure (0-1)
        cognitive_load: Situational complexity (0-1)

    Returns:
        True if player should make a mistake
    """
    if is_deterministic():
        return False

    # Base error rate (inverse of awareness)
    base_rate = 0.15 * attribute_to_factor(awareness)

    # Pressure increases errors
    pressure_factor = 1.0 + (pressure * 1.0) if _config.pressure_affects_variance else 1.0

    # Cognitive load increases errors
    load_factor = 1.0 + (cognitive_load * 0.5)

    error_chance = base_rate * pressure_factor * load_factor * _config.decision_multiplier

    return random.random() < clamp(error_chance, 0, 0.4)  # Cap at 40%


def decision_hesitation(
    base_time: float,
    awareness: int,
    confidence: float = 1.0,
) -> float:
    """Add hesitation to decision timing.

    Args:
        base_time: Base decision time
        awareness: Awareness/IQ attribute
        confidence: Inner Weather confidence (0-1)

    Returns:
        Actual decision time with possible hesitation
    """
    if is_deterministic():
        return base_time

    attr_factor = attribute_to_factor(awareness)

    # Low confidence adds hesitation
    confidence_penalty = (1.0 - confidence) * 0.3 if _config.pressure_affects_variance else 0

    variance = base_time * 0.2 * attr_factor * _config.decision_multiplier
    noise = random.gauss(0, variance)

    return max(0.05, base_time + noise + confidence_penalty)


def target_selection_noise(
    rankings: list[tuple[str, float]],
    awareness: int,
    pressure: float = 0.0,
) -> list[tuple[str, float]]:
    """Add noise to target selection rankings.

    This can cause a player to pick a suboptimal target.

    Args:
        rankings: List of (target_id, score) tuples, highest score = best
        awareness: Decision-maker's awareness
        pressure: Inner Weather pressure

    Returns:
        Potentially reordered rankings
    """
    if is_deterministic() or len(rankings) <= 1:
        return rankings

    attr_factor = attribute_to_factor(awareness)
    pressure_factor = 1.0 + (pressure * 0.5) if _config.pressure_affects_variance else 1.0

    # Add noise to each score
    noise_scale = 0.15 * attr_factor * pressure_factor * _config.decision_multiplier

    noisy_rankings = []
    for target_id, score in rankings:
        noise = random.gauss(0, abs(score) * noise_scale)
        noisy_rankings.append((target_id, score + noise))

    # Re-sort by noisy scores
    noisy_rankings.sort(key=lambda x: x[1], reverse=True)

    return noisy_rankings
