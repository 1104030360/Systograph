# 前端同步總覽：User-controlled Scan Inventory Selection（2026-07-15）

Last updated: 2026-07-15（補會議釐清：可見範圍、fail closed、5,000 適用範圍）

## 這次新增什麼

Phase2 Step 2 新增「單次 scan inventory review」：使用者可在 scan 前決定 exact file 或
bounded recursive directory path 這次要掃或略過，包含對 `.gitignore`／Git exclude 與 KAI
inventory catalog 的 soft exclusion 做單次覆寫。Directory `scan_this_run`代表其下所有通過
backend hard safety 的regular files，不代表可繞過`.git/**`、symlink、special file或資源上限。

前提是Plan 19的product-owned TOML baseline已先完成：KAI-Mind先提供可獨立運作的推薦掃描
範圍，Frontend再讓使用者依本次需求調配。這不是空白file explorer，也不能在catalog
missing/invalid時用人工選檔取代backend fail-closed。

這不是永久設定，也不會改寫 target repo。Frontend 只負責呈現 backend preflight、收集
`scan_this_run`／`skip_this_run`，再把 decisions 送回 backend；hard safety、final inventory、
snapshot 與 downstream build 都由 backend 擁有。

**Scope freeze：本次 Plan 20 不接 UA。** Frontend task 不等待、不呼叫也不顯示 UA state；
UA request、sidecar、`files[]` adapter與parity由Plan 16後續獨立處理。

## 會議釐清（2026-07-15）— 務必對齊的產品語意

詳細 FAQ 以 Plan 20 §1.5 為準；本節是前端同步包摘要。

### 1. 預設「跳過什麼」仍由 TOML + `.gitignore` 決定

| 層級 | 角色 |
| --- | --- |
| Plan 19 `scan_inventory_rules.toml` | KAI 預設 soft exclude（dependency／build／cache…） |
| 專案 `.gitignore`／exclude | 專案來源控制略過 |
| Plan 20 UI decision | **這一次** exact path／directory 的 soft override |
| Hard safety | 永遠不可覆寫 |

優先序：`hard safety > 使用者這次決策 > TOML／gitignore 預設`。  
Decision **不寫回** TOML、`.gitignore`，也**不是** Manual Mapping。

### 2. 前端不是整庫 checkbox；看到的是 preflight JSON 分區

| 區塊 | 使用者看到什麼 |
| --- | --- |
| Summary | default included／excluded／blocked 等**數量**（一般檔通常不逐檔列出） |
| Needs your decision | 系統主動推的敏感檔（必答） |
| Excluded by default | soft-excluded 分頁列表（可選這次掃） |
| Add exact path | 使用者主動查 file／folder 後才出現可決策列 |
| Cannot be scanned | hard block／missing／over-limit 摘要（不可勾掃） |

### 3. Fail closed＝超過安全上限不「只掃前 N 筆」

Directory 超過 **5,000 files／500MB／64 depth**（或多目錄 aggregate 超限）時：

- **不建立可批准 proposal**／整個 preflight 可 422；
- **不得** silently truncate 前 N 筆再假裝整包成功；
- 使用者改選較小 subdirectory。

「分頁 Load more」只用於瀏覽 soft-excluded list，與 directory 全選的 fail closed 無關。

### 4. 5,000 上限防什麼、不防什麼

| 情境 | 會不會因 5,000 失敗 |
| --- | --- |
| 對 `node_modules/` 等預設排除的大目錄做 recursive `scan_this_run` | **會**（主要防護） |
| 對超大目錄做 recursive `skip_this_run` | **也會**（scan／skip 都要完整 manifest） |
| 大目錄已被 soft exclude，使用者**不展開** | **不會**（維持預設略過） |
| Repo 內預設會掃的安全檔加總 >5,000（例如 `src/` 有 8,000 個 `.py`） | **不會**（上限不套在整庫 default inventory） |

一句話：5,000 是「**directory 遞迴決策要完整列清**」的成本上限，不是「整個專案最多 5,000 檔」。

### 5. 與 Manual Mapping 的差異

- Inventory selection：掃**前** I/O 授權 → per-run overlay → 才開始讀檔建 map。
- Manual Mapping：掃**後** component／slot 語意 → 走 `/api/mappings`。
- **不要**把 file／directory decision 存進 Manual Mapping store。

## Source of truth

- [Plan 19：Inventory Selection Policy Catalog](../../Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-track-d-inventory/19-add-scan-inventory-rules-toml.md)
- [Plan 20：User-controlled Scan Inventory Selection](../../Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-track-d-inventory-review/20-add-user-controlled-scan-inventory-selection.md)
  （含 §1.5 產品語意澄清、§5.4 5,000 bound scope）
- `docs/API-GUIDE.md`（Plan 20 Task 9 完成後成為 HTTP canonical contract）
- `docs/MODEL-CONTRACT.md`（Plan 20 Task 9 完成後成為 lifecycle canonical contract）
- `frontend/API_CONTRACT.md`（Plan 20 Task 9 完成後成為 frontend integration contract）

Plan 尚未實作期間，Plan 19擁有TOML baseline、loader與
`inventory_rules_unavailable`／`inventory_rules_invalid`；Plan 20擁有preflight、selection欄位、
enum與lifecycle。實作完成後若本同步包與canonical API/model docs衝突，以canonical docs為準。

## Frontend work item

- [Frontend：Scan Inventory Review 與 per-run override](./frontend-inventory-selection-review.md)

## Backend / Frontend ownership

| 領域 | Backend | Frontend |
| --- | --- | --- |
| TOML baseline readiness | 驗證Plan 19 schema/catalog、fail closed並提供version/digest | 不讀TOML、不判斷完整度、不提供繞過UI |
| Candidate enumeration | Git/recursive/ignored/exact file/directory manifest | 不自行讀 filesystem |
| Policy outcome | included/soft-excluded/hard-blocked/missing | 依 payload分組渲染 |
| Safety | root/symlink/type/size/binary/stale checks | 顯示 typed reason，不能 override |
| Decision | 驗證path/scope/fingerprint/action並套overlay | 收集並送explicit scope decisions |
| Final inventory | 唯一 owner，供current providers使用；UA deferred | 不自行推導或保存 |
| Persistence | completed snapshot audit/digests | preflight/choices只留當次記憶體 |
| Result | build publish + viewer payload | completed後走既有viewer refresh |

## Integration sequence

```text
Plan 19 non-UA baseline gate
  -> pass: Import project
  -> fail: no frontend integration start

Import project
  -> POST scan-preflights
       -> inventory_rules_unavailable / inventory_rules_invalid
            -> baseline_error; no review controls; never POST scans
       -> success (zero candidates is still valid)
  -> render prepared baseline in Review scan scope
  -> user decisions / exact file-directory lookup
       -> exact file: review one file
       -> exact directory: review bounded recursive manifest summary
  -> POST scans(preflight_request_id, boundary_decisions)
       -> pending: keep review open
       -> stale: refresh preflight and re-review changed targets
       -> completed: discard one-run state and refresh latest viewer payload
       -> error: show typed error; never invent completed state
```

## Delivery checklist

- [ ] Plan 19 non-UA TOML baseline gate已通過；default policy version、digest與audit可用。
- [ ] Frontend只用typed success/error判定baseline health；zero candidates不等於catalog failure。
- [ ] Backend preflight request/response schemas與sample payload已可用。
- [ ] `POST /api/scans`接受optional `preflight_request_id`。
- [ ] Pending response無`scan_id`；frontend Zod把`scan_id`改為optional。
- [ ] Existing `BoundaryDecisionModal`延伸成單一review flow，不新增第二套modal。
- [ ] Opening copy說明KAI已提供推薦baseline，使用者只做one-run調配。
- [ ] Catalog missing/invalid時fail closed，不顯示blank inventory authoring UI。
- [ ] Exact `inventory_rules_unavailable`／`inventory_rules_invalid`進`baseline_error`且永不呼叫scan。
- [ ] Default rows保留backend source/reason，不把project ignore誤標成KAI catalog rule。
- [ ] Required、soft-excluded、exact file/directory override、hard blocked/missing四區可辨識。
- [ ] Reviewable directory顯示bounded counts，並可選scan-all-selectable或skip-all。
- [ ] Directory decision送一筆`selection_scope=recursive_directory`，不在client展開descendants。
- [ ] Directory over-limit copy說明fail closed（非整包成功只掃前N）；引導選較小子目錄。
- [ ] UI／docs不暗示「整庫 default-included >5,000 就不能掃」。
- [ ] Stale refresh只保留相同`target_path + selection_scope + fingerprint`的choice。
- [ ] Cancel/complete都清除preflight與one-run decisions。
- [ ] Completed後沿用existing latest-build/viewer refresh。
- [ ] 本frontend flow沒有UA request、UA state或UA parity dependency。
- [ ] Vitest、RTL、lint、TypeScript build全部通過。

## 不屬於這次工作

- 由Frontend讀取、驗證、補齊或編輯`scan_inventory_rules.toml`；
- catalog failure後提供blank picker、continue-anyway或其他fallback；
- 永久 always scan/never scan preference；
- 修改 `.gitignore`／TOML／target repo；
- runtime glob、follow symlink或unbounded directory recursive selection；
- frontend自行判斷soft/hard safety；
- 把file decision存成Manual Mapping；
- 從preflight資料自行產生map/report；
- 對 directory `skip_this_run` 自行放寬 5,000／bytes／depth（與 scan 共用同一 backend 契約）；
- 提供「只掃／只略過前 N 個檔」的 UI escape hatch。
