"""Resolution context for UA edge derivation.

Callee-name resolution is scoped, case-sensitive, and import-aware:

- A bare name resolves in the scope file first (a local definition wins),
  then across the files the scope file imports; if more than one imported
  file defines the name the name path yields nothing and is flagged
  ambiguous.
- A dotted name resolves through its module prefix: an imported file
  matches when the prefix equals one of the file's dotted path suffixes
  (``pkg/mod.py`` matches ``mod`` and ``pkg.mod``); several matching
  files are ambiguous.
- Attribute calls on local variables, builtins, and external symbols
  match no import and fall out of the name path naturally.

Import facts carry no alias or symbol data, so ``import ... as`` aliases
and ``__init__.py`` re-exports fail closed by design.

A failed or ambiguous name path never vetoes a call on its own: matched
evidence and call-site location still contribute target components, and
the deriver counts the final-empty case as an unresolved target.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from types import MappingProxyType

from systograph.core.models.structural_fact import (
    ImportStructuralFact,
    SourceSpan,
    StructuralFact,
)
from systograph.core.models.system_map import ComponentInstance, Evidence
from systograph.core.services.component_residence_index import (
    ComponentResidenceIndex,
)
from systograph.core.services.edge_relationship_catalog import CallKind


@dataclass(frozen=True, slots=True)
class TargetResolution:
    component_ids: frozenset[str]
    ambiguous_name: bool


@dataclass(frozen=True, slots=True)
class _NameResolution:
    component_ids: frozenset[str]
    ambiguous: bool


_EMPTY_NAME = _NameResolution(component_ids=frozenset(), ambiguous=False)
_AMBIGUOUS_NAME = _NameResolution(component_ids=frozenset(), ambiguous=True)


@dataclass(frozen=True, slots=True)
class EdgeResolutionContext:
    residence: ComponentResidenceIndex
    _evidence: tuple[Evidence, ...]
    _components_by_evidence_id: dict[str, frozenset[str]]
    _components_by_location: dict[tuple[str, int], frozenset[str]]
    _imports_by_file: dict[str, frozenset[str]]
    # Evidence reaches tens of thousands of rows on real repositories;
    # per-span linear scans are quadratic, so lookups are indexed once.
    _evidence_by_line: dict[tuple[str, int], tuple[Evidence, ...]]
    _evidence_by_file_path: dict[tuple[str, str], tuple[Evidence, ...]]

    @classmethod
    def build(
        cls,
        *,
        components: Sequence[ComponentInstance],
        evidence: Sequence[Evidence],
        residence: ComponentResidenceIndex,
        structural_facts: Sequence[StructuralFact],
    ) -> EdgeResolutionContext:
        evidence_by_id = {item.id: item for item in evidence}
        by_evidence_id: dict[str, set[str]] = {}
        by_location: dict[tuple[str, int], set[str]] = {}
        for component in sorted(components, key=lambda item: item.id):
            for evidence_id in sorted(component.evidence_ids):
                by_evidence_id.setdefault(evidence_id, set()).add(component.id)
                item = evidence_by_id.get(evidence_id)
                if (
                    item is not None
                    and item.file is not None
                    and item.line_start is not None
                ):
                    by_location.setdefault(
                        (item.file, item.line_start), set()
                    ).add(component.id)
        imports_by_file: dict[str, set[str]] = {}
        for fact in structural_facts:
            if (
                isinstance(fact, ImportStructuralFact)
                and fact.import_scope == "internal"
            ):
                imports_by_file.setdefault(fact.span.file, set()).add(
                    fact.module
                )
        ordered_evidence = tuple(sorted(evidence, key=lambda item: item.id))
        by_line: dict[tuple[str, int], list[Evidence]] = {}
        by_file_path: dict[tuple[str, str], list[Evidence]] = {}
        for item in ordered_evidence:
            if item.file is not None and item.line_start is not None:
                by_line.setdefault((item.file, item.line_start), []).append(
                    item
                )
            if item.file is not None and item.path is not None:
                by_file_path.setdefault((item.file, item.path), []).append(
                    item
                )
        return cls(
            residence=residence,
            _evidence=ordered_evidence,
            _evidence_by_line={
                key: tuple(items) for key, items in by_line.items()
            },
            _evidence_by_file_path={
                key: tuple(items) for key, items in by_file_path.items()
            },
            _components_by_evidence_id=dict(
                MappingProxyType(
                    {
                        key: frozenset(value)
                        for key, value in sorted(by_evidence_id.items())
                    }
                )
            ),
            _components_by_location=dict(
                MappingProxyType(
                    {
                        key: frozenset(value)
                        for key, value in sorted(by_location.items())
                    }
                )
            ),
            _imports_by_file=dict(
                MappingProxyType(
                    {
                        key: frozenset(value)
                        for key, value in sorted(imports_by_file.items())
                    }
                )
            ),
        )

    def source_component_ids(self, span: SourceSpan) -> frozenset[str]:
        if span.line_start is None:
            return frozenset()
        return self.residence.component_ids_at(span.file, span.line_start)

    def target_component_ids(
        self,
        *,
        symbol: str,
        scope_file: str,
        span: SourceSpan,
        matched_evidence: Sequence[Evidence],
    ) -> TargetResolution:
        name = self._resolve_symbol_by_name(
            symbol=symbol,
            scope_file=scope_file,
        )
        component_ids = set(name.component_ids)
        for item in matched_evidence:
            component_ids.update(
                self._components_by_evidence_id.get(item.id, ())
            )
        if span.line_start is not None:
            component_ids.update(
                self._components_by_location.get(
                    (span.file, span.line_start), ()
                )
            )
        return TargetResolution(
            component_ids=frozenset(component_ids),
            ambiguous_name=name.ambiguous,
        )

    def call_evidence(self, span: SourceSpan) -> tuple[Evidence, ...]:
        return tuple(
            item
            for item in self._evidence_at(span)
            if item.rule_id is not None and _is_direct(item)
        )

    def factory_evidence(self, span: SourceSpan) -> tuple[Evidence, ...]:
        return tuple(
            item
            for item in self._evidence_at(span)
            if item.rule_id is not None and _is_indirect(item)
        )

    def import_evidence(
        self,
        *,
        source_file: str,
        target_file: str,
    ) -> tuple[Evidence, ...]:
        expected_path = f"imports[{target_file}]"
        return tuple(
            item
            for item in self._evidence_by_file_path.get(
                (source_file, expected_path), ()
            )
            if item.rule_id is not None and _is_indirect(item)
        )

    def _resolve_symbol_by_name(
        self,
        *,
        symbol: str,
        scope_file: str,
    ) -> _NameResolution:
        prefix, separator, name = symbol.rpartition(".")
        if not separator:
            return self._resolve_bare_name(name=name, scope_file=scope_file)
        return self._resolve_dotted_name(
            prefix=prefix,
            name=name,
            scope_file=scope_file,
        )

    def _resolve_bare_name(
        self,
        *,
        name: str,
        scope_file: str,
    ) -> _NameResolution:
        residence = self.residence
        if residence.symbol_spans(scope_file, name):
            return _NameResolution(
                component_ids=residence.component_ids_for_symbol_in_file(
                    scope_file, name
                ),
                ambiguous=False,
            )
        defining_files = [
            file
            for file in sorted(self._imported_files(scope_file))
            if residence.symbol_spans(file, name)
        ]
        if len(defining_files) > 1:
            return _AMBIGUOUS_NAME
        if not defining_files:
            return _EMPTY_NAME
        return _NameResolution(
            component_ids=residence.component_ids_for_symbol_in_file(
                defining_files[0], name
            ),
            ambiguous=False,
        )

    def _resolve_dotted_name(
        self,
        *,
        prefix: str,
        name: str,
        scope_file: str,
    ) -> _NameResolution:
        matching_files = [
            file
            for file in sorted(self._imported_files(scope_file))
            if prefix in _module_suffixes(file)
        ]
        if len(matching_files) > 1:
            return _AMBIGUOUS_NAME
        if not matching_files:
            return _EMPTY_NAME
        return _NameResolution(
            component_ids=self.residence.component_ids_for_symbol_in_file(
                matching_files[0], name
            ),
            ambiguous=False,
        )

    def _imported_files(self, scope_file: str) -> frozenset[str]:
        return self._imports_by_file.get(scope_file, frozenset())

    def _evidence_at(self, span: SourceSpan) -> tuple[Evidence, ...]:
        if span.line_start is None:
            return ()
        return self._evidence_by_line.get((span.file, span.line_start), ())


def infer_call_kind(callee: str) -> CallKind:
    terminal = callee.rsplit(".", maxsplit=1)[-1]
    if terminal[:1].isupper():
        return "constructor"
    if "." in callee:
        return "method"
    return "function"


def _module_suffixes(file: str) -> frozenset[str]:
    parts = PurePosixPath(file).with_suffix("").parts
    return frozenset(".".join(parts[index:]) for index in range(len(parts)))


def _is_direct(item: Evidence) -> bool:
    if item.evidence_kind_hint is not None:
        return item.evidence_kind_hint == "direct"
    return item.file is not None and item.line_start is not None


def _is_indirect(item: Evidence) -> bool:
    if item.evidence_kind_hint is not None:
        return item.evidence_kind_hint == "indirect"
    return item.line_start is None
