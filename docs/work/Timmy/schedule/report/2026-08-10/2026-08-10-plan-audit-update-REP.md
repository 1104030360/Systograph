# 2026-08-10 計畫查核更新（Stage 1）REP

- 對應 TODO：`docs/work/Timmy/schedule/todo/2026-08-10-build-scoped-report-download-TODO.md`
- 分支：`main`（本輪依指示**不 commit**，全部改動留在 working tree）
- 範圍：後端主計畫
  `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/download.md`
  ＋前端計畫
  `docs/work/Meeting-Sync/meeting_sync_2026_08_10/frontend-build-scoped-report-download.md`

## 實作邏輯

兩份計畫都是 2026-08-10 起草、方向正確，但計畫是後續實作 subagent 的唯一
需求來源，任何遺漏的受影響檔案都會直接變成實作破洞。因此先由主 agent 對
程式碼做一輪引用面掃描（rg + 逐檔讀），把「刪掉舊端點後會爆的東西」全部
找出來回填進計畫，確保實作階段照著計畫走就不會踩雷。

## 步驟

1. 主 agent 掃描 `/api/map/report`、`latest_build_result`、`map_routes`
   在 repo 的全部引用點，對照計畫的檔案清單找缺口。
2. 派 1 個 Opus subagent 依查核結果修訂兩份計畫（只回填缺口、不改決策、
   不動 checkbox 與 Status）。
3. Opus reviewer 逐條驗證每個新增引用的 file:line；發現的問題進 fix
   round，再由 scoped re-review 確認全數解決。

## 回填的缺口

| 缺口 | 內容 |
|---|---|
| G1 | `tests/unit/core/test_query_trace_boundaries.py` import `map_routes`——刪檔會直接 ImportError，計畫 Task 3 補「改綁 `map_build_routes`」步驟 |
| G2 | `docs/MODEL-CONTRACT.md:165` 仍引用舊端點——Task 4 補上 |
| G3 | session_store 清理範圍寫窄了：`_latest_build_result` 在**兩個** store 都會變 write-only 死欄位；`PersistentSessionStore.save_build_result` 會變 no-op 但**方法必須保留**（Protocol 契約仍被呼叫） |
| G4 | `tests/web/test_retired_endpoints.py` 是 #277 退役 404 斷言的家——Task 3 補比照樣式新增 |
| G5 | `test_map_routes.py` 內兩支無關測試（CORS、SSE）必須搬家留存，不得隨檔案刪除流失 |
| G6 | `trace_map_report.sh` 退役後名稱失真——決策改為更名 `trace_map_build_artifact.sh` |
| G7 | 計畫 §10 引用清單補齊（boundary test、docs 引用） |

## 遇到的問題與解法

1. **主 agent 的查核也有錯**：brief 把前端 `activeBuildId` 標在
   `types.ts:266`，實作 subagent 驗證後發現該行其實是
   `viewer_load_result.build_id`（nullable），`activeBuildId` 在
   `store/viewerStore.ts:10`——已依實況修正計畫引用（兩個來源都列）。
2. **Reviewer 抓到計畫自相矛盾**：G4 新增的退役測試常數必然含
   `/api/map/report` 字串，與 §6 驗收「repo 內已無任何引用」衝突——
   fix round 以 carve-out 子句解決（退役常數與 `docs/work/**` 歷史紀錄
   不在此列）。
3. 兩處既有行號漂移（`§5/§7` 交叉引用、`session_store.py:160-174`
   範圍）一併修正。

## 測試方式與結果

文件任務無程式測試；驗證方式為 reviewer 逐條 rg/Read 實測每個 file:line
引用（含 §10 引用清單與 repo 全域掃描比對，結論「exactly complete」），
fix round 後 scoped re-review 確認 3/3 findings addressed、Status 仍為
`planned`、checkbox 全未勾。
