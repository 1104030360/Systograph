from __future__ import annotations

from dataclasses import dataclass

from kai_mind.core.models.profile_signal import ProfileAxis


@dataclass(frozen=True, slots=True)
class ProfileDefinition:
    profile_id: str
    label: str
    primary_axis: ProfileAxis
    required_node_ids: tuple[str, ...]
    required_relationship: str | None = None


PROFILE_DEFINITIONS: tuple[ProfileDefinition, ...] = (
    ProfileDefinition(
        "rag-grounding",
        "RAG Grounding",
        "grounding",
        ("dense_retriever", "llm_answerer"),
        "context_flow",
    ),
    ProfileDefinition(
        "agentic-control",
        "Agentic Control",
        "agent_control",
        ("agent_loop", "llm_answerer"),
    ),
    ProfileDefinition(
        "tool-calling",
        "Tool Calling",
        "tool_use",
        ("agent_loop", "tool_using_generator"),
        "tool_call",
    ),
    ProfileDefinition(
        "memory",
        "Memory",
        "memory",
        ("long_term_memory",),
    ),
    ProfileDefinition(
        "workflow-orchestration",
        "Workflow Orchestration",
        "workflow_orchestration",
        ("orchestrator",),
        "workflow_transition",
    ),
    ProfileDefinition(
        "hybrid-retrieval",
        "Hybrid Retrieval",
        "retrieval_strategy",
        ("hybrid_retriever",),
        "retrieval_fusion",
    ),
    ProfileDefinition(
        "reranking",
        "Reranking",
        "retrieval_strategy",
        ("reranker",),
        "rerank",
    ),
    ProfileDefinition(
        "corrective-retrieval",
        "Corrective Retrieval",
        "agent_control",
        ("conflict_checker", "router"),
        "fallback_route",
    ),
    ProfileDefinition(
        "self-reflection",
        "Self Reflection",
        "agent_control",
        ("conflict_checker", "agent_loop"),
        "self_critique",
    ),
    ProfileDefinition(
        "graph-retrieval",
        "Graph Retrieval",
        "knowledge_structure",
        ("graph_retriever",),
        "graph_retrieval",
    ),
    ProfileDefinition(
        "hierarchical-retrieval",
        "Hierarchical Retrieval",
        "knowledge_structure",
        ("index_builder", "context_composer"),
        "hierarchical_flow",
    ),
    ProfileDefinition(
        "contextual-retrieval",
        "Contextual Retrieval",
        "context_enrichment",
        ("metadata_extractor", "context_composer"),
        "context_enrichment",
    ),
    ProfileDefinition(
        "multimodal-grounding",
        "Multimodal Grounding",
        "data_modality",
        ("rag_anything_system",),
        "multimodal_retrieval",
    ),
    ProfileDefinition(
        "modular-composition",
        "Modular Composition",
        "design_paradigm",
        ("orchestrator", "router"),
        "component_selection",
    ),
    ProfileDefinition(
        "multi-query-retrieval",
        "Multi-query Retrieval",
        "retrieval_strategy",
        ("query_classifier", "router"),
        "query_route",
    ),
)

MVP_CAPABILITY_PROFILE_IDS = tuple(
    definition.profile_id for definition in PROFILE_DEFINITIONS
)
