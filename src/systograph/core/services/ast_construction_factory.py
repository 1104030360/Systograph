from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Literal

from systograph.core.models.structural_fact import (
    FactoryInferenceStep,
    SourceSpan,
)
from systograph.core.services.ast_construction_factory_index import (
    FactoryFunction,
    FactoryIndex,
    resolve_internal_function,
)
from systograph.core.services.ast_construction_returns import function_returns
from systograph.core.services.ast_construction_types import (
    resolve_call_symbol,
    resolve_reference,
)

MAX_FACTORY_HOPS = 3
FactoryResolutionKind = Literal[
    "return_annotation",
    "return_construction",
    "delegate_call",
    "registry_entry",
]


@dataclass(frozen=True)
class FactoryCandidate:
    symbol: str
    provenance: tuple[FactoryInferenceStep, ...]


@dataclass(frozen=True)
class FactoryResolution:
    candidates: tuple[FactoryCandidate, ...]
    warnings: frozenset[str]


class FactoryResolver:
    def __init__(
        self,
        index: FactoryIndex,
        known_symbols: frozenset[str],
    ) -> None:
        self.index = index
        self.known_symbols = known_symbols

    def resolve(self, factory: str) -> FactoryResolution:
        return self._resolve(factory, hop=0, visited=frozenset())

    def _resolve(
        self,
        factory: str,
        *,
        hop: int,
        visited: frozenset[str],
    ) -> FactoryResolution:
        if factory in visited:
            return FactoryResolution(
                candidates=(),
                warnings=frozenset({"ast_construction_factory_cycle"}),
            )
        if hop > MAX_FACTORY_HOPS:
            return FactoryResolution(
                candidates=(),
                warnings=frozenset({"ast_construction_factory_hop_limit"}),
            )
        info = self.index.functions[factory]
        if info.node.decorator_list:
            return FactoryResolution(candidates=(), warnings=frozenset())
        annotation = self._annotation_candidate(info, hop)
        if annotation is not None:
            return FactoryResolution(
                candidates=(annotation,),
                warnings=frozenset(),
            )

        candidates: list[FactoryCandidate] = []
        warnings: set[str] = set()
        next_visited = visited | {factory}
        for return_node in function_returns(info.node):
            value = return_node.value
            if not isinstance(value, ast.Call):
                continue
            direct = resolve_call_symbol(
                value.func,
                scope=(info.node.name,),
                bindings=info.bindings,
                known_symbols=self.known_symbols,
                module_bindings=self.index.module_bindings,
            )
            if direct is not None:
                candidates.append(
                    FactoryCandidate(
                        symbol=direct,
                        provenance=(
                            _step(
                                info,
                                hop,
                                "return_construction",
                                value,
                            ),
                        ),
                    )
                )
                continue
            registry_symbols = self._registry_symbols(info, value)
            if registry_symbols:
                candidates.extend(
                    FactoryCandidate(
                        symbol=symbol,
                        provenance=(
                            _step(info, hop, "registry_entry", value),
                        ),
                    )
                    for symbol in registry_symbols
                )
                continue
            delegate = self._delegate(info, value)
            if delegate is None:
                continue
            child = self._resolve(
                delegate,
                hop=hop + 1,
                visited=next_visited,
            )
            warnings.update(child.warnings)
            delegate_step = _step(info, hop, "delegate_call", value)
            candidates.extend(
                FactoryCandidate(
                    symbol=item.symbol,
                    provenance=(delegate_step, *item.provenance),
                )
                for item in child.candidates
            )
        return FactoryResolution(
            candidates=tuple(candidates),
            warnings=frozenset(warnings),
        )

    def _annotation_candidate(
        self,
        info: FactoryFunction,
        hop: int,
    ) -> FactoryCandidate | None:
        annotation = info.node.returns
        if isinstance(annotation, ast.Constant) and isinstance(
            annotation.value, str
        ):
            try:
                annotation = ast.parse(annotation.value, mode="eval").body
            except SyntaxError:
                return None
        if annotation is None:
            return None
        symbol = resolve_call_symbol(
            annotation,
            scope=(),
            bindings=info.bindings,
            known_symbols=self.known_symbols,
            module_bindings=self.index.module_bindings,
        )
        if symbol is None:
            return None
        return FactoryCandidate(
            symbol=symbol,
            provenance=(_step(info, hop, "return_annotation", info.node),),
        )

    def _registry_symbols(
        self,
        info: FactoryFunction,
        call: ast.Call,
    ) -> tuple[str, ...]:
        if not isinstance(call.func, ast.Subscript):
            return ()
        reference = resolve_reference(
            call.func.value,
            scope=(info.node.name,),
            bindings=info.bindings,
        )
        if reference is None:
            return ()
        qualified = reference
        if qualified not in self.index.registries:
            qualified = f"{info.parsed.module_name}.{reference}"
        return self.index.registries.get(qualified, ())

    def _delegate(
        self,
        info: FactoryFunction,
        call: ast.Call,
    ) -> str | None:
        reference = resolve_reference(
            call.func,
            scope=(info.node.name,),
            bindings=info.bindings,
        )
        if reference is None:
            return None
        return resolve_internal_function(
            reference,
            module_name=info.parsed.module_name,
            functions=self.index.functions,
        )


def _step(
    info: FactoryFunction,
    hop: int,
    resolution: FactoryResolutionKind,
    node: ast.expr | ast.FunctionDef | ast.AsyncFunctionDef,
) -> FactoryInferenceStep:
    line_start = node.lineno
    return FactoryInferenceStep(
        hop=hop,
        factory=info.qualified_name,
        resolution=resolution,
        span=SourceSpan(
            file=info.parsed.relative_path,
            line_start=line_start,
            line_end=node.end_lineno or line_start,
        ),
    )
