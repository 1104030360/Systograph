# 16F — 新增模組清單與管線前後對照

> 📖 **第一次看？** 先讀 [`README.md`](./README.md)（閱讀順序 + 名詞對照表）。
> **白話一句話：** 這批計畫做完後，管線上「多出來的東西」總共有哪些、各自歸誰管。
> **這份不是實作計畫**，是查詢用的清單 + 兩張前後對照圖。

Status: reference（2026-08-04 建立）— 內容全部從 `16` / `16C` / `16D` / `16E` 抽取，
不新增任何決策。四份計畫任一有變更時，以計畫本體為準，本檔跟改。

---

## 1. 為什麼需要這份

`16` / `16C` / `16D` / `16E` 四份合計 1600+ 行，**新增的模組散落在各自的 Task 清單裡**，
沒有任何一處可以一眼看出「這批做完，codebase 到底多了什麼」。
Review 時最常問的三個問題——

- 這批總共要新造幾個模組？分別住在哪一層？
- 哪些是「新檔」、哪些只是「改既有檔」？
- 有沒有東西是我以為要改、其實不用動的？

——本檔回答這三個。

---

## 2. 管線前後對照

### 2.1 做完前（今日 runtime · UA Phase A · TOML-primary）

```text
Step 1  IMPORT
+------------------------------------------------------------------------+
| validate source / path  ->  project_id  ->  registry project.json      |
+------------------------------------------------------------------------+
     |
     v
Step 2  BOUNDARY -- decide what gets scanned      [scan_inventory_rules.toml]
+------------------------------------------------------------------------+
| 2-1  candidate enumeration (git / recursive + catalog + safety)        |
| 2-2  metadata-only preflight (required / soft-excluded / exact / dir)  |
| 2-3  one-run decisions:  exact > deepest dir > ancestor > default      |
| 2-4  openat no-follow + fstat + content hash                           |
|      ->  final FileInventory + per-file audit / digests                |
+------------------------------------------------------------------------+
     |
     v
Step 3  SCAN -> facts + evidence                          <<< WEAK SPOT 1
+------------------------------------------------------------------------+
| ConfigParse | DockerCompose | DependencyManifest | CodePattern         |
|   13 regex rules, 11 of them Python-only                               |
|   NO import graph   NO symbol table   NO call graph                    |
| -> merge / dedupe / secret masking                                     |
| -> ProjectScanResult -> snapshot.json      (scan_id = immutable)       |
+------------------------------------------------------------------------+
     |
     v
Step 4  MATERIALIZE = BRIDGE 1 (Python)                   <<< WEAK SPOT 2
+------------------------------------------------------------------------+
| 4-1  component_bridge_registry.py   rule_id + evidence  ->             |
|         +-- component            (into system map)                     |
|         +-- capability candidate (Step 6 input)                        |
|         +-- unmapped needs_review -> proposal candidate                |
| 4-2  apply confirmed ManualMapping   (Apply replay re-enters here)     |
| 4-3  endpoints[]                                                       |
| 4-4  risk_hints[]                    [risk_hint_rules.toml = text only]|
| 4-5  edges / flows  FlowDerivationService                              |
|         12 HARDWIRED relations, zero repo code involved                |
|         normalize:153 stamps EVERY edge status="observed"  <-- lying   |
| 4-6  assemble draft   4-7  mask paths   4-8  schema validate           |
+------------------------------------------------------------------------+
     |
     v   ai_system_map.json  (v2, CANONICAL repo truth, build_id)
     |
Step 5  INDEX     SystemMapIndex -- in-memory lookup only, writes nothing
     |
     v
Step 6  ASSESSMENT = BRIDGE 2 (pure Python)
+------------------------------------------------------------------------+
| input: system map + Index + capability_reference_map.toml (10x52)      |
|                            + profile_registry.toml (15 profiles)       |
| 6-1  ProfileInferenceService  repo component <-> reference node        |
|         52 nodes five-state + 15 profiles   (SOLE owner)               |
| 6-2  ReadinessReport    6-3  call_graph      6-4  dataflow_hints       |
| 6-5  execution_paths    6-6  evidence_table                            |
+------------------------------------------------------------------------+
     |
     v
Step 7  PUBLISH
+------------------------------------------------------------------------+
| GraphProjectionService                                                 |
|   emit 52 reference cells by plane (always) + repo overlay             |
|   Mermaid / Markdown                                                   |
| atomic publish of sibling JSON  ->  MapBuildResult                     |
+------------------------------------------------------------------------+
     |
     v
Step 8  VIEWER    GET /projects/{id}/map-builds/latest  or /map-builds/{id}
     |            ViewerLoadResult + GraphViewModel -> React render
     v
Step 9  REVIEW (optional)
+------------------------------------------------------------------------+
| unmapped -> MappingEvidencePacket -> MappingProposalService            |
|   deterministic heuristics + optional LLM [llm_proposal.toml]          |
| -> pending proposal -> accept/edit -> ManualMappingService             |
| -> APPLY: skip Step 3, replay same scan_id, rerun 4-2 .. 7, new build  |
+------------------------------------------------------------------------+
     |
     +----------------------------> back to Step 4-2
```

### 2.2 做完後（Plan 16 + 16C + 16D + 16E G3 · Phase B/C）

```text
Step 1  IMPORT                          unchanged
Step 2  BOUNDARY                        unchanged + UA enrichment
+------------------------------------------------------------------------+
| 2-1 .. 2-4 same as before                                              |
| NEW  inventory enrichment: language / fileCategory / line count        |
|      (logic ported from scan-project.mjs; that script is NOT run)      |
+------------------------------------------------------------------------+
     |
     v
Step 3  SCAN -- UA becomes primary                          [Plan 16]
+------------------------------------------------------------------------+
| NEW  UnderstandAnythingAnalysisService (Python orchestrates subprocess)|
|        NodeRuntimePreflight -> SubprocessRunner -> ResultValidator     |
|                                                                        |
|        spawns the 3 scripts directly -- no .mjs wrapper                |
|          extract-import-map.mjs    who imports whom                    |
|          compute-batches.mjs       Louvain grouping  (Systograph patch)       |
|          extract-structure.mjs     functions / classes / call hints    |
|          file-analyzer (LLM)       DEFERRED -- never executed          |
|        work-dir = system temp, deleted when the scan ends              |
|        -> ua-analysis-result.json  (semantic = null)                   |
|                                                                        |
| NEW  UaStructuralAdapter  ->  ScanFact + Evidence                      |
|        ua_import_*   file -> file, NO line number                      |
|        ua_symbol_*   function spans, startLine / endLine               |
|        ua_call_hint_*  caller -> callee @ line   <-- DIRECT evidence   |
|      + G3 external imports (16E, do this first)                        |
|                                                                        |
| OLD TOML providers demoted to parity comparison only                   |
| fail-closed: bad schema / missing Node / failed batch -> STOP          |
| 12 languages instead of ~1                                             |
+------------------------------------------------------------------------+
     |
     v   ScanFact pool -- same shape as before, richer content
     |
Step 4  MATERIALIZE = BRIDGE 1                     [13.7 + 16C]
+------------------------------------------------------------------------+
| 4-1  bridge registry, now fed by ua_* rule_ids                         |
|        13.7 aligns bridge kind -> 52-cell vocabulary                   |
|        (without it: UA scans perfectly and still lights up 1/52)       |
|                                                                        |
| NEW  ComponentResidenceIndex  -- which component lives in which code   |
|        component.evidence_ids -> Evidence.file / line_start            |
|        -> enclosing_function_span via ua_symbol_*                      |
|        -> by_component / by_file / by_span                             |
|                                                                        |
| 4-5  edge derivation replaces the 12-row table -- 2 levels only:       |
|        L1  call hint, has line -> direct   -> observed      COUNTS     |
|        L2  import, no line     -> indirect -> undetermined  IGNORED    |
|      only L1 feeds profile wiring evidence; L2 is honest-but-unusable  |
|      template edges linger as undetermined until 16G deletes them      |
|      status becomes HONEST; L2 must never fake a line number           |
|                                                                        |
| 4-2 / 4-3 / 4-4 / 4-6 / 4-7 / 4-8  unchanged                           |
+------------------------------------------------------------------------+
     |
     v   ai_system_map.json -- edges now carry real provenance
     |
Step 5  INDEX                           unchanged, in-memory only
     |
     v
Step 6  ASSESSMENT = BRIDGE 2                      [13.8 + 16D]
+------------------------------------------------------------------------+
| 6-1  ProfileInference unchanged as owner, but:                         |
|        13.8 adds endpoint constraints to relationship lookup           |
|        (edges go from 12 to hundreds -- without it, false positives)   |
|        detected now reachable via L1 direct evidence                   |
| 6-3  call_graph      fed by real call hints, not template              |
| 6-4  dataflow_hints  fed by real edges                                 |
| 6-5  execution_paths call-first, template demoted to fallback  [16D]   |
+------------------------------------------------------------------------+
     |
     v
Step 7  PUBLISH                         unchanged code path, truer data
Step 8  VIEWER                          NO frontend contract change [16A]
Step 9  REVIEW / APPLY                  unchanged; Apply still skips UA
+------------------------------------------------------------------------+
| Apply replays snapshot.scan_result -- it does NOT re-run the sidecar   |
+------------------------------------------------------------------------+
```

### 2.3 兩條執行路徑（前後相同，不受本批影響）

```text
Rescan   new preflight -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8   new snapshot, new scan_id
Apply    no preflight, no repo read -> 4-2 -> 5 -> 6 -> 7 -> 8  same scan_id, new build_id
```

---

## 3. 圖上標 `NEW` 的四項（主清單）

| # | 名稱 | 檔案 | Step | Owner | 種類 |
|---|------|------|------|-------|------|
| N1 | inventory enrichment | `core/providers/filesystem_provider.py`<br>`core/models/scan.py` | 2 | [`16`](./16-implement-understand-anything-sidecar-service.md) Task 2 | **改既有檔** |
| N2 | `UnderstandAnythingAnalysisService` | `core/services/understand_anything_analysis_service.py` | 3 | [`16`](./16-implement-understand-anything-sidecar-service.md) Task 3 | **新檔** |
| N3 | `UaStructuralAdapter` | `core/services/ua_structural_adapter.py` | 3 | [`16`](./16-implement-understand-anything-sidecar-service.md) Task 3 | **新檔** |
| N4 | `ComponentResidenceIndex` | `core/services/component_residence_index.py` | 4 | [`16C`](./16C-component-attribution-and-edge-derivation.md) Task 1 | **新檔** |

### N1 — inventory enrichment（Step 2）

替 `FileInventory` 每筆補上 `language` / `file_category` / `size_lines`，
供 UA request 的 `files[]` 使用。

- **移植自** `scan-project.mjs` 的 enrichment 邏輯；**該腳本本身不執行**
- **不得**改變 boundary policy——可掃描檔案仍由 Step 2 決定
- binary / large / generated / ignored 檔案維持 skip audit trail
- Windows / macOS path normalization 與 encoding fallback 要有 focused test

### N2 — `UnderstandAnythingAnalysisService`（Step 3）

Python 端的 subprocess 編排者，內含三個子元件：

```text
NodeRuntimePreflight          檢查 Node executable / script path / 版本 / 執行權限
                              以及 @understand-anything/core 的 dist 產物是否存在
                              （submodule 未 build 時三支 script 必死於 module load）
UnderstandAnythingSubprocessRunner
                              固定 argument list、shell=False、timeout
                              bounded stdout/stderr + redaction
UnderstandAnythingResultValidator
                              驗 schema / path allowlist / line ranges / stats
                              / batch completion
```

- **fail-closed**：schema 不合法、Node runtime 缺失、必要 batch 失敗 → 停止進入 Step 4
- **不得**寫入 target repo（含 `.understand-anything/` 暫存目錄）
- 實測 I/O 與 runtime 需求見 [`16B`](./16B-ua-sidecar-io-adapter-reference.md) §3

### N3 — `UaStructuralAdapter`（Step 3）

把 UA 的 import map / symbols / endpoints / resources / call hints
翻成 Systograph 的 `ScanFact` / `Evidence` / `Issue`。**整批整合的正確性樞紐。**

`rule_id` 穩定前綴：`ua_import_*`、`ua_symbol_*`、`ua_endpoint_*`、`ua_call_hint_*`。

**三條硬規則（16B §5.1，違反任一整條路白接）：**

| 規則 | 內容 | 違反後果 |
|------|------|----------|
| A | 每個 `ScanFact` 必須配一筆 `(file, path, kind, rule_id)` 四元組完全一致的 `Evidence` | Step 4 bridge 回 `NO_MATCH`，fact 被**靜默丟棄** |
| B | UA 自帶行號的欄位必須填 `Evidence.line_start` 才算 `direct`；`import_map` 無行號者誠實維持 `indirect` | 捏造行號 = 假造 `detected` 五態 |
| C | evidence id 由內容決定，同 repo 狀態跨次重跑必須相同 | Apply 的 `ManualMapping.evidence_ids` 子集檢查會壞 |

- **不得**用「兩端 component 證據聯集」假裝成 call wiring（16A Lv2 要求真 call-site）
- 實作前必讀 [`16E`](./16E-ua-coverage-gaps-and-llm-boundary.md) §5（證據來源硬化）

### N4 — `ComponentResidenceIndex`（Step 4）

回答「哪個元件住在哪個檔案的哪個函式區間」——這句話今天在 codebase 裡一行都不存在，
是檔案層跨到元件層的唯一橋樑。

```text
輸入   components + evidence + ua_symbol_* facts
輸出   by_component / by_file / by_span   (frozen dataclass)
       Residence(file, span: tuple[int,int] | None)
```

- 歸屬最小單位是**函式區間**，不是檔案（一個檔常同時住多個元件）
- `enclosing_function_span` 取**最小**包含區間；巢狀函式取最內層
- 找不到函式 → `span=None`，代表模組頂層宣告（見 16C §5 風險 1）
- 服務檔頭要補「責任 / 呼叫鏈」結構化註解（`core/services/` 慣例）

---

## 4. 同批新增、但圖上未標 `NEW` 的（次清單）

圖上為了可讀性沒逐一標記，但同屬本批的新產出。開工排期時要一起算進去。

| 名稱 | 檔案 | Step | Owner | 備註 |
|------|------|------|-------|------|
| UA request / result 模型 | `core/models/ua_analysis.py` | 3 | `16` Task 1 | 含兩份 schema（見下列） |
| UA request schema | `schemas/systograph-ua-request.v1.schema.json` | 3 | `16` Task 1 | unknown fields 預設拒絕 |
| UA result schema | `schemas/systograph-ua-result.v1.schema.json` | 3 | `16` Task 1 | 禁 raw source / 絕對路徑 / secret |
| `compute-batches` patch | `sidecar/patches/compute-batches-workdir.patch` | 3 | `16` Task 4 | 唯一的 vendored 樹改動；不複製檔案 |
| sidecar 安裝腳本 | `scripts/setup_ua_sidecar.sh` | 3 | `16` Task 4 | submodule init → pnpm install → core build → `git apply` |
| `ast_construction_provider.py` | `core/providers/ast_construction_provider.py` | 3 | `16E` §2.3 / §4.3（G1 + G3） | 形狀對齊 `code_pattern_provider.py` |
| relationship 規則表 | `core/rules/edge_relationship_rules.toml` | 4 | `16C` Task 2 | 用既有 `RuleCatalogLoader`，不新造 loader |
| `UaEdgeDerivationService` | `core/services/ua_edge_derivation_service.py` | 4 | `16C` Task 3～5 | L1 `observed` / L2 `undetermined` 邊推導（+ 過渡期 L3 降級） |

> ✅ **2026-08-04 裁定（原為兩個未定案問題，見 [`16B`](./16B-ua-sidecar-io-adapter-reference.md) §6.1）：**
>
> - **不做 `systograph-analyze.mjs` wrapper。** Python 直接依序 spawn 三支 script；
>   16B §4 的膠水責任全部落在 Python。**Systograph 自有 `.mjs` 檔案數 = 0。**
> - **`compute-batches.mjs` 以 patch 檔改，不複製檔案。** 樹外 fork 會同時斷掉
>   `@understand-anything/core`（`PLUGIN_ROOT` 由 `__dirname` 推導）與 `graphology`
>   兩個靜態 bare import，且要背 588 行的永久 rebase 負擔。
> - **work-dir = 系統暫存目錄，掃完刪除。** 中間檔含目標 repo 的檔案清單與符號名，
>   屬 privacy 保護對象；要留存的是 `ua-analysis-result.json`，走既有 snapshot 機制。
>
> **已知副作用：** `git status` 會顯示 submodule modified。**不得 stage gitlink。**

> ⚠️ **`ast_construction_provider.py` 可以先做。** 它是 16E 裁定中唯一「不必等 Gate」的項目，
> 而且照 16E §2.7，只要沿用既有 `rule_id` / `kind`，`component_bridge_rules.py` 的
> 13 條規則**一行都不用改**。

---

## 5. 明確**不**新增、只改既有檔的部分

列出來是為了避免 review 時誤以為要新造模組。

| 計畫 | 動到什麼 | 是否新檔 |
|------|----------|----------|
| [`16D`](./16D-call-priority-consumer-cutover.md) 全篇 | `system_map_v2_materialization_service.py`、`map_build_pipeline.py`、`system_map_v2_normalize_service.py`、靜態執行產出檔 | **全部否** |
| `16D` Task 6 | 前端只做冒煙測試 + 可選視覺微調 | **否**，不改 GraphViewModel 欄位 |
| `16C` 的資料模型 | `CanonicalEdge.status` / `undetermined_reason` / `evidence_ids` / `relationship` 四個欄位都已存在 | **否**，不改 schema |
| `16E` G1 的 bridge 規則 | `component_bridge_rules.py` 13 條規則 | **否**，零改動 |
| `16` Task 4 的 JS 面 | 三支 UA script 留在 vendored 樹原位執行 | **否**，Systograph 自有 `.mjs` = 0，只有一份 patch |

**一句話：** 這批的新模組全部集中在 Step 3 與 Step 4；Step 5～9 只有行為變準，
沒有新檔案，前端契約完全不動（16A 的核心論點）。

---

## 6. 開工順序與硬前置

```text
可以現在做（不等 Gate）
  16E G3 + G1   ast_construction_provider.py
                外部 import 邊：indirect -> direct，零 LLM
       |
       v
Gate-1 通過後
  16 Task 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7      N1 / N2 / N3 落地
       |
       |  併行前置（不依賴 UA，可提前完成）
       |    13.7  bridge kind -> 52 格字彙對齊
       |    13.8  profile relationship 端點約束
       v
  16C Task 1 -> 7                              N4 + 邊推導落地
       |
       v
  16D Task 1 -> 7                              下游改「呼叫優先」
```

| 前置 | 不做的後果（已實測） |
|------|----------------------|
| 13.7 | UA 掃得再準，52 格照樣點不亮（今天 4/52 靠 legacy slot 撐，拆掉後 1/52） |
| 13.8 | 邊從 12 條放大到數百條，無端點約束時假陽性同步放大 |
| 16E §5 證據來源硬化 | 16C 的兩級證據分級失去正確性前提 |

---

## 7. 相關文件

| 檔案 | 為什麼要知道 |
|------|--------------|
| [`README.md`](./README.md) | 本資料夾閱讀指南 + 名詞對照表 |
| [`16`](./16-implement-understand-anything-sidecar-service.md) | N1 / N2 / N3 的 Task 本體 |
| [`16B`](./16B-ua-sidecar-io-adapter-reference.md) | 三支 script 實測 I/O、adapter 三條硬規則、§6 裁定紀錄與剩餘 Q3～Q5 |
| [`16C`](./16C-component-attribution-and-edge-derivation.md) | N4 與兩級證據設計（L1=`observed` 算接線／L2=`undetermined` 不算） |
| [`16E`](./16E-ua-coverage-gaps-and-llm-boundary.md) | `ast_construction_provider` 的裁定與 LLM 邊界 |
| [`16G`](./16G-retire-template-flow-derivation.md) | 本檔的反向操作：這批之後要**刪掉**什麼（模板猜測邊） |
| [`../../../phase4-scanner-expansion/00-phase2-pipeline-ascii-map.md`](../../../phase4-scanner-expansion/00-phase2-pipeline-ascii-map.md) | Step 1～9 的視覺 source of truth（本檔兩張圖與它對齊） |
| `ref-opensource/systograph-understand-anything-integration-boundary.md` | **最高權威**，任何衝突以它為準 |
