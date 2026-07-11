from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence

from kai_mind.core.models.ai_system_map_v2 import (
    AiSystemMapV2,
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
from kai_mind.core.services.profile_registry import (
    PROFILE_DEFINITIONS,
    ProfileDefinition,
)


class ProfileFindingService:
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
        relationships: dict[str, list[CanonicalEdge]] = defaultdict(list)
        for edge in system_map.edges:
            relationships[edge.relationship].append(edge)
        direct_evidence_ids = {
            item.evidence_id
            for item in system_map.evidence
            if item.evidence_kind == "direct"
        }
        return tuple(
            self._finding(
                definition,
                by_node=by_node,
                relationships=relationships,
                direct_evidence_ids=direct_evidence_ids,
                risk_hints=system_map.risk_hints,
                build_id=build_id,
                scan_id=scan_id,
                environment_id=environment_id,
            )
            for definition in PROFILE_DEFINITIONS
        )

    @staticmethod
    def _finding(
        definition: ProfileDefinition,
        *,
        by_node: dict[str, ReferenceCapabilityAssessment],
        relationships: Mapping[str, Sequence[CanonicalEdge]],
        direct_evidence_ids: set[str],
        risk_hints: Sequence[CanonicalRiskHint],
        build_id: str,
        scan_id: str,
        environment_id: str,
    ) -> ProfileFinding:
        required = tuple(
            by_node[node] for node in definition.required_node_ids
        )
        relationship_evidence, relationship_direct = (
            ProfileFindingService._relationship_evidence(
                definition.required_relationship,
                relationships,
                direct_evidence_ids,
            )
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
                item
                for assessment in required
                for item in assessment.evidence_ids
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
            label=definition.label,
            status=status,
            activation=activation(required),
            primary_axis=definition.primary_axis,
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
            evidence_strength=evidence_strength(
                status,
                direct,
            ),
            uncertainty=uncertainty,
            related_component_ids=related_component_ids,
            related_unmapped_component_ids=(related_unmapped_component_ids),
            related_capability_candidate_component_ids=related_candidate_ids,
            related_risk_hint_ids=tuple(
                item.risk_id
                for item in risk_hints
                if item.target in navigation_targets
                or item.evidence_id in evidence_ids
            ),
            recommended_next_checks=(
                ()
                if status in {"detected", "not_detected"}
                else ("Review the missing deterministic capability signals.",)
            ),
            build_id=build_id,
            scan_id=scan_id,
            environment_id=environment_id,
        )

    @staticmethod
    def _relationship_evidence(
        relationship: str | None,
        relationships: Mapping[str, Sequence[CanonicalEdge]],
        direct_evidence_ids: set[str],
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
        direct = tuple(
            item for item in evidence if item in direct_evidence_ids
        )
        return evidence, direct
