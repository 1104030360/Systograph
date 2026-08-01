"""Load the packaged transitional profile relationship alias table.

Responsibility: read `profile_relationship_alias.toml` -- the single
source of truth for relationship-name aliasing in the Step 6 profile
relationship gate -- and fail-closed validate that every key is a
profile card's `required_relationship` and every value is a known
FlowDerivation relationship name.
Call chain: ProfileFindingService.__init__ -> load().
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from importlib import resources
from typing import Any

from systograph.core.services.flow_derivation_service import RELATIONSHIPS
from systograph.core.services.profile_rule_definitions import (
    PROFILE_RULE_DEFINITIONS,
)

RULES_PACKAGE = "systograph.core.rules"
ALIAS_RESOURCE = "profile_relationship_alias.toml"
ALIAS_SECTION = "relationship_aliases"


class ProfileRelationshipAliasError(ValueError):
    """Raised when the packaged relationship alias table is malformed."""


class ProfileRelationshipAliasLoader:
    """Load and fail-closed validate the relationship alias table."""

    def load(self) -> Mapping[str, tuple[str, ...]]:
        try:
            text = (
                resources.files(RULES_PACKAGE)
                .joinpath(ALIAS_RESOURCE)
                .read_text(encoding="utf-8")
            )
        except OSError as exc:
            raise ProfileRelationshipAliasError(
                f"failed to read packaged {ALIAS_RESOURCE}: {exc}"
            ) from exc
        return self.parse_text(text)

    def parse_text(self, text: str) -> Mapping[str, tuple[str, ...]]:
        try:
            payload = tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            raise ProfileRelationshipAliasError(
                f"failed to parse {ALIAS_RESOURCE}: {exc}"
            ) from exc
        unknown_sections = set(payload) - {ALIAS_SECTION}
        if unknown_sections:
            joined = ", ".join(sorted(unknown_sections))
            raise ProfileRelationshipAliasError(
                f"{ALIAS_RESOURCE}: unknown section: {joined}"
            )
        entries: Any = payload.get(ALIAS_SECTION, {})
        if not isinstance(entries, Mapping) or not entries:
            raise ProfileRelationshipAliasError(
                f"{ALIAS_RESOURCE}: [{ALIAS_SECTION}] must be a "
                "non-empty table"
            )
        card_relationships = {
            definition.required_relationship
            for definition in PROFILE_RULE_DEFINITIONS
            if definition.required_relationship is not None
        }
        unknown_keys = tuple(
            key for key in entries if key not in card_relationships
        )
        if unknown_keys:
            raise ProfileRelationshipAliasError(
                f"{ALIAS_RESOURCE}: [{ALIAS_SECTION}] unknown alias key "
                f"'{unknown_keys[0]}'; every key must be a profile "
                "card's required_relationship in "
                "profile_rule_definitions.py"
            )
        known_relationships = set(RELATIONSHIPS.values())
        return {
            key: self._alias_names(key, value, known_relationships)
            for key, value in entries.items()
        }

    def _alias_names(
        self,
        key: str,
        value: Any,
        known_relationships: set[str],
    ) -> tuple[str, ...]:
        if (
            not isinstance(value, list)
            or not value
            or any(
                not isinstance(item, str) or not item.strip() for item in value
            )
        ):
            raise ProfileRelationshipAliasError(
                f"{ALIAS_RESOURCE}: [{ALIAS_SECTION}].{key} must be a "
                f"non-empty list of relationship names, got {value!r}"
            )
        unknown = tuple(
            item for item in value if item not in known_relationships
        )
        if unknown:
            raise ProfileRelationshipAliasError(
                f"{ALIAS_RESOURCE}: [{ALIAS_SECTION}].{key} references "
                f"unknown relationship name '{unknown[0]}'; every alias "
                "must be a FlowDerivationService.RELATIONSHIPS name"
            )
        return tuple(value)
