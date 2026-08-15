from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from systograph.core.models.inventory_policy import InventoryPolicyAction
from systograph.core.services.scan_inventory_rule_loader import (
    ScanInventoryRuleLoader,
    ScanInventoryRulesError,
    ScanInventoryRulesErrorCode,
)


def _catalog_bytes(
    *,
    pattern: str,
    action: str = "exclude",
) -> bytes:
    return (
        "schema_version = 'scan-inventory-policy/v1'\n"
        "[[path_rules]]\n"
        "inventory_policy_id = 'inventory.test.rule'\n"
        f"action = '{action}'\n"
        f"pattern = '{pattern}'\n"
        "reason = 'build_output'\n"
        "category = 'build'\n"
        "message = 'Build output is excluded by default.'\n"
    ).encode()


def _duplicate_id_catalog_bytes() -> bytes:
    rule = (
        "[[path_rules]]\n"
        "inventory_policy_id = 'inventory.test.duplicate'\n"
        "action = 'exclude'\n"
        "pattern = 'dist/'\n"
        "reason = 'build_output'\n"
        "category = 'build'\n"
        "message = 'Build output is excluded by default.'\n"
    )
    return (
        "schema_version = 'scan-inventory-policy/v1'\n" + rule + rule
    ).encode()


def test_load_default_returns_packaged_catalog_in_source_order() -> None:
    # Given: the package-bundled inventory policy resource.
    loader = ScanInventoryRuleLoader()

    # When: the default catalog is loaded.
    catalog = loader.load_default()

    # Then: its typed contract and source order are preserved.
    assert catalog.schema_version == "scan-inventory-policy/v1"
    assert catalog.catalog_digest.startswith("sha256:")
    assert [rule.inventory_policy_id for rule in catalog.path_rules[:4]] == [
        "inventory.block.tests_directory",
        "inventory.block.test_directory",
        "inventory.block.dunder_tests_directory",
        "inventory.exclude.node_modules",
    ]
    assert catalog.path_rules[0].action == InventoryPolicyAction.BLOCK
    assert catalog.path_rules[3].action == InventoryPolicyAction.EXCLUDE


def test_load_hashes_the_exact_catalog_bytes(tmp_path: Path) -> None:
    # Given: a valid catalog with deterministic UTF-8 bytes.
    catalog_path = tmp_path / "rules.toml"
    raw = _catalog_bytes(pattern="dist/")
    catalog_path.write_bytes(raw)

    # When: the catalog is loaded.
    catalog = ScanInventoryRuleLoader().load(catalog_path)

    # Then: provenance is the SHA-256 of those exact bytes.
    assert catalog.catalog_digest == (
        "sha256:" + hashlib.sha256(raw).hexdigest()
    )


@pytest.mark.parametrize(
    ("raw", "expected_code"),
    [
        (
            b"schema_version = 'scan-inventory-policy/v1'\nunknown = true\n",
            ScanInventoryRulesErrorCode.INVALID,
        ),
        (
            b"schema_version = 'scan-inventory-policy/v2'\n",
            ScanInventoryRulesErrorCode.INVALID,
        ),
        (
            _catalog_bytes(pattern=""),
            ScanInventoryRulesErrorCode.INVALID,
        ),
        (
            _catalog_bytes(pattern="../outside"),
            ScanInventoryRulesErrorCode.INVALID,
        ),
        (
            _catalog_bytes(pattern="!keep.py"),
            ScanInventoryRulesErrorCode.INVALID,
        ),
        (
            _catalog_bytes(pattern="C:\\temp\\file.txt"),
            ScanInventoryRulesErrorCode.INVALID,
        ),
        (
            _catalog_bytes(pattern="dist/", action="review"),
            ScanInventoryRulesErrorCode.INVALID,
        ),
        (
            _duplicate_id_catalog_bytes(),
            ScanInventoryRulesErrorCode.INVALID,
        ),
        (
            b"schema_version = 'scan-inventory-policy/v1'\n[[path_rules]\n",
            ScanInventoryRulesErrorCode.INVALID,
        ),
    ],
)
def test_load_rejects_invalid_catalogs_with_stable_code(
    tmp_path: Path,
    raw: bytes,
    expected_code: ScanInventoryRulesErrorCode,
) -> None:
    # Given: an invalid catalog at a local path that must stay private.
    catalog_path = tmp_path / "private-rules.toml"
    catalog_path.write_bytes(raw)

    # When: the loader parses the invalid boundary input.
    with pytest.raises(ScanInventoryRulesError) as captured:
        ScanInventoryRuleLoader().load(catalog_path)

    # Then: only the stable code is exposed, not path or catalog content.
    assert captured.value.code == expected_code
    assert str(tmp_path) not in str(captured.value)
    assert raw.decode("utf-8", errors="ignore") not in str(captured.value)


def test_load_rejects_missing_catalog_with_stable_code(
    tmp_path: Path,
) -> None:
    # Given: a catalog path that does not exist.
    missing_path = tmp_path / "missing.toml"

    # When: the loader attempts to read it.
    with pytest.raises(ScanInventoryRulesError) as captured:
        ScanInventoryRuleLoader().load(missing_path)

    # Then: the failure is unavailable and does not leak the local path.
    assert captured.value.code == ScanInventoryRulesErrorCode.UNAVAILABLE
    assert str(tmp_path) not in str(captured.value)
