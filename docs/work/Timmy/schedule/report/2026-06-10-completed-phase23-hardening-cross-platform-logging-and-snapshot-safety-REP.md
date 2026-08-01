# 2026-06-10 Completed Phase 23 Hardening Cross-platform Logging Snapshot Safety Report

## 實作邏輯

- Phase 23 不是新增大型產品功能，而是替 Epic 1 backend baseline 補 release-readiness 防線：cross-platform path、snapshot secret safety、structured logging、target/path validation 與 local API resource limit。
- Cross-platform path 改用共用 helper 集中處理，避免各 provider 散落 `replace("\\", "/")` 或直接用 host `Path()` 誤解 Windows-style path。
- Snapshot scanner 不新增 Syrupy dependency，先用 dependency-free helper 掃 JSON-like data 與 Markdown/text，並復用既有 `SecretMaskingService`。
- Structured logging 保持 stdlib logging-compatible，透過 `event_data` 放結構化欄位，並在 log 前遮蔽 secret 與本機絕對路徑。
- Local API hardening 以外層 CORS wrapper 守住錯誤回應，並加入 request body size limit 與 stable masked 500 response。

## 步驟

1. 先更新 Task 23 plan，寫回 cross-platform path、snapshot safety、structured logging、local API hardening 的研究校正。
2. 依 TDD 寫出 RED tests：cross-platform path tests、snapshot safety contract tests、local API hardening tests、provider failure structured logging tests、schema path metadata contract。
3. 新增 `path_safety_service.py`，並接到 filesystem provider、code path scan、project scan 與 system map validation。
4. 新增 `snapshot_safety_service.py`，提供 `scan_text()`、`scan_json_like()` 與 fail-fast `assert_safe_text()`。
5. 新增 `logging_service.py`，提供 `safe_log_event()`，讓 provider failure log 不輸出 raw exception message、secret 或 local path。
6. 新增 `web/middleware.py`，提供 request size limit 與 masked unhandled exception response。
7. 調整 `create_app()`：FastAPI inner app 保留 routes / state，外層用 CORS wrapper 包住，確保 413 / 500 在 allowlisted Origin 下仍有 CORS header。
8. 補 Pydantic model path field description，並用既有 schema generator 重新產生 `schemas/ai-system-map.v1.schema.json`。
9. 更新 `docs/API-GUIDE.md` 與 Task 23 plan 的實作紀錄 / 驗收對照。

## 測試方式

- `.venv/bin/pytest tests/contracts/test_ai_system_map_schema.py::test_schema_documents_project_relative_posix_path_fields tests/contracts/test_ai_system_map_schema.py::test_checked_in_schema_matches_pydantic_generated_schema tests/contracts/test_secret_snapshot_safety.py tests/unit/core/test_cross_platform_paths.py tests/web/test_local_api_hardening.py -q`
- `.venv/bin/pytest tests/contracts/test_ai_system_map_schema.py tests/contracts/test_secret_snapshot_safety.py tests/unit/core/test_cross_platform_paths.py tests/unit/core/test_project_scan_service.py tests/web/test_local_api_hardening.py tests/web/test_map_routes.py -q`
- `.venv/bin/ruff check .`
- `.venv/bin/ruff format --check .`
- `.venv/bin/mypy src tests`
- `.venv/bin/pytest`

## 遇到的問題與解法

- Symlink path regression：一開始用 resolved path 計算 relative path，會把 project 內的 symlink 檔名解析到 project 外，導致既有 skip flow 中斷。解法是對 host absolute path 先嘗試 lexical `relative_to(project_root)`，必要時才 fallback resolve。
- CORS middleware introspection regression：外層 CORS wrapper 後，測試不能再只看 FastAPI inner middleware stack。解法是改測 wrapper 的 `allowed_origins` 與實際 response header。
- Schema contract 字串大小寫太死：Pydantic description 寫成 `Project-relative POSIX path`，測試原本硬比 `project-relative POSIX`。解法是改成 case-insensitive 檢查核心語意。
- 最終格式驗收第一次發現 `src/systograph/core/services/path_safety_service.py` 與 `tests/contracts/test_secret_snapshot_safety.py` 需要 ruff format。解法是只對這兩個檔案跑 formatter，並重跑 focused tests、ruff、mypy、full pytest。

## 測試結果

- Phase23 focused regression tests：41 passed。
- ruff check：All checks passed。
- ruff format --check：第一次發現 2 files would be reformatted；格式化後重跑為 150 files already formatted。
- mypy：Success，136 source files 無 issue。
- 全套 pytest：422 passed。

