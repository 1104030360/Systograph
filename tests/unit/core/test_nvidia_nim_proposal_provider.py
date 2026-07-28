from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from pytest import MonkeyPatch

from systograph.core.models.mapping import MappingEvidencePacket
from systograph.core.providers.llm_proposal_provider import (
    NvidiaNimProposalProvider,
    nvidia_nim_provider_from_env,
)
from systograph.core.services.llm_proposal_config_loader import (
    LlmProposalConfigError,
)
from systograph.core.services.mapping_proposal_service import (
    MappingProposalProviderUnavailableError,
)


def packet() -> MappingEvidencePacket:
    return MappingEvidencePacket(
        project_id="project:demo",
        source_unmapped_id="unmapped:src_router_py:route",
        source_file="src/router.py",
        observed_kind="code_pattern",
        reason="Router-like code needs confirmation.",
        evidence_ids=["evidence:router"],
        rule_ids=["code_pattern_custom_router"],
        masked_evidence_values=["OPENAI_API_KEY=sk-l...7890 route_query"],
        masked_snippets=["OPENAI_API_KEY=sk-l...7890\nroute_query"],
        call_like_signals=["QueryRouter.route"],
        available_slots=["retriever"],
    )


def test_nvidia_provider_sends_masked_packet_and_schema_only() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {"candidates": []},
                            )
                        }
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = NvidiaNimProposalProvider(
        api_key="nvapi-test-token",
        http_client=client,
        model="google/gemma-4-31b-it",
    )

    raw = provider.generate(
        packet=packet(),
        output_schema={"type": "object"},
    )

    assert raw == '{"candidates": []}'
    assert len(requests) == 1
    request = requests[0]
    assert request.url == (
        "https://integrate.api.nvidia.com/v1/chat/completions"
    )
    assert request.headers["authorization"] == "Bearer nvapi-test-token"
    assert request.headers["accept"] == "application/json"
    body = json.loads(request.content)
    serialized_body = json.dumps(body)
    assert body["model"] == "google/gemma-4-31b-it"
    assert "messages" in body
    assert body["max_tokens"] == 16384
    assert body["temperature"] == 1.0
    assert body["top_p"] == 0.95
    assert body["stream"] is False
    assert body["chat_template_kwargs"] == {"enable_thinking": True}
    assert "sk-live-1234567890" not in serialized_body
    assert "/Users/linjunting/Systograph" not in serialized_body
    assert "read_file" not in serialized_body
    assert "shell" not in serialized_body


def test_nvidia_provider_renders_prompt_from_yaml_template(
    tmp_path: Path,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps({"candidates": []})}}
                ]
            },
        )

    template_path = tmp_path / "mapping_proposal.v1.yaml"
    template_path.write_text(
        """
version: mapping_proposal.test
required_variables:
  - masked_evidence_packet_json
  - output_schema_json
  - validation_error
messages:
  - role: user
    content: |
      CUSTOM TEMPLATE
      Packet: {masked_evidence_packet_json}
      Schema: {output_schema_json}
      Error: {validation_error}
""",
        encoding="utf-8",
    )
    provider = NvidiaNimProposalProvider(
        api_key="nvapi-test-token",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        prompt_template_path=template_path,
    )

    provider.generate(
        packet=packet(),
        output_schema={"type": "object"},
        validation_error="candidate references unknown evidence",
    )

    body = json.loads(requests[0].content)
    packet_json = json.dumps(packet().model_dump(mode="json"), sort_keys=True)
    assert body["messages"] == [
        {
            "role": "user",
            "content": (
                "CUSTOM TEMPLATE\n"
                f"Packet: {packet_json}\n"
                'Schema: {"type": "object"}\n'
                "Error: candidate references unknown evidence\n"
            ),
        }
    ]


def test_nvidia_provider_reports_unavailable_for_invalid_prompt_template(
    tmp_path: Path,
) -> None:
    template_path = tmp_path / "mapping_proposal.v1.yaml"
    template_path.write_text(
        """
version: mapping_proposal.test
required_variables:
  - missing_variable
messages:
  - role: user
    content: "This references {missing_variable}"
""",
        encoding="utf-8",
    )
    provider = NvidiaNimProposalProvider(
        api_key="nvapi-test-token",
        prompt_template_path=template_path,
    )

    with pytest.raises(
        MappingProposalProviderUnavailableError,
        match="Prompt template",
    ):
        provider.generate(
            packet=packet(),
            output_schema={"type": "object"},
        )


def test_nvidia_provider_raises_unavailable_for_http_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    provider = NvidiaNimProposalProvider(
        api_key="nvapi-test-token",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(MappingProposalProviderUnavailableError):
        provider.generate(
            packet=packet(),
            output_schema={"type": "object"},
        )


def test_nvidia_provider_can_be_created_from_dotenv(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "SYSTOGRAPH_ENABLE_NVIDIA_NIM_PROPOSALS=true",
                "NVIDIA_API_KEY=nvapi-from-dotenv",
                "NVIDIA_NIM_MODEL=google/gemma-4-31b-it",
            ]
        ),
        encoding="utf-8",
    )

    provider = nvidia_nim_provider_from_env(env_file=env_file)

    assert isinstance(provider, NvidiaNimProposalProvider)


def test_nvidia_provider_requires_explicit_enable_flag(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("SYSTOGRAPH_ENABLE_NVIDIA_NIM_PROPOSALS", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("NVIDIA_API_KEY=nvapi-from-dotenv\n", encoding="utf-8")

    provider = nvidia_nim_provider_from_env(env_file=env_file)

    assert provider is None


def test_nvidia_provider_uses_non_secret_defaults_from_toml(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps({"candidates": []})}}
                ]
            },
        )

    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    config_file = tmp_path / "llm_proposal.toml"
    config_file.write_text(
        """
[mapping_proposal.provider]
name = "nvidia-nim"
endpoint = "https://example.test/v1/chat/completions"
model = "google/test-model"
timeout_seconds = 12.5

[mapping_proposal.provider.generation]
max_tokens = 2048
temperature = 0.2
top_p = 0.8
stream = false
enable_thinking = false

[mapping_proposal.prompt]
template = "mapping_proposal.v1.yaml"
""",
        encoding="utf-8",
    )
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "SYSTOGRAPH_ENABLE_NVIDIA_NIM_PROPOSALS=true",
                "NVIDIA_API_KEY=nvapi-from-dotenv",
            ]
        ),
        encoding="utf-8",
    )

    provider = nvidia_nim_provider_from_env(
        env_file=env_file,
        config_file=config_file,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert provider is not None
    provider.generate(packet=packet(), output_schema={"type": "object"})

    assert str(requests[0].url) == "https://example.test/v1/chat/completions"
    body = json.loads(requests[0].content)
    assert body["model"] == "google/test-model"
    assert body["max_tokens"] == 2048
    assert body["temperature"] == 0.2
    assert body["top_p"] == 0.8
    assert body["stream"] is False
    assert body["chat_template_kwargs"] == {"enable_thinking": False}


def test_env_can_override_non_secret_toml_values(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps({"candidates": []})}}
                ]
            },
        )

    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-from-env")
    monkeypatch.setenv("SYSTOGRAPH_ENABLE_NVIDIA_NIM_PROPOSALS", "true")
    monkeypatch.setenv("NVIDIA_NIM_MODEL", "google/env-model")
    monkeypatch.setenv("NVIDIA_NIM_MAX_TOKENS", "512")
    config_file = tmp_path / "llm_proposal.toml"
    config_file.write_text(
        """
[mapping_proposal.provider]
name = "nvidia-nim"
endpoint = "https://example.test/v1/chat/completions"
model = "google/toml-model"
timeout_seconds = 12.5

[mapping_proposal.provider.generation]
max_tokens = 2048
temperature = 0.2
top_p = 0.8
stream = false
enable_thinking = false

[mapping_proposal.prompt]
template = "mapping_proposal.v1.yaml"
""",
        encoding="utf-8",
    )

    provider = nvidia_nim_provider_from_env(
        env_file=tmp_path / ".env",
        config_file=config_file,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert provider is not None
    provider.generate(packet=packet(), output_schema={"type": "object"})

    body = json.loads(requests[0].content)
    assert body["model"] == "google/env-model"
    assert body["max_tokens"] == 512


def test_env_overrides_outside_safe_ranges_are_rejected(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-from-env")
    monkeypatch.setenv("SYSTOGRAPH_ENABLE_NVIDIA_NIM_PROPOSALS", "true")
    monkeypatch.setenv("NVIDIA_NIM_MAX_TOKENS", "999999")
    config_file = tmp_path / "llm_proposal.toml"
    config_file.write_text(
        """
[mapping_proposal.provider]
name = "nvidia-nim"
endpoint = "https://example.test/v1/chat/completions"
model = "google/toml-model"
timeout_seconds = 12.5

[mapping_proposal.provider.generation]
max_tokens = 2048
temperature = 0.2
top_p = 0.8
stream = false
enable_thinking = false

[mapping_proposal.prompt]
template = "mapping_proposal.v1.yaml"
""",
        encoding="utf-8",
    )

    with pytest.raises(
        LlmProposalConfigError,
        match="NVIDIA_NIM_MAX_TOKENS",
    ):
        nvidia_nim_provider_from_env(
            env_file=tmp_path / ".env",
            config_file=config_file,
        )


def test_env_overrides_with_invalid_numeric_values_are_rejected(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-from-env")
    monkeypatch.setenv("SYSTOGRAPH_ENABLE_NVIDIA_NIM_PROPOSALS", "true")
    monkeypatch.setenv("NVIDIA_NIM_TOP_P", "not-a-number")
    config_file = tmp_path / "llm_proposal.toml"
    config_file.write_text(
        """
[mapping_proposal.provider]
name = "nvidia-nim"
endpoint = "https://example.test/v1/chat/completions"
model = "google/toml-model"
timeout_seconds = 12.5

[mapping_proposal.provider.generation]
max_tokens = 2048
temperature = 0.2
top_p = 0.8
stream = false
enable_thinking = false

[mapping_proposal.prompt]
template = "mapping_proposal.v1.yaml"
""",
        encoding="utf-8",
    )

    with pytest.raises(LlmProposalConfigError, match="NVIDIA_NIM_TOP_P"):
        nvidia_nim_provider_from_env(
            env_file=tmp_path / ".env",
            config_file=config_file,
        )


def test_env_overrides_with_invalid_boolean_values_are_rejected(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-from-env")
    monkeypatch.setenv("SYSTOGRAPH_ENABLE_NVIDIA_NIM_PROPOSALS", "true")
    monkeypatch.setenv("NVIDIA_NIM_ENABLE_THINKING", "maybe")
    config_file = tmp_path / "llm_proposal.toml"
    config_file.write_text(
        """
[mapping_proposal.provider]
name = "nvidia-nim"
endpoint = "https://example.test/v1/chat/completions"
model = "google/toml-model"
timeout_seconds = 12.5

[mapping_proposal.provider.generation]
max_tokens = 2048
temperature = 0.2
top_p = 0.8
stream = false
enable_thinking = false

[mapping_proposal.prompt]
template = "mapping_proposal.v1.yaml"
""",
        encoding="utf-8",
    )

    with pytest.raises(
        LlmProposalConfigError,
        match="NVIDIA_NIM_ENABLE_THINKING",
    ):
        nvidia_nim_provider_from_env(
            env_file=tmp_path / ".env",
            config_file=config_file,
        )


def test_direct_provider_overrides_outside_safe_ranges_are_rejected() -> None:
    with pytest.raises(LlmProposalConfigError, match="max_tokens"):
        NvidiaNimProposalProvider(
            api_key="nvapi-test",
            max_tokens=999999,
        )


def test_env_var_takes_precedence_over_dotenv(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps({"candidates": []})}}
                ]
            },
        )

    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-from-env")
    monkeypatch.setenv("SYSTOGRAPH_ENABLE_NVIDIA_NIM_PROPOSALS", "true")
    env_file = tmp_path / ".env"
    env_file.write_text("NVIDIA_API_KEY=nvapi-from-dotenv\n", encoding="utf-8")

    provider = nvidia_nim_provider_from_env(
        env_file=env_file,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert provider is not None
    provider.generate(packet=packet(), output_schema={"type": "object"})

    assert requests[0].headers["authorization"] == "Bearer nvapi-from-env"
