from __future__ import annotations

from typing import Protocol

from kai_mind.core.models.mapping import MappingProposal


class MappingProposalRepository(Protocol):
    def save(self, proposal: MappingProposal) -> MappingProposal: ...

    def get(self, proposal_id: str) -> MappingProposal | None: ...

    def list_for_project(self, project_id: str) -> list[MappingProposal]: ...


class InMemoryMappingProposalRepository:
    def __init__(self) -> None:
        self._items: dict[str, MappingProposal] = {}

    def save(self, proposal: MappingProposal) -> MappingProposal:
        self._items[proposal.proposal_id] = proposal
        return proposal

    def get(self, proposal_id: str) -> MappingProposal | None:
        return self._items.get(proposal_id)

    def list_for_project(self, project_id: str) -> list[MappingProposal]:
        return sorted(
            [
                proposal
                for proposal in self._items.values()
                if proposal.project_id == project_id
            ],
            key=lambda item: item.created_at,
        )
