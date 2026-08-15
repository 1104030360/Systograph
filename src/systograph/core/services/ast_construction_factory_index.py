from __future__ import annotations

import ast
from dataclasses import dataclass

from systograph.core.services.ast_construction_types import (
    ImportBinding,
    ParsedPythonFile,
    RuntimeCall,
    is_type_checking,
    resolve_call_symbol,
    resolve_reference,
)


@dataclass(frozen=True)
class FactoryFunction:
    qualified_name: str
    parsed: ParsedPythonFile
    node: ast.FunctionDef | ast.AsyncFunctionDef
    bindings: list[ImportBinding]


@dataclass(frozen=True)
class FactoryCallSite:
    parsed: ParsedPythonFile
    runtime_call: RuntimeCall
    factory: str


@dataclass(frozen=True)
class FactoryIndex:
    functions: dict[str, FactoryFunction]
    registries: dict[str, tuple[str, ...]]
    call_sites: tuple[FactoryCallSite, ...]
    module_bindings: dict[str, list[ImportBinding]]


def build_factory_index(
    parsed_files: list[ParsedPythonFile],
    bindings_by_file: dict[str, list[ImportBinding]],
    known_symbols: frozenset[str],
    *,
    module_bindings: dict[str, list[ImportBinding]],
) -> FactoryIndex:
    functions: dict[str, FactoryFunction] = {}
    registries: dict[str, tuple[str, ...]] = {}
    for parsed in parsed_files:
        bindings = bindings_by_file[parsed.relative_path]
        for statement in parsed.tree.body:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualified_name = f"{parsed.module_name}.{statement.name}"
                functions[qualified_name] = FactoryFunction(
                    qualified_name=qualified_name,
                    parsed=parsed,
                    node=statement,
                    bindings=bindings,
                )
            elif isinstance(statement, (ast.Assign, ast.AnnAssign)):
                registry = _literal_registry(
                    statement,
                    parsed=parsed,
                    bindings=bindings,
                    known_symbols=known_symbols,
                    module_bindings=module_bindings,
                )
                if registry is not None:
                    name, symbols = registry
                    registries[f"{parsed.module_name}.{name}"] = symbols

    call_sites: list[FactoryCallSite] = []
    for parsed in parsed_files:
        bindings = bindings_by_file[parsed.relative_path]
        collector = _FactoryCallCollector(parsed.module_name)
        collector.visit(parsed.tree)
        for runtime_call in collector.calls:
            reference = resolve_reference(
                runtime_call.node.func,
                scope=runtime_call.scope,
                bindings=bindings,
            )
            if reference is None:
                continue
            factory = _function_reference(
                reference,
                module_name=parsed.module_name,
                functions=functions,
            )
            if factory is not None:
                call_sites.append(
                    FactoryCallSite(
                        parsed=parsed,
                        runtime_call=runtime_call,
                        factory=factory,
                    )
                )
    call_sites.sort(
        key=lambda item: (
            item.parsed.relative_path,
            item.runtime_call.node.lineno,
            item.factory,
        )
    )
    return FactoryIndex(
        functions=functions,
        registries=registries,
        call_sites=tuple(call_sites),
        module_bindings=module_bindings,
    )


def resolve_internal_function(
    reference: str,
    *,
    module_name: str,
    functions: dict[str, FactoryFunction],
) -> str | None:
    return _function_reference(
        reference,
        module_name=module_name,
        functions=functions,
    )


def _function_reference(
    reference: str,
    *,
    module_name: str,
    functions: dict[str, FactoryFunction],
) -> str | None:
    if reference in functions:
        return reference
    local_reference = f"{module_name}.{reference}"
    return local_reference if local_reference in functions else None


def _literal_registry(
    statement: ast.Assign | ast.AnnAssign,
    *,
    parsed: ParsedPythonFile,
    bindings: list[ImportBinding],
    known_symbols: frozenset[str],
    module_bindings: dict[str, list[ImportBinding]],
) -> tuple[str, tuple[str, ...]] | None:
    target: ast.expr
    value: ast.expr | None
    if isinstance(statement, ast.Assign):
        if len(statement.targets) != 1:
            return None
        target = statement.targets[0]
        value = statement.value
    else:
        target = statement.target
        value = statement.value
        if value is None:
            return None
    if not isinstance(target, ast.Name) or not isinstance(value, ast.Dict):
        return None
    symbols: list[str] = []
    for item in value.values:
        symbol = resolve_call_symbol(
            item,
            scope=(),
            bindings=bindings,
            known_symbols=known_symbols,
            module_bindings=module_bindings,
        )
        if symbol is not None and symbol not in symbols:
            symbols.append(symbol)
    if not symbols:
        return None
    return target.id, tuple(symbols)


class _FactoryCallCollector(ast.NodeVisitor):
    def __init__(self, module_name: str) -> None:
        self.module_name = module_name
        self.scope: list[str] = []
        self.calls: list[RuntimeCall] = []

    def visit_Call(self, node: ast.Call) -> None:
        caller = ".".join([self.module_name, *self.scope])
        self.calls.append(
            RuntimeCall(node=node, scope=tuple(self.scope), caller=caller)
        )
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        if node.value is None:
            return
        if not isinstance(node.value, ast.Call):
            self.visit(node.value)
            return
        for argument in node.value.args:
            self.visit(argument)
        for keyword in node.value.keywords:
            self.visit(keyword.value)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        self._visit_definition_outer(node)
        self.scope.append(node.name)
        for statement in node.body:
            self.visit(statement)
        self.scope.pop()

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        self.scope.append(node.name)
        for statement in node.body:
            self.visit(statement)
        self.scope.pop()

    def visit_If(self, node: ast.If) -> None:
        if is_type_checking(node.test):
            for statement in node.orelse:
                self.visit(statement)
            return
        self.generic_visit(node)

    def _visit_definition_outer(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in node.args.defaults:
            self.visit(default)
        for keyword_default in node.args.kw_defaults:
            if keyword_default is not None:
                self.visit(keyword_default)
