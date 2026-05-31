from __future__ import annotations

from tests.helpers.fixtures import (
    fixture_file_text,
    rag_project_fixture_path,
)


def test_canonical_local_rag_exposes_core_provider_signals() -> None:
    fixture_path = rag_project_fixture_path("basic_qdrant_ollama_rag")

    compose = fixture_file_text(
        "basic_qdrant_ollama_rag", "docker-compose.yml"
    )
    requirements = fixture_file_text(
        "basic_qdrant_ollama_rag", "requirements.txt"
    )
    retriever = fixture_file_text(
        "basic_qdrant_ollama_rag", "src/retriever.py"
    )

    assert "qdrant/qdrant" in compose
    assert "ollama/ollama" in compose
    assert "qdrant-client" in requirements
    assert "ollama" in requirements
    assert "QdrantClient" in retriever
    assert "nomic-embed-text" in retriever
    assert fixture_path.joinpath("src/app.py").is_file()


def test_provider_variations_cover_core_rag_stages() -> None:
    openai_config = fixture_file_text(
        "openai_external_provider_rag", "config.yaml"
    )
    pgvector_compose = fixture_file_text(
        "pgvector_openai_rag", "docker-compose.yml"
    )
    faiss_config = fixture_file_text(
        "faiss_sentence_transformers_rag", "config.yaml"
    )
    lancedb_config = fixture_file_text(
        "lancedb_or_chroma_local_rag", "config.yaml"
    )

    assert "text-embedding-3-small" in openai_config
    assert "openai-compatible" in openai_config
    assert "pgvector/pgvector" in pgvector_compose
    assert "provider: faiss" in faiss_config
    assert "provider: sentence_transformers" in faiss_config
    assert "provider: lancedb" in lancedb_config


def test_malformed_config_keeps_parse_error_signal_isolated() -> None:
    compose = fixture_file_text("malformed_config_rag", "docker-compose.yml")
    readme = fixture_file_text("malformed_config_rag", "README.md")

    assert "broken_service" in compose
    assert "intentionally malformed" in readme
    assert "does not require network" in readme


def test_custom_pipeline_components_remain_extension_signals() -> None:
    router = fixture_file_text("custom_router_rag", "src/router.py")
    reranker = fixture_file_text("reranker_extension_rag", "config.yaml")

    assert "custom_query_router" in router
    assert "needs_confirmation" in router
    assert "cross-encoder" in reranker


def test_graph_rag_fixture_exposes_graph_extension_signals() -> None:
    requirements = fixture_file_text(
        "graph_rag_extension_rag", "requirements.txt"
    )
    config = fixture_file_text("graph_rag_extension_rag", "config.yaml")
    retriever = fixture_file_text(
        "graph_rag_extension_rag", "src/graph_retriever.py"
    )

    assert "graphrag" in requirements
    assert "neo4j" in requirements
    assert "knowledge_graph" in config
    assert "graph_retriever" in retriever
    assert "entity_extraction" in retriever


def test_healthcare_rag_fixture_exposes_medical_safety_signals() -> None:
    config = fixture_file_text("healthcare_rag_minimal", "config.yaml")
    guardrails = fixture_file_text(
        "healthcare_rag_minimal", "src/guardrails.py"
    )
    citation = fixture_file_text("healthcare_rag_minimal", "src/citation.py")
    synthetic_note = fixture_file_text(
        "healthcare_rag_minimal", "docs/fake_patient_note.md"
    )

    assert "synthetic_patient_data" in config
    assert "phi_policy" in config
    assert "cite_sources_required" in config
    assert "no_diagnosis" in guardrails
    assert "emergency_escalation" in guardrails
    assert "source_id" in citation
    assert "SYNTHETIC" in synthetic_note
