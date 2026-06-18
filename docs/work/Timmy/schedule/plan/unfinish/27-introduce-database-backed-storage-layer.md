# PostgreSQL-Backed Storage Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 為 Task 26 已凍結的 repository ports 實作 PostgreSQL persistence，保存 project/scan history、manual mapping 與 safe artifact metadata，同時保留 JSON artifact 為 canonical truth。

**Architecture:** SQLAlchemy ORM 與 Alembic 只存在 storage adapter；transaction boundary 位於 application service/use-case 外層，route 不接觸 ORM rows。PostgreSQL-first 決策保留，但 pgvector 不再是第一個 history migration 的必要條件；只有 Task 40 或其他已核准 semantic retrieval use case 才新增 vector migration。

**Tech Stack:** SQLAlchemy 2.x, Alembic, PostgreSQL, psycopg 3, pytest.

---

## 最新狀態（2026-06-18）

- `pyproject.toml` 無 SQLAlchemy/Alembic/psycopg runtime dependencies。
- 無 database config、ORM、migration 或 PostgreSQL tests。
- `src/kai_mind/storage/repositories.py` 目前只有 manual mapping 的 in-memory boundary。
- GitHub issue：[#127](https://github.com/1104030360/Local-AI-Health-Doctor/issues/127)。
- 官方文件查證（2026-06-18）：SQLAlchemy 2.x transaction 應優先使用 `Session.begin()` / context manager；Alembic 應使用正式 migration environment；PostgreSQL `jsonb` 只在需要查詢 metadata 時使用，不能拿來保存 raw source 或 full secret。

## Important correction

舊計畫把 session domain、history API、PostgreSQL、manual mapping、pgvector、seed script一次塞進同一任務，範圍過大且與 Task 26 重複。新版邊界：

- Task 26：domain/service/repository protocol/retention semantics。
- Task 27：PostgreSQL adapter、migration、transaction wiring、restart persistence。
- Task 40：若 explain-only assistant 後續真的需要 semantic retrieval，再新增 pgvector；不以「未來可能需要」為由阻塞基本 persistence。

### Task 1: Add storage settings and dependencies

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `src/kai_mind/config/storage.py`
- Test: `tests/unit/storage/test_storage_config.py`

- [ ] **Step 1: Write red tests for missing/invalid database URL**
- [ ] **Step 2: Add bounded settings; tests must inject URL and never read developer `.env` implicitly**
- [ ] **Step 3: Add SQLAlchemy 2.x, Alembic, and psycopg dependencies**

### Task 2: Create ORM schema and initial migration

**Files:**
- Create: `src/kai_mind/storage/database.py`
- Create: `src/kai_mind/storage/orm.py`
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/versions/0001_session_history.py`
- Test: `tests/integration/storage/test_migrations.py`

- [ ] **Step 1: Write migration upgrade/downgrade smoke test**
- [ ] **Step 2: Create tables for projects, scans, manual mappings, and artifact metadata**
- [ ] **Step 3: Store masked JSON metadata with JSONB only where querying is required**
- [ ] **Step 4: Do not create vector extension/table in migration 0001**

### Task 3: Implement repository adapters

**Files:**
- Create: `src/kai_mind/storage/postgres_repositories.py`
- Modify: `src/kai_mind/storage/repositories.py`
- Test: `tests/integration/storage/test_postgres_repositories.py`

- [ ] **Step 1: Write repository contract tests shared by in-memory and PostgreSQL adapters**
- [ ] **Step 2: Implement explicit domain ↔ ORM mapping**
- [ ] **Step 3: Use `with Session.begin()` at the outer transaction boundary**
- [ ] **Step 4: Ensure ORM rows never leave the storage package**

### Task 4: Wire app dependency injection

**Files:**
- Modify: `src/kai_mind/web/app.py`
- Modify: `src/kai_mind/web/dependencies.py`
- Modify: `src/kai_mind/core/services/manual_mapping_service.py`
- Test: `tests/web/test_storage_app_wiring.py`

- [ ] **Step 1: Write tests for in-memory default and explicit PostgreSQL mode**
- [ ] **Step 2: Construct repositories once per app and sessions per use case/request**
- [ ] **Step 3: Verify app recreation can reload project, scan, and mapping records**

### Task 5: Add local development and CI workflow

**Files:**
- Create: `docker-compose.storage.yml`
- Modify: `.github/workflows/ci.yml`
- Modify: `docs/API-GUIDE.md`

- [ ] **Step 1: Add PostgreSQL healthcheck and non-production credentials**
- [ ] **Step 2: Run migration before integration tests**
- [ ] **Step 3: Document backup/retention limitations and local-only default**

## Verification

```bash
.venv/bin/pytest tests/unit/storage tests/integration/storage tests/web/test_storage_app_wiring.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## Acceptance Criteria

- Service restart preserves project/scan/mapping metadata.
- Routes and core services do not import SQLAlchemy ORM classes.
- Failed transactions rollback and release sessions.
- `ai_system_map.json` remains generated and schema validated.
- Database stores no raw source code or full secret.
- pgvector is introduced only with a concrete, tested vector-use plan.

## Official references

- SQLAlchemy 2.x session/transaction patterns: https://docs.sqlalchemy.org/en/20/orm/session.html
- SQLAlchemy 2.x transaction context manager: https://docs.sqlalchemy.org/en/20/orm/session_transaction.html
- Alembic migrations: https://alembic.sqlalchemy.org/en/latest/
- PostgreSQL JSONB: https://www.postgresql.org/docs/current/datatype-json.html
