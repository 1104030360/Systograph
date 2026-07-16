# Phase2 Scan Inventory Policy 與單次選擇 TODO

## 目標

完成 Plan 19 與 Plan 20 backend scope：先把 KAI-Mind 預設路徑規則收斂到
`scan_inventory_rules.toml`，再提供 metadata-only preflight、exact file／bounded directory
單次選擇、不可覆寫的 filesystem safety、snapshot provenance 與實際 API trace。

## 實作邏輯

1. `scan_inventory_rules.toml` 是預設 include／exclude policy 的唯一來源。
2. `FilesystemProvider` 只負責候選列舉、路徑安全與 inventory materialization；所有 downstream
   providers 只讀同一份 final `FileInventory`。
3. Preflight 僅讀 path metadata、Git ignore 與 catalog，不讀候選檔內容。
4. 使用者 decision 只影響當次 scan；優先序固定為 hard safety、exact file、最深 directory、
   ancestor directory、default policy。
5. Pending、stale 或 invalid selection 不得建立 `scan_id`、snapshot、build 或 output artifact。
6. 新契約以 additive optional 欄位保存，legacy snapshot 必須仍可讀。

## 階段與步驟

### 階段 1：Repo truth check 與計畫校正

- [x] 讀取 Phase 6、Plan 19、Plan 20、AGENTS.md、Linus 規則與 canonical contracts。
- [x] 建立 baseline：`850 passed`、ruff clean、mypy clean。
- [x] 逐檔更新 Plan 19，再更新 Plan 20；移除 frontend-deferred 與 Task 0 的矛盾。

### 階段 2：Plan 19 policy catalog

- [x] 先寫 loader、schema、digest、resource packaging 與 invalid catalog 的 failing tests。
- [x] 實作 frozen catalog model、loader、ordered matcher 與 packaged TOML。
- [x] 先寫 Git／recursive／fallback parity 與 safety tests，再移除 Python hidden path defaults。
- [x] 保存 policy schema、digest、source mode、audit 與 run digest到 inventory／snapshot。

### 階段 3：Plan 20 metadata-only preflight

- [x] 先寫 candidate、metadata fingerprint、directory manifest 與 bounds tests。
- [x] 實作 ignored candidate enumeration、exact path resolver 與 bounded directory expansion。
- [x] 先寫 API／service failing tests，再實作 stateless preflight endpoint與 typed error surface。

### 階段 4：單次 decision overlay 與 snapshot

- [x] 先寫 exact／directory precedence、stale、duplicate、hard block 與 no-content-read tests。
- [x] 實作 post-decision safety、final inventory、selection audit／summary／digests。
- [x] 驗證 Apply 重用 snapshot、Rescan 重新 preflight，且 target repo完全不變。

### 階段 5：Scripts、文件與驗收

- [x] 更新 API／MODEL／frontend contract sample 與 Phase2 pipeline文件。
- [x] 更新 scan trace scripts，加入 typed 422、preflight與directory selection實際 API流程。
- [x] 更新 `docs/work/Timmy/learn/architecture.md` ASCII全景圖。
- [x] 執行 targeted、full pytest、ruff、mypy、wheel resource smoke與 shell trace／API手動 QA。
- [x] 逐條回查 Plan 19／20 acceptance criteria並完成階段 Report。

## 完成證據

- Backend：final regression `972 passed in 62.15s`。
- Static：ruff clean、strict mypy `181 source files` clean、`git diff --check` clean。
- Packaging：wheel 內含 `scan_inventory_rules.toml`，隔離安裝後成功載入 17 rules。
- Handoff：Step 2 的 8 份 JSON samples 全部通過 current Pydantic validation。
- Manual QA：非法 path 回 typed HTTP 422；happy path preflight／scan 均回 HTTP 200。
- Side effect：E2E 與 shell trace 均確認 target tree unchanged。
- Scope：`frontend/src` 無變更；無 UA runtime；未建立 commit／stage／push。

## 問題與處理摘要

- Candidate 與 final inventory 原本混在同一 provider，改成 metadata-only candidate pipeline 與
  decision 後 materialization。
- Metadata fingerprint 無法單獨消除 TOCTOU，增加 directory-handle safe-open、`fstat` 與同
  handle content hash，snapshot 前再次驗證。
- Directory overlap 可繞過單 scope 上限，preflight 與 submit 都改以 canonical child path 去重
  後重算 aggregate budget。
- Git tracked-missing 與 private／global exclude source 改為 typed、可稽核但不洩漏本機路徑。
- Final wheel probe 首次使用錯誤 JSON 名稱，回讀 loader 後改以真實 packaged TOML 驗證；沒有
  因誤判修改 packaging。

## 本次限制

- 不使用 subagent。
- 不修改 `frontend/src`，也不把 frontend tests／build當 Plan 20 backend DoD。
- 不建立 UA request、adapter、sidecar或 parity integration。
- 不在 target repo寫入任何檔案，也不輸出 secret value或本機 absolute path。
