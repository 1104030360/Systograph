# 2026-06-10 Phase 23 Hardening TODO

## 實作邏輯

Phase 23 的重點不是新增大型功能，而是把已完成的 Epic 1 backend baseline 補上防線：路徑輸出要跨平台穩定、snapshot/test artifact 不可留下完整 secret 或本機絕對路徑、provider failure log 要結構化且安全、local API 要能拒絕過大的 request 且錯誤回應不可洩漏 raw path/secret。

本階段採 TDD + BDD：先寫可讀的行為測試，確認紅燈後才補 production code。驗收時跑 focused tests、ruff、mypy 與完整 pytest。

## 步驟

1. 校正 Task 23 plan
   - 對照目前 `src/`、`tests/`、`schemas/` 與官方/一手來源。
   - 將 path、snapshot、structured logging、CORS/resource limit 的研究結論寫回 plan。
   - 修正不精準說法，例如 `Path(path).as_posix()` 無法可靠處理非本機平台語意的 Windows path 字串。

2. Cross-platform path safety
   - 先補 `tests/unit/core/test_cross_platform_paths.py`。
   - 建立共用 path helper，輸出 project-relative POSIX path。
   - 讓 filesystem provider、detail/code-path resolver、schema validator 使用同一套 path 判斷。

3. Snapshot secret safety
   - 先補 `tests/contracts/test_secret_snapshot_safety.py`。
   - 建立 dependency-free snapshot scanner helper，掃描 JSON/Markdown/snapshot-like text。
   - 偵測完整 secret、本機 workspace 絕對路徑與 Windows-style 絕對路徑。

4. Structured logging safety
   - 先補 provider failure logging 測試。
   - 建立 `logging_service.py` 或等價 helper，輸出結構化 event 並遮蔽敏感欄位。
   - provider crash log 不輸出完整 secret 或本機絕對路徑。

5. Local API hardening
   - 先補 `tests/web/test_local_api_hardening.py`。
   - 增加 request size middleware，過大 request 回 413。
   - 確保 413 / 500 類錯誤在有 Origin 時仍帶 CORS header。
   - 錯誤 detail 不包含 raw path 或 secret。

6. 文件與驗收
   - 更新 `docs/API-GUIDE.md` 的 local API safety / request size 說明。
   - 更新 Task 23 plan 的 implementation notes / acceptance status。
   - 建立 phase23 report，記錄測試方式、遇到問題與結果。

