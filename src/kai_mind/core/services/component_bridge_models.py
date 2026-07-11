from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from kai_mind.core.models.scan import ScanFact
from kai_mind.core.models.system_map import UnmappedComponent


@dataclass(frozen=True, slots=True)
class ComponentCandidate:
    slot: str
    kind: str
    name: str
    provider: str | None
    evidence_ids: tuple[str, ...]

    @property
    def id(self) -> str:
        return f"component:{self.slot}:{_slug(self.provider or self.name)}"


@dataclass(frozen=True, slots=True)
class ComponentBridgeCandidateSpec:
    slot: str
    kind: str
    name: str
    provider: str | None

    def materialize(
        self,
        evidence_ids: tuple[str, ...],
    ) -> ComponentCandidate:
        return ComponentCandidate(
            slot=self.slot,
            kind=self.kind,
            name=self.name,
            provider=self.provider,
            evidence_ids=evidence_ids,
        )


@dataclass(frozen=True, slots=True)
class ComponentBridgeRule:
    rule_ids: frozenset[str]
    fact_kinds: frozenset[str]
    candidates: tuple[ComponentBridgeCandidateSpec, ...]
    required_file_tokens: frozenset[str] = frozenset()

    def matches(self, fact: ScanFact) -> bool:
        if (
            fact.rule_id not in self.rule_ids
            or fact.kind not in self.fact_kinds
        ):
            return False
        return self.required_file_tokens <= _tokens(fact.file)


class ComponentBridgeDecisionKind(StrEnum):
    COMPONENT_CANDIDATE = "component_candidate"
    UNMAPPED_REVIEW_ITEM = "unmapped_review_item"
    NON_BASELINE_CAPABILITY_SIGNAL = "non_baseline_capability_signal"
    NO_MATCH = "no_match"


@dataclass(frozen=True, slots=True)
class ComponentBridgeDecision:
    kind: ComponentBridgeDecisionKind
    component_candidates: tuple[ComponentCandidate, ...] = ()
    unmapped_component: UnmappedComponent | None = None


class ComponentBridgeMatcher(Protocol):
    def match(
        self,
        fact: ScanFact,
        *,
        evidence_ids: tuple[str, ...],
    ) -> ComponentBridgeDecision: ...


def _tokens(value: str) -> set[str]:
    return {
        token for token in re.split(r"[^a-zA-Z0-9]+", value.lower()) if token
    }


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")
    return normalized or "unknown"
