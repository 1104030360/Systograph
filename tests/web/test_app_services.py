"""Unit tests for the typed application service container."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from kai_mind.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from kai_mind.core.services.detail_scan_service import DetailScanService
from kai_mind.core.services.map_build_service import MapBuildService
from kai_mind.web.app_services import AppServices, build_app_services
from kai_mind.web.session_store import PersistentSessionStore


def test_build_app_services_wires_defaults(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"

    services = build_app_services(state_dir=state_dir)

    assert isinstance(services, AppServices)
    assert isinstance(services.state_repository, LocalJsonStateProvider)
    assert isinstance(services.map_build_service, MapBuildService)
    assert isinstance(services.session_store, PersistentSessionStore)
    assert services.state_dir == state_dir


def test_build_app_services_honours_injected_service(
    tmp_path: Path,
) -> None:
    injected = DetailScanService()

    services = build_app_services(
        state_dir=tmp_path / "state",
        detail_scan_service=injected,
    )

    assert services.detail_scan_service is injected


def test_build_app_services_resolves_every_field(tmp_path: Path) -> None:
    services = build_app_services(state_dir=tmp_path / "state")

    for field in dataclasses.fields(services):
        assert getattr(services, field.name) is not None


def test_app_services_is_immutable(tmp_path: Path) -> None:
    services = build_app_services(state_dir=tmp_path / "state")

    with pytest.raises(dataclasses.FrozenInstanceError):
        services.state_dir = Path("/somewhere/else")  # type: ignore[misc]
