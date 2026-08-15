from __future__ import annotations

from systograph.core.models.scan import ScanFact
from systograph.core.models.structural_fact import (
    ImportStructuralFact,
    SourceSpan,
    StructuralFact,
)
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


def test_package_import_fact_detects_component_with_import_evidence() -> None:
    import_fact = fact_with_evidence(
        kind="external_import_declaration",
        file="src/retriever.py",
        path="line[1]",
        value="ollama",
        rule_id="ast_external_import",
    )

    result = detect([import_fact])

    llm_slot = result.components_by_slot["llm"]
    assert llm_slot.status == "detected"
    assert llm_slot.instances[0].id == "component:llm:ollama"
    assert llm_slot.instances[0].kind == "local_llm_runtime"
    assert llm_slot.instances[0].evidence_ids == [import_fact[1].id]
    assert result.unmapped_components == []


def test_package_import_dedupes_with_other_evidence_families() -> None:
    # The same component id from docker evidence and from the package
    # identity layer must collapse to one instance with merged evidence.
    docker_fact = fact_with_evidence(
        kind="docker_service",
        file="docker-compose.yml",
        path="services.ollama.image",
        value="ollama/ollama:0.5.4",
        rule_id="docker_ollama_image_detected",
    )
    import_fact = fact_with_evidence(
        kind="external_import_declaration",
        file="src/retriever.py",
        path="line[1]",
        value="ollama",
        rule_id="ast_external_import",
    )

    result = detect([docker_fact, import_fact])

    llm_instances = result.components_by_slot["llm"].instances
    assert [instance.id for instance in llm_instances] == [
        "component:llm:ollama"
    ]
    assert set(llm_instances[0].evidence_ids) == {
        docker_fact[1].id,
        import_fact[1].id,
    }


def test_package_import_materializes_non_template_parser_slot() -> None:
    # "parser" is not a rag-core-v1 template slot: the detection service
    # must materialize it as a detected, non-required capability slot.
    import_fact = fact_with_evidence(
        kind="external_import_declaration",
        file="src/ingest.py",
        path="line[2]",
        value="bs4.BeautifulSoup",
        rule_id="ast_external_import",
    )

    result = detect([import_fact])

    parser_slot = result.components_by_slot["parser"]
    assert parser_slot.status == "detected"
    assert parser_slot.required_for_rag is False
    assert parser_slot.instances[0].id == "component:parser:beautifulsoup4"
    assert parser_slot.instances[0].kind == "parser"
    template = RagTemplateService.load("rag-core-v1")
    assert "parser" not in {slot.id for slot in template.slots}


def import_with_evidence(
    *,
    file: str,
    line: int,
    module: str,
    symbol: str | None = None,
    alias: str | None = None,
) -> tuple[ScanFact, Evidence, ImportStructuralFact]:
    """One external import as the AST provider emits it: fact,
    mirrored indirect evidence row, and the structural fact carrying
    symbol/alias."""
    value = module if symbol is None else f"{module}.{symbol}"
    path = f"line[{line}]"
    return (
        ScanFact(
            kind="external_import_declaration",
            file=file,
            path=path,
            value=value,
            rule_id="ast_external_import",
        ),
        Evidence(
            id=f"evidence:import:{file.replace('/', '_')}:{line}",
            kind="external_import_declaration",
            file=file,
            path=path,
            value=value,
            rule_id="ast_external_import",
            line_start=line,
            line_end=line,
            evidence_kind_hint="indirect",
        ),
        ImportStructuralFact(
            identity_namespace="ua_external_import",
            import_scope="external",
            module=module,
            symbol=symbol,
            alias=alias,
            span=SourceSpan(file=file, line_start=line, line_end=line),
        ),
    )


def call_evidence(
    *,
    file: str,
    line: int,
    caller: str,
    callee: str,
) -> Evidence:
    """One UA call evidence row as the UA structural adapter emits it."""
    return Evidence(
        id=f"evidence:ua:call:{file.replace('/', '_')}:{line}",
        kind="call_hint",
        file=file,
        path=f"calls[{caller}->{callee}]",
        value=callee,
        rule_id="ua_call_hint_static",
        line_start=line,
        line_end=line,
        evidence_kind_hint="direct",
    )


def detect_with_structural(
    facts: list[ScanFact],
    evidence: list[Evidence],
    structural_facts: list[StructuralFact],
) -> ComponentDetectionResult:
    return ComponentDetectionService().detect(
        template=RagTemplateService.load("rag-core-v1"),
        facts=facts,
        evidence=evidence,
        structural_facts=structural_facts,
    )


def test_usage_join_attaches_same_file_call_evidence() -> None:
    fact, import_evidence, structural = import_with_evidence(
        file="backend/engine/engine.py",
        line=10,
        module="llama_index.core.memory",
        symbol="ChatMemoryBuffer",
    )
    usage = call_evidence(
        file="backend/engine/engine.py",
        line=42,
        caller="backend.engine.engine.get_chat_engine",
        callee="ChatMemoryBuffer.from_defaults",
    )

    result = detect_with_structural(
        [fact],
        [import_evidence, usage],
        [structural],
    )

    memory_slot = result.components_by_slot["working_memory"]
    assert memory_slot.status == "detected"
    instance = memory_slot.instances[0]
    assert instance.id == "component:working_memory:llama_index"
    assert set(instance.evidence_ids) == {import_evidence.id, usage.id}


def test_usage_join_ignores_calls_in_other_files() -> None:
    fact, import_evidence, structural = import_with_evidence(
        file="backend/engine/engine.py",
        line=10,
        module="llama_index.core.memory",
        symbol="ChatMemoryBuffer",
    )
    other_file_usage = call_evidence(
        file="backend/workflows/single.py",
        line=42,
        caller="backend.workflows.single.plan",
        callee="ChatMemoryBuffer.from_defaults",
    )

    result = detect_with_structural(
        [fact],
        [import_evidence, other_file_usage],
        [structural],
    )

    instance = result.components_by_slot["working_memory"].instances[0]
    assert instance.evidence_ids == [import_evidence.id]


def test_usage_join_matches_alias_not_module_name() -> None:
    # "import qdrant_client as qc": qc is the only name usable in code.
    fact, import_evidence, structural = import_with_evidence(
        file="src/store.py",
        line=1,
        module="qdrant_client",
        alias="qc",
    )
    alias_usage = call_evidence(
        file="src/store.py",
        line=9,
        caller="src.store.build_store",
        callee="qc.QdrantClient",
    )

    result = detect_with_structural(
        [fact],
        [import_evidence, alias_usage],
        [structural],
    )

    instance = result.components_by_slot["vector_store"].instances[0]
    assert instance.id == "component:vector_store:qdrant"
    assert set(instance.evidence_ids) == {import_evidence.id, alias_usage.id}


def test_usage_join_requires_exact_name_or_attribute_extension() -> None:
    # "ChatMemoryBufferFactory" must NOT match "ChatMemoryBuffer".
    fact, import_evidence, structural = import_with_evidence(
        file="backend/engine/engine.py",
        line=10,
        module="llama_index.core.memory",
        symbol="ChatMemoryBuffer",
    )
    near_miss = call_evidence(
        file="backend/engine/engine.py",
        line=42,
        caller="backend.engine.engine.get_chat_engine",
        callee="ChatMemoryBufferFactory.build",
    )

    result = detect_with_structural(
        [fact],
        [import_evidence, near_miss],
        [structural],
    )

    instance = result.components_by_slot["working_memory"].instances[0]
    assert instance.evidence_ids == [import_evidence.id]


def test_usage_join_module_only_import_matches_dotted_callee() -> None:
    # "import llama_index.core.memory": the usable name is the full
    # dotted module path itself.
    fact, import_evidence, structural = import_with_evidence(
        file="backend/engine/engine.py",
        line=3,
        module="llama_index.core.memory",
    )
    dotted_usage = call_evidence(
        file="backend/engine/engine.py",
        line=21,
        caller="backend.engine.engine.get_chat_engine",
        callee="llama_index.core.memory.ChatMemoryBuffer.from_defaults",
    )

    result = detect_with_structural(
        [fact],
        [import_evidence, dotted_usage],
        [structural],
    )

    instance = result.components_by_slot["working_memory"].instances[0]
    assert set(instance.evidence_ids) == {import_evidence.id, dotted_usage.id}


def test_ragapp_shaped_imports_create_distinct_deduped_components() -> None:
    # One engine file importing three capabilities plus a second file
    # importing memory again: three distinct components, memory merged.
    engine_agent = import_with_evidence(
        file="backend/engine/engine.py",
        line=7,
        module="llama_index.core.agent",
        symbol="AgentRunner",
    )
    engine_chat = import_with_evidence(
        file="backend/engine/engine.py",
        line=9,
        module="llama_index.core.chat_engine",
        symbol="CondensePlusContextChatEngine",
    )
    engine_memory = import_with_evidence(
        file="backend/engine/engine.py",
        line=10,
        module="llama_index.core.memory",
        symbol="ChatMemoryBuffer",
    )
    workflow_memory = import_with_evidence(
        file="backend/workflows/single.py",
        line=7,
        module="llama_index.core.memory",
        symbol="ChatMemoryBuffer",
    )
    pairs = [engine_agent, engine_chat, engine_memory, workflow_memory]

    result = detect_with_structural(
        [fact for fact, _evidence, _structural in pairs],
        [evidence for _fact, evidence, _structural in pairs],
        [structural for _fact, _evidence, structural in pairs],
    )

    assert result.components_by_slot["agent_loop"].instances[0].id == (
        "component:agent_loop:llama_index"
    )
    assert result.components_by_slot["context_composer"].instances[0].id == (
        "component:context_composer:llama_index"
    )
    memory_instances = result.components_by_slot["working_memory"].instances
    assert [instance.id for instance in memory_instances] == [
        "component:working_memory:llama_index"
    ]
    assert set(memory_instances[0].evidence_ids) == {
        engine_memory[1].id,
        workflow_memory[1].id,
    }
    assert result.unmapped_components == []
