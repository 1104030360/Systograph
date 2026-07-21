"""Build masked, bounded evidence packets for mapping proposals."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from kai_mind.core.models.ai_system_map_v2 import CanonicalEvidence
from kai_mind.core.models.mapping import (
    MAX_USER_DESCRIPTION_CHARS,
    MappingEvidencePacket,
)
from kai_mind.core.services.secret_masking_service import (
    SecretMaskingService,
)
from kai_mind.core.services.system_map_index import SystemMapIndex


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
        index: SystemMapIndex,
        unmapped_id: str,
        available_slots: Sequence[str],
        confirmed_component_ids: Sequence[str] | None = None,
        user_description: str | None = None,
    ) -> MappingEvidencePacket:
        unmapped = index.unmapped_by_id(unmapped_id)
        if unmapped is None:
            raise KeyError(unmapped_id)
        evidence = index.evidence_for_ids(unmapped.evidence_ids)[
            : self._max_evidence_items
        ]
        summaries = [
            self._bounded_masked_text(item.extract_summary)
            for item in evidence
            if item.extract_summary is not None
        ]
        return MappingEvidencePacket(
            project_id=project_id,
            source_unmapped_id=unmapped.unmapped_id,
            source_file=unmapped.source_file,
            observed_kind=unmapped.observed_kind,
            reason=unmapped.reason,
            user_description=self._bounded_masked_user_description(
                user_description
            ),
            evidence_ids=[item.evidence_id for item in evidence],
            rule_ids=_unique(
                item.rule_id for item in evidence if item.rule_id
            ),
            line_ranges=_canonical_line_ranges(evidence),
            masked_evidence_values=summaries,
            masked_snippets=summaries,
            dependency_signals=[
                summary
                for item, summary in _canonical_summaries(evidence, self)
                if _canonical_signal_matches(item, {"dependency"})
            ],
            import_signals=[
                self._bounded_masked_text(signal)
                for item in evidence
                if _canonical_signal_matches(item, {"import"})
                and (signal := _canonical_signal_text(item)) is not None
            ],
            class_function_signals=[
                self._bounded_masked_text(location)
                for item in evidence
                if (location := _canonical_symbol_location(item)) is not None
            ],
            call_like_signals=[
                self._bounded_masked_text(signal)
                for item in evidence
                if _canonical_signal_matches(
                    item,
                    {"call", "route", "invoke"},
                )
                and (signal := _canonical_signal_text(item)) is not None
            ],
            context_limits={
                "source": "system_map_index",
                "max_evidence_items": self._max_evidence_items,
                "max_value_chars": self._max_value_chars,
                "evidence_truncated": (
                    len(unmapped.evidence_ids) > self._max_evidence_items
                ),
                "best_effort": True,
            },
            available_slots=_unique(available_slots),
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


def _looks_like_symbol_path(value: str) -> bool:
    return "." in value or value.endswith(")") or "(" in value


def _canonical_line_ranges(
    evidence: Sequence[CanonicalEvidence],
) -> list[str]:
    ranges: list[str] = []
    for item in evidence:
        location = item.location
        if location.path is None or location.start_line is None:
            continue
        line_end = location.end_line or location.start_line
        ranges.append(f"{location.path}:{location.start_line}-{line_end}")
    return ranges


def _canonical_summaries(
    evidence: Sequence[CanonicalEvidence],
    builder: MappingEvidencePacketBuilder,
) -> list[tuple[CanonicalEvidence, str]]:
    return [
        (item, builder._bounded_masked_text(item.extract_summary))
        for item in evidence
        if item.extract_summary is not None
    ]


def _canonical_signal_matches(
    evidence: CanonicalEvidence,
    tokens: set[str],
) -> bool:
    location = evidence.location
    haystack = " ".join(
        [
            evidence.artifact_type,
            evidence.rule_id or "",
            evidence.extract_summary or "",
            location.json_pointer or "",
            location.config_key or "",
        ]
    ).lower()
    parts = {part for part in re.split(r"[^a-z0-9]+", haystack) if part}
    return any(token in parts for token in tokens)


def _canonical_symbol_location(
    evidence: CanonicalEvidence,
) -> str | None:
    location = evidence.location
    value = location.config_key or location.json_pointer
    if value is None or not _looks_like_symbol_path(value):
        return None
    return value


def _canonical_signal_text(evidence: CanonicalEvidence) -> str | None:
    return _canonical_symbol_location(evidence) or evidence.extract_summary
