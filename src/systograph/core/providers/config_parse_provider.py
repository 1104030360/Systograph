"""Parse config files into masked low-level scan facts."""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]

from systograph.core.models.filesystem import FileInventory
from systograph.core.models.scan import (
    ParseIssue,
    ProviderScanResult,
    ScanFact,
)
from systograph.core.models.system_map import Evidence
from systograph.core.services.secret_masking_service import (
    SecretMaskingService,
)

StructuredParser = Callable[[str], Any]
CONFIG_PARSE_STAGE: Literal["config_parse"] = "config_parse"
CONFIG_PROVIDER_NAME = "config"
PARSE_ERROR_RULE_ID = "config_parse_error"
CONFIG_VALUE_KIND = "config_value"
PARSE_ERROR_KIND = "parse_error"
ENV_RULE_ID = "config_env_value_detected"
JSON_RULE_ID = "config_json_value_detected"
TOML_RULE_ID = "config_toml_value_detected"
YAML_RULE_ID = "config_yaml_value_detected"
ENV_ASSIGNMENT_RE = re.compile(
    r"^\s*(?:export\s+)?(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>.*)$"
)
COMPOSE_FILENAMES = {
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
}


class ConfigParseProvider:
    """Read supported config files from deterministic inventory input."""

    def __init__(
        self,
        *,
        masking_service: SecretMaskingService | None = None,
    ) -> None:
        self._masking_service = masking_service or SecretMaskingService()

    def collect(self, inventory: FileInventory) -> ProviderScanResult:
        result = ProviderScanResult()
        project_root = Path(inventory.project_root)

        for record in inventory.files:
            if not self._is_candidate_config_path(record.path):
                continue

            file_path = project_root / record.path
            file_result = self._collect_file(
                file_path,
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
        suffix = file_path.suffix.lower()
        if file_path.name.startswith(".env"):
            return self._collect_env_file(
                file_path,
                relative_path=relative_path,
            )
        if suffix == ".json":
            return self._collect_structured_file(
                file_path,
                relative_path=relative_path,
                rule_id=JSON_RULE_ID,
                format_name="JSON",
                parser=lambda text: json.loads(text),
            )
        if suffix == ".toml":
            return self._collect_structured_file(
                file_path,
                relative_path=relative_path,
                rule_id=TOML_RULE_ID,
                format_name="TOML",
                parser=lambda text: tomllib.loads(text),
            )
        return self._collect_structured_file(
            file_path,
            relative_path=relative_path,
            rule_id=YAML_RULE_ID,
            format_name="YAML",
            parser=lambda text: yaml.safe_load(text),
        )

    def _collect_env_file(
        self,
        file_path: Path,
        *,
        relative_path: str,
    ) -> ProviderScanResult:
        result = ProviderScanResult()
        for line_number, raw_line in enumerate(
            file_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            match = ENV_ASSIGNMENT_RE.match(raw_line)
            if match is None:
                issue = self._build_parse_issue(
                    file=relative_path,
                    message=f"Invalid .env assignment at line {line_number}",
                    line=line_number,
                )
                result.issues.append(issue)
                result.evidence.append(
                    self._build_evidence(
                        file=relative_path,
                        path=f"line[{line_number}]",
                        value=None,
                        kind=PARSE_ERROR_KIND,
                        rule_id=PARSE_ERROR_RULE_ID,
                    )
                )
                continue

            key = match.group("key")
            value = self._normalize_env_value(match.group("value"))
            fact, evidence = self._build_fact_and_evidence(
                file=relative_path,
                path=key,
                key_name=key,
                value=value,
                rule_id=ENV_RULE_ID,
            )
            result.facts.append(fact)
            result.evidence.append(evidence)

        return result

    def _collect_structured_file(
        self,
        file_path: Path,
        *,
        relative_path: str,
        rule_id: str,
        format_name: str,
        parser: StructuredParser,
    ) -> ProviderScanResult:
        result = ProviderScanResult()
        try:
            loaded = parser(file_path.read_text(encoding="utf-8"))
        except (
            json.JSONDecodeError,
            tomllib.TOMLDecodeError,
            yaml.YAMLError,
        ) as exc:
            message = self._format_parse_error_message(format_name, exc)
            issue = self._build_parse_issue(
                file=relative_path,
                message=message,
            )
            result.issues.append(issue)
            result.evidence.append(
                self._build_evidence(
                    file=relative_path,
                    path="$parse_error",
                    value=message,
                    kind=PARSE_ERROR_KIND,
                    rule_id=PARSE_ERROR_RULE_ID,
                )
            )
            return result

        if loaded is None:
            return result

        masked_loaded = self._masking_service.mask_json_like(loaded)
        for scalar_path, key_name, value in self._iter_scalar_entries(
            masked_loaded
        ):
            fact, evidence = self._build_fact_and_evidence(
                file=relative_path,
                path=scalar_path,
                key_name=key_name,
                value=value,
                rule_id=rule_id,
            )
            result.facts.append(fact)
            result.evidence.append(evidence)
        return result

    def _build_fact_and_evidence(
        self,
        *,
        file: str,
        path: str,
        key_name: str | None,
        value: Any,
        rule_id: str,
    ) -> tuple[ScanFact, Evidence]:
        rendered_value = self._render_scalar(value)
        rendered_value = self._masking_service.mask_value(
            rendered_value,
            key=key_name,
        )
        rendered_value = self._masking_service.mask_text(rendered_value)

        fact = ScanFact(
            kind=CONFIG_VALUE_KIND,
            file=file,
            path=path,
            value=rendered_value,
            rule_id=rule_id,
        )
        evidence = self._build_evidence(
            file=file,
            path=path,
            value=rendered_value,
            kind=CONFIG_VALUE_KIND,
            rule_id=rule_id,
        )
        return fact, evidence

    def _build_evidence(
        self,
        *,
        file: str,
        path: str,
        value: str | None,
        kind: str,
        rule_id: str,
    ) -> Evidence:
        digest_source = f"{file}:{path}:{rule_id}".encode()
        digest = hashlib.sha1(digest_source).hexdigest()
        return Evidence(
            id=f"evidence:{rule_id}:{file}:{digest[:12]}",
            kind=kind,
            file=file,
            path=path,
            value=value,
            rule_id=rule_id,
        )

    def _build_parse_issue(
        self,
        *,
        file: str,
        message: str,
        line: int | None = None,
        column: int | None = None,
    ) -> ParseIssue:
        return ParseIssue(
            provider=CONFIG_PROVIDER_NAME,
            scan_stage=CONFIG_PARSE_STAGE,
            file=file,
            message=self._masking_service.mask_text(message),
            rule_id=PARSE_ERROR_RULE_ID,
            line=line,
            column=column,
        )

    def _format_parse_error_message(
        self,
        format_name: str,
        exc: Exception,
    ) -> str:
        problem = getattr(exc, "problem", None)
        message = problem or getattr(exc, "msg", None) or str(exc)
        return f"Failed to parse {format_name} config: {message}"

    def _iter_scalar_entries(
        self,
        value: Any,
        *,
        current_path: str = "",
        key_name: str | None = None,
    ) -> list[tuple[str, str | None, Any]]:
        if isinstance(value, Mapping):
            scalars: list[tuple[str, str | None, Any]] = []
            for child_key, child_value in value.items():
                child_path = (
                    str(child_key)
                    if not current_path
                    else f"{current_path}.{child_key}"
                )
                scalars.extend(
                    self._iter_scalar_entries(
                        child_value,
                        current_path=child_path,
                        key_name=str(child_key),
                    )
                )
            return scalars

        if isinstance(value, list):
            scalars = []
            for index, child_value in enumerate(value):
                child_path = (
                    f"[{index}]"
                    if not current_path
                    else f"{current_path}[{index}]"
                )
                scalars.extend(
                    self._iter_scalar_entries(
                        child_value,
                        current_path=child_path,
                        key_name=key_name,
                    )
                )
            return scalars

        scalar_path = current_path or "$"
        return [(scalar_path, key_name, value)]

    def _normalize_env_value(self, value: str) -> str:
        stripped = value.strip()
        if (
            len(stripped) >= 2
            and stripped[0] == stripped[-1]
            and stripped[0] in {'"', "'"}
        ):
            return stripped[1:-1]
        return stripped

    def _render_scalar(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        try:
            return json.dumps(
                value,
                separators=(",", ":"),
                ensure_ascii=False,
            )
        except TypeError:
            return str(value)

    def _is_candidate_config_path(self, relative_path: str) -> bool:
        file_name = Path(relative_path).name
        if file_name in COMPOSE_FILENAMES:
            return False
        if file_name.startswith(".env"):
            return True

        suffix = Path(relative_path).suffix.lower()
        return suffix in {".json", ".toml", ".yaml", ".yml"}
