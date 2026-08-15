from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from systograph.core.models.ua_analysis import ProjectRelativePath


class UaScriptModel(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        validate_by_alias=True,
        validate_by_name=True,
    )


class UaImportScriptStats(UaScriptModel):
    files_scanned: int = Field(alias="filesScanned", ge=0)
    files_with_imports: int = Field(alias="filesWithImports", ge=0)
    total_edges: int = Field(alias="totalEdges", ge=0)


class UaImportScriptOutput(UaScriptModel):
    script_completed: bool = Field(alias="scriptCompleted")
    stats: UaImportScriptStats
    import_map: dict[ProjectRelativePath, tuple[ProjectRelativePath, ...]] = (
        Field(alias="importMap")
    )


class UaBatchFile(UaScriptModel):
    path: ProjectRelativePath
    language: str
    file_category: str = Field(alias="fileCategory")
    size_lines: int = Field(alias="sizeLines", ge=0)


class UaBatch(UaScriptModel):
    batch_index: int = Field(alias="batchIndex", ge=1)
    files: tuple[UaBatchFile, ...]
    batch_import_data: dict[
        ProjectRelativePath,
        tuple[ProjectRelativePath, ...],
    ] = Field(alias="batchImportData")


class UaBatchScriptOutput(UaScriptModel):
    schema_version: Literal[1] = Field(alias="schemaVersion")
    algorithm: Literal["louvain", "count-fallback"]
    total_files: int = Field(alias="totalFiles", ge=0)
    total_batches: int = Field(alias="totalBatches", ge=0)
    batches: tuple[UaBatch, ...]


class UaNamedSpan(UaScriptModel):
    name: str = Field(min_length=1, max_length=512)
    start_line: int = Field(alias="startLine", ge=1)
    end_line: int = Field(alias="endLine", ge=1)

    @model_validator(mode="after")
    def validate_span_order(self) -> Self:
        if self.end_line < self.start_line:
            raise ValueError("Span end must not precede start")
        return self


class UaExport(UaScriptModel):
    name: str = Field(min_length=1, max_length=512)
    line: int = Field(ge=1)


class UaCall(UaScriptModel):
    caller: str = Field(min_length=1, max_length=512)
    callee: str = Field(min_length=1, max_length=512)
    line_number: int = Field(alias="lineNumber", ge=1)


class UaOptionalSpan(UaScriptModel):
    # Mirrors the UaLineRangeRow contract the projection feeds these
    # into: both endpoints or neither, and never inverted. Entries that
    # break this must fail here so they are quarantined individually
    # instead of exploding at contract-row construction.
    start_line: int | None = Field(default=None, alias="startLine", ge=1)
    end_line: int | None = Field(default=None, alias="endLine", ge=1)

    @model_validator(mode="after")
    def validate_span(self) -> Self:
        if (self.start_line is None) != (self.end_line is None):
            raise ValueError("Span must contain both endpoints")
        if (
            self.start_line is not None
            and self.end_line is not None
            and self.end_line < self.start_line
        ):
            raise ValueError("Span end must not precede start")
        return self


class UaResource(UaOptionalSpan):
    name: str = Field(min_length=1, max_length=512)
    kind: str = Field(min_length=1, max_length=512)


class UaService(UaOptionalSpan):
    # Upstream emits Dockerfile stages as {name, image, ports, startLine,
    # endLine} with no kind; Systograph assigns its own kind at projection.
    name: str = Field(min_length=1, max_length=512)


class UaEndpoint(UaScriptModel):
    path: str = Field(min_length=1, max_length=2048)
    method: str | None = Field(default=None, min_length=1, max_length=32)
    line: int | None = Field(default=None, ge=1)
    start_line: int | None = Field(default=None, alias="startLine", ge=1)
    end_line: int | None = Field(default=None, alias="endLine", ge=1)

    @model_validator(mode="after")
    def validate_span(self) -> Self:
        # The projection derives the row span as (line or startLine,
        # line or endLine or start); reject the shapes that cannot form
        # a valid UaEndpointRow so they are quarantined as entries.
        if self.line is not None:
            return self
        if self.start_line is None and self.end_line is not None:
            raise ValueError("Endpoint end line requires a start line")
        if (
            self.start_line is not None
            and self.end_line is not None
            and self.end_line < self.start_line
        ):
            raise ValueError("Span end must not precede start")
        return self


class UaStructureFile(UaScriptModel):
    path: ProjectRelativePath
    functions: tuple[UaNamedSpan, ...] = ()
    classes: tuple[UaNamedSpan, ...] = ()
    exports: tuple[UaExport, ...] = ()
    call_graph: tuple[UaCall, ...] = Field(default=(), alias="callGraph")
    resources: tuple[UaResource, ...] = ()
    services: tuple[UaService, ...] = ()
    endpoints: tuple[UaEndpoint, ...] = ()


class UaStructureScriptOutput(UaScriptModel):
    script_completed: bool = Field(alias="scriptCompleted")
    files_analyzed: int = Field(alias="filesAnalyzed", ge=0)
    files_skipped: tuple[ProjectRelativePath, ...] = Field(
        alias="filesSkipped"
    )
    results: tuple[UaStructureFile, ...]
