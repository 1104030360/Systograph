# 2026-06-14 Scan Template UI Polish Fixes Report

本文件用途是交接 `feat/scan-template-mapping-ui` 後續切出的前端 UI 修正分支狀態、已完成工作、驗證結果與下一步範圍。

目前工作分支：

- Base branch: `feat/scan-template-mapping-ui`
- Head branch: `codex/scan-template-ui-polish-fixes`
- PR: #137 `Polish scan template mapping UI copy and layout`
- URL: https://github.com/1104030360/Local-AI-Health-Doctor/pull/137
- PR 狀態：open
- 主要範圍：Scan Template / Mapping Proposal 前端介面、排版、文字與 lint/build hygiene

本次刻意不處理 Timmy backend / scanner correctness 類 issue，避免把前端 UI polish PR 變成跨層修正。

## 一、目前分支定位

`feat/scan-template-mapping-ui` 是 Scan Template mapping UI 的 mock-first prototype branch。

它目前主要提供：

- Scan Template page / template gallery / template detail。
- Project custom setup 與 built-in setup 的切換 UI。
- Mapping status tabs：confirmed / to review / skipped。
- Mapping proposal modal：候選建議、edit form、accept / reject / decide later flow。
- Mock service `scanTemplateApi` 與 typed mock data。

重要邊界：

- 目前 selection / proposal API 尚未接真實 backend。
- 前端仍從 typed mock data 讀取畫面狀態。
- 本 PR 不改 scanner core、不改 JSON report schema、不新增 backend contract。

## 二、這次 PR 完成的主軸

### 1. 修正 lint / build hygiene

已完成：

- 移除 `ScanTemplatePage` 未使用的 `systemDefault`。
- `scanTemplateApi` 的 mock-only `projectId` 參數改成明確保留但不觸發 unused error。
- `wording.tsx` 改為純 TS 模組 `wording.ts`，避免 Fast Refresh 對 exported copy constants 產生 warning。

### 2. Local AI 使用說明與名詞收斂

已完成：

- 新增 `Local AI setup` 說明區塊，放在 selected template summary 與 gallery 之間。
- 補充「Kai-Mind 在本機掃描專案」與「project setup 由已確認 matches 組成」的短說明。
- 將 `Standard setup` 收斂為 `Built-in setup`，避免使用者以為它是可編輯的標準流程。
- 將 `Best match` / `Best candidate` 改為 `Suggested match` / `Suggested first`，降低 AI 已確認完成的語氣。

### 3. Mapping Proposal modal 資訊層級整理

已完成：

- Modal title 改為 `Review suggestions`。
- Header 內合併：
  - review 狀態 tag
  - 待確認檔案
  - suggestion count
  - 使用者下一步動作說明
- 移除 loaded 狀態下重複的「best match is open below」status row。
- Loading / error / fallback 訊息改成中性文字，不顯示 provider/internal source badge。

### 4. Candidate card 降低內部實作曝光

已完成：

- 移除 candidate card 上的 source badge，因此畫面不再顯示：
  - `AI found it`
  - `Matched by a rule`
- 移除候選卡 verdict 後面的 internal slot tag，例如 `ui_account_view`。
- 保留使用者真正需要看的資訊：
  - suggested component name
  - rationale
  - evidence refs
  - accept / edit / reject actions

### 5. Mapping status table 排版修正

已完成：

- Confirmed table 移除 source 欄位，避免欄位過多與 source wording 干擾。
- `File we found` path 允許換行，避免長路徑把 table 撐破。
- 補上 table `colgroup` 欄位比例，降低欄寬差異過大的問題。
- Review action icon 從 `Sparkles` 改成較中性的 `Eye`。
- Mapping arrow 保留在 mapped-to cell，但欄位比例更穩定。

### 6. Icon / visual consistency

已完成：

- 移除 suggestion card 與 status row 中過度強調 AI 的 `Sparkles`。
- Review action 改成 `Eye`，更符合「查看 / review」行為。
- Local AI 說明區塊使用 `FileCode2`，和 page header 的 project context 保持一致。

## 三、主要修改區域

這次 PR 主要涵蓋：

- `frontend/src/pages/ScanTemplatePage.tsx`
- `frontend/src/components/proposal/CandidateCard.tsx`
- `frontend/src/components/proposal/ProposalModal.tsx`
- `frontend/src/components/scan-template/MappingStatusTables.tsx`
- `frontend/src/services/scanTemplateApi.ts`
- `frontend/src/styles/template-ui.css`
- `frontend/src/wording.ts`
- `docs/work/Bo-han/schedule/report/2026-06-14-scan-template-ui-polish-fixes-REP.md`

注意：

- `frontend/src/wording.tsx` 已改名為 `frontend/src/wording.ts`。
- 現有 import 都使用 extensionless `../wording` / `../../wording`，不需要逐一改 import path。

## 四、驗證方式

已執行：

```bash
cd frontend
corepack pnpm run lint
corepack pnpm run build
```

## 五、驗證結果

結果：

- `corepack pnpm run lint`：通過，0 errors，0 warnings。
- `corepack pnpm run build`：通過。

補充：

- 第一次 build 在 sandbox 內因 Windows filesystem access 被擋，升權重跑後通過。
- Build 仍有既有 Vite warning：
  - `web-worker` treated as external dependency。
  - bundle chunk 超過 500 kB。
- 以上 warning 不屬於本次 Scan Template UI polish 範圍，建議另開 build/performance cleanup。

## 六、目前未處理 / 不建議混入本 PR

這些項目目前不建議放進本 PR：

1. 真實 backend API integration
   - 目前 Scan Template selection / proposal 還是 mock-first。
   - 應等 backend contract 穩定後獨立開 integration PR。

2. Timmy backend / scanner correctness issue
   - 例如 scanner target resolution、secret masking、session persistence、proposal lifecycle 等。
   - 這些屬於 backend release-readiness correctness，不應混入前端 copy/layout PR。

3. Frontend automated tests
   - 本 PR 已跑 lint/build。
   - 若要補 Playwright / React Testing Library，建議獨立成 frontend regression test PR。

4. Bundle / Vite warning cleanup
   - `web-worker` external 與 large chunk warning 仍存在。
   - 建議獨立處理 code splitting / bundling。

5. A/B/C wording toggle cleanup
   - 目前仍保留 wording compare toggle，方便產品確認文案方向。
   - 等 copy direction 定案後，再獨立移除 unused copy sets 與 header toggle。

## 七、對應 issue 進度

這次 PR 對應先前建立的 Scan Template UI follow-up issues：

- #131 Local AI usage guide / glossary：部分完成，已新增 Local AI setup 說明。
- #132 Header layout / template naming：部分完成，已收斂 `Built-in setup` 命名與 header-adjacent copy。
- #133 Proposal modal header consolidation：已完成主要合併。
- #134 Best-match semantics / remove source badges：已完成主要文字與 badge 修正。
- #135 Mapping table layout / column widths / arrows：部分完成，已補欄寬與 path wrapping。
- #136 Icon consistency：部分完成，已移除主要 AI-style sparkle icon 並改用 review icon。

不建議在本 PR 自動關閉全部 issue，原因是部分項目仍需要產品或視覺驗收，例如 screenshot 區塊細節、完整 icon audit、A/B/C wording 最終定案。

## 八、下一步建議

建議 PR review 時重點看：

- `Built-in setup` 是否就是想取代 `Standard setup` 的最終命名。
- Local AI setup 說明是否需要中文化或更偏產品語氣。
- Proposal modal 的「suggested first」是否足夠清楚，不會被誤讀成 AI BEST Match。
- Confirmed / To review / Skipped tables 在實際資料量下是否仍需要更細欄位調整。

PR merge 後，建議下一支 frontend branch 處理：

```text
branch: scan-template-ui-visual-pass
scope: screenshot area layout, final wording decision, full icon audit, mobile visual QA
```

backend/API integration 請另開：

```text
branch: scan-template-api-integration
scope: replace mock scanTemplateApi with real selection/proposal endpoints
```
