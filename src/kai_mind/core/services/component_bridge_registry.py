from __future__ import annotations

import re
from collections.abc import Sequence

from kai_mind.core.models.scan import ScanFact
from kai_mind.core.models.system_map import UnmappedComponent
from kai_mind.core.services.component_bridge_models import (
    ComponentBridgeDecision,
    ComponentBridgeDecisionKind,
    ComponentBridgeMatcher,
    ComponentBridgeRule,
    ComponentCandidate,
)
from kai_mind.core.services.component_bridge_rules import (
    COMPONENT_BRIDGE_RULES,
)

NEEDS_CONFIRMATION_STATUS = "needs_confirmation"

__all__ = [
    "ComponentBridgeDecisionKind",
    "ComponentBridgeMatcher",
    "ComponentBridgeRegistry",
    "ComponentCandidate",
]


class ComponentBridgeRegistry:
    def __init__(
        self,
        rules: Sequence[ComponentBridgeRule] = COMPONENT_BRIDGE_RULES,
    ) -> None:
        self._rules = tuple(rules)

    def match(
        self,
        fact: ScanFact,
        *,
        evidence_ids: tuple[str, ...],
    ) -> ComponentBridgeDecision:
        if not evidence_ids:
            return ComponentBridgeDecision(
                ComponentBridgeDecisionKind.NO_MATCH
            )
        candidates = self._rule_candidates(fact, evidence_ids)
        candidates += _config_candidates(fact, evidence_ids)
        if candidates:
            return ComponentBridgeDecision(
                ComponentBridgeDecisionKind.COMPONENT_CANDIDATE,
                component_candidates=candidates,
            )
        if _looks_like_reranker(fact):
            return _review_decision(
                ComponentBridgeDecisionKind.NON_BASELINE_CAPABILITY_SIGNAL,
                fact,
                evidence_ids,
                observed_kind="reranker_candidate",
            )
        if _looks_like_router(fact):
            return _review_decision(
                ComponentBridgeDecisionKind.NON_BASELINE_CAPABILITY_SIGNAL,
                fact,
                evidence_ids,
                observed_kind="router_like_evidence",
            )
        if fact.kind == "dependency_candidate":
            return _review_decision(
                ComponentBridgeDecisionKind.UNMAPPED_REVIEW_ITEM,
                fact,
                evidence_ids,
                observed_kind=fact.kind,
            )
        return ComponentBridgeDecision(ComponentBridgeDecisionKind.NO_MATCH)

    def _rule_candidates(
        self,
        fact: ScanFact,
        evidence_ids: tuple[str, ...],
    ) -> tuple[ComponentCandidate, ...]:
        candidates: list[ComponentCandidate] = []
        for rule in self._rules:
            if rule.matches(fact):
                candidates.extend(
                    spec.materialize(evidence_ids) for spec in rule.candidates
                )
        return tuple(candidates)


def _config_candidates(
    fact: ScanFact,
    evidence_ids: tuple[str, ...],
) -> tuple[ComponentCandidate, ...]:
    if fact.kind != "config_value":
        return ()
    path_tokens = _tokens(fact.path)
    value = (fact.value or "").strip().lower()
    candidates = _vector_store_candidates(path_tokens, fact.path, value)
    candidates += _llm_candidates(path_tokens, value)
    candidates += _openai_config_candidates(fact.path, path_tokens, value)
    return tuple(
        ComponentCandidate(
            slot=slot,
            kind=kind,
            name=name,
            provider=provider,
            evidence_ids=evidence_ids,
        )
        for slot, kind, name, provider in candidates
    )


def _vector_store_candidates(
    path_tokens: set[str],
    path: str,
    value: str,
) -> tuple[tuple[str, str, str, str], ...]:
    compact = re.sub(r"[^a-zA-Z0-9]+", "", path.lower())
    has_vector_store = {"vector", "store"}.issubset(path_tokens) or (
        "vectorstore" in compact
    )
    if not has_vector_store or "provider" not in path_tokens:
        return ()
    names = {
        "chroma": "Chroma",
        "qdrant": "Qdrant",
        "pgvector": "pgvector",
    }
    name = names.get(value)
    if name is None:
        return ()
    return (("vector_store", "vector_db_config", name, value),)


def _llm_candidates(
    path_tokens: set[str],
    value: str,
) -> tuple[tuple[str, str, str, str], ...]:
    if "llm" not in path_tokens or "provider" not in path_tokens:
        return ()
    if value == "ollama":
        return (("llm", "local_llm_runtime", "Ollama", "ollama"),)
    if value == "openai":
        return (("llm", "external_llm_provider", "OpenAI", "openai"),)
    return ()


def _openai_config_candidates(
    path: str,
    path_tokens: set[str],
    value: str,
) -> tuple[tuple[str, str, str, str], ...]:
    if "openai" in path.lower():
        return (
            ("llm", "external_llm_provider", "OpenAI", "openai"),
            (
                "embedding_model",
                "embedding_provider",
                "OpenAI Embeddings",
                "openai",
            ),
        )
    candidates: list[tuple[str, str, str, str]] = []
    if "openai" in value and path_tokens & {"llm", "chat"}:
        candidates.append(("llm", "external_llm_provider", "OpenAI", "openai"))
    if "openai" in value and path_tokens & {"embedding", "embeddings"}:
        candidates.append(
            (
                "embedding_model",
                "embedding_provider",
                "OpenAI Embeddings",
                "openai",
            )
        )
    return tuple(candidates)


def _review_decision(
    kind: ComponentBridgeDecisionKind,
    fact: ScanFact,
    evidence_ids: tuple[str, ...],
    *,
    observed_kind: str,
) -> ComponentBridgeDecision:
    component = UnmappedComponent(
        id=(
            f"unmapped:{_slug(fact.file)}:{_slug(fact.path)}:"
            f"{_slug(fact.rule_id or fact.kind)}"
        ),
        source_file=fact.file,
        observed_kind=observed_kind,
        status=NEEDS_CONFIRMATION_STATUS,
        reason=(
            f"Detected {observed_kind}, but no safe canonical component "
            "mapping exists yet."
        ),
        evidence_ids=list(evidence_ids),
        suggested_actions=["confirm_mapping", "mark_not_applicable"],
    )
    return ComponentBridgeDecision(kind, unmapped_component=component)


def _looks_like_reranker(fact: ScanFact) -> bool:
    return any(
        "rerank" in value.lower()
        for value in (fact.path, fact.value or "", fact.rule_id or "")
    )


def _looks_like_router(fact: ScanFact) -> bool:
    return any(
        token in value.lower()
        for value in (fact.path, fact.value or "", fact.rule_id or "")
        for token in ("router", "route")
    )


def _tokens(value: str) -> set[str]:
    return {
        token for token in re.split(r"[^a-zA-Z0-9]+", value.lower()) if token
    }


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")
    return normalized or "unknown"
