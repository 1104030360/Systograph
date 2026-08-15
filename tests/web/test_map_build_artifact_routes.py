"""Behaviour of the build-scoped artifact download route.

`GET /api/map-builds/{build_id}/artifacts/{file_name}` is the only HTTP way
to read a build's rendered Markdown report. It answers from the `build_id`
the caller already holds, so reading an older build downloads *that* build's
report, and no response ever carries a server-local path.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tests.helpers.fixtures import rag_project_fixture_path
from tests.helpers.web_flows import scan_project

from systograph.web.app import create_app

MARKDOWN_ARTIFACT = "ai_system_map.md"


def artifact_url(build_id: str, file_name: str = MARKDOWN_ARTIFACT) -> str:
    return f"/api/map-builds/{build_id}/artifacts/{file_name}"


def copy_fixture_project(tmp_path: Path) -> Path:
    """Copy the sample RAG project so a test may mutate its own copy.

    The fixture tree under `tests/fixtures/` is shared and must stay
    untouched; a rescan needs a project it is allowed to change.
    """

    project_root = tmp_path / "project"
    shutil.copytree(
        rag_project_fixture_path("basic_qdrant_ollama_rag"),
        project_root,
    )
    return project_root


def add_second_vector_store(project_root: Path) -> None:
    """Give the project a second, differently-exposed vector store.

    A published Compose port only becomes an endpoint when a matching
    client dependency is declared too, so both files move together.
    """

    requirements = project_root / "requirements.txt"
    requirements.write_text(
        requirements.read_text(encoding="utf-8") + "chromadb==0.5.0\n",
        encoding="utf-8",
    )
    compose = project_root / "docker-compose.yml"
    compose.write_text(
        compose.read_text(encoding="utf-8").replace(
            "volumes:\n  qdrant_data:",
            "  chroma:\n"
            "    image: chromadb/chroma:0.5.0\n"
            "    ports:\n"
            '      - "8001:8000"\n'
            "\n"
            "volumes:\n"
            "  qdrant_data:",
        ),
        encoding="utf-8",
    )


def import_project(client: TestClient, project_root: Path) -> str:
    response = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(project_root),
        },
    )
    assert response.status_code == 200, response.text
    return str(response.json()["project_id"])


def scan_into_build(
    client: TestClient,
    project_id: str,
    tmp_path: Path,
) -> str:
    scan = scan_project(
        client,
        project_id,
        output=str(tmp_path / "outputs"),
    )
    return str(scan["build_result"]["lineage"]["build_id"])


def scan_fixture_project(client: TestClient, tmp_path: Path) -> str:
    """Import a private copy of the sample project and build it once."""

    project_id = import_project(client, copy_fixture_project(tmp_path))
    return scan_into_build(client, project_id, tmp_path)


def markdown_on_disk(tmp_path: Path, build_id: str) -> Path:
    """Point at `outputs/build_<id>/ai_system_map.md` for one build."""

    build_dir = tmp_path / "outputs" / build_id.replace(":", "_")
    return build_dir / MARKDOWN_ARTIFACT


def test_artifact_route_serves_each_build_its_own_markdown(
    tmp_path: Path,
) -> None:
    """Given one project built twice into different reports, when each
    build's artifact is downloaded, then each response is byte-identical
    to that build's own file on disk — the newer build never wins."""

    client = TestClient(create_app())
    project_root = copy_fixture_project(tmp_path)
    project_id = import_project(client, project_root)
    build_a = scan_into_build(client, project_id, tmp_path)
    add_second_vector_store(project_root)
    build_b = scan_into_build(client, project_id, tmp_path)

    response_a = client.get(artifact_url(build_a))
    response_b = client.get(artifact_url(build_b))

    assert build_a != build_b
    assert response_a.status_code == response_b.status_code == 200
    assert response_a.text != response_b.text
    assert f"- Build: `{build_a}`" in response_a.text
    assert build_b not in response_a.text
    assert f"- Build: `{build_b}`" in response_b.text
    assert build_a not in response_b.text
    assert (
        response_a.content == markdown_on_disk(tmp_path, build_a).read_bytes()
    )
    assert (
        response_b.content == markdown_on_disk(tmp_path, build_b).read_bytes()
    )
    assert "8001" in response_b.text
    assert "8001" not in response_a.text


def test_artifact_route_serves_markdown_inline_without_download_query(
    tmp_path: Path,
) -> None:
    """Given a committed build, when its report is read without the
    download flag, then the body is the Markdown report served for inline
    viewing, with no attachment header."""

    client = TestClient(create_app())
    build_id = scan_fixture_project(client, tmp_path)

    response = client.get(artifact_url(build_id))

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/markdown; charset=utf-8"
    assert "content-disposition" not in response.headers
    assert response.text.splitlines()[0] == "# Systograph System Map"


def test_artifact_route_serves_file_bytes_without_newline_translation(
    tmp_path: Path,
) -> None:
    """Given a report stored with CRLF line endings — what the build
    writes on Windows — when it is downloaded, then the response carries
    those bytes unchanged, so byte identity with the file holds on every
    platform rather than only where the separator is already LF."""

    client = TestClient(create_app())
    build_id = scan_fixture_project(client, tmp_path)
    markdown = markdown_on_disk(tmp_path, build_id)
    unix_bytes = markdown.read_bytes().replace(b"\r\n", b"\n")
    markdown.write_bytes(unix_bytes.replace(b"\n", b"\r\n"))

    response = client.get(artifact_url(build_id))

    assert response.status_code == 200
    assert response.content == markdown.read_bytes()
    assert b"\r\n" in response.content


def test_artifact_route_marks_download_query_as_attachment(
    tmp_path: Path,
) -> None:
    """Given a committed build, when the report is requested with
    `download=true`, then the response is an attachment named from the
    whitelist rather than from anything the caller sent."""

    client = TestClient(create_app())
    build_id = scan_fixture_project(client, tmp_path)

    response = client.get(f"{artifact_url(build_id)}?download=true")

    assert response.status_code == 200
    assert response.headers["content-disposition"] == (
        'attachment; filename="ai_system_map.md"'
    )
    assert response.text.splitlines()[0] == "# Systograph System Map"


def test_artifact_route_returns_build_not_found_for_unknown_build(
    tmp_path: Path,
) -> None:
    """Given a whitelisted file name under a build id nobody committed,
    when it is requested, then the API answers `build_not_found`."""

    client = TestClient(create_app())
    scan_fixture_project(client, tmp_path)

    response = client.get(artifact_url("build:missing"))

    assert response.status_code == 404
    assert response.json()["detail"] == "build_not_found"


@pytest.mark.parametrize(
    "file_name",
    [
        "secret.txt",
        ".env",
        "ai_system_map.json",
        "..%5Cai_system_map.md",
    ],
)
def test_artifact_route_returns_artifact_not_found_outside_whitelist(
    tmp_path: Path,
    file_name: str,
) -> None:
    """Given a file name the whitelist does not carry — including a
    traversal-shaped one — when it is requested for a real build, then the
    handler answers `artifact_not_found` without touching the filesystem."""

    client = TestClient(create_app())
    build_id = scan_fixture_project(client, tmp_path)

    response = client.get(artifact_url(build_id, file_name))

    assert response.status_code == 404
    assert response.json()["detail"] == "artifact_not_found"


def test_artifact_route_screens_the_file_name_before_the_build_id(
    tmp_path: Path,
) -> None:
    """Given both an unknown build id and a name outside the whitelist,
    when they arrive together, then the fixed check order reports the name
    first, so an unknown name never probes build storage."""

    client = TestClient(create_app())
    scan_fixture_project(client, tmp_path)

    response = client.get(artifact_url("build:missing", "secret.txt"))

    assert response.status_code == 404
    assert response.json()["detail"] == "artifact_not_found"


def test_slash_encoded_traversal_never_reaches_the_artifact_handler(
    tmp_path: Path,
) -> None:
    """Given a name whose encoded separator would escape the artifacts
    segment, when it is requested, then routing rejects it before the
    handler runs and no report content comes back."""

    client = TestClient(create_app())
    build_id = scan_fixture_project(client, tmp_path)

    response = client.get(artifact_url(build_id, "..%2Fai_system_map.md"))

    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"
    assert "# Systograph System Map" not in response.text


def test_artifact_route_reports_not_available_when_markdown_left_disk(
    tmp_path: Path,
) -> None:
    """Given a committed build whose report was deleted from disk, when it
    is downloaded, then the API answers `artifact_not_available` instead of
    falling back to some other build's file."""

    client = TestClient(create_app())
    build_id = scan_fixture_project(client, tmp_path)
    markdown_on_disk(tmp_path, build_id).unlink()

    response = client.get(artifact_url(build_id))

    assert response.status_code == 404
    assert response.json()["detail"] == "artifact_not_available"


def test_artifact_route_responses_never_expose_server_local_paths(
    tmp_path: Path,
) -> None:
    """Given every answer the route can give, when their bodies and
    headers are inspected, then none of them carries a server-local
    absolute path for the caller to aim a later request at."""

    client = TestClient(create_app())
    build_id = scan_fixture_project(client, tmp_path)
    outputs_dir = str(markdown_on_disk(tmp_path, build_id).parent)

    served = client.get(f"{artifact_url(build_id)}?download=true")
    unknown_name = client.get(artifact_url(build_id, "secret.txt"))
    unknown_build = client.get(artifact_url("build:missing"))
    markdown_on_disk(tmp_path, build_id).unlink()
    unavailable = client.get(artifact_url(build_id))

    assert served.status_code == 200
    assert unknown_name.status_code == 404
    assert unknown_build.status_code == 404
    assert unavailable.status_code == 404
    for response in (served, unknown_name, unknown_build, unavailable):
        exposed = response.text + "".join(
            f"{name}: {value}" for name, value in response.headers.items()
        )
        assert str(tmp_path) not in exposed
        assert outputs_dir not in exposed
