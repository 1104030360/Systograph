"""Unit tests for WorkflowJsonProvider."""

from __future__ import annotations

import json
from pathlib import Path

from kai_mind.core.models.filesystem import (
    FileInventory,
    FileInventorySource,
    FileRecord,
)
from kai_mind.core.providers.workflow_json_provider import WorkflowJsonProvider


def _inventory(tmp_path: Path, relative: str, content: str) -> FileInventory:
    target = tmp_path / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(tmp_path.resolve()),
        files=[
            FileRecord(
                path=relative,
                size_bytes=len(content.encode("utf-8")),
            )
        ],
    )


def test_provider_emits_components_and_edges_from_validated_workflow_shape(
    tmp_path: Path,
) -> None:
    workflow = {
        "nodes": [
            {"id": "start", "data": {"label": "Start"}},
            {"id": "llm", "data": {"label": "LLM"}},
        ],
        "edges": [
            {"id": "e1", "source": "start", "target": "llm"},
        ],
    }
    inventory = _inventory(
        tmp_path,
        "flows/main.json",
        json.dumps(workflow),
    )

    result = WorkflowJsonProvider().collect(inventory)

    component_values = {
        fact.value
        for fact in result.facts
        if fact.kind == "workflow_component"
    }
    edge_values = {
        fact.value for fact in result.facts if fact.kind == "workflow_edge"
    }
    assert "component:workflow:flows/main.json:start" in component_values
    assert "component:workflow:flows/main.json:llm" in component_values
    assert "edge:workflow:flows/main.json:e1" in edge_values
    assert any(
        evidence.file == "flows/main.json"
        and evidence.path is not None
        and evidence.path.startswith("/nodes/")
        for evidence in result.evidence
    )


def test_provider_masks_secret_like_node_labels(tmp_path: Path) -> None:
    raw_label = "OPENAI_API_KEY=sk-live-secret-value"
    workflow = {
        "nodes": [
            {
                "id": "auth",
                "data": {"label": raw_label},
            },
            {"id": "llm", "data": {"label": "LLM"}},
        ],
        "edges": [
            {"id": "e1", "source": "auth", "target": "llm"},
        ],
    }
    inventory = _inventory(
        tmp_path,
        "flows/secret.json",
        json.dumps(workflow),
    )

    result = WorkflowJsonProvider().collect(inventory)

    label_values = [
        evidence.value
        for evidence in result.evidence
        if evidence.kind == "workflow_node"
    ]
    assert label_values
    assert raw_label not in label_values
    assert all(
        "sk-live-secret-value" not in (value or "") for value in label_values
    )


def test_provider_namespaces_ids_by_workflow_path_to_avoid_collisions(
    tmp_path: Path,
) -> None:
    workflow_a = {
        "nodes": [
            {"id": "start", "data": {"label": "A"}},
            {"id": "llm", "data": {"label": "LLM-A"}},
        ],
        "edges": [{"id": "e1", "source": "start", "target": "llm"}],
    }
    workflow_b = {
        "nodes": [
            {"id": "start", "data": {"label": "B"}},
            {"id": "llm", "data": {"label": "LLM-B"}},
        ],
        "edges": [{"id": "e1", "source": "start", "target": "llm"}],
    }
    (tmp_path / "flows").mkdir()
    (tmp_path / "flows" / "a.json").write_text(
        json.dumps(workflow_a),
        encoding="utf-8",
    )
    (tmp_path / "flows" / "b.json").write_text(
        json.dumps(workflow_b),
        encoding="utf-8",
    )
    inventory = FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(tmp_path.resolve()),
        files=[
            FileRecord(path="flows/a.json", size_bytes=100),
            FileRecord(path="flows/b.json", size_bytes=100),
        ],
    )

    result = WorkflowJsonProvider().collect(inventory)

    component_values = {
        fact.value
        for fact in result.facts
        if fact.kind == "workflow_component"
    }
    assert "component:workflow:flows/a.json:start" in component_values
    assert "component:workflow:flows/b.json:start" in component_values


def test_provider_rejects_duplicate_node_ids_within_one_workflow(
    tmp_path: Path,
) -> None:
    workflow = {
        "nodes": [
            {"id": "start", "data": {"label": "One"}},
            {"id": "start", "data": {"label": "Dup"}},
            {"id": "llm", "data": {"label": "LLM"}},
        ],
        "edges": [{"id": "e1", "source": "start", "target": "llm"}],
    }
    inventory = _inventory(
        tmp_path,
        "flows/dup.json",
        json.dumps(workflow),
    )

    result = WorkflowJsonProvider().collect(inventory)

    assert result.facts == []
    assert any(
        issue.rule_id == "workflow_json_duplicate_node_id"
        for issue in result.issues
    )


def test_provider_ignores_json_without_explicit_node_and_edge_shape(
    tmp_path: Path,
) -> None:
    inventory = _inventory(
        tmp_path,
        "config/settings.json",
        json.dumps({"platform": "langflow", "nodes": "not-a-list"}),
    )

    result = WorkflowJsonProvider().collect(inventory)

    assert result.facts == []
    assert result.evidence == []


def test_provider_does_not_infer_platform_from_blob_substring(
    tmp_path: Path,
) -> None:
    inventory = _inventory(
        tmp_path,
        "notes/readme-like.json",
        json.dumps({"description": "This mentions Langflow and Dify only"}),
    )

    result = WorkflowJsonProvider().collect(inventory)

    assert result.facts == []
