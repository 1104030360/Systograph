"""Assemble ai-system-map/v1 draft documents from scanner outputs.

Operator-rollback-only v1 writer. Not reachable from the normal v2 build
path; Plan 15 removes it. The active writer is
SystemMapV2MaterializationService + SystemMapV2NormalizeService. This
service is reached only through SystemMapMaterializationService, which
MapBuildService constructs lazily when the operator selects the legacy v1
canonical output version.
"""

from __future__ import annotations

from collections.abc import Sequence

from kai_mind.core.models.scan import ProjectScanResult
from kai_mind.core.models.system_map import (
    Classification,
    ComponentSlot,
    DetailScanResult,
    Endpoint,
    Evidence,
    Flow,
    Project,
    QueryTraceEvent,
    RagSystemMap,
    ReferenceArchitecture,
    RiskHint,
    ScanSummary,
    UnmappedComponent,
)
from kai_mind.core.models.template import RagTemplate
from kai_mind.core.services.component_detection_service import (
    ComponentDetectionResult,
)
from kai_mind.core.services.recommended_next_check_service import (
    RecommendedNextCheckService,
)


class SystemMapNormalizeService:
    """Assemble upstream scanner outputs into a RagSystemMap draft."""

    def __init__(
        self,
        *,
        recommended_next_check_service: (
            RecommendedNextCheckService | None
        ) = None,
    ) -> None:
        self._recommended_next_check_service = (
            recommended_next_check_service or RecommendedNextCheckService()
        )

    def assemble(
        self,
        *,
        project_name: str,
        raw_scan: ProjectScanResult,
        template: RagTemplate,
        components: ComponentDetectionResult,
        endpoints: Sequence[Endpoint],
        flows: Sequence[Flow],
        risk_hints: Sequence[RiskHint],
        detail_scans: Sequence[DetailScanResult] | None = None,
        query_trace_events: Sequence[QueryTraceEvent] | None = None,
    ) -> RagSystemMap:
        recommended_next_checks = self._recommended_next_check_service.derive(
            raw_scan=raw_scan,
            components=components,
            endpoints=endpoints,
            risk_hints=risk_hints,
        )

        system_map = RagSystemMap(
            schema_version="ai-system-map/v1",
            system_type="rag",
            classification=Classification(
                mode="user_selected_or_default",
                selected_template="rag-core-v1",
            ),
            project=Project(
                name=project_name,
                root_path="<project_root>",
                root_path_redacted="<project_root>",
                path_mode="redacted",
                system_map_schema_version="ai-system-map/v1",
            ),
            reference_architecture=ReferenceArchitecture(
                id="rag-core-v1",
                version=template.version,
                slots=[slot.id for slot in template.slots],
                flows=[flow.id for flow in template.flows],
            ),
            scan_depth="system",
            scan_summary=self._scan_summary(
                raw_scan=raw_scan,
                components=components,
                risk_hints=risk_hints,
            ),
            components_by_slot=self._ordered_components_by_slot(
                template,
                components,
            ),
            evidence=self._sort_evidence(raw_scan.evidence),
            endpoints=sorted(endpoints, key=lambda item: item.id),
            flows=sorted(flows, key=lambda item: item.id),
            extensions=[],
            unmapped_components=self._sort_unmapped(
                components.unmapped_components
            ),
            detail_scans=sorted(
                detail_scans or [],
                key=lambda item: item.id,
            ),
            risk_hints=sorted(risk_hints, key=lambda item: item.id),
            recommended_next_checks=recommended_next_checks,
            query_trace_events=sorted(
                query_trace_events or [],
                key=lambda item: item.id,
            ),
        )

        return system_map

    def _ordered_components_by_slot(
        self,
        template: RagTemplate,
        components: ComponentDetectionResult,
    ) -> dict[str, ComponentSlot]:
        ordered: dict[str, ComponentSlot] = {}
        for template_slot in template.slots:
            slot = components.components_by_slot[template_slot.id]
            ordered[template_slot.id] = ComponentSlot(
                slot=slot.slot,
                required_for_rag=slot.required_for_rag,
                status=slot.status,
                instances=sorted(slot.instances, key=lambda item: item.id),
            )

        extras = sorted(
            set(components.components_by_slot) - set(ordered),
        )
        for slot_id in extras:
            slot = components.components_by_slot[slot_id]
            ordered[slot_id] = ComponentSlot(
                slot=slot.slot,
                required_for_rag=slot.required_for_rag,
                status=slot.status,
                instances=sorted(slot.instances, key=lambda item: item.id),
            )
        return ordered

    def _scan_summary(
        self,
        *,
        raw_scan: ProjectScanResult,
        components: ComponentDetectionResult,
        risk_hints: Sequence[RiskHint],
    ) -> ScanSummary:
        slots = components.components_by_slot.values()
        return ScanSummary(
            status="partial" if raw_scan.issues or raw_scan.warnings else "ok",
            files_scanned=raw_scan.files_scanned,
            files_skipped=raw_scan.files_skipped,
            detected_slots=sum(
                1 for slot in slots if slot.status == "detected"
            ),
            missing_slots=sum(
                1
                for slot in components.components_by_slot.values()
                if slot.status == "missing"
            ),
            not_configured_slots=sum(
                1
                for slot in components.components_by_slot.values()
                if slot.status == "not_configured"
            ),
            unmapped_components=len(components.unmapped_components),
            risk_hints=len(risk_hints),
            secret_masking_applied=self._has_masked_value(raw_scan.evidence),
        )

    def _has_masked_value(self, evidence: Sequence[Evidence]) -> bool:
        return any(
            evidence_item.value is not None
            and (
                "[MASKED]" in evidence_item.value
                or "..." in evidence_item.value
            )
            for evidence_item in evidence
        )

    def _sort_evidence(self, evidence: Sequence[Evidence]) -> list[Evidence]:
        return sorted(evidence, key=lambda item: item.id)

    def _sort_unmapped(
        self,
        unmapped: Sequence[UnmappedComponent],
    ) -> list[UnmappedComponent]:
        return sorted(unmapped, key=lambda item: item.id)
