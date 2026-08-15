from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath

MAX_REEXPORT_HOPS = 3


@dataclass(frozen=True)
class ImportBinding:
    module: str
    symbol: str | None
    alias: str | None
    local_name: str | None
    binding_target: str
    scope: tuple[str, ...]
    runtime: bool
    project_internal: bool
    external: bool
    is_star: bool
    line_start: int
    line_end: int


@dataclass(frozen=True)
class RuntimeCall:
    node: ast.Call
    scope: tuple[str, ...]
    caller: str


@dataclass(frozen=True)
class ParsedPythonFile:
    relative_path: str
    source: str
    tree: ast.Module
    module_name: str
    is_package: bool


def module_name_for_path(relative_path: str) -> str:
    parts = list(PurePosixPath(relative_path).with_suffix("").parts)
    if parts and parts[0] == "src":
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) or "__init__"


def internal_module_names(relative_paths: list[str]) -> frozenset[str]:
    modules = {module_name_for_path(path) for path in relative_paths}
    roots = {module.split(".", 1)[0] for module in modules}
    return frozenset(modules | roots)


def dotted_symbol(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted_symbol(node.value)
        return f"{parent}.{node.attr}" if parent is not None else None
    return None


def is_type_checking(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Name)
        and node.id == "TYPE_CHECKING"
        or isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "typing"
        and node.attr == "TYPE_CHECKING"
    )


def resolve_call_symbol(
    node: ast.AST,
    *,
    scope: tuple[str, ...],
    bindings: list[ImportBinding],
    known_symbols: frozenset[str],
    module_bindings: Mapping[str, list[ImportBinding]],
) -> str | None:
    raw = dotted_symbol(node)
    if raw is None:
        return None
    root, *tail = raw.split(".")
    binding = visible_binding(root, scope, bindings)
    if binding is None:
        return raw if raw in known_symbols else None
    resolved = ".".join([binding.binding_target, *tail])
    if resolved in known_symbols:
        return resolved
    # A name imported from a project module may be a re-export of an
    # external symbol; follow the module-level import chain and return a
    # catalog symbol only when the chain proves the origin. A name the
    # module defines itself has no matching binding and resolves to None.
    for _ in range(MAX_REEXPORT_HOPS):
        if not binding.project_internal:
            return None
        module, _, name = resolved.rpartition(".")
        target_bindings = module_bindings.get(module)
        if target_bindings is None:
            return None
        next_binding = visible_binding(name, (), target_bindings)
        if next_binding is None:
            return None
        binding = next_binding
        resolved = binding.binding_target
        if resolved in known_symbols:
            return resolved
    return None


def module_level_bindings(
    parsed_files: list[ParsedPythonFile],
    bindings_by_file: Mapping[str, list[ImportBinding]],
) -> dict[str, list[ImportBinding]]:
    modules: dict[str, list[ImportBinding]] = {}
    # Two inventory paths can collapse to one module name ("src/" is
    # stripped); an ambiguous module name cannot anchor a re-export chain.
    duplicated: set[str] = set()
    for parsed in parsed_files:
        if parsed.module_name in modules:
            duplicated.add(parsed.module_name)
            continue
        modules[parsed.module_name] = [
            binding
            for binding in bindings_by_file[parsed.relative_path]
            if binding.scope == ()
        ]
    for module_name in duplicated:
        del modules[module_name]
    return modules


def resolve_reference(
    node: ast.AST,
    *,
    scope: tuple[str, ...],
    bindings: list[ImportBinding],
) -> str | None:
    raw = dotted_symbol(node)
    if raw is None:
        return None
    root, *tail = raw.split(".")
    binding = visible_binding(root, scope, bindings)
    if binding is None:
        return raw
    return ".".join([binding.binding_target, *tail])


def visible_binding(
    local_name: str,
    scope: tuple[str, ...],
    bindings: list[ImportBinding],
) -> ImportBinding | None:
    for length in range(len(scope), -1, -1):
        candidate_scope = scope[:length]
        for binding in reversed(bindings):
            if (
                binding.runtime
                and binding.local_name == local_name
                and binding.scope == candidate_scope
            ):
                return binding
    return None
