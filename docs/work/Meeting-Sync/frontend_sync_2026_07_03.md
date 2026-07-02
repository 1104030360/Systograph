# KAI-Mind Frontend 交接:Viewer 穩定性修正批次(2026-07-03)

先抓住這批 PR 的主軸:

```text
這一批不是新功能,而是把 2026-07-02 前端盤點掃出的 Viewer 穩定性與誠實性問題收掉:
scan 流程狀態不會再卡住、request 會被正確取消、sample/mock 資料一律有明確標示。
```

全部六個 PR 都是 frontend-only、彼此獨立、base 為 `main`,
**刻意不碰 Timmy 調整中的 API contract**(`API_CONTRACT.md`、`/api/*` 契約、
`src/kai_mind/` 一律未動)。

## 1. 本批 PR 範圍

| PR | Branch | 內容 |
|---|---|---|
| #221 | `fix/scan-flow-state-reset` | scan 流程三個出口的狀態重置 + boundary modal Escape |
| #222 | `fix/178-viewer-payload-cancellation` | viewer payload request 取消(related #178) |
| #223 | `feat/176-sample-data-indicator` | graph 區域 Sample data 常駐標示(related #176) |
| #224 | `fix/scan-template-mock-affordances` | Scan Template 頁 sample 標示 + 停用無作用按鈕 |
| #225 | `fix/api-base-url-env-fallback` | `VITE_API_BASE_URL` 空字串 fallback |
| #226 | `fix/sse-reconnect-tolerance` | SSE 瞬斷容錯,連續 3 次失敗才降級 mock |

起源:2026-07-02 前端全面盤點(main `13a2bde` 當時的程式碼)、issue #176 / #178
的 objective,以及 `2026-06-12-frontend-ux-findings.md` 的 A-3 / B-1 findings。

## 2. 各 PR 解決什麼

### #221 scan 流程狀態重置

原問題:boundary review 按取消後,`isProgressRunning` 仍為 true,ProgressStrip
永久停在「Waiting for scan boundary review / 10%」,SSE 連線也不會關;
project import 失敗與 scan 錯誤路徑有同樣的洩漏。

修正後:

1. 取消 boundary review → progress 停止、strip 回到 idle、SSE 關閉。
2. import 失敗 / scan 錯誤 → progress 停止,錯誤事件保留在 strip 上可見。
3. BoundaryDecisionModal 支援 Escape 關閉(與 ProposalModal / DetailPanel 一致),
   submit 進行中忽略 Escape,避免誤觸放棄決策。

### #222 request 取消(related #178)

原問題:`useViewerPayload` 沒有把 React Query 提供的 `AbortSignal` 傳進
`fetchJson`,舊 request 在 unmount 或切換 base URL 後仍持續存活;
使用者取消也會被誤報成「Request timed out」。

修正後:

1. signal 從 queryFn 一路傳到 `fetch`;query key 變更或 consumer unmount 即取消。
2. 已取消的 request 不會 fallback 到 `/map` 第二個 endpoint。
3. 「Request was cancelled.」與「Request timed out...」訊息分離。

注意:#178 deliverable 中的 fake-timer regression tests 需要前端 test runner,
等 contract 穩定後與 #90/#91 一起處理,因此 issue 先不關。

### #223 Sample data 常駐標示(related #176)

Sample mode 時 graph 區域常駐顯示
`Sample data — example map, not a real scan` 徽章;API mode 不顯示。
徽章位於 docked progress strip 下方左側,不與 map key / canvas controls /
minimap / zoom hint 重疊,不隨互動淡出、不攔截滑鼠事件。

### #224 Scan Template 頁誠實化

原問題:整頁跑在 `scanTemplateApi` mock seam 上但無任何標示;
「New scan」按鈕沒有 onClick,看起來像壞掉。

修正後:頁面標題旁常駐「Sample data」徽章(tooltip 說明尚未接後端);
「New scan」改為 disabled,tooltip 引導改用 viewer 工具列的 Start scan。
文案集中於 `wording.ts`。Scan Template 的真實 selection API 落地後
(#208 之後由 #86/#123 承接)應一併移除。

### #225 env fallback

`VITE_API_BASE_URL` 為空字串時 `??` 不會 fallback,store 會拿到空 base URL。
改用 `||`,空值正確退回 `http://127.0.0.1:8000`。

### #226 SSE 瞬斷容錯

原問題:第一次 `onerror` 就永久關閉 EventSource 並降級 mock progress,
一次網路瞬斷就靜默失去真實進度。

修正後:交給瀏覽器內建的 EventSource 自動重連;連續 3 次錯誤
(期間無任何成功訊息)或 `readyState === CLOSED` 才降級並顯示警告。
收到任何成功訊息即歸零重算。

## 3. 資料安全與限制

- 全部變更維持 read-only viewer 行為,不修改 canonical map 或 scanner。
- 不新增任何 secret / evidence 的顯示途徑;#223/#224 反而降低把範例資料
  誤認為真實掃描結果的風險(evidence-first 原則)。
- 未修改 `API_CONTRACT.md` 與任何 request/response shape。

## 4. 主要修改檔案

- `frontend/src/App.tsx`(#221、#223)
- `frontend/src/components/BoundaryDecisionModal.tsx`(#221)
- `frontend/src/services/http.ts`、`frontend/src/services/viewerApi.ts`(#222)
- `frontend/src/hooks/useViewerPayload.ts`(#222)
- `frontend/src/hooks/useScanProgress.ts`(#226)
- `frontend/src/store/viewerStore.ts`(#225)
- `frontend/src/pages/ScanTemplatePage.tsx`、`frontend/src/wording.ts`(#224)
- `frontend/src/styles.css`、`frontend/src/styles/template-ui.css`(#223、#224)

## 5. 驗證結果

每個 PR 的每個 commit 都各自通過:

```powershell
corepack pnpm --dir frontend run lint    # 0 errors(1 個既有 Fast Refresh warning)
corepack pnpm --dir frontend run build   # tsc -b + vite build 通過
```

既有 build warnings(`web-worker` external、chunk > 500 kB)由 #187 追蹤,不變。
前端尚無 test runner,自動化 regression tests 待 contract 穩定後建立
(#90/#91;#176/#178/#226 各欠一項測試)。

## 6. 合併後的分支影響

- `codex/query-trace-ui-flow`(#218)、`feature/detail-scan-ui-flow`(#198)、
  `feature/mapping-proposal-confirm-reject`(#199)、
  `feature/219-viewer-artifact-actions`(#227)需要同步最新 main;
  其中 #227 與 #222 都動到 `http.ts`,#218/#198 與 #221/#223 都動到 `App.tsx`,
  同步時需解衝突。
- 建議後續合併順序維持:#198 →(rebase 後)#199 → #218 → #227。
