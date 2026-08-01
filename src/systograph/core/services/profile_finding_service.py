from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from systograph.core.models.ai_system_map_v2 import (
    AiSystemMapV2,
    CanonicalEdge,
)
from systograph.core.models.profile_signal import (
    ProfileFinding,
    ReferenceCapabilityAssessment,
)
from systograph.core.services.profile_finding_assembler import (
    ProfileFindingContext,
    build_profile_finding,
)
from systograph.core.services.profile_registry_loader import (
    ProfileMetadataRegistry,
    ProfileRegistryLoader,
)
from systograph.core.services.profile_relationship_alias_loader import (
    ProfileRelationshipAliasLoader,
)
from systograph.core.services.profile_rule_definitions import (
    MVP_CAPABILITY_PROFILE_IDS,
    PROFILE_RULE_DEFINITIONS,
)


class ProfileFindingService:
    def __init__(
        self,
        *,
        metadata_registry: ProfileMetadataRegistry | None = None,
    ) -> None:
        registry = (
            metadata_registry
            if metadata_registry is not None
            else ProfileRegistryLoader().load_default()
        )
        self._metadata_registry = registry.require_profile_ids(
            MVP_CAPABILITY_PROFILE_IDS
        )
        # Single source of truth: profile_relationship_alias.toml.
        self._relationship_aliases = ProfileRelationshipAliasLoader().load()

    def infer(
        self,
        assessments: Sequence[ReferenceCapabilityAssessment],
        *,
        system_map: AiSystemMapV2,
        build_id: str,
        scan_id: str,
        environment_id: str,
    ) -> tuple[ProfileFinding, ...]:
        by_node = {item.reference_node_id: item for item in assessments}
        relationship_lists: dict[str, list[CanonicalEdge]] = defaultdict(list)
        for edge in system_map.edges:
            relationship_lists[edge.relationship].append(edge)
        context = ProfileFindingContext(
            by_node=by_node,
            relationships={
                relationship: tuple(edges)
                for relationship, edges in relationship_lists.items()
            },
            relationship_aliases=self._relationship_aliases,
            direct_evidence_ids=frozenset(
                item.evidence_id
                for item in system_map.evidence
                if item.evidence_kind == "direct"
            ),
            risk_hints=tuple(system_map.risk_hints),
            build_id=build_id,
            scan_id=scan_id,
            environment_id=environment_id,
        )
        return tuple(
            build_profile_finding(
                definition,
                self._metadata_registry.metadata_for(definition.profile_id),
                context,
            )
            for definition in PROFILE_RULE_DEFINITIONS
        )
