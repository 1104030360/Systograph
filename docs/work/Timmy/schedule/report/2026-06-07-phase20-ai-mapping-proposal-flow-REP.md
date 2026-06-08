# 2026-06-07 Phase 20 AI Mapping Proposal Flow Report

## 實作邏輯
Phase 20 的核心是 pending-only mapping proposal。Proposal 只根據 masked / bounded `MappingEvidencePacket` 產生候選建議，不直接修改 canonical `ai_system_map.json`。

本次實作採用以下資料流：

```text
latest ai_system_map.unmapped_components[]
  -> MappingEvidencePacketBuilder
  -> masked MappingEvidencePacket
  -> MappingProposalService
  -> deterministic candidates or optional provider output
  -> pending_user_confirmation proposal
  -> user decision
  -> optional ManualMappingService draft
  -> next scan / normalize applies confirmed mapping
```

`MappingProposalService` 是唯一處理 provider validation、fallback、proposal lifecycle 與 decision handoff 的地方。Route 只從目前 session 的最新 map 找 unmapped/evidence，建立 packet 後呼叫 service；不接受前端提交 raw evidence、raw source 或 project root。

2026-06-08 補強：`NvidiaNimProposalProvider` 的 prompt 文字已從 Python hardcoded string 移到 YAML template。YAML 只負責「怎麼跟 LLM 說話」；真正的 schema validation、evidence id / slot reference validation、secret validation 與 deterministic fallback 仍保留在 Python service/provider 邊界。

2026-06-08 補強：`NvidiaNimProposalProvider` 的 endpoint、model、timeout、generation defaults 已從 Python hardcoded constants 移到 bundled TOML config。TOML 只放非敏感預設值；`NVIDIA_API_KEY` 仍只從 `.env` / 環境變數提供，不進 repo config。

2026-06-08 review 修正：確認並修正三個 proposal lifecycle 問題。Proposal create 現在使用 requested project 的 build result，不再讀 process-wide latest map；proposal decision 現在只允許 pending proposal；provider suggested edge validation 現在和 `ManualMappingService` 可持久化的 endpoint 規則一致。

2026-06-08 review 修正：hosted NVIDIA provider 現在是真正 explicit opt-in。即使 `.env` 或 process env 有 `NVIDIA_API_KEY`，也必須同時設定 `KAI_MIND_ENABLE_NVIDIA_NIM_PROPOSALS=true` 才會 wire `NvidiaNimProposalProvider`。

2026-06-08 open-source config 校正：參考 R2R、LangChain、LlamaIndex、Dify 後，KAI-Mind 採用「runtime provider defaults 放 TOML/env；output schema / safety bounds 留在 Pydantic model」的分界。`timeout_seconds`、`max_tokens`、`temperature`、`top_p` 可由 TOML 設定並由 loader 檢查範圍；`MappingCandidate` 欄位長度、candidate count、suggested edge count、provider error reason 長度等屬於 API/safety contract，已集中成 Python constants 並保留在 `src/kai_mind/core/models/mapping.py`。

2026-06-08 follow-up 修正：同一個 `project_id` / `source_unmapped_id` 已有 pending proposal 時，`create_proposal()` 會回傳既有 proposal，不再重複建立；accept/edit 前會檢查同一個 source 是否已有 confirmed manual mapping，避免舊的重複 pending proposal 被後續 accept 成重複 mapping。Provider secret rejection 測試也已參數化覆蓋 `label`、`component_name`、`provider`、`flow_hint`、`suggested_edges`。`MappingProposalDecisionResult` 現在會用 model validator 擋下 accepted/edited 卻沒有 `manual_mapping` 的不可能狀態。

2026-06-08 blocking 修正：edit decision 不再信任 client 傳入的 proposal identity fields。`project_id`、`source_unmapped_id`、`source_file`、`observed_kind`、`proposal_id`、`decision_source` 會由 server 從 proposal 覆蓋；`edited_mapping.evidence_ids` 必須是 proposal packet evidence ids 的 subset。`user_description` 現在會在 evidence packet builder 走 masking + truncation，並由 Pydantic schema 限長。NVIDIA `.env` numeric / boolean overrides 與 direct provider overrides 現在套用和 TOML loader 相同的 timeout / max_tokens / temperature / top_p / boolean guard；格式錯誤或超界會 raise sanitized `LlmProposalConfigError`，不再 silent fallback。

## 實作步驟
1. 查證 NVIDIA 官方 NIM / Gemma 4 31B 文件，修正 Task 20 plan：hosted NIM 是外部 endpoint，不是本機模型；`google/gemma-4-31b-it` 只能作為 optional hosted provider adapter。
2. 建立 Phase 20 TODO，先記錄資料流、TDD 步驟與驗收點。
3. RED：新增 builder / service / NVIDIA provider / web route tests，先確認新模組不存在時測試失敗。
4. GREEN：擴充 `src/kai_mind/core/models/mapping.py`，新增 proposal、candidate、evidence packet、decision models。
5. GREEN：新增 `MappingEvidencePacketBuilder`，只從 canonical evidence array 取 unmapped 引用到的 evidence，並套用 `SecretMaskingService`。
6. GREEN：新增 `MappingProposalService`、proposal repository protocol、in-memory repository、optional provider protocol。
7. GREEN：新增 deterministic fallback candidates，支援 vector store、router extension、reranker extension、needs more information、skip for now。
8. GREEN：新增 `NvidiaNimProposalProvider`，使用 hosted NIM chat completions 端點；測試使用 `httpx.MockTransport`，不打真實 NVIDIA API。
9. GREEN：新增 `/api/mapping-proposals` list/create routes 與 `/api/mapping-proposals/{proposal_id}/decision` route。
10. GREEN：新增 `src/kai_mind/core/services/prompt_template_loader.py` 與 `src/kai_mind/core/prompts/mapping_proposal.v1.yaml`，讓 provider prompt 可以獨立調整。
11. GREEN：新增 `src/kai_mind/core/services/llm_proposal_config_loader.py` 與 `src/kai_mind/core/configs/llm_proposal.toml`，讓 provider 非敏感預設值可以獨立調整。
12. GREEN：修正 proposal route 的 project boundary，`InMemorySessionStore` 會保存 per-project build result，`POST /api/mapping-proposals` 只使用 requested project 的 map。
13. GREEN：修正 proposal decision lifecycle，非 pending proposal 不能再 accept/edit/reject/skip，避免 retry 建立重複 manual mapping 或覆蓋 final status。
14. GREEN：修正 suggested edge endpoint validation，只允許 manual mapping 可保存的 template slot ids 與 proposed extension id。
15. GREEN：新增 explicit opt-in guard，hosted NVIDIA provider 需 `KAI_MIND_ENABLE_NVIDIA_NIM_PROPOSALS=true` + `NVIDIA_API_KEY` 才啟用。
16. GREEN：新增 provider output bounds，限制 candidate count、文字欄位長度、evidence id 數量、suggested edge 數量，避免 response bloat 或 UI/report leakage。
17. GREEN：收斂 provider exception handling，只把預期 provider unavailable / validation 類錯誤轉 deterministic fallback，並用 stable sanitized reason code。
18. GREEN：補 decision request invariant，accept/edit/reject/skip 的 payload shape 不再允許互相矛盾。
19. GREEN：補 proposal decision lock，降低同 process concurrent decision 建立重複 manual mapping 的風險。
20. GREEN：補 duplicate pending proposal guard、confirmed mapping guard、decision result impossible-state validator。
21. Scope 修正：前端 proposal UI / API helper / candidate cards / decision mutation 不混入 Task 20，已拆到 Task 20a。
22. 文件：更新 Epic 1 local API guide、Task 20 plan、Task 20a plan、Phase 20 TODO 與本 report 最新狀態。

## 測試方式
新增測試：

- `tests/unit/core/test_mapping_evidence_packet_builder.py`
  - packet 只包含 unmapped 引用的 evidence。
  - evidence value / snippet 已遮蔽 secret，並保留 source file、rule id、line range、context metadata。
- `tests/unit/core/test_mapping_proposal_service.py`
  - deterministic proposal 預設 pending，使用 rank / recommendation_level，不使用 confidence。
  - provider output 含 `confidence` 時 retry 一次後 fallback。
  - provider 回傳不存在的 evidence / slot 時 fallback。
  - provider output 含未遮蔽 secret 時 fallback，且 API reason 只保留 stable code。
  - provider output 未遮蔽 secret 出現在 `label`、`component_name`、`provider`、`flow_hint`、`suggested_edges` 時都會 fallback。
  - provider output 超過 bounded field length 時 fallback。
  - provider unexpected bug 不被 broad catch 靜默吞掉。
  - valid provider output 會被保存成 pending proposal。
  - accept / edit 會建立 Phase 19 manual mapping draft；reject / skip 不建立 manual mapping。
  - edit decision 無法用 client payload 改寫 project/source/source_file/observed_kind，且 unknown evidence 會被拒絕。
  - 同一個 project/source 的重複 pending proposal 不會被重複建立。
  - 同一個 source 已有 confirmed manual mapping 時，後續 pending proposal accept/edit 會被拒絕。
  - unknown candidate、missing proposal、second decision、矛盾 decision payload 都會被拒絕。
  - `MappingCandidate` tagged-union shape 會被 Pydantic validator 擋下。
  - `MappingProposalDecisionResult` 會拒絕 accepted/edited 但缺少 `manual_mapping` 的不可能狀態。
- `tests/unit/core/test_nvidia_nim_proposal_provider.py`
  - NVIDIA provider 只送 masked packet 與 schema summary。
  - NVIDIA provider 可從 YAML template render prompt messages。
  - YAML template 缺少必要變數時會回報 provider unavailable，讓上層可 fallback。
  - NVIDIA provider 可從 TOML 讀取 endpoint、model、max_tokens、temperature、top_p、stream、enable_thinking 等非敏感預設。
  - NVIDIA provider 需要 explicit enable flag，不能只因 `NVIDIA_API_KEY` 存在就啟用。
  - `.env` / environment variable 可以覆蓋 TOML 的非敏感值；`NVIDIA_API_KEY` 不放 TOML。
  - `.env` numeric / boolean overrides 格式錯誤或超出 safe range 時會 raise sanitized config error。
  - direct provider overrides 超出 safe range 時會 raise sanitized config error。
  - HTTP 401 會轉成 provider unavailable error。
- `tests/web/test_mapping_proposal_routes.py`
  - `/api/mapping-proposals` create/list。
  - proposal create 不 mutate current `/api/map` payload。
  - 多專案情境下，proposal create 不會用 latest scan 的其他 project evidence。
  - decision accept 會建立 manual mapping。
  - decision edit / skip / missing proposal / second decision lifecycle。
  - provider unavailable 時 route 仍 deterministic fallback。
  - 尚未載入 map 時回傳 `map_not_loaded`。
- Review regression tests:
  - accepted/edited/rejected/skipped proposal 不可再次 decision。
  - provider candidate suggested edge 不可引用 `ManualMappingService` 無法保存的 confirmed component id。

## 遇到的問題與解法
- 問題：NVIDIA Platform 容易被誤寫成 local LLM。
  - 解法：在 Task 20 plan 補明 `NvidiaNimProposalProvider` 是 hosted endpoint adapter，不是 production default，也不是本機模型。
- 問題：provider output 若只靠 prompt 要求，很容易混入 `confidence` 或不存在的 reference。
  - 解法：所有 provider output 都先經 Pydantic `extra="forbid"` 與 reference validation；失敗最多 retry 一次，仍失敗就 fallback。
- 問題：route 若接受前端送 evidence packet，信任邊界會變成 UI。
  - 解法：route 只接受 `project_id`、`source_unmapped_id`、可選 user description；packet 由 backend 從 latest map 建立。
- 問題：前端尚未有 proposal UI。
  - 解法：不把前端實作混入 Task 20；proposal UI / API helper / candidate cards / decision mutation 已另開 Task 20a。
- 問題：provider prompt hardcode 在 Python 裡，後續調整 template 需要改程式碼。
  - 解法：新增 YAML prompt template loader，預設 template 放在 `src/kai_mind/core/prompts/mapping_proposal.v1.yaml`。Provider 每次呼叫時把 masked packet、output schema、validation error summary 填入 template；validation 規則仍留在 Python。
- 問題：provider endpoint/model/generation defaults hardcode 在 Python 裡，和 R2R 類似的 profile config 風格不一致。
  - 解法：新增 TOML config loader，預設 config 放在 `src/kai_mind/core/configs/llm_proposal.toml`。`.env` 仍可覆蓋非敏感值，但 secret 只允許由 `.env` / 環境變數提供。
- 問題：本機 `.env` 若有 `NVIDIA_API_KEY`，web route deterministic 測試會真的接上 provider。
  - 解法：web route 測試改成明確注入無 provider 的 `MappingProposalService`，測試結果不再受本機 `.env` 影響；NVIDIA app wiring 另由專門測試覆蓋。
- 問題：proposal route 使用 process-wide latest build result，可能把 A project evidence 塞進 B project proposal。
  - 解法：session store 增加 per-project build result，scan 時用 project_id 保存，proposal create 只用 requested project 的 build result。
- 問題：proposal accept 後 retry decision 會再次建立 manual mapping，reject/skip 也能覆蓋 final status。
  - 解法：`MappingProposalService.decide()` 在任何 decision 前檢查 proposal status 必須是 `pending_user_confirmation`。
- 問題：provider candidate suggested edge 可以引用 confirmed component id，但 manual mapping extension validation 不接受該 endpoint。
  - 解法：proposal validation 的 allowed edge endpoints 收斂為 template slot ids + proposed extension id，和 manual mapping persistence 規則一致。
- 問題：只要 `.env` 存在 `NVIDIA_API_KEY` 就 wire hosted provider，和 explicit opt-in 承諾衝突。
  - 解法：新增 `KAI_MIND_ENABLE_NVIDIA_NIM_PROPOSALS=true` guard；沒有 flag 時 deterministic fallback，不會呼叫 hosted endpoint。
- 問題：provider output 缺少 bounded field / candidate count limits。
  - 解法：`MappingCandidate` / `MappingProviderCandidateBatch` / `MappingProposal` 加上 Pydantic limits，並集中成 Python constants。這些是 API/safety contract，不放 TOML。
- 問題：provider exception broad catch 會把 provider bug 也當 fallback，且可能把 `str(exc)` 帶到 API response。
  - 解法：只 catch 預期 provider unavailable / validation 類錯誤，回 stable sanitized code `provider_unavailable` 或 `provider_invalid_output`。
- 問題：decision payload 可同時帶互斥欄位。
  - 解法：`MappingProposalDecisionRequest` 加 validator，固定 accept/edit/reject/skip 的 payload invariant。

## 外部查證摘要
- R2R 使用 TOML profile / generation config 管理 model、temperature、top_p、max_tokens、stream、api_base 等 provider runtime 參數；secret 仍走 env。
- LangChain 文件把 model 參數如 temperature / max_tokens 視為 model invocation config，同時 structured output 仍透過 Pydantic / TypedDict / JSON Schema 表達資料形狀與驗證。
- LlamaIndex 的 Settings pattern 也是集中設定 LLM / embedding / request_timeout 這類 runtime defaults。
- Dify self-host docs 用 environment variables 管理 indexing token length、sandbox timeout、provider credentials 等部署參數。
- 對 KAI-Mind 的結論：runtime/provider defaults 適合 TOML/env；proposal candidate 的欄位長度、candidate count、suggested edge count 屬於 output contract / safety guardrail，保留在 Pydantic model。

## 測試結果
```bash
.venv/bin/pytest tests/unit/core/test_mapping_evidence_packet_builder.py tests/unit/core/test_mapping_proposal_service.py tests/unit/core/test_nvidia_nim_proposal_provider.py tests/web/test_mapping_proposal_routes.py tests/web/test_nvidia_provider_app_wiring.py -q
# 54 passed

.venv/bin/ruff check src tests
# All checks passed

.venv/bin/mypy src tests
# Success: no issues found

cd frontend && pnpm build
# 前一輪 Phase 20 曾執行並通過；2026-06-08 prompt template 補強未修改 frontend，因此本輪未重跑。

.venv/bin/pytest -q
# 365 passed
```

## 驗收狀態
- Proposal status 永遠先是 `pending_user_confirmation`：已完成。
- AI/provider unavailable 不影響 deterministic proposal flow：已完成。
- Provider 只能收到 masked packet / schema summary，不收到 raw project root 或 raw source：已完成。
- Provider output 必須 structured validation，不合法、含 `confidence`、unknown evidence / slot / edge reference 時 fallback：已完成。
- Proposal 不進 canonical map，未 accept 不改 `components_by_slot`、`extensions`、`flows` 或 replay events：已完成。
- Accept / edit 轉成 Phase 19 manual mapping draft，canonical map 等下次 scan / normalize 生效：已完成。
- Local web API 可 list/create/decision proposal：已完成。
- Provider prompt template 外部化到 YAML，且不把 validation rule 搬進 prompt：已完成。
- Provider 非敏感預設值外部化到 TOML，且 secret 仍只走 `.env` / 環境變數：已完成。
- 多 project proposal create 不會跨 project 取錯 evidence：已完成。
- Proposal final status 不可被重複 decision 覆蓋，也不會建立重複 manual mapping：已完成。
- Provider suggested edge endpoints 和 manual mapping persistence 規則一致：已完成。
- API guide 已同步；前端 proposal API helper / candidate UI 已拆到 Task 20a：已完成。
- GUI candidate card UI、production provider config、NVIDIA key management / retention / licensing：未納入本階段，需另開任務。
