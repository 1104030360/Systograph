from __future__ import annotations

from typing import Protocol

from systograph.core.models.mapping import MappingEvidencePacket


class MappingProposalProviderUnavailableError(RuntimeError):
    pass


class MappingProposalProvider(Protocol):
    name: str

    def generate(
        self,
        *,
        packet: MappingEvidencePacket,
        output_schema: dict[str, object],
        validation_error: str | None = None,
    ) -> str: ...
