# Systograph / Systograph (Phase 2) 完整運作流程圖 (Operational Flow)

本檔是 **時序 / 生命週期視角**：一次掃描從觸發、產出到前端渲染，中間每一段由誰負責、
在哪裡驗證、落地了什麼。分層元件清單與依賴方向請看同目錄的 `systograph_architecture.md`，
本檔不重複列舉元件，只描述 runtime sequence。

流程貫徹 **Two-Phase Analysis**：先由 deterministic providers（filesystem / config parser /
docker compose / dependency manifest / code pattern）產生結構化 facts，再交給純 Python 的
`ProfileInferenceService` 做語意對位與五態判定。Phase 2 **不建立 `AssessmentOrchestrator`**，
也不讓 LLM 裁決 profile / readiness；LLM 只出現在 mapping proposal（預設 provider 為
`deterministic`，NVIDIA NIM 需 `SYSTOGRAPH_ENABLE_NVIDIA_NIM_PROPOSALS` 才啟用），
AI semantic candidate flow 屬 **Plan 17 deferred**。UA rollout 目前在 Phase A：
TOML rule providers 是 Step 3 主路徑，UA sidecar 可缺席。

---

## 0. 進入點一覽

| 進入點 | 指令 / 端點 | 是否重新掃描 | 原子性 |
|---|---|---|---|
| CLI（最簡變體） | `uv run systograph map <project_path>`（同一 entry point 也註冊為 `systograph`） | 是 | 無 commit gate，直接寫 `--output`，**設計上非原子** |
| Web 專案流程（viewer 實際使用） | `POST /api/projects/import` →（`POST /api/projects/{id}/scan-preflights`）→ `POST /api/scans` | 是 | `BuildCommitService`：staging → validate → publish → manifest → CAS latest |
| Apply | `POST /api/map-builds/{base_build_id}/apply` | 否（replay 同一 snapshot） | `BuildCommitService` |
| Detail scan | `POST /api/detail-scans` | 否（enriched map 子 build） | 子 build，不動 latest 指標語意以外的東西 |

> 舊版本檔案寫的 `systograph scan [target_repo]` **不存在**；沒有 `scan` 這個 CLI 子命令。
> CLI 只有 `map` / `migrate-legacy-mappings` / `trace` / `validate-map` 四個命令。

---

## 1. 主時序：Web 掃描 → build → commit

```text
┌─ [1] Import project (frontend: DataSourceControl "Start scan") ────────────────────────┐
│ POST /api/projects/import                                                              │
│   body { source_type: "local_path", project_path }                                     │
│   -> ProjectState persisted under projects/{project_id}/                               │
│   -> returns project_id                                                                │
└────────────────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─ [2] Preflight (optional, read-only) ──────────────────────────────────────────────────┐
│ POST /api/projects/{project_id}/scan-preflights                                        │
│   InventoryPreflightService -> bounded candidate preview + HMAC cursor                 │
│   limits: 100 paths / 20 dir scopes / 200 reviews                                      │
│   creates NO scan_id, NO build, NO latest pointer                                      │
└────────────────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─ [3] Create scan run ──────────────────────────────────────────────────────────────────┐
│ POST /api/scans   body { project_id, boundary_decisions[] }                            │
│   InventorySelectionService:                                                           │
│     normalize -> revalidate (409 PREFLIGHT_STALE) -> resolve -> materialize            │
│     materialize: TOCTOU safety -> precedence -> proposal -> audit -> provenance        │
└────────────────────────────────────────────────────────────────────────────────────────┘
     │
     ├─ pending proposals ──▶ 200 { status: "requires_boundary_decision" }  (no scan_id)
     │                          └─▶ BoundaryDecisionModal: scan_this_run | skip_this_run
     │                                └─▶ re-POST /api/scans with decisions   (loop)
     ▼
┌─ [4] Step 3 scan phase (deterministic facts only, read-only) ──────────────────────────┐
│ ScanSnapshotService.scan_and_save -> ProjectScanService.scan                           │
│   FilesystemProvider.build_inventory -> FileInventory                                  │
│     -> inventory_policy.apply (approved boundary overlay)                              │
│     -> ConfigParseProvider -> DockerComposeProvider                                    │
│        -> DependencyManifestProvider -> CodePatternProvider   (fixed order)            │
│   provider exception => warning + ParseIssue, run continues                            │
│   => ScanSnapshot (immutable), scan_id = "scan:<uuid4>"                                │
└────────────────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─ [5] Build phase: Step 4 -> Step 6 ────────────────────────────────────────────────────┐
│ MapBuildService.build_from_snapshot -> MapBuildPipeline.materialize                    │
│   build_id = "build:<uuid4>", build_reason = "initial_scan"                            │
│                                                                                        │
│   Step 4  SystemMapV2MaterializationService.materialize                                │
│     RagTemplateService.load("rag-core-v1")        [legacy template, 13 slots]          │
│     -> ComponentDetectionService (ComponentBridgeRegistry.match)                       │
│     -> ManualMappingService.apply -> EndpointDetectionService                          │
│     -> RiskHintService -> RecommendedNextCheckService                                  │
│     -> FlowDerivationService -> SystemMapV2NormalizeService.assemble                   │
│     -> SystemMapV2ValidationService.validate            <== GATE 1                     │
│                                                                                        │
│   Step 6-1  ProfileInferenceService.infer    (sole owner, pure Python)                 │
│     ReferenceCapabilityAssessmentService -> exactly 52 assessments                     │
│     ProfileFindingService                -> exactly 15 profile findings                │
│     mapping_completeness = (detected + not_detected + 0.5*partial) / 52                │
│     ProfileSignalValidationService.validate (fail-closed)  <== GATE 2                  │
│                                                                                        │
│   Step 6-2  ReadinessReportService.build                                               │
│   Step 6-3+ StaticExecutionArtifactService.build                                       │
└────────────────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─ [6] Step 7: BuildArtifactPublisher.publish ───────────────────────────────────────────┐
│ 10 public sibling artifacts, written in this order:                                    │
│   1 ai_system_map.json      2 ai_system_map.md       3 profile_signals.json            │
│   4 readiness_report.json   5 call_graph.json        6 dataflow_hints.json             │
│   7 execution_paths.json    8 evidence_table.json    9 system_map.mmd                  │
│  10 execution_map.mmd                                                                  │
│ ephemeral: GraphViewModel -> API-inline only (viewer_load_result), never on disk       │
│ publish itself is sequential (+ _discard_partial on error), NOT atomic                 │
└────────────────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─ [7] BuildCommitService.commit  <== GATE 3 (web path only) ────────────────────────────┐
│ staging dir -> validate artifact set -> publish directory                              │
│   -> persist MapBuildManifest -> promote latest pointer (CAS)                          │
│ errors: build_artifact_set_invalid | build_manifest_persist_failed                     │
│         | stale_latest_revision                                                        │
│ CLI map has no commit service => CLI builds are non-atomic by design                   │
└────────────────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─ [8] Response to caller ───────────────────────────────────────────────────────────────┐
│ 200 MapBuildScopedResponse (save_committed_build_projection)                           │
│   { project_id, scan_id, build_id, based_on_build_id, build_reason,                    │
│     applied_mapping_ids[],                                                             │
│     build_result:       { status, active/requested/source_schema_version,              │
│                           profile_inference_result, readiness_report, warnings[] },    │
│     viewer_load_result: { loaded, ai_system_map, graph_view_model } }                  │
│ no output_run_dir / *_path fields (MODEL-CONTRACT 7.2)                                 │
└────────────────────────────────────────────────────────────────────────────────────────┘

parallel channel, whole run:
  GET /api/scan/events (SSE)  ┄┄▶  useScanProgress  ┄┄▶  ProgressStrip
    percent / stage / message only; gives up after 3 consecutive errors;
    progress is never treated as completion (completion = the [8] response)
```

### 1.1 CLI 變體（同一核心，少了 HTTP 與 commit gate）

```text
uv run systograph map <project_path>        (pyproject also exposes: systograph map)
  │
  ├─▶ MapBuildService.build
  │     OutputArtifactProvider.check_preconditions
  │       fail ──▶ map-error.md + status="error"  (no siblings, no build)
  │     -> ProjectScanService.scan  -> mint scan_id + build_id
  │     -> MapBuildPipeline.materialize   (same Step 4 / 6 / 7, same GATE 1 + 2)
  │     -> BuildArtifactPublisher.publish -> 10 siblings into --output dir
  │
  └─▶ no BuildCommitService: no staging dir, no manifest, no latest-pointer promote

other CLI commands: migrate-legacy-mappings | trace <map_json> | validate-map <map_json>
no web equivalent:  the HTTP build entry is POST /api/scans (project-scoped, commit-gated)
```

### 1.2 解說

1. **邊界先於掃描**：Step 2 的 inventory / boundary 決策發生在任何檔案被讀取之前。
   preflight 只給有界的候選預覽（100 paths / 20 dir scopes / 200 reviews），
   不產生 `scan_id`、不產生 build、不動 latest 指標。
   `requires_boundary_decision` 回應同樣沒有 `scan_id`，且決策只對「這一次 run」有效。
2. **Facts 先於 Assessment**：Step 3 只做確定性抽取（AST、regex、config parser、TOML 規則目錄），
   任何 provider 失敗都降級成 warning + `ParseIssue`，不會用推測補洞。
3. **三道驗證閘口，不是單一 Validator**：
   - GATE 1 `SystemMapV2ValidationService.validate` —— Step 4 組裝完 v2 normalized map 後驗證。
   - GATE 2 `ProfileSignalValidationService.validate` —— Step 6 的 fail-closed 第二意見，
     52 格與 15 profiles 數量、身分欄位不符即擋下。
   - GATE 3 `BuildCommitService.commit` —— 只存在於 web 路徑，
     staging → validate artifact set → publish → 寫 manifest → CAS 提升 latest 指標。
     失敗碼為 `build_artifact_set_invalid` / `build_manifest_persist_failed` / `stale_latest_revision`。
4. **發布的是 10 個 sibling artifacts，不是單一 `ai_system_map.json`**：
   7 個 JSON（map / profile_signals / readiness_report / call_graph / dataflow_hints /
   execution_paths / evidence_table）+ 3 個 render（`ai_system_map.md`、`system_map.mmd`、
   `execution_map.mmd`）。`GraphViewModel` 是第 11 個產物但**只走 API inline，不落地磁碟**。
   `map-error.md` 只在 precondition 失敗時出現，不算 sibling。
5. **原子性來自 commit，不是 publish**：`BuildArtifactPublisher.publish` 是逐檔序列寫入，
   例外時 `_discard_partial`；真正的原子切換由 `BuildCommitService` 的 staging + CAS 完成。
   因此 CLI `map` 產出的目錄本質上不是原子交付。
6. **SSE 只是進度**：`GET /api/scan/events` 供 `ProgressStrip` 顯示 percent / stage / message，
   前端連續 3 次錯誤即放棄；完成與否一律以 `POST /api/scans` 的回應為準。
7. **身分是 `scan_id` + `build_id`**：沒有獨立 `snapshot_id`；同一 build 的所有 sibling 必須滿足
   `generated_from_build_id === build_id`；`environment_id` 在 Phase 2 固定為
   `environment:default-static`。

---

## 2. Viewer 載入時序（前端一律走 API，不讀磁碟）

```text
┌─ [V1] Mount ───────────────────────────────────────────────────────────────────────────┐
│ main.tsx -> QueryClientProvider -> App (single page shell, no router)                  │
│ useViewerPayload(mode, apiBaseUrl, projectId, buildId)                                 │
│   dataSourceMode defaults to "api"; activeBuildId null = follow latest                 │
└────────────────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─ [V2] Fetch build-scoped payload ──────────────────────────────────────────────────────┐
│ GET /api/projects/{project_id}/map-builds/latest        (primary read)                 │
│   pinned historical build -> GET /api/map-builds/{build_id}                            │
│   build list             -> GET /api/projects/{project_id}/map-builds                  │
│ no fallback: GET /api/map and GET /map are retired (404); read failure is an error     │
│ the viewer NEVER opens ai_system_map.json from disk                                    │
└────────────────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─ [V3] zod contract layer  (frontend/src/contracts/viewer.ts) ──────────────────────────┐
│ parseMapBuildPayload -> mapBuildScopedResponseSchema                                   │
│   phase2BuildGraphViewModelSchema: "graph-view-model/v1" + "ai-system-map/v2"          │
│     (viewer_load / demo path uses phase2GraphViewModelSchema)                          │
│   profileInferenceResultSchema: assessments.length(52), profiles.length(15)            │
│   readinessReportSchema      : "readiness-report/v1"                                   │
│   superRefine: generated_from_build_id === build_id, sidecar identity match            │
│ fail -> ViewerContractError -> StateOverlay error (never silent Sample fallback)       │
└────────────────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─ [V4] Derive view state ───────────────────────────────────────────────────────────────┐
│ react-query cache -> App derives graph, 16 architecture views, completeness            │
│ extractMappingCompleteness: graph first, then profile_inference_result                 │
│ frontend never recomputes five-state / activation / mapping completeness               │
└────────────────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─ [V5] ArchitectureMap render ──────────────────────────────────────────────────────────┐
│ input = graph_view_model (API-inline, ephemeral) -- not a graph library                │
│   hasBackendPlaneProjection guard (reference_map_version + node.plane_id)              │
│   bucket nodes by node.plane_id; plane membership is backend-owned                     │
│   10 DOM plane bands in PLANE_PRESENTATION_ORDER + "unassigned" band last              │
│   ArchitectureEdgeOverlay: useLayoutEffect + ResizeObserver + DOMRect-measured         │
│                            cubic-bezier SVG paths over graph.edges/relationships       │
│ SystemGraph (reactflow + elkjs) exists but is mounted by no live path                  │
└────────────────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─ [V6] Selection -> DetailPanel ────────────────────────────────────────────────────────┐
│ click node card -> store.setSelected -> DetailPanel                                    │
│   Summary  : graph.details.evidence_by_id / risk_hints_by_id /                         │
│              reference_assessments_by_id / profile_findings_by_id                      │
│              -> same payload, no extra disk read and no extra request                  │
│   L2 / L3  : POST /api/detail-scans { project_id, build_id, target_type,               │
│              target, scan_depth } -> child build (build_reason="detail_scan")          │
│              -> GET /api/map-builds/{child_build_id} -> setQueryData                   │
│              409 base_build_not_latest -> isStaleBase, reload latest                   │
└────────────────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─ [V7] Query Trace replay ──────────────────────────────────────────────────────────────┐
│ POST /api/trace { project_id, build_id, endpoint_id, query, timeout_seconds }          │
│   -> traceRunResultSchema (asserts source_build_id === buildId)                        │
│   -> useTraceReplay (sort by sequence_index, id) -> ReplayTimeline scrub               │
│   -> resolveTraceHighlight -> ArchitectureMap highlight                                │
│ trace events are transient: never persisted, never a sibling artifact                  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 解說

1. **前端沒有磁碟路徑**：viewer 不開啟 `ai_system_map.json`。主讀取是
   `GET /api/projects/{project_id}/map-builds/latest`，pinned 歷史 build 走
   `GET /api/map-builds/{build_id}`。**沒有 fallback**——process-wide 的 `GET /api/map` 與
   `GET /map` 已退役（回 404），讀取失敗直接呈現錯誤，不再靜默降級。
   （`frontend/src/services/viewerApi.ts` 仍留著呼叫這兩支的死碼，由 FE-2 清除。）
   回應本身不含 `output_run_dir` 或任何 `*_path`。
2. **契約層是硬閘口**：`contracts/viewer.ts` 用 zod 檢查 `graph-view-model/v1` /
   `ai-system-map/v2` 字面值、assessments 必須剛好 52 筆、profiles 必須剛好 15 筆，
   並用 superRefine 驗身分一致（`generated_from_build_id === build_id`、sidecar 對齊）。
   驗證失敗顯示 `StateOverlay` 錯誤，**絕不靜默退回 Sample**。
3. **渲染器是 `ArchitectureMap`，不是 reactflow**：10 條 plane band 由 DOM + CSS 排版，
   邊線由 `ArchitectureEdgeOverlay` 依 `DOMRect` 量測後畫成 SVG bezier。
   `SystemGraph` / `SystemNode` / `PlaneBandNode`（reactflow + elkjs）留在 repo 且有單元測試，
   但**沒有任何 live 路徑掛載它們**。plane 歸屬完全由後端 `node.plane_id` 決定，前端不推論。
4. **證據來自同一份 payload**：DetailPanel 的 Summary 直接讀
   `graph.details.evidence_by_id` / `risk_hints_by_id` / `reference_assessments_by_id` /
   `profile_findings_by_id`，不需要第二次請求，更不會去讀檔。
   只有 L2 / L3 深掃需要 `POST /api/detail-scans`，而那會產生一個新的子 build。
5. **前端不重算**：五態、activation 六態、Mapping Completeness 一律由後端
   `ProfileInferenceService` 定案；前端連 profile 標籤 / 數量 / 排序都不得硬編。
6. **Sample 模式是同一條驗證路徑**：`data/sampleMap.ts` 由 4 份 JSON fixture 組出真實 v2 envelope，
   再走同一個 `parseViewerPayload`；沒有 `frontend-json-sample.json` 這個檔案。

---

## 3. Apply / Detail scan / Rescan 的分岔

```text
ScanSnapshot   scan_id = "scan:<uuid4>"   (immutable, scans/{scan_id}/snapshot.json)
     │
     ├──▶ [Apply]  POST /api/map-builds/{base_build_id}/apply  { mapping_ids[] }
     │              * never re-scans: replays the SAME snapshot
     │                (build_from_snapshot, Step 3 skipped, Steps 4-7 rerun)
     │              * same scan_id, NEW build_id, fresh 10 siblings
     │              * build_reason = "apply_confirmations"
     │              * base_build_id MUST equal the latest pointer,
     │                otherwise 409 base_build_not_latest
     │              * idempotent per request digest; commits via BuildCommitService
     │
     ├──▶ [Detail scan]  POST /api/detail-scans
     │              * child build from the enriched map (build_from_enriched_map)
     │              * build_reason = "detail_scan", parent via based_on_build_id
     │              * missing parent sidecar -> 409 profile_sidecar_unavailable
     │
     └──▶ [Rescan]  POST /api/scans  (fresh preflight + boundary decisions)
                    * ProjectScanService runs again against the working tree
                    * NEW scan_id AND NEW build_id
                    * build_reason = "initial_scan"
```

- **Apply 永不重掃**：它把同一個 `scan_id` 的 snapshot 重放進一個新的 `build_id`，
  跳過 Step 3，只重跑 bridge + confirmed mappings 與 Steps 4–7，並重新產出全套 sibling。
  前置條件是 `base_build_id` 必須等於 latest 指標，否則 409 `base_build_not_latest`；
  前端 `useMappingProposal` 收到 409 會 `reloadLatest` 後重試。
- **Detail scan** 產生子 build（`build_reason = "detail_scan"`），透過 `based_on_build_id` 記錄父子關係；
  父 build 缺少 profile sidecar 時 409 `profile_sidecar_unavailable`。
- **Rescan 才是新 snapshot**：重新走 preflight / boundary 決策，產生新的 `scan_id` 與 `build_id`。
- `build_reason` 只有三個合法值：`initial_scan` / `apply_confirmations` / `detail_scan`。

---

## 4. 這條流程刻意沒有的東西

- **沒有 LLM orchestration**：整條管線由 Python 服務推動；LLM 只在 mapping proposal 產生候選，
  且候選不能決定五態、profile 或 readiness。
- **沒有 `AssessmentOrchestrator`**：Step 6 是純 deterministic Python（Plan 17 deferred）。
- **沒有 UA semantic merge**：UA rollout Phase A 只採用 deterministic 抽取腳本，
  `semantic` 在 Phase 2 固定為 `null`；sidecar 允許缺席，TOML providers 仍是主路徑。
- **沒有 runtime 證明**：static execution artifacts 只能說「static evidence suggests」，
  不得寫成 executed / traversed。
- **沒有數值 confidence**：證據強度用 `evidence_strength` 列舉值表達，
  Mapping Completeness 是覆蓋率而非信心分數（分母恆為 52）。
