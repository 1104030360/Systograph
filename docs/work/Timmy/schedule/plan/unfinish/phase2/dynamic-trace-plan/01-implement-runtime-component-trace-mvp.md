# Runtime Component Trace MVP 實作計畫

> **For agentic workers:** 本計畫是 **dynamic-trace-plan** 的第一份可執行計畫。
> 語意邊界以 static Plan `12` 為準；black-box 行為以 finished Plan `22` 為基線。
> Active static path（`00`～`15`，含 cutover、validation、complete retirement）完成前不要開始實作。

**Goal:** 讓 Query Trace 能回傳 **typed、bounded、masked** 的 `trace_steps` 與
`component_ref`，供 Viewer 做 **transient** graph focus——不修改 canonical map /
profile artifacts。

**Architecture:** 擴展現有 `QueryTraceService` / `/api/trace`；steps 必須來自 target
runtime **explicit envelope** 或可驗證 fixture harness，禁止從 static topology 合成。
Frontend 只 consume observed steps，不 infer path。

**Tech Stack:** Python (`query_trace_service`, `trace` models, FastAPI), React
(`ReplayTimeline`, `viewerStore`), contract tests + fixture RAG apps.

---

## 執行摘要

### 與 Plan 22 的差異

| | Finished Plan 22 | 本計畫 (Dynamic 01) |
|---|---|---|
| 觀測方式 | Black-box HTTP 呼叫 target endpoint | 同上 + 解析 typed trace envelope |
| Steps | 單一完成事件 / response summary | `trace_steps[]` + per-step `component_ref` |
| Graph | 無 component-level highlight | Transient focus on existing projection nodes |
| Map 寫入 | 不寫入 | 仍不寫入 |

### 與 Static Plan 12 的對齊

- Opt-in、transient、bounded、masked
- Unknown `component_ref` → warning，不建 graph node/edge
- 不得宣稱 static profile = runtime proof
- v2 normalized ids；active Plan `15` 必須在 00A/13/14 通過後退役 v1 compatibility

---

## Phase 0 — Contract lock（文件 + sample）

**Deliverables**

1. 更新 `frontend/API_CONTRACT.md` 與 `docs/API-GUIDE.md` 的 trace section：
   - `TraceComponentRef`（`ref_type`, `ref_id`, optional `label`）
   - `RuntimeTraceStep`（`step_id`, `component_ref`, `status`, `warnings[]`, optional timing）
   - `QueryTraceEvent.trace_steps[]`, `QueryTraceEvent.component_ref`
2. 新增 handoff sample：
   `docs/work/Timmy/design/EPIC1/frontend-json-handoff/deferred/frontend-runtime-trace-event-sample.json`
3. Future `ref_type` enum 與 Plan 12 唯一 frozen boundary 對齊：
   `endpoint`, `component`, `edge`, `grounding_dimension`,
   `capability_candidate`, `capability_profile`

**Gate:** Timmy / product 確認 envelope 後，才開 frontend 工（見 Meeting Sync
`frontend-runtime-trace.md`）。

---

## Phase 1 — Backend MVP

**Primary files**

- `src/systograph/core/models/trace.py`
- `src/systograph/core/services/query_trace_service.py`
- `src/systograph/core/providers/endpoint_call_provider.py`
- `src/systograph/web/routes/trace_routes.py`

**Tasks**

1. Pydantic models + schema validation for `trace_steps` / `component_ref`
2. Parse trace envelope from target response（JSON body field 或 agreed header——需 ADR 二選一）
3. Resolve refs against loaded `SystemMapIndex`（unknown → structured warning）
4. Bounds：max steps、max payload、timeout（對齊 final-phase `167` policy 方向）
5. Masking：沿用 `SecretMaskingService`；禁止 raw secrets in steps
6. SSE/streaming：若保留 stream，每 event 帶完整或 incremental steps（需 contract test）

**Tests**

- `tests/unit/core/test_query_trace_service.py` — envelope parse, unknown ref, bounds
- `tests/web/test_trace_routes.py` — response shape, error codes
- `tests/contracts/` — sample JSON vs schema

**Fixture harness**

- 在 `tests/fixtures/rag_projects/` 新增最小 **trace-envelope** scenario（e.g.
  `basic_qdrant_ollama_rag_with_trace.json` stub），供 CI 不依賴 live LLM

---

## Phase 2 — Frontend transient focus

**Primary files**

- `frontend/src/types.ts`
- `frontend/src/services/viewerApi.ts`
- `frontend/src/components/ReplayTimeline.tsx`
- `frontend/src/store/viewerStore.ts`

**Tasks**

1. Zod/TS types mirroring backend contract
2. ReplayTimeline：逐步顯示 `trace_steps`；點選 step → graph transient highlight
3. Viewer：只 highlight **已存在** projection node；unknown ref 顯示 warning badge
4. 不寫入 profile sidecar；不新增 permanent graph edges

**Gate:** Backend sample payload 就緒 + Phase 0 contract merged。

---

## Phase 3 — Security & egress re-review

- 重新跑 `docs/security/query-trace-egress-policy.md` checklist
- 確認 typed envelope 不引入 SSRF / log leakage 新 surface
- 對齊 `final-phase-hardening/163`、`167` 若已 merge

---

## 驗收標準

- [ ] `/api/trace` 回傳 documented `trace_steps` + `component_ref` shape
- [ ] Unknown refs 不 crash；回 warning 且不 mutate map
- [ ] Viewer 可 replay steps 並 transient focus；reload 後 trace overlay 清除
- [ ] Static readiness path 不依賴本功能（Plan 12 gate 仍成立）
- [ ] Contract tests + unit tests 通過；無 secret 出現在 logs/responses

## 不在範圍內

- OpenTelemetry / distributed tracing
- Trace persistence、history、跨 session 聚合
- 自動更新 mapping / profile / readiness verdict
- 要求任意 target app 必須實作 envelope（opt-in 不變）
- Production multi-tenant trace storage

## 相依與順序

```text
static 00 → 00A → 01 → 01A → 02–11 → dynamic 00 → 13 → static 14 → 15
        → dynamic 01 Phase 0 (contract)
        → dynamic 01 Phase 1 (backend)
        → product sign-off
        → dynamic 01 Phase 2 (frontend)
```

## 相關連結

- [`../static-trace-plan/12-add-runtime-component-trace-contract.md`](../static-trace-plan/12-add-runtime-component-trace-contract.md)
- [finished Plan 22](../../../finish/22-implement-query-trace-mvp.md)
- [frontend-runtime-trace.md](../../../../../../Meeting-Sync/meeting_sync_2026_07_07/frontend-runtime-trace.md)
