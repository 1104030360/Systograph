# 16B — UA Sidecar 實測 I/O 與 Adapter 技術參考

Status: **reference recorded**（2026-07-29）— Plan 16 的技術參考附件，非獨立實作 plan。

> **對象：** Plan 16 執行者（Task 1/3/4/6 的直接輸入）
> **性質：** 實測查核紀錄；**不**改產品碼
> **來源：** 2026-07-29 三路查核 —— (a) vendored submodule 三支 script 原始碼逐行讀
> （pinned commit `73559a1`，plugin v2.8.2）、(b) `src/kai_mind/` 掃描管線程式碼、
> (c) boundary decision record 全文
> **權威順序：** `ref-opensource/kai-mind-understand-anything-integration-boundary.md`
> （Accepted）> [`16`](./16-implement-understand-anything-sidecar-service.md) > 本檔。
> 本檔只記「實測為何」；若與 boundary doc 衝突，以 boundary doc 為準並回報。

---

## 1. 全景圖：四個關鍵位置

```text
====================================================================================
              UA-PRIMARY SCAN - FULL PICTURE (Plan 16, Phase B/C)
====================================================================================

 KAI-MIND SIDE (Python, src/kai_mind/)          UA SIDECAR SIDE (Node >= 22)
 --------------------------------------         ------------------------------------

 Step 2  Boundary gate（核心不變）
    |      => FileInventory (approved allowlist)
    |      + NEW enrichment: language / file_category / size_lines
    |        （移植自 scan-project.mjs；scan-project.mjs 本身永不執行）
    v
 Step 3  UnderstandAnythingAnalysisService     <== [K1] KAI 接入點（新增）
    |     | (1) NodeRuntimePreflight  -- Node 缺失 => fail-closed
    |     | (2) 產生 kai-mind-ua-request/v1
    |     | (3) SubprocessRunner (shell=False, timeout)
    |     |        |
    |     |        v
    |     |   node kai-mind-analyze.mjs         <== [U0] UA 起點（新增 wrapper）
    |     |     --project-root / --inventory / --work-dir / --output
    |     |        |
    |     |        |  [U1] extract-import-map.mjs      （原樣沿用）
    |     |        |  [U2] 合成 scan-result.json       （wrapper 膠水）
    |     |        |  [U3] compute-batches.mjs         （必須 fork，見 §3.2）
    |     |        |  [U4] extract-structure.mjs       （原樣沿用，逐 batch）
    |     |        v
    |     |   kai-mind-ua-result/v1             <== [U5] UA 輸出點
    |     |
    |     | (4) ResultValidator  -- schema + path allowlist，fail-closed
    |     | (5) UaStructuralAdapter              <== [K2] Adapter（轉換點）
    |     |       UA structural -> ScanFact / Evidence / ParseIssue
    |     v
    |   ProjectScanResult
    |   [Phase B: TOML providers 陪跑 -> parity report，非 canonical]
    v
 ScanSnapshot                                   <== [K3] 落盤點
    |   .scan_result        = ProjectScanResult （Step 4-7 / Apply 只讀這個）
    |   .ua_analysis_result = wrapper JSON      （可選留存，追溯用）
    v
 Step 4-7 / Step 8  完全不變
```

---

## 2. KAI 側已驗證接縫（2026-07-29 對 codebase 實測）

### 2.1 接縫早已預留（Plan 03A 產物，全部存在且有測試覆蓋）

| 錨點 | 位置 | 現況 |
|------|------|------|
| `ScanSnapshot.ua_analysis_result` | `core/models/analysis_history.py:55` | `dict[str, Any] \| None = None` |
| `ScanSnapshotManifest.ua_analysis_available` | `core/models/analysis_history.py:86` | boolean，manifest 只暴露有無 |
| `scan_and_save(..., ua_analysis_result=)` | `core/services/scan_snapshot_service.py:61,116` | 參數已通到 snapshot |
| Web 路由的孔位 | `web/routes/scan_routes.py:294` | 字面 `ua_analysis_result=None`——**這行就是 Plan 16 要換掉的地方** |
| Approved `FileInventory` 誕生點 | `core/services/inventory_selection_materializer.py:182-207` | 唯一產生處；`scan_routes.py:261-264` 取用 |

`src/` 目前沒有任何模組 import `ref-opensource/`；`UnderstandAnythingAnalysisService`
與 `UaStructuralAdapter` 皆尚未存在。

### 2.2 為什麼不能只做成一個普通 provider（fail-closed 衝突）

現有最窄介面是 `ScanResultProvider` Protocol（`core/services/project_scan_service.py:51-56`）：

```python
class ScanResultProvider(Protocol):
    def collect(self, inventory: FileInventory) -> ProviderScanResult: ...
```

四個 TOML providers 都只實作這個介面，理論上 UA 也能直接插進 provider tuple——但
`ProjectScanService` 的 loop 會**吞掉 provider 例外**（`:155-161` 降級成
`ParseIssue("project_scan_provider_failed")` + warning 繼續跑），與 Plan 16 Task 6
的 fail-closed 要求相反。**所以 UA 必須由 `UnderstandAnythingAnalysisService` 在
provider loop 之上包住，失敗直接 raise，不得依賴 provider 例外路徑。**

### 2.3 Apply 重放契約（UA 結果為何必須進 `scan_result`）

- `ApplyConfirmationsService.apply`（`core/services/apply_confirmations_service.py:60-139`）
  只從快照拿 `scan_result` 重放；`ua_analysis_result` 永遠不被 Step 4-7 / Apply / Viewer 讀取。
- Apply 會驗證 `ManualMapping.evidence_ids ⊆ {e.id for e in snapshot.scan_result.evidence}`
  （`:167-170`）。**因此 Adapter 產生的 evidence id 必須由內容決定（deterministic），
  對同一份 repo 狀態跨次重跑保持穩定**——否則使用者已確認的 mapping 會全部失效。
- 快照不可變：同 id 重存不同內容會 `StateConflictError`（`local_json_history_repository.py:53-58`）。

### 2.4 CLI 路徑的缺口

`kai-mind map`（`cli/map_command.py:63`）直接呼叫 `MapBuildService.build()`——
**沒有 boundary gate、沒有 snapshot**。UA 接入 web 路徑後，CLI 是否也走 UA
（以及怎麼補 gate）是 open question，見 §6。

---

## 3. UA 三支 script 實測 I/O（讀原始碼確認，pinned `73559a1`）

只採用 Phase 1 的三支 deterministic script。不採用：`scan-project.mjs`（會變成第二個
掃描邊界；只移植其 enrichment 邏輯）、`file-analyzer`（LLM，Plan 17）、Phase 3-7 全部。

### 3.1 `extract-import-map.mjs`（原樣沿用，路徑乾淨）

```text
CLI : node extract-import-map.mjs <input.json> <output.json>     （純 positional）
in  : { "projectRoot": "/abs/path",
        "files": [ {"path":"src/a.py","language":"python","fileCategory":"code"} ] }
out : { "scriptCompleted": true,
        "stats": { "filesScanned": 314, "filesWithImports": 142, "totalEdges": 487 },
        "importMap": { "src/a.py": ["src/b.py"], "README.md": [] } }
```

- `importMap` 對每個輸入檔都有 key（非 code 檔為 `[]`）；值**只含 repo 內部解析路徑**，
  外部套件全部丟棄——所有候選都經 `fileSet` 過濾，**天然閉合在 inventory 白名單內**。
- `files[].language` 是 **load-bearing**：驅動 resolver 分派表（typescript / javascript /
  tsx / jsx / vue / python / go / java / kotlin / csharp / swift / php / rust / c / cpp /
  ruby）。**寫錯不報錯，只是該語言 import edge 全部靜默消失。**
- `fileCategory !== "code"` 直接短路成 `[]`；`sizeLines` 此 script 不讀。
- 解析上下文（tsconfig / go.mod / Package.swift / composer.json）**只讀 `files[]` 內
  已存在的檔**，不會自行踩出白名單。
- stdout 恆空；警告走 stderr（`Warning: extract-import-map: ...`）。

### 3.2 `compute-batches.mjs`（⚠️ 唯一違反 read-only，必須 fork）

```text
CLI : node compute-batches.mjs <project-root> [--changed-files=<path>]
in  : <project-root>/.understand-anything/intermediate/scan-result.json   （寫死！L364）
      { "files": [ {path, language, sizeLines, fileCategory} ],
        "importMap": { "<path>": ["<resolvedPath>"] } }
out : <project-root>/.understand-anything/intermediate/batches.json       （寫死！L550）
      { "schemaVersion": 1, "algorithm": "louvain" | "count-fallback",
        "totalFiles": 314, "totalBatches": 27,
        "exportsByPath": { "src/a.py": ["main"] },
        "batches": [ { "batchIndex": 1, "files": [...],
                       "batchImportData": {...}, "neighborMap": {...} } ] }
```

Fork 需求（boundary doc §7 已裁定「改成明確 input/output/work-dir」，實測補充）：

1. 輸入輸出路徑寫死在 `<target>/.understand-anything/intermediate/`——會**讀寫目標
   repo**，違反 read-only。fork 需加 `--input` / `--output` / `--work-dir`。
2. **必須保留 source-root 參數**：`extractExports()`（L51-121）真的會
   `readFile(join(projectRoot, file.path))` 讀原始碼、跑 tree-sitter 抽 export 符號
   （供 `neighborMap[].symbols`）。所以 `projectRoot` 不只是 JSON 容器，
   單純換掉輸入輸出路徑不夠。
3. `scan.files` 缺失時 L544 直接 TypeError crash（非優雅降級）——wrapper 合成
   `scan-result.json` 時 `files` 必須存在。
4. 環境變數 `UA_COMPUTE_BATCHES_FORCE_LOUVAIN_THROW=1` 可強制走 count-fallback
   （測試有用；production 環境不得洩入）。

Batching 語意（adapter / runner 必須尊重）：

| 規則 | 內容 |
|------|------|
| 分群 | code 檔走 Louvain（無向圖、邊來自 importMap）；超過 `MAX_COMMUNITY_SIZE=35` 按字母序切塊 |
| 排序 | 社群依大小降冪（同大小取最小路徑字典序）；batch 內檔案字典序；全部 1-based 重編號 |
| 非 code 分組 | Dockerfile 目錄群 / GitHub workflows / GitLab CI / migrations SQL（皆不可合併）→ 其餘按父目錄、每批最多 20 |
| 小批合併 | `mergeable` 且 <3 檔者併入 misc 批（每批 ≤25）；stderr 記 `Info:` 非 `Warning:` |
| 大小單位 | **只算檔案數**——`sizeLines` 從未被讀取，沒有 token/byte 預算 |
| `neighborMap` | 跨 batch 1-hop；`MAX_NEIGHBORS=50` 截斷會發 `Warning:` 點名檔案——**必須轉成 issue，不得靜默丟**（BD §4.2） |
| `--changed-files` | `batchIndex` 刻意不重編（可能不連續）、`totalFiles` 仍為全量——不可假設連續或加總相等。Apply 不重跑 UA，此模式 Phase 2 應該用不到 |
| 決定性 | 全流程 byte-for-byte 可重現（上游測試有 assert）——這是 evidence id 穩定性的基礎 |

### 3.3 `extract-structure.mjs`（原樣沿用，路徑乾淨；逐 batch 執行）

```text
CLI : node extract-structure.mjs <input.json> <output.json>       （純 positional）
in  : { "projectRoot": "...",
        "batchFiles": batches[i].files,
        "batchImportData": batches[i].batchImportData }
out : ua-file-extract-results-<batchIndex>.json
      { "scriptCompleted": true, "filesAnalyzed": 5, "filesSkipped": [],
        "results": [ /* 逐檔記錄，見下 */ ] }
```

逐檔記錄（base 欄位恆在；其餘**空陣列時整個 key 省略**）：

```jsonc
{
  "path": "src/a.py", "language": "python", "fileCategory": "code",
  "totalLines": 150, "nonEmptyLines": 120,
  "functions":  [{ "name":"main","startLine":10,"endLine":45,"params":["cfg"] }],
  "classes":    [{ "name":"App","startLine":50,"endLine":140,
                   "methods":["run"],"properties":["cfg"] }],
  "exports":    [{ "name":"App","line":50,"isDefault":false }],
  "endpoints":  [{ "method":"GET","path":"/users/{id}","startLine":40,"endLine":58 }],
  "services":   [{ "name":"api","image":"node:22","ports":[8080],
                   "startLine":4,"endLine":19 }],
  "sections":   [...], "definitions": [...], "steps": [...], "resources": [...],
  "callGraph":  [{ "caller":"main","callee":"init","lineNumber":15 }],
  "metrics":    { "importCount":5, "functionCount":4, ... }
}
```

- `callGraph` 只在 `fileCategory ∈ {code, script}` 時嘗試抽取；失敗**非致命、靜默為缺**。
- `filesSkipped` 只收 `readFileSync` 丟例外的檔（ENOENT/EACCES），不是「二進位跳過」。
- 結構抽取的分派 key 是**副檔名/檔名**（非 `language` 欄位）——language 標錯只壞
  import 解析，不壞結構抽取。
- `sizeLines` 不讀（行數重算）；`batchImportData` 只用來算 `metrics.importCount`，可缺。

### 3.4 Runtime 需求（NodeRuntimePreflight 的檢查清單來源）

| 項目 | 實測 |
|------|------|
| Node | `>= 22`（ESM、top-level await、`node:` builtins） |
| **Build 狀態** | **submodule 目前未 build**：無 `node_modules`、無 `packages/core/dist/`。三支 script 都 `await import('@understand-anything/core')`，現在直接跑必死（top-level rejection，在 main() 的 try/catch 之前）。需先於 submodule 根目錄 `pnpm install && pnpm --filter @understand-anything/core build`（pnpm 10 workspace） |
| `pluginRoot` 解析 | `resolve(__dirname, '../..')`——**把三支 .mjs 複製出樹外會壞掉 core 解析**；必須留在 plugin root 下兩層（或 patch 該常數） |
| tree-sitter | `web-tree-sitter`（WASM，非 native）；14 種語言 grammar 來自 npm + 2 個 workspace 內建 WASM（dart/swift） |
| 降級模式 | 單一 grammar 載入失敗**靜默降級**（該語言無結構分析）；整體 init 失敗時 `extract-import-map` 仍 exit 0 但 importMap 全空 → **`scriptCompleted:true` 不等於成功**，Validator 必須另看 `stats.totalEdges` / stderr（BD §8.7 fail-closed） |
| mkdir | **三支 script 都不會自建輸出目錄**——runner 每次呼叫前要先 `mkdir -p` work dir |
| Process 紀律 | stdout 恆空；log 全走 stderr；fatal 一律 exit 1 |

---

## 4. `kai-mind-analyze.mjs` wrapper 的膠水責任（Task 4 輸入）

```text
 [U1] extract-import-map  ->  importMap
            |
            v
 [U2] 合成 scan-result.json = { files:(inventory 含 sizeLines), importMap:(原樣) }
      （上游這份 JSON 由 LLM agent 拼裝；KAI 改由 wrapper 決定性拼裝，
        files 與 importMap 必須原樣傳遞、不得增刪改）
            |
            v
 [U3] compute-batches(fork)  ->  batches.json
            |
            v  （loop：逐 batch，以 batchIndex 為 key）
 [U4] extract-structure  ->  ua-file-extract-results-<batchIndex>.json
            |
            v
 [U5] 收攏成 kai-mind-ua-result/v1（semantic 恆 null）
```

| # | 責任 | 原因 |
|---|------|------|
| 1 | snake_case ⇄ camelCase 轉換 | KAI request 是 `size_lines`/`file_category`；UA 內部是 `sizeLines`/`fileCategory`（BD §3.2.A 兩邊皆有示例） |
| 2 | 決定性合成 `scan-result.json` | 上游無此接合產物（LLM agent 拼的）；KAI 必須自拼 |
| 3 | 逐 batch 呼叫並以 `batchIndex` 收檔 | `batchIndex` 1-based；`--changed-files` 下可能不連續 |
| 4 | 每步前 `mkdir -p` work dir | 三支 script 都不自建目錄 |
| 5 | 絕不執行 `scan-project.mjs` | 它會自己 walk 檔案樹，破壞「KAI inventory 是唯一白名單」 |
| 6 | stderr 全量收集、限量、轉交 | stderr 是唯一警告通道；截斷/降級訊息必須進 warnings（不得靜默丟） |

---

## 5. `UaStructuralAdapter` 硬規則（Task 3 輸入）

### 5.1 三條生死攸關規則（不做對，整條 pipeline 白接）

**規則 A — 四元組對齊。** Step 4 的 `EvidenceLookup.ids_for_fact`
（`component_detection_service.py:163-173`）用 `(file, path, kind, rule_id)` 四元組
join fact 與 evidence；join 不到 → `ComponentBridgeRegistry.match` 對空 `evidence_ids`
直接回 `NO_MATCH`（`component_bridge_registry.py:42-45`）→ **fact 被靜默丟棄**。
Adapter 產生每個 `ScanFact` 時必須同時產生四欄位完全一致的 `Evidence`。

**規則 B — direct 證據門檻。** `canonical_evidence_from_scan`
（`canonical_evidence_service.py:26-31`）：

```python
evidence_kind = "direct" if (file is not None and
                             (line_start is not None or json_pointer is not None))
                else "indirect"
```

五態規則裡 `detected` **只認 direct**；indirect 最多到 `partial`，且下游無任何機制
可升級。UA 的 `functions/classes/exports/endpoints/services/callGraph` 都自帶行號
→ **必須填進 `Evidence.line_start`**。`import_map` 沒行號 → 誠實維持 indirect，
**不得捏造行號**（evidence-based 原則）。

**規則 C — evidence id 穩定。** id 必須由內容決定（如
`hash(rule_id, file, symbol, line)`），跨次重跑同一 repo 狀態必須相同——否則 Apply 的
`ManualMapping.evidence_ids` 子集檢查（§2.3）會讓已確認 mapping 全部失效。
UA batching 全程 byte-for-byte 決定性（§3.2），穩定 id 有基礎。

### 5.2 欄位映射表（BD §4.2 裁定 + rule_id 前綴）

```text
 UA 欄位                          rule_id 前綴      -> KAI 去向
 -------------------------------  ----------------  --------------------------------
 import_map[src] -> dst           ua_import_*       import fact + evidence
                                                    （file-level 無行號 => indirect）
 functions / classes / exports    ua_symbol_*       symbol fact + evidence
                                                    （有 startLine => 可 direct）
 endpoints / services /           ua_endpoint_*     provider fact + evidence
   resources / definitions                          （不得決定 component slot）
 callGraph {caller,callee,line}   ua_call_hint_*    static call hint fact + evidence
                                                    （不得宣稱 runtime；16A Lv2 原料）
 warnings / filesSkipped /        （不適用）        ParseIssue / warnings
   stderr 截斷訊息                                  （不得靜默丟棄）
```

禁止輸出：`plane_id`、reference node id、profile 五態、`confidence`、runtime 結論
（BD §4.2；相關名不得自創，見 16A §7.2）。

### 5.3 白名單與安全（Task 5 輸入）

- UA result 每個 path 必須落在 approved inventory；拒絕 `..`、絕對路徑注入、
  symlink 逃逸、NUL、跨 drive path。
- stderr/stdout 限量 + secret masking + path redaction 後才可進 artifacts；
  `ua_analysis_result` 留存前同樣過 `LocalJsonSnapshotSafety.sanitize`（既有機制，免費）。

---

## 6. Open questions（動工前需裁定）

| # | 問題 | 衝突點 |
|---|------|--------|
| 1 | `kai-mind-analyze.mjs` 放哪 | Plan 16 Task 4 寫「`ref-opensource/understand-anything/` 或實際 vendored sidecar path」，但 `ref-opensource/CLAUDE.md` 規定該目錄不放 KAI 產品碼、submodule 是 pinned 不可改。且 §3.4：script 對 `pluginRoot` 有相對位置依賴。需裁定新家（例如 repo 根 `sidecar/`）與 script 路徑解析策略 |
| 2 | `compute-batches.mjs` fork 形式 | local fork / patch layer / 上游 PR？`ref-opensource/CLAUDE.md` 說 vendored 樹的修改應走 upstream 貢獻 |
| 3 | `kai-mind-ua-result/v1` 的 `stats` / `warnings` 內部形狀 | BD 留白為開放物件；Task 1 需定案（fail-closed + unknown fields 拒絕的前提是形狀有定義） |
| 4 | CLI `kai-mind map` 是否走 UA | CLI 路徑無 boundary gate 無 snapshot（§2.4）；若走 UA 需先補 gate，若不走需明文記錄行為差異 |
| 5 | UA 未 build 的 preflight 邊界 | `pnpm install + build` 是安裝時一次性動作還是 preflight 檢查項？（preflight 只該檢查、不該現場 build） |

---

## 7. 相關檔案

| 檔案 | 角色 |
|------|------|
| [`16-implement-understand-anything-sidecar-service.md`](./16-implement-understand-anything-sidecar-service.md) | S2 實作主 plan（本檔是其技術參考） |
| [`16A-q3-lv2-call-graph-flow-visualization.md`](./16A-q3-lv2-call-graph-flow-visualization.md) | Q3 Lv2 決策（call hints 的 why 與下游） |
| `ref-opensource/kai-mind-understand-anything-integration-boundary.md` | UA 整合邊界（Accepted，最高權威） |
| `ref-opensource/Understand-Anything/understand-anything-plugin/skills/understand/` | 三支 script 原始碼（pinned `73559a1`） |
| `src/kai_mind/core/services/project_scan_service.py` | `ScanResultProvider` Protocol 與 provider loop |
| `src/kai_mind/core/services/component_detection_service.py` | 四元組 join（規則 A 出處） |
| `src/kai_mind/core/services/canonical_evidence_service.py` | direct/indirect 判定（規則 B 出處） |
| `src/kai_mind/core/services/apply_confirmations_service.py` | evidence id 子集檢查（規則 C 出處） |
