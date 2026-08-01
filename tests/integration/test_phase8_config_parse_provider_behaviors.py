from __future__ import annotations

from tests.helpers.fixtures import rag_project_fixture_path

from systograph.core.providers.config_parse_provider import ConfigParseProvider
from systograph.core.providers.filesystem_provider import FilesystemProvider
from systograph.core.services.secret_masking_service import (
    SecretMaskingService,
)


def test_openai_fixture_exposes_masked_config_signals() -> None:
    project_root = rag_project_fixture_path("openai_external_provider_rag")
    inventory = FilesystemProvider().build_inventory(project_root)

    result = ConfigParseProvider().collect(inventory)

    fact_by_path = {
        (fact.file, fact.path): fact.value for fact in result.facts
    }
    masker = SecretMaskingService()
    assert fact_by_path[
        (".env.example", "OPENAI_API_KEY")
    ] == masker.mask_value("sk-test-example", key="OPENAI_API_KEY")
    assert (
        fact_by_path[("config.yaml", "providers.llm.base_url")]
        == "https://api.openai.example/v1"
    )
    assert (
        fact_by_path[("config.yaml", "providers.embedding.model")]
        == "text-embedding-3-small"
    )
    assert not result.issues


def test_config_provider_only_reads_inventory_config_files() -> None:
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")
    inventory = FilesystemProvider().build_inventory(project_root)

    result = ConfigParseProvider().collect(inventory)

    files = {fact.file for fact in result.facts}
    assert files == {".env.example"}
    assert all(evidence.file == ".env.example" for evidence in result.evidence)
