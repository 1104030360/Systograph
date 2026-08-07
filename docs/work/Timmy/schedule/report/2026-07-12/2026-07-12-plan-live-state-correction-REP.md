# Plan 05–09 Live-state Correction Report

## 範圍與結果

逐檔校正 Plan 05–09，使內容符合目前 `CanonicalMapLoader`、normalized v2、profile
inference、readiness、build lineage 與既有 v1 compatibility 的真實狀態。依 2026-07-12
最新分工，本次交付已收斂為 backend-only，`frontend/` 不含本輪變更。

## 實作邏輯

- 先以 live code、tests 與 contract 文件判定既有能力，不把已完成的 Step 6/profile
  sidecars 重列為待辦。
- 將執行順序固定為 `05 -> 06A -> 07 -> 06B -> 08 -> 09`。
- 將 normalized read-only lookup、projection、v1 mutation compatibility 與 cleanup owner
  分開，避免 index 吸收 validation/inference/persistence。
- Plan 06 的完成 gate 改為 backend JSON/Mermaid/Markdown、CLI/API 與 sidecar degraded
  behavior；frontend integration 留給 frontend owner。

## 步驟

1. 校正 Plan 05 的七組 canonical lookup 與 validator boundary。
2. 校正 Plan 06 的 single projection owner、semantic overlay 與 renderer ownership。
3. 校正 Plan 07 的 grouping/direction/location 擴充契約。
4. 校正 Plan 08 的 canonical read-only migration 與 v1 child-map mutation seam。
5. 校正 Plan 09 的 remove/keep ownership inventory。
6. 依最新分工撤回所有 frontend tracked/untracked changes，並更新 Plan 06/TODO。

## 測試方式

- `git diff --check`
- `git diff --exit-code -- frontend`
- 逐檔搜尋 stale schema branch、legacy extension overclaim 與 frontend completion gate。

## 遇到的問題與解法

- 問題：2026-07-11 草案把 frontend implementation 列為 Plan 06 完成條件。
- 解法：依 backend owner分工新增 2026-07-12 scope correction，保留 additive backend
  handoff contract，但移除本次 pnpm/browser/frontend gate。

## 測試結果

- `frontend/` 相對 HEAD 無 tracked 或 untracked 差異。
- `git diff --check` 通過。
- 五份 plan 已與 backend-only execution boundary 對齊並在原路徑標示完成。
- 未搬入 flat `plan/finish`：該目錄已有同名 05–09，搬移會造成 filename collision並
  破壞 phase2 relative links；TODO已記錄此 repo結構限制。
