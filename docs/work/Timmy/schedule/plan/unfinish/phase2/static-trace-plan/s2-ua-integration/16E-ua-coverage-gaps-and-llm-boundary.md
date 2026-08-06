# 16E — UA 三個覆蓋缺口：根因、確定性解法與 LLM 邊界裁定

> 📖 **第一次看？** 先讀 [`README.md`](./README.md)（閱讀順序 + 名詞對照表）。
> **白話一句話：** UA 有三個先天看不到的盲點，這份說明各自的原因、怎麼用
> 確定性方法補（**都不需要 LLM**），以及為什麼「用 LLM 補」會破壞產品契約。
> **§7 是已拍板的五條決策**，包含「NIM 換本地模型延後」。

Status: **decision recorded + 技術參考**（2026-08-04）— 非實作 plan

> **對象：** Plan 16 / 16C 執行者；任何提案「用 LLM 補 UA 的洞」的人
> **性質：** 三方專家獨立查核後的合併裁定 + 實作參考；**不**改產品碼
> **來源：** 2026-08-04 三個專家 agent 平行查核（LLM 架構、Python 靜態分析、契約審查）
> **證據等級：** 本檔所有 `file:line` 引用均**逐條開檔驗證**，非記憶推測。
> 未經驗證的推論一律標示。

---

## 0. 一句話結論

**三個缺口裡，零個需要 LLM 進掃描路徑。** 兩個是可以直接修的確定性缺口
（其中一個的解法已經躺在 repo 裡），第三個的正確答案本來就是
`undetermined` + 人工確認——那正是五態評估存在的理由。

---

## 1. 三個缺口的實測根因

| # | 缺口 | 根因（已驗證） | 需要 LLM？ |
|---|------|----------------|-----------|
| G1 | 函式外的建構看不到 | `python-extractor.ts:167` 的 `functionStack.length > 0` 守衛 | **否** |
| G2 | 工廠 / 間接建構解不出 | 靜態分析的固有邊界 | **否**（殘量走人工確認） |
| G3 | 外部 import 邊消失 | UA 兩條輸出路徑各自主動丟棄 | **否** |

---

## 2. G1 — 函式外的建構（範圍比原本以為的大）

### 2.1 根因與真實範圍

```text
python-extractor.ts:152-155   functionStack.push 只在 function_definition 發生
python-extractor.ts:167       if (calleeNode && functionStack.length > 0)
python-extractor.ts:125       class_definition 只是 structural 分支，不 push
```

所以正確描述**不是**「模組頂層看不到」，而是 **「任何 `def` 之外的呼叫都看不到」**：

```python
client = QdrantClient(host="localhost")   # 模組頂層 — 看不到

class Settings:
    EMBEDDING = OpenAIEmbeddings()        # class body 頂層 — 同樣看不到
```

第二種是 RAG 專案極常見的設定類別寫法。同一守衛存在於全部 12 個 extractor
（`cpp` / `csharp` / `dart` / `go` / `java` / `kotlin` / `php` / `python` /
`ruby` / `rust` / `typescript` 皆驗證過有 `functionStack.length > 0`）。

### 2.2 這是「未來會退步」的風險，不是今天的能力缺口

**今天抓得到。** `code_pattern_provider.py:122` 是
`rule.regex.finditer(text)` 掃整個檔案文字——regex 沒有作用域概念，
`code_pattern_rules.toml` 的 `\bQdrantClient\s*\(` 照樣命中模組頂層那行，
產出帶 file+line 的 evidence，經 `canonical_evidence_service.py:26-31`
歸為 `direct`。

**所以風險點是 Plan 18（TOML providers 退役）**，不是現在。
把它講成「需要 LLM 才能看到頂層程式碼」是把因果講反——那等於用機率性方法
取代一個現在就能用的確定性偵測。

- [ ] **把「函式外建構 parity」寫進 Plan 18 的退役準則**（現在寫最便宜）

### 2.3 確定性解法：解法已經在 repo 裡

`code_path_scan_service.py:174-176`：

```python
for node in ast.walk(tree):
    if not isinstance(node, ast.Call):
        continue
    symbol = _call_symbol(node.func)      # :225-235 遞迴解 dotted name
```

`ast.walk` **完全沒有 scope guard**，模組頂層與 class body 的呼叫全數抓得到；
`_call_symbol` 已經處理 `chromadb.HttpClient` 這種點分形式。既有測試與
masking 都已就位。

建議新增 `core/providers/ast_construction_provider.py`，形狀對齊
`code_pattern_provider.py`（`collect(inventory) -> ProviderScanResult`，
只吃 `.py`，`SyntaxError` → `ParseIssue`）。

**設計要點：用 scope-depth 計數器，不要逐一列舉語句型別。**
只在 `FunctionDef` / `AsyncFunctionDef` / `Lambda` 的 body 遞增 depth；
depth 0 的 `Call` 即為 import-time 建構。這一招統一涵蓋 `Assign`、
`AnnAssign`、裸 `Expr(Call)`、`With` / `AsyncWith`、list comprehension、
walrus，不必逐型別特判。

**`ClassDef` 不遞增 depth**——class body 的頂層語句在 import 時就執行一次。

### 2.4 通解（語言無關，可選）

UA 的 `extract-structure` 已經給每個函式的 `lineRange`。
「函式外呼叫」的定義就是「行號落在所有函式區間之外」——
**這是集合差集，不是推論**。若要跨語言處理，這條路比逐語言重寫 parser 便宜。

### 2.5 ⚠️ 實作雷區（會靜默寫錯的地方）

| # | 雷區 | 說明 |
|---|------|------|
| 1 | `import a.b.c` vs `import a.b.c as m` | 有 `as` 綁**完整點分模組**（`m.Foo` → `a.b.c.Foo`）；沒有 `as` **只綁頂層名 `a`**，後續 `a.b.c.Foo()` 必須照作者寫的屬性鏈解。兩者同樣處理會產出 `a.b.c.b.c.Foo` 這種重複片段 |
| 2 | 裝飾器 / 基底類別 / `def` 參數預設值 | 在**外層**作用域求值。naive visitor 若先遞增 depth 再 `generic_visit`，會把 `@app.on_event("startup")` 或 `def f(x=Client())` 誤判成埋在函式內 |
| 3 | `if TYPE_CHECKING:` | body 要跳過（runtime 不執行），`orelse` 要正常走 |
| 4 | `from X import *` | 無法靜態解析。標記 `is_star`，永遠落 `unresolved`，**不猜** |
| 5 | 跨檔案 re-export | `from .clients import QdrantClient`（而 `clients.py` 自己 `from qdrant_client import ...`）單檔解析只得到 `clients.QdrantClient`。保留「裸末段名」fallback 並明確標記，等同今天 regex 的行為，不是新風險 |
| 6 | `try: import X / except ImportError: X = None` | 兩個分支都在 depth 0，binding 照常記錄，不需特判 |
| 7 | metaclass / `__init_subclass__` 隱式建構 | 靜態分析看不到。**不發 fact** — 符合「缺席 ≠ negative」 |

### 2.6 意外收穫：AST 比 regex 強

`from qdrant_client import QdrantClient as QC` 之後的 `QC(...)`，
現有 regex `\bQdrantClient\s*\(` **完全無效**；AST 經 `alias.name` /
`alias.asname` 解得出來。

而 **UA 自己解不出來**：`extractFromImport`（`python-extractor.ts:294-333`）
處理 `from X import Y as Z` 時只把本地別名 `Z` 推進 `specifiers`，
**原始名 `Y` 直接蒸發**。這是「符號解析該在 Python 端做，而不是後處理 UA
JSON」最具體的技術論據。

### 2.7 關鍵發現：bridge rules 可以零改動

`ComponentBridgeRule.matches`（`component_bridge_models.py:52-58`）
只 key 在 `(fact.rule_id, fact.kind)` 加可選 file token：

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

- [ ] 在 `code_pattern_rules.toml` 每列加可選 `symbol` 欄位
      （如 `symbol = "qdrant_client.QdrantClient"`），
      讓 regex 目錄與 AST 符號目錄共用同一 source of truth，避免兩表漂移。
      加性變更，既有列不需修改。

`ParseIssue.provider` 是自由 `str`（`core/models/scan.py`），
可直接用 `provider="ast_construction"`，`scan_stage` 沿用既有
`"code_pattern_scan"` 即可，**不需改封閉 Literal**。

---

## 3. G2 — 工廠 / 間接建構

### 3.1 確定性階梯（先走完，再談殘量）

```text
1. 回傳型別標註      def get_vector_store(cfg) -> QdrantClient:
                     → 免費，但 UA 的 extractReturnType（python-extractor.ts:70-79）
                       只讀字面標註、不從 return 語句推論，且膠水碼少寫標註

2. 兩跳 in-repo 解析  工廠在專案內 → import map 給檔案 → symbol table 給行區間
                     → 只 AST 走那一段找 return
                     → 覆蓋絕大多數真實案例（RAG 工廠幾乎都在 repo 內）

3. framework 已知工廠  .as_retriever() / .from_documents()
                     → TOML 規則，已在做（code_pattern_retriever_as_retriever）
```

### 3.2 兩跳解析：限制追幾層（hop cap）＋ 防止繞圈（cycle guard）

固定點迭代，建議 `MAX_FACTORY_HOPS = 3`，另加 visited-set 防環。
回傳分類三種：`construction`（直接解到匯入符號）、
`delegate_call`（轉呼叫另一個專案內函式）、其他（終止，不發 fact）。

### 3.3 分支工廠**不得塌縮**

```python
if cfg.provider == "qdrant":
    return QdrantClient(...)
else:
    return ChromaClient(...)
```

這是**確定性事實**：「此工廠可建構兩種後端，執行期由 config 決定」。
**每個分支各發一筆 fact**，全部標 `indirect`，落到 `partial`——
這是誠實答案，不是待修的缺陷。

同理建議特判 RAG 膠水碼常見的 **dict registry 模式**：
`PROVIDERS = {"qdrant": QdrantClient}; return PROVIDERS[name](...)`，
同樣以析取（disjunction）處理。

### 3.4 邊界清單：到這裡就停，且必須停

| 邊界 | 例子 | 該做什麼 |
|------|------|----------|
| 參數傳遞型 | `def get_store(client): return client` | 不發 fact（需跨全部呼叫點的常數傳播，無界） |
| 反射式派發 | `getattr(m, name)()`、`importlib.import_module(s)` | 不發 fact |
| 不透明屬性鏈 | `return self.config.client` | 不發 fact |
| 裝飾器替換回傳值 | 自訂 `@registered_provider` | 不發 fact（無法與 `@lru_cache` 這類透明裝飾器區分） |
| 超過 hop 上限 / 成環 | — | 降級 `undetermined`，不得掛起或崩潰 |

**每個邊界的統一規則：發不出 fact 就什麼都不發。**
不得發 `not_detected`，不得捏造 `detected`。
若別處另有獨立訊號證明同一格，那筆 fact 自行成立；若都沒有，
`ProfileInferenceService` 既有的缺席處理會正確落在 `undetermined`。

### 3.5 殘量的正確答案是「問問題」，不是「猜答案」

一個 release gate 說

> `app/deps.py:41` 綁定了一個我無法靜態解析的 store，請確認是哪一個

比說「大概是 Qdrant」**更站得住也更有用**。
`undetermined` 在 mapping completeness 權重為 0，不會扭曲任何數字。

殘量走既有的 `MappingProposalService` 人工確認通道（見 §5）。

---

## 4. G3 — 外部 import 邊（投報率最高，優先做）

### 4.1 兩個丟棄點（不是一個）

```text
丟棄點 1：extract-import-map.mjs:1789 / :1781 / :1800
          if (out && ctx.fileSet.has(out)) resolvedSet.add(out)
          → 解析成功但不在專案內的路徑，全部靜默丟棄

丟棄點 2：extract-structure-result.mjs:106-111
          const internal = analysis.imports.filter(
              imp => (imp?.source ?? '').startsWith('.')
          );
          metrics.importCount = internal.length;
          → 只輸出「數量」，而且只算相對 import；來源字串完全不輸出
```

**資料沒有丟在解析階段。** tree-sitter 早就把 `import openai` 連同行號解析
出來了，是 UA 的兩條輸出路徑各自主動丟棄。

### 4.2 為什麼比現有訊號更強

| 來源 | 語意 | 證據等級 |
|------|------|----------|
| `dependency_manifest_rules.toml` | **宣告了**什麼依賴（requirements.txt） | indirect |
| 外部 import 邊 | **哪一行實際用了**（帶行號） | **direct** |

修好之後不只補洞，是**實質升級評估品質**，零 LLM。

### 4.3 解法裁定：在 Python 端獨立掃一次，**不改 vendored tree（外部借用的原始碼）**

`ref-opensource/CLAUDE.md` 明文：
「Never implement Systograph features inside this tree.
Changes to the vendored code are upstream contributions via the upstream repo.」

理由（依權重排序）：

1. **邊界文件明文禁止**——外部 import 用於 readiness 評估是 Systograph 功能，
   不是通用的 upstream 修正
2. **改了也只涵蓋 Python**：UA 的 `resolveImport` 是逐語言 dispatch
   （`extract-import-map.mjs:1623-1661`），要全語言涵蓋得逐一改 + 改輸出
   schema + 等 upstream review；而 `ast.Import` / `ast.ImportFrom`
   在最重要的那個語言上約 15 行就解決
3. **本地 diff 會變成永久 rebase 負擔**（submodule 是刻意 pin 的）
4. **幾乎是 G1 的免費副產品**：G1 的 binding table 已記錄
   `(local_name → module, original_name)`，過濾掉專案自己的 package root
   就是答案——正好是 UA `fileSet` 過濾掉的那一半

`project_module_roots` 可由 `ProjectScanService` 既有的專案佈局理解推導，
不需新能力。

---

## 5. 共用前置：證據來源硬化（三位專家獨立指出同一處）

`canonical_evidence_service.py:26-31`：

```python
evidence_kind: AssessmentEvidenceKind = (
    "direct"
    if item.file is not None
    and (item.line_start is not None or json_pointer is not None)
    else "indirect"
)
```

**判定純粹看形狀，全函式沒有任何來源檢查。** `direct` 只用「一個檔名 + 一個
行號」就買得到。

### 5.1 為什麼這是硬前置

`reference_capability_assessment_service.py:147-151` 的 `direct` **只從
`component_evidence` 取**，`:170-187` 的階梯是：

```python
if active_components and direct and coverage_evidence_ids:  "conflicted"
elif active_components and direct:                          "detected"
elif active_components or candidates:                       "partial"
elif coverage_evidence_ids:                                 "not_detected"
else:                                                       "undetermined"
```

任何「帶行號但屬推論」的 fact（G2 兩跳解析的結果就是典型）都會被
形狀啟發式**自動升級成 `direct`** → 節點升成 `detected` → 五態契約破功，
**而且型別系統攔不住、code review 也很難看出來**。

### 5.2 建議修法（加性 = 只加不改，既有程式完全不受影響）

```python
# core/models/system_map.py — Evidence 新增欄位
evidence_kind_hint: AssessmentEvidenceKind | None = None
```

```python
# canonical_evidence_service.py — 有 hint 時優先採用
evidence_kind = (
    item.evidence_kind_hint
    if item.evidence_kind_hint is not None
    else (原本的形狀判定)
)
```

既有 provider 全部不設此欄，行為完全不變。

- [ ] 此變更同時是 [`16C`](./16C-component-attribution-and-edge-derivation.md)
      L1/L2 分級的正確性前提

---

## 6. LLM 邊界裁定

### 6.1 裁定：**不得進入掃描路徑（Step 3）**

`ref-opensource/systograph-understand-anything-integration-boundary.md` §8 第 6 條
（文件狀態 `Accepted（2026-07-07 P0 決策拍板）`）：

> **Phase2 不呼叫 LLM**；若 Plan 17 日後重啟，只能接收 bounded、masked
> evidence，不得把整個 repo 原始碼一次送入模型。

同文件 §9 另裁定 generic semantic relationship 候選為
`Plan 17 / post-Phase2 deferred；Phase2 不產生`——而 G2 在定義上正是這一類。

**推翻此決策是合法的，但必須走書面取代性修訂，不是 feature PR。**

### 6.2 三個會壞掉的機制（全部驗證過）

**① `scan_id` 的 digest 退化成執行序號**

`scan_snapshot_service.py:73-80` 對**整個 `scan_result`** 做 SHA-256：

```python
payload = scan_result.model_dump(mode="json")
digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ...)).hexdigest()
```

LLM 輸出一旦進 `scan_result`，byte-identical 的 repo 每次掃描 digest 都不同。
它從「內容綁定」變成隨機 token，而快照不可變（同 id 不同內容 →
`StateConflictError`），沒有和解路徑。

**② Apply 與 Rescan 語意互相矛盾**

```text
Apply   重放同一 scan_id 的 scan_result
        → LLM 那一次的猜測被凍進快照，被所有後代 build_id 永久繼承

Rescan  新 scan_id 全部重跑
        → 同一個沒改過的 repo 得到不同的圖

淨效果：同一掃描內的 build 彼此一致，跨掃描不一致
        使用者心裡的「重掃刷新」變成「重骰一次」
```

**③ Gate-2 / Gate-3 失去量測工具**

那兩個 gate 要的是 UA-vs-TOML 的 **parity report**——parity 就是兩次執行的
diff。對非確定性來源做 diff，**真實退化與取樣雜訊分不出來**。
這不只是通不過 gate，是把 gate 的量測儀器刪掉。

**④ 額外的 fail-closed 陷阱**

`project_scan_service.py:151-161` 會把 provider 例外吞成 `ParseIssue` +
warning 然後 `continue`。LLM 若當一般 provider 插進去會繼承這個吞噬行為——
**模型 timeout 時掃描靜悄悄降級，但 build 照樣發布**。

### 6.3 唯一合法通道（已由程式碼結構保證）

```text
LLM 提議 → 人工採納 → ManualMapping → CapabilityCandidateComponent → 最多 partial
```

`reference_capability_assessment_service.py:147-151` 的 `direct` **只從
`component_evidence` 取**，`candidate_evidence` 被結構性排除、一律落
`indirect`。**capability-candidate 通道在數學上不可能產生 `detected`**——
靠構造保證，不是靠慣例。

既有 `MappingProposalService` 已是「LLM-propose + deterministic-verify」模式：

| 保護 | 落實位置 |
|------|----------|
| 只給 bounded / masked packet（12 筆、240 字元上限） | `mapping_evidence_packet_builder.py:26-27`、`:110-113` |
| **不能自造證據**：引用 packet 外的 evidence id 直接拒絕 | `mapping_proposal_candidates.py:105-112` |
| 未知 target slot 拒絕 | `mapping_proposal_candidates.py:114-119` |
| 只有人工 `decide()` 才落地，帶 `proposal_id` / `decision_source` | `mapping_proposal_service.py` |

**新的 LLM 介面必須重用這個 validator，不得重寫。**

### 6.4 永遠不得寫入的欄位（實作時逐條加測試）

- `AiSystemMapV2.components[]` / `edges[]`（bridge 獨佔）
- `CanonicalEdge.relationship`（這是讓卡片翻 `detected` 的欄位）
- 任何 `evidence_kind="direct"` 的 `CanonicalEvidence`
- 任何 `evidence_kind="explicit_negative"` 且 `rule_id` 以
  `coverage.reference.` 開頭的 evidence
  （`reference_capability_assessment_service.py:56-65` 會據此鑄出
  `not_detected`，而 `not_detected` 在 mapping completeness 權重為 **1**，
  與 `detected` 相同——**幻覺的「不存在」會和幻覺的「存在」一樣灌水**）
- `ReferenceCapabilityAssessment.status` / `ProfileFinding.*` /
  `MappingCompleteness.*` / `ReadinessFinding.status`
- 任何 `confidence` / `score` / `quality` / 及格與否的字彙
- 任何自創的 relationship 名（見 16A §7.2 字彙漂移）

### 6.5 Schema 阻擋點

`schemas/ai-system-map.v2.schema.json` 有 **12 處** `additionalProperties: false`。
**目前沒有任何地方可以記錄「這筆是 LLM 猜的」。**
任何要發布的 LLM 衍生值都得先做 schema migration——
而沒有文件化的破壞性 schema 變更在 `AGENTS.md` 是 **P1**。

### 6.6 若日後要做，動工前必須通過的檢查清單

- [ ] 先寫取代性修訂進 boundary doc §8.6（比照該檔既有修訂體例）
- [ ] 決定性測試：同 fixture × N ≥ 20 次 → `ai_system_map.json` 除 `build_id`
      外 byte-identical。**若 LLM 訊號在 `scan_result` 內，此測試必然失敗——
      那個失敗就是設計評審結論**
- [ ] Apply 重放穩定性測試（守 `apply_confirmations_service.py` 的
      evidence id 子集檢查）
- [ ] 對抗性 fixture：含注入形狀的註解／docstring／檔名，斷言 52 格與 15 張卡
      **零變化**
- [ ] fail-closed：必須在 provider loop 之上拋出，不得被 §6.2 ④ 吞掉
- [ ] parity harness 必須能在 LLM 關閉下跑，產生確定性基準線
- [ ] 預設 **OFF**，opt-in env flag（比照
      `SYSTOGRAPH_ENABLE_NVIDIA_NIM_PROPOSALS`）
- [ ] **先落地 [`../../../final-phase-hardening/161-fix-proposal-prompt-untrusted-evidence-isolation.md`](../../../final-phase-hardening/161-fix-proposal-prompt-untrusted-evidence-isolation.md)**——
      現在既有那條 LLM 路徑正用 `temperature = 1.0`
      （`core/configs/llm_proposal.toml:11-12`）跑**未加固**的 prompt 吃不可信
      的 repo 文字。**先修好已經有的那個 LLM，再談加第二個。**

---

## 7. 已拍板決策

| # | 決策 | 理由 |
|---|------|------|
| 1 | G1 / G3 走確定性解法，**零 LLM** | 解法已存在或成本極低；用 LLM 取代會是退步 |
| 2 | G2 殘量走既有人工確認通道，**不新建子系統** | boundary doc §9 明定 `AssessmentOrchestrator` 為 Plan 17 deferred |
| 3 | UA 維持 12 語言 primary，**不倒轉為 Python-primary** | 避免兩套結構不同的 fact 產生管線，違反「core engine 平台獨立」原則 |
| 4 | 新增 Python-only **補充** provider，範圍嚴格限於 G1 + G3 | 只補 UA 架構上（`functionStack` 守衛、`fileSet` 過濾）先天做不到的兩件事 |
| 5 | **NIM → local model 延後，本階段不做** | 2026-08-04 使用者裁定：**本機硬體不足**。此項與三個缺口完全脫鉤，日後獨立 PR 處理即可，不阻塞任何 gate |

### 7.1 關於決策 5 的補充

三位專家原本都建議把 `llm_proposal.toml:5` 的
`https://integrate.api.nvidia.com` 換成本地模型，理由是符合
`CLAUDE.md` 的 local-first privacy 主張。

**此建議已裁定延後，原因是硬體限制，不是技術反對。** 記錄要點供日後重啟：

- 走完確定性階梯後，500 檔 repo 的 G2 殘量約**數十個**未解析點，不是數千個
  → 這不是吞吐問題，**vLLM 是錯的選擇**（要獨佔 GPU + 常駐 server）
- 建議 runtime 為 Ollama：`llm_proposal_provider.py` 已用 `httpx` POST
  OpenAI 格式 JSON，等於改個 `base_url` 加一個子類，整合成本最低
- 模型不宜低於 7B（3B 級在封閉詞彙結構化輸出上失敗率高到讓 repair loop
  變常態）
- **架構建議（與硬體無關，日後仍適用）**：不要在掃描時批次跑，改成使用者在
  Mapping UI 點開某個 unmapped component 時才觸發——這樣結構上保證
  LLM 永遠不在 build path 上
- 另註：`llm_proposal.toml:6` 釘的 `google/gemma-4-31b-it` 值得對一次
  NIM 目前 catalog 是否仍存在（未驗證，僅提醒）

---

## 8. 建議執行順序

```text
1. G3 撈回外部 import              零 LLM，投報率最高，證據等級升 direct
        │
2. G1 新增 ast_construction_provider   沿用既有 rule_id → bridge 零改動
   + 把 parity 寫進 Plan 18 退役準則
        │
3. 補 Evidence.evidence_kind_hint     加性；16C 與 G2 的正確性前提
        │
4. 完成 Plan 16 到 Gate-2             semantic = null；建立確定性基準線
        │
5. 落地 #161                          修好既有 LLM 路徑的注入防護
        │
6. G2 走人工確認通道                   + 用 Plan 14 真實 repo 量工廠模式的
                                       實際頻率（唯一能證明風險值不值得的數字）
        │
7.（延後）NIM → local model            硬體就緒後獨立 PR，不阻塞任何 gate
```

**第 6 步的「量」是關鍵**：現在沒有人知道工廠模式在真實 RAG repo 裡出現的
頻率。在拿到那個數字之前，任何「為 G2 引入新子系統」的提案都缺少論證基礎。

---

## 9. 相關檔案

| 檔案 | 角色 |
|------|------|
| [`16-implement-understand-anything-sidecar-service.md`](./16-implement-understand-anything-sidecar-service.md) | S2 實作主 plan |
| [`16A-q3-lv2-call-graph-flow-visualization.md`](./16A-q3-lv2-call-graph-flow-visualization.md) | Lv2 決策（call graph 為槓桿點） |
| [`16B-ua-sidecar-io-adapter-reference.md`](./16B-ua-sidecar-io-adapter-reference.md) | UA I/O 實測 + adapter 三條硬規則 |
| [`16C-component-attribution-and-edge-derivation.md`](./16C-component-attribution-and-edge-derivation.md) | 檔案層→元件層歸屬與邊推導（消費本檔的 G1 產物） |
| [`16D-call-priority-consumer-cutover.md`](./16D-call-priority-consumer-cutover.md) | Step 4～7 消費順序改 call 優先（接在 16C 之後） |
| `ref-opensource/systograph-understand-anything-integration-boundary.md` | §8 read-only/安全邊界（最高權威，§6.1 引用來源） |
| `../../../final-phase-hardening/161-*.md` | 既有 LLM 路徑的注入防護（§6.6 前置） |
| `src/systograph/core/services/code_path_scan_service.py` | `ast.walk` 無 scope guard（G1 現成參考） |
| `src/systograph/core/services/canonical_evidence_service.py` | 形狀判定 direct/indirect（§5 出處） |
| `src/systograph/core/services/reference_capability_assessment_service.py` | 五態階梯 + coverage 前綴（§5.1、§6.4 出處） |
| `src/systograph/core/services/component_bridge_models.py` | `matches` 只 key `(rule_id, kind)`（§2.7 出處） |
| `src/systograph/core/services/mapping_proposal_candidates.py` | 候選驗證（§6.3 必須重用者） |
| `src/systograph/core/services/scan_snapshot_service.py` | scan_result 全量 SHA-256（§6.2 ① 出處） |
| `ref-opensource/Understand-Anything/.../extractors/python-extractor.ts` | `functionStack` 守衛與 alias 遺失（§2.1、§2.6 出處） |
