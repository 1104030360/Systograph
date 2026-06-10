"""Path normalization and redaction helpers for scanner-safe output."""

from __future__ import annotations

import os
import re
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from typing import Final

WINDOWS_DRIVE_RE: Final = re.compile(r"^[A-Za-z]:")
WINDOWS_ABSOLUTE_PATH_RE: Final = re.compile(r"[A-Za-z]:[\\/][^\s\"'<>),]+")
WINDOWS_UNC_RE: Final = re.compile(r"^(?:\\\\|//)[^\\/]+[\\/][^\\/]+")
POSIX_LOCAL_PATH_RE: Final = re.compile(
    r"(?<![A-Za-z0-9_:])"
    r"(?P<path>/(?:Users|home|tmp|private/tmp|var|opt|Volumes)"
    r"/[^\s\"'<>),]+)"
)
WINDOWS_LOCAL_PATH_RE: Final = re.compile(
    r"(?P<path>[A-Za-z]:[\\/][^\s\"'<>),]+)"
)
DISPLAY_MARKERS: Final = (
    "src",
    "tests",
    "docs",
    "schemas",
    "frontend",
    "outputs",
)
LOCAL_PATH_PLACEHOLDER: Final = "<LOCAL_PATH>"


class PathSafetyError(ValueError):
    """Raised when a path cannot be represented safely in public output."""


def normalize_project_relative_path(
    path: str | os.PathLike[str],
    *,
    project_root: Path | None = None,
) -> str:
    """Return a project-relative POSIX path or raise PathSafetyError."""

    raw = os.fspath(path)
    if raw in {"", "."}:
        raise PathSafetyError("Path must not be empty")

    if project_root is not None:
        local_relative = _host_relative_path(raw, project_root)
        if local_relative is not None:
            return _parts_to_posix(local_relative.parts)

    pure_path = _pure_path_for(raw)
    _reject_absolute_or_anchored(raw, pure_path)
    return _parts_to_posix(pure_path.parts)


def is_project_relative_posix_path(value: str) -> bool:
    """Return whether value is safe for ai-system-map path fields."""

    if value in {"", "."}:
        return False
    if "\\" in value:
        return False
    if WINDOWS_DRIVE_RE.match(value) or WINDOWS_UNC_RE.match(value):
        return False

    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and bool(path.parts)
        and ".." not in path.parts
        and all(part not in {"", "."} for part in path.parts)
    )


def redact_local_paths(
    text: str,
    *,
    workspace_root: Path | None = None,
) -> str:
    """Redact local absolute paths while preserving useful file context."""

    redacted = text
    if workspace_root is not None:
        workspace = workspace_root.as_posix().rstrip("/")
        redacted = redacted.replace(workspace, LOCAL_PATH_PLACEHOLDER)

    redacted = POSIX_LOCAL_PATH_RE.sub(_redact_posix_match, redacted)
    redacted = WINDOWS_LOCAL_PATH_RE.sub(_redact_windows_match, redacted)
    return redacted


def contains_local_path(
    text: str,
    *,
    workspace_root: Path | None = None,
) -> bool:
    """Return whether text contains a local absolute path."""

    return redact_local_paths(text, workspace_root=workspace_root) != text


def _host_relative_path(raw: str, project_root: Path) -> Path | None:
    candidate = Path(raw)
    if not candidate.is_absolute():
        return None

    root = project_root.resolve()
    try:
        return candidate.relative_to(root)
    except ValueError:
        pass

    try:
        return candidate.resolve().relative_to(root)
    except (OSError, ValueError) as exc:
        raise PathSafetyError("Absolute path is outside project root") from exc


def _pure_path_for(raw: str) -> PurePath:
    if _looks_like_windows_path(raw):
        return PureWindowsPath(raw)
    return PurePosixPath(raw)


def _looks_like_windows_path(raw: str) -> bool:
    return "\\" in raw or WINDOWS_DRIVE_RE.match(raw) is not None


def _reject_absolute_or_anchored(raw: str, path: PurePath) -> None:
    if isinstance(path, PureWindowsPath):
        if path.drive or path.root or WINDOWS_UNC_RE.match(raw):
            raise PathSafetyError("Windows absolute or anchored path rejected")
        return

    if path.is_absolute() or WINDOWS_UNC_RE.match(raw):
        raise PathSafetyError("POSIX absolute path rejected")


def _parts_to_posix(parts: tuple[str, ...]) -> str:
    if not parts:
        raise PathSafetyError("Path must include at least one segment")
    if any(part in {"", ".", ".."} for part in parts):
        raise PathSafetyError("Path must stay inside project root")
    if any(":" in part for part in parts):
        raise PathSafetyError("Path segment is not cross-platform safe")
    return PurePosixPath(*parts).as_posix()


def _redact_posix_match(match: re.Match[str]) -> str:
    return _redacted_display_path(match.group("path"), windows=False)


def _redact_windows_match(match: re.Match[str]) -> str:
    return _redacted_display_path(match.group("path"), windows=True)


def _redacted_display_path(raw_path: str, *, windows: bool) -> str:
    if raw_path.startswith(LOCAL_PATH_PLACEHOLDER):
        return raw_path

    if windows:
        normalized = PureWindowsPath(raw_path).as_posix()
    else:
        normalized = PurePosixPath(raw_path).as_posix()

    parts = [part for part in normalized.split("/") if part]
    for marker in DISPLAY_MARKERS:
        if marker in parts:
            return f"{LOCAL_PATH_PLACEHOLDER}/" + "/".join(
                parts[parts.index(marker) :]
            )

    return (
        f"{LOCAL_PATH_PLACEHOLDER}/{parts[-1]}"
        if parts
        else (LOCAL_PATH_PLACEHOLDER)
    )
