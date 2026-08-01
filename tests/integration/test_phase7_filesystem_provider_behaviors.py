from __future__ import annotations

from pathlib import Path

from tests.helpers.fixtures import rag_project_fixture_path

from systograph.core.providers.filesystem_provider import FilesystemProvider


def test_rag_fixture_inventory_exposes_safe_project_relative_files() -> None:
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")

    inventory = FilesystemProvider().build_inventory(project_root)

    file_paths = {record.path for record in inventory.files}
    assert {
        ".env.example",
        "README.md",
        "docker-compose.yml",
        "requirements.txt",
        "src/app.py",
        "src/ingest.py",
        "src/retriever.py",
    }.issubset(file_paths)
    assert all(not Path(path).is_absolute() for path in file_paths)
    assert all("\\" not in path for path in file_paths)
    assert all("node_modules" not in path for path in file_paths)
    assert all(".venv" not in path for path in file_paths)
