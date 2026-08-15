from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from systograph.core.models.recommended_next_check import RecommendedNextCheck
from systograph.core.models.structural_fact import (
    CallStructuralFact,
    FactoryInferenceStructuralFact,
    ImportStructuralFact,
    SourceSpan,
)
from systograph.core.models.system_map import ComponentInstance, Evidence
from systograph.core.services.edge_relationship_catalog import (
    CallKind,
    EdgeRelationshipCatalog,
    SignalKind,
)
from systograph.core.services.ua_edge_derivation_models import (
    EdgeCandidate,
    EdgeStatus,
    EdgeTier,
)
from systograph.core.services.ua_edge_resolution import (
    EdgeResolutionContext,
    infer_call_kind,
)


@dataclass(frozen=True, slots=True)
class SignalDerivationOutcome:
    candidates: tuple[EdgeCandidate, ...]
    counters: Counter[str]
    checks: tuple[RecommendedNextCheck, ...]


class UaEdgeSignalDeriver:
    def __init__(
        self,
        *,
        components: Sequence[ComponentInstance],
        context: EdgeResolutionContext,
        catalog: EdgeRelationshipCatalog,
    ) -> None:
        self._components = {item.id: item for item in components}
        self._context = context
        self._catalog = catalog
        self._counters: Counter[str] = Counter()
        self._candidates: list[EdgeCandidate] = []
        self._checks: dict[str, RecommendedNextCheck] = {}

    def derive_calls(
        self,
        facts: Sequence[CallStructuralFact],
    ) -> None:
        for fact in sorted(facts, key=lambda item: item.sort_key):
            self._counters["calls_seen"] += 1
            self._derive_semantic_signal(
                span=fact.span,
                symbol=fact.callee,
                scope_file=fact.span.file,
                signal_kind="call",
                call_kind=infer_call_kind(fact.callee),
                tier="L1",
                rank=0,
                status="observed",
                reason=None,
                evidence=self._context.call_evidence(fact.span),
                ambiguity_counter="ambiguous_calls",
            )

    def derive_factories(
        self,
        facts: Sequence[FactoryInferenceStructuralFact],
    ) -> None:
        for fact in sorted(facts, key=lambda item: item.sort_key):
            self._counters["factories_seen"] += 1
            # The constructed symbol is named inside the factory, so name
            # resolution is scoped by the terminal factory definition file
            # (the last provenance hop) and the files it imports — never
            # by the call-site file's imports.
            self._derive_semantic_signal(
                span=fact.call_span,
                symbol=fact.constructed_symbol,
                scope_file=fact.provenance[-1].span.file,
                signal_kind="factory_inference",
                call_kind="factory",
                tier="L2",
                rank=1,
                status="undetermined",
                reason="factory_inference",
                evidence=self._context.factory_evidence(fact.call_span),
                ambiguity_counter="ambiguous_factories",
            )

    def derive_imports(
        self,
        facts: Sequence[ImportStructuralFact],
    ) -> None:
        for fact in sorted(facts, key=lambda item: item.sort_key):
            self._counters["imports_seen"] += 1
            if fact.import_scope == "external":
                self._counters["ignored_external_imports"] += 1
                continue
            source_ids = self._context.residence.by_file.get(
                fact.span.file, frozenset()
            )
            target_ids = self._context.residence.by_file.get(
                fact.module, frozenset()
            )
            if len(source_ids) > 1 or len(target_ids) > 1:
                self._counters["ambiguous_imports"] += 1
                continue
            if not source_ids:
                self._counters["dropped_unresolved_source"] += 1
                continue
            if not target_ids:
                self._counters["dropped_unresolved_target"] += 1
                continue
            source = next(iter(source_ids))
            target = next(iter(target_ids))
            if source == target:
                self._counters["dropped_self_loop"] += 1
                continue
            evidence = self._context.import_evidence(
                source_file=fact.span.file,
                target_file=fact.module,
            )
            if not evidence:
                self._counters["dropped_missing_evidence"] += 1
                continue
            self._derive_import_candidate(source, target, evidence)

    def outcome(self) -> SignalDerivationOutcome:
        return SignalDerivationOutcome(
            candidates=tuple(
                sorted(self._candidates, key=lambda item: item.sort_key)
            ),
            counters=self._counters.copy(),
            checks=tuple(self._checks[key] for key in sorted(self._checks)),
        )

    def _derive_semantic_signal(
        self,
        *,
        span: SourceSpan,
        symbol: str,
        scope_file: str,
        signal_kind: SignalKind,
        call_kind: CallKind,
        tier: EdgeTier,
        rank: int,
        status: EdgeStatus,
        reason: str | None,
        evidence: Sequence[Evidence],
        ambiguity_counter: str,
    ) -> None:
        source_ids = self._context.source_component_ids(span)
        if not source_ids:
            self._counters["dropped_unresolved_source"] += 1
            return
        if not evidence:
            self._counters["dropped_missing_evidence"] += 1
            return
        resolution = self._context.target_component_ids(
            symbol=symbol,
            scope_file=scope_file,
            span=span,
            matched_evidence=evidence,
        )
        # An ambiguous name path is counted but never vetoes the signal:
        # evidence- and location-based target resolution still apply.
        if resolution.ambiguous_name:
            self._counters["ambiguous_callee_names"] += 1
        target_ids = resolution.component_ids
        if not target_ids:
            self._counters["dropped_unresolved_target"] += 1
            return
        non_self_pairs = {
            (source, target)
            for source in source_ids
            for target in target_ids
            if source != target
        }
        if not non_self_pairs:
            self._counters["dropped_self_loop"] += 1
            return
        # Attribution must resolve to one pair before the catalog is
        # consulted: the rules table names the relationship of a resolved
        # pair, it never picks which candidate pair the code meant.
        if len(non_self_pairs) > 1:
            self._counters[ambiguity_counter] += 1
            return
        ((source, target),) = non_self_pairs
        matches = self._relationship_matches(
            source=source,
            target=target,
            evidence=evidence,
            signal_kind=signal_kind,
            call_kind=call_kind,
            symbol=symbol,
        )
        if not matches:
            self._counters["dropped_missing_relationship"] += 1
            self._record_check(
                frozenset({source}), frozenset({target}), symbol
            )
            return
        if len(matches) > 1:
            self._counters[ambiguity_counter] += 1
            return
        relationship, evidence_ids = next(iter(matches.items()))
        self._candidates.append(
            EdgeCandidate(
                source=source,
                target=target,
                relationship=relationship,
                tier=tier,
                rank=rank,
                status=status,
                evidence_ids=tuple(sorted(evidence_ids)),
                undetermined_reason=reason,
            )
        )

    def _relationship_matches(
        self,
        *,
        source: str,
        target: str,
        evidence: Sequence[Evidence],
        signal_kind: SignalKind,
        call_kind: CallKind,
        symbol: str,
    ) -> dict[str, set[str]]:
        matches: dict[str, set[str]] = defaultdict(set)
        for item in evidence:
            if item.rule_id is None:
                continue
            relationship = self._catalog.lookup_values(
                from_kind=self._components[source].kind,
                to_kind=self._components[target].kind,
                signal_kind=signal_kind,
                call_kind=call_kind,
                callee_symbol=symbol,
                producer_rule_id=item.rule_id,
            )
            if relationship is not None:
                matches[relationship].add(item.id)
        return matches

    def _derive_import_candidate(
        self,
        source: str,
        target: str,
        evidence: Sequence[Evidence],
    ) -> None:
        relationships: dict[str, set[str]] = defaultdict(set)
        for item in evidence:
            if item.rule_id is None:
                continue
            relationship = self._catalog.lookup_values(
                from_kind=self._components[source].kind,
                to_kind=self._components[target].kind,
                signal_kind="import",
                call_kind="import",
                callee_symbol="internal_import",
                producer_rule_id=item.rule_id,
            )
            if relationship is not None:
                relationships[relationship].add(item.id)
        if not relationships:
            self._counters["dropped_missing_relationship"] += 1
            self._record_check(
                frozenset({source}), frozenset({target}), "internal_import"
            )
            return
        if len(relationships) > 1:
            self._counters["ambiguous_imports"] += 1
            return
        relationship, evidence_ids = next(iter(relationships.items()))
        self._candidates.append(
            EdgeCandidate(
                source=source,
                target=target,
                relationship=relationship,
                tier="L2",
                rank=2,
                status="undetermined",
                evidence_ids=tuple(sorted(evidence_ids)),
                undetermined_reason="import_only_no_call_site",
            )
        )

    def _record_check(
        self,
        source_ids: frozenset[str],
        target_ids: frozenset[str],
        symbol: str,
    ) -> None:
        source_kinds = sorted(
            self._components[item].kind for item in source_ids
        )
        target_kinds = sorted(
            self._components[item].kind for item in target_ids
        )
        target = f"{','.join(source_kinds)}->{','.join(target_kinds)}:{symbol}"
        digest = hashlib.sha256(target.encode("utf-8")).hexdigest()[:16]
        check_id = f"next_check:ua-edge-relationship:{digest}"
        self._checks[check_id] = RecommendedNextCheck(
            id=check_id,
            target_type="edge_relationship",
            target=target,
            reason="No audited relationship rule matched the typed signal.",
            action="Review the endpoint kinds and add a precise catalog rule.",
        )
