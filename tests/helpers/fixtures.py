from __future__ import annotations

from pathlib import Path

RAG_PROJECT_FIXTURE_NAMES = (
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
    "secret_masking_regression_rag",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def rag_project_fixtures_root() -> Path:
    return repo_root() / "tests" / "fixtures" / "rag_projects"


def rag_project_fixture_path(name: str) -> Path:
    if name not in RAG_PROJECT_FIXTURE_NAMES:
        raise KeyError(f"Unknown RAG project fixture: {name}")
    return rag_project_fixtures_root() / name


def fixture_file_text(fixture_name: str, relative_path: str) -> str:
    return (rag_project_fixture_path(fixture_name) / relative_path).read_text(
        encoding="utf-8"
    )
