"""Load package-bundled deterministic provider rule catalogs."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Literal

RULE_PACKAGE = "systograph.core.rules"
DEPENDENCY_RULE_CATALOG = "dependency_manifest_rules.toml"
DOCKER_IMAGE_RULE_CATALOG = "docker_image_rules.toml"
CODE_PATTERN_RULE_CATALOG = "code_pattern_rules.toml"
RISK_HINT_RULE_CATALOG = "risk_hint_rules.toml"
RECOMMENDED_NEXT_CHECK_RULE_CATALOG = "recommended_next_check_rules.toml"


class RuleCatalogError(ValueError):
    """Raised when a provider rule catalog is malformed."""


@dataclass(frozen=True)
class DependencyPackageRule:
    """One dependency package rule for provider-local candidate facts."""

    ecosystem: Literal["python", "node"]
    package: str
    rule_id: str
    match_prefix: bool


@dataclass(frozen=True)
class DependencyRuleCatalog:
    """Dependency rules split by manifest ecosystem."""

    python: tuple[DependencyPackageRule, ...]
    node: tuple[DependencyPackageRule, ...]


@dataclass(frozen=True)
class DockerImageRule:
    """One Docker repository rule for provider-local image facts."""

    repository: str
    rule_id: str


@dataclass(frozen=True)
class CodePatternRule:
    """One source pattern rule emitted as a provider-local scan fact."""

    rule_id: str
    languages: tuple[str, ...]
    extensions: tuple[str, ...]
    regex: re.Pattern[str]
    fact_kind: str
    snippet_group: str


@dataclass(frozen=True)
class RiskHintRuleMetadata:
    """Metadata for one emitted risk hint rule."""

    rule_id: str
    type: str
    default_severity_hint: str
    rationale: str
    uncertainty: str


@dataclass(frozen=True)
class RecommendedNextCheckRuleMetadata:
    """Metadata for one emitted recommended next check."""

    id: str
    default_target_type: str
    reason: str
    action: str


class RuleCatalogLoader:
    """Load and validate deterministic provider rule catalogs."""

    def load_default_dependency_rules(self) -> DependencyRuleCatalog:
        return self.load_dependency_rules(None)

    def load_default_docker_image_rules(self) -> tuple[DockerImageRule, ...]:
        return self.load_docker_image_rules(None)

    def load_default_code_pattern_rules(self) -> tuple[CodePatternRule, ...]:
        return self.load_code_pattern_rules(None)

    def load_default_risk_hint_rules(
        self,
    ) -> tuple[RiskHintRuleMetadata, ...]:
        return self.load_risk_hint_rules(None)

    def load_default_recommended_next_check_rules(
        self,
    ) -> tuple[RecommendedNextCheckRuleMetadata, ...]:
        return self.load_recommended_next_check_rules(None)

    def load_dependency_rules(
        self,
        catalog_path: Path | str | None,
    ) -> DependencyRuleCatalog:
        loaded = self._load_toml(
            catalog_path,
            default_name=DEPENDENCY_RULE_CATALOG,
        )
        self._reject_unknown_sections(loaded, {"python", "node"})
        python_rules = self._load_dependency_section(
            loaded,
            ecosystem="python",
        )
        node_rules = self._load_dependency_section(loaded, ecosystem="node")
        return DependencyRuleCatalog(
            python=tuple(python_rules),
            node=tuple(node_rules),
        )

    def load_docker_image_rules(
        self,
        catalog_path: Path | str | None,
    ) -> tuple[DockerImageRule, ...]:
        loaded = self._load_toml(
            catalog_path,
            default_name=DOCKER_IMAGE_RULE_CATALOG,
        )
        self._reject_unknown_sections(loaded, {"images"})
        entries = self._section_list(loaded, "images")
        repositories: set[str] = set()
        rule_ids: set[str] = set()
        rules: list[DockerImageRule] = []
        for index, entry in enumerate(entries):
            repository = self._required_string(
                entry,
                "repository",
                section=f"images[{index}]",
            ).lower()
            rule_id = self._required_string(
                entry,
                "rule_id",
                section=f"images[{index}]",
            )
            self._reject_duplicate(
                repositories,
                repository,
                label="duplicate repository",
            )
            self._reject_duplicate(
                rule_ids,
                rule_id,
                label="duplicate rule_id",
            )
            rules.append(
                DockerImageRule(repository=repository, rule_id=rule_id)
            )
        return tuple(rules)

    def load_code_pattern_rules(
        self,
        catalog_path: Path | str | None,
    ) -> tuple[CodePatternRule, ...]:
        loaded = self._load_toml(
            catalog_path,
            default_name=CODE_PATTERN_RULE_CATALOG,
        )
        self._reject_unknown_sections(loaded, {"patterns"})
        entries = self._section_list(loaded, "patterns")
        pattern_keys: set[tuple[tuple[str, ...], str]] = set()
        rule_ids: set[str] = set()
        rules: list[CodePatternRule] = []
        for index, entry in enumerate(entries):
            section = f"patterns[{index}]"
            rule_id = self._required_string(
                entry,
                "rule_id",
                section=section,
            )
            fact_kind = self._required_string(entry, "kind", section=section)
            languages = self._required_string_tuple(
                entry,
                "languages",
                section=section,
            )
            extensions = tuple(
                extension.lower()
                for extension in self._required_string_tuple(
                    entry,
                    "extensions",
                    section=section,
                )
            )
            regex_text = self._required_string(entry, "regex", section=section)
            snippet_group = self._required_string(
                entry,
                "snippet_group",
                section=section,
                allow_empty=True,
            )
            self._reject_duplicate(
                rule_ids,
                rule_id,
                label="duplicate rule_id",
            )
            pattern_key = (extensions, regex_text)
            self._reject_duplicate(
                pattern_keys,
                pattern_key,
                label="duplicate pattern",
            )
            try:
                regex = re.compile(regex_text)
            except re.error as exc:
                raise RuleCatalogError(
                    f"{section}.regex failed to compile: {exc}"
                ) from exc
            if snippet_group:
                self._validate_snippet_group(regex, snippet_group, section)
            rules.append(
                CodePatternRule(
                    rule_id=rule_id,
                    languages=languages,
                    extensions=extensions,
                    regex=regex,
                    fact_kind=fact_kind,
                    snippet_group=snippet_group,
                )
            )
        return tuple(rules)

    def load_risk_hint_rules(
        self,
        catalog_path: Path | str | None,
    ) -> tuple[RiskHintRuleMetadata, ...]:
        loaded = self._load_toml(
            catalog_path,
            default_name=RISK_HINT_RULE_CATALOG,
        )
        self._reject_unknown_sections(loaded, {"risk_hints"})
        entries = self._section_list(loaded, "risk_hints")
        rule_ids: set[str] = set()
        rules: list[RiskHintRuleMetadata] = []
        for index, entry in enumerate(entries):
            section = f"risk_hints[{index}]"
            rule_id = self._required_string(
                entry,
                "rule_id",
                section=section,
            )
            self._reject_duplicate(
                rule_ids,
                rule_id,
                label="duplicate rule_id",
            )
            rules.append(
                RiskHintRuleMetadata(
                    rule_id=rule_id,
                    type=self._required_string(
                        entry,
                        "type",
                        section=section,
                    ),
                    default_severity_hint=self._required_string(
                        entry,
                        "default_severity_hint",
                        section=section,
                    ),
                    rationale=self._required_string(
                        entry,
                        "rationale",
                        section=section,
                    ),
                    uncertainty=self._required_string(
                        entry,
                        "uncertainty",
                        section=section,
                    ),
                )
            )
        return tuple(rules)

    def load_recommended_next_check_rules(
        self,
        catalog_path: Path | str | None,
    ) -> tuple[RecommendedNextCheckRuleMetadata, ...]:
        loaded = self._load_toml(
            catalog_path,
            default_name=RECOMMENDED_NEXT_CHECK_RULE_CATALOG,
        )
        self._reject_unknown_sections(loaded, {"recommended_next_checks"})
        entries = self._section_list(loaded, "recommended_next_checks")
        ids: set[str] = set()
        rules: list[RecommendedNextCheckRuleMetadata] = []
        for index, entry in enumerate(entries):
            section = f"recommended_next_checks[{index}]"
            check_id = self._required_string(entry, "id", section=section)
            self._reject_duplicate(ids, check_id, label="duplicate id")
            rules.append(
                RecommendedNextCheckRuleMetadata(
                    id=check_id,
                    default_target_type=self._required_string(
                        entry,
                        "default_target_type",
                        section=section,
                    ),
                    reason=self._required_string(
                        entry,
                        "reason",
                        section=section,
                    ),
                    action=self._required_string(
                        entry,
                        "action",
                        section=section,
                    ),
                )
            )
        return tuple(rules)

    def _load_dependency_section(
        self,
        loaded: Mapping[str, Any],
        *,
        ecosystem: Literal["python", "node"],
    ) -> list[DependencyPackageRule]:
        entries = self._section_list(loaded, ecosystem)
        packages: set[str] = set()
        rules: list[DependencyPackageRule] = []
        for index, entry in enumerate(entries):
            section = f"{ecosystem}[{index}]"
            package = self._required_string(
                entry,
                "package",
                section=section,
            ).lower()
            rule_id = self._required_string(
                entry,
                "rule_id",
                section=section,
            )
            match_prefix = self._required_bool(
                entry,
                "match_prefix",
                section=section,
            )
            self._reject_duplicate(
                packages,
                package,
                label="duplicate package",
            )
            rules.append(
                DependencyPackageRule(
                    ecosystem=ecosystem,
                    package=package,
                    rule_id=rule_id,
                    match_prefix=match_prefix,
                )
            )
        return rules

    def _load_toml(
        self,
        catalog_path: Path | str | None,
        *,
        default_name: str,
    ) -> Mapping[str, Any]:
        try:
            if catalog_path is None:
                text = (
                    resources.files(RULE_PACKAGE)
                    .joinpath(default_name)
                    .read_text(encoding="utf-8")
                )
            else:
                text = Path(catalog_path).read_text(encoding="utf-8")
            loaded = tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            raise RuleCatalogError(
                f"Failed to parse rule catalog: {exc}"
            ) from exc
        except OSError as exc:
            raise RuleCatalogError(
                f"Failed to read rule catalog: {exc}"
            ) from exc

        if not isinstance(loaded, Mapping):
            raise RuleCatalogError("rule catalog root must be a table")
        return loaded

    def _reject_unknown_sections(
        self,
        loaded: Mapping[str, Any],
        allowed_sections: set[str],
    ) -> None:
        unknown_sections = set(loaded) - allowed_sections
        if unknown_sections:
            joined = ", ".join(sorted(unknown_sections))
            raise RuleCatalogError(f"unknown rule catalog section: {joined}")

    def _section_list(
        self,
        loaded: Mapping[str, Any],
        section: str,
    ) -> list[Mapping[str, Any]]:
        raw_entries = loaded.get(section, [])
        if not isinstance(raw_entries, list):
            raise RuleCatalogError(f"{section} must be a list of tables")

        entries: list[Mapping[str, Any]] = []
        for index, raw_entry in enumerate(raw_entries):
            if not isinstance(raw_entry, Mapping):
                raise RuleCatalogError(f"{section}[{index}] must be a table")
            entries.append(raw_entry)
        return entries

    def _required_string(
        self,
        entry: Mapping[str, Any],
        field: str,
        *,
        section: str,
        allow_empty: bool = False,
    ) -> str:
        value = entry.get(field)
        if not isinstance(value, str):
            raise RuleCatalogError(f"{section}.{field} is required")
        if not allow_empty and not value.strip():
            raise RuleCatalogError(f"{section}.{field} cannot be empty")
        return value

    def _required_string_tuple(
        self,
        entry: Mapping[str, Any],
        field: str,
        *,
        section: str,
    ) -> tuple[str, ...]:
        value = entry.get(field)
        if (
            not isinstance(value, Sequence)
            or isinstance(value, str)
            or not value
        ):
            raise RuleCatalogError(f"{section}.{field} must be a string list")

        values: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                raise RuleCatalogError(
                    f"{section}.{field}[{index}] must be a non-empty string"
                )
            values.append(item)
        return tuple(values)

    def _required_bool(
        self,
        entry: Mapping[str, Any],
        field: str,
        *,
        section: str,
    ) -> bool:
        value = entry.get(field)
        if not isinstance(value, bool):
            raise RuleCatalogError(f"{section}.{field} is required")
        return value

    def _reject_duplicate(
        self,
        seen: set[Any],
        value: Any,
        *,
        label: str,
    ) -> None:
        if value in seen:
            raise RuleCatalogError(f"{label}: {value}")
        seen.add(value)

    def _validate_snippet_group(
        self,
        regex: re.Pattern[str],
        snippet_group: str,
        section: str,
    ) -> None:
        if snippet_group not in regex.groupindex:
            raise RuleCatalogError(
                f"{section}.snippet_group is not a named regex group"
            )
