# 2026-07-11 Phase 2 S1 Pipeline Core Backend Report

## 結論

Phase 3 指定七份 S1 pipeline core 計畫的 **backend scope 已完成**：Step 4 typed
bridge、10-plane/52-node catalog、Profile Inference、readiness/static artifacts、
scan/build lineage、Apply replay、local JSON persistence、restart recovery、Detail Scan child
build、Trace binding 與 proposal/profile boundary 都已落成。

2026-07-11 使用者將範圍改為 backend only。本次曾建立的 `frontend/` 程式碼與測試已
全部還原；最終 `frontend/` 沒有 tracked diff 或 untracked 檔案。Frontend handoff JSON
保留為後端契約範例，不代表 UI 已完成。

## 實作邏輯

1. **Facts first**：Step 3 只產生 raw facts/evidence；Step 4 的 typed Python bridge
   決定 canonical component、unmapped review item 或 non-baseline candidate。
2. **Derived assessment read-only**：`ProfileInferenceService` 只消費 normalized v2 map
   與 capability candidates；不 import proposal/manual-mapping mutation services。
3. **Scan 與 Build 分離**：`scan_id` 是 immutable scan snapshot；`build_id` 是從 snapshot
   materialize 的完整 artifact set。Apply 重用原 scan，不讀 repo。
4. **單一路徑重算**：initial、Apply、Detail child 共用 `MapBuildPipeline`，產生同 scope
   的 profile、readiness、static execution、Markdown、Mermaid 與 viewer result。
5. **先 publish、後 promotion**：10 public siblings 全部寫完並驗證後，才以
   `latest.json` revision CAS 推進 latest；失敗清除 unpublished build。
6. **Durable JSON staging contract**：project、snapshot、mapping、manifest 與 latest
   使用 repository protocols、同目錄 atomic replace、project-scoped file lock，保留未來
   database adapter 邊界。
7. **Legacy userspace 穩定**：active canonical artifact 仍為 v1；internal normalized v2、
   requested schema 與 migration warnings 透過 build metadata 明確表達。

## 主要完成項目

### Mapping、catalog 與 bridge

- 新增 `CapabilityCandidateComponent` 與 generic/non-baseline mapping contracts。
- reject、skip、not-applicable 都持久化為 durable decision，但不 materialize 進 topology。
- `evidence_table.json.review_state` 對應 confirmed、rejected、needs_confirmation、
  not_required。
- package-bundled TOML 固定 10 planes / 52 nodes；loader 拒絕 duplicate、unknown ref、
  invalid order、unknown fields 與 executable rule keys。
- `ComponentBridgeRegistry` 接手 Qdrant、Chroma、pgvector、Ollama、OpenAI、retriever、
  application 等 deterministic mapping；weak dependency、reranker、router 保留 review。
- registry 不讀 TOML detector DSL；`ComponentDetectionService` 只負責 orchestration、
  deterministic merge/sort 與 manual mapping hook。

### Profile、readiness 與 artifacts

- `profile-signals/v1` 固定 52 筆 reference assessments、15 筆 profiles。
- 五態 status、activation、typed evidence、conflict、coverage gate 與 related refs 都有
  strict Pydantic validation。
- Mapping Completeness denominator 固定 52，weights 與 numerator 可由 artifact 重算。
- `readiness-report/v1` 輸出 grounding dimensions、15 capability summaries、
  evidence-backed findings、next checks 與 limitations，不輸出不透明總分。
- 每個成功 build atomic publish 10 public siblings：7 JSON + 3 Markdown/Mermaid render。
- canonical map invalid 時 fail closed；profile/readiness/optional static sidecar invalid 時
  build-scoped read 回 stable warning，base graph 仍可讀。

### Identity、Apply 與 persistence

- 新增 `ProjectState`、`ScanSnapshot`、`MapBuildLineage`、`MapBuildManifest`、
  `LatestBuildPointer`。
- `${KAI_MIND_STATE_DIR:-~/.kai-mind}` 為 default durable state root；測試透過 fixture
  隔離，不污染使用者 home。
- project import 以 canonical path digest 重用 identity；restart 後可讀 project、mapping、
  snapshot、history 與 latest build。
- Apply 驗證 latest base、non-empty/unique confirmed mappings、same-project 與 snapshot
  evidence；相同 command idempotent。
- 每個 project 使用獨立 cross-process lock；latest promotion 使用 expected base + revision
  CAS，避免 lost update 與 lineage fork。
- Detail Scan 綁定 parent build、檢查 file fingerprint、產生 immutable child；Trace 綁定
  source build 但不建立或修改 artifact。

## TDD / BDD 步驟

1. 建立 TODO 並記錄 588 passed baseline。
2. 依 model → service → integration → web/E2E 順序，先寫 failing tests。
3. 實作 capability candidate、catalog、bridge，再跑 focused red-green-refactor。
4. 實作 profile models、validation、inference、readiness 與 10 sibling lifecycle。
5. 實作 snapshot、manifest、repositories、lock/CAS、Apply/read routes 與 restart recovery。
6. 接上 Detail child 與 Trace build binding。
7. 用 direct review 找 contract gaps，再各自補紅燈測試與 root fix。
8. 還原全部 frontend code/test 變更，改以後端 API/CLI 為 manual QA surface。
9. 執行 full pytest、Ruff、Mypy、lock check、live API lineage 與 CLI happy/bad paths。

## Review 發現的問題與解法

| 問題 | Runtime / test 證據 | 解法 |
|------|-----------------------|------|
| `create_app()` default state 曾使用 temporary directory | restart recovery red test | 改為 `${KAI_MIND_STATE_DIR:-~/.kai-mind}`，tests 自動隔離 |
| mapping decision 未反映 evidence review state | static artifact red test | 由 durable mapping decision 推導四種 review state |
| weak profile signal 缺少 unmapped/candidate/risk navigation refs | inference boundary red test | 保留 `undetermined`，只增加 read-only related refs |
| artifact publisher 中途失敗可能留下 sibling | failing writer integration test | 集中 cleanup 所有 public paths/temp files |
| state lock timeout 非 route-level 例外時可能變 500 | middleware BDD test | 全域穩定回 `503 project_state_busy` |
| persisted reload 後 map node order 漂移 | raw payload equality driver | JSON key sort + component slot deterministic sort |
| malformed typed ID 回 500 | live HTTP 四條路徑皆 500 | middleware 將 `InvalidStateIdError` 穩定映射為 `404 resource_not_found` |
| ID regex 接受 `project:..` / `project:a..b` | parameterized red test | validator 明確拒絕任何 `..` |
| v2 opt-in build restart 後被改成 requested v1 | manifest reload red test | manifest 保存 active/requested schema 與 migration warnings |
| Apply／Detail child 把 parent v2 selection 洗回 v1 | 兩條 HTTP red tests | child request 沿用 parent `requested_schema_version` |
| parent profile sidecar 缺失時 Detail child 把 unknown candidates 當空集合 | live/TestClient 原本回 200 | fail closed `409 profile_sidecar_unavailable`，latest 保持不變 |
| design doc history newest-first 與 03A E2E B1→B2 衝突 | context mining | 以具體 03A contract 為準，同步為 `generated_at ASC` |
| 同一已套用 project 再做 v2 manual QA 時 queue 為空 | live explicit rescan | 確認是 durable mappings 正常生效，改用 fresh fixture copy 驗證 v2 Apply |

## Debugging Runtime Audit

### Hypothesis 1：Apply 可能仍重新掃描 filesystem

- 結果：**refuted**。
- 證據：`test_second_build_reuses_snapshot_without_filesystem_scan` 使用 counting double；
  live trace 顯示 B1/B2 共用相同 `scan_id`，B2 有新 `build_id` 與 parent B1。

### Hypothesis 2：並發 Apply 可能造成 latest lost update 或兩個有效 child

- 結果：**refuted**。
- 證據：concurrent promotion / identical Apply tests 只允許一個 winner；live history 只有
  `[B1, B2]`，latest 指向 B2。

### Hypothesis 3：restart／reload 可能改變同一 build 的 payload metadata

- 結果：**confirmed，已修正**。
- 證據：先發現 deterministic map ordering drift，再發現 v2 requested schema 被硬編成 v1；
  修正後 raw reload equality regression、manifest reload、restart web test 與 live v2
  B1→B2→GET 均保持 v2 request metadata與 migration warnings。

## Direct Review Work Gate

| Review area | Verdict | 證據 |
|-------------|---------|------|
| Goal / constraints | PASS | backend scope完成；未使用 subagent；`frontend/` diff 為空 |
| Hands-on QA | PASS | live Scan→mapping→Apply→history/restart、malformed ID、v2 child、Detail 409、CLI |
| Code quality | PASS | modular services、Ruff scoped pass、Mypy pass、715 tests |
| Security / privacy | PASS | ID traversal、secret masking、safe 404/413/500/503、snapshot path/secret tests |
| Context mining | PASS | git history、Phase2 design、03A、Meeting Sync 與 cross-reference audit；修正 history doc drift |

因使用者明確禁止 subagent，本 gate 由主代理逐 lane 執行，不使用 review skill 原本的
multi-agent orchestration。

## 測試方式

```bash
.venv/bin/pytest -q
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
.venv/bin/mypy
.venv/bin/python -m uv lock --check

bash -n scripts/trace_apply_confirmations_build_lineage.sh
scripts/trace_apply_confirmations_build_lineage.sh \
  --start-server \
  --project-path tests/fixtures/rag_projects/basic_qdrant_ollama_rag \
  --output <temp-output>

.venv/bin/kai-mind map --help
.venv/bin/kai-mind map \
  tests/fixtures/rag_projects/basic_qdrant_ollama_rag \
  --output <temp-output> \
  --system-map-schema-version ai-system-map/v2
.venv/bin/kai-mind map /tmp/kai-mind-does-not-exist --output <temp-output>
```

## 測試結果

- Backend full suite：**715 passed**。
- Mypy：**Success: no issues found in 231 source files**。
- Backend Ruff：`ruff check src tests` **通過**。
- Lock：`uv lock --check` **通過**，55 packages。
- Live lineage：HTTP 200；B1/B2 同 `scan_id`、不同 `build_id`、parent/mapping ids/history
  全部正確。
- Restart：latest build 與 profile sidecar可用狀態成功恢復。
- Malformed typed IDs：GET/POST 四條路徑皆 `404 resource_not_found`。
- Live v2：initial、Apply child、build-by-id 都保持 `requested_schema_version=v2`。
- Missing profile + Detail：`409 profile_sidecar_unavailable`，latest 不變。
- CLI：help=0、valid v2 opt-in=0 並寫出 10 siblings、nonexistent path=1 且產生安全
  `map-error.md`。
- `git diff --check`：通過。
- Handoff samples：7 份 current backend JSON 通過 Pydantic validation；profile 為
  52 assessments / 15 profiles。

## 既有範圍外狀態

Bare `ruff check` 會遞迴掃入 `ref-opensource/`，目前回報 181 個既有 lint findings；另有
未修改的 `scripts/dev.py` 兩個 E501。這些檔案不在本次 backend diff，沒有為了製造全綠
而改動。正式 gate 使用本 repo production/test scope：`ruff check src tests`。

## 後續邊界

- Frontend Zod、store、proposal Apply button、degraded warning UI 未在本次交付；已還原。
- Plan 06 richer Graph projection / safe artifact refs 與 Plan 13 public v2 cutover 仍是後續計畫。
- Database adapter、multi-user auth、remote sync 不在 Phase2 local JSON staging scope。
