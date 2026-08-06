# Explicit Preflight Cutover（前端兩段式掃描 → 退役 implicit preflight 分支）實作計畫

Status: **Phase B 已於 2026-08-07 完成（commit 4d8f5c6）；Phase A 待 FE-1**
（2026-08-05 起草；GitHub issue #277。前置事實查核：現行前端
`projectScanApi.ts` 從未送 `preflight_request_id`，正式前端今天 100% 走 implicit
compatibility 分支——所以退役順序必須是前端先遷移、後端才拆橋）

> **2026-08-07 使用者決策 —— gate 解除，後端先行動工：** 前端會在後端之後補上
> handoff 工作包 FE-1，因此**後端不必等前端上線即可執行 Phase B**。上方「必須
> 前端先遷移」是**排程**約束，就此解除；其技術理由仍然成立，保留下來供判斷
> **合併時機**參考——Phase B 是 breaking change，合併後到 FE-1 上線前，正式前端
> 送不出 `preflight_request_id`，`POST /api/scans` 會全數回 422，這段期間 `main`
> 對前端是壞的，屬已知並接受的代價。

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** #277（umbrella：Web 邊界收斂後端先行，2026-08-07 回填；檔名不改）

**Goal:** 前端改走 Plan 20 設計的 explicit preflight 主路徑（先
`POST /api/projects/{project_id}/scan-preflights` 取得 `preflight_request_id`
與 required proposals → decision UI → 帶單號 + delta decisions 掃描一次），
之後退役 `create_scan` 的 implicit preflight compatibility 分支，讓
`POST /api/scans` 一律要求 `preflight_request_id`。

**Architecture:** 兩段式、跨 repo 邊界的 cutover：Phase A 全在 `frontend/`
（Hardy ownership，走 handoff，不動 `docs/work/Hardy/` 既有 plan）；Phase B 在
backend `web/routes/scan_routes.py` + 契約文件，是 breaking API change，須與
`docs/API-GUIDE.md`、`frontend/API_CONTRACT.md` 同 PR 更新。Preflight token 綁
candidate set / policy digest / safety version，是 stale token 不是
authorization token。

**Tech Stack:** React + zod（frontend service/schema）、FastAPI（backend
分支退役）、pytest web/e2e tests、
`scripts/trace_inventory_selection_preflight.sh`。

---

## Source（判準基線）

- `docs/API-GUIDE.md` §`POST /api/projects/{project_id}/scan-preflights`、
  §`POST /api/scans`、錯誤對照表；`:278`「未傳 `preflight_request_id` 的舊
  client 仍可走 sensitive-file compatibility flow」＝本計畫要退役的段落。
- `docs/work/Timmy/schedule/plan/finish/s1-track-d-inventory-review/20-add-user-controlled-scan-inventory-selection.md`
  ——decision UI 三規則（required 不預選、只送 delta、fingerprint +
  `selection_scope`）與「rescan 必須新 preflight、新 required 必須重新
  explicit decision」的出處。
- `src/systograph/web/routes/scan_routes.py:183-218`——implicit 分支本體
  （含 `requires_boundary_decision` 短路與 `OVERRIDE_NOT_ALLOWED` 守門）；
  同檔 `:228-250` 是 implicit-only 的 stale／changed 自動 re-preflight
  fallback（`if not explicit_preflight and exc.code in {PREFLIGHT_STALE,
  TARGET_CHANGED}`），同屬退役範圍。
- `frontend/src/services/projectScanApi.ts:10-37`——現行 payload 只送
  `project_id` + `boundary_decisions`，無 preflight 呼叫。

## 範圍外（本計畫明確不做）

- **scan_id 作為 primary key 的身份重構**：2026-08-05 使用者決定先擱置，
  project_id 照舊。相關分析另見對話結論（mapping 已透過 evidence subset
  檢查 de facto scan-bound；未來要動再開獨立計畫）。
- **path-digest dedup 移除**：與 restart recovery / mapping 延續性綁定，
  屬身份重構的一部分，同上擱置。
- UA integration（16 系列）與本計畫無相依。

---

## Phase A — Frontend（Hardy ownership；以 handoff 交付）

> **2026-08-06 前端工作已抽出：** 本區段（含全部 Task 細節）已 handoff 至
> `docs/work/Meeting-Sync/meeting_sync_2026_08_06/frontend-web-boundary-refactor-handoff.md`（工作包 FE-1）。後端不執行本區段。
>
> **2026-08-07 更新：** 原本「完成前 Phase B 不得動工」的 gate **已解除**——
> 前端會於後端之後補上，後端不再等本區段上線即可進 Phase B。見文件開頭決策。

### Task 1: preflight service + zod schema

**Files:**
- Create: `frontend/src/services/scanPreflightApi.ts`
- Modify: `frontend/src/contracts/`（新增 preflight response schema）

- [ ] **Step 1: 呼叫 `POST /api/projects/{project_id}/scan-preflights`**
- [ ] **Step 2: zod schema 覆蓋關鍵欄位**——`preflight_request_id`、
  `required_boundary_proposals[]`、`reviewable_excluded_page`
  （含 `next_cursor` 分頁；`reviewable_excluded_limit` 預設 100、上限 200）、
  `summary`、`blocked_summaries`、`warnings`
- [ ] **Step 3: service 單元測試（mock HTTP，含分頁 cursor 迭代）**

### Task 2: 流程反轉——preflight 先行、帶單號掃描

**Files:**
- Modify: `frontend/src/services/projectScanApi.ts`
- Modify: `frontend/src/types.ts`（`scanCreateRequestSchema` /
  `scanCreateResponseSchema` 現行 zod 定義所在）
- Modify: 發動掃描的 hook / 元件（現行接線在 `frontend/src/App.tsx:194-297`）

- [ ] **Step 1: `StartScanOptions` 加 `preflightRequestId`；payload 加
  `preflight_request_id`**
- [ ] **Step 2: 掃描入口改為「preflight → （有 required 則 decision UI）→
  帶單號掃一次」**，取代現行「先掃 → 被 `requires_boundary_decision` 擋 →
  再掃」的兩次請求
- [ ] **Step 3: 無 required 項目時一步直達（preflight 後直接掃）**

### Task 3: Decision UI 遵守 Plan 20 三規則

**Files:**
- Modify: boundary decision UI 元件

- [ ] **Step 1: required 項目不預選；全部有 explicit decision 才可 submit**
- [ ] **Step 2: decisions 只送 delta（explicit 改動 + required 回答），
  不 echo 整份 candidate list**
- [ ] **Step 3: 每筆 decision 帶 `fingerprint`（directory 用 manifest
  fingerprint）與 `selection_scope`**

### Task 4: stale token 與 fallback 處理

- [ ] **Step 1: 接住 409 `inventory_preflight_stale` /
  `inventory_selection_target_missing` / `inventory_selection_target_changed`
  → 自動重新 preflight → 重新收集 decisions（不得自動沿用舊答案；新
  required 必須重新 explicit 決定）**
- [ ] **Step 2: rescan 一律開新 preflight（不重用上次單號與 decisions）**
- [ ] **Step 3: 保留並修好 `requires_boundary_decision` 處理邏輯**——candidate
  set 有變動時會先撞 409 `inventory_preflight_stale`（`revalidate` 重算並比對
  單號，`inventory_preflight_service.py:132-137`）；帶單號時這個 status 來自
  `InventorySelectionMaterializer`（`inventory_selection_materializer.py:79-94`）：
  universe 內仍有 `decision_required` 卻沒有對應決策（delta 漏答，或 directory
  manifest 展開帶進來的項目）就回 pending。此 status 從主流程降級為例外路徑，
  但不可刪。另須修 `frontend/src/types.ts:474`——`scanCreateResponseSchema` 的
  `scan_id` 目前是必填，但 pending response 不含該欄位（`ScanCreateResponse`
  的 `exclude_if`），zod 會直接拋錯，現行這條路徑其實走不通
- [ ] **Step 4: 元件／hook 測試覆蓋 stale → re-preflight 循環**

---

## Phase B — Backend（2026-08-07 起 gate 解除，可立即動工；原為「Phase A 上線後」）

### Task 5: 退役 implicit 分支（breaking change）

**Files:**
- Modify: `src/systograph/web/routes/scan_routes.py`
- Modify: `docs/API-GUIDE.md`、`frontend/API_CONTRACT.md`
- Modify: `tests/web/`、`tests/e2e/`（現行有 17 個不帶單號的 `/api/scans`
  呼叫點，散在 11 個測試檔）

- [x] **Step 1: 刪除 `scan_routes.py:183-218` implicit 分支與 `:228-250`
  implicit-only re-preflight fallback；未帶 `preflight_request_id` 一律回 422
  穩定 code（新增 code 併入錯誤對照表）；同步移除隨之失效的 `create_scan`
  參數 `boundary_service` / `preflight_service`，以及 `InventoryPreflightRequest`
  與 `InventorySelectionErrorCode` import（兩者僅 implicit 分支在用，留著會被
  ruff 擋）**
- [x] **Step 2: 同 PR 刪除 `docs/API-GUIDE.md:278` compatibility flow 段落，
  並把 `POST /api/scans` 的 `preflight_request_id` 更新為必填
  （`frontend/API_CONTRACT.md:185` 現寫成 optional，同 PR 一併改）**
- [x] **Step 3: 更新／移除倚賴 implicit 路徑的測試**——整檔建立在 implicit
  流程上的 `tests/web/test_scan_boundary_routes.py` 與
  `test_inventory_preflight_routes.py::test_legacy_pending_flow_does_not_open_sensitive_candidate_content`
  移除；其餘只是「順手不帶單號」的呼叫點（`test_project_scan_routes.py`、
  `test_mapping_routes.py`、`test_mapping_proposal_routes.py`、
  `test_local_json_restart_recovery.py`、`test_detail_scan_build_binding.py`、
  `test_legacy_mapping_write_rejection.py`、`test_map_build_apply_routes.py`、
  `tests/e2e/test_apply_confirmations_build_lineage.py`、
  `tests/e2e/test_inventory_selection_scan_flow.py` 的 rescan 段）改成先
  preflight 再帶單號；補「未帶單號 → 422」regression test**
- [x] **Step 4: `scripts/trace_inventory_selection_preflight.sh` 全流程驗證**

---

## 驗收標準

1. 前端掃描全程只發一次 `POST /api/scans`，且必帶 `preflight_request_id`
   （devtools / mock transport 可證）。
2. required 項目未收齊 explicit decision 時無法 submit；decisions payload
   只含 delta。
3. 中途改動檔案觸發 409 stale 系列 code 時，UI 自動重新 preflight 並要求
   重新決定，不靜默沿用。
4. Phase B 後：未帶單號的 `POST /api/scans` 回 422 穩定 code；
   `pnpm test` 與 `uv run pytest -m "web or e2e"` 全綠（e2e 目錄同樣有
   implicit 呼叫點，只跑 `-m web` 驗不到）；`docs/API-GUIDE.md` 與
   `frontend/API_CONTRACT.md` 無 compatibility flow 殘留敘述。
5. 全程不動 `docs/work/Hardy/` 既有 plan 文件（前端工作以 Meeting-Sync
   handoff 交付）。
