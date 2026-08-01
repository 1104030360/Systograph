"""Integration tests for ai-system-map/v2 compatibility gate (00A)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from systograph.core.models.ai_system_map_v2 import (
    AiSystemMapV2,
    CanonicalCandidateFact,
    CanonicalComponent,
    CanonicalEdge,
    CanonicalEndpoint,
    CanonicalEvidence,
    CanonicalProject,
    CanonicalRecommendedNextCheck,
    CanonicalRiskHint,
    CanonicalUnmappedComponent,
)
from systograph.core.models.readiness_report import ReadinessFinding
from systograph.core.services.canonical_map_loader import CanonicalMapLoader
from systograph.core.services.profile_inference_service import (
    ProfileInferenceService,
)
from systograph.core.services.readiness_report_service import (
    ReadinessReportService,
)
from systograph.core.services.system_map_v1_to_v2_adapter import (
    SystemMapV1ToV2Adapter,
)
from systograph.core.services.system_map_v2_validation_service import (
    SystemMapV2ValidationService,
)
from systograph.core.services.system_map_validation_service import (
    SystemMapValidationService,
)

V1_RICH = Path(
    "tests/fixtures/ai_system_map/valid_rich_frontend_sample.v1.json"
)
V2_DIR = Path("tests/fixtures/ai_system_map/v2")
V1_SEMANTIC = Path(
    "tests/fixtures/ai_system_map/grounded_rag_equivalent.v1.json"
)
V2_SEMANTIC = V2_DIR / "grounded_rag_equivalent.v2.json"
REPORT_PATH = Path(
    "docs/work/Timmy/schedule/report/"
    "2026-07-10-ai-system-map-v2-compatibility-gate.md"
)


@dataclass(frozen=True, slots=True)
class CanonicalFactSignature:
    project: CanonicalProject
    components: tuple[CanonicalComponent, ...]
    edges: tuple[CanonicalEdge, ...]
    evidence: tuple[CanonicalEvidence, ...]
    endpoints: tuple[CanonicalEndpoint, ...]
    risk_hints: tuple[CanonicalRiskHint, ...]
    unmapped_components: tuple[CanonicalUnmappedComponent, ...]
    candidate_facts: tuple[CanonicalCandidateFact, ...]
    recommended_next_checks: tuple[CanonicalRecommendedNextCheck, ...]
    readiness_findings: tuple[ReadinessFinding, ...]


def test_v1_fixture_adapter_preserves_resolvable_evidence_locations() -> None:
    payload = json.loads(V1_RICH.read_text(encoding="utf-8"))
    system_map = SystemMapValidationService().validate(payload)
    canonical = SystemMapV1ToV2Adapter().adapt_to_canonical(system_map)

    SystemMapV2ValidationService().validate(canonical.model_dump(mode="json"))
    source_ids = {item.id for item in system_map.evidence}
    adapted_ids = {item.evidence_id for item in canonical.evidence}
    assert adapted_ids == source_ids
    for item in canonical.evidence:
        if item.location.path is not None:
            assert "\\" not in item.location.path
            assert not item.location.path.startswith("/")
            assert ":" not in item.location.path.split("/")[0]


def test_dual_read_loader_keeps_v1_and_v2_clients_compatible() -> None:
    v1_payload = json.loads(V1_RICH.read_text(encoding="utf-8"))
    v2_payload = json.loads(
        (V2_DIR / "grounded_rag.v2.json").read_text(encoding="utf-8")
    )
    loader = CanonicalMapLoader()

    v1_result = loader.load(v1_payload)
    v2_result = loader.load(v2_payload)

    assert v1_result.active_schema_version == "ai-system-map/v1"
    assert v2_result.active_schema_version == "ai-system-map/v2"
    assert isinstance(v1_result.normalized, AiSystemMapV2)
    assert isinstance(v2_result.normalized, AiSystemMapV2)
    # Active artifact contract for v1 clients remains the original payload.
    assert v1_payload["schema_version"] == "ai-system-map/v1"
    assert "components_by_slot" in v1_payload


def test_fact_equivalent_v1_and_native_v2_have_identical_readiness() -> None:
    # Given
    loader = CanonicalMapLoader()
    v1_map = loader.load(
        json.loads(V1_SEMANTIC.read_text(encoding="utf-8"))
    ).normalized
    v2_map = loader.load(
        json.loads(V2_SEMANTIC.read_text(encoding="utf-8"))
    ).normalized

    # When
    signatures = tuple(
        _readiness_findings(system_map) for system_map in (v1_map, v2_map)
    )

    # Then
    assert signatures[0] == signatures[1]


def test_paired_v1_and_native_v2_have_identical_canonical_facts() -> None:
    # Given
    loader = CanonicalMapLoader()
    v1_map = loader.load(
        json.loads(V1_SEMANTIC.read_text(encoding="utf-8"))
    ).normalized
    v2_map = loader.load(
        json.loads(V2_SEMANTIC.read_text(encoding="utf-8"))
    ).normalized

    # When
    signatures = tuple(
        _canonical_fact_signature(system_map)
        for system_map in (v1_map, v2_map)
    )

    # Then
    assert signatures[0] == signatures[1]


@pytest.mark.parametrize(
    "fixture_name",
    [
        "non_grounded_llm_app.v2.json",
        "tool_using_agent.v2.json",
        "workflow_graph.v2.json",
    ],
)
def test_non_rag_v2_fixtures_are_not_forced_into_rag_slots(
    fixture_name: str,
) -> None:
    payload = json.loads((V2_DIR / fixture_name).read_text(encoding="utf-8"))
    system_map = SystemMapV2ValidationService().validate(payload)

    dumped = system_map.model_dump(mode="json")
    assert "components_by_slot" not in dumped
    assert system_map.system_type == "ai_system"


def test_windows_and_posix_project_relative_paths_round_trip_as_posix() -> (
    None
):
    payload = json.loads(
        (V2_DIR / "grounded_rag.v2.json").read_text(encoding="utf-8")
    )
    payload["evidence"][0]["location"]["path"] = "src/api/chat.py"
    system_map = SystemMapV2ValidationService().validate(payload)
    assert system_map.evidence[0].location.path == "src/api/chat.py"

    with pytest.raises(Exception, match="project-relative|POSIX|path"):
        bad = json.loads(json.dumps(payload))
        bad["evidence"][0]["location"]["path"] = r"C:\repo\src\api\chat.py"
        SystemMapV2ValidationService().validate(bad)


def test_compatibility_gate_report_exists_with_consumer_matrix() -> None:
    assert REPORT_PATH.is_file()
    text = REPORT_PATH.read_text(encoding="utf-8")
    assert "等价" in text or "等價" in text or "equivalent" in text.lower()
    assert "Plan 13" in text
    assert "active output" in text.lower() or "active output" in text


def _canonical_fact_signature(
    system_map: AiSystemMapV2,
) -> CanonicalFactSignature:
    return CanonicalFactSignature(
        project=system_map.project,
        components=tuple(
            sorted(
                system_map.components,
                key=lambda item: item.component_id,
            )
        ),
        edges=tuple(sorted(system_map.edges, key=lambda item: item.edge_id)),
        evidence=tuple(
            sorted(
                system_map.evidence,
                key=lambda item: item.evidence_id,
            )
        ),
        endpoints=tuple(
            sorted(
                system_map.endpoints,
                key=lambda item: item.endpoint_id,
            )
        ),
        risk_hints=tuple(
            sorted(
                system_map.risk_hints,
                key=lambda item: item.risk_id,
            )
        ),
        unmapped_components=tuple(
            sorted(
                system_map.unmapped_components,
                key=lambda item: item.unmapped_id,
            )
        ),
        candidate_facts=tuple(
            sorted(
                system_map.candidate_facts,
                key=lambda item: item.candidate_fact_id,
            )
        ),
        # Order is part of the contract: checks are service-sorted at build
        # time and the adapter must copy them without re-sorting.
        recommended_next_checks=tuple(system_map.recommended_next_checks),
        readiness_findings=_readiness_findings(system_map),
    )


def _readiness_findings(
    system_map: AiSystemMapV2,
) -> tuple[ReadinessFinding, ...]:
    profiles = ProfileInferenceService().infer(
        system_map,
        build_id="build:semantic-equivalence",
        scan_id="scan:semantic-equivalence",
        environment_id="environment:default-static",
    )
    return (
        ReadinessReportService()
        .build(
            system_map=system_map,
            profile_result=profiles,
        )
        .findings
    )
