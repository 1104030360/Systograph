"""Bounded L2 component detail scan using Python ast only."""

from __future__ import annotations

import ast
import io
import re
import tokenize
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from systograph.core.models.system_map import DetailScanFinding, Evidence
from systograph.core.services.secret_masking_service import (
    SecretMaskingService,
)

PYTHON_IMPORT_RULE_ID = "detail_scan.python_import"
PYTHON_SYMBOL_RULE_ID = "detail_scan.python_symbol"
PYTHON_FUNCTION_RULE_ID = "detail_scan.python_function"
PYTHON_DECORATOR_RULE_ID = "detail_scan.python_decorator"
REGEX_IMPORT_RULE_ID = "detail_scan.regex_import"
REGEX_FUNCTION_RULE_ID = "detail_scan.regex_function"
IMPORT_LINE_RE = re.compile(
    r"^\s*(?:import\s+[A-Za-z_][\w.]*|from\s+[A-Za-z_][\w.]*\s+import\s+.+)"
)
FUNCTION_LINE_RE = re.compile(
    r"^\s*(?:async\s+def|def)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\("
)


@dataclass(frozen=True)
class ComponentDetailScanExtraction:
    evidence: list[Evidence] = field(default_factory=list)
    findings: list[DetailScanFinding] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    context_limits: dict[str, object] = field(default_factory=dict)


class ComponentDetailScanService:
    """Extract imports, signatures and decorators from target-related files."""

    def __init__(
        self,
        *,
        masking_service: SecretMaskingService | None = None,
        max_files_per_target: int = 4,
        max_symbols_per_file: int = 24,
        max_snippet_chars: int = 320,
        max_evidence_items: int = 40,
    ) -> None:
        self._masking_service = masking_service or SecretMaskingService()
        self._max_files_per_target = max_files_per_target
        self._max_symbols_per_file = max_symbols_per_file
        self._max_snippet_chars = max_snippet_chars
        self._max_evidence_items = max_evidence_items

    def scan(
        self,
        *,
        project_root: Path,
        relative_files: Sequence[str],
        target_slug: str,
        existing_evidence_ids: set[str],
    ) -> ComponentDetailScanExtraction:
        warnings: list[str] = []
        evidence: list[Evidence] = []
        findings: list[DetailScanFinding] = []
        python_files = self._bounded_python_files(
            project_root=project_root,
            relative_files=relative_files,
            warnings=warnings,
        )

        for relative_file, file_path in python_files:
            file_evidence = self._scan_file(
                file_path=file_path,
                relative_file=relative_file,
                target_slug=target_slug,
                existing_evidence_ids=existing_evidence_ids
                | {item.id for item in evidence},
                warnings=warnings,
            )
            evidence.extend(file_evidence)
            if len(evidence) >= self._max_evidence_items:
                warnings.append("detail_scan_evidence_truncated")
                evidence = evidence[: self._max_evidence_items]
                break

        for item in evidence:
            findings.append(
                DetailScanFinding(
                    kind=item.kind,
                    summary=f"Static detail signal: {item.path or item.value}",
                    evidence_ids=[item.id],
                    best_effort=True,
                )
            )

        return ComponentDetailScanExtraction(
            evidence=evidence,
            findings=findings,
            warnings=warnings,
            context_limits={
                "max_files_per_target": self._max_files_per_target,
                "max_symbols_per_file": self._max_symbols_per_file,
                "max_snippet_chars": self._max_snippet_chars,
                "max_evidence_items": self._max_evidence_items,
                "files_considered": len(python_files),
                "truncated": "detail_scan_evidence_truncated" in warnings,
                "parse_fallback_used": any(
                    warning.startswith("detail_scan_ast_parse_failed:")
                    for warning in warnings
                ),
                "best_effort": True,
            },
        )

    def _bounded_python_files(
        self,
        *,
        project_root: Path,
        relative_files: Sequence[str],
        warnings: list[str],
    ) -> list[tuple[str, Path]]:
        files: list[tuple[str, Path]] = []
        for relative_file in relative_files:
            if len(files) >= self._max_files_per_target:
                warnings.append("detail_scan_files_truncated")
                break
            resolved = self._resolve_python_file(project_root, relative_file)
            if resolved is None:
                continue
            files.append((relative_file, resolved))
        return files

    def _resolve_python_file(
        self,
        project_root: Path,
        relative_file: str,
    ) -> Path | None:
        posix_path = PurePosixPath(relative_file)
        if (
            "\\" in relative_file
            or posix_path.is_absolute()
            or ".." in posix_path.parts
            or posix_path.suffix != ".py"
        ):
            return None

        root = project_root.resolve()
        candidate = (root / Path(*posix_path.parts)).resolve()
        if not candidate.is_file() or not candidate.is_relative_to(root):
            return None
        return candidate

    def _scan_file(
        self,
        *,
        file_path: Path,
        relative_file: str,
        target_slug: str,
        existing_evidence_ids: set[str],
        warnings: list[str],
    ) -> list[Evidence]:
        try:
            source = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            warnings.append(f"detail_scan_parse_skipped:{relative_file}")
            warnings.append(self._masking_service.mask_text(str(exc)))
            return []

        lines = source.splitlines()
        try:
            tree = ast.parse(source, filename=relative_file)
        except SyntaxError as exc:
            warnings.append(f"detail_scan_ast_parse_failed:{relative_file}")
            warnings.append(self._masking_service.mask_text(str(exc)))
            return self._regex_fallback_scan(
                relative_file=relative_file,
                lines=lines,
                target_slug=target_slug,
                existing_evidence_ids=existing_evidence_ids,
            )

        evidence: list[Evidence] = []
        for node in ast.iter_child_nodes(tree):
            self._collect_node(
                node=node,
                relative_file=relative_file,
                lines=lines,
                target_slug=target_slug,
                parent_symbols=[],
                existing_evidence_ids=existing_evidence_ids,
                evidence=evidence,
            )
            if len(evidence) >= self._max_symbols_per_file:
                warnings.append(
                    f"detail_scan_symbols_truncated:{relative_file}"
                )
                break
        return evidence

    def _regex_fallback_scan(
        self,
        *,
        relative_file: str,
        lines: list[str],
        target_slug: str,
        existing_evidence_ids: set[str],
    ) -> list[Evidence]:
        evidence: list[Evidence] = []
        for index, line in enumerate(lines, start=1):
            import_match = IMPORT_LINE_RE.match(line)
            if import_match is not None:
                evidence.append(
                    self._base_evidence(
                        kind="detail_scan_import",
                        rule_id=REGEX_IMPORT_RULE_ID,
                        relative_file=relative_file,
                        path=import_match.group(0).strip(),
                        value=import_match.group(0).strip(),
                        line_start=index,
                        line_end=index,
                        lines=lines,
                        target_slug=target_slug,
                        id_suffix="regex-import",
                        existing_evidence_ids=existing_evidence_ids
                        | {item.id for item in evidence},
                    )
                )
                continue

            function_match = FUNCTION_LINE_RE.match(line)
            if function_match is not None:
                evidence.append(
                    self._base_evidence(
                        kind="detail_scan_function",
                        rule_id=REGEX_FUNCTION_RULE_ID,
                        relative_file=relative_file,
                        path=f"{function_match.group('name')}(...)",
                        value=f"{function_match.group('name')}(...)",
                        line_start=index,
                        line_end=index,
                        lines=lines,
                        target_slug=target_slug,
                        id_suffix="regex-function",
                        existing_evidence_ids=existing_evidence_ids
                        | {item.id for item in evidence},
                    )
                )

            if len(evidence) >= self._max_symbols_per_file:
                break
        return evidence

    def _collect_node(
        self,
        *,
        node: ast.AST,
        relative_file: str,
        lines: list[str],
        target_slug: str,
        parent_symbols: list[str],
        existing_evidence_ids: set[str],
        evidence: list[Evidence],
    ) -> None:
        if isinstance(node, ast.Import | ast.ImportFrom):
            evidence.append(
                self._import_evidence(
                    node=node,
                    relative_file=relative_file,
                    lines=lines,
                    target_slug=target_slug,
                    existing_evidence_ids=existing_evidence_ids
                    | {item.id for item in evidence},
                )
            )
            return

        if isinstance(node, ast.ClassDef):
            symbol = ".".join([*parent_symbols, node.name])
            evidence.append(
                self._symbol_evidence(
                    node=node,
                    kind="detail_scan_symbol",
                    rule_id=PYTHON_SYMBOL_RULE_ID,
                    symbol=symbol,
                    relative_file=relative_file,
                    lines=lines,
                    target_slug=target_slug,
                    existing_evidence_ids=existing_evidence_ids
                    | {item.id for item in evidence},
                )
            )
            self._collect_decorators(
                node=node,
                symbol=symbol,
                relative_file=relative_file,
                lines=lines,
                target_slug=target_slug,
                existing_evidence_ids=existing_evidence_ids,
                evidence=evidence,
            )
            for child in node.body:
                self._collect_node(
                    node=child,
                    relative_file=relative_file,
                    lines=lines,
                    target_slug=target_slug,
                    parent_symbols=[*parent_symbols, node.name],
                    existing_evidence_ids=existing_evidence_ids,
                    evidence=evidence,
                )
            return

        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            symbol = ".".join([*parent_symbols, node.name])
            evidence.append(
                self._symbol_evidence(
                    node=node,
                    kind="detail_scan_function",
                    rule_id=PYTHON_FUNCTION_RULE_ID,
                    symbol=self._function_signature(node, symbol),
                    relative_file=relative_file,
                    lines=lines,
                    target_slug=target_slug,
                    existing_evidence_ids=existing_evidence_ids
                    | {item.id for item in evidence},
                )
            )
            self._collect_decorators(
                node=node,
                symbol=symbol,
                relative_file=relative_file,
                lines=lines,
                target_slug=target_slug,
                existing_evidence_ids=existing_evidence_ids,
                evidence=evidence,
            )

    def _collect_decorators(
        self,
        *,
        node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
        symbol: str,
        relative_file: str,
        lines: list[str],
        target_slug: str,
        existing_evidence_ids: set[str],
        evidence: list[Evidence],
    ) -> None:
        for decorator in node.decorator_list:
            decorator_name = self._node_text(decorator, lines)
            evidence.append(
                self._base_evidence(
                    kind="detail_scan_decorator",
                    rule_id=PYTHON_DECORATOR_RULE_ID,
                    relative_file=relative_file,
                    path=f"{symbol}@{decorator_name}",
                    value=f"@{decorator_name}",
                    line_start=decorator.lineno,
                    line_end=getattr(decorator, "end_lineno", None)
                    or decorator.lineno,
                    lines=lines,
                    target_slug=target_slug,
                    id_suffix="decorator",
                    existing_evidence_ids=existing_evidence_ids
                    | {item.id for item in evidence},
                )
            )

    def _import_evidence(
        self,
        *,
        node: ast.Import | ast.ImportFrom,
        relative_file: str,
        lines: list[str],
        target_slug: str,
        existing_evidence_ids: set[str],
    ) -> Evidence:
        if isinstance(node, ast.Import):
            value = "import " + ", ".join(alias.name for alias in node.names)
        else:
            module = "." * node.level + (node.module or "")
            names = ", ".join(alias.name for alias in node.names)
            value = f"from {module} import {names}"
        return self._base_evidence(
            kind="detail_scan_import",
            rule_id=PYTHON_IMPORT_RULE_ID,
            relative_file=relative_file,
            path=value,
            value=value,
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", None) or node.lineno,
            lines=lines,
            target_slug=target_slug,
            id_suffix="import",
            existing_evidence_ids=existing_evidence_ids,
        )

    def _symbol_evidence(
        self,
        *,
        node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
        kind: str,
        rule_id: str,
        symbol: str,
        relative_file: str,
        lines: list[str],
        target_slug: str,
        existing_evidence_ids: set[str],
    ) -> Evidence:
        return self._base_evidence(
            kind=kind,
            rule_id=rule_id,
            relative_file=relative_file,
            path=symbol,
            value=symbol,
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", None) or node.lineno,
            lines=lines,
            target_slug=target_slug,
            id_suffix="symbol",
            existing_evidence_ids=existing_evidence_ids,
        )

    def _base_evidence(
        self,
        *,
        kind: str,
        rule_id: str,
        relative_file: str,
        path: str,
        value: str,
        line_start: int,
        line_end: int,
        lines: list[str],
        target_slug: str,
        id_suffix: str,
        existing_evidence_ids: set[str],
    ) -> Evidence:
        evidence_id = _unique_evidence_id(
            base=(
                f"evidence:detail-scan:{target_slug}:"
                f"{_slug(relative_file)}:{line_start}:{id_suffix}"
            ),
            existing_ids=existing_evidence_ids,
        )
        snippet = self._snippet(
            lines,
            line_start=line_start,
            line_end=line_end,
        )
        return Evidence(
            id=evidence_id,
            kind=kind,
            file=relative_file,
            path=self._masking_service.mask_text(path),
            value=self._masking_service.mask_text(value),
            rule_id=rule_id,
            line_start=line_start,
            line_end=line_end,
            snippet=snippet,
        )

    def _snippet(
        self,
        lines: list[str],
        *,
        line_start: int,
        line_end: int,
    ) -> str:
        raw = "\n".join(lines[line_start - 1 : line_end])
        masked = sanitized_python_snippet(self._masking_service.mask_text(raw))
        if len(masked) <= self._max_snippet_chars:
            return masked
        return f"{masked[: self._max_snippet_chars]}...[truncated]"

    def _function_signature(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        symbol: str,
    ) -> str:
        args = [arg.arg for arg in node.args.posonlyargs]
        args.extend(arg.arg for arg in node.args.args)
        args.extend(arg.arg for arg in node.args.kwonlyargs)
        if node.args.vararg is not None:
            args.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg is not None:
            args.append(f"**{node.args.kwarg.arg}")
        prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
        return f"{prefix}{symbol}({', '.join(args)})"

    def _node_text(self, node: ast.AST, lines: list[str]) -> str:
        segment = ast.get_source_segment("\n".join(lines), node)
        if segment:
            return self._masking_service.mask_text(segment)
        return type(node).__name__


def _unique_evidence_id(*, base: str, existing_ids: set[str]) -> str:
    if base not in existing_ids:
        return base
    index = 2
    while f"{base}:{index}" in existing_ids:
        index += 1
    return f"{base}:{index}"


def _slug(value: str) -> str:
    return "".join(
        character.lower() if character.isalnum() else "-"
        for character in value
    ).strip("-")


def sanitized_python_snippet(text: str) -> str:
    """Keep snippets as untrusted data by redacting comments and literals."""

    try:
        tokens = tokenize.generate_tokens(io.StringIO(text).readline)
        safe_tokens = []
        for token in tokens:
            if token.type == tokenize.STRING:
                safe_tokens.append(
                    tokenize.TokenInfo(
                        token.type,
                        '"[STRING]"',
                        token.start,
                        token.end,
                        token.line,
                    )
                )
                continue
            if token.type == tokenize.COMMENT:
                safe_tokens.append(
                    tokenize.TokenInfo(
                        token.type,
                        "# [COMMENT]",
                        token.start,
                        token.end,
                        token.line,
                    )
                )
                continue
            safe_tokens.append(token)
        return tokenize.untokenize(safe_tokens)
    except tokenize.TokenError:
        return _regex_redact_untrusted_text(text)


def _regex_redact_untrusted_text(text: str) -> str:
    without_comments = re.sub(r"#.*", "# [COMMENT]", text)
    return re.sub(
        r"(?s)(\"\"\".*?\"\"\"|'''.*?'''|\".*?\"|'.*?')",
        '"[STRING]"',
        without_comments,
    )
