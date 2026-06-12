# Phase 1 Find-Error — 修補 TODO Backlog

- 日期：2026-06-12
- 來源：`../report/2026-06-12-phase1-find-error-overview.md` 及兩份詳細發現
- 用途：把本次「只檢查、不修補」的發現轉成可獨立拆解的 issue 候選。**本次未修補任何項目**，以下為下一階段工作。
- 性質提醒：所有項目都已用 repo 實際程式碼 / 實跑驗證確認存在（Critical/High 附 `/tmp/kai_verify/` 驗證腳本佐證）。

> 勾選框代表「是否已修補」，目前全部未修補（`[ ]`）。

---

## P0 — 立即（Critical / High，安全與可用性）

### [ ] T-C1：Secret masking 補洞（DSN / 變體 key / URL userinfo）
- 對應：C-1（Critical）
- 檔案：`src/kai_mind/core/services/secret_masking_service.py`
- 動作：(1) `SECRET_KEY_MARKERS` 增 `PASSWD/PWD/CREDENTIAL/PRIVATE_KEY/ACCESS_KEY/CLIENT_SECRET/SESSION/COOKIE`；(2) key marker 比對正規化掉底線（`MYAPIKEY`→命中）；(3) 新增 URL userinfo pattern 遮罩 `scheme://user:pass@host` 的 password 群組。
- 驗收：fixture 專案含 `DATABASE_URL`/`DB_PASSWD`/`MYAPIKEY`/`config.yaml url 帳密` 四種 case，跑 `kai map` 後 `ai_system_map.json` 無明文；`mask_text` parametrized 單元測試全綠；既有 435 測試不退步。
- 風險：marker 太寬可能誤遮正常值 → 需配合 T-M8 異源偵測與既有 snapshot 測試確認無過度遮罩。
- 角色：後端 / 資安

### [ ] T-H1：Query trace SSRF egress 控制
- 對應：H-1（High）
- 檔案：`src/kai_mind/core/providers/endpoint_call_provider.py`（preflight）
- 動作：解析 host → resolve IP → 拒絕 loopback / link-local(`169.254.0.0/16`) / 私網(RFC1918) / `0.0.0.0` / `::1` / metadata；resolve 後對「連線的 IP」比對以防 DNS rebinding；「允許非 loopback trace」設為預設關閉的明確 opt-in；保留 localhost 給本地 LLM 需顯式開關。
- 驗收：對 `169.254.169.254`/`127.0.0.1:22`/`10.x`/`192.168.x`/`[::1]` 斷言回 `unsupported_endpoint`/`blocked`、`query_sent=False`、provider 未被呼叫；正常外部 https endpoint 仍可 trace。
- 角色：後端 AI / 資安

### [ ] T-H2：`viewer/load` 路徑封閉 + 錯誤碼穩定化
- 對應：H-2（High）
- 檔案：`src/kai_mind/web/routes/viewer_routes.py`、`src/kai_mind/core/services/viewer_session_service.py`
- 動作：限制可載入範圍在 session output allowlist 或要求 `project_id` + 相對路徑經 `normalize_project_relative_path()` 封閉檢查；`error_reason` 改穩定碼（`map_read_failed`/`invalid_json`/`invalid_map`），不嵌 `str(exc)`，細節僅進 masked log。
- 驗收：傳不存在/目錄/非 JSON 路徑斷言 `error_reason` 不含 `/Users`、`[Errno`、引號路徑；傳 `..`/絕對路徑斷言被拒。
- 角色：後端 / 資安

### [ ] T-H3：docker-compose 崩潰修復 + 非 env 欄位遮罩 + build 結構化錯誤處理
- 對應：H-3（High）
- 檔案：`src/kai_mind/core/providers/docker_compose_provider.py`、`src/kai_mind/core/services/map_build_service.py`
- 動作：compose volume/env_file/image/port 一律過 `mask_text`（volume host 段走 `redact_local_paths`）；`MapBuildService` 在 normalize/validate/write 外層加 try/except，validation 失敗輸出 `map-error.md`（新增 failure reason）而非冒泡 traceback。
- 驗收：`volumes: ./secrets:/run/secrets:ro` 的 compose fixture，build 成功且 evidence 已遮罩；validation 失敗回 error 結果而非拋例外。
- 角色：後端

### [ ] T-H4：非 UTF-8 檔案不可讓掃描崩潰（含 inventory 階段隔離）
- 對應：H-4（High）
- 檔案：`src/kai_mind/core/providers/filesystem_provider.py`、`src/kai_mind/core/providers/config_parse_provider.py`
- 動作：`read_text` 改 `errors="replace"`（或 try/except 跳過該檔記 warning）；`config_parse_provider` 改 per-file 隔離；`build_inventory` 納入更廣錯誤隔離（降級 recursive/empty + warning）。
- 驗收：non-UTF8 `.gitignore`/`.env` fixture，斷言掃描不崩潰、其他檔案仍被掃、有 warning。
- 角色：後端

### [ ] T-H5：測試環境與本機 `.env` 隔離
- 對應：H-5（High）
- 檔案：`tests/conftest.py`（新增 autouse fixture）
- 動作：autouse fixture 強制 `create_app` 的 env_file 指向不存在路徑（或 monkeypatch `nvidia_nim_provider_from_env` 回 None / 清相關環境變數），讓 `tests/web` 與本機 `.env`、os.environ 完全隔離。
- 驗收：tmp 放含 flag+key 的假 `.env`，斷言測試模式下 app factory 不 wire 真實 provider；在 export 過 flag 的 shell 跑 `tests/web` 全綠。
- 角色：後端 / DX

### [ ] T-H6：最小 CI（含 Windows job）
- 對應：H-6（High）
- 檔案：`.github/workflows/ci.yml`（新增）
- 動作：`uv sync` + `ruff check` + `ruff format --check` + `mypy` + `pytest`，matrix `ubuntu-latest` + `windows-latest`（Windows job 跑 `tests/cli/` 與 `test_cross_platform_paths.py`）。
- 驗收：開 PR 觀察 check 執行且全綠。
- 角色：DX

### [ ] T-H7：`.env` 不從被掃描 repo 的 CWD 讀取
- 對應：H-7（High）
- 檔案：`src/kai_mind/web/app.py`、`src/kai_mind/core/providers/llm_proposal_provider.py`
- 動作：`.env` 改從明確設定路徑 / 使用者 home 讀，不依賴 CWD；或啟動時 log 實際讀取的 `.env` 路徑並文件化「CWD 不可為被掃描 repo」。
- 驗收：以 tmp「被掃描 repo」（含惡意 `.env`）為 CWD 啟動，斷言不自動 wire NVIDIA provider。
- 角色：後端 / 資安

---

## P1 — 短期（Medium）

### [ ] T-M1：掃描入口路徑驗證 + scope；map/build 與 CLI 揭露/收斂 boundary
- 對應：M-1。檔案：`project_routes.py`、`map_routes.py`、`session_store.import_project`、`cli/map_command.py`。
- 動作：import/build 驗證路徑存在且為目錄、限制可掃 root scope；map/build 對任意路徑預設 `no_snippets=true` 或套 boundary gate；CLI `--help`/README 揭露繞過 gate 行為。
- 驗收：對不存在/非目錄/scope 外路徑斷言拒絕；CLI 掃含 `.env` 專案的行為被測試鎖定。

### [ ] T-M2：`output` 參數封閉在受控輸出根
- 對應：M-2。檔案：`web/schemas.py`、`output_artifact_provider.py`。
- 動作：限 `output` 為相對路徑、經 `normalize_project_relative_path()` 拒絕絕對路徑/`..`。
- 驗收：`output` 給絕對路徑或 `../..` 斷言被拒。

### [ ] T-M3：trace `invalid_trace_config` 錯誤碼穩定化
- 對應：M-3。檔案：`trace_routes.py`、`query_trace_config_loader.py`。
- 動作：`detail` 改穩定碼 `invalid_trace_config`，不嵌 `str(exc)`。
- 驗收：壞掉/不可讀 `pyproject.toml` → `detail == "invalid_trace_config"`，不含 `Failed to`/`/Users`/`Errno`。

### [ ] T-M4：`redact_local_paths` 補容器/CI/掛載路徑前綴
- 對應：M-4。檔案：`path_safety_service.py`（`POSIX_LOCAL_PATH_RE`）。
- 動作：增補 `app|workspace|srv|data|mnt|root`，或改「凡絕對路徑都 redact、僅留尾段」。
- 驗收：對 `/app`、`/workspace`、`/srv`、`/data`、`/mnt` 斷言有 redact。

### [ ] T-M5：`InMemorySessionStore` 上限 / eviction（含 trace script port 修正）
- 對應：M-5、M-5b。檔案：`session_store.py`、`scripts/lib/api_trace_common.sh`。
- 動作：加最大 project/scan 數上限 + LRU/TTL eviction；trace script 從 `$API_BASE_URL` 解析 port。
- 驗收：大量 import 後筆數受限/最舊淘汰；`--start-server` + 自訂 port 正確運作。

### [ ] T-M6：掃描檔案總數 / evidence 量上限
- 對應：M-6。檔案：`filesystem_provider.py`、`project_scan_service.py`。
- 動作：`max_total_files`、`max_total_evidence`，超過記 warning 並截斷（截斷前排序維持決定性）。
- 驗收：合成大量小檔案，斷言有上限與 warning。

### [ ] T-M7：短 secret 完整遮罩
- 對應：M-7。檔案：`secret_masking_service.py`（`_mask_secret_value`）。
- 動作：≤16 字元一律 `[MASKED]`，或限制可見比例。
- 驗收：9/12/16 字元 secret 斷言可見字元數受限。

### [ ] T-M8：validation gate 異源 secret 偵測（C-1 治本配套）
- 對應：M-8。檔案：`system_map_validation_service.py`。
- 動作：gate 端加異維度偵測（高熵字串啟發式 / 針對 `value`/`snippet` 的獨立 scanner），與輸出遮罩盲點不重疊。
- 驗收：餵遮罩規則涵蓋不到但明顯是 secret 的值，斷言 validation 仍擋下。

### [ ] T-M9：`scan_routes` 編排下沉 core service
- 對應：M-9。檔案：`scan_routes.py`、新增 `core/services/scan_session_service.py`（建議）。
- 動作：把 inventory + boundary preflight + build 收斂進 service，route 只呼叫 + 例外→HTTP。
- 驗收：thin-adapter 測試斷言 `scan_routes` source 不含 `FilesystemProvider`；新增 service 編排測試。

### [ ] T-M10：AI 呼叫加 logging / 可觀測性
- 對應：M-10。檔案：`llm_proposal_provider.py`、`mapping_proposal_service.py`。
- 動作：結構化 log（masked prompt 摘要、model、token、latency、cost、fallback 原因），保留版本隔離層以對齊 OpenTelemetry GenAI（規範仍 Development）。
- 驗收：proposal 流程產生可觀測 log event 且不含未遮罩 secret。

### [ ] T-M11：query trace response size / 遞迴防護
- 對應：M-11。檔案：`endpoint_call_provider.py`、`query_trace_service.py`。
- 動作：trace response 加 max bytes 讀取上限；`_summary` 加深度上限與 dict keys 數量上限。
- 驗收：mock 超大/深層巢狀回應，斷言被截斷、不 OOM、不 RecursionError。

### [ ] T-M12：API-GUIDE `MapBuildResult.error` 型別修正
- 對應：M-12。檔案：`docs/API-GUIDE.md`。
- 動作：更新為實際 shape（`error: {project_path, failure_reason, scan_stage} | null`、`output_run_dir` nullable）。
- 驗收：`tests/web/test_map_routes.py` 加 error path 測試斷言 `error.failure_reason` 結構。

### [ ] T-M13：404 錯誤碼風格統一
- 對應：M-13。檔案：`scan_routes.py`（與 API-GUIDE）。
- 動作：統一 `project_not_found`（標 migration）或文件明列兩種格式。
- 驗收：route 測試斷言 detail 精確字串。

### [ ] T-M14：補 route error path 與 `safe_log_event` 測試（AGENTS.md P1）
- 對應：M-14。檔案：`tests/web/`、`tests/cli/`、`tests/unit/core/`。
- 動作：補 trace 400 / detail-scan 404 / mapping PATCH 404+422 / scans 422 / CLI map error path；`safe_log_event` 餵含 `OPENAI_API_KEY=sk-...` + 絕對路徑 fields 斷言遮罩。
- 驗收：上述路徑皆有測試且全綠。

### [ ] T-M15：AI prompt 結構化隔離 + evidence packet 欄位遮罩
- 對應：M-15。檔案：`llm_proposal_provider.py`、`mapping_evidence_packet_builder.py`、前端 DetailPanel。
- 動作：prompt 用結構化 delimiter / spotlighting 標記不可信區塊；packet `source_file`/`reason` 過遮罩；UI 顯示 LLM rationale 標示「AI 生成、未驗證」。
- 驗收：含 injection 字串的 packet，斷言 output validation 仍只接受合法 candidate、proposal 維持 pending。

### [ ] T-M16：前端 `fetch` timeout
- 對應：M-16 / B-1。檔案：`frontend/src/services/viewerApi.ts`。
- 動作：`AbortController` + 逾時（10-15s），逾時轉 error 並提示。
- 驗收（需先 T-FE Vitest）：mock 不回應 fetch，斷言逾時後進 error 狀態。

### [ ] T-M17：前端 bundle 主 chunk 拆分
- 對應：M-17。檔案：`frontend/vite.config.ts`、`App.tsx`。
- 動作：dynamic import 拆非首屏元件（DetailPanel/ReplayTimeline/ChatPanel）；確認 `web-worker` external 警告是否影響 ELK production。
- 驗收：build 主 chunk < 設定門檻。

---

## P2 — 中期（Low / 架構 / 測試覆蓋）

### [ ] T-FE1：前端導入 Vitest + React Testing Library（B-3）
- 檔案：`frontend/package.json`、`frontend/vite.config.ts` 或新增 test config。
- 動作：新增 `pnpm test`，導入 Vitest + React Testing Library + jest-dom。
- 驗收：graph render smoke、detail panel open/close、filter highlight 不隱藏 graph、API error 不 crash、`viewerApi` schema parse tests 先落地；CI（T-H6）可呼叫 `pnpm test`。

### [ ] T-FE2：前端互動 lifecycle typed schema（B-2）
- 檔案：`frontend/src/types.ts`、`frontend/src/services/viewerApi.ts`。
- 動作：接真實互動 API 前，為 detail scan / mapping proposal / project-scan lifecycle 補 Zod schema，避免 `record(unknown)` 直接流進 UI。
- 驗收：schema success/failure tests；拼錯 detail/proposal/project-scan 欄位時測試失敗。

### [ ] T-UX1：API error / pending / sample 狀態文案與標示（A-1/A-2/A-3）
- 檔案：`frontend/src/components/StateOverlay.tsx`、`frontend/src/App.tsx`、`frontend/src/components/SystemGraph.tsx`。
- 動作：依 network error / 404 / schema parse / `viewer_load_result.error_reason` 顯示可操作文案；sample mode 在 graph 區域增加常駐標示。
- 驗收：mock `Failed to fetch`、404、`loaded=false,error_reason=invalid_map`、sample mode，斷言文案與 sample badge 正確。

### [ ] T-UX2：Project scan + scan-boundary decision frontend flow（A-4）
- 檔案：`frontend/src/services/viewerApi.ts`、`frontend/src/store/viewerStore.ts`、新增 scan/boundary components、`frontend/API_CONTRACT.md`。
- 動作：實作 `POST /api/projects/import` -> `POST /api/scans` -> `requires_boundary_decision` -> submit decisions -> rescan -> refresh `/api/map`；UI 清楚標示 decision 只影響本次 scan。
- 驗收：mock `requires_boundary_decision` response，斷言 proposal 列表、`scan_this_run` / `skip_this_run` action、rescan request shape 與 success/error state。

### [ ] T-UX3：Accessibility hardening for inspector/progress（A-5）
- 檔案：`frontend/src/components/DetailPanel.tsx`、`frontend/src/components/ProgressStrip.tsx`。
- 動作：補 floating inspector 的 dialog/region 語意、focus trap 或 return focus；progress meter 補 `role="progressbar"` / `aria-valuenow` 等語意。
- 驗收：RTL role/name/aria tests；鍵盤 Escape/Tab smoke 通過。

### [ ] T-FE3：前端 no-secret display regression（A-6）
- 檔案：`frontend/src/components/DetailPanel.tsx`、前端 fixture/test。
- 動作：加入 raw secret evidence fixture/test，避免 sample/API payload 的 secret 直接顯示；主 masking policy 仍由後端 C-1/M-8 負責。
- 驗收：含 `DATABASE_URL=postgres://u:p@h/db` 或 `sk-...` 的 evidence payload 不會在 rendered output 出現明文。

### [ ] T-L1：LLM provider transient failure backoff / circuit breaker
- 對應：L-1。檔案：`llm_proposal_provider.py`、`mapping_proposal_service.py`。
- 驗收：429/timeout/provider unavailable mock 有 bounded retry/backoff 或短路紀錄，不含未遮罩 prompt。

### [ ] T-L3：Mapping proposal create race 去重
- 對應：L-3。檔案：`mapping_proposal_service.py`。
- 驗收：同一 source 並發 create 只產生一個 pending proposal 或只呼叫 provider 一次。

### [ ] T-L5：local API host binding / non-loopback warning
- 對應：L-5。檔案：`web/app.py`、CLI/dev server entrypoint 或 README。
- 驗收：官方啟動預設 `127.0.0.1`；非 loopback bind 有明確警告或拒絕策略。

### [ ] T-L7：成功回應路徑 redacted mode
- 對應：L-7。檔案：`map_build.py`、web schemas / API docs。
- 驗收：可選 redacted mode 下成功 response 不含本機絕對路徑；預設相容性策略文件化。

### [ ] T-L8：`is_project_relative_posix_path` 拒絕冒號 segment
- 對應：L-8。檔案：`path_safety_service.py`。
- 驗收：`foo/a:b`、Windows drive-like path、UNC-like path 皆被拒；既有 normalized project-relative path 不退步。

### [ ] T-L9：scan summary 欄位語意修正
- 對應：L-9。檔案：`system_map_normalize_service.py`。
- 驗收：`not_configured_slots` 不再恆 0 或移除/文件化；`secret_masking_applied` 由遮罩流程實際回報旗標。

### [ ] T-L10：CLI trace timeout bound
- 對應：L-10。檔案：`cli/trace_command.py`、`QueryTraceService`。
- 驗收：CLI timeout 與 web schema 一致，非法值被拒絕且錯誤訊息穩定。

### [ ] T-L11：測試硬編碼本機絕對路徑清理
- 對應：L-11/L-12。檔案：`tests/contracts/test_secret_snapshot_safety.py`、`tests/unit/core/test_cross_platform_paths.py`、`tests/web/test_local_api_hardening.py`、viewer fixture helper。
- 驗收：測試不依賴 `/Users/linjunting` 或 CWD；使用合成 path / repo_root helper。

### [ ] T-L13：未版控 smoke script 去留與 secret-safe curl
- 對應：L-13。檔案：`.gitignore`、`test_mapping_proposal_llm.sh`、`test_nvidia_nim_direct.sh`（若決定保留）。
- 驗收：保留則入版控並避免 key 出現在 process argv；不保留則移除並文件化替代 trace。

### [ ] T-L14：README roadmap / command drift 修正
- 對應：L-14。檔案：`README.md`。
- 驗收：READY/RISKY/NOT READY 明確標成 roadmap 或對齊實作；補 API-GUIDE、CLI commands、`kai-mind` entry point。

### [ ] T-L15：`viewer_command.py` 命名與 validate-map command 對齊
- 對應：L-15。檔案：`src/kai_mind/cli/viewer_command.py`、`src/kai_mind/cli/main.py`。
- 驗收：rename 或 docstring 說明職責；CLI tests 不退步。

### [ ] T-L16：dev dependency upper bound review
- 對應：L-16。檔案：`pyproject.toml`、`uv.lock`。
- 驗收：決定是否為 `mypy` 補 `<3` 或保留 lock-only；若保留，README/CONTRIBUTING 說明以 `uv.lock` 為準。

---

## 驗證腳本備查（本次臨時，未進版控）

- `/tmp/kai_verify/verify_findings.py` — C-1 secret masking、H-1 SSRF preflight
- `/tmp/kai_verify/verify_findings2.py` — M-4 容器路徑 redact、H-4 `.env` 編碼例外
- 這些為一次性驗證腳本，若要納入正式 regression，請改寫為 `tests/` 下的測試（見各 T-* 驗收）。
