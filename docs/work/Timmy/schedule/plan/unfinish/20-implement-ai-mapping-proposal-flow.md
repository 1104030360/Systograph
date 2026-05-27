# Task 20: Implement AI Mapping Proposal Flow

## 目標
實作 pending-only `MappingProposalService`，讓 AI 或 rule-assisted helper 可以根據 masked evidence summary 與使用者說明產生 mapping proposal。proposal 必須等待使用者 accept/edit/reject，不能直接寫入 canonical JSON。

## 為什麼要先做這個
Manual mapping store 先完成後，AI proposal 才有安全落點。這符合設計文件的分期：baseline manual selection first，AI mapping proposal later milestone。

## 前置需求
- Task 13 已有 unmapped components。
- Task 19 已有 manual mapping store。
- Task 5 已有 masking service。

## 實作範圍
- 建立 `MappingProposal` model。
- 建立 `MappingProposalService`。
- 支援 input：unmapped component、masked evidence summary、user description、available slots/extensions。
- 產生 proposal status：`pending_user_confirmation`。
- 支援 accept/edit/reject 轉成 manual mapping。

## 不包含範圍
- 不要求連接外部 LLM。
- 不讓 AI 自動確認。
- 不讓 proposal 直接改 `components_by_slot`。
- 不做 scan boundary review。

## 建議實作步驟
1. 擴充 `src/kai_mind/core/models/mapping.py`。
2. 建立 `src/kai_mind/core/services/mapping_proposal_service.py`。
3. 實作 deterministic fallback proposal：根據 known extension keywords 提供候選。
4. 預留 optional local LLM provider interface，但 unavailable 時 graceful degrade。
5. 實作 proposal validation。
6. 實作 accept -> manual mapping draft。
7. 測試：proposal pending、不進 canonical map、accept 後需 validation。

## 預期輸出
- `src/kai_mind/core/services/mapping_proposal_service.py`
- 更新 `src/kai_mind/core/models/mapping.py`
- `tests/core/test_mapping_proposal_service.py`

## 驗收標準
- proposal status 永遠先是 `pending_user_confirmation`。
- AI/local provider unavailable 不影響 deterministic scan。
- proposal 不會出現在 canonical components，除非使用者確認並重新 normalize。
- evidence summary 已 masked。

## 可能風險與注意事項
- 不要把 AI output 當 source of truth。
- 如果 proposal reference 不存在 evidence/slot，必須拒絕。
- 參考依據：設計文件明確要求 AI 只可做 proposal；Stage 5/6 的 AI 只能輔助 mapping/rationale wording。

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
