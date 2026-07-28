"""Shared secret-boundary checks for ai-system-map validators."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from systograph.core.services.secret_masking_service import (
    SecretMaskingService,
)
from systograph.core.services.secret_validation_service import (
    SecretValidationService,
)

STRUCTURAL_SECRET_SCAN_KEYS = frozenset(
    {
        "activation",
        "artifact_type",
        "canonical_type",
        "component_id",
        "component_instance_id",
        "edge_id",
        "endpoint_id",
        "evidence_id",
        "evidence_kind",
        "flow_id",
        "from_slot",
        "id",
        "layer",
        "method",
        "relationship",
        "risk_id",
        "rule_id",
        "schema_version",
        "slot",
        "source",
        "status",
        "system_type",
        "target",
        "target_type",
        "to_slot",
        "type",
        "unmapped_id",
    }
)
SECRET_CONTEXT_METADATA_KEYS = frozenset(
    {
        "description",
        "fingerprint",
        "is_present",
        "key",
        "last4",
        "masked",
        "present",
        "provider",
        "redacted",
        "source",
    }
)


class SystemMapSecretBoundary:
    """Reject unmasked secret-like values in map payloads."""

    def __init__(
        self,
        *,
        secret_masking_service: SecretMaskingService | None = None,
        secret_validation_service: SecretValidationService | None = None,
        on_violation: Callable[[str], Exception],
    ) -> None:
        self._secret_masking_service = (
            secret_masking_service or SecretMaskingService()
        )
        self._secret_validation_service = (
            secret_validation_service or SecretValidationService()
        )
        self._on_violation = on_violation

    def reject_unmasked_secrets(
        self,
        value: Any,
        path: str = "$",
        key_context: str | None = None,
    ) -> None:
        if isinstance(value, str):
            if (
                self._secret_validation_service.contains_unmasked_url_credentials(
                    value
                )
                or self._contains_unmasked_secret(value, key=key_context)
            ):
                raise self._on_violation(
                    f"Unmasked secret-like value is not allowed at {path}"
                )
            return

        if isinstance(value, Mapping):
            sibling_key = value.get("key")
            for key, child in value.items():
                self.reject_unmasked_secrets(
                    child,
                    f"{path}.{key}",
                    key_context=self._child_key_context(
                        inherited_key_context=key_context,
                        key=key,
                        sibling_key=sibling_key,
                    ),
                )
            return

        if isinstance(value, list):
            for index, child in enumerate(value):
                self.reject_unmasked_secrets(
                    child,
                    f"{path}[{index}]",
                    key_context=key_context,
                )

    def _contains_unmasked_secret(
        self,
        value: str,
        *,
        key: str | None,
    ) -> bool:
        return self._secret_masking_service.contains_unmasked_secret(
            value,
            key=key,
            scan_key_value_pairs=key not in STRUCTURAL_SECRET_SCAN_KEYS,
        )

    def _child_key_context(
        self,
        *,
        inherited_key_context: str | None,
        key: Any,
        sibling_key: Any,
    ) -> str:
        candidate = str(key)
        if key == "value" and isinstance(sibling_key, str):
            candidate = sibling_key

        if self._secret_masking_service.is_secret_key_name(candidate):
            return candidate

        if (
            self._secret_masking_service.is_secret_key_name(
                inherited_key_context
            )
            and candidate not in SECRET_CONTEXT_METADATA_KEYS
            and candidate not in STRUCTURAL_SECRET_SCAN_KEYS
        ):
            return str(inherited_key_context)

        return candidate
