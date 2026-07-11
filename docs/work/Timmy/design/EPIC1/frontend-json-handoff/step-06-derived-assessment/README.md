# Step 6 — 衍生評估（sidecar JSON）

Last updated: 2026-07-11（current S1 Pydantic payloads）

**命名：** 流程與服務叫 **Profile Inference** / `ProfileInferenceService`（6-1）；磁碟檔
`profile_signals.json`；API 欄位 `profile_inference_result`（同一份 `ProfileInferenceResult`）。

**主畫布：** Current Gate-1 viewer 仍是 canonical v1 base projection，**不是** merge
本步六份 JSON。Plan 06 才把 **6-1 profile assessment** 經 Step 7 投影進 canvas，並為
其他 artifacts 增加 safe lazy refs。

**Step 6 子步速查：** 見 `static-trace-plan/README.md` § Step 6 子步驟與 Ownership 速查；
契約細節見 `docs/MODEL-CONTRACT.md` § Phase2 Pipeline · Step 6 Assessment。

從 canonical map **推導**出來的資料，Step 7 寫入磁碟。**不是** canonical truth，不要 write back 到 `ai_system_map.json`。

2026-07-07 UA 整合決策：Step 6 在 Phase2 維持純 Python
`ProfileInferenceService` 唯一定案五態。Plan 17 `AssessmentOrchestrator` / AI semantic
candidate flow deferred；UA semantic sidecar 是 reserved nullable slot，Phase2 active path
不產生、不消費。
**本 README 下所有 sample JSON schema 不新增** `ua-analysis-result`、`signal_origin`、
`confidence` 或 semantic candidate 欄位。

```text
canonical map + evidence
  -> ProfileInferenceService（純 Python）
       profile_signals / readiness / static artifacts

reserved nullable UA semantic sidecar
  -> Phase2 active path 不產生、不消費（Plan 17 deferred）
```

---

## frontend-profile-signals-sample.json

`profile-signals/v1` — 能力 overlay（可堆疊 profile，不是 RAG 變體分類）。

| 欄位 | 白話 |
|------|------|
| `profiles[]` | 每個 capability 的推斷結果（如 rag-grounding、reranking） |
| `reference_catalog_version` | 固定 reference catalog 版本；Phase2 sample 為 `1` |
| `reference_capability_assessments[]` | 完整 52 格五態；sample 不得只放 detected rows |
| `mapping_completeness` | 依全部 52 格與固定 weights 由 backend 計算 |
| `profile_id` / `label` | 能力 ID 與顯示名 |
| `status` | 五態：這能力證據夠不夠 |
| `activation` | 與五態分開的啟用狀態；正式欄位不是 `activation_state` |
| `coverage_detected` / `coverage_total` | 該 profile 訊號命中幾個 / 總共幾個 |
| `evidence_ids` | 支撐此 profile 的 evidence |
| `related_unmapped_component_ids` | 相關但未對位的元件（可點過去 review） |
| `capability_candidate_components[]` | 使用者確認過的 non-baseline 候選（來自 Step 9） |

---

## frontend-readiness-report-sample.json

`readiness-report/v1` — release readiness 摘要與 findings。

| 欄位 | 白話 |
|------|------|
| `mapping_completeness` | 與 profile sidecar 同一份 52 格摘要 |
| `grounding` | applicability、status、dimensions、evidence 與 reason |
| `capability_summaries[]` | 15 個 profile 的 status / activation / evidence 摘要 |
| `findings[]` | readiness 項目（如 `source_traceability` 引用缺失） |
| `findings[].status` | 每個 finding 使用統一 assessment 五態 |
| `findings[].evidence_ids` / `reason` | finding 必須有 evidence 或明確 reason |
| `limitations[]` | 靜態證據無法證明的 report-level 邊界 |
| `primary_map_type` | 衍生摘要標籤，不是 canonical |

Current Gate-1 不輸出 `release_verdict`、`severity`、`finding_registry_version` 或
`ui_hints`。

---

## frontend-evidence-table-sample.json

`evidence-table/v1` — 把 evidence **攤平成表格**，方便 debug / report join。

| 欄位 | 白話 |
|------|------|
| `rows[]` | 一列一筆 evidence |
| `artifact_type` / `evidence_kind` | evidence 類型與 direct / indirect / explicit negative |
| `relative_path` / `rule_id` / `summary` | safe location、rule 與摘要 |
| `review_state` | `confirmed` / `rejected` / `needs_confirmation` / `not_required` |

---

## 靜態執行三件套：差在哪？

三者都是 **static inferred、不是 runtime trace**，但回答的問題不同：

三份 static execution JSON 與 `evidence_table.json` 共用 `scan_id`、`build_id`、
`environment_id`、`generated_from_build_id` scope。Current schema 沒有
`runtime_verified` / `limitations` 欄位；不得因欄位缺席就宣稱已觀察 runtime。

| | Call Graph | Dataflow Hints | Execution Paths |
|---|------------|----------------|-----------------|
| **看什麼** | canonical component call graph | 元件間 shallow dataflow hints | ordered static component path |
| **節點** | `node_id` + `kind` | edge-like `source` / `target` | component id 陣列 |
| **關係** | `relationship` | `relationship` | 隱含在 id 順序 |
| **粒度** | 元件圖 | 元件資料流 | 最粗（路徑） |
| **典型 UI** | Debug、跳原始碼 | 疊在 system map 標 flow | Timeline / 步驟 walkthrough |

**Sample 同一案例（tool-using agent）：**

- **Call graph**：component nodes + observed canonical edges。
- **Dataflow hints**：同一批 edge 以 shallow hint shape 呈現。
- **Execution paths**：每條 edge 形成 `[source, target]` 的 deterministic static path。

**什麼時候用哪個：** 工程師追 call chain → call graph；在 map 上標資料怎麼流 → dataflow hints；給 PM 看「一次請求可能走哪幾步」→ execution paths。三者互補，不是重複掃描。

**UI 共同約束：** 文案必須標 static inferred；不可當成已執行 trace；不可混用 `deferred/` 的 runtime trace event。

---

## frontend-call-graph-sample.json

`call-graph/v1` — **靜態推斷**的 canonical component 呼叫圖。

| 欄位 | 白話 |
|------|------|
| `nodes[]` | `node_id` + canonical `kind` |
| `edges[]` | `edge_id`, `source`, `target`, `relationship`, `evidence_ids` |

---

## frontend-dataflow-hints-sample.json

`dataflow-hints/v1` — 元件之間的 shallow static dataflow hints。

| 欄位 | 白話 |
|------|------|
| `hints[]` | 每條 hint 描述一種 flow（如 query→retriever） |
| `relationship` | canonical edge relationship |
| `source` / `target` | component ids |

---

## frontend-execution-paths-sample.json

`execution-paths/v1` — 靜態 component id 路徑。

| 欄位 | 白話 |
|------|------|
| `paths[][]` | ordered component ids；current Gate-1 每個 observed edge 形成一條兩點 path |
