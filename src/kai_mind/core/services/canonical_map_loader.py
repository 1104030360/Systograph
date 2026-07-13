# 這個檔案負責：dual-read 載入 map JSON，統一產出 canonical AiSystemMapV2。
# 它是 schema 分支的唯一入口：下游不要自己看 schema_version，一律吃 load()
# 結果。
#
# 呼叫鏈：
#   MapBuildPipeline / MapBuildService / BuildManifest /
#   mapping_proposal_routes / ApplyConfirmations / Viewer / Profile 相關
#     → CanonicalMapLoader.load(data)
#         ├─ v1 → SystemMapValidationService.validate
#         │       → SystemMapV1ToV2Adapter.adapt_to_canonical
#         │       → SystemMapV2ValidationService.validate（再驗一次）
#         └─ v2 → SystemMapV2ValidationService.validate
#     → CanonicalMapLoadResult.normalized（AiSystemMapV2）
#     → SystemMapIndex.from_map(...) 或其他下游
"""Dual-read loader for ai-system-map/v1 and ai-system-map/v2."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.services.system_map_v1_to_v2_adapter import (
    LegacySystemMapAdaptError,
    SystemMapV1ToV2Adapter,
)
from kai_mind.core.services.system_map_v2_validation_service import (
    SystemMapV2ValidationError,
    SystemMapV2ValidationService,
)
from kai_mind.core.services.system_map_validation_service import (
    SystemMapValidationError,
    SystemMapValidationService,
)

ActiveSchemaVersion = Literal["ai-system-map/v1", "ai-system-map/v2"]


# 做什麼：dual-read 載入失敗時丟出的錯誤（包住 validate / adapt 例外）。
# 被誰用：load / _load_v1 / _load_v2；呼叫端（Viewer / routes / tests）catch。
# 自己呼叫：無。
class CanonicalMapLoadError(ValueError):
    """Raised when dual-read loading fails."""


# 做什麼：load() 成功後的回傳值（原始 schema、正規化 map、migration warnings）
# 。
# 被誰用：所有呼叫 CanonicalMapLoader.load() 的 service / route。
# 內含：normalized → AiSystemMapV2（下游主要吃這個）。
@dataclass(frozen=True, slots=True)
class CanonicalMapLoadResult:
    active_schema_version: ActiveSchemaVersion
    normalized: AiSystemMapV2
    migration_warnings: list[str]


# 做什麼：擁有全部 schema 分支邏輯的 loader；把 v1/v2 payload 收斂成
# AiSystemMapV2。
# 被誰用：MapBuildPipeline、MapBuildService、BuildManifest、mapping routes、
#         ApplyConfirmations、Viewer、Profile inference 等。
# 自己呼叫：_load_v1 / _load_v2；內部依賴 validation + adapter。
class CanonicalMapLoader:
    """Own all schema branching for map payloads.

    Routes and downstream services must consume the normalized v2 view from
    this loader instead of inspecting schema_version themselves.
    """

    # 做什麼：注入（或預設建立）v1/v2 validator 與 v1→v2 adapter。
    # 被誰呼叫：各 service 建構時 new CanonicalMapLoader(...)，或測時注入
    # fake。
    # 自己呼叫：預設 SystemMapValidationService / SystemMapV2ValidationService
    # /
    #           SystemMapV1ToV2Adapter。
    def __init__(
        self,
        *,
        v1_validation_service: SystemMapValidationService | None = None,
        v2_validation_service: SystemMapV2ValidationService | None = None,
        adapter: SystemMapV1ToV2Adapter | None = None,
    ) -> None:
        self._v1_validation_service = (
            v1_validation_service or SystemMapValidationService()
        )
        self._v2_validation_service = (
            v2_validation_service or SystemMapV2ValidationService()
        )
        self._adapter = adapter or SystemMapV1ToV2Adapter()

    # 做什麼：依 data["schema_version"] 分流到 v1 或 v2 載入路徑。
    # 被誰呼叫：MapBuildPipeline、BuildManifest、routes、ApplyConfirmations、
    #           Profile / Reference assessment、Viewer 等。
    # 自己呼叫：_load_v1 / _load_v2；未知 version → CanonicalMapLoadError。
    def load(self, data: Mapping[str, Any]) -> CanonicalMapLoadResult:
        schema_version = data.get("schema_version")
        if schema_version == "ai-system-map/v1":
            return self._load_v1(data)
        if schema_version == "ai-system-map/v2":
            return self._load_v2(data)
        raise CanonicalMapLoadError(
            f"unsupported schema_version: {schema_version!r}"
        )

    # 做什麼：載入 v1 map → validate → adapter 轉 canonical → 再用 v2
    # validator 驗一次。
    # 被誰呼叫：load()（當 schema_version == ai-system-map/v1）。
    # 自己呼叫：
    #   - SystemMapValidationService.validate → RagSystemMap
    #   - SystemMapV1ToV2Adapter.adapt_to_canonical → AiSystemMapV2
    #   - SystemMapV2ValidationService.validate（確保轉完仍合法）
    # 失敗：任何一步例外都包成 CanonicalMapLoadError。
    def _load_v1(self, data: Mapping[str, Any]) -> CanonicalMapLoadResult:
        try:
            system_map = self._v1_validation_service.validate(data)
            normalized = self._adapter.adapt_to_canonical(system_map)
            self._v2_validation_service.validate(
                normalized.model_dump(mode="json")
            )
        except (
            SystemMapValidationError,
            LegacySystemMapAdaptError,
            SystemMapV2ValidationError,
        ) as exc:
            raise CanonicalMapLoadError(str(exc)) from exc
        return CanonicalMapLoadResult(
            active_schema_version="ai-system-map/v1",
            normalized=normalized,
            migration_warnings=list(normalized.migration_warnings),
        )

    # 做什麼：直接用 v2 validator 載入原生 v2 payload（不經 adapter）。
    # 被誰呼叫：load()（當 schema_version == ai-system-map/v2）。
    # 自己呼叫：SystemMapV2ValidationService.validate → AiSystemMapV2。
    # 失敗：SystemMapV2ValidationError → CanonicalMapLoadError。
    def _load_v2(self, data: Mapping[str, Any]) -> CanonicalMapLoadResult:
        try:
            normalized = self._v2_validation_service.validate(data)
        except SystemMapV2ValidationError as exc:
            raise CanonicalMapLoadError(str(exc)) from exc
        return CanonicalMapLoadResult(
            active_schema_version="ai-system-map/v2",
            normalized=normalized,
            migration_warnings=list(normalized.migration_warnings),
        )
