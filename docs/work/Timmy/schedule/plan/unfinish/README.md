# Unfinished Plan Phase Index

未完成計畫依產品/工程相依關係分類。檔案編號保留原樣，避免 issue、commit、
report 與歷史討論失去對應。

| Folder | Plans | 用途 |
|---|---:|---|
| `phase2/static-trace-plan/` | `00A`～`14` + `18` + `01A` + `03A`（`15` 已移至 `refactor/`） | 靜態 release-readiness 主線；00A 建立 generic `ai-system-map/v2` 與 legacy compatibility migration；01A 定義 AI 系統能力參考地圖；12 為 runtime deferred boundary；13 gated cutover；14 驗證後立即執行 15 complete migration |
| `phase2/dynamic-trace-plan/` | `00` 起 | `00` 為 static inferred call graph / execution path；`01` 起為 runtime trace 實作 |
| `phase3-platform-foundation/` | `25`～`30` | Upload、durable domain/storage、OpenAPI contract、shared validation、error artifact |
| `phase4-scanner-expansion/` | `31`～`39A` | Fixtures、manifest/Compose/AST、local profile/template、multimodal、governance/observability scanner expansion |
| `phase5-product-experience/` | `40`～`42` | Explain-only assistant、durable project/mapping/rescan UX、Graph Studio |
| `final-phase-hardening/` | `140`～`175`（不含已完成 `153`、`154`、`159`、`170`） | Cross-platform、path/error/resource/concurrency/contract hardening 與 bugfix queue |
| `refactor/` | `01`～`08`、`15` | Web 邊界收斂與 legacy 退役計畫（**全部先於 s2-ua-integration 執行**）。`07` 投影平面改由 canonical type 推導（退役 slot→layer 查表；UA 零相依。模板假邊的另一半屬 16C→16D→16G 鏈，**刻意不搬入**——其硬前置住在 s2-ua-integration，搬入會依賴倒置）。`08` 移除 `ViewerPayload` 型別與 session 旁路槽（**gate：02＋05 都完成後**；純死碼清除）。另含非計畫索引 `RAG-CORE-V1-RETIREMENT-INDEX.md`——`rag-core-v1` 模板退場的七個滲透點歸屬表（**其中 C1/C3b/C4/C5/C7 目前無人認領**；與 `ai-system-map/v1` schema 退場〔`15`〕是兩件事）。**前端工作已全數抽出**：`01`/`02` 的 Phase A 與 `04` 全份 → `docs/work/Meeting-Sync/meeting_sync_2026_08_06/frontend-web-boundary-refactor-handoff.md`（2026-08-06；本佇列對後端而言只含 backend 部分）。`06` 移除 v1 rollback 寫入路徑（由 `15` Task 2 抽出，**不受 Gate-4 約束、可立即動工**；保留 v1 讀取能力）。`15` 為 legacy v1 完全退役（2026-08-06 由 `phase2/static-trace-plan/s3-retirement/` 搬入，編號保留；**仍受 Gate-4 約束**）。`01` explicit preflight cutover（退役 `create_scan` implicit 分支，frontend 先行）；`02` 退役 process-wide 讀圖 `GET /api/map`＋`GET /map`（卡在前端 fallback，frontend 先行）；`03` 退役 `POST /api/map/build`（前端零引用，**可立即動工**，CLI `systograph map` 為等價替代）；`04` 前端接上 `GET /api/map/report` 取得 Markdown report（#219 的縮小範圍先行版，**已知只能拿 process-wide 最新 build**，待 build-scoped artifact API 再 refine）；`05` 退役 `POST /api/viewer/load`（前端零引用，**會使 issue #140／`final-phase-hardening/140-*.md` 失效**，執行前須先決定該 issue 處置） |

## Phase2 Boundary

2026-07-03 重組：`phase2/static-trace-plan/`（00A～15）、`phase2/dynamic-trace-plan/`（動態 trace 實作）。

2026-07-03 新增 `phase2/static-trace-plan/00A-introduce-ai-system-map-v2-compatibility-migration.md`：
先完成 v1/v2 dual-read 與 compatibility gate，再由 Plan 13 切換 active generic v2，
Plan 14 執行 final validation，通過後立即執行 Plan 15。Plan 12 維持 deferred boundary。

2026-07-06 決策更新：`rag-core-v1` 只保留為 legacy v1 template 與 migration
adapter input；active assessment surface 收斂為 Capability Map / profile /
readiness findings。

2026-07-03 使用者決策更新：**先做相容遷移並確認沒問題，再接續完全遷移**。
因此 Plan 15 改為 `refactor/15-complete-legacy-v1-retirement-after-compatibility.md`
（2026-08-06 由 `phase2/static-trace-plan/s3-retirement/` 搬入 refactor，編號保留）；
不得跳過 00A dual-read、13 cutover 或 14 validation。

Phase2 差異化來自 `00A`～`11`、13 migration、Capability Map plane/component
assessment、dynamic `00` static inferred execution mapping、`14` final static
inspection/readiness path，以及 `15` 的相容驗證後退役：

- `12` runtime trace 不阻擋 MVP。
- `13` 只在 00A compatibility gate 通過後執行，且是 14 final gate 前置。
- dynamic `00` 產生 `call_graph.json`、`dataflow_hints.json`、`execution_paths.json`
  與 `execution_map.mmd`，但仍是 static-only，不是 runtime proof。
- Phase3 之後的 upload、database、assistant、remote template 等工作不得倒灌成
  Phase2 的產品承諾。

## Canonical Execution Order

舊 `00-implementation-order.md` 已由新的 phase folder 結構取代；本 README 是跨 phase
的 canonical index，各 phase 的細部順序由其 README 擁有。

```text
Phase2 foundation
00 -> 00A -> 01 -> 01A -> 02 -> 03 -> 03A -> 04

Lookup / projection
05 -> 06 -> 07 -> 08 -> 09

Rule metadata branch
04 -> 10 -> 11

Static execution
00A + 03 + 05 -> dynamic/00

Cutover / validation / complete retirement
13 -> 14 -> 15

12 = boundary document only
dynamic/01 = post-Phase2 runtime work
```

Phase3 延伸 03A 的 domain/persistence；Phase4 擴充 deterministic evidence；Phase5
消費穩定 backend projection，不成為 scanner truth source。

## Capability Map Decision Source

- [Capability Map Assessment Decision Summary](./phase2/capability-map-assessment-decision-summary.md)
- `DeepResearch/` 僅為研究與視覺參考，不是可直接複製或修改的 production frontend。

## Move Verification

2026-07-03 搬移前後以 SHA-256 比對 53 份非 Phase2 plan，內容完全一致：

- Phase3：6 份。
- Phase4：9 份。
- Phase5：2 份。
- Final phase：36 份。

2026-07-05 重新以 focused tests 驗證 #153/#154（70 tests passed）後，兩份 plan 已移至
`../finish/`，final hardening unfinish queue 由 36 降為 34 份。

2026-08-05 以 GitHub issue 狀態 + commit + 程式碼實況逐份複查 unfinish plan 後再搬移：

- `phase2/static-trace-plan/s1-v2-cutover/13.5`～`13.8` → `../finish/s1-v2-cutover/`：
  四份 plan 自身 Status 皆為 done，並各有 report 與 commit（`47e84cd`、`2a65fb8`）可回溯。
- `13-retire-legacy-extension-contract.md` → `../finish/s1-v2-cutover/`（2026-08-05 使用者
  確認）：backend 2026-07-17 完成，frontend handoff 由 commit `25f2223`（PR #258）完成，
  contract test 強制 `migrate` 消費者為 0；`s1-v2-cutover/` 於 unfinish 端清空移除。
- `final-phase-hardening/159`（plan 自訂剩餘範圍 `scan_routes.py` typed 404 與一致性測試
  皆已落地）與 `final-phase-hardening/170`（issue #170 CLOSED、commit `8b38c7f`）→
  `../finish/`；final hardening unfinish queue 為 32 份。
- 其餘 `140`～`175` 經讀碼查核確認仍未實作，維持在 unfinish；GitHub issue 仍為 OPEN。
