"""Assemble ai-system-map/v1 draft documents from scanner outputs.

00A compatibility note: this service remains the active v1 writer. Normalized
ai-system-map/v2 views are produced by CanonicalMapLoader + adapter after the
v1 map is validated. Do not silent-cutover this writer to v2 before Plan 13.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from systograph.core.models.scan import ProjectScanResult
from systograph.core.models.system_map import (
    Classification,
    ComponentSlot,
    DetailScanResult,
    Endpoint,
    Evidence,
    Flow,
    Project,
    QueryTraceEvent,
    RagSystemMap,
    RecommendedNextCheck,
    ReferenceArchitecture,
    RiskHint,
    ScanSummary,
    UnmappedComponent,
)
from systograph.core.models.template import RagTemplate
from systograph.core.services.component_detection_service import (
    ComponentDetectionResult,
)
from systograph.core.services.rule_catalog_loader import (
    RecommendedNextCheckRuleMetadata,
    RuleCatalogLoader,
)

# RecommendedNextCheck triggers; reason/action text
# is in recommended_next_check_rules.toml.
# Privacy: add risk_hint_rules.toml first, then rule_id/type here.

RUNTIME_CRITICAL_SLOTS = {  # -> runtime_readiness when missing
    "app_api_or_orchestrator",
    "retriever",
    "vector_store",
    "llm",
}

RAG_TRUST_CRITICAL_SLOTS = {  # -> rag_knowledge_trust when missing
    "data_sources",
    "document_loader",
    "chunking",
    "embedding_model",
    "retriever",
    "prompt_builder",
    "llm",
    "citation_or_response_composer",
    "guardrails",
}

PRIVACY_RISK_RULE_IDS = {  # risk_hint rule_id -> privacy_exposure
    "docker_published_port_exposure",
    "external_provider_detected",
    "secret_like_config_key_detected",
    "chroma_http_endpoint_detected",
    "chroma_local_persistence_detected",
    "chroma_server_published_port",
}

PRIVACY_RISK_TYPES = {  # risk_hint type -> privacy_exposure
    "network_exposure",
    "external_provider",
    "secret_config",
    "local_persistence",
    "vector_store_endpoint",
    "vector_store_network_exposure",
}


@dataclass(frozen=True)
class RecommendedCheckTarget:
    """Concrete target for one recommended next check."""

    target_type: str
    target: str


class RecommendedNextCheckService:
    """Derive deterministic next checks from normalized scanner signals."""

    def __init__(
        self,
        *,
        rule_catalog_path: Path | str | None = None,
    ) -> None:
        rules = RuleCatalogLoader().load_recommended_next_check_rules(
            rule_catalog_path
        )
        self._metadata_by_id = {rule.id: rule for rule in rules}

    def derive(
        self,
        *,
        raw_scan: ProjectScanResult,
        components: ComponentDetectionResult,
        endpoints: Sequence[Endpoint],
        risk_hints: Sequence[RiskHint],
    ) -> list[RecommendedNextCheck]:
        checks: dict[tuple[str, str, str], RecommendedNextCheck] = {}

        for target in self._runtime_targets(raw_scan, components, endpoints):
            self._add_check(checks, "runtime_readiness", target)

        for target in self._privacy_targets(risk_hints, endpoints):
            self._add_check(checks, "privacy_exposure", target)

        for target in self._rag_trust_targets(components):
            self._add_check(checks, "rag_knowledge_trust", target)

        return sorted(checks.values(), key=lambda item: item.id)

    def _add_check(
        self,
        checks: dict[tuple[str, str, str], RecommendedNextCheck],
        check_id: str,
        target: RecommendedCheckTarget,
    ) -> None:
        key = (check_id, target.target_type, target.target)
        checks.setdefault(key, self._check(check_id, target))

    def _check(
        self,
        check_id: str,
        target: RecommendedCheckTarget,
    ) -> RecommendedNextCheck:
        metadata = self._metadata(check_id)
        return RecommendedNextCheck(
            id=(
                f"check:{metadata.id}:"
                f"{_slug(target.target_type)}:{_slug(target.target)}"
            ),
            target_type=target.target_type,
            target=target.target,
            reason=metadata.reason,
            action=metadata.action,
        )

    def _metadata(self, check_id: str) -> RecommendedNextCheckRuleMetadata:
        metadata = self._metadata_by_id.get(check_id)
        if metadata is None:
            raise ValueError(
                f"Missing recommended next check metadata: {check_id}"
            )
        return metadata

    def _runtime_targets(
        self,
        raw_scan: ProjectScanResult,
        components: ComponentDetectionResult,
        endpoints: Sequence[Endpoint],
    ) -> list[RecommendedCheckTarget]:
        targets: set[RecommendedCheckTarget] = set()
        for endpoint in endpoints:
            targets.add(self._endpoint_target(endpoint))

        for slot in components.components_by_slot.values():
            if (
                slot.slot in RUNTIME_CRITICAL_SLOTS
                and slot.status == "missing"
            ):
                targets.add(
                    RecommendedCheckTarget(
                        target_type="component_slot",
                        target=slot.slot,
                    )
                )

        has_docker_signal = any(
            (fact.rule_id or "").startswith("docker_")
            for fact in raw_scan.facts
        )
        if has_docker_signal and not targets:
            targets.add(self._default_target("runtime_readiness"))
        return _sorted_targets(targets)

    def _privacy_targets(
        self,
        risk_hints: Sequence[RiskHint],
        endpoints: Sequence[Endpoint],
    ) -> list[RecommendedCheckTarget]:
        endpoint_by_id = {endpoint.id: endpoint for endpoint in endpoints}
        targets: set[RecommendedCheckTarget] = set()
        for risk in risk_hints:
            if not self._is_privacy_risk(risk):
                continue
            targets.add(self._risk_target(risk, endpoint_by_id))
        return _sorted_targets(targets)

    def _rag_trust_targets(
        self,
        components: ComponentDetectionResult,
    ) -> list[RecommendedCheckTarget]:
        targets = {
            RecommendedCheckTarget(
                target_type="component_slot",
                target=slot.slot,
            )
            for slot in components.components_by_slot.values()
            if slot.slot in RAG_TRUST_CRITICAL_SLOTS
            and slot.status == "missing"
        }
        return _sorted_targets(targets)

    def _risk_target(
        self,
        risk: RiskHint,
        endpoint_by_id: dict[str, Endpoint],
    ) -> RecommendedCheckTarget:
        if risk.target_type == "component_instance":
            return RecommendedCheckTarget(
                target_type="component_instance",
                target=risk.target,
            )
        if risk.target_type == "component_slot":
            return RecommendedCheckTarget(
                target_type="component_slot",
                target=risk.target,
            )
        if risk.target_type == "endpoint":
            endpoint = endpoint_by_id.get(risk.target)
            if endpoint is not None:
                return self._endpoint_target(endpoint)
            return RecommendedCheckTarget(
                target_type="endpoint",
                target=risk.target,
            )
        return self._default_target("privacy_exposure")

    def _endpoint_target(self, endpoint: Endpoint) -> RecommendedCheckTarget:
        if endpoint.component_instance_id:
            return RecommendedCheckTarget(
                target_type="component_instance",
                target=endpoint.component_instance_id,
            )
        return RecommendedCheckTarget(
            target_type="endpoint",
            target=endpoint.id,
        )

    def _default_target(self, check_id: str) -> RecommendedCheckTarget:
        metadata = self._metadata(check_id)
        return RecommendedCheckTarget(
            target_type=metadata.default_target_type,
            target="system",
        )

    def _is_privacy_risk(self, risk: RiskHint) -> bool:
        return (
            risk.rule_id in PRIVACY_RISK_RULE_IDS
            or risk.type in PRIVACY_RISK_TYPES
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


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower() or "unknown"


def _sorted_targets(
    targets: set[RecommendedCheckTarget],
) -> list[RecommendedCheckTarget]:
    return sorted(targets, key=lambda item: (item.target_type, item.target))
