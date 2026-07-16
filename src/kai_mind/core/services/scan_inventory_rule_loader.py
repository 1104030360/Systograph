from __future__ import annotations

import hashlib
import tomllib
from importlib import resources
from pathlib import Path

from pydantic import ValidationError

from kai_mind.core.models.errors import (
    ScanInventoryRulesError,
    ScanInventoryRulesErrorCode,
)
from kai_mind.core.models.inventory_policy import ScanInventoryPolicyCatalog

DEFAULT_RESOURCE_NAME = "scan_inventory_rules.toml"
DEFAULT_RESOURCE_PACKAGE = "kai_mind.core.rules"


class ScanInventoryRuleLoader:
    def load_default(self) -> ScanInventoryPolicyCatalog:
        try:
            raw = (
                resources.files(DEFAULT_RESOURCE_PACKAGE)
                .joinpath(DEFAULT_RESOURCE_NAME)
                .read_bytes()
            )
        except (FileNotFoundError, ModuleNotFoundError, OSError) as exc:
            raise ScanInventoryRulesError(
                ScanInventoryRulesErrorCode.UNAVAILABLE
            ) from exc
        return self._parse(raw)

    def load(self, path: Path) -> ScanInventoryPolicyCatalog:
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise ScanInventoryRulesError(
                ScanInventoryRulesErrorCode.UNAVAILABLE
            ) from exc
        return self._parse(raw)

    def _parse(self, raw: bytes) -> ScanInventoryPolicyCatalog:
        try:
            payload = tomllib.loads(raw.decode("utf-8"))
            catalog = ScanInventoryPolicyCatalog.model_validate(payload)
        except (
            UnicodeDecodeError,
            tomllib.TOMLDecodeError,
            ValidationError,
        ) as exc:
            raise ScanInventoryRulesError(
                ScanInventoryRulesErrorCode.INVALID
            ) from exc
        digest = "sha256:" + hashlib.sha256(raw).hexdigest()
        return catalog.model_copy(update={"catalog_digest": digest})


__all__ = [
    "ScanInventoryRuleLoader",
    "ScanInventoryRulesError",
    "ScanInventoryRulesErrorCode",
]
