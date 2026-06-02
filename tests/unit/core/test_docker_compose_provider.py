from __future__ import annotations

from pathlib import Path

from kai_mind.core.models.filesystem import (
    FileInventory,
    FileInventorySource,
    FileRecord,
)
from kai_mind.core.providers.docker_compose_provider import (
    DockerComposeProvider,
)
from kai_mind.core.services.secret_masking_service import SecretMaskingService


def build_inventory(project_root: Path, *paths: str) -> FileInventory:
    return FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(project_root),
        files=[
            FileRecord(
                path=path,
                size_bytes=(project_root / path).stat().st_size,
            )
            for path in paths
        ],
    )


def test_collect_reads_compose_files_from_inventory_only(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "docker-compose.yml").write_text(
        "services:\n  qdrant:\n    image: qdrant/qdrant:v1.12.1\n",
        encoding="utf-8",
    )
    (project_root / "compose.yaml").write_text(
        "services:\n  ollama:\n    image: ollama/ollama:0.5.1\n",
        encoding="utf-8",
    )
    (project_root / "config.yaml").write_text(
        "services:\n  ignored:\n    image: redis:7\n",
        encoding="utf-8",
    )
    inventory = build_inventory(
        project_root,
        "docker-compose.yml",
        "compose.yaml",
        "config.yaml",
    )

    result = DockerComposeProvider().collect(inventory)

    fact_files = {fact.file for fact in result.facts}
    assert fact_files == {"docker-compose.yml", "compose.yaml"}
    assert not result.issues


def test_collect_emits_service_image_and_published_port_evidence(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "docker-compose.yml").write_text(
        "\n".join(
            [
                "services:",
                "  qdrant:",
                "    image: qdrant/qdrant:v1.12.1",
                "    ports:",
                '      - "6333:6333"',
                "  ollama:",
                "    image: ollama/ollama:0.5.1",
                "    ports:",
                '      - "127.0.0.1:11434:11434"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "docker-compose.yml")

    result = DockerComposeProvider().collect(inventory)

    evidence_by_path = {
        evidence.path: evidence for evidence in result.evidence
    }
    assert evidence_by_path["services.qdrant.image"].kind == "docker_service"
    assert (
        evidence_by_path["services.qdrant.image"].rule_id
        == "docker_qdrant_image_detected"
    )
    assert evidence_by_path["services.ollama.image"].kind == "docker_service"
    assert (
        evidence_by_path["services.ollama.image"].rule_id
        == "docker_ollama_image_detected"
    )
    assert (
        evidence_by_path["services.qdrant.ports[0]"].kind == "published_port"
    )
    assert evidence_by_path["services.qdrant.ports[0]"].value == "6333:6333"


def test_collect_normalizes_long_syntax_ports(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "compose.yaml").write_text(
        "\n".join(
            [
                "services:",
                "  postgres:",
                "    image: pgvector/pgvector:pg16",
                "    ports:",
                "      - target: 5432",
                '        published: "5432"',
                "        host_ip: 127.0.0.1",
                "        protocol: tcp",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "compose.yaml")

    result = DockerComposeProvider().collect(inventory)

    fact_by_path = {fact.path: fact for fact in result.facts}
    assert fact_by_path["services.postgres.ports[0]"].kind == "published_port"
    assert (
        fact_by_path["services.postgres.ports[0]"].value
        == "host_ip=127.0.0.1,published=5432,target=5432,protocol=tcp"
    )


def test_collect_masks_environment_map_and_list_values(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "docker-compose.yml").write_text(
        "\n".join(
            [
                "services:",
                "  api:",
                "    image: kai-mind/api:test",
                "    environment:",
                "      OPENAI_API_KEY: sk-test-example",
                "      QDRANT_URL: http://localhost:6333",
                "  worker:",
                "    image: kai-mind/worker:test",
                "    environment:",
                "      - PASSWORD=correct horse battery staple",
                "      - EMPTY_RUNTIME_KEY",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "docker-compose.yml")

    result = DockerComposeProvider().collect(inventory)

    fact_by_path = {fact.path: fact for fact in result.facts}
    masker = SecretMaskingService()
    assert fact_by_path[
        "services.api.environment.OPENAI_API_KEY"
    ].value == masker.mask_value("sk-test-example", key="OPENAI_API_KEY")
    assert (
        fact_by_path["services.api.environment.QDRANT_URL"].value
        == "http://localhost:6333"
    )
    assert fact_by_path[
        "services.worker.environment.PASSWORD"
    ].value == masker.mask_value(
        "correct horse battery staple",
        key="PASSWORD",
    )
    assert (
        fact_by_path["services.worker.environment.EMPTY_RUNTIME_KEY"].value
        is None
    )
    leaked_values = {
        value
        for value in [fact.value for fact in result.facts]
        + [evidence.value for evidence in result.evidence]
        if value is not None
    }
    assert "sk-test-example" not in leaked_values
    assert "correct horse battery staple" not in leaked_values


def test_collect_emits_env_file_volume_and_depends_on_facts(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "docker-compose.yml").write_text(
        "\n".join(
            [
                "services:",
                "  api:",
                "    image: kai-mind/api:test",
                "    env_file:",
                "      - .env",
                "      - path: ./worker.env",
                "    volumes:",
                "      - ./data:/app/data:ro",
                "      - type: volume",
                "        source: model-cache",
                "        target: /models",
                "    depends_on:",
                "      qdrant:",
                "        condition: service_started",
                "      redis:",
                "        condition: service_healthy",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "docker-compose.yml")

    result = DockerComposeProvider().collect(inventory)

    fact_by_path = {fact.path: fact for fact in result.facts}
    assert fact_by_path["services.api.env_file[0]"].value == ".env"
    assert fact_by_path["services.api.env_file[1]"].value == "./worker.env"
    assert (
        fact_by_path["services.api.volumes[0]"].value == "./data:/app/data:ro"
    )
    assert (
        fact_by_path["services.api.volumes[1]"].value
        == "source=model-cache,target=/models,type=volume"
    )
    assert fact_by_path["services.api.depends_on[0]"].value == "qdrant"
    assert fact_by_path["services.api.depends_on[1]"].value == "redis"


def test_collect_reports_malformed_compose_without_stopping_other_files(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "docker-compose.yml").write_text(
        "services:\n  broken\n    image: ollama/ollama:0.5.1\n",
        encoding="utf-8",
    )
    (project_root / "compose.yaml").write_text(
        "services:\n  qdrant:\n    image: qdrant/qdrant:v1.12.1\n",
        encoding="utf-8",
    )
    inventory = build_inventory(
        project_root,
        "docker-compose.yml",
        "compose.yaml",
    )

    result = DockerComposeProvider().collect(inventory)

    fact_by_path = {fact.path: fact for fact in result.facts}
    assert fact_by_path["services.qdrant.image"].value == (
        "qdrant/qdrant:v1.12.1"
    )
    assert len(result.issues) == 1
    assert result.issues[0].provider == "docker_compose"
    assert result.issues[0].scan_stage == "docker_compose_parse"
    assert result.issues[0].file == "docker-compose.yml"
    parse_error_evidence = [
        evidence
        for evidence in result.evidence
        if evidence.kind == "parse_error"
    ]
    assert len(parse_error_evidence) == 1
    assert parse_error_evidence[0].rule_id == "docker_compose_parse_error"
