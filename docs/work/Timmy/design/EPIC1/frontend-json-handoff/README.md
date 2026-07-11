# Frontend JSON Handoff

Last updated: 2026-07-11（S1 implemented contract 與 later projection target 分界）

Phase2 pipeline 各步驟的 JSON mock sample。Contract 細節見 `docs/MODEL-CONTRACT.md`、`docs/API-GUIDE.md`。

**狀態：** Step 6 與 Step 9 samples 已用 current Pydantic contract 驗證；Step 4 v2
sample 是 Plan 13 cutover target；Step 7/8 richer graph / artifact-ref samples是 Plan 06
target，尚不是 current response shape。

Current Phase A 的 Step 3 仍由 KAI deterministic providers 產生 facts。Phase B 才改為
UA-primary `UnderstandAnythingAnalysisService` structural sidecar；Step 6 維持純 Python
`ProfileInferenceService` 定五態。Plan 17 `AssessmentOrchestrator` / AI semantic candidate
flow deferred，UA semantic sidecar 是 reserved nullable slot，Phase2 active path 不產生、
不消費。這是 backend 內部 pipeline 調整，**不影響任何 sample JSON schema**；本資料夾不得新增 `signal_origin`、
`confidence`、semantic candidate 或 `ua-analysis-result` frontend 欄位。

```text
Step 2 boundary + inventory enrichment
  -> Step 3 KAI deterministic facts（Phase B: UA structural sidecar）
  -> Step 4 ai_system_map.json v1 active + internal v2 normalized view
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
| **Review 工作流** | `needs_confirmation` / `pending_user_confirmation` | 這件事要人決策（map / proposal 各自的 stable enum） |
| **Capability candidate** | `confirmed_non_baseline` | 使用者確認的 non-baseline 能力 |
| **Readiness finding** | Assessment 五態 | release-readiness findings 的 evidence-backed 狀態 |
| **Evidence review** | `confirmed` / `rejected` / `needs_confirmation` / `not_required` | 單筆 evidence 的 durable review 結果 |
| **Build / 載入** | `ok`；`loaded: true/false` | API build 成功與否；viewer 有沒有載入 |
| **Runtime trace**（延後） | `completed` + `event_type` | 執行期事件，不是 static assessment |

> **Assessment 五態** 與 `activation`（`enabled` / `disabled` / …）在 contract 裡是分開的；profile 可 `detected` 但 `disabled`。正式欄位名稱是 `activation`，不是 `activation_state`。詳見 `MODEL-CONTRACT.md`。

### 出現在哪（依步驟）

| 步驟 | JSON / 路徑 | 用的狀態種類 |
|------|-------------|--------------|
| **4** map | `components[].status`、`edges[].status`；`components[].activation` | Assessment 五態；activation 獨立欄位 |
| **4** map | `unmapped_components[].status` | Review（current v1: `needs_confirmation`） |
| **6** profile | `profiles[].status`、`profiles[].activation` | Assessment 五態；activation 獨立欄位 |
| **6** profile | `capability_candidate_components[].status` | Capability candidate |
| **6** readiness | `grounding.status`、`capability_summaries[].status`、`findings[].status` | Assessment 五態 |
| **6** readiness | `findings[].category`、`findings[].evidence_ids` | Readiness finding 分類與證據 |
| **6** evidence_table | `rows[].review_state` | Evidence review |
| **6** call / dataflow / paths | static nodes / edges / paths | 無 runtime status；schema 名稱與 UI 文案明示 static inferred |
| **7** MapBuildResult | 頂層 `status` | Build（`ok`） |
| **7** graph | `nodes[].status`、`details.*.status` | 五態 + Review + candidate（畫布直接用） |
| **7** graph | `filters[].kind: "status"` | 依節點 status 篩選（如 Needs review） |
| **8** ViewerLoadResult | 內嵌 map / profile / readiness / graph | 以上全部可能再出現一次 |
| **8** ViewerLoadResult | `loaded` | Build / 載入 |
| **9** proposal | `status` | Review（`pending_user_confirmation`） |
| **9** decision request | `decision` | 使用者決策（`confirmed` 等，**不是**五態） |
| **延後** trace | `status`、`event_type` | Runtime trace |

Step 8 sample 是 Plan 06 richer aggregation target；current S1 build-scoped response 把
profile/readiness 放在 `build_result`，base graph 放在 `viewer_load_result`。

### 前端三條規則

1. **五態 UI 要一致** — component、edge、profile、readiness finding、static execution 共用同一套 legend。
2. **Review status ≠ 五態** — `needs_confirmation` / `pending_user_confirmation` 表示待 review，**不阻塞**第一次 scan 顯示；決策走 Step 9 API，下次 Apply（B2）才更新。
3. **缺證據不用 `failed`** — readiness 用 finding `status` + `evidence_gap` 說明；graph 不自行算 completeness。

## Same-build 驗證規則

- Gate-1 的 6 個 derived JSON 必須共享同一組 `scan_id`、`build_id`、`environment_id`，且 `generated_from_build_id === build_id`。
- Active canonical `ai_system_map.json` 暫時維持 v1 shape；其 scope 由同 build manifest 綁定。Plan 13 切 v2 後才自帶相同 header。
- `profile_signals` 必須包含完整 52 筆 `reference_capability_assessments` 與 15 筆 `profiles`。
- `readiness_report` 必須帶 Mapping Completeness、grounding、15 個 capability summaries 與 evidence-backed findings；Gate-1 不輸出 `release_verdict` / `severity`。
- static execution artifacts 的 current schema 沒有 `runtime_verified` / `limitations` 欄位；其 schema 與文案一律視為 static inferred。

## 驗證

```bash
find docs/work/Timmy/design/EPIC1/frontend-json-handoff -name '*.json' -print0 | xargs -0 -n1 jq empty
```
