# Frontend JSON Handoff

Last updated: 2026-07-07（UA 整合決策對齊）

Phase2 pipeline 各步驟的 JSON mock sample。Contract 細節見 `docs/MODEL-CONTRACT.md`、`docs/API-GUIDE.md`。

**注意：** target contract，不代表 backend 已全部實作。

2026-07-07 UA 整合決策：Step 3 改為 UA-primary
`UnderstandAnythingAnalysisService` sidecar scan；Step 6 在 Phase2 維持純 Python
`ProfileInferenceService` 定五態。Plan 17 `AssessmentOrchestrator` / AI semantic candidate
flow deferred，UA semantic sidecar 是 reserved nullable slot，Phase2 active path 不產生、
不消費。這是 backend 內部 pipeline 調整，**不影響任何 sample JSON schema**；本資料夾不得新增 `signal_origin`、
`confidence`、semantic candidate 或 `ua-analysis-result` frontend 欄位。

```text
Step 2 boundary + inventory enrichment
  -> Step 3 UA structural sidecar（deterministic facts；semantic sidecar slot deferred）
  -> Step 4 ai_system_map.json
  -> Step 6 ProfileInferenceService（純 Python；Plan 17 AI flow deferred）
  -> Step 7 GraphViewModel / MapBuildResult
  -> Step 8 ViewerLoadResult
  -> Step 9 MappingProposal / ManualMapping（API 不變）
```

## 目錄

| 步驟 | 資料夾 | Sample |
|------|--------|--------|
| 4 正規化 | `step-04-normalize-validate/` | `frontend-ai-system-map-sample.json` → `ai-system-map/v2` |
| 6 衍生評估 | `step-06-derived-assessment/` | `profile_signals` / `readiness_report` / `evidence_table` / `call_graph` / `dataflow_hints` / `execution_paths` |
| 7 投影發布 | `step-07-projection-publication/` | `frontend-map-build-result-sample.json` / `frontend-graph-view-model-sample.json` |
| 8 Viewer | `step-08-viewer/` | `frontend-json-sample.json` → `ViewerLoadResult` |
| 9 Review | `step-09-review-apply/` | `frontend-mapping-proposal-sample.json` / `frontend-manual-mapping-create-capability-candidate-sample.json` |
| 延後 | `deferred/` | `frontend-runtime-trace-event-sample.json` |

步驟 1–3、5 無 handoff sample（見各 step README）。有 JSON 的 step 資料夾內有 **欄位說明 README**，與 sample 對照閱讀。

Step 6 的 call graph / dataflow hints / execution paths 三者差異 → 見 [`step-06-derived-assessment/README.md`](step-06-derived-assessment/README.md#靜態執行三件套差在哪)。

## 狀態欄位一覽

handoff JSON 裡有多種「狀態」，**語意不同、不可混用**。前端只 **render backend 給的值**，不要從 graph topology 自己推。

### 七種狀態（先看這張）

| 名稱 | 常見值 | 白話 |
|------|--------|------|
| **Assessment 五態** | `detected` / `partial` / `undetermined` / `not_detected` / `conflicted` | 靜態證據夠不夠、有沒有衝突 |
| **Review 工作流** | `needs_review` | 這件事要人決策（接 Step 9） |
| **Capability candidate** | `confirmed_non_baseline` | 使用者確認的 non-baseline 能力 |
| **Readiness finding** | Assessment 五態 | release-readiness findings 的 evidence-backed 狀態 |
| **Evidence review** | `not_required` / `needs_review` | 單筆 evidence 要不要進 review |
| **Build / 載入** | `ok`；`loaded: true/false` | API build 成功與否；viewer 有沒有載入 |
| **Runtime trace**（延後） | `completed` + `event_type` | 執行期事件，不是 static assessment |

> **Assessment 五態** 與 `activation`（`enabled` / `disabled` / …）在 contract 裡是分開的；profile 可 `detected` 但 `disabled`。正式欄位名稱是 `activation`，不是 `activation_state`。詳見 `MODEL-CONTRACT.md`。

### 出現在哪（依步驟）

| 步驟 | JSON / 路徑 | 用的狀態種類 |
|------|-------------|--------------|
| **4** map | `components[].status`、`edges[].status`；`components[].activation` | Assessment 五態；activation 獨立欄位 |
| **4** map | `unmapped_components[].status` | Review（`needs_review`） |
| **6** profile | `profiles[].status`、`profiles[].activation` | Assessment 五態；activation 獨立欄位 |
| **6** profile | `capability_candidate_components[].status` | Capability candidate |
| **6** readiness | `summary.status`、`findings[].status` | Assessment 五態 |
| **6** readiness | `findings[].category`、`findings[].evidence_ids` | Readiness finding 分類與證據 |
| **6** evidence_table | `rows[].review_state` | Evidence review |
| **6** call / dataflow / paths | `edges[].status`、`hints[].status`、`paths[].status` | Assessment 五態 |
| **7** MapBuildResult | 頂層 `status` | Build（`ok`） |
| **7** graph | `nodes[].status`、`details.*.status` | 五態 + Review + candidate（畫布直接用） |
| **7** graph | `filters[].kind: "status"` | 依節點 status 篩選（如 Needs review） |
| **8** ViewerLoadResult | 內嵌 map / profile / readiness / graph | 以上全部可能再出現一次 |
| **8** ViewerLoadResult | `loaded` | Build / 載入 |
| **9** proposal | `status` | Review（`needs_review`） |
| **9** decision request | `decision` | 使用者決策（`confirmed` 等，**不是**五態） |
| **延後** trace | `status`、`event_type` | Runtime trace |

Step 8 是 Step 4/6/7 的 **聚合包**；狀態語意與 sidecar 相同。

### 前端三條規則

1. **五態 UI 要一致** — component、edge、profile、readiness finding、static execution 共用同一套 legend。
2. **`needs_review` ≠ 五態** — 表示待 review，**不阻塞**第一次 scan 顯示；決策走 Step 9 API，下次 Apply（B2）才更新。
3. **缺證據不用 `failed`** — readiness 用 finding `status` + `evidence_gap` 說明；graph 不自行算 completeness。

## 驗證

```bash
find docs/work/Timmy/design/EPIC1/frontend-json-handoff -name '*.json' -print0 | xargs -0 -n1 jq empty
```
