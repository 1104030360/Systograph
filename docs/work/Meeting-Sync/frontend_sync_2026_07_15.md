# KAI-Mind Frontend Sync：Phase2 十層架構 Viewer 與互動收尾（2026-07-15）

本文件對應 `codex/phase2-plan06-contract` 對 `main` 的 frontend PR。

```text
目標：以 backend GraphViewModel / build-scoped payload 驅動十層 AI Agent System 架構 Viewer，
取代舊白板式主畫面，並完成 Filter Views、Node Inspector、Readiness、狀態資訊與連線互動。
範圍：frontend + docs；不修改 src/kai_mind/ backend contract 或 scanner 行為。
```

## 1. PR scope

### Backend contract 與 immutable build

- 新增 Phase2 viewer contract adapter，支援 target sample、legacy `/api/map` 與 build-scoped response。
- API mode 優先讀取 project latest build，並支援 immutable build history 切換。
- Mapping completeness、plane/lens membership、assessment、activation、readiness、evidence、risk hints 與 lineage 均使用 backend payload；缺少欄位時顯示 unavailable，不在瀏覽器推論。

### 十層 AI Agent System Viewer

- 主畫面改為固定十層 architecture planes：Input & Intent、Control、Ingestion & Indexing、Retrieval、Extension Subsystems、Evidence、Generation、Memory & State、Governance & Observability、Deployment Topology。
- Reference capabilities、repo components、profile attachments 與 unassigned components 依 backend `plane_id` 投影。
- Backend-declared edges 與 projection relationships 會在 Overview / Filter Views 中依 membership 顯示或淡化；nodes 位於連線上層，planes 保持半透明遮罩。
- DeepResearch icon language 已集中至單一 registry，包含 brand、lens 與 plane icons。

### Filter、Inspector 與輔助資訊

- 左側 Filter 保留 16 個 backend-aware views；未具 contract metadata 的 Runtime、Variants、Reasoning Mode 維持 disabled 並提供原因。
- Assessment 與 node/edge 圖樣 legend 移到 Filter 底部；在 1280×720 實測所有 Filter（含 Risk Lens）完整顯示且沒有內部捲軸。
- Backend-declared flows 預設收斂為白板左下方半透明箭頭，點擊後向右展開，最多顯示目前 view 的前 12 條 edges。
- Node Inspector 精簡標頭與寬度，修正水平 overflow，並保留 Overview、L2 Component、L3 Code Path 等 backend facts。
- Mapping completeness 狀態列固定於 viewport 底部，顯示 normalized nodes、declared edges、reference map 與 projection/source 狀態。

### Dialog 與頁面資訊架構

- Readiness 從白板底部改為 modal dialog；即使已選取 node 仍可直接開啟。
- 原頁面下方的 architecture / assessment / contract 說明卡改由頂欄 `i` icon 開啟。
- Dialog 支援背景點擊、關閉按鈕、Escape 與焦點返回。
- 移除主頁額外向下捲動的資訊卡區域，白板、Filter、Inspector 與狀態列維持同一 viewport 工作區。

## 2. Validation

在 2026-07-15 最終工作樹執行：

```powershell
pnpm --dir frontend test
# 21 files / 83 tests passed

pnpm --dir frontend lint
# 0 errors；1 個既有 BoundaryDecisionModal fast-refresh warning

pnpm --dir frontend build
# tsc -b && vite build passed
```

Build 仍會顯示既有 `web-worker` external dependency warning；本 PR 未新增該 dependency。

Browser QA（API mode、`basic_qdrant_ollama_rag`、1280×720）確認：

- 十層 planes、backend connections、Filter dim/highlight 與 node selection 正常。
- Filter scroll height 與 content height 均為 463px，Risk Lens 完整可見。
- Filter legend 字體 8.2px、高度約 55px，無水平 overflow。
- Flows drawer 收合時只保留 34×44px 半透明箭頭；展開寬度 340px，無水平 overflow，可再次收回。
- Readiness 與 Architecture information dialogs 的 focus、Escape、互斥開啟與焦點返回正常。
- 主頁 scroll height 等於 viewport；底部狀態列固定。

## 3. Known limitations

- 若 selected build 沒有 readiness report，Readiness dialog 會明確顯示缺少 report，不建立假 findings。
- Runtime、Variants 與 Reasoning Mode 要等 backend 發布 typed membership metadata 才會啟用。
- Flows drawer 為避免大型 build 遮住白板，一次最多呈現 12 條目前 view 可見 edges。
- Edge 視覺目前只區分 backend-declared edge 與 projection relationship；更細的 typed-edge taxonomy 仍需 backend contract。
- `BoundaryDecisionModal.tsx` 的 fast-refresh warning 為既有限制，本 PR 未處理。

## 4. Submodule 狀態與跨電腦操作

`ref-opensource/Understand-Anything` 已改為 Git submodule。本機已完成初始化，並於 2026-07-15 驗證：

```text
主專案 pin：73559a160645359c57be44c174935899dec9f9f2
本機 checkout：73559a160645359c57be44c174935899dec9f9f2
狀態：一致（detached HEAD 為 submodule 固定版本的正常狀態）
```

換電腦或重新 pull 後仍需執行：

```bash
git submodule update --init --recursive
```

也可以使用 `git pull --recurse-submodules`，避免 reference project 是空資料夾或停在舊版。

## 5. Handoff notes

- 請 Timmy 以 current backend payload 檢查 plane/lens membership、readiness sidecar、typed edges 與 environment/build lineage 是否符合預期。
- Frontend 不會從 node label、type 或 source code 猜測缺少的 plane/lens membership。
- `docs/work/Hardy/frontend-review-2026-07-02.md` 是本機既有未追蹤筆記，不屬於本 PR，未 stage、未 commit。
- 後續若新增 Apply/review queue、runtime trace 或更多 edge taxonomy，應先更新 backend contract 與 fixtures，再啟用對應 UI。
