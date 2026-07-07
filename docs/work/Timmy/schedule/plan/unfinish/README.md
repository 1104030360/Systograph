# Unfinished Plan Phase Index

未完成計畫依產品/工程相依關係分類。檔案編號保留原樣，避免 issue、commit、
report 與歷史討論失去對應。

| Folder | Plans | 用途 |
|---|---:|---|
| `phase2/static-trace-plan/` | `00A`～`15` + `01A` + `03A` | 靜態 release-readiness 主線；00A 建立 generic `ai-system-map/v2` 與 legacy compatibility migration；01A 定義 AI 系統能力參考地圖；12 為 runtime deferred boundary；13 gated cutover；14 驗證後立即執行 15 complete migration |
| `phase2/dynamic-trace-plan/` | `00` 起 | `00` 為 static inferred call graph / execution path；`01` 起為 runtime trace 實作 |
| `phase3-platform-foundation/` | `25`～`30` | Upload、durable domain/storage、OpenAPI contract、shared validation、error artifact |
| `phase4-scanner-expansion/` | `31`～`39A` | Fixtures、manifest/Compose/AST、local profile/template、multimodal、governance/observability scanner expansion |
| `phase5-product-experience/` | `40`～`42` | Explain-only assistant、durable project/mapping/rescan UX、Graph Studio |
| `final-phase-hardening/` | `140`～`175`（不含已完成 `153`、`154`） | Cross-platform、path/error/resource/concurrency/contract hardening 與 bugfix queue |

## Phase2 Boundary

2026-07-03 重組：`phase2/static-trace-plan/`（00A～15）、`phase2/dynamic-trace-plan/`（動態 trace 實作）。

2026-07-03 新增 `phase2/static-trace-plan/00A-introduce-ai-system-map-v2-compatibility-migration.md`：
先完成 v1/v2 dual-read 與 compatibility gate，再由 Plan 13 切換 active generic v2，
Plan 14 執行 final validation，通過後立即執行 Plan 15。Plan 12 維持 deferred boundary。

2026-07-06 決策更新：`rag-core-v1` 只保留為 legacy v1 template 與 migration
adapter input；active assessment surface 收斂為 Capability Map / profile /
readiness findings。

2026-07-03 使用者決策更新：**先做相容遷移並確認沒問題，再接續完全遷移**。
因此 Plan 15 改為 `phase2/static-trace-plan/15-complete-legacy-v1-retirement-after-compatibility.md`；
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
`../finish/`；目前 final hardening unfinish queue 為 34 份。
