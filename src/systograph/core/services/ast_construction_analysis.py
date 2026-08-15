from __future__ import annotations

import ast
import sys

from systograph.core.services.ast_construction_types import (
    ImportBinding,
    RuntimeCall,
    is_type_checking,
)


def collect_imports(
    tree: ast.Module,
    *,
    module_name: str,
    is_package: bool,
    internal_modules: frozenset[str],
) -> list[ImportBinding]:
    collector = _ImportCollector(
        module_name=module_name,
        is_package=is_package,
        internal_modules=internal_modules,
    )
    collector.visit(tree)
    return collector.bindings


def collect_runtime_calls(
    tree: ast.Module,
    *,
    module_name: str,
) -> list[RuntimeCall]:
    collector = _RuntimeCallCollector(module_name)
    collector.visit(tree)
    return collector.calls


class _ImportCollector(ast.NodeVisitor):
    def __init__(
        self,
        *,
        module_name: str,
        is_package: bool,
        internal_modules: frozenset[str],
    ) -> None:
        self.package_parts = module_name.split(".")
        if not is_package:
            self.package_parts = self.package_parts[:-1]
        self.internal_modules = internal_modules
        self.bindings: list[ImportBinding] = []
        self.scope: list[str] = []
        self.runtime = True

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            local_name = alias.asname or alias.name.split(".", 1)[0]
            binding_target = alias.name if alias.asname else local_name
            self._append(
                node,
                module=alias.name,
                symbol=None,
                alias=alias.asname,
                local_name=local_name,
                binding_target=binding_target,
                is_star=False,
                relative=False,
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = self._absolute_module(node.module or "", node.level)
        for alias in node.names:
            binding_target = f"{module}.{alias.name}" if module else alias.name
            self._append(
                node,
                module=module,
                symbol=alias.name,
                alias=alias.asname,
                local_name=(
                    None if alias.name == "*" else alias.asname or alias.name
                ),
                binding_target=binding_target,
                is_star=alias.name == "*",
                relative=node.level > 0,
            )

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
        if not is_type_checking(node.test):
            self.generic_visit(node)
            return
        previous = self.runtime
        self.runtime = False
        for statement in node.body:
            self.visit(statement)
        self.runtime = previous
        for statement in node.orelse:
            self.visit(statement)

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

    def _absolute_module(self, module: str, level: int) -> str:
        if level == 0:
            return module
        keep = max(0, len(self.package_parts) - (level - 1))
        parts = [*self.package_parts[:keep], *module.split(".")]
        return ".".join(part for part in parts if part)

    def _append(
        self,
        node: ast.Import | ast.ImportFrom,
        *,
        module: str,
        symbol: str | None,
        alias: str | None,
        local_name: str | None,
        binding_target: str,
        is_star: bool,
        relative: bool,
    ) -> None:
        root = module.split(".", 1)[0]
        project_internal = relative or root in self.internal_modules
        external = (
            not project_internal
            and root not in sys.stdlib_module_names
            and root != "__future__"
        )
        self.bindings.append(
            ImportBinding(
                module=module,
                symbol=symbol,
                alias=alias,
                local_name=local_name,
                binding_target=binding_target,
                scope=tuple(self.scope),
                runtime=self.runtime,
                project_internal=project_internal,
                external=external,
                is_star=is_star,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
            )
        )


class _RuntimeCallCollector(ast.NodeVisitor):
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

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_definition_outer(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_definition_outer(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        for default in node.args.defaults:
            self.visit(default)
        for keyword_default in node.args.kw_defaults:
            if keyword_default is not None:
                self.visit(keyword_default)

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
