# 2026-06-01 Phase6 Precondition and Output Policy TODO

## 實作邏輯

本階段實作 Stage 1 precondition check 與 output directory policy。
核心資料結構先收斂成 structured `PreconditionError` 與
`PreconditionResult`，並使用薄的 `OutputRun` context 保存本次 scan
的 resolved artifact paths，再由 `OutputArtifactProvider` 將 fatal
precondition error render 成 `map-error.md`。

核心原則：

- Scanner 啟動前先檢查 `project_path` exists、is directory、readable。
- `failure_reason` 由程式 deterministic 判斷，不由 AI 產生。
- `map-error.md` 由 structured error object render，不從 log 反推。
- 本階段不輸出 `map-error.json`。
- output artifacts 已存在時不可覆寫，改用可注入 clock 的 timestamp
  run directory。
- 若 timestamp run directory 已存在，使用 deterministic suffix，避免同秒
  重複執行覆寫舊 run artifact。
- `output_dir` 只作為 raw input 傳入 precondition；writer 後續使用
  `OutputRun`，避免重複傳遞 raw path。
- 使用 `pathlib` 保持 Windows/macOS path 行為可攜。
- 不跑 provider，不建立 full `ai_system_map.json`。

## 階段拆分

### 1. Red：定義 unit contract tests

- 新增 `tests/unit/core/test_precondition_output_policy.py`。
- 測試 missing project 產生 fatal `PreconditionError`。
- 測試 project path 是檔案時回傳 `project_path_not_directory`。
- 測試 unreadable project path 回傳 `project_path_not_readable`。
- 測試 readable project path 成功時回傳 normalized root。
- 測試 `PreconditionResult` 回傳 `OutputRun`，且包含 `map-error.md`、
  `ai_system_map.json`、`ai_system_map.md` resolved paths。
- 測試 `map-error.md` writer 只從 structured error object render。
- 測試 `outputs/ai_system_map.json` 已存在時使用 timestamp directory。
- 測試 timestamp directory collision 時使用 deterministic suffix。

### 2. Red：定義 BDD-style integration behavior

- 新增 `tests/integration/test_phase6_precondition_output_policy_behaviors.py`。
- 情境：missing project 只產生 `map-error.md`，不產生正常 map。
- 情境：既有 output artifact 不被覆寫，新 run 寫入 timestamp directory；
  同秒 collision 時寫入 suffixed directory。

### 3. Green：建立最小 implementation

- 新增 `src/kai_mind/core/models/errors.py`。
- 新增 `src/kai_mind/core/models/scan.py`。
- 新增 `src/kai_mind/core/providers/output_artifact_provider.py`。
- `PreconditionError` 欄位包含 `project_path`、`failure_reason`、
  `scan_stage`。
- `PreconditionResult` 欄位包含 `ok`、`project_root`、`output_run_dir`、
  `output_run`、`warnings`、`error`。
- `OutputRun` 只保存 artifact path，不負責寫檔，避免把 writer logic
  塞進 context。
- `OutputArtifactProvider` 提供 output run directory preparation、
  precondition check 與 `map-error.md` rendering。

### 4. Refactor：穩定 API 與型別

- 維持函式短小，避免 provider-specific 分支。
- 保持 `mypy --strict` 可通過。
- 不把 log 當作 error contract。
- 不增加 runtime dependency。

### 5. 驗證與報告

- 執行 targeted unit tests。
- 執行 targeted integration tests。
- 執行完整 pytest、ruff、mypy。
- 新增 Phase6 report，記錄實作邏輯、步驟、測試方式、遇到的問題與
  測試結果。

## 安全注意事項

- `map-error.md` 不應包含 secret value。
- precondition 只讀 project path metadata，不掃描專案內容。
- output directory 是 report artifact，不可成為下一次 scan 的 source of
  truth。
