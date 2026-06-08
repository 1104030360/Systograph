"""Load non-secret defaults for optional LLM proposal providers."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any


class LlmProposalConfigError(ValueError):
    """Raised when provider config cannot be safely loaded."""


@dataclass(frozen=True)
class NvidiaNimGenerationConfig:
    max_tokens: int
    temperature: float
    top_p: float
    stream: bool
    enable_thinking: bool


@dataclass(frozen=True)
class NvidiaNimProposalConfig:
    name: str
    endpoint: str
    model: str
    timeout_seconds: float
    generation: NvidiaNimGenerationConfig
    prompt_template: str


def load_nvidia_nim_proposal_config(
    *,
    path: Path | None = None,
    package: str = "kai_mind.core.configs",
    resource_name: str = "llm_proposal.toml",
) -> NvidiaNimProposalConfig:
    """Load bundled or explicit TOML defaults for NVIDIA NIM proposals."""

    try:
        raw = (
            path.read_bytes()
            if path is not None
            else files(package).joinpath(resource_name).read_bytes()
        )
        loaded = tomllib.loads(raw.decode("utf-8"))
    except (
        FileNotFoundError,
        ModuleNotFoundError,
        OSError,
        tomllib.TOMLDecodeError,
        UnicodeDecodeError,
    ) as exc:
        raise LlmProposalConfigError(
            f"LLM proposal config could not be loaded: {exc}"
        ) from exc

    mapping_proposal = _required_table(loaded, "mapping_proposal")
    provider = _required_table(mapping_proposal, "provider")
    generation = _required_table(provider, "generation")
    prompt = _required_table(mapping_proposal, "prompt")

    return NvidiaNimProposalConfig(
        name=_required_str(provider, "name"),
        endpoint=_required_str(provider, "endpoint"),
        model=_required_str(provider, "model"),
        timeout_seconds=_required_float(provider, "timeout_seconds"),
        generation=NvidiaNimGenerationConfig(
            max_tokens=_required_int(generation, "max_tokens"),
            temperature=_required_float(generation, "temperature"),
            top_p=_required_float(generation, "top_p"),
            stream=_required_bool(generation, "stream"),
            enable_thinking=_required_bool(generation, "enable_thinking"),
        ),
        prompt_template=_required_str(prompt, "template"),
    )


def _required_table(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise LlmProposalConfigError(f"LLM proposal config {key} missing")
    return value


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LlmProposalConfigError(f"LLM proposal config {key} must be text")
    return value


def _required_int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise LlmProposalConfigError(
            f"LLM proposal config {key} must be integer"
        )
    return value


def _required_float(data: dict[str, Any], key: str) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise LlmProposalConfigError(
            f"LLM proposal config {key} must be numeric"
        )
    return float(value)


def _required_bool(data: dict[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise LlmProposalConfigError(
            f"LLM proposal config {key} must be boolean"
        )
    return value
