# Phase 1 Epic 2-7 Roadmap Solidation Report

## Executive Summary

**審查範圍**：GitHub Epic 2-7（issue [#3](https://github.com/1104030360/Systograph/issues/3)-[#8](https://github.com/1104030360/Systograph/issues/8)），對照 `check1.md` 訂定的審查準則與 `.cursor/rules/linus_torvalds.mdc` 的 5 層分析法（資料結構 → 特殊情況 → 複雜度 → 破壞性 → 實用性）逐一檢視。

**頂層結論**：6 個 Epic 全數判定為 **Refine existing issue**——沒有任何 Epic 需要重新定位（滑向 chatbot / RAG-builder / 完整 observability platform / 企業安全掃描 / model-serving 平台）或拆成全新 issue。整體 roadmap 方向正確，本階段修正集中在三件事：(1) 把 Epic 1 已經做出的「預先承諾」與 Epic 2-7 的範圍明確連結；(2) 修正範圍措辭中與既有實作進度不符的低估/高估；(3) 釐清 Epic 之間（Epic 2↔5、Epic 6↔7）原本模糊的分工界線。

**5 個跨 Epic 關鍵發現**：
1. **Epic 1 的 3 個「預告」未被引用**：`recommended_next_check_rules.toml` 已存在 `runtime_readiness`（→Epic 2）、`privacy_exposure`（→Epic 3）、`rag_knowledge_trust`（→Epic 5）三條規則，原始 body 均未提及「本 Epic 正是在履行這個承諾」——重寫後已補上引用，讓 Epic 1 與 Epic 2/3/5 的敘事連起來。
2. **Epic 3、Epic 7 的既有進度被低估**：Epic 3 範圍中過半的偵測規則（`risk_hint_rules.toml` 5 條規則 + `secret_masking_service`）已存在；Epic 7 的「Codex review / `AGENTS.md`」項目已有實質文件且已被 CLAUDE.md 引用為強制流程——兩者在原 body 中都被寫成「待建」，應改為「整理/延伸既有成果」。
3. **Epic 6 ↔ Epic 7 的「GitHub Action」用詞重疊已釐清**：Epic 6 完成條件第三項與 Epic 7 範圍都寫「GitHub Action(s) integration」，容易讓人誤判工作重複或已涵蓋。重寫後分工為：Epic 6 提供 `systograph gate --ci` 的 CLI/JSON/exit-code 合約 + 通用範例；Epic 7 負責打包成可發布、可重用的 GitHub Action，且應排在 Epic 6 合約穩定後開始。
4. **Epic 5 的複雜度量級不對稱已拆分**：原範圍把 5 項機械式檢查（連線查詢等級）與 1 項「Unsupported claims detection」（LLM-as-judge 評測等級）並列，後者已移至 Epic 5 body 的 Follow-Up Candidates，作為獨立排期項目記錄（未另開新 issue），讓核心 5 項可以不依賴即時 LLM 呼叫先交付。
5. **Epic 4 是唯一真正 0% 起點、且是「Agent」識別的關鍵 Epic**：`code_pattern_rules.toml` 確認目前完全沒有 agent/tool-call 偵測規則，也是 Epic 2-7 中唯一沒有 Epic 1 鉤子的 Epic；本階段釐清其「靜態程式碼模式偵測」vs.「動態 audit log / policy engine」的範圍模糊點，並將是否需要 `agent_tools` schema 概念列為 Follow-Up Candidate。

**執行紀律**：本階段僅修改 GitHub issue body（6 個 issue 標題全部保留不變）與 `docs/work/Timmy/schedule/fable-5/solidate-MyPlan/` 下的文件，**未修改任何功能程式碼**——`git status --short` 與 `git diff --check` 已驗證。6 筆 `gh issue edit` 均成功並經 `gh issue view` 重新確認；2026-06-13 另以 GitHub MCP 補正 #7 的 CLI 現況清單（標題不變、新區塊段落存在）。過程中無 Blocked 項目，詳見 Final Gap Audit。

## Inputs Checked

| Input | 類型／位置 | 用途 |
|---|---|---|
| `check1.md`（761 行） | 任務指令，`solidate-MyPlan/solifate-prompt/check1.md` | 本階段審查範圍、9 大準則、deliverable 結構與約束條件來源 |
| `phase1-solidate.md`（598 行） | 規劃文件，`solidate-MyPlan/plan/unfinish/phase1-solidate.md` | Phase 1 整體規劃背景 |
| `.cursor/rules/linus_torvalds.mdc`（224 行） | Review persona 規則 | Decision 小節 5 層分析法與輸出格式（核心判斷／關鍵洞察／Linus式方案）、zh-TW 用詞對照 |
| `principles.md`（354 行） | 外部最佳實踐參考 | Ragas/DeepEval、LLM-as-judge 定位、OWASP LLM Top 10 等外部研究引用基礎 |
| GitHub Issue #2（Epic 1） | `gh issue view 2` | Epic 1 基準狀態，作為 Epic 2-7 上游依賴與既有鉤子來源 |
| GitHub Issue #3-#8（Epic 2-7，修改前） | `gh issue view N` | 原始 body 結構與內容，Epic Review Matrix 的 Repo Reality/Issue Alignment 分析對象 |
| GitHub Issue #3-#8（Epic 2-7，修改後） | `gh issue view N`（`/tmp/epicN_after.json`） | 驗證 `gh issue edit` 套用成功、標題未變、新區塊段落存在 |
| `src/systograph/core/rules/recommended_next_check_rules.toml`（24 行，全文讀取） | 規則定義 | Epic 1 對 Epic 2/3/5 的 3 個預先承諾規則 |
| `src/systograph/core/rules/risk_hint_rules.toml`（84 行，全文讀取） | 規則定義 | 12 條規則，5 條對應 Epic 3、1 條（`missing_required_slot`）對應 Epic 5 |
| `src/systograph/core/rules/code_pattern_rules.toml`（13 條規則） | 規則定義 | 確認 Epic 4 範圍的 agent/tool-call 偵測模式目前完全不存在 |
| `src/systograph/core/templates/rag-core-v1.json` | RAG 樣板 | 13 個 slot 定義，含第 79 行 `guardrails` slot（Epic 4 命名衝突檢查對象） |
| `web/app.py` | 後端 router 註冊 | 確認 8 個 router 已掛載；CLI 僅有 `map`/`validate-map`/`trace`，無 `gate` |
| `frontend/src`（`rg` 搜尋結果） | 前端原始碼 | 確認 project scan flow、detail-proposal flow 尚未在前端串接 |
| `CLAUDE.md`（專案層級） | 專案慣例 | 產品定位（Release Readiness Gate）、核心設計原則、Workflow Conventions |
| `git status --short` / `git diff --check` | 終端指令輸出 | 驗證本階段未修改功能程式碼、無空白字元錯誤 |

## Verification Commands And External Sources

本段為 2026-06-13（Asia/Taipei）重新查證補記，用來把本報告的結論對齊目前 repo 與 GitHub 現況。

| Check | Command / source | Result |
|---|---|---|
| GitHub auth | `gh auth status` | 已登入 `1104030360`，具 `repo` scope |
| Epic issue inventory | `gh issue list --repo 1104030360/Systograph --state open --limit 100 --json number,title,state,labels,assignees,updatedAt` | Epic 2-7 仍為 issue #3-#8，皆為 OPEN |
| Epic issue bodies | `gh issue view 3..8 --repo 1104030360/Systograph --json number,title,state,body,url,updatedAt` + GitHub MCP `_update_issue` for #7 CLI-current-reality correction | 6/6 issue 皆已套用 `Goal` / `Current Reality` / `Scope` / `Non-Goals` / `Acceptance Criteria` / `Evidence To Preserve` / `Follow-Up Candidates` 結構 |
| Plan inventory | `find docs/work/Timmy/schedule/plan/finish -maxdepth 1 -type f`、`find docs/work/Timmy/schedule/plan/unfinish -maxdepth 1 -type f`、`find docs/work/Hardy/schedule/plan -maxdepth 3 -type f` | Backend finished/unfinish 與 Hardy frontend plan 狀態符合本報告 baseline |
| Backend surface | `rg -n "include_router|MapBuildService|ProjectScanService|ScanBoundaryReviewService|MappingProposalService|DetailScanService|QueryTraceService|InMemorySessionStore" src/systograph docs/API-GUIDE.md scripts tests` | 確認 web factory 掛載既有 services/routes；`InMemorySessionStore` 仍是 session state 邊界 |
| Frontend surface | `rg -n "loadApiViewerPayload|loadSampleViewerPayload|EventSource|detail_scan_result_sample|mapping_proposal_result_sample|project_id|scan_id|boundary|proposal|createDetailScan|createMappingProposal" frontend/src frontend/API_CONTRACT.md docs/work/Hardy` | 確認 project scan / boundary decision / detail scan / mapping proposal 仍未形成完整前端閉環 |
| Document hygiene | `git diff --check -- docs/work/Timmy/schedule/fable-5/solidate-MyPlan`、`rg -n "[ \t]+$" docs/work/Timmy/schedule/fable-5/solidate-MyPlan/...` | 無 trailing whitespace 或 patch hygiene 錯誤 |
| Forbidden overclaim check | `rg -n "production-ready|已完成|persistent|database|chat 已完成|scan history|always_skip|metadata_only|完整 observability|企業級資安|model serving" docs/work/Timmy/schedule/fable-5/solidate-MyPlan/todo docs/work/Timmy/schedule/fable-5/solidate-MyPlan/report` | 命中皆落在 missing / deferred / Non-Goals / Rejected Goals 語境，未發現過度宣稱 |
| External best-practice source | `docs/work/Timmy/schedule/fable-5/check-list/principles.md`（2026-06-13 重新讀取） | 作為 RAG evaluation、LLM-as-judge、OWASP LLM、AI infra / AI application 邊界的外部來源索引；下方 `Live External Research Refresh` 補上本輪重新查證的外部來源與查詢日期 |

### Live External Research Refresh

補查時間：2026-06-13（Asia/Taipei）。外部資料只用來校準 roadmap / issue wording，不取代 repo 實際 code、docs、tests、scripts 作為完成度證據。

| Topic | Source checked | Evidence used in this review |
|---|---|---|
| Qdrant runtime readiness | [Qdrant Monitoring & Telemetry](https://qdrant.tech/documentation/ops-monitoring/monitoring/) | Qdrant 官方文件列出 `/healthz`、`/livez`、`/readyz`，支撐 Epic 2 / Epic 5 要共用 vector store 連線層，但 health 與 collection content 是不同檢查層級。 |
| Ollama local runtime probe | [Ollama List models API](https://docs.ollama.com/api/tags) | `GET /api/tags` 是可列出本機模型的官方 API，支撐 TODO 中「實作前確認 Ollama health endpoint 慣例」的 follow-up，而不是在 issue body 直接寫死非官方 health path。 |
| LLM security taxonomy | [OWASP Top 10 for LLMs and Gen AI Apps 2025](https://genai.owasp.org/llm-top-10/) | OWASP 2025 將 Prompt Injection、Sensitive Information Disclosure、Excessive Agency 等列為主要風險，支撐 Epic 3 / Epic 4 的 privacy、tool permission、auditability 邊界。 |
| Agent/tool security | [MCP Security Best Practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices) | MCP 官方 security best practices 涵蓋 confused deputy、SSRF、session hijacking、scope minimization 等，支撐 Epic 4 只能做靜態 tool-risk 檢查，不應變成 runtime policy engine。 |
| RAG groundedness metric | [Ragas Faithfulness metric](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/) | Ragas 把 faithfulness 定義為 response claims 是否可由 retrieved context 支撐，支撐 Epic 5 將 groundedness evaluation 作為獨立 follow-up，而不是混進 5 項機械式 collection 檢查。 |
| RAG eval decomposition | [DeepEval RAG Evaluation Quickstart](https://deepeval.com/docs/getting-started-rag) | DeepEval 將 RAG 指標拆成 generator-focused 與 retriever-focused metrics，支撐本報告「不要用單一 trust score 當唯一閘門」的判斷。 |
| Agent safety research | [AgentDojo paper](https://arxiv.org/html/2406.13352v3) + [Agent-SafetyBench](https://arxiv.org/abs/2412.14470) | 近期 agent benchmark 強調 tool-calling、prompt injection、interactive environment 的安全挑戰，支撐 Epic 4 是 Agent 產品定位的關鍵 Epic，且不能只靠 prompt wording 覆蓋。 |
| AI eval / safety process | [OpenAI Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) + [OpenAI Safety best practices](https://developers.openai.com/api/docs/guides/safety-best-practices) | 官方文件強調 eval objective / dataset / metrics 與 prompt injection safety controls，支撐 Epic 5 / Epic 6 的 evaluation evidence 與 safety boundary。 |
| GenAI governance baseline | [NIST AI 600-1 Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) | NIST GenAI profile 作為治理與風險分類背景；本階段只用於確認 governance wording，不把 Systograph 擴大成企業級合規平台。 |

## Current Implementation Baseline

| # | 項目 | 狀態 | Evidence | 與 Epic 2-7 的關聯 |
|---|---|---|---|---|
| 1 | Backend L1 map build | DONE | `MapBuildService.build()` 串接 10 個服務，輸出驗證 `schemas/ai-system-map.v1.schema.json` | 所有 Epic 2-7 的輸出皆建立在 `ai_system_map.json` 之上 |
| 2 | Scan boundary decision（[#46](https://github.com/1104030360/Systograph/issues/46), Task24, CLOSED） | DONE | same-run-only gate；`scan_this_run`/`skip_this_run`，以 `target_path` + fingerprint 為 key，不持久化 | 確立「決策不持久化」模式，Epic 2/5/6 的 opt-in 產出物設計可參考此先例 |
| 3 | Manual mapping（[#41](https://github.com/1104030360/Systograph/issues/41), Task19, CLOSED） | DONE | `ManualMappingService`，使用者確認 slot 指派 | Epic 4 若新增 `agent_tools` 概念，需評估與既有 slot 指派流程的關係 |
| 4 | AI mapping proposal（[#42](https://github.com/1104030360/Systograph/issues/42), Task20, CLOSED） | DONE | `MappingProposalService`/`llm_proposal_provider`，masked `MappingEvidencePacket`，NVIDIA NIM opt-in + deterministic fallback | 確立「LLM 呼叫為 opt-in、有 fallback」模式，與 Epic 5 groundedness follow-up 的設計原則一致 |
| 5 | Detail scan（[#43](https://github.com/1104030360/Systograph/issues/43), Task21, CLOSED） | DONE | `DetailScanService`，L2/L3 component/code_path，僅限 target 範圍內、專案自身 Python 檔案 | Epic 4 的 agent-tool 程式碼模式偵測可能延伸自此 L2/L3 掃描層級 |
| 6 | Query trace（[#44](https://github.com/1104030360/Systograph/issues/44), Task22, CLOSED） | DONE | `QueryTraceService`，opt-in、單次、有時間戳記的黑箱 HTTP probe | Epic 2 runtime probe 的既有架構範本，Epic 2 重寫後 body 已引用 |
| 7 | Viewer API | DONE | `/api/map/build` + `/api/map`，無 `project_id` 的 viewer demo 流程；`app.py` 掛載全部 8 個 router | Epic 6/7 的 report/CI 輸出建立在此 API 層之上 |
| 8 | Frontend project scan flow | MISSING | `rg` 確認 `frontend/src` 中無 `project_id`/`scan_id`/`createScan` 等字串匹配 | 不在 Epic 2-7 直接範圍內，但是「使用者如何觸發 Epic 2-6 檢查」的前端缺口 |
| 9 | Frontend detail-proposal flow | MISSING | `rg` 確認無 `createDetailScan`/`createMappingProposal`/`listMappingProposals`/`decideMappingProposal`；`detail_scan_result_sample`/`mapping_proposal_result_sample` 僅出現在 `types.ts:111-112`、`DetailPanel.tsx:67-68` | 同上，前端串接缺口，非本階段範圍 |
| 10 | Persistent session-scan history | MISSING | 僅有 `InMemorySessionStore`；後續工作項目為 [#126](https://github.com/1104030360/Systograph/issues/126) | Epic 2/5/6 的「opt-in、有時間戳記的獨立產出物」設計需考慮與此既有限制的相容性 |
| 11 | Database-backed storage | MISSING | 同上，[#126](https://github.com/1104030360/Systograph/issues/126) | 同上 |
| 12 | OpenAPI generated SDK | MISSING | `viewerApi.ts` 為手寫 client，非自動生成 | 不在 Epic 2-7 直接範圍內 |
| 13 | Testing / eval / regression | PARTIAL | pytest 套件（unit/integration/contracts/cli/web/fixtures）覆蓋功能正確性；AI 輸出評測（Ragas/DeepEval 風格 groundedness）不存在 | 即 Epic 5「Unsupported claims detection」/ RAG Answer Groundedness Evaluation 待補的缺口 |

## GitHub Epic Inventory

| Epic | Issue | State | 標題 | 本階段處理 |
|---|---|---|---|---|
| Epic 1 | [#2](https://github.com/1104030360/Systograph/issues/2) | OPEN | [Epic 1] RAG System Map Builder：ai-system-map/v1、Viewer 與 Query Trace MVP | 不在本階段審查/編輯範圍（範圍為 Epic 2-7）；作為基準與上游依賴大量引用——`recommended_next_check_rules.toml` 的 3 個鉤子（`runtime_readiness`/`privacy_exposure`/`rag_knowledge_trust`）即源自此 Epic 既有實作 |
| Epic 2 | [#3](https://github.com/1104030360/Systograph/issues/3) | OPEN | [Epic 2] Runtime Readiness：Ollama、Docker、Native Services 與 Qdrant | 已審查 + 重寫 body，標題不變 |
| Epic 3 | [#4](https://github.com/1104030360/Systograph/issues/4) | OPEN | [Epic 3] Privacy & Exposure Guard：Secrets、Ports 與 Cloud Endpoints | 已審查 + 重寫 body，標題不變 |
| Epic 4 | [#5](https://github.com/1104030360/Systograph/issues/5) | OPEN | [Epic 4] Agent Tool Risk Guard：Tool Inventory、Permissions 與 Auditability | 已審查 + 重寫 body，標題不變 |
| Epic 5 | [#6](https://github.com/1104030360/Systograph/issues/6) | OPEN | [Epic 5] RAG Knowledge Trust：Collections、Metadata、Citations 與 Grounding | 已審查 + 重寫 body，標題不變 |
| Epic 6 | [#7](https://github.com/1104030360/Systograph/issues/7) | OPEN | [Epic 6] Release Report & CI Gate：Verdict、Evidence、JSON 與 Exit Code | 已審查 + 重寫 body，標題不變 |
| Epic 7 | [#8](https://github.com/1104030360/Systograph/issues/8) | OPEN | [Epic 7] Distribution & Integrations：Packaging、GitHub Action 與 Developer Workflow | 已審查 + 重寫 body，標題不變 |

備註：Epic N 對應 issue #(N+1)（Epic 1 = #2 … Epic 7 = #8），本階段確認此對應關係無誤；全部 7 個 issue 狀態皆為 OPEN。

## Epic Review Matrix

### Epic 2（#3）：Runtime Readiness — Ollama、Docker、Native Services 與 Qdrant

**Repo Reality**
- Implemented：0%。`code_pattern_rules.toml`（13 條規則）、`docker_image_rules.toml`、`dependency_manifest_rules.toml` 都只做「靜態偵測 Qdrant/Ollama 是否被當作依賴」，沒有任何 runtime health probe（HTTP GET health endpoint、Docker socket/CLI、`nvidia-smi`/`torch.cuda.is_available()`）程式碼。`DockerComposeProvider` 確認只解析 compose 檔內容，不連線 Docker daemon。
- Partial：`core/rules/recommended_next_check_rules.toml:1-7` 已存在 `runtime_readiness` 規則，`reason`＝「Static scan found runtime-dependent services, endpoints, or missing runtime-critical RAG slots」，`action`＝「Verify required services start successfully and configured endpoints are reachable」——這是 Epic 1 對 Epic 2 的「預先承諾」，但措辭是泛用的 services/endpoints，不是寫死的 Ollama/Docker/Qdrant 三個品牌。
- Missing：5 個範圍項目（Ollama health、Docker daemon/container、Qdrant health、App/Agent API endpoint、CPU/GPU/hybrid detection）全部 0%。`QueryTraceService`（#44, opt-in 黑箱 probe）是目前唯一的「runtime 對外請求」前例，但探的是專案自己的 API，不是基礎設施。
- Must not claim：目前 issue body 是規劃文字，沒有過度宣稱完成度的問題；但未來實作時不可把「compose 檔宣告了 qdrant image」這種 Epic 1 既有的靜態事實，重新包裝成 Epic 2 的「runtime health」證據——兩者是不同層級的 evidence。

**Issue Alignment**
- Accurate：「demo/交付/部署前確認 local AI stack 是否真的 ready」與產品定位（Release Readiness Gate）高度一致，方向正確。
- Missing product goal：沒有提到本 Epic 是在「履行」Epic 1 已經在 `recommended_next_check_rules.toml` 裡對使用者做出的 `runtime_readiness` 提示——應該明確連結，讓兩個 Epic 的敘事連起來（"Epic 1 說『你該檢查這個』，Epic 2 就是那個檢查"）。
- Missing AC：完成條件只列 healthy/missing/degraded/unknown 四態，缺少「這個 component 根本不在這個專案的系統圖裡（not applicable）」狀態——例如純 OpenAI + pgvector 專案，Ollama/Qdrant 不適用，不該被標成 missing（暗示「應該有但沒有」）。
- Missing AC：沒有說明 runtime readiness 結果存放在哪裡——是併入 `ai_system_map.json` 的靜態 component evidence，還是獨立、有時間戳記的 opt-in 產出物？這是 source-of-truth 邊界，必須在 Scope/Non-Goals 講清楚，否則容易把「某個時間點的 runtime 狀態」誤植進「靜態系統圖」。
- Scope conflict：標題把技術寫死成「Ollama、Docker、Native Services 與 Qdrant」三個品牌，但 `rag-core-v1` 樣板的 `vector_store`/`llm`/`embedding_model` slot 本來就支援多種 provider（`tests/fixtures/rag_projects/pgvector_openai_rag` 即為一例）。標題寫死品牌，容易讓人誤以為這個產品只支援這三種技術。

**User/Adoption Value**
- 對「demo 前確認 stack 真的活著」這個情境，價值非常高，是把產品從「靜態 linter」拉到「release gate」的關鍵差異化功能。
- Still weak：目前敘事是「檢查 Ollama/Docker/Qdrant」，但對「我的 stack 不是這三個」的使用者（例如 OpenAI API + pgvector、無 Docker）沒有交代——應該改成「根據系統圖偵測到的 runtime 依賴去檢查」，Ollama/Docker/Qdrant 作為第一批具名範例，而不是全部範圍。

**Product Positioning / Source-of-Truth Cross-Check**
- 不是 chatbot／RAG-builder／企業安全掃描／model-serving，方向正確。
- 與「完整 observability platform」的邊界要小心：「CPU/GPU/hybrid state detection」＋「App/Agent API endpoint check」如果被寫成「持續監控」，就會滑向 observability platform。需要在 Non-Goals 寫明：這是 point-in-time 的 gate 檢查，不是常駐監控/APM。
- Source-of-truth：runtime readiness 結果 vs. `ai_system_map.json`（靜態）、vs. `QueryTraceService`（既有 opt-in runtime probe 前例）、vs. Epic 5 的 Qdrant collection 檢查（Epic 2 查「Qdrant 活著嗎」，Epic 5 查「Qdrant collection 裡有什麼」——層級不同但都需要連 Qdrant，屬於跨 Epic 協調事項，記錄於 Follow-Up Candidates，不是重複範圍）。

**Decision**
【核心判斷】✅ 方向正確：這是 Epic 1 已經預告、且是產品核心賣點（"靜態設定 ≠ 真的能跑"）的必要功能。
【關鍵洞察】真正的問題不是「要不要做 Epic 2」，而是「Epic 2 目前用品牌名稱（Ollama/Docker/Qdrant）定義範圍，但 Epic 1 用泛用詞（services/endpoints）定義對應的 recommended-check——兩者措辭層級不一致，會讓 Epic 2 看起來比 Epic 1 的承諾窄，也比 rag-core-v1 的多 provider 模型窄」。
【Linus式方案】保留 Ollama/Docker/Qdrant 作為「第一批具名、有完整證據鏈的範例」，但用「根據系統圖偵測到的 runtime 依賴」作為範圍的主敘事；新增 Non-Goals（非常駐監控、非通用 infra 工具、非 Docker socket 管理）；新增「not applicable」狀態；明確 runtime readiness 結果是獨立、有時間戳記的 opt-in 產出物，遵循 QueryTraceService 既有的 opt-in 模式。
Outcome：Refine existing issue。

---

### Epic 3（#4）：Privacy & Exposure Guard — Secrets、Ports 與 Cloud Endpoints

**Repo Reality**
- Implemented（比看起來多）：`core/rules/risk_hint_rules.toml` 已經有 5 條與本 Epic 直接對應的規則：`docker_published_port_exposure`（network_exposure）、`external_provider_detected`（external_provider）、`secret_like_config_key_detected`（secret_config）、`chroma_server_published_port`（vector_store_network_exposure）、`chroma_local_persistence_detected`（local_persistence）。再加上 CLAUDE.md 列出的 `secret_masking_service`——「不顯示完整 secrets，只顯示 key type 與 evidence location」（完成條件第二項）**已經是現有的安全機制**，不是待建功能。
- Partial：「Docker port binding check」對 Chroma（`chroma_server_published_port`）與通用 Docker（`docker_published_port_exposure`）已有規則，但對 Ollama（預設 port 11434）、Qdrant（6333/6334）、Open WebUI（8080/3000）等「常見 local AI ports」沒有具名規則——這正是範圍第一項點名要做、但目前缺的部分。
- Missing：「Data Leaves Device risk report」這個*彙總視圖*本身不存在——現有 5 條 risk_hint 是分散在各 component 上的個別提示，沒有被彙整成「localhost-only / LAN-exposed / possible external exposure / unknown」四象限的單一報告。
- Must not claim：未來實作不可把「重新發明一套 secret scanner」當作本 Epic 的主要工作量——`secret_masking_service` 與 `secret_like_config_key_detected` 已存在，本 Epic 在這塊的真正工作是「彙整 + 補 Ollama/Qdrant/OpenWebUI 具名 port 規則」，不是從零開始。

**Issue Alignment**
- Accurate：「分享/demo/部署前偵測 privacy 與 exposure 風險」與定位一致，方向正確。
- Missing product goal：body 完全沒提到 Epic 1 的 `risk_hint_rules.toml` 已經覆蓋了範圍中一半以上的偵測規則，也沒提到 `recommended_next_check_rules.toml:9-15` 的 `privacy_exposure` 規則（`reason`＝「Static scan found potential data egress, published port, secret-like config, or local persistence evidence」）——這正是 Epic 1 對 Epic 3 的預告，應該明確連結。
- Missing AC：「Data Leaves Device risk report」要把現有 risk_hint 的 `type`（`network_exposure`/`external_provider`/`secret_config`/`vector_store_network_exposure`/`local_persistence`）對應到「localhost-only/LAN-exposed/possible external/unknown」四個分類，這個 mapping 規則本身就是一個可驗收的產出，但目前完成條件沒寫到。
- Scope conflict：無重大衝突，但應該明確引用 Epic 1 既有的 risk_hint 規則，避免被誤讀為「從零打造一套掃描器」。

**User/Adoption Value**
- 高：「我準備 demo 的東西是不是不小心對外網開了 port、洩漏了 API key」是 local AI 開發者真實會擔心的場景（對應 Qdrant/Ollama/ChromaDB 被掃到開放在公網的真實新聞案例）。
- Still weak：目前敘事把「port scanner」「secret scanner」「cloud fallback detection」「Data Leaves Device report」並列成 5 個平行項目，但對使用者而言真正有價值的是「Data Leaves Device report」這個*單一彙總畫面*——其他 4 項其實是這個畫面的*資料來源*，body 應該把「報告」標示為主產出，其餘為既有/待補的資料來源。

**Product Positioning / Source-of-Truth Cross-Check**
- 與「企業安全掃描工具」的邊界：「port exposure scanner」+「secret scanner」聽起來像 mini security scanner。差異化在於：只報告「系統圖裡已偵測到的元件」相關的 exposure 訊號，不是對任意 host/port 做主動掃描——這點必須寫進 Non-Goals。
- Source-of-truth：「Data Leaves Device risk report」應定義為「對既有 `risk_hints` 的彙總投影（projection/aggregation）」，不是新的平行偵測系統或新的 schema 欄位。

**Decision**
【核心判斷】✅ 方向正確，且比 Epic 2 更接近「已經做了一半」的狀態。
【關鍵洞察】真正的問題不是「要不要做 Epic 3」，而是「body 把已經存在於 Epic 1（5 條 risk_hint 規則 + secret_masking_service）的成果，描述成跟其他全新項目並列的待辦清單，會讓人低估完成度、也會讓實作者誤判工作量（甚至重做）」。
【Linus式方案】把 body 改寫成「彙總既有 risk_hints → Data Leaves Device report（主產出）＋ 補 Ollama/Qdrant/OpenWebUI 具名 port 規則（範圍中唯一真正缺的偵測）」；新增 Non-Goals（不是通用網路安全/弱點掃描器，不對任意 host 做主動掃描）；引用 `privacy_exposure` recommended-check 作為本 Epic 履行的承諾。
Outcome：Refine existing issue。

---

### Epic 4（#5）：Agent Tool Risk Guard — Tool Inventory、Permissions 與 Auditability

**Repo Reality**
- Implemented：0%。`code_pattern_rules.toml`（13 條規則）對 `tool|agent|subprocess|shell|os\.system|smtplib|requests\.|httpx\.` 的 grep 結果為空——目前完全沒有 agent tool-call 偵測規則。這是 Epic 2-7 中唯一「真正從零開始、且 Epic 1 沒有預先留下任何 recommended-check 鉤子」的 Epic（`recommended_next_check_rules.toml` 只有 `runtime_readiness`/`privacy_exposure`/`rag_knowledge_trust` 三條，對應 Epic 2/3/5，沒有對應 Epic 4 的）。
- Partial：`rag-core-v1` 樣板有一個 `guardrails` slot（`core/templates/rag-core-v1.json:79`），但這個 slot 描述的是 RAG 回應層的 content guardrails（例如輸出內容過濾），與 Epic 4 講的「agent tool 權限/風險」是不同概念——兩者用了相近的詞「guardrails」，有命名上互相干擾的風險，但**不是同一件事，也沒有重複實作**。
- Missing：全部 5 個範圍項目（tool inventory、permission risk assessment、tool call log availability check、approval/policy presence check、OWASP Excessive Agency 對齊）皆為 0%。
- Must not claim：body 為規劃文字，無過度宣稱問題。

**Issue Alignment**
- Accurate：「評估 AI Agent tools 是否足夠安全」直接對應產品名稱「AI Agent / RAG Release Readiness Gate」中的 **Agent** 那一半——Epic 1/2/3/5/6 大多偏 RAG/infra，Epic 4 是目前唯一明確扛起「Agent」面向的 Epic，對產品識別很重要。
- Missing product goal：沒有明確說明「為什麼是這 5 個風險類別（shell/file/email/database/workflow triggers）」——但這份清單本身已經很具體、可對應到 `code_pattern_rules.toml` 的偵測模式（`subprocess`/`os.system`、`open(...,'w')`/`os.remove`、`smtplib`、SQL `INSERT/UPDATE/DELETE`、webhook/Action triggers），應該把這個對應關係寫進 Evidence To Preserve，作為可驗收的具體依據。
- **關鍵模糊點**：「Tool call log availability check」與「Approval / policy presence check」——是靜態（程式碼裡是否存在 logging/approval 的程式碼模式，符合現有 L3 code_path scan 模型、read-only）、還是動態（讀取實際 audit log 內容或連接 policy engine，會打破「read-only 掃描專案目錄」的邊界，且涉及 audit log 裡可能有使用者資料的隱私問題）？「availability check」這個用詞本身比較像「程式碼裡有沒有這個機制存在」（靜態），但 body 沒有明確排除動態解讀。這個模糊必須在 Non-Goals 寫死：只做「程式碼路徑是否包含 logging/approval 結構」的靜態偵測，不讀取實際 audit log 內容、不連接 policy engine。
- Missing AC：「Agent tool inventory」的結果要放在 `ai_system_map.json` 的哪裡？目前 `rag-core-v1` 樣板是 RAG 專屬的 13 個 slot，沒有「agent tools」這個概念。這可能需要 schema 層級的擴充（例如新增 `agent_tools` 陣列），但這個決定太大，不該由本 Epic 的 body 自己決定——應該標記為 Follow-Up Candidate，留給實作時的 schema 設計討論。

**User/Adoption Value**
- 高，且具差異化：principles.md 引用的 RAG 評測工具（Ragas/DeepEval）聚焦於檢索/回答品質，沒有覆蓋「agent tool 權限稽核」——這是目前 RAG 評測生態系統的空白，也正是 Systograph 名稱裡「Agent」的真正落地之處。
- Still weak：目前清單是「能辨識哪些高風險 tools」，但沒有交代「辨識到之後，使用者看到的是什麼」——應該明確：辨識結果＝風險清單＋每項風險對應的 evidence（檔案/行號/程式碼模式），讓使用者知道「為什麼這段程式碼被標成 file-write 風險」。

**Product Positioning / Source-of-Truth Cross-Check**
- 與「企業級 policy/audit 平台」的邊界：「approval/policy presence check」如果做成「讀取/管理 policy 規則」，就會滑向企業 IAM/policy engine 產品——必須限定在「偵測程式碼裡是否存在這類機制的痕跡」。
- `guardrails`（rag-core-v1 RAG content slot）vs. Epic 4 的 "tool permission guardrails"——命名相近但語意不同，建議 Epic 4 body 使用「tool permission / tool risk」而非單獨的「guardrails」，避免讀者把兩者混為一談。

**Decision**
【核心判斷】✅ 方向正確，且是目前 Epic 2-7 中對「Agent」產品定位最關鍵、也是唯一真正 0% 起步（無 Epic 1 鉤子）的 Epic。
【關鍵洞察】真正的問題不是「這個 Epic 該不該做」，而是「『tool call log availability check』與『approval/policy presence check』這兩句話，靜態讀法和動態讀法會導致完全不同的架構決策（read-only 程式碼掃描 vs. 連接外部 audit/policy 系統），而 body 目前沒有排除動態讀法，等於把一個架構邊界問題留給未來的實作者自己猜」。
【Linus式方案】Non-Goals 明確寫死「靜態程式碼模式偵測，不讀取 runtime audit log、不連接 policy engine」；Evidence To Preserve 列出 5 大風險類別 → `code_pattern_rules.toml` 偵測模式的對應表；schema 是否需要新增 `agent_tools` 概念列為 Follow-Up Candidate；body 中避免單獨使用「guardrails」一詞以免與 rag-core-v1 的 RAG content guardrails slot 混淆。
Outcome：Refine existing issue。

---

### Epic 5（#6）：RAG Knowledge Trust — Collections、Metadata、Citations 與 Grounding

**Repo Reality**
- Implemented：0% 的 runtime 部分（見下），但 Epic 1 有兩個明確鉤子：`core/rules/recommended_next_check_rules.toml:17-23` 的 `rag_knowledge_trust` 規則（`reason`＝「Static scan found incomplete evidence for RAG knowledge source, retrieval, citation, guardrails, or response composition」，`action`＝「Review source trust, retrieval quality, citation traceability, and answer reliability before release」）；以及 `risk_hint_rules.toml` 的 `missing_required_slot`（missing_component 型），當 `rag-core-v1` 的 13 個 slot（包含 `citation_or_response_composer`）任一缺席時觸發——這是「citation support」在*靜態設定層*的既有部分覆蓋。
- Missing（重）：「Qdrant collection existence check」「Empty collection detection」「Payload metadata completeness check」三項，都需要**連線到實際運行中的 Qdrant 並查詢其 collections/points**——這是全新能力，且與 Epic 2 的「Qdrant health/live/ready check」是*同一個連線目標、不同層級的查詢*（Epic 2 問「Qdrant 活著嗎」，Epic 5 問「Qdrant 裡面的 collection 內容對不對」）。
- Missing（複雜度量級不同）：「Unsupported claims detection」本質是評估 LLM 輸出是否被檢索內容支撐（hallucination/groundedness 評測），屬於 Ragas/DeepEval 等 LLM-as-judge 範疇——複雜度遠高於其餘 5 項（連線查詢 collection 是「能不能連上＋回傳什麼」的層級，groundedness 評測是「呼叫 LLM 來判斷另一個 LLM 的輸出」的層級）。
- Must not claim：「初版 RAG trust score generation」不可被實作成單一數字的 pass/fail 閘門——這點 Epic 5 自己的完成條件第三項（「避免過度相信單一分數，並展示 evidence」）已經講對了，但範圍裡的「trust score」用詞本身容易被誤讀成「一個分數＝一個閘門」，措辭應該與完成條件第三項互相呼應。

**Issue Alignment**
- Accurate：「檢查 RAG 系統是否具備可用、可追蹤、由 evidence 支持的知識基礎」與 CLAUDE.md「Findings must be evidence-based, traceable to file/line/config」高度一致——只是這裡的 evidence 多了一種新類型：「vector store 查詢結果」，不只是「file/line/config」。
- Missing product goal：沒有引用 `rag_knowledge_trust` recommended-check 作為本 Epic 履行的 Epic 1 承諾（與 Epic 2/3 同樣的缺漏模式）。
- Missing AC / Scope conflict：「Qdrant collection existence/empty/metadata 檢查」與 Epic 2「Qdrant health/live/ready check」都需要 Qdrant 連線能力——應該記錄成 Follow-Up Candidates 裡的跨 Epic 協調事項（建議實作順序：Epic 2 先建立 Qdrant 連線基礎設施，Epic 5 在其上查詢 collection 內容），而不是兩個 Epic 各自重複做一套 Qdrant client。
- Scope conflict：標題與範圍寫死「Qdrant」，但 `rag-core-v1` 的 `vector_store` slot 支援多種後端（`tests/fixtures/rag_projects/pgvector_openai_rag` 即用 pgvector）；`recommended_next_check_rules.toml` 的 `rag_knowledge_trust` 規則本身用詞是泛用的「RAG knowledge source / retrieval / citation」，沒有寫死 Qdrant。建議範圍改為「vector store（Qdrant 為第一個具體目標）」。
- Scope 過大：「Unsupported claims detection」與其餘 5 項在實作複雜度上不對稱（見上），建議在 body 中明確標示為「進階／第二階段」項目，或記錄為獨立的 Follow-Up Candidate，讓 Epic 5 的主體聚焦在「collection existence/empty/metadata/citation-support/trust-score-v1（不含 LLM-as-judge）」這 5 項機械式檢查。

**User/Adoption Value**
- 高，且方向完全正確：「我的 RAG 是真的有根據，還是在自信地編故事」是 RAG 信任問題的核心，而「避免過度相信單一分數，並展示 evidence」的框架，正好對應 principles.md 引用的最新業界共識（LLM-as-judge 只能當訊號、不能當唯一閘門）——這是 Epic 2-7 中與外部最佳實踐對齊度最高的一條。
- Still weak：如果「Unsupported claims detection」+「trust score」被包裝成「我們會告訴你 RAG 有沒有幻覺」這種強承諾，但底層是 LLM-as-judge 的粗略訊號，容易造成**過度信任**（使用者看到「trust score: 85/100」就直接上線）——這是產品層級的風險，緩解方式是：完成條件第三項的「展示 evidence」要做得足夠顯眼，且（如上）把 groundedness 評測獨立列為進階項目。

**Product Positioning / Source-of-Truth Cross-Check**
- 不是 RAG-builder（本 Epic 是「檢查」既有 RAG，不是幫你建一個）；不是「完整 RAG 評測平台」——範圍應鎖定在「release gate 需要的最小信任訊號」，完整評測（Ragas/DeepEval 全套 metric）超出範圍，屬於 Non-Goals。
- Source-of-truth：vector store 查詢結果是新的 evidence 類型，需要明確：這類 evidence 是否寫回 `ai_system_map.json`，還是與 Epic 2 一樣是獨立、有時間戳記的 opt-in 產出物（建議與 Epic 2 採用一致的模式）。

**Decision**
【核心判斷】✅ 方向正確，且是 Epic 2-7 中與外部最新實踐（principles.md 引用的 Ragas/DeepEval、LLM-as-judge 訊號定位）對齊度最高的一個。
【關鍵洞察】真正的問題不是「這些檢查該不該做」，而是「6 個範圍項目的複雜度量級差距太大（5 個是『連線查詢＋比對 metadata』等級，1 個『Unsupported claims detection』是『跑一次 LLM-as-judge 評測』等級），全部塞在同一個完成條件下，會讓人低估整個 Epic 的工作量，也會讓『trust score』被誤讀成單一閘門——這正好與 Epic 自己完成條件第三項想避免的事情相矛盾」。
【Linus式方案】把「Unsupported claims detection」標示為進階/Follow-Up Candidate，主體聚焦在 5 項機械檢查；標題與範圍的「Qdrant」改為「vector store（Qdrant 為第一個目標）」；引用 `rag_knowledge_trust` recommended-check 作為履行的承諾；與 Epic 2 的 Qdrant 連線能力記錄為協調順序（Epic 2 → Epic 5），不是重複範圍。
Outcome：Refine existing issue。

---

### Epic 6（#7）：Release Report & CI Gate — Verdict、Evidence、JSON 與 Exit Code

**Repo Reality**
- Implemented：0%。CLI 目前只有 `map`/`validate-map`/`trace`，沒有 `gate` 指令；沒有 verdict engine；沒有「Fix First Recommendation」產生器。
- Partial：`ai_system_map.json` 的 `risk_hints` 已經帶有 `severity_hint`（如 medium/low），這是 verdict engine 的原始素材；`MarkdownSummaryService` 已存在於 L1 pipeline，產出人類可讀摘要，但它是在 Epic 2-5 的檢查都還不存在的階段就跑完的——目前的 Markdown 摘要描述的是「系統圖長什麼樣子」，不是「READY/RISKY/NOT READY 的 verdict」。
- **關鍵相依性**：verdict engine 要產生有意義的 READY/RISKY/NOT READY，輸入訊號理論上應該來自 Epic 2（runtime readiness）、Epic 3（privacy/exposure）、Epic 4（agent tool risk）、Epic 5（RAG trust）的檢查結果——但這 4 個 Epic 目前全部是 0% 實作（見上述四個 Epic 的 Repo Reality）。若 Epic 6 在 Epic 2-5 之前實作，verdict 只能基於 Epic 1 現有的 12 條靜態 risk_hint，覆蓋面明顯不足（例如：一個專案完全沒有觸發任何靜態 risk_hint，但其 Qdrant 容器其實沒在跑——Epic 1 抓不到，verdict 會誤判為 READY）。issue 編號順序（#3-#6 為 Epic 2-5，#7 為 Epic 6）已經暗示了正確順序，但 body 內文沒有把這個相依性寫清楚。
- Must not claim：body 為規劃文字，無過度宣稱問題；但「JSON report output」未來實作時，不可直接把 verdict 寫進 `ai_system_map.json` 本體——應該是從 system map + risk_hints +（未來）Epic 2-5 輸出*衍生*出來的獨立產出物。

**Issue Alignment**
- Accurate：「READY / RISKY / NOT READY」直接對應 CLAUDE.md 對整個產品的定義（"outputs one of READY/RISKY/NOT READY with evidence"）——這是產品的核心收斂點，方向完全正確。
- Missing product goal：沒有明確寫出「verdict 的訊號品質，取決於 Epic 2-5 是否已經產出對應的檢查結果」這個相依性——這應該寫進 Scope 或 Evidence To Preserve，避免被提前實作成一個訊號薄弱的 verdict engine。
- Missing AC：「Fix First Recommendation generator」沒有定義排序依據——建議至少定為「依 `risk_hints[].severity_hint`（以及未來 Epic 2-5 的發現）做嚴重度排序」，否則無法驗收。
- **Scope conflict（與 Epic 7 重疊）**：完成條件第三項「GitHub Actions integration path」與 Epic 7 範圍「GitHub Action integration」用詞高度重疊，讀者會問「Epic 6 不是已經做了？」。實際上兩者應該是不同層級：Epic 6＝讓 `systograph gate --ci` 的 JSON/exit code 可以被*任何* CI 消費（並提供一個 GitHub Actions 的*範例* workflow YAML 作為文件），Epic 7＝把這個 gate 包裝成一個*可發布、可重用*的 GitHub Action（`uses: systograph/action@v1`）。這個差異必須在兩個 Epic 的 body 裡都寫清楚，否則會有兩個 Epic 都認為自己該做「GitHub Actions 整合」的混亂。

**User/Adoption Value**
- 非常高：這是「Release Readiness *Gate*」的「Gate」本身，是整個產品的收斂與命名來源，CI 可消費的 exit code 是讓這個工具能真正卡在 CI pipeline 裡的關鍵。
- Still weak：如上，價值會被「上游訊號是否齊備」綁住——如果 Epic 6 搶在 Epic 2-5 之前做完，第一版 gate 的判斷力會很弱，可能讓早期使用者對「verdict」的可信度產生錯誤的第一印象。

**Product Positioning / Source-of-Truth Cross-Check**
- 不是通用 CI 平台（不取代 GitHub Actions/Jenkins 本身），是「產生一個可被任何 CI 消費的 verdict + exit code」——這個邊界目前 body 沒寫明，但也沒有寫錯的內容，屬於補充說明。
- Source-of-truth：「JSON report output」＝衍生產出物，不是 `ai_system_map.json` 的 schema 變更——應在 Scope 中明確。

**Decision**
【核心判斷】✅ 方向正確，是整個產品的命名收斂點，完全不該被取消或大改方向。
【關鍵洞察】真正的問題不是「verdict engine 該怎麼設計」，而是「這個 Epic 的『輸入訊號』完全依賴 Epic 2-5 的產出，但 body 沒有寫出這個相依性，等於把『verdict 品質取決於實作順序』這個事實藏起來——一旦有人照 issue 編號以外的順序去做（例如先做 Epic 6 因為它『聽起來最重要』），第一版 gate 就會是一個訊號很薄的空殼」。
【Linus式方案】在 Scope/Evidence To Preserve 明確寫出「verdict 的覆蓋面取決於 Epic 2-5 是否已產出對應結果，初版可先用 Epic 1 的 risk_hints 作為唯一訊號來源，但必須在 report 中誠實標示『目前訊號來源僅含靜態掃描』」；把完成條件第三項改寫為「CLI exit code + JSON 適用於任何 CI（並提供一個通用範例）」，與 Epic 7 的「打包成可重用 GitHub Action」明確分工。
Outcome：Refine existing issue。

---

### Epic 7（#8）：Distribution & Integrations — Packaging、GitHub Action 與 Developer Workflow

**Repo Reality**
- Implemented：0% 的 packaging/launcher 部分（無 `.exe`/`.app`/`.dmg` build script）。
- Partial（被低估的既有進度）：「Codex code review workflow 與 `AGENTS.md` review guidance」——`AGENTS.md` 已存在且已被 CLAUDE.md 的 Workflow Conventions 直接引用（"Merges to main require human review and Codex review"、"AGENTS.md has PR-review focus areas"）——這個範圍項目在「指引文件已寫好並在用」的層級上，已經相當接近完成，本 Epic 在這塊的工作更像是「整理/延伸既有文件」而非「從零建立」。
- Partial：「Local Web UI launch flow」——`pnpm dev`（frontend）與 `uv run systograph viewer`/web app（backend）作為*開發者*啟動流程已存在；本 Epic 缺的是「給非開發者的一鍵啟動封裝」，不是重建 Web UI 本身。
- Missing：「GitHub Action integration」0%（與 Epic 6 的重疊見上）。
- 適當的範圍收斂（無需修改）：「VS Code / Docker Desktop extension」明確標示為「後續...討論」，已經是恰當的 hedge（非本 Epic 驗收項），建議在 Non-Goals 中明確化即可，不算缺陷。

**Issue Alignment**
- Accurate：「在 core MVP 可用後」的明確排序語句，是 Epic 2-7 中*唯一*明確寫出「這個 Epic 排在後面」的，比 Epic 6 的隱含排序更清楚，值得保留作為範本語句。
- Missing product goal：沒有承認「Codex review / AGENTS.md guidance」已經有實質進度——應改用「整理/延伸」而非「建立」的語氣。
- **Scope conflict（與 Epic 6 重疊）**：「GitHub Action integration」見 Epic 6 分析——本 Epic 應該是「打包成可重用 GitHub Action，建立在 Epic 6 的 `systograph gate --ci` exit-code 合約之上」的那一方。
- Missing Non-Goals：「VS Code / Docker Desktop extension」應從「後續討論」的措辭，明確移到 Non-Goals 區塊，避免被誤認為本 Epic 的驗收範圍。
- 完成條件第三項「Packaging 與 Core Engine behavior 清楚分離」直接呼應 CLAUDE.md 核心設計原則「Core engine is platform-independent — CLI, Web API, and launchers must not duplicate core scanner logic」——這是 Epic 2-7 中與既有架構原則對齊度最高的一條，應保留並列入 Evidence To Preserve。

**User/Adoption Value**
- 高：packaging/launcher 是「會寫程式碼的開發者」與「任何想試用的人」之間的門檻，對採用率很關鍵。
- Still weak：範圍同時涵蓋 Windows + macOS + Web UI + GitHub Action + Codex workflow + 未來 VS Code/Docker 討論，是典型的「大雜燴」Epic——但因為明確標示「在 core MVP 可用後」，作為*路線圖佔位*是合理的（不要求一次做完）；若未來真正開工，建議拆成 per-platform 的子 issue，但這屬於實作階段的決定，本階段不需要拆分。

**Product Positioning / Source-of-Truth Cross-Check**
- 無產品定位衝突——本 Epic 是「怎麼把現有功能交到使用者手上」，不影響核心掃描邏輯的定位。
- 「Packaging 與 Core Engine behavior 清楚分離」本身就是 source-of-truth/邊界原則的延伸（packaging 不應該有自己的一套掃描邏輯），現有完成條件已經講對，應保留。

**Decision**
【核心判斷】✅ 方向正確，且是 Epic 2-7 中*排序語意最清楚*（明確寫「在 core MVP 可用後」）、與既有架構原則（core/packaging 分離）對齊度最高的一個。
【關鍵洞察】真正的問題不是這個 Epic 的範圍「太雜」（路線圖佔位本來就允許雜），而是「GitHub Action integration」這四個字同時出現在 Epic 6 的完成條件與 Epic 7 的範圍裡，沒有任何文字說明兩者的差異——這是唯一需要修正的實質問題，其餘（Codex/AGENTS.md 既有進度、VS Code/Docker 的 hedge）都是措辭層級的小修。
【Linus式方案】Epic 7 的「GitHub Action integration」改寫為「打包成可重用、可發布的 GitHub Action，封裝 Epic 6 的 `systograph gate --ci` exit-code 合約」；「Codex review/AGENTS.md」改用「整理/延伸既有指引」措辭；「VS Code/Docker Desktop extension」移入明確的 Non-Goals。
Outcome：Refine existing issue。

## GitHub Issue Changes

所有編輯均透過 `gh issue edit <N> --repo 1104030360/Systograph --body-file <file>` 套用，僅修改 body，**標題全部保留不變**（理由：標題在其他文件/issue 中被引用作識別碼，本階段的修正重點是 body 結構與內容，不是識別碼；範圍收斂等措辭調整已在 body 的 Scope/Non-Goals 中處理）。每筆編輯後皆重新 `gh issue view` 確認。

| Issue | 標題（不變） | Before（原結構） | After（新結構） | 確認 |
|---|---|---|---|---|
| [#3](https://github.com/1104030360/Systograph/issues/3) | [Epic 2] Runtime Readiness：Ollama、Docker、Native Services 與 Qdrant | `## 目標` / `## 範圍` / `## 完成條件`（無 Current Reality、Non-Goals、Evidence、Follow-Up） | `## Goal` / `## Current Reality` / `## Scope`（改為「系統圖偵測到的執行期依賴，Ollama/Docker/Qdrant 為首批範例」+ not-applicable 狀態）/ `## Non-Goals`（非常駐監控、非通用 infra 工具、非 Docker socket 管理、非 model-serving 建議）/ `## Acceptance Criteria` / `## Evidence To Preserve`（引用 `runtime_readiness` 規則 + QueryTraceService 前例）/ `## Follow-Up Candidates`（與 Epic 5 共用 Qdrant 連線） | 已重新 `gh issue view`，body 長度 2012 字元，4 個新區塊段落均存在 |
| [#4](https://github.com/1104030360/Systograph/issues/4) | [Epic 3] Privacy & Exposure Guard：Secrets、Ports 與 Cloud Endpoints | `## 目標` / `## 範圍` / `## 完成條件` | `## Goal` / `## Current Reality`（列出 `risk_hint_rules.toml` 既有 5 條規則 + `secret_masking_service` 已存在）/ `## Scope`（聚焦「Data Leaves Device 報告」彙總 + 補 Ollama/Qdrant/OpenWebUI 具名 port 規則）/ `## Non-Goals`（非通用弱點掃描器、不主動掃任意 host）/ `## Acceptance Criteria` / `## Evidence To Preserve` / `## Follow-Up Candidates`（無） | 已重新 `gh issue view`，body 長度 2507 字元，4 個新區塊段落均存在 |
| [#5](https://github.com/1104030360/Systograph/issues/5) | [Epic 4] Agent Tool Risk Guard：Tool Inventory、Permissions 與 Auditability | `## 目標` / `## 範圍` / `## 完成條件` | `## Goal` / `## Current Reality`（確認 0% 起點 + `guardrails` slot 命名差異說明）/ `## Scope`（5 類高風險 tool-call 具體偵測模式）/ `## Non-Goals`（明定 log/approval check 為靜態程式碼偵測，不讀 runtime audit log、不接 policy engine）/ `## Acceptance Criteria` / `## Evidence To Preserve` / `## Follow-Up Candidates`（schema 是否需要 `agent_tools` 概念，留待實作前討論） | 已重新 `gh issue view`，body 長度 2130 字元，4 個新區塊段落均存在 |
| [#6](https://github.com/1104030360/Systograph/issues/6) | [Epic 5] RAG Knowledge Trust：Collections、Metadata、Citations 與 Grounding | `## 目標` / `## 範圍` / `## 完成條件` | `## Goal` / `## Current Reality`（引用 `rag_knowledge_trust` 規則 + `missing_required_slot`，並標出與 Epic 2 共用 vector store 連線）/ `## Scope`（Qdrant 改為「vector store，Qdrant 為首個目標」；5 項機械檢查 + trust score 訊號定位）/ `## Non-Goals`（不做完整 RAG 評測平台、不自動 re-index、不是 RAG-builder；「Unsupported claims detection」移出主體）/ `## Acceptance Criteria` / `## Evidence To Preserve` / `## Follow-Up Candidates`（groundedness evaluation 獨立排期 + 與 Epic 2 協調順序） | 已重新 `gh issue view`，body 長度 2498 字元，4 個新區塊段落均存在 |
| [#7](https://github.com/1104030360/Systograph/issues/7) | [Epic 6] Release Report & CI Gate：Verdict、Evidence、JSON 與 Exit Code | `## 目標` / `## 範圍` / `## 完成條件` | `## Goal` / `## Current Reality`（指出 verdict 訊號相依 Epic 2-5，目前皆 0%，並修正 CLI 現況為 `map` / `validate-map` / `trace`）/ `## Scope`（含「初版若 Epic 2-5 未完成，須誠實標示訊號來源範圍」）/ `## Non-Goals`（不打包 GitHub Action——劃給 Epic 7，本 Epic 只出 CLI/JSON/exit-code 合約）/ `## Acceptance Criteria` / `## Evidence To Preserve` / `## Follow-Up Candidates`（與 Epic 7 的分工說明） | 已於 2026-06-13 04:35 UTC 重新檢查，4 個新區塊段落均存在 |
| [#8](https://github.com/1104030360/Systograph/issues/8) | [Epic 7] Distribution & Integrations：Packaging、GitHub Action 與 Developer Workflow | `## 目標` / `## 範圍` / `## 完成條件` | `## Goal` / `## Current Reality`（指出 AGENTS.md/Codex review 已有實質進度，Local Web UI 開發者流程已存在）/ `## Scope`（GitHub Action 改為「封裝 Epic 6 的 `systograph gate --ci` 合約」）/ `## Non-Goals`（VS Code/Docker Desktop extension 明確移入 Non-Goals；不重新定義 verdict 邏輯）/ `## Acceptance Criteria` / `## Evidence To Preserve` / `## Follow-Up Candidates`（依賴 Epic 6 合約穩定後才能開始） | 已重新 `gh issue view`，body 長度 1907 字元，4 個新區塊段落均存在 |

所有 6 個 Epic 的 Decision 皆為 **Refine existing issue**——詳細理由見上方 Epic Review Matrix 各 Epic 的「Decision」小節。

## New Goal Candidates

| Candidate goal | Best Epic | Why it improves product | Repo evidence | Risk if added too early |
|---|---|---|---|---|
| RAG Answer Groundedness Evaluation（LLM-as-judge，作為 Epic 5「Unsupported claims detection」的進階/獨立子項，記錄於 Epic 5 重寫後 body 的 Follow-Up Candidates，不另開新 issue） | Epic 5（#6） | 把「連線查詢 collection/metadata」（5 項機械檢查，可確定性高、成本低）與「呼叫 LLM 評估另一個 LLM 輸出是否被支撐」（1 項評測，成本高、有非決定性）拆開，讓 Epic 5 的核心可以在不依賴 LLM API 呼叫的情況下先交付；同時呼應 principles.md「LLM-as-judge 只能當訊號，不應是唯一上線閘門」，避免「trust score」被誤讀為單一分數即可放行。 | `recommended_next_check_rules.toml:17-23`（`rag_knowledge_trust`）+ Epic 5 完成條件第三項「避免過度相信單一分數，並展示 evidence」+ principles.md 對 Ragas/DeepEval 與 LLM-as-judge 定位的引用。 | 若在 Epic 5 主體中與其餘 5 項機械檢查綁在一起一次性要求完成，會把整個 Epic 5 的交付時程拉長到等同於導入完整 RAG 評測框架的程度，且會讓「trust score」自帶 LLM 呼叫成本與結果不穩定性，提早暴露給使用者容易造成過度信任或信任崩潰。 |

## Rejected Or Deferred Goals

審查過程中曾考慮、但依 check1.md 約束明確排除的候選目標，逐一對應排除類別：

- **互動式 RAG 對話測試介面**（讓使用者在 Viewer 裡直接跟自己的 RAG 對話，藉此「感受」groundedness）——審查 Epic 5 時曾想到的替代方案，用來取代/輔助「Unsupported claims detection」。排除類別：**chatbot**。理由：Systograph 的角色是「檢查既有系統」，一旦提供互動對話介面，產品定位會從「release gate」滑向「RAG 聊天工具」，與 CLAUDE.md 明確的「NOT a chatbot」定位衝突。
- **自動補建/重新索引以修補 metadata 缺失**（偵測到 chunk 缺少 `source`/`page`/`chunk_id` 時，由 Systograph 自動重新跑 chunking/embedding 來補上）——審查 Epic 5「Payload metadata completeness check」時考慮過的「順手修好」方案。排除類別：**full-RAG-workflow**。理由：Systograph 只能「報告」metadata 缺失與其證據，不能執行 indexing/chunking/embedding 等 RAG pipeline 操作——否則就是在做 RAG-builder 的工作，違反「NOT a RAG-builder」定位，也違反本階段「不修改功能程式碼/不修補實作問題」的約束精神（若在產品設計上就把「自動修補」當成目標，會在根本上與唯讀掃描定位衝突）。
- **通用網路弱點/任意主機 port 掃描器**（審查 Epic 3 時考慮：既然要做 port exposure，要不要順便對使用者整台機器或區網做一次通用安全掃描）。排除類別：**enterprise-SIEM** + **arbitrary-runtime-probing**。理由：Epic 3 的範圍應限定在「系統圖中已偵測到的元件」相關的 exposure 訊號，對任意 host/port 做主動掃描已經是企業資安掃描器（如 Nessus/Nmap 全網掃描）的領域，超出「local AI privacy guard」的定位，也違反「Local-first privacy」（掃描整台機器/區網需要遠超讀取專案目錄的權限）。
- **常駐排程監控/Daemon 模式**（審查 Epic 2 時考慮：CPU/GPU/runtime readiness 檢查既然存在，是否應該變成背景持續監控、定期重新評分）。排除類別：**完整 observability platform**（check1.md 9 大審查準則之一，非 Task5 列舉的 6 類但同樣明確排除）。理由：CLAUDE.md 將本產品定位為 point-in-time 的「release readiness gate」，常駐監控會把產品變成 APM/observability 工具，與「不是完整 observability platform」的定位直接衝突；Epic 2 的 runtime readiness 應保持「使用者主動觸發、單次、有時間戳記」的 opt-in 檢查模式。
- **內建 policy engine 與長期 audit log 儲存**（審查 Epic 4「approval/policy presence check」時考慮：要不要讓 Systograph 自己提供一套 policy 規則定義語言，並長期儲存 agent tool 呼叫記錄）。排除類別：**long-term-policy-store**。理由：這會讓 Systograph 從「檢查工具」變成「執行期治理基礎設施」，且長期儲存 tool 呼叫記錄本身就是新的隱私/留存風險（與「Local-first privacy」原則衝突）；Epic 4 應僅檢查「程式碼中是否存在這類機制的痕跡」。
- **GPU/硬體偏好下的 model serving 調校建議**（審查 Epic 2「CPU/GPU/hybrid state detection」時考慮：偵測到特定 GPU 後，順便建議使用者該換用哪個量化模型/推論引擎設定）。排除類別：**model-serving-platform-features**。理由：Systograph 的角色是回報「偵測到的硬體狀態」作為 evidence，不是提供模型服務調校建議——後者是 vLLM/Ollama/LM Studio 等推論服務本身或專門的 MLOps 工具的職責範圍。

## Risks And Follow-Up Items

本節彙整本階段識別、但屬於**後續實作階段**（非本階段 roadmap/docs 審查範圍）的風險與協調事項；完整清單與額外的 Code Fixes / Test-Verification / Research Follow-Ups 見 `../todo/phase1-solidate-todo.md`。

| # | 風險／事項 | 涉及 Epic | 影響 | 建議下一步 | Owner bucket |
|---|---|---|---|---|---|
| 1 | Epic 2 與 Epic 5 共用 vector store（Qdrant）連線能力，但分別記錄在兩個 Epic 的 body 中 | Epic 2（#3）↔ Epic 5（#6） | 若各自實作一套 Qdrant client，造成重複實作與行為不一致風險 | 實作排序：Epic 2 先建立連線基礎設施，Epic 5 在其上查詢 collection 內容；具體連線層設計留待 Epic 2 實作時決定 | AI infra |
| 2 | Epic 6 完成條件與 Epic 7 範圍曾均使用「GitHub Action(s) integration」一詞 | Epic 6（#7）↔ Epic 7（#8） | 可能造成兩個 Epic 互相誤判對方已涵蓋、或重複規劃同一件事 | 已在重寫後 body 分工：Epic 6＝CLI/JSON/exit-code 合約 + 通用範例；Epic 7＝打包為可發布、可重用的 GitHub Action，且應排在 Epic 6 合約穩定後開始 | Backend |
| 3 | Epic 5「Unsupported claims detection」（LLM-as-judge groundedness）複雜度遠高於其餘 5 項機械檢查 | Epic 5（#6） | 若綁在一起交付會拖慢核心（不需即時 LLM 呼叫）的進度，且容易讓「trust score」被誤讀為單一可信分數 | 已拆分記錄為 Epic 5 body 的 Follow-Up Candidate（未另開新 issue）；Epic 5 主體先交付 5 項機械檢查，groundedness 評測待核心穩定後再獨立排期 | AI application |
| 4 | Epic 4「agent tool inventory」結果在 `ai_system_map.json` 中的 schema 位置未定（`rag-core-v1` 13 個 slot 為 RAG 專屬，無對應「agent tools」概念） | Epic 4（#5） | 影響面含 `schemas/ai-system-map.v1.schema.json`、frontend `types.ts`、`API_CONTRACT.md`，屬 Shared contract 層級決定 | 在 Epic 4 實作前另行召開 schema 設計討論 | Shared contract |
| 5 | Epic 6 verdict engine 的訊號覆蓋面依賴 Epic 2-5（目前皆 0% 實作）的檢查結果 | Epic 6（#7）依賴 Epic 2-5（#3-#6） | 若 Epic 6 搶先於 Epic 2-5 之前實作，初版 verdict 僅能基於 Epic 1 的 12 條靜態 `risk_hints`，訊號薄弱且若未誠實標示來源範圍，容易讓使用者對「READY」結果產生錯誤信任 | 若 Epic 6 先開工，第一版必須在 report 中明確標示「本次 verdict 基於：僅 Epic 1 靜態掃描」 | Backend |

## Finding Category Coverage

| Category required by `check1.md` | 本次結論 | Evidence / follow-up |
|---|---|---|
| Roadmap 問題 | 6/6 Epic 都需要 refine existing issue，沒有需要重開定位或新拆 Epic | Epic Review Matrix + GitHub Issue Changes |
| 產品定位問題 | 未發現 Epic 2-7 滑向 chatbot / RAG builder / 完整 observability platform / 企業級資安掃描器 / model serving platform；已把錯誤候選列為 rejected/deferred | Rejected Or Deferred Goals |
| 資安風險 | Epic 3 的 Data Leaves Device 報告、Epic 4 的 tool permission / auditability 是主要 security/privacy 後續工作 | Risks #3/#4 與 TODO Security/AI infra 項目 |
| 實作缺陷 | Epic 2 runtime probe、Epic 4 agent tool rules、Epic 5 vector store content checks、Epic 6 verdict engine 皆尚未實作 | Current Implementation Baseline + TODO Code Fixes |
| UX / usability 問題 | 目前前端仍缺 project import -> scan -> boundary decision -> viewer refresh 閉環；distribution/launcher 仍待 Epic 7 | Baseline rows 8-9、Epic 7 review |
| AI backend 問題 | Gate/verdict 與 runtime probe 尚未落地，且必須避免把 runtime 狀態寫回 static canonical map | Epic 2 / Epic 6 decisions |
| AI infra 問題 | Ollama / Docker / Qdrant / Open WebUI 等 runtime 或 port 規則仍待實作，Qdrant client 應避免 Epic 2/5 重複實作 | Risks #1、TODO AI infra |
| AI application 問題 | RAG trust 的 groundedness evaluation 應拆成 follow-up，不應把 LLM-as-judge 當唯一閘門 | New Goal Candidates + Risks #3 |
| Testing / eval 缺口 | Epic 2/4/5 需要 mock/fixture 類 regression tests；Ragas/DeepEval 類 groundedness API 研究保留到後續 | TODO Test / Verification Follow-Ups + Research Follow-Ups |

## Final Gap Audit

| Epic | Issue | Outcome | Edited? | New goals added? | Follow-up candidates | Blocker |
|---|---|---|---|---|---|---|
| Epic 2 | [#3](https://github.com/1104030360/Systograph/issues/3) | Refine existing issue | Yes | No | 與 Epic 5 共用 Qdrant 連線（協調順序：Epic 2 → Epic 5） | 無 |
| Epic 3 | [#4](https://github.com/1104030360/Systograph/issues/4) | Refine existing issue | Yes | No | 無 | 無 |
| Epic 4 | [#5](https://github.com/1104030360/Systograph/issues/5) | Refine existing issue | Yes | No | `agent_tools` schema 概念（待 Epic 4 實作前另行討論） | 無 |
| Epic 5 | [#6](https://github.com/1104030360/Systograph/issues/6) | Refine existing issue | Yes | 1（RAG Answer Groundedness Evaluation，記錄為本 issue 的 Follow-Up Candidate，未另開新 issue） | Groundedness evaluation 獨立排期 + 與 Epic 2 協調 Qdrant 連線順序 | 無 |
| Epic 6 | [#7](https://github.com/1104030360/Systograph/issues/7) | Refine existing issue | Yes | No | 與 Epic 7 的 GitHub Action 分工（Epic 6＝CLI/JSON/exit-code 合約，Epic 7＝可重用 Action） | 無 |
| Epic 7 | [#8](https://github.com/1104030360/Systograph/issues/8) | Refine existing issue | Yes | No | 依賴 Epic 6 的 `systograph gate --ci` 合約穩定後才能開始 GitHub Action 開發 | 無 |

**驗收狀態**：
- 6/6 Epic 完成審查與 Decision；6/6 Outcome 為 `Refine existing issue`；0 個 Epic 為 `No change needed` / `Add goals to existing issue` / `Split into follow-up issue candidate` / `Blocked by missing GitHub access`。
- 6/6 issue body 已套用並經 `gh issue view` / GitHub MCP 重新驗證（標題不變、新區塊段落存在；#7 於 2026-06-13 04:35 UTC 額外修正 CLI 現況清單）。
- 新增產品目標：1 項（RAG Answer Groundedness Evaluation），記錄於 Epic 5 body 的 Follow-Up Candidates，未另開新 GitHub issue（符合 `check1.md` 僅可編輯 #3-#8 的範圍限制）。
- Rejected/Deferred 候選目標：6 項，逐一對應 chatbot / full-RAG-workflow / enterprise-SIEM + arbitrary-runtime-probing / 完整 observability platform / long-term-policy-store / model-serving-platform-features 等排除類別（詳見 Rejected Or Deferred Goals）。
- 功能程式碼變更：**0**。`git status --short` 重新檢查時仍有文件/設定變更（`.gitignore`、`AGENTS.md`、`phase1-solidate.md`、`check1.md`、本 Report/TODO），但未出現 `src/`、`frontend/src/`、`tests/`、`scripts/` 的功能程式碼變更；Codex agent/MCP 設定已改由全域 `/Users/linjunting/.codex/` 管理，不再使用 repo-local `.codex/`；`git diff --check -- docs/work/Timmy/schedule/fable-5/solidate-MyPlan` 無空白字元錯誤。
- Forbidden-overclaim grep（`production-ready|已完成|persistent|database|...`）已對全部 6 份新 body + 本報告執行，所有匹配均落在 Non-Goals/Rejected-Goals 的否定語境中，無過度宣稱問題。
- Blockers：**無**。所有 GitHub 讀寫操作（讀取 #2-#8、編輯 #3-#8、重新讀取確認）皆正常完成。

**後續銜接**：本報告與 `../todo/phase1-solidate-todo.md` 共同構成 Phase 1 Epic 2-7 roadmap solidation 的完整產出；下一階段（實作階段）應以 TODO 中列出的 GitHub Issue Follow-Ups、Code Fixes Not Performed、Test/Verification Follow-Ups、Research Follow-Ups 作為起點，並以本報告 Epic Review Matrix 中各 Epic 的 Decision／Linus式方案 作為實作時的範圍依據。
