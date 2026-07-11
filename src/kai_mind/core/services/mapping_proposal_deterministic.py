from __future__ import annotations

from kai_mind.core.models.mapping import (
    MappingCandidate,
    MappingCandidateType,
    MappingEvidencePacket,
)
from kai_mind.core.services.mapping_proposal_support import (
    packet_text,
    vector_component_name,
    vector_provider,
)


def deterministic_candidates(
    packet: MappingEvidencePacket,
) -> list[MappingCandidate]:
    text = packet_text(packet)
    candidates: list[MappingCandidate] = []
    if "vector_store" in packet.available_slots and any(
        token in text
        for token in ("chroma", "qdrant", "faiss", "lancedb", "pgvector")
    ):
        candidates.append(
            MappingCandidate(
                candidate_type=MappingCandidateType.EXISTING_SLOT,
                target_slot="vector_store",
                component_name=vector_component_name(text),
                component_kind="vector_db",
                provider=vector_provider(text),
                label="Map evidence to Vector Store",
                rationale=(
                    "Dependency or code evidence points to a vector store "
                    "client, but the scanner marked it as needing "
                    "confirmation."
                ),
                evidence_ids=list(packet.evidence_ids),
                rank=1,
                recommendation_level="strong_candidate",
                uncertainty_reason="Static evidence only.",
            )
        )
    if "router" in text or "route" in text:
        candidates.append(
            capability_candidate(
                candidate_id="capability-candidate:query_router",
                name="Query Router",
                kind="routing_orchestration",
                rationale=(
                    "Router-like evidence is a capability signal, not a "
                    "canonical map structure component."
                ),
                packet=packet,
                rank=len(candidates) + 1,
            )
        )
    if "rerank" in text:
        candidates.append(
            capability_candidate(
                candidate_id="capability-candidate:reranker",
                name="Reranker",
                kind="reranker",
                rationale=(
                    "Reranker-like evidence is a capability signal, not a "
                    "canonical map structure component."
                ),
                packet=packet,
                rank=len(candidates) + 1,
            )
        )
    candidates.append(
        MappingCandidate(
            candidate_type=MappingCandidateType.NEEDS_MORE_INFORMATION,
            label="Ask for more mapping context",
            rationale=(
                "The bounded packet is not enough to safely confirm a "
                "legacy slot or non-map capability candidate."
            ),
            evidence_ids=list(packet.evidence_ids),
            rank=len(candidates) + 1,
            recommendation_level="needs_more_context",
            uncertainty_reason=("More user context or detail scan is needed."),
        )
    )
    if len(candidates) < 3:
        candidates.append(
            MappingCandidate(
                candidate_type=MappingCandidateType.SKIP_FOR_NOW,
                label="Skip for now",
                rationale=(
                    "Keep the component unmapped until stronger evidence "
                    "or user confirmation exists."
                ),
                evidence_ids=list(packet.evidence_ids),
                rank=len(candidates) + 1,
                recommendation_level="low_candidate",
                uncertainty_reason="Skipping does not change canonical map.",
            )
        )
    return candidates[:3]


def capability_candidate(
    *,
    candidate_id: str,
    name: str,
    kind: str,
    rationale: str,
    packet: MappingEvidencePacket,
    rank: int,
) -> MappingCandidate:
    return MappingCandidate(
        candidate_type=(
            MappingCandidateType.NON_BASELINE_CAPABILITY_CANDIDATE
        ),
        proposed_capability_candidate_id=candidate_id,
        proposed_capability_candidate_name=name,
        proposed_capability_candidate_kind=kind,
        label="Mark as non-baseline capability candidate",
        rationale=rationale,
        evidence_ids=list(packet.evidence_ids),
        rank=rank,
        recommendation_level="plausible_candidate",
        uncertainty_reason="Static evidence only.",
    )
