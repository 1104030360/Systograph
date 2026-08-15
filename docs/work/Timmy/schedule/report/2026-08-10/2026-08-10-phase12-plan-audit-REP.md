# 2026-08-10 Phase 12 計畫與契約稽核 — REP

- 對應 TODO：`docs/work/Timmy/schedule/todo/2026-08-10-phase12-ua-sidecar-integration-TODO.md`
- 稽核基準：HEAD `da0d402e931a4b286022f6581f41e78342214351`
- UA pin：`73559a160645359c57be44c174935899dec9f9f2`
- 範圍：16、16A～16H；驅動 prompt 的不存在 16G 名稱已正規化為 canonical
  `16G-retire-template-flow-derivation.md`

## 實作邏輯

先把計畫當成後續 TDD 的 executable contract，逐項與 live models、services、CLI、
Viewer projection、fixtures 及 pinned UA 原始碼對照。任何會讓未觀察事實升級、讓
backend 丟失狀態、或讓合法空輸入被誤判失敗的舊敘述，先修正計畫再碰 production code。

## 步驟

1. 主 agent 讀取 AGENTS、工程 prompt、TDD／subagent execution skills、s2 README、
   CLARIFICATIONS、accepted boundary 與九份計畫全文。
2. 建立隔離 worktree `codex/phase12-ua-sidecar`，確認原始工作樹不受改動；初始化 UA
   submodule 並核對 pin、Node/pnpm runtime 與 upstream 三支 script。
3. 三位 read-only subagent 分別稽核 plan、backend、frontend/contract；主 agent
   逐條回到 live source 驗證並整合。
4. 依使用者指定順序逐一更新九份 canonical 計畫；每一份修改後各自執行
   `git diff --check`，全部完成前沒有修改 production code。

## 更新結果

| 計畫 | 本輪校正 |
|---|---|
| 16 | Gate-1 仍 blocked；FileRecord/CLI owner、typed payload、UA patch safety、G3 import-only |
| 16A | canonical status 不等於 Viewer status；backend projection 必改、frontend 維持空 diff |
| 16B | pin/runtime/live UA I/O 重驗；合法零邊不等於 sidecar failure |
| 16C | typed structural facts；semantic relationship discriminant；merge key 改三元組；stable cap sort |
| 16D | GraphEdgeModel/ArtifactEdge 保存 status/reason；零 profile 改善可誠實通過 |
| 16E | G2 current target 統一為 deterministic inference；G3 import-only 固定 indirect |
| 16F | 主清單 N1～N8；補 typed payload 與 Viewer/static projection；owner/path 校正 |
| canonical 16G | 修不存在檔名；edge-bearing/empty fixture gate 分流；delegated sign-off 綁 SHA/report |
| 16H | topology facts 與 component facts 分流；G3 假陽性反向契約；symbol 不湊滿 13 筆 |

## 遇到的問題與解法

1. **Gate-1 沒有可重現完成證據**：完整 baseline 綠仍不能替代 Viewer/E2E/manual
   acceptance。Plan 16 保持 blocked，執行順序改為先做唯一 ungated 的 16H。
2. **未使用 import 會假 detected**：現行 bridge 依 `(rule_id, kind)` 建 component，
   canonical evidence 又會把 file+line 升 direct。解法是新增 typed structural fact
   channel；G3 不進 bridge，evidence 明設 indirect。
3. **Viewer/backend contract 丟 status**：frontend schema 接受 optional status，但
   backend model/projection 未提供。16D 擴充 backend/static contract，frontend production
   code 仍不在本階段修改。
4. **16C payload 與 relationship 未定型**：不再解析自由字串；以 discriminated union
   承載 call/import/symbol/factory。relationship 需完整 semantic discriminant，避免
   `(from_kind,to_kind)` 把不同語意壓成一條。
5. **16G 對所有 fixture 要求 >0 與空 repo gate 衝突**：edge-bearing fixture 才要求
   L1+L2 >0；空/config-only/malformed 的正確 topology edge 數是 0。
6. **驅動 prompt 引用不存在 16G**：不做相容 alias；以 canonical 16G 退役計畫執行，
   新模組 overview 仍由 16F 負責。

## 測試方式與結果

- Python baseline：`.venv/bin/python -m pytest -q` → `1146 passed, 1 skipped`
- Frontend baseline：`pnpm test` → `38 files, 199 tests passed`
- Frontend production build：subagent 實測成功（僅既有 web-worker warning；最終 gate
  仍由主 agent重跑）
- 文件：九份逐檔 `git diff --check`，以及總體 `git diff --check` → 通過
- UA pin/runtime：submodule HEAD `73559a160645...`、Node `v22.22.3`、pnpm `10.22.0`

本階段只修改計畫、TODO 與本報告，尚未修改 production code 或 tests。
