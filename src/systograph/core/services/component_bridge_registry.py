from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import replace

from systograph.core.models.scan import ScanFact
from systograph.core.models.system_map import UnmappedComponent
from systograph.core.services.ast_construction_output import (
    EXTERNAL_IMPORT_FACT_KIND,
    EXTERNAL_IMPORT_RULE_ID,
)
from systograph.core.services.component_bridge_models import (
    ComponentBridgeCandidateSpec,
    ComponentBridgeDecision,
    ComponentBridgeDecisionKind,
    ComponentBridgeMatcher,
    ComponentBridgeRule,
    ComponentCandidate,
)
from systograph.core.services.component_bridge_rules import (
    COMPONENT_BRIDGE_RULES,
)
from systograph.core.services.rule_catalog_loader import (
    ENDPOINT_VENDOR_FACT_KIND,
    EndpointCapabilityRule,
    PackageCapabilityRule,
    RuleCatalogLoader,
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
        package_rules: Sequence[PackageCapabilityRule] | None = None,
        endpoint_rules: Sequence[EndpointCapabilityRule] | None = None,
    ) -> None:
        ua_rule_ids_by_legacy = {
            rule.rule_id: rule.ua_rule_id
            for rule in RuleCatalogLoader().load_default_code_pattern_rules()
            if rule.ua_rule_id is not None
        }
        self._rules = tuple(
            replace(
                rule,
                rule_ids=rule.rule_ids
                | frozenset(
                    ua_rule_ids_by_legacy[rule_id]
                    for rule_id in rule.rule_ids
                    if rule_id in ua_rule_ids_by_legacy
                ),
            )
            for rule in rules
        )
        loaded_package_rules = (
            RuleCatalogLoader().load_default_package_capability_rules()
            if package_rules is None
            else tuple(package_rules)
        )
        self._endpoint_specs_by_rule_id = {
            rule.rule_id: ComponentBridgeCandidateSpec(
                slot=rule.slot,
                kind=rule.kind,
                name=rule.name,
                provider=rule.provider,
            )
            for rule in (
                RuleCatalogLoader().load_default_endpoint_capability_rules()
                if endpoint_rules is None
                else tuple(endpoint_rules)
            )
        }
        self._package_specs_by_module = {
            rule.module: ComponentBridgeCandidateSpec(
                slot=rule.slot,
                kind=rule.kind,
                name=rule.name,
                provider=rule.provider,
            )
            for rule in loaded_package_rules
        }

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
        if (fact.rule_id or "").startswith("ua_import_"):
            return ComponentBridgeDecision(
                ComponentBridgeDecisionKind.NO_MATCH
            )
        if (
            fact.kind == EXTERNAL_IMPORT_FACT_KIND
            and fact.rule_id == EXTERNAL_IMPORT_RULE_ID
        ):
            return self._package_identity_decision(fact, evidence_ids)
        if fact.kind == ENDPOINT_VENDOR_FACT_KIND:
            return self._endpoint_identity_decision(fact, evidence_ids)
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

    def _package_identity_decision(
        self,
        fact: ScanFact,
        evidence_ids: tuple[str, ...],
    ) -> ComponentBridgeDecision:
        """Package identity layer: import module -> canonical component.

        Tier 1 of the three-tier detection contract:

        1. Package identity (here): a registry entry keyed on an import
           module path -- a top-level package name or a dotted
           submodule prefix -- deterministically decides the
           vendor/service component, carrying the import fact evidence.
           The LONGEST registry key that prefixes the import's dotted
           path on segment boundaries wins, so a dotted key
           (llama_index.core.memory) and a top-level key of the same
           package can coexist deterministically. A framework's bare
           top-level name matches nothing unless the table carries an
           explicit top-level entry: frameworks are mapped at the
           submodule level because mapping a whole framework to one
           capability would fabricate meaning.
        2. code_pattern rules: deterministic disambiguation only --
           endpoint-based vendor attribution and usage-shape
           capabilities that an import alone cannot decide.
        3. No deterministic signature (chunker, prompt_builder,
           session_state, ...): deliberately not rule-detected; those
           flow through the mapping_proposal_service LLM-proposal +
           human-confirmation path, which never decides states itself.

        An unmatched import returns NO_MATCH -- never an unmapped
        review item and never the reranker/router heuristics, so
        excluded packages (openai, chromadb, torch, ...) create
        nothing from this layer.
        """
        segments = (fact.value or "").split(".")
        spec: ComponentBridgeCandidateSpec | None = None
        for end in range(len(segments), 0, -1):
            spec = self._package_specs_by_module.get(".".join(segments[:end]))
            if spec is not None:
                break
        if spec is None:
            return ComponentBridgeDecision(
                ComponentBridgeDecisionKind.NO_MATCH
            )
        return ComponentBridgeDecision(
            ComponentBridgeDecisionKind.COMPONENT_CANDIDATE,
            component_candidates=(spec.materialize(evidence_ids),),
        )

    def _endpoint_identity_decision(
        self,
        fact: ScanFact,
        evidence_ids: tuple[str, ...],
    ) -> ComponentBridgeDecision:
        """Endpoint identity layer: vendor API host -> component.

        A sibling of the package identity layer for systems that call a
        vendor over raw HTTP and therefore import no vendor SDK. The
        catalog decides the whole mapping, so this layer never reaches
        the rule frozensets, the reranker/router heuristics or the
        unmapped-review path: an endpoint fact whose rule id is not in
        the catalog is a contract violation elsewhere, not a guess to be
        made here.
        """
        spec = self._endpoint_specs_by_rule_id.get(fact.rule_id or "")
        if spec is None:
            return ComponentBridgeDecision(
                ComponentBridgeDecisionKind.NO_MATCH
            )
        return ComponentBridgeDecision(
            ComponentBridgeDecisionKind.COMPONENT_CANDIDATE,
            component_candidates=(spec.materialize(evidence_ids),),
        )

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
