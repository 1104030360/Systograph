# Step 2 — 掃描邊界 Gate

Last updated: 2026-07-07（UA 整合決策對齊）

僅 `POST /api/scans` API；blocked 時不產生 artifact。無 handoff sample。

Step 2 是 KAI-Mind 的唯一掃描邊界 owner。Boundary complete 後，backend 會在
FileInventory 上補 UA 需要的 enrichment：language、`fileCategory`、行數等 metadata
（移植自 Understand-Anything `scan-project` 的有用邏輯，但不讓 UA 自行決定掃描範圍）。
這些 metadata 只供 Step 3 UA sidecar request 使用，不新增 frontend payload 欄位。
