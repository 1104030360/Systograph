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
- 若 outputs 已有 artifact，建立 timestamped subdirectory。
- fatal precondition error 只輸出 `map-error.md`。

## 不包含範圍
- 不跑 provider。
- 不建立 full `ai_system_map.json`。
- 不做 permission repair。
- 不做 GUI error state。

## 建議實作步驟
1. 建立 `src/kai_mind/core/models/errors.py`。
2. 建立 `src/kai_mind/core/models/scan.py` 的 `PreconditionResult`。
3. 建立 `OutputArtifactProvider` 的最小 output directory preparation。
4. 實作 `map-error.md` writer。
5. 測試 missing project：只產生 error report。
6. 測試 outputs 已存在：不覆寫，改 timestamp directory。
7. 測試 project path readable 成功時回傳 normalized root。

## 預期輸出
- `src/kai_mind/core/models/errors.py`
- `src/kai_mind/core/models/scan.py`
- `src/kai_mind/core/providers/output_artifact_provider.py`
- `tests/core/test_precondition_output_policy.py`

## 驗收標準
- missing project 回傳 fatal result。
- `map-error.md` 包含 `project_path`、`failure_reason`、`scan_stage`。
- 既有 `outputs/ai_system_map.json` 不被覆寫。
- timestamp directory 命名 deterministic 可注入 clock 測試。

## 可能風險與注意事項
- 不要用真實現在時間寫死測試，應注入 clock。
- Windows/macOS path 要用 `pathlib`。
- output directory 是 report artifact，不應成為下一次 scan 的 source of truth。

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
