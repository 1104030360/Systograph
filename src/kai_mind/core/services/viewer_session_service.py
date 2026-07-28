# 這個檔案負責：把已驗證的 system map 轉成前端 ViewerLoadResult。
# 核心路徑：load / build → CanonicalMapLoader →
# GraphProjectionService.project。
#
# 呼叫鏈：
#   Web POST /api/viewer/load、BuildArtifactPublisher、BuildManifestService
#     → ViewerSessionService.load_map / build / project_to_graph
#         → CanonicalMapLoader.load（v1/v2 → AiSystemMapV2）
#         → _graph_recommended_next_checks（只讀 normalized，v1/v2 同一條路）
#         → GraphProjectionService.project（→ GraphViewModel）
#         → ViewerLoadResult
"""Load validated system maps into frontend viewer payloads."""

from __future__ import annotations

import json
from collections.abc import Mapping
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.models.profile_signal import ProfileInferenceResult
from kai_mind.core.models.system_map import RagSystemMap
from kai_mind.core.models.viewer import (
    GraphDetailsModel,
    GraphFiltersModel,
    GraphRecommendedNextCheckModel,
    GraphViewModel,
    ViewerLoadResult,
)
from kai_mind.core.services.canonical_map_loader import (
    CanonicalMapLoader,
    CanonicalMapLoadError,
    CanonicalMapLoadResult,
)
from kai_mind.core.services.graph_projection_service import (
    GRAPH_SCHEMA_VERSION,
    GraphProjectionService,
)
from kai_mind.core.services.path_safety_service import (
    is_project_relative_posix_path,
)
from kai_mind.core.services.system_map_validation_service import (
    SystemMapValidationService,
)
from kai_mind.core.services.viewer_legacy_compatibility import (
    _preserve_legacy_edge_order,
    _with_legacy_details,
)


# 做什麼：Viewer session 服務；讀 map、正規化、呼叫 graph projection。
# 被誰用：viewer_routes、BuildArtifactPublisher、BuildManifestService、
# MapBuild 相關。
# 自己呼叫：CanonicalMapLoader、GraphProjectionService。
class ViewerSessionService:
    """Convert validated canonical maps into frontend graph payloads."""

    # 做什麼：注入（或預設）canonical loader 與 graph projection。
    # 被誰呼叫：各 service / DI 建構時。
    # 自己呼叫：CanonicalMapLoader、GraphProjectionService。
    def __init__(
        self,
        *,
        validation_service: SystemMapValidationService | None = None,
        canonical_loader: CanonicalMapLoader | None = None,
        graph_projection_service: GraphProjectionService | None = None,
    ) -> None:
        self._canonical_loader = canonical_loader or CanonicalMapLoader(
            v1_validation_service=validation_service
        )
        self._graph_projection = (
            graph_projection_service or GraphProjectionService()
        )

    # 做什麼：從磁碟讀 ai_system_map.json → validate/load → 投影成
    # ViewerLoadResult。
    # 被誰呼叫：viewer_routes.POST /api/viewer/load。
    # 自己呼叫：CanonicalMapLoader.load → build_loaded。
    # 失敗：回 empty(error_reason=...)，不丟未處理例外給 API。
    def load_map(self, map_json_path: Path) -> ViewerLoadResult:
        """Read, validate, and project one ai_system_map.json file."""

        try:
            raw = map_json_path.read_text(encoding="utf-8")
            parsed = json.loads(raw)
            if not isinstance(parsed, Mapping):
                return self.empty(error_reason="map_json_must_be_object")
            loaded = self._canonical_loader.load(parsed)
        except OSError as exc:
            return self.empty(error_reason=f"map_read_failed: {exc}")
        except JSONDecodeError as exc:
            return self.empty(error_reason=f"invalid_json: {exc.msg}")
        except CanonicalMapLoadError as exc:
            return self.empty(error_reason=f"invalid_map: {exc}")

        return self.build_loaded(
            loaded,
            map_json_path=map_json_path,
        )

    def build_loaded(
        self,
        loaded: CanonicalMapLoadResult,
        *,
        map_json_path: Path | None = None,
        profile_result: ProfileInferenceResult | None = None,
    ) -> ViewerLoadResult:
        normalized = loaded.normalized
        legacy_source = loaded.legacy_source_map
        if legacy_source is not None:
            normalized = _preserve_legacy_edge_order(
                legacy_source,
                normalized,
            )
        graph = self._graph_projection.project(
            normalized,
            profile_result=profile_result,
            artifact_ref=_safe_artifact_ref(map_json_path),
            recommended_next_checks=_graph_recommended_next_checks(normalized),
        )
        if legacy_source is not None:
            graph = _with_legacy_details(graph, legacy_source)
        return self._result(
            ai_system_map=loaded.source_map.model_dump(mode="json"),
            graph=graph,
        )

    def build_canonical(
        self,
        system_map: AiSystemMapV2,
        *,
        map_json_path: Path | None = None,
        profile_result: ProfileInferenceResult | None = None,
    ) -> ViewerLoadResult:
        loaded = self._canonical_loader.load(
            system_map.model_dump(mode="json")
        )
        return self.build_loaded(
            loaded,
            map_json_path=map_json_path,
            profile_result=profile_result,
        )

    # 做什麼：對已驗證的 v1 RagSystemMap 做投影，回完整 ViewerLoadResult。
    # 被誰呼叫：load_map（v1）、BuildArtifactPublisher.publish、
    # BuildManifestService.load。
    # 自己呼叫：
    #   CanonicalMapLoader（若缺 normalized）→ 保序 edges →
    #   GraphProjectionService.project → _with_legacy_details → _result。
    def build(
        self,
        system_map: RagSystemMap,
        *,
        map_json_path: Path | None = None,
        normalized_system_map: AiSystemMapV2 | None = None,
        profile_result: ProfileInferenceResult | None = None,
    ) -> ViewerLoadResult:
        """Return a complete viewer load result for a validated map."""

        loaded = self._canonical_loader.load(
            system_map.model_dump(mode="json")
        )
        if normalized_system_map is not None:
            loaded = loaded.with_normalized(normalized_system_map)
        return self.build_loaded(
            loaded,
            map_json_path=map_json_path,
            profile_result=profile_result,
        )

    # 做什麼：只回 GraphViewModel（不要完整 ViewerLoadResult）。
    # 被誰呼叫：需要純圖資料的路徑 / tests。
    # 自己呼叫：CanonicalMapLoader → GraphProjectionService.project → legacy
    # details。
    def project_to_graph(
        self,
        system_map: RagSystemMap,
        *,
        map_json_path: Path | None = None,
    ) -> GraphViewModel:
        """Project canonical facts into semantic graph data only."""

        normalized = _preserve_legacy_edge_order(
            system_map,
            self._canonical_loader.load(
                system_map.model_dump(mode="json")
            ).normalized,
        )
        graph = self._graph_projection.project(
            normalized,
            artifact_ref=_safe_artifact_ref(map_json_path),
            recommended_next_checks=_graph_recommended_next_checks(normalized),
        )
        return _with_legacy_details(graph, system_map)

    # 做什麼：組成功的 ViewerLoadResult（loaded=True + map JSON 字串 + graph）
    # 。
    # 被誰呼叫：build_loaded。
    # 自己呼叫：json.dumps（排序 key，確定性輸出）。
    @staticmethod
    def _result(
        *,
        ai_system_map: dict[str, Any],
        graph: GraphViewModel,
    ) -> ViewerLoadResult:
        return ViewerLoadResult(
            loaded=True,
            error_reason=None,
            map_json=json.dumps(
                ai_system_map,
                ensure_ascii=False,
                sort_keys=True,
            ),
            ai_system_map=ai_system_map,
            graph_view_model=graph,
        )

    # 做什麼：回契約相容的空結果（loaded=False），給錯誤路徑用。
    # 被誰呼叫：load_map 各失敗分支。
    # 自己呼叫：組空 GraphViewModel / GraphDetailsModel / GraphFiltersModel。
    def empty(
        self, *, error_reason: str = "no_map_loaded"
    ) -> ViewerLoadResult:
        """Return a contract-compatible empty viewer load result."""

        return ViewerLoadResult(
            loaded=False,
            error_reason=error_reason,
            map_json=None,
            ai_system_map={},
            graph_view_model=GraphViewModel(
                schema_version=GRAPH_SCHEMA_VERSION,
                source_schema_version=None,
                map_json=None,
                summary=None,
                nodes=[],
                edges=[],
                details=GraphDetailsModel(),
                filters=GraphFiltersModel(
                    available=[],
                    behavior="highlight",
                ),
            ),
        )


# 做什麼：把 canonical map 的 recommended_next_checks 投成 viewer model。
# 被誰呼叫：build_loaded / project_to_graph（v1、v2 走同一條投影路徑）。
# 自己呼叫：GraphRecommendedNextCheckModel。
# 注意：只讀 normalized AiSystemMapV2；不要改回讀 v1 legacy source map，
# 否則 v2 build 的 checks 會再次消失。順序沿用 map 內的順序（build 時已排序）。
def _graph_recommended_next_checks(
    system_map: AiSystemMapV2,
) -> list[GraphRecommendedNextCheckModel]:
    return [
        GraphRecommendedNextCheckModel(
            id=check.id,
            target_type=check.target_type,
            target=check.target,
            reason=check.reason,
            action=check.action,
        )
        for check in system_map.recommended_next_checks
    ]


# 做什麼：把 map 路徑收成投影用的 artifact_ref（必須是專案相對 POSIX，
# 否則只留檔名）。
# 被誰呼叫：load_map / build / project_to_graph。
# 自己呼叫：is_project_relative_posix_path。
def _safe_artifact_ref(map_json_path: Path | None) -> str | None:
    if map_json_path is None:
        return None
    candidate = map_json_path.as_posix()
    if is_project_relative_posix_path(candidate):
        return candidate
    return map_json_path.name
