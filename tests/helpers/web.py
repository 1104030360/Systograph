"""Test-only accessors for services wired into the local API app.

這是測試讀取 app 內部服務的**唯一** choke point。
Plan 1 把 app.state.X 改成 app.state.services.X 時，只有這個檔案要改。
"""

from __future__ import annotations

from typing import cast

from kai_mind.core.services.mapping_proposal_service import (
    MappingProposalService,
)
from kai_mind.web.app import LocalApiApp
from kai_mind.web.session_store import SessionStore


def app_session_store(app: LocalApiApp) -> SessionStore:
    """Return the session store instance the routes actually use."""
    return cast(SessionStore, app.state.session_store)


def app_mapping_proposal_service(
    app: LocalApiApp,
) -> MappingProposalService:
    """Return the mapping proposal service instance routes actually use."""
    return cast(MappingProposalService, app.state.mapping_proposal_service)
