# Test Regression Verification Report

## 結論

本次測試整理已完成。最終共有 850 個測試全數通過，branch coverage 為 89.90%，高於
85% regression floor；Ruff、Mypy、lockfile、shell syntax、sdist/wheel build 與 diff whitespace
檢查全部通過。CLI 成功／錯誤路徑與 live FastAPI import → scan → detail scan 也已實際操作
驗收。

本次沒有修改 `src/` production code。新增與調整的是測試、pytest/coverage 設定、dev
dependency、API trace scripts 的 macOS Bash 3.2 相容性，以及 TODO/Report/Plan 路徑同步。
沒有未解的相關或非相關測試失敗。

## 實作邏輯

- 以完整 suite、marker count 與 branch coverage 驗證，不以 focused green 代替完成。
- 以真實 CLI 與 localhost FastAPI process 驅動主要 surface，確認 artifact、HTTP response、
  child build 與 graph projection 都能實際產生。
- 手動 QA 發現錯誤時先重現與定位，再寫 regression contract；不以改測試預期掩蓋 runtime
  failure。
- 遵守不使用 subagent 的約束，以單代理完成 goal、QA、code quality、security 與 repository
  context 五個面向的最終審核。

## 步驟

1. 執行 unit、integration、contract 與 CLI/Web/E2E/smoke 分層測試。
2. 執行全量 pytest 與 branch coverage，確認 marker 總數等於全量 collection。
3. 執行 Ruff、Mypy、`uv sync --frozen`、`uv lock --check`、`git diff --check`、所有 shell
   script 的 `bash -n`，並建立 sdist/wheel。
4. 在 temporary directory 執行 CLI `--help`、map 成功路徑與 missing-project 錯誤路徑。
5. 以 temporary state/output 啟動 uvicorn，透過 curl 完成 import、system scan 與 detail scan，
   最後確認 process 與暫存檔均清除。
6. 重讀 mission 與完整 diff，檢查 production scope、secret/debug 殘留、舊測試路徑引用及
   文件一致性。

## 最終測試方式與結果

### 分層測試

- `pytest -q -m unit`：`662 passed, 188 deselected in 10.04s`。
- `pytest -q -m integration`：`70 passed, 780 deselected in 7.32s`。
- `pytest -q -m contract`：`36 passed, 814 deselected in 2.62s`。
- `pytest -q -m 'cli or web or e2e or smoke'`：`82 passed, 768 deselected in 14.73s`。
- 四層合計：662 + 70 + 36 + 82 = 850，沒有漏收或重複分類。

### 全量與 coverage

- `pytest -q`：`850 passed in 21.13s`。
- `pytest -q --cov --cov-report=json:coverage.json`：
  `850 passed in 27.27s`，精確 coverage 89.90%。
- coverage 明細：9,420 statements、680 missing lines、2,410 branches、439 partial branches。
- coverage gate：85% floor，exit 0。

### 靜態、相依與封裝

- `.venv/bin/ruff check src tests`：通過。
- `.venv/bin/mypy src tests`：259 個 source files，無問題。
- `uv sync --frozen` 與 `uv lock --check`：通過；pytest-cov 7.1.0、coverage 7.15.1。
- `git diff --check`：通過。
- 所有 `scripts/**/*.sh` 執行 `bash -n`：通過。
- `uv build`：成功建立 `systograph-0.1.0.tar.gz` 與
  `systograph-0.1.0-py3-none-any.whl`，輸出位於暫存目錄並已清除。

## Manual QA

### CLI

- `.venv/bin/systograph --help`：exit 0，正確顯示 commands/options。
- 對 `basic_qdrant_ollama_rag` 執行 `systograph map`：exit 0，產生 10 個 output files；
  `ai_system_map.json` 為 `ai-system-map/v1`，`profile_signals.json` 為
  `profile-signals/v1`，Markdown artifact 存在。
- 對不存在的 project path 執行 `systograph map`：exit 1，產生 `map-error.md`；沒有
  `ai_system_map.json` 或 `profile_signals.json` success artifacts。

### Live API

- 以隔離的 `SYSTOGRAPH_STATE_DIR` 啟動 uvicorn，再由 trace script 透過 curl 執行。
- project import：成功取得 `project_id`。
- system scan：status completed，成功取得 source `build_id`。
- `POST /api/detail-scans`：HTTP 200，detail scan status completed，finding count 4。
- child build：`build_id` 與 source build 不同，viewer graph loaded，70 nodes、1 edge、
  8 relationships。
- 結束後 port 8000 沒有 listener；temporary state/output 均由 trap 清除。

## 遇到的問題以及解法

### macOS Bash 3.2 把全形標點解析進變數名

- 現象：第一次 live API trace 在 import 與 scan 成功後，於 detail scan 前失敗：
  `TARGET�: unbound variable`。
- 根因：macOS 內建 GNU Bash 3.2 在 `set -u` 下，會把 `$TARGET` 後緊接的全形右括號誤認
  為變數名的一部分；同類 unbraced interpolation 共 7 處。
- Red：新增 shell portability contract 後，明確列出 7 個 offenders 並失敗。
- Fix：全部改為 `${VAR}`，沒有改 API payload 或 business behavior。
- Green：contract `1 passed`、所有 scripts `bash -n` 通過、Bash 3.2 最小重現通過；重跑同一
  live API trace 後完整 HTTP 200，server cleanup 通過。

### 最終 Ruff gate 發現 import block formatting

- 現象：新 portability contract 多一個空白行，Ruff I001 失敗。
- 解法：依 Ruff diff 移除多餘空白行；重跑 Ruff、Mypy、focused contract 與 full coverage
  全部通過。

## 三個 Runtime 假設與證據

1. **Marker hook 可能漏標或重複分類**：反證。四個互斥 layer 實跑分別為 662、70、36、
   82，合計與 full collection 850 完全一致；全量測試亦為 850 passed。
2. **新增測試可能只證明 mock，而非真實 artifact/API lifecycle**：反證。CLI 真實 process
   產生可解析 map/profile artifacts；live uvicorn + curl 產生 source/child builds 並成功載入
   graph projection。
3. **Python suite 全綠仍可能漏掉 macOS shell runtime failure**：證實。第一次 live trace
   實際在 Bash 3.2 失敗；`${VAR}` 修正與 portability contract 後，同一流程成功且 process
   正常清除。

## 最終審核

- Goal／constraints：四個階段 TODO 與 Report 均存在；Context7 pytest 官方實踐與 R2R
  test layout 比對已記錄；未使用 subagent。
- Code quality：集中 marker hook 取代逐檔 decorator；manifest 測試搬到真實 integration
  boundary；沒有新增無用 abstraction 或 production workaround。
- Security：scanner/API QA 只讀既有 fixture 並寫入 temporary directory；沒有新增 secret、
  token 或完整敏感值；跨 project 404 concealment 測試保留 fail-closed contract。
- Context：active Plan 13 的 manifest test path 已同步；全 repo 搜尋沒有舊 unit path 引用。
- Cleanup：coverage/debug journal、build、CLI/API state/output 與 server process 均不保留。

## 驗收對照

- 測試整理：完成，可透過 7 個正式 markers 選取。
- Unit Test／Integration Test 補齊：完成；新增案例集中在 loader validation、artifact
  lifecycle、CLI/API failure contract 與 shell portability。
- 所有測試通過：完成，850/850。
- Context7 與參考專案：完成，決策記錄於 baseline/infrastructure reports。
- 分階段 TODO／Report：完成，共 4 個 TODO 與 4 個 Report。
- 相關錯誤修正：完成；live QA 發現的 macOS Bash 3.2 failure 已 TDD 修正。
- 非相關錯誤：無。

## 剩餘風險

- 本輪在 macOS 26.5.1／Python 3.11 環境驗收，沒有使用實體 Windows host；Python CLI 使用
  `pathlib` 且現有 suite 通過，但 Windows runtime 仍應由 CI matrix 持續驗證。
- coverage floor 是 regression guard，不代表所有未來 Plan 13 failure mode 已完成；新 contract
  或 production branch 仍應依 release-readiness 風險補測。
