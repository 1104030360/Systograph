from __future__ import annotations

from pathlib import Path

from tests.helpers.fixtures import rag_project_fixture_path

from kai_mind.core.models.map_build import MapBuildRequest
from kai_mind.core.services.map_build_service import MapBuildService

# Today's adjudicated status of all 15 capability profile cards on the
# basic Qdrant + Ollama fixture. Two cards reach `partial`, the other 13
# stay `undetermined`; none is `detected`, and that is the point.
#
# Why each value is what it is (see `infer_profile_status`, which keys
# `partial` off the FIRST required node's state):
#
# - rag-grounding: dense_retriever is `detected` so the card is
#   `partial`, but llm_answerer is only `partial` (indirect-only Ollama
#   evidence) and the fixture emits a single `queries_vector_store`
#   edge, so neither the node gate nor the `context_flow` relationship
#   gate (alias-expanded to provides_retrieved_context / prompts_llm)
#   is satisfied.
# - hierarchical-retrieval: index_builder is `detected` so the card is
#   `partial`; context_composer is unreachable by auto-scan and no
#   `hierarchical_flow` edge exists.
# - agentic-control: llm_answerer is `partial`, but the first required
#   node agent_loop is `undetermined`, which pins the card at
#   `undetermined`.
# - the remaining 12: their first required reference node is not
#   reachable by any component bridge rule, so the node gate alone
#   already holds them at `undetermined`.
EXPECTED_PROFILE_CARD_STATUSES = {
    "rag-grounding": "partial",
    "agentic-control": "undetermined",
    "tool-calling": "undetermined",
    "memory": "undetermined",
    "workflow-orchestration": "undetermined",
    "hybrid-retrieval": "undetermined",
    "reranking": "undetermined",
    "corrective-retrieval": "undetermined",
    "self-reflection": "undetermined",
    "graph-retrieval": "undetermined",
    "hierarchical-retrieval": "partial",
    "contextual-retrieval": "undetermined",
    "multimodal-grounding": "undetermined",
    "modular-composition": "undetermined",
    "multi-query-retrieval": "undetermined",
}


def test_basic_rag_fixture_pins_all_fifteen_profile_card_statuses(
    tmp_path: Path,
) -> None:
    """No card may quietly turn green on this fixture.

    Given the basic Qdrant + Ollama RAG project fixture,
    When the complete scan + build pipeline runs through
    MapBuildService,
    Then every one of the 15 capability profile cards reports exactly
    the status pinned above.

    This snapshot exists to stop a future relationship alias, bridge
    rule, or vocabulary edit from "fixing" a card via a false positive
    without anyone noticing, and it catches those edits only where this
    fixture's own components and edges reach the card's gates. A widened
    alias for a gate this fixture cannot exercise leaves the snapshot
    green -- aliasing `rerank` to `queries_vector_store` changes nothing
    because no reranker component exists here, so the endpoint filter
    drops the edge, and aliasing `hierarchical_flow` to
    `stores_vectors` changes nothing because this fixture emits no
    `stores_vectors` edge at all. Those unreachable cards are guarded
    instead by `test_packaged_table_leaves_every_other_card_unaliased`
    in tests/unit/core/test_profile_relationship_alias.py, which
    forbids an alias key for any card but `rag-grounding`.

    When a change does reach a gate here, the card flips and the dict
    diff names it. A card moving to `detected` on this fixture is a
    claim that the scanner proved wiring it cannot see today --
    re-derive the card's gates before touching this expectation.

    Durable local state is redirected by the autouse
    `isolate_default_state_root` fixture in tests/conftest.py, so this
    build never writes to the real ~/.kai-mind.
    """
    # Given / When
    result = MapBuildService().build(
        MapBuildRequest(
            project_path=rag_project_fixture_path("basic_qdrant_ollama_rag"),
            output=tmp_path / "outputs",
        )
    )

    # Then
    assert result.status == "ok"
    assert result.profile_inference_result is not None
    profiles = result.profile_inference_result.profiles
    assert {
        finding.profile_id: finding.status for finding in profiles
    } == EXPECTED_PROFILE_CARD_STATUSES
