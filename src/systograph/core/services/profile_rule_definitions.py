from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class ProfileRuleDefinition:
    profile_id: str
    required_node_ids: tuple[str, ...]
    required_relationship: str | None = None


PROFILE_RULE_DEFINITIONS: Final = (
    ProfileRuleDefinition(
        "rag-grounding",
        ("dense_retriever", "llm_answerer"),
        "context_flow",
    ),
    ProfileRuleDefinition(
        "agentic-control",
        ("agent_loop", "llm_answerer"),
    ),
    ProfileRuleDefinition(
        "tool-calling",
        ("agent_loop", "tool_using_generator"),
        "tool_call",
    ),
    ProfileRuleDefinition("memory", ("long_term_memory",)),
    ProfileRuleDefinition(
        "workflow-orchestration",
        ("orchestrator",),
        "workflow_transition",
    ),
    ProfileRuleDefinition(
        "hybrid-retrieval",
        ("hybrid_retriever",),
        "retrieval_fusion",
    ),
    ProfileRuleDefinition("reranking", ("reranker",), "rerank"),
    ProfileRuleDefinition(
        "corrective-retrieval",
        ("conflict_checker", "router"),
        "fallback_route",
    ),
    ProfileRuleDefinition(
        "self-reflection",
        ("conflict_checker", "agent_loop"),
        "self_critique",
    ),
    ProfileRuleDefinition(
        "graph-retrieval",
        ("graph_retriever",),
        "graph_retrieval",
    ),
    ProfileRuleDefinition(
        "hierarchical-retrieval",
        ("index_builder", "context_composer"),
        "hierarchical_flow",
    ),
    ProfileRuleDefinition(
        "contextual-retrieval",
        ("metadata_extractor", "context_composer"),
        "context_enrichment",
    ),
    ProfileRuleDefinition(
        "multimodal-grounding",
        ("rag_anything_system",),
        "multimodal_retrieval",
    ),
    ProfileRuleDefinition(
        "modular-composition",
        ("orchestrator", "router"),
        "component_selection",
    ),
    ProfileRuleDefinition(
        "multi-query-retrieval",
        ("query_classifier", "router"),
        "query_route",
    ),
)

MVP_CAPABILITY_PROFILE_IDS: Final = tuple(
    definition.profile_id for definition in PROFILE_RULE_DEFINITIONS
)
