from __future__ import annotations

from tests.helpers.fixtures import rag_project_fixture_path

from systograph.core.providers.code_pattern_provider import CodePatternProvider
from systograph.core.providers.filesystem_provider import FilesystemProvider


def test_basic_local_rag_fixture_exposes_route_and_qdrant_code_signals() -> (
    None
):
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")
    inventory = FilesystemProvider().build_inventory(project_root)

    result = CodePatternProvider().collect(inventory)

    fact_rules = {fact.rule_id for fact in result.facts}
    assert "code_pattern_route_fastapi" in fact_rules
    assert "code_pattern_vector_store_qdrant" in fact_rules
    assert {
        fact.file
        for fact in result.facts
        if fact.rule_id == "code_pattern_route_fastapi"
    } == {"src/app.py"}
    assert {
        fact.file
        for fact in result.facts
        if fact.rule_id == "code_pattern_vector_store_qdrant"
    } >= {"src/retriever.py"}
    assert not result.issues


def test_openai_fixture_exposes_route_and_openai_embedding_call_signals() -> (
    None
):
    project_root = rag_project_fixture_path("openai_external_provider_rag")
    inventory = FilesystemProvider().build_inventory(project_root)

    result = CodePatternProvider().collect(inventory)

    fact_rules = {fact.rule_id for fact in result.facts}
    assert "code_pattern_route_fastapi" in fact_rules
    assert "code_pattern_embedding_openai_sdk_create" in fact_rules
    assert all(evidence.snippet for evidence in result.evidence)
    assert not result.issues
