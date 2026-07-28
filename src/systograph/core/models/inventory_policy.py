from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from systograph.core.models.filesystem import SkipReason

WINDOWS_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")


class InventoryPolicyModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class InventoryPolicyAction(StrEnum):
    EXCLUDE = "exclude"
    INCLUDE = "include"


class InventoryPolicyRule(InventoryPolicyModel):
    inventory_policy_id: str
    action: InventoryPolicyAction
    pattern: str
    reason: str
    category: str
    message: str

    @field_validator(
        "inventory_policy_id",
        "reason",
        "category",
        "message",
    )
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("inventory policy text must not be blank")
        return value

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, value: str) -> str:
        pattern = value.strip()
        parts = pattern.removeprefix("/").rstrip("/").split("/")
        if not pattern:
            raise ValueError("inventory policy pattern must not be blank")
        if pattern.startswith("!"):
            raise ValueError("inventory policy action must be explicit")
        if "\\" in pattern or WINDOWS_DRIVE_PATTERN.match(pattern):
            raise ValueError("inventory policy pattern must use POSIX paths")
        if ".." in parts:
            raise ValueError("inventory policy pattern must stay in project")
        return pattern

    @model_validator(mode="after")
    def validate_exclude_reason(self) -> InventoryPolicyRule:
        if self.action == InventoryPolicyAction.EXCLUDE:
            try:
                SkipReason(self.reason)
            except ValueError as exc:
                raise ValueError(
                    "exclude reason must be a supported skip reason"
                ) from exc
        return self


class ScanInventoryPolicyCatalog(InventoryPolicyModel):
    schema_version: Literal["scan-inventory-policy/v1"]
    path_rules: tuple[InventoryPolicyRule, ...]
    catalog_digest: str = ""

    @model_validator(mode="after")
    def validate_unique_ids(self) -> ScanInventoryPolicyCatalog:
        ids = [rule.inventory_policy_id for rule in self.path_rules]
        if len(ids) != len(set(ids)):
            raise ValueError("inventory policy ids must be unique")
        return self
