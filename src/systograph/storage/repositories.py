"""Repository protocols for Systograph managed storage."""

from systograph.core.services.manual_mapping_service import (
    InMemoryManualMappingRepository,
    ManualMappingRepository,
)
from systograph.core.services.mapping_proposal_service import (
    InMemoryMappingProposalRepository,
    MappingProposalRepository,
)

__all__ = [
    "InMemoryManualMappingRepository",
    "InMemoryMappingProposalRepository",
    "ManualMappingRepository",
    "MappingProposalRepository",
]
