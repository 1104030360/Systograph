# 2026-08-10 後端 build-scoped 下載端點與退役（Stage 2）REP

- 對應 TODO：`docs/work/Timmy/schedule/todo/2026-08-10-build-scoped-report-download-TODO.md`
- 分支：`main`（不 commit，改動留在 working tree）
- 對應計畫：`download.md` Task 1–4（端點、測試、退役、契約文件）

## 實作邏輯

1. **路徑不過牆**：新端點只收 `build_id` + 白名單檔名；
   `build_id → manifest → map_markdown_path` 全在 server 端解析，回應只有
   檔案 bytes 與 headers。白名單是參數通往檔案系統的**唯一橋**，白名單外
   的檔名（含 traversal 樣式）從不觸碰 filesystem，天然免疫 path traversal。
2. **零新儲存**：複用既有 `MapBuildQueryService.get(build_id)` 與
   manifest 還原，不新增服務、不新增 app.state。
3. **硬退役**：`GET /api/map/report` 是 process-wide「全域最新」語意
   （會跨 build、甚至跨 project 給錯檔），依 #277 前例直接移除，不留
   deprecated 過渡；前端從未接上，風險受控。
4. **TDD**：每步先寫失敗測試（紅）再實作（綠），退役側先寫 404 斷言
   （路由還活著時是紅的）再刪程式碼。

## 步驟與產出

### Task 2：新端點 + 測試

- `src/systograph/web/routes/map_build_routes.py`：
  `GET /api/map-builds/{build_id}/artifacts/{file_name}`。
  白名單常數 `DOWNLOADABLE_BUILD_ARTIFACTS`（3-tuple：正規檔名、manifest
  欄位、media type）。檢查順序固定：白名單（404 `artifact_not_found`）→
  build 查詢（404 `build_not_found`）→ 檔案可用性（404
  `artifact_not_available`）。`?download=true` 時加
  `Content-Disposition: attachment; filename="ai_system_map.md"`
  （檔名取自白名單表，永不取自請求參數）。
- `tests/web/test_map_build_artifact_routes.py`：13 個行為導向測試——
  build 隔離（同 project 兩個 build，各自下載到各自的檔、與磁碟 byte
  一致）、404 三態、header 行為、**所有回應（成功與錯誤）不含 absolute
  path**、CRLF byte-fidelity 迴歸測試。

### Task 3：退役

- 刪 `src/systograph/web/routes/map_routes.py` 與 `app.py` 的註冊。
- `session_store.py`：`latest_build_result` 自 Protocol 與兩個實作移除，
  `_latest_build_result` 死欄位一併刪；`PersistentSessionStore.
  save_build_result` 保留為有註解的 no-op（Protocol 仍被
  `save_committed_build_projection` 呼叫；durable 持久化本來就由 build
  pipeline 寫 repository）。
- `tests/web/test_retired_endpoints.py` 補第 5 組退役常數與 404 斷言；
  boundary test 改綁 `map_build_routes`；原 `test_map_routes.py` 刪除，
  其中無關的 CORS 測試搬到 `test_local_api_hardening.py`、SSE 測試搬到
  `test_project_scan_routes.py`（兩支皆無等價既有斷言，整支搬移，涵蓋
  不縮水）。
- `scripts/trace_map_report.sh` **更名** `trace_map_build_artifact.sh`
  （`git mv`）並重寫為：import → scan → 取 `build_id` → 打新端點驗證
  200 與 attachment header；`--no-setup` 改為誠實語意（對不存在的
  build 斷言 404 `build_not_found`——舊版 usage 宣稱預期 404 但實際上
  任何狀態碼都放行，這個謊一併修掉）；`trace_all.sh` 清單同步。

### Task 4：契約文件

- `docs/API-GUIDE.md`：端點總覽表換行、新端點完整章節（含 404 三態表、
  curl 範例、routing-level `%2F` 拒絕的說明）、「已無 process-wide 端點」
  敘述、退役清單補第 5 筆（全檔唯一一處刻意保留的舊端點字面，與退役測試
  常數互為佐證）、全域 404 表補 `artifact_not_found` /
  `artifact_not_available` / `build_not_found`（最後一個是既有缺漏，
  順手補上）。
- `frontend/API_CONTRACT.md`：新增「Build Artifact Download」章節
  （前端視角：何時打、錯誤碼分類處理、422 例外說明）。
- `docs/MODEL-CONTRACT.md:165`：render 產物清單的端點引用更新。

## 遇到的問題與解法

1. **Windows byte-identity（reviewer 抓到）**：`read_text()` 會做
   universal-newline 轉換，Windows 上磁碟是 CRLF、回應變 LF，破壞
   §6.1「與磁碟 byte 一致」驗收與 manifest 記錄的 digest。改
   `read_bytes()` 原樣送出，並先寫 CRLF 迴歸測試證明舊寫法會爆。
2. **attachment 檔名來源**：原寫法從請求參數插值（值相等所以安全，但
   一次 lookup 正規化就會破功）。改為白名單 3-tuple 帶正規檔名，header
   永不含請求文字。
3. **「Every error is a 404」誤述（reviewer 對 live app 實測抓到）**：
   FastAPI 對 `?download=banana` 回 422 且 `detail` 是 array——
   API_CONTRACT 補 422 說明子句。
4. **退役清單 vs 0-hit 掃描的張力**：裁決為「掃描是 coverage 證明、
   不是內容禁令」——退役清單本來就該具名列出退役路徑（與退役測試常數
   同理），計畫 §6.4 的 carve-out 同步擴充第三個成員。
5. **既有死分支的正確歸因**：`save_committed_build_projection` 的
   except 分支在本次改動**之前**就已無法在 production 觸發（舊 body 是
   純屬性賦值、不會 raise）——不是本次造成的退化，記錄為既有現象。

## 測試方式與結果

- TDD 紅綠證據逐 task 記錄於 SDD workspace 報告。
- 全套 gate：`uv run pytest` **1146 passed, 1 skipped**（起點 1135：
  +13 新端點測試、+2 退役斷言、−4 舊 `/api/map/report` 測試；CORS/SSE
  兩支搬家保留、淨 0）；`ruff check`、`ruff format --check`、
  `mypy src tests`（strict）全綠。
- trace script 對本機後端實測 3 條路徑（inline / `--download` /
  `--no-setup`）全過；`bash -n` + shellcheck 0 warnings。
- 驗收 grep：`rg "api/map/report" src tests scripts` 僅剩退役常數；
  `rg latest_build_result` src/tests/scripts 0 筆；契約文件四樣式掃描
  僅剩 API-GUIDE 退役清單 1 筆刻意保留。
