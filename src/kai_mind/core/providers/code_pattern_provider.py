"""Scan source files for deterministic RAG code pattern signals."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from kai_mind.core.models.filesystem import FileInventory
from kai_mind.core.models.scan import ParseIssue, ProviderScanResult, ScanFact
from kai_mind.core.models.system_map import Evidence
from kai_mind.core.providers.code_patterns import (
    CODE_PATTERN_RULES,
    SOURCE_EXTENSIONS,
    PatternRule,
)
from kai_mind.core.services.secret_masking_service import SecretMaskingService

CODE_PATTERN_SCAN_STAGE: Literal["code_pattern_scan"] = "code_pattern_scan"
CODE_PATTERN_PROVIDER_NAME = "code_pattern"
FILE_SKIPPED_RULE_ID = "code_pattern_file_skipped"
READ_ERROR_RULE_ID = "code_pattern_read_error"
PARSE_ERROR_KIND = "parse_error"
DEFAULT_MAX_FILE_SIZE_BYTES = 250_000
DEFAULT_CONTEXT_LINES = 0
DEFAULT_MAX_SNIPPET_CHARS = 800


class CodePatternProvider:
    """Read source files from inventory and emit provider-local code facts."""

    def __init__(
        self,
        *,
        masking_service: SecretMaskingService | None = None,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
        context_lines: int = DEFAULT_CONTEXT_LINES,
        max_snippet_chars: int = DEFAULT_MAX_SNIPPET_CHARS,
    ) -> None:
        self._masking_service = masking_service or SecretMaskingService()
        self._max_file_size_bytes = max_file_size_bytes
        self._context_lines = max(0, context_lines)
        self._max_snippet_chars = max(1, max_snippet_chars)

    def collect(self, inventory: FileInventory) -> ProviderScanResult:
        result = ProviderScanResult()
        project_root = Path(inventory.project_root)

        for record in inventory.files:
            if not self._is_source_path(record.path):
                continue
            if record.size_bytes > self._max_file_size_bytes:
                self._append_issue(
                    result,
                    file=record.path,
                    path="$file",
                    message=(
                        "Skipped source file: large_file "
                        f"({record.size_bytes} bytes)"
                    ),
                    rule_id=FILE_SKIPPED_RULE_ID,
                )
                continue

            file_result = self._collect_file(
                project_root / record.path,
                relative_path=record.path,
            )
            result.facts.extend(file_result.facts)
            result.evidence.extend(file_result.evidence)
            result.issues.extend(file_result.issues)

        return result

    def _collect_file(
        self,
        file_path: Path,
        *,
        relative_path: str,
    ) -> ProviderScanResult:
        result = ProviderScanResult()
        try:
            text = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            self._append_issue(
                result,
                file=relative_path,
                path="$read_error",
                message=f"Failed to read source file: {exc}",
                rule_id=READ_ERROR_RULE_ID,
            )
            return result

        lines = text.splitlines()
        line_starts = self._line_start_offsets(text)
        for rule in self._rules_for_path(relative_path):
            for match in rule.regex.finditer(text):
                line_number = self._line_number_for_offset(
                    line_starts,
                    match.start(),
                )
                path = f"line[{line_number}]"
                value = self._masking_service.mask_text(match.group(0))
                snippet, line_start, line_end = self._snippet_for_match(
                    lines,
                    line_number=line_number,
                    match_text=value,
                )
                self._append_fact(
                    result,
                    file=relative_path,
                    path=path,
                    value=value,
                    kind=rule.fact_kind,
                    rule_id=rule.rule_id,
                    line_start=line_start,
                    line_end=line_end,
                    snippet=snippet,
                )

        return result

    def _append_fact(
        self,
        result: ProviderScanResult,
        *,
        file: str,
        path: str,
        value: str,
        kind: str,
        rule_id: str,
        line_start: int,
        line_end: int,
        snippet: str,
    ) -> None:
        result.facts.append(
            ScanFact(
                kind=kind,
                file=file,
                path=path,
                value=value,
                rule_id=rule_id,
            )
        )
        result.evidence.append(
            Evidence(
                id=self._evidence_id(file, path, rule_id, value),
                kind=kind,
                file=file,
                path=path,
                value=value,
                rule_id=rule_id,
                line_start=line_start,
                line_end=line_end,
                snippet=snippet,
            )
        )

    def _append_issue(
        self,
        result: ProviderScanResult,
        *,
        file: str,
        path: str,
        message: str,
        rule_id: str,
    ) -> None:
        masked_message = self._masking_service.mask_text(message)
        result.issues.append(
            ParseIssue(
                provider=CODE_PATTERN_PROVIDER_NAME,
                scan_stage=CODE_PATTERN_SCAN_STAGE,
                file=file,
                message=masked_message,
                rule_id=rule_id,
            )
        )
        result.evidence.append(
            Evidence(
                id=self._evidence_id(file, path, rule_id, masked_message),
                kind=PARSE_ERROR_KIND,
                file=file,
                path=path,
                value=masked_message,
                rule_id=rule_id,
            )
        )

    def _snippet_for_match(
        self,
        lines: list[str],
        *,
        line_number: int,
        match_text: str,
    ) -> tuple[str, int, int]:
        line_index = line_number - 1
        start_index = max(0, line_index - self._context_lines)
        end_index = min(len(lines), line_index + self._context_lines + 1)
        raw_snippet = "\n".join(lines[start_index:end_index])
        snippet = self._masking_service.mask_text(raw_snippet)
        if len(snippet) <= self._max_snippet_chars:
            return snippet, start_index + 1, end_index

        match_line = self._masking_service.mask_text(lines[line_index])
        if len(match_line) <= self._max_snippet_chars:
            return match_line, line_number, line_number

        return (
            self._truncate_around_match(match_line, match_text),
            line_number,
            line_number,
        )

    def _truncate_around_match(self, text: str, match_text: str) -> str:
        match_index = text.find(match_text)
        if match_index < 0:
            return text[: self._max_snippet_chars]

        half_window = max(1, (self._max_snippet_chars - len(match_text)) // 2)
        start = max(0, match_index - half_window)
        end = min(len(text), start + self._max_snippet_chars)
        start = max(0, end - self._max_snippet_chars)
        return text[start:end]

    def _line_start_offsets(self, text: str) -> list[int]:
        starts = [0]
        for index, character in enumerate(text):
            if character == "\n":
                starts.append(index + 1)
        return starts

    def _line_number_for_offset(
        self,
        line_starts: list[int],
        offset: int,
    ) -> int:
        line_number = 1
        for index, start in enumerate(line_starts, start=1):
            if start > offset:
                break
            line_number = index
        return line_number

    def _rules_for_path(self, relative_path: str) -> tuple[PatternRule, ...]:
        suffix = Path(relative_path).suffix.lower()
        return tuple(
            rule for rule in CODE_PATTERN_RULES if suffix in rule.extensions
        )

    def _is_source_path(self, relative_path: str) -> bool:
        return Path(relative_path).suffix.lower() in SOURCE_EXTENSIONS

    def _evidence_id(
        self,
        file: str,
        path: str,
        rule_id: str,
        value: str,
    ) -> str:
        digest_source = f"{file}:{path}:{rule_id}:{value}".encode()
        digest = hashlib.sha1(digest_source).hexdigest()
        return f"evidence:{rule_id}:{file}:{digest[:12]}"
