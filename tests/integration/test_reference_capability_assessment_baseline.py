from __future__ import annotations

from pathlib import Path

from tests.helpers.fixtures import rag_project_fixture_path

from systograph.core.models.map_build import MapBuildRequest
from systograph.core.services.map_build_service import MapBuildService

# End-to-end baseline for the canonical_type -> reference node lookup
# packaged as capability_type_node_map.toml. Scanning the Qdrant +
# Ollama fixture must keep lighting up these four reference nodes at
# exactly these states, so that a vocabulary edit which still loads
# (every node id valid, loader happy) but no longer routes real
# components to their node cannot pass unnoticed.
#
# These four rows are all this test pins -- not exclusivity. A fifth
# node lighting up stays green here; the packaged lookup's full key AND
# value set is snapshotted by
# `test_packaged_map_pins_every_canonical_type_and_node_tuple` in
# tests/unit/core/test_capability_type_node_map_loader.py, so an edit
# that re-targets or widens the vocabulary has to be deliberate there.
#
# llm_answerer is `detected`: the fixture's direct in-code
# `ollama.embeddings(...)` call (src/retriever.py) is direct evidence
# for the Ollama runtime via code_pattern_embedding_ollama, on top of
# the indirect docker-compose service. Before that rule existed the
# runtime was reachable only through indirect evidence and the
# MODEL-CONTRACT indirect-only cap kept this node at `partial`.
EXPECTED_BASELINE_STATES = {
    "index_builder": "detected",
    "api_server": "detected",
    "dense_retriever": "detected",
    "llm_answerer": "detected",
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
    build never writes to the real ~/.systograph.
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
