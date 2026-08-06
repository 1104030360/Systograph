# 16C — 檔案層 → 元件層：歸屬映射與邊推導

> 📖 **第一次看？** 先讀 [`README.md`](./README.md)（閱讀順序 + 名詞對照表）。
> **白話一句話：** UA 只會說「a.py import 了 b.py」，但圖上要畫的是
> 「Retriever 元件 → Vector Store 元件」。這份定義中間怎麼跨過去。
> **Review 重點看 §2 的兩級證據表**——那是整份的核心設計（選項 B：L1=`observed`、L2=`undetermined`）。

Status: planned — **依賴 Plan 16 Task 3（`UaStructuralAdapter`）產出穩定 fact/evidence 之後**

> **執行者注意：** 逐 task 實作本計畫。步驟使用 checkbox（`- [ ]`）語法以便追蹤。
>
> **本檔補的缺口：** [`16A`](./16A-q3-lv2-call-graph-flow-visualization.md) §6 第 2 步只寫
> 「Step 4 / bridge：需要時把 call facts 編成 `context_flow`（及其他 relationship）邊」，
> **沒有定義「怎麼編」**。[`16B`](./16B-ua-sidecar-io-adapter-reference.md) §5.2 把 UA 欄位
> 映射到 `ScanFact` / `Evidence` 為止，也停在**檔案層**。本檔定義從檔案層跨到元件層的
> 那一段推導邏輯——它今天在 codebase 裡**一行都不存在**。
>
> **⚠️ 硬前置（缺一不可）：**
>
> | 前置 | 為什麼是前置 |
> |------|--------------|
> | Plan 16 Task 3 `UaStructuralAdapter` | 本檔消費 `ua_call_hint_*` / `ua_import_*` / `ua_symbol_*` 三類 fact；沒有它就沒有輸入 |
> | [`../../../../finish/s1-v2-cutover/13.8.md`](../../../../finish/s1-v2-cutover/13.8.md) Task 1 — 端點約束 | `_relationship_evidence()`（`profile_finding_assembler.py:196-205`）只用關係名查邊、**不驗端點**。本檔會把邊從 12 條放大到數百條，無端點約束時假陽性同步放大 |
> | [`../../../../finish/s1-v2-cutover/13.7.md`](../../../../finish/s1-v2-cutover/13.7.md) — bridge kind → 52 格字彙 | 邊推得再準，元件字彙沒對齊 52 格仍然點不亮 |

---

## 1. 問題陳述：兩個抽象層對不上

```text
UA 給的（檔案 / 函式層）
  src/retriever.py  ──import────▶  src/store.py
  retrieve()        ──call──────▶  QdrantClient.search()   @ line 42

圖要畫的（元件層）
  [Retriever 元件]  ──context_flow──▶  [Vector Store 元件]
```

中間缺的是一句話：**「哪個元件住在哪段程式碼裡」**。
沒有它，UA 的 call graph 再準，也只能停在檔案依賴圖，接不進
`GraphViewModel` 的 canvas，也點不亮 15 張 profile 卡。

### 1.1 好消息：反查鏈已經存在，不需新增資料

```text
ComponentInstance.evidence_ids          system_map.py:101
        │
        ▼
Evidence.file / line_start / line_end    system_map.py:114+
        │
        ▼
「Vector Store 元件住在 src/store.py 第 12 行」
```

**要新寫的只有推導邏輯，不是資料模型。** 現有 contract 欄位足夠承載結果：

| 需求 | 既有欄位 | 是否需改 schema |
|------|----------|-----------------|
| 邊的來源分級 | `CanonicalEdge.status`（Phase2 實際產出：`observed` / `undetermined`；`detected` 保留但不用） | **否**，enum 不動 |
| 說明為何不確定 | `CanonicalEdge.undetermined_reason` | **否** |
| 邊的證據 | `CanonicalEdge.evidence_ids` | **否** |
| 關係語意 | `CanonicalEdge.relationship`（schema 為自由 string） | **否** |

---

## 2. 中心設計：兩級證據（L1 / L2）↔ 邊 `status`

> **2026-08-04 裁定（選項 B）：由三級改為兩級。** 原設計 L2 標 `detected`、L3 標
> `undetermined`；模板刪掉後 `undetermined` 會變死值。裁定改為：
> **只有看到呼叫點的邊（L1=`observed`）才算接線證據；只有 import 的邊
> （L2=`undetermined`）誠實標無法判定。** L1 用 `observed` 而非 `detected`，
> 避免與 52 格五態撞名。舊三級表見 §2.3。

| 級別 | 來源 | `evidence_kind` | `EdgeObservationStatus` | 算不算 profile 接線？ |
|------|------|-----------------|--------------------------|----------------------|
| **L1** | `ua_call_hint_*`（帶 `lineNumber`） | `direct` | `observed` | **算** |
| **L2** | `ua_import_*`（檔案級，無行號） | `indirect` | `undetermined`<br>`undetermined_reason="import_only_no_call_site"` | **不算** |

**模板刪掉後，`undetermined` 誰來產生？** → **L2（import-only）**。

**過渡期（16C／16D 期間，16G 尚未執行）** 模板邊仍存在，同樣標 `undetermined`，
靠 `undetermined_reason="template_adjacency_only"` 與 L2 區分。16G 完成後該值消失；
此後 `undetermined` 的唯一生產者是 L2。

`detected` 在邊上**沒有生產者**。enum 保留三個值（不動 schema，避免既有已發布
artifact 讀不回來），但 Phase2 不產生 `detected` 邊——這點要有契約測試守住，
否則未來有人補一個「中間級」會意外讓它算數（見 §2.2）。

### 2.1 這順手修掉一個現存缺陷

`system_map_v2_normalize_service.py:153` 今天把**每一條邊**硬寫成
`status="observed"`：

```python
CanonicalEdge(
    ...,
    status="observed",      # ← 無條件
    evidence_ids=sorted(edge.evidence_ids),
)
```

但這些邊全部來自 `flow_derivation_service.py:18` 的 12 條寫死關係表，跟目標
repo 的程式碼無關（16A §2.3 已量化：12 個 fixture 端到端只產出 2 種關係名）。
也就是說——**今天的產品宣稱「觀察到」，實際是模板推定的。**

本計畫讓這個欄位變誠實，這本身就符合 CLAUDE.md 的
「Findings must be evidence-based」與「no opaque single scores」。

### 2.2 L2 為何是 `undetermined`（而不是 `observed` 或 `detected`）

**為何不是 `observed`：** 16B 規則 B（`canonical_evidence_service.py:26-31`）
沒有 `line_start` 就是 `indirect`。`import_map` 天生無行號，
**不得為了讓邊變 `observed` 而捏造行號**。

**為何不是 `detected`：** 一條 import 邊只證明「A 檔依賴 B 檔」，
**不證明這個依賴的關係語意**。邊上的 `relationship`（如 `context_flow`）
是 Task 2 從規則表**查**出來的，不是**看**到的。用它點亮 profile 卡，
正是 13.8 端點約束想擋的那類假陽性。

**這個選擇的實際效果**（`profile_finding_assembler.py:214`）：

```python
if edge.status in {"observed", "detected"}   # undetermined 不在集合裡
```

L2 邊**不進入 profile 卡的接線證據**。卡片要動，必須有真實呼叫點。

> **已知取捨（必須寫進驗收）：** 16E 的 G1（函式外建構）與 G2（工廠模式）
> 是 UA 的先天缺口，會產生「有元件證據但沒有呼叫點」的 repo。這類 repo 在
> 新規則下，依賴 relationship 的卡片會停在 `undetermined`——**這是刻意的**，
> 但 16D Task 5 的驗收必須明確記錄哪些 fixture 因此不再前進，避免被誤判成回歸。

**安全網已經在了，兩層都在：** 就算 L2 有資格進第 214 行的閘門，
`reference_capability_assessment_service.py:147-151` 的 `direct` 也只從
`component_evidence` 且 `evidence_kind == "direct"` 取——indirect 證據
在五態上本來就到不了 `detected`，最多 `partial`。本次改動是在那之上**再加一層**。

### 2.3 舊的三級表（2026-08-04 前，僅供對照）

| 級別 | 來源 | `EdgeObservationStatus` |
|------|------|--------------------------|
| L1 | `ua_call_hint_*` | `observed` |
| L2 | `ua_import_*` | ~~`detected`~~ → 改為 `undetermined` |
| L3 | 模板相鄰推定 | ~~`undetermined`~~ → 由 16G 刪除 |

改動理由：`undetermined` 原本唯一的生產者是模板；模板刪除後該值會變成死值。
與其留一個沒人產生的狀態，不如把它分配給「真正無法判定」的那一類——
**有依賴訊號、但看不到呼叫點**，這正好符合 `undetermined`
在契約裡的定義（「有相關訊號，但不足以判定」）。

---

## 3. 演算法

### 3.1 `ComponentResidenceIndex` 元件居所索引（新建，本計畫核心）

歸屬的最小單位是**函式區間**，不是檔案——因為一個檔案常同時住著多個元件
（`main.py` 裡既有 retriever 呼叫也有 llm 呼叫）。

```text
輸入
  components: Sequence[ComponentInstance]      （Step 4 已產出）
  evidence:   Sequence[Evidence]               （含 file / line_start / line_end）
  symbols:    ua_symbol_* facts                （函式的 startLine / endLine）

輸出（frozen dataclass）
  by_component: Mapping[str, frozenset[Residence]]
  by_file:      Mapping[str, frozenset[str]]        # file -> component_id
  by_span:      Mapping[tuple[str, int, int], str]  # (file,start,end) -> component_id

Residence
  file: str
  span: tuple[int, int] | None   # 函式區間；無法定位到函式時為 None
```

建構步驟：

```text
for each ComponentInstance c:
    for each evidence_id in c.evidence_ids:
        e = evidence_by_id[evidence_id]
        if e.file is None: continue
        span = enclosing_function_span(e.file, e.line_start)   # 查 ua_symbol_*
        record Residence(file=e.file, span=span)
```

`enclosing_function_span` 從 `ua_symbol_*` fact 找**最小**包含 `line_start` 的
函式區間（巢狀函式取最內層）。找不到 → `span=None`，代表「住在檔案層，
但不知道住哪個函式」——這是模組頂層宣告的典型情況（見 §5 風險 1）。

### 3.2 L1：從 call hint 推元件邊

```text
for each ua_call_hint_* fact h:            # h = {file, caller, callee, line}
    src_component = resolve_by_span(h.file, h.line)
    dst_component = resolve_callee(h.callee, h.file)
    if src_component is None or dst_component is None: continue
    if src_component == dst_component: continue          # 元件內部呼叫，不畫
    emit Edge(
        from=src_component, to=dst_component,
        relationship=lookup_relationship(src.kind, dst.kind),   # §3.4
        status="observed",
        evidence_ids=[h 對應的 evidence id],                     # 有行號 → direct
    )
```

`resolve_callee` 兩條路，依序嘗試：

1. **callee 命中某元件的 detection rule**（例如 `callee == "QdrantClient"` 而
   Vector Store 元件正是由該符號偵測出來的）→ 直接對到該元件。
2. **callee 是專案內符號**，用 `ua_symbol_*` 反查它定義在哪個檔的哪個函式，
   再用 `by_span` 對到元件。

兩條都失敗 → 丟棄該 hint，**不猜**（記入 §4 的 dropped 統計，不得靜默）。

### 3.3 L2：從 import 邊推元件邊

```text
for each ua_import_* fact (src_file -> dst_file):
    src_components = by_file[src_file]
    dst_components = by_file[dst_file]
    if len(src_components) != 1 or len(dst_components) != 1:
        record_ambiguous(...)      # §4 歧義處理，不畫邊
        continue
    a, b = single(src_components), single(dst_components)
    if a == b: continue
    if edge(a, b) already emitted at L1: continue      # L1 優先，不重複
    emit Edge(a, b, status="undetermined",
              undetermined_reason="import_only_no_call_site",
              evidence_ids=[import fact 的 evidence id])   # indirect
```

**為何要求兩端都恰好單一元件**：`by_file` 是 N 對 M。若 `main.py` 住 3 個元件、
`store.py` 住 2 個，一條 import 邊會展開成 6 條元件邊，全是猜的。寧可不畫，
也不製造假陽性（13.8 的教訓）。

### 3.4 `relationship` 查表（**不得自創關係名**）

16A §7.2 已明確：關係名必須是 `profile_rule_definitions.py` 既有字串，
UA 端自創同義名會重演 G5 字彙漂移。

新增一張 TOML 對照表（與既有 `core/rules/*.toml` 同一風格，可審計）：

```toml
# core/rules/edge_relationship_rules.toml
[[relationships]]
from_kind = "retriever"
to_kind = "vector_db"
relationship = "queries_vector_store"

[[relationships]]
from_kind = "retriever"
to_kind = "llm"
relationship = "context_flow"        # ← rag-grounding 卡要求的關係
```

查不到 `(from_kind, to_kind)` 組合 → **不畫邊**，並記一筆
`recommended_next_check`，而不是 fallback 到 `connects_to`。
（`flow_derivation_service.py:51` 的 `connects_to` fallback 經 16A §2.3 查核
確認為死碼，本計畫不繼承這個設計。）

### 3.5 L3：模板邊降級（過渡期措施，最終由 16G 刪除）

`FlowDerivationService` 在本計畫內保留，但輸出的邊改標 `status="undetermined"` 加
`undetermined_reason="template_adjacency_only"`。理由：

- 保留但標記，符合「absence of evidence ≠ negative evidence」
- 前端可用 `status` 畫實線／虛線，**契約不變、不必改前端**（16A ③④）
- 本計畫階段還沒有 L1/L2 的實測覆蓋數據，不宜同步拔掉舊來源

L1/L2 已產出的 (a, b) 配對，L3 不再重複輸出。

> **⚠️ 原本列的第一條理由已作廢（2026-08-04）：**
> 舊文寫「刪掉會讓掃不到東西的 repo 圖上全空，失去參考骨架」——**這是錯的**。
> 骨架來自 Step 7 永遠 emit 的 52 格 `reference_capability`
> （`MODEL-CONTRACT` 固定行為），不是 L3。空 repo 拿掉 L3 後看到的仍是完整底圖，
> 只是上面沒有 repo overlay 的邊，**那才是誠實的畫面**。
> 詳見 [`16G`](./16G-retire-template-flow-derivation.md) §3。

---

## 4. 遇到模稜兩可時怎麼辦（歧義處理與「失敗就停」規則）

| 情境 | 處理 | 不得做 |
|------|------|--------|
| call hint 的 caller 落不進任何元件居所 | 丟棄 + 計數 | 不得歸給「最近的」元件 |
| import 兩端非單一元件 | 不畫邊 + 記 ambiguous 計數 | 不得 N×M 展開 |
| `(from_kind, to_kind)` 查無關係名 | 不畫邊 + 發 `recommended_next_check` | 不得 fallback `connects_to` |
| 同一對元件 L1 與 L2 都成立 | 取 L1（`observed`），evidence 合併 | 不得產生兩條平行邊 |
| 元件居所 `span=None`（只知檔案） | 只能參與 L2，不得參與 L1 | 不得用檔案級當 call-site 證據 |

所有丟棄與歧義計數必須進 `ProjectScanResult.warnings` 或
`recommended_next_check`——**不得靜默丟棄**（16B §5.2 末列）。

### 4.1 邊的數量上限（避免圖爆炸）

UA 產出的邊數量級遠大於現有 12 條（16A §2.4）。需設上限並在超限時
明確 log 被丟棄的數量（"No silent caps" 原則）：

- 單一元件對外邊數上限：建議 50（與 UA `MAX_NEIGHBORS` 同量級）
- 全圖邊數上限：建議 2000，超限時保留 L1 > L2 > L3 優先序

---

## 5. 已知風險

**風險 1 — 函式外的建構導致 `span=None`（Python 場景最嚴重）**

```python
client = QdrantClient(host="localhost")   # 模組頂層

class Settings:
    EMBEDDING = OpenAIEmbeddings()        # class body 頂層 — 同樣看不到
```

UA 的 call graph **兩種都不記錄**。守衛是 `functionStack.length > 0`
（`python-extractor.ts:167`），而 `functionStack.push` **只發生在
`function_definition`**（`:152-155`），`class_definition` 不推入
（`:125` 只是 structural 分支）。所以正確的描述不是「模組頂層看不到」，
而是 **「任何 `def` 之外的呼叫都看不到」**——包含極常見的
`class Settings: CLIENT = QdrantClient()` 設定類別寫法。

後果連鎖：

1. 沒有 call hint → Vector Store 元件的居所 `span=None`
2. → 該元件無法參與 L1
3. → 相關邊最多到 L2（`undetermined`），永遠到不了 `observed`，也進不了 profile 接線證據

**解法已確定，但不在本計畫內**（2026-08-04 三方專家查核結論，完整分析見
[`16E`](./16E-ua-coverage-gaps-and-llm-boundary.md) §2）：新增一個
Python-only 的補充 provider（建議 `core/providers/ast_construction_provider.py`），
用 stdlib `ast` 以 scope-depth 計數器走訪，depth 0 的 `Call` 即為 import-time
建構。現成參考在 repo 內：`code_path_scan_service.py:174-176` 的 `ast.walk`
**完全沒有 scope guard**，且 `_call_symbol`（`:225-235`）已能遞迴解 dotted name。

**本計畫的責任不變：遇到 `span=None` 時誠實降級為 L2，不假裝。**
補上該 provider 後，這些元件自然取得 span 並升級到 L1，本計畫的演算法無需修改。

> **關鍵前置警告：** 該 provider 若重用既有 `rule_id` / `kind`
> （如 `code_pattern_vector_store_qdrant` / `vector_store_client`），
> `component_bridge_rules.py` **完全不需要改**——
> `ComponentBridgeRule.matches`（`component_bridge_models.py:52-58`）只 key 在
> `(rule_id, kind)` 加可選 file token。建議在
> `code_pattern_rules.toml` 每列加一個可選 `symbol` 欄位
> （如 `symbol = "qdrant_client.QdrantClient"`），讓 regex 目錄與 AST 符號目錄
> 共用同一份 source of truth，避免兩張表漂移。

**風險 2 — 工廠模式**

`store = get_vector_store(cfg)` 的 callee 是 `get_vector_store`，
不是 `QdrantClient`。`resolve_callee` 第 2 條路（專案內符號反查）能追到
工廠函式所在檔，但追不到它回傳什麼。→ 邊會接到「工廠函式所屬元件」，
可能是錯的。**緩解**：工廠函式若不屬於任何元件居所，第 1 條路失敗、
第 2 條路對到 `None` → 丟棄，不畫錯邊。

**風險 3 — 外部服務邊畫不出來**

`extract-import-map.mjs:1789` 過濾掉所有專案外邊
（`if (out && ctx.fileSet.has(out))`），所以「app → OpenAI API」這條線在
L1/L2 都不存在。這類邊仍由 `EndpointDetectionService` 負責，本計畫不接管。

補充（2026-08-04 查核）：資料其實沒有丟失在解析階段——tree-sitter
早已把 `import openai` 連同行號解析出來，是 UA 的**兩條輸出路徑各自丟棄**：
`extract-import-map.mjs:1789` 的 fileSet 過濾，以及
`extract-structure-result.mjs:106-111` 只輸出經相對路徑過濾後的
`metrics.importCount`、完全不輸出來源字串。撈回來屬 Plan 16 adapter 範疇。

**⚠️ 證據來源硬化（本計畫落地前建議先補）**

`canonical_evidence_service.py:26-31` 判定 `direct` / `indirect`
**純粹看形狀**（有 `file` 且有 `line_start` 就是 `direct`），全函式沒有任何
來源檢查：

```python
evidence_kind = ("direct"
    if item.file is not None
    and (item.line_start is not None or json_pointer is not None)
    else "indirect")
```

本計畫的 L1 邊依賴 `direct` 語意成立。任何未來帶行號但屬「推論」的
fact（如工廠模式兩跳解析的結果）都會被這個啟發式**自動升級成 `direct`**，
連帶讓 `reference_capability_assessment_service.py:178-180` 把節點升成
`detected`——五態契約破功，且型別系統攔不住。

建議的加性修法（向後相容，既有 provider 全部不受影響）：
`Evidence` 新增 `evidence_kind_hint: AssessmentEvidenceKind | None = None`，
`canonical_evidence_service` 有 hint 時優先採用。此變更**不屬本計畫**，
但屬本計畫的正確性前提。

---

## 6. Task 清單

### Task 1 — `ComponentResidenceIndex`

- [ ] 新增 `core/services/component_residence_index.py`，含
      `Residence` frozen dataclass 與 `ComponentResidenceIndex`
- [ ] 實作 `enclosing_function_span`：從 `ua_symbol_*` fact 找最小包含區間
- [ ] 實作 `resolve_by_span(file, line) -> component_id | None`
- [ ] 單元測試：單元件單檔、多元件同檔（用 span 區分）、`span=None`、
      巢狀函式取最內層
- [ ] 服務檔頭補「責任 / 呼叫鏈」結構化註解（同 `core/services/` 慣例）

### Task 2 — relationship 規則表

- [ ] 新增 `core/rules/edge_relationship_rules.toml`
- [ ] 用 `RuleCatalogLoader` 既有機制載入（不新造 loader）
- [ ] 表中每個 `relationship` 值必須存在於
      `profile_rule_definitions.py` 的 `required_relationship` 集合或
      13.8 alias 表 → 加一個 contract 測試守住這件事
- [ ] 查無組合時不 fallback；測試覆蓋此路徑

### Task 3 — L1 call-hint 邊推導

- [ ] 新增 `core/services/ua_edge_derivation_service.py`
- [ ] 實作 `resolve_callee` 兩條路徑（rule 命中 / 專案內符號反查）
- [ ] 產出 `Edge` 時 `status="observed"`、evidence 指向 call hint
- [ ] 元件內部呼叫（src == dst）不畫邊
- [ ] 測試：跨檔案 call、同檔案跨元件 call、callee 解不出、self-loop

### Task 4 — L2 import 邊推導

- [ ] 兩端單一元件才畫；否則記 ambiguous 計數
- [ ] `status="undetermined"` +
      `undetermined_reason="import_only_no_call_site"`、
      evidence 為 import fact（indirect）
- [ ] L1 已有的配對不重複產出
- [ ] 測試：單一對單一、N 對 M（不畫）、與 L1 重疊（取 L1）
- [ ] **契約測試：L2 邊不得出現在 profile 卡的 relationship evidence 裡**
      （`profile_finding_assembler.py:214` 的閘門行為）

### Task 5 — L3 模板邊降級

> **這是止血，不是根治（2026-08-04 新增）：** 降級後 L3 仍是一條不帶任何 repo
> 資訊的邊。[`16G`](./16G-retire-template-flow-derivation.md) 會在 16D 完成且六道
> 門檻全過後，把 L3 連同 `FlowDerivationService` 整支刪除。本 task 新增的
> `undetermined_reason="template_adjacency_only"` 屆時一併移除。
>
> **注意：L2 與 L3 在過渡期同樣是 `undetermined`**，唯一的區分是
> `undetermined_reason`（`import_only_no_call_site` vs `template_adjacency_only`）。
> 16D Task 4 的開關測試與 16G 的門檻量測都依賴這個欄位，**不得省略**。

- [ ] `FlowDerivationService` 輸出的邊改標
      `status="undetermined"` + `undetermined_reason="template_adjacency_only"`
- [ ] 移除 `system_map_v2_normalize_service.py:153` 的無條件
      `status="observed"`，改為沿用 `Edge` 帶進來的狀態
- [ ] `Edge`（`system_map.py:154`）新增 `status` 與 `undetermined_reason`
      欄位以承載分級（**這是本計畫唯一的 model 變更**）
- [ ] 更新既有測試中對 `status` 的斷言
- [ ] 契約測試：`observed` 與 `undetermined` 各一；**外加一條「不得產生
      `detected` 邊」的斷言**（該值保留在 enum 只為既有 artifact 相容）
- [ ] `profile_finding_assembler.py:214` 的 `{"observed", "detected"}` 集合
      **維持不動**（`detected` 已無生產者，留著只為讀回舊 artifact），
      但補一行註解說明為什麼不收斂成 `{"observed"}`
- [ ] 更新 `docs/MODEL-CONTRACT.md`：邊的來源分級為兩級（`observed` /
      `undetermined`），`detected` 標記為 reserved-unused（schema 不變，語意變）

### Task 6 — 上限與可觀測性

- [ ] 實作 §4.1 的兩層上限，超限時寫入 warnings（數量 + 被丟棄的級別）
- [ ] 丟棄／歧義計數進 `ProjectScanResult.warnings`
- [ ] 查無 relationship 的組合 → `recommended_next_check`

### Task 7 — 端到端驗證

- [ ] 對 `tests/fixtures/rag_projects/basic_qdrant_ollama_rag` 跑全管線，
      記錄兩級邊數量（`observed` / `undetermined`；過渡期另計
      `template_adjacency_only`），對照 16A §2.3 基線
- [ ] 對 `pgvector_openai_rag` 重複，確認不同 stack 也有 L1 邊
- [ ] 確認 `call_graph.json` / `execution_paths.json` / `execution_map.mmd`
      三個 sibling 吃到同一批邊（16A ③）
- [ ] Viewer 煙測：前端契約不變，只驗資料變真（16A ④）

---

## 7. 驗收條件

| # | 條件 | 量測方式 |
|---|------|----------|
| 1 | 至少一個 fixture 產出 `status="observed"` 的邊 | 端到端跑，數 `ai_system_map.json` 的 edges |
| 2 | 無 call-site direct evidence 的邊不得為 `observed` | 契約測試：`observed` ⇒ 至少一個 direct evidence |
| 3 | 新產出的邊不得為 `detected`；L2 全為 `undetermined` + `import_only_no_call_site` | contract test |
| 4 | L2 邊不進入 profile relationship evidence | Task 4 契約測試 |
| 5 | 關係名 100% 落在 profile 契約字彙內 | Task 2 的 contract 測試 |
| 6 | 歧義與丟棄全部可見 | warnings 非空且數字與實際相符 |
| 7 | Apply 重放不變 | 同 `scan_id` 重放，邊集合與 evidence id 逐位元相同（16B 規則 C） |
| 8 | 前端未改任何檔 | `git diff frontend/` 為空 |

---

## 8. 不在本計畫範圍

| 項目 | 歸屬 |
|------|------|
| 模組頂層呼叫的補抓（風險 1） | Plan 16 adapter 層，或獨立的 Python AST 掃描 |
| 外部服務邊（風險 3） | `EndpointDetectionService`，既有職責 |
| profile 五態判定 | Step 6 `ProfileInferenceService` 獨佔，本計畫只供邊 |
| `plane_id` / reference node id | Step 6；本計畫**不得**輸出（16B §5.2 禁止清單） |
| runtime 驗證 | 永遠不做；`runtime_verified=false`（16A §5.3） |

---

## 9. 相關檔案

| 檔案 | 角色 |
|------|------|
| [`16-implement-understand-anything-sidecar-service.md`](./16-implement-understand-anything-sidecar-service.md) | S2 實作主 plan（本檔的上游） |
| [`16A-q3-lv2-call-graph-flow-visualization.md`](./16A-q3-lv2-call-graph-flow-visualization.md) | Lv2 決策；§7.2 是本檔 Task 2 的字彙來源 |
| [`16B-ua-sidecar-io-adapter-reference.md`](./16B-ua-sidecar-io-adapter-reference.md) | adapter 三條硬規則；本檔消費其 fact 輸出 |
| [`../../../../finish/s1-v2-cutover/13.7.md`](../../../../finish/s1-v2-cutover/13.7.md) / [`13.8.md`](../../../../finish/s1-v2-cutover/13.8.md) | 硬前置 |
| `src/systograph/core/services/component_detection_service.py` | `EvidenceLookup` 四元組 join（Task 1 輸入） |
| `src/systograph/core/services/flow_derivation_service.py` | 今日模板邊（Task 5 改造對象） |
| `src/systograph/core/services/system_map_v2_normalize_service.py` | `status="observed"` 無條件寫入處（Task 5） |
| `src/systograph/core/models/system_map.py` | `ComponentInstance:94` / `Edge:154`（Task 5 model 變更） |
| `src/systograph/core/services/canonical_evidence_service.py` | direct/indirect 判定（L1/L2 分級依據） |
