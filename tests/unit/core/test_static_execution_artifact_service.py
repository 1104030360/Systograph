from __future__ import annotations

import json
from pathlib import Path

import pytest

from systograph.core.models.ai_system_map_v2 import (
    AiSystemMapV2,
    CanonicalComponent,
    CanonicalEdge,
    CanonicalEvidence,
    CanonicalEvidenceLocation,
    CanonicalLayer,
    CanonicalProject,
    CanonicalUnmappedComponent,
)
from systograph.core.models.mapping import (
    ManualMapping,
    ManualMappingDecision,
    ManualMappingType,
)
from systograph.core.services.build_manifest_artifacts import (
    validate_static_edge_parity,
)
from systograph.core.services.canonical_map_loader import CanonicalMapLoader
from systograph.core.services.static_execution_artifact_service import (
    StaticExecutionArtifactService,
)


def mapping(
    decision: ManualMappingDecision,
    evidence_id: str,
) -> ManualMapping:
    return ManualMapping(
        project_id="project:test",
        mapping_type=ManualMappingType.EXISTING_SLOT,
        decision=decision,
        evidence_ids=[evidence_id],
        mapping_id=f"mapping:{decision.value}",
        mapping_digest=f"sha256:{decision.value}",
        created_at="2026-07-11T00:00:00Z",
        updated_at="2026-07-11T00:00:00Z",
    )


def test_evidence_review_state_tracks_durable_mapping_decisions() -> None:
    fixture = Path(
        "tests/fixtures/ai_system_map/v2/non_grounded_llm_app.v2.json"
    )
    system_map = (
        CanonicalMapLoader()
        .load(json.loads(fixture.read_text(encoding="utf-8")))
        .normalized
    )
    evidence_ids = (
        "evidence:confirmed",
        "evidence:rejected",
        "evidence:not-applicable",
        "evidence:skipped",
        "evidence:pending",
        "evidence:not-required",
    )
    evidence = [
        CanonicalEvidence(
            evidence_id=evidence_id,
            artifact_type="source_code",
            evidence_kind="direct",
            location=CanonicalEvidenceLocation(path=f"src/{index}.py"),
        )
        for index, evidence_id in enumerate(evidence_ids)
    ]
    unmapped = [
        CanonicalUnmappedComponent(
            unmapped_id=f"unmapped:{index}",
            observed_kind="ambiguous_component",
            status="needs_confirmation",
            reason="User review is required.",
            evidence_ids=[evidence_id],
        )
        for index, evidence_id in enumerate(
            ("evidence:skipped", "evidence:pending")
        )
    ]
    system_map = system_map.model_copy(
        update={"evidence": evidence, "unmapped_components": unmapped}
    )

    artifacts = StaticExecutionArtifactService().build(
        system_map,
        manual_mappings=(
            mapping(ManualMappingDecision.CONFIRMED, "evidence:confirmed"),
            mapping(ManualMappingDecision.REJECTED, "evidence:rejected"),
            mapping(
                ManualMappingDecision.NOT_APPLICABLE,
                "evidence:not-applicable",
            ),
            mapping(ManualMappingDecision.SKIP_FOR_NOW, "evidence:skipped"),
        ),
    )

    states = {
        row.evidence_id: row.review_state
        for row in artifacts.evidence_table.rows
    }
    assert states == {
        "evidence:confirmed": "confirmed",
        "evidence:rejected": "rejected",
        "evidence:not-applicable": "not_required",
        "evidence:skipped": "needs_confirmation",
        "evidence:pending": "needs_confirmation",
        "evidence:not-required": "not_required",
    }


def test_static_artifacts_preserve_canonical_edge_status_and_reason() -> None:
    # Given: canonical edges contain observed and import-only relationships.
    component_ids = (
        "component:input:api",
        "component:retrieval:retriever",
        "component:generation:llm",
    )
    layers: tuple[CanonicalLayer, ...] = (
        "input_intent",
        "retrieval",
        "generation",
    )
    canonical_edges = (
        CanonicalEdge(
            edge_id="edge:api:retriever:invokes",
            source=component_ids[0],
            target=component_ids[1],
            relationship="invokes",
            status="observed",
        ),
        CanonicalEdge(
            edge_id="edge:retriever:llm:context_flow",
            source=component_ids[1],
            target=component_ids[2],
            relationship="context_flow",
            status="undetermined",
            undetermined_reason="import_only_no_call_site",
        ),
    )
    system_map = AiSystemMapV2(
        schema_version="ai-system-map/v2",
        system_type="ai_system",
        project=CanonicalProject(name="static-edge-contract"),
        scan_id="scan:static-edge-contract",
        build_id="build:static-edge-contract",
        components=[
            CanonicalComponent(
                component_id=component_id,
                display_name=component_id,
                canonical_type="component",
                layer=layer,
                status="detected",
                activation="enabled",
            )
            for component_id, layer in zip(
                component_ids,
                layers,
                strict=True,
            )
        ],
        edges=list(canonical_edges),
    )

    # When: static execution siblings are built from that canonical map.
    artifacts = StaticExecutionArtifactService().build(system_map)

    # Then: typed edge siblings preserve the canonical uncertainty contract.
    expected = tuple(
        (edge.edge_id, edge.status, edge.undetermined_reason)
        for edge in canonical_edges
    )
    assert (
        tuple(
            (edge.edge_id, edge.status, edge.undetermined_reason)
            for edge in artifacts.call_graph.edges
        )
        == expected
    )
    assert (
        tuple(
            (edge.edge_id, edge.status, edge.undetermined_reason)
            for edge in artifacts.dataflow_hints.hints
        )
        == expected
    )
    assert tuple(
        (
            edge.edge_id,
            edge.source,
            edge.target,
            edge.status,
            edge.undetermined_reason,
            edge.evidence_ids,
        )
        for edge in artifacts.execution_paths.paths
    ) == tuple(
        (
            edge.edge_id,
            edge.source,
            edge.target,
            edge.status,
            edge.undetermined_reason,
            tuple(edge.evidence_ids),
        )
        for edge in canonical_edges
    )
    assert all(
        artifact.runtime_verified is False
        for artifact in (
            artifacts.call_graph,
            artifacts.dataflow_hints,
            artifacts.execution_paths,
            artifacts.evidence_table,
        )
    )

    tampered_execution = artifacts.execution_paths.model_copy(
        update={
            "paths": (
                artifacts.execution_paths.paths[0].model_copy(
                    update={"relationship": "tampered"}
                ),
                *artifacts.execution_paths.paths[1:],
            )
        }
    )
    with pytest.raises(
        ValueError,
        match="static artifact edge mismatch: execution_paths.json",
    ):
        validate_static_edge_parity(
            system_map,
            call_graph=artifacts.call_graph,
            dataflow_hints=artifacts.dataflow_hints,
            execution_paths=tampered_execution,
        )
