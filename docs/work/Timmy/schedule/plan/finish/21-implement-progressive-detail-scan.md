# Task 21: Implement Progressive Detail Scan

## 目標
實作 L2 `ComponentDetailScanService` 與 L3 `CodePathScanService`，讓使用者能針對 component、extension、unmapped、edge、evidence 做 bounded detail scan。結果寫入 `detail_scans[]`，不得繞過 validation 改寫 canonical facts。

## 為什麼要先做這個
L1 system map 先可用後，才需要 progressive drill-down。這符合設計文件要求：先粗看，再由使用者選特定元件深入，避免一開始做 whole-repo call graph。

## 最新狀態校正（2026-06-08）

Task 20 已完成下列可重用基礎，本任務需要知道以下邊界才能正確銜接：

### 已完成可重用的部分

- `src/systograph/core/models/system_map.py` 已定義 `DetailScanResult`、`DetailScanFinding`、`CodePathStep`。不需要另建 `detail_scan.py`。
- `src/systograph/core/services/mapping_evidence_packet_builder.py` 已建立，由 Task 20 完成。本任務需擴充它，讓它能讀 detail scan 發現的 evidence，不要重複建立一個新的 builder。
- `SystemMapNormalizeService.normalize()` 已接受 `detail_scans: Sequence[DetailScanResult] | None` 參數，`SystemMapValidationService` 也已驗證 `detail_scans[]` 的 target 是否存在、findings 的 evidence id 是否合法。Schema 端已準備好。

### 目前的缺口（本任務要補的）

- `MapBuildService._build_system_map()` 沒有把 `detail_scans` 傳進 `normalize()`，所以 `ai_system_map.json` 的 `detail_scans[]` 永遠是空陣列。本任務需提供獨立的 detail scan 觸發路徑，不走 `_build_system_map()`，而是由 `POST /api/detail-scans` route 觸發後 append 結果。
- `DetailScanService`、`ComponentDetailScanService`、`CodePathScanService` 皆尚未存在。
- Web route `detail_scan_routes.py` 尚未存在。

### Evidence 連接機制（Task 21 最重要的設計決策）

這是 Task 21 銜接 Task 20 的核心：

**`MappingEvidencePacketBuilder` 的現行邏輯：**

```python
# mapping_evidence_packet_builder.py
referenced = set(unmapped_component.evidence_ids)   # ← 只讀這個 index
selected = [item for item in evidence if item.id in referenced]  # ← 從 canonical evidence[] 反查
```

也就是說，AI 能看到的 evidence 由兩個條件決定：
1. `unmapped_component.evidence_ids` 包含該 evidence id
2. `system_map.evidence[]` 中存在該 evidence id 對應的完整 Evidence 物件

**Task 21 必須同時做到這兩件事，detail scan signal 才能進 AI input：**

1. 把新抽取到的 signal 建立成 `Evidence` 物件，寫入 canonical `system_map.evidence[]`
2. 把新 evidence id 掛到對應 `UnmappedComponent.evidence_ids`（或 extension、component）

若 L2/L3 只把結果放在 `detail_scans[].findings[]` 而沒有同時更新 `evidence[]` 與 `unmapped_component.evidence_ids`，Task 20 的 proposal flow 永遠看不到這些 detail scan signal。

**建議的兩層輸出：**

```text
detail scan 執行後：
  ① detail_scans[]      ← 給前端顯示 findings summary、code_path、warnings
  ② evidence[]          ← 把 detail signal 加進 canonical evidence，讓 Task 20 能用
  ③ unmapped_component.evidence_ids ← 把新 evidence id 掛上去，讓 packet builder 能查到
```

這樣的好處是粗掃 evidence 和細掃 evidence 都用同一個 indexed 查詢，不需要改 packet builder 的核心邏輯。

## 產品與架構校正
本任務是 Task 20 AI proposal 的安全上下文來源之一。它要幫使用者和 AI 看「足夠相關、已遮蔽、可追溯」的 evidence，而不是讓 AI 自己翻整個 repo。

合理設計是由 Python scanner / detail scan service 先產生 bounded `MappingEvidencePacket`：

- 只針對使用者選到的 target-related files。
- 擷取 imports、class/function signatures、decorators、call-like patterns、相鄰少量 masked snippets。
- 記錄 evidence ids、line range、rule ids、source file、context limit metadata。
- 所有 snippet / value 必須先經過 `SecretMaskingService`。
- 不執行 target project，不使用 `sys.settrace`，不呼叫 runtime endpoint。

Task 20 可以把這份 packet 餵給 deterministic fallback 或 optional local LLM 產生候選；但本任務產出的 detail/evidence 本身仍不得直接升級成 canonical component / extension / flow edge。

### 為什麼 detail scan 要 deterministic + bounded

本任務不能改成「讓 local AI 自己掃整個 repo」。即使模型在本機執行，whole-repo prompt scanning 仍不適合 release-readiness gate：

- 不可重現：同一份 repo 需要穩定產生相同 target-scoped evidence，否則無法回歸測試、無法在 CI 或 demo 前當 gate。
- Evidence chain 會斷：Systograph 需要 file、line range、rule id、evidence id、masked snippet。LLM 直接讀 repo 容易輸出不可追溯摘要或 hallucinated path。
- 長上下文不可靠：大 context 不代表模型會穩定注意到中間檔案或深層 call；lost-in-the-middle 類問題會讓全 repo prompt 掃描漏看高價值片段。
- prompt injection 風險：source code、README、註解、fixture 都是 untrusted input。detail scan 應把它們視為資料，不可讓這些內容控制 scanner 或 LLM 行為。
- 效能與資源成本：用 deterministic parser 先抽 imports / signatures / call-like hints，通常能用很小 packet 表達關鍵訊號；直接餵整個 repo 給地端模型會慢且容易 OOM。

因此 L2/L3 的責任是先用可測、可重現、可裁切的 Python code 產生 high-signal packet，再讓 Task 20 optional LLM 做候選 mapping 語意判斷。這是 Semgrep / CodeQL / SAST+LLM 研究共同支持的 hybrid pattern：static analysis 先建立 findings，再讓 AI 做 triage / explanation / proposal，而不是反過來。

### 外部參考與取捨

- Semgrep：參考 rule id、file location、matched pattern、bounded finding 的資料模型；第一版不要引入 Semgrep runtime，也不要假裝支援完整 Semgrep rule language。
- CodeQL：參考「先建立可查詢的 code facts / database，再用 query 找證據」的思路；Task 21 不需要實作 CodeQL dataflow，只需保留 deterministic query-like extraction 與 evidence traceability。
- IRIS-SAST / SAST+LLM 研究：參考 hybrid SAST + LLM 的分工。LLM 可輔助 triage 或 reduce false positives，但 finding source 仍應是 static analyzer。
- Lost-in-the-middle 研究：支持本任務不要把整個 repo 放進 prompt；要用 target selection、context budget、bounded snippets 降低長上下文遺漏。
- Tree-sitter / Python `ast`：第一版以 Python standard library `ast` + bounded regex 為主；Tree-sitter 可作多語言未來強化，不應阻塞本任務。

## 承接 Task 16 延後功能
- 承接 Task 16 「不做 progressive detail scan / L2-L3 lazy loading」的延後範圍。
- Task 16 只建立 L1 map build 與 basic event shell；本任務才處理使用者點選 graph target 後的 bounded detail scan。
- Task 18 提供完整 `GraphViewModel` 後，本任務的 target id 必須能對應 `node_id`、`edge_id`、`component_id`、`source_id` 或 evidence id。
- 因為 GUI/local web UI 需要 lazy loading，本任務要提供 detail scan API 與必要的 progress event。

## 前置需求
- Task 16 已有 L1 map build。
- Task 18 已有 viewer graph projection。
- Task 20 已有 mapping proposal flow 可處理 detail scan 發現的不確定 mapping。

## 實作範圍
- 建立 `DetailScanService` 作為入口。
- 建立 `ComponentDetailScanService` 做 L2。
- 建立 `CodePathScanService` 做 L3。
- target validation：slot/component/extension/unmapped/edge/evidence 必須存在。
- L2/L3 只掃 target-related files。
- 產生或更新 target-scoped `MappingEvidencePacket`，供 Task 20 proposal 使用。
- 第一版可用 Python `ast` / bounded regex pattern 抽取 Python imports、class/function signatures、decorators、call-like hints；Tree-sitter 可作未來多語言強化。
- 對 snippets 設定明確上限，例如 per snippet max chars、per file max snippets、per packet max chars。
- 對 target files 設定明確上限，例如 max files per target、max functions/classes per file、max call-like hints per packet；超過時標示 truncated / best_effort。
- L3 call-like hints 只能表示 static observation，例如 `module.call(...)`、`self.retriever.invoke(...)`、`vectorstore.similarity_search(...)`，不得宣稱已證明 runtime path。
- 將結果 append 到 `detail_scans[]` 並重新 validate。
- 使用 FastAPI 建立 detail scan route，例如 `POST /api/detail-scans`、`GET /api/detail-scans/{detail_scan_id}`。
- 更新 `GET /api/scan/events` 或新增 detail-specific event，讓前端能顯示 selected target 的進度。
- 更新 Epic 1 local API guide，加入 target ids、detail result schema、lazy loading rule。

## 不包含範圍
- 不做完整 call graph。
- 不做 whole-repo LLM scan。
- 不追 framework/runtime internals。
- 不讓 AI 自己決定要讀哪些檔案。
- 不把整份 raw source file 交給 AI。
- 不執行目標專案、不使用 `sys.settrace`、不做 in-process runtime instrumentation。
- 不呼叫 runtime endpoint；Task 22 才處理 opt-in query trace。
- 不把 detail scan 結果直接升級成 detected slot。
- 不拆成外部 detail artifact，Epic 1 先寫回同一 JSON。
- 不做 frontend detail panel；本任務只提供 backend API 與 data contract。

## 建議實作步驟

> `DetailScanResult`、`DetailScanFinding`、`CodePathStep` 已在 `system_map.py` 定義，步驟 1 改為確認而非新建。

1. 確認 `src/systograph/core/models/system_map.py` 中 `DetailScanResult`、`DetailScanFinding`、`CodePathStep` 已符合本任務需要，必要時補充欄位（例如 `best_effort`、`context_budget_metadata`）。若有欄位需求超出現有 contract，記得同步更新 `SystemMapValidationService`。
2. 建立 `src/systograph/core/services/detail_scan_service.py` 作為 L2/L3 入口 dispatcher；它接收 target type 與 target id，決定走 `ComponentDetailScanService` 或 `CodePathScanService`。
3. 建立 `component_detail_scan_service.py` 做 L2 bounded scan：只看 target component 關聯的 source files，用 Python `ast` 抽取 imports、class/function signatures、decorators，並用 `SecretMaskingService` 遮蔽 snippet value。
4. 建立 `code_path_scan_service.py` 做 L3 bounded call-like extraction：從 L2 找到的 function 往下抽 call-like hints；所有 call-like signal 必須帶 source file、line range；標示 `best_effort`，不可宣稱 runtime execution 已確認。
5. **實作 evidence 連接機制（最關鍵步驟）**：L2/L3 找到的新 signal 必須同時：
   - 建立 `Evidence` 物件（帶 id、kind、file、line_start、line_end、rule_id、masked snippet）
   - 把新 evidence id 追加到對應 `UnmappedComponent.evidence_ids`（或 `ExtensionComponent.evidence_ids`）
   - 把新 `Evidence` 加入 canonical `system_map.evidence[]`
   - 把 `DetailScanResult` 加入 `system_map.detail_scans[]`
   這樣 `MappingEvidencePacketBuilder`（Task 20）不需要修改核心邏輯，就能自動把 detail scan signal 納入 AI proposal input。
6. 重用（不重建）`MappingEvidencePacketBuilder`，確認它能正確從更新後的 `evidence[]` 與 `unmapped_component.evidence_ids` 建立 packet，不需要額外感知 `detail_scans[]` 結構。
7. 實作 target validation：slot/component/extension/unmapped/edge/evidence id 必須存在於目前 loaded map，不存在則回傳 422 並不寫入。
8. 實作 context budget：限制 max target files、per-snippet max chars、per-packet max evidence items、max call-like hints；超過時在 `DetailScanResult.warnings` 與 `context_limits` metadata 標示 `truncated: true` / `best_effort: true`。
9. 對 Python AST extraction 加入 prompt-injection-safe handling：source text 只作語法解析，不可被放進 system instruction；輸出只保留 masked snippets / normalized signatures，不輸出 raw 解析後的 docstring 或 annotation string literal。
10. 呼叫 `SystemMapValidationService.validate()` 確認追加 evidence 與 detail scan 後整份 map 仍合法；失敗時不寫入，rollback 並記錄錯誤。
11. 建立 FastAPI detail scan routes：`POST /api/detail-scans` 觸發掃描並更新 session store 的 map；`GET /api/detail-scans/{detail_scan_id}` 查詢結果。Route 只能呼叫 `DetailScanService`，不直接呼叫 `ComponentDetailScanService` 或 AST parser。
12. 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`，加入 detail scan request/response contract、target id 規則、evidence 追加行為說明、lazy loading rule。
13. 測試：L2 只掃 target 相關檔案；L3 標示 best_effort；invalid target 422；detail scan 後 `MappingEvidencePacketBuilder` 可在 AI proposal 中看到新 evidence；packet 不含 raw full file；不呼叫 runtime endpoint；source comment 中的 prompt-like text 不改變 scanner 行為；`SecretMaskingService` 套用在所有 snippet。

## 預期輸出

> `DetailScanResult`、`DetailScanFinding`、`CodePathStep` 已在 `src/systograph/core/models/system_map.py` 定義，不需要另建 `detail_scan.py`。

- 更新 `src/systograph/core/models/system_map.py`（若需補充 `best_effort`、`context_budget_metadata` 欄位）
- `src/systograph/core/services/detail_scan_service.py`
- `src/systograph/core/services/component_detail_scan_service.py`
- `src/systograph/core/services/code_path_scan_service.py`
- 更新 `src/systograph/core/services/mapping_evidence_packet_builder.py`（Task 20 已建立；本任務確認 builder 可正確消費 detail scan 追加的新 evidence，必要時補充 test coverage）
- `src/systograph/web/routes/detail_scan_routes.py`
- 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`
- `tests/unit/core/test_detail_scan_service.py`
- 更新 `tests/unit/core/test_mapping_evidence_packet_builder.py`（補 detail scan evidence 場景）
- `tests/web/test_detail_scan_routes.py`

## 驗收標準
- L2 只掃 target 相關檔案，不掃整個 repo。
- L3 call-like hints 標示 `best_effort`，不宣稱 runtime execution 已確認，並附 source file / line range / evidence id。
- `detail_scans[]` 不含大量 raw source 或 unmasked secret；所有 snippet 已過 `SecretMaskingService`。
- **detail scan 執行後，`MappingEvidencePacketBuilder` 能在下一次 proposal 建立時，自動把 detail scan 抽到的新 evidence 納入 `MappingEvidencePacket`。** 這是連接 Task 21 與 Task 20 的核心驗收條件。
- 新 evidence 同時出現在 `system_map.evidence[]` 與對應 `unmapped_component.evidence_ids`（或 extension）。
- `MappingEvidencePacket` 只包含 bounded、masked、target-scoped context；packet builder 不需要另外讀 `detail_scans[]` 結構。
- detail scan 不會給 AI file tool、project root、raw source dump 或 shell/runtime 權限。
- detail scan 不會執行 target project、`sys.settrace` 或 runtime endpoint call。
- 追加 detail scan 後，整份 map 仍通過 `SystemMapValidationService.validate()`；validation 失敗時不寫入。
- invalid target 不會寫入 map，回傳 422。
- local web API 可依 target id 觸發 bounded detail scan。
- API guide 已同步記錄 detail scan request/response、evidence 追加行為與 lazy loading rule。

## 可能風險與注意事項
- Tree-sitter 可作未來改善，但第一版不要因此卡住。
- 不要追 LangChain/OpenAI/Qdrant client internals。
- 單純 AST/import/call-like signal 仍可能不足以證明 runtime path，因此 response 要保留 uncertainty，不要把它包裝成已確認事實。
- 如果使用者需要 runtime 證據，應導到 Task 22 opt-in query trace，而不是在 detail scan 偷偷執行目標程式。
- 參考依據：Tree-sitter 官方 docs 可支援 bounded AST extraction；設計文件明確要求 L3 != whole-repo call graph。
- 不要把 Semgrep / CodeQL 當成本任務必要依賴；本任務只採用其 traceable finding / query-first 思路。未來若整合外部 scanner，必須透過 adapter 轉成 Systograph evidence model，再經 validation。

## 參考資料
- Semgrep rules / pattern syntax: https://semgrep.dev/docs/running-rules/ , https://semgrep.dev/docs/writing-rules/pattern-syntax
- CodeQL code database + query model: https://codeql.github.com/docs/codeql-overview/about-codeql/
- IRIS-SAST hybrid SAST + LLM reference: https://github.com/iris-sast/iris
- Lost in the Middle: https://arxiv.org/abs/2307.03172
- Tree-sitter docs: https://tree-sitter.github.io/tree-sitter/
- OWASP Top 10 for LLM Applications: https://owasp.org/www-project-top-10-for-large-language-model-applications/

## 新手提示
Detail scan 是放大鏡，不是重新掃整個城市。使用者點哪裡，就只看那附近。

## 視覺化說明

### 掃描層次（粗 → 細）

```text
L1  System Map Scan（粗掃）
    ├─ 掃整個 project 的 config、dependency、docker、code pattern
    ├─ 產出 evidence[]、unmapped_components[]
    └─ scan_depth = "system"

    ↓ 使用者點某個 component node

L2  ComponentDetailScan（中掃）
    ├─ 只看 target component 相關的 source files
    ├─ 用 Python ast 抽取 imports、class/function signatures、decorators
    ├─ 產出較細的 Evidence（file + line range + masked snippet）
    └─ scan_depth = "component"

    ↓ 使用者再點某個 function / edge / call hint

L3  CodePathScan（細掃）
    ├─ 從 L2 找到的 function 往下追 call-like hints
    ├─ 抽取 call chain：self.retriever.invoke(...)、vectorstore.search(...)
    ├─ 每個 call-like hint 必須附 source file + line range
    ├─ 標示 best_effort：static observation only，不代表 runtime 已確認
    └─ scan_depth = "code_path"
```

### Detail scan 觸發路徑與 evidence 連接

```text
┌──────────────────────────────────┐
│ L1 base map                      │
│ evidence[]  unmapped[]           │
└──────────────────┬───────────────┘
                   ↓ POST /api/detail-scans
         ┌─────────┴─────────────┐
         │ target_type?          │
    component/slot            edge / evidence / call hint
         ↓                        ↓
┌──────────────────┐      ┌──────────────────────┐
│ L2               │      │ L3                   │
│ ComponentDetail  │  或   │ CodePathScan          │
│ Scan             │  之後  │ (L2 之後可繼續深入)   │
│ (ast + regex)    │ ────→ │ (call-like hints)    │
└────────┬─────────┘      └──────────┬───────────┘
         └──────────────────┬────────┘
                            ↓ 同時寫入三個地方
         ┌──────────────────────────────────────────┐
         │ ① evidence[]        新 Evidence 物件      │
         │ ② unmapped[].evidence_ids  追加新 id      │
         │ ③ detail_scans[]    findings + code_path  │
         └──────────────────────┬───────────────────┘
                                ↓
         ┌──────────────────────────────────┐
         │ SystemMapValidationService       │
         │ validate 整份 map 仍合法          │
         └──────────────────────────────────┘
```

### Detail scan evidence 如何進入 Task 20 AI input

```text
L1 + L2 + L3 scan 後                Task 20 proposal 建立時
─────────────────────────           ──────────────────────────────────
unmapped_component                  MappingEvidencePacketBuilder.build()
  .evidence_ids                       ↓
  = ["evid:L1-a",     ←──────────  referenced = set(unmapped.evidence_ids)
     "evid:L2-new",                 selected = [e for e in evidence
     "evid:L3-call"]                            if e.id in referenced]
                                      ↓
evidence[]                          MappingEvidencePacket
  = [Evidence(id="evid:L1-a"),       .evidence_ids = ["evid:L1-a",
     Evidence(id="evid:L2-new"),                       "evid:L2-new",
     Evidence(id="evid:L3-call")]                       "evid:L3-call"]
                                      .masked_snippets = [L1, L2, L3 snippets]
                                      ↓
                                    LLM / deterministic fallback
                                    → 粗/中/細掃 signal 全部進入 AI input
```

