# 2026-06-01 Phase6 Precondition and Output Policy Report

## 實作摘要

本階段依照 `06-implement-precondition-and-output-policy.md` 實作 Stage 1
precondition check 與 output directory policy。

本次重點是把「是否能安全開始掃描」從後續 provider pipeline 前面切乾淨：

- 檢查 `project_path` exists、is directory、readable。
- 檢查 output directory 可建立、可寫入。
- output artifacts 已存在時不覆寫，改用 timestamped run directory。
- timestamped run directory 已存在時使用 deterministic suffix，避免同秒
  重複執行重用舊 run directory。
- 新增薄的 `OutputRun` context，集中保存本次 scan 的 resolved artifact
  paths。
- fatal precondition error 使用 structured `PreconditionError` 表示。
- `map-error.md` 由 `PreconditionError` render，不由 AI 產生，也不從 log
  反推。
- 本階段不輸出 `map-error.json`。
- 不跑 provider，不建立 full `ai_system_map.json`。

## 實作邏輯

依照 TDD + BDD 方式執行：

1. 先建立 Phase6 TODO，明確拆分 Red / Green / Refactor / 驗證。
2. 新增 unit contract tests，定義 missing project、file path、unreadable
   project、readable project、error markdown writer、timestamped output
   directory 行為。
3. 新增 BDD-style integration tests，覆蓋 missing project 只產生
   `map-error.md`，以及既有 outputs 不被覆寫。
4. 執行 targeted tests，確認 RED：測試因缺少 `PreconditionError` 與
   `OutputArtifactProvider` 失敗。
5. 新增 structured error / scan models。
6. 新增 `OutputArtifactProvider`，集中處理 output directory policy 與
   `map-error.md` rendering。
7. 執行 targeted tests、完整 pytest、ruff、mypy。

核心設計決策：

- `PreconditionFailureReason` 使用 enum，避免 error reason 變成散落字串。
- `PreconditionError` 是錯誤來源的 structured object。
- `OutputRun` 是本次 scan 的 output context，只保存 artifact path：
  `map_error_path`、`map_json_path`、`map_markdown_path`。
- `OutputArtifactProvider` 保持 stateless，writer method 使用 resolved
  `OutputRun`，不再要求呼叫端重複傳 raw `output_dir`。
- `map-error.md` 是正式使用者可讀 artifact，但不是 canonical map。
- `map-error.json` 暫不落地，避免提前增加公開 failure contract。
- JSON 與 Markdown 若未來並列輸出，必須來自同一個 structured error
  object。
- `OutputArtifactProvider` 只負責 artifact policy，不掃 project files。
- timestamp 由 injectable clock 產生，測試不依賴真實現在時間。
- timestamp collision 使用 `-1`、`-2` 這類 deterministic suffix，不重用
  既有 run directory。
- path 全部使用 `pathlib.Path`。

## 實作步驟

### 1. 建立 TODO

新增：

- `docs/work/Timmy/schedule/todo/2026-06-01-phase6-precondition-output-policy-TODO.md`

內容包含：

- 實作邏輯
- TDD / BDD 階段拆分
- 安全注意事項
- 驗證計畫

### 2. 建立 unit contract tests

新增：

- `tests/unit/core/test_precondition_output_policy.py`

測試覆蓋：

- missing project 回傳 fatal `PreconditionError`
- project path 是檔案時回傳 `project_path_not_directory`
- unreadable project path 回傳 `project_path_not_readable`
- readable project path 成功時回傳 normalized root
- `map-error.md` 由 structured error object render
- 既有 `outputs/ai_system_map.json` 不被覆寫，改用 timestamp directory
- timestamp directory collision 時改用 deterministic suffixed directory

### 3. 建立 BDD-style integration tests

新增：

- `tests/integration/test_phase6_precondition_output_policy_behaviors.py`

測試情境：

- missing project 只寫出 `outputs/map-error.md`
- missing project 不寫出 `ai_system_map.json` 或 `ai_system_map.md`
- outputs 已存在時保留舊 artifact，新的 run directory 使用 deterministic
  timestamp
- timestamp 已存在時，新的 run directory 使用 deterministic suffix

### 4. 建立 structured models

新增：

- `src/kai_mind/core/models/errors.py`
- `src/kai_mind/core/models/scan.py`

主要型別：

- `PreconditionFailureReason`
- `PreconditionError`
- `OutputRun`
- `PreconditionResult`

### 5. 建立 OutputArtifactProvider

新增：

- `src/kai_mind/core/providers/__init__.py`
- `src/kai_mind/core/providers/output_artifact_provider.py`

主要 API：

- `check_preconditions(project_path: Path, output_dir: Path)`
- `prepare_output_run(output_dir: Path)`
- `prepare_output_run_dir(output_dir: Path)`
- `write_map_error(error: PreconditionError, output_run: OutputRun)`

## 測試方式

RED 階段執行：

```bash
.venv/bin/pytest tests/unit/core/test_precondition_output_policy.py tests/integration/test_phase6_precondition_output_policy_behaviors.py
```

結果符合預期：

```text
ModuleNotFoundError: No module named 'kai_mind.core.models.errors'
ModuleNotFoundError: No module named 'kai_mind.core.providers'
```

GREEN / 完整驗證執行：

```bash
.venv/bin/pytest tests/unit/core/test_precondition_output_policy.py tests/integration/test_phase6_precondition_output_policy_behaviors.py
.venv/bin/ruff check .
.venv/bin/mypy
.venv/bin/pytest
```

## 測試結果

```text
targeted phase6 tests: 8 passed
ruff: All checks passed
mypy: Success, no issues found in 30 source files
pytest: 91 passed
```

## 遇到的問題與解法

### 問題 1：sandbox 無可用 temporary directory

現象：

- read-only sandbox 執行 pytest 時，pytest capture 需要 temporary file，
  啟動階段失敗。

解法：

- 依執行環境限制改用 escalated command，讓 pytest 可以使用系統 temp
  directory。
- targeted RED、targeted GREEN 與完整 pytest 都在可寫 temp directory 的
  環境重新執行。

### 問題 2：phase6 prompt 的 unit / integration 目錄描述互相顛倒

現象：

- prompt 文字提到整合功能測試先寫在 `tests/unit`，單元測試寫在
  `tests/integration`。
- 這與目前 repo 慣例相反。

解法：

- 依現有專案慣例與 pytest 結構，unit tests 放 `tests/unit`，
  BDD-style integration tests 放 `tests/integration`。
- 避免為單一 phase 製造反直覺的測試目錄規則。

### 問題 3：`map-error.md` 是否要先從 JSON file render

現象：

- 設計討論中確認目前不需要 `outputs/map-error.json`。

解法：

- 程式內部保留 structured `PreconditionError`。
- `map-error.md` 從 structured object render。
- 若未來需要 machine-readable failure artifact，再由同一個
  `PreconditionError` 同時輸出 `map-error.json` 與 `map-error.md`。

### 問題 4：timestamped run directory 可能同秒 collision

現象：

- Review 指出 timestamp 只有秒級精度。
- 若 `outputs/ai_system_map.json` 已存在，且 `outputs/YYYYMMDDTHHMMSS`
  也已存在，舊寫法會因 `mkdir(..., exist_ok=True)` 重用該目錄。
- 後續 writer 可能覆寫前一次 run 的 artifact，違反 output policy。

解法：

- 新增 failing test 覆蓋 timestamp collision。
- `prepare_output_run_dir()` 改成先找唯一 timestamped run directory。
- 若 `20260601T093000` 已存在，依序嘗試 `20260601T093000-1`、
  `20260601T093000-2`。
- 不重用既有 run directory。

## Task 6 驗收對照

| Task 6 項目 | 結果 |
|---|---|
| 建立 precondition result/error models | 已完成：`PreconditionResult`、`PreconditionError`、`PreconditionFailureReason` |
| 建立 output run context | 已完成：`OutputRun` 保存 resolved artifact paths |
| 檢查 project path exists | 已完成：`project_path_not_found` |
| 檢查 project path is directory | 已完成：`project_path_not_directory` |
| 檢查 project path readable | 已完成：`project_path_not_readable` |
| 決定 output run directory | 已完成：`prepare_output_run_dir()` |
| outputs 已有 artifact 時建立 timestamped subdirectory | 已完成：`20260601T093000` deterministic clock test |
| timestamped run directory collision 不覆寫舊 run | 已完成：collision 時使用 `20260601T093000-1` |
| fatal precondition error 只輸出 `map-error.md` | 已完成：BDD test 確認不產生正常 map |
| `map-error.md` 包含 `project_path`、`failure_reason`、`scan_stage` | 已完成 |
| `map-error.md` 由 structured object render | 已完成 |
| writer 不重複接收 raw `output_dir` | 已完成：`write_map_error()` 使用 `OutputRun` |
| 既有 `outputs/ai_system_map.json` 不被覆寫 | 已完成 |
| timestamp directory 命名 deterministic 可注入 clock 測試 | 已完成 |
| Windows/macOS path 使用 `pathlib` | 已完成 |
| output directory 不作為下一次 scan source of truth | 已遵守：provider 只處理 artifact policy |

## 後續提醒

- Phase7 的 filesystem inventory 應使用這裡的 successful
  `PreconditionResult.project_root`，不要重新定義 precondition 行為。
- 未來若新增 CLI `--format json` 或 CI machine-readable failure contract，
  再新增 `map-error.json`，不要讓 Markdown parse 成為 machine contract。
