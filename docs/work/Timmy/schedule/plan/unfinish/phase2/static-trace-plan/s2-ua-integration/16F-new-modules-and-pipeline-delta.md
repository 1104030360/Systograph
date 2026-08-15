# 16F — 新增模組清單與管線前後對照

> 📖 **第一次看？** 先讀 [`README.md`](./README.md)（閱讀順序 + 名詞對照表）。
> **白話一句話：** 這批計畫做完後，管線上「多出來的東西」總共有哪些、各自歸誰管。
> **這份不是實作計畫**，是查詢用的清單 + 兩張前後對照圖。

Status: reference（2026-08-04 建立）— **2026-08-10 已同步實作結果**。
內容全部從 `16` / `16C` / `16D` / `16E` / `16H` 抽取，不新增任何決策。
任一計畫本體有變更時，以計畫本體為準，本檔跟改。

> **2026-08-10 Phase 12 live sync（HEAD `da0d402`）：** 主清單擴為 N1～N8：
> N7 是 typed UA structural payload contract，N8 是 backend Viewer/static edge status
> projection。N1 owner 校正為 `models/filesystem.py::FileRecord`，N5 production 入口
> 校正為 `cli/map_command.py`。G3 external import 不再描述成 indirect→direct；
> import-only 固定 indirect，只有實際 call/constructor 目擊才可 direct。

> **2026-08-10 實作後校正：** UA 已進 active scan path，但 legacy providers 仍會
> 掃描、參與 parity 並與 UA facts 合併；只有 Plan 18 parity gate 通過後才可退役。
> canonical edges 已採 L1 > L2 > L3 call-priority merge；16G 實測為 NO-GO，故 L3
> transitional path 與開關仍在，不得把本圖讀成已完成退役。

> **2026-08-10 注記：** 本次同步補入 Plan 16 Task 8（CLI 非互動 gate＋snapshot）與
> [`16H`](./16H-ast-construction-provider.md)（`ast_construction_provider.py` 的實作計畫，
> 承接 G1/G2/G3），並把 16B §6 的「剩餘未裁定」敘述改為已收斂。
> 裁定出處見 [`CLARIFICATIONS-2026-08-10.md`](./CLARIFICATIONS-2026-08-10.md)（Q1／Q2／Q11）。

---

## 1. 為什麼需要這份

`16` / `16C` / `16D` / `16E`（＋2026-08-10 新增的 `16H`）合計 1600+ 行，
**新增的模組散落在各自的 Task 清單裡**，
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
|         normalize:183 stamps EVERY edge status="observed"  <-- lying   |
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

### 2.2 做完後（Plan 16 + 16C + 16D + 16H · Phase B/C）

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
Step 3  SCAN -- UA joins the active deterministic path     [Plan 16]
+------------------------------------------------------------------------+
| NEW  UnderstandAnythingAnalysisService (Python orchestrates subprocess)|
|        NodeRuntimePreflight -> SubprocessRunner -> ResultValidator     |
|                                                                        |
|        spawns the 3 scripts directly -- no .mjs wrapper                |
|          extract-import-map.mjs    who imports whom                    |
|          compute-batches.mjs       Louvain grouping  (Systograph patch)|
|          extract-structure.mjs     functions / classes / call hints    |
|          file-analyzer (LLM)       DEFERRED -- never executed          |
|        work-dir = system temp, deleted when the scan ends              |
|        -> ua-analysis-result.json  (semantic = null)                   |
|                                                                        |
| NEW  UaStructuralAdapter  ->  ScanFact + Evidence                      |
|        ua_import_*   file -> file, NO line number                      |
|        ua_symbol_*   function spans, startLine / endLine               |
|        ua_call_hint_*  caller -> callee @ line   <-- DIRECT evidence   |
|      + G3 external imports (16H, do this first)                        |
|                                                                        |
| EXISTING providers remain active + parity inputs until Plan 18 gate    |
| merged ProjectScanResult retains both provenances during transition    |
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
| 4-5  call-priority multi-source edge derivation:                       |
|        L1  call hint, has line -> direct   -> observed      COUNTS     |
|        L2  import, no line     -> indirect -> undetermined  IGNORED    |
|      only L1 feeds profile wiring evidence; L2 is honest-but-unusable  |
|      L3 template edges remain undetermined; 16G NO-GO blocks deletion  |
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
| 6-3  call_graph      fed from the canonical call-priority edge set     |
| 6-4  dataflow_hints  fed from the same canonical edge set              |
| 6-5  execution_paths/v2 stores the same full edge records              |
|      status/reason/evidence stay intact; no sibling recomputation      |
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

### 2.3 執行路徑（Rescan / Apply 前後相同；CLI 於本批被拉齊）

```text
Rescan   new preflight -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8   new snapshot, new scan_id
Apply    no preflight, no repo read -> 4-2 -> 5 -> 6 -> 7 -> 8  same scan_id, new build_id

CHANGED BY THIS BATCH                                            [16 Task 8]
CLI  before  systograph map -> MapBuildService.build() directly
             no boundary gate, no snapshot  <-- UA whitelist premise missing
CLI  after   systograph map -> non-interactive Step 2 gate -> 3 -> ... -> 7
             default policy auto-decide; blocked => fail-closed to Web review
             persists ScanSnapshot, same scan_id / lineage semantics as Web
```

> **Plan 16 Task 8（2026-08-05 Q4 裁定）：** CLI 立刻補 gate、直接走 UA，不留過渡期分歧。
> **已知代價（裁定時已接受）：本 task 進入 Gate-2 關鍵路徑**——Gate-2 的定義必須含 Task 8。

---

## 3. 主清單（N1～N8）

N1～N4 是 §2.2 圖上標 `NEW` 的四項；**N5～N8 為 2026-08-10 補列**，
§2.2 的方框圖尚未重繪（N5 見 §2.3；N6/N7 落在 Step 3；N8 橫跨 Step 4～7）。

| # | 名稱 | 檔案 | Step | Owner | 種類 |
|---|------|------|------|-------|------|
| N1 | inventory enrichment | `core/providers/filesystem_provider.py`<br>`core/models/filesystem.py` | 2 | [`16`](./16-implement-understand-anything-sidecar-service.md) Task 2 | **改既有檔** |
| N2 | `UnderstandAnythingAnalysisService` | `core/services/understand_anything_analysis_service.py` | 3 | [`16`](./16-implement-understand-anything-sidecar-service.md) Task 3 | **新檔** |
| N3 | `UaStructuralAdapter` | `core/services/ua_structural_adapter.py` | 3 | [`16`](./16-implement-understand-anything-sidecar-service.md) Task 3 | **新檔** |
| N4 | `ComponentResidenceIndex` | `core/services/component_residence_index.py` | 4 | [`16C`](./16C-component-attribution-and-edge-derivation.md) Task 1 | **新檔** |
| N5 | CLI 非互動 boundary gate + snapshot | `cli/map_command.py`<br>`cli/map_workflow.py`<br>`tests/cli/test_map_command.py` | 2→3 | [`16`](./16-implement-understand-anything-sidecar-service.md) **Task 8** | **新 workflow＋改既有檔／測試** |
| N6 | `ast_construction_provider.py`（G1 + G2 + G3） | `core/providers/ast_construction_provider.py`<br>`core/models/evidence_kind.py` + `core/models/system_map.py`<br>`core/rules/code_pattern_rules.toml` | 3 | [`16H`](./16H-ast-construction-provider.md) | **新檔＋改既有檔**；source 以 no-follow、descriptor-pinned safe-open 讀取 |
| N7 | typed UA structural payloads | `core/models/structural_fact.py`<br>`core/models/ua_analysis.py` | 3→4 | [`16`](./16-implement-understand-anything-sidecar-service.md) Task 1/3 + [`16C`](./16C-component-attribution-and-edge-derivation.md) | **新檔＋改既有檔** |
| N8 | edge status projection | `core/models/viewer.py`<br>`core/models/execution_artifact.py`<br>`core/services/graph_projection_service.py` | 4→7 | [`16D`](./16D-call-priority-consumer-cutover.md) Task 3/6 | **改既有檔**；`execution-paths/v2` 改存完整 canonical edge record |

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

### N5 — CLI 非互動 boundary gate + snapshot（Step 2→3）

`16` Task 8。今天 CLI map 命令直接呼叫 `MapBuildService.build()`，沒有 boundary gate、
沒有 snapshot；而 UA request 的白名單前提**就是** Step 2 的 `FileInventory`——
不補這一段，CLI 這條入口拿不到合法的 UA 輸入。

- 非互動模式：全部採 default policy 自動決策；`blocked` / 需人工決策時 **fail-closed**，
  錯誤訊息指向 Web review 流程
- CLI 產生並持久化 `ScanSnapshot`，與 Web 同一套機制（Apply / lineage 語意一致）
- **不得**在 CLI 複製 `inventory_*` 的邏輯，也不得自行 walk 檔案樹
- **排程影響：本項在 Gate-2 關鍵路徑上**（2026-08-05 Q4 裁定已接受此代價）

### N6 — `ast_construction_provider.py`（Step 3）

Owner 為 [`16H`](./16H-ast-construction-provider.md)（2026-08-10 Q1 裁定新開的實作計畫；
規格自 16E §2.3／§4.3／§7 抽取）。形狀對齊 `code_pattern_provider.py`，**零 LLM**。

```text
G3  外部 import declaration   import-only 固定 indirect，先做
G1  函式外的建構              繞開 UA extractor 的 functionStack 守衛
G2  工廠 / 間接建構           確定性 AST 推論（追進工廠函式，MAX_FACTORY_HOPS=3 起）
```

- **G2 為 2026-08-10 新裁定**（Q2）：取代 16E 決策 2 的「人工確認為主」——改走確定性程式推論，
  **非 LLM**；人工確認通道不刪，降為可選旁路
- **`Evidence.evidence_kind_hint` 是 G2 的必需前置**（16H Task 1，加性欄位）：
  誠實性三鎖＝分支不塌縮／全部標推論（hint→`indirect`）／
  節點最多 `partial`、邊為 `undetermined` 加專屬 `undetermined_reason`（如 `factory_inference`），
  不進 profile 接線證據（`profile_finding_assembler.py:214` 閘門不變）
- `code_pattern_rules.toml` 的 `symbol` 欄併入 16H PR 落地（Q4）——
  它是「符號 → (rule_id, kind) 身份證」的共用翻譯字典，供 regex／AST／UA adapter 三個生產者共用；
  沿用既有 `rule_id` / `kind` 即可讓 `component_bridge_rules.py` 的 13 條規則零改動
- 明示後果（owner 已知悉）：推論邊買到的是**圖的完整性**（虛線），卡片翻綠仍靠 L1 真呼叫點

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
| `ast_construction_provider.py` | `core/providers/ast_construction_provider.py` | 3 | [`16H`](./16H-ast-construction-provider.md)（G1 + G2 + G3） | 已升為主清單 **N6**；規格出處仍是 `16E` §2.3 / §4.3 / §7，形狀對齊 `code_pattern_provider.py` |
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
> **Lifecycle 邊界：** setup 套 patch 後，submodule 會暫時顯示 modified；測試／執行結束
> 必須用同一 patch 反套並確認 pin clean。**不得 stage gitlink。**

> ⚠️ **`ast_construction_provider.py` 可以先做（＝ [`16H`](./16H-ast-construction-provider.md)，見 N6）。**
> 它是唯一「不必等 Gate」的項目——2026-08-10 Q1 裁定後由 16H 承接並**立即可開工**。
> 照 16E §2.7，只要沿用既有 `rule_id` / `kind`，`component_bridge_rules.py` 的
> 13 條規則**一行都不用改**。
>
> **但 G3 那半是 `16` Task 3 的硬前置（Q6）**：G3 會新增 import-only structural
> facts；落在 parity 基線之後做仍會污染 diff。先做零成本，後做要重測基線。

---

## 5. 明確**不**新增、只改既有檔的部分

列出來是為了避免 review 時誤以為要新造模組。

| 計畫 | 動到什麼 | 是否新檔 |
|------|----------|----------|
| [`16D`](./16D-call-priority-consumer-cutover.md) 全篇 | `system_map_v2_materialization_service.py`、`map_build_pipeline.py`、`system_map_v2_normalize_service.py`、靜態執行產出檔 | **全部否** |
| `16D` Task 6 | 前端只做冒煙測試 + 可選視覺微調 | **否**，不改 GraphViewModel 欄位 |
| `16C` 的資料模型 | `CanonicalEdge.status` / `undetermined_reason` / `evidence_ids` / `relationship` 四個欄位都已存在 | **否**，不改 schema |
| `16H` G1/G2 的 bridge 規則 | `component_bridge_rules.py` 13 條規則 | **否**，零改動（前提＝沿用既有 `rule_id` / `kind`，見 N6） |
| `16` Task 4 的 JS 面 | 三支 UA script 留在 vendored 樹原位執行 | **否**，Systograph 自有 `.mjs` = 0，只有一份 patch |
| `16` Task 8 的 CLI 面 | `cli/map_command.py` 委派新 `cli/map_workflow.py` 共用既有 `inventory_*` services | **新增一個 workflow 檔＋改既有 command／測試**；不得複製 scanner 邏輯進 CLI |

**一句話：** 主要新 scanner 模組集中在 Step 3 與 Step 4；Step 5～9 的
`GraphViewModel` 欄位與 frontend production code 不動。Static JSON handoff 則有一項
刻意的 breaking contract：`execution_paths` 從 v1 node-id pairs 升為 v2 full edge
records，consumer 必須依更新後的 sample／README 讀取。
**Task 8（N5）是唯一動到 Step 2 入口的項目；它新增薄 `map_workflow.py` 編排層，
但沒有重造 inventory 或 scanner service。**

---

## 6. 開工順序與硬前置

```text
可以現在做（不等 Gate）
  16H          ast_construction_provider.py             N6
               Task 1  Evidence.evidence_kind_hint（G2 的必需前置）
               G3  外部 import declaration：import-only indirect，零 LLM
               G1  函式外的建構
               G2  工廠 / 間接建構：確定性 AST 推論，非 LLM
               + code_pattern_rules.toml 的 symbol 欄（同一 PR）
       |
       |  G3 那半是 16 Task 3 的硬前置（parity 基線一致性）
       v
Gate-1 通過後
  16 Task 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7      N1 / N2 / N3 / N7 落地
     Task 8（CLI 非互動 gate + snapshot）      N5，Gate-2 關鍵路徑
       |
       |  併行前置：13.7 / 13.8 皆已完成（2026-07-29），不再擋路
       v
  16C Task 1 -> 7                              N4 + 邊推導落地
       |
       v
  16D Task 1 -> 7                              下游改「呼叫優先」
       |
       v
  16G                                          刪 FlowDerivationService
```

| 前置 | 狀態 | 不做的後果（已實測） |
|------|------|----------------------|
| 13.7 | **✅ 已滿足（2026-07-29 done）** | UA 掃得再準，52 格照樣點不亮（當時 4/52 靠 legacy slot 撐，拆掉後 1/52） |
| 13.8 | **✅ 已滿足（2026-07-29 done；由回歸測試守護）** | 邊從 12 條放大到數百條，無端點約束時假陽性同步放大 |
| 16H Task 1（`evidence_kind_hint`） | **✅ 已完成（2026-08-10）** | G1 direct、G2/G3 indirect 的中立 hint 已由 contract tests 守護 |
| 16H 的 G3 | **✅ 已完成（2026-08-10）** | external import declaration 可追溯但不單獨點亮 component，已進 parity 基線 |
| `16` Task 8（CLI） | **✅ 已完成（2026-08-11）** | CLI 走共用 FileInventory、non-interactive gate、snapshot 與 UA 管線；`--help` 說明 Web review 邊界 |

---

## 7. 相關文件

| 檔案 | 為什麼要知道 |
|------|--------------|
| [`README.md`](./README.md) | 本資料夾閱讀指南 + 名詞對照表 |
| [`16`](./16-implement-understand-anything-sidecar-service.md) | N1 / N2 / N3 / **N5（Task 8）** / N7 的 Task 本體 |
| [`16D`](./16D-call-priority-consumer-cutover.md) | N8 backend Viewer/static status projection 與 consumer cutover |
| [`16B`](./16B-ua-sidecar-io-adapter-reference.md) | 三支 script 實測 I/O、adapter 三條硬規則、§6 裁定紀錄——**§6 已全數裁定（2026-08-05）**，無剩餘未決項 |
| [`16C`](./16C-component-attribution-and-edge-derivation.md) | N4 與兩級證據設計（L1=`observed` 算接線／L2=`undetermined` 不算） |
| [`16E`](./16E-ua-coverage-gaps-and-llm-boundary.md) | G1/G2/G3 缺口分析與 LLM 邊界＝**16H 的規格出處**（16E 本身非實作計畫；決策 2／決策 4 已被 2026-08-10 Q2 取代） |
| [`16H`](./16H-ast-construction-provider.md) | N6 的 Task 本體：`ast_construction_provider.py`＋`evidence_kind_hint`＋`symbol` 欄 |
| [`16G`](./16G-retire-template-flow-derivation.md) | 本檔的反向操作：這批之後要**刪掉**什麼（模板猜測邊） |
| [`../../../phase4-scanner-expansion/00-phase2-pipeline-ascii-map.md`](../../../phase4-scanner-expansion/00-phase2-pipeline-ascii-map.md) | Step 1～9 的視覺 source of truth（本檔兩張圖與它對齊） |
| `ref-opensource/systograph-understand-anything-integration-boundary.md` | **最高權威**，任何衝突以它為準 |
