# Phase 12 — UA Sidecar and Adapter REP

Date: 2026-08-10
Plan: `16-implement-understand-anything-sidecar-service.md`

## 結果

- 建立 strict `systograph-ua-request/v1`、`systograph-ua-result/v1` models 與 checked-in
  JSON schemas；unknown fields、path escape、dangling evidence、invalid line ranges 均拒絕。
- `FileInventory` 補語言、分類與行數，但 selectable boundary 仍由 Step 2 決定。
- `UnderstandAnythingAnalysisService` 以固定 argv、`shell=False`、timeout 與系統暫存
  work-dir 直接編排三支 pinned UA scripts；不執行 `scan-project.mjs` 或 LLM analyzer。
- `sidecar/patches/compute-batches-workdir.patch` 與 `scripts/setup_ua_sidecar.sh` 提供
  install-time、pin-checked、idempotent patch；submodule source 不納入產品 diff。
- `UaStructuralAdapter` 將 sidecar structural payload 轉成 typed facts、Evidence 與
  ParseIssue；禁輸出 full source、raw prompts、secret-like values 與 absolute paths。
- Web 與 CLI 都從同一 approved `FileInventory` 建 snapshot；CLI 新增 non-interactive
  gate、durable `--state-dir` 與公開 help。Apply 重用 snapshot，不重跑 sidecar；Rescan
  取得新 snapshot。
- `UaParityService` 保存 legacy/current 與 UA 的 equivalent/missing/extra/conflict，並釘住
  `filesystem_scan=1`、`ua_sidecar=1`、`parity_providers=1`。

## 真實操作證據

- pinned UA commit：`73559a160645359c57be44c174935899dec9f9f2`
- real CLI 對 `basic_qdrant_ollama_rag` 與 `pgvector_openai_rag` 成功產生 v2 artifacts、
  snapshot 與 parity report。
- target fixture 掃描前後 digest 相同；temp work-dir 在成功與錯誤路徑都 cleanup。
- CLI/Web 同 fixture facts/evidence 等價；sidecar 缺失、schema invalid 與 inventory
  變更均 fail closed，沒有 partial successful build。

## 主要測試

- `tests/contracts/test_ua_analysis_schema.py`
- `tests/contracts/test_ua_sidecar_setup_contract.py`
- `tests/integration/test_understand_anything_sidecar_contract.py`
- `tests/integration/test_scan_snapshot_ua_pipeline.py`
- `tests/integration/test_scan_snapshot_ua_parity_pipeline.py`
- `tests/integration/test_cli_web_ua_pipeline_parity.py`
- `tests/integration/test_ua_parity_service.py`
- `tests/unit/core/test_ua_work_dir_lifecycle.py`

## 現況限制

legacy providers 目前仍是 active scan input，並非 parity-only；Plan 18 退役 gate 尚未
通過。UA 已進 active path，但不能把本階段誤寫成 legacy scanner 已刪除。
