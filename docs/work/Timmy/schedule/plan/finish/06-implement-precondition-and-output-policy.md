# Task 6: Implement Precondition and Output Policy

## 目標
實作 Stage 1 precondition check 與 output directory policy。這個任務要讓 missing/unreadable project、output 已存在、error report 行為都可測且可重現。

## 為什麼要先做這個
`MapBuildService` 第一件事就是確認 project path 與 output policy。若這層不穩，後面 providers 寫得再好，也可能覆蓋舊報告或在 missing project 時產生不完整 artifact。

## 前置需求
- Task 1 已完成 backend foundation。
- Task 2 已有 error/model 基礎。
- Task 4 已有 fixture path helpers。

## 實作範圍
- 建立 precondition result/error models。
- 檢查 project path exists、is directory、readable。
- 決定 output run directory。
- 建立薄的 `OutputRun` context，集中保存本次 scan 的 resolved artifact paths。
- 若 outputs 已有 artifact，建立 timestamped subdirectory。
- fatal precondition error 先建立 structured `PreconditionError`，再由程式 render 成 `map-error.md`。
- `map-error.md` 是使用者可讀的正式 error artifact；錯誤原因不可只存在 log。

## 不包含範圍
- 不跑 provider。
- 不建立 full `ai_system_map.json`。
- 不做 permission repair。
- 不做 GUI error state。
- 不在本任務輸出 `map-error.json`；若未來 CLI/CI 需要 machine-readable failure contract，再新增 `outputs/map-error.json`。

## 建議實作步驟
1. 建立 `src/kai_mind/core/models/errors.py`。
2. 建立 `src/kai_mind/core/models/scan.py` 的 `PreconditionResult`。
3. 建立 `OutputRun`，保存 `root_dir`、`map_error_path`、`map_json_path`、`map_markdown_path`。
4. 建立 `OutputArtifactProvider` 的最小 output directory preparation。
5. 定義 `PreconditionError` 欄位與 `failure_reason` enum，例如 `project_path_not_found`、`project_path_not_directory`、`project_path_not_readable`、`output_directory_not_writable`。
6. 實作 `map-error.md` writer：只接受 structured error object 與 `OutputRun`，不直接從 exception/log 字串拼接錯誤報告。
7. 測試 missing project：只產生 error report。
8. 測試 outputs 已存在：不覆寫，改 timestamp directory。
9. 測試 project path readable 成功時回傳 normalized root 與 `OutputRun`。

## 預期輸出
- `src/kai_mind/core/models/errors.py`
- `src/kai_mind/core/models/scan.py`
- `src/kai_mind/core/providers/output_artifact_provider.py`
- `tests/unit/core/test_precondition_output_policy.py`

## 驗收標準
- missing project 回傳 fatal result。
- `map-error.md` 包含 `project_path`、`failure_reason`、`scan_stage`。
- `map-error.md` 由 `PreconditionError` render 產生，不由 AI 產生，也不從 log 檔反推。
- writer 使用 resolved `OutputRun`，不要求呼叫端重複傳 raw `output_dir`。
- 既有 `outputs/ai_system_map.json` 不被覆寫。
- timestamp directory 命名 deterministic 可注入 clock 測試。
- timestamp directory 若已存在，使用 deterministic suffix，例如 `20260601T093000-1`，不可重用舊 run directory。

## 可能風險與注意事項
- 不要用真實現在時間寫死測試，應注入 clock。
- Windows/macOS path 要用 `pathlib`。
- output directory 是 report artifact，不應成為下一次 scan 的 source of truth。
- log 可以記錄 debug 訊息，但不能取代 `map-error.md`，也不能成為測試 error contract 的來源。
- 若未來新增 `map-error.json`，它應與 `map-error.md` 來自同一個 structured error object，避免兩份輸出內容漂移。

## 新手提示
Precondition 是掃描前的安全門。它不理解 RAG，只負責確認「能不能安全開始」。

## 視覺化說明
```text
┌──────────────┐
│ project_path │
└──────┬───────┘
       ↓
┌──────────────────────┐
│ exists and readable?  │
└──────┬─────────┬─────┘
       │ no      │ yes
       ↓         ↓
┌──────────────┐ ┌──────────────────────┐
│ write         │ │ outputs has          │
│ map-error.md  │ │ artifacts?           │
└──────────────┘ └──────┬─────────┬─────┘
                        │ no      │ yes
                        ↓         ↓
                 ┌──────────────┐ ┌──────────────────────┐
                 │ use outputs/ │ │ use outputs/timestamp │
                 └──────────────┘ └──────────────────────┘
```
