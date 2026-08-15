from __future__ import annotations

import pytest
from pydantic import ValidationError

from systograph.core.models.scan import ProjectScanResult, ProviderScanResult
from systograph.core.models.structural_fact import (
    CallStructuralFact,
    FactoryInferenceStep,
    FactoryInferenceStructuralFact,
    ImportStructuralFact,
    SourceSpan,
    StructuralFact,
    SymbolStructuralFact,
)


def structural_facts() -> tuple[StructuralFact, ...]:
    return (
        CallStructuralFact(
            identity_namespace="ua_call_hint",
            caller="app.main",
            callee="qdrant_client.QdrantClient",
            span=SourceSpan(
                file="src/app.py",
                line_start=12,
                line_end=12,
            ),
        ),
        ImportStructuralFact(
            identity_namespace="ua_external_import",
            import_scope="external",
            module="qdrant_client",
            symbol="QdrantClient",
            alias="Client",
            span=SourceSpan(
                file="src/app.py",
                line_start=3,
                line_end=3,
            ),
        ),
        SymbolStructuralFact(
            identity_namespace="ua_symbol",
            symbol="app.main",
            symbol_kind="function",
            span=SourceSpan(
                file="src/app.py",
                line_start=8,
                line_end=16,
            ),
        ),
        FactoryInferenceStructuralFact(
            identity_namespace="ast_factory_inference",
            caller="app.build",
            factory="app.get_store",
            constructed_symbol="qdrant_client.QdrantClient",
            call_span=SourceSpan(
                file="src/app.py",
                line_start=20,
                line_end=20,
            ),
            provenance=(
                FactoryInferenceStep(
                    hop=0,
                    factory="app.get_store",
                    resolution="return_construction",
                    span=SourceSpan(
                        file="src/factories.py",
                        line_start=9,
                        line_end=9,
                    ),
                ),
            ),
        ),
    )


def test_structural_fact_union_round_trips_through_project_scan_result() -> (
    None
):
    # Given: all four typed structural fact variants.
    original = ProjectScanResult(structural_facts=list(structural_facts()))

    # When: the aggregate scan payload crosses its JSON persistence boundary.
    restored = ProjectScanResult.model_validate_json(
        original.model_dump_json()
    )

    # Then: the discriminator restores concrete models, not free-form dicts.
    assert restored == original
    assert [type(item) for item in restored.structural_facts] == [
        CallStructuralFact,
        ImportStructuralFact,
        SymbolStructuralFact,
        FactoryInferenceStructuralFact,
    ]


def test_provider_scan_result_carries_typed_structural_facts() -> None:
    original = ProviderScanResult(structural_facts=list(structural_facts()))

    restored = ProviderScanResult.model_validate_json(
        original.model_dump_json()
    )

    assert restored == original
    assert isinstance(restored.structural_facts[0], CallStructuralFact)


def test_structural_fact_identity_and_sort_key_are_stable() -> None:
    # Given: the same semantic call built from a differently ordered mapping.
    original = structural_facts()[0]
    replayed = CallStructuralFact.model_validate(
        {
            "span": {
                "line_end": 12,
                "file": "src/app.py",
                "line_start": 12,
            },
            "callee": "qdrant_client.QdrantClient",
            "caller": "app.main",
            "identity_namespace": "ua_call_hint",
            "fact_type": "call",
        }
    )

    # When/Then: identity ignores input key order and survives replay.
    assert replayed.stable_id == original.stable_id
    assert replayed.sort_key == original.sort_key
    assert original.stable_id.startswith("ua_call_hint:sha256:")

    changed = original.model_copy(update={"callee": "chromadb.HttpClient"})
    assert changed.stable_id != original.stable_id


def test_structural_fact_models_are_frozen() -> None:
    # Given: one validated structural call fact.
    fact = structural_facts()[0]

    # When/Then: mutation is rejected at the model boundary.
    with pytest.raises(ValidationError, match="frozen"):
        fact.identity_namespace = "changed"


def test_project_scan_result_defaults_structural_facts_to_empty() -> None:
    # Given/When: an existing caller constructs the additive scan contract.
    result = ProjectScanResult()

    # Then: old payloads remain valid without a compatibility shim.
    assert result.structural_facts == []
    assert ProviderScanResult().structural_facts == []
