from __future__ import annotations

from importlib.util import find_spec

from systograph.core.models.evidence_kind import AssessmentEvidenceKind
from systograph.core.models.structural_fact import (
    CallStructuralFact,
    FactoryInferenceStep,
    FactoryInferenceStructuralFact,
    ImportStructuralFact,
    SourceSpan,
    StructuralFact,
    SymbolStructuralFact,
)
from systograph.core.models.system_map import ComponentInstance, Evidence
from systograph.core.services.component_residence_index import (
    ComponentResidenceIndex,
)
from systograph.core.services.edge_relationship_catalog import (
    CallKind,
    EdgeRelationshipCatalog,
    SignalKind,
    parse_edge_relationship_catalog,
)
from systograph.core.services.ua_edge_derivation_models import (
    UaEdgeDerivationResult,
)
from systograph.core.services.ua_edge_derivation_service import (
    UaEdgeDerivationService,
)
from systograph.core.services.ua_edge_resolution import EdgeResolutionContext
from systograph.core.services.ua_edge_signal_deriver import UaEdgeSignalDeriver


def test_ua_edge_derivation_service_module_exists() -> None:
    assert (
        find_spec("systograph.core.services.ua_edge_derivation_service")
        is not None
    )


def component(
    component_id: str,
    kind: str,
    *evidence_ids: str,
) -> ComponentInstance:
    return ComponentInstance(
        id=component_id,
        slot=kind,
        kind=kind,
        name=component_id,
        evidence_ids=list(evidence_ids),
    )


def evidence(
    evidence_id: str,
    *,
    file: str,
    line: int | None,
    rule_id: str,
    hint: AssessmentEvidenceKind,
    path: str | None = None,
) -> Evidence:
    return Evidence(
        id=evidence_id,
        kind="call_hint",
        file=file,
        path=path,
        rule_id=rule_id,
        line_start=line,
        line_end=line,
        evidence_kind_hint=hint,
    )


def symbol(
    name: str,
    file: str,
    start: int,
    end: int,
) -> SymbolStructuralFact:
    return SymbolStructuralFact(
        identity_namespace="ua_symbol",
        symbol=name,
        symbol_kind="function",
        span=SourceSpan(file=file, line_start=start, line_end=end),
    )


def class_symbol(
    name: str,
    file: str,
    start: int,
    end: int,
) -> SymbolStructuralFact:
    return SymbolStructuralFact(
        identity_namespace="ua_symbol",
        symbol=name,
        symbol_kind="class",
        span=SourceSpan(file=file, line_start=start, line_end=end),
    )


def internal_import(
    source_file: str,
    target_file: str,
) -> ImportStructuralFact:
    return ImportStructuralFact(
        identity_namespace="ua_import",
        import_scope="internal",
        module=target_file,
        span=SourceSpan(file=source_file),
    )


def call(
    caller: str,
    callee: str,
    file: str,
    line: int,
) -> CallStructuralFact:
    return CallStructuralFact(
        identity_namespace="ua_call_hint",
        caller=caller,
        callee=callee,
        span=SourceSpan(file=file, line_start=line, line_end=line),
    )


def derive(
    components: tuple[ComponentInstance, ...],
    evidence_items: tuple[Evidence, ...],
    structural_facts: tuple[StructuralFact, ...],
    *,
    service: UaEdgeDerivationService | None = None,
) -> UaEdgeDerivationResult:
    return (service or UaEdgeDerivationService()).derive(
        components=components,
        evidence=evidence_items,
        structural_facts=structural_facts,
    )


def relationship_catalog(
    *,
    signal_kind: SignalKind,
    call_kind: CallKind,
    symbols: list[str],
) -> EdgeRelationshipCatalog:
    return parse_edge_relationship_catalog(
        {
            "relationships": [
                {
                    "from_kinds": ["api_route"],
                    "to_kinds": ["retriever"],
                    "signal_kinds": [signal_kind],
                    "call_kinds": [call_kind],
                    "callee_symbols": symbols,
                    "producer_rule_ids": [
                        "ua_call_hint_static"
                        if signal_kind == "call"
                        else "ua_import_internal"
                    ],
                    "relationship": "context_flow",
                }
            ]
        }
    )


def test_l1_call_emits_one_observed_edge_with_only_direct_evidence() -> None:
    call_evidence = evidence(
        "evidence:call:qdrant",
        file="src/retriever.py",
        line=6,
        rule_id="code_pattern_vector_store_qdrant",
        hint="direct",
    )
    result = derive(
        (
            component(
                "component:retriever",
                "retriever",
                "evidence:retriever",
            ),
            component(
                "component:vector",
                "vector_db",
                call_evidence.id,
            ),
        ),
        (
            evidence(
                "evidence:retriever",
                file="src/retriever.py",
                line=3,
                rule_id="code_pattern_retriever_as_retriever",
                hint="direct",
            ),
            call_evidence,
        ),
        (
            symbol("retrieve", "src/retriever.py", 1, 10),
            call(
                "retrieve",
                "qdrant_client.QdrantClient",
                "src/retriever.py",
                6,
            ),
        ),
    )

    assert len(result.edges) == 1
    edge = result.edges[0]
    assert (edge.source, edge.target, edge.relationship) == (
        "component:retriever",
        "component:vector",
        "queries_vector_store",
    )
    assert edge.status == "observed"
    assert edge.undetermined_reason is None
    assert edge.evidence_ids == [call_evidence.id]
    assert result.stats.l1_emitted == 1


def test_l1_resolves_an_internal_callee_symbol_across_files() -> None:
    # Contract change (import-scoped name resolution): a bare callee only
    # resolves into another file when the caller's file demonstrably
    # imports it, so this fixture now carries the ImportStructuralFact.
    result = derive(
        (
            component("component:api", "api_route", "evidence:api"),
            component(
                "component:retriever",
                "retriever",
                "evidence:retriever",
            ),
        ),
        (
            evidence(
                "evidence:api",
                file="src/app.py",
                line=3,
                rule_id="code_pattern_route_fastapi",
                hint="direct",
            ),
            evidence(
                "evidence:retriever",
                file="src/retriever.py",
                line=2,
                rule_id="code_pattern_retriever_as_retriever",
                hint="direct",
            ),
            evidence(
                "evidence:call:retrieve",
                file="src/app.py",
                line=5,
                rule_id="ua_call_hint_static",
                hint="direct",
            ),
        ),
        (
            symbol("serve", "src/app.py", 1, 8),
            symbol("retrieve", "src/retriever.py", 1, 5),
            call("serve", "retrieve", "src/app.py", 5),
            internal_import("src/app.py", "src/retriever.py"),
        ),
    )

    assert [
        (edge.source, edge.target, edge.relationship) for edge in result.edges
    ] == [("component:api", "component:retriever", "context_flow")]


def test_unresolved_callee_is_counted_and_never_guessed() -> None:
    result = derive(
        (component("component:api", "api_route", "evidence:api"),),
        (
            evidence(
                "evidence:api",
                file="src/app.py",
                line=2,
                rule_id="code_pattern_route_fastapi",
                hint="direct",
            ),
            evidence(
                "evidence:call:unknown",
                file="src/app.py",
                line=4,
                rule_id="ua_call_hint_static",
                hint="direct",
            ),
        ),
        (
            symbol("serve", "src/app.py", 1, 8),
            call("serve", "unknown", "src/app.py", 4),
        ),
    )

    assert result.edges == ()
    assert result.stats.dropped_unresolved_target == 1
    assert any("unresolved target=1" in warning for warning in result.warnings)


def test_ambiguous_source_is_discarded_before_catalog_lookup() -> None:
    # Given: two components share the smallest enclosing span while the
    # catalog recognizes only one of the candidate source kinds.
    call_evidence = evidence(
        "evidence:call:qdrant",
        file="src/pipeline.py",
        line=6,
        rule_id="code_pattern_vector_store_qdrant",
        hint="direct",
    )
    result = derive(
        (
            component(
                "component:retriever",
                "retriever",
                "evidence:retriever",
            ),
            component("component:api", "api_route", "evidence:api"),
            component("component:vector", "vector_db", call_evidence.id),
        ),
        (
            evidence(
                "evidence:retriever",
                file="src/pipeline.py",
                line=3,
                rule_id="code_pattern_retriever_as_retriever",
                hint="direct",
            ),
            evidence(
                "evidence:api",
                file="src/pipeline.py",
                line=4,
                rule_id="code_pattern_route_fastapi",
                hint="direct",
            ),
            call_evidence,
        ),
        (
            symbol("build_pipeline", "src/pipeline.py", 1, 10),
            call(
                "build_pipeline",
                "qdrant_client.QdrantClient",
                "src/pipeline.py",
                6,
            ),
        ),
    )

    # When/Then: the catalog never picks the endpoint — no edge, counted.
    assert result.edges == ()
    assert result.stats.ambiguous_calls == 1
    assert any("ambiguous calls=1" in warning for warning in result.warnings)


def test_self_loop_is_counted_and_not_emitted() -> None:
    result = derive(
        (
            component(
                "component:workflow",
                "workflow_node",
                "evidence:workflow",
            ),
        ),
        (
            evidence(
                "evidence:workflow",
                file="src/flow.py",
                line=3,
                rule_id="workflow_node",
                hint="direct",
            ),
            evidence(
                "evidence:call:transition",
                file="src/flow.py",
                line=5,
                rule_id="ua_call_hint_static",
                hint="direct",
            ),
        ),
        (
            symbol("transition", "src/flow.py", 1, 8),
            call("transition", "transition", "src/flow.py", 5),
        ),
    )

    assert result.edges == ()
    assert result.stats.dropped_self_loop == 1


def test_l2_internal_import_is_undetermined_and_indirect() -> None:
    result = derive(
        (
            component("component:api", "api_route", "evidence:api"),
            component(
                "component:retriever",
                "retriever",
                "evidence:retriever",
            ),
        ),
        (
            evidence(
                "evidence:api",
                file="src/app.py",
                line=None,
                rule_id="code_pattern_route_fastapi",
                hint="indirect",
            ),
            evidence(
                "evidence:retriever",
                file="src/retriever.py",
                line=None,
                rule_id="code_pattern_retriever_as_retriever",
                hint="indirect",
            ),
            evidence(
                "evidence:import",
                file="src/app.py",
                line=None,
                rule_id="ua_import_internal",
                hint="indirect",
                path="imports[src/retriever.py]",
            ),
        ),
        (
            ImportStructuralFact(
                identity_namespace="ua_import",
                import_scope="internal",
                module="src/retriever.py",
                span=SourceSpan(file="src/app.py"),
            ),
        ),
    )

    assert len(result.edges) == 1
    edge = result.edges[0]
    assert edge.status == "undetermined"
    assert edge.undetermined_reason == "import_only_no_call_site"
    assert edge.evidence_ids == ["evidence:import"]
    assert result.stats.l2_emitted == 1


def test_ambiguous_import_does_not_expand_to_n_by_m_edges() -> None:
    result = derive(
        (
            component("component:api", "api_route", "evidence:api"),
            component(
                "component:workflow",
                "workflow_node",
                "evidence:workflow",
            ),
            component(
                "component:retriever",
                "retriever",
                "evidence:retriever",
            ),
        ),
        (
            evidence(
                "evidence:api",
                file="src/app.py",
                line=None,
                rule_id="route",
                hint="indirect",
            ),
            evidence(
                "evidence:workflow",
                file="src/app.py",
                line=None,
                rule_id="workflow",
                hint="indirect",
            ),
            evidence(
                "evidence:retriever",
                file="src/retriever.py",
                line=None,
                rule_id="retriever",
                hint="indirect",
            ),
            evidence(
                "evidence:import",
                file="src/app.py",
                line=None,
                rule_id="ua_import_internal",
                hint="indirect",
                path="imports[src/retriever.py]",
            ),
        ),
        (
            ImportStructuralFact(
                identity_namespace="ua_import",
                import_scope="internal",
                module="src/retriever.py",
                span=SourceSpan(file="src/app.py"),
            ),
        ),
    )

    assert result.edges == ()
    assert result.stats.ambiguous_imports == 1
    assert any("ambiguous imports=1" in warning for warning in result.warnings)


def test_factory_inference_is_undetermined_with_its_own_reason() -> None:
    factory_evidence = evidence(
        "evidence:factory:qdrant",
        file="src/retriever.py",
        line=6,
        rule_id="code_pattern_vector_store_qdrant",
        hint="indirect",
    )
    result = derive(
        (
            component(
                "component:retriever",
                "retriever",
                "evidence:retriever",
            ),
            component(
                "component:vector",
                "vector_db",
                factory_evidence.id,
            ),
        ),
        (
            evidence(
                "evidence:retriever",
                file="src/retriever.py",
                line=3,
                rule_id="code_pattern_retriever_as_retriever",
                hint="direct",
            ),
            factory_evidence,
        ),
        (
            symbol("retrieve", "src/retriever.py", 1, 10),
            FactoryInferenceStructuralFact(
                identity_namespace="ast_factory_inference",
                caller="retrieve",
                factory="build_client",
                constructed_symbol="qdrant_client.QdrantClient",
                call_span=SourceSpan(
                    file="src/retriever.py",
                    line_start=6,
                    line_end=6,
                ),
                provenance=(
                    FactoryInferenceStep(
                        hop=0,
                        factory="build_client",
                        resolution="return_construction",
                        span=SourceSpan(
                            file="src/factory.py",
                            line_start=1,
                            line_end=3,
                        ),
                    ),
                ),
            ),
        ),
    )

    assert len(result.edges) == 1
    edge = result.edges[0]
    assert edge.status == "undetermined"
    assert edge.undetermined_reason == "factory_inference"
    assert edge.evidence_ids == [factory_evidence.id]


def test_missing_relationship_emits_a_recommended_next_check() -> None:
    call_evidence = evidence(
        "evidence:call:unknown-relation",
        file="src/app.py",
        line=5,
        rule_id="ua_call_hint_static",
        hint="direct",
    )
    result = derive(
        (
            component("component:api", "api_route", "evidence:api"),
            component("component:vector", "vector_db", call_evidence.id),
        ),
        (
            evidence(
                "evidence:api",
                file="src/app.py",
                line=2,
                rule_id="code_pattern_route_fastapi",
                hint="direct",
            ),
            call_evidence,
        ),
        (
            symbol("serve", "src/app.py", 1, 8),
            call("serve", "unknown_relation", "src/app.py", 5),
        ),
    )

    assert result.edges == ()
    assert result.stats.dropped_missing_relationship == 1
    assert len(result.recommended_next_checks) == 1
    assert result.recommended_next_checks[0].target_type == (
        "edge_relationship"
    )


def test_l1_wins_over_l2_without_absorbing_loser_evidence() -> None:
    result = derive(
        (
            component(
                "component:retriever",
                "retriever",
                "evidence:retriever",
            ),
            component(
                "component:vector",
                "vector_db",
                "evidence:vector",
            ),
        ),
        (
            evidence(
                "evidence:retriever",
                file="src/retriever.py",
                line=2,
                rule_id="code_pattern_retriever_as_retriever",
                hint="direct",
            ),
            evidence(
                "evidence:vector",
                file="src/store.py",
                line=2,
                rule_id="code_pattern_vector_store_qdrant",
                hint="direct",
            ),
            evidence(
                "evidence:call",
                file="src/retriever.py",
                line=4,
                rule_id="code_pattern_vector_store_qdrant",
                hint="direct",
            ),
            evidence(
                "evidence:import",
                file="src/retriever.py",
                line=None,
                rule_id="ua_import_internal",
                hint="indirect",
                path="imports[src/store.py]",
            ),
        ),
        (
            symbol("retrieve", "src/retriever.py", 1, 6),
            class_symbol("QdrantClient", "src/store.py", 1, 4),
            call(
                "retrieve",
                "QdrantClient",
                "src/retriever.py",
                4,
            ),
            internal_import("src/retriever.py", "src/store.py"),
        ),
    )

    assert len(result.edges) == 1
    edge = result.edges[0]
    assert edge.status == "observed"
    assert edge.evidence_ids == ["evidence:call"]
    assert result.stats.discarded_lower_tier == 1
    assert any("discarded lower-tier L2=1" in item for item in result.warnings)


def test_pgvector_mirror_pair_is_ambiguous_not_catalog_directed() -> None:
    # Given: retriever and vector_db are synthesized from the same query
    # evidence, so both directions are candidate pairs and only the
    # catalog's kind coverage could pick one.
    query_evidence = evidence(
        "evidence:pgvector-query",
        file="src/retrieval.py",
        line=15,
        rule_id="code_pattern_vector_store_pgvector_query",
        hint="direct",
    )

    # When
    result = derive(
        (
            component(
                "component:retriever",
                "retriever",
                query_evidence.id,
            ),
            component(
                "component:vector",
                "vector_db",
                query_evidence.id,
            ),
        ),
        (query_evidence,),
        (
            symbol("retrieve", "src/retrieval.py", 6, 19),
            call("retrieve", "conn.execute", "src/retrieval.py", 15),
        ),
    )

    # Then: edge direction is not the catalog's call — discard and count.
    assert result.edges == ()
    assert result.stats.ambiguous_calls == 1
    assert any("ambiguous calls=1" in warning for warning in result.warnings)


def test_source_cap_reports_dropped_l1_count_and_tier() -> None:
    # Given
    source = component("component:api", "api_route", "evidence:api")
    targets = (
        component("component:r1", "retriever", "evidence:r1"),
        component("component:r2", "retriever", "evidence:r2"),
    )
    evidence_items = (
        evidence(
            "evidence:api",
            file="src/app.py",
            line=2,
            rule_id="code_pattern_route_fastapi",
            hint="direct",
        ),
        evidence(
            "evidence:r1",
            file="src/r1.py",
            line=2,
            rule_id="code_pattern_retriever_as_retriever",
            hint="direct",
        ),
        evidence(
            "evidence:r2",
            file="src/r2.py",
            line=2,
            rule_id="code_pattern_retriever_as_retriever",
            hint="direct",
        ),
        evidence(
            "evidence:call:r1",
            file="src/app.py",
            line=5,
            rule_id="ua_call_hint_static",
            hint="direct",
        ),
        evidence(
            "evidence:call:r2",
            file="src/app.py",
            line=6,
            rule_id="ua_call_hint_static",
            hint="direct",
        ),
    )
    service = UaEdgeDerivationService(
        relationship_catalog=relationship_catalog(
            signal_kind="call",
            call_kind="function",
            symbols=["retrieve_one", "retrieve_two"],
        ),
        max_outgoing_edges=1,
    )

    # When
    result = derive(
        (source, *targets),
        evidence_items,
        (
            symbol("serve", "src/app.py", 1, 10),
            symbol("retrieve_one", "src/r1.py", 1, 4),
            symbol("retrieve_two", "src/r2.py", 1, 4),
            call("serve", "retrieve_one", "src/app.py", 5),
            call("serve", "retrieve_two", "src/app.py", 6),
            internal_import("src/app.py", "src/r1.py"),
            internal_import("src/app.py", "src/r2.py"),
        ),
        service=service,
    )

    # Then
    assert len(result.edges) == 1
    assert result.stats.source_cap_dropped_l1 == 1
    assert "UA edge derivation source cap dropped 1 L1" in result.warnings


def test_global_cap_reports_dropped_l1_count_and_tier() -> None:
    # Given
    evidence_items = (
        evidence(
            "evidence:api1",
            file="src/app1.py",
            line=2,
            rule_id="code_pattern_route_fastapi",
            hint="direct",
        ),
        evidence(
            "evidence:api2",
            file="src/app2.py",
            line=2,
            rule_id="code_pattern_route_fastapi",
            hint="direct",
        ),
        evidence(
            "evidence:r1",
            file="src/r1.py",
            line=2,
            rule_id="code_pattern_retriever_as_retriever",
            hint="direct",
        ),
        evidence(
            "evidence:r2",
            file="src/r2.py",
            line=2,
            rule_id="code_pattern_retriever_as_retriever",
            hint="direct",
        ),
        evidence(
            "evidence:call:r1",
            file="src/app1.py",
            line=5,
            rule_id="ua_call_hint_static",
            hint="direct",
        ),
        evidence(
            "evidence:call:r2",
            file="src/app2.py",
            line=5,
            rule_id="ua_call_hint_static",
            hint="direct",
        ),
    )
    service = UaEdgeDerivationService(
        relationship_catalog=relationship_catalog(
            signal_kind="call",
            call_kind="function",
            symbols=["retrieve_one", "retrieve_two"],
        ),
        max_edges=1,
    )

    # When
    result = derive(
        (
            component("component:api1", "api_route", "evidence:api1"),
            component("component:api2", "api_route", "evidence:api2"),
            component("component:r1", "retriever", "evidence:r1"),
            component("component:r2", "retriever", "evidence:r2"),
        ),
        evidence_items,
        (
            symbol("serve_one", "src/app1.py", 1, 8),
            symbol("serve_two", "src/app2.py", 1, 8),
            symbol("retrieve_one", "src/r1.py", 1, 4),
            symbol("retrieve_two", "src/r2.py", 1, 4),
            call("serve_one", "retrieve_one", "src/app1.py", 5),
            call("serve_two", "retrieve_two", "src/app2.py", 5),
            internal_import("src/app1.py", "src/r1.py"),
            internal_import("src/app2.py", "src/r2.py"),
        ),
        service=service,
    )

    # Then
    assert len(result.edges) == 1
    assert result.stats.global_cap_dropped_l1 == 1
    assert "UA edge derivation global cap dropped 1 L1" in result.warnings


def test_source_cap_reports_dropped_l2_count_and_tier() -> None:
    # Given
    evidence_items = (
        evidence(
            "evidence:api",
            file="src/app.py",
            line=None,
            rule_id="code_pattern_route_fastapi",
            hint="indirect",
        ),
        evidence(
            "evidence:r1",
            file="src/r1.py",
            line=None,
            rule_id="code_pattern_retriever_as_retriever",
            hint="indirect",
        ),
        evidence(
            "evidence:r2",
            file="src/r2.py",
            line=None,
            rule_id="code_pattern_retriever_as_retriever",
            hint="indirect",
        ),
        evidence(
            "evidence:import:r1",
            file="src/app.py",
            line=None,
            rule_id="ua_import_internal",
            hint="indirect",
            path="imports[src/r1.py]",
        ),
        evidence(
            "evidence:import:r2",
            file="src/app.py",
            line=None,
            rule_id="ua_import_internal",
            hint="indirect",
            path="imports[src/r2.py]",
        ),
    )
    service = UaEdgeDerivationService(
        relationship_catalog=relationship_catalog(
            signal_kind="import",
            call_kind="import",
            symbols=["internal_import"],
        ),
        max_outgoing_edges=1,
    )

    # When
    result = derive(
        (
            component("component:api", "api_route", "evidence:api"),
            component("component:r1", "retriever", "evidence:r1"),
            component("component:r2", "retriever", "evidence:r2"),
        ),
        evidence_items,
        (
            ImportStructuralFact(
                identity_namespace="ua_import",
                import_scope="internal",
                module="src/r1.py",
                span=SourceSpan(file="src/app.py"),
            ),
            ImportStructuralFact(
                identity_namespace="ua_import",
                import_scope="internal",
                module="src/r2.py",
                span=SourceSpan(file="src/app.py"),
            ),
        ),
        service=service,
    )

    # Then
    assert len(result.edges) == 1
    assert result.stats.source_cap_dropped_l2 == 1
    assert "UA edge derivation source cap dropped 1 L2" in result.warnings


def test_replay_is_stable_when_input_order_changes() -> None:
    components = (
        component("component:api", "api_route", "evidence:api"),
        component(
            "component:retriever",
            "retriever",
            "evidence:retriever",
        ),
    )
    evidence_items = (
        evidence(
            "evidence:api",
            file="src/app.py",
            line=2,
            rule_id="code_pattern_route_fastapi",
            hint="direct",
        ),
        evidence(
            "evidence:retriever",
            file="src/retriever.py",
            line=2,
            rule_id="code_pattern_retriever_as_retriever",
            hint="direct",
        ),
        evidence(
            "evidence:call",
            file="src/app.py",
            line=4,
            rule_id="ua_call_hint_static",
            hint="direct",
        ),
    )
    facts: tuple[StructuralFact, ...] = (
        symbol("serve", "src/app.py", 1, 6),
        symbol("retrieve", "src/retriever.py", 1, 6),
        call("serve", "retrieve", "src/app.py", 4),
        internal_import("src/app.py", "src/retriever.py"),
    )

    first = derive(components, evidence_items, facts)
    second = derive(
        tuple(reversed(components)),
        tuple(reversed(evidence_items)),
        tuple(reversed(facts)),
    )

    assert second.edges == first.edges
    assert second.stats == first.stats
    assert second.warnings == first.warnings


def build_deriver(
    components: tuple[ComponentInstance, ...],
    evidence_items: tuple[Evidence, ...],
    structural_facts: tuple[StructuralFact, ...],
    catalog: EdgeRelationshipCatalog,
) -> UaEdgeSignalDeriver:
    residence = ComponentResidenceIndex.build(
        components=components,
        evidence=evidence_items,
        structural_facts=structural_facts,
    )
    context = EdgeResolutionContext.build(
        components=components,
        evidence=evidence_items,
        residence=residence,
        structural_facts=structural_facts,
    )
    return UaEdgeSignalDeriver(
        components=components,
        context=context,
        catalog=catalog,
    )


def test_same_name_in_an_unimported_file_never_creates_a_cross_edge() -> None:
    # Regression for collision-driven recommended_next_checks pollution:
    # the old repo-wide name bag matched "search" in an unrelated file,
    # produced a wrong api_route->vector_db pair, and recorded a bogus
    # next check for it. Without an import fact the name path now stays
    # empty and no check is fabricated.
    result = derive(
        (
            component("component:api", "api_route", "evidence:api"),
            component("component:vector", "vector_db", "evidence:vector"),
        ),
        (
            evidence(
                "evidence:api",
                file="src/app.py",
                line=3,
                rule_id="code_pattern_route_fastapi",
                hint="direct",
            ),
            evidence(
                "evidence:vector",
                file="src/other.py",
                line=2,
                rule_id="code_pattern_vector_store_qdrant",
                hint="direct",
            ),
            evidence(
                "evidence:call:search",
                file="src/app.py",
                line=5,
                rule_id="ua_call_hint_static",
                hint="direct",
            ),
        ),
        (
            symbol("serve", "src/app.py", 1, 8),
            symbol("search", "src/other.py", 1, 5),
            call("serve", "search", "src/app.py", 5),
        ),
    )

    assert result.edges == ()
    assert result.stats.dropped_unresolved_target == 1
    assert result.stats.dropped_missing_relationship == 0
    assert result.recommended_next_checks == ()


def test_bare_name_resolves_only_into_the_imported_definition() -> None:
    # Two files define "retrieve"; only the imported one may win.
    result = derive(
        (
            component("component:api", "api_route", "evidence:api"),
            component("component:ra", "retriever", "evidence:ra"),
            component("component:rb", "retriever", "evidence:rb"),
        ),
        (
            evidence(
                "evidence:api",
                file="src/app.py",
                line=3,
                rule_id="code_pattern_route_fastapi",
                hint="direct",
            ),
            evidence(
                "evidence:ra",
                file="src/a.py",
                line=2,
                rule_id="code_pattern_retriever_as_retriever",
                hint="direct",
            ),
            evidence(
                "evidence:rb",
                file="src/b.py",
                line=2,
                rule_id="code_pattern_retriever_as_retriever",
                hint="direct",
            ),
            evidence(
                "evidence:call:retrieve",
                file="src/app.py",
                line=5,
                rule_id="ua_call_hint_static",
                hint="direct",
            ),
        ),
        (
            symbol("serve", "src/app.py", 1, 8),
            symbol("retrieve", "src/a.py", 1, 5),
            symbol("retrieve", "src/b.py", 1, 5),
            call("serve", "retrieve", "src/app.py", 5),
            internal_import("src/app.py", "src/b.py"),
        ),
    )

    assert [
        (edge.source, edge.target, edge.relationship) for edge in result.edges
    ] == [("component:api", "component:rb", "context_flow")]


def test_local_definition_wins_over_imported_same_name() -> None:
    result = derive(
        (
            component("component:api", "api_route", "evidence:api"),
            component("component:local", "retriever", "evidence:local"),
            component("component:remote", "retriever", "evidence:remote"),
        ),
        (
            evidence(
                "evidence:api",
                file="src/app.py",
                line=3,
                rule_id="code_pattern_route_fastapi",
                hint="direct",
            ),
            evidence(
                "evidence:local",
                file="src/app.py",
                line=11,
                rule_id="code_pattern_retriever_as_retriever",
                hint="direct",
            ),
            evidence(
                "evidence:remote",
                file="src/retriever.py",
                line=2,
                rule_id="code_pattern_retriever_as_retriever",
                hint="direct",
            ),
            evidence(
                "evidence:call:retrieve",
                file="src/app.py",
                line=5,
                rule_id="ua_call_hint_static",
                hint="direct",
            ),
        ),
        (
            symbol("serve", "src/app.py", 1, 8),
            symbol("retrieve", "src/app.py", 10, 15),
            symbol("retrieve", "src/retriever.py", 1, 5),
            call("serve", "retrieve", "src/app.py", 5),
            internal_import("src/app.py", "src/retriever.py"),
        ),
    )

    assert [(edge.source, edge.target) for edge in result.edges] == [
        ("component:api", "component:local")
    ]


def test_case_mismatch_never_matches_a_symbol() -> None:
    result = derive(
        (
            component("component:api", "api_route", "evidence:api"),
            component(
                "component:retriever",
                "retriever",
                "evidence:retriever",
            ),
        ),
        (
            evidence(
                "evidence:api",
                file="src/app.py",
                line=3,
                rule_id="code_pattern_route_fastapi",
                hint="direct",
            ),
            evidence(
                "evidence:retriever",
                file="src/search.py",
                line=3,
                rule_id="code_pattern_retriever_as_retriever",
                hint="direct",
            ),
            evidence(
                "evidence:call:search",
                file="src/app.py",
                line=5,
                rule_id="ua_call_hint_static",
                hint="direct",
            ),
        ),
        (
            symbol("serve", "src/app.py", 1, 8),
            class_symbol("Search", "src/search.py", 1, 5),
            call("serve", "search", "src/app.py", 5),
            internal_import("src/app.py", "src/search.py"),
        ),
    )

    assert result.edges == ()
    assert result.stats.dropped_unresolved_target == 1


def test_dotted_package_qualified_callee_resolves_via_import() -> None:
    # "pkg.mod.retrieve" must match pkg/mod.py through the dotted path
    # suffix {mod, pkg.mod}; matching the first segment against the file
    # stem alone would be too narrow.
    service = UaEdgeDerivationService(
        relationship_catalog=relationship_catalog(
            signal_kind="call",
            call_kind="method",
            symbols=["pkg.mod.retrieve"],
        ),
    )
    result = derive(
        (
            component("component:api", "api_route", "evidence:api"),
            component(
                "component:retriever",
                "retriever",
                "evidence:retriever",
            ),
        ),
        (
            evidence(
                "evidence:api",
                file="src/app.py",
                line=3,
                rule_id="code_pattern_route_fastapi",
                hint="direct",
            ),
            evidence(
                "evidence:retriever",
                file="pkg/mod.py",
                line=2,
                rule_id="code_pattern_retriever_as_retriever",
                hint="direct",
            ),
            evidence(
                "evidence:call:retrieve",
                file="src/app.py",
                line=5,
                rule_id="ua_call_hint_static",
                hint="direct",
            ),
        ),
        (
            symbol("serve", "src/app.py", 1, 8),
            symbol("retrieve", "pkg/mod.py", 1, 5),
            call("serve", "pkg.mod.retrieve", "src/app.py", 5),
            internal_import("src/app.py", "pkg/mod.py"),
        ),
        service=service,
    )

    assert [
        (edge.source, edge.target, edge.relationship) for edge in result.edges
    ] == [("component:api", "component:retriever", "context_flow")]


def test_two_imported_files_with_the_same_stem_are_ambiguous() -> None:
    components = (
        component("component:api", "api_route", "evidence:api"),
        component("component:m1", "retriever", "evidence:m1"),
        component("component:m2", "retriever", "evidence:m2"),
    )
    evidence_items = (
        evidence(
            "evidence:api",
            file="src/app.py",
            line=3,
            rule_id="code_pattern_route_fastapi",
            hint="direct",
        ),
        evidence(
            "evidence:m1",
            file="pkg/mod.py",
            line=2,
            rule_id="code_pattern_retriever_as_retriever",
            hint="direct",
        ),
        evidence(
            "evidence:m2",
            file="other/mod.py",
            line=2,
            rule_id="code_pattern_retriever_as_retriever",
            hint="direct",
        ),
        evidence(
            "evidence:call:retrieve",
            file="src/app.py",
            line=5,
            rule_id="ua_call_hint_static",
            hint="direct",
        ),
    )
    call_fact = call("serve", "mod.retrieve", "src/app.py", 5)
    structural_facts: tuple[StructuralFact, ...] = (
        symbol("serve", "src/app.py", 1, 8),
        symbol("retrieve", "pkg/mod.py", 1, 5),
        symbol("retrieve", "other/mod.py", 1, 5),
        call_fact,
        internal_import("src/app.py", "pkg/mod.py"),
        internal_import("src/app.py", "other/mod.py"),
    )
    deriver = build_deriver(
        components,
        evidence_items,
        structural_facts,
        relationship_catalog(
            signal_kind="call",
            call_kind="method",
            symbols=["mod.retrieve"],
        ),
    )

    deriver.derive_calls((call_fact,))
    outcome = deriver.outcome()

    assert outcome.candidates == ()
    assert outcome.counters["ambiguous_callee_names"] == 1
    assert outcome.counters["dropped_unresolved_target"] == 1


def test_ambiguous_name_path_does_not_veto_evidence_resolution() -> None:
    # Both imported files define "search" (ambiguous name path), but the
    # call-site evidence still attributes the target on its own.
    call_ev = evidence(
        "evidence:call:search",
        file="src/app.py",
        line=5,
        rule_id="ua_call_hint_static",
        hint="direct",
    )
    components = (
        component("component:api", "api_route", "evidence:api"),
        component("component:impl", "retriever", call_ev.id),
    )
    evidence_items = (
        evidence(
            "evidence:api",
            file="src/app.py",
            line=3,
            rule_id="code_pattern_route_fastapi",
            hint="direct",
        ),
        call_ev,
    )
    call_fact = call("serve", "search", "src/app.py", 5)
    structural_facts: tuple[StructuralFact, ...] = (
        symbol("serve", "src/app.py", 1, 8),
        symbol("search", "src/a.py", 1, 5),
        symbol("search", "src/b.py", 1, 5),
        call_fact,
        internal_import("src/app.py", "src/a.py"),
        internal_import("src/app.py", "src/b.py"),
    )
    deriver = build_deriver(
        components,
        evidence_items,
        structural_facts,
        relationship_catalog(
            signal_kind="call",
            call_kind="function",
            symbols=["search"],
        ),
    )

    deriver.derive_calls((call_fact,))
    outcome = deriver.outcome()

    assert outcome.counters["ambiguous_callee_names"] == 1
    assert [(item.source, item.target) for item in outcome.candidates] == [
        ("component:api", "component:impl")
    ]


def test_imported_class_construction_resolves() -> None:
    service = UaEdgeDerivationService(
        relationship_catalog=relationship_catalog(
            signal_kind="call",
            call_kind="constructor",
            symbols=["VectorClient"],
        ),
    )
    result = derive(
        (
            component("component:api", "api_route", "evidence:api"),
            component(
                "component:retriever",
                "retriever",
                "evidence:retriever",
            ),
        ),
        (
            evidence(
                "evidence:api",
                file="src/app.py",
                line=3,
                rule_id="code_pattern_route_fastapi",
                hint="direct",
            ),
            evidence(
                "evidence:retriever",
                file="src/models.py",
                line=3,
                rule_id="code_pattern_retriever_as_retriever",
                hint="direct",
            ),
            evidence(
                "evidence:call:construct",
                file="src/app.py",
                line=5,
                rule_id="ua_call_hint_static",
                hint="direct",
            ),
        ),
        (
            symbol("serve", "src/app.py", 1, 8),
            class_symbol("VectorClient", "src/models.py", 1, 6),
            call("serve", "VectorClient", "src/app.py", 5),
            internal_import("src/app.py", "src/models.py"),
        ),
        service=service,
    )

    assert [
        (edge.source, edge.target, edge.relationship) for edge in result.edges
    ] == [("component:api", "component:retriever", "context_flow")]


def test_factory_resolution_is_scoped_by_the_factory_definition_file() -> None:
    # The constructed symbol's defining file is imported by the FACTORY
    # file, not by the call-site file; caller-import scoping would fail
    # to resolve this edge.
    service = UaEdgeDerivationService(
        relationship_catalog=parse_edge_relationship_catalog(
            {
                "relationships": [
                    {
                        "from_kinds": ["retriever"],
                        "to_kinds": ["vector_db"],
                        "signal_kinds": ["factory_inference"],
                        "call_kinds": ["factory"],
                        "callee_symbols": ["VectorClient"],
                        "producer_rule_ids": ["factory_rule"],
                        "relationship": "queries_vector_store",
                    }
                ]
            }
        ),
    )
    result = derive(
        (
            component(
                "component:retriever",
                "retriever",
                "evidence:retriever",
            ),
            component("component:vector", "vector_db", "evidence:vector"),
        ),
        (
            evidence(
                "evidence:retriever",
                file="src/app.py",
                line=3,
                rule_id="code_pattern_retriever_as_retriever",
                hint="direct",
            ),
            evidence(
                "evidence:vector",
                file="src/models.py",
                line=3,
                rule_id="code_pattern_vector_store_qdrant",
                hint="direct",
            ),
            evidence(
                "evidence:factory",
                file="src/app.py",
                line=5,
                rule_id="factory_rule",
                hint="indirect",
            ),
        ),
        (
            symbol("serve", "src/app.py", 1, 8),
            class_symbol("VectorClient", "src/models.py", 1, 6),
            internal_import("src/factory.py", "src/models.py"),
            FactoryInferenceStructuralFact(
                identity_namespace="ast_factory_inference",
                caller="serve",
                factory="build_client",
                constructed_symbol="VectorClient",
                call_span=SourceSpan(
                    file="src/app.py",
                    line_start=5,
                    line_end=5,
                ),
                provenance=(
                    FactoryInferenceStep(
                        hop=0,
                        factory="build_client",
                        resolution="return_construction",
                        span=SourceSpan(
                            file="src/factory.py",
                            line_start=1,
                            line_end=3,
                        ),
                    ),
                ),
            ),
        ),
        service=service,
    )

    assert len(result.edges) == 1
    edge = result.edges[0]
    assert (edge.source, edge.target, edge.relationship) == (
        "component:retriever",
        "component:vector",
        "queries_vector_store",
    )
    assert edge.status == "undetermined"
    assert edge.undetermined_reason == "factory_inference"
