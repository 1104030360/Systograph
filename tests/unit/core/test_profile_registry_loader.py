from __future__ import annotations

import tomllib
from collections.abc import Callable
from importlib import resources
from pathlib import Path

import pytest

from systograph.core.services.profile_registry_loader import (
    PROFILE_REGISTRY_RESOURCE,
    RULES_PACKAGE,
    ProfileMetadataCoverageError,
    ProfileRegistryError,
    ProfileRegistryLoader,
)
from systograph.core.services.profile_rule_definitions import (
    MVP_CAPABILITY_PROFILE_IDS,
)

ROOT_FIELDS = {"schema_version", "profiles"}
PROFILE_FIELDS = {
    "profile_id",
    "display_name",
    "short_label",
    "description",
    "primary_axis",
    "secondary_axes",
    "display_order",
    "default_uncertainty",
    "recommended_next_checks",
}


def valid_catalog_text(*, omitted_id: str | None = None) -> str:
    lines = ['schema_version = "profile-registry/v1"', ""]
    for index, profile_id in enumerate(MVP_CAPABILITY_PROFILE_IDS):
        if profile_id == omitted_id:
            continue
        lines.extend(
            (
                "[[profiles]]",
                f'profile_id = "{profile_id}"',
                f'display_name = "Profile {index}"',
                f'short_label = "P{index}"',
                f'description = "Profile {index} description."',
                'primary_axis = "grounding"',
                "secondary_axes = []",
                f"display_order = {index * 10}",
                (
                    'default_uncertainty = "Static evidence does not '
                    'confirm runtime behavior."'
                ),
                (
                    'recommended_next_checks = ["Review the runtime '
                    'execution path."]'
                ),
                "",
            )
        )
    return "\n".join(lines)


def write_catalog(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "profile_registry.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_loader_accepts_valid_catalog(tmp_path: Path) -> None:
    # Given: a Systograph-owned catalog covering every active profile id.
    path = write_catalog(tmp_path, valid_catalog_text())

    # When: the dedicated loader parses the catalog boundary.
    registry = ProfileRegistryLoader().load(path)

    # Then: it returns frozen typed metadata in source order.
    assert registry.schema_version == "profile-registry/v1"
    assert tuple(item.profile_id for item in registry.profiles) == (
        MVP_CAPABILITY_PROFILE_IDS
    )
    assert registry.profiles[0].display_name == "Profile 0"


def test_loader_loads_packaged_default_catalog() -> None:
    # Given / When: the loader reads its package-bundled default resource.
    registry = ProfileRegistryLoader().load_default()

    # Then: the package catalog exactly covers the active Python definitions.
    assert tuple(item.profile_id for item in registry.profiles) == (
        MVP_CAPABILITY_PROFILE_IDS
    )


def test_packaged_catalog_contains_metadata_fields_only() -> None:
    # Given: the parsed package-bundled TOML payload.
    text = (
        resources.files(RULES_PACKAGE)
        .joinpath(PROFILE_REGISTRY_RESOURCE)
        .read_text(encoding="utf-8")
    )

    # When: root and profile-table keys are enumerated after TOML parsing.
    payload = tomllib.loads(text)

    # Then: every table exactly matches the allowed Metadata contract.
    assert set(payload) == ROOT_FIELDS
    assert all(
        set(profile) == PROFILE_FIELDS for profile in payload["profiles"]
    )


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (
            lambda text: text.replace(
                'schema_version = "profile-registry/v1"',
                (
                    'schema_version = "profile-registry/v1"\n'
                    "unknown_root = true"
                ),
                1,
            ),
            "extra_forbidden",
        ),
        (
            lambda text: text.replace(
                'display_name = "Profile 0"',
                'display_name = "Profile 0"\nunknown_field = true',
                1,
            ),
            "extra_forbidden",
        ),
        (
            lambda text: text.replace(
                'description = "Profile 0 description."\n',
                "",
                1,
            ),
            "description",
        ),
        (
            lambda text: text.replace(
                'description = "Profile 0 description."',
                'description = " "',
                1,
            ),
            "must not be blank",
        ),
        (
            lambda text: text.replace(
                'primary_axis = "grounding"',
                'primary_axis = "invalid-axis"',
                1,
            ),
            "primary_axis",
        ),
        (
            lambda text: text.replace(
                "display_order = 0",
                'display_order = "first"',
                1,
            ),
            "display_order",
        ),
        (
            lambda text: text.replace(
                'schema_version = "profile-registry/v1"',
                'schema_version = "profile-registry/v2"',
                1,
            ),
            "schema_version",
        ),
    ],
)
def test_loader_rejects_invalid_catalog_shape(
    tmp_path: Path,
    mutate: Callable[[str], str],
    match: str,
) -> None:
    # Given: one malformed field at the TOML trust boundary.
    path = write_catalog(tmp_path, mutate(valid_catalog_text()))

    # When / Then: parsing fails closed with a catalog error.
    with pytest.raises(ProfileRegistryError, match=match):
        ProfileRegistryLoader().load(path)


@pytest.mark.parametrize(
    ("mutated_text", "match"),
    [
        ("[[profiles]\n", "failed to parse"),
        (
            valid_catalog_text().replace(
                'profile_id = "agentic-control"',
                'profile_id = "rag-grounding"',
                1,
            ),
            "duplicate profile_id",
        ),
        (
            valid_catalog_text().replace(
                "display_order = 10",
                "display_order = 0",
                1,
            ),
            "duplicate display_order",
        ),
        (
            valid_catalog_text().replace(
                "secondary_axes = []",
                'secondary_axes = ["grounding"]',
                1,
            ),
            "primary axis",
        ),
        (
            valid_catalog_text().replace(
                "secondary_axes = []",
                'secondary_axes = ["agent_control", "agent_control"]',
                1,
            ),
            "secondary axes must be unique",
        ),
        (
            valid_catalog_text().replace(
                (
                    'recommended_next_checks = ["Review the runtime '
                    'execution path."]'
                ),
                'recommended_next_checks = [" "]',
                1,
            ),
            "recommended next checks must not be blank",
        ),
    ],
)
def test_loader_rejects_invalid_catalog_semantics(
    tmp_path: Path,
    mutated_text: str,
    match: str,
) -> None:
    # Given: malformed TOML or conflicting profile metadata.
    path = write_catalog(tmp_path, mutated_text)

    # When / Then: the loader rejects it before runtime inference.
    with pytest.raises(ProfileRegistryError, match=match):
        ProfileRegistryLoader().load(path)


def test_loader_rejects_incomplete_active_profile_coverage(
    tmp_path: Path,
) -> None:
    # Given: a structurally valid catalog missing one active profile.
    path = write_catalog(
        tmp_path,
        valid_catalog_text(omitted_id=MVP_CAPABILITY_PROFILE_IDS[-1]),
    )

    # When / Then: exact active-id coverage fails with its typed error.
    with pytest.raises(
        ProfileMetadataCoverageError,
        match="coverage mismatch",
    ):
        ProfileRegistryLoader().load(path)


def test_loader_rejects_missing_catalog_path(tmp_path: Path) -> None:
    # Given: a Systograph-owned path that does not exist.
    missing_path = tmp_path / "missing-profile-registry.toml"

    # When / Then: the loader fails closed with a typed read error.
    with pytest.raises(ProfileRegistryError, match="failed to read"):
        ProfileRegistryLoader().load(missing_path)
