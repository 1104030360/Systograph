"""Parse dependency manifests into low-level candidate facts."""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from packaging.requirements import InvalidRequirement, Requirement

from systograph.core.models.filesystem import FileInventory
from systograph.core.models.scan import (
    ParseIssue,
    ProviderScanResult,
    ScanFact,
)
from systograph.core.models.system_map import Evidence
from systograph.core.services.rule_catalog_loader import (
    DependencyPackageRule,
    RuleCatalogLoader,
)
from systograph.core.services.secret_masking_service import (
    SecretMaskingService,
)

DEPENDENCY_MANIFEST_PARSE_STAGE: Literal["dependency_manifest_parse"] = (
    "dependency_manifest_parse"
)
DEPENDENCY_MANIFEST_PROVIDER_NAME = "dependency_manifest"
DEPENDENCY_MANIFEST_PARSE_ERROR_RULE_ID = "dependency_manifest_parse_error"
DEPENDENCY_MANIFEST_PARSE_ERROR_KIND = "parse_error"
DEPENDENCY_CANDIDATE_KIND = "dependency_candidate"
REQUIREMENTS_FILENAMES = {
    "requirements.txt",
    "requirements.in",
    "requirements.pip",
}
MANIFEST_FILENAMES = REQUIREMENTS_FILENAMES | {
    "pyproject.toml",
    "package.json",
}
PYTHON_NAME_NORMALIZE_RE = re.compile(r"[-_.]+")
PIP_OPTION_PREFIXES = ("-", "--")
VCS_REQUIREMENT_PREFIXES = (
    "git+",
    "hg+",
    "svn+",
    "bzr+",
)


class DependencyManifestProvider:
    """Read dependency manifests from deterministic inventory input."""

    def __init__(
        self,
        *,
        masking_service: SecretMaskingService | None = None,
        rule_catalog_path: Path | str | None = None,
    ) -> None:
        self._masking_service = masking_service or SecretMaskingService()
        self._rule_catalog = RuleCatalogLoader().load_dependency_rules(
            rule_catalog_path,
        )

    def collect(self, inventory: FileInventory) -> ProviderScanResult:
        result = ProviderScanResult()
        project_root = Path(inventory.project_root)

        for record in inventory.files:
            if not self._is_manifest_path(record.path):
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
        file_name = Path(relative_path).name
        if file_name in REQUIREMENTS_FILENAMES:
            return self._collect_requirements_file(
                file_path,
                relative_path=relative_path,
            )
        if file_name == "pyproject.toml":
            return self._collect_pyproject_file(
                file_path,
                relative_path=relative_path,
            )
        return self._collect_package_json_file(
            file_path,
            relative_path=relative_path,
        )

    def _collect_requirements_file(
        self,
        file_path: Path,
        *,
        relative_path: str,
    ) -> ProviderScanResult:
        result = ProviderScanResult()
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            self._append_parse_error(
                result,
                file=relative_path,
                path="$parse_error",
                message=self._format_parse_error_message(
                    "requirements.txt",
                    exc,
                ),
            )
            return result

        for line_number, raw_line in enumerate(lines, start=1):
            line = self._strip_requirement_comment(raw_line).strip()
            if not line:
                continue
            path = f"line[{line_number}]"
            if self._is_unsupported_requirements_line(line):
                self._append_parse_error(
                    result,
                    file=relative_path,
                    path=path,
                    message=(
                        "Unsupported requirements.txt entry "
                        f"at line {line_number}"
                    ),
                    line=line_number,
                )
                continue

            try:
                requirement = Requirement(line)
            except InvalidRequirement:
                self._append_parse_error(
                    result,
                    file=relative_path,
                    path=path,
                    message=(
                        "Failed to parse requirements.txt entry "
                        f"at line {line_number}"
                    ),
                    line=line_number,
                )
                continue

            package_name = self._normalize_python_name(requirement.name)
            self._append_known_package_fact(
                result,
                file=relative_path,
                path=path,
                package_name=package_name,
                ecosystem="python",
            )

        return result

    def _collect_pyproject_file(
        self,
        file_path: Path,
        *,
        relative_path: str,
    ) -> ProviderScanResult:
        result = ProviderScanResult()
        try:
            loaded = tomllib.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            self._append_parse_error(
                result,
                file=relative_path,
                path="$parse_error",
                message=self._format_parse_error_message(
                    "pyproject.toml",
                    exc,
                ),
            )
            return result

        if not isinstance(loaded, Mapping):
            self._append_parse_error(
                result,
                file=relative_path,
                path="$parse_error",
                message="Failed to parse pyproject.toml: root is not a map",
            )
            return result

        project = loaded.get("project")
        if isinstance(project, Mapping):
            self._collect_pep621_dependencies(result, relative_path, project)

        tool = loaded.get("tool")
        poetry = tool.get("poetry") if isinstance(tool, Mapping) else None
        if isinstance(poetry, Mapping):
            self._collect_poetry_dependencies(result, relative_path, poetry)

        return result

    def _collect_pep621_dependencies(
        self,
        result: ProviderScanResult,
        file: str,
        project: Mapping[Any, Any],
    ) -> None:
        dependencies = project.get("dependencies")
        if isinstance(dependencies, list):
            self._collect_python_requirement_list(
                result,
                file=file,
                path_prefix="project.dependencies",
                entries=dependencies,
            )

        optional_dependencies = project.get("optional-dependencies")
        if not isinstance(optional_dependencies, Mapping):
            return

        for group_name, entries in optional_dependencies.items():
            if isinstance(entries, list):
                self._collect_python_requirement_list(
                    result,
                    file=file,
                    path_prefix=(
                        f"project.optional-dependencies.{group_name}"
                    ),
                    entries=entries,
                )

    def _collect_poetry_dependencies(
        self,
        result: ProviderScanResult,
        file: str,
        poetry: Mapping[Any, Any],
    ) -> None:
        dependencies = poetry.get("dependencies")
        if isinstance(dependencies, Mapping):
            self._collect_poetry_dependency_map(
                result,
                file=file,
                path_prefix="tool.poetry.dependencies",
                dependencies=dependencies,
            )

        groups = poetry.get("group")
        if not isinstance(groups, Mapping):
            return

        for group_name, group_data in groups.items():
            if not isinstance(group_data, Mapping):
                continue
            group_dependencies = group_data.get("dependencies")
            if not isinstance(group_dependencies, Mapping):
                continue
            self._collect_poetry_dependency_map(
                result,
                file=file,
                path_prefix=(f"tool.poetry.group.{group_name}.dependencies"),
                dependencies=group_dependencies,
            )

    def _collect_python_requirement_list(
        self,
        result: ProviderScanResult,
        *,
        file: str,
        path_prefix: str,
        entries: list[Any],
    ) -> None:
        for index, entry in enumerate(entries):
            path = f"{path_prefix}[{index}]"
            if not isinstance(entry, str):
                self._append_parse_error(
                    result,
                    file=file,
                    path=path,
                    message=f"Failed to parse dependency entry at {path}",
                )
                continue
            try:
                requirement = Requirement(entry)
            except InvalidRequirement:
                self._append_parse_error(
                    result,
                    file=file,
                    path=path,
                    message=f"Failed to parse dependency entry at {path}",
                )
                continue

            self._append_known_package_fact(
                result,
                file=file,
                path=path,
                package_name=self._normalize_python_name(requirement.name),
                ecosystem="python",
            )

    def _collect_poetry_dependency_map(
        self,
        result: ProviderScanResult,
        *,
        file: str,
        path_prefix: str,
        dependencies: Mapping[Any, Any],
    ) -> None:
        for package_key in dependencies:
            package_name = self._normalize_python_name(str(package_key))
            if package_name == "python":
                continue
            self._append_known_package_fact(
                result,
                file=file,
                path=f"{path_prefix}.{package_key}",
                package_name=package_name,
                ecosystem="python",
            )

    def _collect_package_json_file(
        self,
        file_path: Path,
        *,
        relative_path: str,
    ) -> ProviderScanResult:
        result = ProviderScanResult()
        try:
            loaded = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._append_parse_error(
                result,
                file=relative_path,
                path="$parse_error",
                message=self._format_parse_error_message(
                    "package.json",
                    exc,
                ),
            )
            return result

        if not isinstance(loaded, Mapping):
            self._append_parse_error(
                result,
                file=relative_path,
                path="$parse_error",
                message="Failed to parse package.json: root is not a map",
            )
            return result

        for section_name in ("dependencies", "devDependencies"):
            dependencies = loaded.get(section_name)
            if not isinstance(dependencies, Mapping):
                continue
            for package_key in dependencies:
                package_name = self._normalize_node_name(str(package_key))
                self._append_known_package_fact(
                    result,
                    file=relative_path,
                    path=f"{section_name}.{package_key}",
                    package_name=package_name,
                    ecosystem="node",
                )

        return result

    def _append_known_package_fact(
        self,
        result: ProviderScanResult,
        *,
        file: str,
        path: str,
        package_name: str,
        ecosystem: Literal["python", "node"],
    ) -> None:
        rule = self._match_rule(package_name, ecosystem)
        if rule is None:
            return

        self._append_fact(
            result,
            file=file,
            path=path,
            value=package_name,
            kind=DEPENDENCY_CANDIDATE_KIND,
            rule_id=rule.rule_id,
        )

    def _match_rule(
        self,
        package_name: str,
        ecosystem: Literal["python", "node"],
    ) -> DependencyPackageRule | None:
        rules = self._rules_for_ecosystem(ecosystem)
        for rule in rules:
            if package_name == rule.package:
                return rule
            if rule.match_prefix and self._matches_rule_prefix(
                package_name,
                rule.package,
            ):
                return rule
        return None

    def _rules_for_ecosystem(
        self,
        ecosystem: Literal["python", "node"],
    ) -> tuple[DependencyPackageRule, ...]:
        if ecosystem == "python":
            return self._rule_catalog.python
        return self._rule_catalog.node

    def _matches_rule_prefix(self, package_name: str, prefix: str) -> bool:
        if prefix.endswith("/"):
            return package_name.startswith(prefix)
        return package_name.startswith(f"{prefix}-")

    def _append_parse_error(
        self,
        result: ProviderScanResult,
        *,
        file: str,
        path: str,
        message: str,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        masked_message = self._masking_service.mask_text(message)
        result.issues.append(
            ParseIssue(
                provider=DEPENDENCY_MANIFEST_PROVIDER_NAME,
                scan_stage=DEPENDENCY_MANIFEST_PARSE_STAGE,
                file=file,
                message=masked_message,
                rule_id=DEPENDENCY_MANIFEST_PARSE_ERROR_RULE_ID,
                line=line,
                column=column,
            )
        )
        result.evidence.append(
            Evidence(
                id=self._evidence_id(
                    file,
                    path,
                    DEPENDENCY_MANIFEST_PARSE_ERROR_RULE_ID,
                ),
                kind=DEPENDENCY_MANIFEST_PARSE_ERROR_KIND,
                file=file,
                path=path,
                value=masked_message,
                rule_id=DEPENDENCY_MANIFEST_PARSE_ERROR_RULE_ID,
            )
        )

    def _append_fact(
        self,
        result: ProviderScanResult,
        *,
        file: str,
        path: str,
        value: str,
        kind: str,
        rule_id: str,
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
                id=self._evidence_id(file, path, rule_id),
                kind=kind,
                file=file,
                path=path,
                value=value,
                rule_id=rule_id,
            )
        )

    def _evidence_id(self, file: str, path: str, rule_id: str) -> str:
        digest_source = f"{file}:{path}:{rule_id}".encode()
        digest = hashlib.sha1(digest_source).hexdigest()
        return f"evidence:{rule_id}:{file}:{digest[:12]}"

    def _format_parse_error_message(
        self,
        format_name: str,
        exc: Exception,
    ) -> str:
        problem = getattr(exc, "problem", None)
        message = problem or getattr(exc, "msg", None) or str(exc)
        return f"Failed to parse {format_name}: {message}"

    def _strip_requirement_comment(self, line: str) -> str:
        if line.lstrip().startswith("#"):
            return ""
        return line.split(" #", maxsplit=1)[0]

    def _is_unsupported_requirements_line(self, line: str) -> bool:
        lowered = line.lower()
        return lowered.startswith(PIP_OPTION_PREFIXES) or lowered.startswith(
            VCS_REQUIREMENT_PREFIXES
        )

    def _normalize_python_name(self, name: str) -> str:
        return PYTHON_NAME_NORMALIZE_RE.sub("-", name).lower()

    def _normalize_node_name(self, name: str) -> str:
        return name.lower()

    def _is_manifest_path(self, relative_path: str) -> bool:
        return Path(relative_path).name in MANIFEST_FILENAMES
