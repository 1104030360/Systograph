# Capability Map Assessment Decision Summary

Status: confirmed Phase 2 contract decision.

Audience: Timmy backend implementers, Hardy frontend implementers, reviewers, and
future plan authors.

Last updated: 2026-07-08（對齊 `docs/MODEL-CONTRACT.md`、`docs/API-GUIDE.md`：`activation`、
`scan_id` / `environment_id` scope；Phase2 不另設 `snapshot_id`）。

## Purpose

本文件凍結 Capability Map assessment 的共同語意，作為
`ai-system-map/v2`、`profile-signals/v1`、`readiness-report/v1` 與
`GraphViewModel` 的規劃依據。它不宣稱目前 source code 已實作這些欄位；實作仍需依
各 Phase2 plan 逐步完成。

`DeepResearch/` 是研究與 UI 草稿參考，不是可直接複製的 schema、source code、fixture
或產品 contract。任何研究建議都必須先經本 repo 的 deterministic-first、安全、相容性與
evidence contract 審核後，才能進入 implementation plan。

## Confirmed Product Model

Capability Map 採用兩層表示：

```text
Fixed ten-plane / 52-node reference map
  = 穩定的能力座標與 reference nodes
  = 用來比較不同 AI systems

Repo overlay for one assessed build
  = 實際掃描到的 repo components / edges / evidence
  = 對位 reference nodes，但不假裝 reference node 一定存在於 repo
```

Reference map 與 repo overlay 不得合併成一套模糊 node type：

- **Reference node**：產品定義的穩定能力座標。它可以在沒有 repo evidence 時存在於
  reference map，但不能因此被判為 repo 已實作。
- **Repo component**：由目前 build/snapshot 的 deterministic evidence 支撐的實際元件。
  它可對位零個、一個或多個 reference nodes；無法可靠對位時保留為 unmapped。
- Frontend 必須用不同 visual semantics 顯示 reference node 與 repo component。
- Canonical truth 是 repo facts 與 evidence；reference map、overlay、filters 和 layout 都是
  versioned projection contract。

固定十個 plane：

| Order | Plane id | Display name |
|---:|---|---|
| 1 | `input_intent` | Input & Intent Plane |
| 2 | `control` | Control Plane |
| 3 | `ingestion_indexing` | Ingestion & Indexing Plane |
| 4 | `retrieval` | Retrieval Plane |
| 5 | `extension_subsystems` | Extension Subsystems Plane |
| 6 | `evidence` | Evidence Plane |
| 7 | `generation` | Generation Plane |
| 8 | `memory_state` | Memory & State Plane |
| 9 | `governance_observability` | Governance & Observability Plane |
| 10 | `deployment_topology` | Deployment Topology Plane |

固定底圖包含 52 個 reference nodes，完整 ids/counts 以 `docs/MODEL-CONTRACT.md` 與
Plan `01A` 為準。Governance / observability 現在是 canonical plane；cross-plane
governance lens 可保留為 backend-derived view，但不得建立第二套 canonical facts。
`extension_subsystems` 只代表 reference grouping，不恢復已退役的 `ExtensionComponent`
product contract。TOML 可保存 label、description、legend copy 與排序；Python 擁有對位、
狀態、衝突、coverage gate 與 scoring 行為。

舊 8-plane / 35-node 是 superseded planning/prototype draft；production catalog 尚未建立，
所以不新增 runtime dual-read。若保留舊 fixture 作 regression 對照，只能以 explicit id
mapping 轉換，不得依 display label 或 alias 猜測。

## Unified Assessment Status

所有 capability/reference-node assessment 統一使用五態：

```text
detected | partial | undetermined | not_detected | conflicted
```

| Status | Meaning | Minimum evidence rule |
|---|---|---|
| `detected` | 已有足夠證據證明該 capability 在此 scope 存在 | 至少一項 direct evidence 並通過 capability-specific gate；多個 convergent indirect signals 仍不得升級為 detected |
| `partial` | 只完成該 capability 的部分必要訊號或路徑 | 有直接或明確 evidence，但 required coverage 未達 `detected` gate |
| `undetermined` | 有相關訊號，但證據不足以判定存在或不存在 | indirect、ambiguous、unresolved mapping 或 coverage 不足 |
| `not_detected` | 在已完成足夠 coverage 的 scope 內未偵測到該 capability | 必須先通過 capability-specific `not_detected` coverage gate；不得把「尚未掃到」當成不存在 |
| `conflicted` | 同一欄位、同一 scope 的可信證據互相矛盾 | conflict refs 必須指出互斥 evidence 與受影響欄位 |

舊三態不是 active target contract。Migration adapter 可將舊資料映射為五態，但新 output
不得再以 coverage/depth/reason 隱藏 `partial` 或 `conflicted` 的一級語意。

## Activation

Assessment status 回答「能力是否被辨識」；JSON 欄位名 **`activation`** 回答「能力在此環境
是否啟用」（不是 `activation_state`）。
兩者不可合併：

```text
enabled | disabled | conditional | unknown | conflicted | not_applicable
```

| Activation state | Meaning |
|---|---|
| `enabled` | 有直接 config/wiring/path evidence 顯示此環境啟用 |
| `disabled` | 有 explicit negative evidence 顯示明確關閉 |
| `conditional` | 由 feature flag、route、environment、input 或 runtime branch 決定 |
| `unknown` | 靜態 evidence 無法判斷是否啟用 |
| `conflicted` | 同一 activation 欄位與 scope 有互斥證據 |
| `not_applicable` | Reference catalog metadata 宣告此 node 本質上沒有啟用/停用語意；不是 backend 對目前 system/scope 的判斷 |

`detected + disabled`、`partial + conditional`、`detected + unknown` 都是合法組合。
不得因 capability 被 detect 就自動填 `enabled`。

## Evidence Model

Evidence 必須區分：

- **Direct evidence**：AST/symbol/call edge、validated workflow JSON pointer、明確 config
  binding、route-to-handler、實際 component wiring，或經核准的 runtime envelope。
- **Indirect evidence**：dependency、檔名、README claim、命名、prompt wording、generic
  framework usage，或缺少完整 call/dataflow linkage 的 signal。只有 indirect evidence 時
  一律是 `partial`，即使有多個彼此一致的 indirect signals 也不能升級成 `detected`。
- **Explicit negative evidence**：明確 disabled flag、bypassed branch、forbidden policy、
  deny/skip branch、被驗證的空 registry、incompatible config，或其他直接否定特定欄位的
  證據。單純 absence / 沒搜尋到不是 explicit negative。

每筆 assessment 至少能回查：

```text
evidence_id
evidence_kind = direct | indirect | explicit_negative
project-relative path / config key / JSON pointer
optional symbol and line range
rule id / parser id
build_id + scan_id + environment_id scope
```

LLM semantic assist 只能解釋 bounded deterministic fact packet；它不能建立 canonical
component/edge/evidence、不能單獨改變五態、不能解決未被 deterministic evidence 支撐的
conflict。

## Assessment Scope

每個結果都綁定 **`scan_id` / `build_id` / `environment_id`**：

- `build_id`：已驗證 artifact set 的 immutable identity。
- `scan_id`：一次 immutable read-only scan snapshot identity（Phase2 **不另設**
  `snapshot_id`）；相同 repo 的不同 commit、import 或 Apply build 不可混用 evidence。
- `environment_id`：Phase2 固定為 `environment:default-static`；不提供建立、選擇或切換
  environment。
- 未指定 environment 時必須使用明確的 `environment:default-static` scope，不可假裝是
  production。

同一 capability 在不同 `environment_id` 可以有不同 `activation`。Frontend 比較結果時
必須顯示 scope，避免把 staging disabled 與 production enabled 合併成單一結論。

## Field-Specific Conflict

Conflict 必須落在欄位，不得粗暴把整個 component/profile 都標成 conflicted：

```text
assessment.status = detected
assessment.activation = "conflicted"
assessment.conflicts = [
  { field: "activation", evidence_ids: ["...", "..."] }
]
```

可能衝突的欄位包含 status、activation、provider、endpoint、relationship、version、
environment binding 與 implementation depth。未受衝突影響的欄位仍保留其已驗證值。

## `not_detected` Coverage Gate

只有在 scanner 證明對該 capability 的必要 evidence surfaces 已完成 bounded coverage 時，
才能輸出 `not_detected`。Gate 至少記錄：

- required providers/parsers 是否執行；
- required file/config/workflow surfaces 是否在 scan boundary 內；
- parse warnings、unsupported language、ignored files 與 size/cap limits；
- required positive/negative signals 的檢查結果；
- coverage 不足時為何只能輸出 `undetermined`。

只有 catalog metadata 宣告該 reference node 本質上沒有 activation 語意時，才使用
`activation="not_applicable"`。對有 activation 語意的 node，backend 必須輸出
`enabled`、`disabled`、`conditional`、`unknown` 或 `conflicted`；不得依目前 system/scope
臨時改成 `not_applicable`，也不得用 `not_detected` 取代 activation 判斷。

## Mapping Completeness

Mapping Completeness 是 reference-map coverage 指標，不是 model confidence、品質保證或
release verdict。每個固定 reference node 的權重如下：

| Status | Weight |
|---|---:|
| `detected` | 1.0 |
| `not_detected` | 1.0，僅限 coverage gate 通過 |
| `partial` | 0.5 |
| `undetermined` | 0.0 |
| `conflicted` | 0.0 |

```text
mapping_completeness = sum(status_weight) / total_fixed_reference_node_count
```

- `not_detected` 未通過 coverage gate時，必須先降為 `undetermined`，權重為 0。
- denominator 永遠是 catalog 內全部固定 reference nodes；activation 與
  `not_applicable` 都不排除任何 node。
- Catalog metadata 必須宣告每個 reference node 的 activation applicability（data-only）；
  Python 依 evidence 推論實際 `activation`。
- UI 可以顯示百分比，但必須同時顯示分子、分母、各狀態數量、scope 與公式說明。
- 此數值不得命名為 confidence、accuracy、readiness score 或 mapping quality。

## Python / TOML Ownership

Python 擁有所有 executable semantics：

- reference-node matching 與 repo-component mapping；
- 五態判斷與 capability-specific gates；
- activation-state inference；
- direct/indirect/explicit-negative evidence classification；
- field-specific conflict resolution；
- `not_detected` coverage gate；
- Mapping Completeness denominator、weights 與 calculation；
- cross-field validation 與 fail-closed behavior。

TOML 只擁有 data-only metadata：

- plane/reference-node ids、display labels、descriptions、排序；
- 每個 reference node 是否本質上具有 activation 語意的 applicability metadata；
- legend copy、default uncertainty、recommended next checks；
- evidence-kind 和 activation-state 的 display wording；
- 不含 regex、conditions、thresholds、weights、conflict precedence、provider config、prompt、
  lifecycle action 或任意 executable expression。

## Frontend Legend Contract

Frontend legend 至少清楚區分：

1. reference node 與 repo component；
2. 五種 assessment status；
3. 六種 activation state；
4. direct、indirect、explicit-negative evidence；
5. static inferred 與 runtime observed；
6. current build/snapshot/environment scope；
7. Mapping Completeness 的分子、分母與非 confidence 說明。

Frontend 只 render backend `GraphViewModel`/assessment contract，不自行從 node 名稱、
dependency 或 topology 重建 status、activation、conflict 或 Mapping Completeness。

## Deterministic-First and Understand-Anything Boundary

本專案採用 Understand-Anything 類型的兩階段思想：

```text
deterministic repository/workflow scan
  -> bounded structural facts + evidence graph
  -> domain-specific capability assessment
  -> optional bounded semantic explanation
  -> reference-map repo overlay + readiness artifacts
```

差異在於 Systograph 不是通用 codebase knowledge-map clone：

- Systograph 使用固定 10-plane / 52-node 的 AI capability reference map。
- Systograph 的輸出是 release-readiness evidence、capability status、activation、conflict 與
  next checks，不是只產生 repository symbol/import graph。
- Systograph 不把 raw source tree 整包交給 LLM，也不讓 LLM 產生 canonical facts。
- Systograph 必須保留 unknown、partial、not-detected coverage 與 environment scope，而不是
  為了畫出完整圖而補猜缺失節點。

## Plan Ownership

- Plan 00：`rag-core-v1` legacy v1 template boundary；不定義 active product
  readiness layer 或 frontend summary。
- Plan 00A：generic v2 facts、五態基礎欄位、scope 與 v1 adapter。
- Plan 02：capability assessment/profile inference；不擁有 artifact writer、graph projection
  或 frontend renderer。
- Plan 03：唯一 artifact lifecycle / writer / build-result owner。
- Plan 06：backend reference-map + repo-overlay projection，以及最小 frontend consumption
  contract。
- Plan 10/11：Python executable semantics 與 TOML metadata 邊界。
- Plan 14：fixtures、external repo validation、coverage gate 與 contract regression；不是產品
  Validation Simulator。
- Plan 15：只在 00A、13、14、18 gates 通過後收斂 active v2 / legacy compatibility。

## Completion Gate

- [ ] `MODEL-CONTRACT.md` 與 00A/02/03/06/10/11/14/15 使用相同五態與 activation enum。
- [ ] 所有 status/activation 都綁定 `scan_id` / `build_id` / `environment_id` scope。
- [ ] `not_detected` 無法繞過 coverage gate。
- [ ] Mapping Completeness 使用固定 weights，且沒有 confidence/mapping-quality wording。
- [ ] Capability Map / profile / readiness findings 是唯一 active assessment surface。
- [ ] Python/TOML ownership 無 executable metadata drift。
- [ ] Frontend 不自行推論 assessment facts。
- [ ] DeepResearch 未被當成 schema 或 code source 直接複製。
