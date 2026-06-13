# Phase 1 Epic 2-7 Roadmap Solidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 根據目前實作進度與 repo 證據，重新檢查 GitHub Epic 2 到 Epic 7 的既有 issue，修正不符合現實的目標，補上能讓產品更好、更容易試用、更容易理解、更容易貢獻的新目標。

**Architecture:** 先建立「目前實作進度 baseline」，再用 baseline 對照 GitHub Epic 2 到 Epic 7 的 title、body、checklist、acceptance criteria。所有結論必須分成 repo 實際觀察、GitHub issue 現況、外部最佳實踐建議、建議修改內容；本階段只修改 roadmap / issue / TODO / Report，不修改功能程式碼。

**Tech Stack:** GitHub CLI 或 GitHub MCP、`rg` / shell、repo docs、Python backend `pytest` / `ruff` / `mypy`、frontend `pnpm run lint` / `pnpm run build`、Context7 / web research for current official docs and AI best practices when needed.

---

## Scope

本計畫處理的是 roadmap solidation，不是功能實作。

要做的事：

- 讀目前 repo 的實際 code、docs、tests、scripts。
- 讀 `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/check-list/principles.md`。
- 讀本計畫檔與 `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/solidate-MyPlan/solifate-prompt/check1.md`。
- 查 GitHub repo `1104030360/Local-AI-Health-Doctor` 上實際存在的 Epic 2 到 Epic 7 issues。
- 根據目前實作進度，判斷每個 Epic 是否要 refine、修正文案、補新目標、補驗收標準、調整 scope、或拆出後續 issue。
- 直接修改 GitHub issue 內容；若權限或認證阻擋，輸出可貼上的 replacement body。
- 建立 TODO / Report，記錄證據、修改摘要、仍未修補的風險與後續建議。

不要做的事：

- 不修改功能程式碼。
- 不直接修補 scanner、frontend、backend、AI provider、storage、API、tests。
- 不把 sample、placeholder、mock progress、in-memory state 寫成 production-ready。
- 不把 KAI-Mind 寫成 chatbot、RAG builder、完整 observability 平台、企業級資安掃描器或模型 serving 平台。
- 不把後續 backlog 任意塞進既有 Epic 2；必須先確認 GitHub 上 Epic 2 的真實 scope。

## Files And External Targets

**Read:**

- `/Users/linjunting/Local_AI_Health_Doctor/AGENTS.md`
- `/Users/linjunting/Local_AI_Health_Doctor/.cursor/rules/linus_torvalds.mdc`
- `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/check-list/principles.md`
- `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/solidate-MyPlan/solifate-prompt/check1.md`
- `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/finish`
- `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish`
- `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/design`
- `/Users/linjunting/Local_AI_Health_Doctor/docs/API-GUIDE.md`
- `/Users/linjunting/Local_AI_Health_Doctor/frontend/API_CONTRACT.md`
- `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Bo-han`
- `/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind`
- `/Users/linjunting/Local_AI_Health_Doctor/frontend/src`
- `/Users/linjunting/Local_AI_Health_Doctor/tests`
- `/Users/linjunting/Local_AI_Health_Doctor/scripts`

**Modify or create during execution:**

- `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/solidate-MyPlan/todo/phase1-solidate-todo.md`
- `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/solidate-MyPlan/report/phase1-solidate-report.md`

**External targets to inspect and possibly modify:**

- GitHub repo: `1104030360/Local-AI-Health-Doctor`
- GitHub issues: actual Epic 2, Epic 3, Epic 4, Epic 5, Epic 6, Epic 7 issues as discovered from GitHub. Do not assume issue numbers.

## Evidence Rules

- Repo evidence must cite exact files, command output, or test/script names.
- GitHub evidence must cite issue number, title, current body section, and checked timestamp.
- External best-practice evidence must cite source URL and query/check date.
- If a claim is an inference, label it as inference.
- If a source is unavailable because auth/network/tooling failed, record the blocker and do not pretend the check succeeded.
- Every Epic must have one of these outcomes:
  - `No change needed`
  - `Refine existing issue`
  - `Add goals to existing issue`
  - `Split into follow-up issue candidate`
  - `Blocked by missing GitHub access`

## Stop Conditions

The task is complete only when all of these are true:

- Epic 2 to Epic 7 were each inspected from actual GitHub issue content.
- Current implementation baseline was built from repo files, not memory alone.
- Every Epic has a decision and evidence.
- Every GitHub issue that needed revision was updated, or a ready-to-paste replacement was written into the Report.
- TODO and Report files exist under `solidate-MyPlan/todo` and `solidate-MyPlan/report`.
- Report includes a final gap audit: what goals are still missing, what goals should not be added yet, and which product improvements would most improve adoption.

---

### Task 1: Bootstrap Context And Guardrails

**Files:**

- Read: `/Users/linjunting/Local_AI_Health_Doctor/AGENTS.md`
- Read: `/Users/linjunting/Local_AI_Health_Doctor/.cursor/rules/linus_torvalds.mdc`
- Read: `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/check-list/principles.md`
- Read: `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/solidate-MyPlan/solifate-prompt/check1.md`
- Modify: `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/solidate-MyPlan/report/phase1-solidate-report.md`

- [x] **Step 1: Read project rules and prompt**

Run:

```bash
sed -n '1,220p' AGENTS.md
sed -n '1,240p' .cursor/rules/linus_torvalds.mdc
sed -n '1,260p' docs/work/Timmy/schedule/fable-5/check-list/principles.md
sed -n '1,820p' docs/work/Timmy/schedule/fable-5/solidate-MyPlan/solifate-prompt/check1.md
```

Expected:

- Product positioning is confirmed as AI Agent / RAG Release Readiness Gate.
- Audit-only boundary is confirmed.
- Linus-style review means practical scope, simple source of truth, backward compatibility, and no invented problems.

- [x] **Step 2: Create the report shell**

Create or update:

```markdown
# Phase 1 Epic 2-7 Roadmap Solidation Report

## Executive Summary

## Inputs Checked

## Current Implementation Baseline

## GitHub Epic Inventory

## Epic Review Matrix

## GitHub Issue Changes

## New Goal Candidates

## Rejected Or Deferred Goals

## Risks And Follow-Up Items

## Final Gap Audit
```

Acceptance:

- Report exists before issue edits begin.
- Later tasks append evidence instead of relying on chat history.

### Task 2: Build Current Implementation Baseline

**Files:**

- Read: `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/finish`
- Read: `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish`
- Read: `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/design`
- Read: `/Users/linjunting/Local_AI_Health_Doctor/docs/API-GUIDE.md`
- Read: `/Users/linjunting/Local_AI_Health_Doctor/frontend/API_CONTRACT.md`
- Read: `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Bo-han`
- Read: `/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind`
- Read: `/Users/linjunting/Local_AI_Health_Doctor/frontend/src`
- Read: `/Users/linjunting/Local_AI_Health_Doctor/tests`
- Read: `/Users/linjunting/Local_AI_Health_Doctor/scripts`
- Modify: `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/solidate-MyPlan/report/phase1-solidate-report.md`

- [x] **Step 1: Inventory finished and unfinished plans**

Run:

```bash
find docs/work/Timmy/schedule/plan/finish -maxdepth 1 -type f | sort
find docs/work/Timmy/schedule/plan/unfinish -maxdepth 1 -type f | sort
find docs/work/Bo-han/schedule/plan -maxdepth 3 -type f | sort
```

Expected:

- Finished backend tasks and unfinished frontend/backend follow-ups are visible.
- Bo-han frontend finished/unfinish state is visible.

- [x] **Step 2: Inspect current backend surface**

Run:

```bash
rg -n "include_router|MapBuildService|ProjectScanService|ScanBoundaryReviewService|MappingProposalService|DetailScanService|QueryTraceService|InMemorySessionStore" src/kai_mind docs/API-GUIDE.md scripts tests
```

Record:

- What backend flows are implemented.
- Which APIs are local-only.
- Which flows are explicit opt-in.
- Which storage/session pieces are still in-memory or unfinished.

- [x] **Step 3: Inspect current frontend surface**

Run:

```bash
rg -n "loadApiViewerPayload|loadSampleViewerPayload|EventSource|detail_scan_result_sample|mapping_proposal_result_sample|project_id|scan_id|boundary|proposal|createDetailScan|createMappingProposal" frontend/src frontend/API_CONTRACT.md docs/work/Bo-han
```

Record:

- What is real API integration.
- What is sample-only or placeholder.
- What frontend user flows are not complete yet.
- Whether frontend tests exist or are still missing.

- [x] **Step 4: Write the baseline table**

Add this table to the Report:

```markdown
| Area | Current reality | Evidence | Do not overclaim |
|---|---|---|---|
| Backend L1 map build |  |  |  |
| Scan boundary decision |  |  |  |
| Manual mapping |  |  |  |
| AI mapping proposal |  |  |  |
| Detail scan |  |  |  |
| Query trace |  |  |  |
| Viewer API |  |  |  |
| Frontend project scan flow |  |  |  |
| Frontend detail/proposal flow |  |  |  |
| Persistent session / scan history |  |  |  |
| Database-backed storage |  |  |  |
| OpenAPI generated SDK |  |  |  |
| Testing / eval / regression |  |  |  |
```

Acceptance:

- Baseline separates implemented, partial, sample-only, and not implemented.
- Baseline is enough to prevent GitHub issue bodies from claiming false progress.

### Task 3: Discover GitHub Epic 2-7 Issues

**Files / external targets:**

- External: GitHub repo `1104030360/Local-AI-Health-Doctor`
- Modify: `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/solidate-MyPlan/report/phase1-solidate-report.md`

- [x] **Step 1: Confirm GitHub authentication**

Run:

```bash
gh auth status
```

Expected:

- If authenticated, continue.
- If not authenticated, record blocker in Report and prepare replacement issue bodies locally instead of pretending issues were edited.

- [x] **Step 2: List actual Epic issues**

Run:

```bash
gh issue list --repo 1104030360/Local-AI-Health-Doctor --state all --search "Epic" --limit 100
```

Expected:

- Actual Epic 2 to Epic 7 issue numbers and titles are discovered.
- Existing Epic 2 scope is confirmed before any relabeling.

- [x] **Step 3: Fetch each Epic body**

For each discovered Epic 2 to Epic 7 issue:

```bash
gh issue view <ISSUE_NUMBER> --repo 1104030360/Local-AI-Health-Doctor --json number,title,state,body,labels,assignees,comments,url
```

Record in Report:

```markdown
| Epic | Issue | Current title | Current scope summary | Risk before edit |
|---|---:|---|---|---|
| Epic 2 | # |  |  |  |
| Epic 3 | # |  |  |  |
| Epic 4 | # |  |  |  |
| Epic 5 | # |  |  |  |
| Epic 6 | # |  |  |  |
| Epic 7 | # |  |  |  |
```

Acceptance:

- No Epic number is assumed from memory.
- Report contains issue URLs or issue numbers for every inspected Epic.

### Task 4: Review Each Epic Against Current Reality

**Files / external targets:**

- Read: repo baseline from Task 2
- Read: GitHub issue bodies from Task 3
- Modify: `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/solidate-MyPlan/report/phase1-solidate-report.md`

- [x] **Step 1: Apply the same review rubric to every Epic**

For each Epic 2 to Epic 7, answer:

```markdown
## Epic N Review

### Repo Reality
- Implemented:
- Partial:
- Missing:
- Must not claim:

### Issue Alignment
- Accurate:
- Misleading:
- Missing product goal:
- Missing acceptance criteria:
- Scope conflict:

### User / Adoption Value
- Helps first-time users because:
- Helps demo / evaluation because:
- Helps contributors because:
- Still weak because:

### Decision
Outcome: No change needed / Refine existing issue / Add goals to existing issue / Split follow-up issue candidate / Blocked
Reason:
```

- [x] **Step 2: Check product-positioning mistakes**

For each Epic, explicitly check whether it incorrectly turns the product into:

- chatbot
- RAG builder
- full observability platform
- enterprise security scanner
- model serving platform
- generic AI agent platform

Record any mismatch as a roadmap issue, not a code bug.

- [x] **Step 3: Check source-of-truth mistakes**

For each Epic, explicitly check whether it blurs these boundaries:

- `ai_system_map.json` vs viewer projection
- scan boundary decision vs manual mapping decision
- mapping proposal vs accepted manual mapping
- query trace vs default scanner
- local in-memory session vs persistent storage
- sample data vs real API integration

Record each mismatch with repo evidence.

Acceptance:

- Every Epic has a completed review section.
- Every conclusion is tied to baseline evidence or GitHub issue text.

### Task 5: Add Product-Improvement Goals Where They Fit

**Files / external targets:**

- Read: Report review sections
- Modify: GitHub Epic 2 to Epic 7 issues when appropriate
- Modify: `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/solidate-MyPlan/report/phase1-solidate-report.md`

- [x] **Step 1: Identify adoption-focused gaps**

Look for goals that make the product better without expanding it into the wrong product category:

- first-run onboarding and local setup clarity
- example project scan flow
- project import -> scan -> boundary decision -> viewer refresh loop
- clearer readiness report and recommended next checks
- reproducible demo fixture
- frontend error states that do not hide backend truth
- contract drift prevention between backend and frontend
- evidence-backed issue / risk explanations
- local-only safety defaults
- contributor-friendly architecture docs
- regression tests for key user flows

Record each candidate as:

```markdown
| Candidate goal | Best Epic | Why it improves product | Repo evidence | Risk if added too early |
|---|---|---|---|---|
```

- [x] **Step 2: Reject goals that are attractive but wrong for this product**

Explicitly reject or defer goals like:

- general chatbot experience
- full RAG-building workflow
- enterprise SIEM / full observability
- arbitrary runtime probing by default
- long-term scan boundary policy store before user model is stable
- model serving / orchestration platform features not needed for release readiness

Record each rejected goal with a short reason.

- [x] **Step 3: Decide whether to edit Epic or create follow-up candidate**

Use this rule:

- If the goal improves the Epic's existing outcome, add it to that Epic.
- If it changes ownership or delivery boundary, record it as follow-up issue candidate.
- If it belongs to an already-reserved Epic namespace, do not relabel it without evidence.

Acceptance:

- New goals are user-value-driven, not technology shopping.
- Every suggested goal has a concrete acceptance criterion.

### Task 6: Draft And Apply GitHub Issue Edits

**Files / external targets:**

- Modify: GitHub Epic 2 to Epic 7 issues
- Modify: `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/solidate-MyPlan/report/phase1-solidate-report.md`

- [x] **Step 1: Draft issue replacement sections**

For each Epic that needs changes, draft:

```markdown
## Goal

## Current Reality

## Scope

## Non-Goals

## Acceptance Criteria

## Evidence To Preserve

## Follow-Up Candidates
```

Rules:

- Keep title/body practical and specific.
- Keep acceptance criteria checkable.
- Keep non-goals explicit.
- Keep frontend/backend/shared ownership visible when relevant.
- Do not remove useful historical context unless it is misleading.

- [x] **Step 2: Apply edits with `gh issue edit`**

For each issue:

```bash
gh issue edit <ISSUE_NUMBER> --repo 1104030360/Local-AI-Health-Doctor --title "<REFINED_TITLE>" --body-file <TEMP_BODY_FILE>
```

If writing a temp body file is not convenient, use GitHub MCP or another safe non-secret method. Do not expose secrets in issue body.

- [x] **Step 3: Re-read edited issue**

Run:

```bash
gh issue view <ISSUE_NUMBER> --repo 1104030360/Local-AI-Health-Doctor --json number,title,body,url
```

Acceptance:

- The edited issue no longer contradicts repo baseline.
- The edited issue has clear goals, non-goals, and acceptance criteria.
- Report records the before/after summary.

### Task 7: Write TODO And Final Report

**Files:**

- Create or modify: `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/solidate-MyPlan/todo/phase1-solidate-todo.md`
- Modify: `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/solidate-MyPlan/report/phase1-solidate-report.md`

- [x] **Step 1: Write TODO**

The TODO file must contain:

```markdown
# Phase 1 Epic 2-7 Solidation TODO

## GitHub Issue Follow-Ups

## Product Goals Added Or Proposed

## Code Fixes Not Performed In This Phase

## Test / Verification Follow-Ups

## Research Follow-Ups

## Blockers
```

Each item must include:

- issue number or repo path
- problem
- impact
- evidence
- suggested next action
- owner bucket: Frontend / Backend / Shared contract / AI backend / AI infra / AI application / Security / Docs

- [x] **Step 2: Finish report**

The Report must include:

- input files checked
- commands run
- GitHub issues inspected
- per-Epic decision
- issue edit summary
- product-improvement goals added
- goals rejected or deferred
- evidence table
- external sources and check date
- final gap audit

- [x] **Step 3: Check for overclaims**

Search the Report and TODO for forbidden overclaims:

```bash
rg -n "production-ready|已完成|persistent|database|chat 已完成|scan history|always_skip|metadata_only|完整 observability|企業級資安|model serving" docs/work/Timmy/schedule/fable-5/solidate-MyPlan/todo docs/work/Timmy/schedule/fable-5/solidate-MyPlan/report
```

Expected:

- Any appearance is either evidence-backed or clearly marked as not implemented / deferred.

### Task 8: Verification And Closure

**Files / external targets:**

- Check: GitHub Epic 2 to Epic 7 issues
- Check: TODO / Report
- Check: git diff

- [x] **Step 1: Run document hygiene check**

Run:

```bash
git diff --check -- docs/work/Timmy/schedule/fable-5/solidate-MyPlan
```

Expected:

- No trailing whitespace or patch hygiene errors.

- [x] **Step 2: Verify no functional code changed**

Run:

```bash
git status --short
```

Expected:

- Changes are limited to roadmap prompt / plan / TODO / Report docs unless the user explicitly approved additional work.

- [x] **Step 3: Verify all Epic outcomes are recorded**

Report must include this final table:

```markdown
| Epic | Issue | Outcome | Edited? | New goals added? | Follow-up candidates | Blocker |
|---|---:|---|---|---|---|---|
| Epic 2 | # |  |  |  |  |  |
| Epic 3 | # |  |  |  |  |  |
| Epic 4 | # |  |  |  |  |  |
| Epic 5 | # |  |  |  |  |  |
| Epic 6 | # |  |  |  |  |  |
| Epic 7 | # |  |  |  |  |  |
```

Acceptance:

- A future worker can tell exactly which GitHub issues changed and why.
- If no issue changed, the report explains why no change was needed or why the work was blocked.
- The final answer to the user links the plan, TODO, Report, and edited GitHub issues.
