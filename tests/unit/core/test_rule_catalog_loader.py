from __future__ import annotations

from pathlib import Path

import pytest

from systograph.core.services.rule_catalog_loader import (
    RuleCatalogError,
    RuleCatalogLoader,
)

TASK14_RISK_RULE_IDS = {
    "docker_published_port_exposure",
    "external_provider_detected",
    "config_parse_error",
    "secret_like_config_key_detected",
    "missing_required_slot",
    "chroma_http_endpoint_detected",
    "chroma_local_persistence_detected",
    "chroma_server_published_port",
}
PROVIDER_PARSE_RISK_RULE_IDS = {
    "config_parse_error",
    "docker_compose_parse_error",
    "dependency_manifest_parse_error",
    "code_pattern_read_error",
    "project_scan_provider_failed",
}
RECOMMENDED_NEXT_CHECK_IDS = {
    "runtime_readiness",
    "privacy_exposure",
    "rag_knowledge_trust",
}


def write_catalog(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_load_dependency_rules_from_valid_catalog(tmp_path: Path) -> None:
    catalog_path = write_catalog(
        tmp_path / "dependency_rules.toml",
        "\n".join(
            [
                "[[python]]",
                'package = "langchain"',
                'rule_id = "dependency_rag_framework_langchain"',
                "match_prefix = true",
                "",
                "[[node]]",
                'package = "@langchain/"',
                'rule_id = "dependency_rag_framework_langchain"',
                "match_prefix = true",
            ]
        )
        + "\n",
    )

    rules = RuleCatalogLoader().load_dependency_rules(catalog_path)

    assert [rule.package for rule in rules.python] == ["langchain"]
    assert rules.python[0].match_prefix is True
    assert [rule.package for rule in rules.node] == ["@langchain/"]


def test_dependency_catalog_rejects_missing_required_field(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "dependency_rules.toml",
        "\n".join(
            [
                "[[python]]",
                'package = "openai"',
                "match_prefix = false",
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="rule_id"):
        RuleCatalogLoader().load_dependency_rules(catalog_path)


def test_dependency_catalog_rejects_duplicate_package(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "dependency_rules.toml",
        "\n".join(
            [
                "[[python]]",
                'package = "openai"',
                'rule_id = "dependency_external_llm_embedding_openai"',
                "match_prefix = false",
                "",
                "[[python]]",
                'package = "openai"',
                'rule_id = "dependency_duplicate_openai"',
                "match_prefix = false",
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="duplicate package"):
        RuleCatalogLoader().load_dependency_rules(catalog_path)


def test_dependency_catalog_requires_explicit_prefix_match(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "dependency_rules.toml",
        "\n".join(
            [
                "[[python]]",
                'package = "openai"',
                'rule_id = "dependency_external_llm_embedding_openai"',
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="match_prefix"):
        RuleCatalogLoader().load_dependency_rules(catalog_path)


def test_load_docker_image_rules_from_valid_catalog(tmp_path: Path) -> None:
    catalog_path = write_catalog(
        tmp_path / "docker_image_rules.toml",
        "\n".join(
            [
                "[[images]]",
                'repository = "qdrant/qdrant"',
                'rule_id = "docker_qdrant_image_detected"',
            ]
        )
        + "\n",
    )

    rules = RuleCatalogLoader().load_docker_image_rules(catalog_path)

    assert rules[0].repository == "qdrant/qdrant"
    assert rules[0].rule_id == "docker_qdrant_image_detected"


def test_docker_image_catalog_rejects_duplicate_repository(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "docker_image_rules.toml",
        "\n".join(
            [
                "[[images]]",
                'repository = "ollama/ollama"',
                'rule_id = "docker_ollama_image_detected"',
                "",
                "[[images]]",
                'repository = "ollama/ollama"',
                'rule_id = "docker_duplicate_ollama"',
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="duplicate repository"):
        RuleCatalogLoader().load_docker_image_rules(catalog_path)


def test_docker_image_catalog_rejects_duplicate_rule_id(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "docker_image_rules.toml",
        "\n".join(
            [
                "[[images]]",
                'repository = "ollama/ollama"',
                'rule_id = "docker_shared"',
                "",
                "[[images]]",
                'repository = "qdrant/qdrant"',
                'rule_id = "docker_shared"',
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="duplicate rule_id"):
        RuleCatalogLoader().load_docker_image_rules(catalog_path)


def test_load_code_pattern_rules_from_valid_catalog(tmp_path: Path) -> None:
    catalog_path = write_catalog(
        tmp_path / "code_pattern_rules.toml",
        "\n".join(
            [
                "[[patterns]]",
                'rule_id = "code_custom_qdrant"',
                'kind = "vector_store_client"',
                'languages = ["python"]',
                'extensions = [".py"]',
                'regex = "\\\\bQdrantClient\\\\b"',
                'snippet_group = ""',
            ]
        )
        + "\n",
    )

    rules = RuleCatalogLoader().load_code_pattern_rules(catalog_path)

    assert rules[0].rule_id == "code_custom_qdrant"
    assert rules[0].regex.search("QdrantClient")
    assert rules[0].snippet_group == ""
    assert rules[0].symbol is None
    assert rules[0].ua_rule_id is None


def test_load_code_pattern_rule_with_optional_symbol(tmp_path: Path) -> None:
    # Given: a constructor pattern with one precise dotted symbol.
    catalog_path = write_catalog(
        tmp_path / "code_pattern_rules.toml",
        "\n".join(
            [
                "[[patterns]]",
                'rule_id = "code_custom_qdrant"',
                'kind = "vector_store_client"',
                'languages = ["python"]',
                'extensions = [".py"]',
                'regex = "\\\\bQdrantClient\\\\b"',
                'snippet_group = ""',
                'symbol = "qdrant_client.QdrantClient"',
            ]
        )
        + "\n",
    )

    # When: the catalog is loaded.
    rules = RuleCatalogLoader().load_code_pattern_rules(catalog_path)

    # Then: the optional translation identity is retained as typed metadata.
    assert rules[0].symbol == "qdrant_client.QdrantClient"


def test_load_code_pattern_rule_with_optional_ua_mirror(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "code_pattern_rules.toml",
        "\n".join(
            [
                "[[patterns]]",
                'rule_id = "code_pattern_vector_store_qdrant"',
                'kind = "vector_store_client"',
                'languages = ["python"]',
                'extensions = [".py"]',
                'regex = "QdrantClient"',
                'snippet_group = ""',
                'symbol = "qdrant_client.QdrantClient"',
                'ua_rule_id = "ua_call_hint_vector_store_qdrant"',
            ]
        )
        + "\n",
    )

    when_rules = RuleCatalogLoader().load_code_pattern_rules(catalog_path)

    assert when_rules[0].ua_rule_id == "ua_call_hint_vector_store_qdrant"


def test_code_pattern_catalog_requires_symbol_for_ua_mirror(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "code_pattern_rules.toml",
        "\n".join(
            [
                "[[patterns]]",
                'rule_id = "code_pattern_vector_store_qdrant"',
                'kind = "vector_store_client"',
                'languages = ["python"]',
                'extensions = [".py"]',
                'regex = "QdrantClient"',
                'snippet_group = ""',
                'ua_rule_id = "ua_call_hint_vector_store_qdrant"',
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="ua_rule_id requires symbol"):
        RuleCatalogLoader().load_code_pattern_rules(catalog_path)


def test_code_pattern_catalog_rejects_duplicate_ua_rule_id(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "code_pattern_rules.toml",
        "\n".join(
            [
                "[[patterns]]",
                'rule_id = "code_qdrant_one"',
                'kind = "vector_store_client"',
                'languages = ["python"]',
                'extensions = [".py"]',
                'regex = "QdrantClient"',
                'snippet_group = ""',
                'symbol = "qdrant_client.QdrantClient"',
                'ua_rule_id = "ua_call_hint_shared"',
                "",
                "[[patterns]]",
                'rule_id = "code_chroma_two"',
                'kind = "vector_store_client"',
                'languages = ["python"]',
                'extensions = [".py"]',
                'regex = "HttpClient"',
                'snippet_group = ""',
                'symbol = "chromadb.HttpClient"',
                'ua_rule_id = "ua_call_hint_shared"',
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="duplicate ua_rule_id"):
        RuleCatalogLoader().load_code_pattern_rules(catalog_path)


def test_default_code_pattern_catalog_pins_ua_legacy_mirrors() -> None:
    when_rules = RuleCatalogLoader().load_default_code_pattern_rules()

    assert {
        rule.rule_id: rule.ua_rule_id
        for rule in when_rules
        if rule.ua_rule_id is not None
    } == {
        "code_pattern_embedding_ollama": "ua_call_hint_embedding_ollama",
        "code_pattern_vector_store_qdrant": (
            "ua_call_hint_vector_store_qdrant"
        ),
        "code_pattern_vector_store_chroma_http": (
            "ua_call_hint_vector_store_chroma_http"
        ),
        "code_pattern_vector_store_chroma_async_http": (
            "ua_call_hint_vector_store_chroma_async_http"
        ),
        "code_pattern_vector_store_chroma_persistent": (
            "ua_call_hint_vector_store_chroma_persistent"
        ),
    }


def test_code_pattern_catalog_rejects_duplicate_symbol(tmp_path: Path) -> None:
    # Given: two distinct patterns that claim the same semantic symbol.
    catalog_path = write_catalog(
        tmp_path / "code_pattern_rules.toml",
        "\n".join(
            [
                "[[patterns]]",
                'rule_id = "code_qdrant_one"',
                'kind = "vector_store_client"',
                'languages = ["python"]',
                'extensions = [".py"]',
                'regex = "QdrantClient\\\\("',
                'snippet_group = ""',
                'symbol = "qdrant_client.QdrantClient"',
                "",
                "[[patterns]]",
                'rule_id = "code_qdrant_two"',
                'kind = "vector_store_client"',
                'languages = ["python"]',
                'extensions = [".py"]',
                'regex = "QdrantClient\\\\.from_url\\\\("',
                'snippet_group = ""',
                'symbol = "qdrant_client.QdrantClient"',
            ]
        )
        + "\n",
    )

    # When/Then: ambiguity is rejected instead of picking one rule silently.
    with pytest.raises(RuleCatalogError, match="duplicate symbol"):
        RuleCatalogLoader().load_code_pattern_rules(catalog_path)


@pytest.mark.parametrize(
    "symbol_line",
    [
        'symbol = ""',
        'symbol = "QdrantClient"',
        'symbol = "qdrant_client. QdrantClient"',
        "symbol = 42",
    ],
)
def test_code_pattern_catalog_rejects_invalid_symbol_format(
    tmp_path: Path,
    symbol_line: str,
) -> None:
    # Given: a present symbol that is not a non-empty dotted identifier.
    catalog_path = write_catalog(
        tmp_path / "code_pattern_rules.toml",
        "\n".join(
            [
                "[[patterns]]",
                'rule_id = "code_invalid_symbol"',
                'kind = "vector_store_client"',
                'languages = ["python"]',
                'extensions = [".py"]',
                'regex = "QdrantClient"',
                'snippet_group = ""',
                symbol_line,
            ]
        )
        + "\n",
    )

    # When/Then: malformed identity metadata fails closed.
    with pytest.raises(RuleCatalogError, match="symbol"):
        RuleCatalogLoader().load_code_pattern_rules(catalog_path)


def test_default_code_pattern_symbols_only_cover_precise_calls() -> None:
    # Given/When: the bundled translation catalog is loaded.
    rules = RuleCatalogLoader().load_default_code_pattern_rules()
    symbols_by_rule = {rule.rule_id: rule.symbol for rule in rules}

    # Then: only unambiguous dotted callables are catalogued.
    assert {
        rule_id: symbol
        for rule_id, symbol in symbols_by_rule.items()
        if symbol is not None
    } == {
        "code_pattern_embedding_ollama": "ollama.embeddings",
        "code_pattern_vector_store_qdrant": ("qdrant_client.QdrantClient"),
        "code_pattern_vector_store_chroma_http": "chromadb.HttpClient",
        "code_pattern_vector_store_chroma_async_http": (
            "chromadb.AsyncHttpClient"
        ),
        "code_pattern_vector_store_chroma_persistent": (
            "chromadb.PersistentClient"
        ),
    }
    assert symbols_by_rule["code_pattern_retriever_as_retriever"] is None
    assert symbols_by_rule["code_pattern_route_fastapi"] is None


def test_code_pattern_catalog_rejects_regex_compile_failure(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "code_pattern_rules.toml",
        "\n".join(
            [
                "[[patterns]]",
                'rule_id = "code_broken"',
                'kind = "code_pattern"',
                'languages = ["python"]',
                'extensions = [".py"]',
                'regex = "["',
                'snippet_group = ""',
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="regex"):
        RuleCatalogLoader().load_code_pattern_rules(catalog_path)


def test_catalog_loader_rejects_malformed_toml(tmp_path: Path) -> None:
    catalog_path = write_catalog(
        tmp_path / "dependency_rules.toml",
        "[[python]\n",
    )

    with pytest.raises(RuleCatalogError, match="Failed to parse"):
        RuleCatalogLoader().load_dependency_rules(catalog_path)


def test_load_risk_hint_rules_from_valid_catalog(tmp_path: Path) -> None:
    catalog_path = write_catalog(
        tmp_path / "risk_hint_rules.toml",
        "\n".join(
            [
                "[[risk_hints]]",
                'rule_id = "docker_published_port_exposure"',
                'type = "network_exposure"',
                'default_severity_hint = "medium"',
                (
                    'rationale = "Docker published port may expose a '
                    'service endpoint."'
                ),
                (
                    'uncertainty = "Static scan does not verify runtime '
                    'reachability."'
                ),
            ]
        )
        + "\n",
    )

    rules = RuleCatalogLoader().load_risk_hint_rules(catalog_path)

    assert rules[0].rule_id == "docker_published_port_exposure"
    assert rules[0].type == "network_exposure"
    assert rules[0].default_severity_hint == "medium"
    assert "Docker published port" in rules[0].rationale
    assert "Static scan" in rules[0].uncertainty


def test_risk_hint_catalog_rejects_duplicate_rule_id(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "risk_hint_rules.toml",
        "\n".join(
            [
                "[[risk_hints]]",
                'rule_id = "external_provider_detected"',
                'type = "external_provider"',
                'default_severity_hint = "medium"',
                'rationale = "External provider detected."',
                'uncertainty = "Static scan only."',
                "",
                "[[risk_hints]]",
                'rule_id = "external_provider_detected"',
                'type = "external_provider"',
                'default_severity_hint = "medium"',
                'rationale = "Duplicate external provider detected."',
                'uncertainty = "Static scan only."',
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="duplicate rule_id"):
        RuleCatalogLoader().load_risk_hint_rules(catalog_path)


@pytest.mark.parametrize("missing_field", ["rationale", "uncertainty"])
def test_risk_hint_catalog_requires_wording_fields(
    tmp_path: Path,
    missing_field: str,
) -> None:
    fields = {
        "rule_id": 'rule_id = "config_parse_error"',
        "type": 'type = "partial_scan"',
        "default_severity_hint": 'default_severity_hint = "medium"',
        "rationale": 'rationale = "Config parse error may make map partial."',
        "uncertainty": 'uncertainty = "Only parsed files produce facts."',
    }
    del fields[missing_field]
    catalog_path = write_catalog(
        tmp_path / "risk_hint_rules.toml",
        "\n".join(["[[risk_hints]]", *fields.values()]) + "\n",
    )

    with pytest.raises(RuleCatalogError, match=missing_field):
        RuleCatalogLoader().load_risk_hint_rules(catalog_path)


def test_default_risk_hint_catalog_covers_task14_rule_ids() -> None:
    rules = RuleCatalogLoader().load_default_risk_hint_rules()

    assert {rule.rule_id for rule in rules} >= TASK14_RISK_RULE_IDS


def test_default_risk_hint_catalog_covers_provider_parse_rule_ids() -> None:
    rules = RuleCatalogLoader().load_default_risk_hint_rules()

    assert {rule.rule_id for rule in rules} >= PROVIDER_PARSE_RISK_RULE_IDS


def test_load_recommended_next_check_rules_from_valid_catalog(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "recommended_next_check_rules.toml",
        "\n".join(
            [
                "[[recommended_next_checks]]",
                'id = "runtime_readiness"',
                'default_target_type = "system"',
                'reason = "Static scan found runtime-dependent services."',
                (
                    'action = "Verify services start and endpoints are '
                    'reachable."'
                ),
            ]
        )
        + "\n",
    )

    rules = RuleCatalogLoader().load_recommended_next_check_rules(catalog_path)

    assert rules[0].id == "runtime_readiness"
    assert rules[0].default_target_type == "system"
    assert "runtime-dependent" in rules[0].reason
    assert "endpoints" in rules[0].action


def test_recommended_next_check_catalog_rejects_duplicate_id(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "recommended_next_check_rules.toml",
        "\n".join(
            [
                "[[recommended_next_checks]]",
                'id = "runtime_readiness"',
                'default_target_type = "system"',
                'reason = "Static scan found runtime-dependent services."',
                'action = "Verify services start."',
                "",
                "[[recommended_next_checks]]",
                'id = "runtime_readiness"',
                'default_target_type = "system"',
                'reason = "Duplicate runtime check."',
                'action = "Duplicate action."',
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="duplicate id"):
        RuleCatalogLoader().load_recommended_next_check_rules(catalog_path)


@pytest.mark.parametrize("missing_field", ["reason", "action"])
def test_recommended_next_check_catalog_requires_wording_fields(
    tmp_path: Path,
    missing_field: str,
) -> None:
    fields = {
        "id": 'id = "runtime_readiness"',
        "default_target_type": 'default_target_type = "system"',
        "reason": 'reason = "Static scan found runtime services."',
        "action": 'action = "Verify runtime services."',
    }
    del fields[missing_field]
    catalog_path = write_catalog(
        tmp_path / "recommended_next_check_rules.toml",
        "\n".join(["[[recommended_next_checks]]", *fields.values()]) + "\n",
    )

    with pytest.raises(RuleCatalogError, match=missing_field):
        RuleCatalogLoader().load_recommended_next_check_rules(catalog_path)


def test_default_recommended_next_check_catalog_covers_initial_ids() -> None:
    rules = RuleCatalogLoader().load_default_recommended_next_check_rules()

    assert {rule.id for rule in rules} == RECOMMENDED_NEXT_CHECK_IDS


def test_load_package_capability_rules_from_valid_catalog(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "package_capability_rules.toml",
        "\n".join(
            [
                "[[packages]]",
                'module = "qdrant_client"',
                'slot = "vector_store"',
                'kind = "vector_db"',
                'name = "Qdrant"',
                'provider = "qdrant"',
            ]
        )
        + "\n",
    )

    rules = RuleCatalogLoader().load_package_capability_rules(catalog_path)

    assert [
        (rule.module, rule.slot, rule.kind, rule.name, rule.provider)
        for rule in rules
    ] == [("qdrant_client", "vector_store", "vector_db", "Qdrant", "qdrant")]


@pytest.mark.parametrize(
    "missing_field",
    ["module", "slot", "kind", "name", "provider"],
)
def test_package_capability_catalog_requires_fields(
    tmp_path: Path,
    missing_field: str,
) -> None:
    fields = {
        "module": 'module = "ollama"',
        "slot": 'slot = "llm"',
        "kind": 'kind = "local_llm_runtime"',
        "name": 'name = "Ollama"',
        "provider": 'provider = "ollama"',
    }
    del fields[missing_field]
    catalog_path = write_catalog(
        tmp_path / "package_capability_rules.toml",
        "\n".join(["[[packages]]", *fields.values()]) + "\n",
    )

    with pytest.raises(RuleCatalogError, match=missing_field):
        RuleCatalogLoader().load_package_capability_rules(catalog_path)


def test_package_capability_catalog_rejects_duplicate_module(
    tmp_path: Path,
) -> None:
    entry = "\n".join(
        [
            "[[packages]]",
            'module = "ollama"',
            'slot = "llm"',
            'kind = "local_llm_runtime"',
            'name = "Ollama"',
            'provider = "ollama"',
        ]
    )
    catalog_path = write_catalog(
        tmp_path / "package_capability_rules.toml",
        f"{entry}\n\n{entry}\n",
    )

    with pytest.raises(RuleCatalogError, match="duplicate module"):
        RuleCatalogLoader().load_package_capability_rules(catalog_path)


def test_package_capability_catalog_accepts_dotted_module_prefix(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "package_capability_rules.toml",
        "\n".join(
            [
                "[[packages]]",
                'module = "llama_index.core.memory"',
                'slot = "working_memory"',
                'kind = "working_memory"',
                'name = "LlamaIndex Chat Memory"',
                'provider = "llama_index"',
            ]
        )
        + "\n",
    )

    rules = RuleCatalogLoader().load_package_capability_rules(catalog_path)

    assert [rule.module for rule in rules] == ["llama_index.core.memory"]


def test_package_capability_catalog_accepts_top_level_coexistence(
    tmp_path: Path,
) -> None:
    # Longest-prefix matching makes a top-level key and a dotted key
    # of the same package deterministic, so the loader accepts both.
    catalog_path = write_catalog(
        tmp_path / "package_capability_rules.toml",
        "\n".join(
            [
                "[[packages]]",
                'module = "pkg"',
                'slot = "llm"',
                'kind = "local_llm_runtime"',
                'name = "Pkg"',
                'provider = "pkg"',
                "",
                "[[packages]]",
                'module = "pkg.memory"',
                'slot = "working_memory"',
                'kind = "working_memory"',
                'name = "Pkg Memory"',
                'provider = "pkg"',
            ]
        )
        + "\n",
    )

    rules = RuleCatalogLoader().load_package_capability_rules(catalog_path)

    assert [rule.module for rule in rules] == ["pkg", "pkg.memory"]


@pytest.mark.parametrize(
    "invalid_module",
    [
        "llama_index..core",
        ".llama_index",
        "llama_index.",
        "llama_index.1core",
        "llama-index.core",
    ],
)
def test_package_capability_catalog_rejects_invalid_module_keys(
    tmp_path: Path,
    invalid_module: str,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "package_capability_rules.toml",
        "\n".join(
            [
                "[[packages]]",
                f'module = "{invalid_module}"',
                'slot = "vector_store"',
                'kind = "vector_db"',
                'name = "Qdrant"',
                'provider = "qdrant"',
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="dotted module path"):
        RuleCatalogLoader().load_package_capability_rules(catalog_path)


def test_package_capability_catalog_rejects_unknown_section(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "package_capability_rules.toml",
        "\n".join(
            [
                "[[modules]]",
                'module = "ollama"',
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="unknown rule catalog"):
        RuleCatalogLoader().load_package_capability_rules(catalog_path)


def test_default_package_capability_catalog_keeps_exclusions_out() -> None:
    # The division-of-labor contract: openai stays with the endpoint
    # disambiguation ladder, chromadb with the client-variant regexes,
    # and general-purpose packages are never mapped. Frameworks are
    # mapped at the submodule level only: a bare "llama_index" entry
    # (or a vendor-less "llama_index.llms" / "llama_index.embeddings"
    # prefix) would fabricate meaning and must never appear.
    rules = RuleCatalogLoader().load_default_package_capability_rules()
    modules = {rule.module for rule in rules}

    assert {"ollama", "qdrant_client", "PyPDF2", "pypdf", "bs4"} <= modules
    assert {
        "llama_index.core.agent",
        "llama_index.core.workflow",
        "llama_index.core.memory",
        "llama_index.core.tools",
        "llama_index.core.chat_engine",
        "llama_index.core.node_parser",
        "llama_index.core.postprocessor.SentenceTransformerRerank",
        "llama_index.core.postprocessor.LLMRerank",
        "llama_index.postprocessor.cohere_rerank",
        "llama_index.core.readers",
        "llama_index.readers",
        "llama_index.vector_stores.qdrant",
        "llama_index.embeddings.openai",
        "llama_index.llms.openai",
        "llama_index.llms.ollama",
        "llama_index.embeddings.ollama",
    } <= modules
    assert (
        modules
        & {
            "openai",
            "chromadb",
            "torch",
            "numpy",
            "requests",
            "llama_index",
            "llama_index.core",
            "llama_index.llms",
            "llama_index.embeddings",
            "llama_index.vector_stores",
            # 16 exports, 3 rerankers: the bare namespace claims nothing.
            "llama_index.core.postprocessor",
            # Ambiguous by construction -- see the catalog EXCLUSIONS.
            "tiktoken",
            "spacy",
            "networkx",
            "httpx",
            "aiohttp",
        }
        == set()
    )
