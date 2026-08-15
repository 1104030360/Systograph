"""Detect unsafe secrets and local paths in committed test snapshots."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from systograph.core.services.path_safety_service import contains_local_path
from systograph.core.services.secret_masking_service import (
    SecretMaskingService,
)


@dataclass(frozen=True)
class SnapshotSafetyFinding:
    """One unsafe value class found in a snapshot-like artifact."""

    source: str
    kind: str
    message: str


class SnapshotSafetyError(AssertionError):
    """Raised when a snapshot-like artifact contains unsafe content."""


class SnapshotSafetyService:
    """Scan snapshot-like strings for raw secrets and local machine paths."""

    def __init__(
        self,
        *,
        workspace_root: Path | None = None,
        masking_service: SecretMaskingService | None = None,
    ) -> None:
        self._workspace_root = workspace_root
        self._masking_service = masking_service or SecretMaskingService()

    def scan_json_like(
        self,
        value: Any,
        *,
        source: str,
    ) -> list[SnapshotSafetyFinding]:
        # Scan raw strings (keys included), never the JSON-serialized
        # text: escaping turns a captured "as f:" + newline into the
        # literal `f:\n`, which reads as a Windows drive path and would
        # fail an honest snapshot closed.
        findings: list[SnapshotSafetyFinding] = []
        for text in self._iter_strings(value):
            findings.extend(self.scan_text(text, source=source))
        return findings

    def assert_safe_json_like(
        self,
        value: Any,
        *,
        source: str,
    ) -> None:
        findings = self.scan_json_like(value, source=source)
        if findings:
            summary = ", ".join(
                f"{finding.source}:{finding.kind}" for finding in findings
            )
            raise SnapshotSafetyError(summary)

    def _iter_strings(self, value: Any) -> Iterator[str]:
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for key, child in value.items():
                yield str(key)
                yield from self._iter_strings(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                yield from self._iter_strings(child)
        elif value is not None and not isinstance(value, (int, float, bool)):
            yield json.dumps(value, default=str)

    def scan_text(
        self,
        text: str,
        *,
        source: str,
    ) -> list[SnapshotSafetyFinding]:
        findings: list[SnapshotSafetyFinding] = []
        if self._masking_service.contains_unmasked_secret(text):
            findings.append(
                SnapshotSafetyFinding(
                    source=source,
                    kind="unmasked_secret",
                    message="Snapshot contains an unmasked secret-like value.",
                )
            )
        if contains_local_path(text, workspace_root=self._workspace_root):
            findings.append(
                SnapshotSafetyFinding(
                    source=source,
                    kind="local_path",
                    message="Snapshot contains a local absolute path.",
                )
            )
        return findings

    def assert_safe_text(
        self,
        text: str,
        *,
        source: str,
    ) -> None:
        findings = self.scan_text(text, source=source)
        if findings:
            summary = ", ".join(
                f"{finding.source}:{finding.kind}" for finding in findings
            )
            raise SnapshotSafetyError(summary)
