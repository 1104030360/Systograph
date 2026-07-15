# Frontend JSON Handoff Live-State Sync Report

## 結果

已將 `docs/work/Timmy/design/EPIC1/frontend-json-handoff/` 的 11 份 README 與 21 份 JSON
按 2026-07-15 live state 重新分類，明確區分 current runtime、current backend model fixture
與 planned target。

本次沒有改變專案結構或長期開發規則，因此未修改 `AGENTS.md`。

## Source of truth

本次以實際 code 與 runtime 為主，交叉檢查：

- Backend Pydantic models、map build／manifest／publisher／projection／mapping services 與 web
  schemas。
- Frontend `types.ts`、`viewerApi.ts`、`projectScanApi.ts`、
  `BoundaryDecisionModal.tsx`、mapping `EditForm` 與 mocks。
- Plan 13 live blockers、Plan 19／20 target、Plan 05～09 implementation／manual QA reports。
- `docs/MODEL-CONTRACT.md`、`docs/API-GUIDE.md`、`docs/spec/` 與 Phase2 static plan index。

## 主要更新

### Current / target 邊界

- Current Phase A 仍是 KAI deterministic scan；UA-primary 是 future Phase B。
- Current public map 仍是 v1，normalized v2 供 backend consumers；Plan 13 仍 blocked。
- `SystemMapIndex` 與 richer `GraphProjectionService` 已實作，不再列為 future。
- Current build-scoped envelope 是 `MapBuildScopedResponse`；`ArtifactRef[]` 仍是 target。
- Current `/api/trace` 與 deferred richer safe-linkage sample 已分開描述。

### JSON contracts

- 修正 Step 4 v2 sample 的 layer literals、edge status、nested evidence location、endpoint
  shape、source version、migration warnings 與 candidate facts，使其通過 `AiSystemMapV2`。
- 修正 Step 7 graph sample 的 semantic kinds、52-count `status_counts` 與 exact completeness
  value，使其通過 `GraphViewModel`。
- Step 8 改為 current `ViewerPayload` fragment：保留 raw v1 map，graph 截短為 6 nodes／2
  edges，並將重複 serialized map／compatibility path 設為 `null`。
- Step 2 的 8 份 Plan 20 target samples 保留為 planned contract，未冒充 current API。

### Frontend integration truth

實際 runtime probe 確認：

- Current Zod 可以 parse Step 8 sample，但會丟掉 `semantic_kind`、lenses 等 rich fields。
- Current `scanCreateResponseSchema` 無法 parse 沒有 `scan_id` 的 Plan 20 pending response。
- Current mapping schemas 無法 parse non-baseline proposal／manual mapping samples。

這些差距已寫入 handoff，沒有以 sample fallback 隱藏。

## 驗證結果

| Gate | 結果 |
| --- | --- |
| 全部 JSON syntax | 21 files，`jq empty` 通過 |
| Current Pydantic samples | 11 model validations 通過 |
| Plan 20 target invariants | pending 無 `scan_id`、completed 有 `scan_id`、3 個 typed error codes 通過 |
| Backend focused matrix | 84 passed in 4.54s |
| Frontend tests | 3 files／7 tests passed |
| Frontend production build | 通過；保留既有 `web-worker` external 與 large chunk warnings |
| Frontend Zod runtime probe | Step 8 parse 通過；3 個已記錄 integration gaps 可重現 |
| Markdown local links | 15 targets 通過 |
| Secret／absolute-path scan | 無命中 `/Users/`、private-key、AWS/OpenAI-style token patterns |
| Whitespace / patch format | `git diff --check` 通過 |
| Shell syntax | `bash -n scripts/trace_graph_projection_qa.sh` 通過 |

## Manual QA 與 trace script 修正

第一次執行 `scripts/trace_graph_projection_qa.sh` 時，runtime 已產生 10 個 siblings、52 個
reference assessments、15 個 profiles 與 6 個 lenses，但最後一行把未加大括號的
`$SESSION_RELS` 緊接全形分號。Bash 將它解讀成不同變數名稱；雖然第一次外層執行狀態顯示
exit 0，log tail 已明確出現 unbound-variable error，因此該次結果未被接受。

後續隔離驗證確認同一未加大括號案例會回 127，`kai_cleanup` EXIT trap 也會保留原本的
non-zero status；因此不把第一次外層狀態異常歸因於 cleanup trap。已證實且需要修正的 root
cause 是變數邊界不明確。

以實際失敗作為 RED evidence 後，僅將四個 shell 變數改成 `${...}` 明確邊界。Fresh state
重跑結果：

- 10 個 sibling artifacts。
- `loaded=true`、`graph-view-model/v1`。
- 71 nodes：52 reference、13 repo、6 unmapped。
- 52 reference assessments、15 profile findings、6 lenses。
- `profile_signals_available=true`、`readiness_report_available=true`。
- Session 與 build-scoped node count 都是 71、relationship count 都是 0，最終比對通過。
- Server、state、outputs 與 temp logs 已清理。

## 尚未完成的產品工作

- Plan 13 的 v2 normal cutover 與 legacy extension retirement 仍受 00A Task 4／5 阻擋。
- Plan 19／20 inventory selection 仍是 planned contract，尚無 runtime endpoint／schema／UI。
- Frontend 尚未切 project-scoped latest build，也尚未完整保留 richer graph contract。
- Safe `ArtifactRef` lazy-load API 尚未凍結或實作。

以上是既有 owner 的 follow-up，不是本次文件同步已完成的功能。

## 最終 review

### Runtime 假設

1. **假設：Plan 13 v2 normal cutover 已經生效。** 反證：fresh TestClient map build 得到
   `active_schema_version=ai-system-map/v1`、`requested_schema_version=ai-system-map/v1`，raw public
   map 也是 v1。文件保留 Plan 13 blocked 邊界。
2. **假設：Richer graph 仍只是 future design。** 反證：同一 fresh build 得到 71 nodes、52
   reference nodes／assessments、15 profile findings 與 6 lenses；trace script 的 session／
   build-scoped counts 也一致。文件改列為 current backend。
3. **假設：Current frontend 已完整消費 backend rich contract。** 反證：Node runtime probe
   顯示 Step 8 雖能 parse，`semantic_kind`／lenses 會被 Zod 丟棄；pending 無 `scan_id` 與兩份
   non-baseline mapping samples 都 parse 失敗。文件保留明確 integration gaps。

### 五個 review lanes

- Requirement coverage：11 份 README、21 份 JSON 全部有 current／target 分類；每份 JSON 都被
  同資料夾 README 索引。
- Contract accuracy：所有 current samples 通過實際 Pydantic；Plan 20、ArtifactRef 與 richer
  trace targets 沒有冒充 runtime。
- Frontend usability：已用 current Zod 實際 parse，能用與尚未支援的欄位都明確記錄。
- Security／privacy：無 absolute local path 或 raw secret；Step 2 維持 no-read-before-decision，
  Step 8 secret-like evidence value仍為 masked fixture。
- Git／history：保留原有 dirty worktree 與使用者 Plan 13／19／20／Meeting-Sync 變更，只修改本
  task 的 handoff、TODO／Report 與直接阻擋 trace QA 的一行 shell 變數邊界。

最終沒有 handoff blocker；未完成事項都是已標明 owner 的後續產品／frontend 工作，不被誤寫成
本次已交付功能。
