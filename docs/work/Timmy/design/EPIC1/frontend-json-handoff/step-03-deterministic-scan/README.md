# Step 3 — 確定性掃描

Last updated: 2026-07-07（UA 整合決策對齊）

Backend 會持久化 `snapshot.json`（`scan-snapshot/v1`，Plan 03A），內含 raw
`ProjectScanResult` 與 snapshot internal UA sidecar。

**Frontend 不使用此檔。** Viewer 與 handoff mock 從 Step 4 起的 build artifacts / API 載入即可。

2026-07-07 決策後，Step 3 掃描來源為 UA-primary：

```text
Step 2 allowlisted inventory
  -> UnderstandAnythingAnalysisService
       extract-import-map
       -> compute-batches
       -> extract-structure
       -> file-analyzer（bounded LLM）deferred；不執行
       -> ua-analysis-result.json nullable deferred sidecar
  -> Structural Adapter：structural facts → facts / evidence / issues
  -> semantic → reserved nullable internal sidecar（Phase2 不產生、不消費）
```

`ua-analysis-result.json` 不是 public artifact，也不是 frontend JSON handoff sample。Phase2 active
path 不產生也不消費它；Frontend 不得依賴它的欄位；semantic candidate、`signal_origin`、
`confidence` 等資訊不進入 sample schema。

過渡期 KAI scan TOML providers 仍可並跑做 parity gate；Plan 14 驗證通過後退役主掃描路徑。
UA sidecar 失敗採 fail-closed：不進 Step 4，frontend 只會透過既有 build error contract
感知失敗。
