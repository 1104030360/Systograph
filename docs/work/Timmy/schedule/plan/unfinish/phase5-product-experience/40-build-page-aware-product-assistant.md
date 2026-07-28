# Page-Aware Product Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將 disabled `ChatPanel` 升級為 page-aware explain-only assistant，幫使用者理解目前 viewer、map、trace、proposal、boundary context。

**Architecture:** Assistant 是產品解釋層，不是 scanner truth source。第一版只回答與目前頁面/產品文件/已遮罩 map summary 相關的問題，不自動執行 scan、trace、mapping decision 或 filesystem 讀取。

**Tech Stack:** FastAPI, Pydantic v2, React/TypeScript, existing LLM provider boundary only after safety checks, deterministic retrieval first.

---

## 最新狀態（2026-06-18）

- `frontend/src/components/ChatPanel.tsx` 仍是 disabled placeholder。
- 尚無 `POST /api/assistant/messages` route、assistant schemas、page context collector、assistant retrieval/generation service。
- GitHub #128 是 Future frontend+backend assistant issue。
- OWASP LLM Top 10 2025 要求特別注意 prompt injection、sensitive disclosure、excessive agency、unbounded consumption。

## Product phase

第一版只做 **Phase 1: Explain-only assistant**。

Allowed:

```text
explain selected node/edge/trace/risk/proposal/boundary state
summarize what the current page means
suggest next UI panel/action as text or safe UI suggestion
cite product docs/API/map summary
```

Not allowed:

```text
start scan
send boundary decision
accept/edit/reject mapping proposal
execute query trace
read raw source file
read arbitrary filesystem path
write canonical ai_system_map.json
create scanner facts
```

## Scope

- Backend assistant request/response schemas.
- Deterministic retrieval from product docs + API guide + redacted map summary.
- Optional LLM generation only behind same provider safety/masking/validation boundary; deterministic fallback must work.
- Frontend `collectPageContext()` with minimal redacted context.
- ChatPanel message state, citations, safe suggested actions.

## Out of scope

- 不做通用 chatbot。
- 不做 autonomous agent。
- 不做 long-term memory。
- 不做 raw source/code Q&A。
- 不做 tool calling without explicit user confirmation; first version has no state-changing actions.

### Task 1: Define assistant schemas

**Files:**
- Create: `src/systograph/core/models/assistant.py`
- Modify: `src/systograph/web/schemas.py`
- Test: `tests/unit/core/test_assistant_models.py`

- [ ] **Step 1: Add request/response model tests**

Request fields:

```text
project_id optional
scan_id optional
message
page_context
allowed_capabilities
```

Response fields:

```text
answer
citations
suggested_actions
safety_notes
```

- [ ] **Step 2: Reject raw source/snippet/path fields in page context**
- [ ] **Step 3: Validate suggested action types against allowlist**

### Task 2: Build deterministic assistant context service

**Files:**
- Create: `src/systograph/core/services/assistant_context_service.py`
- Test: `tests/unit/core/test_assistant_context_service.py`

- [ ] **Step 1: Collect product docs sections from allowlisted docs**

Allowed docs:

```text
docs/API-GUIDE.md
frontend/API_CONTRACT.md
docs/work/Meeting-Sync/meeting_sync_2026_06_12/frontend-sync.md
```

- [ ] **Step 2: Build redacted map summary from session store build result**
- [ ] **Step 3: Enforce max context size and section count**
- [ ] **Step 4: Assert no raw secret, raw source, or local absolute path enters context**

### Task 3: Implement explain-only assistant service

**Files:**
- Create: `src/systograph/core/services/product_assistant_service.py`
- Test: `tests/unit/core/test_product_assistant_service.py`

- [ ] **Step 1: Add deterministic keyword/section retrieval**
- [ ] **Step 2: Add answer template fallback with citations**
- [ ] **Step 3: Add optional LLM provider hook disabled by default**
- [ ] **Step 4: Validate generated answer for secret/path/source leakage before returning**
- [ ] **Step 5: Require at least one citation for non-empty answer**

### Task 4: Add backend route

**Files:**
- Create: `src/systograph/web/routes/assistant_routes.py`
- Modify: `src/systograph/web/app.py`
- Modify: `src/systograph/web/dependencies.py`
- Test: `tests/web/test_assistant_routes.py`

- [ ] **Step 1: Add `POST /api/assistant/messages`**
- [ ] **Step 2: Return deterministic answer when LLM provider disabled**
- [ ] **Step 3: Reject page context containing raw source/snippet/path**
- [ ] **Step 4: Ensure route does not read arbitrary file path or instantiate scanner providers**

### Task 5: Implement frontend page context collector

**Files:**
- Create: `frontend/src/services/assistantApi.ts`
- Create: `frontend/src/utils/pageContext.ts`
- Modify: `frontend/src/components/ChatPanel.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Define TypeScript types from OpenAPI generated types if Task 28 is complete**
- [ ] **Step 2: Collect minimal context**

Allowed context:

```text
route_or_view
data_source_mode
project_id
scan_id
selected kind/id
detail_mode
active_filters
scan_summary counts/status
visible_panel
available_actions
redacted labels/risk titles/evidence titles
```

- [ ] **Step 3: Do not include raw snippets, raw source, local absolute path, or full map JSON**
- [ ] **Step 4: Add loading/error/citations/suggestion UI**

### Task 6: Suggested actions allowlist

**Files:**
- Modify: `src/systograph/core/models/assistant.py`
- Modify: `frontend/src/components/ChatPanel.tsx`
- Test: `tests/unit/core/test_assistant_models.py`

- [ ] **Step 1: Allow only non-state-changing suggestions**

Initial actions:

```text
focus_node
open_detail_panel
open_mapping_proposal_panel
open_boundary_decision_panel
```

- [ ] **Step 2: Mark state-changing actions as rejected in Phase 1**

Rejected:

```text
start_scan
send_boundary_decision
accept_mapping_proposal
run_query_trace
```

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_assistant_models.py tests/unit/core/test_assistant_context_service.py tests/unit/core/test_product_assistant_service.py tests/web/test_assistant_routes.py -v
pnpm --dir frontend run build
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- ChatPanel can send a question and render answer/citations/safe suggestions.
- Assistant context contains only minimal redacted page/map/product-doc context.
- Backend response never contains raw secret, raw source, or unmanaged absolute path.
- Assistant does not create scanner facts or mutate canonical artifacts.
- Phase 1 rejects all state-changing actions.
