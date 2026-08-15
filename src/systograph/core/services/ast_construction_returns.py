from __future__ import annotations

import ast


def function_returns(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.Return]:
    collector = _ReturnCollector()
    for statement in function.body:
        collector.visit(statement)
    return collector.returns


class _ReturnCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.returns: list[ast.Return] = []

    def visit_Return(self, node: ast.Return) -> None:
        self.returns.append(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return
