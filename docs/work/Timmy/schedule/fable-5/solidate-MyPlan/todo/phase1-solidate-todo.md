# Phase 1 Epic 2-7 Solidation TODO

本清單為 Epic 2-7（issue #3-#8）對齊審查（見 `../report/phase1-solidate-report.md`）產出的後續事項。本階段僅完成 roadmap/issue/docs 層級的檢查與 GitHub issue body 修訂，**未修改任何功能程式碼**；以下項目皆為留給後續實作階段的追蹤事項。

## GitHub Issue Follow-Ups

- **[#3 ↔ #6] Epic 2 與 Epic 5 共用 vector store 連線能力**
  - 問題：Epic 2（Qdrant health/live/ready check）與 Epic 5（Qdrant collection existence/empty/metadata check）都需要連線到同一個 Qdrant 實例，只是查詢層級不同（infra liveness vs. content）。
  - 影響：若兩個 Epic 各自實作一套 Qdrant client，會造成重複實作與未來行為不一致的風險。
  - Evidence：Epic 2（#3）與 Epic 5（#6）重寫後 body 的 Scope / Follow-Up Candidates 區塊已互相標註此相依。
  - 建議下一步：實作排序為 Epic 2 先建立 vector store 連線基礎設施，Epic 5 在其上查詢 collection 內容；具體連線層的設計留待 Epic 2 實作時決定。
  - Owner bucket：AI infra

- **[#7 ↔ #8] Epic 6 與 Epic 7 的「GitHub Action」分工**
  - 問題：原始 body 中，Epic 6 完成條件「GitHub Actions integration path」與 Epic 7 範圍「GitHub Action integration」用詞重疊，容易讓人誤判工作已被涵蓋或重複規劃。
  - 影響：若不釐清，未來可能出現兩個 Epic 都想做「GitHub Actions 整合」、或都認為對方已經做了的協調落差。
  - Evidence：Epic 6（#7）與 Epic 7（#8）重寫後 body 已分工：Epic 6 提供 `kai-mind gate --ci` 的 CLI/JSON/exit-code 合約 + 通用範例；Epic 7 負責打包成可發布、可重用的 GitHub Action。
  - 建議下一步：Epic 7 的 GitHub Action 開發應排在 Epic 6 的 CLI 合約穩定之後開始。
  - Owner bucket：Backend

- **[#6] Epic 5「Unsupported claims detection」拆分為獨立 Follow-Up**
  - 問題：原範圍中「Unsupported claims detection」（LLM-as-judge groundedness 評測）的實作複雜度與成本，遠高於 Epic 5 其餘 5 項機械式檢查（collection existence/empty/metadata/citation-support/trust-score-v1）。
  - 影響：若綁在一起要求交付，會拖慢 Epic 5 核心（不需即時 LLM 呼叫）的進度，且容易讓「trust score」被誤讀為單一可信分數。
  - Evidence：Epic 5（#6）重寫後 body 的 Non-Goals 與 Follow-Up Candidates 區塊；principles.md 對 Ragas/DeepEval 與「LLM-as-judge 只能當訊號」的引用。
  - 建議下一步：Epic 5 主體先交付 5 項機械檢查；groundedness 評測作為獨立排期項目，於 Epic 5 核心穩定後再規劃。
  - Owner bucket：AI application

- **[#5] Epic 4「agent_tools」schema 概念待設計**
  - 問題：「Agent tool inventory」的結果要放在 `ai_system_map.json` 的哪裡，目前 `rag-core-v1` 樣板的 13 個 slot 是 RAG 專屬，沒有「agent tools」對應概念。
  - 影響：這是 schema 層級的決定（新增 `agent_tools` 概念 vs. 套用既有 `components`/`endpoints`），影響面包含 `schemas/ai-system-map.v1.schema.json`、frontend `types.ts`、`API_CONTRACT.md`，太大且太早，不該由 Epic 4 body 自行定案。
  - Evidence：Epic 4（#5）重寫後 body 的 Follow-Up Candidates 區塊。
  - 建議下一步：在 Epic 4 實作前，另行召開 schema 設計討論（涉及 Shared contract）。
  - Owner bucket：Shared contract

- **[#7] Epic 6 verdict engine 的訊號相依性**
  - 問題：verdict（READY/RISKY/NOT READY）的訊號覆蓋面取決於 Epic 2-5 是否已產出對應結果，這 4 個 Epic 目前皆為 0% 實作；若 Epic 6 搶先實作，初版 verdict 只能基於 Epic 1 現有的 12 條靜態 `risk_hints`。
  - 影響：訊號薄弱的 verdict 若未誠實標示來源範圍，容易讓早期使用者對「READY」結果產生錯誤的信任（例如：靜態掃描沒有觸發任何 risk_hint，但 Qdrant 容器其實沒在跑，verdict 卻顯示 READY）。
  - Evidence：Epic 6（#7）重寫後 body 的 Current Reality / Scope / Acceptance Criteria 區塊（要求 verdict report 明確標示訊號來源範圍）。
  - 建議下一步：若 Epic 6 在 Epic 2-5 之前開工，第一版必須在 report 中明確標示「本次 verdict 基於：僅 Epic 1 靜態掃描」。
  - Owner bucket：Backend

## Product Goals Added Or Proposed

- **RAG Answer Groundedness Evaluation（LLM-as-judge）**
  - 內容：對 Epic 5 原範圍「Unsupported claims detection」的拆分產出，作為 Epic 5（#6）body 中的 Follow-Up Candidate 記錄，**未另開新 issue**。
  - Repo evidence：`core/rules/recommended_next_check_rules.toml:17-23`（`rag_knowledge_trust`）+ Epic 5 完成條件第三項 + principles.md 對 Ragas/DeepEval、LLM-as-judge 定位的引用（詳見報告 New Goal Candidates 表）。
  - Owner bucket：AI application

## Code Fixes Not Performed In This Phase

本階段未修改任何功能程式碼。以下為審查過程中發現、屬於 Epic 2-7 既有範圍內、但目前尚未實作的具體缺口，供未來實作者參考：

- **Epic 3（#4）範圍第一項「Ollama/Qdrant/Open WebUI 常見 port 規則」尚未實作**
  - 現況：`core/rules/risk_hint_rules.toml` 目前只有通用 `docker_published_port_exposure` 與 Chroma 專屬的 `chroma_server_published_port`，沒有 Ollama（11434）、Qdrant（6333/6334）、Open WebUI（8080/3000）等具名 port 規則。
  - 這是 Epic 3 **自己範圍內**已寫明、但尚未實作的部分，不是本階段新增的需求。
  - Owner bucket：AI infra

- **是否已能偵測「Open WebUI」這個元件，尚待確認**
  - Epic 3（#4）範圍提到 Open WebUI，但本階段未直接驗證 `component_detection_service` 是否已能識別 Open WebUI（例如透過 Docker image 名稱或 dependency manifest）。
  - 建議 Epic 3 實作前先確認此元件的偵測現況，若尚未支援，需與 port 規則一併補上。
  - Owner bucket：Backend

- **Epic 2（#3）「App / Agent API endpoint check」與 `QueryTraceService` 的關係待確認**
  - `QueryTraceService`（#44）已有 opt-in 黑箱 HTTP probe 的實作模式；Epic 2 的「App/Agent API endpoint check」在語意上高度相似（探測本專案自己的 API 是否回應）。
  - 建議 Epic 2 實作時優先確認能否直接複用/延伸 `QueryTraceService` 的程式碼，而非另起一套 HTTP client。
  - Owner bucket：Backend

## Test / Verification Follow-Ups

- **Epic 2（#3）runtime probe 測試 fixtures**：需要可模擬 Ollama/Docker/Qdrant 健康/不健康/未知回應的測試樣本（mock HTTP 回應或測試替身），以覆蓋 healthy/degraded/missing/not-applicable/unknown 五態，不應依賴真實啟動的 stack。Owner bucket：Backend
- **Epic 4（#5）agent-tool 程式碼模式測試 fixtures**：需要在 `tests/fixtures/rag_projects/` 下新增（或擴充既有）含 `subprocess`/檔案寫入刪除/`smtplib`/SQL write/webhook trigger 的範例專案，驗證新增的 `code_pattern_rules.toml` 規則。Owner bucket：Backend
- **Epic 5（#6）vector store 內容測試 fixtures**：需要可測試「collection 存在但為空」「collection 有資料但缺 `source`/`page`/`chunk_id`/`document_id`」「collection 完整」三種情境的測試替身，可能需要 mock Qdrant client 而非真實連線。Owner bucket：AI infra
- **Forbidden-overclaim grep 已執行**：對本階段新增/修改的 6 份 issue body 內容與本報告執行 `rg -n "production-ready|已完成|persistent|database|chat 已完成|scan history|always_skip|metadata_only|完整 observability|企業級資安|model serving"`，比對結果全部落在 Non-Goals / Rejected Goals 的「不是/不提供/排除」語境中（例如「不提供 model serving 調校建議」「不是完整 observability platform」），**已檢查，未發現過度宣稱問題**。Owner bucket：Docs（本階段已完成）
- **本階段未執行 `uv run pytest` / `ruff` / `mypy` / `pnpm build`**：因本階段未修改任何功能程式碼，僅修改 `docs/work/Timmy/...` 下的文件與 GitHub issue body，`git status --short` 確認改動範圍符合預期，`git diff --check` 無空白字元錯誤。是否需要對目前分支既有的未提交變更（`AGENTS.md`、`.gitignore` 等，皆非本階段產生）額外執行完整測試，留給分支擁有者決定。Owner bucket：Docs

## Research Follow-Ups

本輪已於 2026-06-13 針對 OWASP、MCP、Ragas、DeepEval、OpenAI eval/safety、Qdrant、Ollama、AgentDojo、Agent-SafetyBench、NIST AI 600-1 做 live research refresh，來源已記錄在 Report 的 `Live External Research Refresh`。以下項目是「後續實作前仍要確認當時版本/API 細節」，不是本輪 blocked 項目。

- **OWASP LLM Top 10（2025）「Excessive Agency」條目編號確認**：Epic 4（#5）body 刻意使用條目名稱而非編號以避免版本漂移；若未來需要附上正式編號引用，應在實作前透過 Context7 / 官方 OWASP 文件確認當前版本的編號對應。Owner bucket：Security
- **Ragas / DeepEval 現況 API 研究**：Epic 5（#6）的 groundedness evaluation follow-up 啟動前，應再次確認 Ragas/DeepEval 當時版本的 API、metric names、dataset shape、threshold 設定與 CI 整合方式。Owner bucket：AI application
- **Ollama / Qdrant 健康檢查 endpoint 慣例研究**：Epic 2（#3）實作前，應再次確認 Ollama（如 `/api/tags` 或其他官方推薦方式）與 Qdrant（`/healthz`/`/readyz`/`/livez`）當時推薦的健康檢查方式，避免寫死過時的 endpoint 路徑。Owner bucket：AI infra

## Blockers

無。本階段所有 GitHub 操作（讀取 #2-#8、編輯 #3-#8、重新讀取確認）皆正常完成，未遇到存取被阻擋的情況。Epic 2-7 六個 Epic 的 Decision 皆為「Refine existing issue」，沒有 Epic 被判定為 Blocked by missing GitHub access。
