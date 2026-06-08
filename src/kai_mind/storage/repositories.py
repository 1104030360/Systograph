"""Repository protocols for KAI-Mind managed storage."""

from kai_mind.core.services.manual_mapping_service import (
    InMemoryManualMappingRepository,
    ManualMappingRepository,
)
from kai_mind.core.services.mapping_proposal_service import (
    InMemoryMappingProposalRepository,
    MappingProposalRepository,
)

__all__ = [
    "InMemoryManualMappingRepository",
    "InMemoryMappingProposalRepository",
    "ManualMappingRepository",
    "MappingProposalRepository",
]
