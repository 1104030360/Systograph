# Step 6 — 衍生評估（sidecar JSON）

Last updated: 2026-07-08（Step 6-1～6-6 ownership、Profile Inference 命名、GraphViewModel 邊界）

**命名：** 流程與服務叫 **Profile Inference** / `ProfileInferenceService`（6-1）；磁碟檔
`profile_signals.json`；API 欄位 `profile_inference_result`（同一份 `ProfileInferenceResult`）。

**主畫布：** Viewer 的 System Graph 用 Step 7 **`graph_view_model`**（inline），**不是** merge
本步六份 JSON。僅 **6-1 profile assessment** 經 Step 7 投影進 canvas；call graph / dataflow /
execution paths / evidence table 多為 `artifact_refs` lazy load。

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
| `reference_map_version` | 固定 reference catalog 版本；Phase2 sample 為 `1` |
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
| `summary.status` | release-readiness 摘要，使用統一 assessment 五態 |
| `release_verdict` | backend 定案的 `ready` / `needs_review` / `blocked` |
| `finding_registry_version` | finding catalog 版本，sample 為 `readiness-finding-registry/v1` |
| `summary.evidence_scope` | 這份 readiness report 使用哪些 capability / component evidence |
| `findings[]` | readiness 項目（如 `source_traceability` 引用缺失） |
| `findings[].status` | 每個 finding 使用統一 assessment 五態 |
| `findings[].evidence_ids` | 支撐 finding 的 evidence；缺證據時用 `evidence_gap` 說明 |
| `findings[].limitations` | 靜態證據無法證明的邊界，避免把推論寫成 runtime fact |
| `ui_hints` | viewer 顯示提示，不可反推 canonical truth |
| `primary_map_type` | 衍生摘要標籤，不是 canonical |

---

## frontend-evidence-table-sample.json

`evidence-table/v1` — 把 evidence **攤平成表格**，方便 debug / report join。

| 欄位 | 白話 |
|------|------|
| `rows[]` | 一列一筆 evidence |
| `emits_component_ids` | 這 evidence 支撐哪些 component |
| `emits_profile_ids` | 影響哪些 profile |
| `review_state` | `not_required` 或 `needs_review` |
| `source_artifact_refs` | 指向 map / profile 的邏輯路徑 |

---

## 靜態執行三件套：差在哪？

三者都是 **static inferred、不是 runtime trace**，但回答的問題不同：

三份 static execution JSON 與 `evidence_table.json` 共用
`runtime_verified: false`、`limitations[]` header；不得因為欄位完整就宣稱已觀察 runtime。

| | Call Graph | Dataflow Hints | Execution Paths |
|---|------------|----------------|-----------------|
| **看什麼** | 函式 / call site | 元件（component） | 一條完整「故事線」 |
| **節點** | `src.api.chat.chat` 等 symbol | `component:…` / `capability-candidate:…` | 有序 `steps[]`，每步有 `role` |
| **關係** | `function_call`（誰叫誰） | `flow_kind`（query→retriever 等語意） | 隱含在 step 順序 |
| **粒度** | 最細（程式碼） | 中等（架構） | 最粗（使用者路徑） |
| **典型 UI** | Debug、跳原始碼 | 疊在 system map 標 flow | Timeline / 步驟 walkthrough |

**Sample 同一案例（reranker）：**

- **Call graph**：`chat()` → `answer()` → `rerank()`；後段邊 `undetermined`；節點 `component_id` 常為 `null`。
- **Dataflow hints**：`component:input:api` → `component:retriever`（`query_to_retriever`）；`reranker candidate` → LLM（`docs_to_context`，`undetermined`）。
- **Execution paths**：entrypoint → retrieval → reranking（candidate）→ generation；整條 path `undetermined`，`interpretation` 一句話總結。

**什麼時候用哪個：** 工程師追 call chain → call graph；在 map 上標資料怎麼流 → dataflow hints；給 PM 看「一次請求可能走哪幾步」→ execution paths。三者互補，不是重複掃描。

**UI 共同約束：** 文案必須標 static inferred；不可當成已執行 trace；不可混用 `deferred/` 的 runtime trace event。

---

## frontend-call-graph-sample.json

`static-call-graph/v1` — **靜態推斷**的函式呼叫圖。回答：「code 裡誰呼叫誰？」

| 欄位 | 白話 |
|------|------|
| `nodes[]` | 函式 / call site |
| `edges[]` | 誰呼叫誰 |
| `component_id` | 能對上 map 就填，對不上為 `null` |
| `limitations` | UI 必須標「static inferred，未 runtime 驗證」 |

---

## frontend-dataflow-hints-sample.json

`static-dataflow-hints/v1` — 元件之間**資料流暗示**（比 call graph 更語意化）。回答：「資料可能在哪些元件之間傳？」

| 欄位 | 白話 |
|------|------|
| `hints[]` | 每條 hint 描述一種 flow（如 query→retriever） |
| `flow_kind` | 流類型：`query_to_retriever`、`docs_to_context` 等 |
| `source_ref` / `target_ref` | component 或 capability-candidate ID |

---

## frontend-execution-paths-sample.json

`static-execution-paths/v1` — 一條「可能」的查詢路徑（有序 steps）。回答：「使用者打 `/chat` 可能依序經過哪些階段？」

| 欄位 | 白話 |
|------|------|
| `paths[].steps[]` | 依序：entrypoint → retrieval → generation… |
| `role` | 這步在路徑中的角色 |
| `runtime_verified` | sample 固定 `false` |
| `interpretation` | 給人讀的靜態解讀，**不可**當成已執行的 trace |
