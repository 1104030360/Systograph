from __future__ import annotations

import hashlib
import json
from typing import Any, Final

from systograph.core.models.filesystem import (
    FileInventory,
    FileInventorySource,
    SkipReason,
)
from systograph.core.models.inventory_policy import (
    InventoryPolicyAction,
    ScanInventoryPolicyCatalog,
)
from systograph.core.models.inventory_provenance import (
    InventoryPolicyAuditEntry,
    InventoryPolicyAuditOutcome,
    InventoryPolicyAuditScope,
    InventoryPolicyAuditSource,
    InventoryPolicyDecisionOrigin,
)
from systograph.core.services.inventory_policy_matcher import (
    InventoryPolicyMatcher,
)

FILESYSTEM_SAFETY_VERSION: Final = "inventory-safety/v1"


class InventoryProvenanceService:
    def finalize(
        self,
        inventory: FileInventory,
        *,
        catalog: ScanInventoryPolicyCatalog,
        matcher: InventoryPolicyMatcher,
    ) -> FileInventory:
        audit = self._build_audit(inventory, matcher=matcher)
        candidate_set_digest = self._digest(
            [
                {
                    "path": entry.path,
                    "size_bytes": self._size_for_path(
                        inventory,
                        entry.path,
                    ),
                }
                for entry in audit
            ]
        )
        boundary_decision_digest = self._digest([])
        final_inventory_digest = self._digest(
            [entry.model_dump(mode="json") for entry in audit]
        )
        inventory_run_digest = self._digest(
            {
                "inventory_source_mode": inventory.source.value,
                "candidate_set_digest": candidate_set_digest,
                "inventory_policy_digest": catalog.catalog_digest,
                "filesystem_safety_version": FILESYSTEM_SAFETY_VERSION,
                "boundary_decision_digest": boundary_decision_digest,
                "final_inventory_digest": final_inventory_digest,
            }
        )
        return inventory.model_copy(
            update={
                "inventory_policy_schema_version": catalog.schema_version,
                "inventory_policy_digest": catalog.catalog_digest,
                "candidate_set_digest": candidate_set_digest,
                "filesystem_safety_version": FILESYSTEM_SAFETY_VERSION,
                "boundary_decision_digest": boundary_decision_digest,
                "final_inventory_digest": final_inventory_digest,
                "inventory_run_digest": inventory_run_digest,
                "inventory_policy_audit": audit,
            }
        )

    def finalize_boundary(
        self,
        inventory: FileInventory,
        *,
        audit: list[InventoryPolicyAuditEntry],
    ) -> FileInventory:
        ordered_audit = sorted(
            audit,
            key=lambda entry: (
                entry.path,
                entry.reason,
                entry.outcome.value,
            ),
        )
        update: dict[str, object] = {
            "inventory_policy_audit": ordered_audit,
        }
        if not all(
            (
                inventory.candidate_set_digest,
                inventory.inventory_policy_digest,
                inventory.filesystem_safety_version,
            )
        ):
            return inventory.model_copy(update=update)

        boundary_decision_digest = self._digest(
            [
                {
                    "path": entry.path,
                    "outcome": entry.outcome.value,
                    "decision": entry.boundary_decision,
                    "decision_target_path": entry.decision_target_path,
                    "decision_scope": entry.decision_scope,
                    "decision_fingerprint": entry.decision_fingerprint
                    or entry.target_fingerprint,
                }
                for entry in ordered_audit
                if entry.source == InventoryPolicyAuditSource.RUNTIME_BOUNDARY
                or entry.decision_origin
                == InventoryPolicyDecisionOrigin.RUNTIME_USER_DECISION
            ]
        )
        final_inventory_digest = self._digest(
            [entry.model_dump(mode="json") for entry in ordered_audit]
        )
        inventory_run_digest = self._digest(
            {
                "inventory_source_mode": inventory.source.value,
                "candidate_set_digest": inventory.candidate_set_digest,
                "inventory_policy_digest": inventory.inventory_policy_digest,
                "filesystem_safety_version": (
                    inventory.filesystem_safety_version
                ),
                "boundary_decision_digest": boundary_decision_digest,
                "final_inventory_digest": final_inventory_digest,
            }
        )
        update.update(
            {
                "boundary_decision_digest": boundary_decision_digest,
                "final_inventory_digest": final_inventory_digest,
                "inventory_run_digest": inventory_run_digest,
            }
        )
        return inventory.model_copy(update=update)

    def runtime_boundary_entry(
        self,
        *,
        existing: InventoryPolicyAuditEntry | None,
        path: str,
        source_mode: FileInventorySource,
        outcome: InventoryPolicyAuditOutcome,
        reason: str,
        boundary_decision: str | None,
        target_fingerprint: str,
    ) -> InventoryPolicyAuditEntry:
        return InventoryPolicyAuditEntry(
            path=path,
            outcome=outcome,
            source=InventoryPolicyAuditSource.RUNTIME_BOUNDARY,
            source_mode=source_mode.value,
            audit_scope=InventoryPolicyAuditScope.PATH,
            reason=reason,
            matched_inventory_policy_ids=(
                list(existing.matched_inventory_policy_ids)
                if existing is not None
                else []
            ),
            effective_inventory_policy_id=(
                existing.effective_inventory_policy_id
                if existing is not None
                else None
            ),
            matched_pattern=(
                existing.matched_pattern if existing is not None else None
            ),
            boundary_decision=boundary_decision,
            target_fingerprint=target_fingerprint,
        )

    def _build_audit(
        self,
        inventory: FileInventory,
        *,
        matcher: InventoryPolicyMatcher,
    ) -> list[InventoryPolicyAuditEntry]:
        entries = [
            self._included_entry(
                record.path,
                inventory=inventory,
                matcher=matcher,
            )
            for record in inventory.files
        ]
        entries.extend(
            self._skipped_entry(
                record.path,
                reason=record.reason,
                inventory=inventory,
                matcher=matcher,
            )
            for record in inventory.skipped
        )
        return sorted(entries, key=lambda entry: (entry.path, entry.reason))

    def _included_entry(
        self,
        path: str,
        *,
        inventory: FileInventory,
        matcher: InventoryPolicyMatcher,
    ) -> InventoryPolicyAuditEntry:
        match = matcher.match(path)
        reason = (
            match.effective_reason
            if match.effective_action == InventoryPolicyAction.INCLUDE
            else "included_by_default"
        )
        return self._entry(
            path,
            outcome=InventoryPolicyAuditOutcome.INCLUDED,
            source=InventoryPolicyAuditSource.SYSTOGRAPH_INVENTORY_CATALOG,
            reason=reason or "included_by_default",
            inventory=inventory,
            matcher=matcher,
        )

    def _skipped_entry(
        self,
        path: str,
        *,
        reason: SkipReason,
        inventory: FileInventory,
        matcher: InventoryPolicyMatcher,
    ) -> InventoryPolicyAuditEntry:
        match = matcher.match(path, is_directory=path.endswith("/"))
        if reason == SkipReason.GITIGNORED:
            source = InventoryPolicyAuditSource.PROJECT_IGNORE
        elif match.effective_action == InventoryPolicyAction.EXCLUDE:
            source = InventoryPolicyAuditSource.SYSTOGRAPH_INVENTORY_CATALOG
        else:
            source = InventoryPolicyAuditSource.FILESYSTEM_SAFETY
        return self._entry(
            path,
            outcome=InventoryPolicyAuditOutcome.SKIPPED,
            source=source,
            reason=reason.value,
            inventory=inventory,
            matcher=matcher,
        )

    def _entry(
        self,
        path: str,
        *,
        outcome: InventoryPolicyAuditOutcome,
        source: InventoryPolicyAuditSource,
        reason: str,
        inventory: FileInventory,
        matcher: InventoryPolicyMatcher,
    ) -> InventoryPolicyAuditEntry:
        is_directory = path.endswith("/")
        match = matcher.match(path, is_directory=is_directory)
        return InventoryPolicyAuditEntry(
            path=path,
            outcome=outcome,
            source=source,
            source_mode=inventory.source.value,
            audit_scope=(
                InventoryPolicyAuditScope.DIRECTORY_SUMMARY
                if is_directory
                else InventoryPolicyAuditScope.PATH
            ),
            reason=reason,
            matched_inventory_policy_ids=list(
                match.matched_inventory_policy_ids
            ),
            effective_inventory_policy_id=(
                match.effective_inventory_policy_id
            ),
            matched_pattern=match.effective_pattern,
        )

    def _size_for_path(
        self,
        inventory: FileInventory,
        path: str,
    ) -> int | None:
        for file_record in inventory.files:
            if file_record.path == path:
                return file_record.size_bytes
        for skipped_record in inventory.skipped:
            if skipped_record.path == path:
                return skipped_record.size_bytes
        return None

    def _digest(self, value: Any) -> str:
        encoded = json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(encoded).hexdigest()
