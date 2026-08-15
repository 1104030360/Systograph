from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Annotated, Literal, Self, assert_never

from pydantic import BaseModel, ConfigDict, Field, model_validator

from systograph.core.models.filesystem import FileInventory
from systograph.core.models.scan import ScanFact
from systograph.core.models.system_map import Evidence

NonEmptyText = Annotated[str, Field(min_length=1)]
Sha256Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
ParityClassification = Literal[
    "equivalent",
    "missing",
    "extra",
    "intentionally_degraded",
]
ParitySource = Literal["ua", "legacy"]


@dataclass(frozen=True, slots=True)
class UaParityContractError(ValueError):
    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class ParityFactProjection:
    source: ParitySource
    provider: str
    fact: ScanFact
    evidence: tuple[Evidence, ...]


class FrozenParityModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ParityFactProvenance(FrozenParityModel):
    source: ParitySource
    provider: NonEmptyText
    rule_id: NonEmptyText
    kind: NonEmptyText
    file: NonEmptyText
    path: NonEmptyText
    evidence_ids: tuple[NonEmptyText, ...]
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)

    @classmethod
    def from_projection(cls, projection: ParityFactProjection) -> Self:
        fact = projection.fact
        if fact.rule_id is None:
            raise UaParityContractError(
                f"{projection.provider} emitted a fact without rule_id: "
                f"{fact.file}"
            )
        if not projection.evidence:
            raise UaParityContractError(
                f"{projection.provider} fact has no evidence: {fact.file}"
            )
        with_span = next(
            (
                evidence
                for evidence in projection.evidence
                if evidence.line_start is not None
                and evidence.line_end is not None
            ),
            None,
        )
        return cls(
            source=projection.source,
            provider=projection.provider,
            rule_id=fact.rule_id,
            kind=fact.kind,
            file=fact.file,
            path=fact.path,
            evidence_ids=tuple(
                evidence.id for evidence in projection.evidence
            ),
            line_start=(
                with_span.line_start if with_span is not None else None
            ),
            line_end=with_span.line_end if with_span is not None else None,
        )

    @model_validator(mode="after")
    def validate_line_range(self) -> Self:
        if (self.line_start is None) != (self.line_end is None):
            raise UaParityContractError(
                "line range must contain both endpoints"
            )
        if (
            self.line_start is not None
            and self.line_end is not None
            and self.line_end < self.line_start
        ):
            raise UaParityContractError(
                "line range end must not precede start"
            )
        return self

    @property
    def sort_key(self) -> tuple[str, ...]:
        return (
            self.provider,
            self.rule_id,
            self.kind,
            self.file,
            str(self.line_start or 0),
            str(self.line_end or 0),
            self.path,
        )

    def has_same_location(self, other: Self) -> bool:
        if self.kind != other.kind or self.file != other.file:
            return False
        if self.line_start is not None or other.line_start is not None:
            return (
                self.line_start == other.line_start
                and self.line_end == other.line_end
            )
        return self.path == other.path


class ParityRuleMapping(FrozenParityModel):
    legacy_rule_id: NonEmptyText
    ua_rule_id: NonEmptyText


class ParityFactComparison(FrozenParityModel):
    classification: ParityClassification
    mapping: ParityRuleMapping | None = None
    legacy: ParityFactProvenance | None = None
    ua: ParityFactProvenance | None = None

    @model_validator(mode="after")
    def validate_classification_shape(self) -> Self:
        match self.classification:
            case "equivalent":
                valid = (
                    self.mapping is not None
                    and self.legacy is not None
                    and self.ua is not None
                )
            case "missing":
                valid = (
                    self.mapping is not None
                    and self.legacy is not None
                    and self.ua is None
                )
            case "extra":
                valid = self.legacy is None and self.ua is not None
            case "intentionally_degraded":
                valid = (
                    self.mapping is None
                    and self.legacy is not None
                    and self.ua is None
                )
            case unreachable:
                assert_never(unreachable)
        if not valid:
            raise UaParityContractError(
                "classification does not match provenance shape"
            )
        return self

    @property
    def sort_key(self) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
        legacy_key = () if self.legacy is None else self.legacy.sort_key
        ua_key = () if self.ua is None else self.ua.sort_key
        return (self.classification, legacy_key, ua_key)


class UaParitySummary(FrozenParityModel):
    equivalent: int = Field(ge=0)
    missing: int = Field(ge=0)
    extra: int = Field(ge=0)
    intentionally_degraded: int = Field(ge=0)

    @classmethod
    def from_comparisons(
        cls,
        comparisons: tuple[ParityFactComparison, ...],
    ) -> Self:
        return cls(
            equivalent=sum(
                item.classification == "equivalent" for item in comparisons
            ),
            missing=sum(
                item.classification == "missing" for item in comparisons
            ),
            extra=sum(item.classification == "extra" for item in comparisons),
            intentionally_degraded=sum(
                item.classification == "intentionally_degraded"
                for item in comparisons
            ),
        )


class UaParityInvocationCounters(FrozenParityModel):
    filesystem_scan: int = Field(ge=0)
    ua_sidecar: int = Field(ge=0)
    parity_providers: int = Field(ge=0)


class UaParityReport(FrozenParityModel):
    schema_version: Literal["systograph-ua-parity/v1"]
    llm_mode: Literal["disabled"]
    inventory_digest: Sha256Digest
    invocations: UaParityInvocationCounters
    summary: UaParitySummary
    comparisons: tuple[ParityFactComparison, ...]

    @classmethod
    def from_one_shot(
        cls,
        inventory: FileInventory,
        comparisons: tuple[ParityFactComparison, ...],
    ) -> Self:
        digest = inventory.final_inventory_digest
        if digest is None:
            payload = tuple(
                (
                    record.path,
                    record.size_bytes,
                    record.size_lines,
                    record.content_fingerprint,
                )
                for record in sorted(
                    inventory.files,
                    key=lambda item: item.path,
                )
            )
            encoded = json.dumps(payload, separators=(",", ":")).encode()
            digest = "sha256:" + hashlib.sha256(encoded).hexdigest()
        return cls(
            schema_version="systograph-ua-parity/v1",
            llm_mode="disabled",
            inventory_digest=digest,
            invocations=UaParityInvocationCounters(
                filesystem_scan=1,
                ua_sidecar=1,
                parity_providers=1,
            ),
            summary=UaParitySummary.from_comparisons(comparisons),
            comparisons=comparisons,
        )
