# 2026-06-03 Phase 12 Project Scan Service REP

## 實作邏輯

本階段建立 `ProjectScanService`，把 Task 8-11 providers 的 `ProviderScanResult` 聚合成一份 raw scan result。核心原則是：

```text
FilesystemProvider
  -> FileInventory
  -> Config / Docker / Dependency / CodePattern providers
  -> ProviderScanResult facts/evidence/issues
  -> ProjectScanService
  -> ProjectScanResult raw facts/evidence/issues/skipped_file summaries/warnings
```

`ProjectScanService` 只做 orchestration、partial failure isolation、dedupe、evidence merge、deterministic ordering 與 skipped summary。它不做 component detection、endpoint/risk/flow derivation，也不寫 artifacts。

## 實作步驟

1. 建立 `docs/work/Timmy/schedule/todo/2026-06-03-phase12-project-scan-service-TODO.md`。
2. 先寫 `tests/unit/core/test_project_scan_service.py`，鎖定以下行為：
   - 會呼叫 filesystem provider 建立 shared inventory。
   - 會把 provider facts/evidence/issues 聚合。
   - 單一 provider `collect()` 丟 exception 時不讓整體 scan crash。
   - 重複 facts 會 dedupe，但 evidence 仍保留。
   - facts/evidence/issues/skipped_files ordering deterministic。
   - raw scan result 不包含 components/endpoints/risk/flows final judgment。
3. 先寫 `tests/integration/test_phase12_project_scan_service_behaviors.py`，用真實 fixtures 驗證：
   - `basic_qdrant_ollama_rag` 可聚合 Docker / dependency / code pattern facts。
   - `malformed_config_rag` 會保留 parse issues 和 parse error evidence，不 crash。
4. RED 階段確認兩個新測試檔都因 `ProjectScanService` 尚不存在而失敗。
5. 擴充 `src/kai_mind/core/models/scan.py`：
   - `ScanFact.provider`
   - `ParseIssue.scan_stage = "project_scan"`
   - `SkippedFileSummary`
   - `ProjectScanResult`
6. 建立 `src/kai_mind/core/services/project_scan_service.py`：
   - default provider wiring。
   - dependency injection，方便 unit tests。
   - `collect()` exception isolation。
   - exact fact dedupe。
   - evidence id dedupe。
   - deterministic sorting。
   - skipped files summary。
7. 將完成的 plan 從 `docs/work/Timmy/schedule/plan/unfinish/12-aggregate-raw-scan-facts.md` 移到 `docs/work/Timmy/schedule/plan/finish/12-aggregate-raw-scan-facts.md`。

## 測試方式

RED 階段：

```bash
.venv/bin/python -m pytest tests/unit/core/test_project_scan_service.py
.venv/bin/python -m pytest tests/integration/test_phase12_project_scan_service_behaviors.py
```

兩者都先失敗在：

```text
ModuleNotFoundError: No module named 'kai_mind.core.services.project_scan_service'
```

GREEN 後針對 Phase 12：

```bash
.venv/bin/python -m pytest tests/unit/core/test_project_scan_service.py
.venv/bin/python -m pytest tests/integration/test_phase12_project_scan_service_behaviors.py
```

Provider regression：

```bash
.venv/bin/python -m pytest tests/unit/core/test_config_parse_provider.py tests/unit/core/test_docker_compose_provider.py tests/unit/core/test_dependency_manifest_provider.py tests/unit/core/test_code_pattern_provider.py tests/unit/core/test_rule_catalog_loader.py
.venv/bin/python -m pytest tests/integration/test_phase8_config_parse_provider_behaviors.py tests/integration/test_phase9_docker_compose_provider_behaviors.py tests/integration/test_phase10_dependency_manifest_provider_behaviors.py tests/integration/test_phase11_code_pattern_provider_behaviors.py
```

Full verification：

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 遇到的問題與解法

### 1. Sandbox 無法建立 pytest temporary file

第一次跑 pytest 時，Python 無法取得可用 temporary directory。這是 sandbox filesystem 限制，不是 repo regression。

解法：改用正常 filesystem 權限重跑同一個 pytest 指令，取得真正 RED failure。

### 2. `Protocol` import 錯誤

初版 `project_scan_service.py` 從 `collections.abc` 匯入 `Protocol`，Python 3.14 實際應從 `typing` 匯入。

解法：改成 `from typing import Literal, Protocol`。

### 3. 測試預期 rule_id 與既有 catalogs 不一致

integration test 初版使用了不存在的 rule_id，例如 `docker_image_vector_store_qdrant`。實際 Task 12a catalog 使用：

- `docker_qdrant_image_detected`
- `docker_ollama_image_detected`
- `dependency_vector_store_client_qdrant`
- `dependency_local_llm_provider_ollama`

解法：測試改回既有 catalogs 的真實 rule_id，避免為了測試重新命名已穩定 contract。

### 4. Ruff / mypy 驗證

初版有 import ordering、行長與 literal type 問題。

解法：調整 import、縮短 docstring/型別宣告，並將 `PROJECT_SCAN_STAGE` 宣告為 `Literal["project_scan"]`。

## 測試結果

```text
.venv/bin/python -m pytest
170 passed in 1.45s

.venv/bin/ruff check .
All checks passed!

.venv/bin/mypy
Success: no issues found in 52 source files
```

## 驗收對照

- 建立 `ProjectScanService`：已完成。
- 統一 orchestration providers：已完成，default wiring 包含 Config、Docker、Dependency、CodePattern providers，並先由 FilesystemProvider 建立 inventory。
- 整理 `ScanFact[]`、`Evidence[]`、`ParseIssue[]`：已完成。
- 保留 skipped files summary：已完成，`ProjectScanResult.skipped_files` 保存 path、reason、size_bytes summary。
- 這一層只收集 facts，不做 slot final judgment：已完成，測試確認不輸出 components/endpoints/risk/flows。
- provider partial failure 不讓 ProjectScanService crash：已完成，runtime `collect()` exception 轉成 `project_scan` issue 與 warning。
- deterministic ordering：已完成，facts/evidence/issues/skipped_files 都有穩定排序。
- dedupe + evidence merge：已完成，重複 facts 只保留一筆，evidence 保留並排序。
- 所有 facts 都有 rule_id 或 provider source：已完成，既有 provider facts 保留 rule_id；缺 rule_id 的 injected provider fact 會補 provider source。
- 所有 evidence 都有 project-relative file path 或合理 non-file source：已透過 integration tests 覆蓋 provider evidence。
- Task 12a rule catalog malformed 不被靜默吞掉：已保留 provider constructor/catalog loading 的 fail-fast 行為；ProjectScanService 只隔離 provider runtime `collect()` failure。
- Full verification 通過：已完成。
