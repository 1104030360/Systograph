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
12. Scope 修正：前端 proposal UI / API helper / candidate cards / decision mutation 不混入 Task 20，已拆到 Task 20a。
13. 文件：更新 Epic 1 local API guide、Task 20 plan、Phase 20 TODO 與本 report 最新狀態。

## 測試方式
新增測試：

- `tests/unit/core/test_mapping_evidence_packet_builder.py`
  - packet 只包含 unmapped 引用的 evidence。
  - evidence value / snippet 已遮蔽 secret，並保留 source file、rule id、line range、context metadata。
- `tests/unit/core/test_mapping_proposal_service.py`
  - deterministic proposal 預設 pending，使用 rank / recommendation_level，不使用 confidence。
  - provider output 含 `confidence` 時 retry 一次後 fallback。
  - provider 回傳不存在的 evidence / slot 時 fallback。
  - valid provider output 會被保存成 pending proposal。
  - accept 會建立 Phase 19 manual mapping draft；reject 不建立 manual mapping。
- `tests/unit/core/test_nvidia_nim_proposal_provider.py`
  - NVIDIA provider 只送 masked packet 與 schema summary。
  - NVIDIA provider 可從 YAML template render prompt messages。
  - YAML template 缺少必要變數時會回報 provider unavailable，讓上層可 fallback。
  - NVIDIA provider 可從 TOML 讀取 endpoint、model、max_tokens、temperature、top_p、stream、enable_thinking 等非敏感預設。
  - `.env` / environment variable 可以覆蓋 TOML 的非敏感值；`NVIDIA_API_KEY` 不放 TOML。
  - HTTP 401 會轉成 provider unavailable error。
- `tests/web/test_mapping_proposal_routes.py`
  - `/api/mapping-proposals` create/list。
  - proposal create 不 mutate current `/api/map` payload。
  - decision accept 會建立 manual mapping。
  - provider unavailable 時 route 仍 deterministic fallback。
  - 尚未載入 map 時回傳 `map_not_loaded`。

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

## 測試結果
```bash
.venv/bin/pytest tests/unit/core/test_mapping_evidence_packet_builder.py tests/unit/core/test_mapping_proposal_service.py tests/unit/core/test_nvidia_nim_proposal_provider.py tests/web/test_mapping_proposal_routes.py tests/web/test_nvidia_provider_app_wiring.py -q
# 21 passed

.venv/bin/ruff check src tests
# All checks passed

.venv/bin/mypy src tests
# Success: no issues found

cd frontend && pnpm build
# 前一輪 Phase 20 曾執行並通過；2026-06-08 prompt template 補強未修改 frontend，因此本輪未重跑。

.venv/bin/pytest -q
# 332 passed
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
- API guide 已同步；前端 proposal API helper / candidate UI 已拆到 Task 20a：已完成。
- GUI candidate card UI、production provider config、NVIDIA key management / retention / licensing：未納入本階段，需另開任務。
