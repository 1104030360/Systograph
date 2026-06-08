# 2026-06-08 Phase21 Progressive Detail Scan TODO

## 目標

依照 `docs/work/Timmy/schedule/plan/unfinish/21-implement-progressive-detail-scan.md` 實作 Task 21：提供 target-scoped 的 bounded detail scan，讓 L2 component detail scan 與 L3 code path scan 能追加 `detail_scans[]`、canonical `evidence[]`，並把新 evidence id 掛回對應 target，供 Task 20 `MappingEvidencePacketBuilder` 使用。

## 實作邏輯

- 以 deterministic static analysis 為主：Python `ast` 抽取 imports、class/function signatures、decorators，bounded regex / AST walker 抽取 call-like hints。
- 只掃 target-related files，不做 whole-repo LLM scan、不執行目標專案、不呼叫 runtime endpoint。
- 所有 snippet / value 進入 system map 前都先經過 `SecretMaskingService`。
- detail scan signal 同時寫入三個位置：
  - `detail_scans[]`：給前端 lazy loading 顯示 findings / code path / warnings。
  - `evidence[]`：維持 canonical evidence query source。
  - target 的 `evidence_ids`：讓 Task 20 packet builder 不需讀 `detail_scans[]` 也能取得細掃 evidence。
- 寫入後重新跑 `SystemMapValidationService.validate()`；失敗時不得保存變更。

## 步驟

1. 讀取現有 `RagSystemMap`、validation、session store、API route 與 mapping proposal 測試慣例。
2. 先寫紅燈測試：
   - L2 只掃 unmapped/component/extension 相關檔案並遮蔽 secret。
   - L3 call-like hints 標示 `best_effort`，且帶 file / line / evidence id。
   - detail scan 後新 evidence 同時出現在 `evidence[]` 與 target `evidence_ids`。
   - `MappingEvidencePacketBuilder` 能吃到 detail scan 追加 evidence。
   - invalid target route 回傳 422 且不寫入 map。
3. 實作 core services：
   - `DetailScanService`
   - `ComponentDetailScanService`
   - `CodePathScanService`
4. 實作 web API：
   - `POST /api/detail-scans`
   - `GET /api/detail-scans/{detail_scan_id}`
5. 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`，補 detail scan request / response、target id 規則、lazy loading 與 evidence 追加行為。
6. 執行 unit / web / integration 相關測試，再跑完整測試與格式檢查。
7. 完成後寫 `docs/work/Timmy/schedule/report/2026-06-08-phase21-progressive-detail-scan-REP.md`，逐項記錄驗收結果。

## 驗收重點

- 不破壞既有 `ai-system-map/v1` contract 與 validation。
- 不把 detail scan finding 直接升級成 confirmed component / extension / edge。
- 不輸出 raw full file、不保留 unmasked secret。
- invalid target 不保存變更。
- Task 20 proposal packet 可自動包含 Task 21 追加的 evidence。
