# 16H — AST 建構補充 provider：G1 函式外建構 / G2 工廠推論 / G3 外部 import declaration

> 📖 **第一次看？** 先讀 [`README.md`](./README.md)（閱讀順序 + 名詞對照表）。
> **白話一句話：** UA 有三個先天看不到的盲點（16E 的 G1/G2/G3），這份是把它們
> 用純 Python `ast` 補起來的**實作計畫**——零 LLM、不改 vendored tree。
> **Review 重點看 Task 1**——`evidence_kind_hint` 是 G2 推論與 16C L1/L2 分級的
> 正確性前提，**必須第一個做**，否則後面全錯而且型別系統攔不住。

Status: **completed（2026-08-10）** — Task 1～5 已接入 deterministic scan，typed facts、G1/G2/G3 與 evidence hint 均有契約／回歸測試。

> **AST source-read 平台邊界：** 現行安全實作需要 POSIX `dirfd` / `openat` /
> `O_NOFOLLOW`。每次 descriptor read 都要匹配 inventory `size_bytes` 與
> `content_fingerprint`。非 POSIX 或缺少這組 primitive 時會對 Python 檔案產生
> structured read issue、零 AST fact；不得退回 pathname check。原生 Windows
> safe-handle 支援是後續 capability，不是本計畫假裝已完成的相容層。

> **2026-08-10 Phase 12 live-code 校正（HEAD `da0d402`）：ready，先修規格再實作。**
> 現行 component bridge 會把既有 `(rule_id, kind)` fact 直接建成 component，且
> canonical evidence 只要有 file+line 就會被形狀啟發式升 direct；因此舊 Task 4
> 會讓未使用 import 產生假 detected。取代規則如下：
>
> 1. 新增 frozen、可判別聯集的 `StructuralFact`（call/import/symbol/factory），並在
>    `ProviderScanResult` / `ProjectScanResult` 加 `structural_facts`；topology facts
>    不送進 component bridge。
> 2. G1 的實際 call/constructor 可同時產 component fact（direct）與 call structural
>    fact；G2 component fact 必帶 `hint=indirect`，factory structural fact 保留
>    provenance；G3 **只**產 `ExternalImportStructuralFact` + indirect evidence。
> 3. Task 2 只替語意能精確對應 constructor/call 的規則填 `symbol`；route decorator、
>    `.as_retriever()`、設定型 regex 不得為湊滿 13 筆硬塞假 constructor symbol。
> 4. 反向 contract：未使用 external import 不建立 component、不產 observed edge；
>    只有真正 symbol usage/call 才能升 direct。

> **執行者注意：** 逐 task 實作本計畫。步驟使用 checkbox（`- [ ]`）語法以便追蹤。
>
> **本檔的由來：** [`16E`](./16E-ua-coverage-gaps-and-llm-boundary.md) 是決策紀錄，
> 自我宣告非實作計畫（沒有 Task 清單、沒有 Files、沒有驗收條件）；
> [`16C`](./16C-component-attribution-and-edge-derivation.md) §8 曾把這件事寫成
> 「Plan 16 adapter 層，**或**獨立的 Python AST 掃描」二選一未定。
> **2026-08-10 裁定**（見 [`CLARIFICATIONS-2026-08-10.md`](./CLARIFICATIONS-2026-08-10.md)
> Q1）：新開本檔為實作計畫，規格自 16E §2.3／§2.5／§2.7／§3／§4.3／§5 抽取為
> Task ＋ Files ＋ 驗收條件；不動 Gate 結構。
>
> **⚠️ 範圍變更（2026-08-10 裁定，見 CLARIFICATIONS Q2）：**
> provider 範圍由 16E 決策 4 的「嚴格限於 G1 + G3」**擴為 G1 + G2 + G3**；
> **G2 改走確定性程式推論**（取代 16E 決策 2 的「殘量走人工確認為主」）。
> 人工確認通道**不刪**，降為可選旁路（推論仍解不出、或使用者要否決推論時可用）；
> 使用者不 review 也能得到完整（含推論標記）的圖。
> **全程零 LLM**——16E §6 的 LLM 邊界裁定原封不動適用於本檔。
>
> **⚠️ 硬前置：**
>
> | 前置 | 狀態 / 為什麼 |
> |------|---------------|
> | Gate-1 / Gate-2 / Plan 16 | **不需要**。本檔不消費任何 UA 輸出，只用 stdlib `ast` 掃 repo 內的 `.py`；2026-08-10 Q1 裁定明文「16H 不等 Gate」 |
> | [`13.7`](../../../../finish/s1-v2-cutover/13.7.md) / [`13.8`](../../../../finish/s1-v2-cutover/13.8.md) | ✅ 已滿足（2026-07-29 done；由回歸測試守護）。本檔沿用既有 `rule_id` / `kind`，字彙對齊工作已完成 |
> | 本檔 **Task 1**（`evidence_kind_hint`） | **內部硬前置**：Task 5（G2）產出的是**推論型且帶行號**的 fact，若沒有 hint，`canonical_evidence_service.py:26-31` 的形狀啟發式會**自動把它升級成 `direct`** → 節點升成 `detected` → 五態契約破功。**Task 1 契約測試未綠前，不得動 Task 5** |
> | 本檔 **Task 2**（typed structural facts + `symbol` 欄） | **內部硬前置**：Task 3/4/5 都要用 typed topology payload；只有能精確表示 constructor/call 的規則才加入「符號 →(rule_id, kind)」翻譯，避免私有清單與假語意 |
>
> **本檔是誰的硬前置：** **Task 4（G3 外部 import declaration）為
> [`16`](./16-implement-understand-anything-sidecar-service.md) Task 3
> （`UaStructuralAdapter`）的硬前置**（2026-08-10 Q6 裁定，三處措辭已統一為
> 「硬前置」而非「建議／應」）。理由是 **parity 基線一致性**：G3 會新增 typed
> import-only facts（證據維持 `indirect`）；若落在 adapter 的 parity 基線
> **之後**才做，這批新增事實會混進 parity diff 裡，**真實退化與基線位移分不出來**。
> Q1 裁定後本檔立即開工、Plan 16 仍等 Gate-1，此硬前置實務上零成本。

---

## 1. 本檔在補什麼（三個缺口 ↔ 三個 Task）

| # | 缺口 | 根因（16E 已驗證） | 本檔解法 | 產出 fact 的證據等級 |
|---|------|--------------------|----------|----------------------|
| **G1** | 任何 `def` 之外的呼叫看不到（含 class body） | `python-extractor.ts:167` 的 `functionStack.length > 0` 守衛 | Task 3：scope-depth 計數器，depth 0 的 `Call` 即 import-time 建構 | `direct`（目擊，帶行號） |
| **G2** | 工廠 / 間接建構解不出 | 靜態分析的固有邊界 | Task 5：追進工廠函式，`MAX_FACTORY_HOPS = 3`，分支不塌縮 | `indirect`（**推論，一律標 hint**） |
| **G3** | 外部 import declaration 消失 | UA 兩條輸出路徑各自主動丟棄（`extract-import-map.mjs:1790` 的 `fileSet` 過濾、`extract-structure-result.mjs:106-111` 只輸出數量） | Task 4：G1 綁定表的副產品，過濾掉專案自己的 module root；只進 structural facts | `indirect`（有行號仍未證明 symbol 被使用） |

**三個缺口裡，零個需要 LLM。** 這是 16E §0 的結論，本檔只是把它變成可執行的步驟。

### 1.1 為什麼「今天 regex 抓得到」不等於「不用做」

`code_pattern_provider.py:128` 是 `rule.regex.finditer(text)` 掃整個檔案文字，
regex 沒有作用域概念，所以 `\bQdrantClient\s*\(` 今天照樣命中模組頂層那行。
**G1 的風險點是 Plan 18（TOML providers 退役）**，不是現在——退役當天若沒有
AST 來源接手，函式外建構會從「抓得到」變成「抓不到」。

順帶的實質升級：`from qdrant_client import QdrantClient as QC` 之後的 `QC(...)`，
現有 regex **完全無效**，AST 經 `alias.name` / `alias.asname` 解得出來；
而 UA 自己也解不出來——`extractFromImport`（`python-extractor.ts:297`）處理
`from X import Y as Z` 時只把本地別名 `Z` 推進 `specifiers`，**原始名 `Y` 直接蒸發**。

---

## 2. 四條設計不變式（動工前先讀）

### 2.1 零 LLM

16E §6 的裁定完整適用：LLM **不得進入掃描路徑（Step 3）**。本檔全部產出皆為
stdlib `ast` 的確定性結果，同一份 repo 掃 N 次必須逐位元相同（見 §4 驗收 7）。

### 2.2 沿用既有 `rule_id` / `kind` → bridge 13 條零改動

`ComponentBridgeRule.matches`（`component_bridge_models.py:52-58`）只 key 在
`(fact.rule_id, fact.kind)` 加可選 file token：

```python
def matches(self, fact: ScanFact) -> bool:
    if (fact.rule_id not in self.rule_ids
            or fact.kind not in self.fact_kinds):
        return False
    return self.required_file_tokens <= _tokens(fact.file)
```

**只要新 provider 沿用既有 `rule_id` / `kind`**（如
`code_pattern_vector_store_qdrant` / `vector_store_client`），
`component_bridge_rules.py` 的 13 條規則**一行都不用改**。

> **這是文件敘述，不是要動 code。** 本檔**不新增、不修改任何 bridge 規則**；
> 「13 條零改動」是驗收條件（`git diff` 該檔為空），不是待辦事項。
> bridge 認得 `ua_*` 的鏡射項屬 Plan 16 Task 3 既定範圍，與本檔無關。

### 2.3 誠實性三鎖（G2 專用）

| 鎖 | 內容 | 落點 |
|----|------|------|
| ① 分支不塌縮 | 工廠有 N 個 return 分支就發 N 筆 fact，不挑一個當答案 | Task 5 |
| ② 全部標推論 | 每一筆推論 fact 都帶 `evidence_kind_hint="indirect"`；**節點因此最多 `partial`** | Task 1 + Task 5 |
| ③ 邊標無法判定 | 由 16C 消費後標 `status="undetermined"` ＋專屬 `undetermined_reason`（如 `factory_inference`），**不進 profile 接線證據**（`profile_finding_assembler.py:214` 的閘門不變） | **16C 職責**，本檔只產 facts |

**明示後果（plan owner 已知悉）：** 推論邊不會讓 profile 卡前進——這個選項買到的
是**圖的完整性**（虛線畫得出來），卡片翻綠仍然只靠 L1 的真實呼叫點。

### 2.4 發不出 fact 就什麼都不發

16E §3.4 的統一邊界規則，本檔三個 Task 一體適用：

**不得發 `not_detected`，不得捏造 `detected`。** 若別處另有獨立訊號證明同一格，
那筆 fact 自行成立；若都沒有，`ProfileInferenceService` 既有的缺席處理會正確
落在 `undetermined`——**缺席 ≠ negative evidence**。

丟棄與無法解析的計數必須進 `ProjectScanResult.warnings` 或 `ParseIssue`，
**不得靜默丟棄**。

---

## 3. Task 清單

### Task 1 — `Evidence.evidence_kind_hint`（**必須第一個做**）

> **為什麼是第一個：** 三位專家在 16E §5 獨立指出同一處——
> `canonical_evidence_service.py:26-31` 的 `direct` 判定**純粹看形狀**，
> 全函式沒有任何來源檢查，「一個檔名 + 一個行號」就買得到 `direct`。
> Task 5（G2）產出的正是「帶行號但屬推論」的 fact，會被這個啟發式自動升級。
> 這同時也是 [`16C`](./16C-component-attribution-and-edge-derivation.md)
> L1/L2 分級的正確性前提（16C §5 末段已標明「不屬本計畫，但屬本計畫的正確性前提」）。

> **⚠️ 動工順序更正（2026-08-10，PR #280 review）：加欄位之前必須先搬型別別名。**
> `AssessmentEvidenceKind` 現住 `ai_system_map_v2.py:57`，而該模組已在
> `:31` `from systograph.core.models.system_map import Evidence`。若直接讓
> `system_map.py` 反向 import 它，兩個 model 模組會**循環相依、載入即失敗**，
> 掃描器整個起不來。故 Task 1 拆為三步：**先搬別名 → 再加欄位 → 最後改判定**。
>
> **判例：** 07-28 的 `RecommendedNextCheck` 遇過同一個死結，解法相同——
> 移到中立 module、原模組 re-export 綁名字
> （`core/models/recommended_next_check.py` 檔頭記錄了完整理由）。
>
> **與 Plan 15 的關係：** 這個中立 module 即 Plan 15「把版本中立 symbol 拆出
> `system_map.py`」的落腳處（Plan 15 §Task 2 前置清單）。本 task 只搬一個型別
> 別名，是該拆分的第一小步，方向一致、不製造需要回頭的中間態。
> **本 task 不搬 `Evidence` 本體**（37 個 import 點，屬 Plan 15 範圍）。

**Files**

- Add: `src/systograph/core/models/evidence_kind.py`
  （**中立 module**：只放 `AssessmentEvidenceKind`；刻意不 import 任何其他
  systograph model，確保不可能產生循環相依——同
  `core/models/recommended_next_check.py` 的既有慣例）
- Modify: `src/systograph/core/models/ai_system_map_v2.py`
  （`:57` 的定義改為 `from ...evidence_kind import AssessmentEvidenceKind` re-export，
  維持既有兩個消費者 `canonical_evidence_service.py` /
  `system_map_v1_to_v2_adapter.py` 零改動）
- Modify: `src/systograph/core/models/system_map.py`
  （`Evidence`（`:117`）新增 `evidence_kind_hint` 欄位，型別自中立 module import）
- Modify: `src/systograph/core/services/canonical_evidence_service.py`
  （`:26-31` 的形狀判定改為「有 hint 時優先採 hint」）
- Add: `tests/contracts/test_evidence_kind_hint_contract.py`
- Modify: `docs/MODEL-CONTRACT.md`（證據語意一節補 hint 的定義與適用規則）

**Steps**

- [x] **步驟 ①（必須最先）** 新增 `core/models/evidence_kind.py`，把
      `AssessmentEvidenceKind = Literal["direct", "indirect", "explicit_negative"]`
      從 `ai_system_map_v2.py:57` 移入；該檔**不得 import 任何其他 systograph
      model**（檔頭比照 `recommended_next_check.py` 寫明此紀律與理由）
- [x] **步驟 ②** `ai_system_map_v2.py` 改為 re-export 綁名字；驗證
      `canonical_evidence_service.py` 與 `system_map_v1_to_v2_adapter.py`
      **一行都不用改**（字彙不變、值域不變）
- [x] **步驟 ③** `Evidence` 加**加性**欄位（只加不改，既有 provider 全部不設此欄，行為不變）：

      ```python
      # core/models/system_map.py — Evidence
      from systograph.core.models.evidence_kind import AssessmentEvidenceKind
      ...
      evidence_kind_hint: AssessmentEvidenceKind | None = None
      ```

      值域沿用既有三值，**不新增字彙**
- [x] 迴圈防護測試：斷言 `evidence_kind.py` 的 import 集合為空（或不含任何
      `systograph.core.models.*`），避免日後有人往中立 module 加相依
- [x] `canonical_evidence_service` 改為 hint 優先：

      ```python
      evidence_kind = (
          item.evidence_kind_hint
          if item.evidence_kind_hint is not None
          else (原本的形狀判定)
      )
      ```

- [x] 契約測試①（正向）：設 `evidence_kind_hint="indirect"` 且**同時帶
      `file` + `line_start`** 的 Evidence，經 `canonical_evidence_service`
      之後必須是 `indirect`——形狀啟發式不得覆寫 hint
- [x] 契約測試②（回歸）：未設 hint 的 Evidence 走原本形狀判定，結果與改動前逐筆相同
- [x] **契約測試③（反向斷言）：任何推論型 fact 必須申報
      `evidence_kind_hint="indirect"`**——以本檔 Task 5 的 provider 輸出為對象，
      斷言「G2 產出的每一筆 evidence 都帶 hint 且值為 `indirect`」，
      漏標即紅（Task 5 落地時一併補上這條的實際資料來源；Task 1 階段先以
      合成 fixture 釘住規則）
- [x] **契約測試④（反向斷言）：LLM 產出不得宣告 `direct`**——
      任何經 `MappingProposalService` / `llm_proposal_provider` 路徑產生的
      evidence，其 `evidence_kind` 不得為 `direct`
      （對齊 16E §6.4「永遠不得寫入的欄位」清單第 3 條；
      `reference_capability_assessment_service.py:147-151` 的結構性保證再加一層釘子）
- [x] `mypy src tests` 全綠——`AssessmentEvidenceKind | None` 的引入不得讓
      既有 `Evidence` 建構點噴型別錯

---

### Task 2 — typed structural facts + `code_pattern_rules.toml` 可選 `symbol`

> **為什麼併進本 PR（2026-08-10 Q4 裁定）：** 16H 開工即需要「符號 →(rule_id, kind)」
> 的翻譯字典；若不先落地共用表，provider 內部會長出臨時私有清單，造成
> **regex 目錄與 AST 符號目錄兩表漂移**。
> 釐清紀錄：這張 TOML **只是身份證翻譯字典**，供 regex／16H AST／未來 UA adapter
> 三個生產者共用；**「什麼變成 component」仍由 Step 4 bridge（typed Python 13 條）
> 獨占決定**。Plan 16 Task 3 屆時只在**同一張表**再加 `ua_*` 對照欄。

**Files**

- Add: `src/systograph/core/models/structural_fact.py`（frozen discriminated union：
  call/import/symbol/factory inference；每一型別自帶 deterministic identity fields）
- Modify: `src/systograph/core/models/scan.py`（`ProviderScanResult` / `ProjectScanResult`
  的 `structural_facts` 加性欄位）
- Modify: `src/systograph/core/rules/code_pattern_rules.toml`（只對語意精確的列加可選 `symbol`）
- Modify: `src/systograph/core/services/rule_catalog_loader.py`
  （`CodePatternRule`（`:52-60`）加欄位；`load_code_pattern_rules`（`:164-233`）
  解析可選字串；目前 loader 只有 `_required_string` 系列，需補一個 optional 版）
- Modify: `tests/unit/core/test_rule_catalog_loader.py`

**Steps**

- [x] 先定義 typed structural fact union；禁止把 caller/callee/span/provenance 塞進
      自由格式 `ScanFact.value`。每種 payload 必須可 JSON round-trip 且排序鍵固定。
- [x] 對可精確表示 constructor/call 的 TOML 列加**可選** `symbol` 欄，值為完整點分
      符號路徑，例如：

      ```toml
      [[patterns]]
      rule_id = "code_pattern_vector_store_qdrant"
      kind = "vector_store_client"
      languages = ["python"]
      extensions = [".py"]
      regex = "\\bQdrantClient\\s*\\("
      snippet_group = ""
      symbol = "qdrant_client.QdrantClient"
      ```

- [x] **加性變更：既有 13 列不需修改語意**，只是多一個鍵；未填 `symbol` 的列
      loader 照常載入（`symbol=None`），AST provider 單純不消費該列
- [x] route decorator、`.as_retriever()`、設定型 regex 等非 constructor 語意列維持
      `symbol=None`；測試明確證明不會為了覆蓋數量把它們錯配成 constructor
- [x] `CodePatternRule` 加 `symbol: str | None`；loader 補 optional-string 解析
- [x] 護欄測試①：`symbol` 在整張表內**唯一**（重複即 `RuleCatalogError`，
      比照既有 `duplicate rule_id` / `duplicate pattern` 的處理）
- [x] 護欄測試②：`symbol` 若存在必須是非空點分字串（不得是空字串、不得含空白）
- [x] 護欄測試③：**缺 `symbol` 不得讓載入失敗**（加性保證），且該列不會被
      AST provider 靜默當成「符號未知」而發出錯誤 fact
- [x] 護欄測試④：**符號目錄與 regex 目錄同源**——斷言 AST provider 認得的符號集合
      ⊆ TOML 的 `symbol` 集合，provider 內不得有硬編碼清單（防兩表漂移）

---

### Task 3 — G1：`ast_construction_provider.py`（函式外建構）

> **解法已經躺在 repo 裡：** `code_path_scan_service.py:176-181` 的 `ast.walk`
> **完全沒有 scope guard**，模組頂層與 class body 的呼叫全數抓得到；
> `_call_symbol`（`:227-237`）已能遞迴解 `chromadb.HttpClient` 這種點分形式。
> 既有測試與 masking 都已就位，本 Task 是把這套能力包成一個 provider。

**Files**

- Add: `src/systograph/core/providers/ast_construction_provider.py`
- Modify: `src/systograph/core/services/project_scan_service.py`
  （`:88-92` 的預設 provider tuple 加入新 provider）
- Add: `tests/unit/core/test_ast_construction_provider.py`
- Add: `tests/fixtures/rag_projects/` 下的 G1 場景 fixture（函式外建構 + class body 建構）

**Steps**

- [x] 形狀對齊 `code_pattern_provider.py`：`collect(inventory) -> ProviderScanResult`、
      只吃 `.py`、`SyntaxError` → `ParseIssue`（**不得讓整次掃描崩掉**）
- [x] `ParseIssue` 用 `provider="ast_construction"`（該欄是自由 `str`），
      **`scan_stage` 沿用既有 `"code_pattern_scan"`**——16E §2.7 既有裁定，
      **不改 `scan.py:107-114` 的封閉 Literal**
      （Literal 的第 7 個值 `"ua_structural_scan"` 屬 Plan 16 Task 1，與本檔無關）
- [x] **演算法＝scope-depth 計數器，不要逐一列舉語句型別**：
      只在 `FunctionDef` / `AsyncFunctionDef` / `Lambda` 的 body 遞增 depth；
      **depth 0 的 `Call` 即為 import-time 建構**。這一招統一涵蓋 `Assign`、
      `AnnAssign`、裸 `Expr(Call)`、`With` / `AsyncWith`、list comprehension、walrus
- [x] **`ClassDef` 不遞增 depth**——class body 的頂層語句在 import 時就執行一次
      （`class Settings: CLIENT = QdrantClient()` 是 RAG 專案極常見的設定類別寫法）
- [x] 維護 import 綁定表 `(local_name → module, original_name, line)`，
      用 Task 2 的 `symbol` 目錄把解出的完整符號翻回 `(rule_id, kind)`
- [x] 沿用既有 `rule_id` / `kind` 發 `ScanFact` ＋帶行號的 `Evidence`
      （目擊事實，**不設 hint**，走原本的形狀判定即為 `direct`）
- [x] 走 `SecretMaskingService`，snippet 比照 `code_pattern_provider` 的上限處理
- [x] provider 檔頭補「責任 / 呼叫鏈」結構化註解（同 `core/providers/` 慣例）

**七個實作雷區——各自一個 Step ＋ 一條測試（16E §2.5，會靜默寫錯的地方）**

- [x] **雷區 1｜import 別名綁定**：`import a.b.c as m` 綁**完整點分模組**
      （`m.Foo` → `a.b.c.Foo`）；`import a.b.c`（無 `as`）**只綁頂層名 `a`**，
      後續 `a.b.c.Foo()` 必須照作者寫的屬性鏈解。
      測試：兩種寫法各一，斷言**不得**產出 `a.b.c.b.c.Foo` 這種重複片段
- [x] **雷區 2｜decorator / 基底類別 / `def` 參數預設值在外層作用域求值**：
      naive visitor 若先遞增 depth 再 `generic_visit`，會把
      `@app.on_event("startup")` 或 `def f(x=Client())` 誤判成埋在函式內。
      測試：三種寫法各一，斷言都被視為 depth 0
- [x] **雷區 3｜`if TYPE_CHECKING:`**：body 要**跳過**（runtime 不執行），
      `orelse` 要正常走。測試：TYPE_CHECKING body 內的建構不得產生 fact，
      `else` 分支內的要產生
- [x] **雷區 4｜`from X import *`**：無法靜態解析。標記 `is_star`，
      永遠落 `unresolved`，**不猜**。測試：star import 後的呼叫不得產生已解析 fact，
      且該 star import 必須被計數（不得靜默）
- [x] **雷區 5｜跨檔案 re-export**：`from .clients import QdrantClient`
      （而 `clients.py` 自己 `from qdrant_client import ...`）單檔解析只得到
      `clients.QdrantClient`。保留「**裸末段名 fallback**」並**明確標記**——
      等同今天 regex 的行為，不是新風險。測試：斷言 fallback 有標記、可與
      完整解析區分
- [x] **雷區 6｜`try: import X / except ImportError: X = None`**：
      兩個分支都在 depth 0，binding **照常記錄**，不需特判。
      測試：斷言 try 分支的 import 正常進綁定表
- [x] **雷區 7｜metaclass / `__init_subclass__` 隱式建構**：靜態分析看不到，
      **不發 fact**（符合「缺席 ≠ negative」）。
      測試：metaclass fixture 產出 0 筆相關 fact，且**不得**發任何 `not_detected`

---

### Task 4 — G3：外部 import declaration（**Plan 16 Task 3 的硬前置**）

> **投報率最高的一項，而且幾乎是 G1 的免費副產品（16E §4.3）：**
> Task 3 的 binding table 已記錄 `(local_name → module, original_name, line)`，
> **過濾掉專案自己的 package root 就是答案**——正好是 UA `fileSet` 過濾掉的那一半。

**Files**

- Modify: `src/systograph/core/providers/ast_construction_provider.py`
  （沿用 Task 3 的 binding table，加 typed external-import structural fact）
- Add: `tests/unit/core/test_ast_construction_provider_external_imports.py`
- Modify: `tests/fixtures/rag_projects/` 既有 fixture（確認外部 import 有被撈到）

**Steps**

- [x] 從 Task 3 的 binding table 產出 `ExternalImportStructuralFact`，
      **證據帶行號＝`import` / `from ... import` 陳述那一行**
      但明設 `evidence_kind_hint="indirect"`；import declaration 不是 symbol usage
- [x] `project_module_roots` **由既有 inventory 推導**（`ProjectScanService` 的
      專案佈局理解已足夠），用來過濾內部 / 外部；**不新增掃描能力、不新增設定項**
- [x] 內部 import（解得到專案內模組）**不由本檔處理**——那是 Plan 16 adapter 的
      `ua_import_*` 職責，本檔只補 UA 主動丟棄的**外部**那一半，避免兩個生產者打架
- [x] structural fact 使用專屬 stable identity（例如 `ua_external_import`），不得鏡射
      component bridge 的 `(rule_id, kind)`；contract test 斷言 bridge 回 `NO_MATCH`
- [x] 測試：外部 import 產出帶行號但仍為 indirect 的 evidence；專案內 import 不產出；
      同一個外部套件同時被 `requirements.txt` 與 import 陳述命中時，
      兩筆證據**並存不互相覆寫**
- [x] 反向測試：只有未使用 external import 時，component 數與 observed edge 數均不變；
      增加真正 call 後才可由 G1/UA call fact 產 direct evidence
- [x] 測試：`project_module_roots` 推導對 `src/` layout 與扁平 layout 皆正確

> **⚠️ 合併順序是硬性的：** 本 Task 必須**先於**
> [`16`](./16-implement-understand-anything-sidecar-service.md) Task 3 合併。
> 理由見檔頭硬前置表（parity 基線一致性）。
>
> **查核註記（2026-08-10 親驗）：** `component_bridge_rules.py` 裡
> **零條規則**引用 `dependency_*` 開頭的 rule_id；G3 的價值在 import provenance
> 與 parity 基線，不在「新增元件」或證據升級。不得宣稱它會讓卡片翻綠。

---

### Task 5 — G2：工廠確定性推論（**Task 1 未綠不得動工**）

> **這是 2026-08-10 的新裁定**（見 CLARIFICATIONS Q2），**取代 16E 決策 2**
> 的「G2 殘量走既有人工確認通道」。改判內容：G2 由**確定性 AST 推論**解，
> **非 LLM**；人工確認通道不刪，降為可選旁路。

**Files**

- Modify: `src/systograph/core/providers/ast_construction_provider.py`
  （加工廠追蹤路徑；或視體積抽成同目錄的 `_factory_resolution.py` 私有模組）
- Add: `tests/unit/core/test_ast_construction_factory_inference.py`
- Add: `tests/fixtures/rag_projects/` 下的工廠場景 fixture
      （分支工廠、dict registry、五種邊界各一）

**Steps**

- [x] 依 16E §3.1 的**確定性階梯**實作，順序不可顛倒：
      ① 回傳型別標註（`def get_vector_store(cfg) -> QdrantClient:`，免費）→
      ② **兩跳 in-repo 解析**（工廠在專案內 → 用 Task 3 的 binding table 找到檔案
      與函式區間 → 只 AST 走那一段找 `return`）→
      ③ framework 已知工廠（`.as_retriever()` / `.from_documents()`）
      **已由既有 TOML 規則處理**（`code_pattern_retriever_as_retriever`），不重做
- [x] 固定點迭代，**深度上限 `MAX_FACTORY_HOPS = 3`**（模組級常數，不做成設定項），
      另加 visited-set **防環**
- [x] 回傳分類三種：`construction`（直接解到匯入符號）、
      `delegate_call`（轉呼叫另一個專案內函式，計入 hop）、
      其他（**終止，不發 fact**）
- [x] **分支不塌縮**：每個 `return` 分支**各發一筆 fact**——

      ```python
      if cfg.provider == "qdrant":
          return QdrantClient(...)
      else:
          return ChromaClient(...)
      ```

      這是**確定性事實**：「此工廠可建構兩種後端，執行期由 config 決定」。
      發兩筆，不挑一個當答案
- [x] 同理處理 RAG 膠水碼常見的 **dict registry 模式**
      （`PROVIDERS = {"qdrant": QdrantClient}; return PROVIDERS[name](...)`），
      同樣以析取（disjunction）處理，每個 registry 值各一筆
- [x] **每一筆 G2 fact 的 evidence 都帶 `evidence_kind_hint="indirect"`**
      （Task 1 的欄位），**無例外**——節點因此最多 `partial`
- [x] 實作下方**五條邊界，到這裡就停且必須停**（16E §3.4）

**五條邊界（每條各一個 fixture，全部斷言 0 筆 fact）**

| 邊界 | 例子 | 該做什麼 |
|------|------|----------|
| 參數傳遞型 | `def get_store(client): return client` | 不發 fact（需跨全部呼叫點的常數傳播，無界） |
| 反射式派發 | `getattr(m, name)()`、`importlib.import_module(s)` | 不發 fact |
| 不透明屬性鏈 | `return self.config.client` | 不發 fact |
| 裝飾器替換回傳值 | 自訂 `@registered_provider` | 不發 fact（無法與 `@lru_cache` 這類透明裝飾器區分） |
| 超過 hop 上限 / 成環 | — | 降級為不發 fact ＋計數，**不得掛起或崩潰** |

- [x] **防假陽性測試（驗收必備，2026-08-10 裁定明列）**：五條邊界各一個 fixture，
      斷言**產出 0 筆 fact**；並斷言**不得**因此發出 `not_detected`
      （§2.4：發不出 fact 就什麼都不發）
- [x] 測試：分支工廠 → 恰好 N 筆 fact（N = return 分支數），**全部** `hint=indirect`
- [x] 測試：hop 上限——第 4 跳的工廠鏈產出 0 筆 fact 並計入 warnings
- [x] 測試：成環的工廠鏈不掛起（有時間上界）且產出 0 筆 fact
- [x] 邊的處理**不在本 Task**：16C 消費這批 fact 後標
      `status="undetermined"` ＋專屬 `undetermined_reason="factory_inference"`，
      **不進 profile 接線證據**。本檔只產 facts，
      16C 落地時需在其 Task 4 附近補上這個 reason 值與對應契約測試

---

## 4. 驗收條件

| # | 條件 | 量測方式 |
|---|------|----------|
| 1 | **Task 4（G3）先於 [`16`](./16-implement-understand-anything-sidecar-service.md) Task 3 合併** | PR 合併順序；Plan 16 Task 3 的 PR 描述須引用本檔 Task 4 的 commit |
| 2 | **`evidence_kind_hint` 契約測試全綠**（含兩條反向斷言） | Task 1 的測試①～④；其中③「推論型 fact 必須申報 hint」與④「LLM 產出不得宣告 `direct`」缺一不可 |
| 3 | 既有行為零回歸 | 未設 hint 的 Evidence 判定結果與改動前逐筆相同 |
| 4 | **G1 七個雷區各有一條測試** | Task 3 的雷區 1～7，逐條對得上測試函式名 |
| 5 | **G2 防假陽性測試通過** | 五條邊界 fixture 各產出 0 筆 fact，且無 `not_detected` |
| 6 | G2 產出的 evidence **100% 帶 `hint="indirect"`** | 契約測試掃該 provider 全部輸出，漏標即紅 |
| 7 | **確定性** | 同一 fixture 掃 N ≥ 20 次，facts + evidence 逐位元相同（零 LLM 的可驗證後果） |
| 8 | **bridge 13 條零改動** | `git diff src/systograph/core/services/component_bridge_rules.py` 為空 |
| 9 | **G3 不製造 component 假陽性** | internal module 名單只由 approved inventory 的合法 Python 相對路徑推導，不依賴 live pathname existence；未使用 external import 只產 indirect structural fact，bridge `NO_MATCH`，observed edge=0 |
| 10 | **typed structural facts 可重放** | call/import/symbol/factory union JSON round-trip 與 stable sort/id contract |
| 11 | **不改 `ParseIssue.scan_stage` 封閉 Literal** | `git diff` 該 Literal 為空；AST provider 的 ParseIssue 全部是 `"code_pattern_scan"` |
| 12 | **不改 vendored tree** | `git diff ref-opensource/Understand-Anything/` 為空（16E §4.3、`ref-opensource/CLAUDE.md`） |
| 13 | read-only 與 approved-bytes 保證 | 掃描過程不寫入被掃專案；POSIX source read 由 pinned root dirfd 逐層 no-follow 開啟，descriptor bytes 必須符合 inventory size/fingerprint。缺少安全 primitive 時 structured fail closed，禁止 pathname fallback |
| 14 | 前端未改任何檔 | `git diff frontend/` 為空 |
| 15 | 全綠且不掉覆蓋率 | `uv run pytest`、`ruff check src tests`、`ruff format --check src tests`、`mypy src tests`；branch coverage ≥ 85% |
| 16 | **不得為了讓 fixture 過而寫特化 code** | 見下方紅線 |

> **🚨 紅線——引用根 `CLAUDE.md` 的「Never game a red CI into green」原則：**
> 當誠實掃描模式暴露出「掃描器對某個檔案／fixture 產不出真實 facts」時，
> **唯二合法解＝(a) 真實的掃描能力改進，或 (b) 明文記錄的基線調整**。
> **禁止**：fixture 特化的 pattern hack、捏造 facts/evidence、
> 以及任何「只為了讓測試過」而存在的掃描器路徑——**違者 review P1**。
> **誠實的空圖勝過造假的滿圖。** 本檔的 G2 尤其容易踩這條線：
> 推不出來就是推不出來，`undetermined` 是正確答案，不是待修的缺陷。

---

## 5. 不在本計畫範圍

| 項目 | 歸屬 |
|------|------|
| 元件層邊推導（`ComponentResidenceIndex`、L1/L2 分級、`status` / `undetermined_reason`、`factory_inference` 這個值本身） | [`16C`](./16C-component-attribution-and-edge-derivation.md) |
| UA sidecar / `UaStructuralAdapter` / `ua_*` facts / `scan_stage="ua_structural_scan"` | [`16`](./16-implement-understand-anything-sidecar-service.md) |
| 任何 LLM 用途（含 NIM → local model 遷移） | Plan 17；16E §6 的邊界裁定原封不動適用 |
| 模板邊退役、`FlowDerivationService` 刪除 | [`16G`](./16G-retire-template-flow-derivation.md) |
| TOML providers 退役準則（含「函式外建構 parity」條款） | Plan 18（承接方式見 16E `:71` 註記） |
| profile 五態判定 | Step 6 `ProfileInferenceService` 獨佔；本檔只供 facts |
| `plane_id` / reference node id / 五態 / `confidence` | 本檔**不得**輸出（16B §5.2 禁止清單、16E §6.4） |
| 改 vendored tree（UA 原始碼） | **永不**；修 UA 只能走 upstream 貢獻（`ref-opensource/CLAUDE.md`） |
| 人工確認通道的 UI / 服務改動 | 既有 `MappingProposalService`；本檔不動它，只是不再依賴它作為 G2 的主路徑 |

---

## 6. 相關檔案

| 檔案 | 角色 |
|------|------|
| [`16E-ua-coverage-gaps-and-llm-boundary.md`](./16E-ua-coverage-gaps-and-llm-boundary.md) | **本檔的規格來源**（§2.3 演算法、§2.5 七個雷區、§2.7 bridge 零改動、§3 G2 階梯與邊界、§4.3 G3 解法、§5 hint 修法） |
| [`CLARIFICATIONS-2026-08-10.md`](./CLARIFICATIONS-2026-08-10.md) | 本檔全部裁定的出處（Q1 歸屬、Q2 G2 路線與 hint、Q4 `symbol` 欄、Q6 G3 硬前置） |
| [`16-implement-understand-anything-sidecar-service.md`](./16-implement-understand-anything-sidecar-service.md) | S2 實作主 plan；其 Task 3 以本檔 Task 4 為硬前置 |
| [`16C-component-attribution-and-edge-derivation.md`](./16C-component-attribution-and-edge-derivation.md) | 消費本檔產出的 facts；L1/L2 分級以本檔 Task 1 為正確性前提 |
| [`README.md`](./README.md) | 閱讀順序、名詞對照表、各計畫可否開工的狀態表 |
| `ref-opensource/systograph-understand-anything-integration-boundary.md` | §9 職責表已補列 16H 與工廠推論（最高權威） |
| `ref-opensource/CLAUDE.md` | 為什麼不能改 vendored 程式碼 |
| `src/systograph/core/providers/code_pattern_provider.py` | 形狀範本（`collect` / 只吃 `.py` / `SyntaxError` → ParseIssue）；`:128` 是今天的 regex 掃描點 |
| `src/systograph/core/services/code_path_scan_service.py` | `:176-181` 的 `ast.walk` 無 scope guard、`:227-237` 的 `_call_symbol` 遞迴解點分名（現成參考） |
| `src/systograph/core/services/canonical_evidence_service.py` | `:26-31` 形狀判定 direct/indirect（Task 1 改動點） |
| `src/systograph/core/models/system_map.py` | `Evidence`（`:117`）——Task 1 加欄位處 |
| `src/systograph/core/models/ai_system_map_v2.py` | `AssessmentEvidenceKind`（`:57`）現址、`Evidence`（`:31`）import 處——Task 1 步驟①②的循環相依來源 |
| `src/systograph/core/models/recommended_next_check.py` | **中立 module 判例**：07-28 同型死結的既有解法與檔頭紀律 |
| `../../../refactor/15-complete-legacy-v1-retirement-after-compatibility.md` | Plan 15：版本中立 symbol 拆出 `system_map.py` 的完整清單；本 task 的中立 module 即其落腳處 |
| `src/systograph/core/models/scan.py` | `ScanFact`（`:92`）／`ParseIssue`（`:103`，`scan_stage` 封閉 Literal 在 `:107-114`） |
| `src/systograph/core/services/rule_catalog_loader.py` | `CodePatternRule`（`:52-60`）／`load_code_pattern_rules`（`:164-233`）——Task 2 改動點 |
| `src/systograph/core/rules/code_pattern_rules.toml` | 13 列 regex 目錄；Task 2 只在語意可精確對應的列加 `symbol` 欄 |
| `src/systograph/core/services/component_bridge_models.py` | `matches` 只 key `(rule_id, kind)`（§2.2 出處） |
| `src/systograph/core/services/component_bridge_rules.py` | 13 條規則；本檔驗收要求 `git diff` 為空 |
| `src/systograph/core/services/project_scan_service.py` | `:88-92` 預設 provider tuple（Task 3 註冊點）；`:153-163` 把 provider 例外吞成 ParseIssue 的 loop |
| `src/systograph/core/services/profile_finding_assembler.py` | `:214` 的 `{"observed", "detected"}` 閘門——推論邊被擋在外的地方 |
| `src/systograph/core/services/reference_capability_assessment_service.py` | `:147-151` `direct` 只從 `component_evidence` 取（Task 1 反向斷言的依據） |
