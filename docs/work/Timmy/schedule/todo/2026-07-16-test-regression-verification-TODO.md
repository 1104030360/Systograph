# Test Regression Verification TODO

## 目標

以新環境中的完整命令與實際使用情境驗收整理結果，確認測試、型別、lint 與主要使用介面
同時成立。

## 實作邏輯

- focused green 不是完成；必須重新執行全量 suite 與 production quality gates。
- CLI 要實際執行 `--help`、成功路徑與錯誤路徑；API 若本次觸及則以 live process + curl
  驗證。
- 最終只保留必要 source/test/docs 變更，移除 coverage 與 debug 暫存產物。

## 步驟

- [x] 執行所有分層測試與完整 pytest。
- [x] 執行 coverage、`ruff check src tests`、`mypy src tests`、`git diff --check`。
- [x] 執行 CLI `--help`、一個成功案例與一個錯誤案例。
- [x] 啟動隔離的 FastAPI process，以 curl 驗證 import → scan → detail scan。
- [x] 以 red-green 修正 macOS Bash 3.2 trace script portability failure。
- [x] 以三個 runtime 假設逐項附上觀測證據。
- [x] 清理暫存產物、重讀 mission、完成最終 Report 與驗收對照。
