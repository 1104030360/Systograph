from __future__ import annotations

from systograph.core.models.scan import ScanFact
from systograph.core.services.component_bridge_registry import (
    ComponentBridgeDecisionKind,
    ComponentBridgeRegistry,
)
from systograph.core.services.rule_catalog_loader import (
    PackageCapabilityRule,
)


def test_qdrant_rule_maps_to_component_with_evidence() -> None:
    decision = ComponentBridgeRegistry().match(
        ScanFact(
            kind="docker_service",
            file="docker-compose.yml",
            path="services.qdrant.image",
            value="qdrant/qdrant:v1.12.1",
            rule_id="docker_qdrant_image_detected",
        ),
        evidence_ids=("evidence:qdrant",),
    )

    assert decision.kind is ComponentBridgeDecisionKind.COMPONENT_CANDIDATE
    assert decision.component_candidates[0].slot == "vector_store"
    assert decision.component_candidates[0].provider == "qdrant"


def test_ua_rule_mirror_maps_through_the_same_catalog_row() -> None:
    decision = ComponentBridgeRegistry().match(
        ScanFact(
            kind="vector_store_client",
            file="src/app.py",
            path="calls[main->qdrant_client.QdrantClient]",
            value="qdrant_client.QdrantClient",
            rule_id="ua_call_hint_vector_store_qdrant",
        ),
        evidence_ids=("evidence:ua:qdrant",),
    )

    assert decision.kind is ComponentBridgeDecisionKind.COMPONENT_CANDIDATE
    assert decision.component_candidates[0].slot == "vector_store"
    assert decision.component_candidates[0].provider == "qdrant"


def test_pgvector_query_maps_to_store_and_retriever_components() -> None:
    decision = ComponentBridgeRegistry().match(
        ScanFact(
            kind="vector_store_client",
            file="src/retrieval.py",
            path="line[8]",
            value="<->",
            rule_id="code_pattern_vector_store_pgvector_query",
        ),
        evidence_ids=("evidence:pgvector-query",),
    )

    assert decision.kind is ComponentBridgeDecisionKind.COMPONENT_CANDIDATE
    assert {
        (candidate.slot, candidate.kind, candidate.provider)
        for candidate in decision.component_candidates
    } == {
        ("retriever", "retriever", None),
        ("vector_store", "vector_db", "pgvector"),
    }


def test_ollama_embedding_call_maps_to_embedding_and_runtime() -> None:
    decision = ComponentBridgeRegistry().match(
        ScanFact(
            kind="embedding",
            file="localrag.py",
            path="line[25]",
            value="ollama.embeddings(",
            rule_id="code_pattern_embedding_ollama",
        ),
        evidence_ids=("evidence:ollama-embeddings",),
    )

    assert decision.kind is ComponentBridgeDecisionKind.COMPONENT_CANDIDATE
    assert {
        (candidate.slot, candidate.kind, candidate.name, candidate.provider)
        for candidate in decision.component_candidates
    } == {
        ("embedding_model", "embedding_provider", "Ollama", "ollama"),
        ("llm", "local_llm_runtime", "Ollama", "ollama"),
    }


def test_ollama_embedding_ua_mirror_maps_through_the_same_row() -> None:
    decision = ComponentBridgeRegistry().match(
        ScanFact(
            kind="embedding",
            file="localrag.py",
            path="calls[get_relevant_context->ollama.embeddings]",
            value="ollama.embeddings",
            rule_id="ua_call_hint_embedding_ollama",
        ),
        evidence_ids=("evidence:ua:ollama-embeddings",),
    )

    assert decision.kind is ComponentBridgeDecisionKind.COMPONENT_CANDIDATE
    assert {
        (candidate.slot, candidate.provider)
        for candidate in decision.component_candidates
    } == {
        ("embedding_model", "ollama"),
        ("llm", "ollama"),
    }


def test_ollama_llm_call_rules_map_to_local_llm_runtime() -> None:
    registry = ComponentBridgeRegistry()
    for rule_id in (
        "code_pattern_llm_chat_ollama",
        "code_pattern_llm_client_ollama",
        "code_pattern_llm_openai_compat_local_ollama",
    ):
        decision = registry.match(
            ScanFact(
                kind="llm_call",
                file="localrag.py",
                path="line[118]",
                value="OpenAI(",
                rule_id=rule_id,
            ),
            evidence_ids=(f"evidence:{rule_id}",),
        )

        assert decision.kind is ComponentBridgeDecisionKind.COMPONENT_CANDIDATE
        assert {
            (
                candidate.slot,
                candidate.kind,
                candidate.name,
                candidate.provider,
            )
            for candidate in decision.component_candidates
        } == {("llm", "local_llm_runtime", "Ollama", "ollama")}


def test_plain_openai_client_maps_to_external_openai_provider() -> None:
    decision = ComponentBridgeRegistry().match(
        ScanFact(
            kind="llm_call",
            file="src/app.py",
            path="line[7]",
            value="OpenAI(",
            rule_id="code_pattern_llm_client_openai",
        ),
        evidence_ids=("evidence:openai-client",),
    )

    assert decision.kind is ComponentBridgeDecisionKind.COMPONENT_CANDIDATE
    assert {
        (candidate.slot, candidate.kind, candidate.name, candidate.provider)
        for candidate in decision.component_candidates
    } == {("llm", "external_llm_provider", "OpenAI", "openai")}


def test_openai_sdk_chat_protocol_evidence_does_not_pick_a_vendor() -> None:
    decision = ComponentBridgeRegistry().match(
        ScanFact(
            kind="llm_call",
            file="localrag.py",
            path="line[97]",
            value=".chat.completions.create(",
            rule_id="code_pattern_llm_chat_openai_sdk",
        ),
        evidence_ids=("evidence:openai-sdk-chat",),
    )

    assert decision.kind is ComponentBridgeDecisionKind.NO_MATCH
    assert decision.component_candidates == ()


def test_bridge_marks_reranker_as_non_baseline_review_signal() -> None:
    decision = ComponentBridgeRegistry().match(
        ScanFact(
            kind="code_pattern",
            file="src/rerank.py",
            path="Reranker.rerank",
            value="rerank_documents",
            rule_id="code_pattern_reranker",
        ),
        evidence_ids=("evidence:reranker",),
    )

    assert (
        decision.kind
        is ComponentBridgeDecisionKind.NON_BASELINE_CAPABILITY_SIGNAL
    )
    assert decision.unmapped_component is not None
    assert decision.unmapped_component.observed_kind == "reranker_candidate"


def test_bridge_does_not_materialize_items_without_evidence() -> None:
    decision = ComponentBridgeRegistry().match(
        ScanFact(
            kind="docker_service",
            file="docker-compose.yml",
            path="services.qdrant.image",
            value="qdrant/qdrant:v1.12.1",
            rule_id="docker_qdrant_image_detected",
        ),
        evidence_ids=(),
    )

    assert decision.kind is ComponentBridgeDecisionKind.NO_MATCH
    assert decision.component_candidates == ()
    assert decision.unmapped_component is None


def _import_fact(value: str, *, line: int = 1) -> ScanFact:
    return ScanFact(
        kind="external_import_declaration",
        file="src/app.py",
        path=f"line[{line}]",
        value=value,
        rule_id="ast_external_import",
    )


def test_package_import_maps_to_registry_component() -> None:
    decision = ComponentBridgeRegistry().match(
        _import_fact("ollama"),
        evidence_ids=("evidence:import:ollama",),
    )

    assert decision.kind is ComponentBridgeDecisionKind.COMPONENT_CANDIDATE
    assert [
        (candidate.slot, candidate.kind, candidate.name, candidate.provider)
        for candidate in decision.component_candidates
    ] == [("llm", "local_llm_runtime", "Ollama", "ollama")]
    assert decision.component_candidates[0].evidence_ids == (
        "evidence:import:ollama",
    )


def test_package_import_submodule_matches_top_level_segment() -> None:
    # "from qdrant_client.http import models" -> top-level qdrant_client.
    decision = ComponentBridgeRegistry().match(
        _import_fact("qdrant_client.http.models"),
        evidence_ids=("evidence:import:qdrant-http",),
    )

    assert decision.kind is ComponentBridgeDecisionKind.COMPONENT_CANDIDATE
    assert [
        (candidate.slot, candidate.kind, candidate.provider)
        for candidate in decision.component_candidates
    ] == [("vector_store", "vector_db", "qdrant")]


def test_package_import_document_and_parser_capabilities_map() -> None:
    registry = ComponentBridgeRegistry()
    expected = {
        "PyPDF2.PdfReader": ("document_loader", "document_loader", "pypdf2"),
        "pypdf.PdfReader": ("document_loader", "document_loader", "pypdf"),
        "bs4.BeautifulSoup": ("parser", "parser", "beautifulsoup4"),
    }
    for value, (slot, kind, provider) in expected.items():
        decision = registry.match(
            _import_fact(value),
            evidence_ids=(f"evidence:import:{provider}",),
        )

        assert decision.kind is (
            ComponentBridgeDecisionKind.COMPONENT_CANDIDATE
        )
        assert [
            (
                candidate.slot,
                candidate.kind,
                candidate.provider,
            )
            for candidate in decision.component_candidates
        ] == [(slot, kind, provider)]


def test_excluded_package_imports_create_nothing() -> None:
    # openai belongs to the endpoint disambiguation ladder; torch is a
    # general-purpose package. Neither may create components, unmapped
    # review items, or capability signals from the import layer.
    registry = ComponentBridgeRegistry()
    for value in ("openai", "openai.OpenAI", "torch", "chromadb"):
        decision = registry.match(
            _import_fact(value),
            evidence_ids=("evidence:import:excluded",),
        )

        assert decision.kind is ComponentBridgeDecisionKind.NO_MATCH
        assert decision.component_candidates == ()
        assert decision.unmapped_component is None


def test_unmatched_import_never_falls_into_router_heuristics() -> None:
    # "fastapi.APIRouter" contains "router": the import layer must stay
    # silent instead of fabricating a router-like review item.
    decision = ComponentBridgeRegistry().match(
        _import_fact("fastapi.APIRouter"),
        evidence_ids=("evidence:import:fastapi",),
    )

    assert decision.kind is ComponentBridgeDecisionKind.NO_MATCH
    assert decision.unmapped_component is None


def test_package_import_without_evidence_is_not_materialized() -> None:
    decision = ComponentBridgeRegistry().match(
        _import_fact("ollama"),
        evidence_ids=(),
    )

    assert decision.kind is ComponentBridgeDecisionKind.NO_MATCH
    assert decision.component_candidates == ()


def test_dotted_submodule_import_maps_to_framework_capability() -> None:
    # "from llama_index.core.memory import ChatMemoryBuffer" -- the
    # capability lives in the dotted submodule path.
    decision = ComponentBridgeRegistry().match(
        _import_fact("llama_index.core.memory.ChatMemoryBuffer"),
        evidence_ids=("evidence:import:llamaindex-memory",),
    )

    assert decision.kind is ComponentBridgeDecisionKind.COMPONENT_CANDIDATE
    assert [
        (candidate.slot, candidate.kind, candidate.name, candidate.provider)
        for candidate in decision.component_candidates
    ] == [
        (
            "working_memory",
            "working_memory",
            "LlamaIndex Chat Memory",
            "llama_index",
        )
    ]


def test_deeper_submodule_import_matches_registry_prefix() -> None:
    # "from llama_index.core.node_parser.text.sentence import ..."
    # matches the llama_index.core.node_parser prefix on segment
    # boundaries.
    decision = ComponentBridgeRegistry().match(
        _import_fact(
            "llama_index.core.node_parser.text.sentence.SentenceSplitter"
        ),
        evidence_ids=("evidence:import:llamaindex-node-parser",),
    )

    assert decision.kind is ComponentBridgeDecisionKind.COMPONENT_CANDIDATE
    assert [
        (candidate.slot, candidate.kind, candidate.provider)
        for candidate in decision.component_candidates
    ] == [("chunking", "chunker", "llama_index")]


def test_bare_or_unmapped_framework_imports_create_nothing() -> None:
    # The framework top level is deliberately unmapped, and so is any
    # prefix without an explicit entry -- including vendor-less
    # llama_index.llms / llama_index.embeddings and unknown vendors.
    registry = ComponentBridgeRegistry()
    for value in (
        "llama_index",
        "llama_index.core",
        "llama_index.core.settings.Settings",
        "llama_index.llms",
        "llama_index.embeddings.cohere.CohereEmbedding",
    ):
        decision = registry.match(
            _import_fact(value),
            evidence_ids=("evidence:import:llamaindex-unmapped",),
        )

        assert decision.kind is ComponentBridgeDecisionKind.NO_MATCH
        assert decision.component_candidates == ()
        assert decision.unmapped_component is None


def test_vendor_bearing_llamaindex_imports_map_to_known_vendors() -> None:
    registry = ComponentBridgeRegistry()
    expected = {
        "llama_index.vector_stores.qdrant.QdrantVectorStore": (
            "vector_store",
            "vector_db",
            "qdrant",
        ),
        "llama_index.embeddings.openai.OpenAIEmbedding": (
            "embedding_model",
            "embedding_provider",
            "openai",
        ),
        "llama_index.llms.openai.OpenAI": (
            "llm",
            "external_llm_provider",
            "openai",
        ),
        "llama_index.llms.ollama.Ollama": (
            "llm",
            "local_llm_runtime",
            "ollama",
        ),
        "llama_index.embeddings.ollama.OllamaEmbedding": (
            "embedding_model",
            "embedding_provider",
            "ollama",
        ),
    }
    for value, (slot, kind, provider) in expected.items():
        decision = registry.match(
            _import_fact(value),
            evidence_ids=(f"evidence:import:{provider}",),
        )

        assert decision.kind is (
            ComponentBridgeDecisionKind.COMPONENT_CANDIDATE
        )
        assert [
            (candidate.slot, candidate.kind, candidate.provider)
            for candidate in decision.component_candidates
        ] == [(slot, kind, provider)]


def test_longest_prefix_wins_over_top_level_coexistence() -> None:
    registry = ComponentBridgeRegistry(
        package_rules=(
            PackageCapabilityRule(
                module="pkg",
                slot="llm",
                kind="local_llm_runtime",
                name="Pkg",
                provider="pkg",
            ),
            PackageCapabilityRule(
                module="pkg.memory",
                slot="working_memory",
                kind="working_memory",
                name="Pkg Memory",
                provider="pkg",
            ),
        ),
    )

    dotted = registry.match(
        _import_fact("pkg.memory.Buffer"),
        evidence_ids=("evidence:import:pkg-memory",),
    )
    top_level = registry.match(
        _import_fact("pkg.other.Client"),
        evidence_ids=("evidence:import:pkg-other",),
    )

    assert [
        (candidate.slot, candidate.kind)
        for candidate in dotted.component_candidates
    ] == [("working_memory", "working_memory")]
    assert [
        (candidate.slot, candidate.kind)
        for candidate in top_level.component_candidates
    ] == [("llm", "local_llm_runtime")]
