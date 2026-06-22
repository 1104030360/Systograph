from __future__ import annotations

import json
from dataclasses import dataclass

import pytest
from tests.helpers.fixtures import rag_project_fixture_path

from kai_mind.core.models.scan import ProjectScanResult
from kai_mind.core.models.system_map import (
    Endpoint,
    Flow,
    RagSystemMap,
    RiskHint,
)
from kai_mind.core.models.template import RagTemplate
from kai_mind.core.services.component_detection_service import (
    ComponentDetectionResult,
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
from kai_mind.core.services.system_map_normalize_service import (
    RecommendedNextCheckService,
    SystemMapNormalizeService,
)
from kai_mind.core.services.system_map_validation_service import (
    SystemMapValidationService,
)


@dataclass(frozen=True)
class PipelineResult:
    project_name: str
    raw_scan: ProjectScanResult
    template: RagTemplate
    components: ComponentDetectionResult
    endpoints: list[Endpoint]
    flows: list[Flow]
    risk_hints: list[RiskHint]


def derive_pipeline(fixture_name: str) -> PipelineResult:
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
    return PipelineResult(
        project_name=fixture_name,
        raw_scan=raw_scan,
        template=template,
        components=components,
        endpoints=endpoints,
        flows=flows,
        risk_hints=risk_hints,
    )


def assemble_pipeline(result: PipelineResult) -> RagSystemMap:
    return SystemMapNormalizeService().assemble(
        project_name=result.project_name,
        raw_scan=result.raw_scan,
        template=result.template,
        components=result.components,
        endpoints=result.endpoints,
        flows=result.flows,
        risk_hints=result.risk_hints,
    )


def test_assemble_returns_unvalidated_draft() -> None:
    result = derive_pipeline("basic_qdrant_ollama_rag")
    dangling_risk = RiskHint(
        id="risk:dangling-evidence",
        type="external_provider",
        target="evidence:missing",
        target_type="evidence",
        evidence_id="evidence:missing",
        rule_id="external_provider_detected",
        rationale="Deliberately references missing evidence.",
    )

    system_map = SystemMapNormalizeService().assemble(
        project_name=result.project_name,
        raw_scan=result.raw_scan,
        template=result.template,
        components=result.components,
        endpoints=result.endpoints,
        flows=result.flows,
        risk_hints=[dangling_risk],
    )

    assert system_map.risk_hints[0].evidence_id == "evidence:missing"
    with pytest.raises(ValueError):
        SystemMapValidationService().validate(
            system_map.model_dump(mode="json")
        )


def test_normalize_basic_fixture_outputs_valid_canonical_map() -> None:
    result = derive_pipeline("basic_qdrant_ollama_rag")

    system_map = assemble_pipeline(result)
    serialized = system_map.model_dump(mode="json")
    validated = SystemMapValidationService().validate(serialized)

    assert validated.schema_version == "ai-system-map/v1"
    assert validated.classification.selected_template == "rag-core-v1"
    assert validated.project.name == "basic_qdrant_ollama_rag"
    assert validated.project.root_path == "<project_root>"
    assert validated.project.root_path_redacted == "<project_root>"
    assert validated.scan_summary is not None
    assert (
        validated.scan_summary.files_scanned == result.raw_scan.files_scanned
    )
    assert (
        validated.scan_summary.files_skipped == result.raw_scan.files_skipped
    )
    assert validated.scan_summary.risk_hints == len(result.risk_hints)
    assert serialized["detail_scans"] == []
    assert serialized["query_trace_events"] == []

    qdrant_endpoint = next(
        endpoint
        for endpoint in validated.endpoints
        if endpoint.slot == "vector_store"
    )
    assert qdrant_endpoint.component_instance_id is not None
    assert any(
        check.id.startswith("check:privacy_exposure:")
        and check.target_type == "component_instance"
        and check.target == qdrant_endpoint.component_instance_id
        for check in validated.recommended_next_checks
    )
    assert any(
        check.id.startswith("check:runtime_readiness:")
        and check.target_type == "component_instance"
        and check.target == qdrant_endpoint.component_instance_id
        for check in validated.recommended_next_checks
    )
    assert any(
        check.id.startswith("check:rag_knowledge_trust:")
        and check.target_type == "component_slot"
        and check.target == "data_sources"
        for check in validated.recommended_next_checks
    )


def test_normalize_openai_fixture_keeps_secrets_masked() -> None:
    result = derive_pipeline("openai_external_provider_rag")

    system_map = assemble_pipeline(result)
    serialized_text = json.dumps(system_map.model_dump(mode="json"))
    validated = SystemMapValidationService().validate(
        system_map.model_dump(mode="json")
    )

    assert "sk-test" not in serialized_text
    assert any(
        endpoint.endpoint_type == "external"
        for endpoint in validated.endpoints
    )
    assert any(
        check.id.startswith("check:privacy_exposure:")
        for check in validated.recommended_next_checks
    )


def test_normalize_uses_deterministic_ordering() -> None:
    result = derive_pipeline("basic_qdrant_ollama_rag")
    reversed_components = ComponentDetectionResult(
        components_by_slot=dict(
            reversed(result.components.components_by_slot.items())
        ),
        extensions=list(reversed(result.components.extensions)),
        unmapped_components=list(
            reversed(result.components.unmapped_components)
        ),
    )

    system_map = SystemMapNormalizeService().assemble(
        project_name=result.project_name,
        raw_scan=ProjectScanResult(
            facts=list(reversed(result.raw_scan.facts)),
            evidence=list(reversed(result.raw_scan.evidence)),
            issues=list(reversed(result.raw_scan.issues)),
            skipped_files=list(reversed(result.raw_scan.skipped_files)),
            warnings=list(reversed(result.raw_scan.warnings)),
            files_scanned=result.raw_scan.files_scanned,
            files_skipped=result.raw_scan.files_skipped,
        ),
        template=result.template,
        components=reversed_components,
        endpoints=list(reversed(result.endpoints)),
        flows=list(reversed(result.flows)),
        risk_hints=list(reversed(result.risk_hints)),
    )

    data = system_map.model_dump(mode="json")

    assert list(data["components_by_slot"]) == [
        slot.id for slot in result.template.slots
    ]
    assert [item["id"] for item in data["evidence"]] == sorted(
        item.id for item in result.raw_scan.evidence
    )
    assert [item["id"] for item in data["endpoints"]] == sorted(
        item.id for item in result.endpoints
    )
    assert [item["id"] for item in data["risk_hints"]] == sorted(
        item.id for item in result.risk_hints
    )
    assert [item["id"] for item in data["recommended_next_checks"]] == sorted(
        item["id"] for item in data["recommended_next_checks"]
    )


def test_recommended_next_checks_deduplicate_by_check_and_target() -> None:
    component_id = "component:vector_store:chroma"
    risk_hints = [
        RiskHint(
            id="risk:chroma-http",
            type="vector_store_endpoint",
            target=component_id,
            target_type="component_instance",
            evidence_id="evidence:chroma-http",
            rule_id="chroma_http_endpoint_detected",
            rationale="Chroma HTTP endpoint detected.",
        ),
        RiskHint(
            id="risk:chroma-persistence",
            type="local_persistence",
            target=component_id,
            target_type="component_instance",
            evidence_id="evidence:chroma-persistence",
            rule_id="chroma_local_persistence_detected",
            rationale="Chroma local persistence detected.",
        ),
    ]

    checks = RecommendedNextCheckService().derive(
        raw_scan=ProjectScanResult(),
        components=ComponentDetectionResult(
            components_by_slot={},
            extensions=[],
            unmapped_components=[],
        ),
        endpoints=[],
        risk_hints=risk_hints,
    )
    privacy_checks = [
        check
        for check in checks
        if check.id.startswith("check:privacy_exposure:")
    ]

    assert len(privacy_checks) == 1
    assert privacy_checks[0].target_type == "component_instance"
    assert privacy_checks[0].target == component_id


def test_privacy_endpoint_without_component_falls_back_to_endpoint() -> None:
    endpoint = Endpoint(
        id="endpoint:external:provider",
        value="https://api.example.test/v1",
        endpoint_type="external",
        slot="llm",
        component_instance_id=None,
        evidence_id="evidence:endpoint",
    )
    risk_hint = RiskHint(
        id="risk:external-provider",
        type="external_provider",
        target=endpoint.id,
        target_type="endpoint",
        evidence_id="evidence:endpoint",
        rule_id="external_provider_detected",
        rationale="External provider endpoint detected.",
    )

    checks = RecommendedNextCheckService().derive(
        raw_scan=ProjectScanResult(),
        components=ComponentDetectionResult(
            components_by_slot={},
            extensions=[],
            unmapped_components=[],
        ),
        endpoints=[endpoint],
        risk_hints=[risk_hint],
    )

    assert any(
        check.id.startswith("check:privacy_exposure:")
        and check.target_type == "endpoint"
        and check.target == endpoint.id
        for check in checks
    )
