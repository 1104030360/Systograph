from __future__ import annotations

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.models.profile_signal import (
    ProfileFinding,
    ProfileInferenceResult,
    ReferenceCapabilityAssessment,
)
from kai_mind.core.models.readiness_report import (
    CapabilityReadinessSummary,
    GroundingReadinessSummary,
    ReadinessDimension,
    ReadinessFinding,
    ReadinessReport,
)


class ReadinessReportService:
    def build(
        self,
        *,
        system_map: AiSystemMapV2,
        profile_result: ProfileInferenceResult,
    ) -> ReadinessReport:
        assessments = {
            item.reference_node_id: item
            for item in profile_result.reference_capability_assessments
        }
        grounding_profile = next(
            item
            for item in profile_result.profiles
            if item.profile_id == "rag-grounding"
        )
        grounding = GroundingReadinessSummary(
            applicability=(
                "applicable"
                if grounding_profile.status in {"detected", "partial"}
                else "undetermined"
            ),
            status=grounding_profile.status,
            dimensions=(
                self._dimension("retrieval", assessments["dense_retriever"]),
                self._dimension("generation", assessments["llm_answerer"]),
                self._dimension(
                    "traceability", assessments["citation_mapper"]
                ),
            ),
            evidence_ids=grounding_profile.evidence_ids,
            reason=grounding_profile.uncertainty,
        )
        capabilities = tuple(
            CapabilityReadinessSummary(
                profile_id=item.profile_id,
                status=item.status,
                activation=item.activation,
                evidence_ids=item.evidence_ids,
            )
            for item in profile_result.profiles
        )
        findings = tuple(
            self._profile_finding(item) for item in profile_result.profiles
        ) + (self._source_traceability(assessments["citation_mapper"]),)
        next_checks = tuple(
            dict.fromkeys(
                check
                for item in profile_result.profiles
                for check in item.recommended_next_checks
            )
        )
        return ReadinessReport(
            source_schema_version=profile_result.source_schema_version,
            build_id=profile_result.build_id,
            scan_id=profile_result.scan_id,
            environment_id=profile_result.environment_id,
            generated_from_build_id=profile_result.build_id,
            mapping_completeness=profile_result.mapping_completeness,
            grounding=grounding,
            capability_summaries=capabilities,
            findings=findings,
            recommended_next_checks=next_checks,
            limitations=(
                "Static analysis does not prove runtime behavior.",
                "Undetermined does not mean the capability is absent.",
            ),
            primary_map_type=self._primary_map_type(profile_result),
        )

    @staticmethod
    def _dimension(
        dimension_id: str,
        assessment: ReferenceCapabilityAssessment,
    ) -> ReadinessDimension:
        return ReadinessDimension(
            dimension_id=dimension_id,
            status=assessment.status,
            evidence_ids=assessment.evidence_ids,
            reason=(
                None
                if assessment.status == "detected"
                else "Deterministic evidence is incomplete."
            ),
        )

    @staticmethod
    def _profile_finding(profile: ProfileFinding) -> ReadinessFinding:
        profile_id = profile.profile_id
        status = profile.status
        evidence_ids = profile.evidence_ids
        uncertainty = profile.uncertainty
        next_checks = profile.recommended_next_checks
        return ReadinessFinding(
            finding_id=f"readiness:profile:{profile_id}",
            category="capability_readiness",
            status=status,
            title=f"Capability readiness: {profile_id}",
            reason=uncertainty or "Deterministic capability gate passed.",
            evidence_ids=evidence_ids,
            recommended_next_checks=next_checks,
        )

    @staticmethod
    def _source_traceability(
        assessment: ReferenceCapabilityAssessment,
    ) -> ReadinessFinding:
        return ReadinessFinding(
            finding_id="readiness:source-traceability",
            category="source_traceability",
            status=assessment.status,
            title="Source traceability",
            reason=(
                "Citation mapping evidence is present."
                if assessment.status == "detected"
                else "Citation mapping coverage is not proven."
            ),
            evidence_ids=assessment.evidence_ids,
            recommended_next_checks=(
                ()
                if assessment.status == "detected"
                else ("Verify answer-to-source citation mapping.",)
            ),
        )

    @staticmethod
    def _primary_map_type(result: ProfileInferenceResult) -> str:
        detected = {
            item.profile_id
            for item in result.profiles
            if item.status == "detected"
        }
        if "agentic-control" in detected:
            return "agentic_ai_system"
        if "rag-grounding" in detected:
            return "grounded_rag_system"
        return "ai_system"
