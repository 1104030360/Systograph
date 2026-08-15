"""Endpoint identity provider: vendor API URLs -> provider-local facts.

責任：找出「沒有 SDK、直接打 API URL」的廠商整合（raw aiohttp/httpx/
requests 風格），輸出專屬 fact kind ``endpoint_vendor``。
呼叫鏈：ProjectScanService.scan_inventory -> collect ->
        ComponentBridgeRegistry（endpoint 分支）。

Only literal URLs in product source and config count. A URL inside a
comment or a documentation file is a mention, not an integration, and
an unknown host produces nothing at all -- a self-hosted
OpenAI-compatible runtime must never be attributed to OpenAI.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path, PurePosixPath
from typing import Final, Literal
from urllib.parse import urlsplit

from systograph.core.models.filesystem import FileInventory
from systograph.core.models.scan import ProviderScanResult, ScanFact
from systograph.core.models.system_map import Evidence
from systograph.core.services.rule_catalog_loader import (
    ENDPOINT_VENDOR_FACT_KIND,
    EndpointCapabilityRule,
    RuleCatalogLoader,
)
from systograph.core.services.secret_masking_service import (
    SecretMaskingService,
)

ENDPOINT_SCAN_STAGE: Literal["code_pattern_scan"] = "code_pattern_scan"
ENDPOINT_PROVIDER_NAME = "endpoint_capability"
DEFAULT_MAX_FILE_SIZE_BYTES: Final = 250_000
DEFAULT_MAX_SNIPPET_CHARS: Final = 200
# Scheme-qualified URLs plus the bare host:port form config files use
# ("OLLAMA_URL=host.docker.internal:11434").
_URL_PATTERN: Final = re.compile(
    r"(?P<url>https?://[^\s\"'`<>)\\\]}]+)"
    r"|(?P<hostport>(?<![\w.:/])[A-Za-z0-9][\w.-]*:\d{2,5}(?:/[^\s\"'`<>)]*)?)"
)
_COMMENT_PREFIXES: Final = ("#", "//", "*", "<!--", "--", ";")
_DOCUMENTATION_SUFFIXES: Final = frozenset(
    {".md", ".mdx", ".rst", ".txt", ".adoc", ".ipynb"}
)
_SCANNED_SUFFIXES: Final = frozenset(
    {
        ".cfg",
        ".conf",
        ".env",
        ".example",
        ".go",
        ".ini",
        ".java",
        ".js",
        ".json",
        ".jsx",
        ".kt",
        ".mjs",
        ".php",
        ".properties",
        ".py",
        ".rb",
        ".rs",
        ".sh",
        ".template",
        ".toml",
        ".ts",
        ".tsx",
        ".vue",
        ".yaml",
        ".yml",
    }
)
_SCANNED_NAMES: Final = frozenset({"dockerfile", ".env", "makefile"})


class EndpointCapabilityProvider:
    """Read inventory files and emit vendor endpoint identity facts."""

    def __init__(
        self,
        *,
        rules: tuple[EndpointCapabilityRule, ...] | None = None,
        masking_service: SecretMaskingService | None = None,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
        max_snippet_chars: int = DEFAULT_MAX_SNIPPET_CHARS,
    ) -> None:
        self._rules = (
            RuleCatalogLoader().load_default_endpoint_capability_rules()
            if rules is None
            else rules
        )
        self._masking_service = masking_service or SecretMaskingService()
        self._max_file_size_bytes = max_file_size_bytes
        self._max_snippet_chars = max(1, max_snippet_chars)

    def collect(self, inventory: FileInventory) -> ProviderScanResult:
        result = ProviderScanResult()
        project_root = Path(inventory.project_root).resolve()
        for record in inventory.files:
            if not self._is_scannable(record.path):
                continue
            if record.size_bytes > self._max_file_size_bytes:
                continue
            file_path = self._resolve_inventory_path(
                project_root,
                record.path,
            )
            if file_path is None:
                continue
            self._collect_file(result, file_path, relative_path=record.path)
        return result

    def _collect_file(
        self,
        result: ProviderScanResult,
        file_path: Path,
        *,
        relative_path: str,
    ) -> None:
        try:
            text = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            # A file the endpoint layer cannot read is reported by the
            # code-pattern provider, which reads the same inventory.
            return
        for line_number, line in enumerate(text.splitlines(), start=1):
            if line.lstrip().startswith(_COMMENT_PREFIXES):
                continue
            for match in _URL_PATTERN.finditer(line):
                target = self._target(
                    match.group("url") or match.group("hostport")
                )
                if target is None:
                    continue
                host, port, path = target
                rule = self._best_rule(host=host, port=port, path=path)
                if rule is None:
                    continue
                self._append(
                    result,
                    file=relative_path,
                    line_number=line_number,
                    line=line,
                    rule=rule,
                    value=host if rule.host is not None else f"{host}:{port}",
                )

    def _target(self, raw: str) -> tuple[str, int | None, str] | None:
        candidate = raw if "//" in raw else f"//{raw}"
        try:
            parts = urlsplit(candidate)
            host = parts.hostname
            port = parts.port
        except ValueError:
            return None
        if not host:
            return None
        return host.lower(), port, parts.path or "/"

    def _best_rule(
        self,
        *,
        host: str,
        port: int | None,
        path: str,
    ) -> EndpointCapabilityRule | None:
        matches = [
            rule
            for rule in self._rules
            if rule.matches(host=host, port=port, path=path)
        ]
        if not matches:
            return None
        return max(matches, key=lambda rule: rule.specificity)

    def _append(
        self,
        result: ProviderScanResult,
        *,
        file: str,
        line_number: int,
        line: str,
        rule: EndpointCapabilityRule,
        value: str,
    ) -> None:
        path = f"line[{line_number}]"
        # The snippet is masked because a literal URL can carry inline
        # credentials (https://user:pass@host/...).
        snippet = self._masking_service.mask_text(
            line.strip()[: self._max_snippet_chars]
        )
        result.facts.append(
            ScanFact(
                kind=ENDPOINT_VENDOR_FACT_KIND,
                file=file,
                path=path,
                value=value,
                rule_id=rule.rule_id,
            )
        )
        result.evidence.append(
            Evidence(
                id=self._evidence_id(file, path, rule.rule_id, value),
                kind=ENDPOINT_VENDOR_FACT_KIND,
                file=file,
                path=path,
                value=value,
                rule_id=rule.rule_id,
                line_start=line_number,
                line_end=line_number,
                snippet=snippet,
                evidence_kind_hint="direct",
            )
        )

    def _is_scannable(self, relative_path: str) -> bool:
        pure = PurePosixPath(relative_path)
        name = pure.name.lower()
        suffix = pure.suffix.lower()
        if suffix in _DOCUMENTATION_SUFFIXES:
            return False
        if name in _SCANNED_NAMES or name.startswith(".env"):
            return True
        return suffix in _SCANNED_SUFFIXES

    def _resolve_inventory_path(
        self,
        project_root: Path,
        record_path: str,
    ) -> Path | None:
        if "\\" in record_path:
            return None
        pure_path = PurePosixPath(record_path)
        if pure_path.is_absolute() or ".." in pure_path.parts:
            return None
        resolved = (project_root / Path(*pure_path.parts)).resolve()
        if not resolved.is_relative_to(project_root):
            return None
        return resolved

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


__all__ = [
    "ENDPOINT_PROVIDER_NAME",
    "ENDPOINT_VENDOR_FACT_KIND",
    "EndpointCapabilityProvider",
]
