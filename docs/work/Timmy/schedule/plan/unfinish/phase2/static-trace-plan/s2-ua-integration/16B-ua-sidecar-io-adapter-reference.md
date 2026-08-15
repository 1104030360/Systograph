# 16B — UA Sidecar 實測 I/O 與 Adapter 技術參考

> 📖 **第一次看？** 先讀 [`README.md`](./README.md)（閱讀順序 + 名詞對照表）。
> **白話一句話：** 三支 UA 腳本實際吃什麼、吐什麼，以及翻譯層有哪三條不能違反的死規則。
> **要動手寫 code 才需要細讀**；只是 review 的話可以跳過。

Status: **reference recorded**（2026-07-29）— Plan 16 的技術參考附件，非獨立實作 plan。

> **2026-08-10 Phase 12 live revalidation：** 本輪已初始化 submodule 並逐檔核對 pin
> `73559a160645359c57be44c174935899dec9f9f2`；本機 Node `v22.22.3`、pnpm
> `10.22.0`。確認 `scan-project.mjs` 會自行列舉檔案、`extract-import-map.mjs`
> 只保留 internal `fileSet` 邊、未 patch 的 `compute-batches.mjs` 會寫 target
> `.understand-anything/intermediate`，以及 Python extractor 只在 `functionStack`
> 非空時輸出 call。故 authoritative inventory、install-time patch、G1/G3 補充仍是
> 硬邊界。
>
> **結果驗證校正：** `totalEdges == 0` 不是 sidecar 失敗訊號；單檔、空專案或沒有
> internal dependency 的合法輸入可以誠實得到零邊。fail-closed 應依 process exit、
> schema/version、batch completion、structured error marker、approved-path invariant 與
> stderr policy 判定；零邊只記 stats，不單獨拒絕。stdout 只承載 JSON，stderr 必須
> 限量、遮罩 secret 與本機絕對路徑。

> **對象：** Plan 16 執行者（Task 1/3/4/6 的直接輸入）
> **性質：** 實測查核紀錄；**不**改產品碼
> **來源：** 2026-07-29 三路查核 —— (a) vendored submodule 三支 script 原始碼逐行讀
> （pinned commit `73559a1`，plugin v2.8.2）、(b) `src/systograph/` 掃描管線程式碼、
> (c) boundary decision record 全文
> **權威順序：** `ref-opensource/systograph-understand-anything-integration-boundary.md`
> （Accepted）> [`16`](./16-implement-understand-anything-sidecar-service.md) > 本檔。
> 本檔只記「實測為何」；若與 boundary doc 衝突，以 boundary doc 為準並回報。
> **2026-08-10 行號校正**（#277 合併後 `src/` 行號漂移，§2.1／§2.2 已更新）；
> 裁定補充見 [`CLARIFICATIONS-2026-08-10.md`](./CLARIFICATIONS-2026-08-10.md)。

---

## 1. 全景圖：四個關鍵位置

```text
====================================================================================
              UA-PRIMARY SCAN - FULL PICTURE (Plan 16, Phase B/C)
====================================================================================

 Systograph SIDE (Python, src/systograph/)          UA SIDECAR SIDE (Node >= 22)
 --------------------------------------         ------------------------------------

 Step 2  Boundary gate（核心不變）
    |      => FileInventory (approved allowlist)
    |      + NEW enrichment: language / file_category / size_lines
    |        （移植自 scan-project.mjs；scan-project.mjs 本身永不執行）
    v
 Step 3  UnderstandAnythingAnalysisService     <== [K1] Systograph 接入點（新增）
    |     | (1) NodeRuntimePreflight  -- Node 缺失 => fail-closed
    |     | (2) 產生 systograph-ua-request/v1
    |     | (3) SubprocessRunner (shell=False, timeout)
    |     |        |
    |     |        v
    |     |   Python 直接 spawn 三支 script     <== [U0] UA 起點（無 wrapper，§6 Q1）
    |     |     work-dir = 系統暫存目錄，掃完刪除
    |     |        |
    |     |        |  [U1] extract-import-map.mjs      （原樣沿用）
    |     |        |  [U2] 合成 scan-result.json       （Python 膠水，見 §4）
    |     |        |  [U3] compute-batches.mjs         （套 Systograph patch，見 §3.2）
    |     |        |  [U4] extract-structure.mjs       （原樣沿用，逐 batch）
    |     |        v
    |     |   systograph-ua-result/v1             <== [U5] UA 輸出點
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

## 2. Systograph 側已驗證接縫（2026-07-29 對 codebase 實測）

### 2.1 接縫早已預留（Plan 03A 產物，全部存在且有測試覆蓋）

| 錨點 | 位置 | 現況 |
|------|------|------|
| `ScanSnapshot.ua_analysis_result` | `core/models/analysis_history.py:57` | `dict[str, Any] \| None = None` |
| `ScanSnapshotManifest.ua_analysis_available` | `core/models/analysis_history.py:88` | boolean，manifest 只暴露有無 |
| `scan_and_save(..., ua_analysis_result=)` | `core/services/scan_snapshot_service.py:61,116` | 參數已通到 snapshot |
| Web 路由的孔位 | `web/routes/scan_routes.py` 中字面 `ua_analysis_result=None` 那行（現行 `:210`） | **這行就是 Plan 16 要換掉的地方**（行號易漂移，以字面錨點定位） |
| Approved `FileInventory` 誕生點 | `core/services/inventory_selection_materializer.py:182-207` | 唯一產生處；`scan_routes.py:186-188`（`selection.inventory` 取用處）接手 |

`src/` 目前沒有任何模組 import `ref-opensource/`；`UnderstandAnythingAnalysisService`
與 `UaStructuralAdapter` 皆尚未存在。

### 2.2 為什麼不能只做成一個普通 provider（與「失敗就停」的原則衝突）

現有最窄介面是 `ScanResultProvider` Protocol（`core/services/project_scan_service.py:51-56`）：

```python
class ScanResultProvider(Protocol):
    def collect(self, inventory: FileInventory) -> ProviderScanResult: ...
```

四個 TOML providers 都只實作這個介面，理論上 UA 也能直接插進 provider tuple——但
`ProjectScanService` 的 loop 會**吞掉 provider 例外**（`:157-163` 降級成
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

`systograph map`（`cli/map_command.py:63`）直接呼叫 `MapBuildService.build()`——
**沒有 boundary gate、沒有 snapshot**。
**2026-08-05 裁定（原 §6 Q4）：CLI 立刻補非互動 gate、直接走 UA**——
default policy 自動決策 + snapshot 落地，與 Web 共用同一條 Step 2 → 3 管線；
`blocked` 時 fail-closed 並指向 Web review。落地為 Plan 16 Task 8。

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
- **2026-08-05 native 實測驗證**：對 `basic_qdrant_ollama_rag` 副本跑通——
  `filesScanned=6 / totalEdges=1`（`app.py → retriever.py`，與源碼一致）；
  fastapi / qdrant_client / ollama 等外部套件正確排除（此即 16E G3 要另行撈回的那批）。

### 3.2 `compute-batches.mjs`（⚠️ 唯一違反唯讀保證，必須套 patch）

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

Patch 需求（boundary doc §7 已裁定「改成明確 input/output/work-dir」，實測補充；
patch 形式見 §6 Q2）：

1. 輸入輸出路徑寫死在 `<target>/.understand-anything/intermediate/`——會**讀寫目標
   repo**，違反 read-only。patch 需加 `--input` / `--output` / `--work-dir`。
   **是讀寫都違規**：`:364` 規定輸入檔必須位於目標 repo 內（我們得先寫一個檔進去
   它才讀得到），`:550` 再把 `batches.json` 寫回同一處。
   **不能靠傳假 project-root 迴避**——`extractExports()`（`:83`）會
   `readFile(join(projectRoot, file.path))` 真的讀原始碼跑 tree-sitter，
   `projectRoot` 必須是真實 repo。單一參數同時承擔「去哪讀原始碼」與
   「中間檔放哪」兩種語意，正是本問題的根因。
2. **必須保留 source-root 參數**：`extractExports()`（L51-121）真的會
   `readFile(join(projectRoot, file.path))` 讀原始碼、跑 tree-sitter 抽 export 符號
   （供 `neighborMap[].symbols`）。所以 `projectRoot` 不只是 JSON 容器，
   單純換掉輸入輸出路徑不夠。
3. `scan.files` 缺失時 L544 直接 TypeError crash（非優雅降級）——Python 合成
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
| Node | `>= 22`（ESM、top-level await、`node:` builtins）。2026-08-05 於 v22.22.3 驗證通過 |
| **Build 狀態** | 三支 script 都 `await import('@understand-anything/core')`，未 build 直接跑必死（top-level rejection，在 main() 的 try/catch 之前）。**2026-08-05 native 實測：`pnpm install` 於 submodule 根一步到位（root `prepare` hook 自動 `pnpm --filter @understand-anything/core build`；實測 install 1m52s、顯式 build 冪等可重跑 ~10s）。** pnpm 10 會依 root `packageManager` pin 自動下載並切換版本（實測 volta pnpm 10.22.0 → 自動改用 10.6.2），離線環境需預先備好 |
| `pluginRoot` 解析 | `resolve(__dirname, '../..')`——**把三支 .mjs 複製出樹外會壞掉 core 解析**（`@understand-anything/core` 靠 workspace symlink 解析，2026-08-05 實測證實）；必須留在 plugin root 下兩層（或 patch 該常數） |
| tree-sitter | `web-tree-sitter`（WASM，非 native）；14 種語言 grammar 來自 npm + 2 個 workspace 內建 WASM（dart/swift） |
| **Kotlin grammar 例外** | `@tree-sitter-grammars/tree-sitter-kotlin` 的 build script 被 pnpm 預設擋下（未 approve），該 grammar 不可用；其他語言 grammar 不受影響（2026-08-05 實測）。掃 Kotlin 專案前需手動 `pnpm approve-builds`——setup script **不自動** approve（避免默許任意 postinstall 執行）。未 approve 時 Kotlin 檔走「單一 grammar 靜默降級」路徑（見下列），Validator 需可觀測 |
| 降級模式 | 單一 grammar 載入失敗**靜默降級**（該語言無結構分析）；整體 init 失敗時 `extract-import-map` 仍 exit 0 但 importMap 全空 → **`scriptCompleted:true` 不等於成功**，Validator 必須另看 `stats.totalEdges` / stderr（BD §8.7 fail-closed） |
| mkdir | **三支 script 都不會自建輸出目錄**——runner 每次呼叫前要先 `mkdir -p` work dir |
| Process 紀律 | stdout 恆空；log 全走 stderr；fatal 一律 exit 1 |

---

## 4. 串接責任（膠水；Task 4 輸入）

> **2026-08-04（§6 Q1）：** 原規劃由 `systograph-analyze.mjs` wrapper 承擔本節責任，
> 已裁定**不做 wrapper**——下列六項全部由 Python
> （`UnderstandAnythingSubprocessRunner`）負責。責任內容不變，只換執行者。

```text
 [U1] extract-import-map  ->  importMap
            |
            v
 [U2] 合成 scan-result.json = { files:(inventory 含 sizeLines), importMap:(原樣) }
      （上游這份 JSON 由 LLM agent 拼裝；Systograph 改由 Python 決定性拼裝，
        files 與 importMap 必須原樣傳遞、不得增刪改）
            |
            v
 [U3] compute-batches(patched)  ->  batches.json
            |
            v  （loop：逐 batch，以 batchIndex 為 key）
 [U4] extract-structure  ->  ua-file-extract-results-<batchIndex>.json
            |
            v
 [U5] 收攏成 systograph-ua-result/v1（semantic 恆 null）
```

| # | 責任 | 原因 |
|---|------|------|
| 1 | snake_case ⇄ camelCase 轉換 | Systograph request 是 `size_lines`/`file_category`；UA 內部是 `sizeLines`/`fileCategory`（BD §3.2.A 兩邊皆有示例） |
| 2 | 決定性合成 `scan-result.json` | 上游無此接合產物（LLM agent 拼的）；Systograph 必須自拼 |
| 3 | 逐 batch 呼叫並以 `batchIndex` 收檔 | `batchIndex` 1-based；`--changed-files` 下可能不連續 |
| 4 | 每步前 `mkdir -p` work dir | 三支 script 都不自建目錄 |
| 5 | 絕不執行 `scan-project.mjs` | 它會自己 walk 檔案樹，破壞「Systograph inventory 是唯一白名單」 |
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

### 5.2 欄位對照表（BD = boundary doc 整合邊界文件 §4.2 裁定 + rule_id 前綴）

```text
 UA 欄位                          rule_id 前綴      -> Systograph 去向
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

> **2026-08-05（§6 Q6）：** 上表的 `ua_*` 前綴已正式裁定（不沿用 legacy id）。
> `ua_*` ↔ legacy `rule_id` 對照併入語彙目錄，每列同載兩組 id；
> parity 的 provenance 判定即以前綴為準。

> **2026-08-10（裁定 Q3）：** 上表 `warnings / filesSkipped / stderr 截斷訊息` 一列
> 產生的 `ParseIssue` 使用 `scan_stage="ua_structural_scan"`——
> `ParseIssue.scan_stage` Literal 的第 7 個值，由 Plan 16 Task 1 一併加入；
> AST provider（16H）依 16E 既有裁定沿用 `code_pattern_scan`。

### 5.3 白名單與安全（Task 5 輸入）

- UA result 每個 path 必須落在 approved inventory；拒絕 `..`、絕對路徑注入、
  symlink 逃逸、NUL、跨 drive path。
- stderr/stdout 限量 + secret masking + path redaction 後才可進 artifacts；
  `ua_analysis_result` 留存前同樣過 `LocalJsonSnapshotSafety.sanitize`（既有機制，免費）。

---

## 6. 待裁定問題（Open questions）

### 6.1 已裁定（2026-08-04）

| # | 問題 | 裁定 |
|---|------|------|
| 1 | `systograph-analyze.mjs` 放哪 | **不做這支 wrapper。** Python（`UnderstandAnythingSubprocessRunner`）直接依序 spawn 三支 script；§4 的膠水責任全部落在 Python |
| 2 | `compute-batches.mjs` fork 形式 | **patch 檔 + 安裝腳本。** 改動存成 `sidecar/patches/compute-batches-workdir.patch`，由 `scripts/setup_ua_sidecar.sh` 在安裝階段 `git apply` 到 submodule 工作樹 |
| — | work-dir 位置（原表未列，一併裁定） | **系統暫存目錄，每次掃描一個、掃完刪除。** 不落在 `src/systograph/`，也不落在 `~/.systograph/` |
| — | 部署形態（2026-08-05 裁定） | **Native**：Python（uv）+ 本機 Node 直接跑三支 script。Docker 化 deferred 另案，非本批 scope。裁定依據：2026-08-05 本機實測 end-to-end 跑通（見 §3.4 實測列與 Q5） |
| 5 | UA 未 build 的 preflight 邊界（2026-08-05 裁定，自 §6.2 移入） | **安裝階段一次完成、preflight 只檢查不建置。** `setup_ua_sidecar.sh` = submodule init → `pnpm install`（root `prepare` hook 自動 `--filter core build`，實測一步到位）→ `git apply` patch。preflight 只驗：Node >= 22、`packages/core/dist/` 存在、patch 已套（`git apply --check --reverse`）；任一缺失 fail-closed 並指向 setup script。setup script **不自動** `pnpm approve-builds`（Kotlin grammar 例外情況見 §3.4） |
| 3 | `stats` / `warnings` 內部形狀（2026-08-05 裁定，自 §6.2 移入） | **定型核心 + `extra` 逃生欄。** `stats` 核心欄位定型且 required（filesScanned / filesWithImports / totalEdges / totalBatches / algorithm / filesAnalyzed / per-batch 完成清單）；`warnings` 結構化 `{stage, message}`（遮罩、限量）；`extra` 為唯一開放容器——原樣傳遞、不驗證、**不消費**，契約測試保證其內容不流入 `ScanFact` / `Evidence` / 判定。unknown 拒絕範圍 = `extra` 以外全部層級。細節見 Plan 16 Task 1 |
| 4 | CLI `systograph map` 是否走 UA（2026-08-05 裁定，自 §6.2 移入） | **立刻補非互動 gate，CLI 直接走 UA**，不留過渡期分歧（已接受 Gate-2 關鍵路徑變重）。default policy 自動決策 + snapshot 落地；`blocked` fail-closed 指向 Web review。落地為 Plan 16 Task 8；現況缺口見 §2.4 |
| 6 | UA rule_id 命名與 fact provenance（2026-08-05 裁定，自 §6.2 移入） | **新 `ua_*` id；`ua_*` ↔ legacy 對照併入語彙目錄**（每列同載 legacy id / kind / symbol / ua id，單一 source of truth，同 16E §2.7 / 13.7 模式）。provenance 靠 rule_id 前綴天然可分，零 model 變更；bridge 鏡射項 = 01B「支援 UA rule_id」依賴的具體化（13.7 已 done，不回頭改它）。[Plan 18](../s3-retirement/18-retire-systograph-scan-toml-providers-after-parity.md) 的 parity gate 輸入需求不變 |

#### Q1 裁定理由

`pluginRoot = resolve(__dirname, '../..')` +
`createRequire(resolve(pluginRoot, 'package.json'))`（`compute-batches.mjs:28-29`，
另兩支同構）**鎖死三支 script 的位置**——這點無可迴避。但 wrapper 本身只是 spawn
三個子行程、不 import 任何 UA 模組，**沒有位置依賴**，所以「wrapper 該住哪」這個
衝突其實是 Plan 16 Task 4 措辭造成的，不是技術約束。

既然 wrapper 可以住任何地方，就該問它是否該存在。§4 列的膠水責任
（合成 `scan-result.json`、命名轉換、`mkdir -p`、per-batch 收檔、stderr 收集）
**沒有一項需要 Node**，而 fail-closed、secret masking、path safety 已經全部長在
Python 端。多一層 `.mjs` = 多一個跨語言介面要測、要遮罩、要維護。

**被否決：** 放 `ref-opensource/` 內（違反該目錄 CLAUDE.md「No Systograph product code
lives here」）；放 repo 根 `sidecar/`（可行但無收益，只是把膠水從 Python 搬到 Node）。

#### Q2 裁定理由

樹外 fork 會**同時斷掉兩條依賴**，不是一條：

| 斷掉的 | 原因 |
|--------|------|
| `@understand-anything/core` | `PLUGIN_ROOT` 由 `__dirname` 往上兩層推導 |
| `graphology` / `graphology-communities-louvain` | `:41-42` 是**靜態 bare import**，Node 從新位置往上找不到 `node_modules`（兩者列在 plugin `package.json` dependencies） |

代價是複製一支 588 行、且其決定性排序語意是 **evidence id 穩定性基礎**的檔案，
之後上游每次修正都要手動 merge。patch 只需保存十幾行差異，且日後可整份送上游；
上游合併後刪掉 patch、bump pin 即可。

**被否決：** 樹外 fork（上述負擔）；上游 PR（最乾淨但把 Task 4 開工時程綁在外部
review 上，無限期 blocked）。

**已知副作用：** `git status` 會顯示 submodule 為 modified。`ref-opensource/CLAUDE.md`
已預期此情況——**不得 stage gitlink**，除非 pin bump 是明確意圖。

#### work-dir 裁定理由

中間檔（`scan-result.json` / `batches.json` / per-batch structure 輸出）含目標 repo
的完整檔案清單、函式名與 export 名，是使用者程式碼的衍生資訊；留在硬碟上就是多一份
要保護的資料，與 local-first privacy 相悖。需要留存的是收攏後的
`ua-analysis-result.json`，它已有既有的家（`ScanSnapshot`，Phase B/C 可選保存）。
除錯時以環境變數保留現場，預設不留。

### 6.2 仍待裁定

**（2026-08-05 起：無。** Q1／Q2／Q5／work-dir／部署形態於 2026-08-04～05 裁定，
Q3／Q4／Q6 於 2026-08-05 裁定，全部收錄於 §6.1。動工前不再有未拍板事項。**）**

---

## 7. 相關檔案

| 檔案 | 角色 |
|------|------|
| [`16-implement-understand-anything-sidecar-service.md`](./16-implement-understand-anything-sidecar-service.md) | S2 實作主 plan（本檔是其技術參考） |
| [`16A-q3-lv2-call-graph-flow-visualization.md`](./16A-q3-lv2-call-graph-flow-visualization.md) | Q3 Lv2 決策（call hints 的 why 與下游） |
| `ref-opensource/systograph-understand-anything-integration-boundary.md` | UA 整合邊界（Accepted，最高權威） |
| `ref-opensource/Understand-Anything/understand-anything-plugin/skills/understand/` | 三支 script 原始碼（pinned `73559a1`） |
| `src/systograph/core/services/project_scan_service.py` | `ScanResultProvider` Protocol 與 provider loop |
| `src/systograph/core/services/component_detection_service.py` | 四元組 join（規則 A 出處） |
| `src/systograph/core/services/canonical_evidence_service.py` | direct/indirect 判定（規則 B 出處） |
| `src/systograph/core/services/apply_confirmations_service.py` | evidence id 子集檢查（規則 C 出處） |
