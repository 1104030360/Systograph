# 2026-07-10 00A Code Review P1 Fixes TODO

## 目標

依 code review findings 修正 00A（ai-system-map/v2 compatibility）的
Standards P1 / Spec P1 / Spec P2 問題。不切換 active output；不 commit/push。

## 現況盤點

| Finding | 嚴重度 | 狀態 |
|---------|--------|------|
| native v2 缺 secret/path boundary | Standards P1 | fixed |
| WorkflowJsonProvider label 未遮罩 | Standards P1 | fixed |
| Workflow ID 跨檔碰撞 | Standards P1 | fixed |
| observed/detected edge 可無 evidence | Standards P1 | fixed |
| Ruff/Mypy gate 未過 | Standards P1 | fixed |
| adapter 非 deterministic | Spec P1 | fixed |
| legacy candidate 升格 + facts 遺失 | Spec P1 | fixed |
| 00A Task 4/5 勾選與 REP 衝突 | Spec P1 | fixed |
| precondition 改回 requested=v1 | Spec P2 | fixed |

## 實作邏輯

1. **Never break userspace**：active artifact 仍 v1；opt-in v2 行為不變。
2. **重用既有安全邊界**：抽出 `SystemMapSecretBoundary` 給 v1/v2。
3. **Workflow facts**：path-namespaced IDs + label masking + 單檔 duplicate reject。
4. **Edge evidence**：observed/detected 至少一筆；未知用 undetermined + reason。
5. **Candidate 語意**：未確認 extension 不得自動 confirmed/enabled；canonical 保留
   candidate_facts / confirmed_by_user。
6. **文件誠實**：未完成項改回 `[ ]`；REP 不宣稱假通過。
7. **TDD**：每條 finding 先寫失敗測試，再最小修法。

## 步驟

### A. 文件與基線

- [x] 寫本 TODO
- [x] 盤點相關 tests / fixtures / schema
- [x] 修正 00A plan Task 4/5 與 REP 不實勾選（finding 8）

### B. Standards P1（TDD）

- [x] Finding 1：native v2 secret/path regression tests → validator
- [x] Finding 2：secret-label masking test → WorkflowJsonProvider
- [x] Finding 3：cross-file ID + duplicate ParseIssue tests → provider
- [x] Finding 4：edge evidence required tests → validator + model
- [x] Finding 5：修 E501 / Literal.__args__；跑 ruff + mypy

### C. Spec P1/P2（TDD）

- [x] Finding 6：slot-order deterministic regression → adapter
- [x] Finding 7：candidate state + candidate_facts on canonical → model/schema/adapter
- [x] Finding 9：precondition requested_schema_version error-path test → MapBuildService

### D. 驗證

- [x] `uv run pytest` 相關 unit/contracts/integration/web/cli（177 passed）
- [x] `uv run ruff check` + format check（touched）
- [x] `uv run mypy`（touched scope）
- [x] 寫 REP：finding 對照表、結果、剩餘風險

## 驗收標準

- [x] 九條 findings 皆 fixed
- [x] 相關測試綠；ruff/mypy 通過
- [x] active output 仍 v1；CLI help 未宣稱 cutover
- [x] TODO/REP 以繁體中文清楚分區

## 風險與注意

- Viewer / profile / readiness 仍未改讀 normalized（不可當 Gate-0 通過）
- readiness findings equivalence 仍 deferred
- Workflow provider 尚未接入預設 scan pipeline
