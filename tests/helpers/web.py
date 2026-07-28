"""Test-only accessors for services wired into the local API app.

這是測試「拿 app 裡真正那個服務實例來斷言」的 choke point：需要摸到
內部服務的測試都走這裡，不要各自去碰 `app.state`。

唯一另一個刻意直接碰 `app.state` 的檔案是
`tests/web/test_app_wiring_contract.py`——它的職責就是釘住接線契約本身，
必須看得見原始結構，所以不透過這裡。

`cast` 只在 `_services()` 出現一次（Starlette state 本質是動態的），
跨過那道邊界之後就是 `AppServices` 的欄位存取，打錯字 mypy 會抓到。
"""

from __future__ import annotations

from typing import cast

from kai_mind.core.services.mapping_proposal_service import (
    MappingProposalService,
)
from kai_mind.web.app import LocalApiApp
from kai_mind.web.app_services import AppServices
from kai_mind.web.session_store import SessionStore


def _services(app: LocalApiApp) -> AppServices:
    return cast(AppServices, app.state.services)


def app_session_store(app: LocalApiApp) -> SessionStore:
    """Return the session store instance the routes actually use."""
    return _services(app).session_store


def app_mapping_proposal_service(
    app: LocalApiApp,
) -> MappingProposalService:
    """Return the mapping proposal service instance routes actually use."""
    return _services(app).mapping_proposal_service
