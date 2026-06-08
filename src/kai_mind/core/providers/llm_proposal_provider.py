"""LLM proposal provider adapters."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

from kai_mind.core.models.mapping import MappingEvidencePacket
from kai_mind.core.services.llm_proposal_config_loader import (
    LlmProposalConfigError,
    NvidiaNimProposalConfig,
    load_nvidia_nim_proposal_config,
)
from kai_mind.core.services.mapping_proposal_service import (
    MappingProposalProviderUnavailableError,
)
from kai_mind.core.services.prompt_template_loader import (
    PromptTemplateError,
    load_yaml_prompt_template,
)


class NvidiaNimProposalProvider:
    """Hosted NVIDIA NIM adapter for proposal candidate generation."""

    name = "nvidia-nim"

    def __init__(
        self,
        *,
        api_key: str,
        model: str | None = None,
        endpoint: str | None = None,
        timeout: float | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        stream: bool | None = None,
        enable_thinking: bool | None = None,
        http_client: httpx.Client | None = None,
        prompt_template_path: Path | None = None,
        prompt_template_resource_name: str | None = None,
        config: NvidiaNimProposalConfig | None = None,
    ) -> None:
        config = config or load_nvidia_nim_proposal_config()
        self._api_key = api_key
        self._model = model or config.model
        self._endpoint = endpoint or config.endpoint
        self._timeout = (
            timeout if timeout is not None else config.timeout_seconds
        )
        self._max_tokens = (
            max_tokens
            if max_tokens is not None
            else config.generation.max_tokens
        )
        self._temperature = (
            temperature
            if temperature is not None
            else config.generation.temperature
        )
        self._top_p = top_p if top_p is not None else config.generation.top_p
        self._stream = (
            stream if stream is not None else config.generation.stream
        )
        self._enable_thinking = (
            enable_thinking
            if enable_thinking is not None
            else config.generation.enable_thinking
        )
        self._http_client = http_client
        self._prompt_template_path = prompt_template_path
        self._prompt_template_resource_name = (
            prompt_template_resource_name or config.prompt_template
        )

    def generate(
        self,
        *,
        packet: MappingEvidencePacket,
        output_schema: dict[str, object],
        validation_error: str | None = None,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            payload = {
                "model": self._model,
                "messages": self._render_messages(
                    packet=packet,
                    output_schema=output_schema,
                    validation_error=validation_error,
                ),
                "max_tokens": self._max_tokens,
                "temperature": self._temperature,
                "top_p": self._top_p,
                "stream": self._stream,
                "chat_template_kwargs": {
                    "enable_thinking": self._enable_thinking,
                },
            }
            if self._http_client is not None:
                response = self._http_client.post(
                    self._endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self._timeout,
                )
            else:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.post(
                        self._endpoint,
                        json=payload,
                        headers=headers,
                    )
            response.raise_for_status()
            data = response.json()
        except (
            LlmProposalConfigError,
            PromptTemplateError,
            httpx.HTTPError,
            ValueError,
        ) as exc:
            raise MappingProposalProviderUnavailableError(str(exc)) from exc

        return _extract_message_content(data)

    def _render_messages(
        self,
        *,
        packet: MappingEvidencePacket,
        output_schema: dict[str, object],
        validation_error: str | None,
    ) -> list[dict[str, str]]:
        template = load_yaml_prompt_template(
            path=self._prompt_template_path,
            resource_name=self._prompt_template_resource_name,
        )
        variables = {
            "masked_evidence_packet_json": json.dumps(
                packet.model_dump(mode="json"),
                sort_keys=True,
            ),
            "output_schema_json": json.dumps(output_schema, sort_keys=True),
            "validation_error": validation_error or "None.",
        }
        return template.render_messages(variables)


def _extract_message_content(data: dict[str, Any]) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise MappingProposalProviderUnavailableError(
            "NVIDIA NIM response did not include message content"
        ) from exc
    if not isinstance(content, str) or not content.strip():
        raise MappingProposalProviderUnavailableError(
            "NVIDIA NIM response content is empty"
        )
    return content


def nvidia_nim_provider_from_env(
    *,
    env_file: Path | None = None,
    config_file: Path | None = None,
    environ: dict[str, str] | None = None,
    http_client: httpx.Client | None = None,
) -> NvidiaNimProposalProvider | None:
    """Create a NVIDIA NIM provider when NVIDIA_API_KEY is configured."""

    config = load_nvidia_nim_proposal_config(path=config_file)
    env = dict(_dotenv_values(env_file or Path(".env")))
    env.update(environ or os.environ)
    if not _bool_env(env, "KAI_MIND_ENABLE_NVIDIA_NIM_PROPOSALS", False):
        return None

    api_key = env.get("NVIDIA_API_KEY")
    if api_key is None or not api_key.strip():
        return None

    return NvidiaNimProposalProvider(
        api_key=api_key.strip(),
        config=config,
        model=env.get("NVIDIA_NIM_MODEL", config.model),
        endpoint=env.get("NVIDIA_NIM_ENDPOINT", config.endpoint),
        timeout=_float_env(
            env,
            "NVIDIA_NIM_TIMEOUT_SECONDS",
            config.timeout_seconds,
        ),
        max_tokens=_int_env(
            env,
            "NVIDIA_NIM_MAX_TOKENS",
            config.generation.max_tokens,
        ),
        temperature=_float_env(
            env,
            "NVIDIA_NIM_TEMPERATURE",
            config.generation.temperature,
        ),
        top_p=_float_env(env, "NVIDIA_NIM_TOP_P", config.generation.top_p),
        stream=_bool_env(env, "NVIDIA_NIM_STREAM", config.generation.stream),
        enable_thinking=_bool_env(
            env,
            "NVIDIA_NIM_ENABLE_THINKING",
            config.generation.enable_thinking,
        ),
        prompt_template_resource_name=env.get(
            "KAI_MIND_MAPPING_PROPOSAL_PROMPT_TEMPLATE",
            config.prompt_template,
        ),
        http_client=http_client,
    )


def _dotenv_values(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = _clean_env_value(raw_value.strip())
    return values


def _clean_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _int_env(env: dict[str, str], key: str, default: int) -> int:
    try:
        return int(env.get(key, str(default)))
    except ValueError:
        return default


def _float_env(env: dict[str, str], key: str, default: float) -> float:
    try:
        return float(env.get(key, str(default)))
    except ValueError:
        return default


def _bool_env(env: dict[str, str], key: str, default: bool) -> bool:
    raw = env.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
