# Task 20: Implement AI Mapping Proposal Flow

## 目標
實作 pending-only `MappingProposalService`，讓 AI 或 rule-assisted helper 可以根據 masked evidence summary 與使用者說明產生 mapping proposal。proposal 必須等待使用者 accept/edit/reject，不能直接寫入 canonical JSON。

## 為什麼要先做這個
Manual mapping store 先完成後，AI proposal 才有安全落點。這符合設計文件的分期：baseline manual selection first，AI mapping proposal later milestone。

## 最新狀態校正（2026-06-07）
Phase 20 已完成第一版 core / local API implementation：

- 已新增 `MappingEvidencePacket`、`MappingCandidate`、`MappingProposal`、proposal decision models。
- 已新增 `MappingEvidencePacketBuilder`，從目前 canonical map 的 `unmapped_components[]` 與 `evidence[]` 建立 masked / bounded / traceable packet。
- 已新增 `MappingProposalService`、proposal repository protocol / in-memory implementation。
- 已支援 deterministic fallback candidates，包含 existing slot mapping、new extension candidate、needs more information、skip for now。
- 已支援 optional provider protocol，provider output 會經 Pydantic schema validation、bounded output limits、unknown evidence / slot / edge reference validation、secret validation、`confidence` rejection；失敗時最多 retry 一次後 fallback。
- 已新增 `NvidiaNimProposalProvider` hosted NIM adapter。它不是 production default，也不是本機模型；必須 explicit opt-in 注入 provider，測試不呼叫真實 NVIDIA endpoint。
- `NvidiaNimProposalProvider` 的 prompt template 已外部化到 YAML，方便後續調整提示詞；但 schema validation、evidence/slot reference validation 與 secret validation 仍保留在 Python service 層。
- `NvidiaNimProposalProvider` 的 endpoint、model、timeout、generation defaults 已外部化到 bundled TOML；`KAI_MIND_ENABLE_NVIDIA_NIM_PROPOSALS=true` 與 `NVIDIA_API_KEY` 仍只允許由 `.env` / 環境變數提供。
- provider runtime defaults 參考 R2R / LangChain 這類開源 RAG/LLM 專案做成可設定值；但 `MappingCandidate` 的欄位長度、candidate count、suggested edge count 等 output bounds 屬於 API/schema safety contract，集中成 Python constants 並留在 Pydantic model，不放 TOML。
- 已新增 `/api/mapping-proposals` list/create routes 與 `/api/mapping-proposals/{proposal_id}/decision` route。
- Accept / edit 會轉成 Phase 19 `ManualMappingService` 的 manual mapping draft；reject / skip 只更新 proposal status。
- 已更新 `docs/work/Timmy/design/epic1-local-api-guide.md`。
- 前端 proposal UI / API helper / candidate cards / decision mutation 不混入本任務，已拆到 Task 20a。

仍刻意不包含：

- 不會只因 `.env` 或 process env 有 `NVIDIA_API_KEY` 就啟用 hosted NIM；必須同時設定 `KAI_MIND_ENABLE_NVIDIA_NIM_PROPOSALS=true`。production config / secrets policy / licensing / retention 需另開設定任務。
- 不做 frontend implementation、GUI candidate card UI、proposal button、decision mutation 或 frontend API helper；這些工作由 Task 20a 獨立處理。
- 不把 proposal 寫進 canonical `ai_system_map.json`；confirmed 後仍要由下次 scan / normalize 套用 manual mapping。

## 產品與架構校正
本任務的核心 UX 不是讓使用者自己翻 code，也不是讓 AI 自動修改 map；而是讓 KAI-Mind 針對 `unmapped / needs_confirmation` 提供 2-3 個有 evidence 的候選方案，使用者再 accept/edit/reject/skip。

AI 可以是地端模型，但仍不可被設計成「自己去找檔案、自己讀 raw source、自己決定要掃哪裡」的 agent。KAI-Mind scanner 必須先用 deterministic provider / bounded detail scan 收集 evidence，經過 `SecretMaskingService` 後組成 `MappingEvidencePacket`，再把這個 bounded context 餵給 AI。

### Evidence packet 與現有能力邊界

`MappingEvidencePacket` 在本任務中是未來要新增的 proposal input model，不是目前 canonical `ai_system_map.json` 已有欄位。它應該彙整既有 `Evidence`、`UnmappedComponent`、provider facts，以及 Task 21 detail scan 補出的 target-scoped signals，但 proposal 仍只代表待確認建議，不是 source of truth。

目前已完成的基礎能力如下：

- `SecretMaskingService` 已提供 shared masking path，支援 secret-like key/value、token-like pattern 與 JSON-like 遞迴遮蔽。實際遮蔽格式是 `[MASKED]` 或保留前後 4 碼的 `xxxx...yyyy`，不要在 contract 範例中固定寫成 `***MASKED_SECRET***`。
- `CodePatternProvider` 目前是 deterministic regex provider，會依 inventory 掃 source file、套用 rule catalog、產生 bounded masked snippet、line range 與 evidence id。
- `RiskHintService` 目前可針對 secret-like config key 產生 `secret_like_config_key_detected` 這類 heuristic risk hint，但尚未有 `HARDCODED_SECRET`、`CRITICAL`、`line_number` 這種專門 hardcoded secret finding model。
- repo 內雖有局部 AST 使用，例如 Chroma HTTP endpoint literal arg 解析，但尚未有通用 `CodePathScanService` 去彙整任意 imports / class / function / call signatures。

因此說明或測試資料若使用 Pinecone / OpenAI API key 例子，只能作為「未來 packet 應如何安全表達 evidence」的示意，不可暗示 scanner 已能用 AST 判定所有 hardcoded secret，或已能輸出完整 call graph。

### 看不到 call path 時怎麼辦

只給 imports、env var 名稱或前幾行 snippet 通常不足以判斷實際行為，尤其核心呼叫可能藏在檔案後段或 class method 裡。本任務第一版可以先從既有 evidence array 組出較薄的 packet；更完整的 call-like context 應由 Task 21 的 bounded detail scan 補齊。

Task 21 應負責：

- 只掃使用者選到的 target-related files。
- 擷取 imports、class/function signatures、decorators、call-like hints 與少量相鄰 masked snippets。
- 記錄 evidence ids、line range、rule ids、source file 與 context limit metadata。
- 標示 `best_effort` / truncated / uncertainty，避免把 static call-like hints 包裝成 runtime truth。

如果需要證明真實 runtime execution path，應導到 Task 22 opt-in query trace；Task 20/21 不可偷偷執行 target project、使用 `sys.settrace` 或呼叫 runtime endpoint。

### 為什麼 local AI 仍不能自己掃 repo

地端模型降低了雲端傳輸風險，但不代表可以把它設計成有權限的 repo-scanning agent。Task 20 的 local LLM 只能是 proposal helper，原因如下：

- 權限風險：一旦給 local LLM `read_file`、shell、network 或 project root traversal，它就從純函數變成 agent。repo 內 README、註解、fixture 或測試資料也可能含有 prompt injection，讓模型偏離原本任務。
- 不可重現：release-readiness gate 需要同一份 repo、同一組 deterministic rules 產生可追溯 facts。LLM output 可能因模型版本、sampling、prompt wording 或上下文順序而變動。
- Evidence 不可信：KAI-Mind 需要 `evidence_id`、file、line range、rule id、masked snippet。LLM 自掃容易編造不存在的 path、slot、edge 或 evidence id，不能直接進 canonical map。
- 長上下文退化：即使 local model 支援大 context，把整個 repo 塞進 prompt 仍會有 lost-in-the-middle、漏看中段細節、被雜訊稀釋的問題。
- 成本與 UX：地端模型逐檔讀整個 repo 慢、吃 RAM/GPU，且會把大量不相關 UI、test、log、template 放進 prompt；deterministic provider 先篩掉 99% 雜訊更穩。
- Secret 最小化：local 不等於無外洩。proposal JSON、logs、GUI、debug trace 都是 downstream leakage surface，所以送進模型前仍必須先 bounded + masked。

因此本任務採用 hybrid flow：deterministic scanner / Task 21 detail scan 先收斂 evidence，`SecretMaskingService` 先遮蔽，再交給 optional LLM 產生 pending proposal。LLM 產物只可作為候選，不可作為 source of truth。

### 外部參考與取捨

- Semgrep / CodeQL：參考其「先用 rules / semantic query 產生可追溯 finding，再做後續 triage」的精神；不要在 Task 20 引入大型 SAST runtime，也不要讓 AI 取代 deterministic findings。
- LangGraph HITL：參考 interrupt / resume / checkpoint 的產品語意，也就是 proposal 先 pending、等待使用者 accept/edit/reject；不需要把 Task 20 實作成 LangGraph workflow。
- Microsoft Presidio：參考 analyzer/anonymizer 的資料流觀念；目前不要直接引入核心依賴，因為 KAI-Mind 現階段主要處理 code/config/report secrets，已由 `SecretMaskingService` 負責。若未來要掃醫療個資或 report PII，再評估是否擴充。
- OpenAI Structured Outputs / JSON Schema 類型約束：參考 structured output + schema validation 的作法；即使 local LLM 不支援 strict structured output，也必須在 KAI-Mind 端用 Pydantic / JSON Schema 做最終驗證。
- OWASP LLM Top 10 / NIST SSDF：參考 prompt injection、sensitive information disclosure、excessive agency、secure-by-design、least privilege 與 auditability 原則。

### 開源 RAG / LLM 專案設定模式校正

已查 R2R、LangChain、LlamaIndex、Dify 的設定方式後，本任務採用以下分界：

- 可調 runtime provider 設定放 TOML / env：model、endpoint、timeout、temperature、top_p、max_tokens、stream、enable_thinking。這類設定類似 R2R 的 `[completion.generation_config]`，或 LangChain / LlamaIndex 對 LLM model、temperature、request timeout 的設定。
- Secret 不放 TOML：`NVIDIA_API_KEY` 只走 `.env` / process env，且 hosted NVIDIA provider 還需要 `KAI_MIND_ENABLE_NVIDIA_NIM_PROPOSALS=true` 才啟用。
- Output schema / safety bounds 不放 TOML：`MappingCandidate` 的 `label`、`rationale`、`flow_hint` 長度、candidate 數量、evidence id 數量、suggested edge 數量是 API contract 與安全邊界，集中成 Python constants 並由 Pydantic model 產生 JSON Schema。
- Provider TOML loader 仍會檢查 runtime 設定範圍，例如 timeout、temperature、top_p、max_tokens，避免 TOML 設成不合理值造成 hanging request 或超大 response。

取捨理由：R2R / Dify 類產品會讓 ingestion chunk size、LLM generation、timeout 這些部署參數可調；但 KAI-Mind 的 proposal candidate 是前後端 API contract，也是防止 LLM output bloat / leakage 的 safety guardrail。若把這些 output bounds 變成 TOML，部署時一個錯誤設定就可能放寬 AI output 邊界，和 Task 20 的 bounded proposal 承諾衝突。

### NVIDIA NIM / Gemma 4 31B 查證與整合邊界

使用者提到的 NVIDIA Platform / Gemma 4 31B 可以作為 Task 20 的「optional proposal provider」測試 adapter，但文件必須修正幾個容易誤解的點：

- 官方模型 ID 應寫成 `google/gemma-4-31b-it`，不是只寫「Gemma 4 31b」。NVIDIA API reference 顯示該模型的 inference endpoint 是 `POST https://integrate.api.nvidia.com/v1/chat/completions`，request body 需要 `model` 與 `messages`。
- NVIDIA hosted NIM API 是外部雲端 endpoint，不是 KAI-Mind 本機模型。若用它解決本機 GPU/VRAM 不足，應命名為 `NvidiaNimProposalProvider` 或 `HostedNimProposalProvider`，不要把它寫成 `LocalLlmProvider` 的唯一實作。
- `NVIDIA_API_KEY=nvapi-...` 可以作為 explicit opt-in 憑證，但 default scan/proposal flow 必須在沒有 key、401、quota、timeout、202 pending、422 validation 或 500 provider error 時直接 deterministic fallback。不得讓 proposal endpoint 因外部服務不可用而中斷。
- NVIDIA NIM API 雖有 OpenAI-compatible chat completions 形狀，但不同 model 的可用 message role / 參數可能不同；Gemma 4 31B reference 顯示 `messages` role 以 `user` / `assistant` 為主，且有 `chat_template_kwargs`。因此 provider 不應假設所有模型都支援 strict structured output 或同一組 OpenAI 參數；KAI-Mind 端仍要用 Pydantic schema 做最終驗證。
- NVIDIA Developer Program hosted endpoint 適合 prototype / development / testing；production 使用 NVIDIA NIM 需要另行確認 NVIDIA AI Enterprise 授權、資料處理政策、retention、region、audit 與成本。Phase 20 不把 hosted NIM 設為 production default。
- 即使用 NVIDIA hosted NIM，也只能送 masked `MappingEvidencePacket`、allowed slots/extensions 與 output schema summary；不得送 project root、raw source、未遮蔽 secret、raw prompt logs，或讓 provider 有任何 repo traversal / shell 權限。

實作建議：

- Core service 只依賴 `MappingProposalProvider` protocol，不依賴 NVIDIA SDK 或 HTTP payload。
- `NvidiaNimProposalProvider` 放在 provider/infrastructure 層，用 `httpx.AsyncClient` 或等價 HTTP client，設定短 timeout，將網路/HTTP/JSON parse/validation error 轉成 provider unavailable / invalid output reason。
- NVIDIA provider 可以支援最多一次 validation retry，但 retry body 只包含 validation error summary、同一份 masked packet 與 schema summary。
- 測試只使用 fake provider 或 mock HTTP client，不呼叫真實 NVIDIA endpoint，不需要真實 `NVIDIA_API_KEY`。

推薦邊界：

- Python scanner 負責找檔案、讀檔、抽取 imports / class / function / call-like signals、遮蔽 secret。
- `MappingProposalService` 負責把 masked `MappingEvidencePacket` 轉成 pending proposal。
- Optional local LLM 只能像 stateless function 一樣接收 bounded input / 回傳 structured JSON，不可擁有 `read_file`、shell、network、repo traversal 等工具權限。
- Local LLM unavailable、輸出不合法或 schema validation 失敗時，必須退回 deterministic fallback，不可讓 scan 掛掉。
- LLM validation retry 最多一次；重試 input 只能包含 validation error summary、原始 masked packet 與 allowed schema，不可加入 raw source 或 project root。
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
- 若 local LLM output validation 失敗，可做最多一次 bounded retry；retry 後仍失敗就記錄 AI unavailable / invalid output reason，改用 deterministic fallback。
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
9. 實作 LLM validation retry guard：最多一次，且 retry prompt 不得包含 raw source / project root / unmasked evidence。
10. 實作 proposal validation。
11. 實作 accept -> manual mapping draft。
12. 建立 FastAPI proposal routes，所有 decision 都必須走 `MappingProposalService` / `ManualMappingService`。
13. API response 要讓前端能渲染候選卡片：label、target、recommendation_level/rank、rationale、evidence ids、uncertainty_reason、available actions。
14. 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`。
15. 測試：proposal pending、不進 canonical map、accept 後需 validation；proposal 不會讓 unmapped component 直接出現在 baseline `Flow.edges`；web route 不會在 AI unavailable 時讓 scan 失敗；local LLM provider 不會收到 raw project root 或 unmasked evidence；`confidence` output 被拒絕；LLM hallucinated evidence/slot 被拒絕後 fallback。

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
- LLM 回傳的 `evidence_ids`、target slot、extension reference、suggested edge endpoint 都必須存在於 input packet 或 allowed target set；不存在者視為 hallucinated reference 並拒絕。
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
- 不要把 LangGraph / Presidio / Semgrep / CodeQL 當成 Task 20 必要依賴；本任務只採用其設計原則：HITL、anonymization、rule/query-first findings、structured validation。
- 參考依據：設計文件明確要求 AI 只可做 proposal；Stage 5/6 的 AI 只能輔助 mapping/rationale wording。
- Query router / custom router 這類候選 extension 不屬於 Task 14 baseline flow；proposal 只能協助使用者確認，confirmed 後由 Task 19 manual mapping store 和後續 normalize/replay 階段生效。
- Task 21 可以產生更豐富的 `MappingEvidencePacket`；Task 22 的 runtime trace 只能在使用者 opt-in 後提供補充 evidence，不得變成本任務預設行為。

## 參考資料
- Semgrep rules / pattern syntax: https://semgrep.dev/docs/running-rules/ , https://semgrep.dev/docs/writing-rules/pattern-syntax
- CodeQL code database + query model: https://codeql.github.com/docs/codeql-overview/about-codeql/
- LangGraph human-in-the-loop interrupts: https://docs.langchain.com/oss/python/langgraph/human-in-the-loop
- Microsoft Presidio anonymization flow: https://microsoft.github.io/presidio/text_anonymization/
- OpenAI Structured Outputs: https://platform.openai.com/docs/guides/structured-outputs
- NVIDIA NIM LLM APIs: https://docs.api.nvidia.com/nim/reference/llm-apis
- NVIDIA Gemma 4 31B IT inference reference: https://docs.api.nvidia.com/nim/reference/google-gemma-4-31b-it-infer
- NVIDIA Gemma 4 31B IT model card: https://docs.api.nvidia.com/nim/reference/google-gemma-4-31b-it
- NVIDIA NIM product / licensing FAQ: https://docs.api.nvidia.com/nim/docs/product
- R2R GitHub / generation config examples: https://github.com/SciPhi-AI/R2R , https://raw.githubusercontent.com/SciPhi-AI/R2R/main/py/core/configs/full_ollama.toml
- R2R self-hosting agent configuration: https://r2r-docs.sciphi.ai/self-hosting/configuration/agent
- LangChain model parameters / structured output: https://docs.langchain.com/oss/python/langchain/models
- LlamaIndex Settings / request timeout pattern: https://docs.llamaindex.ai/en/v0.10.20/module_guides/supporting_modules/service_context_migration.html
- Dify self-host environment variables / indexing and timeout settings: https://docs.dify.ai/en/self-host/configuration/environments
- OWASP Top 10 for LLM Applications: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- NIST Secure Software Development Framework: https://csrc.nist.gov/Projects/ssdf

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
