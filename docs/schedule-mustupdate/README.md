# schedule-mustupdate 目錄規則

本目錄集中管理進度相關文件，所有內容均限定在 `docs/schedule-mustupdate` 之下。每個子資料夾的用途與命名方式如下。

## 1. `codex-review/`
- 存放稽核、真實進度檢查與補救建議，例如 `phase2_testing_optimization_todo.md`。
- 命名無日期限制，但應能直接看出檔案目的（如 `PHASE1_REALITY_CHECK.md`）。
- 檔案內容只描述問題、佐證與建議，不在此目錄寫 TODO／報告。

## 2. `plan/`
- `plan/finish/`：保存已結案或已發布的完整計畫（例如 `phase1_architecture_refactor.md`）。
- `plan/unfinish/`：保存尚未完成或需補完的計畫（例如 `phase1-1-services-integration.md`、`phase2_testing_optimization.md`）。
- plan 目錄僅描述「要做什麼」與「為什麼要做」，不記錄執行紀錄。

## 3. `todo/`
- 每日彙整待辦，命名規則為 `YYYY-MM-DD-todo.md`，例如 `2025-11-05-todo.md`。
- 若同日有多個任務，請寫在同一份文件的不同章節內。
- 檔案內容包含任務來源（對應的 plan 或 codex-review）、待辦清單、驗收標準與狀態。

## 4. `report/`
- 每日彙整完成紀錄，命名規則為 `YYYY-MM-DD-report.md`。
- 每份報告會依序收錄當日所有完成的 TODO/計畫成果，章節標題使用原始檔名方便追蹤。
- 若有摘要、日誌或補充，也集中在同一份 report 內。

## 5. 工作流程
1. 依 `plan/` 與 `codex-review/` 的內容確認需求。
2. 將實際要執行的事項寫入當日 `todo/YYYY-MM-DD-todo.md`。
3. 執行完成後，把成果補進 `report/YYYY-MM-DD-report.md`，並更新相關 plan 狀態。
4. 若有新問題或需重新評估，將分析寫回 `codex-review/` 或新的 plan 檔案。

> 只要遵守以上規則，所有進度相關文件都可以在本目錄清楚溯源。EOF
