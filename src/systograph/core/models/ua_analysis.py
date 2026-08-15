from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated, Final, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

from systograph.core.models.filesystem import FileCategory
from systograph.core.services.path_safety_service import (
    is_project_relative_posix_path,
)

UA_REQUEST_SCHEMA_ID: Final = (
    "https://systograph.local/schemas/systograph-ua-request.v1.schema.json"
)
UA_RESULT_SCHEMA_ID: Final = (
    "https://systograph.local/schemas/systograph-ua-result.v1.schema.json"
)
JSON_SCHEMA_DRAFT: Final = "https://json-schema.org/draft/2020-12/schema"


def _validate_project_relative_path(value: str) -> str:
    if not is_project_relative_posix_path(value):
        raise ValueError("Path must be a project-relative POSIX path")
    return value


ProjectRelativePath = Annotated[
    str,
    StringConstraints(min_length=1),
    AfterValidator(_validate_project_relative_path),
]
Sha256Digest = Annotated[
    str,
    StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$"),
]
BoundedName = Annotated[str, StringConstraints(min_length=1, max_length=512)]


class UaContractModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_by_alias=True,
        validate_by_name=True,
        serialize_by_alias=True,
    )


class UaWorkDirectory(UaContractModel):
    location: Literal["system_temporary_directory"]
    cleanup: Literal["after_analysis"]


class UaAnalysisRequestFile(UaContractModel):
    path: ProjectRelativePath
    language: BoundedName
    size_lines: int = Field(ge=0)
    file_category: FileCategory
    digest: Sha256Digest


class UaAnalysisRequest(UaContractModel):
    schema_version: Literal["systograph-ua-request/v1"]
    project_root: str
    inventory_digest: Sha256Digest
    work_dir: UaWorkDirectory
    files: tuple[UaAnalysisRequestFile, ...]

    @field_validator("project_root")
    @classmethod
    def validate_absolute_project_root(cls, value: str) -> str:
        if not value or not (
            PurePosixPath(value).is_absolute()
            or PureWindowsPath(value).is_absolute()
        ):
            raise ValueError("Project root must be an absolute local path")
        return value


class UaImportRow(UaContractModel):
    source_file: ProjectRelativePath
    target_file: ProjectRelativePath


class UaLineRangeRow(UaContractModel):
    file: ProjectRelativePath
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_line_range(self) -> Self:
        if (self.line_start is None) != (self.line_end is None):
            raise ValueError("Line range must contain both endpoints")
        if (
            self.line_start is not None
            and self.line_end is not None
            and self.line_end < self.line_start
        ):
            raise ValueError("Line range end must not precede start")
        return self


class UaSymbolRow(UaLineRangeRow):
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    name: BoundedName
    kind: Literal["function", "class", "export"]


class UaCallRow(UaContractModel):
    file: ProjectRelativePath
    caller: BoundedName
    callee: BoundedName
    line_number: int = Field(ge=1)


class UaResourceRow(UaLineRangeRow):
    name: BoundedName
    kind: BoundedName


class UaEndpointRow(UaLineRangeRow):
    method: (
        Annotated[
            str,
            StringConstraints(min_length=1, max_length=32),
        ]
        | None
    ) = None
    path: Annotated[str, StringConstraints(min_length=1, max_length=2048)]


class UaStructuralResult(UaContractModel):
    imports: tuple[UaImportRow, ...]
    symbols: tuple[UaSymbolRow, ...]
    calls: tuple[UaCallRow, ...]
    resources: tuple[UaResourceRow, ...]
    endpoints: tuple[UaEndpointRow, ...]


class UaWarning(UaContractModel):
    stage: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    message: Annotated[str, StringConstraints(min_length=1, max_length=2048)]


class UaBatchCompletion(UaContractModel):
    batch_index: int = Field(alias="batchIndex", ge=1)
    script_completed: bool = Field(alias="scriptCompleted")
    output_present: bool = Field(alias="outputPresent")
    files_analyzed: int = Field(alias="filesAnalyzed", ge=0)


class UaAnalysisStats(UaContractModel):
    files_scanned: int = Field(alias="filesScanned", ge=0)
    files_with_imports: int = Field(alias="filesWithImports", ge=0)
    total_edges: int = Field(alias="totalEdges", ge=0)
    total_batches: int = Field(alias="totalBatches", ge=0)
    algorithm: Literal["louvain", "count-fallback"]
    files_analyzed: int = Field(alias="filesAnalyzed", ge=0)
    batch_completion: tuple[UaBatchCompletion, ...] = Field(
        alias="batchCompletion"
    )


class UaAnalysisResult(UaContractModel):
    schema_version: Literal["systograph-ua-result/v1"]
    status: Literal["completed"]
    structural: UaStructuralResult
    semantic: None
    warnings: tuple[UaWarning, ...] = Field(max_length=100)
    stats: UaAnalysisStats
    extra: dict[str, JsonValue]
