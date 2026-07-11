from __future__ import annotations

from datetime import UTC, datetime

from kai_mind.core.models.mapping import MappingEvidencePacket


def now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def require_text(field: str, value: str | None) -> str:
    if value is None or not value.strip():
        raise ValueError(f"{field} is required")
    return value


def packet_text(packet: MappingEvidencePacket) -> str:
    return " ".join(
        [
            packet.observed_kind,
            packet.reason,
            " ".join(packet.rule_ids),
            " ".join(packet.masked_evidence_values),
            " ".join(packet.dependency_signals),
            " ".join(packet.import_signals),
            " ".join(packet.class_function_signals),
            " ".join(packet.call_like_signals),
        ]
    ).lower()


def vector_component_name(text: str) -> str:
    if "chroma" in text:
        return "Chroma"
    if "qdrant" in text:
        return "Qdrant"
    if "pgvector" in text:
        return "pgvector"
    if "lancedb" in text:
        return "LanceDB"
    if "faiss" in text:
        return "FAISS"
    return "Vector Store"


def vector_provider(text: str) -> str | None:
    for token, provider in (
        ("chroma", "chroma"),
        ("qdrant", "qdrant"),
        ("pgvector", "pgvector"),
        ("lancedb", "lancedb"),
        ("faiss", "faiss"),
    ):
        if token in text:
            return provider
    return None
