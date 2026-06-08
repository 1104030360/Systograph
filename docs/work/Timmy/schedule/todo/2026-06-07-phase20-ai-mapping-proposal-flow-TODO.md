# 2026-06-07 Phase 20 AI Mapping Proposal Flow TODO

## 目標
實作 pending-only mapping proposal flow，讓使用者面對 `unmapped / needs_confirmation` 元件時，可以取得 2-3 個有 evidence 的候選對應建議，再由使用者 accept/edit/reject/skip。

## 實作邏輯
- `MappingProposal` 是待確認草稿，不是 canonical `ai_system_map.json` 的一部分。
- Proposal 只能由 masked `MappingEvidencePacket` 產生，不讀 project root、不收 raw source、不執行 target app。
- `MappingProposalService` 負責 validation、fallback、pending lifecycle 與 decision handoff。
- Optional provider 只能像純函式一樣接收 bounded packet 與 schema summary；provider unavailable、timeout、HTTP error、invalid JSON、unknown evidence/slot、超出 bounded output limits、unmasked secret 或 `confidence` 都要 fallback 到 deterministic candidates。
- Accept/edit 後只建立 `ManualMappingCreate` draft，真正 canonical map 影響仍由 Phase 19 manual mapping flow 在下一次 scan 生效。
- Route 只呼叫 service；HTTP client / NVIDIA NIM payload 只留在 provider/infrastructure 層。
- Provider prompt template 使用 YAML 外部化，方便後續調整措辭；schema validation、evidence/slot reference validation 與 secret validation 仍保留在 Python service 層。
- Provider 非敏感 runtime 預設值使用 TOML 外部化；`NVIDIA_API_KEY` 仍只放 `.env` / 環境變數，且必須搭配 `KAI_MIND_ENABLE_NVIDIA_NIM_PROPOSALS=true` 才啟用 hosted NVIDIA provider。
- Provider output bounds 是 API/safety contract，集中在 Pydantic model constants，不放 TOML。

## 階段規劃
1. RED：新增 `MappingEvidencePacketBuilder` 單元測試，鎖定 evidence masking、source/evidence/rule/context metadata、available target set。
2. RED：新增 `MappingProposalService` 單元測試，鎖定 pending status、deterministic candidates、invalid provider output fallback、unknown references rejection、`confidence` rejection、accept/edit/reject decision handoff。
3. RED：新增 provider 單元測試，確認 NVIDIA/NIM provider 只送 masked packet/schema summary，HTTP/validation failure 可被 service fallback。
4. RED：新增 `/api/mapping-proposals` web route 測試，確認 list/create/decision lifecycle 不 mutate current map artifact，且 AI unavailable 時仍回傳 deterministic proposal。
5. GREEN：擴充 `src/kai_mind/core/models/mapping.py` 的 proposal / evidence packet models。
6. GREEN：建立 `mapping_evidence_packet_builder.py`，從 unmapped component + evidence array 組 masked bounded packet。
7. GREEN：建立 `mapping_proposal_service.py`、repository protocol / in-memory implementation、provider protocol。
8. GREEN：建立 optional `NvidiaNimProposalProvider` adapter，但測試不呼叫真實 endpoint。
9. GREEN：建立 FastAPI proposal routes 與 app dependency wiring。
10. GREEN：新增 YAML prompt template loader 與 `mapping_proposal.v1.yaml`，讓 NVIDIA provider 不再 hardcode prompt。
11. GREEN：新增 TOML provider config loader 與 `llm_proposal.toml`，讓 endpoint/model/generation defaults 不再 hardcode 在 provider。
12. GREEN：新增 explicit opt-in guard、provider output bounds、decision invariant 與 lifecycle regression tests。
13. Scope 修正：前端 proposal UI / API helper 不混入 Task 20，另由 Task 20a 處理。
14. 文件：更新 Epic 1 local API guide 的 proposal lifecycle、pending-only rule、fallback 行為。
15. 驗證：跑 focused tests、ruff、mypy、全量 pytest；若有非本次相關失敗，記錄在 report。

## 驗收重點
- Proposal status 永遠先是 `pending_user_confirmation`。
- Proposal 未 accept 前不改 `components_by_slot`、`extensions`、`flows`、`query_trace_events` 或 latest map payload。
- Provider unavailable / invalid output 不影響 deterministic proposal flow。
- Provider input/output 不含 unmasked secret、project root、raw source、`confidence`。
- Provider 回傳不存在的 evidence id、slot、extension reference 或 edge endpoint 時會被拒絕並 fallback。
- Candidate 使用 `rank`、`recommendation_level`、`uncertainty_reason`，不使用 `confidence`。
- Accept/edit 只產生 manual mapping draft，不直接 mutate canonical artifact。
- API guide 已同步；前端 proposal API helper / candidate UI 已拆到 Task 20a。
