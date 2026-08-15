from __future__ import annotations

from collections.abc import Sequence
from typing import Final, assert_never

from systograph.core.models.structural_fact import (
    CallStructuralFact,
    FactoryInferenceStructuralFact,
    ImportStructuralFact,
    StructuralFact,
    SymbolStructuralFact,
)
from systograph.core.models.system_map import ComponentInstance, Evidence
from systograph.core.services.component_residence_index import (
    ComponentResidenceIndex,
)
from systograph.core.services.edge_relationship_catalog import (
    EdgeRelationshipCatalog,
)
from systograph.core.services.rule_catalog_loader import RuleCatalogLoader
from systograph.core.services.ua_edge_derivation_models import (
    UaEdgeDerivationResult,
    UaEdgeDerivationStats,
)
from systograph.core.services.ua_edge_merge import (
    canonical_edges,
    merge_and_cap_edges,
)
from systograph.core.services.ua_edge_resolution import EdgeResolutionContext
from systograph.core.services.ua_edge_signal_deriver import UaEdgeSignalDeriver

MAX_OUTGOING_EDGES: Final = 50
MAX_GRAPH_EDGES: Final = 2_000


class UaEdgeDerivationService:
    def __init__(
        self,
        *,
        relationship_catalog: EdgeRelationshipCatalog | None = None,
        max_outgoing_edges: int = MAX_OUTGOING_EDGES,
        max_edges: int = MAX_GRAPH_EDGES,
    ) -> None:
        if max_outgoing_edges < 1 or max_edges < 1:
            raise ValueError("edge caps must be positive")
        self._catalog = relationship_catalog or (
            RuleCatalogLoader().load_default_edge_relationship_rules()
        )
        self._max_outgoing_edges = max_outgoing_edges
        self._max_edges = max_edges

    def derive(
        self,
        *,
        components: Sequence[ComponentInstance],
        evidence: Sequence[Evidence],
        structural_facts: Sequence[StructuralFact],
    ) -> UaEdgeDerivationResult:
        residence = ComponentResidenceIndex.build(
            components=components,
            evidence=evidence,
            structural_facts=structural_facts,
        )
        context = EdgeResolutionContext.build(
            components=components,
            evidence=evidence,
            residence=residence,
            structural_facts=structural_facts,
        )
        calls: list[CallStructuralFact] = []
        imports: list[ImportStructuralFact] = []
        factories: list[FactoryInferenceStructuralFact] = []
        for fact in structural_facts:
            match fact:
                case CallStructuralFact():
                    calls.append(fact)
                case ImportStructuralFact():
                    imports.append(fact)
                case FactoryInferenceStructuralFact():
                    factories.append(fact)
                case SymbolStructuralFact():
                    continue
                case unreachable:
                    assert_never(unreachable)
        deriver = UaEdgeSignalDeriver(
            components=components,
            context=context,
            catalog=self._catalog,
        )
        deriver.derive_calls(calls)
        deriver.derive_factories(factories)
        deriver.derive_imports(imports)
        signal = deriver.outcome()
        merged = merge_and_cap_edges(
            signal.candidates,
            max_outgoing_edges=self._max_outgoing_edges,
            max_edges=self._max_edges,
        )
        stats = UaEdgeDerivationStats(
            calls_seen=signal.counters["calls_seen"],
            imports_seen=signal.counters["imports_seen"],
            factories_seen=signal.counters["factories_seen"],
            ignored_external_imports=signal.counters[
                "ignored_external_imports"
            ],
            l1_emitted=sum(item.tier == "L1" for item in merged.candidates),
            l2_emitted=sum(item.tier == "L2" for item in merged.candidates),
            missing_component_evidence_ids=len(residence.missing_evidence_ids),
            dropped_unresolved_source=signal.counters[
                "dropped_unresolved_source"
            ],
            dropped_unresolved_target=signal.counters[
                "dropped_unresolved_target"
            ],
            dropped_missing_evidence=signal.counters[
                "dropped_missing_evidence"
            ],
            dropped_missing_relationship=signal.counters[
                "dropped_missing_relationship"
            ],
            dropped_self_loop=signal.counters["dropped_self_loop"],
            ambiguous_calls=signal.counters["ambiguous_calls"],
            ambiguous_factories=signal.counters["ambiguous_factories"],
            ambiguous_imports=signal.counters["ambiguous_imports"],
            discarded_lower_tier=merged.discarded_lower_tier,
            source_cap_dropped_l1=merged.source_cap_dropped_l1,
            source_cap_dropped_l2=merged.source_cap_dropped_l2,
            global_cap_dropped_l1=merged.global_cap_dropped_l1,
            global_cap_dropped_l2=merged.global_cap_dropped_l2,
        )
        return UaEdgeDerivationResult(
            edges=canonical_edges(merged.candidates),
            warnings=_warnings(stats),
            recommended_next_checks=signal.checks,
            stats=stats,
        )


def _warnings(stats: UaEdgeDerivationStats) -> tuple[str, ...]:
    warnings: list[str] = []
    values = (
        (
            "missing component evidence ids",
            stats.missing_component_evidence_ids,
        ),
        ("unresolved source", stats.dropped_unresolved_source),
        ("unresolved target", stats.dropped_unresolved_target),
        ("missing evidence", stats.dropped_missing_evidence),
        ("missing relationship", stats.dropped_missing_relationship),
        ("self loops", stats.dropped_self_loop),
        ("ambiguous calls", stats.ambiguous_calls),
        ("ambiguous factories", stats.ambiguous_factories),
        ("ambiguous imports", stats.ambiguous_imports),
    )
    warnings.extend(
        f"UA edge derivation {label}={count}"
        for label, count in values
        if count
    )
    if stats.discarded_lower_tier:
        warnings.append(
            "UA edge derivation discarded lower-tier "
            f"L2={stats.discarded_lower_tier}"
        )
    cap_values = (
        ("source", "L1", stats.source_cap_dropped_l1),
        ("source", "L2", stats.source_cap_dropped_l2),
        ("global", "L1", stats.global_cap_dropped_l1),
        ("global", "L2", stats.global_cap_dropped_l2),
    )
    warnings.extend(
        f"UA edge derivation {cap} cap dropped {count} {tier}"
        for cap, tier, count in cap_values
        if count
    )
    return tuple(warnings)
