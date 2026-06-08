"""Load small YAML prompt templates for optional LLM providers."""

from __future__ import annotations

import string
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


class PromptTemplateError(ValueError):
    """Raised when a prompt template cannot be safely rendered."""


@dataclass(frozen=True)
class PromptMessageTemplate:
    role: str
    content: str


@dataclass(frozen=True)
class PromptTemplate:
    version: str
    required_variables: tuple[str, ...]
    messages: tuple[PromptMessageTemplate, ...]

    def render_messages(
        self,
        variables: Mapping[str, str],
    ) -> list[dict[str, str]]:
        missing = [
            name for name in self.required_variables if name not in variables
        ]
        if missing:
            raise PromptTemplateError(
                "Prompt template missing variables: " + ", ".join(missing)
            )

        rendered: list[dict[str, str]] = []
        for message in self.messages:
            try:
                content = message.content.format(**variables)
            except KeyError as exc:
                name = str(exc).strip("'")
                raise PromptTemplateError(
                    f"Prompt template references unknown variable: {name}"
                ) from exc
            rendered.append({"role": message.role, "content": content})
        return rendered


def load_yaml_prompt_template(
    *,
    path: Path | None = None,
    package: str = "kai_mind.core.prompts",
    resource_name: str = "mapping_proposal.v1.yaml",
) -> PromptTemplate:
    """Load and validate a compact YAML prompt template."""

    try:
        text = (
            path.read_text(encoding="utf-8")
            if path is not None
            else files(package)
            .joinpath(resource_name)
            .read_text(encoding="utf-8")
        )
    except (FileNotFoundError, ModuleNotFoundError, OSError) as exc:
        raise PromptTemplateError(
            f"Prompt template could not be read: {exc}"
        ) from exc

    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise PromptTemplateError("Prompt template YAML is invalid") from exc
    if not isinstance(loaded, dict):
        raise PromptTemplateError("Prompt template root must be an object")

    version = _required_str(loaded, "version")
    required_variables = tuple(
        _required_str_list(loaded, "required_variables")
    )
    messages = tuple(_parse_messages(loaded.get("messages")))
    _validate_placeholders(messages, set(required_variables))

    return PromptTemplate(
        version=version,
        required_variables=required_variables,
        messages=messages,
    )


def _required_str(data: dict[Any, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PromptTemplateError(f"Prompt template {key} must be text")
    return value


def _required_str_list(data: dict[Any, Any], key: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        raise PromptTemplateError(f"Prompt template {key} must be a list")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise PromptTemplateError(
                f"Prompt template {key} must only contain text"
            )
        items.append(item)
    return items


def _parse_messages(value: object) -> list[PromptMessageTemplate]:
    if not isinstance(value, list) or not value:
        raise PromptTemplateError("Prompt template messages must be a list")

    messages: list[PromptMessageTemplate] = []
    for raw_message in value:
        if not isinstance(raw_message, dict):
            raise PromptTemplateError(
                "Prompt template message must be an object"
            )
        role = raw_message.get("role")
        content = raw_message.get("content")
        if not isinstance(role, str) or not role.strip():
            raise PromptTemplateError("Prompt template message role missing")
        if not isinstance(content, str) or not content.strip():
            raise PromptTemplateError(
                "Prompt template message content missing"
            )
        messages.append(
            PromptMessageTemplate(role=role.strip(), content=content)
        )
    return messages


def _validate_placeholders(
    messages: tuple[PromptMessageTemplate, ...],
    allowed_variables: set[str],
) -> None:
    formatter = string.Formatter()
    for message in messages:
        for _, field_name, _, _ in formatter.parse(message.content):
            if field_name is None:
                continue
            if field_name not in allowed_variables:
                raise PromptTemplateError(
                    "Prompt template references unknown variable: "
                    + field_name
                )
