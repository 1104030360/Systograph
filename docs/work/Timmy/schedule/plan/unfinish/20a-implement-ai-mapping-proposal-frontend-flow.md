# Task 20a: Implement AI Mapping Proposal Frontend Flow

## 目標

> [!IMPORTANT]
> **提醒：本任務得要補完整所有前端測試**。包含導入測試框架（如 Vitest + React Testing Library），並確實撰寫 Component、API hook 等相關測試。

在 frontend viewer 中接上 Task 20 的 mapping proposal API，讓使用者可以針對 `needs_confirmation` / unmapped target 產生 proposal、檢視候選 mapping、選擇 accept/edit/reject/skip，並在決策後刷新畫面。

本任務只做前端接線與 UI，不改 Task 20 backend service 行為，也不改 canonical `ai_system_map.json` contract。

## 為什麼要拆成 20a

Task 20 的核心是 backend pending-only proposal lifecycle。Frontend UI / API helper / candidate cards / mutation flow 是另一個獨立交付面，若混在 Task 20 會讓 scope 變大，也會讓後端驗收與前端 UX 驗收互相干擾。

因此 Task 20a 專門處理：

- frontend type / API helper。
- API mode proposal query。
- create proposal 入口。
- candidate card UI。
- accept / edit / reject / skip mutation。
- mutation 後 refetch。
- proposal loading / error / fallback states。
- 前端測試或最低限度 build 驗證。

## 已檢查的目前前端狀態（2026-06-08）

已實際檢查：

- `frontend/src/types.ts`
- `frontend/src/services/viewerApi.ts`
- `frontend/src/components/DetailPanel.tsx`
- `frontend/src/App.tsx`
- `frontend/src/store/viewerStore.ts`
- `frontend/src/hooks/useViewerPayload.ts`
- `frontend/src/hooks/useScanProgress.ts`
- `frontend/API_CONTRACT.md`
- `frontend/package.json`

目前觀察：

- `DetailPanel.tsx` 目前仍只讀 `payload.mapping_proposal_result_sample`，不是後端 `/api/mapping-proposals` 的真實 response。
- `DetailPanel.tsx` 目前會顯示 sample action buttons，但 buttons 沒有 `onClick`，不會呼叫 decision API。
- `DetailPanel.tsx` 也已經有 `Overview` / `L2 Component` / `L3 Code Path` tab，但 L2/L3 目前只讀 `payload.detail_scan_result_sample`，不是後端 detail scan API。
- `App.tsx` 目前沒有 proposal query / mutation wiring，也沒有把 proposal handler 傳給 `DetailPanel`。
- `viewerStore.ts` 目前只管理 viewer selection、filters、trace/progress/detail mode，沒有 proposal lifecycle state。
- `useViewerPayload()` 目前只讀 sample 或 `/api/map` / `/map`，沒有 proposal query。
- `frontend/package.json` 目前只有 `build` / `lint`，尚未看到 frontend test runner。

### 與 Task 21a 的分工（2026-06-08 補充）

目前前端有兩個容易混在一起的未完成互動：

1. **Mapping proposal frontend flow**：使用者針對 `needs_confirmation` / unmapped target 產生候選 mapping，並 accept/edit/reject/skip。
2. **Progressive detail scan frontend flow**：使用者針對 graph node / edge / evidence 觸發 L2/L3 detail scan，讓後端補更多 bounded evidence。

本任務只做第 1 項，也就是接 Task 20 的 `/api/mapping-proposals` lifecycle。

第 2 項請由新增的 **Task 21a: Implement Detail Scan Frontend Flow** 負責。Task 21a 會接 Task 21 backend 的 `POST /api/detail-scans` / `GET /api/detail-scans/{detail_scan_id}`，並把 L2/L3 tab 從 sample-only 顯示改成真實 detail scan 結果。

兩個任務的交會點是 `DetailPanel.tsx`：

- Task 20a：在 selected unmapped target 上顯示 `Create proposal` / candidate cards / decision actions。
- Task 21a：在 L2/L3 tab 上顯示 `Run component detail scan` / `Run code path scan` / scan progress / real `detail_scans[]`。

Task 21a 完成後，detail scan 追加的新 evidence 會進 `system_map.evidence[]` 與 `unmapped_component.evidence_ids`。Task 20a 只需要在 create/decision 成功後 refetch viewer payload；不需要自己解析 source code 或 detail scan output。

## 後端 API contract

Task 20 backend 已提供：

```text
GET  /api/mapping-proposals?project_id=...
POST /api/mapping-proposals
POST /api/mapping-proposals/{proposal_id}/decision
```

Create proposal request：

```json
{
  "project_id": "project:...",
  "source_unmapped_id": "unmapped:...",
  "user_description": "optional user note"
}
```

Decision request：

```json
{
  "decision": "accept",
  "candidate_id": "candidate:..."
}
```

`edit` 可帶：

```json
{
  "decision": "edit",
  "edited_mapping": {
    "project_id": "project:...",
    "mapping_type": "existing_slot_mapping",
    "decision": "confirmed",
    "source_unmapped_id": "unmapped:...",
    "evidence_ids": ["evidence:..."],
    "target_slot": "vector_store",
    "component_name": "Edited Chroma",
    "component_kind": "vector_db"
  }
}
```

`reject` / `skip_for_now` 可帶：

```json
{
  "decision": "reject",
  "reason": "optional reason"
}
```

Payload 規則：

- `accept` 必須帶 `candidate_id`，不可帶 `edited_mapping`。
- `edit` 必須帶完整 `edited_mapping`，不可帶 `candidate_id`。
- `reject` / `skip_for_now` 只能選擇性帶 `reason`，不可帶 `candidate_id` 或 `edited_mapping`。

## 實作範圍

- 擴充 `frontend/src/types.ts`，加入 mapping proposal response / request schema。
- 擴充 `frontend/src/services/viewerApi.ts`，加入 `listMappingProposals()`、`createMappingProposal()`、`decideMappingProposal()`。
- 在 API mode 建立 proposal query，例如 `useMappingProposals(projectId)`。
- 在 selected node / edge 對應 `needs_confirmation` 或 unmapped source 時，顯示 `Create proposal` 入口。
- 若 Task 21a 已完成 detail scan 並刷新 viewer payload，本任務可以自然使用更新後的 evidence/proposal response；但本任務不負責觸發 L2/L3 detail scan。
- 將 proposal candidates render 成卡片，至少顯示：
  - `label`
  - `candidate_type`
  - `target_slot`
  - `component_name`
  - `component_kind`
  - `provider`
  - `rationale`
  - `evidence_ids`
  - `recommendation_level`
  - `uncertainty_reason`
  - `suggested_edges`
  - `flow_hint`
- 讓使用者選擇 candidate，accept 時必須送出選到的 `candidate_id`。
- 接上 `accept` / `edit` / `reject` / `skip_for_now` button 的 `onClick`。
- 實作 edit form，支援 `edited_mapping`、欄位驗證、取消、送出。
- Reject / skip 可選填 reason，送出後顯示 proposal status。
- Mutation 成功後 refetch proposal list 與 viewer payload。
- 顯示 loading / error / fallback states：
  - create proposal in progress
  - LLM timeout / deterministic fallback
  - provider invalid output
  - decision failed
  - backend validation error
  - `provider_name`
  - `provider_error_reason`
- 在 sidebar 或 graph node 顯示 pending proposal badge / count，讓使用者知道哪裡需要決策。
- 明確區分 sample mode 與 API mode：
  - sample mode 可繼續展示 `mapping_proposal_result_sample`。
  - API mode 必須讀真實 proposal endpoints。
- 不改 L2/L3 tab 的 detail scan 觸發與結果呈現；那是 Task 21a。

## 不包含範圍

- 不修改 Task 20 backend service / route 行為。
- 不讓前端直接修改 canonical `ai_system_map.json`。
- 不讓前端繞過 `POST /api/mapping-proposals/{proposal_id}/decision` 直接建立 confirmed mapping。
- 不在前端保存 raw prompt、raw source、unmasked evidence 或 API key。
- 不在 frontend 直接呼叫 NVIDIA / LLM；前端只能呼叫 KAI-Mind backend API。
- 不把 pending proposal 渲染成已確認 canonical fact。
- 不實作 `POST /api/detail-scans` / `GET /api/detail-scans/{detail_scan_id}` 前端接線；這由 Task 21a 負責。
- 不在本任務把 `payload.detail_scan_result_sample` 改成真實 L2/L3 detail scan UI；這由 Task 21a 負責。

## 建議實作步驟

1. RED：導入 Vitest 等測試框架，新增 frontend contract/schema 測試，以及 proposal list/create/decision 的 API hooks 與 Component 測試（得要補完整所有測試）。
2. 實作 `frontend/src/types.ts` proposal schemas。
3. 實作 `frontend/src/services/viewerApi.ts` proposal API helpers。
4. 建立 `useMappingProposals(projectId)` query hook。
5. 在 `App.tsx` 取得 project id；若目前 viewer payload 缺 project id，先定義 API mode 的 project id 來源或 fallback UX。
6. 在 `DetailPanel` 判斷 selected target 是否可 create proposal。
7. 建立 candidate cards component，先支援 read-only render。
8. 接 `createMappingProposal()` mutation，補 loading/error UI。
9. 接 `decideMappingProposal()` mutation，支援 accept/reject/skip。
10. 實作 edit form 與 validation。
11. Mutation success 後 refetch proposal list 與 viewer payload。
12. 補 pending proposal badge / count。
13. 更新 `frontend/API_CONTRACT.md`。
14. 跑 `cd frontend && pnpm build`，並執行所有 frontend 測試確認全數通過。

## 驗收標準

- API mode 可以列出某 project 的 pending proposals。
- 使用者點到需要確認的 target 時，可以從 UI 建立 proposal。
- UI 顯示後端回來的真實 `MappingProposal.candidates[]`，不是 sample-only data。
- Accept 時必須送出選定 `candidate_id`。
- Edit 時必須送出 `edited_mapping`，且前端有基本欄位驗證。
- Reject / skip 可以送出 optional reason，並顯示更新後 status。
- Provider fallback / provider error reason 能被使用者看見，但不暴露 raw prompt 或 secret。
- Decision 成功後 proposal list 與 viewer payload 會刷新。
- Sample mode 不會誤呼叫 backend proposal API。
- API mode 不再把 `mapping_proposal_result_sample` 當成真實 proposal。
- API mode 不會把 L2/L3 detail scan sample 誤當成真實 proposal evidence；detail scan sample 的替換由 Task 21a 驗收。
- `pnpm build` 通過；必須引入 frontend test runner，且相關的 proposal UI tests 等所有前端測試皆已補完整並通過。

## 前端工程師白話版

現在後端已經會產生 mapping 建議，但前端還沒有真正接起來。畫面目前只有 sample button，看起來像能 Accept / Reject，實際上按了不會做事。

Task 20a 要做的是把這套流程補完整：使用者看到 `Needs confirmation`，可以按「產生建議」，看到 AI / rule 給的候選卡片，選一個接受或編輯，也可以拒絕或先跳過。送出後畫面要更新，並清楚告訴使用者這個建議是 AI 產生、規則 fallback，還是 AI 失敗後改用 deterministic。
