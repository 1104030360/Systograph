"""Models for explicit, opt-in query trace runs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from systograph.core.models.system_map import QueryTraceEvent

TraceRunStatus = Literal[
    "completed",
    "partial",
    "endpoint_not_found",
    "error",
]


class TraceModel(BaseModel):
    """Base model that forbids silent trace contract drift."""

    model_config = ConfigDict(extra="forbid")


class TraceRunResult(TraceModel):
    trace_id: str
    status: TraceRunStatus
    query_sent: bool
    endpoint_id: str
    source_scan_id: str | None = None
    source_build_id: str | None = None
    events: list[QueryTraceEvent] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error_reason: str | None = None
