# 前端工作：Scan Inventory Review 與 per-run override

Status: backend contract ready；frontend implementation／integration pending

Last updated: 2026-07-16（Plan 19／20 backend gate、Pydantic samples 與 live API trace 已通過）

## 目的

這不是從空白建立scan inventory。Backend會先以已驗收的Plan 19
`scan_inventory_rules.toml`產生KAI推薦baseline；延伸目前`BoundaryDecisionModal`與project scan
flow，讓使用者在每次scan前依自己的需求調配：

- 決定 default-included sensitive file 要掃或略過；
- 從 `.gitignore`／Git exclude／KAI catalog soft-excluded files 中選擇本次要掃的 exact file；
- 輸入 exact project-relative file 或 directory path，要求 backend解析；directory path 會建立
  bounded recursive selection，代表其下所有通過 hard safety 的 regular files；
- 對default-included exact path選擇本次略過；
- 對reviewable directory明確選擇「掃描全部可掃描檔案」或「略過全部可掃描檔案」；
- 看懂hard block、missing、empty與directory limit理由，但不能越過backend safety。

所有choice只適用一次scan。UI不得暗示已修改ignore rule或保存永久偏好。
Catalog missing/invalid時backend必須fail closed；Frontend不得退回空白file picker要求使用者自行
建立清單。

## 產品語意速查（與 Plan 20 §1.5／會議釐清同步）

### 預設略過 vs 這次調配

- **預設跳過什麼**：Plan 19 TOML + `.gitignore`（產品／專案政策）。
- **這次要不要例外**：Plan 20 preflight → `scan_this_run`／`skip_this_run`（one-run overlay）。
- **Hard safety**：永遠不可覆寫；UI只顯示原因，不提供 override control。

### 使用者會「看到」什麼

| 看到 | 看不到／不逐檔列出 |
| --- | --- |
| 敏感檔必答列 | 全部 default-included 一般檔的 checkbox 樹 |
| soft-excluded 分頁（可 Load more） | 未展開的 `node_modules/` 底下數萬檔 |
| exact path 查詢結果 | Manual Mapping 表單 |
| hard block／over-limit 摘要 | absolute path、檔案內容、secret |

Summary 的 `default_included_file_count` 可以很大；那代表「預設會掃多少」，**不是**要前端
逐檔渲染。

### Fail closed 與 5,000

- Directory／aggregate 超 **5,000 files、500MB、64 depth** → 不可批准；**不得**只掃前 N 筆。
- `scan_this_run` 與 `skip_this_run` 的 recursive directory **同一上限**（都要完整 manifest）。
- 已被 soft exclude 的大目錄，使用者不 Expand／不 Check path → **維持略過，不報 5,000 錯**。
- 整庫 default-included >5,000 → **一般 scan 仍可進行**；上限不套在整庫 default inventory。

Copy 建議：

- Over-limit：`Too large to select as one folder; choose a smaller folder.`（不要寫「已掃描前
  5000 個」。）
- Soft-excluded 大目錄摘要：`Excluded by default. Expand only if you need this folder this run.`

### 不是 Manual Mapping

File／directory selection 是掃前 I/O 授權；不要重用 Manual Mapping store、reducer 或
`/api/mappings`。Dialog 互動可以像 proposal → decision，但資料模型必須分開。

## 依賴與開始條件

Canonical plan：

- [Plan 19：Inventory Selection Policy Catalog](../../Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-track-d-inventory/19-add-scan-inventory-rules-toml.md)
- [Plan 20](../../Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-track-d-inventory-review/20-add-user-controlled-scan-inventory-selection.md)
  （§1.5 產品語意澄清、§5.4 5,000 bound scope）

開始整合前，backend至少需提供：

- Plan 19 non-UA TOML baseline gate已通過，default inventory、policy digest與audit sample可用；
- `POST /api/projects/{project_id}/scan-preflights`；
- `InventoryPreflightResponse` sample／schema；
- additive `ScanBoundaryProposal.selection_context`；
- `POST /api/scans.preflight_request_id`；
- stable error `detail.code`；
- pending response無`scan_id`的contract test。

以上 backend prerequisites 已於 2026-07-16 全部提供；8 份 Step 2 JSON samples 已通過 current
Pydantic validation，backend regression 為 `972 passed`。Frontend 仍需自行完成 Zod、flow state、
accessibility、browser E2E 與 build gate，不能把 backend 綠燈視為 UI 已完成。

Frontend可以先獨立完成現有bug修正：把
`scanCreateResponseSchema.scan_id`從required改為optional，並補pending parse test。

## Baseline contract（Frontend視角）

Frontend不負責判斷TOML規則「夠不夠完整」，也不讀取或解析TOML。Backend只有在Plan 19 gate
通過後才能回成功preflight；成功payload內的下列欄位共同識別這次KAI-prepared baseline：

```text
source_mode
inventory_policy_schema_version
inventory_policy_digest
candidate_set_digest
filesystem_safety_version
```

Frontend必須遵守：

- Baseline是backend truth；不得在browser重算include/exclude或補一份hidden default list。
- `summary` count為0可能只是合法空專案，不能據此推論catalog missing/invalid。
- Catalog是否可用只能看typed API error；不可從空array、warning copy或HTTP message猜測。
- `inventory_policy_schema_version`可顯示成使用者可理解的policy版本；完整digest主要供stale、audit
  與support details使用，不需塞進每一列UI。
- Preflight成功後，default rows代表prepared baseline outcome；使用者只送explicit delta與required
  confirmation。
- Plan 20允許的soft-exclusion override是Plan 19 baseline之上的one-run extension，不代表TOML規則
  可以不完整。

Plan 19 catalog failure的stable codes：

| `detail.code` | 意義 | Frontend行為 |
| --- | --- | --- |
| `inventory_rules_unavailable` | packaged TOML缺失或不可讀 | 進`baseline_error`，不render review controls、不呼叫scan |
| `inventory_rules_invalid` | parse/schema/field/id/action/pattern validation失敗 | 進`baseline_error`，不render review controls、不呼叫scan |

Safe error UI只顯示backend message與retry guidance，不顯示TOML內容、package path、raw exception或
absolute local path。是否顯示Retry依`detail.retryable`，但Retry只重做preflight，不能切換到blank
authoring mode。

## Frontend 會拿到的資料

Preflight top-level：

```text
preflight_request_id
project_id
generated_at
source_mode
inventory_policy_schema_version
inventory_policy_digest
candidate_set_digest
filesystem_safety_version
summary
required_boundary_proposals[]
reviewable_excluded_page
requested_target_results[]
blocked_summaries[]
warnings[]
```

`requested_target_results[]` 每筆都有 `proposal: ScanBoundaryProposal | null`；只有
`status="reviewable"` 有 actionable proposal。每筆另有backend判定的
`target_kind=file|directory`；directory result必須使用proposal內的bounded summary，Frontend
不得自行enumerate。若同一 proposal 同時出現在required/page/requested result，Frontend以
`proposal_id`去重，不能顯示或送出兩次decision。

其他requested target status：

```text
hard_blocked
missing
empty_directory
directory_limit_exceeded
```

這些status均不可送decision。Collapsed directory summary本身也不可送decision；使用者按下
「Expand this folder」後，Frontend要把該exact directory path加入`requested_paths`，由backend
完整展開並回傳新的reviewable directory proposal。

`directory_limit_exceeded` result的`limit_context`，以及typed 422 error的`detail.context`，皆提供：

```text
limit_kind
limit
observed_at_least
optional project-relative target_path
```

Frontend不得把`observed_at_least`顯示成完整總數；也不得暗示「已選取前 N 筆繼續掃描」。

每個actionable proposal沿用existing shape，並新增：

```text
selection_context.base_outcome
  included | soft_excluded | mixed

selection_context.review_kind
  required_confirmation | optional_override

selection_context.default_decision
  scan_this_run | skip_this_run | null

selection_context.decision_required
selection_context.override_allowed
selection_context.exclusion_sources[]
selection_context.matched_inventory_policy_ids[]
selection_context.target_kind
  file | directory

selection_context.selection_scope
  exact_file | recursive_directory

selection_context.directory_summary
  null | {
    observed_regular_file_count,
    selectable_file_count,
    default_included_count,
    soft_excluded_count,
    sensitive_file_count,
    pre_content_hard_blocked_count,
    selectable_bytes,
    observed_max_relative_depth,
    blocked_reason_counts
  }
```

Frontend不得從`reason`文字反推 enum，也不得依file extension自行判斷hard/soft。

## UI information architecture

延伸 `frontend/src/components/BoundaryDecisionModal.tsx`，使用者可見名稱改為
`Review scan scope`。保留同一dialog，不建立另一個file picker modal。

Opening copy需先說明：「KAI-Mind已依預設規則準備建議掃描範圍；以下調整只適用這次scan。」
Default rows應標示prepared baseline的`Default: scan/skip`，並呈現backend source/reason。不要把
project `.gitignore`誤標成KAI catalog rule，也不能讓使用者以為所有檔案都尚未設定。

```text
+------------------------------------------------------------------+
| Review scan scope                                                |
| KAI-Mind prepared a recommended baseline for this project.       |
| Adjustments apply once. .gitignore and policy stay unchanged.    |
+------------------------------------------------------------------+
| Summary: 143 included | 12 excluded | 3 blocked | 1 missing      |
+------------------------------------------------------------------+
| Needs your decision (2)                                          |
|  .env                     [Scan this run] [Skip this run]         |
|  local/vector.db          [Scan this run] [Skip this run]         |
+------------------------------------------------------------------+
| Excluded by default (12)                              [Load more] |
|  ignored/custom.py        Default: skip   [Scan this run]         |
+------------------------------------------------------------------+
| Add exact file or folder path                                    |
|  [ node_modules/small-local-package                ] [Check path] |
|  -> Folder: 84 selectable | 3 blocked | 12.4 MB                   |
|     [Scan all selectable files] [Skip all selectable files]      |
+------------------------------------------------------------------+
| Cannot be scanned / not found                                    |
|  node_modules/             Too large; choose a smaller folder    |
|  missing.env               File not found                        |
|  link-outside              Outside project root                  |
+------------------------------------------------------------------+
| [Cancel]                                           [Continue]    |
+------------------------------------------------------------------+
```

## Decision mapping

| Payload case | Default UI | Must choose? | Send decision when |
| --- | --- | ---: | --- |
| Included + sensitive | none | yes | always |
| Soft-excluded | skip | no | only if user chooses scan |
| Exact requested included file | scan | no | only if user chooses skip |
| Reviewable recursive directory | none | yes | always; scan or skip all selectable files |
| Collapsed directory summary | no action; may request expansion | no | never |
| Hard blocked | no action | no | never |
| Missing | no action | no | never |
| Empty/over-limit directory | no action | no | never |

不要用current `decisionsForBoundary()`的fallback把所有未決proposal自動轉成
`skip_this_run`。新的serializer必須區分required decision與default outcome，只送explicit
deltas + required decisions。

## Request flow

### 1. Import後先preflight

```ts
const preflight = await createScanPreflight(baseUrl, {
  projectId,
  requestedPaths: [],
  reviewableExcludedCursor: null,
  reviewableExcludedLimit: 100,
});
```

只有成功preflight才可進`reviewing`。若收到`inventory_rules_unavailable`或
`inventory_rules_invalid`，立即進`baseline_error`：不建立empty preflight object、不保留可提交
decision，也不以exact path lookup重試繞過catalog gate。

### 2. 使用者可要求exact file/directory path解析

- Input只做基本non-empty UX validation；安全/path normalization以backend回覆為準。
- 再呼叫preflight並帶目前deduplicated exact paths；Frontend不以trailing slash猜file或directory。
- Exact directory回`reviewable`時顯示backend提供的完整manifest摘要，並要求使用者明確選擇
  `scan_this_run`或`skip_this_run`。`scan_this_run`的UI copy固定為「掃描全部可掃描檔案」，不可
  宣稱會繞過hard safety或真的包含symlink／special file／`.git/**`。
- Collapsed directory的「Expand this folder」只觸發新的preflight，不代表已選擇掃描。
- 保存 response 的 latest `preflight_request_id`；base candidate state 未變時它可以與舊值相同。
- 既有choice只有在`target_path + selection_scope + fingerprint`相同時保留；directory fingerprint
  代表完整descendant manifest。
- Missing、hard-blocked、empty與over-limit result沒有choice control。
- Over-limit 必須用 fail-closed copy；不可提供「只掃前 N 個」的假 action。

### 3. Submit scan

```ts
await startProjectScan(baseUrl, {
  projectId,
  preflightRequestId,
  boundaryDecisions: explicitDecisions,
});
```

Frontend只送：

```text
target_path
fingerprint
decision
selection_scope
optional reason
```

`selection_scope`不得由path字串推測：file decision送`exact_file`，directory decision送
`recursive_directory`。

不要echo `base_outcome`、policy ids、size、risk type或hard safety facts；backend會重新建立與驗證。

### 4. Backend response

```text
requires_boundary_decision
  -> merge最新required proposals，保持dialog開啟
  -> scan_id必須absent

completed
  -> 清除preflight/choices/requested paths
  -> 可顯示backend inventory_selection_summary.directory_scope_results
  -> 呼叫GET /api/projects/{project_id}/map-builds/latest
  -> 保存response的scan_id/build_id並切換viewer_load_result
  -> 不從decisions自行patch graph

inventory_preflight_stale / target_changed / target_missing
  -> 顯示此次沒有開始scan
  -> refresh preflight
  -> 只保留path+selection_scope+fingerprint仍相同的choices
  -> 不自動retry scan

inventory_rules_unavailable / inventory_rules_invalid
  -> 此次沒有建立preflight或開始scan；scan_id必須absent
  -> 清除任何actionable review state
  -> 顯示baseline unavailable/invalid safe error
  -> 不render file/directory decision controls
  -> 只有detail.retryable=true才提供Retry preflight

other typed error
  -> 保留review內容供使用者修正/重試
  -> 顯示safe message，不顯示raw response stack/path
```

## State ownership

建議建立 `frontend/src/hooks/useProjectScanFlow.ts`，避免preflight、decision、stale與viewer
refresh繼續堆進`App.tsx`。

```text
idle
  -> importing
  -> preflighting
      -> baseline_error (catalog unavailable/invalid; no review controls)
          -> preflighting (explicit safe retry only)
          -> cancelled -> idle
  -> reviewing
      -> preflighting (exact file/directory path / folder expansion / next page)
      -> submitting
          -> reviewing (remaining required)
          -> stale -> preflighting -> reviewing
          -> completed -> viewer refresh
          -> error
      -> cancelled -> idle
```

Hook應own：

- imported project session；
- current preflight response/id；
- baseline policy identity（schema version/digest）與typed `baseline_error`；
- pages與requested exact file/directory paths；
- decisions keyed byproposal id，並可用path+scope+fingerprint reconcile；
- busy/stale/error states；
- submit/cancel/reset transitions。

`App.tsx`只提供start action、modal composition、progress copy與existing completed viewer refresh。

## Files

Modify:

- `frontend/src/types.ts`
- `frontend/src/services/projectScanApi.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/BoundaryDecisionModal.tsx`
- `frontend/src/styles.css`

Create:

- `frontend/src/services/projectScanApi.test.ts`
- `frontend/src/hooks/useProjectScanFlow.ts`
- `frontend/src/hooks/useProjectScanFlow.test.tsx`
- `frontend/src/components/BoundaryDecisionModal.test.tsx`

## Implementation checklist

### Contract與service

- [ ] 增加`inventory_rules_unavailable`／`inventory_rules_invalid` typed error normalization；不可把
  failure parse成empty success payload。
- [ ] `scanCreateResponseSchema.scan_id`改為optional，並補pending parse regression test。
- [ ] 增加preflight summary/page/result/selection-context Zod schemas。
- [ ] 增加`InventorySelectionScope`、directory summary與completed
  `inventory_selection_summary.directory_scope_results` schemas。
- [ ] Zod enum與backend exact value一致；unknown enum fail closed。
- [ ] 增加`createScanPreflight()`與pagination/exact file/directory path request。
- [ ] `startProjectScan()`可傳`preflightRequestId`。
- [ ] 每筆decision明確serialize `selection_scope`，不得從path尾端slash猜scope。
- [ ] Typed API error能讀`detail.code`與`retryable`。

### Flow state

- [ ] Import成功後不直接scan，先preflight。
- [ ] 只有successful baseline preflight可進reviewing；catalog error進`baseline_error`且不能submit。
- [ ] Retry只重送preflight，不保留或產生任何decision。
- [ ] Required proposals未全決定時Continue disabled。
- [ ] Soft-excluded default skip不製造大量decision rows。
- [ ] Exact included default scan，只有skip時送delta。
- [ ] Reviewable directory必須明確選scan-all-selectable或skip-all-selectable，未決定時Continue
  disabled。
- [ ] Exact path重新preflight後以path+scope+fingerprint reconcile choice。
- [ ] Stale不自動submit舊choice。
- [ ] Cancel/complete清空one-run state。

### UI

- [ ] Opening copy與default labels清楚表達「KAI已設定baseline，user只做one-run調配」。
- [ ] Default row同時顯示backend outcome/source；project ignore不得誤標為KAI catalog rule。
- [ ] Baseline error畫面不render path input、decision buttons或空白candidate sections。
- [ ] 顯示summary counts與source mode。
- [ ] 四種sections有清楚heading/copy。
- [ ] Soft exclusion顯示backend提供的source/reason，不自行判斷。
- [ ] Reviewable directory顯示selectable/blocked/bytes/depth摘要與scan-all/skip-all controls。
- [ ] Collapsed directory只有expand action；hard blocked/missing/empty/over-limit沒有decision controls。
- [ ] Directory limit error顯示backend `limit_kind`、`limit`與`observed_at_least`，不宣稱已取得完整count。
- [ ] Over-limit copy 明確 fail closed，不提供「掃前 N 筆」action。
- [ ] Directory copy使用「全部可掃描檔案」，不宣稱hard-blocked entries已包含。
- [ ] 顯示「只適用這次scan」與「不修改`.gitignore`／TOML」。
- [ ] Copy／helper 不暗示「整庫 included >5,000 就不能掃」。
- [ ] Load more使用opaque cursor，不從cursor解析path。
- [ ] Long project-relative path可讀、可copy且不洩漏absolute root。
- [ ] Dialog focus、Escape、keyboard、aria-live與disabled state通過RTL tests。

## Required tests

### `projectScanApi.test.ts`

- [ ] Normalize exact `inventory_rules_unavailable`與`inventory_rules_invalid` codes、message、retryable。
- [ ] Catalog error不可parse成`InventoryPreflightResponse`，也沒有`preflight_request_id`／`scan_id`。
- [ ] Parse pending response without `scan_id`。
- [ ] Parse completed response with `scan_id`。
- [ ] Serialize preflight request／exact file-directory paths／cursor。
- [ ] Serialize scan request with preflight id + explicit decisions only。
- [ ] Serialize file=`exact_file`、directory=`recursive_directory`，並parse directory summary/result。
- [ ] Parse completed directory scope actual included/blocked counts，不自行重算。
- [ ] Reject malformed enum/payload。
- [ ] Normalize typed stale/missing/blocked/directory-limit errors。

### `useProjectScanFlow.test.tsx`

- [ ] Valid baseline preflight直接render KAI recommended defaults，不建立blank authoring state。
- [ ] Missing/invalid catalog typed error不render可提交的file/directory controls。
- [ ] Catalog error後不呼叫`startProjectScan()`；safe retry只再呼叫`createScanPreflight()`。
- [ ] Zero-candidate successful response仍是valid baseline，不誤判成catalog error。
- [ ] import → preflight → review → submit → complete。
- [ ] Required proposal blocks submit until explicit choice。
- [ ] Soft-excluded no choice means no decision is sent。
- [ ] Exact included path skip sends one delta。
- [ ] Exact directory lookup stores latest preflight id and requires an explicit directory decision。
- [ ] Directory decision sends one`recursive_directory` row，不展開成thousands of client decisions。
- [ ] Exact descendant decision與ancestor directory choice可同時保存。
- [ ] Stale refresh keeps unchanged fingerprint choices only。
- [ ] Directory manifest changed會清除choice，不自動沿用。
- [ ] Cancel sends no scan request and clears state。
- [ ] Complete calls viewer refresh once。

### `BoundaryDecisionModal.test.tsx`

- [ ] Opening copy說明KAI baseline與one-run adjustment，不使用「建立inventory」語意。
- [ ] Default rows正確區分project ignore與KAI catalog source copy。
- [ ] Render summary與四sections。
- [ ] Required/optional defaults與button state正確。
- [ ] Hard block/missing沒有action controls。
- [ ] Exact file/directory path submit/loading/error可存取。
- [ ] Reviewable/collapsed/empty/over-limit directory的controls與copy各自正確。
- [ ] Over-limit copy 不含「掃前 N 筆／partial approve」語意。
- [ ] Load more callback使用backend cursor。
- [ ] Escape、focus與aria-live行為。
- [ ] Copy不宣稱permanent preference或ignore／TOML mutation。

## Verification commands

```bash
cd frontend
pnpm test -- projectScanApi.test.ts
pnpm test -- useProjectScanFlow.test.tsx BoundaryDecisionModal.test.tsx
pnpm test
pnpm lint
pnpm build
```

## Acceptance criteria

- [ ] UI從backend baseline開始，不提供空白inventory authoring mode。
- [ ] `inventory_rules_unavailable`／`inventory_rules_invalid`顯示typed fail-closed error，不要求使用者
  自行補選，也不呼叫scan。
- [ ] Zero-candidate successful preflight仍可正常顯示empty-project state，不與catalog error混淆。
- [ ] Default rows顯示真實backend source；`.gitignore`與KAI catalog不混為同一來源。
- [ ] 使用者能在一個review dialog完成required、soft-excluded與exact file/directory decisions。
- [ ] 輸入exact directory path可選擇遞迴掃描其下所有backend判定為selectable的regular files。
- [ ] Frontend只對reviewable directory送`recursive_directory` decision；永遠不能對collapsed、
  hard-blocked、missing、empty或over-limit result送decision。
- [ ] Over-limit／fail-closed 文案與 tests 明確：不可 silent truncate 前 N 筆。
- [ ] UI／tests 區分「directory recursive 超 5,000」與「整庫 default-included >5,000」。
- [ ] Frontend只送explicit deltas + required decisions，不echo全部candidate facts。
- [ ] Pending response沒有`scan_id`也可正常parse/render。
- [ ] Stale/changed/missing會重新review，不自動沿用不相同fingerprint。
- [ ] Completed後只使用backend published viewer result。
- [ ] Cancel/Rescan不保存前一次one-run decisions。
- [ ] UI清楚說明不修改`.gitignore`、TOML或永久設定。
- [ ] Unit/component/hook tests、lint與build全通過。

## Do not do

- 不把catalog failure、缺少preflight id或schema parse failure轉成empty success state。
- 不根據candidate count推論baseline health；只接受backend typed success/error contract。
- 不提供「Skip baseline」「Start from empty」「Continue anyway」等繞過Plan 19 gate的動作。
- 不新增第二套inventory decision modal。
- 不把`ManualMapping` store/reducer用在file decisions。
- 不用file extension、reason copy或frontend glob判定safety。
- 不支援runtime glob、follow symlink或unbounded directory selection；exact directory只能使用backend
  回傳的bounded proposal。
- 不把directory scope在browser展開成每個descendant decision；Frontend只送一筆scope decision。
- 不把hard block做成可點選disabled-looking override。
- 不從preflight candidates產生graph、report或scan progress完成狀態。
- 不在localStorage保存preflight id或decisions。
- 不顯示absolute local path、content snippet或secret value。
- 不提供「只掃／只略過前 N 個檔」的 UI escape hatch。
- 不把整庫 default-included >5,000 顯示成必須 fail 的 directory limit。
- 不對 directory `skip_this_run` 自行放寬 5,000／bytes／depth（與 scan 共用同一 backend 契約）。
