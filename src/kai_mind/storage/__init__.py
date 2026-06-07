"""Storage boundary exports for KAI-Mind managed persistence."""

from kai_mind.storage.repositories import (
    InMemoryManualMappingRepository,
    ManualMappingRepository,
)

__all__ = [
    "InMemoryManualMappingRepository",
    "ManualMappingRepository",
]
