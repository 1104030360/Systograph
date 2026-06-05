# Task 20: Implement AI Mapping Proposal Flow

## 目標
實作 pending-only `MappingProposalService`，讓 AI 或 rule-assisted helper 可以根據 masked evidence summary 與使用者說明產生 mapping proposal。proposal 必須等待使用者 accept/edit/reject，不能直接寫入 canonical JSON。

## 為什麼要先做這個
Manual mapping store 先完成後，AI proposal 才有安全落點。這符合設計文件的分期：baseline manual selection first，AI mapping proposal later milestone。

## 承接 Task 16 延後功能
- 承接 Task 16 「不做 AI mapping proposal」的延後範圍。
- Task 16 / Task 18 只能呈現 unmapped；本任務負責提供「可能怎麼映射」的 pending proposal。
- Proposal 只能輔助使用者決策，不能直接改 `components_by_slot`、`extensions`、`flows` 或 query trace。
- 因為 GUI/local web UI 需要 proposal queue，本任務要提供 local web API 讀取 proposal、建立 proposal、accept/edit/reject proposal。

## 前置需求
- Task 13 已有 unmapped components。
- Task 19 已有 manual mapping store。
- Task 5 已有 masking service。

## 實作範圍
- 建立 `MappingProposal` model。
- 建立 `MappingProposalService`。
- 支援 input：unmapped component、masked evidence summary、user description、available slots/extensions。
- 支援輸出「候選 mapping」，用來回答使用者不知道 unmapped component 應確認到哪裡的情境；候選可以是 existing slot mapping、new extension component，或需要更多使用者說明。
- proposal 若涉及 extension placement，可包含 `suggested_edges` / `flow_hint`，但只能作為 pending proposal，不得進 baseline `Flow.edges`。
- 產生 proposal status：`pending_user_confirmation`。
- 支援 accept/edit/reject 轉成 manual mapping。
- 使用 FastAPI 建立 proposal routes，例如 `GET /api/mapping-proposals`、`POST /api/mapping-proposals`、`POST /api/mapping-proposals/{proposal_id}/decision`。
- 更新 Epic 1 local API guide，加入 proposal lifecycle、pending-only rule、AI unavailable degrade behavior。

## 不包含範圍
- 不要求連接外部 LLM。
- 不讓 AI 自動確認。
- 不讓 proposal 直接改 `components_by_slot`。
- 不讓 proposal 直接改 `flows`、`extensions` 或 `query_trace_events`。
- 不把 `unmapped_components.suggested_actions` 當成 placement proposal；`suggested_actions` 只保留操作建議。
- 不做 scan boundary review。

## 建議實作步驟
1. 擴充 `src/kai_mind/core/models/mapping.py`。
2. 建立 `src/kai_mind/core/services/mapping_proposal_service.py`。
3. 實作 deterministic fallback proposal：根據 known extension keywords 提供候選。
4. 對 ambiguous unmapped component 產生 2-3 個候選：例如 map to existing slot、confirm as extension、skip / needs more info。
5. 若候選是 extension，proposal 可附 `suggested_edges` 或文字型 `flow_hint`；所有 target 必須引用已存在 slot、confirmed component 或 proposed extension id。
6. 預留 optional local LLM provider interface，但 unavailable 時 graceful degrade。
7. 實作 proposal validation。
8. 實作 accept -> manual mapping draft。
9. 建立 FastAPI proposal routes，所有 decision 都必須走 `MappingProposalService` / `ManualMappingService`。
10. 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`。
11. 測試：proposal pending、不進 canonical map、accept 後需 validation；proposal 不會讓 unmapped component 直接出現在 baseline `Flow.edges`；web route 不會在 AI unavailable 時讓 scan 失敗。

## 預期輸出
- `src/kai_mind/core/services/mapping_proposal_service.py`
- 更新 `src/kai_mind/core/models/mapping.py`
- `src/kai_mind/web/routes/mapping_proposal_routes.py`
- 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`
- `tests/unit/core/test_mapping_proposal_service.py`
- `tests/web/test_mapping_proposal_routes.py`

## 驗收標準
- proposal status 永遠先是 `pending_user_confirmation`。
- AI/local provider unavailable 不影響 deterministic scan。
- proposal 不會出現在 canonical components，除非使用者確認並重新 normalize。
- evidence summary 已 masked。
- 使用者面對 unmapped component 時，可以取得候選 mapping 說明，而不是只看到 `confirm_mapping` 這種動作名稱。
- 候選 placement 資訊存在 `MappingProposal`，不是存在 `UnmappedComponent.suggested_actions`。
- 未 accept 的 proposal 不會改動 `components_by_slot`、`extensions`、`flows` 或 replay events。
- local web API 可列出 / 建立 / 決策 proposal，但 response 不包含 unmasked evidence。
- API guide 已同步記錄 proposal status transition。

## 可能風險與注意事項
- 不要把 AI output 當 source of truth。
- 如果 proposal reference 不存在 evidence/slot，必須拒絕。
- 參考依據：設計文件明確要求 AI 只可做 proposal；Stage 5/6 的 AI 只能輔助 mapping/rationale wording。
- Query router / custom router 這類候選 extension 不屬於 Task 14 baseline flow；proposal 只能協助使用者確認，confirmed 後由 Task 19 manual mapping store 和後續 normalize/replay 階段生效。

## 新手提示
AI proposal 像助教建議答案，不是最後答案。最後答案必須由使用者確認，再通過 validator。

## 視覺化說明
```text
┌──────────────────────────┐
│ unmapped + masked         │
│ evidence                  │
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ MappingProposalService    │
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ pending proposal          │
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ user decision             │
└──────┬────────────┬──────┘
       │ accept/edit│ reject
       ↓            ↓
┌──────────────┐ ┌──────────────────────┐
│ ManualMapping │ │ No canonical change  │
└──────────────┘ └──────────────────────┘
```
