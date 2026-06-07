# Database-Backed Storage Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將 KAI-Mind 目前以 JSON artifact / in-memory session 為主的儲存方式，一次導入 PostgreSQL-backed storage，讓 session、scan history、manual mapping、map snapshot metadata、未來 AI embedding / vector search metadata 可以持久化與查詢，同時保留 `ai_system_map.json` 作為穩定對外 contract。

**Architecture:** 採 storage repository abstraction 先切開 core/web 與實際儲存媒介，再用 PostgreSQL + pgvector + SQLAlchemy 2.0 + Alembic migration 作為預設資料庫。`OutputArtifactProvider` 仍負責輸出 `ai_system_map.json` / `ai_system_map.md`，database 先保存可查詢 metadata、safe snapshot、manual decisions、artifact references 與未來 AI vector records，不把 database 變成 scanner 的唯一 truth source。

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, PostgreSQL, pgvector, psycopg, pytest, Ruff, mypy.

---

## Why This Plan Exists

目前 repo 已有三種「儲存」形態：

1. `OutputArtifactProvider` 會把 validated `RagSystemMap` 寫成 `ai_system_map.json`，並把 Markdown report 寫成 `ai_system_map.md`。
2. `InMemorySessionStore` 只在單一 backend process 內保存 `ProjectRecord`、latest viewer payload、latest build result。
3. Task 19 / Task 26 已規劃 KAI-Mind-managed store 與 persistent session/history，但尚未定案資料庫方案。

未來轉 database 時不能直接刪掉 JSON，因為：

- `ai_system_map.json` 是 CLI、GUI、CI/CD、Markdown report、schema validation 共用的 canonical contract。
- Scanner 預設 read-only，不應把使用者設定寫回被掃描 repo。
- Scan history / manual mapping / query trace metadata 都可能含 sensitive metadata，必須先有 retention、masking、migration 規則。
- local web API route 應只呼叫 service/repository，不直接讀寫 DB 或 artifact file。

## External Verification Notes

- SQLAlchemy 2.0 官方文件將 `Session` 定位為 ORM persistence 的主要操作介面：`https://docs.sqlalchemy.org/20/orm/session.html`
- Alembic 官方文件支援依 SQLAlchemy metadata 與現有 database schema 產生 migration 候選，但 migration 仍需人工審查：`https://alembic.sqlalchemy.org/en/latest/autogenerate.html`
- PostgreSQL 官方文件支援 `jsonb`、GIN index 與結構化 JSON 查詢，適合保存 validated map snapshot 與 metadata：`https://www.postgresql.org/docs/current/datatype-json.html`
- pgvector 官方文件支援在 PostgreSQL 內保存 embedding vector 並做 similarity search，適合未來 AI-assisted mapping / semantic search：`https://github.com/pgvector/pgvector`
- psycopg 官方文件支援 SQLAlchemy 常用的 PostgreSQL driver 路線：`https://www.psycopg.org/psycopg3/docs/`
- FastAPI 官方文件建議用 typed response model 讓 API response validation / serialization / OpenAPI 文件化保持一致：`https://fastapi.tiangolo.com/tutorial/response-model/`

## Storage Decision Update: PostgreSQL First

2026-06-07 決策更新：不要先做 SQLite，再等未來 AI 功能才換 DB。本 plan 改為第一版就採 PostgreSQL，並在 initial migration 建立 `pgvector` extension。

決策理由：

- 使用者明確要求「一次就用」，避免 SQLite -> PostgreSQL 二次 migration。
- 未來會套用 AI，需要 embedding / semantic search；PostgreSQL + pgvector 可同時保存 relational records、JSONB snapshot 與 vector records。
- `pgvector` 可讓 manual mapping、AI proposal、query trace、component evidence 做 semantic lookup，而不用另外拆一套 vector DB。
- PostgreSQL 比 SQLite 更適合後續 team workspace、multi-user namespace、retention、audit trail 與 deployment。

架構邊界不變：

- `ai_system_map.json` 仍是正式輸出 contract。
- DB 是 KAI-Mind-managed storage，不寫入被掃描 repo。
- Repository abstraction 仍保留，避免 route/service 直接依賴 ORM row。
- Vector records 只保存 masked/safe metadata 與 embedding，不保存 raw source code 或 full secret。

Local dev / CI 落地方式：

- 新增 repo-managed PostgreSQL dev service，例如 `docker-compose.storage.yml`。
- 建議 image 使用已包含 pgvector extension 的 PostgreSQL image，例如 `pgvector/pgvector:pg16`。
- Local default database URL:

```text
postgresql+psycopg://kai_mind:kai_mind@127.0.0.1:5432/kai_mind
```

- 測試不可共用 developer 真實 DB；測試 fixture 必須建立 isolated test database 或使用 dedicated test schema，並在測試後清理。

## Scope

### In Scope

- 建立 database storage abstraction。
- 新增 PostgreSQL database URL 設定與可注入 test database URL。
- 新增 SQLAlchemy ORM models 與 Alembic migration。
- 將 project import、scan record、latest viewer payload metadata、manual mapping decision 存入 DB。
- 新增 `pgvector` extension 與 vector embedding table，作為未來 AI-assisted mapping / semantic search 的落點。
- 保留 `ai_system_map.json` / `ai_system_map.md` artifact output。
- 建立 restart 後可讀回 scan history 的 repository/service。
- 建立 JSON artifact -> DB seed/migration helper，支援讀既有 output directory 建立 scan/map metadata。
- 更新 local API guide 與 plan cross-reference。
- 測試 DB migration、repository 行為、restart reload、retention、secret/path masking。

### Out Of Scope

- 不移除 `ai_system_map.json`。
- 不把 DB 宣稱為 multi-user production store。
- 不做 cloud sync、team sharing、auth provider。
- 不保存 raw source code、raw dependency file content、raw query、full secret value。
- 不讓 API request 接受任意 filesystem path 去讀 report 或 JSON。
- 不把 `graph_view_model` 寫回 `RagSystemMap` canonical schema。
- 不導入 SQLite-only fallback 作為主要路線。
- 不在本任務實作完整 AI retrieval/reranking；本任務只建立 pgvector-ready storage schema 與 repository 邊界。

## File Structure

- Modify: `pyproject.toml`
  - Add `SQLAlchemy`, `Alembic`, `psycopg[binary]`, `pgvector` dependencies.
- Create: `docker-compose.storage.yml`
  - Local PostgreSQL + pgvector service for development and migration smoke tests.
- Create: `src/kai_mind/config/storage.py`
  - Resolve PostgreSQL database URL; tests can inject isolated test database URL.
- Create: `src/kai_mind/storage/__init__.py`
  - Export storage package symbols.
- Create: `src/kai_mind/storage/database.py`
  - SQLAlchemy `Base`, engine factory, session factory, migration runner wrapper.
- Create: `src/kai_mind/storage/orm.py`
  - ORM rows for projects, scans, map snapshots, manual mappings, schema metadata.
- Create: `src/kai_mind/storage/repositories.py`
  - Repository protocols and PostgreSQL implementations.
- Create: `src/kai_mind/core/models/session.py`
  - Pydantic/domain models for persisted project and scan records.
- Create: `src/kai_mind/core/models/mapping.py`
  - Pydantic/domain models for persisted manual mapping decisions.
- Create: `src/kai_mind/core/services/session_history_service.py`
  - Use repositories to create/list/get projects and scans.
- Create: `src/kai_mind/core/services/manual_mapping_service.py`
  - Use repositories to store confirmed mapping decisions.
- Modify: `src/kai_mind/web/session_store.py`
  - Keep `InMemorySessionStore` for tests/dev fallback; add DB-backed store adapter or dependency-compatible facade.
- Modify: `src/kai_mind/web/dependencies.py`
  - Wire configured store/service through FastAPI dependency injection.
- Modify: `src/kai_mind/web/app.py`
  - Initialize storage services when not injected by tests.
- Create: `src/kai_mind/web/routes/history_routes.py`
  - `GET /api/projects`, `GET /api/projects/{project_id}`, `GET /api/scans/{scan_id}`.
- Create: `src/kai_mind/web/routes/mapping_routes.py`
  - `GET /api/mappings`, `POST /api/mappings`, `PATCH /api/mappings/{mapping_id}`.
- Modify: `src/kai_mind/web/routes/project_routes.py`
  - Persist imported project through `SessionHistoryService`.
- Modify: `src/kai_mind/web/routes/scan_routes.py`
  - Persist scan status and artifact references.
- Modify: `src/kai_mind/web/routes/map_routes.py`
  - Persist latest successful map snapshot metadata after build.
- Create: `migrations/env.py`
  - Alembic environment using `src/kai_mind/storage/orm.py` metadata.
- Create: `migrations/versions/0001_create_storage_tables.py`
  - Initial PostgreSQL schema, including `CREATE EXTENSION IF NOT EXISTS vector`.
- Create: `alembic.ini`
  - Local migration config.
- Create: `scripts/seed_storage_from_outputs.py`
  - Import existing `outputs/**/ai_system_map.json` metadata into DB.
- Test: `tests/unit/storage/test_storage_config.py`
- Test: `tests/unit/storage/test_postgres_repositories.py`
- Test: `tests/unit/core/test_session_history_service.py`
- Test: `tests/unit/core/test_manual_mapping_service.py`
- Test: `tests/web/test_history_routes.py`
- Test: `tests/web/test_mapping_routes.py`
- Test: `tests/integration/test_database_storage_migration.py`
- Modify docs: `docs/work/Timmy/design/epic1-local-api-guide.md`
- Modify docs: `docs/work/Timmy/schedule/plan/unfinish/19-implement-manual-mapping-store.md`
- Modify docs: `docs/work/Timmy/schedule/plan/unfinish/26-implement-persistent-session-store-and-scan-history.md`

## Data Model

```text
projects
  project_id text primary key
  source_type text not null
  project_name text not null
  project_path text null
  project_fingerprint text not null
  created_at text not null
  updated_at text not null
  last_scan_id text null

scans
  scan_id text primary key
  project_id text not null references projects(project_id)
  status text not null
  started_at text not null
  completed_at text null
  output_run_dir text null
  map_json_path text null
  map_markdown_path text null
  map_error_path text null
  error_summary text null

map_snapshots
  snapshot_id text primary key
  scan_id text not null references scans(scan_id)
  schema_version text not null
  project_name text not null
  map_json jsonb not null
  map_json_digest text not null
  created_at text not null

manual_mappings
  mapping_id text primary key
  project_id text not null references projects(project_id)
  source_evidence_id text not null
  target_slot text not null
  component_name text not null
  decision text not null
  mapping_payload_json text not null
  mapping_digest text not null
  created_at text not null
  updated_at text not null

vector_records
  vector_id text primary key
  project_id text not null references projects(project_id)
  source_type text not null
  source_ref text not null
  source_digest text not null
  embedding_model text not null
  embedding vector(1536) not null
  metadata_json jsonb not null
  created_at text not null

schema_metadata
  key text primary key
  value text not null
```

`vector(1536)` is the first planned dimension because common OpenAI embedding models use 1536-dimensional vectors. If the chosen embedding model changes, add a migration that creates a new vector column/table instead of silently mixing dimensions.

## Task 1: Add PostgreSQL Storage Dependencies And Config

**Files:**
- Modify: `pyproject.toml`
- Create: `src/kai_mind/config/storage.py`
- Test: `tests/unit/storage/test_storage_config.py`

- [ ] **Step 1: Write failing config tests**

```python
import pytest

from kai_mind.config.storage import StorageSettings


def test_storage_settings_accepts_injected_postgres_url() -> None:
    url = "postgresql+psycopg://kai_mind:kai_mind@127.0.0.1:5432/kai_mind"

    settings = StorageSettings.from_url(url)

    assert settings.database_url == url


def test_storage_settings_default_uses_local_postgres_url() -> None:
    settings = StorageSettings.default()

    assert settings.database_url == (
        "postgresql+psycopg://kai_mind:kai_mind@127.0.0.1:5432/kai_mind"
    )


def test_storage_settings_reads_env_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "postgresql+psycopg://test:test@127.0.0.1:5433/test_db"
    monkeypatch.setenv("KAI_MIND_DATABASE_URL", url)
    settings = StorageSettings.from_env_or_default()

    assert settings.database_url == url
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/unit/storage/test_storage_config.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'kai_mind.config.storage'
```

- [ ] **Step 3: Add dependencies**

Add to `pyproject.toml` dependencies:

```toml
"SQLAlchemy>=2.0,<3",
"alembic>=1.16,<2",
"psycopg[binary]>=3.2,<4",
"pgvector>=0.3,<1",
```

- [ ] **Step 4: Implement config**

```python
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class StorageSettings:
    database_url: str

    @classmethod
    def from_url(cls, database_url: str) -> StorageSettings:
        if not database_url.startswith("postgresql+psycopg://"):
            raise ValueError("KAI-Mind storage requires PostgreSQL via psycopg")
        return cls(database_url=database_url)

    @classmethod
    def default(cls) -> StorageSettings:
        return cls.from_url(
            "postgresql+psycopg://"
            "kai_mind:kai_mind@127.0.0.1:5432/kai_mind"
        )

    @classmethod
    def from_env_or_default(cls) -> StorageSettings:
        database_url = os.environ.get("KAI_MIND_DATABASE_URL")
        if database_url:
            return cls.from_url(database_url)
        return cls.default()
```

- [ ] **Step 5: Run test and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/unit/storage/test_storage_config.py -v
```

Expected:

```text
3 passed
```

## Task 2: Create PostgreSQL ORM Schema And Alembic Migration

**Files:**
- Create: `src/kai_mind/storage/database.py`
- Create: `src/kai_mind/storage/orm.py`
- Create: `src/kai_mind/storage/__init__.py`
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/versions/0001_create_storage_tables.py`
- Test: `tests/integration/test_database_storage_migration.py`

- [ ] **Step 1: Write migration test**

```python
from pathlib import Path

from sqlalchemy import inspect

from kai_mind.config.storage import StorageSettings
from kai_mind.storage.database import create_engine_for_settings, run_migrations


def test_initial_migration_creates_storage_tables(
    postgres_database_url: str,
) -> None:
    settings = StorageSettings.from_url(postgres_database_url)
    engine = create_engine_for_settings(settings)

    run_migrations(settings)

    inspector = inspect(engine)
    assert set(inspector.get_table_names()) >= {
        "projects",
        "scans",
        "map_snapshots",
        "manual_mappings",
        "vector_records",
        "schema_metadata",
    }
```

- [ ] **Step 2: Run test and verify RED**

Run:

```bash
.venv/bin/pytest tests/integration/test_database_storage_migration.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'kai_mind.storage'
```

- [ ] **Step 3: Implement ORM rows**

```python
from __future__ import annotations

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class ProjectRow(Base):
    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(Text, primary_key=True)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    project_name: Mapped[str] = mapped_column(Text, nullable=False)
    project_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
    last_scan_id: Mapped[str | None] = mapped_column(Text, nullable=True)


class ScanRow(Base):
    __tablename__ = "scans"

    scan_id: Mapped[str] = mapped_column(Text, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("projects.project_id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[str] = mapped_column(Text, nullable=False)
    completed_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_run_dir: Mapped[str | None] = mapped_column(Text, nullable=True)
    map_json_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    map_markdown_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    map_error_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class MapSnapshotRow(Base):
    __tablename__ = "map_snapshots"

    snapshot_id: Mapped[str] = mapped_column(Text, primary_key=True)
    scan_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("scans.scan_id"),
        nullable=False,
    )
    schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    project_name: Mapped[str] = mapped_column(Text, nullable=False)
    map_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    map_json_digest: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class ManualMappingRow(Base):
    __tablename__ = "manual_mappings"

    mapping_id: Mapped[str] = mapped_column(Text, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("projects.project_id"),
        nullable=False,
    )
    source_evidence_id: Mapped[str] = mapped_column(Text, nullable=False)
    target_slot: Mapped[str] = mapped_column(Text, nullable=False)
    component_name: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    mapping_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    mapping_digest: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class VectorRecordRow(Base):
    __tablename__ = "vector_records"

    vector_id: Mapped[str] = mapped_column(Text, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("projects.project_id"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    source_digest: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_model: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class SchemaMetadataRow(Base):
    __tablename__ = "schema_metadata"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
```

- [ ] **Step 4: Implement engine/session and migration wrapper**

```python
from __future__ import annotations

from collections.abc import Iterator
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from kai_mind.config.storage import StorageSettings


def create_engine_for_settings(settings: StorageSettings) -> Engine:
    return create_engine(settings.database_url, future=True)


def create_session_factory(
    settings: StorageSettings,
) -> sessionmaker[Session]:
    engine = create_engine_for_settings(settings)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def run_migrations(settings: StorageSettings) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(config, "head")
```

- [ ] **Step 5: Add Alembic migration**

Use explicit Alembic operations for the initial schema. The first migration must:

1. Run `CREATE EXTENSION IF NOT EXISTS vector`.
2. Create all tables in the data model section.
3. Create a vector index only after row volume justifies it; do not add approximate index before query patterns are known.
4. Insert:

```text
schema_metadata(key="storage_schema_version", value="1")
```

- [ ] **Step 6: Run migration test and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/integration/test_database_storage_migration.py -v
```

Expected:

```text
1 passed
```

## Task 3: Add Repository Interfaces And PostgreSQL Implementations

**Files:**
- Create: `src/kai_mind/core/models/session.py`
- Create: `src/kai_mind/core/models/mapping.py`
- Create: `src/kai_mind/storage/repositories.py`
- Test: `tests/unit/storage/test_postgres_repositories.py`

- [ ] **Step 1: Write repository behavior tests**

```python
from pathlib import Path

from kai_mind.config.storage import StorageSettings
from kai_mind.core.models.session import ProjectRecord, ScanRecord
from kai_mind.storage.database import create_session_factory, run_migrations
from kai_mind.storage.repositories import PostgresProjectRepository


def test_project_repository_persists_across_session_factory_reuse(
    postgres_database_url: str,
) -> None:
    settings = StorageSettings.from_url(postgres_database_url)
    run_migrations(settings)
    factory = create_session_factory(settings)
    repo = PostgresProjectRepository(factory)
    project = ProjectRecord.new_local_path(Path("/tmp/demo-rag"))

    repo.save(project)
    loaded = repo.get(project.project_id)

    assert loaded == project


def test_project_repository_lists_projects(postgres_database_url: str) -> None:
    settings = StorageSettings.from_url(postgres_database_url)
    run_migrations(settings)
    repo = PostgresProjectRepository(create_session_factory(settings))

    repo.save(ProjectRecord.new_local_path(Path("/tmp/demo-a")))
    repo.save(ProjectRecord.new_local_path(Path("/tmp/demo-b")))

    assert [item.project_name for item in repo.list()] == [
        "demo-a",
        "demo-b",
    ]
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/unit/storage/test_postgres_repositories.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'kai_mind.core.models.session'
```

- [ ] **Step 3: Implement domain models**

```python
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict


def utc_now_text() -> str:
    return datetime.now(UTC).isoformat()


class ProjectRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    project_id: str
    source_type: str
    project_name: str
    project_path: str | None
    project_fingerprint: str
    created_at: str
    updated_at: str
    last_scan_id: str | None = None

    @classmethod
    def new_local_path(cls, project_path: Path) -> ProjectRecord:
        resolved = project_path.expanduser()
        now = utc_now_text()
        return cls(
            project_id=f"project:{uuid4()}",
            source_type="local_path",
            project_name=resolved.name or "project",
            project_path=str(resolved),
            project_fingerprint=f"local_path:{resolved}",
            created_at=now,
            updated_at=now,
        )


class ScanRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    scan_id: str
    project_id: str
    status: str
    started_at: str
    completed_at: str | None = None
    output_run_dir: str | None = None
    map_json_path: str | None = None
    map_markdown_path: str | None = None
    map_error_path: str | None = None
    error_summary: str | None = None
```

- [ ] **Step 4: Implement project repository**

Implement `ProjectRepository` protocol and `PostgresProjectRepository` using SQLAlchemy sessions. Methods:

```python
class ProjectRepository(Protocol):
    def save(self, record: ProjectRecord) -> None: ...
    def get(self, project_id: str) -> ProjectRecord | None: ...
    def list(self) -> list[ProjectRecord]: ...
```

The PostgreSQL implementation must use `session.merge(row)` for idempotent save and sort `list()` by `created_at`.

- [ ] **Step 5: Run tests and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/unit/storage/test_postgres_repositories.py -v
```

Expected:

```text
2 passed
```

## Task 4: Replace Process-Only Session State With Service Boundary

**Files:**
- Create: `src/kai_mind/core/services/session_history_service.py`
- Modify: `src/kai_mind/web/session_store.py`
- Modify: `src/kai_mind/web/dependencies.py`
- Modify: `src/kai_mind/web/app.py`
- Modify: `src/kai_mind/web/routes/project_routes.py`
- Modify: `src/kai_mind/web/routes/scan_routes.py`
- Modify: `src/kai_mind/web/routes/map_routes.py`
- Test: `tests/unit/core/test_session_history_service.py`
- Test: `tests/web/test_project_scan_routes.py`

- [ ] **Step 1: Write service restart test**

```python
from pathlib import Path

from kai_mind.config.storage import StorageSettings
from kai_mind.core.services.session_history_service import (
    SessionHistoryService,
)
from kai_mind.storage.database import create_session_factory, run_migrations
from kai_mind.storage.repositories import PostgresProjectRepository


def build_service(database_url: str) -> SessionHistoryService:
    settings = StorageSettings.from_url(database_url)
    run_migrations(settings)
    factory = create_session_factory(settings)
    return SessionHistoryService(
        project_repository=PostgresProjectRepository(factory),
    )


def test_imported_project_survives_service_recreation(
    postgres_database_url: str,
) -> None:
    first_service = build_service(postgres_database_url)
    project = first_service.import_local_path(Path("/tmp/demo-rag"))

    second_service = build_service(postgres_database_url)

    assert second_service.get_project(project.project_id) == project
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/unit/core/test_session_history_service.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'kai_mind.core.services.session_history_service'
```

- [ ] **Step 3: Implement service**

```python
from __future__ import annotations

from pathlib import Path

from kai_mind.core.models.session import ProjectRecord
from kai_mind.storage.repositories import ProjectRepository


class SessionHistoryService:
    def __init__(
        self,
        *,
        project_repository: ProjectRepository,
    ) -> None:
        self._project_repository = project_repository

    def import_local_path(self, project_path: Path) -> ProjectRecord:
        record = ProjectRecord.new_local_path(project_path)
        self._project_repository.save(record)
        return record

    def get_project(self, project_id: str) -> ProjectRecord | None:
        return self._project_repository.get(project_id)

    def list_projects(self) -> list[ProjectRecord]:
        return self._project_repository.list()
```

- [ ] **Step 4: Wire local API through service**

Route rule:

```text
FastAPI route -> SessionHistoryService -> Repository -> DB
```

Do not let route handlers import SQLAlchemy models or call `Path.read_text()` for DB-backed records.

- [ ] **Step 5: Preserve in-memory fallback tests**

Keep `InMemorySessionStore` available for focused unit/web tests that do not need persistence. Add one explicit test proving default app wiring can inject a test PostgreSQL URL, so tests never write to a developer's real database by accident.

- [ ] **Step 6: Run route tests**

Run:

```bash
.venv/bin/pytest tests/web/test_project_scan_routes.py -v
```

Expected:

```text
all selected tests passed
```

## Task 5: Persist Scan Records And Map Snapshot Metadata

**Files:**
- Modify: `src/kai_mind/core/models/session.py`
- Modify: `src/kai_mind/storage/repositories.py`
- Modify: `src/kai_mind/core/services/session_history_service.py`
- Modify: `src/kai_mind/web/routes/scan_routes.py`
- Modify: `src/kai_mind/web/routes/map_routes.py`
- Test: `tests/unit/core/test_session_history_service.py`
- Test: `tests/web/test_history_routes.py`

- [ ] **Step 1: Write scan persistence tests**

```python
def test_completed_scan_stores_artifact_paths_without_raw_secret(
    service: SessionHistoryService,
) -> None:
    project = service.import_local_path(Path("/tmp/demo-rag"))

    scan = service.record_completed_scan(
        project_id=project.project_id,
        output_run_dir=Path("/tmp/out"),
        map_json_path=Path("/tmp/out/ai_system_map.json"),
        map_markdown_path=Path("/tmp/out/ai_system_map.md"),
        error_summary=None,
    )

    loaded = service.get_scan(scan.scan_id)
    assert loaded == scan
    assert "sk-" not in (loaded.error_summary or "")
```

- [ ] **Step 2: Implement scan repository**

Add:

```python
class ScanRepository(Protocol):
    def save(self, record: ScanRecord) -> None: ...
    def get(self, scan_id: str) -> ScanRecord | None: ...
    def list_for_project(self, project_id: str) -> list[ScanRecord]: ...
```

`PostgresScanRepository.list_for_project()` must order by `started_at desc`.

- [ ] **Step 3: Persist map snapshot safely**

`map_snapshots.map_json` may store the validated `RagSystemMap.model_dump(mode="json")` payload as PostgreSQL `jsonb`, but only after `SystemMapValidationService` passes. Store `map_json_digest` as `sha256:` plus hex digest.

- [ ] **Step 4: Route behavior**

`POST /api/scans` must:

1. Load project by `project_id` from `SessionHistoryService`.
2. Run `MapBuildService`.
3. Save scan record with status `completed` or `error`.
4. Save map snapshot only when `result.ai_system_map is not None`.
5. Return the existing `ScanCreateResponse` shape to avoid frontend breakage.

- [ ] **Step 5: Run tests**

Run:

```bash
.venv/bin/pytest tests/unit/core/test_session_history_service.py tests/web/test_history_routes.py -v
```

Expected:

```text
all selected tests passed
```

## Task 6: Move Manual Mapping Store Onto The Same DB Layer

### Phase 19 Handoff: Repository Boundary Already Exists

Phase 19 did not fake PostgreSQL completion. It implemented the manual mapping
domain/service/API and left a deliberate repository boundary for this task to
finish:

- `src/kai_mind/core/services/manual_mapping_service.py` defines
  `ManualMappingRepository` as the storage boundary with only:
  `save(mapping)`, `get(mapping_id)`, and `list_for_project(project_id)`.
- `ManualMappingService` accepts an injected repository. If no repository is
  injected, local tests/dev fallback use `InMemoryManualMappingRepository`.
- `src/kai_mind/storage/repositories.py` currently re-exports the manual
  mapping repository protocol and in-memory implementation so Task 27 can add
  PostgreSQL implementations in the storage layer without rewriting core
  service behavior.
- `create_app()` already accepts `manual_mapping_service`; `MapBuildService`
  already accepts `manual_mapping_service`; `/api/scans` already passes
  `project_id` so confirmed mappings can be applied on the next scan.

Task 27 must preserve this boundary. Do not move SQLAlchemy row logic into
`ManualMappingService` or `mapping_routes.py`. The right implementation is:

```text
ManualMappingService
  -> ManualMappingRepository protocol
  -> PostgresManualMappingRepository
  -> SQLAlchemy session / manual_mappings table
```

In plain terms: Phase 19 made the core code depend on a small storage
interface, not on PostgreSQL directly. Task 27 should swap the current
in-memory repository for a PostgreSQL repository. The service, routes, and
scan pipeline should keep calling the same repository methods.

**Files:**
- Modify: `src/kai_mind/core/models/mapping.py`
- Modify: `src/kai_mind/core/services/manual_mapping_service.py`
- Modify: `src/kai_mind/web/routes/mapping_routes.py`
- Modify: `src/kai_mind/storage/repositories.py`
- Test: `tests/unit/core/test_manual_mapping_service.py`
- Test: `tests/web/test_mapping_routes.py`
- Test: `tests/unit/storage/test_postgres_repositories.py`

- [ ] **Step 1: Write PostgreSQL repository behavior tests**

```python
def test_postgres_manual_mapping_repository_persists_by_project(
    session_factory: SessionFactory,
) -> None:
    repository = PostgresManualMappingRepository(session_factory)
    mapping = ManualMapping(
        mapping_id="mapping:demo",
        project_id="project:demo",
        mapping_type="existing_slot_mapping",
        decision="confirmed",
        source_file="src/reranker.py",
        evidence_ids=["evidence:config:reranker"],
        target_slot="reranker",
        component_name="cross-encoder reranker",
        mapping_digest="sha256:demo",
        created_at="2026-06-07T00:00:00Z",
        updated_at="2026-06-07T00:00:00Z",
    )

    repository.save(mapping)

    assert repository.list_for_project("project:demo") == [mapping]
    assert repository.list_for_project("project:other") == []
```

- [ ] **Step 2: Keep the existing mapping model stable**

Phase 19 already created `src/kai_mind/core/models/mapping.py`. Task 27 should
not replace it with ORM rows. Keep Pydantic/domain models in core and add ORM
rows under `src/kai_mind/storage/orm.py`.

- [ ] **Step 3: Keep validation in `ManualMappingService`**

The service must reject:

- empty `project_id`
- missing `evidence_ids`
- invalid confirmed `target_slot`
- dangling extension edge endpoints
- invalid `source_file` path
- `decision` values outside `confirmed`, `rejected`, `skip_for_now`,
  `not_applicable`
- mapping payloads containing full secret values already detected by `SecretMaskingService`

- [ ] **Step 4: Implement `PostgresManualMappingRepository`**

Add `PostgresManualMappingRepository` to `src/kai_mind/storage/repositories.py`.
It must implement the existing `ManualMappingRepository` protocol:

```text
save(mapping) -> ManualMapping
get(mapping_id) -> ManualMapping | None
list_for_project(project_id) -> list[ManualMapping]
```

Repository behavior rules:

- Use SQLAlchemy sessions from the shared storage session factory.
- Persist into the `manual_mappings` table.
- Keep `mapping_payload_json` / JSONB enough to reconstruct the full
  `ManualMapping` domain model without losing fields like `source_unmapped_id`,
  `extension_edges`, `proposal_id`, or `audit_metadata`.
- Sort `list_for_project()` by `created_at`.
- Do not read or write `ai_system_map.json`.
- Do not write into the scanned project root.

- [ ] **Step 5: Wire default app storage**

When storage settings are enabled, `create_app()` should build:

```text
PostgresManualMappingRepository(session_factory)
  -> ManualMappingService(repository=...)
  -> MapBuildService(manual_mapping_service=...)
```

Focused tests can keep injecting `InMemoryManualMappingRepository` so unit/web
tests do not need PostgreSQL unless they explicitly test storage persistence.

- [ ] **Step 6: Route behavior**

`POST /api/mappings` must write mapping decisions to DB only. It must not mutate an existing `ai_system_map.json`; the mapping becomes effective on next scan/normalize.

- [ ] **Step 7: Run mapping tests**

Run:

```bash
.venv/bin/pytest \
  tests/unit/core/test_manual_mapping_service.py \
  tests/unit/storage/test_postgres_repositories.py \
  tests/web/test_mapping_routes.py \
  -v
```

Expected:

```text
all selected tests passed
```

## Task 7: Add History Routes And Retention Policy

**Files:**
- Create: `src/kai_mind/web/routes/history_routes.py`
- Modify: `src/kai_mind/core/services/session_history_service.py`
- Test: `tests/web/test_history_routes.py`

- [ ] **Step 1: Write route tests**

```python
def test_history_route_lists_projects(client: TestClient) -> None:
    response = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": "/tmp/demo-rag",
        },
    )
    project_id = response.json()["project_id"]

    history_response = client.get("/api/projects")

    assert history_response.status_code == 200
    assert history_response.json()[0]["project_id"] == project_id


def test_unknown_scan_returns_404(client: TestClient) -> None:
    response = client.get("/api/scans/scan:missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "scan_not_found"
```

- [ ] **Step 2: Implement routes**

Routes:

```text
GET /api/projects
GET /api/projects/{project_id}
GET /api/projects/{project_id}/scans
GET /api/scans/{scan_id}
```

Responses must omit raw source file content and full secrets.

- [ ] **Step 3: Add retention cleanup**

Add `SessionHistoryService.cleanup_retention(max_scans_per_project: int)`:

- keep latest N scans per project
- delete old `scans` and `map_snapshots` rows
- do not delete artifact files until a separate artifact retention policy is implemented

- [ ] **Step 4: Run route tests**

Run:

```bash
.venv/bin/pytest tests/web/test_history_routes.py -v
```

Expected:

```text
all selected tests passed
```

## Task 8: Seed Database From Existing JSON Outputs

**Files:**
- Create: `scripts/seed_storage_from_outputs.py`
- Test: `tests/integration/test_database_storage_migration.py`

- [ ] **Step 1: Write seed test**

```python
def test_seed_imports_existing_ai_system_map_json(
    tmp_path: Path,
    postgres_database_url: str,
) -> None:
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    fixture = Path("tests/fixtures/ai_system_map/valid_minimal.v1.json")
    target = outputs / "ai_system_map.json"
    target.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    seed_from_outputs(outputs_dir=outputs, database_url=postgres_database_url)

    service = build_service(postgres_database_url)
    assert len(service.list_projects()) == 1
```

- [ ] **Step 2: Implement seed script behavior**

The script must:

1. Find `ai_system_map.json` under the given outputs directory.
2. Validate each JSON through `SystemMapValidationService`.
3. Create project and completed scan records.
4. Save map snapshot digest.
5. Skip invalid JSON and print a masked error summary.

- [ ] **Step 3: Run seed test**

Run:

```bash
.venv/bin/pytest tests/integration/test_database_storage_migration.py -v
```

Expected:

```text
all selected tests passed
```

## Task 9: Update Documentation And Existing Plans

**Files:**
- Modify: `docs/work/Timmy/design/epic1-local-api-guide.md`
- Modify: `docs/work/Timmy/schedule/plan/unfinish/19-implement-manual-mapping-store.md`
- Modify: `docs/work/Timmy/schedule/plan/unfinish/26-implement-persistent-session-store-and-scan-history.md`

- [ ] **Step 1: Update API guide**

Add sections:

```text
Storage mode:
  default: PostgreSQL database URL from KAI_MIND_DATABASE_URL
  local dev fallback: postgresql+psycopg://kai_mind:kai_mind@127.0.0.1:5432/kai_mind
  test override: isolated PostgreSQL test database URL
  vector extension: pgvector enabled in initial migration

Canonical truth:
  ai_system_map.json remains the external contract
  database stores history, mapping decisions, safe snapshots, artifact refs,
  and future AI vector records

Privacy:
  no raw source code
  no full secret values
  local-only single-user unless auth/namespace exists

Migration:
  Alembic owns schema migration
  JSON output seeding is one-way metadata import
```

- [ ] **Step 2: Update Task 19 plan**

Replace file-based/YAML default wording with:

```text
Default manual mapping persistence now uses the shared DB storage layer from
Task 27. Import/export YAML remains a future exchange format and must not be
treated as the default source of truth.
```

- [ ] **Step 3: Update Task 26 plan**

Replace `選擇 JSONL / SQLite / small local database` with:

```text
Storage decision: use PostgreSQL + pgvector through the shared
database-backed storage layer from Task 27, with Alembic migrations and
injectable test database URLs.
```

## Task 10: Full Verification

**Files:**
- All files changed by Tasks 1-9.

- [ ] **Step 1: Run focused tests**

```bash
.venv/bin/pytest \
  tests/unit/storage/test_storage_config.py \
  tests/unit/storage/test_postgres_repositories.py \
  tests/unit/core/test_session_history_service.py \
  tests/unit/core/test_manual_mapping_service.py \
  tests/web/test_history_routes.py \
  tests/web/test_mapping_routes.py \
  tests/integration/test_database_storage_migration.py \
  -v
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 2: Run full backend tests**

```bash
.venv/bin/pytest
```

Expected:

```text
all tests passed
```

- [ ] **Step 3: Run lint and typing**

```bash
.venv/bin/ruff check .
.venv/bin/mypy
```

Expected:

```text
ruff: no issues
mypy: Success: no issues found
```

- [ ] **Step 4: Run migration smoke test manually**

```bash
KAI_MIND_DATABASE_URL="postgresql+psycopg://kai_mind:kai_mind@127.0.0.1:5432/kai_mind" \
  .venv/bin/python scripts/seed_storage_from_outputs.py --outputs outputs
```

Expected:

```text
No full secret values printed.
Valid ai_system_map.json files imported or invalid files skipped with masked reasons.
```

- [ ] **Step 5: Git hygiene**

```bash
git diff --check
git status --short
```

Expected:

```text
git diff --check exits 0
git status shows only intentional files
```

## Acceptance Criteria

- `ai_system_map.json` remains generated and schema validated.
- PostgreSQL is the default persistent store, configured by `KAI_MIND_DATABASE_URL`.
- Initial migration enables `pgvector`.
- Alembic initial migration creates all storage tables.
- Imported project records survive service/app recreation.
- Scan records and safe map snapshot metadata survive restart.
- Manual mapping decisions are stored in DB and become effective only on future scan/normalize.
- API routes do not import SQLAlchemy ORM classes directly.
- API responses do not include raw source content or full secret values.
- Retention cleanup can delete old scan/map snapshot rows without touching unrelated project records.
- Existing frontend contract for `POST /api/scans`, `POST /api/map/build`, `GET /api/map`, and `GET /map` is not broken.
- Full `pytest`, `ruff`, and `mypy` pass before moving implementation work to completion.

## Plain-Language Summary

現在的 JSON 像正式輸出的報告檔，這個檔案不能消失，因為前端、CLI、CI 都靠它理解掃描結果。Database 則像 KAI-Mind 自己的工作紀錄本，用來記住「掃過哪些專案」、「哪次 scan 產出哪些 artifact」、「使用者確認過哪些 mapping」。

未來執行這份 plan 時，第一步不是刪 JSON，而是先在 JSON 外面加一層 repository，把需要長期保存與查詢的資料搬進 PostgreSQL。因為後續會導入 AI，第一版 migration 就啟用 pgvector，讓 Task 19 manual mapping、Task 20 AI proposal、Task 22 query trace 與 Task 26 scan history 可以共用同一套 database storage，不需要先做 SQLite 再二次搬家。
