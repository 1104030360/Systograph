from __future__ import annotations

from pathlib import Path

import pytest
from tests.helpers.fixtures import (
    RAG_PROJECT_FIXTURE_NAMES,
    fixture_file_text,
    rag_project_fixture_path,
    rag_project_fixtures_root,
)

REQUIRED_FIXTURES = {
    "basic_qdrant_ollama_rag",
    "openai_external_provider_rag",
    "pgvector_openai_rag",
    "faiss_sentence_transformers_rag",
    "lancedb_or_chroma_local_rag",
    "malformed_config_rag",
    "missing_slots_rag",
    "custom_router_rag",
    "reranker_extension_rag",
    "graph_rag_extension_rag",
    "healthcare_rag_minimal",
}

SECRET_LIKE_VALUES = {
    "sk-live",
    "sk-proj-",
    "ghp_",
    "xoxb-",
    "AKIA",
    "-----BEGIN PRIVATE KEY-----",
}


def test_rag_project_fixture_names_are_complete() -> None:
    assert set(RAG_PROJECT_FIXTURE_NAMES) == REQUIRED_FIXTURES


def test_rag_project_fixture_root_is_project_relative() -> None:
    root = rag_project_fixtures_root()

    assert root.is_dir()
    assert root.name == "rag_projects"
    assert not root.is_absolute() or "tests/fixtures/rag_projects" in str(root)


@pytest.mark.parametrize("fixture_name", sorted(REQUIRED_FIXTURES))
def test_rag_project_fixture_has_required_files(fixture_name: str) -> None:
    fixture_path = rag_project_fixture_path(fixture_name)

    assert fixture_path.is_dir()
    assert (fixture_path / "README.md").is_file()
    assert any(
        (fixture_path / name).exists()
        for name in (
            "requirements.txt",
            "pyproject.toml",
            "package.json",
            "docker-compose.yml",
            "config.yaml",
            ".env.example",
        )
    )


@pytest.mark.parametrize("fixture_name", sorted(REQUIRED_FIXTURES))
def test_rag_project_fixture_readme_documents_reference_and_safety(
    fixture_name: str,
) -> None:
    readme = fixture_file_text(fixture_name, "README.md")

    assert "Reference sources" in readme
    assert "Scanner signals" in readme
    assert "Safety notes" in readme
    assert "does not require network" in readme
    assert "does not include real secrets" in readme


def test_fixtures_do_not_contain_real_secret_like_values() -> None:
    root = rag_project_fixtures_root()
    scanned_files = [
        path
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    ]

    assert scanned_files
    for path in scanned_files:
        text = path.read_text(encoding="utf-8")
        for secret in SECRET_LIKE_VALUES:
            assert secret not in text, f"{path} contains {secret}"


def test_fixtures_are_small_and_do_not_vendor_external_repos() -> None:
    root = rag_project_fixtures_root()
    files = [path for path in root.rglob("*") if path.is_file()]
    total_bytes = sum(path.stat().st_size for path in files)

    assert len(files) <= 80
    assert total_bytes <= 120_000
    for banned_dir in (".git", "node_modules", ".venv", "models", "data/raw"):
        assert not (root / banned_dir).exists()


def test_provider_variation_coverage_matrix() -> None:
    all_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in rag_project_fixtures_root().rglob("*")
        if path.is_file()
    )

    expected_signals = {
        "qdrant-client",
        "qdrant/qdrant",
        "pgvector",
        "faiss-cpu",
        "sentence-transformers",
        "lancedb",
        "ollama",
        "OPENAI_API_KEY=sk-test-example",
        "text-embedding-3-small",
        "custom_query_router",
        "cross-encoder",
        "graphrag",
        "neo4j",
        "knowledge_graph",
        "graph_retriever",
        "synthetic_patient_data",
        "no_diagnosis",
        "emergency_escalation",
        "cite_sources_required",
        "phi_policy",
    }
    missing = sorted(
        signal for signal in expected_signals if signal not in all_text
    )

    assert missing == []


def test_unknown_fixture_name_is_rejected() -> None:
    with pytest.raises(KeyError, match="Unknown RAG project fixture"):
        rag_project_fixture_path("missing_fixture")


def test_fixture_paths_can_be_copied_without_absolute_assumptions(
    tmp_path: Path,
) -> None:
    source = rag_project_fixture_path("basic_qdrant_ollama_rag")
    target = tmp_path / source.name
    target.mkdir()

    for child in source.iterdir():
        if child.is_file():
            (target / child.name).write_text(
                child.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

    assert (target / "README.md").is_file()
