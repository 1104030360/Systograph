"""Load per-project query trace configuration from pyproject.toml."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_RETRIEVED_CHUNKS_KEYS = (
    "retrieved_chunks",
    "chunks",
    "documents",
)


class QueryTraceConfigError(ValueError):
    """Raised when query trace configuration is malformed."""


@dataclass(frozen=True)
class QueryTraceConfig:
    retrieved_chunks_keys: tuple[str, ...] = DEFAULT_RETRIEVED_CHUNKS_KEYS


class QueryTraceConfigLoader:
    """Load optional query trace settings from a scanned project root."""

    def load_project_config(
        self,
        project_root: Path | str,
    ) -> QueryTraceConfig:
        pyproject_path = Path(project_root) / "pyproject.toml"
        if not pyproject_path.exists():
            return QueryTraceConfig()

        try:
            with pyproject_path.open("rb") as file:
                loaded = tomllib.load(file)
        except tomllib.TOMLDecodeError as exc:
            raise QueryTraceConfigError(
                f"Failed to parse pyproject.toml: {exc}"
            ) from exc
        except OSError as exc:
            raise QueryTraceConfigError(
                f"Failed to read pyproject.toml: {exc}"
            ) from exc

        if not isinstance(loaded, Mapping):
            raise QueryTraceConfigError("pyproject.toml root must be a table")

        trace_config = self._trace_tool_section(loaded)
        if trace_config is None:
            return QueryTraceConfig()

        raw_keys = trace_config.get("retrieved_chunks_keys")
        if raw_keys is None:
            return QueryTraceConfig()

        return QueryTraceConfig(
            retrieved_chunks_keys=self._string_tuple(
                raw_keys,
                field="retrieved_chunks_keys",
            )
        )

    def _trace_tool_section(
        self,
        loaded: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        tool = loaded.get("tool")
        if not isinstance(tool, Mapping):
            return None

        kai_mind = tool.get("kai-mind")
        if not isinstance(kai_mind, Mapping):
            return None

        trace = kai_mind.get("trace")
        if trace is None:
            return None
        if not isinstance(trace, Mapping):
            raise QueryTraceConfigError("tool.kai-mind.trace must be a table")
        return trace

    def _string_tuple(self, value: Any, *, field: str) -> tuple[str, ...]:
        if (
            not isinstance(value, Sequence)
            or isinstance(value, str)
            or not value
        ):
            raise QueryTraceConfigError(f"{field} must be a string list")

        values: list[str] = []
        seen: set[str] = set()
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                raise QueryTraceConfigError(
                    f"{field}[{index}] must be a non-empty string"
                )
            key = item.strip()
            if key in seen:
                raise QueryTraceConfigError(f"duplicate {field}: {key}")
            seen.add(key)
            values.append(key)
        return tuple(values)
