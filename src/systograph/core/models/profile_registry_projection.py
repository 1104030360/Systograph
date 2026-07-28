from __future__ import annotations

from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter

from systograph.core.models.profile_signal import ProfileAxis

JsonObject: TypeAlias = dict[str, JsonValue]
_JSON_OBJECT_ADAPTER = TypeAdapter(JsonObject)


class ProfileRegistryProjectionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ProfileRegistryProjectionEntry(ProfileRegistryProjectionModel):
    profile_id: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9-]*$")
    display_name: str = Field(min_length=1)
    short_label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    primary_axis: ProfileAxis
    secondary_axes: tuple[ProfileAxis, ...]
    display_order: int = Field(ge=0)
    default_uncertainty: str = Field(min_length=1)
    recommended_next_checks: tuple[str, ...]


class ProfileRegistryProjection(ProfileRegistryProjectionModel):
    schema_version: Literal["profile-registry/v1"] = "profile-registry/v1"
    profiles: tuple[ProfileRegistryProjectionEntry, ...] = Field(min_length=1)


def build_profile_registry_schema() -> JsonObject:
    return _JSON_OBJECT_ADAPTER.validate_python(
        ProfileRegistryProjection.model_json_schema()
    )
