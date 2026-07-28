"""In-memory session state for the local development API."""

from __future__ import annotations

import hashlib
import logging
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from kai_mind.core.models.analysis_history import (
    LatestBuildPointer,
    ProjectState,
)
from kai_mind.core.models.map_build import MapBuildResult
from kai_mind.core.models.viewer import ViewerPayload
from kai_mind.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
    LocalStateError,
)
from kai_mind.core.services.build_manifest_service import (
    BuildArtifactLoadError,
    BuildManifestService,
)
from kai_mind.core.services.logging_service import safe_log_event
from kai_mind.core.services.viewer_session_service import ViewerSessionService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProjectRecord:
    project_id: str
    project_path: Path
    project_name: str
    source_type: str
    reused: bool = False


class SessionStore(Protocol):
    def import_project(
        self, *, project_path: Path, source_type: str
    ) -> ProjectRecord: ...

    def project(self, project_id: str) -> ProjectRecord | None: ...

    def save_build_result(
        self, result: MapBuildResult, *, project_id: str | None = None
    ) -> None: ...

    def save_viewer_payload(self, payload: ViewerPayload) -> None: ...

    def latest_viewer_payload(self) -> ViewerPayload: ...

    def hydrate_from_latest(self) -> None: ...

    def latest_build_result(self) -> MapBuildResult | None: ...

    def build_result(self, project_id: str) -> MapBuildResult | None: ...

    def build_results(self) -> tuple[tuple[str, MapBuildResult], ...]: ...


def save_committed_build_projection(
    store: SessionStore,
    result: MapBuildResult,
    *,
    project_id: str,
) -> MapBuildResult:
    try:
        store.save_build_result(result, project_id=project_id)
    except (OSError, RuntimeError, ValueError):
        warning = "session_projection_save_failed"
        if warning not in result.warnings:
            return result.model_copy(
                update={"warnings": [*result.warnings, warning]}
            )
    return result


class InMemorySessionStore:
    """Non-persistent local API state for one backend process."""

    def __init__(
        self,
        *,
        projection_service: ViewerSessionService | None = None,
    ) -> None:
        self._projection_service = projection_service or ViewerSessionService()
        self._projects: dict[str, ProjectRecord] = {}
        self._latest_viewer_payload = ViewerPayload(
            viewer_load_result=self._projection_service.empty()
        )
        self._latest_build_result: MapBuildResult | None = None
        self._build_results_by_project: dict[str, MapBuildResult] = {}

    def import_project(
        self,
        *,
        project_path: Path,
        source_type: str,
    ) -> ProjectRecord:
        record = ProjectRecord(
            project_id=f"project:{uuid4()}",
            project_path=project_path,
            project_name=project_path.name or "project",
            source_type=source_type,
        )
        self._projects[record.project_id] = record
        return record

    def project(self, project_id: str) -> ProjectRecord | None:
        return self._projects.get(project_id)

    def save_build_result(
        self,
        result: MapBuildResult,
        *,
        project_id: str | None = None,
    ) -> None:
        self._latest_build_result = result
        if project_id is not None:
            self._build_results_by_project[project_id] = result
        if result.viewer_load_result is not None:
            self.save_viewer_payload(
                ViewerPayload(viewer_load_result=result.viewer_load_result)
            )

    def save_viewer_payload(self, payload: ViewerPayload) -> None:
        self._latest_viewer_payload = payload

    def latest_viewer_payload(self) -> ViewerPayload:
        return self._latest_viewer_payload

    def hydrate_from_latest(self) -> None:
        """No-op：記憶體實作沒有可還原的持久化來源。

        存在的理由是讓 `SessionStore` 兩個實作有同一組方法，
        `create_app()` 不必先問「這個 store 撐不撐得住 hydrate」。
        """

    def latest_build_result(self) -> MapBuildResult | None:
        return self._latest_build_result

    def build_result(self, project_id: str) -> MapBuildResult | None:
        return self._build_results_by_project.get(project_id)

    def build_results(self) -> tuple[tuple[str, MapBuildResult], ...]:
        return tuple(self._build_results_by_project.items())


class PersistentSessionStore:
    """Durable local API state plus a "this process wrote it" cache.

    快取語意：`_latest_build_result` / `_latest_viewer_payload` 只代表
    「**本 process 剛寫入**的那一份」，不是「磁碟上最新的那一份」。
    只有 save_* 與開機時的 `hydrate_from_latest()` 會寫這兩個欄位；
    getter 一律不寫（查某個 project 的舊 build 不可以把「最新」換掉）。

    兩個欄位的沒命中行為刻意不同：`latest_build_result()` 沒命中時回頭
    問 repository（呼叫端要的是磁碟上最新的 build）；
    `latest_viewer_payload()` 一律只回快取，因為 `POST /api/viewer/load`
    載入的 map 不可以被既有 build 蓋掉（`docs/API-GUIDE.md`
    的 `POST /api/viewer/load` 段），開機那一份改由 hydrate 預熱。

    `create_app()` 只建一個 store 給所有 request 共用，而 route handler
    多半是 sync `def` → FastAPI 丟進 anyio threadpool，所以這兩個可變欄位
    真的會被多執行緒同時存取，需要 `_lock` 保護。
    """

    def __init__(
        self,
        *,
        repository: LocalJsonStateProvider,
        manifest_service: BuildManifestService,
        projection_service: ViewerSessionService | None = None,
    ) -> None:
        self._repository = repository
        self._manifest_service = manifest_service
        self._projection = projection_service or ViewerSessionService()
        self._lock = threading.RLock()
        self._latest_viewer_payload = ViewerPayload(
            viewer_load_result=self._projection.empty()
        )
        self._latest_build_result: MapBuildResult | None = None

    def import_project(
        self,
        *,
        project_path: Path,
        source_type: str,
    ) -> ProjectRecord:
        resolved = project_path.expanduser().resolve()
        path_digest = (
            "sha256:"
            + hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()
        )
        existing = self._repository.find_project_by_path_digest(path_digest)
        if existing is not None:
            return self._record(existing, reused=True)
        state = ProjectState(
            project_id=f"project:{uuid4()}",
            project_name=resolved.name or "project",
            source_type="local_path",
            canonical_path=str(resolved),
            path_digest=path_digest,
            created_at=datetime.now(UTC),
        )
        self._repository.save_project(state)
        return self._record(state, reused=False)

    def project(self, project_id: str) -> ProjectRecord | None:
        state = self._repository.get_project(project_id)
        return self._record(state, reused=True) if state else None

    def save_build_result(
        self,
        result: MapBuildResult,
        *,
        project_id: str | None = None,
    ) -> None:
        # 直接寫欄位（而非轉呼叫 save_viewer_payload）是為了讓兩個欄位
        # 在同一個 critical section 內更新，不會被 threadpool 切成
        # 「build 已換、viewer 還沒換」的中間狀態。RLock 的可重入性
        # 只解決死鎖，不解決原子性。
        with self._lock:
            self._latest_build_result = result
            if result.viewer_load_result is not None:
                self._latest_viewer_payload = ViewerPayload(
                    viewer_load_result=result.viewer_load_result
                )

    def save_viewer_payload(self, payload: ViewerPayload) -> None:
        with self._lock:
            self._latest_viewer_payload = payload

    def latest_viewer_payload(self) -> ViewerPayload:
        """純快取讀取，不做任何 I/O，也不從 build 反推。

        `POST /api/viewer/load` 寫進來的 payload 就是最新的，不可以被
        磁碟上既有的 build 蓋掉（`docs/API-GUIDE.md` 的
        `POST /api/viewer/load` 段）。process 剛開機、還沒有人 load 也
        還沒 build 時的那一份，由 `hydrate_from_latest()` 預先填好。
        """
        with self._lock:
            return self._latest_viewer_payload

    def hydrate_from_latest(self) -> None:
        """開機時用磁碟上最新一份 build 預熱 viewer payload（只呼叫一次）。

        由 `create_app()` 在組裝完成後呼叫。這一次 I/O 換掉的是「每個
        `GET /api/map` 都重新走一次 repository + 重新載入 artifact」——
        前端是輪詢 `/api/map` 的，那個代價會一直付。

        取不到 build（沒有任何 project、artifact 全失效、state dir 損壞）
        時什麼都不做，快取維持建構子給的空 payload：hydrate 是預熱，
        不是啟動前提，絕對不可以讓 server 起不來。
        """
        try:
            result = self._newest_loadable_build_result()
        except (LocalStateError, OSError) as exc:
            # 最後一道防線，只剩「整份 project 清單讀不出來」會走到這裡
            # （`list_projects()` 自己丟 StateCorruptionError，
            # local_json_state_storage.py:88）。單一 project 的壞 pointer
            # 或壞 manifest 已經在 walk 裡面就地跳過，不會落到這裡 ——
            # 一個壞掉的 project 不可以讓整個 viewer 空白。
            # 這裡若不接，create_app() 會直接炸掉 → server 開不起來。
            safe_log_event(
                logger,
                logging.WARNING,
                "session_store_hydrate_failed",
                stage="web_session_store",
                exception_type=exc.__class__.__name__,
                detail=str(exc),
            )
            return
        if result is not None and result.viewer_load_result is not None:
            self.save_viewer_payload(
                ViewerPayload(viewer_load_result=result.viewer_load_result)
            )

    def latest_build_result(self) -> MapBuildResult | None:
        with self._lock:
            cached = self._latest_build_result
        if cached is not None:
            return cached
        pointers = self._latest_pointers_newest_first()
        if not pointers:
            return None
        # 只看最新那一個：它失效就回 None，不往下找次新的。呼叫端
        # （`GET /api/map/report`）問的是「最新那一個 build」，回一份更舊
        # 的 report 比回 404 更難察覺。往下找的策略只用在 hydrate。
        return self.build_result(pointers[0].project_id)

    def _newest_loadable_build_result(self) -> MapBuildResult | None:
        """由新到舊找第一個載得起來的 build（迴圈上界＝pointer 數量）。

        跟 `latest_build_result()` 的差別是刻意的：開機預熱時，一個壞掉
        的 project 不應該讓 viewer 整個空白 —— 其他 project 還有好的
        build 可以顯示。要真的做到這件事，容錯必須**逐個 project**，
        分兩層：pointer 列舉在 `_latest_pointers_newest_first()`，
        build 載入在下面這個迴圈裡。包在整段外面是不夠的。
        """
        for pointer in self._latest_pointers_newest_first():
            try:
                result = self.build_result(pointer.project_id)
            except (LocalStateError, OSError) as exc:
                # `build_result()` 只接 `manifest_service.load()` 丟的
                # BuildArtifactLoadError/OSError；`get_build_manifest()`
                # 讀到壞掉的 manifest.json 丟的 StateCorruptionError 會
                # 直接穿過它，所以要在迴圈裡面再接一層。
                # （artifact digest 失效那條已經在 build_result() 內轉成
                # None + `build_artifact_invalid`，走下面的 if。）
                self._log_project_skipped(
                    "hydrate_build_unreadable", exc, pointer.project_id
                )
                continue
            if result is not None:
                return result
        return None

    def _latest_pointers_newest_first(
        self,
    ) -> tuple[LatestBuildPointer, ...]:
        """列出各 project 的 latest pointer，由新到舊；讀不出來的跳過。

        逐個 project 容錯：壞掉的 `latest.json` 只能拖垮它自己那個
        project。這一步發生在 `_newest_loadable_build_result()` 的迴圈
        **之前**，只把容錯包在迴圈裡救不到它。

        對 `latest_build_result()` 的影響是刻意接受的：某個 project 的
        pointer 讀不出來時，它從「整支 raise → `/api/map/report` 500」
        變成「那個 project 當作沒有 latest build」。artifact 失效的語意
        沒變 —— 仍然只試最新那一個，載不起來就是 None。
        """
        # repository / artifact I/O 刻意不放在鎖裡：讀檔可能很慢，
        # 在鎖內做會讓所有 request 排隊等一次磁碟往返。
        pointers = []
        for project in self._repository.list_projects():
            try:
                pointer = self._repository.get_latest_pointer(
                    project.project_id
                )
            except (LocalStateError, OSError) as exc:
                self._log_project_skipped(
                    "latest_pointer_unreadable", exc, project.project_id
                )
                continue
            if pointer is not None:
                pointers.append(pointer)
        return tuple(
            sorted(
                pointers,
                key=lambda item: (item.updated_at, item.latest_build_id),
                reverse=True,
            )
        )

    @staticmethod
    def _log_project_skipped(
        event: str,
        exc: Exception,
        project_id: str,
    ) -> None:
        # detail 走 safe_log_event 的遮罩／路徑 redaction，
        # 只會留下檔名，不會外洩本機絕對路徑。
        safe_log_event(
            logger,
            logging.WARNING,
            event,
            stage="web_session_store",
            project_id=project_id,
            exception_type=exc.__class__.__name__,
            detail=str(exc),
        )

    def build_result(self, project_id: str) -> MapBuildResult | None:
        pointer = self._repository.get_latest_pointer(project_id)
        if pointer is None:
            return None
        manifest = self._repository.get_build_manifest(
            project_id,
            pointer.latest_build_id,
        )
        if manifest is None:
            return None
        try:
            return self._manifest_service.load(manifest)
        except (BuildArtifactLoadError, OSError) as exc:
            # OSError 也要接：digest_matches 先 path.is_file() 再 read_bytes()
            # （build_manifest_artifacts.py:235-245），中間檔案可能不可讀
            # （權限）或剛被刪掉，那個 read_bytes 不在任何 try 裡面。
            # detail 走 safe_log_event 的遮罩／路徑 redaction，
            # 只會留下 artifact 檔名，不會外洩本機絕對路徑。
            safe_log_event(
                logger,
                logging.WARNING,
                "build_artifact_invalid",
                stage="web_session_store",
                project_id=project_id,
                build_id=pointer.latest_build_id,
                exception_type=exc.__class__.__name__,
                detail=str(exc),
            )
            return None

    def build_results(self) -> tuple[tuple[str, MapBuildResult], ...]:
        results: list[tuple[str, MapBuildResult]] = []
        for project in self._repository.list_projects():
            # build_result 已在 artifact 失效時回 None，
            # 所以單一壞掉的 project 會被跳過，不會拖垮整批。
            result = self.build_result(project.project_id)
            if result is not None:
                results.append((project.project_id, result))
        return tuple(results)

    @staticmethod
    def _record(state: ProjectState, *, reused: bool) -> ProjectRecord:
        return ProjectRecord(
            project_id=state.project_id,
            project_path=Path(state.canonical_path),
            project_name=state.project_name,
            source_type=state.source_type,
            reused=reused,
        )
