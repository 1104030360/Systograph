from __future__ import annotations

import json
from collections.abc import Iterable
from typing import assert_never

from pydantic import ValidationError

from systograph.core.models.mapping import (
    MappingCandidate,
    MappingCandidateType,
    MappingEvidencePacket,
    MappingProviderCandidateBatch,
)
from systograph.core.services.mapping_proposal_deterministic import (
    deterministic_candidates,
)
from systograph.core.services.mapping_proposal_provider import (
    MappingProposalProvider,
    MappingProposalProviderUnavailableError,
)
from systograph.core.services.mapping_proposal_support import require_text
from systograph.core.services.secret_masking_service import (
    SecretMaskingService,
)


class ProposalCandidateFactory:
    def __init__(self, secret_masking_service: SecretMaskingService) -> None:
        self._secret_masking_service = secret_masking_service

    def validate_packet(self, packet: MappingEvidencePacket) -> None:
        require_text("project_id", packet.project_id)
        require_text("source_unmapped_id", packet.source_unmapped_id)
        if not packet.evidence_ids:
            raise ValueError("MappingEvidencePacket must include evidence")
        self._reject_unmasked_secret(packet.model_dump(mode="json"))

    def provider_candidates(
        self,
        provider: MappingProposalProvider | None,
        packet: MappingEvidencePacket,
    ) -> tuple[list[MappingCandidate] | None, str | None]:
        if provider is None:
            return None, None
        output_schema = MappingProviderCandidateBatch.model_json_schema()
        validation_error: str | None = None
        for _attempt in range(2):
            try:
                raw = provider.generate(
                    packet=packet,
                    output_schema=output_schema,
                    validation_error=validation_error,
                )
                batch = MappingProviderCandidateBatch.model_validate_json(raw)
                candidates = self._validate_candidates(
                    packet, batch.candidates
                )
            except MappingProposalProviderUnavailableError:
                return None, "provider_unavailable"
            except (ValidationError, ValueError) as exc:
                validation_error = self._safe_reason(str(exc))
                continue
            if candidates:
                return candidates, None
            validation_error = "Provider returned no candidates"
        return None, "provider_invalid_output"

    def deterministic_candidates(
        self,
        packet: MappingEvidencePacket,
    ) -> list[MappingCandidate]:
        return deterministic_candidates(packet)

    def assign_candidate_ids(
        self,
        candidates: list[MappingCandidate],
    ) -> list[MappingCandidate]:
        return [
            candidate.model_copy(
                update={
                    "candidate_id": candidate.candidate_id
                    or f"candidate:{index}",
                }
            )
            for index, candidate in enumerate(candidates, start=1)
        ]

    def _validate_candidates(
        self,
        packet: MappingEvidencePacket,
        candidates: Iterable[MappingCandidate],
    ) -> list[MappingCandidate]:
        validated: list[MappingCandidate] = []
        for candidate in candidates:
            self._validate_candidate(packet, candidate)
            validated.append(candidate)
        return sorted(validated, key=lambda item: item.rank)

    def _validate_candidate(
        self,
        packet: MappingEvidencePacket,
        candidate: MappingCandidate,
    ) -> None:
        if not candidate.evidence_ids:
            raise ValueError("candidate must include evidence")
        unknown_evidence = sorted(
            set(candidate.evidence_ids) - set(packet.evidence_ids)
        )
        if unknown_evidence:
            raise ValueError(
                "candidate references unknown evidence: "
                f"{', '.join(unknown_evidence)}"
            )
        match candidate.candidate_type:
            case MappingCandidateType.EXISTING_SLOT:
                if candidate.target_slot not in set(packet.available_slots):
                    raise ValueError(
                        "candidate references unknown target slot: "
                        f"{candidate.target_slot}"
                    )
            case MappingCandidateType.NON_BASELINE_CAPABILITY_CANDIDATE:
                require_text(
                    "proposed_capability_candidate_id",
                    candidate.proposed_capability_candidate_id,
                )
                require_text(
                    "proposed_capability_candidate_name",
                    candidate.proposed_capability_candidate_name,
                )
                require_text(
                    "proposed_capability_candidate_kind",
                    candidate.proposed_capability_candidate_kind,
                )
            case (
                MappingCandidateType.NEEDS_MORE_INFORMATION
                | MappingCandidateType.SKIP_FOR_NOW
            ):
                pass
            case unreachable:
                assert_never(unreachable)
        self._validate_suggested_edges(packet, candidate)
        self._reject_unmasked_secret(candidate.model_dump(mode="json"))

    def _validate_suggested_edges(
        self,
        packet: MappingEvidencePacket,
        candidate: MappingCandidate,
    ) -> None:
        allowed = set(packet.available_slots)
        for edge in candidate.suggested_edges:
            if (
                edge.source_ref not in allowed
                or edge.target_ref not in allowed
            ):
                raise ValueError(
                    "candidate suggested edge references unknown endpoint"
                )

    def _reject_unmasked_secret(self, payload: dict[str, object]) -> None:
        serialized = json.dumps(payload, sort_keys=True)
        if self._secret_masking_service.contains_unmasked_secret(serialized):
            raise ValueError(
                "Proposal payload must not contain unmasked secret"
            )

    def _safe_reason(self, value: str) -> str:
        return self._secret_masking_service.mask_text(value)[:400]
