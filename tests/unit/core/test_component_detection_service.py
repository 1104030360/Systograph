from __future__ import annotations

from systograph.core.models.scan import ScanFact
from systograph.core.models.system_map import Evidence
from systograph.core.services.component_detection_service import (
    ComponentDetectionResult,
    ComponentDetectionService,
)
from systograph.core.services.rag_template_service import RagTemplateService


def fact_with_evidence(
    *,
    kind: str,
    file: str,
    path: str,
    value: str | None,
    rule_id: str,
) -> tuple[ScanFact, Evidence]:
    evidence_id = f"evidence:{rule_id}:{file}:{path}".replace("/", "_")
    return (
        ScanFact(
            kind=kind,
            file=file,
            path=path,
            value=value,
            rule_id=rule_id,
        ),
        Evidence(
            id=evidence_id,
            kind=kind,
            file=file,
            path=path,
            value=value,
            rule_id=rule_id,
        ),
    )


def detect(
    pairs: list[tuple[ScanFact, Evidence]],
) -> ComponentDetectionResult:
    facts = [fact for fact, _evidence in pairs]
    evidence = [evidence for _fact, evidence in pairs]
    template = RagTemplateService.load("rag-core-v1")
    return ComponentDetectionService().detect(
        template=template,
        facts=facts,
        evidence=evidence,
    )


def test_detect_initializes_every_template_slot() -> None:
    template = RagTemplateService.load("rag-core-v1")

    result = ComponentDetectionService().detect(
        template=template,
        facts=[],
        evidence=[],
    )

    assert set(result.components_by_slot) == {
        slot.id for slot in template.slots
    }
    assert all(
        slot.status == "missing"
        for slot in result.components_by_slot.values()
        if slot.required_for_rag
    )
    assert all(
        slot.status == "not_applicable"
        for slot in result.components_by_slot.values()
        if not slot.required_for_rag
    )


def test_docker_qdrant_detects_vector_store_and_missing_citation() -> None:
    qdrant_fact = fact_with_evidence(
        kind="docker_service",
        file="docker-compose.yml",
        path="services.qdrant.image",
        value="qdrant/qdrant:v1.12.1",
        rule_id="docker_qdrant_image_detected",
    )

    result = detect([qdrant_fact])

    vector_store = result.components_by_slot["vector_store"]
    assert vector_store.status == "detected"
    assert vector_store.instances[0].name == "Qdrant"
    assert vector_store.instances[0].provider == "qdrant"
    assert vector_store.instances[0].evidence_ids

    citation = result.components_by_slot["citation_or_response_composer"]
    assert citation.status == "missing"
    assert citation.instances == []


def test_dependency_only_chromadb_does_not_detect_vector_store() -> None:
    chroma_dependency = fact_with_evidence(
        kind="dependency_candidate",
        file="requirements.txt",
        path="line[1]",
        value="chromadb",
        rule_id="dependency_vector_store_client_chromadb",
    )

    result = detect([chroma_dependency])

    vector_store = result.components_by_slot["vector_store"]
    assert vector_store.status == "missing"
    assert vector_store.instances == []
    assert result.unmapped_components
    assert result.unmapped_components[0].observed_kind == (
        "dependency_candidate"
    )


def test_chroma_client_code_patterns_detect_vector_store() -> None:
    http_fact = fact_with_evidence(
        kind="vector_store_client",
        file="src/vector.py",
        path="line[3]",
        value="chromadb.HttpClient(",
        rule_id="code_pattern_vector_store_chroma_http",
    )
    persistent_fact = fact_with_evidence(
        kind="vector_store_client",
        file="src/local_vector.py",
        path="line[7]",
        value="chromadb.PersistentClient(",
        rule_id="code_pattern_vector_store_chroma_persistent",
    )

    result = detect([http_fact, persistent_fact])

    instances = result.components_by_slot["vector_store"].instances
    assert result.components_by_slot["vector_store"].status == "detected"
    assert {instance.kind for instance in instances} == {
        "http_vector_store",
        "local_persistent_vector_store",
    }
    assert all(instance.evidence_ids for instance in instances)


def test_chroma_host_config_only_does_not_detect_vector_store() -> None:
    chroma_config = fact_with_evidence(
        kind="config_value",
        file=".env",
        path="CHROMA_HOST",
        value="localhost",
        rule_id="config_env_value_detected",
    )

    result = detect([chroma_config])

    vector_store = result.components_by_slot["vector_store"]
    assert vector_store.status == "missing"
    assert vector_store.instances == []


def test_chroma_provider_config_detects_vector_store() -> None:
    direct_config = fact_with_evidence(
        kind="config_value",
        file="config.yaml",
        path="vector_store.provider",
        value="chroma",
        rule_id="config_yaml_value_detected",
    )
    nested_config = fact_with_evidence(
        kind="config_value",
        file="settings.toml",
        path="providers.vector_store.provider",
        value="chroma",
        rule_id="config_toml_value_detected",
    )

    direct_result = detect([direct_config])
    nested_result = detect([nested_config])

    direct_vector_store = direct_result.components_by_slot["vector_store"]
    nested_vector_store = nested_result.components_by_slot["vector_store"]
    assert direct_vector_store.status == "detected"
    assert direct_vector_store.instances[0].provider == "chroma"
    assert direct_vector_store.instances[0].kind == "vector_db_config"
    assert direct_vector_store.instances[0].evidence_ids == [
        direct_config[1].id
    ]
    assert nested_vector_store.status == "detected"
    assert nested_vector_store.instances[0].provider == "chroma"
    assert nested_vector_store.instances[0].kind == "vector_db_config"
    assert nested_vector_store.instances[0].evidence_ids == [
        nested_config[1].id
    ]


def test_supported_vector_store_provider_config_detects_vector_store() -> None:
    qdrant_config = fact_with_evidence(
        kind="config_value",
        file="config.yaml",
        path="vector_store.provider",
        value="qdrant",
        rule_id="config_yaml_value_detected",
    )
    nested_qdrant_config = fact_with_evidence(
        kind="config_value",
        file="settings.toml",
        path="providers.vector_store.provider",
        value="qdrant",
        rule_id="config_toml_value_detected",
    )
    pgvector_config = fact_with_evidence(
        kind="config_value",
        file="config.json",
        path="vector_store.provider",
        value="pgvector",
        rule_id="config_json_value_detected",
    )
    nested_pgvector_config = fact_with_evidence(
        kind="config_value",
        file="config.yaml",
        path="providers.vector_store.provider",
        value="pgvector",
        rule_id="config_yaml_value_detected",
    )

    result = detect(
        [
            qdrant_config,
            nested_qdrant_config,
            pgvector_config,
            nested_pgvector_config,
        ]
    )

    vector_store = result.components_by_slot["vector_store"]
    assert vector_store.status == "detected"
    evidence_by_provider = {
        instance.provider: set(instance.evidence_ids)
        for instance in vector_store.instances
    }
    assert evidence_by_provider == {
        "qdrant": {qdrant_config[1].id, nested_qdrant_config[1].id},
        "pgvector": {
            pgvector_config[1].id,
            nested_pgvector_config[1].id,
        },
    }
    assert result.components_by_slot["llm"].status == "missing"
    assert result.components_by_slot["embedding_model"].status == "missing"


def test_api_route_detection_does_not_create_unmapped_router() -> None:
    route_fact = fact_with_evidence(
        kind="api_route",
        file="src/api.py",
        path="line[12]",
        value='@app.get("/health")',
        rule_id="code_pattern_route_fastapi",
    )

    result = detect([route_fact])

    app_slot = result.components_by_slot["app_api_or_orchestrator"]
    assert app_slot.status == "detected"
    assert app_slot.instances[0].kind == "api_route"
    assert result.unmapped_components == []


def test_openai_code_patterns_detect_embedding_and_llm_slots() -> None:
    embedding_fact = fact_with_evidence(
        kind="embedding",
        file="src/rag.py",
        path="line[10]",
        value="client.embeddings.create(",
        rule_id="code_pattern_embedding_openai_sdk_create",
    )
    llm_fact = fact_with_evidence(
        kind="llm_call",
        file="src/rag.py",
        path="line[18]",
        value="ChatOpenAI",
        rule_id="code_pattern_llm_chat_openai",
    )

    result = detect([embedding_fact, llm_fact])

    embedding_slot = result.components_by_slot["embedding_model"]
    llm_slot = result.components_by_slot["llm"]
    assert embedding_slot.status == "detected"
    assert embedding_slot.instances[0].provider == "openai"
    assert llm_slot.status == "detected"
    assert llm_slot.instances[0].provider == "openai"


def test_openai_provider_config_detects_slot_specific_components() -> None:
    llm_provider_fact = fact_with_evidence(
        kind="config_value",
        file="config.yaml",
        path="providers.llm.provider",
        value="openai",
        rule_id="config_yaml_value_detected",
    )
    embedding_provider_fact = fact_with_evidence(
        kind="config_value",
        file="config.yaml",
        path="providers.embedding.provider",
        value="openai",
        rule_id="config_yaml_value_detected",
    )

    result = detect([llm_provider_fact, embedding_provider_fact])

    llm_slot = result.components_by_slot["llm"]
    embedding_slot = result.components_by_slot["embedding_model"]
    assert llm_slot.status == "detected"
    assert llm_slot.instances[0].provider == "openai"
    assert llm_slot.instances[0].evidence_ids == [llm_provider_fact[1].id]
    assert embedding_slot.status == "detected"
    assert embedding_slot.instances[0].provider == "openai"
    assert embedding_slot.instances[0].evidence_ids == [
        embedding_provider_fact[1].id
    ]


def test_openai_env_config_still_detects_embedding_and_llm_slots() -> None:
    openai_env_fact = fact_with_evidence(
        kind="config_value",
        file=".env",
        path="OPENAI_API_KEY",
        value="sk-t...mple",
        rule_id="config_env_value_detected",
    )

    result = detect([openai_env_fact])

    llm_slot = result.components_by_slot["llm"]
    embedding_slot = result.components_by_slot["embedding_model"]
    assert llm_slot.status == "detected"
    assert llm_slot.instances[0].provider == "openai"
    assert embedding_slot.status == "detected"
    assert embedding_slot.instances[0].provider == "openai"


def test_ollama_provider_config_detects_llm_only() -> None:
    direct_config = fact_with_evidence(
        kind="config_value",
        file="config.yaml",
        path="llm.provider",
        value="ollama",
        rule_id="config_yaml_value_detected",
    )
    nested_config = fact_with_evidence(
        kind="config_value",
        file="settings.toml",
        path="providers.llm.provider",
        value="ollama",
        rule_id="config_toml_value_detected",
    )

    result = detect([direct_config, nested_config])

    llm_slot = result.components_by_slot["llm"]
    assert llm_slot.status == "detected"
    assert llm_slot.instances[0].name == "Ollama"
    assert llm_slot.instances[0].provider == "ollama"
    assert set(llm_slot.instances[0].evidence_ids) == {
        direct_config[1].id,
        nested_config[1].id,
    }
    assert result.components_by_slot["vector_store"].status == "missing"
    assert result.components_by_slot["embedding_model"].status == "missing"


def test_dependency_only_supported_providers_remain_weak_signals() -> None:
    qdrant_dependency = fact_with_evidence(
        kind="dependency_candidate",
        file="requirements.txt",
        path="line[1]",
        value="qdrant-client",
        rule_id="dependency_vector_store_client_qdrant",
    )
    ollama_dependency = fact_with_evidence(
        kind="dependency_candidate",
        file="requirements.txt",
        path="line[2]",
        value="ollama",
        rule_id="dependency_local_llm_provider_ollama",
    )

    result = detect([qdrant_dependency, ollama_dependency])

    assert result.components_by_slot["vector_store"].status == "missing"
    assert result.components_by_slot["llm"].status == "missing"
    assert {
        component.observed_kind for component in result.unmapped_components
    } == {"dependency_candidate"}
    assert {
        evidence_id
        for component in result.unmapped_components
        for evidence_id in component.evidence_ids
    } == {qdrant_dependency[1].id, ollama_dependency[1].id}


def test_unsupported_provider_config_does_not_detect_component() -> None:
    faiss_config = fact_with_evidence(
        kind="config_value",
        file="config.yaml",
        path="vector_store.provider",
        value="faiss",
        rule_id="config_yaml_value_detected",
    )
    embedding_ollama_config = fact_with_evidence(
        kind="config_value",
        file="config.yaml",
        path="embedding.provider",
        value="ollama",
        rule_id="config_yaml_value_detected",
    )

    result = detect([faiss_config, embedding_ollama_config])

    assert result.components_by_slot["vector_store"].status == "missing"
    assert result.components_by_slot["llm"].status == "missing"
    assert result.components_by_slot["embedding_model"].status == "missing"


def test_custom_router_goes_to_unmapped_not_retriever() -> None:
    router_fact = fact_with_evidence(
        kind="config_value",
        file="config.yaml",
        path="router.kind",
        value="custom_query_router",
        rule_id="config_yaml_value_detected",
    )

    result = detect([router_fact])

    retriever = result.components_by_slot["retriever"]
    assert retriever.status == "missing"
    assert retriever.instances == []
    assert len(result.unmapped_components) == 1
    assert result.unmapped_components[0].status == "needs_confirmation"
    assert result.unmapped_components[0].evidence_ids


def test_reranker_fact_becomes_non_baseline_confirmation_item() -> None:
    reranker_fact = fact_with_evidence(
        kind="config_value",
        file="config.yaml",
        path="reranker.provider",
        value="sentence_transformers",
        rule_id="config_yaml_value_detected",
    )

    result = detect([reranker_fact])

    assert len(result.unmapped_components) == 1
    assert result.unmapped_components[0].observed_kind == "reranker_candidate"
    assert result.unmapped_components[0].status == "needs_confirmation"
    assert result.unmapped_components[0].evidence_ids
