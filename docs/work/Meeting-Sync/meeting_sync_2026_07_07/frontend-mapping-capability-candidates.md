# 前端同步：Ambiguous Evidence Review

Last updated: 2026-07-07（UA 整合決策對齊）

## 目的（Purpose）

Plan `01` 與 `04` 將產品流程從「confirm as extension」改為
**review scanner suggestions for ambiguous evidence**。

Review scanner suggestions queue 不是顯示 scan 結果的前置條件。它是針對 high-impact、
scanner 不應自動定案的 ambiguous evidence 的 optional exception workflow。

```text
Auto scan result is available
  -> Step 4 emits unmapped needs_review / candidate input
  -> Step 6 ProfileInferenceService runs deterministic Python assessment
  -> Viewer shows a small "needs review" queue
  -> user accepts / edits / rejects / skips scanner proposal
  -> confirmed decision is saved
  -> Apply（同一 snapshot）或 explicit rescan 套用 confirmed decision
```

詳細差異見 [`rescan-vs-apply.md`](rescan-vs-apply.md)。

## Proposal 與 Manual mapping

**Proposal = 問題 + 選項（`candidates[]`）；Manual mapping = 使用者選完後存檔的決策。**
Proposal 不會直接改 profile；`confirmed` 的 Manual mapping 在 **Apply** 時才反映進新 build。
詳見 [`docs/design/epic1-phase2.md`](../../../design/epic1-phase2.md) §12。

2026-07-07 同日修訂：Step 6 由 `ProfileInferenceService` 直接讀 validated system map 與
TOML metadata，以純 Python 定五態。Plan 17 `AssessmentOrchestrator` / AI semantic candidate
flow deferred；snapshot internal `ua-analysis-result` semantic sidecar 是 reserved nullable slot，
Phase2 active path 不產生、不消費。Step 9 `MappingProposal` API 仍與 profile assessment 分離；UI 流程、proposal
payload 與 review decision API 不變，frontend 也不讀 UA sidecar。

### Step 4 / Step 9 分界

```text
Step 4 Bridge 1
  -> component                 # backend 已定案，直接進 map
  -> unmapped needs_review     # review queue 候標
  -> candidate input           # profile sidecar / review context，非 canonical

Step 6 Assessment
  -> validated ai_system_map + TOML metadata
  -> ProfileInferenceService 定五態
  -> AssessmentOrchestrator / AI candidate flow deferred

Step 9 Review
  -> POST create proposal（unmapped_id + masked evidence packet）
  -> pending MappingProposal candidates[]
  -> 使用者 decision
  -> confirmed ManualMapping
  -> Apply 建立新 build
```

Frontend 不需要、也不可以讀 scan TOML 或 `rule_id` 自行決定 component type。候選文案、
candidate type、rationale 與 allowed actions 都由 backend proposal payload 提供。

## UX 原則

不要讓使用者覺得自己在替 scanner 做分類工作。

建議文案：

```text
Scanner found 3 items worth reviewing.
Your report is already available. Reviewing these items can improve future scans.
```

避免暗示 scanner 無法運作、必須手動分類才能看報告：

```text
Please classify this before the report can be shown.
You must classify this evidence before continuing.
```

## Decision 類型

Frontend 應支援 backend candidate / decision types，代表：

- `existing_slot_mapping`：確認屬於 legacy v1 slot 或其他有效 map dimension。
- `non_baseline_capability_candidate`：確認為 capability candidate，非 canonical extension。
- `needs_more_information`：scanner 需要更多 bounded evidence。
- `skip_for_now`：使用者暫不決定。
- `not_applicable`：使用者確認此 evidence 不應影響本專案 map。

Legacy `new_extension_component` 僅可存在於 migration/legacy input。不得作為 Phase2 新流程的 active CTA。

## Frontend 任務

### 1. Review Queue 入口

Viewer 應以 non-blocking queue 呈現 review：

- 顯示 worth reviewing 的項目數量；
- 每項連結 backend 提供的 evidence snippets / source refs；
- system map、profile overlays、readiness report、static execution artifacts 保持可見。

### 2. Candidate Cards

每個 ambiguous item 渲染 backend candidates，含：

- backend label；
- rationale；
- related evidence ids；
- uncertainty / limitation 文案（若有）；
- actions：accept、edit、reject、skip。

不要新增 frontend-only candidate type。

### 3. Decision Mutation

Accepted 或 edited decisions 應使用 backend ids 與 backend payload shape。Frontend 不得
將 capability candidate 改寫成 `new_extension_component`。

儲存後文案應等同：

```text
Decision saved. Apply confirmed decisions to create a new version.
```

不要暗示目前的 `ai_system_map.json` 已被 in-place mutate。

### 4. Profile 邊界

Profile details 為唯讀。不得顯示 accept/edit/reject 按鈕。

Mapping/proposal UI 處理「這段 evidence 應 map 到哪裡」。Profile inference 處理
「哪些 capabilities 為 detected / partial / undetermined / not_detected / conflicted」。

## 驗收標準（Acceptance Criteria）

- [ ] 首次 scan 結果可在不要求 review decisions 的情況下渲染。
- [ ] Review queue 僅對 backend 提供的 ambiguous evidence 出現。
- [ ] Candidate cards 使用 backend labels 與 evidence ids。
- [ ] 支援 `non_baseline_capability_candidate`。
- [ ] Active UI 不以 `new_extension_component` 作 happy path。
- [ ] 儲存 decision 時明確說明需 Apply 才會建立新 build；不要寫成已修改目前 JSON。
- [ ] Profile detail 維持唯讀。

## 禁止事項（Do Not Do）

- 不要要求使用者分類整個 repo。
- 不要建立 frontend-only extension nodes。
- 不要將 decisions 寫入 artifacts。
- 不要未經使用者 decision 就將 proposal 自動提升為 canonical fact。
- 不要在 review 完成前隱藏報告。
