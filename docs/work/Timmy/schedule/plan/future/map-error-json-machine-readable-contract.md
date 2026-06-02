# Future: map-error.json Machine-Readable Failure Contract

## 來源
Task 6 (Implement Precondition and Output Policy) 明確提到：

> 不在本任務輸出 `map-error.json`；若未來 CLI/CI 需要 machine-readable failure contract，再新增 `outputs/map-error.json`。

> 若未來新增 `map-error.json`，它應與 `map-error.md` 來自同一個 structured error object，避免兩份輸出內容漂移。

## 目的
為 CLI/CI pipeline 提供 machine-readable 的 scan failure contract。目前只有 `map-error.md` 供人類閱讀，但自動化流程需要 JSON 格式的結構化錯誤報告。

## 觸發條件
- CLI/CI pipeline 需要程式化判斷 scan failure 原因與類型。
- 需要在 CI/CD gate 中自動解析 precondition failure。
- 需要跨工具串接 scan error 結果。

## 設計約束
- `map-error.json` 必須與 `map-error.md` 來自同一個 `PreconditionError` structured object。
- 不可讓兩份輸出各自獨立 render，避免內容漂移。
- JSON schema 必須 backward-compatible 或有 migration note。

## 與既有任務關係
- Task 6：已建立 `PreconditionError` model 與 `map-error.md` writer。
- Task 16：`MapBuildService` 與 local web API 可作為 JSON error output 的整合點。
- Task 23：hardening 階段可一併驗證 JSON/Markdown error output 一致性。

## 不做事項
- 不取代 `map-error.md`，兩者共存。
- 不做 GUI error rendering（由 Task 18 或後續 frontend 處理）。
