from __future__ import annotations

import base64
import hashlib
import json

from systograph.core.models.errors import (
    InventorySelectionError,
    InventorySelectionErrorCode,
)
from systograph.core.models.inventory_selection import (
    InventoryCandidateOutcome,
    InventoryCandidatePage,
    InventoryPreflightState,
)


class InventoryPreflightCursorService:
    def page(
        self,
        state: InventoryPreflightState,
        *,
        cursor: str | None,
        limit: int,
    ) -> InventoryCandidatePage:
        if not 1 <= limit <= 200:
            self._raise_invalid()
        candidates = tuple(
            item
            for item in state.candidate_set.candidates
            if item.base_outcome == InventoryCandidateOutcome.SOFT_EXCLUDED
        )
        offset = self._decode(state, cursor) if cursor else 0
        if offset > len(candidates):
            self._raise_invalid()
        items = candidates[offset : offset + limit]
        next_offset = offset + len(items)
        return InventoryCandidatePage(
            items=items,
            next_cursor=(
                self._encode(state, next_offset)
                if next_offset < len(candidates)
                else None
            ),
            total=len(candidates),
        )

    def _binding(self, state: InventoryPreflightState, offset: int) -> str:
        value = ":".join(
            (
                state.project_id,
                state.candidate_set.candidate_set_digest,
                state.candidate_set.inventory_policy_digest,
                str(offset),
            )
        )
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _encode(self, state: InventoryPreflightState, offset: int) -> str:
        payload = json.dumps(
            {"offset": offset, "binding": self._binding(state, offset)},
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")

    def _decode(self, state: InventoryPreflightState, cursor: str) -> int:
        try:
            padded = cursor + "=" * (-len(cursor) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded))
            offset = int(payload["offset"])
            binding = str(payload["binding"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise InventorySelectionError(
                InventorySelectionErrorCode.CURSOR_INVALID
            ) from exc
        if offset < 0 or binding != self._binding(state, offset):
            self._raise_invalid()
        return offset

    def _raise_invalid(self) -> None:
        raise InventorySelectionError(
            InventorySelectionErrorCode.CURSOR_INVALID
        )
