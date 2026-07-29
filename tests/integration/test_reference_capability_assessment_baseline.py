from __future__ import annotations

from pathlib import Path

from tests.helpers.fixtures import rag_project_fixture_path

from kai_mind.core.models.map_build import MapBuildRequest
from kai_mind.core.services.map_build_service import MapBuildService

# End-to-end baseline for the canonical_type -> reference node lookup
# packaged as capability_type_node_map.toml. Scanning the Qdrant +
# Ollama fixture must keep lighting up exactly these four reference
# nodes at exactly these states, so that a vocabulary edit which still
# loads (every node id valid, loader happy) but no longer routes real
# components to their node cannot pass unnoticed.
#
# llm_answerer stays `partial` on purpose: the Ollama runtime is only
# reachable through indirect evidence, and MODEL-CONTRACT caps
# indirect-only evidence at partial. Pinning `detected` here would
# write a five-state contract violation into the baseline.
EXPECTED_BASELINE_STATES = {
    "index_builder": "detected",
    "api_server": "detected",
    "dense_retriever": "detected",
    "llm_answerer": "partial",
}


def test_basic_rag_fixture_pins_the_reference_capability_baseline(
    tmp_path: Path,
) -> None:
    """The packaged vocabulary keeps lighting the same four nodes.

    Given the basic Qdrant + Ollama RAG project fixture,
    When the complete scan + build pipeline runs through
    MapBuildService,
    Then the Step 6 reference capability assessment reports the baseline
    states above, and each of those four nodes carries at least one
    related component id -- i.e. the state came from a scanned component
    that reached the node through capability_type_node_map.toml, not
    from an empty node that happens to share the expected label.

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
    assessments = {
        item.reference_node_id: item
        for item in (
            result.profile_inference_result.reference_capability_assessments
        )
    }
    assert {
        node_id: assessments[node_id].status
        for node_id in EXPECTED_BASELINE_STATES
    } == EXPECTED_BASELINE_STATES
    assert {
        node_id: bool(assessments[node_id].related_component_ids)
        for node_id in EXPECTED_BASELINE_STATES
    } == dict.fromkeys(EXPECTED_BASELINE_STATES, True)
