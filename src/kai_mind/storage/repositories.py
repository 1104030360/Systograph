"""Repository protocols for KAI-Mind managed storage."""

from kai_mind.core.services.manual_mapping_service import (
    InMemoryManualMappingRepository,
    ManualMappingRepository,
)

__all__ = [
    "InMemoryManualMappingRepository",
    "ManualMappingRepository",
]
