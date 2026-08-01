from __future__ import annotations

from importlib import resources
from typing import Final, Never

import pytest
from tests.helpers.profile_inference import load_profile_map

from systograph.core.models.ai_system_map_v2 import (
    AiSystemMapV2,
    CanonicalComponent,
    CanonicalEdge,
    CanonicalEvidence,
    CanonicalEvidenceLocation,
)
from systograph.core.models.profile_signal import ProfileFinding
from systograph.core.services.profile_inference_service import (
    ProfileInferenceService,
)
from systograph.core.services.profile_relationship_alias_loader import (
    ProfileRelationshipAliasError,
    ProfileRelationshipAliasLoader,
)
from systograph.core.services.profile_rule_definitions import (
    PROFILE_RULE_DEFINITIONS,
)

# Full snapshot of the packaged transitional alias table. The table is
# the one lever that turns a naming mismatch into reachability, so every
# key AND every value is pinned here: a widened entry must be a
# deliberate edit in this test too. Deleting a row once UA emits real
# `context_flow` edges is a data change plus a one-line edit here.
EXPECTED_RELATIONSHIP_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "context_flow": ("provides_retrieved_context", "prompts_llm"),
}

MINIMAL_TABLE = (
    '[relationship_aliases]\ncontext_flow = ["provides_retrieved_context"]\n'
)

RETRIEVER_COMPONENT_ID = "component:retriever"
LLM_COMPONENT_ID = "component:llm"
VECTOR_STORE_COMPONENT_ID = "component:vector-store"
CHUNKER_COMPONENT_ID = "component:chunker"
WIRING_EVIDENCE_ID = "evidence:wiring"

# `retriever` backs `dense_retriever` and `llm` backs `llm_answerer`,
# so these two carry the `rag-grounding` node gate. `vector_store` and
# `chunker` back neither, so they serve as off-card endpoints.
COMPONENT_TYPES: Final[tuple[tuple[str, str], ...]] = (
    (RETRIEVER_COMPONENT_ID, "retriever"),
    (LLM_COMPONENT_ID, "llm"),
    (VECTOR_STORE_COMPONENT_ID, "vector_store"),
    (CHUNKER_COMPONENT_ID, "chunker"),
)


def _map_with_edge(
    *,
    relationship: str,
    source: str,
    target: str,
) -> AiSystemMapV2:
    """Build a map whose `rag-grounding` node gate always passes.

    Both required reference nodes (`dense_retriever`, `llm_answerer`)
    are backed by directly evidenced components, so only the
    relationship gate differs between scenarios. The edge carries its
    own direct evidence id instead of borrowing a component's.
    """
    base = load_profile_map("non_grounded_llm_app.v2.json")
    evidence = [
        CanonicalEvidence(
            evidence_id=f"evidence:{canonical_type}",
            artifact_type="python",
            evidence_kind="direct",
            location=CanonicalEvidenceLocation(
                path=f"src/{canonical_type}.py",
                start_line=1,
            ),
            rule_id=f"test.{canonical_type}",
        )
        for _, canonical_type in COMPONENT_TYPES
    ]
    evidence.append(
        CanonicalEvidence(
            evidence_id=WIRING_EVIDENCE_ID,
            artifact_type="python",
            evidence_kind="direct",
            location=CanonicalEvidenceLocation(
                path="src/wiring.py",
                start_line=1,
            ),
            rule_id="test.wiring",
        )
    )
    components = [
        CanonicalComponent(
            component_id=component_id,
            display_name=canonical_type.replace("_", " ").title(),
            canonical_type=canonical_type,
            layer="undetermined",
            status="detected",
            activation="enabled",
            evidence_ids=[f"evidence:{canonical_type}"],
            metadata={},
        )
        for component_id, canonical_type in COMPONENT_TYPES
    ]
    edges = [
        CanonicalEdge(
            edge_id=f"edge:{relationship}",
            source=source,
            target=target,
            relationship=relationship,
            status="observed",
            evidence_ids=[WIRING_EVIDENCE_ID],
        )
    ]
    return base.model_copy(
        update={
            "components": components,
            "edges": edges,
            "evidence": evidence,
            "endpoints": [],
            "risk_hints": [],
            "unmapped_components": [],
        }
    )


def _rag_grounding_finding(system_map: AiSystemMapV2) -> ProfileFinding:
    result = ProfileInferenceService().infer(
        system_map,
        build_id="build:relationship-alias",
        scan_id="scan:relationship-alias",
        environment_id=system_map.environment_id,
    )
    return next(
        item for item in result.profiles if item.profile_id == "rag-grounding"
    )


def test_packaged_table_pins_the_single_transitional_entry() -> None:
    # Given / When
    aliases = ProfileRelationshipAliasLoader().load()

    # Then
    assert dict(aliases) == EXPECTED_RELATIONSHIP_ALIASES


def test_packaged_table_leaves_every_other_card_unaliased() -> None:
    """Only `rag-grounding` may gain reachability from this table.

    The other twelve relationship-gated cards name relationships no
    FlowDerivation edge carries for a semantically equivalent reason,
    so an alias there would manufacture false positives.
    """
    # Given
    aliases = ProfileRelationshipAliasLoader().load()

    # When
    aliased_cards = tuple(
        definition.profile_id
        for definition in PROFILE_RULE_DEFINITIONS
        if definition.required_relationship in aliases
    )

    # Then
    assert aliased_cards == ("rag-grounding",)


def test_parse_text_rejects_alias_key_outside_the_card_definitions() -> None:
    # Given: a plausible typo of a card's `required_relationship`.
    invalid = MINIMAL_TABLE.replace("context_flow", "context_flo")

    # When / Then
    with pytest.raises(
        ProfileRelationshipAliasError,
        match="unknown alias key 'context_flo'",
    ):
        ProfileRelationshipAliasLoader().parse_text(invalid)


def test_parse_text_rejects_alias_key_that_is_only_a_flow_name() -> None:
    # Given: a real FlowDerivation relationship name is still not a
    # card's `required_relationship`, so it cannot open a gate.
    invalid = MINIMAL_TABLE.replace("context_flow", "queries_vector_store")

    # When / Then
    with pytest.raises(
        ProfileRelationshipAliasError,
        match="unknown alias key 'queries_vector_store'",
    ):
        ProfileRelationshipAliasLoader().parse_text(invalid)


def test_parse_text_rejects_alias_value_outside_flow_relationships() -> None:
    # Given: a plausible typo of a FlowDerivation relationship name.
    invalid = MINIMAL_TABLE.replace(
        "provides_retrieved_context",
        "provides_retrieved_contex",
    )

    # When / Then
    with pytest.raises(
        ProfileRelationshipAliasError,
        match="unknown relationship name 'provides_retrieved_contex'",
    ):
        ProfileRelationshipAliasLoader().parse_text(invalid)


def test_parse_text_rejects_empty_table() -> None:
    # Given
    empty = "[relationship_aliases]\n"

    # When / Then
    with pytest.raises(
        ProfileRelationshipAliasError,
        match="must be a non-empty table",
    ):
        ProfileRelationshipAliasLoader().parse_text(empty)


def test_parse_text_rejects_missing_table_section() -> None:
    # Given
    missing = "# no alias section at all\n"

    # When / Then
    with pytest.raises(
        ProfileRelationshipAliasError,
        match="must be a non-empty table",
    ):
        ProfileRelationshipAliasLoader().parse_text(missing)


def test_parse_text_rejects_non_list_value() -> None:
    # Given
    invalid = (
        '[relationship_aliases]\ncontext_flow = "provides_retrieved_context"\n'
    )

    # When / Then
    with pytest.raises(
        ProfileRelationshipAliasError,
        match="context_flow must be a non-empty list",
    ):
        ProfileRelationshipAliasLoader().parse_text(invalid)


def test_parse_text_rejects_empty_alias_list() -> None:
    # Given
    invalid = "[relationship_aliases]\ncontext_flow = []\n"

    # When / Then
    with pytest.raises(
        ProfileRelationshipAliasError,
        match="context_flow must be a non-empty list",
    ):
        ProfileRelationshipAliasLoader().parse_text(invalid)


def test_parse_text_rejects_blank_alias_name() -> None:
    # Given
    invalid = '[relationship_aliases]\ncontext_flow = [" "]\n'

    # When / Then
    with pytest.raises(
        ProfileRelationshipAliasError,
        match="context_flow must be a non-empty list",
    ):
        ProfileRelationshipAliasLoader().parse_text(invalid)


def test_parse_text_rejects_unknown_section() -> None:
    # Given
    invalid = MINIMAL_TABLE + '\n[node_aliases]\nllm = ["llm_answerer"]\n'

    # When / Then
    with pytest.raises(
        ProfileRelationshipAliasError,
        match="unknown section: node_aliases",
    ):
        ProfileRelationshipAliasLoader().parse_text(invalid)


def test_parse_text_rejects_duplicate_alias_key() -> None:
    # Given: tomllib rejects duplicate keys natively.
    duplicate = MINIMAL_TABLE + 'context_flow = ["prompts_llm"]\n'

    # When / Then
    with pytest.raises(
        ProfileRelationshipAliasError,
        match="failed to parse profile_relationship_alias.toml",
    ):
        ProfileRelationshipAliasLoader().parse_text(duplicate)


def test_parse_text_rejects_malformed_toml() -> None:
    # Given
    malformed = "[relationship_aliases"

    # When / Then
    with pytest.raises(
        ProfileRelationshipAliasError,
        match="failed to parse profile_relationship_alias.toml",
    ):
        ProfileRelationshipAliasLoader().parse_text(malformed)


def test_load_wraps_packaged_table_read_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    def unavailable(_package: str) -> Never:
        raise OSError("alias table unavailable")

    monkeypatch.setattr(resources, "files", unavailable)

    # When / Then
    with pytest.raises(
        ProfileRelationshipAliasError,
        match="failed to read packaged profile_relationship_alias.toml",
    ):
        ProfileRelationshipAliasLoader().load()


@pytest.mark.parametrize(
    "relationship",
    ["provides_retrieved_context", "prompts_llm"],
)
def test_aliased_edge_on_required_component_detects(
    relationship: str,
) -> None:
    # Given: the `rag-grounding` node gate passes and the only wiring
    # edge carries an aliased FlowDerivation name with one endpoint on
    # a component backing a required reference node.
    system_map = _map_with_edge(
        relationship=relationship,
        source=RETRIEVER_COMPONENT_ID,
        target=LLM_COMPONENT_ID,
    )

    # When: the sole owner of profile assessment evaluates the card.
    finding = _rag_grounding_finding(system_map)

    # Then: the relationship name mismatch was the only blocker.
    assert finding.status == "detected"
    assert WIRING_EVIDENCE_ID in finding.direct_evidence_ids


def test_unaliased_relationship_name_cannot_detect() -> None:
    # Given: the `basic_qdrant_ollama_rag` real-world shape -- a single
    # `queries_vector_store` edge whose source endpoint sits on the
    # card's required retriever component, so only the name differs.
    system_map = _map_with_edge(
        relationship="queries_vector_store",
        source=RETRIEVER_COMPONENT_ID,
        target=VECTOR_STORE_COMPONENT_ID,
    )

    # When: the sole owner of profile assessment evaluates the card.
    finding = _rag_grounding_finding(system_map)

    # Then: the alias table stays narrow -- an unlisted name is not
    # `context_flow`, whatever its endpoints are.
    assert finding.status == "partial"
    assert WIRING_EVIDENCE_ID not in finding.evidence_ids


def test_aliased_edge_off_required_components_cannot_detect() -> None:
    # Given: an aliased name whose two endpoints both sit off the
    # card's required components.
    system_map = _map_with_edge(
        relationship="provides_retrieved_context",
        source=VECTOR_STORE_COMPONENT_ID,
        target=CHUNKER_COMPONENT_ID,
    )

    # When: the sole owner of profile assessment evaluates the card.
    finding = _rag_grounding_finding(system_map)

    # Then: the alias expands the name lookup only -- it composes with
    # the endpoint constraint instead of bypassing it.
    assert finding.status == "partial"
    assert WIRING_EVIDENCE_ID not in finding.evidence_ids
