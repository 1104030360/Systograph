from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from systograph.core.models.ai_system_map_v2 import CanonicalEdge
from systograph.core.models.recommended_next_check import RecommendedNextCheck

EdgeTier: TypeAlias = Literal["L1", "L2"]
EdgeStatus: TypeAlias = Literal["observed", "undetermined"]


@dataclass(frozen=True, slots=True)
class EdgeCandidate:
    source: str
    target: str
    relationship: str
    tier: EdgeTier
    rank: int
    status: EdgeStatus
    evidence_ids: tuple[str, ...]
    undetermined_reason: str | None

    @property
    def merge_key(self) -> tuple[str, str, str]:
        return (self.source, self.target, self.relationship)

    @property
    def sort_key(self) -> tuple[int, str, str, str, tuple[str, ...]]:
        return (
            self.rank,
            self.source,
            self.target,
            self.relationship,
            self.evidence_ids,
        )


@dataclass(frozen=True, slots=True)
class UaEdgeDerivationStats:
    calls_seen: int = 0
    imports_seen: int = 0
    factories_seen: int = 0
    ignored_external_imports: int = 0
    l1_emitted: int = 0
    l2_emitted: int = 0
    missing_component_evidence_ids: int = 0
    components_without_code_residence: int = 0
    dropped_unresolved_source: int = 0
    dropped_unresolved_target: int = 0
    dropped_missing_evidence: int = 0
    dropped_missing_relationship: int = 0
    dropped_self_loop: int = 0
    ambiguous_calls: int = 0
    ambiguous_factories: int = 0
    ambiguous_imports: int = 0
    discarded_lower_tier: int = 0
    source_cap_dropped_l1: int = 0
    source_cap_dropped_l2: int = 0
    global_cap_dropped_l1: int = 0
    global_cap_dropped_l2: int = 0


@dataclass(frozen=True, slots=True)
class UaEdgeDerivationResult:
    edges: tuple[CanonicalEdge, ...]
    warnings: tuple[str, ...]
    recommended_next_checks: tuple[RecommendedNextCheck, ...]
    stats: UaEdgeDerivationStats


@dataclass(frozen=True, slots=True)
class EdgeMergeOutcome:
    candidates: tuple[EdgeCandidate, ...]
    discarded_lower_tier: int
    source_cap_dropped_l1: int
    source_cap_dropped_l2: int
    global_cap_dropped_l1: int
    global_cap_dropped_l2: int
