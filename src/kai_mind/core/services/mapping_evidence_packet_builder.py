"""Build masked, bounded evidence packets for mapping proposals."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from kai_mind.core.models.mapping import (
    MAX_USER_DESCRIPTION_CHARS,
    MappingEvidencePacket,
)
from kai_mind.core.models.system_map import Evidence, UnmappedComponent
from kai_mind.core.services.secret_masking_service import (
    SecretMaskingService,
)


class MappingEvidencePacketBuilder:
    """Convert canonical evidence into a proposal-only bounded packet."""

    def __init__(
        self,
        *,
        secret_masking_service: SecretMaskingService | None = None,
        max_evidence_items: int = 12,
        max_value_chars: int = 240,
    ) -> None:
        self._secret_masking_service = (
            secret_masking_service or SecretMaskingService()
        )
        self._max_evidence_items = max_evidence_items
        self._max_value_chars = max_value_chars

    def build(
        self,
        *,
        project_id: str,
        unmapped_component: UnmappedComponent,
        evidence: Sequence[Evidence],
        available_slots: Sequence[str],
        available_extensions: Sequence[str] | None = None,
        confirmed_component_ids: Sequence[str] | None = None,
        user_description: str | None = None,
    ) -> MappingEvidencePacket:
        referenced = set(unmapped_component.evidence_ids)
        selected = [item for item in evidence if item.id in referenced][
            : self._max_evidence_items
        ]

        return MappingEvidencePacket(
            project_id=project_id,
            source_unmapped_id=unmapped_component.id,
            source_file=unmapped_component.source_file,
            observed_kind=unmapped_component.observed_kind,
            reason=unmapped_component.reason,
            user_description=self._bounded_masked_user_description(
                user_description
            ),
            evidence_ids=[item.id for item in selected],
            rule_ids=_unique(
                item.rule_id for item in selected if item.rule_id
            ),
            line_ranges=_line_ranges(selected),
            masked_evidence_values=[
                self._bounded_masked_text(item.value)
                for item in selected
                if item.value is not None
            ],
            masked_snippets=[
                self._bounded_masked_text(item.snippet)
                for item in selected
                if item.snippet is not None
            ],
            dependency_signals=[
                self._bounded_masked_text(item.value)
                for item in selected
                if item.value is not None and _is_dependency_signal(item)
            ],
            import_signals=[
                self._bounded_masked_text(item.value or item.path or "")
                for item in selected
                if _looks_like_signal(item, {"import"})
            ],
            class_function_signals=[
                self._bounded_masked_text(item.path)
                for item in selected
                if item.path and _looks_like_symbol_path(item.path)
            ],
            call_like_signals=[
                self._bounded_masked_text(item.path or item.value or "")
                for item in selected
                if _looks_like_signal(item, {"call", "route", "invoke"})
            ],
            context_limits={
                "source": "existing_evidence_array",
                "max_evidence_items": self._max_evidence_items,
                "max_value_chars": self._max_value_chars,
                "evidence_truncated": (
                    len(referenced) > self._max_evidence_items
                ),
                "best_effort": True,
            },
            available_slots=_unique(available_slots),
            available_extensions=_unique(available_extensions or []),
            confirmed_component_ids=_unique(confirmed_component_ids or []),
        )

    def _bounded_masked_text(self, value: str) -> str:
        masked = self._secret_masking_service.mask_text(value)
        if len(masked) <= self._max_value_chars:
            return masked
        return f"{masked[: self._max_value_chars]}...[truncated]"

    def _bounded_masked_user_description(
        self,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        masked = self._secret_masking_service.mask_text(value)
        if len(masked) <= MAX_USER_DESCRIPTION_CHARS:
            return masked
        return f"{masked[:MAX_USER_DESCRIPTION_CHARS]}...[truncated]"


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not isinstance(value, str) or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _line_range(evidence: Evidence) -> str | None:
    if evidence.file is None or evidence.line_start is None:
        return None
    line_end = evidence.line_end or evidence.line_start
    return f"{evidence.file}:{evidence.line_start}-{line_end}"


def _line_ranges(evidence: Sequence[Evidence]) -> list[str]:
    ranges: list[str] = []
    for item in evidence:
        line_range = _line_range(item)
        if line_range is not None:
            ranges.append(line_range)
    return ranges


def _is_dependency_signal(evidence: Evidence) -> bool:
    haystack = " ".join(
        [
            evidence.kind,
            evidence.rule_id or "",
        ]
    ).lower()
    return "dependency" in haystack


def _looks_like_signal(
    evidence: Evidence,
    tokens: set[str],
) -> bool:
    haystack = " ".join(
        [
            evidence.kind,
            evidence.rule_id or "",
            evidence.path or "",
            evidence.value or "",
        ]
    ).lower()
    parts = {part for part in re.split(r"[^a-z0-9]+", haystack) if part}
    return any(token in parts for token in tokens)


def _looks_like_symbol_path(value: str) -> bool:
    return "." in value or value.endswith(")") or "(" in value
