# Future Epic: Advanced Contextual Security Engine (SAST & RAG)

## 1. 背景與目標 (Background & Objectives)

在 Epic 1（Task 14）中，KAI-Mind 的風險提示（Risk Hint）採用了「MVP」策略：
- **Hard code in Python**：規則寫死在 `if/else` 邏輯中。
- **Component + Evidence**：單純基於「是否存在該元件」與「設定檔/原始碼字串特徵」來發出靜態提示。

這達成了初步的 Release-Readiness 檢查。然而，為了降低誤判率（False Positives）並提供更深度的 AI/RAG 安全防護，KAI-Mind 未來必須演進為「進階上下文安全引擎（Contextual Security Engine）」。

本計畫紀錄未來應實作的高階架構演進與進階判斷條件。

---

## 2. 架構演進：Policy as Code (Rules Engine)

為了支援未來可能增長的數十至數百條安全規則，系統必須將「規則邏輯」從主程式中解耦。

### 預期重構方向：
1. **Inference Engine（推理引擎）**：Python 主程式只負責解析規則與比對 AST / System Map 狀態。
2. **Knowledge Base（知識庫）**：將所有 Risk Hint 的觸發條件（Condition）、說明（Rationale）、不確定性（Uncertainty）與嚴重度（Severity）全部外部化至 `risk_hint_rules.toml` 或 YAML 中。
3. **動態載入與擴充**：允許使用者自定義專屬企業內部的安全掃描規則，而無需修改 KAI-Mind 核心程式碼。

---

## 3. 進階掃描條件 (Advanced Assessment Capabilities)

未來的 Risk Hint 不能只看「證據存在與否」，必須具備程式碼與架構深度的理解能力：

### 3.1 可達性分析 (Reachability Analysis)
- **問題**：目前只要程式碼裡寫了 `chromadb.HttpClient(...)` 就會報警，即便該函數從未被呼叫過。
- **未來解法**：建立控制流圖（Control Flow Graph），追蹤有風險的元件/設定是否真的能在執行期被觸發。過濾掉 Unreachable Code 以降低誤判。

### 3.2 污點與資料流分析 (Taint & Data Flow Analysis)
- **問題**：目前無法確認使用者輸入是否有被清洗過再交給 LLM（Prompt Injection 風險）。
- **未來解法**：追蹤外部輸入（Source，如 API 請求）到危險操作（Sink，如 LLM Call 或 DB Query）的資料流。確認資料傳遞過程中是否有經過 Sanitizer（資料清洗模組）。

---

## 4. RAG 特有的安全防護條件 (RAG-Specific Security)

針對 LLM 與 RAG 應用程式，未來的掃描必須涵蓋 OWASP Top 10 for LLM Applications 的核心風險：

### 4.1 向量庫權限與個資遮蔽 (RBAC & PII Redaction)
- **掃描目標**：在偵測到 Vector Store（如 Qdrant / Chroma）的寫入操作（`add_documents`）時，檢查前方是否有 PII（個人可識別資訊）遮蔽或過濾的元件。
- **風險**：缺乏資料清理的 RAG 會導致訓練資料或索引資料外洩（Data Leakage）。

### 4.2 護欄機制偵測 (Guardrails Presence)
- **掃描目標**：偵測系統架構（Flows）中，LLM 的 Input / Output 是否有經過護欄機制（如 `NeMo Guardrails`, `LlamaGuard`）。
- **影響**：若系統架構包含護欄機制，原先的高風險提示（如 Prompt Injection）可以被智能降級（Downgraded Severity）。

---

## 5. 為什麼現在（Epic 1）不做？

此計畫歸檔於 `future`，因為：
1. **運算與開發成本過高**：建置 AST 分析與 Taint Analysis 需要巨大的運算資源與開發時間，不符合 MVP 快速交付的原則。
2. **YAGNI (You Aren't Gonna Need It)**：在確認 KAI-Mind 基本價值主張被使用者接受前，過早開發複雜的規則引擎屬於過度工程化（Over-engineering）。
3. **保持純靜態與快速**：目前的設計優先確保掃描過程無副作用、快速且高度可測試。進階功能應作為未來的可選模組（Opt-in features）提供。
