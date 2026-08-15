"""Load package-bundled deterministic provider rule catalogs."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Literal

from systograph.core.services.edge_relationship_catalog import (
    EdgeRelationshipCatalog,
    EdgeRelationshipCatalogError,
    parse_edge_relationship_catalog,
)

RULE_PACKAGE = "systograph.core.rules"
DEPENDENCY_RULE_CATALOG = "dependency_manifest_rules.toml"
DOCKER_IMAGE_RULE_CATALOG = "docker_image_rules.toml"
CODE_PATTERN_RULE_CATALOG = "code_pattern_rules.toml"
RISK_HINT_RULE_CATALOG = "risk_hint_rules.toml"
RECOMMENDED_NEXT_CHECK_RULE_CATALOG = "recommended_next_check_rules.toml"
EDGE_RELATIONSHIP_RULE_CATALOG = "edge_relationship_rules.toml"
PACKAGE_CAPABILITY_RULE_CATALOG = "package_capability_rules.toml"
ENDPOINT_CAPABILITY_RULE_CATALOG = "endpoint_capability_rules.toml"
ENDPOINT_RULE_ID_PREFIX = "endpoint_vendor_"
ENDPOINT_VENDOR_FACT_KIND = "endpoint_vendor"
_HOST_PATTERN = re.compile(
    r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
)
_DOTTED_SYMBOL_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$"
)
_UA_RULE_ID_PATTERN = re.compile(r"^ua_[a-z0-9]+(?:_[a-z0-9]+)*$")
_MODULE_SEGMENT_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


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
    symbol: str | None = None
    ua_rule_id: str | None = None


@dataclass(frozen=True)
class EndpointCapabilityRule:
    """One vendor API endpoint -> canonical component identity rule.

    Exactly one of ``host`` (an exact hostname) or ``port`` (any host on
    that port, for local runtimes) selects the match; ``path_prefix``
    narrows a host that serves several capabilities, and the longest
    matching prefix wins.
    """

    rule_id: str
    slot: str
    kind: str
    name: str
    provider: str
    host: str | None = None
    port: int | None = None
    path_prefix: str | None = None

    def matches(self, *, host: str, port: int | None, path: str) -> bool:
        if self.host is not None and host != self.host.lower():
            return False
        if self.port is not None and port != self.port:
            return False
        if self.path_prefix is not None:
            return path.startswith(self.path_prefix)
        return True

    @property
    def specificity(self) -> int:
        return len(self.path_prefix or "")


@dataclass(frozen=True)
class PackageCapabilityRule:
    """One import-module -> canonical component identity rule.

    ``module`` is an import module path as it appears in code: a
    top-level package name (``qdrant_client``, ``PyPDF2``) or a dotted
    submodule prefix (``llama_index.core.memory``) -- never a PyPI
    distribution name. An import fact matches the LONGEST registry key
    that prefixes its dotted module path on segment boundaries, so
    top-level and dotted keys coexist deterministically. Matching is
    case-sensitive, exactly like Python module resolution.
    """

    module: str
    slot: str
    kind: str
    name: str
    provider: str


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

    def load_default_package_capability_rules(
        self,
    ) -> tuple[PackageCapabilityRule, ...]:
        return self.load_package_capability_rules(None)

    def load_default_endpoint_capability_rules(
        self,
    ) -> tuple[EndpointCapabilityRule, ...]:
        return self.load_endpoint_capability_rules(None)

    def load_default_edge_relationship_rules(
        self,
    ) -> EdgeRelationshipCatalog:
        return self.load_edge_relationship_rules(None)

    def load_edge_relationship_rules(
        self,
        catalog_path: Path | str | None,
    ) -> EdgeRelationshipCatalog:
        loaded = self._load_toml(
            catalog_path,
            default_name=EDGE_RELATIONSHIP_RULE_CATALOG,
        )
        try:
            return parse_edge_relationship_catalog(loaded)
        except EdgeRelationshipCatalogError as exc:
            raise RuleCatalogError(str(exc)) from exc

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
        symbols: set[str] = set()
        ua_rule_ids: set[str] = set()
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
            symbol = self._optional_string(
                entry,
                "symbol",
                section=section,
            )
            ua_rule_id = self._optional_string(
                entry,
                "ua_rule_id",
                section=section,
            )
            if symbol is not None:
                if _DOTTED_SYMBOL_PATTERN.fullmatch(symbol) is None:
                    raise RuleCatalogError(
                        f"{section}.symbol must be a dotted identifier"
                    )
                self._reject_duplicate(
                    symbols,
                    symbol,
                    label="duplicate symbol",
                )
            if ua_rule_id is not None:
                if _UA_RULE_ID_PATTERN.fullmatch(ua_rule_id) is None:
                    raise RuleCatalogError(
                        f"{section}.ua_rule_id must use a stable ua_* id"
                    )
                if symbol is None:
                    raise RuleCatalogError(
                        f"{section}.ua_rule_id requires symbol"
                    )
                self._reject_duplicate(
                    ua_rule_ids,
                    ua_rule_id,
                    label="duplicate ua_rule_id",
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
                    symbol=symbol,
                    ua_rule_id=ua_rule_id,
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

    def load_endpoint_capability_rules(
        self,
        catalog_path: Path | str | None,
    ) -> tuple[EndpointCapabilityRule, ...]:
        loaded = self._load_toml(
            catalog_path,
            default_name=ENDPOINT_CAPABILITY_RULE_CATALOG,
        )
        self._reject_unknown_sections(loaded, {"endpoints", "schema_version"})
        entries = self._section_list(loaded, "endpoints")
        rule_ids: set[str] = set()
        rules: list[EndpointCapabilityRule] = []
        for index, entry in enumerate(entries):
            section = f"endpoints[{index}]"
            rule_id = self._required_string(entry, "rule_id", section=section)
            if not rule_id.startswith(ENDPOINT_RULE_ID_PREFIX):
                raise RuleCatalogError(
                    f"{section}.rule_id must start with "
                    f"{ENDPOINT_RULE_ID_PREFIX!r} so endpoint facts can "
                    "never collide with another rule family"
                )
            self._reject_duplicate(
                rule_ids,
                rule_id,
                label="duplicate endpoint rule id",
            )
            host = self._optional_string(entry, "host", section=section)
            port = entry.get("port")
            if port is not None and (
                not isinstance(port, int)
                or isinstance(port, bool)
                or not 1 <= port <= 65535
            ):
                raise RuleCatalogError(f"{section}.port must be a TCP port")
            if (host is None) == (port is None):
                raise RuleCatalogError(
                    f"{section} must set exactly one of host or port"
                )
            if host is not None and not _HOST_PATTERN.match(host):
                raise RuleCatalogError(
                    f"{section}.host must be an exact hostname"
                )
            path_prefix = self._optional_string(
                entry,
                "path_prefix",
                section=section,
            )
            if path_prefix is not None and not path_prefix.startswith("/"):
                raise RuleCatalogError(
                    f"{section}.path_prefix must start with '/'"
                )
            rules.append(
                EndpointCapabilityRule(
                    rule_id=rule_id,
                    host=host.lower() if host is not None else None,
                    port=port,
                    path_prefix=path_prefix,
                    slot=self._required_string(entry, "slot", section=section),
                    kind=self._required_string(entry, "kind", section=section),
                    name=self._required_string(entry, "name", section=section),
                    provider=self._required_string(
                        entry,
                        "provider",
                        section=section,
                    ),
                )
            )
        return tuple(rules)

    def load_package_capability_rules(
        self,
        catalog_path: Path | str | None,
    ) -> tuple[PackageCapabilityRule, ...]:
        loaded = self._load_toml(
            catalog_path,
            default_name=PACKAGE_CAPABILITY_RULE_CATALOG,
        )
        self._reject_unknown_sections(loaded, {"packages"})
        entries = self._section_list(loaded, "packages")
        modules: set[str] = set()
        rules: list[PackageCapabilityRule] = []
        for index, entry in enumerate(entries):
            section = f"packages[{index}]"
            module = self._required_string(entry, "module", section=section)
            if not _is_module_key(module):
                raise RuleCatalogError(
                    f"{section}.module must be a dotted module path of "
                    "Python identifiers"
                )
            self._reject_duplicate(
                modules,
                module,
                label="duplicate module",
            )
            rules.append(
                PackageCapabilityRule(
                    module=module,
                    slot=self._required_string(
                        entry,
                        "slot",
                        section=section,
                    ),
                    kind=self._required_string(
                        entry,
                        "kind",
                        section=section,
                    ),
                    name=self._required_string(
                        entry,
                        "name",
                        section=section,
                    ),
                    provider=self._required_string(
                        entry,
                        "provider",
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

    def _optional_string(
        self,
        entry: Mapping[str, Any],
        field: str,
        *,
        section: str,
    ) -> str | None:
        if field not in entry:
            return None
        value = entry[field]
        if not isinstance(value, str):
            raise RuleCatalogError(f"{section}.{field} must be a string")
        if not value.strip():
            raise RuleCatalogError(f"{section}.{field} cannot be empty")
        return value

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


def _is_module_key(module: str) -> bool:
    """A module key is dot-separated Python identifiers, no empties."""
    return all(
        _MODULE_SEGMENT_PATTERN.fullmatch(segment) is not None
        for segment in module.split(".")
    )
