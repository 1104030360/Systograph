from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from kai_mind.core.models.ai_system_map_v2 import (
    CanonicalEdge,
    CanonicalRiskHint,
)
from kai_mind.core.models.profile_signal import (
    ProfileFinding,
    ReferenceCapabilityAssessment,
)
from kai_mind.core.services.profile_finding_rules import (
    activation,
    evidence_strength,
    infer_profile_status,
)
from kai_mind.core.services.profile_registry_loader import (
    ProfileMetadataEntry,
)
from kai_mind.core.services.profile_rule_definitions import (
    ProfileRuleDefinition,
)


@dataclass(frozen=True, slots=True)
class ProfileFindingContext:
    by_node: Mapping[str, ReferenceCapabilityAssessment]
    relationships: Mapping[str, tuple[CanonicalEdge, ...]]
    direct_evidence_ids: frozenset[str]
    risk_hints: tuple[CanonicalRiskHint, ...]
    build_id: str
    scan_id: str
    environment_id: str


def build_profile_finding(
    definition: ProfileRuleDefinition,
    metadata: ProfileMetadataEntry,
    context: ProfileFindingContext,
) -> ProfileFinding:
    required = tuple(
        context.by_node[node] for node in definition.required_node_ids
    )
    relationship_evidence, relationship_direct = _relationship_evidence(
        definition.required_relationship,
        context.relationships,
        context.direct_evidence_ids,
    )
    relationship_met = definition.required_relationship is None or bool(
        relationship_direct
    )
    detected_count = sum(item.status == "detected" for item in required)
    status, depth, uncertainty = infer_profile_status(
        required,
        relationship_met=relationship_met,
    )
    evidence_ids = tuple(
        dict.fromkeys(
            item for assessment in required for item in assessment.evidence_ids
        )
    )
    evidence_ids = tuple(
        dict.fromkeys((*evidence_ids, *relationship_evidence))
    )
    direct = tuple(
        dict.fromkeys(
            item
            for assessment in required
            for item in assessment.direct_evidence_ids
        )
    )
    direct = tuple(dict.fromkeys((*direct, *relationship_direct)))
    indirect = tuple(
        dict.fromkeys(
            item
            for assessment in required
            for item in assessment.indirect_evidence_ids
        )
    )
    indirect = tuple(
        dict.fromkeys(
            (
                *indirect,
                *(
                    item
                    for item in relationship_evidence
                    if item not in relationship_direct
                ),
            )
        )
    )
    negative = tuple(
        dict.fromkeys(
            item
            for assessment in required
            for item in assessment.explicit_negative_evidence_ids
        )
    )
    conflicts = tuple(
        conflict
        for assessment in required
        for conflict in assessment.conflict_fields
    )
    related_component_ids = tuple(
        dict.fromkeys(
            component_id
            for item in required
            for component_id in item.related_component_ids
        )
    )
    related_unmapped_component_ids = tuple(
        dict.fromkeys(
            unmapped_id
            for item in required
            for unmapped_id in item.related_unmapped_component_ids
        )
    )
    related_candidate_ids = tuple(
        dict.fromkeys(
            candidate_id
            for item in required
            for candidate_id in (
                item.related_capability_candidate_component_ids
            )
        )
    )
    navigation_targets = {
        *related_component_ids,
        *related_unmapped_component_ids,
        *related_candidate_ids,
        *evidence_ids,
    }
    return ProfileFinding(
        profile_id=definition.profile_id,
        label=metadata.display_name,
        description=metadata.description,
        status=status,
        activation=activation(required),
        primary_axis=metadata.primary_axis,
        secondary_axes=metadata.secondary_axes,
        implementation_depth_level=depth,
        implementation_depth_reason=(
            "Required reference capabilities are directly observed."
            if status == "detected"
            else uncertainty
        ),
        evidence_ids=evidence_ids,
        direct_evidence_ids=direct,
        indirect_evidence_ids=indirect,
        explicit_negative_evidence_ids=negative,
        conflict_fields=conflicts,
        detected_signals=tuple(
            item.reference_node_id
            for item in required
            if item.status == "detected"
        ),
        missing_signals=tuple(
            item.reference_node_id
            for item in required
            if item.status != "detected"
        ),
        coverage_detected=detected_count,
        coverage_total=len(required),
        not_detected_coverage_gate_passed=(status == "not_detected"),
        evidence_strength=evidence_strength(status, direct),
        related_component_ids=related_component_ids,
        related_unmapped_component_ids=related_unmapped_component_ids,
        related_capability_candidate_component_ids=related_candidate_ids,
        related_risk_hint_ids=tuple(
            item.risk_id
            for item in context.risk_hints
            if item.target in navigation_targets
            or item.evidence_id in evidence_ids
        ),
        recommended_next_checks=(
            ()
            if status in {"detected", "not_detected"}
            else metadata.recommended_next_checks
        ),
        uncertainty=uncertainty or metadata.default_uncertainty,
        build_id=context.build_id,
        scan_id=context.scan_id,
        environment_id=context.environment_id,
    )


def _relationship_evidence(
    relationship: str | None,
    relationships: Mapping[str, Sequence[CanonicalEdge]],
    direct_evidence_ids: frozenset[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if relationship is None:
        return (), ()
    evidence = tuple(
        dict.fromkeys(
            evidence_id
            for edge in relationships.get(relationship, ())
            if edge.status in {"observed", "detected"}
            for evidence_id in edge.evidence_ids
        )
    )
    direct = tuple(item for item in evidence if item in direct_evidence_ids)
    return evidence, direct
