# User-controlled Scan Inventory Selection 實作計畫

Status: planned（須先通過 Plan 19 non-UA TOML baseline gate；**執行範圍 = Backend only**；
Frontend deferred to Meeting-Sync 2026-07-15）

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` 逐 task 執行，並在每個 task 內遵守
> `superpowers:test-driven-development`。本工作目前明確禁止使用 subagent；除非使用者之後解除
> 限制，所有步驟由同一執行者依序完成。
> **禁止實作 frontend：** 跳過 §10 實作與 Task 7–8；不要修改 `frontend/src`；不要把
> `pnpm test`／lint／build 當完成條件。專注 Python core／web API／pytest／backend contract docs。

**Goal:** 讓使用者在每次 scan 開始前，以 project-relative exact file或directory path決定
「這次要掃」或「這次不掃」；directory path遞迴套用到其下所有可安全掃描的regular files，
並可對`.gitignore`／Git exclude與KAI inventory catalog的 **soft exclusion** 做單次覆寫；
同時保留不可覆寫的filesystem safety，且不修改target repo、`.gitignore`、catalog TOML或
durable manual mapping。

**Architecture:** 新增 metadata-only inventory preflight，先列出 default inventory、可覆寫
排除、必要敏感檔確認與 hard block，再沿用既有 `ScanBoundaryProposal`／
`ScanBoundaryDecisionRequest` 把使用者選擇送回 `POST /api/scans`。Backend 重新 enumeration、
驗證 preflight/fingerprint，套用 per-run in-memory overlay，經 post-decision content safety 後產生
唯一的 final `FileInventory`；本計畫只接到 current Step 3 providers、snapshot 與後續 build，
**不建立、不呼叫、不測試 UA integration**。

**Execution focus（2026-07-15 鎖定）：本計畫執行只做 Backend。** 文中 Frontend／UI／Zod／React
章節僅作為 **HTTP／產品契約參考與 Meeting-Sync handoff**，**不是**本計畫 agent／執行者要實作的
工作項。前端實作另由 `docs/work/Meeting-Sync/meeting_sync_2026_07_15/` 追蹤，待 backend
preflight schema 可用後再開工。

**Tech Stack（本計畫實作）：** Python 3.11、FastAPI、Pydantic v2、Git CLI、
`pathspec.GitIgnoreSpec`、pytest。  
（React／TypeScript／Zod／Vitest／RTL 列於契約參考，**本計畫不實作、不跑 frontend CI 作為
DoD。**）

## 前置前提：TOML product baseline 先完成，使用者再調配

**Plan 20 不是用來補救不完整的規則檔，也不是讓使用者從空白清單自行建立inventory。**
KAI-Mind必須先依[Plan 19](../s1-track-d-inventory/19-add-scan-inventory-rules-toml.md)完成並驗收
product-owned `scan_inventory_rules.toml` baseline；使用者看到的是我們已設定好的推薦掃描範圍，
再依自己的專案需求做本次scan的exact file／bounded directory調配。

這裡的「完整」不是列舉世界上每一種filename，而是Plan 20 Task 0開始前，下列non-UA baseline
contract都已成立：

- Catalog schema、loader、schema version與`inventory_policy_digest`已穩定；missing、invalid、
  unknown field、duplicate id與unsupported version全部fail closed。
- Product支援的dependency、build、cache、generated、model-weight等path categories已有明確default
  action、stable reason、priority與last-match precedence；unmatched path也有deterministic default。
- `scan_inventory_rules.toml`是KAI default path policy唯一source of truth，Python不保留hidden
  default path list。
- Git、recursive與Git-failure fallback共用同一catalog matcher；共同語意、刻意差異與跨平台path
  normalization已有tests。
- 沒有optional runtime override時，baseline仍可產生deterministic default inventory；只有既有
  required sensitive confirmation可以讓流程停在pending review。
- Audit、policy/candidate/run digests與fail-closed error surface可回溯實際使用的baseline版本。
- Filesystem safety仍由Python擁有，不因TOML「完整」而移入catalog。

Plan 19內屬於Plan 16的UA `files[]`／parity handoff不是這個start gate，仍依本計畫的UA scope
freeze延後處理，避免形成`Plan 20 -> Plan 16 -> Plan 20`循環依賴。

Plan 19原本把catalog排除視為不可由當時的boundary review覆寫，並要求若要保留排除候選供使用者
調整必須另開plan；**Plan 20就是該明確follow-up**。它不取代Plan 19 baseline，而是在baseline
驗收後保留`soft_excluded`候選、增加one-run delta lifecycle。沒有Plan 20 decision時，結果仍與
Plan 19 default outcome一致。

```text
Start gate: validated KAI-Mind product-owned TOML baseline
                                      |
                                      v
candidate enumeration -> project/Git-ignore semantics
  -> non-overridable pre-content filesystem safety
  -> apply validated TOML baseline
  -> deterministic default included / soft-excluded outcome
  -> frontend呈現「KAI推薦預設」與原因
  -> user依本次需求調配exact file / recursive directory scope
  -> non-overridable post-decision content/resource safety
  -> one final FileInventory
```

因此，使用者decision的定位固定是 **adjust a prepared baseline for this run**：

- 沒有decision時沿用KAI default outcome，不需要使用者逐檔重建inventory。
- `scan_this_run`／`skip_this_run`只改本次effective selection，不改寫TOML或形成永久偏好。
- Catalog缺失或無效時直接fail closed；不得降級成空白file explorer要求使用者自己補選。
- Runtime overlay可覆寫Plan 20明確保留的`soft_excluded` outcome，但永遠不能覆寫hard safety。

## Global Constraints

- **執行只做 Backend：** 不修改 `frontend/`、不實作 React／Zod／modal／hooks；Frontend 章節僅契約
  參考。前端工作見 Meeting-Sync 2026-07-15。
- Scanner、preflight、decision overlay 全程 read-only；不得改寫 target repo 任何檔案。
- 使用者 decision 是 **one-run selection overlay**，不是偏好設定、manual mapping 或 durable
  policy mutation。
- Plan 19 TOML baseline是所有preflight的必要輸入；catalog missing/invalid時不得用runtime
  selection或frontend path input繞過fail-closed。
- 優先序固定為：`hard safety > explicit per-run user decision > source/catalog default`。
- 只有 `soft_excluded` 可被 `scan_this_run` 重新納入；`hard_blocked` 永遠不可覆寫。
- Exact path 可解析成 `exact_file` 或 `recursive_directory`。Directory decision套用所有descendant
  regular files，但不得follow symlink、進入`.git/**`或重新納入其他hard-blocked entry。
- Directory expansion固定hard bounds：最多5,000個observed descendant regular files、所有
  pre-content selectable files合計最多500,000,000 bytes、相對directory depth最多64層；任一
  上限超過時整個directory proposal fail closed，不得silent truncate或partial approve。
  **此上限只綁「使用者主動請求的 recursive directory scope／manifest」**（含該scope的
  `scan_this_run`與`skip_this_run`）；**不限制**整庫 default-included inventory 的
  `default_included_file_count`。Repo 內預設會掃的安全檔加總超過5,000時，只要使用者沒有對
  該大目錄做 recursive decision，一般scan仍可進行。
- 同一preflight最多20個directory scopes；所有完成的directory manifests，以及scan submit收到的
  全部directory decisions，都要依canonical descendant path去重後共用5,000 files／
  500,000,000 bytes aggregate budget。Parent/child overlap不得重複計費或繞過上限。
- Preflight 在使用者同意前只可讀 path metadata 與 ignore/catalog policy；不得讀候選檔內容、
  產生 snippet 或用內容 hash 當 proposal fingerprint。
- 本 feature 新增的 target/audit API path 一律使用 project-relative POSIX path；不得在
  preflight/decision/error payload 回傳 absolute local path、檔案內容或 secret value。Existing
  project import response是否暴露root不由本計畫遷移。
- Preflight、pending、stale與其他 **pre-snapshot selection error** 不建立 `scan_id`、snapshot、
  build 或 output artifact。Snapshot已成功但後續build失敗的existing `status="error"` lifecycle
  不在此限制內，仍可帶真實`scan_id`供診斷。
- Existing API fields 只能 additive 演進；舊 frontend 未傳 `preflight_request_id` 時，既有
  sensitive boundary flow 仍可運作。
- `Apply` 重用已保存 snapshot，不重新 preflight、不重新 enumeration、不套用新的 selection。
- `Rescan` 必須建立新的 preflight；前一次 per-run decisions 不得自動沿用。
- **UA integration 明確 deferred：** Plan 20 不修改 Plan 16、UA request constructor、UA
  sidecar、`files[]`、parity harness 或 `ua_analysis_result` lifecycle。後續若要接 UA，由 Plan 16
  另案讀取已穩定的 final inventory contract。
- Windows 與 macOS 都以同一 project-relative POSIX、case-sensitive contract 判定；只有實際
  filesystem lookup 受平台影響，API/audit 語意不得漂移。

---

## Scope Freeze：Plan 20 到 final inventory 為止；不接 UA；不實作 Frontend

```text
Plan 20 本次執行範圍（Backend only）
  preflight API + services
    -> accept user decisions via POST /api/scans
    -> hard-safety revalidation
    -> final FileInventory
    -> current ProjectScanService providers
    -> ScanSnapshot / existing build pipeline
    -> backend contract docs / pytest（含 API／integration）

Plan 20 明確停止線
  X 不建立 UA request
  X 不呼叫 UA service / sidecar
  X 不新增 UA files[] adapter
  X 不跑 UA parity
  X 不修改 Plan 16 實作或驗收
  X 不實作 React／Zod／BoundaryDecisionModal／useProjectScanFlow
  X 不把 frontend lint／build／Vitest 當成本計畫 DoD
  X 不修改 frontend/src（除非日後另開 frontend-owned task 並明確解除本凍結）

未來（不是本計畫執行 task）
  stable final inventory + preflight HTTP contract
    -> Meeting-Sync 2026-07-15 frontend work items
    -> Plan 16 決定如何接入 UA
```

Plan 20 可以保存通用的 final inventory 與 provenance digest，因為 current scanner／snapshot
本來就需要它們；但不得為 UA 增加專用欄位、adapter、branch、feature flag、測試或 runtime
dependency。Current route 已傳入的 `ua_analysis_result=None` 維持原狀，不在本計畫改動。

Frontend 章節（§1.3／§1.5 C／§10／Task 7–8 等）保留的目的是：**凍結 backend 必須滿足的
consumer contract**，讓前端之後不用猜。執行本計畫時把它們當 read-only spec，**不要實作 UI**。

---

## 1. 決策摘要

### 1.1 推薦做法

採用「**獨立 metadata-only preflight + 既有 boundary decision contract + in-memory
overlay**」，不把使用者決策寫回 `.gitignore` 或 `scan_inventory_rules.toml`。

這是「**完整product default + per-run delta**」模型，不是「runtime choice取代default policy」。
Backend必須先算出Plan 19 baseline outcome，才有資格建立Plan 20 proposal與接受使用者delta。

這個做法有四個原因：

1. `.gitignore` 是專案來源控制規則，不是單次掃描 UI state；寫回會污染使用者 repo。
2. `scan_inventory_rules.toml` 是 KAI-Mind default policy source of truth；寫入單一使用者的
   一次選擇會破壞重現性與多人協作。
3. Existing `ScanBoundaryDecisionRequest` 已有 `target_path + fingerprint + decision`，只需
   additive增加`selection_scope`，即可讓file與directory沿用同一proposal → decision → audit
   生命週期，不需建立第二套`ManualMapping` entity。
4. Preflight 與 scan 之間重新驗證 metadata，可避免 UI 看見 A 檔、送出後卻讀到已被替換的
   B 內容。

### 1.2 「覆寫」的正確意思

這裡的覆寫只改變當次記憶體中的 selection result：

```text
base outcome                  explicit decision             effective outcome
---------------------------   ----------------------------  -----------------
included                      (none, non-sensitive)          included
included + confirmation       (none)                         pending review
included                      skip_this_run                  excluded this run
soft_excluded                 (none)                         excluded
soft_excluded                 scan_this_run                  included this run
directory scope               scan_this_run                  include every selectable descendant
directory scope               skip_this_run                  exclude every selectable descendant
directory + exact-file child  conflicting decisions         exact-file decision wins
hard_blocked                  any decision                   reject decision
missing                       any decision                   reject / stale
```

它 **不會** 做以下任何寫入：

```text
target/.gitignore                         unchanged
target/.git/info/exclude                  unchanged
global Git excludes                      unchanged
kai_mind/core/rules/scan_inventory_rules.toml  unchanged
mappings/{mapping_id}.json                not created
project canonical map                    unchanged until normal build publish
```

### 1.3 這不是完整 file explorer，但支援資料夾遞迴全選

本feature是「default inventory + exact-path scoped override」，不需要把整個repo預先展開成
無上限checkbox tree。Frontend可：

- review backend主動提出的敏感檔；
- 分頁查看可覆寫的soft-excluded files；
- 輸入exact project-relative **file path**，只review/override該檔案；
- 輸入exact project-relative **directory path**，建立`recursive_directory` proposal；
- 對default-included file/directory scope做`skip_this_run`；
- 對soft-excluded file/directory scope做`scan_this_run`；
- 在directory decision之上再對個別descendant file下相反decision，exact-file decision優先。

Path resolution固定為：

```text
requested path resolves to regular file
  -> selection_scope = exact_file
  -> decision只影響該file

requested path resolves to directory
  -> selection_scope = recursive_directory
  -> backend完整enumerate該directory下所有descendants
  -> scan_this_run = 納入所有通過hard safety的regular files
  -> skip_this_run = 排除所有selectable descendant regular files；hard-blocked仍維持hard-blocked

requested path contains glob syntax
  -> 422 inventory_selection_path_invalid
```

Directory的「全選」精確意思是 **all selectable descendant regular files**，不是繞過安全機制
讀取每個filesystem entry：

- `.git/**`、outside-root symlink、special files、unreadable、absolute size cap與unsupported
  binary仍不可掃；
- symlink一律不follow；
- soft-excluded descendants（包含`node_modules/`、build/cache、`.gitignore`命中）會因
  directory `scan_this_run`被納入；
- backend在preflight回傳descendant counts、selectable bytes、sensitive count與hard-blocked
  counts，Frontend action文案使用「掃描全部可掃描檔案」，不能宣稱hard-blocked files也會讀取；
- directory超過5,000 files、500,000,000 selectable bytes或64層depth時不建立可批准proposal，
  使用者需改選較小的subdirectory；不得只取前N筆。

Project root使用canonical path `.`，同樣可建立recursive selection；`.git/**`與所有hard bounds
仍適用。V1仍不接受runtime glob，也不提供unbounded tree browsing。

### 1.4 為什麼preflight不直接塞進`POST /api/scans`

Preflight是可重複、metadata-only的read operation；使用者可能分頁、查exact path或取消。
`POST /api/scans`則只有在decisions完整且重新驗證通過後，才有權建立snapshot/build。分開後：

Preflight使用`POST`是因為有bounded path list與opaque cursor request body；它仍是safe-to-retry、
不持久化domain state的查詢，不代表已開始scan。

- 分頁／查path不會產生假的`scan_id`或半成品scan state；
- 取消review不需要rollback；
- frontend可清楚區分`reviewing`與真正`submitting`；
- backend可在單一mutation boundary內套overlay、做post-decision safety並materialize final
  inventory；
- existing `/api/scans` consumer仍保有additive compatibility path。

### 1.5 產品語意澄清（FAQ／常見誤解）

本節固定產品解釋，避免實作或review時把「預設略過」「directory 全選上限」「前端顯示」混在一起。

#### A. 預設要跳過什麼：仍由 TOML + `.gitignore` 決定

| 層級 | 誰決定預設 | 使用者能做什麼 |
| --- | --- | --- |
| Plan 19 `scan_inventory_rules.toml` | dependency／build／cache／generated／model-weight 等 soft exclude | 這次可對**明確 path** soft override |
| 專案 `.gitignore`／exclude | Git ignore 規則 | 同上 |
| Hard safety（Python） | symlink escape、`.git/**`、unsupported binary… | **不可**覆寫 |
| 敏感檔（`.env` 等） | 不預設 hard block；進 default inventory 就要問人 | 必選掃／跳過 |

優先序不變：`hard safety > explicit per-run user decision > source/catalog default`。  
使用者 decision **不寫回** TOML、`.gitignore` 或 Manual Mapping。

#### B. 這不是 Manual Mapping

| | Manual Mapping | Inventory Selection（Plan 20） |
| --- | --- | --- |
| 何時 | 掃**後** | 掃**前** |
| 決定什麼 | component／slot 語意 | 這次能不能**讀**這個 path |
| 前端回傳後 | 組成／存 `ManualMapping` | 組成 per-run inventory overlay |
| 生命週期 | 常為 project-scoped | 預設 scan／request-scoped |

互動套路可以像 proposal → decision → apply，但 **domain 與 persistence 必須分開**；不得把
I/O 授權塞進 `/api/mappings`。

#### C. 前端會看到什麼（不是整庫 checkbox）— **契約參考；本計畫不實作 UI**

Preflight JSON 給前端顯示（由後續 frontend task 消費）；**一般 default-included 檔通常不逐檔
列出**，只在 summary 顯示數量。Backend 必須能產生下列分區 payload：

| UI 區塊 | 內容 | 使用者動作 |
| --- | --- | --- |
| `required_boundary_proposals` | 系統主動提出的敏感檔 | **必答** scan／skip |
| `reviewable_excluded_page` | soft-excluded exact files（分頁） | 可選這次納入；不選＝繼續略過 |
| `requested_target_results` | 使用者輸入的 exact file／directory | 有可決策 proposal 才可勾 |
| `blocked_summaries` + summary | hard block、collapsed 大目錄摘要 | 只讀；collapsed 需再請求 path 才展開 |

媒介是 **HTTP JSON**（preflight／scan response），不是下載靜態檔、也不是另產 Manual Mapping。

#### D. Fail closed＝寧可整 scope 拒絕，也不 silently 只掃前 N 筆

「不得只取前 N 筆」的意思：

- Directory 超過 5,000 files／500MB／64 depth → **不建立可批准 proposal**（或 aggregate 超限則整個
  preflight 422），使用者改選較小 subdirectory。
- **不是**默默掃前 5,000 個再回 `completed` 假裝整包掃完。
- **分頁**只用於瀏覽 soft-excluded list；與 directory 全選／必答敏感提案的 fail closed **無關**。

對 release-readiness gate 這是預期做法：證據必須對齊授權範圍，不能 silent data loss。

#### E. 5,000 threshold 防什麼、不防什麼

**主要防：** 使用者對本來 soft-excluded、底下超多檔的目錄（典型 `node_modules/`）做
`scan_this_run`／recursive 展開，造成資源爆炸或假完整掃描。

**同樣會撞上限：** 對任一超大目錄建立 recursive proposal——含 `skip_this_run`。因為
`scan`／`skip` 都要先有完整 metadata manifest／fingerprint，Plan 20 **不**對 skip 放寬上限。

**不會因為 5,000 報錯：**

| 情境 | 結果 |
| --- | --- |
| `node_modules/` 等已被 gitignore／TOML soft exclude，使用者**不展開** | 預設略過，**正常** |
| Repo 內預設會掃的安全檔加總 >5,000（例如 `src/` 有 8,000 個 `.py`） | **一般 scan 仍可進行**；5000 不套在整庫 default inventory |
| 使用者主動對 >5,000 的目錄 path 做 recursive scan／skip | **該 scope fail closed** |

一句話：5000 是「**directory 遞迴決策要完整列清**」的成本上限，不是「整個專案最多只能有
5000 個可掃檔」。

#### F. 實務建議（寫進產品 copy／docs 時沿用）

- 大目錄要長期略過 → 用 Plan 19 TOML 或專案 `.gitignore`，不要為了略過而去展開超大 directory。
- 這次例外要掃一小包 → 選較小的 subdirectory，勿一次勾整個 `node_modules/`。
- 預設會掃的大樹 → 讓它走 default included；只有要「這次整包 skip／scan」才輸入該 directory。

---

## 2. 現況與需要修正的 gap

Current runtime 已有可重用基礎，但還不能實作這個 feature：

| Current code | 現況 | Gap |
| --- | --- | --- |
| `FilesystemProvider` | Git mode 用 `git ls-files --cached --others --exclude-standard` | 被 ignore 的 path 在進 policy 前已消失，無法被使用者重新納入 |
| `ScanBoundaryReviewService.create_proposals()` | 只迭代 `inventory.files` | `inventory.skipped` 或 Git 沒列出的 ignored file 不會有 proposal |
| `ScanBoundaryReviewService` fingerprint | 讀檔頭尾建立 content-derived fingerprint | 使用者決定前已讀候選內容，不符合 metadata-only preflight |
| `_classify_files()` | `not path.is_file()` 時 silent continue | tracked-but-missing 沒有穩定 missing audit/error |
| `POST /api/scans` | enumeration 後直接 proposal／scan | 沒有可分頁、可新增 exact file/directory scope 的 review surface |
| `ScanCreateResponse` backend | pending 時 `scan_id` 可省略 | Frontend Zod 目前把 `scan_id` 設為必填，pending response 會 parse fail |
| `BoundaryDecisionModal` | 可決定敏感 candidates | 沒有soft-excluded、hard-blocked、file/directory scope summary或stale UX |

因此 Plan 20 必須在 final `FileInventory` 前保留 richer candidate outcomes，不能只把
`FileInventory.skipped` 再包一層 UI。

---

## 3. 名詞與 ownership

| 名詞 | 定義 | Owner |
| --- | --- | --- |
| Candidate enumeration | 觀察 repo 中可能成為 scan target 的 path metadata | `FilesystemProvider` |
| Inventory selection policy catalog | Plan 19 的 KAI default include/exclude rules | TOML loader + matcher |
| Inventory preflight | 不讀候選內容的 selection review snapshot | `InventoryPreflightService` |
| Boundary proposal | 一個可由使用者決定的exact file或recursive directory scope | `ScanBoundaryReviewService` |
| Per-run decision | `scan_this_run` / `skip_this_run` | Frontend input，backend validate/apply |
| Selection overlay | 將 explicit decision 套到 base outcome 的 pure transformation | Backend service |
| Final inventory | post-decision safety 通過後，providers 唯一可讀的 allowlist | `FileInventory` |
| Manual mapping | Step 9 component/capability durable decision | **不屬於本 feature** |

Plan 19 仍擁有 catalog schema、matcher、policy digest 與 base audit；Plan 20 擁有 preflight、
soft-exclusion per-run override、decision validation 與 final selection audit。Plan 20 完成後，
Plan 19 的「catalog exclusion 不可由 runtime decision 覆寫」只保留為 Plan 19 初始狀態；新
canonical contract改為「catalog/project ignore是soft default，可被 **exact file或bounded
recursive-directory one-run decision** 覆寫，hard safety不可覆寫」。

---

## 4. Selection precedence 與分類

### 4.1 三層 precedence

```text
                          highest precedence
                                  |
                                  v
                 +--------------------------------+
                 | HARD FILESYSTEM / RESOURCE SAFE |
                 | outside root, symlink escape,   |
                 | special file, unreadable,       |
                 | .git/**, absolute size cap,     |
                 | unsupported binary after consent|
                 +---------------+----------------+
                                 | blocked -> STOP
                                 v
                 +--------------------------------+
                 | EXPLICIT USER DECISION          |
                 | exact file decision             |
                 | then deepest directory decision |
                 | then ancestor directory decision|
                 +---------------+----------------+
                                 |
                                 v
                 +--------------------------------+
                 | DEFAULT SOURCE / CATALOG OUTCOME |
                 | Git ignore, nested .gitignore,   |
                 | .git/info/exclude, global ignore,|
                 | KAI dependency/build/cache rules |
                 +--------------------------------+
                          lowest precedence
```

### 4.2 Soft exclusion（可覆寫）

- repo `.gitignore` 與 nested `.gitignore`；
- `.git/info/exclude`；
- Git global exclude（只有 Git mode 能觀察）；
- Plan 19 catalog 的 dependency/build/cache/generated/model-weight defaults；
- Python 的 default large-file review threshold；
- 使用者對本次 scan 主動指定的 default-included path（default 為 scan，可選擇 skip）。

### 4.3 Hard block（不可覆寫）

- path normalization 失敗、absolute path、`..` traversal；
- resolved path 不在 project root；
- symlink escape；
- `.git/**` internal metadata；
- socket、device、FIFO或其他非regular file；directory只可當selection scope，不能成為
  `FileRecord`；
- permission/stat/open failure；
- absolute resource cap；
- 使用者同意後的 bounded binary probe 判定為 unsupported binary；
- preflight 後 path missing、type/size/mtime 改變或 fingerprint stale。

`.env`、credential-like config、vector persistence 不預設 hard block。若它們在 default
inventory 中，必須先取得明確 decision；若本來 soft-excluded，只有明確
`scan_this_run` 才會進 post-decision safety。

### 4.4 File與directory decision precedence

同一file同時落在多個scope時，固定採以下順序：

```text
hard safety
  > exact-file decision
  > deepest matching recursive-directory decision
  > ancestor recursive-directory decision
  > default source/catalog outcome
```

範例：

```text
scan_this_run("node_modules/", recursive_directory)
skip_this_run("node_modules/pkg/test.bin", exact_file)

result:
  node_modules/下其餘可掃描files -> included this run
  node_modules/pkg/test.bin       -> skipped this run
```

### 4.5 Pure overlay pseudo-code

```python
def select(candidate, exact_decision, matching_directory_decisions):
    if candidate.base_outcome in {"hard_blocked", "missing"}:
        if exact_decision is not None:
            raise InventorySelectionOverrideNotAllowed(candidate.path)
        return candidate.base_outcome

    decision = exact_decision or deepest_matching(matching_directory_decisions)
    if decision is not None:
        if decision.selection_scope == "exact_file":
            require_same_path_and_metadata_fingerprint(candidate, decision)
        else:
            require_candidate_in_revalidated_directory_manifest(candidate, decision)
        return (
            "included_pending_content_safety"
            if decision.decision == "scan_this_run"
            else "excluded_by_user_this_run"
        )

    if candidate.decision_required:
        return "pending_boundary_review"

    return candidate.base_outcome
```

`included_pending_content_safety` 尚不是 final inventory。Backend 必須在使用者同意後做 bounded
open/binary/resource checks才materialize成`FileRecord`。Directory scope內個別descendant若在
post-decision check變成hard blocked，該file以stable audit reason跳過，其他通過的descendants
仍可進final inventory；completed result/audit必須回報included與blocked counts，不能宣稱整個
directory每個entry都已掃描。Exact-file decision若post-decision blocked，仍回
`inventory_selection_post_decision_blocked`，避免使用者以為該指定file已成功掃描。

---

## 5. Candidate enumeration contract

### 5.1 Git mode

Backend 執行兩種互補 query：

```text
Default candidate source
  git ls-files -z --cached --others --exclude-standard

Ignored review source
  git ls-files -z --others --ignored --exclude-standard --directory

Ignored reason lookup
  git check-ignore -z -v --stdin
```

- 第一個 query 產生 default included candidates；tracked file 即使命中 ignore pattern 仍會列出。
- 第二個 query 只補足 ignored untracked paths，供 soft-excluded review。
- `--directory` 允許 Git 把大型 ignored directory 壓成 `path/` summary，避免列出數萬檔案。
- `git check-ignore -z -v --stdin` 只用於已觀察到的 ignored paths，將命中來源分類成
  `project_ignore`、`git_private_exclude` 或 `git_global_exclude`。Raw source filename 可能是
  使用者機器上的 absolute global exclude path；API/audit 只能保存分類與 stable reason，不得
  回傳 raw source path 或 raw stderr。
- `.git/**` 不得因第二個 query 進入 reviewable set。
- exact `requested_paths[]`另以root-contained `lstat/stat`解析成file或directory；不靠raw
  `Path.exists()`越過symlink/path safety。Directory scope改用bounded safe walker列出完整
  descendants，再以`git check-ignore`分類soft-exclusion來源；不能沿用collapsed Git summary
  假裝已看到所有children。

### 5.2 Recursive mode

- 適用沒有 Git worktree 的匯入目錄。
- `GitIgnoreSpec` 解析 repo 內 root/nested `.gitignore`。
- 一般preflight walker保存ignored directory summary；不得為了UI無條件展開大型excluded
  subtree。
- 只有使用者exact-request某directory時，才啟動bounded recursive expansion；這個walker必須
  穿過soft-excluded subtree並逐file套catalog/ignore classification，但仍hard-prune`.git/**`、
  outside-root symlink與non-directory special entries。
- recursive mode 不假裝支援 `.git/info/exclude` 或 global Git exclude；source difference 寫入
  `source_mode` 與 warnings。

### 5.3 Git failure fallback

- Git query failure可依 Plan 19 切到 recursive，但 `source_mode` 必須是
  `fallback_after_git_error`。
- Fallback 產生不同 `candidate_set_digest`／`inventory_run_digest`，即使 final files 相同也不能
  冒充 Git mode。
- Git 與 recursive 都無法安全 enumeration 時 fail closed，不進 preflight UI。

### 5.4 Exact directory expansion contract

`InventoryPreflightService.resolve_requested_path()`遇到directory時建立完整、bounded、
metadata-only manifest：

```text
DirectorySelectionManifest
  directory_path
  selection_scope = recursive_directory
  observed_regular_file_count
  selectable_file_count
  default_included_count
  soft_excluded_count
  sensitive_file_count
  pre_content_hard_blocked_count
  selectable_bytes
  observed_max_relative_depth
  blocked_reason_counts
  entries[]  # sorted metadata + policy/safety outcome; no content
  manifest_fingerprint
```

Enumeration rules：

1. Exact target若是`.git`或`.git/**`直接回`hard_blocked`；不可把hard-pruned root誤報成empty。
2. `lstat` exact directory，確認resolved path仍在project root；symlink directory本身不follow。
3. Top-down walk；每層dir/file name先normalize成project-relative POSIX path。
4. `.git/` hard prune；soft-excluded directory仍往下走，因為directory decision可覆寫它。
5. 每個regular file套project ignore、catalog與pre-content safety，加入sorted manifest。
6. 單一scope超過5,000 observed regular files、500,000,000 selectable bytes或64層relative depth
   時立即停止該walker，回non-actionable `directory_limit_exceeded` target result；不得回truncated
   proposal。最多20個scopes使worst-case failed-walk work仍有上界。
7. 同一preflight先解析所有target kinds；超過20個directories時不啟動walker。所有完整、
   individually-valid manifests依canonical file path去重後，aggregate仍不得超過5,000 observed
   files或500,000,000 selectable bytes；超過時整個preflight以422 fail closed，不回partial
   response。
8. 0個selectable files回`empty_directory`，不建立actionable proposal。
9. Manifest fingerprint綁定完整entries與policy/safety digest；preflight後任何descendant新增、
   刪除、rename、type/size/mtime/outcome改變，scan submit回
   `inventory_selection_target_changed`並要求重新review。

Directory expansion不把directory本身放入`FileInventory.files`；decision最後仍展開成individual
`FileRecord[]`與per-file audit entries。這維持boundary是final inventory前的filter，而不是
另建一份directory scanner output。

**Scope of the 5,000 bound（必須寫進實作與測試）：**

- 適用：單一 `requested_paths` directory、其 `DirectorySelectionManifest`、以及 submit 時所有
  directory decisions 去重後的 aggregate。
- 適用決策種類：該 manifest 上的 **`scan_this_run` 與 `skip_this_run` 相同**；沒有「只是略過就
  不用展開／可超過上限」的例外。
- 不適用：未請求 recursive expansion 時，整庫 default-included candidate 的總檔數；也不適用於
  僅以 Git `--directory` collapsed summary 呈現、使用者尚未 exact-request 展開的 soft-excluded
  大目錄（那些維持 summary／`can_expand=true`，不因內部有數萬檔而讓一般 preflight 失敗）。

### 5.5 `.gitignore` pattern 沒有對應檔案時

這個 case 必須明確區分「規則存在」與「檔案存在」：

```text
.gitignore contains: secrets/local.env
repo has no secrets/local.env

result:
  catalog / ignore policy digest 仍包含該規則來源
  candidate set 不建立 secrets/local.env
  preflight 不顯示 phantom row
  per-file audit 不建立 skipped entry
  scan 正常繼續
```

若使用者在 exact-path 欄位輸入不存在的 `secrets/local.env`：

```text
requested_target_results[] = {
  target_path: "secrets/local.env",
  status: "missing",
  reason_code: "inventory_selection_target_missing",
  override_allowed: false,
  proposal: null
}
```

Frontend 顯示「目前專案中找不到此檔案」，不得建立可勾選 proposal。若檔案在 preflight 後、
scan submit 前消失，`POST /api/scans` 回 `409 inventory_selection_target_missing`，且不建立
`scan_id`。

### 5.6 Tracked-but-missing

Git index 可能列出 tracked path，但 worktree 檔案已被刪除。這不是 silent skip：

- candidate outcome = `missing`；
- reason code = `missing_at_scan`；
- 不建立 actionable proposal；
- preflight warning/count 可見；
- 若沒有 decision 指向它，其他檔案可繼續 scan；
- 若 client 對它送 decision，回穩定 `409 inventory_selection_target_missing`。

---

## 6. Backend domain model

### 6.1 New internal models

Create `src/kai_mind/core/models/inventory_selection.py`：

```text
InventoryCandidateOutcome
  included
  soft_excluded
  hard_blocked
  missing

InventorySelectionSource
  project_ignore
  git_private_exclude
  git_global_exclude
  kai_inventory_catalog
  filesystem_safety
  runtime_user_decision

InventoryTargetKind
  file
  directory

InventorySelectionScope
  exact_file
  recursive_directory

InventoryRequestedTargetStatus
  reviewable
  hard_blocked
  missing
  empty_directory
  directory_limit_exceeded

InventoryDirectoryLimitKind
  directory_scope_count
  observed_file_count
  selectable_bytes
  relative_depth
  aggregate_observed_file_count
  aggregate_selectable_bytes

InventoryDirectoryLimitContext
  limit_kind: InventoryDirectoryLimitKind
  limit: int
  observed_at_least: int

InventoryCandidate
  path: str
  target_kind: file
  target_type: str
  size_bytes: int | null
  mtime_ns: int | null
  base_outcome: InventoryCandidateOutcome
  exclusion_sources: list[InventorySelectionSource]
  matched_inventory_policy_ids: list[str]
  effective_inventory_policy_id: str | null
  reason_code: str
  risk_type: str | null
  decision_required: bool
  override_allowed: bool
  metadata_fingerprint: str

DirectorySelectionManifest
  directory_path: str
  selection_scope: recursive_directory
  observed_regular_file_count: int
  selectable_file_count: int
  default_included_count: int
  soft_excluded_count: int
  sensitive_file_count: int
  pre_content_hard_blocked_count: int
  selectable_bytes: int
  observed_max_relative_depth: int
  blocked_reason_counts: dict[str, int]
  entries: list[InventoryCandidate]
  manifest_fingerprint: str

DirectorySelectionSummary
  observed_regular_file_count: int
  selectable_file_count: int
  default_included_count: int
  soft_excluded_count: int
  sensitive_file_count: int
  pre_content_hard_blocked_count: int
  selectable_bytes: int
  observed_max_relative_depth: int
  blocked_reason_counts: dict[str, int]

InventoryRequestedTargetResult  # backend internal
  target_path: str
  target_kind: file | directory
  status: InventoryRequestedTargetStatus
  file_candidate: InventoryCandidate | null
  directory_manifest: DirectorySelectionManifest | null
  reason_code: str | null
  limit_context: InventoryDirectoryLimitContext | null

InventoryRequestedTargetView  # API projection
  target_path: str
  target_kind: file | directory
  status: InventoryRequestedTargetStatus
  proposal: ScanBoundaryProposal | null
  reason_code: str | null
  limit_context: InventoryDirectoryLimitContext | null

InventoryCandidateSet
  source_mode: git | recursive | fallback_after_git_error
  candidates: list[InventoryCandidate]
  skipped_summaries: list[InventoryDirectorySummary]
  warnings: list[str]
  inventory_policy_schema_version: str
  inventory_policy_digest: str
  filesystem_safety_version: str
  candidate_set_digest: str

InventoryPreflightState
  candidate_set: InventoryCandidateSet
  requested_target_results: list[InventoryRequestedTargetResult]
```

`InventoryCandidateSet` 是 preflight/internal richer representation；API serializer不得回傳
`DirectorySelectionManifest.entries[]`，directory client只拿redacted `DirectorySelectionSummary`
與manifest fingerprint。`FileInventory` 仍是所有providers 的 final input。不得讓 provider
自行讀 candidate set、ignore rules 或 decisions。

`candidate_set_digest`只涵蓋base enumeration與collapsed summaries；exact
`requested_target_results`是查詢結果，不因使用者只是查看某path就改變base digest。Scan
submit會從`boundary_decisions[].target_path + selection_scope`重新解析所有有語意效果的file或
directory targets；file驗metadata fingerprint，directory驗完整manifest fingerprint。

`preflight_request_id` 計算固定為：

```text
sha256(canonical-json({
  project_id,
  source_mode,
  candidate_set_digest,
  inventory_policy_digest,
  filesystem_safety_version
}))
```

不得納入 `generated_at`、pagination cursor 或純查看但未決定的 `requested_paths`。它是
staleness token，不是 authorization token；backend 仍須依 project access boundary 授權並
重新驗證每個 decision target。

### 6.2 File與directory fingerprint

Preflight proposal 的 existing `target.fingerprint` 改為 metadata fingerprint：

```text
sha256(canonical-json({
  "path": project_relative_posix_path,
  "target_type": lstat_type,
  "size_bytes": size,
  "mtime_ns": mtime_ns
}))
```

- 不含檔案內容、absolute root、inode 或平台專屬 path separator。
- `mtime_ns` 不可取得時 fail closed；不得降級成 path-only fingerprint。
- Final snapshot 的 content fingerprint 仍可在使用者同意後建立；兩者名稱與用途不可混用。

Directory proposal的`target.fingerprint`是manifest fingerprint：

```text
sha256(canonical-json({
  "directory_path": project_relative_posix_directory,
  "selection_scope": "recursive_directory",
  "entries": sorted([{
    "path": descendant_path,
    "target_type": lstat_type,
    "size_bytes": size,
    "mtime_ns": mtime_ns,
    "base_outcome": outcome,
    "reason_code": reason_code,
    "exclusion_sources": sorted_sources,
    "matched_inventory_policy_ids": sorted_policy_ids,
    "effective_inventory_policy_id": effective_policy_id,
    "risk_type": risk_type,
    "decision_required": decision_required,
    "override_allowed": override_allowed
  }]),
  "inventory_policy_digest": policy_digest,
  "filesystem_safety_version": safety_version
}))
```

Directory mtime本身不足以偵測descendant變動，因此不得只hash directory stat。Manifest必須完整
enumerate後才能產生；超過bounds時沒有fingerprint、沒有actionable proposal。

### 6.3 Proposal additive extension

Extend existing `ScanBoundaryProposal`，不要新增第二種 decision lifecycle：

```text
ScanBoundarySelectionContext
  base_outcome: included | soft_excluded | mixed
  review_kind: required_confirmation | optional_override
  default_decision: scan_this_run | skip_this_run | null
  decision_required: bool
  override_allowed: bool
  exclusion_sources: list[str]
  matched_inventory_policy_ids: list[str]
  target_kind: file | directory
  selection_scope: exact_file | recursive_directory
  directory_summary: DirectorySelectionSummary | null

ScanBoundaryProposal
  ...existing fields...
  selection_context: ScanBoundarySelectionContext | null  # additive
```

Interpretation：

| Case | `base_outcome` | `default_decision` | `decision_required` |
| --- | --- | --- | ---: |
| Default-included sensitive file | `included` | `null` | true |
| Soft-excluded file | `soft_excluded` | `skip_this_run` | false |
| User exact-requested normal included file | `included` | `scan_this_run` | false |
| User exact-requested directory | computed aggregate | `null` | true |
| Hard blocked / missing / empty / over-limit directory | 不建立 proposal | none | none |

Directory `base_outcome`只供UI說明aggregate default，不改變「必須明確決定」：

```text
soft_excluded_count == 0
  -> included

default_included_count == 0 and soft_excluded_count > 0
  -> soft_excluded

otherwise
  -> mixed
```

Frontend只顯示backend回傳值與summary，不自行用counts重算。

Directory proposal固定：

```text
target.path = canonical directory path（root為"."）
target.target_type = "directory"
target.size_bytes = null
target.fingerprint = DirectorySelectionManifest.manifest_fingerprint
selection_context.selection_scope = "recursive_directory"
selection_context.directory_summary = bounded counts only
```

Extend existing `ScanBoundaryDecisionRequest`：

```text
selection_scope: exact_file | recursive_directory = exact_file
```

Default=`exact_file`保留舊client compatibility。Directory decision必須明確傳
`recursive_directory`；backend不得只看path尾端slash猜scope。

Existing `evidence_packet.masked_evidence_values`、`masked_snippets` 在 preflight 必須是空 array；
保留欄位只為 backward compatibility。Preflight UI 不顯示內容 evidence。

### 6.4 Existing audit additive extension

Extend Plan 19 的 `InventoryPolicyAuditEntry`，不要另存 durable decision entity：

```text
base_outcome: included | soft_excluded | hard_blocked | missing
effective_outcome: included | skipped | hard_blocked | missing
decision_origin: default_policy | runtime_user_decision
boundary_decision: scan_this_run | skip_this_run | null
decision_target_path: str | null
decision_scope: exact_file | recursive_directory | null
decision_fingerprint: str | null
override_applied: bool
preflight_request_id: str | null
```

Audit 只存 project-relative path、stable ids/reasons、metadata/content digests；不存 content、
snippet、absolute path 或 UI display copy。

一個directory decision會展開成每個descendant的audit entry；每筆都保存同一
`decision_target_path`與`decision_scope="recursive_directory"`，但`path`仍是實際file。如此可
回答「這個file為何被納入」，又不把directory decision誤當成可被provider讀取的file。

`decision_origin="runtime_user_decision"`只表示有winning exact/directory decision，不代表它可
凌駕hard safety。若descendant在pre-content或post-decision階段被hard block，audit仍保存匹配的
decision target/scope，但固定`effective_outcome="hard_blocked"`、`override_applied=false`與stable
safety reason；不得寫成included或user-skipped。Direct exact hard-block target則根本不接受decision。

---

## 7. HTTP contract

### 7.1 Endpoint ownership

新增：

```http
POST /api/projects/{project_id}/scan-preflights
```

保留並 additive 擴充：

```http
POST /api/scans
```

不建立 `/api/inventory-decisions`，因為 decisions 不是 durable resource。也不使用 Step 9 的
`/api/mappings`，因為 file selection 不是 component/capability mapping。

### 7.2 Preflight request

```json
{
  "scan_depth": "system",
  "requested_paths": [
    "ignored/custom-loader.py",
    "src/experimental.py",
    "node_modules/small-local-package"
  ],
  "reviewable_excluded_cursor": null,
  "reviewable_excluded_limit": 100
}
```

Contract：

- `requested_paths` default `[]`，最多100；backend先`lstat`解析全部target kinds，若directory
  scopes超過20則在任何recursive walk前fail closed。去重後依canonical path排序，duplicate input
  不產生duplicate proposals。
- 每個path必須project-relative、POSIX、不可含traversal或glob。Project root唯一合法表示為`.`；
  directory canonical form不帶trailing slash。
- Backend以`lstat`解析exact path：regular file→`exact_file`；directory→bounded
  `recursive_directory`；symlink/special/missing→typed non-actionable result。
- Directory expansion沿用每scope與每preflight aggregate的5,000 unique files、500,000,000
  unique selectable bytes，以及每scope 64 depth hard bounds；overlap path只計一次。
- `reviewable_excluded_limit` 範圍 1～200，default 100。
- Cursor 是 opaque、綁定 project + candidate digest + policy digest，不可由 frontend解析。

### 7.3 Preflight response

```json
{
  "preflight_request_id": "preflight:9d13...",
  "project_id": "project:abc",
  "generated_at": "2026-07-15T08:00:00Z",
  "source_mode": "git",
  "inventory_policy_schema_version": "scan-inventory-policy/v1",
  "inventory_policy_digest": "sha256:catalog...",
  "candidate_set_digest": "sha256:candidates...",
  "filesystem_safety_version": "inventory-safety/v1",
  "summary": {
    "default_included_file_count": 143,
    "required_review_count": 2,
    "reviewable_excluded_count": 12,
    "hard_blocked_count": 3,
    "missing_count": 1,
    "collapsed_directory_count": 4
  },
  "required_boundary_proposals": [],
  "reviewable_excluded_page": {
    "items": [],
    "next_cursor": null,
    "total": 12
  },
  "requested_target_results": [],
  "blocked_summaries": [],
  "warnings": []
}
```

Detailed fields：

- `required_boundary_proposals`：default inventory 內必須決定才可掃的 sensitive candidates；不
  分頁、不 silent truncate。超過 backend safe cap 時 fail closed，code 為
  `inventory_preflight_review_limit_exceeded`。
- `reviewable_excluded_page.items`：soft-excluded exact files，可 `scan_this_run`；default 不選仍
  skip。
- `requested_target_results`：一一回覆`requested_paths`，status為`reviewable`、
  `hard_blocked`、`missing`、`empty_directory`或`directory_limit_exceeded`。每筆固定含
  `InventoryRequestedTargetView`欄位；file或directory只要`reviewable`就有proposal，其餘為
  `null`。若同一file proposal也出現在required/page list，使用相同deterministic `proposal_id`，
  frontend依id去重。
- 單一directory超限以`requested_target_results[].status="directory_limit_exceeded"`回200且
  `proposal=null`，並附`limit_context`；多directory aggregate超限則整個request回422，不得把已
  完成的前幾筆當成可提交partial response。
- `blocked_summaries`：hard block與尚未展開的collapsed directory之bounded summary。Collapsed
  directory row本身沒有decision action，但回`can_expand=true`；Frontend把其exact path送回
  `requested_paths`後，backend才建立recursive directory proposal。
- `warnings` 只能用 stable code，不含 raw Git stderr 或 absolute path。

Reviewable directory的API projection範例（`directory_manifest`與entries不在payload）：

```text
requested_target_results[]
  target_path: node_modules/small-local-package
  target_kind: directory
  status: reviewable
  proposal:
    target.path: node_modules/small-local-package
    target.target_type: directory
    target.size_bytes: null
    target.fingerprint: sha256:directory-manifest-d...
    selection_context.base_outcome: mixed
    selection_context.decision_required: true
    selection_context.selection_scope: recursive_directory
    selection_context.directory_summary:
      observed_regular_file_count: 26
      selectable_file_count: 23
      default_included_count: 4
      soft_excluded_count: 19
      sensitive_file_count: 2
      pre_content_hard_blocked_count: 3
      selectable_bytes: 12400000
      observed_max_relative_depth: 5
      blocked_reason_counts: {unsupported_type: 1, absolute_size_cap: 2}
  reason_code: null
  limit_context: null
```

### 7.4 使用者 decision 回傳給 backend

Frontend review 完成後呼叫：

```json
POST /api/scans
{
  "project_id": "project:abc",
  "scan_depth": "system",
  "preflight_request_id": "preflight:9d13...",
  "boundary_decisions": [
    {
      "target_path": ".env",
      "fingerprint": "sha256:metadata-a...",
      "decision": "skip_this_run",
      "selection_scope": "exact_file"
    },
    {
      "target_path": "ignored/custom-loader.py",
      "fingerprint": "sha256:metadata-b...",
      "decision": "scan_this_run",
      "selection_scope": "exact_file"
    },
    {
      "target_path": "src/experimental.py",
      "fingerprint": "sha256:metadata-c...",
      "decision": "skip_this_run",
      "selection_scope": "exact_file"
    },
    {
      "target_path": "node_modules/small-local-package",
      "fingerprint": "sha256:directory-manifest-d...",
      "decision": "scan_this_run",
      "selection_scope": "recursive_directory"
    }
  ]
}
```

Backend接回後 **不信任client的base outcome、reason、source、counts或size**；只接受path、
fingerprint、decision、selection scope與optional bounded reason。所有candidate/manifest facts都
重新由backend建立。

Rules：

- 同一`(target_path, selection_scope)`不可出現兩次；duplicate即使decision相同也回422，避免
  ambiguous audit。Ancestor/descendant directory scopes與exact child decision可同時存在，依
  exact→deepest directory→ancestor precedence計算。
- Client不得對hard-blocked、missing、empty、over-limit或未先展開的collapsed directory送
  decision；只有帶manifest fingerprint的reviewable directory proposal可送
  `recursive_directory` decision。
- `scan_this_run` 只能在 post-decision safety 通過後進 final inventory。
- `scan_this_run + recursive_directory`納入manifest內所有included/soft-excluded descendants；
  sensitive descendants視為由這次explicit directory confirmation授權。
- `skip_this_run`可移除default-included exact file或整個recursive directory scope。
- Submit必須對所有directory decisions重新計算去重後aggregate budget；即使client分多次preflight
  取得相同`preflight_request_id`下的proposal fingerprints，也不能合併成超過5,000 files／
  500,000,000 bytes的scan。
- Directory scope內post-decision blocked child逐file跳過並audit；若最後0個descendants可進final
  inventory，回`inventory_selection_directory_no_scannable_files`且不建立scan。
- 沒送 soft-excluded decision = 保持 skip；沒送 optional included decision = 保持 scan。
- 沒送 required sensitive decision = `requires_boundary_decision`，不建立 `scan_id`。

### 7.5 Pending response

```json
{
  "project_id": "project:abc",
  "status": "requires_boundary_decision",
  "preflight_request_id": "preflight:9d13...",
  "boundary_proposals": [],
  "available_boundary_actions": ["scan_this_run", "skip_this_run"]
}
```

- `scan_id` 必須 absent；不是 `null` 假 scan。
- `preflight_request_id` additive optional，讓 frontend 對當前 review 重送。
- Frontend `scanCreateResponseSchema.scan_id` 必須改為 optional。

### 7.6 Completed response

沿用 existing response：

```json
{
  "scan_id": "scan:...",
  "project_id": "project:abc",
  "status": "completed",
  "build_result": {
    "status": "ok",
    "build_id": "build:..."
  },
  "boundary_proposals": [],
  "inventory_selection_summary": {
    "included_file_count": 167,
    "skipped_file_count": 8,
    "directory_scope_results": [
      {
        "target_path": "node_modules/small-local-package",
        "decision": "scan_this_run",
        "observed_file_count": 26,
        "included_file_count": 22,
        "hard_blocked_file_count": 3,
        "post_decision_blocked_file_count": 1
      }
    ]
  }
}
```

Frontend 不從 decision 或 preflight 自行合成結果。它收到 completed 後走既有
`loadApiViewerPayload()`／latest build refresh，載入 backend 已 publish 的 map/report。
`inventory_selection_summary`是由final inventory audit投影的additive response，不是第二份
inventory truth；Frontend可用它說明directory全選實際納入／阻擋數量，不得自行重算。

`ScanCreateResponse.status="error"` 若發生在snapshot已建立、build階段失敗，沿用existing
lifecycle並可包含真實`scan_id`；它不可與HTTP層pre-snapshot selection error混為一談。

### 7.7 Stable error surface

Error body：

```json
{
  "detail": {
    "code": "inventory_preflight_stale",
    "message": "Scan selection changed. Refresh the file review.",
    "retryable": true,
    "context": null
  }
}
```

| HTTP | Code | 意義 | Frontend action |
| ---: | --- | --- | --- |
| 404 | `project_not_found` | project id 不存在 | 回 project import error |
| 422 | `inventory_selection_path_invalid` | absolute/traversal/glob/blank path | inline exact-path error |
| 422 | `inventory_selection_scope_invalid` | path type與`selection_scope`不符 | 重新preflight，不猜scope |
| 422 | `inventory_selection_duplicate_decision` | 同 path 重複 | 不送 scan，保留 review state |
| 422 | `inventory_selection_conflicting_decision` | 同 path 有相反 decisions | 不送 scan，保留 review state |
| 422 | `inventory_selection_override_not_allowed` | 對hard block或未展開summary送decision | 顯示不可覆寫原因 |
| 422 | `inventory_selection_directory_limit_exceeded` | directory scope count、preflight aggregate或submit decision aggregate超過hard bound | 顯示limit與at-least count，要求減少scope或選較小subdirectory |
| 422 | `inventory_selection_directory_no_scannable_files` | selected directory經post-decision safety後0 files可掃 | 不建立scan，顯示blocked summary |
| 422 | `inventory_preflight_review_limit_exceeded` | required review 超過安全上限 | 中止並提示縮小 project scope |
| 409 | `inventory_preflight_stale` | candidate/policy/safety/request set digest 改變 | 重新 preflight |
| 409 | `inventory_selection_target_missing` | 選中的 file 已不存在 | 重新 preflight並標 missing |
| 409 | `inventory_selection_target_changed` | file metadata或directory manifest改變 | 重新要求使用者決定 |
| 422 | `inventory_selection_post_decision_blocked` | exact-file consent後binary/resource check不通過 | 顯示hard block，不建立scan |
| 500/422 | Plan 19 existing catalog/enumeration codes | policy unavailable/invalid | fail closed |

Error/log 不得包含 raw Git stderr、absolute root、完整 path outside project、檔案內容或 secret。
Directory limit target result的`limit_context`與HTTP error的`detail.context`使用同一
`InventoryDirectoryLimitContext`；HTTP context可再加project-relative `target_path | null`。
因walker會在越界時立即停止，只回`observed_at_least`，不得捏造完整總數。

---

## 8. Detailed end-to-end ASCII flow

```text
+-------------------+     POST /api/projects/import      +----------------------+
| Frontend          | ---------------------------------> | Backend              |
| local project UI  | <--------------------------------- | ProjectImportResponse|
+---------+---------+                                    +----------+-----------+
          |                                                         |
          | POST /api/projects/{id}/scan-preflights                 |
          | requested_paths[] + page cursor                          |
          v                                                         v
+---------+---------------------------------------------------------+-----------+
|                    METADATA-ONLY PREFLIGHT                                    |
|                                                                                |
|  Git/recursive enumerate                                                       |
|       |                                                                        |
|       +--> default candidates                                                  |
|       +--> ignored candidates / directory summaries                           |
|       +--> exact file resolution / bounded directory manifest                  |
|                 |                                                              |
|                 v                                                              |
|  lstat + root containment + file metadata / recursive directory metadata      |
|  (NO content read; directory expansion must finish within hard bounds)         |
|                 |                                                              |
|                 v                                                              |
|  catalog/project-ignore classification                                         |
|       +--> included                                                            |
|       +--> soft_excluded                                                       |
|       +--> hard_blocked                                                        |
|       +--> missing                                                             |
|                 |                                                              |
|                 v                                                              |
|  metadata fingerprints + candidate_set_digest + preflight_request_id          |
+---------+---------------------------------------------------------+-----------+
          |                                                         |
          | InventoryPreflightResponse                              |
          | - summary                                               |
          | - required_boundary_proposals                           |
          | - reviewable_excluded_page                              |
          | - blocked/missing summaries                             |
          v                                                         |
+---------+---------+                                               |
| Frontend review   |                                               |
|                   |                                               |
| required item:    |  scan / skip must choose                      |
| soft excluded:    |  default skip; may choose scan                |
| exact included:   |  default scan; may choose skip                |
| exact directory:  |  show counts; scan/skip all selectable files  |
| hard blocked:     |  explain only; no action                      |
| missing:          |  explain only; no phantom row                 |
+---------+---------+                                               |
          |                                                         |
          | POST /api/scans                                         |
          | preflight_request_id + scoped boundary_decisions[]       |
          v                                                         v
+---------+---------------------------------------------------------+-----------+
|                    BACKEND REVALIDATION                                         |
|                                                                                |
|  Re-enumerate file metadata/directory manifests + reload policy                 |
|       |                                                                         |
|       +-- digest/fingerprint changed? -- yes --> 409 stale/missing, STOP        |
|       |                                                                         |
|       no                                                                        |
|       v                                                                         |
|  Validate unique decisions + allowed target/action                              |
|       |                                                                         |
|       +-- required decision missing? -- yes --> requires_boundary_decision      |
|       |                                      (NO scan_id/snapshot/build)         |
|       no                                                                        |
|       v                                                                         |
|  Apply exact-file > deepest-directory > ancestor > default overlay              |
|       |                                                                         |
|       +--> selected for scan                                                     |
|       +--> skipped by default                                                    |
|       +--> skipped by user this run                                              |
|       v                                                                         |
|  Post-decision content safety (bounded open/binary/absolute cap)                 |
|       |                                                                         |
|       +-- exact-file blocked --> typed error, STOP                               |
|       +-- directory child blocked --> skip child + audit/count                   |
|       v                                                                         |
|  Materialize ONE final FileInventory + deterministic audit/digests              |
+---------+---------------------------------------------------------+-----------+
          |                                                         |
          v                                                         v
+---------+---------+     final FileInventory          +------------+-----------+
| Snapshot service  | -------------------------------> | Current Step 3         |
| save scan result  |                                  | providers read allowlist|
+---------+---------+                                  +------------+-----------+
          |                                                         |
          +--> ScanSnapshot.scan_result + inventory selection audit |
          |                                                         |
          +--> Step 4 bridge -> Step 5 index -> Step 6 assessment   |
          |                                  -> Step 7 publish       |
          |                                                         |
          | ScanCreateResponse(completed, scan_id, build_result)     |
          v                                                         |
+---------+---------+                                               |
| Frontend          | -- existing latest-build/viewer refresh ------+
| render backend    |
| map/report only   |
+-------------------+
```

---

## 9. Backend execution sequence

### 9.1 Preflight sequence

1. Route 取得 existing imported project；project root 只在 backend 使用。
2. `InventoryPreflightService.build_candidate_set()` 叫用 filesystem provider metadata
   enumeration。
3. Apply Plan 19 catalog matcher，但保留 `included` 與 `soft_excluded`，不立即丟棄後者。
4. Apply pre-content hard checks：root containment、type、symlink、stat、absolute metadata cap。
5. 對每個requested path做`lstat`；file建立metadata proposal，directory完成bounded recursive
   manifest並建立summary/proposal。
6. 建立required sensitive proposals、soft-excluded page、requested target results與summaries。
7. Canonical sort後計算`candidate_set_digest`、file/directory fingerprints與
   `preflight_request_id`。
8. 回metadata-only payload；不寫project state repository。

### 9.2 Scan submit sequence

1. 重新跑同一 candidate builder，禁止信任 client 回傳的 reason/base outcome。
2. 重新計算 expected preflight id；不同即回 stale。
3. 用`(target_path, selection_scope)`建立unique decision map；同scope duplicate/conflict fail
   closed，overlapping scopes保留給precedence resolver。
4. Exact-file decision驗path+metadata fingerprint；recursive-directory decision重新完整enumerate
   並驗manifest fingerprint與bounds。
5. 對 required candidates檢查 decision；未決定就回 pending proposals。
6. 依hard safety→exact file→deepest directory→ancestor directory→default計算effective selection。
7. 對effective included files執行post-decision open/binary/resource safety；directory child blocked
   逐file skip/audit，exact file blocked fail closed。
8. 每個approved directory若0個files通過則回typed error；否則產生directory scope result counts。
9. 產生final `FileInventory`、audit、decision digest、inventory run digest與selection summary。
10. 才呼叫`ScanSnapshotService.scan_and_save()`。
11. Existing build service 從 snapshot materialize build；成功後 existing latest pointer atomic
    promotion 不變。

### 9.3 Content read boundary

```text
Before user decision                         After valid decision/default
------------------------------------------   ---------------------------------
read .gitignore/catalog policy content       bounded binary probe
read path names                              provider source/config parser read
read lstat/stat metadata                     final content fingerprint
DO NOT read candidate source content         snapshot facts/evidence generation
DO NOT create snippets                       build artifacts
```

### 9.4 Final inventory invariant

Plan 20 範圍內的以下 consumers 必須接到同一 ordered allowlist + same digest：

- current KAI TOML providers；
- `ProjectScanService`；
- content fingerprint/snapshot writer；
- static call graph/dataflow/execution recovery；
- any packaging/launcher adapter。

任何 consumer 若重新 `rglob()`、重新跑 Git 或自行讀 ignored files，視為 P1 contract violation。
UA 不列在本次 consumers；Plan 20 不新增 UA import、呼叫或 parity assertion。

---

## 10. Frontend contract 與 state management

> **本節不是本計畫執行範圍。** 以下僅描述 backend HTTP／payload 對 frontend consumer 的契約與
> 建議 UX 分區，供 Meeting-Sync handoff。**禁止**在執行 Plan 20 時修改 `frontend/`、新增
> React hooks／modal、或把 Vitest／`pnpm build` 列為本計畫完成條件。前端實作見
> `docs/work/Meeting-Sync/meeting_sync_2026_07_15/`。

### 10.1 Reuse existing UI（deferred — contract reference only）

延伸 `BoundaryDecisionModal` 成「Review scan scope」，不要建立第二個互不相干的 file decision
modal。Internal component name可先保留，避免一次無關 rename；使用者可見 copy 更新即可。

Dialog opening copy必須先建立正確心智模型，例如：

> KAI-Mind 已依預設規則準備建議的掃描範圍。你可以只針對這次掃描調整；不會修改專案或永久設定。

不得使用「建立掃描清單」「從所有檔案開始選」等copy，避免把runtime delta誤解成baseline authoring。

UI sections：

1. **Needs your decision**：default included sensitive files；每筆必選 scan/skip。
2. **Excluded by default**：`.gitignore`／catalog soft exclusions；default skip，可選 scan。
3. **Exact path overrides**：輸入file後顯示單檔status/action；輸入directory後顯示recursive
   summary、hard bounds與「掃描／略過全部可掃描檔案」。
4. **Cannot be scanned**：hard block、missing、empty/over-limit directory唯讀理由；collapsed
   directory summary提供「展開此資料夾」動作，但未展開前沒有decision action。
5. **Summary**：default-included/reviewable/hard blocked/missing counts、selected directory scope
   counts與source mode。

### 10.2 Frontend 收到什麼、保存什麼

Frontend state只保存：

```text
projectSession
preflightResponse
latest preflightRequestId
decisionByProposalId
requestedExactPaths
directoryScopeSummaryByProposalId
reviewableExcludedPages
flowStatus
inlineError
```

Preflight/review state不得另行保存或推導：

- proposal/error/audit中的absolute project root（existing `ProjectImportResponse.project_path`的
  migration不在本計畫範圍，但不得複製到selection records或review copy）；
- file content/snippet；
- hidden hard safety bypass；
- catalog effective outcome；
- canonical inventory audit；
- long-lived「always scan」偏好。

### 10.3 State machine

```text
                 +--------+
                 |  idle  |
                 +---+----+
                     | Start scan
                     v
                +----+-----+
                | importing|
                +----+-----+
                     | project imported
                     v
               +-----+------+
               | preflighting|
               +--+-------+-+
                  |       |
          success |       | fatal error
                  v       v
             +----+----+  +-------+
        +--->| reviewing|  | error |
        |    +--+---+---+  +---+---+
        |       |   |          | retry
        | exact |   | submit   +----------+
        | path /|   v                     |
        | dir / | +----------+             |
        | page  | |submitting| <-----------+
        +-------+ +----------+
                     |   |
        stale/missing|   | completed
                     |   v
                     | +---------+    refresh latest viewer
                     | |completed| ------------------------> idle/viewer
                     | +---------+
                     v
                  +--+---+
                  | stale|
                  +--+---+
                     | refresh preflight
                     v
                  reviewing

Any non-submitting review state -- Cancel --> cancelled/idle
Cancel discards preflight and all one-run decisions.
```

### 10.4 Default choices與 submit enablement

- Required item：不預選；全數有 explicit decision 才可 submit。
- Soft-excluded item：UI 顯示「預設略過」；不需要為每個 item建立 decision。只有使用者切到
  scan 時才送 `scan_this_run`。
- Exact requested default-included item：UI 顯示「預設掃描」；只有使用者切到 skip 時才送
  `skip_this_run`。
- Exact requested directory：不預選，必須選擇`scan_this_run`、`skip_this_run`或從request list
  移除。Scan action文案固定為「掃描全部可掃描檔案（N）」；summary同時顯示hard-blocked與
  sensitive counts。
- Decision array只送 explicit deltas + required decisions，不把整個 candidate list echo 回 backend。
- Hard block/missing永遠不影響 `allRequiredDecided` 計算。

### 10.5 Stale refresh

收到 stale/missing/changed：

1. Frontend 標示目前 submission 未執行，不能顯示 completed。
2. 重新呼叫 preflight。
3. 只對`target_path + selection_scope + fingerprint`都相同的proposal保留使用者choice；directory
   fingerprint代表完整descendant manifest。
4. File metadata或directory manifest改變、path missing、超限或outcome變成hard block時清除
   choice。
5. 新 required proposal 必須重新取得 explicit decision。

不得在 stale 後自動重送舊 decision。

### 10.6 Accessibility與 copy

- Dialog 使用 `role="dialog"`、可辨識 heading、focus trap、Escape cancel（submit 中禁用）。
- 每個 choice group 的 accessible name包含 project-relative path。
- Directory group的accessible description包含selectable、sensitive與hard-blocked counts；不能只
  用顏色表示部分files不會被掃描。
- Error與 stale notification 使用 `aria-live`。
- Copy 必須明說「只適用這次 scan」與「不會修改 `.gitignore`」。
- 不顯示「已儲存偏好」、「永久允許」或「修改 ignore rule」。
- Path很長時視覺可截斷，但 accessible text與 copy button保留完整 project-relative path。

---

## 11. Downstream consumption 與 lineage

```text
                 NEW SCAN / RESCAN
                       |
                       v
              Inventory preflight P1
                       |
                user decisions D1
                       |
                       v
          final FileInventory + run digest R1
                       |
                       v
                ScanSnapshot S1
                - scan_result
                - file fingerprints
                - inventory audit
                - policy/candidate/decision/final digests
                       |
             +---------+----------+
             |                    |
             v                    v
       Initial Build B1       Current Step 3 providers
             |
             v
       Step 4 -> 5 -> 6 -> 7 -> Viewer


                 APPLY CONFIRMED MAPPINGS
                       |
                       v
                reuse Snapshot S1
                (NO preflight, NO repo read,
                 NO new inventory decisions)
                       |
                       v
                    Build B2
             Step 4 replay -> overlay -> 4..7


                       RESCAN
                         |
                         v
              new Preflight P2 + Decisions D2
                         |
                         v
              new Inventory R2 -> Snapshot S2
                         |
                         v
                       Build B3

P1/D1 decisions expire after S1. They never become defaults for P2.
```

### 11.1 Snapshot persistence

Completed snapshot新增/保存：

```text
inventory_source_mode
inventory_policy_schema_version
inventory_policy_digest
candidate_set_digest
filesystem_safety_version
boundary_decision_digest
final_inventory_digest
inventory_run_digest
inventory_selection_audit[]
inventory_selection_summary
```

- `preflight_request_id` 可出現在 audit provenance，但 preflight response本身不另存成 project
  resource。
- Legacy snapshot 欄位 optional；讀取時標 `legacy_inventory_selection_unknown`，不可用目前
  catalog重建假的歷史決策。
- Apply 只讀 S1 已保存 final facts/digests，不重新詢問使用者。

### 11.2 UA integration deferred boundary

Plan 20 的 executable path 到 `ScanSnapshot`／current build pipeline 即停止。本計畫：

- 不建立 UA request；
- 不傳送 `files[]` 給 UA；
- 不 import 或呼叫 UA service；
- 不新增 KAI/UA parity test；
- 不修改 Plan 16 task、adapter 或 sidecar schema。

Final `FileInventory` 與 `inventory_run_digest` 是通用 scanner provenance，不是 UA 專用輸出。
Plan 16 日後若接 UA，必須自行提出 integration contract 與測試；不得把那段工作回填成 Plan 20
完成條件。

### 11.3 Audit digest

Plan 19 的 `inventory_run_digest` 增加這次 selection inputs：

```text
candidate_set_digest
inventory_policy_digest
filesystem_safety_version
boundary_decision_digest = sha256(sorted(path, selection_scope, fingerprint, decision))
final_inventory_digest
```

同一 target metadata、catalog、安全版本與 decisions 必須得到同一 ordering/digest；任一項改變
就不得宣稱可重現同一次 inventory。

---

## 12. Security、privacy 與 resource safety

### 12.1 No-read-before-decision

- Preflight 可讀 ignore/catalog policy檔，因為它們是 selection規則。
- Preflight不可讀 candidate內容；existing content-based boundary fingerprint必須移到
  post-decision。
- `evidence_packet.masked_snippets`在 preflight固定空值。
- Provider/content parser只能收到 final inventory。

### 12.2 Size policy分層

```text
default_large_file_review_threshold
  -> soft_excluded / reviewable
  -> user may scan_this_run

absolute_max_file_size_bytes
  -> hard_blocked
  -> user cannot override

max_recursive_directory_files = 5_000
max_recursive_directory_selectable_bytes = 500_000_000
max_recursive_directory_depth = 64
max_recursive_directory_scopes_per_preflight = 20
max_recursive_directory_unique_files_per_preflight = 5_000
max_recursive_directory_unique_selectable_bytes_per_preflight = 500_000_000
  -> any exceeded: no proposal, no partial approval
```

兩個門檻都留在 Python safety config，不移入 TOML；必須在 contract/test明確命名，避免同一
`max_file_size_bytes`同時代表可覆寫與不可覆寫。

### 12.3 Binary policy

Preflight只可依 metadata/extension標示「可能是 binary」，不能假裝已確認。只有
`scan_this_run`後做 bounded probe：

- 支援的 textual content → 進 final inventory；
- exact-file unsupported binary → `inventory_selection_post_decision_blocked`；
- recursive-directory descendant unsupported binary → child hard-blocked audit/count，其他children
  繼續；若0 children通過則`inventory_selection_directory_no_scannable_files`；
- probe read failure → hard block；
- 不把 probe bytes、signature或 raw error寫入 API/audit。

### 12.4 Race / TOCTOU

Metadata fingerprint只能降低 preflight→submit race，不能單獨保證 open時檔案不變。Post-decision
read需：

1. safe-open file handle；
2. open後 `fstat`；
3. compare type/size/mtime with approved metadata；
4. mismatch即中止，不把已讀部分交給 provider；
5. final content hash綁定 snapshot。

Recursive directory另外必須在submit時重新enumerate完整manifest，並在任何child open前比對
manifest fingerprint；不得一邊掃描一邊接受新出現的files。Manifest通過後，仍對每個child做
上述safe-open/fstat，避免directory驗證後的第二次race。

平台無法提供完全相同 safe-open primitive時，adapter必須 fail closed並有 macOS/Windows
integration fixtures，不能用 path resolve一次後無條件 open。

---

## 13. Implementation tasks（TDD、tiny commits）

### Start Gate：Task 0 前先驗收 Plan 19 non-UA baseline

- [ ] Default `scan_inventory_rules.toml`已涵蓋product支援categories、reason、priority與precedence。
- [ ] Loader/schema/unknown-field/duplicate-id/missing/invalid fail-closed tests通過。
- [ ] Git／recursive／fallback parity與macOS／Windows path contract tests通過。
- [ ] Default inventory可在沒有optional override時deterministically建立，且policy/audit/run digests
  可回讀。
- [ ] Python無hidden default path list；filesystem safety仍是獨立、不可覆寫的Python contract。
- [ ] 此gate不等待Plan 16 UA request、adapter或parity；Plan 20仍不接UA。

任一項未通過時，Plan 20保持blocked；不得先做file picker讓使用者人工彌補catalog gap。

### Task 0：凍結 current behavior 與 API compatibility

Files:

- Modify: `tests/unit/core/test_filesystem_provider.py`
- Modify: `tests/unit/core/test_scan_boundary_review_service.py`
- Modify: `tests/web/test_project_scan_routes.py`
- Create: `frontend/src/services/projectScanApi.test.ts`

Steps:

- [ ] 寫 characterization test：Git default query不含 ignored untracked file。
- [ ] 寫 characterization test：current boundary service只對 `inventory.files`建立 proposal。
- [ ] 寫 pending response contract test：沒有 `scan_id`、沒有 snapshot/build state。
- [ ] 寫 frontend failing test，證明目前 Zod無法 parse pending response。
- [ ] 執行：
  `uv run pytest tests/unit/core/test_filesystem_provider.py tests/unit/core/test_scan_boundary_review_service.py tests/web/test_project_scan_routes.py -q`
- [ ] 執行：`cd frontend && pnpm test -- projectScanApi.test.ts`。
- [ ] Commit：`test(scan): characterize inventory boundary preflight gaps`

### Task 1：建立 richer candidate model 與 metadata fingerprint

Files:

- Create: `src/kai_mind/core/models/inventory_selection.py`
- Modify: `src/kai_mind/core/models/filesystem.py`
- Modify: `src/kai_mind/core/models/scan_boundary.py`
- Create: `tests/unit/core/test_inventory_selection_models.py`

Steps:

- [ ] 先寫`InventorySelectionScope`、target kind、directory manifest/summary、canonical sorting、
  unknown field與path normalization tests。
- [ ] 寫file metadata fingerprint deterministic test；path/type/size/mtime任一改變都改digest。
- [ ] 寫directory manifest fingerprint test；任一descendant新增/刪除/rename/type/size/mtime、
  policy/safety outcome、risk或decision requirement改變都改digest，只改directory mtime但manifest
  entries不變則不影響結果。
- [ ] 寫 test證明 fingerprint不含 absolute root或 content bytes。
- [ ] 實作 frozen Pydantic internal models與 additive `selection_context`；API view留給web schema
  adapter，core不得import web layer。
- [ ] 保留舊 `ScanBoundaryProposal` fixture可讀，`selection_context=None`。
- [ ] 執行：`uv run pytest tests/unit/core/test_inventory_selection_models.py tests/unit/core/test_scan_boundary_review_service.py -q`。
- [ ] Commit：`feat(scan): define inventory selection candidate contract`

### Task 2：枚舉 ignored candidates與bounded recursive directory manifests

Files:

- Modify: `src/kai_mind/core/providers/filesystem_provider.py`
- Modify: `src/kai_mind/core/services/path_safety_service.py`
- Modify: `tests/unit/core/test_filesystem_provider.py`
- Modify: `tests/integration/test_phase7_filesystem_provider_behaviors.py`

Steps:

- [ ] 建 Git fixture：default、ignored file、ignored directory、tracked+ignored、tracked missing。
- [ ] 建recursive fixture：nested `.gitignore`、collapsed ignored directory、exact file lookup與
  exact directory full expansion。
- [ ] 寫 `git check-ignore -z -v` 解析 tests，並證明 global exclude absolute source path 不進
  API/audit。
- [ ] 寫 unmatched ignore pattern test：無 candidate、無 per-file audit、scan不失敗。
- [ ] 寫exact directory tests：`.` project root、soft-excluded `node_modules/` traversal、`.git/**`
  hard prune、outside-root symlink不follow、FIFO/special child hard block。
- [ ] 寫5,000 files可通過、5,001 files fail；500,000,000 bytes可通過、500,000,001 bytes fail；
  depth 64可通過、65 fail的boundary tests，並驗證無truncated proposal。
- [ ] 寫20 directory scopes可進入expansion、21 scopes在walker前fail；parent/child overlap只計一次，
  non-overlap aggregate第5,001 file／500,000,001 byte整個preflight fail且無partial results。
- [ ] 加 ignored Git query並保存 directory summary；不得把 raw Git stderr放進 warning。
- [ ] 實作exact requested path resolver：regular file→`exact_file`、directory→完整
  `DirectorySelectionManifest`、glob/traversal/symlink/special→typed result。
- [ ] 把 current silent `not path.is_file()`改為 typed missing/non-regular outcome。
- [ ] 驗證 Git/recursive/fallback刻意差異與 shared policy parity。
- [ ] 執行：`uv run pytest tests/unit/core/test_filesystem_provider.py tests/integration/test_phase7_filesystem_provider_behaviors.py -q`。
- [ ] Commit：`feat(scan): enumerate reviewable excluded inventory targets`

### Task 3：實作 metadata-only preflight service

Files:

- Create: `src/kai_mind/core/services/inventory_preflight_service.py`
- Modify: `src/kai_mind/core/services/scan_boundary_review_service.py`
- Modify: `src/kai_mind/web/dependencies.py`
- Create: `tests/unit/core/test_inventory_preflight_service.py`

Interfaces:

- `InventoryPreflightService.create(project_id, project_root, request) -> InventoryPreflightState`
- `InventoryPreflightService.resolve_requested_path(project_root, target_path) -> InventoryRequestedTargetResult`
- `InventoryPreflightService.revalidate(project_id, project_root, preflight_request_id, decisions) -> InventoryPreflightState`
- `ScanBoundaryReviewService.create_selection_proposals(preflight_state) -> list[ScanBoundaryProposal]`

Steps:

- [ ] 先寫四 outcome、proposal grouping、stable ordering與digest tests。
- [ ] 寫 no-content-read spy test；preflight期間任何 candidate `open/read_bytes`都必須讓 test失敗。
- [ ] 寫required sensitive、soft-excluded、exact included、recursive directory、hard blocked/
  missing/empty/over-limit matrix。
- [ ] 寫baseline projection test：`requested_paths=[]`時的default included/soft-excluded outcome、
  policy version與digest全部來自Plan 19，preflight不得發明hidden defaults。
- [ ] 寫directory summary counts、root `.` normalization、manifest fingerprint與no-content-read tests。
- [ ] 寫 exact requested reviewable result inline proposal與跨section `proposal_id`去重 test。
- [ ] 寫 pagination/cursor binding tests；cursor不得洩漏 path，跨 project/digest不可重用。
- [ ] 實作 stateless preflight id與bounded response。
- [ ] `masked_evidence_values`/`masked_snippets`固定空 array。
- [ ] 執行：`uv run pytest tests/unit/core/test_inventory_preflight_service.py tests/unit/core/test_scan_boundary_review_service.py -q`。
- [ ] Commit：`feat(scan): add metadata-only inventory preflight service`

### Task 4：實作 per-run overlay 與 post-decision safety

Files:

- Modify: `src/kai_mind/core/services/scan_boundary_review_service.py`
- Modify: `src/kai_mind/core/providers/filesystem_provider.py`
- Modify: `src/kai_mind/core/models/errors.py`
- Modify: `tests/unit/core/test_scan_boundary_review_service.py`
- Create: `tests/unit/core/test_inventory_selection_safety.py`

Steps:

- [ ] 先寫precedence matrix所有rows：hard safety、exact file、deepest directory、ancestor
  directory、default outcome。
- [ ] 寫 duplicate/conflict、unknown target、hard-block decision、stale fingerprint tests。
- [ ] 寫soft-excludedfile/directory `scan_this_run`進final inventory、included file/directory
  `skip_this_run`移出tests。
- [ ] 寫directory scan + exact child skip、ancestor scan + deeper directory skip與同scope conflict tests。
- [ ] 寫client以多次preflight累積individually-valid directory proposals後，submit仍重算aggregate並
  拒絕超過5,000 unique files／500,000,000 unique selectable bytes的decisions。
- [ ] 寫 no-optional-decision parity test：effective result等於Plan 19 default outcome；required
  sensitive candidate仍維持pending，不可因Plan 20自動scan或skip。
- [ ] 將 current content-derived proposal fingerprint改為 metadata fingerprint；legacy/non-preflight
  sensitive flow也不得在decision前讀candidate內容或產snippet。
- [ ] 使用者同意後才做bounded binary probe、safe-open/fstat與absolute cap；directory manifest先
  整體revalidate，再逐child safe-open。
- [ ] Exact-file post-decision block fail closed；directory child block只跳該child並增加audit/count；
  directory 0 final files回`inventory_selection_directory_no_scannable_files`。
- [ ] 同 decisions重算結果idempotent，audit不重複。
- [ ] 執行：`uv run pytest tests/unit/core/test_scan_boundary_review_service.py tests/unit/core/test_inventory_selection_safety.py -q`。
- [ ] Commit：`feat(scan): apply safe one-run inventory selection overlay`

### Task 5：新增 preflight API並擴充 scan request

Files:

- Modify: `src/kai_mind/web/schemas.py`
- Modify: `src/kai_mind/web/routes/scan_routes.py`
- Modify: `src/kai_mind/web/dependencies.py`
- Modify: `tests/web/test_project_scan_routes.py`
- Modify: `tests/web/test_scan_boundary_routes.py`

Steps:

- [ ] 先寫preflight happy path、pagination、requested file/directory、root `.`、404/422 tests。
- [ ] 寫missing/invalid catalog contract test：preflight fail closed、沒有candidate/proposal payload、
  沒有`scan_id`，且exact path input不能繞過。
- [ ] 寫`InventoryRequestedTargetView` web schema與projection contract test：directory只回
  summary+manifest fingerprint，不序列化internal `DirectorySelectionManifest.entries[]`；core layer
  不import web schema。
- [ ] 寫`POST /api/scans` file fingerprint、directory manifest、scope mismatch、stale/missing/
  changed/limit/blocked error contract tests。
- [ ] 寫 pending invariant：無 `scan_id`、無 snapshot/build/latest pointer/output directory。
- [ ] 寫completed invariant：final inventory才進snapshot/build，response
  `inventory_selection_summary.directory_scope_results[]`與final audit counts一致。
- [ ] Add optional `preflight_request_id`到 request/response，舊 request仍可走 current sensitive flow。
- [ ] Error detail使用 typed object與stable code；不得只回 raw exception string。
- [ ] 執行：`uv run pytest tests/web/test_project_scan_routes.py tests/web/test_scan_boundary_routes.py -q`。
- [ ] Commit：`feat(api): expose inventory preflight and selection decisions`

### Task 6：保存 audit、digest並鎖住 downstream allowlist

Files:

- Modify: `src/kai_mind/core/models/analysis_history.py`
- Modify: `src/kai_mind/core/models/scan.py`
- Modify: `src/kai_mind/core/services/scan_snapshot_service.py`
- Modify: `src/kai_mind/core/services/project_scan_service.py`
- Modify: `tests/integration/test_scan_snapshot_materialization.py`
- Modify: `tests/unit/core/test_project_scan_service.py`
- Modify: `tests/contracts/test_secret_snapshot_safety.py`

Steps:

- [ ] 先寫 snapshot round-trip與legacy optional-field tests。
- [ ] 寫decision/final/run digest deterministic與change-detection tests；decision digest納入
  `selection_scope`與directory manifest fingerprint。
- [ ] 寫 provider spy：只可看到 final `FileInventory.files`。
- [ ] 寫skipped ignored/explicit-skip file或directory descendants不被任何provider open的test。
- [ ] 寫directory decision展開per-file audit，且每筆保存相同decision target/scope的round-trip test。
- [ ] 寫 audit/log/snapshot不含 absolute path、secret value、snippet的 contract test。
- [ ] 以 changed-file review與`rg`驗證本計畫diff沒有UA imports、service calls、request adapter、
  parity fixture或Plan 16檔案變更；本task不新增UA-specific test。
- [ ] 驗證 Apply沿用 snapshot且 filesystem/preflight spy零呼叫；Rescan建立新 digest。
- [ ] 執行：
  `uv run pytest tests/integration/test_scan_snapshot_materialization.py tests/unit/core/test_project_scan_service.py tests/contracts/test_secret_snapshot_safety.py -q`
- [ ] Commit：`feat(scan): persist inventory selection provenance`

### Task 7：Frontend schema與API client — **DEFERRED（不做）**

> **本 task 不在 Plan 20 執行範圍。** 保留條目只為標出 backend contract 就緒後，前端另案要做的
> 工作；執行 Plan 20 的 agent **跳過**本 task，不得修改 `frontend/`。

Files:（參考用，本計畫不改）

- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/services/projectScanApi.ts`
- Modify: `frontend/src/services/projectScanApi.test.ts`

Deferred steps（Meeting-Sync／frontend-owned）：

- [ ] ~~先把 `scan_id` pending parse test寫紅，再改為 `z.string().optional()`。~~
- [ ] ~~加`inventoryPreflight*`、`InventorySelectionScope`、directory summary與completed selection
  summary Zod schemas；所有enum與backend完全一致。~~
- [ ] ~~Add `createScanPreflight()`與page/exact file/directory path request support。~~
- [ ] ~~`startProjectScan()`傳optional `preflightRequestId`；每筆decision送
  `selection_scope`，且只送explicit deltas/required decisions。~~
- [ ] ~~寫 malformed response、typed error與no-absolute-path display tests。~~
- [ ] ~~執行：`cd frontend && pnpm test -- projectScanApi.test.ts`。~~
- [ ] ~~Commit：`feat(frontend): add inventory preflight API contract`~~

### Task 8：Frontend flow state與review UI — **DEFERRED（不做）**

> **本 task 不在 Plan 20 執行範圍。** 同上；UI／hook／modal 由 Meeting-Sync frontend work item
> 承接。

Files:（參考用，本計畫不改）

- Create: `frontend/src/hooks/useProjectScanFlow.ts`
- Create: `frontend/src/hooks/useProjectScanFlow.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/BoundaryDecisionModal.tsx`
- Create: `frontend/src/components/BoundaryDecisionModal.test.tsx`
- Modify: `frontend/src/styles.css`

Deferred steps：（略；見 Meeting-Sync `frontend-inventory-selection-review.md`）

### Task 9：Docs、contract sample與 backend end-to-end regression

Files:

- Modify: `docs/API-GUIDE.md`
- Modify: `docs/MODEL-CONTRACT.md`
- Modify: `frontend/API_CONTRACT.md`（**僅文件同步 contract sample；不實作 frontend code**）
- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase4-scanner-expansion/00-phase2-pipeline-ascii-map.md`
- Create: `tests/e2e/test_inventory_selection_scan_flow.py`（**pytest／API client，非 browser UI**）

Steps:

- [ ] 將本文件API payload/error codes同步到三份canonical contract；不得只留在 plan。
- [ ] 明列 preflight不是 scan、pending無 `scan_id`、Apply vs Rescan lifecycle。
- [ ] E2E fixture含：normal source、ignored exact file、bounded ignored directory、nested exact
  override、sensitive child、hard binary/symlink child、unmatched ignore rule、preflight後directory
  child新增/刪除。
- [ ] E2E驗證directory `scan_this_run`納入所有soft-excluded safe descendants、exact child skip勝出、
  hard-blocked child不被讀取，completed summary與snapshot audit counts一致。
- [ ] E2E驗證target repo tree與Git status前後完全不變。
- [ ] 執行：`uv run pytest tests/e2e/test_inventory_selection_scan_flow.py -q`。
- [ ] 執行 backend 全套：`uv run pytest -q`（**不要**跑 `pnpm test`／frontend lint／build 作為本
  task 通過條件）。
- [ ] Commit：`docs(scan): document user-controlled inventory selection`

---

## 14. Test matrix

| Source | Base outcome | User input | Expected final | Snapshot/build? |
| --- | --- | --- | --- | ---: |
| Plan 19 baseline | valid catalog | no optional override | exact same default outcome/digest | according to required review |
| Plan 19 baseline | missing/invalid catalog | exact file/directory input | typed fail-closed; no picker fallback | no |
| Git default | included normal | none | included | yes |
| Git default | included sensitive | none | pending | no |
| Git default | included sensitive | scan | included after safety | yes |
| Git default | included sensitive | skip | skipped | yes |
| `.gitignore` | soft excluded file | none | skipped | yes |
| `.gitignore` | soft excluded file | scan | included after safety | yes |
| `.gitignore` | pattern unmatched | none | no candidate/audit row | yes |
| `.gitignore` | exact requested missing | scan | 409 missing | no |
| Catalog | soft excluded generated file | scan | included after safety | yes |
| Catalog | collapsed directory under bounds | scan directory | all safe descendants included | yes |
| Catalog | collapsed directory | skip directory | all selectable descendants skipped; hard blocks unchanged | yes |
| Directory | scan parent + skip exact child | scoped decisions | exact child skipped; other safe children included | yes |
| Directory | scan parent + skip nested directory | scoped decisions | deepest nested scope wins | yes |
| Directory | project root `.` under bounds | scan directory | all safe repo files included; `.git/**` blocked | yes |
| Directory | exact `.git` or `.git/**` | any | hard-blocked; never reported empty | no |
| Directory | 5,001 files / >500MB / depth 65 | scan directory | 422 directory limit | no |
| Directory | 21 scopes / aggregate >5,000 unique files | preflight | 422 before partial proposal set | no |
| Directory | empty / no selectable child | scan directory | no proposal / 422 if forged | no |
| Directory | manifest changed after preflight | prior directory decision | 409 target changed | no |
| Directory | one unsupported binary child | scan directory | child skipped/audited; other safe children included | yes |
| Directory | all children post-decision blocked | scan directory | 422 no scannable files | no |
| Safety | outside-root symlink | scan | 422 not allowed | no |
| Safety | absolute oversize | scan | 422 not allowed | no |
| Post-decision | unsupported binary | scan | 422 blocked | no |
| Exact path | included normal | skip | skipped | yes |
| Any | metadata changed after preflight | prior choice | 409 stale/changed | no |
| Any | duplicate decisions | duplicate | 422 duplicate | no |
| Apply | existing snapshot | none | reuse prior inventory | new build, no new scan |
| Rescan | project changed | old decision absent | new preflight | new scan/build |

---

## 15. Migration、rollout與rollback

### 15.1 Backward-compatible rollout

1. 先加 additive model/schema；舊 proposal與snapshot可讀。
2. 加 preflight endpoint，但 `POST /api/scans.preflight_request_id`先 optional。
3. **本計畫只交付 backend API／pytest／contract docs。** Frontend 切到 preflight flow、pending
   `scan_id` Zod parser 修正，由 Meeting-Sync frontend work item 另案執行（不阻塞本計畫
   backend DoD）。
4. Frontend 就緒並觀察 e2e／parity後，再考慮將新 UI flow設為default（非本計畫 task）。

舊 client未使用 preflight時：

- 仍只能對 current default-included sensitive files做既有 decisions；
- `selection_scope`缺省為`exact_file`，舊decision不會意外變成recursive selection；
- 不允許對 soft-excluded path送decision；
- 不影響現有 API consumer；
- response新增optional fields不應破壞 parser。

### 15.2 Rollback flag

若需要 rollout guard，只允許 backend-owned temporary flag：

```text
inventory_preflight_enabled=false
```

Flag off時關閉新 preflight endpoint與soft-exclusion override，但保留舊 sensitive boundary flow。
不得讓 flag切回會寫 repo的做法，也不得同時存在兩個 snapshot writer。Flag的移除條件：backend
E2E、legacy client contract與security tests全通過後，在同一 release plan記錄移除（frontend
build 通過是後續 frontend task 的條件，**不是**本計畫 rollback 移除的硬條件）。

### 15.3 Rollback invariant

- Rollback不刪除已有 snapshot中的additive audit fields。
- Older reader忽略新欄位；new reader可讀legacy null。
- 已完成scan的inventory不得在rollback後被重新解釋。
- Target repo永遠無需rollback，因為feature從未寫入。

---

## 16. Acceptance Criteria

### 16.1 Backend DoD（本計畫必須通過）

- [ ] Plan 19 non-UA TOML baseline gate先通過；Plan 20不是missing/invalid/incomplete catalog的fallback。
- [ ] 沒有optional runtime decisions時沿用KAI推薦default outcome；caller只提交本次delta，不需從
  空白inventory逐檔建立選擇。
- [ ] Preflight／scan HTTP 可回傳 required sensitive、soft-excluded、hard-blocked/missing 摘要
  （pytest／API 驗證即可；**不要求** React UI 已渲染）。
- [ ] Caller可用exact project-relative path要求backend解析regular file或directory；directory
  path建立bounded `recursive_directory` proposal。
- [ ] `.gitignore`/Git exclude/catalog soft exclusion可被`scan_this_run`單次覆寫。
- [ ] Default-included exact path可被`skip_this_run`單次排除。
- [ ] Directory `scan_this_run`納入其下所有通過hard safety的regular files，包含soft-excluded
  descendants；directory `skip_this_run`排除其下所有selectable descendants，hard-blocked outcome
  不被改寫。
- [ ] Exact-file decision勝過deepest/ancestor directory decisions；同一scope conflict fail closed。
- [ ] Collapsed directory summary可要求backend展開；hard safety、missing、empty/over-limit
  directory不可覆寫。
- [ ] Directory summary、manifest fingerprint、final selection summary與per-file audit可回溯實際
  included/blocked counts，不宣稱hard-blocked entries已掃描。
- [ ] Ignore pattern存在但檔案不存在時，不建立phantom candidate/proposal/per-file audit。
- [ ] Preflight不讀candidate內容、不建立snippet、不建立scan/snapshot/build。
- [ ] Backend重新enumeration並驗證preflight id與metadata fingerprint，stale不得自動沿用。
- [ ] Decision只形成in-memory overlay；不改`.gitignore`、TOML、target file或manual mapping state。
- [ ] 所有 current providers 只讀同一 final `FileInventory`；Plan 20 runtime 不 import、不呼叫
  UA，UA integration 明確 deferred 到 Plan 16。
- [ ] Snapshot保存base/effective outcome、decision、policy/candidate/final/run digests與安全audit。
- [ ] Pending與pre-snapshot selection error沒有`scan_id`；snapshot已建立後的existing build
  error可帶真實`scan_id`，completed則回`scan_id`與build result。
- [ ] Directory超過5,000 files／500MB／64 depth時fail closed，不得silent truncate前N筆；
  `scan_this_run`與`skip_this_run`共用同一上限。
- [ ] 整庫 default-included 檔數 >5,000 且未對該大目錄做 recursive decision 時，一般scan不得因
  此directory bound失敗；僅collapsed、未展開的soft-excluded大目錄亦不因此讓preflight失敗。
- [ ] Contract docs 區分：TOML+gitignore=預設略過政策；Plan 20=one-run overlay；非Manual Mapping。
- [ ] Apply不重新preflight或讀repo；Rescan產新preflight且不沿用舊decision。
- [ ] macOS/Windows path normalization、安全open與case contract有tests。
- [ ] Backend pytest／contract／e2e通過；target repo unchanged。

### 16.2 Frontend（明確不在本計畫驗收）

以下項目 **deferred** 到 Meeting-Sync 2026-07-15 frontend work；**不得**列為 Plan 20 完成阻擋：

- [ ] ~~Frontend清楚說明目前清單是KAI預先設定的建議範圍…~~
- [ ] ~~Frontend pending response可通過Zod parse，stale/refresh/cancel狀態有tests。~~
- [ ] ~~Full frontend test、lint、build通過。~~
- [ ] ~~BoundaryDecisionModal／useProjectScanFlow UI 行為。~~

---

## 17. Out of scope

- **本計畫執行不實作任何 frontend code／Vitest／pnpm build**（§10／Task 7–8 deferred）。
- 不提供永久「always scan/never scan」偏好。
- 不允許runtime glob、follow symlink或unbounded recursive override；exact directory selection只在
  5,000 files、500,000,000 bytes、64 depth bounds內成立。
- 不把「整庫 default-included >5,000」誤實作成必須 fail closed；該上限僅針對 directory
  recursive selection／aggregate directory decisions（見 §1.5 E、§5.4）。
- 不對 `skip_this_run` 的 directory scope 放寬 5,000／bytes／depth（scan與skip共用同一manifest
  契約）。
- 不修改Git ignore files、global Git config或KAI catalog。
- 不把selection decision存成`ManualMapping`或送入Step 9 Apply。
- 不讓frontend推論hard/soft outcome、risk type或final inventory（契約約束；本計畫亦不實作
  frontend）。
- 不把預設略過政策改成「只靠前端勾選、沒有TOML baseline」；Plan 19 catalog仍是default skip
  source of truth。
- 不建立或接上 UA request、sidecar、`files[]` adapter、parity harness或Plan 16 runtime。
- 不支援掃描outside-project path。
- 不因使用者同意而放寬absolute resource cap、symlink或special-file safety。
- 不在preflight做source semantics、component mapping、profile inference或LLM分析。

---

## 18. 外部研究依據（查證日：2026-07-15）

- [Git `git-ls-files` 官方文件](https://git-scm.com/docs/git-ls-files)：使用
  `--cached --others --exclude-standard`建立default source，並用
  `--others --ignored --exclude-standard --directory`觀察ignored entries與directory summary。
- [ripgrep Guide](https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md)：成熟scanner會分層
  處理ignore來源、hidden/binary與explicit path，而不是把所有排除視為同一不可解釋black box。
- [Semgrep ignore reference](https://docs.semgrep.dev/semgrepignore-v2-reference)：ignore precedence、
  Git-style pattern與product-owned exclusion需要明確分層。
- [Semgrep ignoring files documentation](https://docs.semgrep.dev/ignoring-files-folders-code)：
  filesystem/project ignore與scanner-owned exclusion應提供可解釋來源與受控 override。
- [Semgrep current text reporting source](https://github.com/semgrep/semgrep/blob/develop/src/osemgrep/reporting/Text_reports.ml)：
  current implementation把always-skipped與Gitignored原因分組呈現；本計畫只借鏡「原因分層」與
  可觀察性，不複製其程式碼或contract。

從這些來源採用的原則是：**ignore是layered default、explicit exact target可被重新評估、hard
safety另外管理、排除原因必須可解釋**。本產品額外維持release-readiness scanner的read-only、
no-secret-output、snapshot reproducibility與Apply/Rescan lineage限制。

---

## 19. Definition of Done

這個feature的 **Plan 20 backend DoD** 只有在以下事實同時成立才算完成：

```text
API/preflight returns metadata-only candidates
  -> caller submits exact file or bounded recursive-directory decisions for this run
  -> backend revalidates the same file metadata or complete directory manifests
  -> hard safety remains authoritative
  -> one final inventory is materialized
  -> every scanner consumes that inventory
  -> snapshot records why each path was included/skipped
  -> build publish uses the resulting snapshot
  -> target repository remains byte-for-byte untouched
  -> frontend UI is NOT required for this DoD
```

只完成UI、只增加API欄位、只把ignored path放回`inventory.files`、或只寫audit而未阻止provider
二次enumeration，都不算完成。  
**反過來說：未完成 React／Zod／modal 也不阻擋本計畫 backend DoD**；前端另案追蹤。
