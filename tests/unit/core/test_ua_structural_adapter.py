from __future__ import annotations

from collections.abc import Mapping

from pydantic import JsonValue

from systograph.core.models.scan import ProviderScanResult
from systograph.core.models.structural_fact import (
    CallStructuralFact,
    ImportStructuralFact,
    SourceSpan,
    SymbolStructuralFact,
)
from systograph.core.models.ua_analysis import (
    UaAnalysisResult,
    UaAnalysisStats,
    UaCallRow,
    UaEndpointRow,
    UaImportRow,
    UaResourceRow,
    UaStructuralResult,
    UaSymbolRow,
    UaWarning,
)
from systograph.core.services.component_bridge_registry import (
    ComponentBridgeDecisionKind,
    ComponentBridgeRegistry,
)
from systograph.core.services.ua_structural_adapter import (
    UaStructuralAdapter,
)


def empty_structural_result() -> UaStructuralResult:
    return UaStructuralResult(
        imports=(),
        symbols=(),
        calls=(),
        resources=(),
        endpoints=(),
    )


def analysis_result() -> UaAnalysisResult:
    return UaAnalysisResult(
        schema_version="systograph-ua-result/v1",
        status="completed",
        structural=empty_structural_result(),
        semantic=None,
        warnings=(),
        stats=UaAnalysisStats(
            filesScanned=1,
            filesWithImports=0,
            totalEdges=0,
            totalBatches=1,
            algorithm="count-fallback",
            filesAnalyzed=1,
            batchCompletion=(),
        ),
        extra={},
    )


def project(structural: UaStructuralResult) -> ProviderScanResult:
    given_result = analysis_result().model_copy(
        update={"structural": structural}
    )
    return UaStructuralAdapter().adapt(given_result)


def projection_json(extra: Mapping[str, JsonValue]) -> str:
    given_result = analysis_result().model_copy(update={"extra": dict(extra)})
    return UaStructuralAdapter().adapt(given_result).model_dump_json()


def test_every_regular_fact_has_one_exact_four_tuple_evidence_join() -> None:
    given_structural = UaStructuralResult(
        imports=(
            UaImportRow(
                source_file="src/app.py", target_file="src/retriever.py"
            ),
        ),
        symbols=(
            UaSymbolRow(
                file="src/app.py",
                line_start=4,
                line_end=10,
                name="main",
                kind="function",
            ),
        ),
        calls=(
            UaCallRow(
                file="src/app.py",
                caller="main",
                callee="qdrant_client.QdrantClient",
                line_number=7,
            ),
        ),
        resources=(
            UaResourceRow(
                file="docker-compose.yml",
                line_start=2,
                line_end=8,
                name="api",
                kind="service",
            ),
        ),
        endpoints=(
            UaEndpointRow(
                file="src/api.py",
                line_start=11,
                line_end=14,
                method="GET",
                path="/health",
            ),
        ),
    )

    when_projection = project(given_structural)

    then_match_counts = tuple(
        sum(
            evidence.file == fact.file
            and evidence.path == fact.path
            and evidence.kind == fact.kind
            and evidence.rule_id == fact.rule_id
            for evidence in when_projection.evidence
        )
        for fact in when_projection.facts
    )
    assert then_match_counts == (1,) * len(when_projection.facts)


def test_true_call_site_uses_catalog_mirror_and_explicit_direct_hint() -> None:
    given_call = UaCallRow(
        file="src/app.py",
        caller="main",
        callee="qdrant_client.QdrantClient",
        line_number=12,
    )
    given_structural = empty_structural_result().model_copy(
        update={"calls": (given_call,)}
    )

    when_projection = project(given_structural)

    assert when_projection.facts[0].rule_id == (
        "ua_call_hint_vector_store_qdrant"
    )
    assert when_projection.facts[0].kind == "vector_store_client"
    assert when_projection.evidence[0].evidence_kind_hint == "direct"
    assert (
        CallStructuralFact(
            identity_namespace="ua_call_hint",
            caller="main",
            callee="qdrant_client.QdrantClient",
            span=SourceSpan(file="src/app.py", line_start=12, line_end=12),
        )
        in when_projection.structural_facts
    )


def test_import_stays_indirect_and_never_lights_a_component() -> None:
    given_import = UaImportRow(
        source_file="src/app.py",
        target_file="src/router.py",
    )
    given_structural = empty_structural_result().model_copy(
        update={"imports": (given_import,)}
    )

    when_projection = project(given_structural)
    when_decision = ComponentBridgeRegistry().match(
        when_projection.facts[0],
        evidence_ids=(when_projection.evidence[0].id,),
    )

    assert when_projection.evidence[0].line_start is None
    assert when_projection.evidence[0].evidence_kind_hint == "indirect"
    assert when_decision.kind is ComponentBridgeDecisionKind.NO_MATCH
    assert (
        ImportStructuralFact(
            identity_namespace="ua_import",
            import_scope="internal",
            module="src/router.py",
            span=SourceSpan(file="src/app.py"),
        )
        in when_projection.structural_facts
    )


def test_symbol_projection_keeps_a_traceable_typed_span() -> None:
    given_symbol = UaSymbolRow(
        file="src/app.py",
        line_start=3,
        line_end=9,
        name="build_app",
        kind="function",
    )
    given_structural = empty_structural_result().model_copy(
        update={"symbols": (given_symbol,)}
    )

    when_projection = project(given_structural)

    assert (
        SymbolStructuralFact(
            identity_namespace="ua_symbol",
            symbol="build_app",
            symbol_kind="function",
            span=SourceSpan(file="src/app.py", line_start=3, line_end=9),
        )
        in when_projection.structural_facts
    )
    assert when_projection.evidence[0].evidence_kind_hint == "direct"


def test_endpoint_without_span_is_explicitly_indirect() -> None:
    given_endpoint = UaEndpointRow(file="src/api.py", path="/health")
    given_structural = empty_structural_result().model_copy(
        update={"endpoints": (given_endpoint,)}
    )

    when_projection = project(given_structural)

    assert when_projection.evidence[0].evidence_kind_hint == "indirect"


def test_evidence_ids_are_stable_and_content_addressed() -> None:
    given_call = UaCallRow(
        file="src/app.py",
        caller="main",
        callee="build_app",
        line_number=12,
    )
    given_structural = empty_structural_result().model_copy(
        update={"calls": (given_call,)}
    )
    given_changed = empty_structural_result().model_copy(
        update={"calls": (given_call.model_copy(update={"line_number": 13}),)}
    )

    when_first = project(given_structural)
    when_replayed = project(given_structural)
    when_changed = project(given_changed)

    assert when_first.evidence[0].id == when_replayed.evidence[0].id
    assert when_first.evidence[0].id != when_changed.evidence[0].id


def test_warnings_and_file_skips_become_ua_structural_parse_issues() -> None:
    given_result = analysis_result().model_copy(
        update={
            "warnings": (
                UaWarning(stage="extract-structure", message="batch warning"),
                UaWarning(stage="filesSkipped", message="src/missing.py"),
            )
        }
    )

    when_projection = UaStructuralAdapter().adapt(given_result)

    assert len(when_projection.issues) == 2
    assert {issue.scan_stage for issue in when_projection.issues} == {
        "ua_structural_scan"
    }
    assert {issue.message for issue in when_projection.issues} == {
        "extract-structure: batch warning",
        "filesSkipped: src/missing.py",
    }


def test_adapter_does_not_output_plane_id() -> None:
    when_payload = projection_json({"plane_id": "control"})

    assert "plane_id" not in when_payload


def test_adapter_does_not_output_reference_node_id() -> None:
    when_payload = projection_json({"reference_node_id": "dense_retriever"})

    assert "reference_node_id" not in when_payload
    assert "dense_retriever" not in when_payload


def test_adapter_does_not_output_profile_five_state_words() -> None:
    given_states = (
        "detected",
        "partial",
        "missing",
        "not_applicable",
        "undetermined",
    )
    when_payload = projection_json({"profile_states": list(given_states)})

    assert all(state not in when_payload for state in given_states)


def test_adapter_does_not_output_confidence() -> None:
    when_payload = projection_json({"confidence": 0.99})

    assert "confidence" not in when_payload


def test_adapter_does_not_output_runtime_conclusion() -> None:
    when_payload = projection_json(
        {"runtime_verified": True, "runtime_conclusion": "executed"}
    )

    assert "runtime_verified" not in when_payload
    assert "runtime_conclusion" not in when_payload
    assert "executed" not in when_payload


def test_adapter_does_not_project_semantic_or_extra_containers() -> None:
    when_payload = projection_json({"opaque": "ignored"})

    assert "semantic" not in when_payload
    assert "extra" not in when_payload
    assert "opaque" not in when_payload
