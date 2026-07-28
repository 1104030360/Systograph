"""Shared fixtures for local API route tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kai_mind.web.app import LocalApiApp, create_app


@pytest.fixture
def local_api_app(tmp_path: Path) -> LocalApiApp:
    """A default app wired against an isolated temp state dir.

    tests/web 目前有 25 處各自寫 create_app(state_dir=tmp_path / "state")；
    這個 fixture 把那個樣板收斂成一處。需要注入自訂服務的測試
    請繼續直接呼叫 create_app()。
    """
    return create_app(state_dir=tmp_path / "state")


@pytest.fixture
def local_api_client(local_api_app: LocalApiApp) -> Iterator[TestClient]:
    """TestClient over the default app."""
    with TestClient(local_api_app) as client:
        yield client
