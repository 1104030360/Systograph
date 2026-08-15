from __future__ import annotations

from importlib.util import find_spec

from systograph.core.models.structural_fact import (
    SourceSpan,
    StructuralFact,
    SymbolStructuralFact,
)
from systograph.core.models.system_map import ComponentInstance, Evidence
from systograph.core.services.component_residence_index import (
    ComponentResidenceIndex,
    Residence,
)


def test_component_residence_index_module_exists() -> None:
    assert (
        find_spec("systograph.core.services.component_residence_index")
        is not None
    )


def test_component_residence_index_exposes_typed_contracts() -> None:
    assert Residence.__name__ == "Residence"
    assert ComponentResidenceIndex.__name__ == "ComponentResidenceIndex"


def component(
    component_id: str,
    evidence_id: str,
    kind: str = "retriever",
) -> ComponentInstance:
    return ComponentInstance(
        id=component_id,
        slot=kind,
        kind=kind,
        name=component_id,
        evidence_ids=[evidence_id],
    )


def evidence(
    evidence_id: str,
    file: str,
    line: int | None,
) -> Evidence:
    return Evidence(
        id=evidence_id,
        kind="component",
        file=file,
        line_start=line,
        line_end=line,
    )


def function_symbol(
    name: str,
    span: SourceSpan,
) -> SymbolStructuralFact:
    return SymbolStructuralFact(
        identity_namespace="ua_symbol",
        symbol=name,
        symbol_kind="function",
        span=span,
    )


def class_symbol(
    name: str,
    span: SourceSpan,
) -> SymbolStructuralFact:
    return SymbolStructuralFact(
        identity_namespace="ua_symbol",
        symbol=name,
        symbol_kind="class",
        span=span,
    )


def build_index(
    components: tuple[ComponentInstance, ...],
    evidence_items: tuple[Evidence, ...],
    structural_facts: tuple[StructuralFact, ...],
) -> ComponentResidenceIndex:
    return ComponentResidenceIndex.build(
        components=components,
        evidence=evidence_items,
        structural_facts=structural_facts,
    )


def test_single_component_resolves_from_its_smallest_function_span() -> None:
    given_span = SourceSpan(file="src/app.py", line_start=10, line_end=20)

    when_index = build_index(
        (component("component:retriever", "evidence:retriever"),),
        (evidence("evidence:retriever", "src/app.py", 15),),
        (function_symbol("retrieve", given_span),),
    )

    assert when_index.component_ids_at("src/app.py", 15) == frozenset(
        {"component:retriever"}
    )
    assert when_index.by_span[("src/app.py", 10, 20)] == (
        "component:retriever"
    )


def test_components_in_one_file_resolve_by_distinct_function_spans() -> None:
    when_index = build_index(
        (
            component("component:api", "evidence:api", "api_route"),
            component("component:retriever", "evidence:retriever"),
        ),
        (
            evidence("evidence:api", "src/app.py", 5),
            evidence("evidence:retriever", "src/app.py", 25),
        ),
        (
            function_symbol(
                "serve",
                SourceSpan(file="src/app.py", line_start=1, line_end=10),
            ),
            function_symbol(
                "retrieve",
                SourceSpan(file="src/app.py", line_start=20, line_end=30),
            ),
        ),
    )

    assert when_index.component_ids_at("src/app.py", 6) == frozenset(
        {"component:api"}
    )
    assert when_index.component_ids_at("src/app.py", 26) == frozenset(
        {"component:retriever"}
    )
    assert when_index.by_file["src/app.py"] == frozenset(
        {"component:api", "component:retriever"}
    )


def test_single_component_file_resolves_a_line_outside_every_span() -> None:
    # A file that hosts exactly one component has no attribution
    # ambiguity, so module-level code in it belongs to that component.
    # Without this, evidence anchored on an import line or a config file
    # gives the component no usable code address and every call in the
    # file drops as an unresolved source.
    when_index = build_index(
        (component("component:vector", "evidence:vector", "vector_db"),),
        (evidence("evidence:vector", "src/store.py", None),),
        (),
    )

    assert when_index.by_component["component:vector"] == frozenset(
        {Residence(file="src/store.py", span=None)}
    )
    assert when_index.component_ids_at("src/store.py", 1) == frozenset(
        {"component:vector"}
    )
    assert when_index.file_level_ambiguous("src/store.py") is False


def test_multi_component_file_refuses_the_module_level_fallback() -> None:
    # Two components in one file: which one owns a module-level line is
    # a guess, so the fallback yields nothing and reports the ambiguity
    # instead of picking a side.
    when_index = build_index(
        (
            component("component:api", "evidence:api", "api_route"),
            component("component:vector", "evidence:vector", "vector_db"),
        ),
        (
            evidence("evidence:api", "src/store.py", None),
            evidence("evidence:vector", "src/store.py", None),
        ),
        (),
    )

    assert when_index.component_ids_at("src/store.py", 1) == frozenset()
    assert when_index.file_level_ambiguous("src/store.py") is True


def test_span_attribution_still_wins_over_the_file_fallback() -> None:
    # The fallback only covers lines no component-bearing span contains.
    when_index = build_index(
        (
            component("component:api", "evidence:api", "api_route"),
            component("component:retriever", "evidence:retriever"),
        ),
        (
            evidence("evidence:api", "src/app.py", 5),
            evidence("evidence:retriever", "src/app.py", 25),
        ),
        (
            function_symbol(
                "serve",
                SourceSpan(file="src/app.py", line_start=1, line_end=10),
            ),
            function_symbol(
                "retrieve",
                SourceSpan(file="src/app.py", line_start=20, line_end=30),
            ),
        ),
    )

    assert when_index.component_ids_at("src/app.py", 6) == frozenset(
        {"component:api"}
    )
    # Line 15 sits between both spans: the file has two components, so
    # the fallback declines rather than guessing.
    assert when_index.component_ids_at("src/app.py", 15) == frozenset()


def test_nested_function_uses_the_innermost_enclosing_span() -> None:
    when_index = build_index(
        (component("component:inner", "evidence:inner"),),
        (evidence("evidence:inner", "src/app.py", 8),),
        (
            function_symbol(
                "outer",
                SourceSpan(file="src/app.py", line_start=1, line_end=20),
            ),
            function_symbol(
                "inner",
                SourceSpan(file="src/app.py", line_start=5, line_end=10),
            ),
        ),
    )

    assert when_index.component_ids_at("src/app.py", 8) == frozenset(
        {"component:inner"}
    )


def test_symbol_lookup_is_scoped_to_a_single_file() -> None:
    # Two unrelated files define the same function name; the per-file
    # index never lets one file's definition answer for the other.
    when_index = build_index(
        (
            component("component:a", "evidence:a"),
            component("component:b", "evidence:b", "vector_db"),
        ),
        (
            evidence("evidence:a", "src/a.py", 2),
            evidence("evidence:b", "src/b.py", 2),
        ),
        (
            function_symbol(
                "search",
                SourceSpan(file="src/a.py", line_start=1, line_end=5),
            ),
            function_symbol(
                "search",
                SourceSpan(file="src/b.py", line_start=1, line_end=5),
            ),
        ),
    )

    assert when_index.symbol_spans("src/a.py", "search") == (
        ("src/a.py", 1, 5),
    )
    assert when_index.component_ids_for_symbol_in_file(
        "src/a.py", "search"
    ) == frozenset({"component:a"})
    assert when_index.component_ids_for_symbol_in_file(
        "src/b.py", "search"
    ) == frozenset({"component:b"})


def test_symbol_lookup_is_case_sensitive() -> None:
    when_index = build_index(
        (component("component:search", "evidence:search"),),
        (evidence("evidence:search", "src/search.py", 2),),
        (
            class_symbol(
                "Search",
                SourceSpan(file="src/search.py", line_start=1, line_end=5),
            ),
        ),
    )

    assert when_index.symbol_spans("src/search.py", "search") == ()
    assert (
        when_index.component_ids_for_symbol_in_file("src/search.py", "search")
        == frozenset()
    )
    assert when_index.symbol_spans("src/search.py", "Search") == (
        ("src/search.py", 1, 5),
    )


def test_symbol_lookup_does_not_strip_dotted_segments() -> None:
    # The old index reduced "pkg.retrieve" to its last segment; the new
    # index matches only the exact recorded symbol name.
    when_index = build_index(
        (component("component:retriever", "evidence:retriever"),),
        (evidence("evidence:retriever", "src/retriever.py", 2),),
        (
            function_symbol(
                "retrieve",
                SourceSpan(file="src/retriever.py", line_start=1, line_end=5),
            ),
        ),
    )

    assert when_index.symbol_spans("src/retriever.py", "pkg.retrieve") == ()


def test_class_symbol_anchors_component_residence_and_lookup() -> None:
    # A component whose evidence sits in a class body (outside any
    # function) resolves through the class span, so an imported ClassA()
    # construction can attribute to it.
    when_index = build_index(
        (component("component:vector", "evidence:vector", "vector_db"),),
        (evidence("evidence:vector", "src/models.py", 3),),
        (
            class_symbol(
                "VectorClient",
                SourceSpan(file="src/models.py", line_start=1, line_end=6),
            ),
        ),
    )

    assert when_index.by_span[("src/models.py", 1, 6)] == "component:vector"
    assert when_index.component_ids_for_symbol_in_file(
        "src/models.py", "VectorClient"
    ) == frozenset({"component:vector"})


def test_export_symbols_are_not_indexed() -> None:
    when_index = build_index(
        (component("component:a", "evidence:a"),),
        (evidence("evidence:a", "src/a.py", 2),),
        (
            SymbolStructuralFact(
                identity_namespace="ua_symbol",
                symbol="search",
                symbol_kind="export",
                span=SourceSpan(file="src/a.py", line_start=1, line_end=5),
            ),
        ),
    )

    assert when_index.symbol_spans("src/a.py", "search") == ()


def test_shared_span_is_explicitly_ambiguous_instead_of_guessing() -> None:
    given_span = SourceSpan(file="src/app.py", line_start=5, line_end=10)

    when_index = build_index(
        (
            component("component:retriever", "evidence:retriever"),
            component("component:vector", "evidence:vector", "vector_db"),
        ),
        (
            evidence("evidence:retriever", "src/app.py", 8),
            evidence("evidence:vector", "src/app.py", 8),
        ),
        (function_symbol("retrieve", given_span),),
    )

    assert when_index.component_ids_at("src/app.py", 8) == frozenset(
        {"component:retriever", "component:vector"}
    )
    assert when_index.ambiguous_spans[("src/app.py", 5, 10)] == frozenset(
        {"component:retriever", "component:vector"}
    )
