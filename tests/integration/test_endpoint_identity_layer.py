from __future__ import annotations

from pathlib import Path

from tests.helpers.fixtures import rag_project_fixture_path

from systograph.core.models.scan import ScanFact
from systograph.core.services.component_bridge_registry import (
    ComponentBridgeDecisionKind,
    ComponentBridgeRegistry,
)
from systograph.core.services.component_detection_service import (
    ComponentDetectionService,
)
from systograph.core.services.project_scan_service import ProjectScanService
from systograph.core.services.rag_template_service import RagTemplateService
from systograph.core.services.rule_catalog_loader import (
    ENDPOINT_VENDOR_FACT_KIND,
    RuleCatalogLoader,
)


def endpoint_fact(rule_id: str, value: str) -> ScanFact:
    return ScanFact(
        kind=ENDPOINT_VENDOR_FACT_KIND,
        file="app/client.py",
        path="line[3]",
        value=value,
        rule_id=rule_id,
    )


def test_endpoint_fact_becomes_the_catalog_component() -> None:
    # Given/When
    decision = ComponentBridgeRegistry().match(
        endpoint_fact("endpoint_vendor_anthropic_llm", "api.anthropic.com"),
        evidence_ids=("evidence:endpoint:anthropic",),
    )

    # Then
    assert decision.kind is ComponentBridgeDecisionKind.COMPONENT_CANDIDATE
    assert [
        (item.slot, item.kind, item.provider)
        for item in decision.component_candidates
    ] == [("llm", "external_llm_provider", "anthropic")]


def test_unknown_endpoint_rule_id_creates_nothing() -> None:
    # Given/When/Then: the catalog is the whole mapping -- an endpoint
    # fact it does not know never falls through to a heuristic.
    decision = ComponentBridgeRegistry().match(
        endpoint_fact("endpoint_vendor_unlisted_llm", "api.unknown.test"),
        evidence_ids=("evidence:endpoint:unknown",),
    )
    assert decision.kind is ComponentBridgeDecisionKind.NO_MATCH


def test_endpoint_rule_ids_never_overlap_the_frozen_rule_families() -> None:
    # Given: the endpoint catalog and the two frozen rule families.
    loader = RuleCatalogLoader()
    endpoint_ids = {
        rule.rule_id
        for rule in loader.load_default_endpoint_capability_rules()
    }
    code_pattern_ids = set()
    for rule in loader.load_default_code_pattern_rules():
        code_pattern_ids.add(rule.rule_id)
        if rule.ua_rule_id is not None:
            code_pattern_ids.add(rule.ua_rule_id)
    package_modules = {
        rule.module for rule in loader.load_default_package_capability_rules()
    }

    # Then: adding endpoint identity cannot change an existing verdict.
    assert endpoint_ids & code_pattern_ids == set()
    assert endpoint_ids & package_modules == set()
    assert all(item.startswith("endpoint_vendor_") for item in endpoint_ids)


def test_raw_http_project_detects_vendors_without_any_sdk(
    tmp_path: Path,
) -> None:
    # Given: a Verba-shaped project -- vendor APIs over plain aiohttp,
    # Ollama through a compose env var, and no vendor SDK anywhere.
    project = tmp_path / "raw_http_rag"
    (project / "app").mkdir(parents=True)
    (project / "app" / "generation.py").write_text(
        "import aiohttp\n"
        "\n"
        "ANTHROPIC_URL = 'https://api.anthropic.com/v1/messages'\n"
        "OPENAI_EMBED_URL = 'https://api.openai.com/v1/embeddings'\n"
        "\n"
        "async def answer(session: aiohttp.ClientSession, prompt: str):\n"
        "    return await session.post(ANTHROPIC_URL, json={'p': prompt})\n",
        encoding="utf-8",
    )
    (project / "docker-compose.yml").write_text(
        "services:\n"
        "  app:\n"
        "    environment:\n"
        "      - OLLAMA_URL=http://host.docker.internal:11434\n",
        encoding="utf-8",
    )
    (project / "requirements.txt").write_text("aiohttp\n", encoding="utf-8")

    # When
    scan = ProjectScanService().scan(project)
    result = ComponentDetectionService().detect(
        template=RagTemplateService.load("rag-core-v1"),
        facts=scan.facts,
        evidence=scan.evidence,
    )

    # Then: the vendors are visible even though nothing imports them.
    providers = {
        instance.provider
        for slot in result.components_by_slot.values()
        for instance in slot.instances
    }
    assert {"anthropic", "openai", "ollama"} <= providers
    assert result.components_by_slot["llm"].status == "detected"
    assert result.components_by_slot["embedding_model"].status == "detected"


def test_sdk_fixture_component_set_is_unchanged_by_the_new_layer() -> None:
    # Given/When: the canonical SDK-style fixture.
    scan = ProjectScanService().scan(
        rag_project_fixture_path("basic_qdrant_ollama_rag")
    )
    result = ComponentDetectionService().detect(
        template=RagTemplateService.load("rag-core-v1"),
        facts=scan.facts,
        evidence=scan.evidence,
    )

    # Then: endpoint identity adds no component of its own here -- the
    # Ollama runtime was already detected through the SDK layers, and
    # merging keeps one instance per provider.
    ollama = [
        instance
        for instance in result.components_by_slot["llm"].instances
        if instance.provider == "ollama"
    ]
    assert len(ollama) == 1
    assert result.components_by_slot["vector_store"].status == "detected"
