from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import product
from types import MappingProxyType
from typing import Any, Literal, TypeAlias, cast

SignalKind: TypeAlias = Literal["call", "import", "factory_inference"]
CallKind: TypeAlias = Literal[
    "constructor",
    "function",
    "method",
    "import",
    "factory",
]

_SIGNAL_KINDS = frozenset({"call", "import", "factory_inference"})
_CALL_KINDS = frozenset(
    {"constructor", "function", "method", "import", "factory"}
)
_EXPECTED_FIELDS = frozenset(
    {
        "from_kinds",
        "to_kinds",
        "signal_kinds",
        "call_kinds",
        "callee_symbols",
        "producer_rule_ids",
        "relationship",
    }
)


class EdgeRelationshipCatalogError(ValueError):
    pass


@dataclass(frozen=True, order=True, slots=True)
class RelationshipDiscriminant:
    from_kind: str
    to_kind: str
    signal_kind: SignalKind
    call_kind: CallKind
    normalized_callee: str
    producer_rule_id: str


@dataclass(frozen=True, order=True, slots=True)
class EdgeRelationshipRule:
    discriminant: RelationshipDiscriminant
    relationship: str


@dataclass(frozen=True, slots=True)
class EdgeRelationshipCatalog:
    rules: tuple[EdgeRelationshipRule, ...]
    _by_discriminant: Mapping[RelationshipDiscriminant, str]

    def lookup(
        self,
        discriminant: RelationshipDiscriminant,
    ) -> str | None:
        return self._by_discriminant.get(discriminant)

    def lookup_values(
        self,
        *,
        from_kind: str,
        to_kind: str,
        signal_kind: SignalKind,
        call_kind: CallKind,
        callee_symbol: str,
        producer_rule_id: str,
    ) -> str | None:
        return self.lookup(
            RelationshipDiscriminant(
                from_kind=_normalize_token(from_kind),
                to_kind=_normalize_token(to_kind),
                signal_kind=signal_kind,
                call_kind=call_kind,
                normalized_callee=normalize_callee_symbol(callee_symbol),
                producer_rule_id=_normalize_token(producer_rule_id),
            )
        )


def parse_edge_relationship_catalog(
    loaded: Mapping[str, Any],
) -> EdgeRelationshipCatalog:
    unknown_sections = set(loaded) - {"relationships"}
    if unknown_sections:
        joined = ", ".join(sorted(unknown_sections))
        raise EdgeRelationshipCatalogError(
            f"unknown rule catalog section: {joined}"
        )
    entries = _relationship_entries(loaded)
    rules_by_key: dict[RelationshipDiscriminant, EdgeRelationshipRule] = {}
    for index, entry in enumerate(entries):
        section = f"relationships[{index}]"
        _validate_fields(entry, section)
        from_kinds = _string_tuple(entry, "from_kinds", section)
        to_kinds = _string_tuple(entry, "to_kinds", section)
        signal_kinds = _signal_kinds(entry, section)
        call_kinds = _call_kinds(entry, section)
        callee_symbols = _string_tuple(entry, "callee_symbols", section)
        producer_rule_ids = _string_tuple(entry, "producer_rule_ids", section)
        relationship = _required_string(entry, "relationship", section)
        for values in product(
            from_kinds,
            to_kinds,
            signal_kinds,
            call_kinds,
            callee_symbols,
            producer_rule_ids,
        ):
            discriminant = RelationshipDiscriminant(
                from_kind=_normalize_token(values[0]),
                to_kind=_normalize_token(values[1]),
                signal_kind=values[2],
                call_kind=values[3],
                normalized_callee=normalize_callee_symbol(values[4]),
                producer_rule_id=_normalize_token(values[5]),
            )
            _validate_signal_call_pair(discriminant, section)
            if discriminant in rules_by_key:
                raise EdgeRelationshipCatalogError(
                    f"duplicate discriminant: {discriminant}"
                )
            rules_by_key[discriminant] = EdgeRelationshipRule(
                discriminant=discriminant,
                relationship=_normalize_token(relationship),
            )
    ordered_rules = tuple(sorted(rules_by_key.values()))
    return EdgeRelationshipCatalog(
        rules=ordered_rules,
        _by_discriminant=MappingProxyType(
            {rule.discriminant: rule.relationship for rule in ordered_rules}
        ),
    )


def normalize_callee_symbol(symbol: str) -> str:
    return _normalize_token(symbol)


def _relationship_entries(
    loaded: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    raw_entries = loaded.get("relationships")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise EdgeRelationshipCatalogError(
            "relationships must be a non-empty list of tables"
        )
    entries: list[Mapping[str, Any]] = []
    for index, entry in enumerate(raw_entries):
        if not isinstance(entry, Mapping):
            raise EdgeRelationshipCatalogError(
                f"relationships[{index}] must be a table"
            )
        entries.append(entry)
    return entries


def _validate_fields(entry: Mapping[str, Any], section: str) -> None:
    unknown_fields = set(entry) - _EXPECTED_FIELDS
    if unknown_fields:
        joined = ", ".join(sorted(unknown_fields))
        raise EdgeRelationshipCatalogError(
            f"{section} has unknown fields: {joined}"
        )


def _string_tuple(
    entry: Mapping[str, Any],
    field: str,
    section: str,
) -> tuple[str, ...]:
    value = entry.get(field)
    if not isinstance(value, Sequence) or isinstance(value, str) or not value:
        raise EdgeRelationshipCatalogError(
            f"{section}.{field} must be a non-empty string list"
        )
    strings: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise EdgeRelationshipCatalogError(
                f"{section}.{field}[{index}] must be a non-empty string"
            )
        strings.append(item)
    normalized = tuple(_normalize_token(item) for item in strings)
    if len(set(normalized)) != len(normalized):
        raise EdgeRelationshipCatalogError(
            f"{section}.{field} contains duplicate values"
        )
    return tuple(strings)


def _signal_kinds(
    entry: Mapping[str, Any],
    section: str,
) -> tuple[SignalKind, ...]:
    values = _string_tuple(entry, "signal_kinds", section)
    if not set(values) <= _SIGNAL_KINDS:
        raise EdgeRelationshipCatalogError(
            f"{section}.signal_kinds contains an unknown signal kind"
        )
    return cast(tuple[SignalKind, ...], values)


def _call_kinds(
    entry: Mapping[str, Any],
    section: str,
) -> tuple[CallKind, ...]:
    values = _string_tuple(entry, "call_kinds", section)
    if not set(values) <= _CALL_KINDS:
        raise EdgeRelationshipCatalogError(
            f"{section}.call_kinds contains an unknown call kind"
        )
    return cast(tuple[CallKind, ...], values)


def _required_string(
    entry: Mapping[str, Any],
    field: str,
    section: str,
) -> str:
    value = entry.get(field)
    if not isinstance(value, str) or not value.strip():
        raise EdgeRelationshipCatalogError(
            f"{section}.{field} must be a non-empty string"
        )
    return value


def _validate_signal_call_pair(
    discriminant: RelationshipDiscriminant,
    section: str,
) -> None:
    allowed = {
        "call": {"constructor", "function", "method"},
        "import": {"import"},
        "factory_inference": {"factory"},
    }
    if discriminant.call_kind not in allowed[discriminant.signal_kind]:
        raise EdgeRelationshipCatalogError(
            f"{section} has incompatible signal_kinds and call_kinds"
        )


def _normalize_token(value: str) -> str:
    normalized = value.strip().casefold()
    if not normalized:
        raise EdgeRelationshipCatalogError("catalog values cannot be empty")
    return normalized
