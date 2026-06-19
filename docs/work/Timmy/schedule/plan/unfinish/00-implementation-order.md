# Unfinished Backend / AI Implementation Order

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement one plan at a time. Every implementation must use TDD + BDD and pass the plan-specific gate before starting the next dependency.

**Goal:** 以目前實際程式碼、測試、完成報告、GitHub backlog 與官方文件查證為準，提供唯一且可執行的後端／AI 計畫順序。

**Architecture:** GitHub 上已開出的 Timmy assigned bug/finding issues 必須先完成，依 Critical/High、Medium、Low 的風險順序收斂安全、正確性、契約與測試可攜性；之後才接續功能型 backend/AI plan。`ai_system_map.json` 持續是 canonical artifact，database、assistant、remote template 都不得取代它。

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, pytest, Ruff, mypy, React/TypeScript, PostgreSQL（後期）, SQLAlchemy 2.x（後期）, Alembic（後期）, Tree-sitter（後期、可選）。

---

## 目前實際基線（2026-06-18）

- Git：`main` / `69958bf02b01`。
- 完成文件：`plan/finish/01-*` 到 `plan/finish/25-implement-provider-config-mapping-matrix.md` 已存在；最新 report 顯示 Task 24 scan boundary review 與 Task 25 provider config mapping 已完成。
- 已完成 backend 主流程：map build、viewer projection、manual mapping、AI mapping proposal、detail scan、query trace、same-run scan boundary review、provider config mapping。
- `POST /api/projects/import` 目前只支援 `source_type="local_path"`；upload archive 尚未實作。
- `InMemorySessionStore` 仍同時承擔 project registry、latest map、build-result lookup；無 history API、TTL、容量上限、SQL repository。
- `pyproject.toml` 尚無 SQLAlchemy、Alembic、psycopg、Tree-sitter、Semgrep、openapi-typescript 相關 dependency。
- `OutputArtifactProvider` 只輸出 `map-error.md`，尚無 `map-error.json`。
- Code pattern scanner 目前是 TOML rule catalog + regex；沒有 bounded AST extraction 或 SAST/taint engine。
- `frontend/src/components/ChatPanel.tsx` 仍是 disabled placeholder；尚無 assistant API。
- GitHub open issues 已於 2026-06-18 查證：Timmy assigned bug/finding 修復為 #138 Critical、#139-#145 High、#146-#161 Medium、#162-#175 Low；Timmy assigned 非 bugfix 主線另有 #1-#12、#124-#128、#130；#176-#181 是 frontend issue，不納入本後端 bugfix queue。

## 官方來源查證（2026-06-18）

- Python `tarfile`：3.14 預設 extraction filter 改成 `data`，但文件仍提醒 extraction exception 後可能部分寫入、需自行 cleanup；本 repo 仍支援 Python 3.11，因此 upload plan 不可依賴 3.14 預設行為，必須手動逐 entry 驗證與寫入。
- FastAPI：client generation 依賴 OpenAPI `operationId`，且必須全域唯一；OpenAPI SDK plan 必須先穩定 operation IDs。
- SQLAlchemy 2.x：建議以 `with session.begin()` / `Session.begin()` 管理 transaction，成功 commit、例外 rollback；DB adapter plan 不應讓 route 層手動操作 ORM row。
- Alembic：migration environment 應以正式 Alembic layout/pyproject template 管理；不要手刻 ad hoc SQL migration script。
- PostgreSQL JSONB：`jsonb` 支援 containment、existence 與 indexing，但只在需要查詢 metadata 時使用；database 不可保存 raw source 或 full secret。
- Docker Compose：interpolation 先於 per-file merge；多 compose file 依指定順序 merge/override/add；profiles 讓服務依環境或用途選擇性啟用。
- Tree-sitter / Semgrep：Tree-sitter query 是 AST S-expression pattern；Semgrep rule 以 `rules`、`id`、`languages`、`pattern`、`severity` 等欄位描述，若未來支援只能做 adapter，不可讓外部工具 output 直接變 canonical fact。
- OWASP GenAI / LLM Top 10 2025：後續 AI assistant、安全引擎與 proposal prompt 必須納入 prompt injection、sensitive information disclosure、supply chain、excessive agency、vector/embedding weakness、unbounded consumption 等邊界。

## 編號規則

既有 Task 編號是歷史識別，不代表現在的執行順序。尤其 `finish/25-*` 與 `unfinish/25-*` 名稱重複，實作時必須以本文件的「執行序」與完整路徑為準。

## GitHub Bugfix Plan Index

以下 GitHub issue 皆已確認為 Timmy assigned，且已在 `plan/unfinish` 建立「一個 issue 一份 plan」。實作順序以本節與下方 Canonical Implementation Order 為準。

| Priority | GitHub Issues | Plan Files |
|---|---|---|
| Critical | #138 | `138-fix-unmasked-credentials-in-system-map-outputs.md` |
| High | #139-#145 | `139-fix-query-trace-ssrf-egress-policy.md` 到 `145-fix-proposal-provider-config-cwd-trust-boundary.md` |
| Medium | #146-#161 | `146-fix-scan-root-boundary-policy.md` 到 `161-fix-proposal-prompt-untrusted-evidence-isolation.md` |
| Low | #162-#175 | `162-add-proposal-provider-retry-backoff-policy.md` 到 `175-support-redacted-local-paths-in-api-responses.md` |

Low issues 不再視為旁支 backlog。它們仍低於 Critical/High/Medium，但必須在功能型 plans（Task 29+、session persistence、upload、remote template、assistant）之前完成或明確由 implementation report 說明 defer 原因。

## Canonical Implementation Order

| 執行序 | Gate / Plan | 目前定位 | 啟動條件 |
|---|---|---|---|
| 0 | `138-fix-unmasked-credentials-in-system-map-outputs.md` | Critical secret leak 會直接破壞 release-readiness 信任 | 立即 |
| 1 | GitHub #139-#145 per-issue plans | High severity SSRF、viewer path oracle、failure isolation、test/env isolation、CI、provider config trust boundary | #138 可同 branch 先行；不得等功能 plan |
| 2 | GitHub #146-#161 per-issue plans | Medium severity scan/output/trace 邊界、資源上限、錯誤契約、AI prompt trust boundary | Gate 0-1 完成 |
| 3 | GitHub #162-#175 per-issue plans | Low severity 但仍屬 bug/finding 修復：retry/backoff、timeout、concurrency、path、summary、docs、dependency、loopback、thread-safety、path redaction | Gate 2 完成；可在不衝突時與同域 Medium fix 合併 |
| 4 | `29-harden-secret-masking-and-validation.md` | 把 #138/#153/#154 收斂成 shared masking + independent validation defense | #138、#153、#154 完成或同 branch 已驗證 |
| 5 | `30-add-map-error-json-contract.md` | CLI/CI 需要穩定 machine-readable failure contract | #141、#148、#158 error model 固定 |
| 6 | `28-introduce-openapi-generated-frontend-sdk.md` | API error/response shape 穩定後建立 contract drift gate | #159 完成；#144 CI 可執行 |
| 7 | `31-expand-advanced-rag-fixtures.md` | 後續 provider/AST/security 演進前先建立 regression corpus | GitHub bugfix gates 完成 |
| 8 | `32-expand-dependency-manifest-and-lockfile-support.md` | Lockfile 是高價值 deterministic evidence；OSV/vulnerability awareness 必須 opt-in | Task 31 基礎 fixture 可用 |
| 9 | `33-expand-docker-compose-static-analysis.md` | 補 interpolation/profile/env_file/health/network semantics，但保持 read-only | #141 完成 |
| 10 | `34-add-bounded-ast-code-extraction.md` | 先建立 bounded AST foundation，再談 SAST/taint | Task 31 完成 |
| 11 | `35-build-contextual-security-engine.md` | 消費 AST/evidence graph，不重做 parser/rule catalog | Task 34 完成且 precision/recall 有基線 |
| 12 | `36-add-explicit-ignored-file-includes.md` | 高風險 optional feature；只能在 scan boundary 與 masking 穩定後做 | #138、#146、#152 完成且有真實需求 |
| 13 | `26-implement-persistent-session-store-and-scan-history.md` | 先固定 domain、retention、repository port，不先綁 ORM | #150、#174 完成 |
| 14 | `27-introduce-database-backed-storage-layer.md` | PostgreSQL adapter 與 migrations 實作 Task 26 的 port | Task 26 contract freeze |
| 15 | `25-implement-project-upload-ingestion.md` | Archive ingestion 需要成熟 path/resource/retention policy | #140、#142、#146、#147、#152 完成；Task 26 完成 |
| 16 | `37-add-scan-profile-catalog.md` | 先支援 local data-only profile，不改 remote trust boundary | Task 28 完成 |
| 17 | `38-add-remote-template-import.md` | 需要 provenance、digest、egress、schema migration | Task 37 完成 |
| 18 | `39-add-multimodal-rag-scanner-support.md` | 先以 extension/unmapped 表達，不破壞 `rag-core-v1` | Task 31、34 完成 |
| 19 | `40-build-page-aware-product-assistant.md` | 最後做產品加值；第一版 explain-only、無 autonomous action | Task 28 完成；前端 project/scan flow 可提供 context |

## 不納入後端主線的工作

- Frontend #176-#181 由 Bo Han 執行，不作為本後端主線文件的直接實作項目。
- GitHub #1-#12、#124-#128、#130 屬 Epic、Post Epic、future 或 research 類型；本輪不混入 bugfix queue。若後端 contract 有變動，要先同步 `docs/API-GUIDE.md` 與 `frontend/API_CONTRACT.md`。

## 執行規則

1. 每次只啟動一個具有共同 contract 的計畫；可平行的工作必須有不重疊檔案與明確 integration gate。
2. 每個計畫先寫 failing tests，再做最小實作，再跑 focused tests、full pytest、Ruff、mypy。
3. Scanner provider 只能讀 `FileInventory` 已授權的檔案；不得自行擴張 filesystem boundary。
4. 任何 network access 預設關閉，必須明確 opt-in、限制 egress、timeout、response size，並記錄 uncertainty。
5. 不把 AI 產生內容當 scanner fact；AI output 必須經 deterministic schema、allowlist 與 secret validation。
6. 不把 database、viewer projection、assistant response 當 canonical truth；canonical truth 仍是 validated `ai_system_map.json`。
7. 若計畫需要修改 `ai-system-map/v1`，必須先寫 migration note 與 backward-compatibility tests。
8. 所有 API/doc 更新都要 trace 實際 route/schema/script，不得只依 plan 文字改文件。

## 每個計畫的共同完成 Gate

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
git status --short
```

Expected:

```text
all backend tests passed
ruff: no issues
mypy: Success
git diff --check exits 0
only intentional files are changed
```
