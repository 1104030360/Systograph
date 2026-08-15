from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal, Self, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

NonEmptyText: TypeAlias = Annotated[str, Field(min_length=1)]
IdentityNamespace: TypeAlias = Annotated[
    str,
    Field(pattern=r"^[a-z][a-z0-9_]*$"),
]


class FrozenStructuralModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceSpan(FrozenStructuralModel):
    file: NonEmptyText
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_lines(self) -> Self:
        if (self.line_start is None) != (self.line_end is None):
            raise ValueError("line_start and line_end must both be present")
        if (
            self.line_start is not None
            and self.line_end is not None
            and self.line_end < self.line_start
        ):
            raise ValueError("line_end must not precede line_start")
        return self


class StructuralFactModel(FrozenStructuralModel):
    identity_namespace: IdentityNamespace

    @property
    def stable_id(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        return f"{self.identity_namespace}:sha256:{digest}"

    @property
    def sort_key(self) -> tuple[str, str]:
        return (self.identity_namespace, self.stable_id)


class CallStructuralFact(StructuralFactModel):
    fact_type: Literal["call"] = "call"
    caller: NonEmptyText
    callee: NonEmptyText
    span: SourceSpan


class ImportStructuralFact(StructuralFactModel):
    fact_type: Literal["import"] = "import"
    import_scope: Literal["internal", "external"]
    module: NonEmptyText
    symbol: NonEmptyText | None = None
    alias: NonEmptyText | None = None
    span: SourceSpan


class SymbolStructuralFact(StructuralFactModel):
    fact_type: Literal["symbol"] = "symbol"
    symbol: NonEmptyText
    symbol_kind: Literal["function", "class", "export"]
    span: SourceSpan


class FactoryInferenceStep(FrozenStructuralModel):
    hop: int = Field(ge=0)
    factory: NonEmptyText
    resolution: Literal[
        "return_annotation",
        "return_construction",
        "delegate_call",
        "registry_entry",
    ]
    span: SourceSpan


class FactoryInferenceStructuralFact(StructuralFactModel):
    fact_type: Literal["factory_inference"] = "factory_inference"
    caller: NonEmptyText
    factory: NonEmptyText
    constructed_symbol: NonEmptyText
    call_span: SourceSpan
    provenance: Annotated[
        tuple[FactoryInferenceStep, ...],
        Field(min_length=1),
    ]


StructuralFact: TypeAlias = Annotated[
    CallStructuralFact
    | ImportStructuralFact
    | SymbolStructuralFact
    | FactoryInferenceStructuralFact,
    Field(discriminator="fact_type"),
]
