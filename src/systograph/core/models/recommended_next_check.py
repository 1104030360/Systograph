# 這個檔案負責：RecommendedNextCheck DTO 的唯一正式來源（canonical home）。
# 這個 model 同時有兩個身分：
#   1. 版本中立的 scan-fact DTO——RecommendedNextCheckService 推導出的結果，
#      v1 / v2 兩條 build 路徑都會用到。
#   2. ai-system-map/v1 contract 的一部分——RagSystemMap
#      .recommended_next_checks 的 element type。
# 正因為這個雙重身分，它不放在 scan.py（scan.py 需要 system_map.Evidence，
# 反向 import 會形成 module 迴圈），也不放在 system_map.py（那樣版本中立的
# service 就得依賴 v1 model 模組）。
# 本模組刻意不 import 任何其他 systograph model，確保不可能產生循環相依。
#
# 呼叫鏈：
#   RecommendedNextCheckService.derive → 產出 RecommendedNextCheck
#   models/system_map.py → import 當作 RagSystemMap.recommended_next_checks
#                          的 element type（v1 contract）
"""Canonical model for a single recommended next check."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


# 做什麼：建議下一步要檢查什麼（target + reason + action）。
# 被誰用：map build 組裝 recommended_next_checks；markdown summary / UI 顯示。
# 內含：無巢狀 model。
# 注意：不要加 class docstring——pydantic 會把它寫進 generated JSON Schema 的
# description，會讓 ai-system-map.v1.schema.json 的 contract 測試失敗。
class RecommendedNextCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    target_type: str
    target: str
    reason: str
    action: str
