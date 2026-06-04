"""Map raw scanner facts to RAG component slots."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Final, Protocol

from kai_mind.core.models.scan import ScanFact
from kai_mind.core.models.system_map import (
    ComponentInstance,
    ComponentSlot,
    Evidence,
    ExtensionComponent,
    SlotStatus,
    UnmappedComponent,
)
from kai_mind.core.models.template import RagTemplate

DETECTED_STATUS: Final = "detected"
MISSING_STATUS: Final = "missing"
NOT_APPLICABLE_STATUS: Final = "not_applicable"
NEEDS_CONFIRMATION_STATUS: Final = "needs_confirmation"
EXTENSION_CANDIDATE_STATUS: Final = "candidate"
VECTOR_STORE_CONFIG_PROVIDERS: Final = {
    "chroma": ("vector_db_config", "Chroma", "chroma"),
    "qdrant": ("vector_db_config", "Qdrant", "qdrant"),
    "pgvector": ("vector_db_config", "pgvector", "pgvector"),
}
LLM_CONFIG_PROVIDERS: Final = {
    "ollama": ("local_llm_runtime", "Ollama", "ollama"),
}


@dataclass(frozen=True)
class ComponentDetectionResult:
    """Detected component slots plus non-standard or ambiguous components."""

    components_by_slot: dict[str, ComponentSlot]
    extensions: list[ExtensionComponent]
    unmapped_components: list[UnmappedComponent]


class ManualMappingHook(Protocol):
    """Placeholder for Task 19 user-confirmed mapping support."""

    def apply(
        self,
        result: ComponentDetectionResult,
    ) -> ComponentDetectionResult:
        """Return a result with confirmed manual mappings applied."""


@dataclass(frozen=True)
class ComponentCandidate:
    """Internal component candidate derived from one or more facts."""

    slot: str
    kind: str
    name: str
    provider: str | None
    evidence_ids: tuple[str, ...]

    @property
    def id(self) -> str:
        return f"component:{self.slot}:{_slug(self.provider or self.name)}"


class ComponentDetectionService:
    """Conservatively map raw facts to rag-core-v1 component slots."""

    def __init__(
        self,
        *,
        manual_mapping_hook: ManualMappingHook | None = None,
    ) -> None:
        self._manual_mapping_hook = manual_mapping_hook

    def detect(
        self,
        *,
        template: RagTemplate,
        facts: Sequence[ScanFact],
        evidence: Sequence[Evidence],
    ) -> ComponentDetectionResult:
        """Return slot status, component instances and ambiguous evidence."""

        evidence_lookup = EvidenceLookup(evidence)
        candidates: dict[str, ComponentCandidate] = {}
        extensions: dict[str, ExtensionComponent] = {}
        unmapped: dict[str, UnmappedComponent] = {}

        for fact in facts:
            evidence_ids = evidence_lookup.ids_for_fact(fact)
            if not evidence_ids:
                continue

            fact_candidates = self._component_candidates(fact, evidence_ids)
            for candidate in fact_candidates:
                self._merge_candidate(candidates, candidate)

            extension = self._extension_candidate(fact, evidence_ids)
            if extension is not None:
                extensions.setdefault(extension.id, extension)
                continue

            if fact_candidates:
                continue

            ambiguous = self._unmapped_candidate(fact, evidence_ids)
            if ambiguous is not None:
                unmapped.setdefault(ambiguous.id, ambiguous)

        components_by_slot = self._build_slots(template, candidates.values())
        result = ComponentDetectionResult(
            components_by_slot=components_by_slot,
            extensions=sorted(extensions.values(), key=lambda item: item.id),
            unmapped_components=sorted(
                unmapped.values(),
                key=lambda item: item.id,
            ),
        )

        if self._manual_mapping_hook is not None:
            return self._manual_mapping_hook.apply(result)
        return result

    def _component_candidates(
        self,
        fact: ScanFact,
        evidence_ids: tuple[str, ...],
    ) -> list[ComponentCandidate]:
        candidates: list[ComponentCandidate] = []
        candidates.extend(self._vector_store_candidates(fact, evidence_ids))
        candidates.extend(self._llm_candidates(fact, evidence_ids))
        candidates.extend(self._embedding_candidates(fact, evidence_ids))
        candidates.extend(self._application_candidates(fact, evidence_ids))
        candidates.extend(self._retriever_candidates(fact, evidence_ids))
        candidates.extend(self._prompt_candidates(fact, evidence_ids))
        return candidates

    def _vector_store_candidates(
        self,
        fact: ScanFact,
        evidence_ids: tuple[str, ...],
    ) -> list[ComponentCandidate]:
        rule_id = fact.rule_id or ""
        if rule_id in {
            "docker_qdrant_image_detected",
            "code_pattern_vector_store_qdrant",
        }:
            return [
                ComponentCandidate(
                    slot="vector_store",
                    kind="vector_db",
                    name="Qdrant",
                    provider="qdrant",
                    evidence_ids=evidence_ids,
                )
            ]

        if rule_id == "docker_pgvector_image_detected":
            return [
                ComponentCandidate(
                    slot="vector_store",
                    kind="vector_db",
                    name="pgvector",
                    provider="pgvector",
                    evidence_ids=evidence_ids,
                )
            ]

        if rule_id == "docker_chromadb_chroma_image_detected":
            return [
                ComponentCandidate(
                    slot="vector_store",
                    kind="http_vector_store",
                    name="Chroma",
                    provider="chroma",
                    evidence_ids=evidence_ids,
                )
            ]

        if rule_id == "code_pattern_vector_store_chroma":
            return [
                ComponentCandidate(
                    slot="vector_store",
                    kind="vector_db",
                    name="Chroma",
                    provider="chroma",
                    evidence_ids=evidence_ids,
                )
            ]

        if rule_id in {
            "code_pattern_vector_store_chroma_http",
            "code_pattern_vector_store_chroma_async_http",
        }:
            return [
                ComponentCandidate(
                    slot="vector_store",
                    kind="http_vector_store",
                    name="Chroma HTTP",
                    provider="chroma_http",
                    evidence_ids=evidence_ids,
                )
            ]

        if rule_id == "code_pattern_vector_store_chroma_persistent":
            return [
                ComponentCandidate(
                    slot="vector_store",
                    kind="local_persistent_vector_store",
                    name="Chroma Persistent",
                    provider="chroma_persistent",
                    evidence_ids=evidence_ids,
                )
            ]

        config_provider = self._vector_store_provider_from_config(fact)
        if config_provider is not None:
            kind, name, provider = config_provider
            return [
                ComponentCandidate(
                    slot="vector_store",
                    kind=kind,
                    name=name,
                    provider=provider,
                    evidence_ids=evidence_ids,
                )
            ]

        return []

    def _llm_candidates(
        self,
        fact: ScanFact,
        evidence_ids: tuple[str, ...],
    ) -> list[ComponentCandidate]:
        rule_id = fact.rule_id or ""
        if rule_id == "docker_ollama_image_detected":
            return [
                ComponentCandidate(
                    slot="llm",
                    kind="local_llm_runtime",
                    name="Ollama",
                    provider="ollama",
                    evidence_ids=evidence_ids,
                )
            ]
        if rule_id == "code_pattern_llm_chat_openai":
            return [
                ComponentCandidate(
                    slot="llm",
                    kind="external_llm_provider",
                    name="OpenAI",
                    provider="openai",
                    evidence_ids=evidence_ids,
                )
            ]
        config_provider = self._llm_provider_from_config(fact)
        if config_provider is not None:
            kind, name, provider = config_provider
            return [
                ComponentCandidate(
                    slot="llm",
                    kind=kind,
                    name=name,
                    provider=provider,
                    evidence_ids=evidence_ids,
                )
            ]
        if self._looks_like_openai_llm_config(fact):
            return [
                ComponentCandidate(
                    slot="llm",
                    kind="external_llm_provider",
                    name="OpenAI",
                    provider="openai",
                    evidence_ids=evidence_ids,
                )
            ]
        return []

    def _embedding_candidates(
        self,
        fact: ScanFact,
        evidence_ids: tuple[str, ...],
    ) -> list[ComponentCandidate]:
        rule_id = fact.rule_id or ""
        if rule_id in {
            "code_pattern_embedding_openai",
            "code_pattern_embedding_openai_sdk_create",
        }:
            return [
                ComponentCandidate(
                    slot="embedding_model",
                    kind="embedding_provider",
                    name="OpenAI Embeddings",
                    provider="openai",
                    evidence_ids=evidence_ids,
                )
            ]
        if self._looks_like_openai_embedding_config(fact):
            return [
                ComponentCandidate(
                    slot="embedding_model",
                    kind="embedding_provider",
                    name="OpenAI Embeddings",
                    provider="openai",
                    evidence_ids=evidence_ids,
                )
            ]
        return []

    def _application_candidates(
        self,
        fact: ScanFact,
        evidence_ids: tuple[str, ...],
    ) -> list[ComponentCandidate]:
        if fact.rule_id in {
            "code_pattern_route_fastapi",
            "code_pattern_route_flask",
            "code_pattern_route_express",
        }:
            return [
                ComponentCandidate(
                    slot="app_api_or_orchestrator",
                    kind="api_route",
                    name="Application API",
                    provider=None,
                    evidence_ids=evidence_ids,
                )
            ]
        return []

    def _retriever_candidates(
        self,
        fact: ScanFact,
        evidence_ids: tuple[str, ...],
    ) -> list[ComponentCandidate]:
        if fact.rule_id == "code_pattern_retriever_as_retriever":
            return [
                ComponentCandidate(
                    slot="retriever",
                    kind="retriever",
                    name="Retriever",
                    provider=None,
                    evidence_ids=evidence_ids,
                )
            ]
        if (
            fact.rule_id == "code_pattern_vector_store_qdrant"
            and "retriever" in fact.file.lower()
        ):
            return [
                ComponentCandidate(
                    slot="retriever",
                    kind="retriever",
                    name="Retriever",
                    provider=None,
                    evidence_ids=evidence_ids,
                )
            ]
        return []

    def _prompt_candidates(
        self,
        fact: ScanFact,
        evidence_ids: tuple[str, ...],
    ) -> list[ComponentCandidate]:
        if fact.rule_id == "code_pattern_prompt_template":
            return [
                ComponentCandidate(
                    slot="prompt_builder",
                    kind="prompt_template",
                    name="Prompt Template",
                    provider=None,
                    evidence_ids=evidence_ids,
                )
            ]
        return []

    def _extension_candidate(
        self,
        fact: ScanFact,
        evidence_ids: tuple[str, ...],
    ) -> ExtensionComponent | None:
        if (
            "reranker" not in fact.path.lower()
            and "rerank" not in (fact.value or "").lower()
        ):
            return None

        return ExtensionComponent(
            id=f"extension:{_slug(fact.file)}:reranker",
            name="Reranker",
            kind="reranker",
            status=EXTENSION_CANDIDATE_STATUS,
            confirmed_by_user=False,
            description=(
                "Detected reranker-like evidence pending confirmation."
            ),
            evidence_ids=list(evidence_ids),
        )

    def _unmapped_candidate(
        self,
        fact: ScanFact,
        evidence_ids: tuple[str, ...],
    ) -> UnmappedComponent | None:
        if self._is_weak_dependency_signal(fact) or self._looks_like_router(
            fact
        ):
            observed_kind = self._observed_kind(fact)
            return UnmappedComponent(
                id=(
                    f"unmapped:{_slug(fact.file)}:"
                    f"{_slug(fact.path)}:{_slug(fact.rule_id or fact.kind)}"
                ),
                source_file=fact.file,
                observed_kind=observed_kind,
                status=NEEDS_CONFIRMATION_STATUS,
                reason=(
                    f"Detected {observed_kind}, but no safe rag-core-v1 "
                    "slot mapping exists yet."
                ),
                evidence_ids=list(evidence_ids),
                suggested_actions=["confirm_mapping", "mark_not_applicable"],
            )
        return None

    def _is_weak_dependency_signal(self, fact: ScanFact) -> bool:
        return fact.kind == "dependency_candidate"

    def _looks_like_router(self, fact: ScanFact) -> bool:
        haystack = " ".join(
            [
                fact.path,
                fact.value or "",
                fact.rule_id or "",
            ]
        ).lower()
        return "router" in haystack or "route" in haystack

    def _looks_like_openai_llm_config(self, fact: ScanFact) -> bool:
        if fact.kind != "config_value":
            return False
        if self._looks_like_openai_global_config(fact):
            return True
        return self._has_path_token(fact, {"llm", "chat"}) and (
            "openai" in (fact.value or "").lower()
        )

    def _looks_like_openai_embedding_config(self, fact: ScanFact) -> bool:
        if fact.kind != "config_value":
            return False
        if self._looks_like_openai_global_config(fact):
            return True
        return self._has_path_token(fact, {"embedding", "embeddings"}) and (
            "openai" in (fact.value or "").lower()
        )

    def _looks_like_openai_global_config(self, fact: ScanFact) -> bool:
        return "openai" in fact.path.lower()

    def _vector_store_provider_from_config(
        self,
        fact: ScanFact,
    ) -> tuple[str, str, str] | None:
        if fact.kind != "config_value" or not (
            self._has_vector_store_provider_path(fact)
        ):
            return None
        provider = (fact.value or "").strip().lower()
        return VECTOR_STORE_CONFIG_PROVIDERS.get(provider)

    def _llm_provider_from_config(
        self,
        fact: ScanFact,
    ) -> tuple[str, str, str] | None:
        if fact.kind != "config_value" or not self._has_llm_provider_path(
            fact
        ):
            return None
        provider = (fact.value or "").strip().lower()
        return LLM_CONFIG_PROVIDERS.get(provider)

    def _has_vector_store_provider_path(self, fact: ScanFact) -> bool:
        path_tokens = set(re.split(r"[^a-zA-Z0-9]+", fact.path.lower()))
        compact_path = re.sub(r"[^a-zA-Z0-9]+", "", fact.path.lower())
        has_vector_store = {"vector", "store"}.issubset(
            path_tokens
        ) or "vectorstore" in compact_path
        return has_vector_store and "provider" in path_tokens

    def _has_llm_provider_path(self, fact: ScanFact) -> bool:
        return self._has_path_token(fact, {"llm"}) and self._has_path_token(
            fact,
            {"provider"},
        )

    def _has_path_token(self, fact: ScanFact, tokens: set[str]) -> bool:
        path_tokens = set(re.split(r"[^a-zA-Z0-9]+", fact.path.lower()))
        return bool(path_tokens & tokens)

    def _observed_kind(self, fact: ScanFact) -> str:
        if self._looks_like_router(fact):
            return "router_like_evidence"
        return fact.kind

    def _merge_candidate(
        self,
        candidates: dict[str, ComponentCandidate],
        candidate: ComponentCandidate,
    ) -> None:
        existing = candidates.get(candidate.id)
        if existing is None:
            candidates[candidate.id] = candidate
            return

        merged_evidence_ids = tuple(
            sorted(set(existing.evidence_ids) | set(candidate.evidence_ids))
        )
        candidates[candidate.id] = ComponentCandidate(
            slot=existing.slot,
            kind=existing.kind,
            name=existing.name,
            provider=existing.provider,
            evidence_ids=merged_evidence_ids,
        )

    def _build_slots(
        self,
        template: RagTemplate,
        candidates: Iterable[ComponentCandidate],
    ) -> dict[str, ComponentSlot]:
        instances_by_slot: dict[str, list[ComponentInstance]] = {
            slot.id: [] for slot in template.slots
        }
        for candidate in sorted(candidates, key=lambda item: item.id):
            instances_by_slot[candidate.slot].append(
                ComponentInstance(
                    id=candidate.id,
                    slot=candidate.slot,
                    kind=candidate.kind,
                    name=candidate.name,
                    provider=candidate.provider,
                    evidence_ids=list(candidate.evidence_ids),
                )
            )

        components_by_slot: dict[str, ComponentSlot] = {}
        for slot in template.slots:
            instances = instances_by_slot[slot.id]
            status: SlotStatus
            status = (
                DETECTED_STATUS
                if instances
                else (
                    MISSING_STATUS
                    if slot.required_for_rag_hint
                    else NOT_APPLICABLE_STATUS
                )
            )
            components_by_slot[slot.id] = ComponentSlot(
                slot=slot.id,
                required_for_rag=slot.required_for_rag_hint,
                status=status,
                instances=instances,
            )
        return components_by_slot


class EvidenceLookup:
    """Find evidence records corresponding to raw facts."""

    def __init__(self, evidence: Sequence[Evidence]) -> None:
        self._evidence = tuple(evidence)

    def ids_for_fact(self, fact: ScanFact) -> tuple[str, ...]:
        matches = [
            item.id
            for item in self._evidence
            if item.file == fact.file
            and item.path == fact.path
            and item.kind == fact.kind
            and item.rule_id == fact.rule_id
        ]
        return tuple(sorted(matches))


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")
    return normalized or "unknown"
