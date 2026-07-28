# Phase2 Frontend Handoff（2026-07-12）

> 對象：接手這條分支的 AI agent（Claude / Codex）或工程師。
> 目標：讓你在另一台電腦 clone 下來後，不需要原對話紀錄就能繼續開發。

## TL;DR

```text
分支 feature/phase2-frontend-contract（base：origin/main 8b38c7f，領先 10 commits，全部 frontend + docs）。
內容：Phase2 contract layer（三種 payload 來源統一正規化）、Graph Studio 固定 plane-band
版面（捨棄白板互動）、六 lens rail、profile attachment overlay、ReadinessPanel、
Mapping Completeness、build-scoped API 接線與 build history 切換。
後端一律以 Timmy 的 main 為準（#248 已含完整 Phase2 S1 API）；前端不動 src/systograph/。
需後端配合的事項已列在 docs/work/Meeting-Sync/frontend_sync_2026_07_12.md，等會議定案。
```

## 0. 環境與啟動

```bash
git clone <repo> && cd Systograph
git checkout feature/phase2-frontend-contract
git submodule update --init --recursive   # ref-opensource/Understand-Anything 是 submodule，必跑一次

# 前端（pnpm）
cd frontend
pnpm install
pnpm test        # Vitest（目前 48/48）
pnpm lint        # ESLint（0 errors；BoundaryDecisionModal 有 1 個既有 fast-refresh warning）
pnpm build       # tsc -b && vite build
pnpm dev         # http://127.0.0.1:5173

# 後端（uv；驗證 API mode 用）
cd ..
uv sync
uv run uvicorn systograph.web.app:create_app --factory --host 127.0.0.1 --port 8000
```

UI 驗證 API mode 流程：開 dev server → 右上 Source 切到 API → 填一個本機專案路徑
→ Start scan → 完成後畫面載入 build-scoped payload（project popover 會顯示
scan/build/environment lineage，toolbar 出現 Builds 選單）。

## 1. 分支 commit 一覽（舊 → 新）

| Commit | 內容 |
|---|---|
| `2a5c1ac` | Phase2 viewer contract adapter：step-08 target sample／legacy `/api/map` 雙讀、same-build identity 驗證、safe `artifact_refs`（拒絕 path、只收 basename） |
| `e7cf06a` | 五態 assessment 渲染（detected/partial/undetermined/not_detected/conflicted）、activation 與 status 分離顯示、MappingCompletenessPanel |
| `0f3ca06` | chore：`.pnpm-store/` 加入 .gitignore |
| `cc33606` | Lens rail：六個固定 lenses（Data/Control/Evidence/Governance/Source/Risk），backend 未發布 membership 時 disabled + 原因；highlight/dim only，不刪節點 |
| `f121d3b` | Profile attachment 依 backend anchor metadata 疊放（不進 ELK 主佈局）；ReadinessPanel 初版 |
| `56e3f05` | 對齊 #248 samples：sidecar 移除 `project_id`、`reference_map_version`→`reference_catalog_version`、assessment 增 `plane_id`、readiness report 換新形狀（grounding + reason-based findings） |
| `fd5cfdc` | **固定 plane-band 版面**：v2 projection 依 `plane_id` 分帶（canonical 10-plane 順序），停用拖拉、保留 zoom/pan/fit/minimap；v1/legacy payload 維持 ELK 自動佈局 |
| `9d2930a` | docs：Meeting-Sync 進度與待討論事項 |
| `8d74f92` | build-scoped API 接線：API mode 優先讀 `GET /api/projects/{id}/map-builds/latest`，`/api/map` 為 fallback；`MapBuildScopedResponse` 正規化；Mapping Completeness 可回退讀 profile sidecar |
| `1eeb628` | Build history 切換：Builds 選單（`GET map-builds` 清單）、pin 歷史 build（`GET /api/map-builds/{build_id}`）、常駐 historical 提示 + Back to latest |

備份：rebase 前的舊分支在 `backup/pre-rebase-phase2`（含一個已被 #248 取代、
勿再使用的 backend build-history commit）。

## 2. 關鍵決策（違反這些就是走錯方向）

1. **版面走「A 案」**：保留 React Flow 引擎，把 ELK 換成固定 plane-band 佈局。
   `DeepResearch/index.html` 只作視覺語言與互動方向參考——**不得**複製其 HTML/CSS/JS、
   16 種 views、hard-coded 52 nodes、87% quality 數字。這是與 Hardy 本人確認過的決策，
   也符合 Meeting-Sync 07-07「不重建 graph engine、沿用 zoom/pan/fit/minimap」。
2. **Backend 是唯一 truth**：五態、activation、Mapping Completeness、lens membership、
   plane 歸屬、readiness findings 全部只渲染 backend 提供的資料；缺資料就顯示
   degraded/unavailable 並說明原因，**不得**前端推導或補值。
3. **後端歸 Timmy**：`src/systograph/` 不動。需要後端改動（欄位、endpoint）一律寫進
   Meeting-Sync 文件向 Timmy 提出，不自己實作。
4. **Build immutability**：apply/rescan 產生新 build；前端永不 in-place 改 canonical 資料。
   跨 build 的 sidecar（identity 不符）在 parser 層直接拒絕。

## 3. 前端架構速覽（本分支新增/重寫的部分）

```text
frontend/src/
├── contracts/viewer.ts        # 契約核心：三種來源 → 統一 ViewerPayload
│     parseViewerPayload()       phase2 target sample ↔ legacy /api/map 雙讀
│     parseMapBuildPayload()     current MapBuildScopedResponse（外層 lineage +
│                                build_result sidecars + v1 base graph）
│     extractMappingCompleteness()  graph 優先、profile sidecar 回退、皆無→undefined
│     readinessReportSchema      鏡射 systograph.core.models.readiness_report
│     mapBuildHistory*Schema     鏡射 systograph.web.schemas
├── types.ts                    # contract_source: legacy-v1 | phase2 | phase2-build
├── utils/
│   ├── planes.ts               # 10-plane 呈現順序 + layoutPlaneBands()（帶內排卡、
│   │                             anchored attachment 疊放、無 plane_id → unassigned 帶）
│   ├── lenses.ts               # 六 lens slot 解析（容錯 id matcher）+ getLensMatches
│   ├── graph.ts                # createFlowElements（filter/lens/trace highlight 合成）
│   │                             + layoutGraph（ELK，legacy 用）
│   └── assessment.ts           # 五態 status key/label
├── components/
│   ├── SystemGraph.tsx         # layoutMode: "planes" | "auto"；band 節點注入；
│   │                             planes 模式停用拖拉
│   ├── PlaneBandNode.tsx       # band 背景（純視覺 chrome，不可選取）
│   ├── LensPanel.tsx           # lens rail（degraded/empty 狀態齊全）
│   ├── ReadinessPanel.tsx      # grounding 摘要 + findings；null/不支援契約 → degraded
│   ├── BuildHistoryMenu.tsx    # Builds 選單（最新在前、latest 標記）
│   ├── HistoricalBuildIndicator.tsx  # 檢視舊 build 的常駐提示
│   └── MappingCompletenessPanel.tsx
├── services/viewerApi.ts       # loadApiViewerPayload（latest 優先、/api/map fallback）、
│                                 loadMapBuildViewerPayload、listMapBuilds
├── hooks/useViewerPayload.ts   # query key 含 projectId + buildId
├── hooks/useMapBuilds.ts       # build history query（API mode + 有 project 時啟用）
└── store/viewerStore.ts        # activeProjectId / activeBuildId（null=跟隨 latest）
```

呈現規則（App.tsx）：`graphIsV2`（graph_view_model.source_schema_version === "ai-system-map/v2"）
決定 plane 版面與五態 legend；`build_id != null` 決定 lineage 顯示。**不要**用單一
contract 旗標控制全部 UI——current build-scoped payload 是 phase2 lineage + v1 graph 的混合。

## 4. 測試現況

- Vitest 48/48：contract 解析（含 handoff sample regression：52 assessments、15 profiles、
  10 artifact refs、cross-build 拒絕、path 拒絕）、plane 佈局、lens 邏輯、
  ReadinessPanel、BuildHistoryMenu、MappingCompletenessPanel。
- handoff samples（`docs/work/Timmy/design/EPIC1/frontend-json-handoff/`）被測試直接
  import 作 fixture——**Timmy 更新 samples 時 parser 測試就是預警器**，跑 `pnpm test` 看斷點。
- 已對真實 backend 完整實測兩輪（import → scan → latest → 切歷史 build → back to latest）。

## 5. 已知缺口與等待事項（詳見 Meeting-Sync 2026-07-12）

1. **等 Timmy Plan 06**：GraphViewModel 尚未發布 `plane_id`／52 reference nodes／
   lens membership／`artifact_refs`。前端版面與 lens UI 已就緒，資料一到自動點亮；
   在那之前 v2 sample 只會有單一 unassigned 帶，六 lens 全 disabled——這是預期行為。
2. **readiness findings 無 component refs**（affected_component_ids 被 #248 移除）→
   finding 回查 component 的驗收項目暫時做不到，已提請討論。
3. **`MapBuildScopedResponse` 外層無 `environment_id`** → 目前從 sidecar 取，已提請討論。
4. Apply 流程（`POST /api/map-builds/{base}/apply`）endpoint 已存在，但 review queue UX
   涉及 proposal 語意，等會議定案再做。
5. Runtime trace 持續 deferred；`ReplayTimeline` 等舊 UI 尚未拆除，等 legacy retirement 計畫。

## 6. 建議的下一步（依序）

1. **DeepResearch 視覺語言迭代**（純前端、不等會議）：plane 配色、icon、node 卡片
   質感，依 `docs/work/Meeting-Sync/meeting_sync_2026_07_07/frontend-deepresearch-icon-migration.md`。
2. 會議後：readiness 缺欄位的處置、Apply/review queue UI。
3. Plan 06 發布後：lens membership 實際點亮驗證、artifact_refs lazy-load、52-node
   reference map 的 plane 版面實測（目前只有合成 fixture 驗過多帶邏輯）。

## 7. 陷阱備忘

- **Submodule**：pull 後要 `git submodule update --init --recursive`（或
  `git config submodule.recurse true` 一次設定），否則 `ref-opensource/Understand-Anything`
  是空資料夾。
- Windows 下 git 會警告 LF→CRLF，無害。
- `pnpm install` 可能在 repo 產生 `.pnpm-store/`，已被 .gitignore 排除，勿 commit。
- 後端本地 JSON 持久層會跨重啟保留 project／build history，import 以路徑去重
  （同路徑回到同一 project_id）——測 build history 時這是 feature 不是 bug。
- Sample mode 目前載 legacy 樣本（`frontend/src/data/frontend-json-sample.json`），
  所以打開網頁看到 ELK 白板佈局是正常的；plane 版面要 v2 projection（API mode 或
  將 sample 換成 step-08 樣本）才會出現。
