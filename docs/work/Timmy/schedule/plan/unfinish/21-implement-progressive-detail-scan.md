# Task 21: Implement Progressive Detail Scan

## 目標
實作 L2 `ComponentDetailScanService` 與 L3 `CodePathScanService`，讓使用者能針對 component、extension、unmapped、edge、evidence 做 bounded detail scan。結果寫入 `detail_scans[]`，不得繞過 validation 改寫 canonical facts。

## 為什麼要先做這個
L1 system map 先可用後，才需要 progressive drill-down。這符合設計文件要求：先粗看，再由使用者選特定元件深入，避免一開始做 whole-repo call graph。

## 產品與架構校正
本任務是 Task 20 AI proposal 的安全上下文來源之一。它要幫使用者和 AI 看「足夠相關、已遮蔽、可追溯」的 evidence，而不是讓 AI 自己翻整個 repo。

合理設計是由 Python scanner / detail scan service 先產生 bounded `MappingEvidencePacket`：

- 只針對使用者選到的 target-related files。
- 擷取 imports、class/function signatures、decorators、call-like patterns、相鄰少量 masked snippets。
- 記錄 evidence ids、line range、rule ids、source file、context limit metadata。
- 所有 snippet / value 必須先經過 `SecretMaskingService`。
- 不執行 target project，不使用 `sys.settrace`，不呼叫 runtime endpoint。

Task 20 可以把這份 packet 餵給 deterministic fallback 或 optional local LLM 產生候選；但本任務產出的 detail/evidence 本身仍不得直接升級成 canonical component / extension / flow edge。

## 承接 Task 16 延後功能
- 承接 Task 16 「不做 progressive detail scan / L2-L3 lazy loading」的延後範圍。
- Task 16 只建立 L1 map build 與 basic event shell；本任務才處理使用者點選 graph target 後的 bounded detail scan。
- Task 18 提供完整 `GraphViewModel` 後，本任務的 target id 必須能對應 `node_id`、`edge_id`、`component_id`、`source_id` 或 evidence id。
- 因為 GUI/local web UI 需要 lazy loading，本任務要提供 detail scan API 與必要的 progress event。

## 前置需求
- Task 16 已有 L1 map build。
- Task 18 已有 viewer graph projection。
- Task 20 已有 mapping proposal flow 可處理 detail scan 發現的不確定 mapping。

## 實作範圍
- 建立 `DetailScanService` 作為入口。
- 建立 `ComponentDetailScanService` 做 L2。
- 建立 `CodePathScanService` 做 L3。
- target validation：slot/component/extension/unmapped/edge/evidence 必須存在。
- L2/L3 只掃 target-related files。
- 產生或更新 target-scoped `MappingEvidencePacket`，供 Task 20 proposal 使用。
- 第一版可用 Python `ast` / bounded regex pattern 抽取 Python imports、class/function signatures、decorators、call-like hints；Tree-sitter 可作未來多語言強化。
- 對 snippets 設定明確上限，例如 per snippet max chars、per file max snippets、per packet max chars。
- 將結果 append 到 `detail_scans[]` 並重新 validate。
- 使用 FastAPI 建立 detail scan route，例如 `POST /api/detail-scans`、`GET /api/detail-scans/{detail_scan_id}`。
- 更新 `GET /api/scan/events` 或新增 detail-specific event，讓前端能顯示 selected target 的進度。
- 更新 Epic 1 local API guide，加入 target ids、detail result schema、lazy loading rule。

## 不包含範圍
- 不做完整 call graph。
- 不追 framework/runtime internals。
- 不讓 AI 自己決定要讀哪些檔案。
- 不把整份 raw source file 交給 AI。
- 不執行目標專案、不使用 `sys.settrace`、不做 in-process runtime instrumentation。
- 不呼叫 runtime endpoint；Task 22 才處理 opt-in query trace。
- 不把 detail scan 結果直接升級成 detected slot。
- 不拆成外部 detail artifact，Epic 1 先寫回同一 JSON。
- 不做 frontend detail panel；本任務只提供 backend API 與 data contract。

## 建議實作步驟
1. 建立 `src/kai_mind/core/models/detail_scan.py`。
2. 建立 `src/kai_mind/core/services/detail_scan_service.py`。
3. 建立 `component_detail_scan_service.py`，重用 existing evidence/files。
4. 建立 `mapping_evidence_packet_builder.py` 或重用 Task 20 的 builder，將 detail scan 結果整理成 target-scoped `MappingEvidencePacket`。
5. 建立 `code_path_scan_service.py`，先用 bounded import/call pattern；Python 專案可用 standard library `ast` 補 class/function/import/call-like extraction，不做 whole-repo call graph。
6. 實作 target validation。
7. 實作 context budget：限制 target files、snippet chars、packet chars、max findings，並在 response 標示 `best_effort` / truncated metadata。
8. 實作 detail result append + validation。
9. 建立 FastAPI detail scan routes，route 只能呼叫 `DetailScanService`。
10. 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`。
11. 測試 L2 retriever detail、L3 edge path、invalid target rejected、web route 不接受不存在的 target id；detail scan 不含 unmasked secret；packet 不包含 raw full file；不會呼叫 runtime endpoint。

## 預期輸出
- `src/kai_mind/core/models/detail_scan.py`
- `src/kai_mind/core/services/detail_scan_service.py`
- `src/kai_mind/core/services/component_detail_scan_service.py`
- `src/kai_mind/core/services/code_path_scan_service.py`
- `src/kai_mind/core/services/mapping_evidence_packet_builder.py`（若未在 Task 20 建立，則本任務建立；若已建立，則本任務擴充）
- `src/kai_mind/web/routes/detail_scan_routes.py`
- 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`
- `tests/unit/core/test_detail_scan_service.py`
- `tests/unit/core/test_mapping_evidence_packet_builder.py`
- `tests/web/test_detail_scan_routes.py`

## 驗收標準
- L2 只掃 target 相關檔案。
- L3 標示 `best_effort` / bounded uncertainty。
- `detail_scans[]` 不含大量 raw source 或 unmasked data。
- `MappingEvidencePacket` 只包含 bounded、masked、target-scoped context。
- detail scan 不會給 AI file tool、project root、raw source dump 或 shell/runtime 權限。
- detail scan 不會執行 target project、`sys.settrace` 或 runtime endpoint call。
- invalid target 不會寫入 map。
- local web API 可依 target id 觸發 bounded detail scan。
- API guide 已同步記錄 detail scan request/response 與 progress event。

## 可能風險與注意事項
- Tree-sitter 可作未來改善，但第一版不要因此卡住。
- 不要追 LangChain/OpenAI/Qdrant client internals。
- 單純 AST/import/call-like signal 仍可能不足以證明 runtime path，因此 response 要保留 uncertainty，不要把它包裝成已確認事實。
- 如果使用者需要 runtime 證據，應導到 Task 22 opt-in query trace，而不是在 detail scan 偷偷執行目標程式。
- 參考依據：Tree-sitter 官方 docs 可支援 bounded AST extraction；設計文件明確要求 L3 != whole-repo call graph。

## 新手提示
Detail scan 是放大鏡，不是重新掃整個城市。使用者點哪裡，就只看那附近。

## 視覺化說明
```text
┌──────────────┐
│ L1 base map  │
└──────┬───────┘
       ↓
┌──────────────────────┐
│ user selected target  │
└──────┬─────────┬─────┘
       │         │
 component       │ edge/evidence
       ↓         ↓
┌──────────────────────┐ ┌──────────────────────┐
│ L2 ComponentDetail    │ │ L3 CodePathScan       │
│ Scan                  │ │                      │
└──────────┬───────────┘ └──────────┬───────────┘
           └──────────────┬─────────┘
                          ↓
┌──────────────────────┐
│ masked bounded        │
│ EvidencePacket        │
└──────────┬───────────┘
                          ↓
┌──────────────────────┐
│ detail_scans[]        │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ validate map          │
└──────────────────────┘
```
