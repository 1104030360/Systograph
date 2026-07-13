# Mapping Consumer Migration / Legacy Lookup Cleanup Report

## 範圍與結果

完成 Plan 08、09：mapping proposal packet與 detail scan canonical read-only target
resolution 改用 `SystemMapIndex`，並移除已被 tests證明取代的 route/service lookup；v1
detail child-map mutation、slot/extension aliases與 public response shape保留。

## 實作邏輯

- Read-only resolve與 mutation分層：`DetailScanTargetResolver` 只接受 canonical target
  types，legacy aliases由 `DetailScanService` compatibility seam處理。
- `MappingEvidencePacketBuilder` 只接 `SystemMapIndex`；route優先重用 build result既有
  normalized map，fallback才交給 `CanonicalMapLoader`。
- Evidence summary仍經 bounded secret masking；canonical packet不輸出 raw source。
- Cleanup採 owner allowlist，不以 repo-wide zero hit誤刪 validator、adapter、profile
  semantic maps、runtime trace或 manual mapping lookup。

## 步驟

1. 先鎖定 component/unmapped/edge/evidence/unknown target與 evidence ordering。
2. 建立 pure resolver與 canonical packet builder input。
3. 將 durable detail flow傳入既有 normalized map，避免重複 schema branching。
4. 移除 proposal route-local `_find_unmapped`與重複 canonical id assembly。
5. 逐項分類 legacy lookup inventory為 remove/keep owner。

## 測試方式

- `test_detail_scan_target_resolver.py`
- `test_detail_scan_service.py`
- `test_mapping_evidence_packet_builder.py`
- mapping proposal/detail build web regression與 parent/child lineage tests。
- Source guard檢查 selected normalized consumers沒有 legacy model import或
  `schema_version ==` branch。

## 遇到的問題與解法

- 問題：canonical evidence沒有 v1 `value/snippet` 欄位，不能假裝完全相同資料來源。
- 解法：public packet維持相同欄位，以已驗證且 masked的 `extract_summary`填入 bounded
  summary；ordering、rule ids、line ranges與 context limits由 equivalence tests鎖定。
- 問題：detail scan仍必須更新 v1 child map。
- 解法：只遷移 scan前的 read-only resolution；mutation helper明確保留 compatibility
  命名並只操作 deep-copied child。

## 測試結果

- Plan 08/09 tests已包含於 `118 passed` focused backend matrix。
- Ruff、Mypy、diff check均通過。
- Public HTTP/error/lineage regression未發現變更。
