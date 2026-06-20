# KAI-Mind 前端交接文件（2026-06-20）

這份文件是給 `codex/toolbar-sidebar-density-draft` 開 PR 前 review 用的版本。

先抓住這次 PR 的主軸：

```text
這支 branch 不是新增後端功能，而是把 Scan Template 與主 Viewer 的前端介面收斂到比較能 review 的狀態。
```

## 1. 目前分支狀態

目前工作分支：

- Base branch: `main`
- Head branch: `codex/toolbar-sidebar-density-draft`
- PR: #186 `Polish viewer density and scan template UI`
- URL: https://github.com/1104030360/Local-AI-Health-Doctor/pull/186
- PR 狀態：open，等待 review / merge 確認
- 主要範圍：主 Viewer toolbar/sidebar density、Scan Template header/workflow/copy、Map key、scan status、proposal wording

目前分支已 push 到遠端：

```text
origin/codex/toolbar-sidebar-density-draft
```

注意：

- 這支 branch 已 rebase 到最新 `origin/main`。
- rebase 後的 base commit 是 `f826f0b`，已包含 #183、#184 的 docs cleanup。
- merge 前請先完成 PR review，不建議未看畫面就直接 merge。

## 2. 這次 PR 想解決什麼

原本 Scan Template 與主 Viewer 有幾個前端 review 風險：

1. Toolbar 一次塞太多資訊，project / setup / source / controls 混在同一層。
2. Sidebar 的 scan summary、highlight、scan depth、legend 視覺重量偏高。
3. Scan Template header 有多版切換草稿，方向尚未收斂。
4. Mapping Proposal 與 template wording 有些語氣太像「AI 已經判定完成」。
5. Map key / minimap / progress strip 在 graph 操作時會干擾主互動區。

這支 branch 的目標是把這些 UI polish 收斂成一版，讓後續 PR review 不需要再同時比較 A/B/C 草稿。

## 3. 目前已完成的前端調整

### 主 Viewer toolbar

已完成：

1. 將 project 資訊收斂成 hover popover，不再把所有 detail 常駐顯示在 toolbar。
2. Source control 改成較 compact 的操作區，降低 toolbar 擁擠感。
3. reset / theme / chat 等次要操作收進更多選單。
4. `Nodes` / `Edges` 開頭改為大寫。
5. 移除 Query replay 下方重複的 `coarse_replay` subtitle。

Review 重點：

- Toolbar 現在比較適合 demo，但需要實際點看看 hover popover 是否夠直覺。
- 如果 reviewer 覺得 source menu 還是太隱晦，後續可以另外拉一支 toolbar IA branch。

### Sidebar density

已完成：

1. `Scan summary` 移除多餘的 `rag` 顯示。
2. Sidebar 的 Legend 移出，不再放在側欄當作固定區塊。
3. `Scan depth` 改成可收折，降低資訊量。
4. 保留 View filters 作為真正會影響畫面的控制。

Review 重點：

- Sidebar 現在比較像狀態與 filter 區，不再混放 map legend。
- 若後續要做 mobile / narrow layout，sidebar 還需要再獨立驗收。

### Graph interaction area

已完成：

1. Map key 移到 graph 左下角。
2. Map key 平常半透明，hover 才完整顯示。
3. 使用者拖曳 / pan graph 時，Map key 不會因 hover 被喚醒。
4. Minimap 也改成平常半透明，拖曳 / pan 時降低干擾。
5. Zoom controls 往上保留間距，避免被 Map key 覆蓋。
6. 移除 `drag to pan` 文字，只保留 zoom percentage。

Map key label 已收斂成：

```text
Detected
Confirmed
Risk
Review
Missing
```

Review 重點：

- Map key 現在比較像畫布輔助資訊，不像 sidebar 裡的操作選單。
- 需要看實際畫面確認左下角是否會遮到節點或 data source panel。

### Scan status / progress strip

已完成：

1. `Scan idle — showing committed map` 預設收起。
2. 只留一個左右方向的箭頭按鈕，點擊後展開 / 收回。
3. running / error 狀態仍會顯示主要資訊。
4. Partial 狀態點點加入重複擴散淡化動畫。
5. 動畫有 `prefers-reduced-motion` 保護。

Review 重點：

- Idle 狀態不再搶畫面注意力。
- Partial 動畫是輕量提示，不應該讓使用者以為正在執行完整 scan。

## 4. Scan Template 這次收斂的內容

### Header / workflow

已完成：

1. 移除 Scan Template Header A/B/C 切換。
2. 只保留使用者選定的 C 版本。
3. `Project > Setup > Review` 做成可互動流程按鈕。
4. `Project` 可以回主 Viewer。
5. `Setup` 可以回 template gallery / setup 層。
6. `Review` 只在 review/build 狀態顯示 active，不允許從 setup 層直接跳到未知 node 的 review。

這個互動限制是刻意的：

```text
Review 需要知道是哪一個 node / file 的 review，所以不能在 Setup 層直接跳過去。
```

### 說明文字

已完成：

1. 移除 Wording Style A/B/C 切換。
2. 保留最後建議版文字。
3. 將 Scan Template 說明改放到頁面底部固定資訊卡。
4. 底部資訊卡固定置中，不跟著內容高度改位置。
5. 資訊卡會依目前頁面顯示不同說明：
   - gallery
   - built-in template detail
   - project template detail
   - build / review flow

目前主說明方向：

```text
A scan template tells Kai-Mind how to name detected files.
The project template keeps confirmed matches for future scans.
```

Review 重點：

- 這版文案比原本短，但仍保留「template 會影響 future scans」這個必要概念。
- 若要再更白話，建議下一輪只微調底部資訊卡，不要再恢復多版切換。

### Template detail / mapping progress

已完成：

1. Project template header 減少常駐說明文字。
2. 移除 `Mapping progress` 標題文字，讓 tabs/table 成為主要內容。
3. Pending review modal 移除冗長說明：

```text
Kai-Mind found 3 mapping suggestions for this file...
```

4. `AI found it` / `Matched by a rule` 等過度內部來源感的 badge 已移除或降調。
5. Best match 語氣收斂為 suggested mapping / suggested first。

Review 重點：

- 這支 PR 不處理 Evidence code preview。
- Evidence 能不能連到原始碼區塊已另開 issue #185，建議放到前後端串接 branch。

## 5. 主要修改區域

這次 PR 主要涵蓋：

- `frontend/src/App.tsx`
- `frontend/src/components/DataSourceControl.tsx`
- `frontend/src/components/ProgressStrip.tsx`
- `frontend/src/components/ReplayTimeline.tsx`
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/components/SystemGraph.tsx`
- `frontend/src/components/proposal/ProposalModal.tsx`
- `frontend/src/components/scan-template/TemplateDetail.tsx`
- `frontend/src/pages/ScanTemplatePage.tsx`
- `frontend/src/styles.css`
- `frontend/src/styles/template-ui.css`
- `frontend/src/wording.ts`

這支 branch 也包含前一段 Scan Template mapping UI work 的檔案，例如：

- `frontend/src/components/proposal/CandidateCard.tsx`
- `frontend/src/components/proposal/EditForm.tsx`
- `frontend/src/components/scan-template/MappingStatusTables.tsx`
- `frontend/src/components/scan-template/TemplateGallery.tsx`
- `frontend/src/data/scanTemplate.mock.ts`
- `frontend/src/services/scanTemplateApi.ts`

## 6. 驗證狀態

最近一次在這支 branch 提交前已執行：

```bash
corepack pnpm run lint
corepack pnpm run build
```

結果：

- `lint`：通過。
- `build`：通過。

補充：

- Build 仍有既有 Vite warning：
  - `web-worker` treated as external dependency。
  - bundle chunk 超過 500 kB。
- 以上 warning 不屬於本次 UI polish scope。
- 依目前協作規則，正式開 PR / merge 前再跑一次 lint/build。

## 7. 目前不建議混入本 PR 的事

這些項目建議不要在本 PR 裡處理：

1. 真實 backend API integration
   - 目前 Scan Template selection / proposal 仍偏 mock-first。
   - 應放在前後端串接 branch。

2. Evidence code preview / source link
   - 已開 issue #185。
   - 需要後端或資料合約確認 evidence refs 如何映射到安全可展示的 code range。

3. Timmy Fable 5 backend/security findings
   - 這些多半是 backend release-readiness / scanner correctness 問題。
   - 不應混入前端 UI polish PR。

4. Bundle / Vite warning cleanup
   - `web-worker` external 與 large chunk warning 建議另開 build/performance cleanup。

5. 大型 responsive redesign
   - 目前只做 desktop / current layout 的密度收斂。
   - mobile 或 narrow viewport 建議獨立驗收。

## 8. 開 PR 前建議步驟

目前已完成：

```text
1. 已同步最新 origin/main
2. 已確認 #183 / #184 docs cleanup 不會造成衝突
3. 已跑 lint
4. 已跑 build
5. 已開 PR 到 main：#186
```

接下來建議：

```text
1. 先看 PR diff 與實際畫面
2. 確認 UI / wording / scope 沒有要再改
3. 確認後再 merge
```

## 9. Review 時建議看的地方

建議 reviewer 優先看：

1. 主 Viewer toolbar 是否真的比原本清爽。
2. Project hover popover 是否足夠可發現。
3. Sidebar 收折後是否還保留必要資訊。
4. Map key / minimap 半透明策略是否干擾或幫助 graph 操作。
5. Scan status 收起後，使用者是否仍能理解目前狀態。
6. Scan Template header C 版本是否可作為最終方向。
7. 底部資訊卡的 wording 是否夠短、但沒有失去必要前提。
8. Pending review / proposal wording 是否避免過度宣稱 AI certainty。

## 10. 參考來源

- `docs/work/Meeting-Sync/frontend_sync_2026_06_12.md`
- `docs/work/Bo-han/schedule/2026-06-14-scan-template-ui-polish-fixes-REP.md`
- `frontend/src/App.tsx`
- `frontend/src/components/ProgressStrip.tsx`
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/components/SystemGraph.tsx`
- `frontend/src/pages/ScanTemplatePage.tsx`
- `frontend/src/styles.css`
- `frontend/src/styles/template-ui.css`
- `frontend/src/wording.ts`
- GitHub issue #185：Evidence code preview / source link follow-up
