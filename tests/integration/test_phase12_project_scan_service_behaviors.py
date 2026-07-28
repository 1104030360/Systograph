from __future__ import annotations

from tests.helpers.fixtures import rag_project_fixture_path

from systograph.core.services.project_scan_service import ProjectScanService


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
