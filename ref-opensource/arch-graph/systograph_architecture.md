# Systograph / Systograph — 完整架構圖（ASCII）

本檔是 `ref-opensource/arch-graph/` 內的 **Systograph 側 reference diagram**，供
Understand-Anything 整合邊界討論使用。權威契約仍以
`docs/MODEL-CONTRACT.md`、`docs/API-GUIDE.md`、`docs/design/epic1-phase2.md` 為準；
本檔若與那三份衝突，一律以那三份為準。

現況（UA rollout **Phase A**）：Step 3 掃描主路徑是 Systograph 自己的 TOML rule providers；
Step 6 是純 deterministic Python 的 `ProfileInferenceService`。UA sidecar 尚未實作
（`src/` 目前沒有任何模組 import `ref-opensource/`），LLM 只出現在 opt-in 的 mapping
proposal 建議路徑，**不能**決定五態、Mapping Completeness 或 readiness。

---

## 1. 完整架構總圖

```text
┌─ Clients / presentation ─────────────────────────────────────────────────────────────────────┐
│ Frontend viewer  "systograph-viewer"  --  React 18 + Vite 6 + TS, pnpm@10.12.1, :5173        │
│   live renderer : ArchitectureMap  = DOM plane bands + DOM-measured SVG edge overlay         │
│   dormant       : SystemGraph (reactflow + elkjs), Sidebar, LensPanel, ScanTemplatePage      │
│   client state  : Zustand viewerStore (14 fields) + react-query + zod contract layer         │
│   run modes     : Sample (data/sampleMap.ts fixtures)  |  API (VITE_API_BASE_URL)            │
│                                                                                              │
│ Operator terminal  --  uv run systograph <cmd>      (pyproject alias: systograph)              │
└───────────────────────────────────────┬──────────────────────────────────────────────────────┘
                                        │  HTTP JSON + SSE   /   in-process call
                                        ▼
┌─ Adapters  (platform-specific; hold no core scanner logic) ──────────────────────────────────┐
│ ┌─ Typer CLI   cli/main.py ─────────────────┐  ┌─ FastAPI   web/app.py :: create_app() ────┐ │
│ │ map <project_path>                        │  │ middleware: CORS -> :5173 origins only    │ │
│ │ migrate-legacy-mappings [--apply|dry-run] │  │             SafeUnhandledException        │ │
│ │ trace <map_json>                          │  │             RequestSizeLimit (1 MB)       │ │
│ │ validate-map <map_json> (viewer_command)  │  │ routers x9: map, map_build, scan,         │ │
│ │                                           │  │             detail_scan, mapping,         │ │
│ │ no BuildCommitService on this path        │  │             mapping_proposal, project,    │ │
│ └───────────────────────────────────────────┘  │             trace, viewer                 │ │
│                                                └───────────────────────────────────────────┘ │
│                                                                                              │
│ every service is a create_app() kwarg and is attached individually as app.state.<name>       │
│ -- there is NO AppServices container; web/dependencies.py exposes 15 typed Depends           │
└───────────────────────────────────────┬──────────────────────────────────────────────────────┘
                                        │  adapters call core services; core never calls back
                                        ▼
┌─ Core engine  src/systograph/core/  (111 services, 28 models; never imports web/ or cli/) ─────┐
│ ┌─ Build pipeline core ─────────────────────┐  ┌─ Detection + Step-4 bridge ───────────────┐ │
│ │ MapBuildService  (3 entry points)         │  │ ProjectScanService                        │ │
│ │ MapBuildPipeline map_build_orchestration  │  │ ComponentDetectionService                 │ │
│ │ SystemMapV2 Materialization / Normalize / │  │ ComponentBridgeRegistry + BridgeRules     │ │
│ │   Validation services                     │  │ EndpointDetection RiskHint FlowDerivation │ │
│ │ BuildArtifactPublisher BuildCommitService │  │ RecommendedNextCheckService               │ │
│ │ BuildManifestService MapBuildQueryService │  │ RagTemplateService  ("rag-core-v1")       │ │
│ │ CanonicalMapLoader CanonicalOutputConfig  │  └───────────────────────────────────────────┘ │
│ └───────────────────────────────────────────┘                                                │
│                                                                                              │
│ ┌─ Profile + readiness (Step 6) ────────────┐  ┌─ Graph projection + viewer ───────────────┐ │
│ │ ProfileInferenceService   (SOLE OWNER)    │  │ ViewerSessionService (3 entries)          │ │
│ │ ReferenceCapabilityAssessmentSvc  -> 52   │  │ GraphProjectionService -> GraphViewModel  │ │
│ │ ProfileFindingService + rules     -> 15   │  │ GraphLensProjector (6 lenses) + filters   │ │
│ │ ProfileSignalValidation (fail-closed)     │  │ ReferenceMapOverlay ProfileAttachment     │ │
│ │ CapabilityReferenceMapLoader (10 / 52)    │  │ GraphMarkdown / GraphMermaid renderers    │ │
│ │ ReadinessReportService                    │  │ SystemMapIndex viewer_legacy_compat       │ │
│ │ StaticExecutionArtifactService            │  └───────────────────────────────────────────┘ │
│ └───────────────────────────────────────────┘                                                │
│                                                                                              │
│ ┌─ Inventory + scan boundary ───────────────┐  ┌─ Mapping + proposals ─────────────────────┐ │
│ │ InventorySelectionService (facade)        │  │ ManualMappingService + repository         │ │
│ │ InventoryPreflightService (+cursor/limit) │  │ MappingProposalService (facade, RLock)    │ │
│ │ Candidate/Ignore/Git/Metadata/Risk svcs   │  │ candidates / decisions / mapping_factory  │ │
│ │ DecisionService Materializer Precedence   │  │ MappingEvidencePacketBuilder (masked)     │ │
│ │ PostDecisionSafety (TOCTOU) Provenance    │  │ LlmProposalProvider -> NIM (opt-in)       │ │
│ │ ScanBoundaryReviewService ScanSnapshotSvc │  └───────────────────────────────────────────┘ │
│ └───────────────────────────────────────────┘                                                │
│                                                                                              │
│ ┌─ Apply + detail scan ─────────────────────┐  ┌─ Trace / security / logging ──────────────┐ │
│ │ ApplyConfirmationsService (no re-scan)    │  │ QueryTraceService (events not persisted)  │ │
│ │ DetailScanService (L2) DetailScanBuild    │  │ SecretMasking + SecretValidation (closed) │ │
│ │ ComponentDetailScanService (ast + regex)  │  │ PathSafety SnapshotSafety SecretBoundary  │ │
│ │ CodePathScanService (L3, ast.Call)        │  │ LoggingService (safe_log_event)           │ │
│ │ DetailScanTargetResolver                  │  │ core/security/egress_policy.py            │ │
│ └───────────────────────────────────────────┘  └───────────────────────────────────────────┘ │
│                                                                                              │
│ ┌─ Legacy v1 compatibility ─────────────────┐  ┌─ Loaders + config ────────────────────────┐ │
│ │ SystemMapV1ToV2Adapter (711 ln)           │  │ RuleCatalogLoader ScanInventoryRuleLoader │ │
│ │ SystemMapValidation (v1 read)             │  │ ProfileRegistryLoader (labels/axes only)  │ │
│ │ LegacyManualMappingMigrationService       │  │ LlmProposalConfigLoader PromptTemplate    │ │
│ └───────────────────────────────────────────┘  │ QueryTraceConfigLoader                    │ │
│                                                │ core/models/ (28)  core/repositories/     │ │
│                                                └───────────────────────────────────────────┘ │
└───────────────────────────────────────┬──────────────────────────────────────────────────────┘
                                        │  core services dispatch providers and load rule catalogs
                                        ▼
┌─ Providers, declarative rule catalogs, legacy template ──────────────────────────────────────┐
│ ┌─ core/providers/  (17 modules) ───────────┐  ┌─ core/rules/*.toml (8) + template ────────┐ │
│ │ scan providers, FIXED order:              │  │ capability_reference_map.toml             │ │
│ │   1 ConfigParseProvider                   │  │   10 planes / 52 nodes (ref catalog)      │ │
│ │   2 DockerComposeProvider                 │  │ profile_registry.toml    15 profiles      │ │
│ │   3 DependencyManifestProvider            │  │ scan_inventory_rules.toml  17 excludes    │ │
│ │   4 CodePatternProvider                   │  │ code_pattern_rules.toml                   │ │
│ │ FilesystemProvider (read-only inventory)  │  │ risk_hint_rules.toml                      │ │
│ │ OutputArtifactProvider (+ policy)         │  │ dependency_manifest_rules.toml            │ │
│ │ EndpointCallProvider (EgressPolicy-gated) │  │ recommended_next_check_rules.toml         │ │
│ │ LlmProposalProvider  "nvidia-nim" opt-in  │  │ docker_image_rules.toml                   │ │
│ │ LocalJson state / project / history repos │  │ core/templates/rag-core-v1.json           │ │
│ └───────────────────────────────────────────┘  │   13 slots, 2 flows -- LEGACY ONLY        │ │
│                                                └───────────────────────────────────────────┘ │
└───────────────────────────────────────┬──────────────────────────────────────────────────────┘
                                        │  write
                                        ▼
┌─ Persistence + published artifacts ──────────────────────────────────────────────────────────┐
│ ┌─ Durable local state   ${SYSTOGRAPH_STATE_DIR:-~/.systograph} ───────────────────────────────┐ │
│ │ projects/{project_id}/                                                                   │ │
│ │   project.json   latest.json (CAS-promoted pointer)   .project.lock                      │ │
│ │   mappings/{mapping_id}.json                                                             │ │
│ │   scans/{scan_id}/snapshot.json + manifest.json        <- immutable snapshot             │ │
│ │   builds/{build_id}/manifest.json                      <- one materialization            │ │
│ │ migration-backups/{project_id}/     {mapping}.{token}.legacy.json + index.json           │ │
│ │ migration-quarantine/{project_id}/  {mapping}.{token}.legacy.json + .original.json       │ │
│ │ files 0600 / dirs 0755  --  build artifacts do NOT live here                             │ │
│ └──────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                              │
│ ┌─ Published build output   (caller-supplied --output dir; one set per build_id) ──────────┐ │
│ │ 7 JSON : ai_system_map.json  profile_signals.json  readiness_report.json                 │ │
│ │          call_graph.json  dataflow_hints.json  execution_paths.json                      │ │
│ │          evidence_table.json                                                             │ │
│ │ 3 render: ai_system_map.md   system_map.mmd   execution_map.mmd                          │ │
│ │ ephemeral: GraphViewModel -> API inline only (viewer_load_result), never on disk         │ │
│ │ error   : map-error.md  (precondition failure only; not one of the 10 siblings)          │ │
│ └──────────────────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
                    ▲  read-back: GET /api/projects/{id}/map-builds/latest
                    │  -> viewer_load_result { map + sidecars + graph_view_model }
                    └── consumed by the Frontend viewer (top of this diagram)
```

### 1.1 圖區塊解說

| 區塊 | 內容與重點 |
|---|---|
| **Clients / presentation** | 前端 package 名稱是 `systograph-viewer`。實際在跑的畫布是 `ArchitectureMap`（純 DOM plane bands + 量測後畫出的 SVG bezier overlay）；`SystemGraph`（reactflow + elkjs）、`Sidebar`、`LensPanel`、`ScanTemplatePage` 都還在 repo 裡且有單元測試，但**沒有任何非測試模組 import 它們**，屬 dormant。 |
| **Adapters** | CLI 與 Web 都只是轉接層。Typer 只有 4 個指令；`validate-map` 由 `viewer_command.py` 註冊（指令名不是 `viewer`）。FastAPI 由 `create_app()` 就地組裝所有 service，並**逐一**掛在 `app.state.<name>`；**沒有** `AppServices` 容器、也沒有 `build_app_services()`。 |
| **Core engine** | 10 個服務叢集，共 111 個 service 模組。依賴方向單向：`core/` 不 import `web/`、`cli/`。`ProfileInferenceService` 是 52 個 assessment 與 15 個 profile 的唯一擁有者。 |
| **Providers / rules** | 掃描 provider 有**固定順序**（ConfigParse → DockerCompose → DependencyManifest → CodePattern）；任一 provider 拋錯只會降級成 warning + `ParseIssue`。8 份 TOML catalog 是宣告式規則來源；`rag-core-v1.json` 只是 legacy template（13 slots、2 flows、**沒有**選用 slot）。 |
| **Persistence** | 本機 state（project / scan / build lineage、manual mapping、latest 指標）住在 `${SYSTOGRAPH_STATE_DIR:-~/.systograph}`；**build artifacts 不住這裡**，它們寫到呼叫端指定的 `--output` 目錄。 |
| **Artifacts** | 一個 build 產出 **10 份公開 sibling**（7 JSON + 3 render）。`GraphViewModel` 是 **ephemeral**：只在 API 回應中內嵌（`viewer_load_result.graph_view_model`），永遠不落地。`map-error.md` 只在 precondition 失敗時出現，不算 sibling。 |

### 1.2 讀圖注意事項

- 這張圖沒有 "Scanner Service" 這種東西：掃描的入口是 `ProjectScanService`，組裝的入口是
  `SystemMapV2MaterializationService`，兩者由 `MapBuildService` / `MapBuildPipeline` 串起來。
- 驗證也不是單一個 `SystemMapValidationService`：v2 的驗證器是
  `SystemMapV2ValidationService`（Step 4 結束）與 `ProfileSignalValidationService`（Step 6，
  fail-closed）；`SystemMapValidationService` 只負責 legacy v1。
- 圖上沒有「AI candidate → canonical」的路徑，因為 Phase 2 根本沒有這條寫入路徑。

---

## 2. Map build pipeline（實際 Step 順序）

```text
MapBuildService.build(request)   entry: CLI `map` only
                                 POST /api/scans + Apply call build_from_snapshot(): no step 2/3
  │
  ├─ 1  require_public_v2_selection()
  ├─ 2  OutputArtifactProvider.check_preconditions()
  │        └─ fail ──▶ map-error.md + status="error"     (pipeline stops here)
  ├─ 3  ProjectScanService.scan()
  │        FilesystemProvider.build_inventory ──▶ FileInventory ──▶ inventory_policy.apply
  │        then the FIXED provider order:
  │          ConfigParse ──▶ DockerCompose ──▶ DependencyManifest ──▶ CodePattern
  │        a provider raising ──▶ warning + ParseIssue "project_scan_provider_failed"
  ├─ 4  mint  scan_id = "scan:{uuid4}"    build_id = "build:{uuid4}"
  │        MapBuildLineage(build_reason="initial_scan")
  ▼
MapBuildPipeline.materialize()
  │
  ├──▶ "ai-system-map/v2" ACTIVE ──▶ SystemMapV2MaterializationService        ◀── Step 4
  │        1 RagTemplateService.load("rag-core-v1")     legacy template, NOT a blueprint
  │        2 ComponentDetectionService.detect + ComponentBridgeRegistry.match
  │        3 ManualMappingService.apply / apply_selected            (apply replay)
  │        4 EndpointDetectionService.detect
  │        5 RiskHintService.derive
  │        6 RecommendedNextCheckService.derive         (System-1, graph-level)
  │        7 FlowDerivationService.derive
  │        8 SystemMapV2NormalizeService.assemble
  │        9 SystemMapV2ValidationService.validate
  ▼
MapBuildPipeline._complete()                                          ◀── Step 6 then Step 7
  1 model_copy(update={scan_id, build_id, generated_from_build_id=build_id})
  2 ProfileInferenceService.infer()          SOLE OWNER of the 52 + 15 assessment
       ├─ ReferenceCapabilityAssessmentService.assess ──▶ exactly 52 assessments
       ├─ ProfileFindingService.infer                 ──▶ exactly 15 ProfileFinding
       ├─ mapping_completeness = (detected + not_detected + 0.5 * partial) / 52
       └─ ProfileSignalValidationService.validate        (fail-closed)
  3 ReadinessReportService.build()
  4 StaticExecutionArtifactService.build()
  5 BuildArtifactPublisher.publish()  ──▶ 10 sibling files, written SEQUENTIALLY:
       ai_system_map.json ──▶ ViewerSessionService.build_canonical
                          ──▶ GraphProjectionService.project (ephemeral GraphViewModel)
                          ──▶ ai_system_map.md ──▶ profile_signals.json
                          ──▶ readiness_report.json ──▶ call_graph.json
                          ──▶ dataflow_hints.json ──▶ execution_paths.json
                          ──▶ evidence_table.json ──▶ system_map.mmd ──▶ execution_map.mmd
       on exception: _discard_partial()      (this step is NOT atomic on its own)
  6 MapBuildResult
```

### 2.1 原子性歸屬

```text
Web path   POST /api/scans   /   POST /api/map-builds/{base_build_id}/apply
    │
    └─▶ BuildCommitService.commit(build=<closure calling MapBuildService>)
            staging dir ──▶ validate artifact set ──▶ publish directory
                        ──▶ persist MapBuildManifest
                        ──▶ promote latest.json by compare-and-swap
            errors: build_artifact_set_invalid · build_manifest_persist_failed
                    · stale_latest_revision

CLI path   uv run systograph map <project_path>
    │
    └─▶ no BuildCommitService in the chain  ══▶  CLI builds are NON-ATOMIC by design
```

### 2.2 解說

- `MapBuildService` 有三個入口：`build()`（會掃描）、`build_from_snapshot()`（Apply / POST
  `/api/scans` 的 snapshot 路徑，不掃描）、`build_from_enriched_map()`（Detail Scan 子 build）。
  三者第一步都會呼叫 `require_public_v2_selection()`。
- **Apply 永遠不重掃**：它重放同一份 `snapshot.json`，換一個新的 `build_id`，重跑 Step 4–7，
  並要求 base build 必須是 latest（否則 409 `base_build_not_latest`）。Rescan 才會產生新的 `scan_id`。
- `BuildArtifactPublisher.publish()` 本身**不是原子**的：它循序寫 10 個檔，例外時 `_discard_partial()`。
  原子性由 `BuildCommitService` 提供（staging → validate → publish → manifest → CAS 推進 latest），
  而 CLI 路徑沒有接 `BuildCommitService`，所以 **CLI build 依設計是非原子的**。
- `RecommendedNextCheckService` 是 pipeline 的正式一步（Step 4 第 6 項），常被舊文件漏掉。

---

## 3. 契約不變式（違反 = P1）

- **身分四元組**：`scan_id`（不可變快照）+ `build_id`（一次 materialization）+ `environment_id`
  + `artifact_set_version`。Phase 2 的 `environment_id` 固定為 `environment:default-static`。
  禁止獨立的 `snapshot_id`。同一個 build 的所有 sibling **MUST** 滿足
  `generated_from_build_id === build_id`；父子關係用 `based_on_build_id`。
- **五態評估**：`detected` / `partial` / `undetermined` / `not_detected` / `conflicted`。
  `detected` 需要非空的 `direct_evidence_ids`；只有間接證據最高只能 `partial`；
  `not_detected` 需要 depth = 0 **且**通過 coverage gate，否則是 `undetermined`；
  `conflicted` 需要雙邊都有證據的 `conflict_fields`。**缺席 ≠ 反證**。
  Activation 是另一組正交的六態。
- **禁止欄位／用語**：`confidence`、`quality`、`accuracy`、`score`、pass/fail 一律不得出現。
  `implementation_depth_level ∈ {0..4}` 表示觀察到的範圍，不是分數。
- **Mapping Completeness**：權重 detected = 1、partial = 0.5、not_detected = 1、
  undetermined = 0、conflicted = 0，**分母恆為 52**；它不是信心值。
- **唯一擁有者**：`ProfileInferenceService` 擁有 52 個 assessment 與 15 個 profile。
  proposal 服務不得決定狀態，viewer 不得重算，前端不得寫死 profile 標籤／數量／順序。
- **Reference catalog**：固定 10 planes / 52 nodes，由 `capability_reference_map.toml` 擁有座標與
  標籤，在 **Step 6 被評估**，**永遠不是 Step 4 的組裝藍圖**；`reference_node_id ≠ component_id`；
  後端一律輸出全部 52 個。15 條可執行規則由 `profile_rule_definitions.py` 擁有，
  `profile_registry.toml` 只擁有標籤／軸／顯示順序（coverage-locked）。
- **rag-core-v1**：legacy-only，1.0.0，凍結，13 slots / 2 flows，無選用 slot。
  「slot」一詞只適用於這個 legacy template，不可與 52 nodes 混用。
- **兩個 `recommended_next_checks` 欄位**（Step 4 graph-level typed 的 System-1 vs Step 6
  profile attachment 上 `string[]` 的 System-2）不得互相替代。
- **靜態執行 artifacts 不是 runtime 證據**：用語必須是 "static evidence suggests"，
  不得說 "executed" / "traversed"。
- **Schema**：`ai-system-map.v2` 是 active public schema；v1 只用於讀取／遷移
  （寫入路徑已於 2026-08-07 移除；公開請求選 v1 會得到
  `legacy_output_not_selectable`）。

---

## 4. Understand-Anything sidecar 邊界（規劃中，尚未實作）

```text
Systograph Step 2  --  approved FileInventory (the only allowlist)
        │  systograph-ua-request/v1
        │    { schema_version, project_root, files[{path, language, size_lines,
        │                                          file_category}] }
        ▼
┌─ UnderstandAnythingAnalysisService   (PLANNED -- no src/ reference exists yet) ──────────┐
│ NodeRuntimePreflight ──▶ SubprocessRunner ──▶ ResultValidator ──▶ ResultAdapter          │
│                                                                                          │
│ systograph-analyze.mjs --project-root <target> --inventory <work>/request.json             │
│                      --work-dir <work>/understand-anything --output <work>/result.json   │
│     extract-import-map.mjs ──▶ compute-batches.mjs ──▶ extract-structure.mjs (per batch) │
│                                                                                          │
│ STOP HERE: no file-analyzer, no semantic graph merge, no UA Phase 3-7,                   │
│ no scan-project.mjs (its enrichment is ported into Systograph Step 2 instead)                   │
└──────────────────────────────────────────────────────────────────────────────────────────┘
        │  systograph-ua-result/v1
        │    { schema_version, status, structural{import_map, files, call_graph_hints},
        │      semantic: null  (FIXED in Phase 2), warnings, stats }
        │    snapshot-internal wrapper -- NOT a public artifact
        ▼
ProjectScanResult (Step 3 facts)
        │
        ├─── today (Phase A): the Systograph TOML rule providers are the ONLY primary path
        ├┄┄▶ Plan 14 parity gate passes: code_pattern / dependency_manifest /
        │                                docker_image providers leave the primary path
        │                                (risk_hint / recommended_next_check TOML stay)
        └┄┄▶ Plan 17 (deferred): UA semantic layer + AssessmentOrchestrator, NOT Phase 2
```

### 4.1 邊界要點

- **採用面只有 3 支腳本**：`extract-import-map.mjs`、`compute-batches.mjs`、`extract-structure.mjs`。
  進入點在 UA Phase 1 之前，回傳點在 deterministic 結構抽取之後、`file-analyzer` 之前。
- **`scan-project.mjs` 永不執行**：它會製造出與 Systograph Step 2 `inventory_policy` 競爭的第二個掃描邊界；
  它的三項 enrichment（語言判定、`fileCategory`、行數）改由 Systograph Step 2 自己做。
- **`semantic` 在 Phase 2 固定為 `null`**；`systograph-ua-result/v1` 是 snapshot 內部包裝，不是公開 artifact。
- **必要改造**：`compute-batches.mjs` 目前把 `.understand-anything/intermediate/` 路徑寫死在目標 repo 內，
  違反 Systograph 的唯讀保證，必須換成顯式的 `--input` / `--output` / `--work-dir`。
- **§8 唯讀與安全規則**：目標 repo 全程唯讀（不得建立 `.understand-anything/`、暫存檔或 fingerprint 檔）、
  中間產物只放 Systograph work dir、路徑重驗、固定 Node 執行檔與腳本路徑、`shell=False` + timeout、
  stdout/stderr 限量並遮罩、Phase 2 不呼叫任何 LLM、fail closed。
- **未採用**：`file-analyzer`、semantic graph merge、`assemble-reviewer`、`architecture-analyzer`
  （10 planes / 52 nodes 由 Systograph Step 6 擁有）、`tour-builder`、knowledge-graph 組裝、dashboard。
- **Plan 14** 是 parity gate（通過後 `code_pattern` / `dependency_manifest` / `docker_image` 三個
  provider 退出主路徑，`risk_hint` / `recommended_next_check` 的 TOML 保留）；
  **Plan 17** 是 deferred 的語意層與 `AssessmentOrchestrator`，不是 Phase 2 的前置條件。

---

## 5. 相關圖檔

- `systograph_flow.md` — Systograph Phase 2 的執行流程（本檔的時序視角）。
- `understand_anything_pipeline_visual.md` — UA `/understand` pipeline 的權威視覺圖。
- `understand_anything_architecture.md` / `understand_anything_architecture_detailed.md` /
  `understand_anything_flow.md` — UA 自身架構與流程。
- `../systograph-understand-anything-integration-boundary.md` — 整合邊界的 accepted 決策紀錄。
