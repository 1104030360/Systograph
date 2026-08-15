from __future__ import annotations

from pathlib import Path

import pytest

from systograph.core.services.flow_derivation_service import RELATIONSHIPS
from systograph.core.services.profile_rule_definitions import (
    PROFILE_RULE_DEFINITIONS,
)
from systograph.core.services.rule_catalog_loader import (
    RuleCatalogError,
    RuleCatalogLoader,
)


def write_catalog(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_relationship_catalog_expands_and_looks_up_full_discriminant(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "edges.toml",
        "\n".join(
            [
                "[[relationships]]",
                'from_kinds = ["retriever"]',
                'to_kinds = ["vector_db", "http_vector_store"]',
                'signal_kinds = ["call"]',
                'call_kinds = ["constructor"]',
                'callee_symbols = ["qdrant_client.QdrantClient"]',
                'producer_rule_ids = ["code_pattern_vector_store_qdrant"]',
                'relationship = "queries_vector_store"',
            ]
        )
        + "\n",
    )

    catalog = RuleCatalogLoader().load_edge_relationship_rules(catalog_path)

    assert (
        catalog.lookup_values(
            from_kind="retriever",
            to_kind="vector_db",
            signal_kind="call",
            call_kind="constructor",
            callee_symbol=" QDRANT_CLIENT.QdrantClient ",
            producer_rule_id="code_pattern_vector_store_qdrant",
        )
        == "queries_vector_store"
    )
    assert len(catalog.rules) == 2


def test_relationship_catalog_rejects_duplicate_full_discriminant(
    tmp_path: Path,
) -> None:
    shared = [
        'from_kinds = ["retriever"]',
        'to_kinds = ["llm"]',
        'signal_kinds = ["call"]',
        'call_kinds = ["method"]',
        'callee_symbols = ["invoke"]',
        'producer_rule_ids = ["ua_call_hint_static"]',
    ]
    catalog_path = write_catalog(
        tmp_path / "edges.toml",
        "\n".join(
            [
                "[[relationships]]",
                *shared,
                'relationship = "context_flow"',
                "",
                "[[relationships]]",
                *shared,
                'relationship = "rerank"',
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="duplicate discriminant"):
        RuleCatalogLoader().load_edge_relationship_rules(catalog_path)


def test_same_endpoints_can_have_distinct_semantic_discriminants(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "edges.toml",
        "\n".join(
            [
                "[[relationships]]",
                'from_kinds = ["retriever"]',
                'to_kinds = ["llm"]',
                'signal_kinds = ["call"]',
                'call_kinds = ["method"]',
                'callee_symbols = ["invoke"]',
                'producer_rule_ids = ["ua_call_hint_static"]',
                'relationship = "context_flow"',
                "",
                "[[relationships]]",
                'from_kinds = ["retriever"]',
                'to_kinds = ["llm"]',
                'signal_kinds = ["call"]',
                'call_kinds = ["method"]',
                'callee_symbols = ["rerank"]',
                'producer_rule_ids = ["ua_call_hint_rerank"]',
                'relationship = "rerank"',
            ]
        )
        + "\n",
    )

    catalog = RuleCatalogLoader().load_edge_relationship_rules(catalog_path)

    assert {rule.relationship for rule in catalog.rules} == {
        "context_flow",
        "rerank",
    }


def test_unknown_relationship_discriminant_has_no_fallback() -> None:
    catalog = RuleCatalogLoader().load_default_edge_relationship_rules()

    assert (
        catalog.lookup_values(
            from_kind="api_route",
            to_kind="vector_db",
            signal_kind="call",
            call_kind="function",
            callee_symbol="unknown",
            producer_rule_id="unknown_rule",
        )
        is None
    )


def test_packaged_relationships_use_existing_profile_vocabulary() -> None:
    catalog = RuleCatalogLoader().load_default_edge_relationship_rules()
    profile_relationships = {
        definition.required_relationship
        for definition in PROFILE_RULE_DEFINITIONS
        if definition.required_relationship is not None
    }
    known_relationships = profile_relationships | set(RELATIONSHIPS.values())

    assert {rule.relationship for rule in catalog.rules} <= known_relationships


def test_packaged_catalog_represents_every_profile_relationship() -> None:
    catalog = RuleCatalogLoader().load_default_edge_relationship_rules()
    required_relationships = {
        definition.required_relationship
        for definition in PROFILE_RULE_DEFINITIONS
        if definition.required_relationship is not None
    }

    assert required_relationships <= {
        rule.relationship for rule in catalog.rules
    }
    assert len({rule.discriminant for rule in catalog.rules}) == len(
        catalog.rules
    )
