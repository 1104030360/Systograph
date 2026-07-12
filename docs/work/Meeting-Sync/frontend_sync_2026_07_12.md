# KAI-Mind Frontend Sync：Phase2 Graph Studio 進度與待討論事項（2026-07-12）

先抓住這份文件的主軸：

```text
前端已完成 Phase2 contract layer 與 Graph Studio 固定 plane-band 版面（捨棄白板互動），
並已 rebase 到含 #248（S1 pipeline-core 後端）的 main。
本文記錄需要與 Timmy 對齊的 backend 事項，以及前端接下來的待辦順序。
```

分支：`feature/phase2-frontend-contract`（base：`origin/main` = `8b38c7f`）。
全部變更為 frontend-only；`src/kai_mind/` 未動。

## 1. 前端目前完成範圍

| Commit | 內容 |
|---|---|
| `2a5c1ac` | Phase2 viewer contract adapter：target sample／legacy `/api/map` 雙讀、same-build identity 驗證、safe `artifact_refs` 檢查 |
| `e7cf06a` | 五態 assessment 渲染、activation 與 status 分離、Mapping Completeness 面板 |
| `cc33606` | Lens rail：六個固定 lenses（Data／Control／Evidence／Governance／Source／Risk），membership 缺失時 disabled + 說明；highlight/dim only |
| `f121d3b` | Profile attachment 依 backend anchor metadata 疊放（不進主 layout）；ReadinessPanel |
| `56e3f05` | 對齊 #248 samples：sidecar 移除 `project_id`、`reference_catalog_version`、assessment `plane_id`、readiness report 新形狀 |
| `fd5cfdc` | **固定 plane-band 版面**：phase2 payload 依 `plane_id` 分帶（canonical 10-plane 順序）、停用拖拉、保留 zoom/pan/fit/minimap；legacy payload 維持 ELK |

版面決策（與 Hardy 對齊）：`DeepResearch/index.html` 只取視覺語言與互動方向；
實作走「React Flow + 固定 plane-band layout」，不複製其 HTML/JS/資料模型，
符合 Meeting Sync 07-07「不重建 graph engine、沿用 zoom/pan/fit-view/minimap」。

## 2. 需與 Timmy 討論（backend 範疇，前端不動手）

1. **Plan 06 graph projection 發布時程**：目前 `GraphViewModel` 的 nodes 沒有
   `plane_id`、`filters.lenses` 為空、52 reference nodes 未進 projection。
   前端 plane 版面與六個 lens UI 均已就緒（缺資料時走 degraded），
   projection 一發布畫面即自動成形——希望能排優先。
2. **Readiness findings 缺 component refs**：新 `ReadinessFinding` 只有
   `evidence_ids`，沒有 `affected_component_ids`。Meeting Sync 07-07 要求
   「Evidence Inspector 可從 finding 回查 components」目前做不到，
   請確認是否加回欄位或改以其他 ref satisfying 這條驗收。
3. **`MapBuildScopedResponse` 外層沒有 `environment_id`**：目前只能從
   profile／readiness sidecar 取得；sidecar 缺失時 lineage 顯示不完整。
   建議外層 lineage 補上 `environment_id`。
4. **`/api/map` active 輸出切 v2 的時程**（確認性質）：前端已雙讀，隨時可切。
5. **detail-scans／trace 的 path-scoped alias 為 later**（確認性質）：
   前端先依 current 契約使用 request body 的 optional `build_id`。

## 3. 前端待處理（依序）

1. （已完成 2026-07-12）接 build-scoped API：`GET /api/projects/{id}/map-builds/latest`
   為 API mode 主要載入路徑，`/api/map` 降為 fallback；lineage 與 warnings 上 UI。
   已對真實 backend 走完 import → scan → latest 全流程驗證。
2. （已完成 2026-07-12）Build history 切換：`GET /api/projects/{id}/map-builds` 清單 +
   `GET /api/map-builds/{build_id}` 載入歷史 build；檢視歷史 build 時顯示常駐
   「Historical build」提示與 Back to latest。已對真實 backend 驗證切換往返。
3. Apply 流程：review queue UI + `POST /api/map-builds/{base}/apply`
   （409 `base_build_not_latest` → 提示 reload latest）。
4. `artifact_refs` lazy-load（等 Plan 06 發布 refs）。
5. DeepResearch 視覺語言迭代：plane 配色、icon（依 07-07 icon-migration 文件）。
6. Runtime trace 維持 deferred（等 typed runtime contract）。

## 4. 附註

- `ref-opensource/Understand-Anything` 已改為 git submodule：pull 後需
  `git submodule update --init --recursive`，或使用 `git pull --recurse-submodules`
  （可 `git config submodule.recurse true` 一次設定）。
- Rebase 前的舊分支備份在 `backup/pre-rebase-phase2`；
  被 #248 取代的舊 backend build-history commit 已丟棄未帶上來。
- 前端驗證基準：Vitest 39/39、TypeScript、ESLint、production build 全數通過（2026-07-12）。
