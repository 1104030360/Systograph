from __future__ import annotations

from pathlib import Path

import pytest
from tests.helpers.fixtures import rag_project_fixture_path

from systograph.core.models.filesystem import FileInventory
from systograph.core.models.scan import ProviderScanResult
from systograph.core.models.structural_fact import (
    CallStructuralFact,
    ImportStructuralFact,
)
from systograph.core.providers.ast_construction_provider import (
    AstConstructionProvider,
)
from systograph.core.services.project_scan_service import ProjectScanService


class KeepOnlyAppInventoryPolicy:
    def apply(
        self,
        *,
        project_root: Path,
        inventory: FileInventory,
    ) -> FileInventory:
        del project_root
        return inventory.model_copy(
            update={
                "files": [
                    record
                    for record in inventory.files
                    if record.path == "app.py"
                ]
            }
        )


def test_basic_local_rag_fixture_aggregates_raw_scan_facts() -> None:
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")

    result = ProjectScanService().scan(project_root)

    rule_ids = {fact.rule_id for fact in result.facts}
    assert "docker_qdrant_image_detected" in rule_ids
    assert "docker_ollama_image_detected" in rule_ids
    assert "dependency_vector_store_client_qdrant" in rule_ids
    assert "dependency_local_llm_provider_ollama" in rule_ids
    assert "code_pattern_route_fastapi" in rule_ids
    assert "code_pattern_vector_store_qdrant" in rule_ids
    assert result.files_scanned > 0
    assert all(fact.rule_id or fact.provider for fact in result.facts)
    assert all(
        evidence.file is not None or evidence.path is not None
        for evidence in result.evidence
    )
    assert not result.issues


def test_malformed_fixture_keeps_partial_output_and_parse_issues() -> None:
    project_root = rag_project_fixture_path("malformed_config_rag")

    result = ProjectScanService().scan(project_root)

    issue_stages = {issue.scan_stage for issue in result.issues}
    assert "docker_compose_parse" in issue_stages
    assert "dependency_manifest_parse" in issue_stages
    assert result.evidence
    assert all(evidence.kind == "parse_error" for evidence in result.evidence)
    assert result.files_scanned > 0


def test_active_scan_runs_ast_provider_once_on_final_inventory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a policy-approved file and an excluded file contain the same call.
    project_root = tmp_path / "project"
    project_root.mkdir()
    source = (
        "from qdrant_client import QdrantClient\nclient = QdrantClient()\n"
    )
    (project_root / "app.py").write_text(source, encoding="utf-8")
    (project_root / "excluded.py").write_text(source, encoding="utf-8")
    seen_inventories: list[tuple[str, ...]] = []
    original_collect = AstConstructionProvider.collect

    def collect_once(
        provider: AstConstructionProvider,
        inventory: FileInventory,
    ) -> ProviderScanResult:
        seen_inventories.append(
            tuple(record.path for record in inventory.files)
        )
        return original_collect(provider, inventory)

    monkeypatch.setattr(AstConstructionProvider, "collect", collect_once)

    # When: the active project-scan path applies its inventory policy.
    result = ProjectScanService().scan(
        project_root,
        inventory_policy=KeepOnlyAppInventoryPolicy(),
    )

    # Then: AST construction consumes that final inventory exactly once.
    assert seen_inventories == [("app.py",)]
    ast_facts = [
        fact
        for fact in result.facts
        if fact.rule_id == "code_pattern_vector_store_qdrant"
        and fact.value == "qdrant_client.QdrantClient"
    ]
    assert [(fact.file, fact.path) for fact in ast_facts] == [
        ("app.py", "line[2]")
    ]
    call_facts = [
        fact
        for fact in result.structural_facts
        if isinstance(fact, CallStructuralFact)
    ]
    import_facts = [
        fact
        for fact in result.structural_facts
        if isinstance(fact, ImportStructuralFact)
    ]
    assert [(fact.span.file, fact.span.line_start) for fact in call_facts] == [
        ("app.py", 2)
    ]
    assert [
        (fact.span.file, fact.span.line_start) for fact in import_facts
    ] == [("app.py", 1)]
    assert [fact.stable_id for fact in result.structural_facts] == sorted(
        {fact.stable_id for fact in result.structural_facts}
    )
