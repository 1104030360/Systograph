from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.models.capability_candidate import (
    CapabilityCandidateComponent,
)
from kai_mind.core.models.profile_signal import (
    MappingCompleteness,
    MappingStatusCounts,
    ProfileInferenceResult,
    ReferenceCapabilityAssessment,
)
from kai_mind.core.services.profile_finding_service import (
    ProfileFindingService,
)
from kai_mind.core.services.profile_registry import (
    MVP_CAPABILITY_PROFILE_IDS,
)
from kai_mind.core.services.profile_signal_validation_service import (
    ProfileSignalValidationService,
)
from kai_mind.core.services.reference_capability_assessment_service import (
    ReferenceCapabilityAssessmentService,
)

__all__ = ["MVP_CAPABILITY_PROFILE_IDS", "ProfileInferenceService"]


class ProfileInferenceService:
    def __init__(
        self,
        *,
        assessment_service: ReferenceCapabilityAssessmentService | None = None,
        finding_service: ProfileFindingService | None = None,
        validation_service: ProfileSignalValidationService | None = None,
    ) -> None:
        self._assessment_service = (
            assessment_service or ReferenceCapabilityAssessmentService()
        )
        self._finding_service = finding_service or ProfileFindingService()
        self._validation_service = (
            validation_service or ProfileSignalValidationService()
        )

    def infer(
        self,
        system_map: AiSystemMapV2,
        *,
        build_id: str,
        scan_id: str,
        environment_id: str,
        capability_candidate_components: Sequence[
            CapabilityCandidateComponent
        ] = (),
    ) -> ProfileInferenceResult:
        candidates = tuple(capability_candidate_components)
        assessments = self._assessment_service.assess(
            system_map,
            build_id=build_id,
            scan_id=scan_id,
            environment_id=environment_id,
            capability_candidate_components=candidates,
        )
        profiles = self._finding_service.infer(
            assessments,
            system_map=system_map,
            build_id=build_id,
            scan_id=scan_id,
            environment_id=environment_id,
        )
        source_version = (
            system_map.source_schema_version or system_map.schema_version
        )
        result = ProfileInferenceResult(
            source_schema_version=source_version,
            build_id=build_id,
            scan_id=scan_id,
            environment_id=environment_id,
            generated_from_build_id=build_id,
            reference_capability_assessments=assessments,
            profiles=profiles,
            capability_candidate_components=candidates,
            mapping_completeness=self._mapping_completeness(assessments),
        )
        return self._validation_service.validate(result, system_map=system_map)

    @staticmethod
    def _mapping_completeness(
        assessments: Sequence[ReferenceCapabilityAssessment],
    ) -> MappingCompleteness:
        counts = Counter(item.status for item in assessments)
        status_counts = MappingStatusCounts(
            detected=counts["detected"],
            partial=counts["partial"],
            undetermined=counts["undetermined"],
            not_detected=counts["not_detected"],
            conflicted=counts["conflicted"],
        )
        numerator = (
            status_counts.detected
            + status_counts.not_detected
            + status_counts.partial * 0.5
        )
        return MappingCompleteness(
            numerator=numerator,
            value=numerator / 52,
            status_counts=status_counts,
        )
