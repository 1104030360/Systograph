# Task 20: Implement AI Mapping Proposal Flow

## 目標
實作 pending-only `MappingProposalService`，讓 AI 或 rule-assisted helper 可以根據 masked evidence summary 與使用者說明產生 mapping proposal。proposal 必須等待使用者 accept/edit/reject，不能直接寫入 canonical JSON。

## 為什麼要先做這個
Manual mapping store 先完成後，AI proposal 才有安全落點。這符合設計文件的分期：baseline manual selection first，AI mapping proposal later milestone。

## 產品與架構校正
本任務的核心 UX 不是讓使用者自己翻 code，也不是讓 AI 自動修改 map；而是讓 KAI-Mind 針對 `unmapped / needs_confirmation` 提供 2-3 個有 evidence 的候選方案，使用者再 accept/edit/reject/skip。

AI 可以是地端模型，但仍不可被設計成「自己去找檔案、自己讀 raw source、自己決定要掃哪裡」的 agent。KAI-Mind scanner 必須先用 deterministic provider / bounded detail scan 收集 evidence，經過 `SecretMaskingService` 後組成 `MappingEvidencePacket`，再把這個 bounded context 餵給 AI。

推薦邊界：

- Python scanner 負責找檔案、讀檔、抽取 imports / class / function / call-like signals、遮蔽 secret。
- `MappingProposalService` 負責把 masked `MappingEvidencePacket` 轉成 pending proposal。
- Optional local LLM 只能像 stateless function 一樣接收 bounded input / 回傳 structured JSON，不可擁有 `read_file`、shell、network、repo traversal 等工具權限。
- Local LLM unavailable、輸出不合法或 schema validation 失敗時，必須退回 deterministic fallback，不可讓 scan 掛掉。
- 不使用 `confidence` 欄位。若 UI 需要排序或語氣，可使用 `rank`、`recommendation_level`、`uncertainty_reason`，且只存在 proposal lifecycle，不進 canonical `ai_system_map.json`。

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
- 建立 `MappingEvidencePacket` / `MappingCandidate` model，用來保存已遮蔽、已裁切、可追溯 evidence context。
- 建立 `MappingProposalService`。
- 支援 input：unmapped component、masked evidence packet、user description、available slots/extensions。
- `MappingEvidencePacket` 至少包含：source file、observed kind、reason、evidence ids、rule ids、masked evidence values/snippets、dependency signals、import/class/function/call-like signals、context limits metadata。
- 支援輸出「候選 mapping」，用來回答使用者不知道 unmapped component 應確認到哪裡的情境；候選可以是 existing slot mapping、new extension component，或需要更多使用者說明。
- 每個 candidate 必須包含：candidate type、target slot 或 proposed extension draft、human-readable label、rationale、evidence ids、rank 或 recommendation_level、uncertainty_reason。
- proposal 若涉及 extension placement，可包含 `suggested_edges` / `flow_hint`，但只能作為 pending proposal，不得進 baseline `Flow.edges`。
- 產生 proposal status：`pending_user_confirmation`。
- 預留 optional local LLM provider interface。provider 只接受 `MappingEvidencePacket` 和 allowed output schema，不接受檔案路徑讀取工具、shell tool 或 raw project root。
- local LLM output 必須通過 Pydantic / JSON Schema validation；不合法輸出直接丟棄並使用 deterministic fallback。
- 支援 accept/edit/reject 轉成 manual mapping。
- 使用 FastAPI 建立 proposal routes，例如 `GET /api/mapping-proposals`、`POST /api/mapping-proposals`、`POST /api/mapping-proposals/{proposal_id}/decision`。
- 更新 Epic 1 local API guide，加入 proposal lifecycle、pending-only rule、AI unavailable degrade behavior。

## 不包含範圍
- 不要求連接外部 LLM。
- 不讓 local LLM 自由讀取 repo、呼叫 `read_file`、執行 shell、做 network request 或自行決定 scan boundary。
- 不把 raw source file 整份交給 AI；若需要 code context，必須先經過 bounded extraction、masking、size limit。
- 不讓 AI 自動確認。
- 不讓 proposal 直接改 `components_by_slot`。
- 不讓 proposal 直接改 `flows`、`extensions` 或 `query_trace_events`。
- 不使用 `confidence` 欄位，也不讓 confidence-like 分數進 canonical JSON。
- 不把 `unmapped_components.suggested_actions` 當成 placement proposal；`suggested_actions` 只保留操作建議。
- 不做 scan boundary review。
- 不做 runtime tracing、`sys.settrace`、in-process instrumentation 或呼叫 target app；runtime trace 屬於 Task 22 且必須 opt-in。

## 建議實作步驟
1. 擴充 `src/kai_mind/core/models/mapping.py`。
2. 建立 `src/kai_mind/core/services/mapping_proposal_service.py`。
3. 建立 `MappingEvidencePacket` builder 的第一版：從既有 unmapped component + evidence array 組出 masked packet；Task 21 可在之後用 bounded detail scan 補更完整 signals。
4. 實作 deterministic fallback proposal：根據 known extension keywords、observed kind、rule ids、dependency/import/function signals 提供候選。
5. 對 ambiguous unmapped component 產生 2-3 個候選：例如 map to existing slot、confirm as extension、skip / needs more info。
6. 若候選是 extension，proposal 可附 `suggested_edges` 或文字型 `flow_hint`；所有 target 必須引用已存在 slot、confirmed component 或 proposed extension id。
7. 預留 optional local LLM provider interface，但 unavailable 時 graceful degrade。
8. 實作 local LLM output structured validation：只接受 schema-defined candidates；拒絕 unknown fields、raw secret-like values、`confidence`。
9. 實作 proposal validation。
10. 實作 accept -> manual mapping draft。
11. 建立 FastAPI proposal routes，所有 decision 都必須走 `MappingProposalService` / `ManualMappingService`。
12. API response 要讓前端能渲染候選卡片：label、target、recommendation_level/rank、rationale、evidence ids、uncertainty_reason、available actions。
13. 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`。
14. 測試：proposal pending、不進 canonical map、accept 後需 validation；proposal 不會讓 unmapped component 直接出現在 baseline `Flow.edges`；web route 不會在 AI unavailable 時讓 scan 失敗；local LLM provider 不會收到 raw project root 或 unmasked evidence；`confidence` output 被拒絕。

## 預期輸出
- `src/kai_mind/core/services/mapping_proposal_service.py`
- 更新 `src/kai_mind/core/models/mapping.py`
- `src/kai_mind/core/services/mapping_evidence_packet_builder.py`
- `src/kai_mind/web/routes/mapping_proposal_routes.py`
- 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`
- `tests/unit/core/test_mapping_proposal_service.py`
- `tests/unit/core/test_mapping_evidence_packet_builder.py`
- `tests/web/test_mapping_proposal_routes.py`

## 驗收標準
- proposal status 永遠先是 `pending_user_confirmation`。
- AI/local provider unavailable 不影響 deterministic scan。
- local LLM provider 只能接收 masked `MappingEvidencePacket`，不能自行讀檔、掃 repo、呼叫 shell 或 network。
- local LLM output 必須是 structured output 並通過 validation；不合法或含 `confidence` / unmasked secret 時丟棄。
- proposal 不會出現在 canonical components，除非使用者確認並重新 normalize。
- evidence summary 已 masked。
- 使用者面對 unmapped component 時，可以取得候選 mapping 說明，而不是只看到 `confirm_mapping` 這種動作名稱。
- 候選 placement 資訊存在 `MappingProposal`，不是存在 `UnmappedComponent.suggested_actions`。
- candidate 使用 `rank` / `recommendation_level` / `uncertainty_reason` 表達排序與不確定性，不使用 `confidence`。
- 未 accept 的 proposal 不會改動 `components_by_slot`、`extensions`、`flows` 或 replay events。
- local web API 可列出 / 建立 / 決策 proposal，但 response 不包含 unmasked evidence。
- API guide 已同步記錄 proposal status transition。

## 可能風險與注意事項
- 不要把 AI output 當 source of truth。
- 如果 proposal reference 不存在 evidence/slot，必須拒絕。
- 地端 AI 降低雲端傳輸風險，但不消除 downstream leakage；rationale、logs、proposal JSON、GUI 都仍可能外洩 secret，因此所有 input/output 仍需 masking + validation。
- 給太多 raw code 會增加 token 成本與降低地端小模型穩定性；優先給 high-signal bounded evidence，而不是整份檔案。
- 參考依據：設計文件明確要求 AI 只可做 proposal；Stage 5/6 的 AI 只能輔助 mapping/rationale wording。
- Query router / custom router 這類候選 extension 不屬於 Task 14 baseline flow；proposal 只能協助使用者確認，confirmed 後由 Task 19 manual mapping store 和後續 normalize/replay 階段生效。
- Task 21 可以產生更豐富的 `MappingEvidencePacket`；Task 22 的 runtime trace 只能在使用者 opt-in 後提供補充 evidence，不得變成本任務預設行為。

## 新手提示
AI proposal 像助教建議答案，不是最後答案。最後答案必須由使用者確認，再通過 validator。

## 視覺化說明
```text
┌──────────────────────────┐
│ unmapped + masked         │
│ EvidencePacket            │
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ MappingProposalService    │
│ deterministic fallback    │
│ optional local LLM        │
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
