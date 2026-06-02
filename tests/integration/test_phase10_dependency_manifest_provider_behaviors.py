from __future__ import annotations

from tests.helpers.fixtures import rag_project_fixture_path

from kai_mind.core.providers.dependency_manifest_provider import (
    DependencyManifestProvider,
)
from kai_mind.core.providers.filesystem_provider import FilesystemProvider


def test_basic_local_rag_fixture_exposes_dependency_manifest_signals() -> None:
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")
    inventory = FilesystemProvider().build_inventory(project_root)

    result = DependencyManifestProvider().collect(inventory)

    fact_by_value = {fact.value: fact for fact in result.facts}
    assert (
        fact_by_value["qdrant-client"].rule_id
        == "dependency_vector_store_client_qdrant"
    )
    assert (
        fact_by_value["ollama"].rule_id
        == "dependency_local_llm_provider_ollama"
    )
    assert all(fact.file == "requirements.txt" for fact in result.facts)
    assert not result.issues


def test_openai_fixture_exposes_external_llm_and_framework_dependencies() -> (
    None
):
    project_root = rag_project_fixture_path("openai_external_provider_rag")
    inventory = FilesystemProvider().build_inventory(project_root)

    result = DependencyManifestProvider().collect(inventory)

    fact_by_value = {fact.value: fact for fact in result.facts}
    assert (
        fact_by_value["openai"].rule_id
        == "dependency_external_llm_embedding_openai"
    )
    assert (
        fact_by_value["llama-index-core"].rule_id
        == "dependency_rag_framework_llama_index"
    )
    assert not result.issues


def test_malformed_dependency_manifest_fixture_returns_parse_issue() -> None:
    project_root = rag_project_fixture_path("malformed_config_rag")
    inventory = FilesystemProvider().build_inventory(project_root)

    result = DependencyManifestProvider().collect(inventory)

    assert result.facts == []
    assert len(result.issues) == 1
    assert result.issues[0].file == "package.json"
    assert result.issues[0].scan_stage == "dependency_manifest_parse"
    assert result.evidence[0].kind == "parse_error"
