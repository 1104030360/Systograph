from __future__ import annotations

from pathlib import Path

from kai_mind.core.models.filesystem import (
    FileInventory,
    FileInventorySource,
    FileRecord,
)
from kai_mind.core.providers.code_pattern_provider import CodePatternProvider


def build_inventory(
    project_root: Path,
    *paths: str,
    size_overrides: dict[str, int] | None = None,
) -> FileInventory:
    overrides = size_overrides or {}
    return FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(project_root),
        files=[
            FileRecord(
                path=path,
                size_bytes=overrides.get(
                    path,
                    (project_root / path).stat().st_size,
                ),
            )
            for path in paths
        ],
    )


def test_collect_scans_source_files_from_inventory_only(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "app.py").write_text(
        "from qdrant_client import QdrantClient\n"
        "client = QdrantClient(url='http://localhost:6333')\n",
        encoding="utf-8",
    )
    (project_root / "not_in_inventory.py").write_text(
        "from langchain_openai import ChatOpenAI\nllm = ChatOpenAI()\n",
        encoding="utf-8",
    )
    (project_root / "notes.md").write_text(
        "QdrantClient(url='http://localhost:6333')\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "app.py", "notes.md")

    result = CodePatternProvider().collect(inventory)

    assert {fact.file for fact in result.facts} == {"app.py"}
    assert {fact.rule_id for fact in result.facts} == {
        "code_pattern_vector_store_qdrant"
    }
    assert not result.issues


def test_collect_emits_python_rag_pattern_facts_and_evidence(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "pipeline.py").write_text(
        "\n".join(
            [
                "from fastapi import FastAPI",
                "from langchain.prompts import PromptTemplate",
                "from langchain_openai import ChatOpenAI, OpenAIEmbeddings",
                "from langchain_chroma import Chroma",
                "",
                "app = FastAPI()",
                'template = PromptTemplate.from_template("Question: {q}")',
                "embeddings = OpenAIEmbeddings()",
                "store = Chroma(collection_name='docs')",
                "retriever = store.as_retriever()",
                "llm = ChatOpenAI(model='gpt-4o-mini')",
                "",
                '@app.post("/query")',
                "def query(payload: dict[str, str]) -> dict[str, str]:",
                "    return {'answer': llm.invoke(payload['question'])}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "pipeline.py")

    result = CodePatternProvider().collect(inventory)

    facts_by_rule = {fact.rule_id: fact for fact in result.facts}
    assert set(facts_by_rule) == {
        "code_pattern_embedding_openai",
        "code_pattern_vector_store_chroma",
        "code_pattern_retriever_as_retriever",
        "code_pattern_prompt_template",
        "code_pattern_llm_chat_openai",
        "code_pattern_route_fastapi",
    }
    assert facts_by_rule["code_pattern_embedding_openai"].kind == "embedding"
    assert facts_by_rule["code_pattern_route_fastapi"].kind == "route_endpoint"
    route_evidence = next(
        evidence
        for evidence in result.evidence
        if evidence.rule_id == "code_pattern_route_fastapi"
    )
    assert route_evidence.file == "pipeline.py"
    assert route_evidence.path == "line[13]"
    assert route_evidence.line_start == 13
    assert route_evidence.line_end == 13
    assert route_evidence.snippet == '@app.post("/query")'
    assert route_evidence.id.startswith(
        "evidence:code_pattern_route_fastapi:pipeline.py:"
    )
    assert not result.issues


def test_collect_emits_chromadb_client_mode_facts(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "vector.py").write_text(
        "\n".join(
            [
                "import chromadb",
                'remote = chromadb.HttpClient(host="localhost", port=8000)',
                'async_remote = chromadb.AsyncHttpClient(host="chroma")',
                'local = chromadb.PersistentClient(path="./chroma")',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "vector.py")

    result = CodePatternProvider().collect(inventory)

    facts_by_rule = {fact.rule_id: fact for fact in result.facts}
    assert (
        facts_by_rule["code_pattern_vector_store_chroma_http"].value
        == "chromadb.HttpClient("
    )
    assert (
        facts_by_rule["code_pattern_vector_store_chroma_async_http"].value
        == "chromadb.AsyncHttpClient("
    )
    assert (
        facts_by_rule["code_pattern_vector_store_chroma_persistent"].value
        == "chromadb.PersistentClient("
    )


def test_collect_emits_javascript_and_typescript_route_facts(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "server.ts").write_text(
        "import express from 'express';\n"
        "const app = express();\n"
        "app.post('/ask', async (req, res) => res.json({ ok: true }));\n",
        encoding="utf-8",
    )
    (project_root / "server.js").write_text(
        "const express = require('express');\n"
        "router.get('/health', (_req, res) => res.send('ok'));\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "server.ts", "server.js")

    result = CodePatternProvider().collect(inventory)

    facts_by_file = {fact.file: fact for fact in result.facts}
    assert facts_by_file["server.ts"].rule_id == "code_pattern_route_express"
    assert facts_by_file["server.ts"].kind == "route_endpoint"
    assert facts_by_file["server.ts"].value == "app.post('/ask'"
    assert facts_by_file["server.js"].rule_id == "code_pattern_route_express"
    assert facts_by_file["server.js"].value == "router.get('/health'"


def test_collect_uses_injected_code_pattern_rule_catalog(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    catalog_path = tmp_path / "code_pattern_rules.toml"
    catalog_path.write_text(
        "\n".join(
            [
                "[[patterns]]",
                'rule_id = "code_pattern_custom_retriever"',
                'kind = "retriever"',
                'languages = ["python"]',
                'extensions = [".py"]',
                'regex = "\\\\bCustomRetriever\\\\s*\\\\("',
                'snippet_group = ""',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "app.py").write_text(
        "client = QdrantClient(url='http://localhost:6333')\n"
        "retriever = CustomRetriever()\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "app.py")

    result = CodePatternProvider(
        rule_catalog_path=catalog_path,
    ).collect(inventory)

    assert {fact.rule_id for fact in result.facts} == {
        "code_pattern_custom_retriever"
    }
    assert result.facts[0].value == "CustomRetriever("


def test_collect_masks_secret_values_in_snippets(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "app.py").write_text(
        "\n".join(
            [
                "headers = {'Authorization': 'Bearer sk-neighbor-secret'}",
                "client = QdrantClient(url='http://localhost:6333')",
                "OPENAI_API_KEY='sk-direct-secret'",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "app.py")

    result = CodePatternProvider(context_lines=1).collect(inventory)

    evidence = result.evidence[0]
    assert evidence.snippet is not None
    assert "sk-neighbor-secret" not in evidence.snippet
    assert "sk-direct-secret" not in evidence.snippet
    assert "...cret" in evidence.snippet
    assert evidence.line_start == 1
    assert evidence.line_end == 3


def test_collect_limits_snippet_length(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "app.py").write_text(
        "prefix = '" + ("x" * 100) + "'\n"
        "client = QdrantClient(url='http://localhost:6333')\n"
        "suffix = '" + ("y" * 100) + "'\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "app.py")

    result = CodePatternProvider(
        context_lines=1,
        max_snippet_chars=80,
    ).collect(inventory)

    snippet = result.evidence[0].snippet
    assert snippet is not None
    assert len(snippet) <= 80
    assert "QdrantClient" in snippet


def test_collect_skips_large_source_file_without_reading_it(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "large.py").write_text(
        "client = QdrantClient(url='http://localhost:6333')\n",
        encoding="utf-8",
    )
    inventory = build_inventory(
        project_root,
        "large.py",
        size_overrides={"large.py": 10_000},
    )

    result = CodePatternProvider(max_file_size_bytes=10).collect(inventory)

    assert result.facts == []
    assert result.evidence[0].kind == "parse_error"
    assert result.issues[0].provider == "code_pattern"
    assert result.issues[0].scan_stage == "code_pattern_scan"
    assert result.issues[0].file == "large.py"
    assert result.issues[0].rule_id == "code_pattern_file_skipped"
    assert "large_file" in result.issues[0].message


def test_collect_reports_decode_error_without_crashing(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "broken.py").write_bytes(b"\xff\xfeQdrantClient(")
    inventory = build_inventory(project_root, "broken.py")

    result = CodePatternProvider().collect(inventory)

    assert result.facts == []
    assert result.evidence[0].kind == "parse_error"
    assert result.issues[0].scan_stage == "code_pattern_scan"
    assert result.issues[0].file == "broken.py"
    assert result.issues[0].rule_id == "code_pattern_read_error"


def test_collect_rejects_inventory_paths_outside_project_root(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "secret.py"
    outside_file.write_text(
        "client = QdrantClient(url='http://localhost:6333')\n",
        encoding="utf-8",
    )
    inventory = FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(project_root),
        files=[
            FileRecord(
                path=str(outside_file),
                size_bytes=outside_file.stat().st_size,
            ),
            FileRecord(
                path="../outside/secret.py",
                size_bytes=outside_file.stat().st_size,
            ),
        ],
    )

    result = CodePatternProvider().collect(inventory)

    assert result.facts == []
    assert {issue.file for issue in result.issues} == {
        str(outside_file),
        "../outside/secret.py",
    }
    assert all(
        issue.rule_id == "code_pattern_invalid_inventory_path"
        for issue in result.issues
    )
    assert all(
        issue.scan_stage == "code_pattern_scan" for issue in result.issues
    )


def test_collect_keeps_import_only_signal_as_provider_local_fact(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "imports.py").write_text(
        "from langchain_openai import ChatOpenAI\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "imports.py")

    result = CodePatternProvider().collect(inventory)

    assert len(result.facts) == 1
    assert result.facts[0].rule_id == "code_pattern_llm_chat_openai"
    assert result.facts[0].kind == "llm_call"
    assert not hasattr(result, "components")
