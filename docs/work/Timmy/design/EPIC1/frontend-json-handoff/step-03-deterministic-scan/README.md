# Step 3 — 確定性掃描

Last updated: 2026-07-15（Phase A live-state correction）

## Current Phase A

Step 2 完成 boundary 後，current pipeline 由 Systograph deterministic TOML／config／filesystem
providers 產生 structural facts、evidence 與 issues。Backend 會保存
`snapshot.json`（`scan-snapshot/v1`）；它是 Apply replay 的內部輸入，不是 public artifact。

```text
Final FileInventory
  -> current Systograph deterministic providers
  -> ProjectScanResult
  -> ScanSnapshot S1
  -> Step 4～7 Build B1
```

Frontend 不直接讀 snapshot 或 raw facts，只讀 build／viewer API。Apply 重播 S1、建立 B2；
Rescan 才重新讀 repo、建立新的 scan 與 snapshot。

## Future Phase B

UA-primary `UnderstandAnythingAnalysisService` structural sidecar 是後續 Phase B；Plan 20
inventory selection 不呼叫 UA。Reserved nullable semantic sidecar、bounded LLM file analyzer 與
Plan 17 `AssessmentOrchestrator` 目前都不在 active path。

因此 frontend sample 不得新增 `ua-analysis-result`、`signal_origin`、numeric `confidence` 或
semantic candidate 欄位，也不得把 current Systograph 說成 parity-only fallback。
