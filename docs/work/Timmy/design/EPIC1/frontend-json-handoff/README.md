# Frontend JSON Handoff

Last updated: 2026-07-15（live code / contract / frontend consumer 全量對齊）

本資料夾整理 Phase2 Step 1～9 的 frontend JSON handoff。它同時包含 **current runtime**、
**current backend model fixture** 與 **planned target**；每份 README 都會標明是哪一種，不能只看
檔名就假設 API 已經上線。

## 讀取優先序

發生不一致時，依序相信：

1. `src/` 的 runtime code、Pydantic schema 與實際 API response。
2. `frontend/src/` 的 Zod schema與 UI consumer（代表「目前前端真的能吃什麼」）。
3. `docs/MODEL-CONTRACT.md`、`docs/API-GUIDE.md` 與 `docs/spec/`。
4. 未完成 plan 與本資料夾的 planned samples。

文件不能把 target 寫成 current。Backend 已產生某欄位，也不等於 frontend 已完整顯示。

## 2026-07-15 現況結論

- Phase A 的 Step 3 仍由 KAI deterministic providers 產生 facts；UA-primary 是 Phase B，
  Plan 20 inventory selection 不介接 UA。
- Normal build 的 public `ai_system_map.json` 與 `active_schema_version` 仍是
  `ai-system-map/v1`；backend 會建立 normalized `AiSystemMapV2` 供下游使用。Plan 13 因 00A
  Task 4／5 尚未通過而維持 blocked。
- `SystemMapIndex`、`GraphProjectionService`、52 個 reference capability nodes、profile
  overlays 與六個 lenses 已在 backend 實作，不再是未來設計。
- 每個 build 寫出 10 個 public siblings（7 JSON + 3 render）；`GraphViewModel` 是 +1
  ephemeral API projection，不是第 11 個磁碟檔。
- Current build-scoped API 使用 `MapBuildScopedResponse`：lineage 在外層，profile／readiness
  在 `build_result`，map／graph 在 `viewer_load_result`。尚未提供 `ArtifactRef[]`。
- Frontend 仍從 process-wide `/api/map` 載入，Zod／UI 只保留舊 graph 子集合，且 mapping
  form 仍接受 `new_extension_component`。因此 richer backend graph 與 Plan 13 legacy
  retirement 尚未完成 end-to-end cutover。
- Step 6 的五態由純 Python `ProfileInferenceService` 決定；Plan 17 AI semantic candidate
  flow 與 UA semantic sidecar 都是 deferred，不得加入 frontend sample。

```text
Step 1 Import
  -> Step 2 current boundary gate
       (Plan 20 target: inventory preflight + one-run selection; no UA)
  -> Step 3 KAI deterministic scan（Phase A current）
  -> Step 4 public v1 + normalized v2
  -> Step 5 SystemMapIndex
  -> Step 6 profile / readiness / static sidecars
  -> Step 7 GraphViewModel + 10-sibling publication
  -> Step 8 ViewerPayload / MapBuildScopedResponse
  -> Step 9 Proposal -> ManualMapping -> Apply child build
```

## Step / sample 狀態矩陣

| Step | Current backend | Sample 狀態 | Current frontend |
| --- | --- | --- | --- |
| 1 Import | `POST /api/projects/import` + project registry | 無 JSON；README 記錄 current API | 已有 import flow |
| 2 Boundary | `POST /api/scans` + sensitive proposal；尚無 preflight endpoint | 8 份 JSON 是 Plan 20 target | Modal 仍是 current sensitive-file flow |
| 3 Scan | KAI deterministic providers + `scan-snapshot/v1` | 無 public JSON | 不直接讀 snapshot |
| 4 Normalize | public v1；internal normalized `AiSystemMapV2` | v2 sample 通過 current Pydantic，但不是 current public artifact | Viewer 仍以 v1 相容資料為主 |
| 5 Index | read-only `SystemMapIndex` 已實作 | 無 public JSON | 不直接消費 index |
| 6 Assessment | 6 份 sidecars 已實作、同 build 發布 | 6 份 sample 通過 current Pydantic | 尚未完整顯示 profile／readiness rich details |
| 7 Projection | richer `GraphViewModel` 已實作 | graph sample 通過 current Pydantic；MapBuildResult + ArtifactRef sample 是 future target | Zod／UI 只吃舊子集合 |
| 8 Viewer | `ViewerPayload` 與 `MapBuildScopedResponse` 均存在 | `frontend-json-sample.json` 是 current `ViewerPayload` contract fragment | 仍呼叫 process-wide `/api/map` |
| 9 Review / Apply | non-baseline candidate + legacy extension contract 並存 | proposal／manual mapping samples 通過 current Pydantic | 仍只有 existing／legacy extension enum |
| Deferred | current `/api/trace` 已有 `TraceRunResult` / `QueryTraceEvent` | sample 是 richer safe-linkage target，不是 current Pydantic | 不可拿 static path 偽裝 runtime event |

## Sample 索引與驗證等級

| 資料夾 | Sample | 驗證等級 |
| --- | --- | --- |
| `step-02-boundary-gate/` | preflight、selection、pending／completed、typed errors | current backend Pydantic；frontend flow 尚待實作 |
| `step-04-normalize-validate/` | `frontend-ai-system-map-sample.json` | current `AiSystemMapV2` Pydantic |
| `step-06-derived-assessment/` | profile、readiness、evidence、call、dataflow、paths | current Pydantic |
| `step-07-projection-publication/` | graph + future artifact index | graph=current Pydantic；artifact index=target |
| `step-08-viewer/` | `frontend-json-sample.json` | current `ViewerPayload` Pydantic；graph 刻意截短 |
| `step-09-review-apply/` | proposal + decision request | current Pydantic |
| `deferred/` | richer runtime trace linkage | future design fixture；current trace shape 以 API model 為準 |

步驟 1、3、5 沒有 frontend JSON；這是 ownership 邊界，不是缺檔。Step 6 三份 static
execution JSON 的差異見
[`step-06-derived-assessment/README.md`](step-06-derived-assessment/README.md#靜態執行三件套差在哪)。

## 狀態欄位不可混用

| 類別 | 值 | 使用位置 |
| --- | --- | --- |
| Assessment 五態 | `detected` / `partial` / `undetermined` / `not_detected` / `conflicted` | profile、reference assessment、readiness |
| Activation | `enabled` / `disabled` / `conditional` / `unknown` / `conflicted` / `not_applicable` | 與 assessment 分開 |
| Current scan lifecycle | `requires_boundary_decision` / `completed` / `error` | `POST /api/scans` |
| Plan 20 inventory target | `reviewable` / `hard_blocked` / `missing` / `empty_directory` / `directory_limit_exceeded` | current backend preflight；frontend 尚未接線 |
| Review workflow | `needs_confirmation` / `pending_user_confirmation` | unmapped／proposal |
| Durable evidence review | `confirmed` / `rejected` / `needs_confirmation` / `not_required` | evidence table／mapping decision |
| Capability candidate | `confirmed_non_baseline` | confirmed non-baseline capability |
| Load / build | `loaded: true/false`、`status: ok/error` | Viewer／build |

Frontend 只 render backend 狀態，不從 topology、檔名、reason 或 counts 重算。缺證據也不使用
`failed`；必須保留五態與 evidence gap。

## Same-build 與安全規則

- 6 個 derived JSON 必須共享 `scan_id`、`build_id`、`environment_id`，且
  `generated_from_build_id === build_id`。
- `profile_signals.json` 必須有 52 筆 reference assessments 與 15 筆 profiles；
  `readiness_report.json` 必須引用同一份 Mapping Completeness。
- static call graph／dataflow／execution paths 只能標示 static inferred，不得宣稱 runtime
  verified。
- API／sample 不得暴露 absolute local path、secret、raw exception 或 server-local artifact
  path。未來 lazy load 只能走受控 `artifact_id` API。
- Apply 重播同一 snapshot、建立新 `build_id`；Rescan 才重新讀 repo 並建立新 `scan_id`。

### Fixture lineage boundary

本資料夾不是一包可以任意 merge 的單一 response：Step 6 六份 current samples 是 initial
`build:sample-b1` 的同 build group；Step 4／7 用 `build:sample-b2` 示範另一個 contract
fragment；Step 8 則是獨立的 current v1 Viewer load fixture。只有 README 明示同 build 的檔案才可
做 cross-file equality 檢查，不能拿 B1 的 Mapping Completeness 覆蓋 B2 graph。

## Current frontend integration gaps

這些是 handoff 必須保留的真實差距，不是 sample 要自行相容的理由：

1. `frontend/src/types.ts` 尚未保留 rich node identity、assessment scope、relationships、
   profile／reference details 與 lenses；Zod parse 會丟掉未知欄位。
2. `frontend/src/services/viewerApi.ts` 尚未改用 project／build-scoped latest endpoint。
3. `scanCreateResponseSchema` 仍要求 pending response 一定有 `scan_id`；Plan 20 target 明確禁止。
4. Mapping Zod／EditForm 仍只有 `existing_slot_mapping` 與 `new_extension_component`，尚未接
   backend 的 `non_baseline_capability_candidate`。

## 基本驗證

```bash
find docs/work/Timmy/design/EPIC1/frontend-json-handoff \
  -name '*.json' -print0 | xargs -0 -n1 jq empty

git diff --check -- \
  docs/work/Timmy/design/EPIC1/frontend-json-handoff
```
