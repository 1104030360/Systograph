from __future__ import annotations

import tomllib
from importlib import resources
from pathlib import Path
from typing import Final, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from kai_mind.core.models.profile_signal import ProfileAxis
from kai_mind.core.services.profile_rule_definitions import (
    MVP_CAPABILITY_PROFILE_IDS,
)

RULES_PACKAGE: Final = "kai_mind.core.rules"
PROFILE_REGISTRY_RESOURCE: Final = "profile_registry.toml"
PROFILE_REGISTRY_SCHEMA_VERSION: Final = "profile-registry/v1"


class ProfileRegistryError(ValueError):
    reason: str

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class ProfileMetadataCoverageError(ProfileRegistryError):
    expected_ids: tuple[str, ...]
    actual_ids: tuple[str, ...]

    def __init__(
        self,
        *,
        expected_ids: tuple[str, ...],
        actual_ids: tuple[str, ...],
    ) -> None:
        self.expected_ids = expected_ids
        self.actual_ids = actual_ids
        missing = tuple(sorted(set(expected_ids) - set(actual_ids)))
        extra = tuple(sorted(set(actual_ids) - set(expected_ids)))
        super().__init__(
            "profile metadata coverage mismatch: "
            f"missing={missing!r}, extra={extra!r}"
        )


class ProfileMetadataEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_id: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9-]*$")
    display_name: str = Field(min_length=1)
    short_label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    primary_axis: ProfileAxis
    secondary_axes: tuple[ProfileAxis, ...]
    display_order: int = Field(ge=0)
    default_uncertainty: str = Field(min_length=1)
    recommended_next_checks: tuple[str, ...]

    @field_validator(
        "profile_id",
        "display_name",
        "short_label",
        "description",
        "default_uncertainty",
    )
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise PydanticCustomError(
                "blank_profile_metadata",
                "profile metadata strings must not be blank",
            )
        return stripped

    @field_validator("recommended_next_checks")
    @classmethod
    def strip_recommended_checks(
        cls,
        values: tuple[str, ...],
    ) -> tuple[str, ...]:
        stripped = tuple(value.strip() for value in values)
        if any(not value for value in stripped):
            raise PydanticCustomError(
                "blank_recommended_next_check",
                "recommended next checks must not be blank",
            )
        return stripped

    @model_validator(mode="after")
    def validate_secondary_axes(self) -> ProfileMetadataEntry:
        if len(set(self.secondary_axes)) != len(self.secondary_axes):
            raise PydanticCustomError(
                "duplicate_secondary_axis",
                "secondary axes must be unique",
            )
        if self.primary_axis in self.secondary_axes:
            raise PydanticCustomError(
                "primary_axis_repeated",
                "secondary axes must not contain the primary axis",
            )
        return self


class ProfileMetadataRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["profile-registry/v1"]
    profiles: tuple[ProfileMetadataEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_profiles(self) -> ProfileMetadataRegistry:
        profile_ids = tuple(item.profile_id for item in self.profiles)
        if len(set(profile_ids)) != len(profile_ids):
            raise PydanticCustomError(
                "duplicate_profile_id",
                "duplicate profile_id",
            )
        display_orders = tuple(item.display_order for item in self.profiles)
        if len(set(display_orders)) != len(display_orders):
            raise PydanticCustomError(
                "duplicate_display_order",
                "duplicate display_order",
            )
        return self

    def metadata_for(self, profile_id: str) -> ProfileMetadataEntry:
        for item in self.profiles:
            if item.profile_id == profile_id:
                return item
        raise ProfileMetadataCoverageError(
            expected_ids=(profile_id,),
            actual_ids=tuple(item.profile_id for item in self.profiles),
        )

    def require_profile_ids(self, expected_ids: tuple[str, ...]) -> Self:
        actual_ids = tuple(item.profile_id for item in self.profiles)
        if set(actual_ids) != set(expected_ids):
            raise ProfileMetadataCoverageError(
                expected_ids=expected_ids,
                actual_ids=actual_ids,
            )
        return self


class ProfileRegistryLoader:
    def load_default(self) -> ProfileMetadataRegistry:
        try:
            text = (
                resources.files(RULES_PACKAGE)
                .joinpath(PROFILE_REGISTRY_RESOURCE)
                .read_text(encoding="utf-8")
            )
        except OSError as exc:
            raise ProfileRegistryError(
                f"failed to read packaged profile registry: {exc}"
            ) from exc
        return self._parse(text)

    def load(self, catalog_path: Path) -> ProfileMetadataRegistry:
        try:
            text = catalog_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ProfileRegistryError(
                f"failed to read profile registry: {exc}"
            ) from exc
        return self._parse(text)

    @staticmethod
    def _parse(text: str) -> ProfileMetadataRegistry:
        try:
            payload = tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            raise ProfileRegistryError(
                f"failed to parse profile registry: {exc}"
            ) from exc
        try:
            registry = ProfileMetadataRegistry.model_validate(payload)
        except ValidationError as exc:
            raise ProfileRegistryError(
                f"invalid profile registry: {exc}"
            ) from exc
        return registry.require_profile_ids(MVP_CAPABILITY_PROFILE_IDS)
