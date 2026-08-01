# GitHub #169 Provider Smoke Script Secret Exposure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/169

**Goal:** 決定兩支被 `.gitignore` 排除的 provider smoke scripts 是否納管，並避免 API key 出現在 curl command line 或 process list。

**Architecture:** Provider smoke tests 若保留，必須是 explicit opt-in、secret-safe、不可在 CI 預設執行。若不保留，應刪除/忽略並提供正式 trace 或 pytest mock 作替代。

**Tech Stack:** shell scripts, `.gitignore`, docs, secret handling best practices.

---

## Source

- GitHub issue #169, assignee Timmy.
- Origin: Backend findings L-13.
- Primary files: `.gitignore`, `scripts/test_mapping_proposal_llm.sh`, `scripts/test_nvidia_nim_direct.sh` if retained.
- Related plans: #138 secret masking, #143 dotenv/env isolation, #145 provider config trust boundary.

### Task 1: Audit current smoke script state

**Files:**
- Inspect: `.gitignore`
- Inspect: `scripts/test_mapping_proposal_llm.sh` if present locally
- Inspect: `scripts/test_nvidia_nim_direct.sh` if present locally

- [ ] **Step 1: Determine whether scripts exist and are intentionally ignored**
- [ ] **Step 2: Check if scripts pass key via argv, URL, echo, or logs**
- [ ] **Step 3: Decide retain vs remove based on project workflow**

### Task 2A: If retaining scripts, make them secret-safe

**Files:**
- Modify: `.gitignore`
- Add/Modify: retained scripts under `scripts/`
- Modify: `docs/API-GUIDE.md` or provider docs section

- [ ] **Step 1: Require key from env or stdin without echo**
- [ ] **Step 2: Avoid passing Authorization value in process argv when feasible**
- [ ] **Step 3: Add dry-run/masked output mode**
- [ ] **Step 4: Mark scripts opt-in and excluded from normal CI**

### Task 2B: If removing scripts, document replacement

**Files:**
- Modify: `.gitignore`
- Modify: `docs/API-GUIDE.md` or README provider section

- [ ] **Step 1: Remove stale ignore entries if scripts are gone**
- [ ] **Step 2: Point developers to pytest mocks or official trace scripts**
- [ ] **Step 3: Document that real provider calls require local explicit opt-in**

## Verification

```bash
rg -n "NVIDIA_API_KEY|OPENAI_API_KEY|Authorization: Bearer|curl" scripts docs README.md .gitignore
.venv/bin/pytest tests/web/test_nvidia_provider_app_wiring.py tests/unit/core/test_nvidia_nim_proposal_provider.py -v
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- The repository has a clear decision for both smoke scripts.
- No retained script exposes API keys through argv, echo, checked-in examples, or logs.
- Documentation explains safe provider smoke testing without requiring real keys in CI.
