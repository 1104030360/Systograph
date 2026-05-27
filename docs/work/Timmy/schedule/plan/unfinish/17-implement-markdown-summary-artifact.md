# Task 17: Implement Markdown Summary Artifact

## 目標
實作 `MarkdownSummaryService`，從 validated `RagSystemMap` 產生 `ai_system_map.md`。Markdown 必須只讀 canonical map，不重新掃描檔案，也不得輸出 full secret。

## 為什麼要先做這個
Local web API 產生 JSON 後，使用者還需要可讀報告快速理解 system map。設計文件要求 Markdown 是 artifact output 的一部分，但它不能成為第二份 truth。

## 前置需求
- Task 15 已完成 normalized validated map。
- Task 16 已完成 `MapBuildService`、local web API map build 與 JSON output。
- Task 5 已完成 secret masking。

## 實作範圍
- 建立 `MarkdownSummaryService`。
- 產生 sections：系統總覽、slot coverage、detected/missing slots、indexing flow、query/answer flow、external endpoints、network exposure、recommended next checks。
- 串接 `MapBuildService` 寫出 `ai_system_map.md`。
- 確認 Markdown 不含 full secret。

## 不包含範圍
- 不重新讀 project files。
- 不產生 final READY/RISKY/NOT_READY verdict。
- 不做 GUI layout。
- 不做 CLI 專屬輸出流程；CLI 後續只讀同一批 artifacts。
- 不做 AI summary。

## 建議實作步驟
1. 建立 `src/kai_mind/core/services/markdown_summary_service.py`。
2. 設計 Markdown section order。
3. 從 map object 渲染 slot coverage table。
4. 從 risk_hints 渲染 risk section，保留 uncertainty。
5. 從 endpoints 渲染 local/external endpoint section。
6. 在 `MapBuildService` 中 JSON validation pass 後產生 Markdown。
7. 寫測試：sections 存在、secret masked、不讀 raw project file。

## 預期輸出
- `src/kai_mind/core/services/markdown_summary_service.py`
- `tests/core/test_markdown_summary_service.py`
- 更新 `src/kai_mind/core/services/map_build_service.py`

## 驗收標準
- Local web API map build result 同時指向 `ai_system_map.json` 與 `ai_system_map.md`。
- CLI 後續接上時應重用同一個 artifact generation service。
- Markdown 包含設計文件指定 sections。
- Markdown 不包含 full fake secret。
- Markdown content 只依賴 validated map。

## 可能風險與注意事項
- 不要在 Markdown 重新開檔讀 snippet。
- risk hint 要寫 uncertainty，不要假裝完整 security verdict。
- Markdown 是報告，不是 schema source。

## 新手提示
Markdown summary 是給人看的翻譯版。正式資料仍然是 `ai_system_map.json`。

## 視覺化說明
```text
┌──────────────────────┐
│ validated             │
│ RagSystemMap          │
└──────┬─────────┬─────┘
       │         │
       ↓         ↓
┌──────────────┐ ┌──────────────────────┐
│ JSON writer  │ │ MarkdownSummary       │
│              │ │ Service               │
└──────┬───────┘ └──────────┬───────────┘
       ↓                    ↓
┌──────────────┐ ┌──────────────────────┐
│ ai_system_   │ │ ai_system_map.md      │
│ map.json     │ │                      │
└──────────────┘ └──────────────────────┘
```
