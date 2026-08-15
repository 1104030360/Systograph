from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeAlias, assert_never

from systograph.core.models.structural_fact import (
    CallStructuralFact,
    FactoryInferenceStructuralFact,
    ImportStructuralFact,
    StructuralFact,
    SymbolStructuralFact,
)
from systograph.core.models.system_map import ComponentInstance, Evidence

SpanKey: TypeAlias = tuple[str, int, int]


@dataclass(frozen=True, slots=True)
class Residence:
    file: str
    span: tuple[int, int] | None


@dataclass(frozen=True, slots=True)
class ComponentResidenceIndex:
    by_component: Mapping[str, frozenset[Residence]]
    by_file: Mapping[str, frozenset[str]]
    by_span: Mapping[SpanKey, str]
    ambiguous_spans: Mapping[SpanKey, frozenset[str]]
    missing_evidence_ids: tuple[str, ...]
    _symbol_spans_by_file_and_name: Mapping[
        tuple[str, str], tuple[SpanKey, ...]
    ]

    @classmethod
    def build(
        cls,
        *,
        components: Sequence[ComponentInstance],
        evidence: Sequence[Evidence],
        structural_facts: Sequence[StructuralFact],
    ) -> ComponentResidenceIndex:
        spans_by_file: dict[str, set[SpanKey]] = {}
        # Symbol names are indexed per file and case-sensitively: name
        # lookups never match across files, so a repo-wide name collision
        # cannot attribute a callee to an unrelated component.
        spans_by_name: dict[tuple[str, str], set[SpanKey]] = {}
        for fact in structural_facts:
            match fact:
                case SymbolStructuralFact(symbol_kind="function" | "class"):
                    if (
                        fact.span.line_start is None
                        or fact.span.line_end is None
                    ):
                        continue
                    key = (
                        fact.span.file,
                        fact.span.line_start,
                        fact.span.line_end,
                    )
                    spans_by_file.setdefault(fact.span.file, set()).add(key)
                    spans_by_name.setdefault(
                        (fact.span.file, fact.symbol), set()
                    ).add(key)
                case SymbolStructuralFact():
                    continue
                case (
                    CallStructuralFact()
                    | ImportStructuralFact()
                    | FactoryInferenceStructuralFact()
                ):
                    continue
                case unreachable:
                    assert_never(unreachable)

        frozen_spans_by_file = {
            file: tuple(sorted(spans, key=_span_sort_key))
            for file, spans in sorted(spans_by_file.items())
        }
        evidence_by_id = {item.id: item for item in evidence}
        residences: dict[str, set[Residence]] = {
            component.id: set() for component in components
        }
        components_by_file: dict[str, set[str]] = {}
        components_by_span: dict[SpanKey, set[str]] = {}
        missing_evidence_ids: set[str] = set()
        for component in sorted(components, key=lambda item: item.id):
            for evidence_id in sorted(component.evidence_ids):
                item = evidence_by_id.get(evidence_id)
                if item is None:
                    missing_evidence_ids.add(evidence_id)
                    continue
                if item.file is None:
                    continue
                span = _smallest_span(
                    frozen_spans_by_file.get(item.file, ()),
                    item.line_start,
                )
                residence = Residence(
                    file=item.file,
                    span=(span[1], span[2]) if span is not None else None,
                )
                residences[component.id].add(residence)
                components_by_file.setdefault(item.file, set()).add(
                    component.id
                )
                if span is not None:
                    components_by_span.setdefault(span, set()).add(
                        component.id
                    )

        unique_spans = {
            span: next(iter(component_ids))
            for span, component_ids in components_by_span.items()
            if len(component_ids) == 1
        }
        ambiguous_spans = {
            span: frozenset(component_ids)
            for span, component_ids in components_by_span.items()
            if len(component_ids) > 1
        }
        return cls(
            by_component=MappingProxyType(
                {
                    key: frozenset(value)
                    for key, value in sorted(residences.items())
                }
            ),
            by_file=MappingProxyType(
                {
                    key: frozenset(value)
                    for key, value in sorted(components_by_file.items())
                }
            ),
            by_span=MappingProxyType(dict(sorted(unique_spans.items()))),
            ambiguous_spans=MappingProxyType(
                dict(sorted(ambiguous_spans.items()))
            ),
            missing_evidence_ids=tuple(sorted(missing_evidence_ids)),
            _symbol_spans_by_file_and_name=MappingProxyType(
                {
                    key: tuple(sorted(value, key=_span_sort_key))
                    for key, value in sorted(spans_by_name.items())
                }
            ),
        )

    def component_ids_at(self, file: str, line: int) -> frozenset[str]:
        spans = tuple(self.by_span) + tuple(self.ambiguous_spans)
        containing = [
            span
            for span in spans
            if span[0] == file and span[1] <= line <= span[2]
        ]
        if not containing:
            return self._file_level_fallback(file)
        smallest_size = min(span[2] - span[1] for span in containing)
        component_ids: set[str] = set()
        for span in containing:
            if span[2] - span[1] != smallest_size:
                continue
            unique = self.by_span.get(span)
            if unique is not None:
                component_ids.add(unique)
            component_ids.update(self.ambiguous_spans.get(span, ()))
        return frozenset(component_ids)

    def _file_level_fallback(self, file: str) -> frozenset[str]:
        """Attribute a line no component-bearing span covers.

        Component evidence often lands where no function or class span
        can hold it -- an import line, a decorator, a module-level
        assignment -- which leaves the component with no usable code
        address and drops every call in the file as an unresolved
        source. A file that hosts exactly ONE component has no
        attribution ambiguity to resolve, so its module-level lines
        belong to that component.

        Two or more components in one file stay unattributed: which of
        them owns a module-level line is a guess, and the caller
        reports it through file_level_ambiguous() instead of picking a
        side. This widens WHERE a component lives, never how a callee
        name is resolved.
        """
        component_ids = self.by_file.get(file, frozenset())
        return component_ids if len(component_ids) == 1 else frozenset()

    def file_level_ambiguous(self, file: str) -> bool:
        """Whether the file hosts several components, blocking fallback."""

        return len(self.by_file.get(file, frozenset())) > 1

    def components_without_code_residence(
        self,
        code_files: frozenset[str],
    ) -> tuple[str, ...]:
        """Components whose evidence never lands in an analysed code file.

        Those components can never be an edge endpoint: a manifest or a
        compose file carries no call sites. Naming them turns "0 edges"
        from a black box into an attributable list.
        """

        return tuple(
            sorted(
                component_id
                for component_id, residences in self.by_component.items()
                if not any(item.file in code_files for item in residences)
            )
        )

    def symbol_spans(self, file: str, name: str) -> tuple[SpanKey, ...]:
        return self._symbol_spans_by_file_and_name.get((file, name), ())

    def component_ids_for_symbol_in_file(
        self,
        file: str,
        name: str,
    ) -> frozenset[str]:
        component_ids: set[str] = set()
        for span in self.symbol_spans(file, name):
            component_ids.update(self.component_ids_at(span[0], span[1]))
        return frozenset(component_ids)


def _smallest_span(
    spans: Sequence[SpanKey],
    line: int | None,
) -> SpanKey | None:
    if line is None:
        return None
    containing = [span for span in spans if span[1] <= line <= span[2]]
    return min(containing, key=_span_sort_key) if containing else None


def _span_sort_key(span: SpanKey) -> tuple[int, int, int, str]:
    return (span[2] - span[1], span[1], span[2], span[0])
