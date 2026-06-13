# Phase 1 Find-Error 審查報告（總覽）

- 日期：2026-06-12
- 範圍：前端、後端、AI backend / infra / application、資安、（資料庫現況）
- 性質：**只做檢查與記錄，未修改任何功能程式碼**
- 依據：`docs/work/Timmy/schedule/fable-5/find-error/check-prompt/check1.md`、`docs/work/Timmy/schedule/fable-5/find-error/plan/unfinish/phase1-check.md`（原則資訊）、`AGENTS.md`、`.cursor/rules/linus_torvalds.mdc`
- 詳細發現分檔：
  - 後端 / 資安 / AI / 資料庫：`2026-06-12-backend-security-ai-findings.md`
  - UI/UX / 前端工程：`2026-06-12-frontend-ux-findings.md`
  - 可拆 issue 的 backlog：`../todo/2026-06-12-phase1-find-error-todo.md`

> 來源標示原則：每個發現都標注「repo 實際觀察」（實際讀 code / 跑驗證）或「外部最佳實踐建議」（含查詢來源與日期）。本報告所有 Critical/High 問題都附有第一手驗證或精確行號證據。

---

## 0. 審查方法與基線

### 0.1 基線驗證（repo 實際觀察，2026-06-12 實跑）

| 檢查 | 指令 | 結果 |
|---|---|---|
| 後端測試 | `.venv/bin/python -m pytest -p no:cacheprovider` | **435 passed in 4.64s** ✅ |
| Lint | `.venv/bin/ruff check src tests` | All checks passed ✅ |
| 格式 | `.venv/bin/ruff format --check src tests` | 154 files already formatted ✅ |
| 型別 | `.venv/bin/mypy src tests` | Success: no issues found in 140 source files ✅ |
| 前端 Lint | `pnpm run lint` | 通過 ✅ |
| 前端 Build | `pnpm run build` | 成功，但有 2 個警告（主 chunk 1.56MB、`web-worker` 被當 external）⚠️ |

基線是綠的：既有測試、型別、lint 全過。**本次發現的問題多半是「測試與 lint 涵蓋不到的行為邊界」與「安全邊界」**，不是會被現有 CI/測試攔下來的 regression。這點本身也是一個訊號（見 H-6 CI 缺失、M-14 error path 無測試）。

### 0.2 檢查方式

- 主審查者實際閱讀 code / tests / scripts / docs，並用臨時 Python one-liner 與既有驗證指令複核 Critical/High 問題（SSRF preflight、secret masking、path redaction、`.env` 編碼例外）。`/tmp/kai_verify/` 只作為本次一次性驗證備查；正式修補時應改寫成 `tests/` regression。
- 本輪追加 3 個唯讀 subagent 複核：後端/資安 Critical/High、前端/UX、文件 contract。subagent 意見已合併到本報告與兩份詳細發現。
- 外部研究：OWASP LLM Top 10 (2025)、OWASP SSRF 防護、MCP Security Best Practices、AgentDojo、OpenTelemetry GenAI（見第 7 節來源）。

### 0.3 分類覆蓋矩陣（2026-06-12 複核後）

| 分類 | 已檢查來源 | 結論 / 對應 finding |
|---|---|---|
| UI/UX | `frontend/src/components/*`、`App.tsx`、Bo-han design/plan | A-1/A-2/A-3；另補 A-4/A-5/A-6（`error_reason`、scan/boundary flow、accessibility） |
| 前端工程 | `frontend/src/services`、`hooks`、`store`、`types.ts`、`vite.config.ts`、`package.json` | B-1/B-2/B-3/B-4；B-5/B-6 為正面確認 |
| 後端工程 | `src/kai_mind/web`、`core/services`、`core/providers`、CLI/tests/scripts | H-2/H-3/H-4/H-6、M-1～M-14、L 系列 |
| 後端 AI / AI application | `mapping_proposal_service.py`、`llm_proposal_provider.py`、`query_trace_service.py`、`endpoint_call_provider.py` | C-1、H-1、H-7、M-10/M-15；proposal output validation 是強防線 |
| AI infra / observability | provider config、NVIDIA NIM provider、trace/provider boundary、外部 OTel GenAI 參考 | M-10、H-5/H-7；目前沒有模型 serving / queue / gateway infra 實作 |
| RAG / Agent / tool calling | scanner pipeline、mapping proposal、detail scan、query trace、frontend replay | M-15、M-11；目前是 deterministic-first workflow，未發現 open-ended agent 自動執行風險 |
| 資料庫 | `src/kai_mind/storage`、unfinish 26/27 | 已檢查，現況沒有 DB/migration/ORM；未發現資料庫層 runtime 問題 |
| 資安 / privacy | path safety、secret masking、API routes、CORS/middleware、trace egress、tests/env | C-1、H-1～H-7、M-1～M-8、M-14 |
| API / contract docs | `docs/API-GUIDE.md`、`web/schemas.py`、route tests | M-12/M-13：已記錄 drift，**本次不直接修 API-GUIDE**，下一階段由 TODO 修補 |

---

## 1. 總覽摘要（最重要的問題與方向）

> 等級定義：Critical＝資安/資料外洩/系統不可用/重大業務風險；High＝嚴重影響穩定性、正確性、可維護性或 UX；Medium＝明顯可改進但非立即阻斷；Low＝可優化但不急迫。

1. **【Critical】Secret masking 覆蓋度不足，明文機密會寫進交付產物 `ai_system_map.json`。** 連線字串內嵌帳密（`DATABASE_URL=postgresql://user:pass@host`）、`PASSWD`/`PWD`、無底線 `APIKEY`/`MYAPIKEY` 變體都可能偵測不到，且 validation gate 與 masking 同源，無法補位。這直接違反專案「不可在 reports 印出完整 secret」的核心承諾。（C-1）

2. **【High】Query trace 沒有 SSRF egress 控制。** `EndpointCallProvider` preflight 只檢查 URL scheme，`169.254.169.254`（雲端 metadata）、`127.0.0.1`、私網 IP 全部放行（已實跑驗證）。endpoint 值來自被掃描 repo，攻擊者可控。（H-1）

3. **【High】`POST /api/viewer/load` 可對任意本機路徑發起讀取嘗試，且 `error_reason` 直接回傳 Python 例外字串與絕對路徑，形成路徑探測 oracle。** 若目標是 JSON，validation error 也可能回顯部分欄位值；違反「錯誤回應不可含 exception string / 絕對路徑」。（H-2）

4. **【High】兩個「正常輸入讓整個工具崩潰」的可用性問題。** docker-compose 的 `volumes` / `env_file` 等非 environment 欄位未統一遮罩，含 secret-like 片段時會在 validation 階段造成 build 失敗；非 UTF-8 的 `.gitignore` 會在 inventory 階段中斷 scan，非 UTF-8 `.env` 會讓 config provider 整體失敗。作為「Release Readiness Gate」，自己先崩潰會嚴重損害可信度。（H-3、H-4）

5. **【High】測試與 CI 的安全/品質治理缺口。** `tests/web` 多數測試會透過 `create_app()` 讀取 process CWD 的 `.env` / process env，可能把真實 provider 或 credential 帶進測試程序，測試結果也會依賴本機環境；`.github/workflows/` 為空，完全沒有 CI gate。（H-5、H-6）

6. **【High，條件式】`.env` 從 process CWD 讀取的信任邊界問題。** 若 KAI-Mind 以 CWD = 被掃描 repo 執行，且 mapping proposal provider 被啟用並被呼叫，惡意 repo 可放 `.env` 影響 NVIDIA provider / endpoint 邊界。這不是一般 map build 自動外洩，但前提成立時會變成資料外送風險。（H-7）

7. **【Medium】掃描入口缺乏路徑/資源邊界。** `projects/import`、`map/build`、CLI `map` 對 `project_path` 零驗證，可掃 `/`、`~/.ssh`；`output` 參數可寫任意目錄；無檔案總數上限（大 repo 記憶體無界）；`map/build` 與 CLI 還繞過 scan boundary gate。（M-1、M-2、M-6）

8. **【Medium】AI 子系統缺乏可觀測性與輸入隔離。** AI 呼叫完全沒有 logging（prompt/token/cost/失敗原因都無法追蹤）；evidence packet 的部分欄位未遮罩、prompt 把不可信 JSON 直接嵌入而無結構化隔離。緩解：output validation（schema + evidence id allowlist + slot allowlist + pending-only）是強防線。（M-10、M-15）

9. **【Medium】前後端 contract drift 與測試缺口。** `MapBuildResult.error` 文件寫 `string` 實際是物件；404 錯誤碼風格不一致（`Project not found` vs `project_not_found`）；多條 route error path 與 `safe_log_event`（遮罩最後防線）無測試。（M-12、M-13、M-14）

10. **【Medium】前端 API 模式韌性不足。** `fetch` 無 timeout/AbortController，後端不回應時會永久停在 loading；build 主 chunk 1.56MB 偏大。正面：無跨站腳本注入風險（全 src 無危險 HTML 注入 API、無 `eval`）、API 失敗不偷偷 fallback sample。（M-16、M-17）

---

## 2. 檔案檢查清單

> 標示「✅ 無明顯問題 / ⚠️ 有發現」。完整逐項在詳細發現檔。

### 後端 core services（`src/kai_mind/core/services/`）

| 檔案 | 是否發現問題 | 主要觀察 |
|---|---|---|
| `secret_masking_service.py` | ⚠️ | C-1 覆蓋度不足（DSN/變體 key）、M-7 短 secret 部分遮罩 |
| `system_map_validation_service.py` | ⚠️ | M-8 secret 偵測與 masking 同源、cross-ref 驗證本身扎實 |
| `project_scan_service.py` | ⚠️ | M-6 無檔案總數上限；provider failure isolation 本身正確 |
| `map_build_service.py` | ⚠️ | H-3 normalize/validate 外無 try/except，validation 失敗冒泡 |
| `scan_boundary_review_service.py` | ⚠️ | `_reject_unsafe_payload` 拋 ValueError 在上層未必被攔 |
| `path_safety_service.py` | ⚠️ | M-4 容器路徑前綴缺漏、L-8 `is_project_relative_posix_path` 較寬鬆 |
| `query_trace_service.py` | ⚠️ | M-11 `_summary` 遞迴/無 size limit；masking 摘要設計本身良好 |
| `system_map_normalize_service.py` | ⚠️ | L-9 `not_configured_slots` 恆 0、`secret_masking_applied` 脆弱啟發式 |
| `mapping_proposal_service.py` | ✅(設計良好) | output validation 強；L-3 race condition |
| `manual_mapping_service.py` | ✅ | evidence overlay 有 live evidence 檢查 |
| `viewer_session_service.py` | ⚠️ | H-2 `load_map` 把 exception string 放進 error_reason |
| `markdown_summary_service.py` | ✅ | 輸出再過 mask_text |
| `component_detection_service.py` / `endpoint_detection_service.py` / `flow_derivation_service.py` / `risk_hint_service.py` / `rag_template_service.py` / `logging_service.py` | ✅ | 邏輯健全；`safe_log_event` 缺直接測試（M-14） |

### 後端 providers（`src/kai_mind/core/providers/`）

| 檔案 | 是否發現問題 | 主要觀察 |
|---|---|---|
| `endpoint_call_provider.py` | ⚠️ | H-1 SSRF：preflight 只驗 scheme |
| `docker_compose_provider.py` | ⚠️ | H-3 volume/port/image/env_file 未遮罩 + 崩潰 |
| `config_parse_provider.py` | ⚠️ | H-4 `.env` `read_text` 無 try/except；YAML 用 safe_load ✅ |
| `filesystem_provider.py` | ⚠️ | H-4 `.gitignore` 非 UTF-8 崩潰；symlink/skip 防護正確 ✅ |
| `code_pattern_provider.py` | ✅ | per-file try/except、250KB 上限、path 解析防護正確 |
| `dependency_manifest_provider.py` | ✅ | 解析例外收斂為 ParseIssue |
| `llm_proposal_provider.py` | ⚠️ | M-10 無 logging、L-1 無 backoff/circuit breaker |
| `output_artifact_provider.py` | ⚠️ | M-2 寫入位置受 `output` 參數控制；timestamp 防覆寫正確 |

### Web layer（`src/kai_mind/web/`）

| 檔案 | 是否發現問題 | 主要觀察 |
|---|---|---|
| `routes/viewer_routes.py` | ⚠️ | H-2 任意路徑讀取嘗試 + oracle |
| `routes/trace_routes.py` | ⚠️ | H-1 SSRF 入口、M-3 invalid_trace_config 洩漏 exception |
| `routes/map_routes.py` | ⚠️ | M-1 繞過 boundary、`/api/map/report` 路徑安全 ✅ |
| `routes/scan_routes.py` | ⚠️ | M-9 違反 thin-adapter、M-13 404 detail 風格不一致 |
| `routes/project_routes.py` | ⚠️ | M-1 import 路徑零驗證 |
| `routes/detail_scan_routes.py` / `mapping_routes.py` / `mapping_proposal_routes.py` | ✅(設計良好) | thin adapter、error handling 一致；M-14 部分 error path 無測試 |
| `middleware.py` | ✅ | 413（實算 bytes）、500 遮罩正確 |
| `schemas.py` | ✅ | `extra="forbid"` 一致；M-2 `output`/`project_path` 為自由字串 |
| `session_store.py` | ⚠️ | M-5 無上限成長、L-6 併發無鎖；project_id uuid4 不可預測 ✅ |
| `app.py` | ⚠️ | H-5 預設讀 `.env`、L-5 host binding 未強制 |

### 前端（`frontend/src/`）

| 檔案 | 是否發現問題 | 主要觀察 |
|---|---|---|
| `services/viewerApi.ts` | ⚠️ | M-16 `fetch` 無 timeout；Zod parse 驗證 ✅ |
| `hooks/useViewerPayload.ts` | ✅ | `retry:false`、staleTime 合理 |
| `hooks/useScanProgress.ts` | ✅ | EventSource cleanup 正確；onError 顯示 mock 警告 |
| `store/viewerStore.ts` | ✅ | 狀態清楚；無 project/scan/boundary lifecycle（符合現況） |
| `App.tsx` | ⚠️ | state matrix 誠實；interval cleanup 正確；M-17 bundle |
| `types.ts` | ⚠️ | B-2 互動 lifecycle typed coverage 不足；`ai_system_map` 有 typed subset 但 detail/proposal/project-scan lifecycle 仍偏寬鬆 |
| `components/StateOverlay.tsx` | ✅ | API 失敗不偷偷 fallback sample（誠實） |
| `components/DataSourceControl.tsx` | ✅ | 無注入風險；API URL 受控於 fetch |
| `components/*.tsx`（其餘） | ✅ | 全 src 無危險 HTML 注入 API、無 `eval`（已 grep 確認） |
| `utils/format.ts` / `utils/graph.ts` | ✅ | 純顯示 helper |

### CLI / tests / scripts / docs

| 項目 | 是否發現問題 | 主要觀察 |
|---|---|---|
| `cli/*.py` | ⚠️ | thin adapter ✅；M-1 繞過 boundary、L-10 timeout 無界、L-15 檔名不一致 |
| `tests/` (435 個測試) | ⚠️ | H-5 讀本機 `.env`、M-14 error path 缺測試、L-11/L-12 路徑問題 |
| `scripts/trace_*.sh` | ✅ | 17 endpoint 一對一、`set -euo pipefail`、cleanup trap；M-5b port 假設 |
| `docs/API-GUIDE.md` | ⚠️ | M-12 error 型別 drift、M-13 404 風格 |
| `README.md` | ⚠️ | L-14 READY/RISKY 未實作、未提 CLI/API-GUIDE |
| `.github/workflows/` | ⚠️ | H-6 空目錄，無 CI |
| `pyproject.toml` / `.gitignore` | ✅ | 依賴有 pin + uv.lock；`.env` 已 ignore；L-16 mypy 無上限 |

---

## 4. 跨分類問題

| 問題 | 影響分類 | 來源引用 | 風險 | 建議 |
|---|---|---|---|---|
| Secret masking 漏 → 寫進 canonical JSON → 前端顯示 → log | 後端AI/資安/後端/UI | `secret_masking_service.py:10-86`、`system_map_validation_service.py:135-145` | Critical | 補 DSN/變體 marker + URL userinfo pattern；validation gate 加異源偵測 |
| SSRF：endpoint 來自掃描結果 → trace 對內網/metadata 發請求 | 後端AI/資安 | `endpoint_call_provider.py:141-165`、`trace_routes.py:47-53` | High | 解析 IP 擋 loopback/private/link-local + opt-in allowlist |
| 任意路徑：import/build/CLI 無驗證 + 繞過 boundary + 預設帶 snippet | 後端/資安/UX | `project_routes.py:26-30`、`map_routes.py:19-28`、`project_scan_service.py:100` | Medium | 路徑存在性/目錄/scope 驗證；map/build 套 gate 或預設 no_snippets |
| Contract drift：`error` 型別、404 風格 → 前端解析錯誤 | 後端/前端/文件 | `map_build.py:28-38` vs `API-GUIDE.md:206-217`；`scan_routes.py:53` | Medium | 更新文件 + route 測試鎖 contract |
| 測試依賴本機 `.env` + 無 CI → 安全/品質 gate 失效 | 資安/後端/DX | `app.py:96-104`、`.github/workflows/`(空) | High | conftest 隔離 env_file；補最小 CI（含 Windows job） |
| 前端把 `ai_system_map` 當 `record/passthrough` + 無 test runner | 前端/UI | `types.ts:98-107`、`package.json`(無 test) | Medium | 為互動 lifecycle 補 typed schema 與 Vitest（對應 unfinish 20a/21a/24b/Bo-han 07） |

---

## 5. 優先修正路線圖

### 立即處理（Critical / High）
1. **C-1 Secret masking 補洞** — 角色：後端/資安。補 `PASSWD/PWD/CREDENTIAL/PRIVATE_KEY/ACCESS_KEY/CLIENT_SECRET/SESSION/COOKIE` marker、key marker 正規化掉底線、新增 URL userinfo pattern。驗收：fixture 含 4 種 case，斷言 `ai_system_map.json` 無明文 + `mask_text` parametrized 單元測試。風險：marker 太寬可能誤遮正常值（需配合 M-8 異源偵測）。
2. **H-1 SSRF egress 控制** — 角色：後端AI/資安。`EndpointCallProvider` 解析 host→IP，擋 loopback/link-local/private，預設僅 allowlist；保留 localhost 給本地 LLM 時要明確 opt-in。驗收：對 `169.254.169.254`/`127.0.0.1:22`/私網斷言 `query_sent=False`。
3. **H-2 viewer/load 路徑封閉 + 錯誤碼穩定化** — 角色：後端/資安。限制在 session output allowlist；`error_reason` 改穩定碼不嵌 `str(exc)`。
4. **H-3 / H-4 崩潰修復** — 角色：後端。compose 非 env 欄位過 mask；`build_inventory`/`read_text` 加 `errors="replace"` 或 try/except 降級；`MapBuildService` 在 normalize/validate 外加結構化錯誤處理。
5. **H-5 / H-7 測試與 `.env` 隔離** — 角色：後端/資安/DX。conftest autouse fixture 強制 env_file 指向不存在路徑；文件化「CWD 不可為被掃描 repo」或改成不從 CWD 讀 `.env`。
6. **H-6 最小 CI** — 角色：DX。`uv sync` + ruff + mypy + pytest，matrix 含 ubuntu + windows。

### 短期處理（Medium）
- M-1 掃描入口路徑驗證與 scope；M-2 `output` 封閉在受控根；M-3 trace config 錯誤碼穩定化；M-4 補容器路徑前綴；M-5 session store 上限/eviction；M-6 檔案總數上限；M-9 scan_routes 編排下沉 service；M-10 AI 呼叫 logging；M-11 trace response size/遞迴防護；M-12/M-13 文件與錯誤碼一致化；M-14 補 error path 與 `safe_log_event` 測試；M-15 evidence packet 欄位遮罩 + prompt 結構化隔離；M-16 前端 fetch timeout；M-17 bundle 拆分檢視。

### 中期處理（架構/可觀測性/測試覆蓋）
- M-8 validation gate 異源 secret 偵測（治本）；前端互動 lifecycle 的 typed schema + Vitest（對應 unfinish 20a/21a/24b 與 Bo-han Task 7）；AI 子系統的 trace/cost 觀測（對齊 OpenTelemetry GenAI 慣例，注意該規範仍 Development 狀態）；L 系列收斂。

---

## 6. 最終結論

### 目前系統最大的 3 個風險
1. **Secret masking 覆蓋度不足（C-1）** — 直接打到產品最核心承諾（read-only + 不洩 secret），且已實證明文寫入交付產物。
2. **Query trace SSRF（H-1）** — 對 local-only + 無 auth 的工具，opt-in trace 仍可被惡意 repo 導向雲端 metadata / 內網。
3. **「正常輸入導致崩潰」（H-3/H-4）** — Release Readiness Gate 自己對合法 compose / 非 UTF-8 檔崩潰，可信度受損。

### 最應優先修正的 5 件事
1. C-1 secret masking 補洞（含 M-8 異源偵測作為治本）。
2. H-1 SSRF egress 控制。
3. H-3 / H-4 崩潰修復 + `MapBuildService` 結構化錯誤處理。
4. H-2 viewer/load 路徑封閉與錯誤碼穩定化（連帶 M-3）。
5. H-5/H-6 測試隔離 + 最小 CI（讓上述修補有 regression 防線）。

### 已經做得不錯的地方
- 架構分層清楚：route/CLI 多為 thin adapter，core services 是共用核心（`MapBuildService.build()` 兩端共用）。
- `mapping_proposal_service` 的 LLM output validation 是教科書級防線（schema + evidence id allowlist + slot allowlist + secret check + pending-only），符合 OWASP「把 LLM 輸出當不可信、在 deterministic code 驗證」。
- YAML 一律 `safe_load`、httpx redirect 預設關閉、API key 只在 header、provider failure isolation、symlink-outside-root 防護、JSON `sort_keys` 決定性輸出、`extra="forbid"` 防 contract 漂移、413 以實際 bytes 計算、500 遮罩——這些安全基本功都做對了。
- 既有 435 個測試、ruff、mypy strict 全綠，secret masking / schema contract / cross-platform path 都有針對性測試。

### 要達到可上線 / 可擴充還需補齊
- secret masking 與 SSRF 兩個安全洞補上 + 異源第二道防線。
- 「正常輸入不可讓工具崩潰」的韌性（結構化錯誤處理 + failure isolation 涵蓋 inventory 階段）。
- AI 子系統可觀測性（logging/trace/cost）與輸入隔離（spotlighting / 結構化 delimiter）。
- CI gate（含 Windows）+ 測試環境隔離，讓品質與安全可被自動把關。
- 前端互動 lifecycle 的 typed contract 與 test runner（對應既有 unfinish issue，不在本次修補範圍）。

---

## 7. 外部來源（最佳實踐建議，附查詢日期 2026-06-12）

- OWASP Top 10 for LLM Applications 2025（LLM01 Prompt Injection 等）— https://owasp.org/www-project-top-10-for-large-language-model-applications/ ；OWASP LLM Prompt Injection Prevention Cheat Sheet — https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html
  - 對應：M-15（把不可信內容與指令分離、輸出格式驗證、最小權限、人工確認）；佐證 `mapping_proposal_service` 的 output validation 是正確方向。
- NCC Group, Analyzing Secure AI Design Principles（2025）— https://www.nccgroup.com/research/analyzing-secure-ai-design-principles/
  - 對應：M-15（guardrails 不足以防 prompt injection，需在執行環境做 data/code 分離）。
- SSRF 2026 防護（allowlist + 解析 IP 擋 loopback/private/link-local/metadata + 不跟隨 redirect + IMDSv2）— APIsec / Invicti / AuditCore / Legba（2026）
  - 對應：H-1（query trace egress 控制）。
- OpenTelemetry GenAI Semantic Conventions（Status: Development，2026）— https://opentelemetry.io/docs/specs/semconv/gen-ai/
  - 對應：M-10（AI 觀測性；採用時需保留版本隔離層，因規範仍會變動）。

> 註：以上為「外部最佳實踐建議」，與 repo 實際觀察分開。本報告的所有問題定級以 repo 實際程式碼與實跑驗證為準，外部來源僅作為修補方向的依據。
