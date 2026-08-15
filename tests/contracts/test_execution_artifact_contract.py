from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from systograph.core.models.execution_artifact import (
    ArtifactEdge,
    CallGraphArtifact,
    DataflowHintsArtifact,
    EvidenceTableArtifact,
    ExecutionPathsArtifact,
    ScopedExecutionArtifact,
)
from systograph.core.services.canonical_map_loader import CanonicalMapLoader
from systograph.core.services.static_execution_artifact_service import (
    StaticExecutionArtifactService,
)

SCOPED_ARTIFACT_TYPES: tuple[type[ScopedExecutionArtifact], ...] = (
    CallGraphArtifact,
    DataflowHintsArtifact,
    ExecutionPathsArtifact,
    EvidenceTableArtifact,
)


def test_service_serializes_static_metadata_for_every_p0_artifact() -> None:
    given_fixture = Path(
        "tests/fixtures/ai_system_map/v2/non_grounded_llm_app.v2.json"
    )
    given_system_map = (
        CanonicalMapLoader()
        .load(json.loads(given_fixture.read_text(encoding="utf-8")))
        .normalized
    )

    when_artifacts = StaticExecutionArtifactService().build(given_system_map)
    when_payloads = tuple(
        artifact.model_dump(mode="json")
        for artifact in (
            when_artifacts.call_graph,
            when_artifacts.dataflow_hints,
            when_artifacts.execution_paths,
            when_artifacts.evidence_table,
        )
    )

    then_metadata = tuple(
        (payload["trace_kind"], payload["runtime_verified"])
        for payload in when_payloads
    )
    assert then_metadata == (("static_inferred", False),) * 4


@pytest.mark.parametrize("artifact_type", SCOPED_ARTIFACT_TYPES)
def test_scoped_p0_artifacts_reject_runtime_trace_kind(
    artifact_type: type[ScopedExecutionArtifact],
) -> None:
    given_payload = {
        "build_id": "build:test",
        "scan_id": "scan:test",
        "environment_id": "environment:test",
        "generated_from_build_id": "build:test",
        "trace_kind": "runtime_observed",
    }

    with pytest.raises(ValidationError):
        artifact_type.model_validate(given_payload)


@pytest.mark.parametrize("artifact_type", SCOPED_ARTIFACT_TYPES)
def test_scoped_p0_artifacts_reject_runtime_verified_true(
    artifact_type: type[ScopedExecutionArtifact],
) -> None:
    given_payload = {
        "build_id": "build:test",
        "scan_id": "scan:test",
        "environment_id": "environment:test",
        "generated_from_build_id": "build:test",
        "runtime_verified": True,
    }

    with pytest.raises(ValidationError):
        artifact_type.model_validate(given_payload)


def test_undetermined_artifact_edge_requires_reason() -> None:
    with pytest.raises(ValidationError):
        ArtifactEdge(
            edge_id="edge:test",
            source="component:a",
            target="component:b",
            relationship="calls",
            status="undetermined",
            evidence_ids=("evidence:test",),
        )


@pytest.mark.parametrize("artifact_type", SCOPED_ARTIFACT_TYPES)
def test_scoped_p0_artifacts_reject_missing_trace_metadata(
    artifact_type: type[ScopedExecutionArtifact],
) -> None:
    given_payload = {
        "build_id": "build:test",
        "scan_id": "scan:test",
        "environment_id": "environment:test",
        "generated_from_build_id": "build:test",
    }

    with pytest.raises(ValidationError):
        artifact_type.model_validate(given_payload)
