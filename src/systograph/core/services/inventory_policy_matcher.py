from __future__ import annotations

from dataclasses import dataclass

from pathspec import GitIgnoreSpec

from systograph.core.models.inventory_policy import (
    InventoryPolicyAction,
    InventoryPolicyRule,
    ScanInventoryPolicyCatalog,
)
from systograph.core.services.path_safety_service import (
    normalize_project_relative_path,
)


@dataclass(frozen=True, slots=True)
class InventoryPolicyMatch:
    matched_inventory_policy_ids: tuple[str, ...]
    effective_action: InventoryPolicyAction | None
    effective_inventory_policy_id: str | None
    effective_pattern: str | None
    effective_reason: str | None


@dataclass(frozen=True, slots=True)
class _CompiledRule:
    rule: InventoryPolicyRule
    spec: GitIgnoreSpec


class InventoryPolicyMatcher:
    def __init__(self, catalog: ScanInventoryPolicyCatalog) -> None:
        self._rules = tuple(
            _CompiledRule(
                rule=rule,
                spec=GitIgnoreSpec.from_lines([rule.pattern]),
            )
            for rule in catalog.path_rules
        )

    @property
    def has_include_rules(self) -> bool:
        return any(
            compiled.rule.action == InventoryPolicyAction.INCLUDE
            for compiled in self._rules
        )

    def match(
        self,
        path: str,
        *,
        is_directory: bool = False,
    ) -> InventoryPolicyMatch:
        safe_path = normalize_project_relative_path(
            path.replace("\\", "/").rstrip("/")
        )
        candidate = f"{safe_path}/" if is_directory else safe_path
        matches = tuple(
            compiled.rule
            for compiled in self._rules
            if compiled.spec.match_file(candidate)
        )
        if not matches:
            return InventoryPolicyMatch((), None, None, None, None)
        effective = matches[-1]
        return InventoryPolicyMatch(
            matched_inventory_policy_ids=tuple(
                rule.inventory_policy_id for rule in matches
            ),
            effective_action=effective.action,
            effective_inventory_policy_id=effective.inventory_policy_id,
            effective_pattern=effective.pattern,
            effective_reason=effective.reason,
        )
