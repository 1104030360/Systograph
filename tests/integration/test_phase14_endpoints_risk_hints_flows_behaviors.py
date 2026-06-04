from __future__ import annotations

from typing import Any

from tests.helpers.fixtures import rag_project_fixture_path

from kai_mind.core.services.component_detection_service import (
    ComponentDetectionService,
)
from kai_mind.core.services.endpoint_detection_service import (
    EndpointDetectionService,
)
from kai_mind.core.services.flow_derivation_service import (
    FlowDerivationService,
)
from kai_mind.core.services.project_scan_service import ProjectScanService
from kai_mind.core.services.rag_template_service import RagTemplateService
from kai_mind.core.services.risk_hint_service import RiskHintService
from kai_mind.core.services.system_map_validation_service import (
    SystemMapValidationService,
)


def derive_phase14_map(fixture_name: str) -> dict[str, Any]:
    fixture_path = rag_project_fixture_path(fixture_name)
    raw_scan = ProjectScanService().scan(fixture_path)
    template = RagTemplateService.load("rag-core-v1")
    components = ComponentDetectionService().detect(
        template=template,
        facts=raw_scan.facts,
        evidence=raw_scan.evidence,
    )
    endpoints = EndpointDetectionService().detect(
        facts=raw_scan.facts,
        evidence=raw_scan.evidence,
        components=components,
    )
    risk_hints = RiskHintService().derive(
        facts=raw_scan.facts,
        evidence=raw_scan.evidence,
        issues=raw_scan.issues,
        components=components,
        endpoints=endpoints,
    )
    flows = FlowDerivationService().derive(
        template=template,
        components=components,
    )

    return {
        "schema_version": "ai-system-map/v1",
        "system_type": "rag",
        "classification": {
            "mode": "user_selected_or_default",
            "selected_template": "rag-core-v1",
        },
        "project": {
            "name": fixture_name,
            "root_path": "<project_root>",
            "root_path_redacted": "<project_root>",
            "path_mode": "redacted",
            "system_map_schema_version": "ai-system-map/v1",
        },
        "reference_architecture": {
            "id": template.id,
            "version": template.version,
            "slots": [slot.id for slot in template.slots],
            "flows": [flow.id for flow in template.flows],
        },
        "scan_depth": "system",
        "components_by_slot": {
            key: value.model_dump(mode="json")
            for key, value in components.components_by_slot.items()
        },
        "evidence": [
            item.model_dump(mode="json") for item in raw_scan.evidence
        ],
        "endpoints": [item.model_dump(mode="json") for item in endpoints],
        "flows": [item.model_dump(mode="json") for item in flows],
        "extensions": [
            item.model_dump(mode="json") for item in components.extensions
        ],
        "unmapped_components": [
            item.model_dump(mode="json")
            for item in components.unmapped_components
        ],
        "detail_scans": [],
        "risk_hints": [item.model_dump(mode="json") for item in risk_hints],
        "recommended_next_checks": [],
        "query_trace_events": [],
    }


def test_basic_qdrant_fixture_derives_valid_endpoint_risk_and_flow() -> None:
    system_map = derive_phase14_map("basic_qdrant_ollama_rag")

    validated = SystemMapValidationService().validate(system_map)

    assert any(
        endpoint.value == "http://localhost:6333"
        and endpoint.slot == "vector_store"
        for endpoint in validated.endpoints
    )
    assert any(
        risk.rule_id == "docker_published_port_exposure"
        for risk in validated.risk_hints
    )
    assert any(
        edge.from_slot == "retriever" and edge.to_slot == "vector_store"
        for flow in validated.flows
        for edge in flow.edges
    )


def test_openai_fixture_derives_external_endpoint_no_secret_leak() -> None:
    system_map = derive_phase14_map("openai_external_provider_rag")

    validated = SystemMapValidationService().validate(system_map)

    openai_endpoints = [
        endpoint
        for endpoint in validated.endpoints
        if endpoint.endpoint_type == "external"
    ]
    assert openai_endpoints
    assert all("sk-" not in endpoint.value for endpoint in openai_endpoints)
    assert any(
        risk.rule_id == "external_provider_detected"
        for risk in validated.risk_hints
    )
