from __future__ import annotations

import pytest

from systograph.core.services.canonical_output_configuration import (
    CANONICAL_OUTPUT_ENV,
    CanonicalOutputConfigurationError,
    canonical_output_version_from_env,
    require_public_v2_selection,
)


def test_operator_output_defaults_to_v2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    monkeypatch.delenv(CANONICAL_OUTPUT_ENV, raising=False)

    # When
    version = canonical_output_version_from_env()

    # Then
    assert version == "ai-system-map/v2"


def test_operator_v1_output_version_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The removed rollback writer leaves no selectable v1 output.

    Given the operator env set to the legacy canonical output version,
    When the version is resolved,
    Then it fails with the same stable code as any other unsupported
    value, because v1 is no longer a mode this process can produce.
    """
    # Given
    monkeypatch.setenv(CANONICAL_OUTPUT_ENV, "ai-system-map/v1")

    # When
    raised = pytest.raises(
        CanonicalOutputConfigurationError,
        match="invalid_canonical_output_version",
    )

    # Then
    with raised:
        canonical_output_version_from_env()


def test_invalid_operator_output_version_fails_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    monkeypatch.setenv(CANONICAL_OUTPUT_ENV, "bogus")

    # When
    raised = pytest.raises(
        CanonicalOutputConfigurationError,
        match="invalid_canonical_output_version",
    )

    # Then
    with raised:
        canonical_output_version_from_env()


def test_public_v1_output_selection_is_rejected() -> None:
    with pytest.raises(
        CanonicalOutputConfigurationError,
        match="legacy_output_not_selectable",
    ):
        require_public_v2_selection("ai-system-map/v1")


def test_configuration_error_supports_runtime_traceback_assignment() -> None:
    error = CanonicalOutputConfigurationError("stable_error")
    try:
        raise error
    except CanonicalOutputConfigurationError as caught:
        caught.__traceback__ = None

    assert error.code == "stable_error"
