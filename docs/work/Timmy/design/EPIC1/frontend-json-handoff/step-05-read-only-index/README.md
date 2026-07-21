# Step 5 — 唯讀索引

Last updated: 2026-07-15（current backend implementation）

`SystemMapIndex` 已在 backend 實作。它只索引 normalized `AiSystemMapV2` 的 components、
edges、evidence、endpoints、risk hints、unmapped components 與 candidate facts，提供穩定的
read-only lookup 給 profile、projection、detail 與 mapping consumers。

本步不寫檔、不修改 canonical map，也不暴露 frontend API，因此沒有 handoff sample。
Frontend 消費的是 Step 6／7 由 backend 推導的結果，不得在 browser 重建第二份 index。
