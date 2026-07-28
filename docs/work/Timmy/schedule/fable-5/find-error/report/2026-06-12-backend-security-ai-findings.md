# Phase 1 Find-Error — 後端 / 資安 / 後端 AI / 資料庫 詳細發現

- 日期：2026-06-12 ／ 性質：只檢查與記錄，未修改功能程式碼
- 編號對應總覽報告 `2026-06-12-phase1-find-error-overview.md`
- 每項標注「repo 實際觀察」或「外部最佳實踐建議」

---

## C. 後端 AI / 資安（Critical）

### C-1：Secret masking 覆蓋度不足，明文機密寫進 `ai_system_map.json`（repo 實際觀察，已實跑驗證）

- 嚴重程度：**Critical**
- 來源引用：
  - 檔案：`src/systograph/core/services/secret_masking_service.py`
  - 位置：`SECRET_KEY_MARKERS`（第 10-17 行）、`KEY_VALUE_RE`（第 22-32 行）、`SECRET_PATTERNS`（第 42-86 行）
  - 證據：`SECRET_KEY_MARKERS = ("API_KEY","TOKEN","SECRET","PASSWORD","BEARER","AUTH")`；`SECRET_PATTERNS` 僅涵蓋 `sk-`/`gh[pousr]_`/`glpat-`/`xox`/AWS `AKIA`/Slack webhook/`Authorization: Bearer`/PEM。沒有任何 pattern 偵測 URL 內嵌帳密 `scheme://user:pass@host`；key marker 是子字串比對且含底線。
- 實跑驗證（`/tmp/systograph_verify/verify_findings.py`，2026-06-12）：

| 輸入 | `mask_value(key=key)` | `mask_json_like({key:value})` |
|---|---|---|
| `DATABASE_URL=postgresql://admin:SuperSecret123@db:5432/app` | ❌ 明文 | ❌ 明文 |
| `REDIS_URL=redis://:MyRedisPass@cache:6379/0` | ❌ 明文 | ❌ 明文 |
| `MONGODB_URI=mongodb://root:RootPass99@mongo:27017/db` | ❌ 明文 | ❌ 明文 |
| `DB_PASSWD=abc123SECRET` | ❌ 明文 | ❌ 明文 |
| `MYAPIKEY=sk-...` | ⚠️ 只因 `sk-` pattern 被部分遮罩 | ⚠️ 無底線 `APIKEY` marker 本身不命中 |
| `OPENAI_API_KEY=sk-...` | ✅ 遮罩 | ✅ 遮罩 |

  core subagent 另在 `/tmp` 沙箱跑完整 `MapBuildService().build()`，確認 `DB_PASSWD=...`、`DATABASE_URL=postgres://u:p@h/db`、`config.yaml` 的 `url: http://admin:pass@qdrant:6333` 等 case 會以明文出現在輸出 `ai_system_map.json`，掃描狀態仍回 `status: ok`。`CLIENT_SECRET` 這類名稱會因 `SECRET` 子字串而命中；真正漏的是 URL userinfo、`PASSWD` / `PWD`、無底線 `APIKEY` 等變體與短 secret 遮罩比例。
- 問題說明：`config_parse_provider`（第 206-236 行）、`docker_compose_provider._append_environment_fact`（第 311-335 行）都只呼叫同一個 `mask_value`+`mask_text`。遮罩規則漏掉的，evidence/fact/markdown/viewer projection 全部跟著漏。注意：預設 `systograph map` 流程不經 scan boundary review（那是 opt-in），所以 `.env` 是被直接讀取解析的。
- 為什麼需要改進：直接違反 `AGENTS.md`「不可在 logs/reports/test snapshots 印出完整 secret values」與產品核心承諾；明文 secret 寫進交付 JSON 後會被前端顯示、被 commit、被分享。
- 具體改善建議：
  1. `SECRET_KEY_MARKERS` 增補 `PASSWD`、`PWD`、`CREDENTIAL`、`PRIVATE_KEY`、`ACCESS_KEY`、`SESSION`、`COOKIE`。
  2. key marker 比對改為「正規化掉底線後」比對（讓 `MYAPIKEY` 命中 `APIKEY`）。
  3. 新增 `SECRET_PATTERNS`：URL 帳密 `\b[a-z][a-z0-9+.\-]*://[^/\s:@]+:(?P<value>[^/\s:@]+)@`，遮罩 password 群組；對 `config_value` 類 fact 額外對 URL userinfo 段遮罩。
- 重現方式：用 `SecretMaskingService().mask_json_like({"key":"DB_PASSWD","value":"abc123SECRET"})` 或含 `DATABASE_URL=postgres://u:p@h/db` 的 fixture 執行 `MapBuildService().build()`，觀察輸出 JSON 仍含明文。
- 建議測試方式：fixture 專案含上述四種 case，斷言 `ai_system_map.json` 不含明文；對 `mask_text` 增 parametrized 單元測試（`DB_PASSWD`、`MYAPIKEY`、URL 帳密、`CLIENT_SECRET` 作為已命中 regression）。
- 相關影響範圍：所有掃描輸出（JSON/Markdown/viewer/trace/proposal evidence）。

---

## H. 後端 / 資安 / AI（High）

### H-1：Query trace 缺 SSRF egress 控制（repo 實際觀察，已實跑驗證）

- 嚴重程度：**High**
- 來源引用：
  - 檔案：`src/systograph/core/providers/endpoint_call_provider.py`
  - 位置：`_endpoint_preflight_result`（第 141-165 行）
  - 證據：preflight 只做 `scheme = urlsplit(url).scheme.lower(); if scheme in {"http","https"}: return None`，完全沒有 host/IP 檢查。route 入口 `src/systograph/web/routes/trace_routes.py:47-53` 直接把 `endpoint_id` 對應的 `endpoint.value` 交給 provider 發 HTTP。`endpoint.value` 來自被掃描 repo（`EndpointDetectionService` 從 docker-compose published port / OpenAI base URL / Chroma client 等推導），`system_map.py` 對 `value` 無格式限制。
- 實跑驗證（`/tmp/systograph_verify/verify_findings.py`，2026-06-12）：`169.254.169.254`（AWS/Azure metadata）、`127.0.0.1:6379`、`10.0.0.5`、`192.168.1.1`、`[::1]:8000`、`metadata.google.internal` 全部「ALLOWED（would send request）」；只有 `file://`、`gopher://` 因非 http/https 被擋。另確認 `httpx.Client()` 預設 `follow_redirects=False`（redirect 攻擊面已關閉，是正面點）。
- 問題說明：使用者匯入惡意 repo → endpoint detection 產出 `value="http://169.254.169.254/latest/meta-data/..."` → opt-in trace 即對雲端 metadata / 內網發請求。回應 body 雖遮罩，但 `status`/`status_code`/`latency_ms`/`error_type` 仍回傳，足以做內網埠掃描與可達性 oracle；`query` 原文送出（masking 只作用於回傳）。
- 為什麼需要改進：對照 2026 SSRF 最佳實踐（外部來源，見總覽第 7 節），URL-fetching 功能必須解析 IP 並擋 loopback/private/link-local/metadata，僅驗 scheme 是已知不足的防線。
- 具體改善建議：在 `EndpointCallProvider` 加 egress policy：解析 host → resolve IP → 拒絕 loopback/link-local(`169.254.0.0/16`)/私網/`0.0.0.0`/`::1`（resolve 後比對以防 DNS rebinding），或改 allowlist；「允許 trace 到非 loopback」設為預設關閉的明確 opt-in。保留 localhost 給本地 LLM（如 Ollama）時要顯式開關。
- 建議測試方式：對 `endpoint.value` 為 metadata/loopback/私網的案例，斷言回 `unsupported_endpoint`/`blocked`、`query_sent=False`、provider 未被呼叫。
- 相關影響範圍：`/api/trace`、CLI `systograph trace`、`QueryTraceService`、`EndpointCallProvider`。

### H-2：`POST /api/viewer/load` 任意路徑讀取嘗試 + 路徑探測 oracle + 回應含 exception/絕對路徑（repo 實際觀察）

- 嚴重程度：**High**
- 來源引用：
  - 檔案：`src/systograph/web/routes/viewer_routes.py`（第 19-34 行）、`src/systograph/core/services/viewer_session_service.py`（第 53-69 行）
  - 證據：route 直接 `service.load_map(Path(payload.map_json_path))`，無 allowlist/base-dir；service 對 `OSError` 回 `self.empty(error_reason=f"map_read_failed: {exc}")`，`JSONDecodeError` 回 `invalid_json: {exc.msg}`，`error_reason` 經 `response_model=ViewerPayload` 原樣輸出，且**不經** `SafeUnhandledExceptionMiddleware` 遮蔽。
- 問題說明：可指向 `/etc/...`、`~/.ssh/...`、其他專案 JSON 嘗試讀取；依回傳 `error_reason` 可區分「不存在/不可讀（含 errno + 絕對路徑）」「存在但非 JSON」「是 JSON 但非合法 map」「目錄（IsADirectoryError）」→ 路徑探測 oracle。若檔案是 JSON，validation error 也可能回顯欄位值。這不是保證能完整讀取任意檔案，但已違反「錯誤回應不可含 Python exception string / 絕對路徑」。
- 重現方式：`curl -s -X POST http://127.0.0.1:8000/api/viewer/load -H 'Content-Type: application/json' -d '{"map_json_path":"/etc/shadow"}'` → `error_reason` 含 `[Errno 13] Permission denied: '/etc/shadow'`。
- 具體改善建議：限制可載入範圍在本次 session 已知 output 目錄 / 已 build 的 `map_json_path` allowlist，或要求 `project_id` + 相對路徑並用 `normalize_project_relative_path()` 做 base-dir 封閉檢查、拒絕 `..` 與絕對路徑；`error_reason` 改穩定錯誤碼（`map_read_failed`/`invalid_json`/`invalid_map`），不嵌 `str(exc)`，細節僅進 masked log。
- 建議測試方式：傳不存在路徑/目錄/非 JSON，斷言 `error_reason` 不含 `/Users`、`[Errno`、引號路徑；傳 `../../etc/...` 與絕對路徑斷言被拒。
- 相關影響範圍：`/api/viewer/load`、`ViewerSessionService`。

### H-3：合法 docker-compose 觸發 validation crash + compose 非 env 欄位未統一遮罩（repo 實際觀察，已實跑驗證）

- 嚴重程度：**High**
- 來源引用：
  - 檔案：`src/systograph/core/providers/docker_compose_provider.py`（`_append_fact` 第 370-398 行不做遮罩；`_collect_volumes` 第 259-281 行）、`src/systograph/core/services/system_map_normalize_service.py`（第 346 行 normalize 末端呼叫 validate）、`src/systograph/core/services/map_build_service.py`（build 路徑無 try/except 包住 normalize/validate）
- 實跑驗證（core subagent 在 `/tmp` 沙箱）：一個完全正常的 compose
  ```yaml
  services:
    app:
      image: qdrant/qdrant:v1.9
      ports: ['6333:6333']
      volumes:
        - ./secrets:/run/secrets:ro
  ```
  跑 `build()` 直接拋 `SystemMapValidationError: Unmasked secret-like value is not allowed at $.evidence[2].value`。原因：volume 值未遮罩進 validation gate，`mask_text("./secrets:/run/secrets:ro")` 因 `secrets:/run` 被 `KEY_VALUE_RE` 當成 `SECRET` key=value 改寫 → `contains_unmasked_secret` 回 True → 拋錯，且整條 build 路徑無 try/except → traceback 冒泡到 CLI/web。
- 問題說明：雙重問題——(1) compose `volumes` / `env_file` 等非 environment 欄位目前走 `_append_fact` 原樣進 facts/evidence，沒有統一套用 `mask_text` / `redact_local_paths`；(2) 一個合法 compose 就能讓工具崩潰（availability/DoS），且 validation 失敗不是優雅錯誤產物（`map-error.md` 只處理 precondition 階段）。注意：`/api/scans` 會攔部分 `ValueError`，但 `MapBuildService` normalize/validate path 的 `SystemMapValidationError` 仍會冒泡；所以最強證據是 release gate DoS 與非 env 欄位 masking 缺口，不是所有非 env 欄位必然外洩 secret。
- 重現方式：上述 compose，`systograph map <project>`，觀察非零退出與 traceback。
- 具體改善建議：compose volume/env_file/image 一律過 `mask_text`（volume host 段走 `redact_local_paths`）；`MapBuildService` 在 normalize/validate/write 外層加結構化錯誤處理，validation 失敗輸出 `map-error.md` 或 structured error result（新增 failure reason）。
- 建議測試方式：compose volume `./secrets:/run/secrets:ro` 的 fixture，斷言 build 成功且 evidence 已遮罩；加「validation 失敗回傳 error 結果而非拋例外」測試。
- 相關影響範圍：`DockerComposeProvider`、`MapBuildService`、`ScanBoundaryReviewService`。

### H-4：非 UTF-8 `.gitignore` / `.env` 在 failure-isolation 之外崩潰（repo 實際觀察，已實跑驗證）

- 嚴重程度：**High**
- 來源引用：
  - 檔案：`src/systograph/core/providers/filesystem_provider.py`（`_load_gitignore_rules` 第 339-351 行 `read_text(encoding="utf-8")` 無錯誤處理；`build_inventory` 第 72-88 行只攔 `OSError`/`SubprocessError`）、`src/systograph/core/providers/config_parse_provider.py`（`_collect_env_file` 第 113-114 行 `read_text` 無 try/except）
  - 證據：`UnicodeDecodeError` 是 `ValueError` 子類、非 `OSError`，所以 `build_inventory` 的 `except (OSError, SubprocessError)` 攔不到；且 `build_inventory` 在 `project_scan_service.py:100` 是 provider try/except 迴圈**之前**呼叫，failure isolation 保護不到。
- 實跑驗證（`/tmp/systograph_verify/verify_findings2.py`，2026-06-12）：放一個 latin-1 `.env`（`API_TOKEN=caf\xe9secret`）+ `settings.json`，`ConfigParseProvider.collect()` 直接拋 `UnicodeDecodeError`，導致同 provider 的 `settings.json` 也沒掃到（facts=0）。core subagent 另確認非 UTF-8 `.gitignore`（`node_modules\n\xff\xfe-bad`）讓 `build()` 直接拋 `UnicodeDecodeError`。
- 問題說明：任何含非 UTF-8（latin-1、被誤存二進位）`.gitignore` 的專案，掃描可能在 inventory 階段完全失敗且無優雅錯誤產物。非 UTF-8 `.env` 情況會被 `project_scan_service` 的 catch-all `except Exception` 轉成單一 provider failure，scan 不一定全倒，但代價是「整個 config provider 放棄」而非 per-file isolation（對比 `code_pattern_provider._collect_file` 第 107-117 行有 per-file try/except，做對了）。
- 重現方式：見上述實跑腳本。
- 具體改善建議：`read_text` 用 `encoding="utf-8", errors="replace"`（或 try/except 後跳過該檔記 warning）；`config_parse_provider` 對每個檔案 per-file 隔離；考慮把 `build_inventory` 納入更廣的錯誤隔離，降級為 recursive/empty inventory + warning。
- 建議測試方式：non-UTF8 `.gitignore`/`.env` fixture，斷言掃描不崩潰、其他檔案仍被掃、產生 warning。
- 相關影響範圍：`FilesystemProvider`、`ConfigParseProvider`、所有掃描入口。

### H-5：`tests/web` 預設載入開發者本機真實 `.env`（含 NVIDIA_API_KEY），測試隔離失效（repo 實際觀察）

- 嚴重程度：**High**
- 來源引用：
  - 檔案：`src/systograph/web/app.py`（第 89-104 行 `create_app` 預設 `env_file or Path(".env")`）、`src/systograph/core/providers/llm_proposal_provider.py`（第 205-209 行 `env = dict(_dotenv_values(...)); env.update(os.environ)`）
- 證據：`tests/web/test_map_routes.py`、`test_viewer_routes.py`、`test_project_scan_routes.py`、`test_scan_boundary_routes.py`、`test_local_api_hardening.py` 多處直接 `create_app()` 不注入 `mapping_proposal_service`；`tests/conftest.py` 目前沒有 autouse fixture 隔離 `.env` / process env。
- 問題說明：(1) 每次 pytest（含 pre-commit 的 pytest hook）都可能載入 CWD `.env` 或 process env 內的真實 provider/credential；(2) 測試結果依賴本機 `.env`/環境變數，若有非法值（如 `NVIDIA_NIM_TIMEOUT_SECONDS=9999` 超界）`_float_env` 拋 `LlmProposalConfigError`，所有 `create_app()` 測試在不同機器上炸掉、乾淨機器卻通過；(3) `env.update(os.environ)` 無條件覆蓋 dotenv → `test_nvidia_provider_app_wiring.py` 在 shell export 過 flag 的環境會失敗。緩解：proposal 測試用 `create_deterministic_test_app()` 注入（做得好），目前沒有測試真的打 NVIDIA。
- 重現方式：`.env` 放 `NVIDIA_NIM_TIMEOUT_SECONDS=99999` 後跑 `pytest tests/web/test_map_routes.py` → create_app 階段失敗。
- 具體改善建議：`tests/conftest.py` 加 autouse fixture 強制 `create_app` 的 env_file 指向不存在路徑（或 monkeypatch `nvidia_nim_provider_from_env` 回 None / 清相關環境變數）。
- 建議測試方式：contract 測試——tmp 放含 flag+key 的假 `.env`，斷言測試模式下 app factory 不 wire 真實 provider。
- 相關影響範圍：整個 `tests/web`、pre-commit、CI（未來）。

### H-6：CI 完全缺失（`.github/workflows/` 為空）（repo 實際觀察）

- 嚴重程度：**High**
- 來源引用：`ls .github/workflows` 為空；`git ls-files .github/` 只有 ISSUE_TEMPLATE 與 PR template；品質 gate 只在本機 `.pre-commit-config.yaml`。`README.md:22` 架構圖卻宣稱 `CI / GitHub Actions`。
- 問題說明：pre-commit 可被 `--no-verify` 跳過、PR 上不強制執行；`AGENTS.md`「Scanner 行為缺少測試視為 P1」無法被自動把關；「CLI 同時適用 Windows 與 macOS」無 Windows runner 驗證。對一個「Release Readiness Gate」產品，自身沒有 readiness gate。
- 具體改善建議：新增最小 workflow：`uv sync` + `ruff check` + `mypy` + `pytest`，matrix 至少含 `ubuntu-latest` 與 `windows-latest`（Windows job 跑 `tests/cli/` 與 `test_cross_platform_paths.py`）。
- 建議測試方式：workflow 落地後開 PR 驗證。
- 相關影響範圍：全專案品質與跨平台保證。

### H-7：`.env` 從 process CWD 讀取的信任邊界問題（repo 實際觀察，條件式 High）

- 嚴重程度：**High**（情境性，需特定執行方式與 proposal provider 呼叫）
- 來源引用：`src/systograph/web/app.py:96-104`（`env_file or Path(".env")`）、`src/systograph/core/providers/llm_proposal_provider.py:206-211`（`_dotenv_values(env_file or Path(".env"))`，相對 CWD）
- 問題說明：若 Systograph 以 CWD = 被掃描 repo 啟動（CI/容器中常見），且 mapping proposal provider 被啟用並被呼叫，惡意 repo 可在自己的 `.env` 放 `SYSTOGRAPH_ENABLE_NVIDIA_NIM_PROPOSALS=true` + provider endpoint/config，影響 LLM proposal 的外送邊界，並可能把 evidence packet 送到攻擊者控制 endpoint。這不是一般 map build 自動外洩，但前提成立時會造成資料外送風險。
- 具體改善建議：`.env` 不從 CWD 讀，改從明確設定路徑或使用者 home 設定；或在啟動時記錄/警告實際讀取的 `.env` 路徑，並文件化「CWD 不可為被掃描 repo」。
- 建議測試方式：在 tmp「被掃描 repo」放惡意 `.env`，以該目錄為 CWD 啟動，斷言不會自動 wire NVIDIA provider。
- 相關影響範圍：`create_app`、`nvidia_nim_provider_from_env`、所有以掃描目錄為 CWD 的部署。

---

## M. 後端 / 資安 / AI（Medium）

### M-1：掃描入口缺路徑驗證 + `map/build`/CLI 繞過 boundary gate（repo 實際觀察）
- 嚴重程度：Medium
- 來源：`src/systograph/web/routes/project_routes.py:26-30`（`Path(payload.project_path)` 零驗證）、`src/systograph/web/session_store.py:38-51`（直接存）、`src/systograph/web/routes/map_routes.py:19-28`（`map/build` 不經 gate）、`src/systograph/core/services/project_scan_service.py:100`（無 overlay 時整份 inventory 交給 providers）
- 說明：可要求後端掃任意目錄（`/`、`~`、`~/.ssh`、他人專案）。`scans` 對 `.env`/secret-like 有同次確認 gate，但 `map/build` 與 CLI `map` 沒有，且預設 `no_snippets=false`（`schemas.py:40`）會回含程式碼片段 evidence。指向超大目錄 → 長時間遞迴掃描 DoS（`FilesystemProvider` 有單檔 1MB 上限與 dir skip，但無整體 scope/檔案數上限，見 M-6）。`docs/API-GUIDE.md:188,613` 有揭露 map/build 不走 gate，屬已記錄設計，但「任意路徑 + 無 gate + 預設帶 snippet」三者疊加建議收斂。
- 條件式升級：若 local API 被非信任 caller 存取，這可從 Medium 升高為 High，因為 caller 可觸發任意本機目錄掃描與 snippet 外洩。
- 建議：import/build 驗證路徑存在且為目錄、限制可掃 root scope（allowlist 或工作區根）；map/build 套 boundary gate 或對任意路徑預設 `no_snippets=true`；CLI `--help`/README 揭露此行為，長期加 `--confirm-boundaries`。
- 測試：對不存在路徑、非目錄、scope 外路徑的拒絕行為斷言。

### M-2：`output` 參數允許寫入任意可寫目錄（repo 實際觀察）
- 嚴重程度：Medium
- 來源：`src/systograph/web/schemas.py:36-48`（`output: str = "outputs"` → `Path`）、`src/systograph/core/providers/output_artifact_provider.py:62-69`（直接 `mkdir`+寫檔）、`scan_routes.py:80` 同樣 `Path(payload.output)`
- 說明：呼叫端可指定任意絕對路徑（`/tmp/x` 或其他可寫目錄），後端建立目錄並寫 `ai_system_map.json/.md`、`map-error.md`，對既有同名檔覆寫風險。違反「scanner 預設 read-only，寫入位置應受控」。
- 條件式升級：`OutputArtifactProvider` 有 timestamp run dir 防覆寫，並非任意檔覆寫；但若 API 暴露給非信任 caller，仍是任意可寫目錄建立固定報告檔的 High 候選。
- 建議：限制 `output` 為相對路徑且封閉在受控輸出根，用 `normalize_project_relative_path()` 拒絕絕對路徑/`..`。
- 測試：`output` 給絕對路徑或 `../..` 時斷言被拒。

### M-3：`POST /api/trace` 的 `invalid_trace_config` 回應內嵌 exception string（repo 實際觀察）
- 嚴重程度：Medium
- 來源：`src/systograph/web/routes/trace_routes.py:41-45`（`detail=f"invalid_trace_config: {exc}"`）、`src/systograph/core/services/query_trace_config_loader.py:41-48`（錯誤訊息帶 `str(exc)`，OSError 含絕對路徑）。`HTTPException` 不經 `SafeUnhandledExceptionMiddleware` 遮蔽。
- 說明：被掃描專案放壞掉/不可讀的 `pyproject.toml` 即可讓後端把 tomllib/OSError 字串（含絕對路徑）回給呼叫端。`docs/API-GUIDE.md:423` 還把 `invalid_trace_config: ...` 當正式契約記載。
- 建議：`detail` 改穩定碼 `invalid_trace_config`，細節僅進 masked log；要回 line/col 則只抽數字欄位。
- 測試：壞掉/不可讀的 `pyproject.toml` → 斷言 `detail == "invalid_trace_config"`，不含 `Failed to`、`/Users`、`Errno`。

### M-4：`redact_local_paths` 前綴清單不含容器/CI/掛載常見根（repo 實際觀察，已實跑驗證）
- 嚴重程度：Medium
- 來源：`src/systograph/core/services/path_safety_service.py:13-17`（`POSIX_LOCAL_PATH_RE` 只含 `Users|home|tmp|private/tmp|private/var|var|opt|Volumes`）
- 實跑驗證（`/tmp/systograph_verify/verify_findings2.py`）：`/app/...`、`/workspace/...`、`/srv/...`、`/data/...`、`/mnt/...` 全部「LEAK（unredacted）」；`/Users`、`/home`、`/opt` 正常 redact。
- 說明：容器內常見工作目錄（`/app`、`/workspace`、`/srv`、`/data`、`/mnt`）的絕對路徑不會被 redact，會洩漏到 error message / log。`normalize_project_relative_path` 是主防線（輸出用 relative），此為二級防線缺口，但工具會放進 CI/docker，實務上會踩到。
- 建議：`POSIX_LOCAL_PATH_RE` 增補 `app|workspace|srv|data|mnt|srv|root`（或改為「凡 `/` 開頭的絕對路徑都 redact，僅保留尾段」策略）。
- 測試：對上述容器路徑斷言 `redact_local_paths` 有 redact。

### M-5：`InMemorySessionStore` 無上限成長 → 記憶體 DoS（repo 實際觀察）
- 嚴重程度：Medium（local-only 緩解）
- 來源：`src/systograph/web/session_store.py:30-51`（`_projects`、`_build_results_by_project` 只增不減，無上限/TTL/eviction）
- 說明：每次 `POST /api/projects/import` 永久新增；每次 scan 存一份完整 `MapBuildResult`（可能很大），重複呼叫即可撐爆記憶體。
- 建議：加最大 project/scan 數上限 + LRU/TTL eviction。
- 測試：大量 import 後斷言筆數受限/最舊被淘汰。
- 正面：`project_id`/`scan_id`/`trace_id` 皆 `uuid4()`，不可預測 ✅。

#### M-5b：trace script `--start-server` 硬編碼 port 8000（repo 實際觀察）
- 嚴重程度：Medium 偏 Low
- 來源：`scripts/lib/api_trace_common.sh:104-116`（uvicorn 永遠 `--port 8000`，但 `wait_for_api` 輪詢 `$API_BASE_URL`）
- 說明：`--start-server` 配自訂 `--api-base-url http://127.0.0.1:9000` 會等 30s 後 timeout。
- 建議：從 `$API_BASE_URL` 解析 port 傳給 uvicorn，或兩者衝突時 `systograph_die`。

### M-6：掃描無「檔案總數 / 總 evidence 量」上限（repo 實際觀察）
- 嚴重程度：Medium（DoS）
- 來源：`src/systograph/core/providers/filesystem_provider.py`（單檔 1MB ✅ 但無總數上限）、`src/systograph/core/services/project_scan_service.py:125-135`（全部 facts/evidence 累積後 dedupe+sort）
- 說明：百萬量級小檔案的 repo → `os.walk` 全量 + 記憶體無界。`code_pattern_provider` 有單檔 250KB 上限（好），但無「總數」上限。
- 建議：加 `max_total_files`、`max_total_evidence`，超過記 warning 並截斷（截斷前先排序以維持決定性）。
- 測試：合成大量小檔案，斷言有上限與 warning。

### M-7：短 secret 部分遮罩幾乎全洩漏（repo 實際觀察）
- 嚴重程度：Medium
- 來源：`src/systograph/core/services/secret_masking_service.py:118-124`（`VISIBLE_EDGE_LENGTH=4`，>8 字元露前 4 後 4）
- 說明：9 字元 `secretpw1` → `secr...tpw1`，只遮 1 字元；9–16 字元密碼/PIN/短 token 等於洩漏絕大部分。
- 建議：≤16 字元一律 `[MASKED]`，或限制可見比例（最多 25% 且 ≤4 字元）。
- 測試：對 9/12/16 字元 secret 斷言可見字元數受限。

### M-8：validation gate 的 secret 偵測與 masking 同源，無獨立第二道防線（repo 實際觀察）
- 嚴重程度：Medium（架構）
- 來源：`src/systograph/core/services/system_map_validation_service.py:100-145`（`_reject_unmasked_secrets` 用的 `contains_unmasked_secret` 與輸出遮罩同一個 `SecretMaskingService`、同套規則）
- 說明：masking 漏的（如 C-1 的 DSN），validation 也一定漏 —「canonical contract 防線」對 secret 而言並非獨立防線。
- 建議：gate 端加異維度偵測（高熵字串啟發式、針對 `value`/`snippet` 的獨立 secret scanner），讓兩道防線盲點不重疊。此為 C-1 的治本配套。
- 測試：餵一個遮罩規則涵蓋不到但明顯是 secret 的值，斷言 validation 仍擋下。

### M-9：`scan_routes` 把 scanner/provider 編排塞進 route（違反 thin-adapter）（repo 實際觀察）
- 嚴重程度：Medium
- 來源：`src/systograph/web/routes/scan_routes.py:55-64`（route 內 `import` 並實例化 `FilesystemProvider().build_inventory(...)`、自行編排 boundary proposal + build）
- 說明：違反「Web route 必須是 thin adapter」。對照 `viewer_routes` 有測試明確禁止出現 `FilesystemProvider`（`tests/web/test_viewer_routes.py:59-67`），但 `scan_routes` 直接違反且該編排無 web 層測試，CLI/web 可能重複實作 inventory→boundary→build。
- 建議：把「inventory + boundary preflight + build」收斂進 core service（如 `ScanSessionService`），route 只負責呼叫 + 例外→HTTP 轉換。
- 測試：仿 viewer 的 thin-adapter 測試斷言 `scan_routes` source 不含 `FilesystemProvider`；新增 service 層編排測試。

### M-10：AI 呼叫完全無 logging / 可觀測性（repo 實際觀察）
- 嚴重程度：Medium
- 來源：`src/systograph/core/providers/llm_proposal_provider.py`、`src/systograph/core/services/mapping_proposal_service.py` 全檔無任何 logging
- 說明：prompt、token、cost、失敗原因、provider 選擇都無追蹤。LLM 失敗時 `MappingProposalProviderUnavailableError` 被收斂成 `"provider_unavailable"`（不洩漏，好），但也代表無法 debug。對照原則資訊「觀測性要從 app traces 升級成 LLM traces」。
- 建議：對 AI 呼叫加結構化 log（masked prompt 摘要、model、token、latency、cost、fallback 原因），對齊 OpenTelemetry GenAI 慣例（外部來源，注意該規範仍 Development 狀態，需保留版本隔離層）。
- 測試：斷言 proposal 流程產生可觀測 log event 且不含未遮罩 secret。

### M-11：query trace 回應無 size limit + `_summary` 遞迴風險（repo 實際觀察）
- 嚴重程度：Medium
- 來源：`src/systograph/core/providers/endpoint_call_provider.py:135-139`（`response.json()` 無 size 限制）、`src/systograph/core/services/query_trace_service.py:240-263`（`_summary` 遞迴，list 截前 5 但 dict keys 數量未限）
- 說明：惡意/異常 endpoint 回傳 GB 級 body → 記憶體耗盡；深層巢狀 JSON → `_summary` 可能 RecursionError（會被 exception middleware 接住但仍是中斷）；慢速回應在 timeout 內持續佔用。
- 建議：對 trace response 加 max bytes（讀取上限）、`_summary` 加深度上限與 dict keys 數量上限。
- 測試：mock 超大/深層巢狀回應，斷言被截斷且不 OOM/不 RecursionError。

### M-12：`MapBuildResult.error` 型別文件 drift（repo 實際觀察）
- 嚴重程度：Medium
- 來源：`docs/API-GUIDE.md:206-217`（宣稱 `error: string | null`、`output_run_dir: string`）vs `src/systograph/core/models/map_build.py:28-38`（`error: PreconditionError | None`、`output_run_dir: Path | None`）；`PreconditionError` shape 是 `{project_path, failure_reason, scan_stage}`（`errors.py:26-32`）
- 說明：前端照文件把 `error` 當字串 render 會顯示 `[object Object]` 或崩潰；`output_run_dir` 早期失敗時為 null，文件未標 nullable。
- 建議：更新 API-GUIDE 為實際 shape，補 `viewer_load_result`/`ai_system_map` 在 error 時為 null 的說明。
- 測試：`tests/web/test_map_routes.py` 加 error path 測試（掃不存在路徑）斷言 `error.failure_reason` 結構。

### M-13：404 錯誤碼風格不一致（repo 實際觀察）
- 嚴重程度：Medium
- 來源：`src/systograph/web/routes/scan_routes.py:53`（`detail="Project not found"`）vs `trace_routes.py:31`/`detail_scan_routes.py:40`/`mapping_proposal_routes.py:66`（`detail="project_not_found"`）。`tests/web/test_project_scan_routes.py:84` 只斷言 status code 未鎖 detail。
- 說明：前端錯誤碼 mapping 須同時處理兩種格式；之後「順手統一」會默默破壞已依賴 `Project not found` 的前端。
- 建議：統一為 `project_not_found`（breaking change，需 API-GUIDE 標 migration），或在錯誤對照表明列兩種格式。
- 測試：route 測試斷言 detail 精確字串。

### M-14：多條 route error path 與 `safe_log_event` 無測試（repo 實際觀察）
- 嚴重程度：Medium（依 AGENTS.md「scanner 行為缺測試 P1」）
- 來源（逐項已比對測試函式名單）：
  1. `POST /api/trace` 400 `invalid_trace_config`（`trace_routes.py:41-45`）只有 CLI 測過，web 層 0 測試。
  2. `GET /api/detail-scans/{id}` 404 `detail_scan_not_found`（`detail_scan_routes.py:92-93`）無測試。
  3. `PATCH /api/mappings/{id}` 404 `mapping_not_found`（`mapping_routes.py:65-69`）與更新後 422 無測試。
  4. `POST /api/scans` boundary decision 非法 422（`scan_routes.py:63-64`）無測試。
  5. CLI `systograph map` error path（`map_command.py:56-64`）無測試。
  6. `safe_log_event`（`logging_service.py:14-37`）是「log 不得印 secret/路徑」最後防線，**全 repo 無直接測試**；`prompt_template_loader.py`、`llm_proposal_config_loader.py` 無專屬單元測試。
- 建議：逐項補 route 層測試（用既有 helper）；`safe_log_event` 餵含 `OPENAI_API_KEY=sk-...` + 絕對路徑的 fields，斷言已遮罩。

### M-15：AI prompt 把不可信內容直接嵌入、evidence packet 部分欄位未遮罩（repo 實際觀察 + 外部最佳實踐）
- 嚴重程度：Medium
- 來源：`src/systograph/core/providers/llm_proposal_provider.py:160-179`（`masked_evidence_packet_json` 直接 `json.dumps(packet)` 嵌入單一 user message）；AI subagent 分析：`MappingEvidencePacket` 的 `source_file`/`observed_kind`/`reason` 來自被掃描 repo、未額外遮罩或 injection 隔離；prompt 僅以 `Masked evidence packet:` header 分隔，無結構化 delimiter / spotlighting。
- 說明：被掃描 repo 內容（檔名、masked snippet、dependency 名）可含 prompt injection payload。**緩解（強）**：`mapping_proposal_service._validate_candidate`（第 264-303 行）強制 candidate 引用的 evidence_ids ⊆ packet.evidence_ids、target_slot ∈ available_slots，並對 candidate output 再跑 `_reject_unmasked_secret`，且 proposal 是 pending-only（須使用者 accept 才變 manual mapping）。這正是 OWASP / NCC「把 LLM 輸出當不可信、在 deterministic code 驗證」的正確做法。殘餘風險：injection 導致 schema-valid 但錯誤的 candidate；LLM rationale（≤800 字元）顯示在 UI 可能被 repo snippet 影響做 social engineering。
- 建議：prompt 用結構化 delimiter / spotlighting 標記不可信區塊；evidence packet 的 `source_file`/`reason` 過遮罩；UI 顯示 LLM rationale 時標示「AI 生成、未驗證」。
- 測試：餵含 injection 字串的 evidence packet，斷言 output validation 仍只接受合法 candidate、proposal 維持 pending。

### M-16：前端 `fetch` 無 timeout / AbortController（repo 實際觀察）
- 嚴重程度：Medium（UX）
- 來源：`frontend/src/services/viewerApi.ts:10-22`（`fetch(url, {headers})` 無 signal/timeout）
- 說明：API mode 連到不回應的 server（或慢速）時，`useViewerPayload` 會永久停在 loading（`StateOverlay` 顯示 "Loading from API"），使用者無從得知卡住。
- 建議：用 `AbortController` + `setTimeout`（如 10-15s）給 fetch 加 timeout，逾時轉 error 狀態並提示。
- 測試（需先補 Vitest）：mock 不回應的 fetch，斷言逾時後進 error 狀態。

### M-17：前端 build 主 chunk 1.56MB（repo 實際觀察）
- 嚴重程度：Medium（效能）
- 來源：`pnpm run build` 輸出 `dist/assets/index-*.js 1,563.23 kB │ gzip: 467.62 kB`，超過 500kB 警告線；另 `web-worker` 被當 external dependency 警告（elkjs worker）。
- 說明：`vite.config.ts` 已分 react/graph/icons chunk，但主 index chunk 仍 1.5MB，首次載入偏慢。
- 建議：檢視主 chunk 內容、用 dynamic import 拆分非首屏元件（DetailPanel/ReplayTimeline/ChatPanel）；確認 `web-worker` external 警告是否影響 ELK layout production 行為。
- 測試：build 後斷言主 chunk < 設定門檻。

---

## L. 後端 / AI（Low）

- **L-1：LLM provider 失敗只立即 fallback，無 backoff / circuit breaker / 429 特別處理**（`llm_proposal_provider.py` generate；`mapping_proposal_service._try_provider:209-231` 2 次 attempt 僅針對 validation error）。建議：對 transient/429 加退避；對齊原則資訊「明確定義 fallback 順序」。
- **L-2：trace `timeout_seconds` 上限 120s 放大慢速探測**（`schemas.py:131`）；配合 H-1 一起收斂。
- **L-3：`_pending_proposal_for_source` 並發 race condition**（`mapping_proposal_service.py:240-251`）：同一 source 並發 create 可能各自 miss 既有 pending → 呼叫 provider 兩次。`decide` 有 RLock，但 create 無。建議：create 也納入鎖或以 source key 去重。
- **L-8：`is_project_relative_posix_path` 比 `normalize_project_relative_path` 寬鬆**（`path_safety_service.py:57-73` 不擋 segment 內冒號）；實測 `is_project_relative_posix_path("foo/a:b")` 為 True。目前 scanner 自身路徑都過正規化，風險低。建議：判斷式也拒絕含冒號 segment。
- **L-9：scan summary 兩欄位語意失真**（`system_map_normalize_service.py:398-416`）：`not_configured_slots` 恆 0（`ComponentDetectionService` 不產此狀態）；`secret_masking_applied` 以字串含 `[MASKED]`/`...` 判定，屬脆弱啟發式。建議：移除恆 0 欄位或正確填值；`secret_masking_applied` 由遮罩流程實際回報旗標。
- **L-10：CLI `trace --timeout-seconds` 無上下限**（`cli/trace_command.py:48-54`），與 web `gt=0, le=120` drift。建議：bound 下沉到 `QueryTraceService.trace` 或 typer option `min/max`。
- **L-11/L-12：測試硬編碼本機絕對路徑 + CWD 依賴 fixture**（`tests/contracts/test_secret_snapshot_safety.py:25`、`test_cross_platform_paths.py:70-79`、`test_local_api_hardening.py:37`、`README.md:97`；`tests/cli/test_viewer_command.py:11-16`、`tests/web/test_viewer_routes.py:11-16` 用相對路徑 fixture）。建議：改合成路徑 `/Users/example/...`、用 `tests/helpers/fixtures.py:repo_root()`。
- **L-13：`.gitignore` 排除兩支 smoke script**（`.gitignore:57-59` 的 `test_mapping_proposal_llm.sh`、`test_nvidia_nim_direct.sh`，檔案存在工作樹但不入版控，內容不含 secret）；`test_nvidia_nim_direct.sh:133` 把 key 放 curl 命令列（本機 `ps` 可見）。建議：決定去留並文件化。
- **L-14：README 與實作 drift**（`README.md:7-9` 宣稱 READY/RISKY/NOT READY verdict 但 `src/` 未實作；未連結 API-GUIDE、未提 CLI 三命令與 `systograph` entry point）。建議：標註 roadmap 狀態、補連結。
- **L-15：`viewer_command.py` 檔名與註冊命令 `validate-map` 不一致**（`cli/viewer_command.py:14`）。建議：rename 或 docstring 註明。
- **L-16：dev dependency `mypy>=2.1.0` 無上限**（`pyproject.toml:25`），與 runtime 依賴 pin 風格不一致（有 uv.lock 鎖定，風險低）。
- **L-5：server host binding 未在程式碼層強制**（`app.py:145` 無 bind host，僅靠 uvicorn `--host` 慣例）。建議：官方啟動進入點預設 `host="127.0.0.1"`，或對非 loopback bind 警告/拒絕。
- **L-6：`InMemorySessionStore` 併發無鎖**（`session_store.py`，FastAPI 同步 route 跑 threadpool，`save_build_result` 多步寫入非原子）。local single-user 影響低。
- **L-7（資安/正面記錄）：成功回應含本機絕對路徑**（`MapBuildResult` 路徑欄位為 `Path` 序列化、`PreconditionError.project_path=str(path)`）。屬 API-GUIDE by-design 成功欄位，但與「不洩漏絕對路徑」精神相左，建議提供 redacted 模式。

---

## E. 資料庫（現況）

- **已檢查，未發現資料庫層問題——因為目前沒有資料庫。**
- 來源：`src/systograph/storage/repositories.py` 只有 repository protocol / in-memory 實作 re-export；無 SQLAlchemy/Alembic/psycopg/pgvector/migrations（與 `AGENTS.md`、check1 第 49 點一致）。
- 相關未完成 plan：`unfinish/26-implement-persistent-session-store-and-scan-history.md`、`unfinish/27-introduce-database-backed-storage-layer.md`。
- 提醒（非本次問題）：未來導入 DB 時，session/scan history 的 secret 欄位需沿用 shared masking path（C-1 修好後），且 pgvector/連線字串需納入 secret masking marker。

---

## 已檢查、未發現明顯問題的區塊（後端 / AI）

- **YAML/TOML/JSON 解析安全**：`config_parse_provider.py:103`、`docker_compose_provider.py:97` 一律 `yaml.safe_load`（無 `yaml.load`）；TOML `tomllib`、JSON `json.loads`，無反序列化風險；解析例外收斂為 `ParseIssue` 並遮罩。
- **Provider failure isolation**：`project_scan_service.py:113-135` 逐 provider try/except，失敗轉 `ParseIssue` + warning，訊息經 `mask_text` + `redact_local_paths`。
- **ReDoS**：`secret_masking_service` 的 `KEY_VALUE_RE`、`private-key-block`（`.*?` 受 END 界定）、code_pattern rules 無巢狀量詞/災難性回溯，且 code_pattern 有 250KB 單檔上限。
- **filesystem symlink 防護**：`_is_symlink_outside_root`（`filesystem_provider.py:396-403`）以 `resolve().relative_to(root)` 判斷；`os.walk(followlinks=False)`；`code_pattern_provider._resolve_inventory_path` 額外擋 `\\`/絕對/`..`/逃出 root。
- **output artifact 寫出**：已存在 artifact 時建 timestamp 子目錄防覆寫；檔名固定；JSON `sort_keys=True` + 清單依 id 排序 → 決定性輸出。
- **system_map cross-reference 驗證**：confidence 欄位、duplicate id、evidence 路徑、components/endpoints/flows/risk/recommended/detail/trace 交叉參照都有防線（`system_map_validation_service.py`），broken cross-ref 會拋 `SystemMapValidationError`。
- **mapping proposal output validation**：schema + evidence id allowlist + slot allowlist + secret check + pending-only（`mapping_proposal_service.py:253-327`）—— 強防線，符合 OWASP LLM 最佳實踐。
- **httpx redirect 預設關閉**（已驗證 `follow_redirects=False`）；**API key 只在 Authorization header、不進回應**；**timeout/max_tokens bounded**（`llm_proposal_config_loader` 上下限）。
- **CORS / 413 / 500**：allowlist 無 wildcard、`allow_credentials=False`；413 以實際 bytes 計算；500 經 `SafeUnhandledExceptionMiddleware` 遮蔽（`middleware.py`）。
- **rule_catalog_loader**：對 unknown section/duplicate id/regex 編譯失敗/snippet_group 非具名群組都有拒絕；catalog 以套件內建資源載入，不吃使用者輸入。
