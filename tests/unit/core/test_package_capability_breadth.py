from __future__ import annotations

import pytest

from systograph.core.models.scan import ScanFact
from systograph.core.services.ast_construction_output import (
    EXTERNAL_IMPORT_FACT_KIND,
    EXTERNAL_IMPORT_RULE_ID,
)
from systograph.core.services.component_bridge_models import (
    ComponentBridgeDecision,
    ComponentCandidate,
)
from systograph.core.services.component_bridge_registry import (
    ComponentBridgeDecisionKind,
    ComponentBridgeRegistry,
)


def decide(module_value: str) -> ComponentBridgeDecision:
    fact = ScanFact(
        kind=EXTERNAL_IMPORT_FACT_KIND,
        file="src/app.py",
        path="line[1]",
        value=module_value,
        rule_id=EXTERNAL_IMPORT_RULE_ID,
    )
    return ComponentBridgeRegistry().match(fact, evidence_ids=("evidence:x",))


def candidate(module_value: str) -> ComponentCandidate:
    decision = decide(module_value)
    assert decision.kind == ComponentBridgeDecisionKind.COMPONENT_CANDIDATE, (
        f"{module_value} produced {decision.kind}"
    )
    assert len(decision.component_candidates) == 1
    return decision.component_candidates[0]


@pytest.mark.parametrize(
    ("module_value", "kind", "provider"),
    [
        # Vector databases (client SDK identity is unambiguous).
        ("weaviate", "vector_db", "weaviate"),
        ("weaviate.classes.init", "vector_db", "weaviate"),
        ("lancedb", "vector_db", "lancedb"),
        ("pymilvus", "vector_db", "milvus"),
        ("pinecone", "vector_db", "pinecone"),
        ("pinecone.grpc", "vector_db", "pinecone"),
        # Multi-provider LLM gateway: an answerer exists, vendor unknown.
        ("litellm", "llm", "litellm"),
        ("litellm.Router", "llm", "litellm"),
        # Chunking / loaders.
        ("langchain_text_splitters", "chunker", "langchain"),
        ("nltk.tokenize", "chunker", "nltk"),
        ("markitdown", "document_loader", "markitdown"),
        ("assemblyai", "document_loader", "assemblyai"),
        # Local embedding models.
        (
            "sentence_transformers",
            "embedding_provider",
            "sentence_transformers",
        ),
        (
            "sentence_transformers.SentenceTransformer",
            "embedding_provider",
            "sentence_transformers",
        ),
        # Graph community detection (GraphRAG-style subsystem).
        ("graspologic.partition", "graph_rag_system", "graspologic"),
        ("graspologic_native", "graph_rag_system", "graspologic"),
    ],
)
def test_package_identity_covers_researched_ecosystem(
    module_value: str,
    kind: str,
    provider: str,
) -> None:
    # Given/When/Then: the import module path decides the component.
    item = candidate(module_value)
    assert (item.kind, item.provider) == (kind, provider)


@pytest.mark.parametrize(
    "module_value",
    [
        "llama_index.core.postprocessor.SentenceTransformerRerank",
        "llama_index.core.postprocessor.sbert_rerank.SentenceTransformerRerank",
        "llama_index.core.postprocessor.LLMRerank",
        "llama_index.core.postprocessor.StructuredLLMRerank",
        "llama_index.core.postprocessor.rankGPT_rerank.RankGPTRerank",
        "llama_index.postprocessor.flag_embedding_reranker.FlagEmbeddingReranker",
        "llama_index.postprocessor.cohere_rerank.CohereRerank",
        "llama_index.postprocessor.colbert_rerank.ColbertRerank",
        "sentence_transformers.CrossEncoder",
    ],
)
def test_specific_reranker_symbols_are_detected(module_value: str) -> None:
    # Given/When/Then: a named reranker class is direct capability
    # identity, not a guess.
    item = candidate(module_value)
    assert item.kind == "reranker"


@pytest.mark.parametrize(
    "module_value",
    [
        "llama_index.core.postprocessor",
        "llama_index.core.postprocessor.SimilarityPostprocessor",
        "llama_index.core.postprocessor.KeywordNodePostprocessor",
        "llama_index.core.postprocessor.PrevNextNodePostprocessor",
        "llama_index.core.postprocessor.MetadataReplacementPostProcessor",
        "llama_index.core.postprocessor.LongContextReorder",
    ],
)
def test_generic_postprocessor_namespace_claims_no_reranker(
    module_value: str,
) -> None:
    # Given/When/Then: only 3 of the 16 exports of that namespace are
    # rerankers, so the bare namespace and its non-reranker members must
    # produce nothing -- an honest undetermined beats a fabricated one.
    assert decide(module_value).kind == ComponentBridgeDecisionKind.NO_MATCH


@pytest.mark.parametrize(
    "module_value",
    [
        "tiktoken",
        "tiktoken.get_encoding",
        "spacy",
        "networkx",
        "httpx",
        "aiohttp",
        "requests",
    ],
)
def test_ambiguous_packages_stay_unmapped(module_value: str) -> None:
    # Given/When/Then: token counting, general NLP, generic graph maths
    # and plain HTTP clients do not imply one capability.
    assert decide(module_value).kind == ComponentBridgeDecisionKind.NO_MATCH
