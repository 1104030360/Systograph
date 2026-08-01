# Residue C — Frontend handoff 殘留稽核（Plan 13 v2 cutover）

READ-ONLY 稽核。Baseline：`pnpm exec tsc -b --noEmit` exit 0；`pnpm test` = 3 files / 7 tests passed（與 Plan 13 L114 宣稱一致）。

---

## 先釐清「5 筆」的定義

`tests/contracts/test_v2_cutover_consumer_allowlist.py` 的 `_text_legacy_hits()`（L307-320）對每個 `(file, symbol)` 只做一次 `re.search`，**命中即記一筆**。所以它是 **file × symbol 去重計數**，不是行數計數。

實測（用同一份演算法重跑 `frontend/src`）：

```
('frontend/src/components/proposal/EditForm.tsx',      'new_extension_component')
('frontend/src/data/frontend-json-sample.json',        'ai-system-map/v1')
('frontend/src/data/frontend-json-sample.json',        'new_extension_component')
('frontend/src/data/scanTemplate.mock.ts',             'new_extension_component')
('frontend/src/types.ts',                              'new_extension_component')
TOTAL UNIQUE PAIRS = 5
```

而 raw grep 命中是 **9 行**（`scanTemplate.mock.ts` 1、`types.ts` 2、`frontend-json-sample.json` 5、`EditForm.tsx` 1）。

**census 掃不到的東西**（`LEGACY_NAMES ∪ LEGACY_LITERALS` 只有 `RagSystemMap` / `ExtensionComponent` / `SystemMapValidationService` / `new_extension_component` / `ai-system-map/v1`，且用 `(?<![A-Za-z0-9_])…(?![A-Za-z0-9_])` word boundary）：

| 未被 census 看見的 v1 殘留 | 位置 |
| --- | --- |
| `ui_extension` slot 字面值 | `scanTemplate.mock.ts:204,237`、`EditForm.tsx:38` |
| top-level `extensions[]` | `frontend-json-sample.json:568` |
| `extension:*` id prefix（9 處） | `frontend-json-sample.json` |
| `confirm_as_extension_component` / `confirm_as_retriever_extension` | `frontend-json-sample.json:592-593` |
| v1-only map 欄位（`components_by_slot` / `flows` / `query_trace_events` / `scan_summary` / `scan_depth` / `detail_scans` / `recommended_next_checks` / `classification` / `reference_architecture`） | sample JSON + `types.ts` + `App.tsx` + `sampleMap.ts` |
| node `type: "extension"`、edge `status: "needs_confirmation"` | sample gvm + `utils/graph.ts:197` |

**結論：allowlist 的 5 筆歸零，並不等於 frontend v1 殘留歸零。** 這 5 筆是必要條件、遠不是充分條件。

---

## 權威 handoff 清單

| # | 檔案 | 行號 | 內容 | allowlist 5 筆之一？ | 連鎖影響 | 風險 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `frontend/src/types.ts` | 334 | `candidate_type: z.enum([…, "new_extension_component"])` | ✅（`types.ts × new_extension_component`，與 #2 合併成 1 筆） | `scanTemplate.mock.ts:201`（`PROPOSALS: Record<string, MappingProposal>` 顯式標註 → 立即 TS error）。`CandidateCard.tsx` 不讀 `candidate_type`，不受影響 | 低 |
| 2 | `frontend/src/types.ts` | 371 | `mapping_type: z.enum([…, "new_extension_component"])` | ✅（同上一筆，census 看不出是 2 行） | `EditForm.tsx:38` 三元運算子的 `"new_extension_component"` 分支立即 TS error | 低 |
| 3 | `frontend/src/components/proposal/EditForm.tsx` | 38 | `form.target_slot === "ui_extension" ? "new_extension_component" : …` | ✅ | 與 #5 `SLOT_OPTIONS` 綁死：刪掉 `ui_extension` 選項後這個三元的 true 分支永遠不可達；刪掉 union member 後 true 分支型別錯誤。**兩處必須同一個 commit 改** | 低 |
| 4 | `frontend/src/data/scanTemplate.mock.ts` | 201 | `candidate_type: "new_extension_component"`（candidate:3 fallback） | ✅ | 同一個 candidate 物件的 :204 `target_slot: "ui_extension"`、:205 `component_name: "UserProfile (new UI extension)"`、:209 rationale 文案 都要一起換 | 低 |
| 5 | `frontend/src/data/scanTemplate.mock.ts` | 237 | `{ value: "ui_extension", label: "UI · New extension" }` | ❌ **census 看不到** | `EditForm.tsx:58-62` 的 `<select>` 直接 map `SLOT_OPTIONS`。刪這行 = #3 的分支變成 dead code | 低 |
| 6 | `frontend/src/data/frontend-json-sample.json` | 21, 32, 842, 1634 | `"ai-system-map/v1"` ×4 | ✅（**4 行壓成 1 筆**） | 整份 sample 是 v1 payload，見 #8 | 高 |
| 7 | `frontend/src/data/frontend-json-sample.json` | 1595 | `"proposal_type": "new_extension_component"` | ✅ | `DetailPanel.tsx:68` 讀 `mapping_proposal_result_sample` 並渲染 `suggested_component.name` / `status` / `user_actions`；`suggested_component.id` 與 `suggested_edges` 也都是 `extension:reranker:…` | 中 |
| 8 | `frontend/src/data/frontend-json-sample.json` | 全檔 1641 行 | `ai_system_map` 有 **10 個 v2 沒有的 key**（`classification`、`reference_architecture`、`scan_depth`、`scan_summary`、`components_by_slot`、`flows`、`extensions`、`detail_scans`、`recommended_next_checks`、`query_trace_events`），且**缺** v2 的 `components`/`edges`/`candidate_facts`/`scan_id`/`build_id`/`environment_id`/`artifact_set_version` | ❌ 只有 `schema_version` 那 1 筆被看到 | `sampleMap.ts:4` `viewerPayloadSchema.parse()` → `App.tsx`、`Sidebar`、`ReplayTimeline`、`SystemGraph`、`DetailPanel` 全鏈 | 高 |
| 9 | `frontend/src/data/sampleMap.ts` | 22 | `payload.viewer_load_result.ai_system_map.query_trace_events` | ❌ | v2 schema 無此欄位（`additionalProperties: false`）。`App.tsx:71` 對 **API payload 也呼叫** `getTraceEvents` → API mode replay 永遠空陣列 | 高 |
| 10 | `frontend/src/App.tsx` | 70, 307 | `aiSystemMap?.scan_summary` / `aiSystemMap?.scan_depth` | ❌ | `Sidebar.tsx:37-42,67-73` 全部退化成 `"unknown"`，深度階梯 `reached = -1` | 中 |
| 11 | `frontend/src/utils/graph.ts` | 197 | `const isUnmapped = edge.status === "needs_confirmation"` | ❌ | backend `GraphEdgeModel`（`core/models/viewer.py:114-126`）**根本沒有 `status` 欄位** → API mode 恆 false；`--unmapped` 邊色與 `data.isUnmapped` 死亡 | 中 |
| 12 | `frontend/src/types.ts` | 100-106 | viewer payload 宣告 `scan_depth` / `scan_summary` / `query_trace_events` | ❌ | 這是 #9/#10 的型別來源；不清掉，TS 不會提醒任何人這些欄位已經不存在 | 中 |
| 13 | `frontend/src/types.ts` | 75-90 | `graphViewModelSchema` 缺 11 個 backend 欄位 + `details` 缺 3 個 map + `filters` 缺 `lenses` | ❌ | zod `z.object` 靜默 strip；Plan 06 / profile overlay 資料到不了 UI | 中 |
| 14 | `frontend/src/components/SystemNode.tsx` | 27-34 | `statusKey()` 未知 status → fallback `"detected"` | ❌ | v2 component status enum 含 `partial` / `undetermined`；兩者會被畫成 detected | 中 |
| 15 | `frontend/API_CONTRACT.md` | 34-38, 310-316 | 文件把 `scan_depth` / `query_trace_events` 寫成 viewer payload 契約 | ❌（census 只掃 `frontend/src`） | 是 #9/#10/#12 的「正當性來源」，不改的話下一個人會照著寫回去 | 低 |

---

## 逐條發現

### RC-1. `ui_extension` slot 與 `new_extension_component` 是同一個死結，但只有一半在 census 裡【A類】

- **位置**：`frontend/src/data/scanTemplate.mock.ts:237`、`frontend/src/data/scanTemplate.mock.ts:204`、`frontend/src/components/proposal/EditForm.tsx:38`
- **現況**

```ts
// scanTemplate.mock.ts:228-238  (SLOT_OPTIONS)
{ value: "ui_account_view",  label: "UI · Account View" },
{ value: "ui_settings_panel", label: "UI · Settings Panel" },
{ value: "ui_extension",      label: "UI · New extension" },   // ← census 看不到

// EditForm.tsx:38
mapping_type: form.target_slot === "ui_extension" ? "new_extension_component" : "existing_slot_mapping",
```

- **判定理由**：allowlist 的 `LEGACY_LITERALS` 只有 `new_extension_component`，正則帶 word boundary，所以 `ui_extension` 完全不在 census 內。但它才是**觸發條件**：`EditForm.tsx:58-62` 的 `<select>` 直接 `SLOT_OPTIONS.map(...)`，使用者選了「UI · New extension」才會走進 :38 的 true 分支。若只按 07-28 文件「刪 `ui_extension` → 舊 type 分支」把 :38 改成常數 `"existing_slot_mapping"`，census 會歸零，但下拉選單仍留著一個對應不到任何 backend slot 的 `ui_extension`——使用者送出後 backend 會用「slot 不存在」而不是 `legacy_mapping_type_read_only` 拒絕，錯誤訊息更難懂。
- **建議處置**：同一個 commit 內：(a) `scanTemplate.mock.ts` 刪 L237 整行；(b) `EditForm.tsx:38` 改成 `mapping_type: "existing_slot_mapping"`（`ManualMappingCreate` 的 union 只剩兩值，`non_baseline_capability_candidate` 目前不在 frontend union 內，見 RC-9）；(c) 順手把 :204/:205/:209 的 candidate:3 改成 `non_baseline_capability_candidate` 示範，或整個刪掉。**接線前改**：現在改零風險（沒有網路呼叫）。若等接線後才改，`decide()` 換成真 mutation 的那一刻，凡是選到 `ui_extension` 的使用者都會吃 422。
- **風險**：低

### RC-2. `frontend-json-sample.json` 的 5 筆 raw hit 只佔實際 v1 殘留的極小部分【A類】

- **位置**：`frontend/src/data/frontend-json-sample.json`（全檔 1641 行）
- **現況**（`ai_system_map` 的 key 與 v2 schema 對照）

```
ai_system_map keys NOT in ai-system-map.v2.schema.json:
  classification / reference_architecture / scan_depth / scan_summary /
  components_by_slot / flows / extensions / detail_scans /
  recommended_next_checks / query_trace_events
v2 core keys MISSING from sample:
  components / edges / candidate_facts / scan_id / build_id /
  environment_id / artifact_set_version
```

`graph_view_model` 同樣是 v1 投影：`schema_version: "graph-view-model/v1"`、`source_schema_version: "ai-system-map/v1"`、node types `{component:10, slot:2, extension:1, unmapped:1}`、edge 有 `status: "needs_confirmation"`、`summary` 帶 `scan_depth`/`status`/`detected_slots`/`risk_hints`/`unmapped_components`（現行 backend `summary` 只有 `project_name`/`schema_version`/`node_count`/`edge_count`）。相對 backend `GraphViewModel`，sample 缺 11 個欄位：`project_id`、`scan_id`、`build_id`、`environment_id`、`artifact_set_version`、`generated_from_build_id`、`reference_map_version`、`mapping_completeness`、`relationships`、`endpoints`、`recommended_next_checks`。

- **判定理由**：07-15 表格寫「把 canonical map sample 改成 `ai-system-map/v2`，移除 top-level `extensions` 與 legacy proposal sample」，07-28 寫「sample 對齊 v2；無舊 proposal type」。兩份都把它描述成**欄位級的小修**。實際上 v2 schema 是 `additionalProperties: false` 且 `components[]`/`edges[]` 取代整個 `components_by_slot` + `flows` + `extensions` 三層結構 —— 這是**整份 payload 重生**，不是改 4 個字串。而 census 只會因為 `schema_version` 那一個字串就宣告這個檔案「清乾淨了」。
- **建議處置**：不要手改。以 `docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-04-normalize-validate/frontend-ai-system-map-sample.json`（已確認 `schema_version: "ai-system-map/v2"`，key 集合完全對得上）為 `ai_system_map` 來源，`graph_view_model` 則跑一次真 backend（`uv run python scripts/dev.py` + `POST /api/viewer/load`）把回應原樣落檔。**必須與 RC-3/RC-4/RC-5 同批**，否則 Sample mode 會靜默退化（見那三條）。
- **風險**：高

### RC-3. `sampleMap.ts:22` 讀 v1-only 的 `query_trace_events`，且這條路徑 API mode 也走【A類】

- **位置**：`frontend/src/data/sampleMap.ts:22`、`frontend/src/App.tsx:71`
- **現況**

```ts
// sampleMap.ts:21-23
export function getTraceEvents(payload: ViewerPayload): TraceEvent[] {
  return parseTraceEvents(payload.viewer_load_result.ai_system_map.query_trace_events);
}

// App.tsx:71 —— 注意 payload 在 API mode 是 data，不是 sample
const traceEvents = useMemo(() => (dataAvailable && payload ? getTraceEvents(payload) : []), [dataAvailable, payload]);
```

- **判定理由**：`ViewerSessionService.build_loaded()` 把 `ai_system_map` 設成 `loaded.source_map.model_dump(mode="json")`（`viewer_session_service.py:129`）；native v2 build 的 `source_map` 就是 `AiSystemMapV2`（`canonical_map_loader.py:167`）。v2 schema 沒有 `query_trace_events`，`additionalProperties: false`。所以 **API mode 的 ReplayTimeline 現在已經是空的**，而且沒有替代來源——`frontend/src/services/` 只有 `http.ts`/`projectScanApi.ts`/`scanTemplateApi.ts`/`viewerApi.ts`，沒有 trace API client。這個檔案不在 07-15 的 4 檔清單、也不在 07-28 的表格。
- **建議處置**：短期把 `getTraceEvents` 標成 sample-only（只吃 `sampleViewerPayload`），`App.tsx:71` 在 API mode 直接給 `[]` 並讓 `ReplayTimeline` 顯示「trace replay 需要 `/api/trace`，尚未接線」；長期接 `query_trace_service` 的 endpoint。**接線前改**：現在就該改，因為現況是「UI 看起來支援但實際永遠空白」，比明講未實作更糟。
- **風險**：高（使用者看到空白 replay 會以為掃描失敗）

### RC-4. `App.tsx` 讀 v1-only 的 `scan_summary` / `scan_depth`，Sidebar 全欄退化成 "unknown"【A類】

- **位置**：`frontend/src/App.tsx:70`、`frontend/src/App.tsx:307`、`frontend/src/components/Sidebar.tsx:37-42,67-73`
- **現況**

```tsx
// App.tsx:69-70
const aiSystemMap = dataAvailable ? payload?.viewer_load_result.ai_system_map : undefined;
const scanSummary = aiSystemMap?.scan_summary;      // v2 沒這個 key
...
// App.tsx:307
scanDepth={aiSystemMap?.scan_depth}                  // v2 沒這個 key
```

```tsx
// Sidebar.tsx:37,41-42
const cell = (value) => (dataAvailable && value != null ? String(value) : "unknown");
const reached = dataAvailable && scanDepth ? DEPTH_ORDER.indexOf(scanDepth) : -1;
const scanStatus = dataAvailable ? (scanSummary?.status ?? "unknown") : "unknown";
```

- **判定理由**：同 RC-3 的機制。v2 map 沒有 `scan_summary`/`scan_depth`，所以 API mode 下 Sidebar 的 detected / missing / risk hints / unmapped 四格全是 `"unknown"`、狀態顯示 `"unknown"`、L1/L2/L3 深度階梯沒有任何一階被點亮。而且 `dataAvailable` 是 true，所以底下那句「No map loaded. Summary unavailable…」的提示**不會**出現——使用者看到的是一個「載入成功但什麼都不知道」的側欄。這兩個檔案完全不在任一份 handoff 文件裡。
- **建議處置**：資料改由 `graph_view_model.summary` + backend 現行欄位取得。Backend `summary` 目前只有 `project_name`/`schema_version`/`node_count`/`edge_count`，`mapping_completeness` 才是承載完成度的欄位（`GraphViewModel.mapping_completeness`，frontend zod 未宣告，見 RC-8）。所以正解是：先在 `graphViewModelSchema` 補 `mapping_completeness`，Sidebar 改吃它；`scanDepth` 若 v2 不再提供就把整個深度階梯降級成靜態說明。**接線前改**：與 RC-2 同批，否則換成 v2 sample 後 Sample mode 也一起退化成 unknown。
- **風險**：中

### RC-5. `utils/graph.ts:197` 依賴一個 backend 模型上根本不存在的欄位【A類】

- **位置**：`frontend/src/utils/graph.ts:197`
- **現況**

```ts
const isUnmapped = edge.status === "needs_confirmation";
const strokeColor = focused ? "var(--accent)" : isRisk ? "var(--risk)" : isUnmapped ? "var(--unmapped)" : "var(--line-strong)";
```

- **判定理由**：`src/systograph/core/models/viewer.py:114-126` 的 `GraphEdgeModel` 欄位是 `id / source_id / flow_id / from_id / to / relationship / label / evidence_ids / risk_hint_ids` —— **沒有 `status`**。`graph_projection_service.py:252-265` 建構 `GraphEdgeModel(...)` 時也沒傳 `status`。v2 `CanonicalEdge.status` 的 enum 是 `observed / detected / undetermined`，即使未來投影下來也不會是 `needs_confirmation`。所以這個判斷在 API mode 恆 false，只有 v1 sample JSON（edge 帶 `status: "needs_confirmation"`）能讓它成立。這是**「只有 sample 能證明功能存在」的假活路徑**，是 v1 sample 沒被換掉造成的最隱蔽副作用。
- **建議處置**：兩選一。(a) 若「未確認邊」概念要保留，跟 backend 談把 `CanonicalEdge.status` 投影進 `GraphEdgeModel`，frontend 改判 `edge.status === "undetermined"`；(b) 若不保留，刪掉 `isUnmapped` 與 `--unmapped` 邊色分支，連同 `FlowEdgeData.isUnmapped`。**接線後改沒有意義**——這條路徑跟 proposal 接線無關，現在就已經死了。
- **風險**：中

### RC-6. `types.ts` 的 viewer payload 宣告仍是 v1 契約【B類】

- **位置**：`frontend/src/types.ts:98-107`
- **現況**

```ts
ai_system_map: z.record(z.unknown()).and(
  z.object({
    schema_version: z.string().optional(),
    system_type: z.string().optional(),
    scan_depth: z.string().optional(),          // v1-only
    scan_summary: scanSummarySchema.optional(), // v1-only
    query_trace_events: z.array(...).optional(),// v1-only
    unmapped_components: z.array(...).optional(),
  }),
)
```

- **判定理由**：三個 v1-only 欄位全部 `.optional()`，所以 v2 payload 照樣 parse 成功、TypeScript 照樣給出 `string | undefined`。這是 RC-3/RC-4「靜默退化而非爆炸」的**直接成因**：型別系統本來該在這裡擋下來，卻因為當初照 v1 sample 寫成 optional 而失效。07-15 只把 `types.ts` 列為「移除 legacy type；對齊目前 proposal 與 manual mapping union」，完全沒提 viewer payload 這一段。
- **建議處置**：把 `scan_depth` / `scan_summary` / `query_trace_events` 從 `ai_system_map` 移出。若要保留 v1 相容讀取，也應該放進一個明確命名的 `legacyV1MapFieldsSchema` 並在使用端顯式 narrow，而不是混在主 schema 裡。`scanSummarySchema`（:59-73）與 `ScanSummary` type 若無其他消費者則一併移除（目前只有 `Sidebar` props 用）。
- **風險**：中

### RC-7. `graphViewModelSchema` 落後 backend `GraphViewModel` 11 個欄位【B類】

- **位置**：`frontend/src/types.ts:75-90`
- **現況**：frontend 宣告 `schema_version / source_schema_version / map_json / summary / nodes / edges / details{evidence_by_id, risk_hints_by_id} / filters{available, behavior}`。backend `GraphViewModel`（`core/models/viewer.py:233-254`）另有 `project_id`、`scan_id`、`build_id`、`environment_id`、`artifact_set_version`、`generated_from_build_id`、`reference_map_version`、`mapping_completeness`、`relationships`、`endpoints`、`recommended_next_checks`；`details` 另有 `reference_assessments_by_id`、`profile_findings_by_id`、`capability_candidates_by_id`；`filters` 另有 `lenses`。
- **判定理由**：zod `z.object` 預設 strip unknown keys，所以 parse 通過但資料被**靜默丟棄**。CLAUDE.md 的 key invariant「Identity = `scan_id` + `build_id`」在 frontend 是拿不到的；`MODEL-CONTRACT.md` §9.3 明寫 lenses 是 6 個固定 id、frontend 只做 highlight/dim，但 frontend 連 `lenses` 欄位都沒宣告。這不是 Plan 13 造成的，但**被 v1 sample 遮蔽**——sample 也沒有這些欄位，所以沒人發現。換成真 v2 payload 後才會浮現。
- **建議處置**：補齊 schema（至少 `scan_id`/`build_id`/`mapping_completeness`/`filters.lenses`），或改用 `.passthrough()` 並在 `MODEL-CONTRACT.md` §9 補一條「frontend schema 必須與 `GraphViewModel` 同步」的 checklist。與 RC-2 同批處理最省事。
- **風險**：中

### RC-8. `mapping_proposal_result_sample` 整塊是 legacy extension proposal【B類】

- **位置**：`frontend/src/data/frontend-json-sample.json:1593-1620`，消費端 `frontend/src/components/DetailPanel.tsx:68,88,100-110`
- **現況**

```json
"proposal_id": "proposal:reranker-extension",
"proposal_type": "new_extension_component",
"suggested_component": { "id": "extension:reranker:health-reranker", ... },
"suggested_edges": [
  { "from": "component:retriever:qdrant-retriever", "to": "extension:reranker:health-reranker", ... },
  { "from": "extension:reranker:health-reranker", "to": "component:prompt_builder:context-prompt-template", ... }
]
```

- **判定理由**：census 只抓到 `proposal_type` 那一行（:1595）。但 `suggested_component.id` 與兩條 `suggested_edges` 都用 `extension:` 前綴，而 `DetailPanel.tsx` 把 `suggested_component.name` 與 `user_actions` 直接渲染成按鈕。也就是說 L2/L3 detail 面板現在還在**示範一條 backend 已 fail-closed 的流程**——這正是 07-15 文件自己說的「畫面仍會教使用者走已停用的流程」，只是文件沒意識到它在 sample 的這個角落。
- **建議處置**：以 `docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-09-review-apply/frontend-mapping-proposal-sample.json` 取代；`suggested_component.id` 改用 `candidate:` 或 v2 component id 命名。與 RC-2 同批。
- **風險**：中

### RC-9. frontend union 缺 `non_baseline_capability_candidate`，刪掉 legacy 值後只剩一個選項【B類】

- **位置**：`frontend/src/types.ts:334`、`frontend/src/types.ts:371`
- **現況**：兩個 union 都是 `z.enum(["existing_slot_mapping", "new_extension_component"])`。
- **判定理由**：07-15 文件 L23 明寫「只能送 `existing_slot_mapping` 或 `non_baseline_capability_candidate`」，L40-43 還列出 `needs_more_information` / `skip_for_now`。但 frontend 的 union **從來沒有** `non_baseline_capability_candidate`。所以「移除 `new_extension_component`」不是刪除操作，是**替換**操作——只刪不加的話 `mappingCandidateSchema` 會退化成單值 enum，backend 送 `non_baseline_capability_candidate` 時 zod parse 直接失敗，整個 proposal 面板炸掉。07-15/07-28 的表格用「移除 / 刪」描述這件事，會誤導人做成刪除。
- **建議處置**：`z.enum(["existing_slot_mapping", "non_baseline_capability_candidate"])`。同時檢查 `mappingProposalSchema.status`（:357）與 `available_actions`（:363）是否涵蓋 `needs_more_information`——目前 `available_actions` 是 `z.array(z.string())`，不會擋，但 UI 沒有對應分支。
- **風險**：中（照字面「移除」做會造成 runtime parse error）

### RC-10. `SystemNode.statusKey()` 把未知 status 一律當成 `detected`【B類】

- **位置**：`frontend/src/components/SystemNode.tsx:27-34`
- **現況**

```tsx
function statusKey(data): NodeStatusKey {
  if (hasNodeLevelRisk(data)) return "risk";
  if (data.status === "needs_confirmation") return "needs_confirmation";
  if (data.status === "not_applicable") return "not_applicable";
  if (data.status === "not_configured") return "not_configured";
  if (data.status === "missing") return "missing";
  if (data.status === "confirmed") return "confirmed";
  return "detected";                      // ← 未知一律綠燈
}
```

- **判定理由**：v2 `CanonicalComponent.status` enum 是 `detected / missing / not_configured / not_applicable / confirmed / partial / undetermined`。`partial` 與 `undetermined` 落進 fallback，被畫成 `detected`（無警示 icon、`s-detected` class）。CLAUDE.md 的 invariant「`detected` requires direct evidence；indirect-only evidence caps at `partial`」在 UI 上被抹平。`contradicted` 在 `frontend/src` **零命中**（已驗證），所以三態殘留這條是乾淨的；問題不是殘留舊值，而是**沒有接住新值**。
- **建議處置**：把 fallback 從 `"detected"` 改成一個明確的 `"undetermined"` 視覺態，並補 `partial`。這條嚴格說偏 Plan 06 範圍，但因為 v1 sample 裡完全沒有 `partial`/`undetermined` 節點（實測 node statuses = `detected:10, not_configured:1, missing:1, confirmed:1, needs_confirmation:1`），換 v2 sample 後才會第一次曝光，所以歸在同一批處理最合理。
- **風險**：中（顯示層誇大 detected，違反 evidence-based 原則）

### RC-11. `invalid_map_error_sample` 的錯誤文案寫死 v1【B類】

- **位置**：`frontend/src/data/frontend-json-sample.json:1630-1638`
- **現況**：`"message": "The map JSON failed ai-system-map/v1 validation."`、`"details": ["schema_version is missing", "components_by_slot.vector_store.status has invalid enum value"]`
- **判定理由**：`components_by_slot` 在 v2 不存在。這行的 `ai-system-map/v1` 有被 census 記到（併入 sample 的 `ai-system-map/v1` 那一筆），但 `components_by_slot` 沒有。目前 `invalid_map_error_sample` 在 `frontend/src` 只被 `types.ts:113` 宣告、無 component 消費，所以是**未接線的死資料**，但留著會誤導下一個實作錯誤畫面的人。
- **建議處置**：改成 v2 版本（`unsupported_system_map_schema_version` 是 Plan 13 定義的 stable code），或整段刪除。
- **風險**：低

### RC-12. `SLOT_OPTIONS` 整份是 legacy `rag-core-v1` slot 清單【B類】

- **位置**：`frontend/src/data/scanTemplate.mock.ts:228-238`
- **現況**：9 個 slot（`api_or_orchestrator` / `retriever` / `vector_store` / `prompt_builder` / `llm` / `reranker` / `ui_account_view` / `ui_settings_panel` / `ui_extension`）
- **判定理由**：CLAUDE.md 明寫「"Slot" refers only to the 13 slots of the legacy `rag-core-v1` template」、「`rag-core-v1` 是 legacy template only」。整個 EditForm 的 slot 選擇模型都建在這上面。07-15 只叫人刪 `ui_extension` 那一行，等於默認保留其餘 8 個 legacy slot。這超出 Plan 13 的最小 scope（Plan 13 只要求停寫 extension），但必須被明確記為 known debt，否則下一輪會有人以為 slot 模型已經對齊 v2。
- **建議處置**：Plan 13 handoff 內**不要動**，但在 07-15 文件補一行「slot 模型仍是 rag-core-v1，屬 Plan 06 / 52-node reference map 遷移範圍」。
- **風險**：低（本輪不動）

### RC-13. 07-28 文件 L27「Frontend 仍會送（活路徑）」與 code 不符【D類】

- **位置**：原 `frontend-stop-new-extension-component.md:27-32`（已併入
  `docs/work/Meeting-Sync/meeting_sync_2026_07_28/frontend-v2-cutover-handoff.md` 第 3 批）
- **現況**：文件寫「Frontend **仍會送**（活路徑）：`EditForm.tsx` `target_slot === "ui_extension"` → `mapping_type: "new_extension_component"`」
- **判定理由**：前次已查證，本輪再確認：`ProposalModal.tsx:197-204` 的 `decide()` 是 `setTimeout(…, 600)` stub，`accept` / `submitEdit` / `confirmReason` 全部只 `setResult` + `setPhase("result")`；`frontend/src/services/` 沒有任何 mapping API client（只有 `http.ts`、`projectScanApi.ts`、`scanTemplateApi.ts`、`viewerApi.ts`）；ProposalModal 的檔頭註解自己就寫「the swap point is small: replace the `runLoad` / `decide` setTimeout stubs with the real create / decide mutations」。所以 `EditForm.tsx:38` 產生的 `ManualMappingCreate` 物件**只會流進 `setResult`，永遠不會離開瀏覽器**。文件的「活路徑」判斷錯誤。
- **建議處置**：把 L27 改成「Frontend 型別與表單仍可組出舊 payload，但 proposal UI 尚未接線（`decide()` 為 stub），目前不會實際送出；接線前必須先清乾淨」。連帶影響 07-15 驗收清單最後一項「API mode 完成 Viewer、proposal accept / edit / reject / skip 的手動測試」—— proposal 部分**現在無法執行**，應標為 blocked-on-wiring。
- **風險**：低（文件層，但會誤導排優先序：這件事其實不緊急）

### RC-14. Plan 13 的收尾條件（5 筆歸零）是結構性弱 gate【D類】

- **位置**：`docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-v2-cutover/13-retire-legacy-extension-contract.md:546,564,575`
- **現況**：「待 frontend handoff 的5筆active hits歸零後，才把Status改為`complete`」
- **判定理由**：見開頭「先釐清 5 筆」。allowlist 是 file×symbol 去重，且 `LEGACY_LITERALS` 不含 `ui_extension`、`extensions`、`components_by_slot`、`query_trace_events`。實際可行的「作弊過關」路徑：把 `types.ts:334/371` 的 union member 刪掉、`EditForm.tsx:38` 改常數、`scanTemplate.mock.ts:201` 改字串、sample JSON 的 4 個 `ai-system-map/v1` + 1 個 `proposal_type` 改掉 —— census 立刻歸零，但 RC-1/RC-3/RC-4/RC-5/RC-8 全部原封不動，Sample mode 與 API mode 的 v1 依賴一個都沒解。
- **建議處置**：在 allowlist test 的 `LEGACY_LITERALS` 增列 `ui_extension`、`components_by_slot`、`query_trace_events`、`extensions`、`needs_confirmation`（後者可能誤傷 backend，可只對 `FRONTEND_ROOT` 生效），並把 `_text_legacy_hits` 改成記錄 `(path, symbol, line)` 讓行數也進 census。Plan 13 的 completion 條件則應改成「frontend census 歸零 **且** Sample/API 兩模式的 Viewer / Sidebar / Replay / DetailPanel 手動驗收通過」。
- **風險**：中（照現況收尾會把未解的 v1 依賴標記成 complete）

### RC-15. 07-15 的 4 檔清單漏了 4 個實際要動的檔【D類】

- **位置**：`docs/work/Meeting-Sync/meeting_sync_2026_07_15/frontend-ai-system-map-v2-cutover.md:28-35`
- **現況**：「目前共有 **4 個檔案、5 筆 legacy contract hit** 要處理」，列 `types.ts` / `EditForm.tsx` / `scanTemplate.mock.ts` / `frontend-json-sample.json`。
- **判定理由**：漏掉 `sampleMap.ts`（RC-3）、`App.tsx`（RC-4）、`Sidebar.tsx`（RC-4 連帶）、`utils/graph.ts`（RC-5）；`SystemNode.tsx`（RC-10）與 `frontend/API_CONTRACT.md`（RC-6 的文件來源）視範圍也應納入。這 4 個檔沒有任何 `new_extension_component` / `ai-system-map/v1` 字串，所以 census 看不到、文件也就沒列——但它們才是**真正會在 API mode 靜默壞掉**的地方（census 掃到的那 5 筆反而因為 proposal UI 未接線而不會造成 runtime 影響）。
- **建議處置**：把 07-15 表格擴成 8 檔並標註「census 可見 / 不可見」；把「驗收清單」第 2 條（sample 是 v2 且無 top-level extensions）拆成 sample 替換 + 消費端修正兩步。
- **風險**：中

### RC-16. 已被正確追蹤的部分【C類】

`types.ts:334`、`types.ts:371`、`EditForm.tsx:38`（mapping_type 字面值）、`scanTemplate.mock.ts:201`、`frontend-json-sample.json:21/1595` —— 這 5 筆 census 命中在 07-15 與 07-28 都有明確對應條目與處置方向，敘述與 code 一致，照文件做即可（唯一要注意的是 RC-9 的「替換而非刪除」）。另外 `contradicted` 在 `frontend/src` **零命中**，三態 status 殘留這一項已經是乾淨的，兩份文件都沒誤報。

---

## 結論

**Plan 13 宣稱：4 個檔案、5 筆 hit。實查：8 個 code 檔 + 1 個契約文件，約 18 處編輯點 + 1 次 1641 行 sample 全檔重生。**

差距的來源不是有人漏看，而是**「5 筆」這個數字本身量的是 `(檔案 × 符號)` 去重值**：`frontend-json-sample.json` 的 5 行 raw hit 壓成 2 筆、`types.ts` 的 2 行壓成 1 筆。9 行 raw → 5 筆 census。再加上 census 的 `LEGACY_LITERALS` 只有 5 個字串，`ui_extension`、`extensions[]`、`components_by_slot`、`query_trace_events`、`scan_summary`、`needs_confirmation` 全都在雷達外。

按實際風險排序，真正的工作量分成三層：

**第 1 層 — census 看得到、但風險最低（proposal UI 未接線，改了不影響任何 runtime 行為）**
`types.ts:334,371` → `scanTemplate.mock.ts:201,204,205,209,237` → `EditForm.tsx:38`。3 檔、8 處。注意是**替換**成 `non_baseline_capability_candidate`（RC-9），不是單純刪除。`ui_extension` 與 `new_extension_component` 必須同 commit（RC-1）。

**第 2 層 — census 看不到、但 API mode 已經壞了**
`sampleMap.ts:22`（replay 永遠空）、`App.tsx:70,307` + `Sidebar.tsx`（摘要全 unknown）、`utils/graph.ts:197`（依賴 backend 不存在的 `edge.status`）、`types.ts:100-106`（讓上述三者靜默通過型別檢查）。4 檔、5 處。**這一層才是使用者現在就看得到的損壞**，優先序應該高於第 1 層。

**第 3 層 — sample 全檔重生 + 消費端連帶**
`frontend-json-sample.json` 整份（10 個 v1-only key、v1 graph_view_model、legacy proposal sample）、`types.ts:75-90` 的 gvm schema 補 11 欄、`SystemNode.tsx:27-34` 接住 `partial`/`undetermined`。必須與第 2 層綁在一起做，否則換 v2 sample 的當下 Sample mode 會跟 API mode 一起退化成 unknown/空白。

**對 Plan 13 收尾的建議**：不要用「census 5 筆歸零」當 completion gate（RC-14）。第 1 層做完 census 就會歸零，但第 2、3 層一處未動。建議把 completion 條件改成「census 歸零 + `LEGACY_LITERALS` 補 `ui_extension`/`components_by_slot`/`query_trace_events`/`extensions` + Sample 與 API 兩模式的 Viewer/Sidebar/Replay/DetailPanel 手動驗收」。

另外：07-28 文件的「Frontend 仍會送（活路徑）」是錯的（RC-13），proposal UI 全是 setTimeout stub、`frontend/src/services/` 沒有 mapping client。這意味著**第 1 層其實不緊急**——目前沒有任何使用者能真的送出 `new_extension_component`。真正緊急的是第 2 層。兩份 handoff 文件把優先序排反了。
