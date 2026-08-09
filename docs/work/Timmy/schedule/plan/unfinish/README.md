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
| `final-phase-hardening/` | `140`～`175`（不含已完成 `153`、`154`、`159`、`170`，與已 superseded 的 `140`） | Cross-platform、path/error/resource/concurrency/contract hardening 與 bugfix queue。`140` 已由 `finish/refactor/05` 以「移除端點」方式消解（Status **superseded**；**GitHub issue #140 於 2026-08-07 仍為 OPEN、待依該結論關閉**），檔案保留為決策軌跡但不再計入未完成數。`151` **部分完成**：Task 2/3 已由 #277 Stage 4 順帶落地（commit `b0d0632`），剩 Task 1（`API_BASE_URL` 解析的自動化測試）未實作，補完才可移入 `finish/` |
| `refactor/` | `15`（`03`/`05`/`06`/`07`/`08` 於 2026-08-07、`01`/`02` 於 2026-08-08 後端範圍完成歸檔至 `../finish/refactor/`；`04` 已於 2026-08-07 搬至 FE handoff 資料夾） | Web 邊界收斂與 legacy 退役計畫（**全部先於 s2-ua-integration 執行**）。**2026-08-07 後端部分已全數完成**（分支 `refactor/web-boundary-and-legacy-retirement`、umbrella issue #277）：`01` Phase B 完成（`6572817`）、`02` Phase B 完成（`eaef26b`）、`03`（`9e04802`）／`05`（`b31cf4e`）／`06`（`829fd75`）／`07`（`e6a378e`）／`08`（`a1ce0c6`）全份 done；各計畫的完整 commit 鏈見 `../../todo/2026-08-07-web-boundary-backend-first-TODO.md` ledger。**剩餘未完成者為 `15`；`01`／`02` 的 Phase A 與 `04` 全份已移交 FE handoff（FE-1／FE-2／FE-3）**。`01` explicit preflight cutover（退役 `create_scan` implicit 分支；Phase A 歸前端工作包 FE-1）；`02` 退役 process-wide 讀圖 `GET /api/map`＋`GET /map`（Phase A 歸 FE-2）；**`01`／`02` 原標註的「frontend 先行」gate 已於 2026-08-07 依使用者決策解除——後端先行動工，前端隨後補上 FE-1／FE-2；代價是 Phase B 合併後到前端上線前 `main` 對前端是壞的**；`03` 退役 `POST /api/map/build`（CLI `systograph map` 為等價替代）；`04` 前端接上 `GET /api/map/report` 取得 Markdown report（**純前端工作包 FE-3**，#219 的縮小範圍先行版，**已知只能拿 process-wide 最新 build**，待 build-scoped artifact API 再 refine；**檔案已於 2026-08-07 搬至 `docs/work/Meeting-Sync/meeting_sync_2026_08_06/04-wire-frontend-map-report-download.md`**，refactor/ 不再保留）；`05` 退役 `POST /api/viewer/load`（連帶使 `final-phase-hardening/140-*.md` superseded；issue #140 待關閉）；`06` 移除 v1 rollback 寫入路徑（由 `15` Task 2 抽出；v1 讀取能力完整保留）；`07` 投影平面改由 canonical type 推導（退役 slot→layer 查表；UA 零相依。模板假邊的另一半屬 16C→16D→16G 鏈，**刻意不搬入**——其硬前置住在 s2-ua-integration，搬入會依賴倒置）；`08` 移除 `ViewerPayload` 型別與 session 旁路槽（gate＝02＋05 完成，執行前已確認滿足）。`15` 為 legacy v1 完全退役（2026-08-06 由 `phase2/static-trace-plan/s3-retirement/` 搬入，編號保留；**仍受 Gate-4 約束、尚未動工**）。另含非計畫索引 `RAG-CORE-V1-RETIREMENT-INDEX.md`——`rag-core-v1` 模板退場的七個滲透點歸屬表（`C3a`／`C6` 已由 `07` 完成，**`C1`/`C3b`/`C4`/`C5`/`C7` 仍無人認領**；與 `ai-system-map/v1` schema 退場〔`15`〕是兩件事）。**前端工作已全數抽出**：`01`/`02` 的 Phase A 與 `04` 全份 → `docs/work/Meeting-Sync/meeting_sync_2026_08_06/frontend-web-boundary-refactor-handoff.md`（2026-08-06；本佇列對後端而言只含 backend 部分） |

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

2026-08-07 **只同步索引狀態、未搬移任何檔案**（umbrella issue #277 Stage 5）：

- `refactor/` 的後端部分（`01` Phase B、`02` Phase B、`03`、`05`、`06`、`07`、`08`）
  於分支 `refactor/web-boundary-and-legacy-retirement` 完成，各計畫檔 Status 已自帶
  commit；本 README 只更新 `refactor/` 列的敘述，計畫檔待 Stage 5 逐項複驗驗收標準後
  才決定是否移入 `../finish/`。→ 複驗通過後已執行搬移：2026-08-07
  `03`/`05`/`06`/`07`/`08`、2026-08-08 `01`/`02`（後端範圍完成，Phase A 移交
  FE handoff）。
- `final-phase-hardening/140` 由 `finish/refactor/05` 以「移除端點」方式消解，Status 改
  **superseded**；檔案依其檔頭指示保留為決策軌跡，但已從未完成計數移出——final
  hardening unfinish queue 由 32 降為 31 份。**注意：GitHub issue #140 於 2026-08-07
  實查仍為 OPEN**，該檔檔頭「issue #140 依此結論關閉」目前只是決策、尚未執行，
  關閉動作仍待辦。
- `final-phase-hardening/151` 為部分完成（Task 2/3 已於 commit `b0d0632` 落地，Task 1
  的自動化測試未實作），仍計入未完成數，維持在 unfinish。
