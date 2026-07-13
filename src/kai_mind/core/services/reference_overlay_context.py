# 這個檔案負責：定義 reference / profile overlay 共用的唯讀「上下文包」。
# 本身不做投影；只把 overlay builders 需要的輸入綁在一起，避免參數散落。
#
# 呼叫鏈：
#   GraphProjectionService.project()
#     → ReferenceMapOverlayProjector.project(...)
#         → 組 ReferenceOverlayContext(index, profile_result,
# node_ids_by_source)
#         → build_reference_capability_overlay(catalog, context)
#         → build_profile_attachment_overlay(context)
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from kai_mind.core.models.profile_signal import ProfileInferenceResult
from kai_mind.core.services.system_map_index import SystemMapIndex


# 做什麼：overlay 建構時共用的輸入上下文（frozen，建好不能改）。
# 被誰用：
#   - ReferenceMapOverlayProjector.project() 建立
#   - reference_capability_overlay_builder / profile_attachment_overlay_builder
# 讀取
# 內含欄位：
#   - index：SystemMapIndex（查 component / unmapped / evidence）
#   - profile_result：可選的 ProfileInferenceResult（assessment / profile
# findings）
#   - node_ids_by_source：canonical source_id → graph node id（把 overlay 錨到
# base
# 圖）
# 自己呼叫：無方法；純資料承載。
@dataclass(frozen=True, slots=True)
class ReferenceOverlayContext:
    index: SystemMapIndex
    profile_result: ProfileInferenceResult | None
    node_ids_by_source: Mapping[str, str]
