from __future__ import annotations

from tests.helpers.fixtures import rag_project_fixture_path

from systograph.core.providers.docker_compose_provider import (
    DockerComposeProvider,
)
from systograph.core.providers.filesystem_provider import FilesystemProvider


def test_basic_local_rag_fixture_exposes_docker_compose_signals() -> None:
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")
    inventory = FilesystemProvider().build_inventory(project_root)

    result = DockerComposeProvider().collect(inventory)

    fact_by_path = {
        (fact.file, fact.path): fact.value for fact in result.facts
    }
    evidence_by_path = {
        (evidence.file, evidence.path): evidence
        for evidence in result.evidence
    }
    assert (
        fact_by_path[("docker-compose.yml", "services.qdrant.image")]
        == "qdrant/qdrant:v1.12.1"
    )
    assert (
        fact_by_path[("docker-compose.yml", "services.ollama.image")]
        == "ollama/ollama:0.5.1"
    )
    assert (
        fact_by_path[("docker-compose.yml", "services.qdrant.ports[0]")]
        == "6333:6333"
    )
    assert (
        evidence_by_path[("docker-compose.yml", "services.qdrant.image")].kind
        == "docker_service"
    )
    assert (
        evidence_by_path[
            ("docker-compose.yml", "services.qdrant.ports[0]")
        ].kind
        == "published_port"
    )
    assert not result.issues


def test_malformed_compose_fixture_returns_parse_issue() -> None:
    project_root = rag_project_fixture_path("malformed_config_rag")
    inventory = FilesystemProvider().build_inventory(project_root)

    result = DockerComposeProvider().collect(inventory)

    assert result.facts == []
    assert len(result.issues) == 1
    assert result.issues[0].file == "docker-compose.yml"
    assert result.issues[0].scan_stage == "docker_compose_parse"
    assert result.evidence[0].kind == "parse_error"


def test_docker_provider_only_reads_inventory_compose_files() -> None:
    project_root = rag_project_fixture_path("openai_external_provider_rag")
    inventory = FilesystemProvider().build_inventory(project_root)

    result = DockerComposeProvider().collect(inventory)

    assert result.facts == []
    assert result.evidence == []
    assert result.issues == []
