"""Repository protocols for KAI-Mind managed storage."""

from kai_mind.core.services.manual_mapping_service import (
    InMemoryManualMappingRepository,
    ManualMappingRepository,
)
from kai_mind.core.services.mapping_proposal_service import (
    InMemoryMappingProposalRepository,
    MappingProposalRepository,
)
from kai_mind.core.services.scan_boundary_review_service import (
    InMemoryScanBoundaryRepository,
    ScanBoundaryRepository,
)

__all__ = [
    "InMemoryManualMappingRepository",
    "InMemoryMappingProposalRepository",
    "InMemoryScanBoundaryRepository",
    "ManualMappingRepository",
    "MappingProposalRepository",
    "ScanBoundaryRepository",
]
