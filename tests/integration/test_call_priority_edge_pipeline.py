from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, cast

import pytest
from tests.helpers.fixtures import rag_project_fixture_path
from typer.testing import CliRunner

from systograph.cli import main as cli_main
from systograph.core.models.map_build import MapBuildRequest
from systograph.core.models.scan import OutputRun
from systograph.core.models.ua_parity import UaParityInvocationCounters
from systograph.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from systograph.core.services.map_build_service import MapBuildService


def _run_cli_map(
    *,
    project_root: Path,
    output: Path,
    state_dir: Path,
) -> str:
    result = CliRunner().invoke(
        cli_main.app,
        [
            "map",
            str(project_root),
            "--output",
            str(output),
            "--state-dir",
            str(state_dir),
        ],
        env={"SYSTOGRAPH_TEMPLATE_FLOW_EDGES": "off"},
    )
    assert result.exit_code == 0, result.stdout
    return next(
        line.removeprefix("scan_id=")
        for line in result.stdout.splitlines()
        if line.startswith("scan_id=")
    )


def _json(path: Path) -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        json.loads(path.read_text(encoding="utf-8")),
    )


@pytest.mark.parametrize(
    "fixture_name",
    ["basic_qdrant_ollama_rag", "pgvector_openai_rag"],
)
def test_real_fixture_edges_drive_all_static_siblings(
    fixture_name: str,
    tmp_path: Path,
) -> None:
    # Given
    output = tmp_path / "output"
    state_dir = tmp_path / "state"

    # When
    scan_id = _run_cli_map(
        project_root=rag_project_fixture_path(fixture_name),
        output=output,
        state_dir=state_dir,
    )

    # Then
    system_map = _json(output / "ai_system_map.json")
    call_graph = _json(output / "call_graph.json")
    dataflow = _json(output / "dataflow_hints.json")
    execution_paths = _json(output / "execution_paths.json")
    edges = system_map["edges"]
    # Documented baseline adjustment (2026-08-13): each fixture's only
    # candidate call edge is a mirror pair — retriever and vector_store
    # are anchored on the same evidence line — so ambiguous attribution
    # is discarded instead of catalog-directed. Real edges return once
    # the bridge separates evidence roles (owner decision); until then
    # the sibling artifacts must stay consistent and invent nothing.
    assert edges == []
    expected_artifact_edges = [
        {
            "edge_id": edge["edge_id"],
            "source": edge["source"],
            "target": edge["target"],
            "relationship": edge["relationship"],
            "status": edge["status"],
            "undetermined_reason": edge["undetermined_reason"],
            "evidence_ids": edge["evidence_ids"],
        }
        for edge in edges
    ]
    assert call_graph["edges"] == expected_artifact_edges
    assert dataflow["hints"] == expected_artifact_edges
    assert execution_paths["schema_version"] == "execution-paths/v2"
    assert execution_paths["paths"] == expected_artifact_edges
    assert call_graph["runtime_verified"] is False
    assert dataflow["runtime_verified"] is False
    assert execution_paths["runtime_verified"] is False
    repository = LocalJsonStateProvider(state_dir)
    project = repository.list_projects()[0]
    snapshot = repository.get_snapshot(project.project_id, scan_id)
    assert snapshot is not None
    assert snapshot.ua_parity_report is not None
    assert snapshot.ua_parity_report.invocations == UaParityInvocationCounters(
        filesystem_scan=1,
        ua_sidecar=1,
        parity_providers=1,
    )


def test_apply_reuses_snapshot_edges_and_parity_counters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")
    output = tmp_path / "b1"
    state_dir = tmp_path / "state"
    scan_id = _run_cli_map(
        project_root=project_root,
        output=output,
        state_dir=state_dir,
    )
    repository = LocalJsonStateProvider(state_dir)
    project = repository.list_projects()[0]
    snapshot = repository.get_snapshot(project.project_id, scan_id)
    assert snapshot is not None
    first_edges = _json(output / "ai_system_map.json")["edges"]
    monkeypatch.setenv("SYSTOGRAPH_TEMPLATE_FLOW_EDGES", "off")

    # When
    applied = MapBuildService().build_from_snapshot(
        snapshot,
        request=MapBuildRequest(project_path=project_root),
        output_run=OutputRun(root_dir=tmp_path / "b2"),
        build_id="build:b2",
        based_on_build_id="build:b1",
        build_reason="apply_confirmations",
        mapping_ids=("mapping:fixture",),
    )

    # Then
    assert applied.ai_system_map is not None
    assert [
        edge.model_dump(mode="json") for edge in applied.ai_system_map.edges
    ] == first_edges
    assert snapshot.ua_parity_report is not None
    assert snapshot.ua_parity_report.invocations == UaParityInvocationCounters(
        filesystem_scan=1,
        ua_sidecar=1,
        parity_providers=1,
    )


def test_rescan_replaces_stale_call_edges(tmp_path: Path) -> None:
    # Given
    project_root = tmp_path / "project"
    shutil.copytree(
        rag_project_fixture_path("basic_qdrant_ollama_rag"),
        project_root,
    )
    state_dir = tmp_path / "state"
    first_scan_id = _run_cli_map(
        project_root=project_root,
        output=tmp_path / "b1",
        state_dir=state_dir,
    )
    retriever = project_root / "src" / "retriever.py"
    retriever.write_text(
        retriever.read_text(encoding="utf-8").replace(
            "QdrantClient",
            "UnrelatedClient",
        ),
        encoding="utf-8",
    )

    # When
    second_scan_id = _run_cli_map(
        project_root=project_root,
        output=tmp_path / "b2",
        state_dir=state_dir,
    )

    # Then: rescan freshness shows up in the replaced scan evidence
    # (the fixture's mirror-pair edge is discarded as ambiguous, so
    # edges stay empty on both builds — documented baseline 2026-08-13).
    assert second_scan_id != first_scan_id
    first_map = _json(tmp_path / "b1" / "ai_system_map.json")
    second_map = _json(tmp_path / "b2" / "ai_system_map.json")
    assert first_map["edges"] == []
    assert second_map["edges"] == []
    stale_rule = ("code_pattern_vector_store_qdrant", "src/retriever.py")
    first_rules = {
        (item["rule_id"], item["location"]["path"])
        for item in first_map["evidence"]
    }
    second_rules = {
        (item["rule_id"], item["location"]["path"])
        for item in second_map["evidence"]
    }
    assert stale_rule in first_rules
    assert stale_rule not in second_rules
