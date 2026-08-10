# Understand-Anything Sidecar Service 實作計畫

> 📖 **第一次看？** 先讀 [`README.md`](./README.md)（閱讀順序 + 名詞對照表）。
> **白話一句話：** 怎麼把 UA 當外部程式叫起來、拿到結果、翻譯成 Systograph 自己的格式。
> 這是本資料夾的**主計畫**，其他五份都圍繞它。

Status: planned — **blocked until Gate-1 passes**（2026-07-07 UA-primary 決策）

> **2026-08-10 補強裁定：** 見
> [`CLARIFICATIONS-2026-08-10.md`](./CLARIFICATIONS-2026-08-10.md)——
> **Q3**（`ParseIssue.scan_stage` 加 `ua_structural_scan`，Task 1）／
> **Q6**（16H G3 為 Task 3 硬前置）／**Q7**（candidate observed_kind 字彙對位，Task 3）／
> **Q11**（BD §4.2 禁輸出契約測試落 Task 5；Rescan 重跑列入驗收條件）／
> **Q17**（Plan 14／18 銜接與呼叫計數器落 Task 7）。各項已逐條落實於下列 Task 與驗收條件。

> **執行者注意：** 逐 task 實作本計畫。步驟使用 checkbox（`- [ ]`）語法以便追蹤。
>
> **相關決策（2026-07-29 Q3）：** 選 **Lv2**——UA call graph 經 Adapter 變成 direct
> evidence 後，同一份資料升級 `context_flow`、FlowDerivation、靜態執行產物與前端 flow
> 可視化。詳見
> [`16A-q3-lv2-call-graph-flow-visualization.md`](./16A-q3-lv2-call-graph-flow-visualization.md)。
> Plan 16 本體仍以 sidecar + adapter + parity 為界；FlowDerivation／profile wiring 升級
> 依 16A §6 後續由 [`16C`](./16C-component-attribution-and-edge-derivation.md)（邊推導）與
> [`16D`](./16D-call-priority-consumer-cutover.md)（消費者 call 優先 cutover）落地，
> 不阻塞本 plan 的 Gate-2 structural path。
>
> **技術參考（2026-07-29 查核後新增）：** 三支 UA script 的實測 I/O、runtime 需求、
> Systograph 側接縫錨點（含 `scan_routes.py` 中字面 `ua_analysis_result=None` 那行的
> 預留孔位，現行 `:210`）、adapter 三條硬規則，見
> [`16B-ua-sidecar-io-adapter-reference.md`](./16B-ua-sidecar-io-adapter-reference.md)。
> **16B §6 的 open questions 已於 2026-08-05 全數裁定**（§6.2「仍待裁定」＝無），
> 該節現為歷史決策紀錄。Task 1/3/4/6 實作前先讀。
>
> **下游推導計畫（2026-08-04 新增）：** adapter 產出的 fact 只到**檔案層**；
> 從檔案層跨到**元件層**（誰住在哪段程式碼 → 元件之間怎麼連邊）的推導邏輯，
> 見 [`16C-component-attribution-and-edge-derivation.md`](./16C-component-attribution-and-edge-derivation.md)。
> 16A §6 第 2 步只說「需要時把 call facts 編成關係邊」，16C 定義「怎麼編」。
>
> **⚠️ UA 覆蓋缺口與 LLM 邊界裁定（2026-08-04 三方專家查核）：**
> UA 有三個先天覆蓋缺口（G1 函式外建構、G2 工廠間接建構、G3 外部 import 邊），
> 裁定結果為**零個需要 LLM 進掃描路徑**；**G1＋G2＋G3 三者統一歸屬實作計畫
> `16H-ast-construction-provider.md`**（2026-08-10 裁定 Q1／Q2：G2 改走確定性 AST
> 推論、非 LLM，故一併併入 16H）。
> **16H 的 G3 部分為本 plan Task 3 的硬前置**（2026-08-10 裁定，理由＝parity 基線
> 一致性——G3 會把外部 import 從 indirect 抬為 direct，若落在基線之後會污染 parity
> diff；見 [`CLARIFICATIONS-2026-08-10.md`](./CLARIFICATIONS-2026-08-10.md) Q6）。
> G1 另影響 Plan 18 退役準則。
> 見 [`16E-ua-coverage-gaps-and-llm-boundary.md`](./16E-ua-coverage-gaps-and-llm-boundary.md)。
> Task 3（adapter）與 Task 6 實作前必讀 §5（證據來源硬化）。
>
> **✅ 前置計畫：已滿足（2026-07-29 done）** —— 原列為「動工前硬前置」，兩者皆不依賴
> UA，已於 2026-07-29 完成，**不再是擋路項**（2026-08-10 裁定 Q5）：
>
> - **13.7**（bridge kind → 52 格字彙對齊）：done。
> - **13.8**（profile relationship 端點約束）：done——端點約束已落地於
>   `profile_finding_assembler.py`（現行 `:214-217`，`edge.status ∈ {observed, detected}`
>   ＋ `required_component_ids.isdisjoint((edge.source, edge.target))` 檢查），
>   由回歸測試 `tests/unit/core/test_profile_finding_endpoint_constraint.py` 守護。
>
> 下表的「不做的後果」欄**保留為歷史理由**（記錄當初為何列為硬前置），非現況風險：
>
> | 前置（✅ 已滿足） | 不做的後果（實測；歷史理由） |
> |------|--------------------|
> | [`../../../../finish/s1-v2-cutover/13.7.md`](../../../../finish/s1-v2-cutover/13.7.md) — bridge kind → 52 格字彙對齊 | UA 只替換 fact 來源，元件仍以 bridge kind 表示；`_TYPE_TO_NODES` 未補齊時，UA 掃得再準 52 格照樣點不亮（今天 4/52 靠 legacy slot 撐，拆掉後 1/52） |
> | [`../../../../finish/s1-v2-cutover/13.8.md`](../../../../finish/s1-v2-cutover/13.8.md) — profile relationship 端點約束 | 關係查表不驗邊的端點；UA 產出的邊數量級遠大於現有 12 條，無約束時任何同名邊都會點亮卡片（假陽性已實證） |
>
> 另見 16A §7.2：12 張 profile 卡的關係語意需求清單，是 adapter call hints
> 設計的驗收輸入。**UA 端不得自創同義關係名**（會重演 G5 字彙漂移）。

## 目標

> **白話版：** 決定要掃哪些檔案之後（Step 2），把 UA 當成外部程式叫起來，
> 讓它回報「哪個檔 import 哪個檔」「有哪些函式」「誰呼叫誰、第幾行」，
> 再把這些翻譯成 Systograph 自己的資料格式。
> UA 的 AI 語意分析**不啟用**（欄位留空），這階段只要確定性的結構事實。
>
> 過渡期的安排：Gate-1 通過前，仍由舊的 TOML 規則當主力；通過後換 UA 當主力，
> 舊規則降為「對照組」，用來驗證兩邊掃出來的結果一不一致（parity 對等性驗證）。

新增 `UnderstandAnythingAnalysisService`，讓 Systograph 在 Step 2 boundary 完成後呼叫
Understand-Anything sidecar，取得 deterministic structural facts（含 **call hints /
誰呼叫誰**，以支援 16A Lv2）；semantic sidecar slot 保持 nullable deferred。
Gate-1 後的 Phase B 由 UA 擔任 Step 3 primary 掃描來源；既有 Systograph scan TOML providers
在過渡期只做 parity 對比。Gate-1 前的 Phase A 仍由現有 Systograph providers 擔任 primary。

## 架構

```text
Step 2 FileInventory（Systograph boundary owner）
  + inventory enrichment（語言 / fileCategory / 行數，移植自 scan-project）
  -> UnderstandAnythingAnalysisService
       NodeRuntimePreflight
       UnderstandAnythingSubprocessRunner
       UnderstandAnythingResultValidator
       UaStructuralAdapter
  -> 直接依序 spawn 三支 UA script（2026-08-04 裁定：無 .mjs wrapper，見 16B §6 Q1）
       extract-import-map
       compute-batches（已套 Systograph patch：--input / --output / --work-dir）
       extract-structure（逐 batch）
       file-analyzer（bounded LLM）deferred；不執行
       ua-analysis-result.json（Phase B/C 可選保存；semantic=null）
       structural -> UaStructuralAdapter -> ScanSnapshot.scan_result（Step 4～7 consumer）
       semantic   -> reserved nullable slot；Phase2 不執行 file-analyzer、不產生、不消費
```

Sidecar request / result schema：

```text
systograph-ua-request/v1
systograph-ua-result/v1
```

`scan-project.mjs` 不執行；只移植其 enrichment 邏輯。UA work-dir 由 Systograph 提供，
不得寫入 target repo。

**執行環境（2026-08-05 裁定）：Native。** Python（uv）+ 本機 Node 直接 spawn 三支
script；Docker 化 deferred 另案評估，不是本計畫的前置或 scope。裁定依據：2026-08-05
本機實測 end-to-end 跑通（Node v22.22.3；`pnpm install` 一步含 core build，1m52s；
三支 script 對 fixture 副本產出 import edge / Louvain batches / 含行號 callGraph，
與源碼逐行吻合）。實測數據與新發現的 runtime 細節見 16B §3.1／§3.4。

**work-dir 位置（2026-08-04 裁定）：系統暫存目錄，每次掃描一個、掃完刪除。**
中間檔（`scan-result.json` / `batches.json` / per-batch structure 輸出）含目標 repo 的
完整檔案清單與符號名，屬 local-first privacy 保護對象；需要留存的是收攏後的
`ua-analysis-result.json`，它走既有 `ScanSnapshot` 機制。除錯時可用環境變數保留現場，
預設不留。**不得**落在 `src/systograph/`（產品原始碼目錄）或 `~/.systograph/`（durable state）。

## 依賴

- **Gate-1 通過前不得開工（Do not start until Gate-1 passes）：** TOML-primary 的 **initial scan 驗 Step 1～7 publish +
  Step 8 viewer（initial scan 不必跑 Step 9）**；**Step 9 decision 與 Apply B1→B2
  （跳 Step 3/UA；4-1 bridge replay → 4-2 overlay → Step 4～7）共用 snapshot 由 Apply path
  另行驗證**；以及 `ua_analysis_result=None` 的 initial build / Apply regression 必須全部通過。
  Gate-1 未通過時，本計畫維持 blocked，不得提前把 UA 切成 primary。
  （拆法以 `static-trace-plan/README.md` 的執行順序與 Gate 表為準；原本寫「Step 1～9 E2E」會
  讓 Gate-1 驗收時對「initial scan 要不要跑 Step 9」各說各話。）
- 依賴 `00A`：generic v2 map 與 evidence contract。
- 依賴 `01B`：UA `rule_id` 必須能進 Step 4 bridge registry。
- 依賴 `03A`：`ScanSnapshot` 預留 nullable `ua-analysis-result` internal sidecar slot，但
  Phase2 Apply 只使用 `ScanSnapshot.scan_result`；semantic sidecar 不產生、不消費。
- Structural path 必須在 Plan 14 final validation 前完成。

## Task 1：定義 UA 的請求 / 回應格式（request / result schema）

**Files**

- Create: `src/systograph/core/models/ua_analysis.py`
- Create: `schemas/systograph-ua-request.v1.schema.json`
- Create: `schemas/systograph-ua-result.v1.schema.json`
- Test: `tests/unit/core/test_ua_analysis_models.py`
- Test: `tests/contracts/test_ua_analysis_schema.py`

**Steps**

- [ ] 定義 `UaAnalysisRequest`，包含 `schema_version`、`project_root`、`files[]`、
  `inventory_digest` 與 work-dir safe metadata。
- [ ] `files[]` 必須使用 project-relative path，含 `language`、`file_category`、
  `size_lines`、content digest 或 fingerprint。
- [ ] 定義 `UaAnalysisResult`，包含 `structural`、`semantic`、`warnings`、`stats` 與
  `status`；禁止 raw full source、absolute local path 與 secret values。
- [ ] **`stats` / `warnings` 形狀（Q3 裁定 2026-08-05：定型核心 + `extra` 逃生欄）：**
  `stats` 必要欄位定型且 required（`filesScanned` / `filesWithImports` / `totalEdges` /
  `totalBatches` / `algorithm` / `filesAnalyzed` / per-batch 完成清單）；`warnings`
  結構化為 `{stage, message}`（已遮罩、限量）；另設一個 `extra` 開放物件——
  原樣傳遞、不驗證、**不消費**。
- [ ] Schema validation fail closed；unknown fields 預設拒絕——**拒絕範圍是 `extra`
  以外的所有層級**（`extra` 是唯一的開放容器）。
- [ ] 契約測試：`extra` 內容不得流入 `ScanFact` / `Evidence` / 任何判定輸入
  （防止它變成未驗證側通道）；Validator 的 fail-closed 檢查只以定型核心欄位為依據。
- [ ] **`ParseIssue.scan_stage` Literal 加第 7 個值 `"ua_structural_scan"`**（一行加性
  變更）——UA adapter 產生的 issues（warnings / `filesSkipped` / stderr 轉入）使用之；
  AST provider（16H）依 16E 既有裁定沿用 `code_pattern_scan`，不新增值。
  **（2026-08-10 裁定 Q3；不加這個值，adapter 第一筆 `ParseIssue` 即 ValidationError。）**

## Task 2：替檔案清單加料（inventory enrichment：補上語言／分類／行數）

**Files**

- Modify: `src/systograph/core/providers/filesystem_provider.py`
- Modify: `src/systograph/core/models/scan.py`
- Test: `tests/unit/core/test_filesystem_provider.py`
- Test: `tests/contracts/test_secret_snapshot_safety.py`

**Steps**

- [ ] 將 `scan-project.mjs` 有價值的 enrichment 移植到 Python inventory：語言偵測、
  `file_category`、行數統計。
- [ ] Enrichment 不改變 boundary policy；可掃描檔案仍由 Systograph Step 2 決定。
- [ ] 對 binary、large、generated、ignored files 維持 skip audit trail。
- [ ] Windows/macOS path normalization 與 encoding fallback 有 focused tests。

## Task 3：建立 `UnderstandAnythingAnalysisService`

**Files**

- Create: `src/systograph/core/services/understand_anything_analysis_service.py`
- Create: `src/systograph/core/services/ua_structural_adapter.py`
- Test: `tests/unit/core/test_understand_anything_analysis_service.py`
- Test: `tests/unit/core/test_ua_structural_adapter.py`

**Steps**

- [ ] `NodeRuntimePreflight` 檢查 Node executable、script path、版本與執行權限，
  以及 `@understand-anything/core` build 產物是否存在（submodule 目前未 build，
  `packages/core/dist/` 缺失時三支 script 必死於 module load，見 16B §3.4）；
  缺失時 fail closed。
- [ ] `UnderstandAnythingSubprocessRunner` 使用固定 argument list、`shell=False`、timeout、
  bounded stdout/stderr 與 redaction。
- [ ] `UnderstandAnythingResultValidator` 驗證 schema、path allowlist、line ranges、stats 與
  batch completion。
- [ ] `UaStructuralAdapter` 將 import map、symbols、endpoints、resources、call hints 轉成
  Systograph `ScanFact` / `Evidence` / `Issue`。
- [ ] UA structural facts 的 `rule_id` 使用穩定前綴，例如 `ua_import_*`、
  `ua_symbol_*`、`ua_endpoint_*`、`ua_call_hint_*`。
  **（Q6 裁定 2026-08-05：確定用新 `ua_*` id，不沿用 legacy id。）**
  `ua_*` ↔ legacy `rule_id` 對照**併入語彙目錄**（`code_pattern_rules.toml` 演進版）：
  每列同時載 legacy id / kind / symbol / ua id，單一 source of truth（同 16E §2.7 的
  `symbol` 欄設計、13.7 的 TOML 單一真相源模式）。bridge 的 `ua_*` 鏡射項屬
  「01B bridge registry 支援 UA rule_id」依賴的具體化，隨本 task 一併落地。
- [ ] **candidate observed_kind 字彙對位（2026-08-10 裁定 Q7）：**
  `capability_type_node_map.toml` 補上兩列——`reranker_candidate = ["reranker"]`、
  `router_like_evidence = ["router"]`（`component_bridge_registry.py` 已在產出這兩個
  `observed_kind`，但 39 鍵的表查不到 → candidates 永遠靜默作廢）；並加**護欄測試**：
  bridge 產出的 `observed_kind` 必須全部可查表，或明文列名豁免。
  效果：此類弱訊號可把 `reranker` / `router` 兩格抬到 `partial`（candidate 封頂不變，
  不會抬到 `detected`）。此項即文末「Final review 移交補記」第一項的處置。
- [ ] **Lv2（16A）：** call hints 必須帶可追溯 path/line，且可標成 `evidence_kind=direct`
  （真 call-site）；禁止用「兩端 component 證據聯集」假裝成 call wiring。call facts
  是後續 `context_flow` / FlowDerivation / static execution 的共同原料。
- [ ] **Adapter 三條硬規則（16B §5.1，違反任一整條路白接）：**
  （A）每個 `ScanFact` 必須配一筆 `(file, path, kind, rule_id)` 四元組完全一致的
  `Evidence`——join 不到時 Step 4 bridge 回 `NO_MATCH`，fact 被**靜默丟棄**；
  （B）UA 自帶行號的欄位（functions/classes/exports/endpoints/services/callGraph）
  必須填 `Evidence.line_start` 才會被判為 `direct`（五態的 `detected` 只認 direct）；
  `import_map` 無行號者誠實維持 indirect，**不得捏造行號**；
  （C）evidence id 由內容決定（deterministic），同一 repo 狀態跨次重跑必須相同——
  Apply 的 `ManualMapping.evidence_ids` 子集檢查依賴此穩定性。

## Task 4：Python 直接編排三支 UA script + `compute-batches` patch

> **2026-08-04 裁定（取代原「新增 `systograph-analyze.mjs` wrapper」）：**
> **不新增任何 Systograph 自有 `.mjs` 檔案。** 編排由 Task 3 的
> `UnderstandAnythingSubprocessRunner` 直接負責；原 wrapper 的膠水責任（16B §4）
> 全部落在 Python。`compute-batches.mjs` 的改動以 **patch 檔**保存，不複製檔案。
> 理由與被否決的方案見 [`16B`](./16B-ua-sidecar-io-adapter-reference.md) §6 Q1 / Q2。

**Files**

- Create: `sidecar/patches/compute-batches-workdir.patch`
- Create: `scripts/setup_ua_sidecar.sh`（submodule init → `pnpm install` → core build → `git apply`）
  ——2026-08-05 實測：`pnpm install` 的 root `prepare` hook 已自動 build core（1m52s 一步
  到位）；顯式 `pnpm --filter @understand-anything/core build` 保留為冪等保險（~10s）。
  script **不自動** `pnpm approve-builds`（Kotlin grammar 例外見 16B §3.4）
- Modify: `src/systograph/core/services/understand_anything_analysis_service.py`（編排邏輯）
- Test: `tests/integration/test_understand_anything_sidecar_contract.py`
- Test: `tests/unit/core/test_ua_work_dir_lifecycle.py`

**Steps**

- [ ] **Patch `compute-batches.mjs`**：加 `--input` / `--output` / `--work-dir`，把寫死的
  `<project-root>/.understand-anything/intermediate/`（`:364` 讀、`:550` 寫）改為參數。
  **必須保留 `<project-root>` positional 參數**——`extractExports()`（`:83`）真的會
  `readFile(join(projectRoot, file.path))` 讀原始碼跑 tree-sitter，它不只是 JSON 容器。
- [ ] Patch **只以 `.patch` 檔形式存在 Systograph repo**，由 `setup_ua_sidecar.sh` 在安裝階段
  `git apply` 到 submodule 工作樹。**不得**把改動 commit 進 submodule、不得 bump gitlink
  （`ref-opensource/CLAUDE.md`：pinned commit 是刻意的）。
- [ ] Patch 套用要 idempotent（重跑不炸）；套用失敗 → preflight fail closed，不得靜默跳過。
- [ ] 三支 script **留在原位執行**（`skills/understand/`）。它們的 `pluginRoot` 是
  `resolve(__dirname, '../..')`，複製出樹外會同時斷掉 `@understand-anything/core` 解析與
  `graphology` / `graphology-communities-louvain` 的 bare import（見 16B §6 Q2）。
- [ ] Python 編排順序：`extract-import-map` → `compute-batches`(patched) →
  `extract-structure`（逐 batch，以 `batchIndex` 為 key）。
- [ ] Python 承接 16B §4 全部膠水責任：決定性合成 `scan-result.json`（`files` + `importMap`
  原樣傳遞、不得增刪改）、`snake_case` ⇄ `camelCase` 轉換、每步呼叫前 `mkdir -p` work dir
  （三支 script 都不自建目錄）、以 `batchIndex` 收 per-batch 輸出、stderr 全量收集限量後
  轉入 warnings。
- [ ] 只分析 request `files[]` allowlist；**絕不執行 `scan-project.mjs`**（它會自己 walk
  檔案樹，破壞「Systograph inventory 是唯一白名單」）。
- [ ] `file-analyzer` bounded LLM / semantic graph 保持 deferred；本計畫只預留 nullable
  sidecar slot，不執行 LLM（邊界理由見 [`16E`](./16E-ua-coverage-gaps-and-llm-boundary.md) §6）。
- [ ] Intermediate artifacts 全部寫入系統暫存 work-dir，**掃完刪除**；不寫 target repo
  `.understand-anything/`。work-dir 生命週期要有測試（正常結束刪除、例外路徑也刪除、
  除錯環境變數下保留）。

## Task 5：唯讀保證 / 路徑安全 / 密鑰遮罩（read-only / path safety / secret masking）

**Files**

- Modify: `src/systograph/core/services/path_safety_service.py`
- Modify: `src/systograph/core/services/secret_masking_service.py`
- Test: `tests/contracts/test_secret_snapshot_safety.py`
- Test: `tests/unit/core/test_understand_anything_analysis_service.py`

**Steps**

- [ ] 驗證 UA result 所有 path 都落在 approved inventory。
- [ ] 拒絕 `..`、absolute path injection、symlink escape、NUL 與跨 drive path。
- [ ] stdout/stderr、warnings、semantic summaries 都套用 secret masking 與 path redaction。
- [ ] Sidecar 不得把 full source、raw prompts、secret-like values 寫入 public artifact。
- [ ] **契約測試逐條釘住 BD §4.2 禁輸出清單（2026-08-10 裁定 Q11①）：** adapter 輸出
  （`ScanFact` / `Evidence` / `Issue` 與 `ua_analysis_result` 留存內容）**不得**含
  ①`plane_id`、②reference node id、③profile 五態（`detected`/`partial`/…）、
  ④`confidence`、⑤runtime 結論。五項各一條斷言，不得只寫一條籠統檢查——
  adapter 只產結構事實，判定一律留給 Step 4／Step 6。

## Task 6：失敗就停（fail-closed：出錯時停下來，不產出半成品）

**Files**

- Test: `tests/unit/core/test_understand_anything_analysis_service.py`
- Test: `tests/integration/test_map_build_service.py`

**Steps**

- [ ] Node runtime 缺失時，scan 不進 Step 4。
- [ ] `ua-analysis-result` schema invalid 時，scan 不進 Step 4。
- [ ] 必要 batch 失敗、missing output、dangling path 或 evidence mismatch 時，scan 不進 Step 4。
- [ ] **`scriptCompleted: true` 不得單獨視為成功**：tree-sitter 全滅時 UA 仍 exit 0、
  importMap 全空——Validator 需另以 `stats.totalEdges` 與 stderr warnings 判斷降級
  並 fail closed（16B §3.4）。
- [ ] Failures 回穩定 error code / finding，不產出可被 viewer 當成功載入的 partial build。

## Task 7：對等性驗證工具（parity harness：比對 UA 與舊規則掃出來的結果）

**Files**

- Create: `src/systograph/core/services/ua_parity_service.py`
- Create: `tests/integration/test_ua_parity_service.py`
- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s3-validation/14-local-project-import-and-test.md`
  ——「Tier A」唯一定義（＝外部真實 repo）與本 task 呼叫計數器的驗收引用（Q17①②）
- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s3-retirement/18-retire-systograph-scan-toml-providers-after-parity.md`
  ——`ua_*` ↔ legacy 對照的**產出者標註改為 Task 3**（原誤標 Task 7），退役報告格式
  與 Plan 14 報告格式對齊（Q17③）

**Steps**

- [ ] 過渡期並跑 Systograph `code_pattern`、`dependency_manifest`、`docker_image`、config patterns。
- [ ] 將 UA structural facts 與 Systograph provider facts 分類為 equivalent / missing / extra /
  intentionally-degraded。equivalence 判定使用語彙目錄的 `ua_*` ↔ legacy `rule_id`
  對照欄（Q6 裁定）；parity report 逐筆標示 fact provenance（rule_id 前綴即來源）。
- [ ] Parity report 不影響 canonical facts，但會成為 Plan 14 gate 與 Plan 18 退役依據。
- [ ] Phase4 Plan 31（`31-expand-advanced-rag-fixtures.md`）的 fixtures 轉為 parity corpus 的第一批資料來源。
- [ ] **呼叫計數器（2026-08-10 裁定 Q17②）：** 實作「檔案系統掃描／UA sidecar／
  parity providers 於 B1→B2 全程**各只跑 1 次**」的計數器並暴露為可斷言值，
  供 Plan 14 的 10+1 E2E gate 直接引用（Apply 不重跑 UA 的既有契約由此變成可測量，
  而非口頭約定）。

## Task 8：CLI 非互動 boundary gate + snapshot（`systograph map` 走同一條 UA 管線）

> **Q4 裁定（2026-08-05）：CLI 立刻補 gate、直接走 UA**——不留過渡期分歧。
> 現況缺口（16B §2.4）：`cli/map_command.py:63` 直接呼叫 `MapBuildService.build()`，
> 沒有 boundary gate、沒有 snapshot；而 UA request 的白名單前提是 Step 2 的
> `FileInventory`。本 task 把缺口補上，讓 CLI 與 Web 共用同一條 Step 2 → 3 管線。
> 已知代價（裁定時已接受）：本 task 進入 Gate-2 關鍵路徑。

**Files**

- Modify: `src/systograph/cli/main.py` / CLI map 命令模組
- Modify: 對應的 core 服務接線（沿用既有 `inventory_*` services，不得複製邏輯進 CLI）
- Test: `tests/cli/test_map_command_boundary_gate.py`
- Test: `tests/cli/` 既有 map 命令測試更新

**Steps**

- [ ] CLI 執行 Step 2 inventory preflight 的**非互動模式**：全部採 default policy
  自動決策，不進互動 review；`blocked` / 需人工決策時 fail-closed，
  錯誤訊息指向 Web review 流程。
- [ ] CLI 產生並持久化 `ScanSnapshot`（`scan_id` 落地 state dir），
  與 Web 路徑同一套 snapshot 機制——Apply / lineage 語意一致。
- [ ] UA request 的 `files[]` 來自同一 `FileInventory`；CLI 不得自行 walk 檔案樹。
- [ ] 回歸測試：同一 fixture 下 CLI 與 Web 產出等價 facts / evidence
  （允許的差異需列舉並說明）。
- [ ] CLI `--help` 與相關文件同步：說明非互動 gate 行為與 blocked 時的處理方式。

## 驗收條件（Acceptance Criteria）

- [ ] `UnderstandAnythingAnalysisService` 可從 Systograph approved inventory 產生 UA request。
- [ ] 編排路徑不執行 `scan-project.mjs`，不寫 target repo；work-dir 於掃描結束刪除。
- [ ] `systograph-ua-request/v1` 與 `systograph-ua-result/v1` schema 通過 contract tests。
- [ ] Structural result 可轉成 Systograph facts / evidence / issues，且 evidence path/line 可追溯。
- [ ] `ScanSnapshot.ua_analysis_result` 為 reserved nullable internal slot（`03A` 預留）；
  Phase2 active path **不產生、不消費** semantic payload；`semantic` 欄位維持 `null`。
- [ ] Phase B/C 可選保存 structural wrapper JSON 於 snapshot 內供追溯，但 Step 4～7 / Apply /
  Viewer 只讀 `ScanSnapshot.scan_result`，不列 public artifact、不新增 API artifact path。
- [ ] Node 缺失、schema invalid、必要 batch 失敗全部 fail closed，不進 Step 4。
- [ ] Parity harness 可產生可追溯 diff，供 Plan 14 / Plan 18 使用；diff 逐筆可辨
  provenance（`ua_*` 前綴 vs legacy rule_id，Q6）。
- [ ] CLI `systograph map` 與 Web 走同一條 Step 2 → 3 管線（非互動 gate + snapshot 落地，
  Task 8）；同 fixture 下兩路徑產出等價 facts。
- [ ] **Rescan 路徑驗收（2026-08-10 裁定 Q11②）：** 重掃（rescan）時**重跑 UA sidecar
  （＋16H providers）並產出新的 `ScanSnapshot`**（新 `scan_id`），不得沿用舊快照；
  對照 Apply（B1→B2）路徑則**不重跑** UA。兩者行為差異須有測試釘住
  （boundary doc §9／§10）。

## Plan 13.8 移交：12 張卡的關係語意驗收清單

**來源**：`../../../../finish/s1-v2-cutover/13.8.md` Task 3（2026-07-29 逐張複核，
`basic_qdrant_ollama_rag` 全管線實測）。與 16A §7.2 同一份清單，此處為
Plan 16 的**驗收面**版本：UA adapter 的 call hints 若無法表達下列語意，
這 12 張卡在 UA 落地後仍會停在 `undetermined` / `partial`。

15 張卡中，`rag-grounding` 屬純命名不一致（13.8 Task 2 已用過渡 alias
`context_flow ≡ {provides_retrieved_context, prompts_llm}` 處理），
`agentic-control` 與 `memory` 無 `required_relationship`；其餘 **12 張**
都必須等 UA 提供語意相符的邊。

| profile_id | 需要的關係語意 | UA call hint 應能證明什麼 |
|---|---|---|
| tool-calling | `tool_call` | agent loop 呼叫了工具函式／工具註冊表 |
| workflow-orchestration | `workflow_transition` | orchestrator 節點之間的狀態轉移呼叫 |
| hybrid-retrieval | `retrieval_fusion` | 兩種以上 retriever 的結果被合併／加權 |
| reranking | `rerank` | retriever 結果流入 rerank 函式後才進下游 |
| corrective-retrieval | `fallback_route` | 檢查失敗後走另一條檢索分支 |
| self-reflection | `self_critique` | 生成結果回饋進同一 agent loop 再評估 |
| graph-retrieval | `graph_retrieval` | 圖查詢 API 的呼叫進入檢索路徑 |
| hierarchical-retrieval | `hierarchical_flow` | 索引層級之間的父子檢索呼叫 |
| contextual-retrieval | `context_enrichment` | metadata 抽取結果併入 context 組裝 |
| multimodal-grounding | `multimodal_retrieval` | 非文字模態的檢索呼叫 |
| modular-composition | `component_selection` | orchestrator 依條件選擇不同元件 |
| multi-query-retrieval | `query_route` | query 分類結果決定走哪條檢索路徑 |

**驗收時必須同時滿足的三個條件**（缺一張卡就不會翻）：

1. **關係名一致**：UA 端不得自創同義新名，必須用
   `profile_rule_definitions.py` 既有字串；要換名就同步改 profile 規則或
   13.8 的 alias 表（否則重演 G5 的字彙漂移）。
2. **端點落點**：13.8 Task 1 已為 relationship 閘門加上端點約束——邊的
   `source`/`target` 至少一端必須落在該卡 `required_node_ids` 對應的元件
   上。只產出關係名而落點不對的 call hint 一律不採計。
3. **node gate 先過**：這 12 張卡**沒有一張**的 required 節點今天能被自動
   掃描點亮到齊。13.7 後自動可達集合只有
   `{api_server, dense_retriever, embedder, index_builder, llm_answerer,
   prompt_builder}` 6 個；本清單需要而不可達的節點為
   `agent_loop`、`tool_using_generator`、`orchestrator`、`router`、
   `hybrid_retriever`、`reranker`、`conflict_checker`、`graph_retriever`、
   `context_composer`、`metadata_extractor`、`rag_anything_system`、
   `query_classifier`。**UA 必須同時補上元件偵測與關係語意**，只補其一
   不會有任何一張卡改變狀態。

**回歸守門**：`tests/integration/test_profile_card_status_baseline.py`
釘住今天 15 張卡的 status 快照（`rag-grounding` / `hierarchical-retrieval`
= `partial`，其餘 13 張 = `undetermined`）。UA 落地讓任何一張卡轉綠時，
該測試會轉紅並在 diff 指名卡片——這是**預期的**，更新快照時要一併說明是
哪一條真實 call-site 證據讓它翻的。

**Final review 移交補記（2026-07-29，13.7/13.8 whole-branch review）**：

- **candidate observed_kind 字彙面未對位**：`component_bridge_registry.py`
  會產出 `observed_kind="reranker_candidate"` / `"router_like_evidence"`
  的 capability candidates，而 `capability_type_node_map.toml`（39 key）
  無此二 key，故 candidates 永遠無法把 `reranker`／`router` 抬到
  `partial`。此為 13.7 前即存在（舊 dict 亦無）、行為中性，但它是
  「bridge 規則 kind 之外的第二個字彙面」，不在 13.7 護欄測試的迭代
  範圍內——UA 字彙工作需一併裁定是否對位並補護欄。
  **（2026-08-10 已裁定：對位，併入 Task 3——補兩列 + 護欄測試，見上。）**
- **rag-grounding 誤亮偵測器**：13.8 待裁定的 `prompts_llm` 風險目前
  無主動偵測器。第一個 full-template（13-slot）fixture 落地時，必須
  同時釘住該 fixture 上 `rag-grounding` 的期望 status——那就是觸發
  條件「UA 前發現真實 repo 誤亮」的檢知點。

## 已裁定問題（全數拍板；歷史紀錄，詳見 16B §6）

- [x] Q1：wrapper 落腳位置 —— **2026-08-04 裁定：不做 wrapper**，Python 直接編排。
- [x] Q2：`compute-batches.mjs` 改動形式 —— **2026-08-04 裁定：patch 檔 + 安裝腳本**。
- [x] work-dir 位置（原表未列）—— **2026-08-04 裁定：系統暫存目錄，掃完刪除**。
- [x] Q3：`stats` / `warnings` 形狀 —— **2026-08-05 裁定：定型核心 + `extra` 逃生欄**
  （核心欄位 required、unknown 拒絕；`extra` 原樣傳遞不驗證不消費，契約測試防側通道）。
  細節見 Task 1。
- [x] Q4：CLI 是否走 UA —— **2026-08-05 裁定：立刻補非互動 gate，CLI 直接走 UA**，
  不留過渡期分歧；已接受 Gate-2 關鍵路徑變重的代價。落地為 Task 8。
- [x] Q5：安裝 vs preflight 邊界 —— **2026-08-05 裁定：安裝階段一次完成
  （`setup_ua_sidecar.sh`：submodule init → `pnpm install` 含自動 build → `git apply`），
  preflight 只檢查不建置**（Node 版本／core dist／patch 已套，缺失 fail-closed 並指向
  setup script）。同日一併裁定**部署形態 = native**，Docker deferred 另案。詳見 16B §6.1。
- [x] Q6：rule_id 命名與 provenance —— **2026-08-05 裁定：新 `ua_*` id；
  `ua_*` ↔ legacy 對照併入語彙目錄（每列同載兩組 id）；provenance 靠前綴天然可分，
  零 model 變更**。bridge 鏡射項 = 01B 依賴的具體化（13.7 已 done，模式沿用其
  TOML 單一真相源做法）。細節見 Task 3／Task 7。

## 邊界 / 不做事項

- 不採用 UA Phase 3～7、dashboard、`knowledge-graph.json` 作為 Systograph canonical truth。
- 不把 UA semantic nodes/edges 直接寫入 `ai_system_map.json`。
- 不新增 frontend contract 欄位。
- 不把 existing Systograph scan TOML providers 立即刪除；退役由 Plan 18 在 parity gate 後處理。
- 不執行 target app、不安裝 target repo dependencies、不修改 target repo。
