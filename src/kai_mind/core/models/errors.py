"""Structured error models for deterministic scanner failures."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ErrorModel(BaseModel):
    """Base model that rejects silent error contract drift."""

    model_config = ConfigDict(extra="forbid")


class PreconditionFailureReason(StrEnum):
    """Fatal reasons detected before provider scanning starts."""

    PROJECT_PATH_NOT_FOUND = "project_path_not_found"
    PROJECT_PATH_NOT_DIRECTORY = "project_path_not_directory"
    PROJECT_PATH_NOT_READABLE = "project_path_not_readable"
    OUTPUT_DIRECTORY_NOT_WRITABLE = "output_directory_not_writable"


class PreconditionError(ErrorModel):
    """Structured data used to render the human-readable error artifact."""

    project_path: str
    failure_reason: PreconditionFailureReason
    scan_stage: Literal["precondition"] = "precondition"
