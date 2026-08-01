from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from systograph.core.models.profile_registry_projection import (
    ProfileRegistryProjection,
)
from systograph.core.services.profile_registry_loader import (
    ProfileRegistryLoader,
)
from systograph.core.services.profile_registry_projection_service import (
    ProfileRegistryProjectionService,
)

SCHEMA_PATH = Path("schemas/profile-registry.v1.schema.json")
PROJECTION_FIELDS = {
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


def test_projection_orders_profiles_by_display_order() -> None:
    # Given: a validated registry in reverse source order.
    registry = ProfileRegistryLoader().load_default()
    reversed_registry = registry.model_copy(
        update={"profiles": tuple(reversed(registry.profiles))}
    )

    # When: the projection service creates the consumer contract.
    projection = ProfileRegistryProjectionService().project(reversed_registry)

    # Then: profiles are ordered deterministically by display_order.
    assert tuple(item.display_order for item in projection.profiles) == tuple(
        sorted(item.display_order for item in registry.profiles)
    )


def test_projection_semantically_matches_typed_registry() -> None:
    # Given: the package-bundled typed Metadata registry.
    registry = ProfileRegistryLoader().load_default()

    # When: it is projected to the read-only JSON model.
    projection = ProfileRegistryProjectionService().project(registry)

    # Then: every allowed Metadata field is preserved without runtime fields.
    expected = tuple(
        item.model_dump(mode="json")
        for item in sorted(
            registry.profiles,
            key=lambda profile: profile.display_order,
        )
    )
    actual = tuple(
        item.model_dump(mode="json") for item in projection.profiles
    )
    assert actual == expected
    assert all(set(item) == PROJECTION_FIELDS for item in actual)


def test_projection_serializes_to_schema_valid_json(tmp_path: Path) -> None:
    # Given: a deterministic projection and its checked-in JSON Schema.
    projection = ProfileRegistryProjectionService().project(
        ProfileRegistryLoader().load_default()
    )
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    output_path = tmp_path / "profile_registry.json"

    # When: a consumer writes the model through real JSON serialization.
    output_path.write_text(
        projection.model_dump_json(indent=2),
        encoding="utf-8",
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    # Then: the serialized projection validates without becoming runtime input.
    Draft202012Validator(schema).validate(payload)
    assert ProfileRegistryProjection.model_validate(payload) == projection
