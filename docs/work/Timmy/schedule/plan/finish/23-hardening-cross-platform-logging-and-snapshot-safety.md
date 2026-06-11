# Task 23: Hardening Cross-platform Paths, Logging, and Snapshot Safety

## 目標
補強 Epic 1 backend 的 cross-platform path、structured logging、snapshot secret safety、target validation 與 release-readiness review gaps。這是 baseline 功能完成後的品質收斂任務。

## 為什麼要先做這個
設計文件與 AGENTS.md 都要求 Windows/macOS path、secret-safe snapshots、scanner tests、evidence-based findings。功能完成後若不做 hardening，很容易在 review 時出現 P1。

## 承接 Task 16 延後功能
- 承接 Task 16 中未集中處理的 cross-platform path、structured logging、snapshot safety、API resource limits hardening。
- Task 16 只要先守住 basic local-only / CORS / no raw secret；本任務要用更完整的 tests 與 helpers 收斂品質。
- 本任務也要回頭檢查 Task 17-22 新增 artifact/API/event 是否符合同一套 path、masking、logging、validation policy。
- 若 Task 25/26 已排入後續，本任務要在 docs 補上 upload/session store 的安全前置要求。

## 前置需求
- Task 16 已完成 end-to-end map build。
- Task 21/22 已完成 progressive scan/query trace。
- Task 5 secret masking 已全域接入。

## 實作範圍
- Cross-platform path tests。
- Snapshot secret scanner。
- Structured logging events。
- Provider failure structured warnings。
- Validation hardening：dangling references、invalid target、unmasked secret pattern。
- Local API hardening：CORS allowlist、local-only bind、request size/resource limit、error response 不含 raw path/secret。
- Docs update：開發命令與 known limitations。

## 不包含範圍
- 不新增大型 feature。
- 不改 JSON schema breaking fields，除非另有 migration note。
- 不做 full security scanner。
- 不做 packaging/launcher。

## 建議實作步驟
1. 建立 cross-platform path fixtures。
2. 補測 Windows-style input -> POSIX evidence path。
3. 建立 snapshot scanner helper，掃描 JSON/Markdown snapshot 是否含 fake full secret。
4. 加入 structured logging wrapper 或 helper。
5. 確認 logs 不輸出 full secret。
6. 補 target validation tests。
7. 補 local API resource limit / error masking tests。
8. 更新 docs 或 README 的 backend test commands。

## 預期輸出
- `tests/contracts/test_secret_snapshot_safety.py`
- `tests/unit/core/test_cross_platform_paths.py`
- `tests/web/test_local_api_hardening.py`
- `src/kai_mind/core/services/logging_service.py` 或等價 helper
- 更新相關 tests/docs

## 2026-06-10 研究校正與最佳實踐

### Cross-platform paths

**結論：研究方向正確，但實作細節需修正。**

- Checkov 是可參考的 scanner 類專案；其 README 說明它是 IaC / container image / package 的 static analysis / SCA scanner，與 KAI-Mind 的 read-only scanner 形態相近：`https://github.com/bridgecrewio/checkov`
- Checkov Windows issue 顯示跨 drive / path normalization 真的會造成 Windows failure，且該 issue 中 output path 被註解為應該維持 Unix path：`https://github.com/bridgecrewio/checkov/issues/1949`
- Python `pathlib` 官方文件指出 `Path` 會使用目前作業系統語意；如果要在 Unix/macOS 上處理 Windows path，應使用 `PureWindowsPath`，而 `PurePath.as_posix()` 才是把 path 轉成 forward slash 的語意化 API：`https://docs.python.org/3/library/pathlib.html`

需要修正的點：

- 不應寫成「一律在最終序列化前呼叫 `pathlib.Path(path).as_posix()`」。在 macOS/Linux 上，`Path("src\\api.py")` 會被當成單一 POSIX filename，不會理解 `\` 是 Windows separator。
- 正確做法是建立共用 path helper：先判斷輸入是本機 `Path`、POSIX-style relative path，還是 Windows-style path，再用 `PurePosixPath` / `PureWindowsPath` 做語意化 normalize。
- `replace("\\", "/")` 不應散落各處當主要實作；若某些 git / subprocess output 已確認是安全 relative path，可以在 helper 內做最後防線，但不能讓各 provider 自己重複替換。
- `ai-system-map.v1.schema.json` 可增加 non-breaking description，說明 `Evidence.file`、`CodePathStep.file` 等 path 欄位必須是 project-relative POSIX path，不可含 drive、UNC root、`..` 或本機絕對路徑。

### Snapshot secret safety

**結論：Syrupy 值得參考，但本任務不應為了 hardening 強加新 dependency。**

- Syrupy 官方 repo 說明它是 pytest snapshot plugin，適合 asserted snapshot immutability：`https://github.com/syrupy-project/syrupy`
- Syrupy matcher 文件支援以 path / value type 取代 snapshot 中不穩定或敏感的值，可作為未來 snapshot framework 的參考：`https://github.com/syrupy-project/syrupy`
- 目前 repo 沒有使用 Syrupy；Phase 23 應先用 dependency-free snapshot scanner helper，直接掃描 JSON / Markdown / snapshot-like artifacts 是否含完整 secret 或本機 workspace 絕對路徑。

需要修正的點：

- 不應限定「path 結尾為 secret 或 api_key 才遮蔽」。secret 可能出現在任意字串、log text、Markdown、JSON nested value、Authorization header 或 provider error message。
- 應復用既有 `SecretMaskingService` 的 token/key-value policy，並額外加入 workspace path / Windows absolute path 偵測。
- Snapshot scanner 應提供 fail-fast result，讓 contract test 能故意放入 fake full secret 並驗證會被抓到。

### Structured logging

**結論：processor chain 的概念正確，但本 repo 應採 stdlib logging-compatible helper，不直接引入 structlog。**

- structlog 官方文件的 processor chain 概念適合集中處理 event dict 與過濾：`https://www.structlog.org/en/stable/processors.html`
- OWASP Logging Cheat Sheet 明確要求 access tokens、passwords、connection strings、encryption keys、敏感個資等不應直接寫入 log，應移除、遮蔽、sanitize、hash 或加密：`https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html`
- pytest 官方 `caplog` fixture 可用於驗證 log record 與 log text，且要避免測試中重設 root logger 導致 caplog 失效：`https://docs.pytest.org/en/stable/how-to/logging.html`

需要修正的點：

- 不應把 logging 設定集中到 `src/kai_mind/core/configs/`；目前 repo 的 logging 使用點在 service 層，Phase 23 應先建立小型 `logging_service.py` helper，避免大規模重構。
- Key-based masking 是第一層，但不能完全取代 pattern-based masking。現有 `SecretMaskingService` 已同時支援 key-value 與常見 token pattern，structured log helper 應復用它。
- Provider failure log 應記錄 `event`、`stage`、`provider`、`exception_type`、`frame_count` 等結構化欄位；不記錄完整 secret、raw exception message 或本機絕對 path。

### Local API hardening

**結論：CORS / resource-limit 方向正確，但原研究的 allowlist 寫法與 middleware 順序描述需修正。**

- Starlette 官方文件建議若要讓 unhandled exception 產生的 error response 也帶 CORS header，應以 `CORSMiddleware` 包住整個 Starlette/FastAPI app：`https://starlette.dev/middleware/`
- FastAPI 官方 CORS 文件說明 `allow_origins` 是明確 origin list；若 `allow_credentials=True`，`allow_origins`、`allow_methods`、`allow_headers` 不能使用 `["*"]`：`https://fastapi.tiangolo.com/tutorial/cors/`
- OWASP API Security API4:2023 建議對 incoming parameters / payloads 定義並強制最大尺寸，避免 unrestricted resource consumption：`https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/`
- Langflow issue 可作為「AI/FastAPI 類工具曾發生 CORS header 格式/設定 regression」的佐證，但它不是 413/CORS 包裝問題的直接證據：`https://github.com/langflow-ai/langflow/issues/10283`

需要修正的點：

- `allow_origins=["http://localhost:*", "http://127.0.0.1:*"]` 不是 FastAPI 的 literal origin list 寫法；若真的需要 wildcard port，應用 `allow_origin_regex`。本 repo 目前先維持明確 `5173` allowlist，避免 local-only API 被任意 origin 呼叫。
- 不能依賴「第一個 `add_middleware()` 就是最外層」這種口訣；實際 Starlette stack 需用測試守住。若要保證 500 / 413 也帶 CORS，應採全域 CORSMiddleware wrapper 或等價的明確 stack。
- Error masking 要同時處理 secret 與 raw local path；前端應看到 stable error code，例如 `request_too_large`、`internal_server_error`，而不是 Python exception string。

## 驗收標準
- Windows/macOS path tests 通過。
- snapshot scanner 可抓到故意放入的 fake full secret。
- logs 只記錄 stage/count/id，不記錄 raw values。
- release-readiness review 沒有 scanner test gap。

## 2026-06-10 實作紀錄與驗收狀態

### 已採用做法

- Cross-platform path：新增共用 `path_safety_service.py`，集中處理 project-relative POSIX path normalize / validation / local path redaction，並接到 filesystem provider、code path scan、project scan 與 system map validation。
- Snapshot secret safety：新增 dependency-free `snapshot_safety_service.py`，復用既有 `SecretMaskingService`，可掃 JSON-like data 與 Markdown/text，抓出完整 secret 與本機絕對路徑。
- Structured logging：新增 stdlib logging-compatible `logging_service.py`，用 `event_data` 保存結構化欄位，並在寫 log 前遮蔽 secret 與 local path。
- Provider failure structured warnings：project scan provider failure log 改為 `provider_failure` event，記錄 `stage`、`provider`、`exception_type`、`frame_count`，不記錄 raw exception message。
- Local API hardening：`create_app()` 改為外層 CORS wrapper，加入 request size limit middleware 與 stable masked 500 middleware；413 / 500 在 allowlisted Origin 下仍保留 CORS header。
- Schema metadata：`Evidence.file`、`CodePathStep.file` 的 JSON schema description 補上 project-relative POSIX contract，屬 non-breaking metadata 更新。
- Docs：`docs/API-GUIDE.md` 補上 request size limit、stable masked error 與 CORS-on-error contract。

### 驗收對照

- Windows/macOS path tests：已由 `tests/unit/core/test_cross_platform_paths.py` 覆蓋 Windows-style relative path、POSIX validation、absolute / UNC / parent traversal rejection。
- Snapshot scanner：已由 `tests/contracts/test_secret_snapshot_safety.py` 覆蓋 fake full secret、本機 workspace absolute path、masked secret + POSIX relative path。
- Logs 不輸出 raw values：已由 `tests/unit/core/test_project_scan_service.py` 覆蓋 provider failure structured event，並驗證 secret / local path 不出現在 log text 與 event data。
- Local API hardening：已由 `tests/web/test_local_api_hardening.py` 覆蓋 oversized request 413、unhandled 500 masked response 與 CORS header。
- Schema path contract：已由 `tests/contracts/test_ai_system_map_schema.py` 覆蓋 checked-in schema 與 Pydantic generated schema 同步，並驗證 path 欄位描述。
- Release-readiness scanner test gap：本任務新增 contract / unit / web tests，避免 hardening 只靠文件宣告。

## 可能風險與注意事項
- 不要在 hardening task 順手重構所有 services。
- 若發現 schema 需要 breaking change，必須記錄 migration。
- 這一步主要是補防線，不是加產品功能。

## 新手提示
Hardening 是把已經能跑的功能變成比較不容易壞、比較不容易洩密、比較能跨平台工作的版本。

## 視覺化說明
```text
┌──────────────────────────────────────────────────────────┐
│ Existing Epic 1 backend baseline                         │
│ - scanner providers                                      │
│ - ai_system_map.json / Markdown                          │
│ - local FastAPI viewer API                               │
└──────────────┬────────────────────┬──────────────────────┘
               │                    │
               ↓                    ↓
┌──────────────────────────┐ ┌──────────────────────────────┐
│ Path safety helper        │ │ Snapshot safety scanner       │
│ - project-relative POSIX  │ │ - fake full secret detection  │
│ - no drive / UNC / ..     │ │ - workspace path detection    │
│ - shared validation       │ │ - JSON / Markdown / snapshots │
└──────────────┬───────────┘ └───────────────┬──────────────┘
               │                             │
               ↓                             ↓
┌──────────────────────────┐ ┌──────────────────────────────┐
│ Structured log helper     │ │ Local API hardening           │
│ - event/stage/provider    │ │ - CORS on error responses     │
│ - masked exception data   │ │ - request size limit / 413    │
│ - no raw local path       │ │ - masked stable error detail  │
└──────────────┬───────────┘ └───────────────┬──────────────┘
               │                             │
               └──────────────┬──────────────┘
                              ↓
┌──────────────────────────────────────────────────────────┐
│ Release-readiness hardening gate                         │
│ - focused RED/GREEN tests                                │
│ - contract tests                                          │
│ - ruff / mypy / full pytest                              │
└──────────────────────────────────────────────────────────┘
```
