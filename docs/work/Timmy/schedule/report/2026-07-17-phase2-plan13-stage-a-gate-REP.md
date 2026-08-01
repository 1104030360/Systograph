# 2026-07-17 Phase 2 Plan 13 Stage A Gate Report

Status: **PASS — Plan 13 `ready` gate only**

## 範圍

本階段只修復 00A compatibility gate 與凍結 Plan 13 consumer census：

- native v1/v2 manifest restart reload 都先經唯一 `CanonicalMapLoader`。
- Viewer graph projection 消費 normalized `AiSystemMapV2`。
- 以獨立保存的 grounded v1/native-v2 fixtures 驗證 canonical facts 與 readiness 語意
  等價。
- 建立 unknown/new/stale direct legacy hit 會 fail closed 的 executable allowlist，涵蓋
  production Python、frontend runtime JSON/TS 與 operational scripts。

本階段沒有切換 normal v1 default、沒有移除
`MapBuildResult.normalized_ai_system_map`、沒有實作 operator rollback，也沒有開始 Plan 13
Task 1B / Tasks 2–7。

## 實作結果

1. `CanonicalMapLoadResult` 同時保存 typed source model、可選的 legacy source model 與
   normalized v2；v1 reconstruction 只發生在 loader 的 v1 validation path。
2. `ViewerSessionService.load_map()` 不再依 `active_schema_version` 分支，也不呼叫
   `RagSystemMap.model_validate()`；`build_loaded()` 一律把 normalized map 交給 graph
   projection。legacy v1 source 只用於相容 response/details。
3. `BuildManifestService.load()` 移除 loader 前的 v1-only validation，改為 loader-first；
   native v2 reload 的 `MapBuildResult.ai_system_map` 保持 `None`，不做 v2-to-v1 downgrade。
4. `grounded_rag_equivalent.v1.json` 與獨立 checked-in 的
   `grounded_rag_equivalent.v2.json` 比較 project semantics、components、edges、evidence、
   endpoints、risk hints、unmapped components、candidate facts，以及 readiness finding
   id/status/evidence refs；測試不在 runtime 由 adapter 產生 v2 fixture。
5. 新增 deterministic Python AST + frontend/script text census。每筆 allowlist 都有
   `path`、`symbol`、`classification`、`removal_plan`；unknown、新增、重複與 stale record
   都失敗。
6. `CanonicalMapLoader` 對非 object JSON root 回穩定 `CanonicalMapLoadError`；manifest
   將它包成 `BuildArtifactLoadError`。manifest active badge 與 artifact schema 不一致時，
   v1→v2 與 v2→v1 都 fail closed。
7. 抽離前先以 characterization 鎖定 v1 recommended-next-check 完整欄位與順序，再把四個
   legacy compatibility helpers 移到 no-I/O module；Viewer public methods 維持不變。

## TDD RED / GREEN 證據

### Native v2 manifest reload

RED：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider \
  tests/integration/test_build_manifest_service.py::test_native_v2_manifest_reloads_into_normalized_viewer -q
```

- Exit code：1；`1 failed in 0.28s`。
- 正確失敗原因：`BuildManifestService.load()` 先呼叫 v1-only validator，native v2 被包成
  `BuildArtifactLoadError("canonical map is invalid")`。

GREEN：同一 command exit 0，`1 passed in 0.33s`。

Final review 再增加 manifest scope assertion，先觀察 Viewer native-v2 source 的
`scan_id` 仍是 fixture scope、與 manifest scope 不一致（exit 1，`1 failed in 0.28s`）；
把 scoped normalization 收回 loader-owned `CanonicalMapLoadResult.with_normalized()` 後，
同一測試 exit 0，`1 passed in 0.28s`。Viewer source、normalized map 與 graph 現在共用
manifest `scan_id/build_id`。

### Paired grounded readiness equivalence

RED：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider \
  tests/integration/test_ai_system_map_v2_compatibility.py::test_fact_equivalent_v1_and_native_v2_have_identical_readiness -q
```

- Exit code：1；`1 failed in 0.16s`。
- 正確失敗原因：既有兩份 grounded fixtures 並非 facts-equivalent；`rag-grounding` 是
  `partial`/retriever evidence 對 `detected`/retriever+LLM evidence。
- 修正方式：新增獨立 grounded v1 fixture，對齊既有 native-v2 的 deterministic facts；
  沒有在測試內呼叫 adapter 產生 v2 fixture。

GREEN：同一 command exit 0，`1 passed in 0.14s`。

### Executable consumer allowlist

RED：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider \
  tests/contracts/test_v2_cutover_consumer_allowlist.py -q
```

- Exit code：1；`1 failed in 0.24s`。
- 正確失敗原因：空 allowlist 偵測到 47 個 unknown direct production/frontend hits。

GREEN：所有 hit 明確分類後，同一 command exit 0，`1 passed in 0.19s`。

### Final audit repair

初次 Stage A review 結果為 FAIL；以下四個 P1 與一個 refactor finding 全部先取得可辨識的
測試證據，再修到 GREEN：

- Paired fixtures：新增 canonical fact signature 後先得到 `1 failed`，差異包含 project
  root、API layer 與十個 placeholder components，證明舊 readiness-only assertion 是
  false green。改用獨立 checked-in v2 paired fixture 後，canonical facts + readiness
  `2 passed in 0.22s`。
- Census operational surfaces：把 frontend `.json` 與 `scripts/*.sh` 納入掃描後先得到
  `1 failed in 0.37s`，精準抓出 runtime JSON 的 v1 badge/legacy kind 與 trace script 的
  legacy kind。Viewer helper 抽離後 census 又主動抓出新 migration-only hit；最終 51 筆
  均有 owner/removal plan。
- Non-object root：array/null/string/number 在 loader unit 與 manifest integration 原先分別
  `4 failed`，因 `AttributeError` 逃逸；加入 boundary guard 後合計 `8 passed in 0.62s`。
- Badge mismatch：真實 v1 artifact/v2 badge 與 v2 artifact/v1 badge 原先 `2 failed`（未
  raise）；加入 manifest/loader schema 一致性檢查後兩方向都回穩定 typed error。
- Viewer refactor：抽離前 recommended-next-check characterization `1 passed in 0.25s`；抽離
  後 Viewer suite `12 passed in 0.49s`，Viewer 為 243 physical LOC、218 AST
  statement-span LOC，新 compatibility module 無 filesystem/network I/O。

## Consumer census

- Records：51
- `migrate`：35
- `migration_only`：15
- `remove`：1
- `operator_rollback`：0（Stage A 未實作 rollback，沒有虛構紀錄）
- Executable scope：`src/systograph/**/*.py` AST、`frontend/src/**/*.{ts,tsx,json}` text、
  `scripts/**/*.sh` operational text。
- Digest payload：依 allowlist tuple 順序，把四欄 record 轉成 sorted-key compact JSON。
- SHA-256：`34d9f531636bef94e67db32664063af014500eb8af832586cc46ce380f457e6f`

35 個 active hits 保持 `migrate`，只代表已知且有 owner/removal plan，不代表已退休。

## Regression 與 quality gates

Focused Stage A suite：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider \
  tests/contracts/test_v2_cutover_consumer_allowlist.py \
  tests/integration/test_ai_system_map_v2_compatibility.py \
  tests/integration/test_build_manifest_service.py \
  tests/unit/core/test_canonical_map_loader.py \
  tests/unit/core/test_viewer_session_service.py -q
```

結果：exit 0，`53 passed in 2.73s`。

完整 gates：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider -q
.venv/bin/ruff check src tests
.venv/bin/mypy src tests
```

- Backend：exit 0，`987 passed in 30.24s`。
- Ruff：exit 0，`All checks passed!`。
- Mypy：exit 0，`Success: no issues found in 297 source files`。

## Runtime reload probes

以真實 `BuildManifestService.load()`、真實 fixture 與 temporary artifact directory 驗證：

```text
ai-system-map/v1: reload=ok viewer=loaded scope=matched
ai-system-map/v2: reload=ok viewer=loaded scope=matched
schema-mismatch: v1-to-v2=rejected v2-to-v1=rejected
non-object-root: array/null/string/number=rejected
```

Final probe exit 0；使用真實 loader/manifest service、checked-in paired fixtures 與 temporary
artifact directory，沒有修改 target project。

## 文件同步

- 00A Task 4/5 依 executable evidence 改為完成。
- 2026-07-10 00A follow-up report 移除已解決的 normalized consumer/readiness risks，追加
  Stage A verification。
- Plan 13 Preconditions 與 Status 更新為 `ready`；Task 1B 與 Tasks 2–7 維持未完成。
- Stage A TODO 完成項改為 `[x]`，後續 cutover/migration/rollback 項目不變。

## 剩餘風險與交接邊界

- Normal producer default 仍為 `ai-system-map/v1`。
- `MapBuildResult` 仍有 v1 `ai_system_map` 與 v2 `normalized_ai_system_map` compatibility
  欄位；Stage A 未移除 public contract。
- `ViewerSessionService.build()`、publisher、producer、detail scan、query trace、API/UI 等
  direct legacy hits仍在 allowlist 的 `migrate` 類；Plan 13 後續必須逐一 RED/GREEN 遷移。
- Operator rollback、persisted mapping migration、extension write retirement 與 atomic
  visibility 尚未實作。
- 本次 compatibility/scanner 行為只讀 target project；report 不保存 evidence snippet、
  secret value 或本機 absolute path。

結論：00A Stage A gate 已有 executable evidence，可讓 Plan 13 進入 `ready` 並開始 Task 1B；
不能把 `ready` 解讀為 cutover 已完成。
