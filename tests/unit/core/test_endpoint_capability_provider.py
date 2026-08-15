from __future__ import annotations

from pathlib import Path

from systograph.core.models.filesystem import (
    FileCategory,
    FileInventory,
    FileInventorySource,
    FileRecord,
)
from systograph.core.models.scan import ProviderScanResult
from systograph.core.providers.endpoint_capability_provider import (
    ENDPOINT_VENDOR_FACT_KIND,
    EndpointCapabilityProvider,
)


def collect(
    tmp_path: Path,
    files: dict[str, str],
) -> ProviderScanResult:
    records = []
    for name, text in files.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        records.append(
            FileRecord(
                path=name,
                size_bytes=len(text.encode()),
                language="python" if name.endswith(".py") else "yaml",
                file_category=FileCategory.CODE,
                size_lines=len(text.splitlines()),
            )
        )
    inventory = FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(tmp_path),
        files=records,
    )
    return EndpointCapabilityProvider().collect(inventory)


def rule_ids(result: ProviderScanResult) -> list[str]:
    return sorted(fact.rule_id or "" for fact in result.facts)


def test_raw_http_vendor_urls_become_endpoint_vendor_facts(
    tmp_path: Path,
) -> None:
    # Given: the Verba integration style -- no SDK, just a base URL.
    result = collect(
        tmp_path,
        {
            "app/generation.py": (
                'ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"\n'
                'OPENAI_URL = "https://api.openai.com/v1/chat/completions"\n'
            )
        },
    )

    # Then: each vendor host is one fact under the dedicated kind.
    assert rule_ids(result) == [
        "endpoint_vendor_anthropic_llm",
        "endpoint_vendor_openai_llm",
    ]
    assert {fact.kind for fact in result.facts} == {ENDPOINT_VENDOR_FACT_KIND}
    assert all(fact.file == "app/generation.py" for fact in result.facts)
    assert len(result.evidence) == len(result.facts)


def test_longest_path_prefix_selects_the_capability(tmp_path: Path) -> None:
    # Given: one host that serves two different capabilities.
    result = collect(
        tmp_path,
        {
            "app/embed.py": (
                'URL = "https://api.openai.com/v1/embeddings"\n'
                'RERANK = "https://api.cohere.com/v2/rerank"\n'
            )
        },
    )

    # Then: the path decides, not the host alone.
    assert rule_ids(result) == [
        "endpoint_vendor_cohere_rerank",
        "endpoint_vendor_openai_embedding",
    ]


def test_ollama_port_is_matched_behind_any_host(tmp_path: Path) -> None:
    # Given: docker-compose env and a python default, both Ollama.
    result = collect(
        tmp_path,
        {
            "docker-compose.yml": (
                "services:\n"
                "  verba:\n"
                "    environment:\n"
                "      - OLLAMA_URL=http://host.docker.internal:11434\n"
            ),
            "app/llm.py": (
                'OLLAMA_URL = os.getenv("OLLAMA_URL", '
                '"http://localhost:11434")\n'
            ),
        },
    )

    # Then: the distinctive port carries the runtime identity.
    assert rule_ids(result) == [
        "endpoint_vendor_ollama_runtime",
        "endpoint_vendor_ollama_runtime",
    ]


def test_unknown_and_self_hosted_hosts_produce_nothing(
    tmp_path: Path,
) -> None:
    # Given: a self-hosted OpenAI-compatible runtime, a generic local
    # port and an unrelated host.
    result = collect(
        tmp_path,
        {
            "app/config.py": (
                'BASE = "http://localhost:8080/v1"\n'
                'VLLM = "http://127.0.0.1:8000/v1/chat/completions"\n'
                'OTHER = "https://example.com/v1/chat/completions"\n'
                'INTERNAL = "https://api.openai.company.internal/v1"\n'
            )
        },
    )

    # Then: an unknown host is never attributed to a vendor.
    assert result.facts == []


def test_comment_and_documentation_urls_are_ignored(tmp_path: Path) -> None:
    # Given: a doc file and code comments referencing vendor docs.
    result = collect(
        tmp_path,
        {
            "README.md": "See https://api.openai.com/v1/chat/completions\n",
            "app/notes.py": (
                "# reference: https://api.anthropic.com/v1/messages\n"
                "// https://api.groq.com/openai/v1/chat/completions\n"
            ),
        },
    )

    # Then: a mention is not an integration.
    assert result.facts == []


def test_url_credentials_never_reach_evidence(tmp_path: Path) -> None:
    # Given: a URL carrying inline credentials.
    result = collect(
        tmp_path,
        {
            "app/client.py": (
                'URL = "https://user:synthetic-pass-42@api.openai.com/v1"\n'
            )
        },
    )

    # Then: the vendor is recorded, the credential is not.
    assert rule_ids(result) == ["endpoint_vendor_openai_llm"]
    serialized = str([item.model_dump() for item in result.evidence])
    assert "synthetic-pass-42" not in serialized
