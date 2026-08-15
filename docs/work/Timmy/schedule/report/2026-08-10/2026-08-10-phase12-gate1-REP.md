# 2026-08-10 Phase 12 Gate-1 Closure — REP

- Gate source：`static-trace-plan/README.md:425`
- Baseline HEAD：`da0d402e931a4b286022f6581f41e78342214351`
- Scope：TOML-primary initial build、inventory review、snapshot／Apply replay、
  static execution publish 與 Viewer
- Verdict：**GO**；Plan 16 由 blocked 轉為 in progress

## 驗收結論

Gate-1 不是以 baseline 綠燈代替。執行真實 CLI 後先發現四個 P0 static JSON
缺少 `trace_kind`／`runtime_verified`，因此第一次判定 NO-GO；補上 required
literal contract 與 producer 後重跑 CLI、E2E 與 Viewer，才轉為 GO。

| Gate | 實證 | 結果 |
|---|---|---|
| B1 Step 1～7 | fixture initial build 產出 canonical map、profile、readiness 與 sibling artifacts | PASS |
| Inventory | Viewer preflight 顯示 7 included、0 needs-review／blocked；同一 final inventory 進 scan | PASS |
| Read-only | CLI 掃描前後 fixture 全檔 SHA-256 清單無 diff | PASS |
| Snapshot | initial snapshot `ua_analysis_result=None` 可持久化並建置 | PASS |
| Apply B1→B2 | snapshot replay、bridge／overlay、lineage 與 no-rescan tests 通過 | PASS |
| Static artifacts | call graph、dataflow hints、execution paths、evidence table 明示 static inferred／非 runtime proof | PASS |
| Viewer | 真實 import → preflight → scan → latest build；61 nodes／1 edge，可切 Data Flow 並開 Retriever details | PASS |
| Browser logs | 操作後 warning/error console 為空 | PASS |

## TDD 修復紀錄

### RED

真實 `systograph map` 產物的四個 static JSON 沒有
`trace_kind=static_inferred` 與 `runtime_verified=false`。新增 required-field
contract 後先得到：

- producer dump：`1 failed, 8 passed`
- 四類 artifact 缺欄位／錯誤 runtime claim：`4 failed, 9 passed`

### GREEN

- focused artifact contract：`13 passed`
- static producer／publisher／build／artifact route regression：`49 passed`
- 主代理重跑 execution artifact＋build＋route：`37 passed`
- Ruff、Mypy、`git diff --check`：通過

## Gate-1 回歸命令

```bash
.venv/bin/python -m pytest -q \
  tests/e2e/test_apply_confirmations_build_lineage.py \
  tests/e2e/test_inventory_selection_scan_flow.py \
  tests/integration/test_build_manifest_service.py \
  tests/integration/test_map_build_service.py \
  tests/integration/test_scan_snapshot_materialization.py \
  tests/web/test_inventory_preflight_routes.py \
  tests/web/test_map_build_apply_routes.py \
  tests/web/test_map_build_artifact_routes.py \
  tests/web/test_project_scan_routes.py \
  tests/web/test_trace_build_binding.py \
  tests/web/test_detail_scan_build_binding.py
```

結果：`94 passed in 13.90s`。

真實 CLI 使用 `basic_qdrant_ollama_rag`，輸出九個 P0 檔案；以 `jq -e`
逐一驗證四個 scoped static JSON 的固定 metadata，並以掃描前後 SHA-256 清單
`diff -u` 證明 target fixture 未被修改。

## Viewer 手動 QA

1. 啟動 FastAPI 與 Vite。
2. 在 API source control 輸入 fixture 絕對路徑並按 Start scan。
3. 確認 preflight：Included 7，其餘所有待決／blocked／missing 計數皆 0。
4. Confirm and start scan 後，latest build 顯示 61 nodes、1 edge、1 build。
5. 切換 Data Flow lens，確認 Retriever node 可見；點選後 Details 顯示
   detected／enabled、type `retriever`、component `retriever:retriever`。
6. 瀏覽器 warning/error log：`[]`。

## 範圍邊界

- Gate-1 不含 reject／skip decision persistence，依 README 裁定屬 Plan 01 Task 8。
- 本 gate 只證明 TOML-primary／nullable-UA 的 Phase A；不代表 UA sidecar 或 parity
  已完成。
- 所有 static artifacts 明確不是 runtime proof。
