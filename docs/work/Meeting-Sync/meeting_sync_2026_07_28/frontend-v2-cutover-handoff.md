# 前端 Handoff — v2 Cutover 收尾 + zod 契約修復（2026-07-28）

Status: **frontend action required**；三批修改都在 `frontend/` 內、backend 零改動
（唯一的 backend 項目是 1-1 末尾「之後要開始做」的動態掃描串流，**不屬於本次三批**）

Last updated: 2026-07-29（合併原 `frontend-stop-new-extension-component.md`；以本檔為唯一最新版）

> 2026-07-29 修訂：1-1 的嚴重度描述經追查後端程式碼後修正——**逐節點 highlight 今天不會動
> 的原因是動態掃描串流還沒做**，不是 zod 契約錯誤造成的。1-1 改列為「接線前排雷」，
> 並補上 backend 之後要開始做的動態掃描串流工作。1-2 仍是現在就壞的活 bug。

**來源**（backend 計畫已把前端職責抽離到本文件）：

- Plan 13.5（`docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-v2-cutover/13.5.md`）
  ＋殘留稽核 `docs/work/Timmy/schedule/report/2026-07-28-plan13-residue/residue-C-frontend.md`（RC-1..RC-16）
- Plan 13.6（`.../s1-v2-cutover/13.6.md`）抽離的 zod 契約修復（原 phase2.5 Plan 2 Task 9）
- 前次：`../meeting_sync_2026_07_15/frontend-ai-system-map-v2-cutover.md`（4 檔清單已知漏檔，以本文為準）
- 前次：`../meeting_sync_2026_07_07/frontend-legacy-extension-retirement.md`

---

## 先看結論

| 批次 | 改什麼 | 為什麼 | 緊急度 |
| --- | --- | --- | --- |
| **第 1 批**：zod 契約修 bug | `types.ts` 3 處 + 2 個新測試檔 | **1-2 是 main 上的活 bug**：boundary 掃描回應直接讓前端 throw。**1-1 是接線前的地雷**：SSE 契約寫錯（`.optional()` 收不到後端送的 `null`），今天只影響狀態文字，但動態掃描接上後會讓每則事件全滅 | 高（1-2 現在就壞；1-1 成本極低，趁早排雷） |
| **第 2 批**：API mode 修復 | 4 檔 5 處 | **API mode 現在就壞三處**：Replay 恆空、Sidebar 全 "unknown"、unmapped 邊色永遠不亮 | **高（現在就壞）** |
| **第 3 批**：sample 重生 + legacy 清理 | sample 全檔重生 + 3 檔 8 處（含停用 `new_extension_component`） | Plan 13 收尾（census 歸零）；proposal UI 未接線所以**不會真的送出**，不急但接線前必須完成 | 中 |

**驗收一句話：** `cd frontend && pnpm lint && pnpm test && pnpm build` 三關全綠，
加上 Sample / API 兩模式手動看 Viewer、Sidebar、Replay、DetailPanel。

三批可以分三個 PR。第 1 批最小、風險最低（且 1-1 是後續動態掃描的前置條件），建議先出；
**使用者可見的修復最多的其實是第 2 批**。

---

## 責任切分（legacy mapping / guard）

| 誰 | 該做什麼 | 不該做什麼 |
| --- | --- | --- |
| **Frontend** | 立刻停止組裝／示範 `new_extension_component`；清掉 type / form / mock / sample | 繼續把 `ui_extension` map 成舊 type；以為「程式還在 = 還要走這條 happy path」 |
| **Backend** | 維持 fail-closed 直到 frontend hit = 0 | 把 `legacy_mapping_guards.py` 當長期產品功能維護或擴充 |
| **雙方** | 文件寫「不要用了」 | 把防護閘門誤當成新功能入口 |

```text
「退場」= 產品 happy path 禁止再建立
         ≠ 宇宙裡再也送不出這個字串

Frontend 未清乾淨 → 未來接線時會撞 422（目前 proposal UI 是 stub，payload 離不開瀏覽器）
Backend guard 還在  → 只是擋寫入 + 穩定錯誤碼 legacy_mapping_type_read_only
                      ≠ backend 要「留這個程式當功能」
```

可選（非優先）：日後可把 `legacy_mapping_guards.py` rename 成
`retired_mapping_type_guard.py`；**HTTP `detail` 字串先不要改**（契約）。
前端清零、Plan 15 收完後再討論刪 guard。

收到 `legacy_mapping_type_read_only`：提示重新整理／重抓 proposal，**不要重試同一份舊 payload**。

---

## 第 1 批 — zod 契約修 bug（半天內可完成）

### 1-1. SSE 進度事件：六個欄位 `.optional()` → `.nullish()`

> ⚠️ **提醒：這是「接線前的地雷」，不是今天壞掉的 highlight 功能。**
> 逐節點掃描進度**後端還沒做**（見下方〈現況核對〉），所以修完**不會**看到節點逐一亮起。
> 現在就修的理由是成本極低（改 6 個字），而且動態掃描一接上，這個契約錯誤會讓**每一則**
> 事件被丟掉——屆時症狀看起來會像「新寫的動態掃描壞了」，很難查。

**契約錯誤：** 後端 SSE 實測送的是 `"node_id": null`（欄位在、值為 `null`），不是省略欄位。
zod 3 的 `.optional()` 只接受 `undefined`、不接受 `null`
（[官方文件](https://v3.zod.dev/?id=optionals)：`.optional()` = `T | undefined`、
`.nullish()` = `T | null | undefined`）→ 事件被 `viewerApi.ts:35-47` 的 catch
判成 `invalid_event`。

**改法：** `frontend/src/types.ts:123-129`，六個欄位改 `.nullish()`
（= `.nullable().optional()`，同檔 `traceEventSchema:239-242` 已在用這寫法）：

```ts
    node_id: z.string().nullish(),
    edge_id: z.string().nullish(),
    component_id: z.string().nullish(),
    source_id: z.string().nullish(),
    slot: z.string().nullish(),
    evidence_id: z.string().nullish(),
```

`percent`（`:122`）**不要動**——後端 `ge=0, le=100` 與前端現況一致。

**現況核對（2026-07-29 追查後端程式碼後補記，修正本節原先的嚴重度描述）：**

- 後端 `ScanProgressEvent`（`src/kai_mind/web/schemas.py:328-345`）六個 ID 欄位
  預設全是 `None` → 序列化成 JSON 時 key 保留、值為 `null`。
- 全 repo **只有一個建構點**：`src/kai_mind/web/routes/scan_routes.py:360`
  的 `ScanProgressEvent()`——零參數、只 `yield` 一次，docstring 自承
  「現階段回傳一筆 completed 狀態」。**沒有任何程式碼路徑會填入真正的 `node_id`。**
- 因此 `App.tsx:114` 的 `resolveProgressTargetId()` 今天不論修不修都回傳 null，
  highlight 本來就不會動——原因是動態掃描沒做，不是 zod 寫錯。

**今天修好的實際差別**（只有三個顯示欄位；`invalid_event` 假物件缺欄位，其餘走 `??` fallback）：

| 位置 | 現在 | 修好後 |
| --- | --- | --- |
| `App.tsx:124` 訊息 | 「Received an unrecognized scan progress event.」 | 「Scan completed.」 |
| `App.tsx:120` percent | fallback 到本地計算值 | 100 |
| `App.tsx:127` stage | fallback 到 `"sse stream"` | `"validate"` |

**之後要開始做（backend，尚未排程 → 待開 issue）：**
把 `/api/scan/events` 從目前的 placeholder 換成真正的逐階段／逐節點進度串流，
在掃描過程中填入 `node_id` / `edge_id` / `component_id` / `source_id` / `slot`，
`API_CONTRACT.md:320-327` 記載的 highlight 解析順序才會真的生效。
**前置條件：本節的 `.nullish()` 必須先修好**，否則新串流會被既有契約錯誤整包吃掉。

**為什麼一直沒被發現：** `useScanProgress.test.ts:8` 把 `parseScanProgressEvent`
整個 `vi.fn()` mock 掉，真實 parser 從沒被測過。→ 保留既有 hook 測試，另加一條
**不 mock** 的整合測試（餵附錄 A 的真實後端 JSON，斷言收到 `scan_progress` 而非
`invalid_event`；若 `vi.mock` 是 module 級關不掉，就開新測試檔）。

### 1-2. `/api/scans` pending 回應：改 discriminated union

**問題：** 掃描需要 boundary 決策時，後端回應**沒有 `scan_id`**（這是契約，
`frontend/API_CONTRACT.md:256`：「When `requires_boundary_decision` is returned,
`scan_id` is absent.」）。但 `types.ts:211` 的 `scan_id: z.string()` 是必填，且
`projectScanApi.ts:36` 用 `.parse()`（不是 `safeParse`）→ **直接 throw**。
掃大一點的 repo 幾乎必觸發 boundary gate，所以這不是邊角案例。

**改法：** `frontend/src/types.ts:210-217` 改成：

```ts
const scanPendingResponseSchema = z.object({
  status: z.literal("requires_boundary_decision"),
  project_id: z.string(),
  preflight_request_id: z.string().nullish(),
  boundary_proposals: z.array(scanBoundaryProposalSchema).default([]),
  available_boundary_actions: z
    .array(scanBoundaryActionSchema)
    .default(["scan_this_run", "skip_this_run"]),
});

const scanSettledResponseSchema = z.object({
  status: z.enum(["completed", "error"]),
  scan_id: z.string(),
  project_id: z.string(),
  build_result: z.record(z.unknown()).nullable().optional(),
  inventory_selection_summary: z.record(z.unknown()).nullable().optional(),
});

export const scanCreateResponseSchema = z.discriminatedUnion("status", [
  scanPendingResponseSchema,
  scanSettledResponseSchema,
]);
```

然後 `pnpm build`——`tsc` 會在每個直接讀 `result.scan_id` 的地方報錯，逐個加 narrow：

```ts
if (result.status === "requires_boundary_decision") {
  // 不要刷新 graph、不要當成掃描完成（API_CONTRACT.md:256）
  return result;
}
// 這之後 TypeScript 知道 result.scan_id 存在
```

**把每一個 build error 修掉，禁止用 `as` 繞過。**

### 1-3. 順手補 `selection_scope`

`types.ts:194-199` 的 `scanBoundaryDecisionSchema` 缺一個後端有、文件也記載
（`API_CONTRACT.md:176`）的欄位：

```ts
  selection_scope: z
    .enum(["exact_file", "recursive_directory"])
    .optional(),
```

### 1-4. 新增測試（全文見附錄 A，照抄即可）

- Create: `frontend/src/services/viewerApi.test.ts`
- Create: `frontend/src/services/projectScanApi.test.ts`

後端側會另加 wire-format 鎖定測試（13.6 Task W1）保證這兩個 JSON 形狀不再無聲
變動；**後端 JSON 本身完全不動**，前端不用等後端。

---

## 第 2 批 — API mode 已壞三處（v2 map 沒有這些欄位）

**背景一句話：** 正式輸出已是 `ai-system-map/v2`（`additionalProperties: false`），
map 本體**沒有** `query_trace_events` / `scan_summary` / `scan_depth`，graph edge
也**沒有** `status` 欄位。前端讀不到不會爆錯（zod 都是 optional），只會**靜默**
變成空白 / "unknown"——使用者看到的是「載入成功但什麼都沒有」。

### 2-1. Replay 恆空（RC-3）

- 位置：`frontend/src/data/sampleMap.ts:22`（`getTraceEvents` 讀
  `ai_system_map.query_trace_events`）+ `App.tsx:71`（API mode 的 payload 也走它）。
- 改法：把 `getTraceEvents` 標成 **sample-only**（只吃 `sampleViewerPayload`）；
  `App.tsx` 在 API mode 直接給 `[]`，`ReplayTimeline` 顯示「trace replay 需要
  `/api/trace`，尚未接線」而不是空白。長期方案（接 trace API）另行排程。

### 2-2. Sidebar 全 "unknown"（RC-4）

- 位置：`App.tsx:70, 307`（讀 `scan_summary` / `scan_depth`）→
  `Sidebar.tsx:37-42, 67-73` 全部退化成 `"unknown"`、深度階梯一階都不亮。
- 改法：資料改吃 `graph_view_model` ——`summary` 現有
  `project_name`/`schema_version`/`node_count`/`edge_count`，完成度要用
  `mapping_completeness`（要先做 3-2 把它補進 zod schema）。`scan_depth` v2
  不再提供 → 深度階梯降級成靜態說明文字。
- 注意：**必須與 3-1（sample 重生）同一批**，否則換 v2 sample 後 Sample mode
  也一起退化。

### 2-3. unmapped 邊色永遠不亮（RC-5）

- 位置：`frontend/src/utils/graph.ts:197`
  `edge.status === "needs_confirmation"`——backend `GraphEdgeModel` **根本沒有
  `status` 欄位**，API mode 恆 false；只有 v1 sample 能讓它成立（假活路徑）。
- 改法二選一：(a) 要保留「未確認邊」概念 → 跟 backend 談把 `CanonicalEdge.status`
  投影進 `GraphEdgeModel`，前端改判 `"undetermined"`；(b) 不保留 → 刪
  `isUnmapped` 分支與 `--unmapped` 邊色、連同 `FlowEdgeData.isUnmapped`。

### 2-4. 型別來源清理（RC-6）

- 位置：`frontend/src/types.ts:100-106`——viewer payload 宣告仍含
  `scan_depth` / `scan_summary` / `query_trace_events` 三個 v1-only 欄位
  （全 `.optional()`，這正是 2-1/2-2 靜默通過型別檢查的原因）。
- 改法：從 `ai_system_map` 宣告移除這三個欄位；`scanSummarySchema`（`:59-73`）
  若只剩 Sidebar props 在用就一併移除。清掉之後 TS 才會替你把 2-1/2-2 的
  殘餘讀取點全部揪出來。

---

## 第 3 批 — sample 重生 + legacy 字面清理（Plan 13 收尾）

### 3-1. `frontend-json-sample.json` 整檔重生（RC-2 / RC-8 / RC-11）

現況：1641 行整份是 v1 payload（10 個 v2 沒有的 key、缺 v2 的
`components`/`edges`/`scan_id`/`build_id` 等、graph_view_model 也是 v1 投影、
proposal sample 是 legacy extension）。**不要手改**：

- `ai_system_map` → 用
  `docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-04-normalize-validate/frontend-ai-system-map-sample.json`
  （已確認是 v2、key 集合對得上）。
- `graph_view_model` → 起真後端落檔：`uv run python scripts/dev.py` 跑一次掃描
  （fixture 建議 `tests/fixtures/rag_projects/pgvector_openai_rag`），
  `POST /api/viewer/load` 的回應原樣存進 sample。
- `mapping_proposal_result_sample` → 用
  `.../step-09-review-apply/frontend-mapping-proposal-sample.json` 取代
  （現在的 sample 在 DetailPanel 示範一條 backend 已 fail-closed 的 extension 流程）。
- `invalid_map_error_sample` → 改 v2 版（stable code
  `unsupported_system_map_schema_version`）或整段刪除（目前無 component 消費）。

### 3-2. `graphViewModelSchema` 補欄位（RC-7）

`types.ts:75-90` 比 backend `GraphViewModel` 少 11 個欄位，zod 會**靜默丟棄**。
至少補：`scan_id`、`build_id`、`mapping_completeness`、`filters.lenses`
（其餘欄位清單見 residue-C RC-7）。

### 3-3. `SystemNode.statusKey()` 接住新 status（RC-10）

`SystemNode.tsx:27-34` 的 fallback 是 `"detected"`——v2 的 `partial` /
`undetermined` 會被畫成綠燈 detected，違反「detected 需 direct evidence」原則。
改法：fallback 改成明確的 `undetermined` 視覺態，並補 `partial`。

### 3-4. 停止 `new_extension_component` / `ui_extension`（RC-1 / RC-9 / RC-16）

⚠️ **是「替換」不是「刪除」**（RC-9）：前端 union 從來沒有
`non_baseline_capability_candidate`，只刪 legacy 值會讓 enum 剩單值，backend 送
`non_baseline_capability_candidate` 時 zod parse 直接炸掉 proposal 面板。

**同一個 commit 內完成**（RC-1：這幾處互相綁死）：

| 檔案 | 改法 |
| --- | --- |
| `types.ts:334`、`types.ts:371` | `z.enum(["existing_slot_mapping", "non_baseline_capability_candidate"])`（backend 現行 enum 就這兩個值） |
| `EditForm.tsx:38` | 三元運算子改常數 `mapping_type: "existing_slot_mapping"`（刪 `ui_extension` → 舊 type 分支） |
| `scanTemplate.mock.ts:237` | 刪 `{ value: "ui_extension", ... }` 整行（不刪的話下拉選單留一個 backend 沒有的 slot，送出會吃難懂的 422） |
| `scanTemplate.mock.ts:201, 204, 205, 209` | candidate:3 改成 `non_baseline_capability_candidate` 示範，或整個刪掉 |
| `frontend-json-sample.json` | sample 對齊 v2；無舊 proposal type（見 3-1） |

**現況備註（已核對）：**

- 正常 map 已是 `ai-system-map/v2`（預設）。
- Backend active enum **不含** `new_extension_component`
  （`ManualMappingType` 只有 `existing_slot_mapping` /
  `non_baseline_capability_candidate`）。
- 若仍 POST 舊 type → **422** `legacy_mapping_type_read_only`。
- Frontend 型別與表單仍可組出舊 payload，但 **proposal UI 尚未接線**
  （`ProposalModal.decide()` 是 `setTimeout` stub，`frontend/src/services/`
  沒有 mapping API client），payload 不會離開瀏覽器。要清的原因是**未來接線時
  的地雷**，不是現行 live bug。

### 3-5. 不要動的東西

- `SLOT_OPTIONS` 其餘 8 個 slot（RC-12）：整份是 legacy `rag-core-v1` slot 模型，
  屬 Plan 06 / 52-node reference map 遷移範圍，**本輪不動**。
- 為什麼第 3 批不急：`ProposalModal.decide()` 是 `setTimeout` stub、
  `frontend/src/services/` 沒有 mapping API client——舊 payload **送不出瀏覽器**
  （RC-13）。它是「接線前必須清完的地雷」，不是 live bug。

---

## 驗收清單

- [ ] `cd frontend && pnpm lint && pnpm test && pnpm build` 三關全綠
  （zod 維持 v3 `^3.24.1`，不用 v4 API；不用 `as` 繞 type error）。
- [ ] **Sample mode**：Viewer / Sidebar / Replay / DetailPanel 用新 v2 sample
  全部正常（不是 unknown / 空白）。
- [ ] **API mode**：`uv run python scripts/dev.py` 起後端，掃 fixture repo——
  進度訊息顯示「Scan completed.」而非「unrecognized scan progress event」警告（1-1；
  ⚠️ **不要**驗收「節點逐一 highlight」，那要等 backend 做完動態掃描串流）、
  boundary 決策流程不 throw（1-2）、Sidebar 顯示
  真實摘要（2-2）、Replay 顯示「尚未接線」而非空白（2-1）。
- [ ] `rg new_extension_component frontend/src` 與 `rg "ui_extension" frontend/src`
  → 0 命中；通知 backend 重跑
  `uv run pytest tests/contracts/test_v2_cutover_consumer_allowlist.py`。
- [ ] Edit / accept 只送 backend 現行 mapping types
  （`existing_slot_mapping` / `non_baseline_capability_candidate`）。
- [ ] ⚠️ RC-14：census 5 筆歸零只是**必要條件**——第 2 批那些檔（`sampleMap.ts`、
  `App.tsx`、`utils/graph.ts`）census 根本掃不到，別做完第 3 批就宣告完工。

---

## 附錄 A — 測試全文（照抄）

`frontend/src/services/viewerApi.test.ts`：

```ts
import { describe, expect, it } from "vitest";

import { parseScanProgressEvent } from "./viewerApi";

describe("parseScanProgressEvent", () => {
  it("accepts the null-valued fields the backend actually sends", () => {
    const raw = JSON.stringify({
      event: "scan_progress",
      status: "completed",
      stage: "validate",
      message: "Scan completed.",
      percent: 100,
      node_id: null,
      edge_id: null,
      component_id: null,
      source_id: null,
      slot: null,
      evidence_id: null,
      scan_depth: "system",
      timestamp: "2026-07-27T15:33:48.556248Z",
    });

    const parsed = parseScanProgressEvent(raw);

    expect(parsed?.event).toBe("scan_progress");
    expect(parsed?.event).not.toBe("invalid_event");
  });
});
```

`frontend/src/services/projectScanApi.test.ts`：

```ts
import { describe, expect, it } from "vitest";

import { scanCreateResponseSchema } from "../types";

describe("scanCreateResponseSchema", () => {
  it("parses a requires_boundary_decision response with no scan_id", () => {
    const payload = {
      project_id: "project:abc",
      status: "requires_boundary_decision",
      boundary_proposals: [],
      available_boundary_actions: ["scan_this_run", "skip_this_run"],
    };

    expect(() => scanCreateResponseSchema.parse(payload)).not.toThrow();
  });

  it("still parses a completed response with scan_id", () => {
    const payload = {
      project_id: "project:abc",
      scan_id: "scan:1",
      status: "completed",
      build_result: {},
    };

    const parsed = scanCreateResponseSchema.parse(payload);
    expect(parsed.status).toBe("completed");
  });
});
```

---

## Source of truth

- 逐條細節與證據：`docs/work/Timmy/schedule/report/2026-07-28-plan13-residue/residue-C-frontend.md`（RC-1..RC-16）
- 原始 backend 計畫：`docs/work/Timmy/schedule/plan/unfinish/phase2.5/2.md`（Task 9）、
  `.../s1-v2-cutover/13.5.md`、`.../s1-v2-cutover/13.6.md`
- 契約：`frontend/API_CONTRACT.md:256`（pending 無 scan_id）、`:301-309`（SSE highlight）、
  `docs/API-GUIDE.md`（含 `legacy_mapping_type_read_only`）
- Backend guard（防護，非產品入口）：`src/kai_mind/web/legacy_mapping_guards.py`
- 歷史 handoff（已併入本檔，勿再開新子集）：
  `../meeting_sync_2026_07_15/frontend-ai-system-map-v2-cutover.md`、
  `../meeting_sync_2026_07_07/frontend-legacy-extension-retirement.md`
