"""Read Registry - Central storage and lookup for all read definitions.

The ReadRegistry stores all read definitions and provides efficient lookup
by brain type, play concept, and coverage. Reads are registered at module
load time and then queried during simulation.

Usage:
    from huddle.simulation.v2.core.read_registry import (
        get_read_registry,
        register_read,
    )

    # At module init (e.g., in qb_reads.py):
    register_read(slant_flat_cover3_read)
    register_read(smash_cover2_read)

    # During simulation:
    registry = get_read_registry()
    reads = registry.get_reads_for_concept("smash", "cover_2", BrainType.QB)
"""

from __future__ import annotations

from typing import List, Optional, Dict
from .reads import ReadDefinition, BrainType


class ReadRegistry:
    """Central registry for all read definitions.

    Provides efficient lookup by:
    - Brain type (QB, DB, LB, OL)
    - Play concept (smash, flood, slant_flat, etc.)
    - Coverage (cover_2, cover_3, man, etc.)

    Internal storage uses nested dictionaries for O(1) lookup:
    _reads[brain_type][play_concept] -> List[ReadDefinition]
    """

    def __init__(self):
        self._reads: Dict[BrainType, Dict[str, List[ReadDefinition]]] = {
            BrainType.QB: {},
            BrainType.DB: {},
            BrainType.LB: {},
            BrainType.OL: {},
        }
        self._by_id: Dict[str, ReadDefinition] = {}

    def register(self, read: ReadDefinition) -> None:
        """Register a read definition.

        Args:
            read: The read definition to register

        Raises:
            ValueError: If a read with the same ID is already registered
        """
        if read.id in self._by_id:
            raise ValueError(f"Read '{read.id}' is already registered")

        # Store by ID
        self._by_id[read.id] = read

        # Store by brain type and concept
        brain_reads = self._reads[read.brain_type]
        concept = read.play_concept.lower()

        if concept not in brain_reads:
            brain_reads[concept] = []

        brain_reads[concept].append(read)

    def get_by_id(self, read_id: str) -> Optional[ReadDefinition]:
        """Get a read by its ID.

        Args:
            read_id: The unique read identifier

        Returns:
            The read definition, or None if not found
        """
        return self._by_id.get(read_id)

    def get_reads_for_concept(
        self,
        concept: str,
        coverage: str = "",
        brain_type: BrainType = BrainType.QB,
    ) -> List[ReadDefinition]:
        """Get all reads for a given concept and optionally filter by coverage.

        Args:
            concept: The play concept (e.g., "smash", "flood")
            coverage: Optional coverage to filter by (e.g., "cover_2")
            brain_type: Which brain type (default: QB)

        Returns:
            List of matching read definitions
        """
        concept = concept.lower()
        brain_reads = self._reads[brain_type]

        if concept not in brain_reads:
            return []

        reads = brain_reads[concept]

        # Filter by coverage if specified
        if coverage:
            reads = [r for r in reads if r.applies_to_coverage(coverage)]

        return reads

    def get_all_reads(self, brain_type: Optional[BrainType] = None) -> List[ReadDefinition]:
        """Get all registered reads, optionally filtered by brain type.

        Args:
            brain_type: Optional brain type filter

        Returns:
            List of all matching read definitions
        """
        if brain_type is not None:
            return list(self._by_id.values())

        return [r for r in self._by_id.values() if r.brain_type == brain_type]

    def get_concepts(self, brain_type: BrainType = BrainType.QB) -> List[str]:
        """Get all registered concepts for a brain type.

        Returns:
            List of concept names (e.g., ["smash", "flood", "slant_flat"])
        """
        return list(self._reads[brain_type].keys())

    def get_coverages_for_concept(
        self,
        concept: str,
        brain_type: BrainType = BrainType.QB,
    ) -> List[str]:
        """Get all coverages that have reads for a concept.

        Args:
            concept: The play concept
            brain_type: Which brain type

        Returns:
            List of coverage names (e.g., ["cover_2", "cover_3"])
        """
        reads = self.get_reads_for_concept(concept, "", brain_type)

        coverages = set()
        for read in reads:
            if read.applicable_coverages:
                coverages.update(c.lower() for c in read.applicable_coverages)

        return sorted(coverages)

    def clear(self) -> None:
        """Clear all registered reads. Useful for testing."""
        self._by_id.clear()
        for brain_type in BrainType:
            self._reads[brain_type] = {}

    def stats(self) -> Dict[str, any]:
        """Get statistics about registered reads.

        Returns:
            Dict with counts by brain type and total
        """
        stats = {
            "total": len(self._by_id),
            "by_brain": {},
            "by_concept": {},
        }

        for brain_type in BrainType:
            brain_count = sum(len(reads) for reads in self._reads[brain_type].values())
            stats["by_brain"][brain_type.value] = brain_count

            for concept, reads in self._reads[brain_type].items():
                key = f"{brain_type.value}:{concept}"
                stats["by_concept"][key] = len(reads)

        return stats


# =============================================================================
# Global Registry Instance
# =============================================================================

_registry = ReadRegistry()


def get_read_registry() -> ReadRegistry:
    """Get the global read registry instance."""
    return _registry


def register_read(read: ReadDefinition) -> None:
    """Register a read with the global registry.

    Convenience function that wraps registry.register().

    Args:
        read: The read definition to register
    """
    _registry.register(read)


def get_reads_for_situation(
    concept: str,
    coverage: str,
    brain_type: BrainType = BrainType.QB,
) -> List[ReadDefinition]:
    """Get reads for a specific game situation.

    Convenience function for the common lookup pattern.

    Args:
        concept: The play concept being run
        coverage: The detected defensive coverage
        brain_type: Which brain is making the read

    Returns:
        List of applicable read definitions
    """
    return _registry.get_reads_for_concept(concept, coverage, brain_type)
