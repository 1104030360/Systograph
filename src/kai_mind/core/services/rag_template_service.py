"""Load and validate built-in RAG reference templates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Literal

from pydantic import ValidationError

from kai_mind.core.models.template import RagTemplate

BUILTIN_TEMPLATE_ID: Final = "rag-core-v1"
EXPECTED_ALLOWED_STATUSES: Final = [
    "detected",
    "missing",
    "not_configured",
    "not_applicable",
]
DEFAULT_TEMPLATE_DIR: Final = Path(__file__).resolve().parents[1] / "templates"


class RagTemplateValidationError(ValueError):
    """Raised when a RAG reference template is invalid."""


@dataclass(frozen=True, slots=True)
class RagTemplateBoundaryMetadata:
    template_id: str
    template_input_kind: Literal["legacy_template_input"]
    active_readiness_surface: bool
    active_profile_status_surface: bool
    active_frontend_summary_surface: bool


RAG_CORE_V1_BOUNDARY_METADATA: Final = RagTemplateBoundaryMetadata(
    template_id=BUILTIN_TEMPLATE_ID,
    template_input_kind="legacy_template_input",
    active_readiness_surface=False,
    active_profile_status_surface=False,
    active_frontend_summary_surface=False,
)


class RagTemplateService:
    """Read and validate internal RAG reference templates."""

    @classmethod
    def load(
        cls,
        template_id: str,
        *,
        template_dir: Path | None = None,
    ) -> RagTemplate:
        if template_id != BUILTIN_TEMPLATE_ID:
            raise RagTemplateValidationError(
                f"Unknown template: {template_id}"
            )

        base_dir = template_dir or DEFAULT_TEMPLATE_DIR
        data = cls._read_template(base_dir / f"{template_id}.json")

        try:
            template = RagTemplate.model_validate(data)
        except ValidationError as exc:
            raise RagTemplateValidationError(str(exc)) from exc

        cls._validate_template(template, expected_id=template_id)
        return template

    @classmethod
    def boundary_metadata(
        cls,
        template_id: str,
    ) -> RagTemplateBoundaryMetadata:
        if template_id != BUILTIN_TEMPLATE_ID:
            raise RagTemplateValidationError(
                f"Unknown template: {template_id}"
            )
        return RAG_CORE_V1_BOUNDARY_METADATA

    @classmethod
    def _read_template(cls, template_path: Path) -> dict[str, Any]:
        if not template_path.exists():
            raise RagTemplateValidationError(
                f"Unknown template: {template_path.stem}"
            )

        try:
            loaded = json.loads(template_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RagTemplateValidationError(
                f"Invalid template JSON: {template_path.name}"
            ) from exc

        if not isinstance(loaded, dict):
            raise RagTemplateValidationError(
                f"Template root must be an object: {template_path.name}"
            )
        return loaded

    @classmethod
    def _validate_template(
        cls, template: RagTemplate, *, expected_id: str
    ) -> None:
        if template.id != expected_id:
            raise RagTemplateValidationError(
                f"Template id '{template.id}' does not match '{expected_id}'"
            )
        if template.system_type != "rag":
            raise RagTemplateValidationError(
                f"Template '{template.id}' must use system_type 'rag'"
            )
        if template.allowed_statuses != EXPECTED_ALLOWED_STATUSES:
            raise RagTemplateValidationError(
                "Allowed statuses must match the rag-core-v1 template "
                "SlotStatus vocabulary"
            )

        slot_ids = [slot.id for slot in template.slots]
        duplicate_slots = cls._duplicates(slot_ids)
        if duplicate_slots:
            raise RagTemplateValidationError(
                f"Duplicate slot ids: {', '.join(duplicate_slots)}"
            )

        slot_id_set = set(slot_ids)
        for flow in template.flows:
            if flow.id.startswith("flow:"):
                raise RagTemplateValidationError(
                    f"Template flow '{flow.id}' must use a bare flow id"
                )

            unknown_slots = [
                slot_id
                for slot_id in flow.slot_order
                if slot_id not in slot_id_set
            ]
            if unknown_slots:
                raise RagTemplateValidationError(
                    f"Flow '{flow.id}' references unknown slot ids: "
                    f"{', '.join(unknown_slots)}"
                )

    @staticmethod
    def _duplicates(values: list[str]) -> list[str]:
        seen: set[str] = set()
        duplicates: list[str] = []
        for value in values:
            if value in seen and value not in duplicates:
                duplicates.append(value)
            seen.add(value)
        return duplicates
