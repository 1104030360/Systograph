from __future__ import annotations

from kai_mind.core.models.scan import ProjectScanResult
from kai_mind.core.models.system_map import Endpoint, RiskHint
from kai_mind.core.services.component_detection_service import (
    ComponentDetectionResult,
)
from kai_mind.core.services.recommended_next_check_service import (
    RecommendedNextCheckService,
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
