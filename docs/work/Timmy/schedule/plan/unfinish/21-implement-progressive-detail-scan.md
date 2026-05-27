# Task 21: Implement Progressive Detail Scan

## 目標
實作 L2 `ComponentDetailScanService` 與 L3 `CodePathScanService`，讓使用者能針對 component、extension、unmapped、edge、evidence 做 bounded detail scan。結果寫入 `detail_scans[]`，不得繞過 validation 改寫 canonical facts。

## 為什麼要先做這個
L1 system map 先可用後，才需要 progressive drill-down。這符合設計文件要求：先粗看，再由使用者選特定元件深入，避免一開始做 whole-repo call graph。

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
- 將結果 append 到 `detail_scans[]` 並重新 validate。

## 不包含範圍
- 不做完整 call graph。
- 不追 framework/runtime internals。
- 不把 detail scan 結果直接升級成 detected slot。
- 不拆成外部 detail artifact，Epic 1 先寫回同一 JSON。

## 建議實作步驟
1. 建立 `src/kai_mind/core/models/detail_scan.py`。
2. 建立 `src/kai_mind/core/services/detail_scan_service.py`。
3. 建立 `component_detail_scan_service.py`，重用 existing evidence/files。
4. 建立 `code_path_scan_service.py`，先用 bounded import/call pattern，不做完整 AST。
5. 實作 target validation。
6. 實作 detail result append + validation。
7. 測試 L2 retriever detail、L3 edge path、invalid target rejected。

## 預期輸出
- `src/kai_mind/core/models/detail_scan.py`
- `src/kai_mind/core/services/detail_scan_service.py`
- `src/kai_mind/core/services/component_detail_scan_service.py`
- `src/kai_mind/core/services/code_path_scan_service.py`
- `tests/core/test_detail_scan_service.py`

## 驗收標準
- L2 只掃 target 相關檔案。
- L3 標示 `best_effort` / bounded uncertainty。
- `detail_scans[]` 不含大量 raw source 或 unmasked data。
- invalid target 不會寫入 map。

## 可能風險與注意事項
- Tree-sitter 可作未來改善，但第一版不要因此卡住。
- 不要追 LangChain/OpenAI/Qdrant client internals。
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
│ detail_scans[]        │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ validate map          │
└──────────────────────┘
```
