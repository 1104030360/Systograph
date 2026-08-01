# AI System Capability Map Graph Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:test-driven-development` for behavior changes and
> `superpowers:verification-before-completion` before claiming completion. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Phase2 evidence-backed projection穩定後，建立 production AI System
Capability Map Graph Studio：以固定 capability reference map作閱讀座標，疊加實際 repo
五態 evidence overlay，提供固定 lenses、Mapping Completeness與 evidence
inspector。

**Architecture:** Backend `GraphProjectionService` 合併 validated
`capability_reference_map.toml`、`ai-system-map/v2`、profile/readiness/evidence與 durable mapping
state，輸出單一 versioned viewer projection。Frontend只 render backend projection，不讀 target
repo、不重跑 inference、不依 node label/position猜 topology或 capability。

**Tech Stack:** Existing React/TypeScript viewer, backend GraphViewModel, Zod,
TanStack Query, existing graph layout stack, Playwright/browser regression, Python contract tests.

---

## Product Boundary

Graph Studio 是 release-readiness inspector，不是 workflow builder。使用者要回答：

- 這個 repo實際偵測到哪些 AI system capabilities？
- 哪些 capability是 detected、partial、undetermined、not_detected或 conflicted？
- 有哪些 readiness findings、evidence gaps 或交付前風險？
- scanner判斷依據能否回到 code/config/workflow evidence？
- Data / Control / Evidence / Governance / Source / Risk六個 lens下各有哪些 evidence與缺口？

固定 10-plane / 52-node 底圖與實際 repo overlay 必須清楚分離，但保持在同一個 canvas：

```text
reference node = 共同閱讀座標
repo overlay   = backend evidence-backed state
```

畫布預設顯示固定底圖；`Repo overlay`按鈕只切換同一 canvas上的 evidence/status overlay，
不得換頁、替換 topology或建立第二張 graph。沒有 repo evidence的 reference node不得看起來像
已存在的 component。

## Five-state Viewer Semantics

五態直接使用統一 capability contract，不另造 frontend display enum：

| Viewer state | Backend meaning |
|---|---|
| `detected` | deterministic evidence足以支持 capability |
| `partial` | 只有 indirect evidence，或已有直接 evidence但 capability wiring／覆蓋仍不完整 |
| `undetermined` | static evidence不足，無法可靠判定 |
| `not_detected` | 已完成適用檢查但未找到支持 evidence；不等於絕對不存在 |
| `conflicted` | 可回溯的正反 evidence或 provider結果互相衝突 |

`needs_review`、`confirmed`、`skipped`是 review/mapping lifecycle或 durable decision，不是
capability state。它們可作 badge/action/detail顯示，但不得覆寫上述五態。

## Readiness Findings

Graph Studio 顯示 backend-provided readiness findings，不建立 frontend-only readiness card。

顯示規則：

- Finding status 使用統一五態，不新增 `passed / partial / not_run / blocked` 類型。
- Finding 必須顯示 category、severity、status、reason、evidence refs 與 recommended next
  checks。
- Evidence Inspector 可從 finding 回查 component / edge / evidence refs。
- Frontend 不得自行從 dependency、node label 或 topology 推論 repo 是否 RAG，也不得產生
  readiness finding。

## Mapping Completeness

`Mapping Completeness` 取代沒有計算契約的 `Mapping quality` 百分比。固定 reference map的
52 nodes 全部進 denominator，由 backend 輸出：

```text
weighted_resolved = detected + not_detected + (partial * 0.5)
mapping_completeness = weighted_resolved / 52
```

要求：

- Backend同時回傳各五態 count、weighted numerator、固定 denominator `52`與 limitation。
- `undetermined`與`conflicted`權重為 0；review/confirmed lifecycle不改變計算。
- `activation_applicable = false`只表示該 node本質上沒有啟用/停用概念，對應 activation
  assessment的 `not_applicable`；不得解讀成 capability對目前 repo不適用，也不得排除
  reference node。該 node仍保留在 52-node denominator，由 capability五態決定權重。
- Completeness只表示 assessment/mapping completeness，不表示 correctness、security、readiness或
  runtime quality。
- Backend若未載入 exactly 52 nodes必須 fail closed，不能動態縮小 denominator或顯示 100%。

## Lenses

MVP lenses固定為六個；membership由 backend projection提供：

- Data
- Control
- Evidence
- Governance
- Source
- Risk

Governance / observability 是 canonical plane；Governance lens 仍可跨 plane highlight
policy、approval、risk 與 audit 關聯，但前端不得因 lens 建立第二套 canonical facts 或
改寫 catalog topology。

`Extension Subsystems Plane` 是 reference grouping；frontend 不得因此暴露 active v2
`ExtensionComponent` product concept。

## Explicit Exclusions

- **不包含 Validation Simulator。** Plan 14 direct/fixture/excluded example matrix是 QA / planning
  artifact，不成為 end-user Graph Studio主畫面。
- 不複製 DeepResearch 的 HTML、CSS、JavaScript、hard-coded graph arrays、example data或
  quality percentages。DeepResearch只作概念與 UX參考。
- 不實作 graph editing、drag-to-connect、workflow execution或 target repo mutation。
- 不把 static execution path顯示成 runtime trace；runtime overlay需 dynamic `01`另行交付。

## Implementation Tasks

### Task 1: Version the backend viewer projection

**Files:**
- Modify: `src/systograph/core/models/viewer.py`
- Modify: `src/systograph/core/services/graph_projection_service.py`
- Test: `tests/unit/core/test_graph_projection_service.py`

- [ ] 定義 exactly 52 reference nodes、repo overlays、統一五態、六個固定 lens filters、Mapping
  Completeness summary與 evidence detail contract。
- [ ] Completeness固定以 52 nodes為 denominator；`activation_applicable` / `not_applicable`
  不得排除 node。
- [ ] Projection只消費 validated artifacts、reference catalog與 durable mapping/build state。
- [ ] 所有 overlay node/edge保留 source/evidence ids與 static/runtime semantics。
- [ ] Missing optional enrichment回 degraded warnings，不阻塞 valid base graph。

### Task 2: Extend frontend parsing without inference

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/services/viewerApi.ts`
- Test: frontend contract fixtures and parser tests

- [ ] Zod只接受 `detected / partial / undetermined / not_detected / conflicted`，並拒絕
  dangling reference ids與 malformed completeness counts。
- [ ] Frontend不hard-code reference nodes、profile count/order或 lens membership；固定六個
  lens ids與 denominator 52由 versioned viewer contract驗證。
- [ ] API/sample mode都使用相同 parser；production API mode不以 sample data填補錯誤。

### Task 3: Build fixed-map plus repo-overlay canvas

**Files:**
- Modify: `frontend/src/components/SystemGraph.tsx`
- Modify: `frontend/src/components/SystemNode.tsx`
- Modify: `frontend/src/utils/graph.ts`
- Modify: `frontend/src/store/viewerStore.ts`

- [ ] Reference nodes使用克制的 neutral visual；repo state不只靠顏色區分。
- [ ] 固定底圖與 repo overlay在同一 canvas；按鈕只切換 overlay，不替換 nodes/edges/layout。
- [ ] 支援六個固定 lenses、search、focus、keyboard selection與 stable layout。
- [ ] 沿用並驗證既有 zoom、pan、fit-view與 minimap，不重做 graph engine。
- [ ] 五態有文字/icon/badge，不只紅綠色；review/confirmed只作 lifecycle badge。
- [ ] Extension subsystem overlay不改寫 base topology truth。

### Task 4: Build Mapping Completeness and evidence inspector

**Files:**
- Modify: `frontend/src/components/Sidebar.tsx`
- Modify: `frontend/src/components/DetailPanel.tsx`
- Add focused components only when existing boundaries cannot remain clear

- [ ] 顯示固定 denominator 52、weighted numerator、五態 counts與 limitation copy；
  not-applicable/activation metadata不得改變 denominator。
- [ ] 顯示 readiness findings、severity/status/reason 與 evidence refs，並可在 Inspector
  展開相關 component/edge/evidence。
- [ ] Inspector顯示 status reason、source location、evidence strength、related component/edge、
  risk/readiness finding與 recommended next checks。
- [ ] 不顯示 raw secret、完整 prompt、retrieved chunk、absolute local path或 opaque confidence。
- [ ] Static inferred execution與runtime-observed evidence使用不同 label。

### Task 5: Integrate review/apply lineage

- [ ] Review lifecycle item連到 `Review scanner suggestions`，不使用 `Manual Mapping`作主要
  user-facing名稱。
- [ ] Confirmed decision顯示 mapping id、applied build id與 base build lineage的 safe summary，
  但保留 capability原始五態。
- [ ] Apply建立新 build後 refetch viewer payload；不把 confirmation直接 mutate目前 graph。
- [ ] Rescan與Apply保持不同操作：repo改變才 rescan，確認 decision只Apply同一 snapshot。

### Task 6: Cover responsive, accessibility and degraded states

- [ ] Loading、empty、invalid base map、missing profile/readiness、partial/conflicted evidence、API error、
  Apply pending/error/success皆有明確畫面。
- [ ] Keyboard可到達 lenses、nodes、inspector與review CTA；focus不因 lens切換遺失。
- [ ] Mobile/tablet可用 horizontal canvas + accessible detail flow，不縮成不可讀小圖。
- [ ] 支援 reduced motion；graph status不依 animation表達。

### Task 7: Add safe export

- [ ] 匯出目前 build/snapshot/environment、overlay visibility、active lens與 completeness
  summary；不得把目前 viewport誤寫成 canonical topology。
- [ ] 支援至少一種可攜格式（例如 PNG/SVG 或 versioned JSON view export），並清楚標示
  static assessment、build identity與產生時間。
- [ ] Export沿用 backend redaction與 project-relative evidence location，不包含 raw secret、
  absolute local path、完整 prompt或 retrieved chunk。
- [ ] 為 overlay on/off、各 lens、degraded payload與大圖匯出加入 regression tests。

### Task 8: Verification

```bash
.venv/bin/pytest tests/unit/core/test_graph_projection_service.py -q
cd frontend && pnpm build && pnpm lint
# Run focused browser regression for all five states plus review/confirmed lifecycle badges.
git diff --check
```

## Acceptance Criteria

- 使用者可清楚區分固定 reference map與目前 repo evidence overlay。
- Capability state固定為
  `detected / partial / undetermined / not_detected / conflicted`；review/confirmed只屬
  lifecycle/decision，frontend沒有 inference或自造狀態。
- Mapping Completeness等於
  `(detected + not_detected + partial * 0.5) / 52`；activation/not-applicable不排除，且明確
  不是 quality/readiness score。
- Evidence inspector可從 visible state回到 project-relative source evidence與 safe findings。
- Readiness findings 顯示 category、severity、status、reason、recommended next checks
  與 evidence drilldown；frontend 不建立額外 readiness surface。
- Lenses固定為 Data / Control / Evidence / Governance / Source / Risk，membership由 backend
  projection驅動。
- 固定底圖與 repo overlay位於同一 canvas，按鈕只切換 overlay visibility。
- Zoom、pan、fit-view、minimap與 safe export均有驗收；export不改寫 canonical artifacts。
- Missing enrichment可 degraded load；invalid canonical map仍 fail closed。
- Validation Simulator與 DeepResearch frontend code/data均未進 production implementation。

## Dependencies

- Phase2 `01A` capability reference catalog、`02/03` profiles/readiness、`05/07` lookup、`06`
  projection、dynamic `00` static execution與 Plan 14 validation。
- Phase2 `03A` Apply/build lineage，Phase5 `41` project/build history與Apply/Rescan UX。
- Phase4 `39` multimodal capability detection與 `39A` governance/observability detection。
- Dynamic `01` runtime trace是 optional follow-up，不阻塞 static Graph Studio MVP。
