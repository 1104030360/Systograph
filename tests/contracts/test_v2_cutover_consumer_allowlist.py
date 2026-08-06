from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Literal, NamedTuple

Classification = Literal[
    "migrate",
    "migration_only",
    "remove",
]

PYTHON_ROOT = Path("src/systograph")
FRONTEND_ROOT = Path("frontend/src")
SCRIPT_ROOT = Path("scripts")
FRONTEND_SUFFIXES = frozenset({".json", ".ts", ".tsx"})
SCRIPT_SUFFIXES = frozenset({".sh"})
LEGACY_NAMES = frozenset(
    {
        "RagSystemMap",
        "ExtensionComponent",
        "SystemMapValidationService",
        "new_extension_component",
        # Enum type and member of the legacy mapping value. Without these
        # two names an `Enum.MEMBER.value` indirection reaches the legacy
        # literal while every AST branch below stays blind to it.
        "LegacyManualMappingType",
        "NEW_EXTENSION",
    }
)
LEGACY_LITERALS = frozenset({"ai-system-map/v1", "new_extension_component"})
LEGAL_CLASSIFICATIONS = frozenset({"migrate", "migration_only", "remove"})


class ConsumerRecord(NamedTuple):
    path: str
    symbol: str
    classification: Classification
    removal_plan: str


CONSUMER_ALLOWLIST: tuple[ConsumerRecord, ...] = (
    ConsumerRecord(
        path=(
            "src/systograph/core/services/"
            "legacy_manual_mapping_migration_service.py"
        ),
        symbol="LegacyManualMappingType",
        classification="migration_only",
        removal_plan="Plan 15 Task 3b removes the legacy mapping type enum.",
    ),
    ConsumerRecord(
        path=(
            "src/systograph/core/services/"
            "legacy_manual_mapping_migration_service.py"
        ),
        symbol="NEW_EXTENSION",
        classification="migration_only",
        removal_plan=(
            "Plan 15 Task 3b removes the legacy mapping type enum member."
        ),
    ),
    ConsumerRecord(
        path=(
            "src/systograph/core/services/"
            "legacy_manual_mapping_migration_service.py"
        ),
        symbol="new_extension_component",
        classification="migration_only",
        removal_plan="Plan 15 removes the legacy migration DTO and command.",
    ),
    ConsumerRecord(
        path="src/systograph/cli/map_command.py",
        symbol="ai-system-map/v1",
        classification="migration_only",
        removal_plan="Plan 15 removes the deprecated rejected CLI input.",
    ),
    ConsumerRecord(
        path=(
            "src/systograph/core/services/canonical_output_configuration.py"
        ),
        symbol="ai-system-map/v1",
        classification="migration_only",
        removal_plan=(
            "Refactor 06 removed the v1 write path; the literal now only "
            "backs the legacy_output_not_selectable rejection. Plan 15 "
            "removes it with the deprecated public request value."
        ),
    ),
    ConsumerRecord(
        path="src/systograph/core/models/ai_system_map_v2.py",
        symbol="ai-system-map/v1",
        classification="migration_only",
        removal_plan="Remove provenance literal after v1 read support ends.",
    ),
    ConsumerRecord(
        path="src/systograph/core/models/analysis_history.py",
        symbol="ai-system-map/v1",
        classification="migration_only",
        removal_plan="Plan 15 removes legacy manifest provenance literals.",
    ),
    ConsumerRecord(
        path="src/systograph/core/models/map_build.py",
        symbol="ai-system-map/v1",
        classification="migration_only",
        removal_plan="Plan 15 removes the deprecated rejected request value.",
    ),
    ConsumerRecord(
        path="src/systograph/core/models/profile_signal.py",
        symbol="ai-system-map/v1",
        classification="migration_only",
        removal_plan="Remove provenance literal after v1 read support ends.",
    ),
    ConsumerRecord(
        path="src/systograph/core/models/readiness_report.py",
        symbol="ai-system-map/v1",
        classification="migration_only",
        removal_plan="Remove provenance literal after v1 read support ends.",
    ),
    ConsumerRecord(
        path="src/systograph/core/models/system_map.py",
        symbol="ExtensionComponent",
        classification="migration_only",
        removal_plan=(
            "Remove with the read-only v1 DTO after migration support."
        ),
    ),
    ConsumerRecord(
        path="src/systograph/core/models/system_map.py",
        symbol="RagSystemMap",
        classification="migration_only",
        removal_plan="Remove the read-only v1 DTO after migration support.",
    ),
    ConsumerRecord(
        path="src/systograph/core/models/system_map.py",
        symbol="ai-system-map/v1",
        classification="migration_only",
        removal_plan="Remove the v1 contract badge after migration support.",
    ),
    ConsumerRecord(
        path="src/systograph/core/services/canonical_map_loader.py",
        symbol="RagSystemMap",
        classification="migration_only",
        removal_plan=(
            "Remove when loader no longer supports historical v1 maps."
        ),
    ),
    ConsumerRecord(
        path="src/systograph/core/services/canonical_map_loader.py",
        symbol="SystemMapValidationService",
        classification="migration_only",
        removal_plan=(
            "Remove when loader no longer supports historical v1 maps."
        ),
    ),
    ConsumerRecord(
        path="src/systograph/core/services/canonical_map_loader.py",
        symbol="ai-system-map/v1",
        classification="migration_only",
        removal_plan="Remove the v1 dispatch branch after migration support.",
    ),
    ConsumerRecord(
        path="src/systograph/core/services/system_map_v1_to_v2_adapter.py",
        symbol="ExtensionComponent",
        classification="migration_only",
        removal_plan=(
            "Remove with the v1 migration adapter after support ends."
        ),
    ),
    ConsumerRecord(
        path="src/systograph/core/services/system_map_v1_to_v2_adapter.py",
        symbol="RagSystemMap",
        classification="migration_only",
        removal_plan=(
            "Remove with the v1 migration adapter after support ends."
        ),
    ),
    ConsumerRecord(
        path="src/systograph/core/services/system_map_v1_to_v2_adapter.py",
        symbol="ai-system-map/v1",
        classification="migration_only",
        removal_plan="Remove the adapter source badge after support ends.",
    ),
    ConsumerRecord(
        path="src/systograph/core/services/system_map_validation_service.py",
        symbol="RagSystemMap",
        classification="migration_only",
        removal_plan=(
            "Remove with the read-only v1 validator after support ends."
        ),
    ),
    ConsumerRecord(
        path="src/systograph/core/services/system_map_validation_service.py",
        symbol="SystemMapValidationService",
        classification="migration_only",
        removal_plan="Remove the v1 validator after migration support ends.",
    ),
    ConsumerRecord(
        path=("src/systograph/core/services/viewer_legacy_compatibility.py"),
        symbol="RagSystemMap",
        classification="migration_only",
        removal_plan=(
            "Remove with Viewer v1 compatibility after migration support."
        ),
    ),
    ConsumerRecord(
        path="src/systograph/core/services/viewer_session_service.py",
        symbol="SystemMapValidationService",
        classification="migration_only",
        removal_plan=(
            "Only the optional v1-validator DI passthrough to "
            "CanonicalMapLoader remains; remove it with v1 read support."
        ),
    ),
    ConsumerRecord(
        path="src/systograph/web/legacy_mapping_guards.py",
        symbol="new_extension_component",
        classification="migration_only",
        removal_plan=(
            "Plan 15 Task 3b bullet 5 owns this guard; the mapping owner "
            "decides its fate after the error code converges."
        ),
    ),
    ConsumerRecord(
        path="src/systograph/web/schemas.py",
        symbol="ai-system-map/v1",
        classification="migration_only",
        removal_plan="Plan 15 removes deprecated rejected request values.",
    ),
)


def test_direct_legacy_consumers_match_classified_allowlist() -> None:
    # Given
    allowed = {
        (record.path, record.symbol): record for record in CONSUMER_ALLOWLIST
    }

    # When
    actual = _direct_legacy_hits()
    unknown = sorted(actual - allowed.keys())
    stale = sorted(allowed.keys() - actual)

    # Then
    assert not unknown, f"unclassified direct legacy consumers: {unknown}"
    assert not stale, f"stale legacy consumer records: {stale}"
    assert len(allowed) == len(CONSUMER_ALLOWLIST)
    assert all(
        record.classification in LEGAL_CLASSIFICATIONS
        for record in CONSUMER_ALLOWLIST
    )
    assert all(record.removal_plan.strip() for record in CONSUMER_ALLOWLIST)


def _direct_legacy_hits() -> set[tuple[str, str]]:
    hits = _python_legacy_hits()
    hits.update(_text_legacy_hits(FRONTEND_ROOT, FRONTEND_SUFFIXES))
    hits.update(_text_legacy_hits(SCRIPT_ROOT, SCRIPT_SUFFIXES))
    return hits


def _text_legacy_hits(
    root: Path,
    suffixes: frozenset[str],
) -> set[tuple[str, str]]:
    hits: set[tuple[str, str]] = set()
    for path in sorted(root.rglob("*")):
        if path.suffix not in suffixes:
            continue
        source = path.read_text(encoding="utf-8")
        for symbol in LEGACY_NAMES | LEGACY_LITERALS:
            pattern = rf"(?<![A-Za-z0-9_]){re.escape(symbol)}(?![A-Za-z0-9_])"
            if re.search(pattern, source):
                hits.add((path.as_posix(), symbol))
    return hits


def _python_legacy_hits() -> set[tuple[str, str]]:
    hits: set[tuple[str, str]] = set()
    for path in sorted(PYTHON_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            symbol = _legacy_symbol(node)
            if symbol is not None:
                hits.add((path.as_posix(), symbol))
    return hits


def _legacy_symbol(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name) and node.id in LEGACY_NAMES:
        return node.id
    if isinstance(node, ast.Attribute) and node.attr in LEGACY_NAMES:
        return node.attr
    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        return node.name if node.name in LEGACY_NAMES else None
    if isinstance(node, ast.alias):
        imported_name = node.name.rsplit(".", maxsplit=1)[-1]
        return imported_name if imported_name in LEGACY_NAMES else None
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value in LEGACY_LITERALS
    ):
        return node.value
    return None
