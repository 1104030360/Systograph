"""Pydantic models for internal RAG reference templates."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TemplateModel(BaseModel):
    """Base model that rejects silent template drift."""

    model_config = ConfigDict(extra="forbid")


class TemplateSlot(TemplateModel):
    id: str
    label: str
    required_for_rag_hint: bool
    description: str | None = None


class TemplateFlow(TemplateModel):
    id: str
    slot_order: list[str] = Field(min_length=1)
    description: str | None = None


class RagTemplate(TemplateModel):
    id: str
    version: str
    system_type: str
    allowed_statuses: list[str]
    slots: list[TemplateSlot] = Field(min_length=1)
    flows: list[TemplateFlow] = Field(min_length=1)
