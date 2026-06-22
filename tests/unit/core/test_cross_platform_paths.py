from __future__ import annotations

from pathlib import Path

import pytest

from kai_mind.core.services.path_safety_service import (
    PathSafetyError,
    is_project_relative_posix_path,
    normalize_project_relative_path,
    redact_local_paths,
)


def test_normalizes_windows_relative_path_on_posix_host() -> None:
    assert normalize_project_relative_path("src\\rag\\api.py") == (
        "src/rag/api.py"
    )


def test_normalizes_absolute_path_inside_project_root(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    source_file = project_root / "src" / "api.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("print('ok')\n", encoding="utf-8")

    assert (
        normalize_project_relative_path(
            source_file,
            project_root=project_root,
        )
        == "src/api.py"
    )


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../secrets.env",
        "/Users/alice/project/secrets.env",
        "C:\\Users\\alice\\project\\secrets.env",
        "\\\\server\\share\\project\\secrets.env",
    ],
)
def test_rejects_absolute_parent_or_unc_paths(unsafe_path: str) -> None:
    with pytest.raises(PathSafetyError):
        normalize_project_relative_path(unsafe_path)


@pytest.mark.parametrize(
    ("candidate", "expected"),
    [
        ("src/api.py", True),
        ("src\\api.py", False),
        ("../src/api.py", False),
        ("/tmp/project/src/api.py", False),
        ("C:/project/src/api.py", False),
        ("//server/share/src/api.py", False),
    ],
)
def test_project_relative_posix_validation(
    candidate: str,
    expected: bool,
) -> None:
    assert is_project_relative_posix_path(candidate) is expected


def test_redacts_local_paths_without_removing_file_names() -> None:
    text = (
        "Failed at /Users/linjunting/Local_AI_Health_Doctor/src/app.py "
        "and C:\\Users\\alice\\project\\src\\api.py"
    )

    redacted = redact_local_paths(
        text,
        workspace_root=Path("/Users/linjunting/Local_AI_Health_Doctor"),
    )

    assert "/Users/linjunting/Local_AI_Health_Doctor" not in redacted
    assert "C:\\Users\\alice" not in redacted
    assert "<LOCAL_PATH>/src/app.py" in redacted
    assert "<LOCAL_PATH>/src/api.py" in redacted


def test_path_redaction_does_not_treat_url_scheme_as_windows_drive() -> None:
    value = "postgresql://demo:[MASKED]@db.example:5432/app"

    assert redact_local_paths(value) == value


def test_redacts_windows_double_slash_drive_path() -> None:
    value = (
        "Failed at D://work/project/src/api.py while "
        "connecting to postgresql://demo:[MASKED]@db.example:5432/app"
    )

    redacted = redact_local_paths(value)

    assert "D://work/project" not in redacted
    assert "<LOCAL_PATH>/src/api.py" in redacted
    assert "postgresql://demo:[MASKED]@db.example:5432/app" in redacted
