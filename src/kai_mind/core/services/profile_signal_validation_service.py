from __future__ import annotations

import re

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.models.profile_signal import (
    ProfileFinding,
    ProfileInferenceResult,
    ReferenceCapabilityAssessment,
)
from kai_mind.core.services.capability_reference_map_loader import (
    CapabilityReferenceMapLoader,
)
from kai_mind.core.services.profile_rule_definitions import (
    MVP_CAPABILITY_PROFILE_IDS,
)

_ABSOLUTE_PATH = re.compile(r"(?:^|\s)(?:/|[A-Za-z]:[\\/])")
_SECRET_VALUE = re.compile(
    r"(?i)(?:api[_-]?key|password|secret|token)\s*[:=]\s*\S+"
)


class ProfileSignalValidationError(ValueError):
    pass


class ProfileSignalValidationService:
    def validate(
        self,
        result: ProfileInferenceResult,
        *,
        system_map: AiSystemMapV2,
    ) -> ProfileInferenceResult:
        catalog = CapabilityReferenceMapLoader().load()
        catalog_nodes = {node.id: node for node in catalog.nodes}
        assessments = {
            item.reference_node_id: item
            for item in result.reference_capability_assessments
        }
        if set(assessments) != set(catalog_nodes):
            raise ProfileSignalValidationError(
                "reference assessment ids do not match catalog"
            )
        for node_id, assessment in assessments.items():
            if assessment.plane_id != catalog_nodes[node_id].plane_id:
                raise ProfileSignalValidationError(
                    f"assessment plane mismatch for {node_id}"
                )
            if not catalog_nodes[node_id].activation_applicable and (
                assessment.activation != "not_applicable"
            ):
                raise ProfileSignalValidationError(
                    f"assessment activation mismatch for {node_id}"
                )

        if {item.profile_id for item in result.profiles} != set(
            MVP_CAPABILITY_PROFILE_IDS
        ):
            raise ProfileSignalValidationError(
                "profile ids do not match MVP registry"
            )

        evidence_ids = {item.evidence_id for item in system_map.evidence}
        component_ids = {item.component_id for item in system_map.components}
        unmapped_ids = {
            item.unmapped_id for item in system_map.unmapped_components
        }
        candidate_ids = {
            item.id for item in result.capability_candidate_components
        }
        risk_hint_ids = {item.risk_id for item in system_map.risk_hints}
        for item in result.reference_capability_assessments:
            self._validate_references(
                item,
                evidence_ids=evidence_ids,
                component_ids=component_ids,
                unmapped_ids=unmapped_ids,
                candidate_ids=candidate_ids,
                risk_hint_ids=risk_hint_ids,
            )
        for profile in result.profiles:
            self._validate_references(
                profile,
                evidence_ids=evidence_ids,
                component_ids=component_ids,
                unmapped_ids=unmapped_ids,
                candidate_ids=candidate_ids,
                risk_hint_ids=risk_hint_ids,
            )

        for candidate in result.capability_candidate_components:
            if set(candidate.evidence_ids) - evidence_ids:
                raise ProfileSignalValidationError(
                    "candidate references unknown evidence"
                )
            if candidate.source_file and self._is_absolute(
                candidate.source_file
            ):
                raise ProfileSignalValidationError(
                    "candidate contains an absolute path"
                )

        for profile in result.profiles:
            text_values = (
                profile.label,
                profile.description,
                profile.implementation_depth_reason,
                profile.uncertainty,
                *profile.recommended_next_checks,
            )
            self._validate_safe_text(text_values)
        return result

    @staticmethod
    def _validate_references(
        item: ReferenceCapabilityAssessment | ProfileFinding,
        *,
        evidence_ids: set[str],
        component_ids: set[str],
        unmapped_ids: set[str],
        candidate_ids: set[str],
        risk_hint_ids: set[str],
    ) -> None:
        unknown_evidence = set(item.evidence_ids) - evidence_ids
        if unknown_evidence:
            raise ProfileSignalValidationError(
                f"unknown evidence ids: {sorted(unknown_evidence)!r}"
            )
        if set(item.related_component_ids) - component_ids:
            raise ProfileSignalValidationError("unknown component reference")
        if set(item.related_unmapped_component_ids) - unmapped_ids:
            raise ProfileSignalValidationError(
                "unknown unmapped component reference"
            )
        if (
            set(item.related_capability_candidate_component_ids)
            - candidate_ids
        ):
            raise ProfileSignalValidationError(
                "unknown capability candidate reference"
            )
        if isinstance(item, ProfileFinding) and (
            set(item.related_risk_hint_ids) - risk_hint_ids
        ):
            raise ProfileSignalValidationError("unknown risk hint reference")

    @staticmethod
    def _validate_safe_text(values: tuple[str | None, ...]) -> None:
        for value in values:
            if not value:
                continue
            if ProfileSignalValidationService._is_absolute(value):
                raise ProfileSignalValidationError(
                    "profile text contains an absolute path"
                )
            if _SECRET_VALUE.search(value):
                raise ProfileSignalValidationError(
                    "profile text contains an unmasked secret"
                )

    @staticmethod
    def _is_absolute(value: str) -> bool:
        return bool(_ABSOLUTE_PATH.search(value))
