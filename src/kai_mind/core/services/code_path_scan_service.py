"""Bounded L3 static call-like extraction."""

from __future__ import annotations

import ast
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from kai_mind.core.models.system_map import (
    CodePathStep,
    DetailScanFinding,
    Evidence,
)
from kai_mind.core.services.component_detail_scan_service import (
    _slug,
    _unique_evidence_id,
    sanitized_python_snippet,
)
from kai_mind.core.services.path_safety_service import (
    is_project_relative_posix_path,
)
from kai_mind.core.services.secret_masking_service import SecretMaskingService

PYTHON_CALL_RULE_ID = "detail_scan.python_call_like"


@dataclass(frozen=True)
class CodePathScanExtraction:
    evidence: list[Evidence] = field(default_factory=list)
    findings: list[DetailScanFinding] = field(default_factory=list)
    code_path: list[CodePathStep] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    context_limits: dict[str, object] = field(default_factory=dict)


class CodePathScanService:
    """Extract call-like hints as static observations, not runtime proof."""

    def __init__(
        self,
        *,
        masking_service: SecretMaskingService | None = None,
        max_files_per_target: int = 4,
        max_call_like_hints: int = 24,
        max_snippet_chars: int = 320,
    ) -> None:
        self._masking_service = masking_service or SecretMaskingService()
        self._max_files_per_target = max_files_per_target
        self._max_call_like_hints = max_call_like_hints
        self._max_snippet_chars = max_snippet_chars

    def scan(
        self,
        *,
        project_root: Path,
        relative_files: Sequence[str],
        target_slug: str,
        existing_evidence_ids: set[str],
    ) -> CodePathScanExtraction:
        warnings: list[str] = []
        evidence: list[Evidence] = []
        code_path: list[CodePathStep] = []

        for relative_file, file_path in self._bounded_python_files(
            project_root=project_root,
            relative_files=relative_files,
            warnings=warnings,
        ):
            file_evidence = self._scan_file(
                file_path=file_path,
                relative_file=relative_file,
                target_slug=target_slug,
                existing_evidence_ids=existing_evidence_ids
                | {item.id for item in evidence},
                warnings=warnings,
            )
            evidence.extend(file_evidence)
            if len(evidence) >= self._max_call_like_hints:
                warnings.append("detail_scan_call_hints_truncated")
                evidence = evidence[: self._max_call_like_hints]
                break

        for item in evidence:
            code_path.append(
                CodePathStep(
                    file=item.file or "",
                    symbol=item.path,
                    line_start=item.line_start,
                    line_end=item.line_end,
                    evidence_id=item.id,
                    best_effort=True,
                )
            )

        findings = [
            DetailScanFinding(
                kind="detail_scan_call_like",
                summary=f"Static call-like hint: {item.path}",
                evidence_ids=[item.id],
                best_effort=True,
            )
            for item in evidence
        ]

        return CodePathScanExtraction(
            evidence=evidence,
            findings=findings,
            code_path=code_path,
            warnings=warnings,
            context_limits={
                "max_files_per_target": self._max_files_per_target,
                "max_call_like_hints": self._max_call_like_hints,
                "max_snippet_chars": self._max_snippet_chars,
                "truncated": "detail_scan_call_hints_truncated" in warnings,
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
            if resolved is not None:
                files.append((relative_file, resolved))
        return files

    def _resolve_python_file(
        self,
        project_root: Path,
        relative_file: str,
    ) -> Path | None:
        posix_path = PurePosixPath(relative_file)
        if (
            not is_project_relative_posix_path(relative_file)
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
            tree = ast.parse(source, filename=relative_file)
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            warnings.append(f"detail_scan_parse_skipped:{relative_file}")
            warnings.append(self._masking_service.mask_text(str(exc)))
            return []

        lines = source.splitlines()
        evidence: list[Evidence] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            symbol = _call_symbol(node.func)
            if symbol is None:
                continue
            line_start = node.lineno
            line_end = getattr(node, "end_lineno", None) or line_start
            evidence_id = _unique_evidence_id(
                base=(
                    f"evidence:detail-scan:{target_slug}:"
                    f"{_slug(relative_file)}:{line_start}:call"
                ),
                existing_ids=existing_evidence_ids
                | {item.id for item in evidence},
            )
            evidence.append(
                Evidence(
                    id=evidence_id,
                    kind="detail_scan_call_like",
                    file=relative_file,
                    path=self._masking_service.mask_text(symbol),
                    value=self._masking_service.mask_text(f"{symbol}(...)"),
                    rule_id=PYTHON_CALL_RULE_ID,
                    line_start=line_start,
                    line_end=line_end,
                    snippet=self._snippet(
                        lines,
                        line_start=line_start,
                        line_end=line_end,
                    ),
                )
            )
            if len(evidence) >= self._max_call_like_hints:
                break
        return evidence

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


def _call_symbol(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_symbol(node.value)
        if parent is None:
            return node.attr
        return f"{parent}.{node.attr}"
    if isinstance(node, ast.Call):
        return _call_symbol(node.func)
    return None
