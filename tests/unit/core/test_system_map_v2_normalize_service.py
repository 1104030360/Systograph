from __future__ import annotations

from pathlib import Path

from systograph.core.models.recommended_next_check import RecommendedNextCheck
from systograph.core.models.scan import ProjectScanResult
from systograph.core.services.component_detection_service import (
    ComponentDetectionResult,
)
from systograph.core.services.system_map_v2_normalize_service import (
    SystemMapV2NormalizeService,
)


def _assemble(
    checks: list[RecommendedNextCheck],
) -> list[RecommendedNextCheck]:
    system_map = SystemMapV2NormalizeService().assemble(
        project_name="fixture-project",
        project_id=None,
        project_root=Path("/fixture-project"),
        raw_scan=ProjectScanResult(),
        components=ComponentDetectionResult(
            components_by_slot={},
            unmapped_components=[],
        ),
        endpoints=[],
        flows=[],
        risk_hints=[],
        recommended_next_checks=checks,
        no_snippets=False,
    )
    return [
        RecommendedNextCheck(**check.model_dump())
        for check in system_map.recommended_next_checks
    ]


def test_assemble_copies_recommended_next_checks_field_for_field() -> None:
    """Given a derived check with every field populated,
    When the v2 normalize service assembles the canonical map,
    Then the canonical check carries the same five field values.
    """
    check = RecommendedNextCheck(
        id="check:privacy_exposure:component-instance:component-vector-store",
        target_type="component_instance",
        target="component:vector_store:pgvector",
        reason="External network exposure was observed.",
        action="Confirm whether this endpoint should be reachable.",
    )

    assembled = _assemble([check])

    assert assembled == [check]


def test_assemble_preserves_recommended_next_check_order() -> None:
    """Given checks in the order RecommendedNextCheckService emitted them,
    When the v2 normalize service assembles the canonical map,
    Then the canonical list keeps that order instead of re-sorting.
    """
    checks = [
        RecommendedNextCheck(
            id=f"check:runtime_readiness:component-slot:{slot}",
            target_type="component_slot",
            target=slot,
            reason="Runtime slot is missing.",
            action="Confirm the runtime wiring.",
        )
        for slot in ("retriever", "llm", "app_api_or_orchestrator")
    ]

    assembled = _assemble(checks)

    assert [item.id for item in assembled] == [item.id for item in checks]
