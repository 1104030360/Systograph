from __future__ import annotations

import json
from pathlib import Path

from systograph.core.models.profile_registry_projection import (
    build_profile_registry_schema,
)

SCHEMA_PATH = Path("schemas/profile-registry.v1.schema.json")


def test_checked_in_profile_registry_schema_matches_generated_schema() -> None:
    # Given: the checked-in profile registry schema.
    checked_in = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    # When: Pydantic generates the schema from the projection model.
    generated = build_profile_registry_schema()

    # Then: schema drift fails the contract test.
    assert checked_in == generated


def test_profile_registry_schema_exposes_metadata_fields_only() -> None:
    # Given / When: the generated projection schema is inspected.
    schema = build_profile_registry_schema()
    definitions = schema["$defs"]
    assert isinstance(definitions, dict)
    entry = definitions["ProfileRegistryProjectionEntry"]
    assert isinstance(entry, dict)
    entry_properties = entry["properties"]
    assert isinstance(entry_properties, dict)

    # Then: executable and assessment fields are absent.
    assert set(entry_properties) == {
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
