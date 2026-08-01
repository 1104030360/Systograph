from __future__ import annotations

from pathlib import Path

from systograph.core.models.inventory_policy import (
    InventoryPolicyAction,
    ScanInventoryPolicyCatalog,
)
from systograph.core.services.inventory_policy_matcher import (
    InventoryPolicyMatcher,
)
from systograph.core.services.scan_inventory_rule_loader import (
    ScanInventoryRuleLoader,
)


def test_match_uses_ordered_last_rule_for_effective_action(
    tmp_path: Path,
) -> None:
    # Given: a broad exclusion followed by one exact include override.
    catalog = _load_catalog(
        tmp_path,
        """
[[path_rules]]
inventory_policy_id = "inventory.exclude.build"
action = "exclude"
pattern = "build/"
reason = "build_output"
category = "build"
message = "Build output is excluded by default."

[[path_rules]]
inventory_policy_id = "inventory.include.build_keep"
action = "include"
pattern = "build/keep.py"
reason = "explicit_include"
category = "source"
message = "Keep this source file."
""",
    )

    # When: both paths are evaluated by one matcher.
    matcher = InventoryPolicyMatcher(catalog)
    excluded = matcher.match("build/generated.py")
    included = matcher.match("build/keep.py")

    # Then: all matches are auditable and the final source-order rule wins.
    assert excluded.effective_action == InventoryPolicyAction.EXCLUDE
    assert excluded.matched_inventory_policy_ids == (
        "inventory.exclude.build",
    )
    assert included.effective_action == InventoryPolicyAction.INCLUDE
    assert included.matched_inventory_policy_ids == (
        "inventory.exclude.build",
        "inventory.include.build_keep",
    )
    assert (
        included.effective_inventory_policy_id
        == "inventory.include.build_keep"
    )


def test_match_applies_directory_pattern_to_descendants(
    tmp_path: Path,
) -> None:
    # Given: a Gitignore-style directory rule.
    catalog = _load_catalog(
        tmp_path,
        """
[[path_rules]]
inventory_policy_id = "inventory.exclude.node_modules"
action = "exclude"
pattern = "node_modules/"
reason = "dependency_directory"
category = "dependency"
message = "Dependency directories are excluded by default."
""",
    )

    # When: a nested descendant is evaluated.
    result = InventoryPolicyMatcher(catalog).match(
        "packages/web/node_modules/pkg/index.js"
    )

    # Then: the directory policy applies at any project depth.
    assert result.effective_action == InventoryPolicyAction.EXCLUDE
    assert result.effective_inventory_policy_id == (
        "inventory.exclude.node_modules"
    )


def test_match_applies_trailing_slash_rule_to_directory_itself(
    tmp_path: Path,
) -> None:
    catalog = _load_catalog(
        tmp_path,
        """
[[path_rules]]
inventory_policy_id = "inventory.exclude.node_modules"
action = "exclude"
pattern = "node_modules/"
reason = "dependency_directory"
category = "dependency"
message = "Dependency directories are excluded by default."
""",
    )

    result = InventoryPolicyMatcher(catalog).match(
        "node_modules",
        is_directory=True,
    )

    assert result.effective_action == InventoryPolicyAction.EXCLUDE


def test_match_normalizes_windows_separator_but_keeps_case_sensitive(
    tmp_path: Path,
) -> None:
    # Given: a lowercase directory rule and equivalent path separators.
    catalog = _load_catalog(
        tmp_path,
        """
[[path_rules]]
inventory_policy_id = "inventory.exclude.dist"
action = "exclude"
pattern = "dist/"
reason = "build_output"
category = "build"
message = "Build output is excluded by default."
""",
    )
    matcher = InventoryPolicyMatcher(catalog)

    # When: POSIX, Windows-looking and differently cased paths are matched.
    posix = matcher.match("apps/web/dist/bundle.js")
    windows = matcher.match("apps\\web\\dist\\bundle.js")
    different_case = matcher.match("apps/web/Dist/bundle.js")

    # Then: separators normalize identically while case does not.
    assert posix == windows
    assert posix.effective_action == InventoryPolicyAction.EXCLUDE
    assert different_case.effective_action is None


def _load_catalog(
    tmp_path: Path,
    rules: str,
) -> ScanInventoryPolicyCatalog:
    path = tmp_path / "rules.toml"
    path.write_text(
        "schema_version = 'scan-inventory-policy/v1'\n" + rules,
        encoding="utf-8",
    )
    return ScanInventoryRuleLoader().load(path)
