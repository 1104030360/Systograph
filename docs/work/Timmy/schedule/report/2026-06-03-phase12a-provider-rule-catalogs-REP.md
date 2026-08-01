# 2026-06-03 Phase 12a Provider Rule Catalogs REP

## 實作邏輯

本階段把 provider 內會持續成長的 deterministic rules 從 Python 硬編碼移到 package-bundled TOML catalogs。核心原則是只搬移 rule data，不改 provider 輸出的 facts / evidence / issues contract，也不改 `ai-system-map/v1` schema。

新的資料流：

```text
package TOML catalog
  -> RuleCatalogLoader validation
  -> provider applies loaded rules
  -> ProviderScanResult facts/evidence/issues
```

這樣 dependency package、Docker image、code pattern 新增規則時，可以先改 TOML catalog，不需要碰 provider 的掃描流程。

## 實作步驟

1. 建立 `tests/unit/core/test_rule_catalog_loader.py`，先用 TDD 鎖住 catalog validation 行為。
2. 補三個 provider 的 custom catalog injection regression tests：
   - `DependencyManifestProvider(rule_catalog_path=...)`
   - `DockerComposeProvider(image_rule_catalog_path=...)`
   - `CodePatternProvider(rule_catalog_path=...)`
3. 建立 package-bundled catalogs：
   - `src/systograph/core/rules/dependency_manifest_rules.toml`
   - `src/systograph/core/rules/docker_image_rules.toml`
   - `src/systograph/core/rules/code_pattern_rules.toml`
4. 建立 `src/systograph/core/services/rule_catalog_loader.py`：
   - `DependencyPackageRule`
   - `DependencyRuleCatalog`
   - `DockerImageRule`
   - `CodePatternRule`
   - `RuleCatalogLoader`
   - `RuleCatalogError`
5. 重構 `DependencyManifestProvider`，移除 `PYTHON_RULES` / `NODE_RULES` / scoped prefix hardcoding，改由 dependency TOML catalog 載入。
6. 重構 `DockerComposeProvider`，移除 Qdrant / Ollama / pgvector image if/else，改由 Docker image TOML catalog 載入。
7. 重構 `CodePatternProvider`，移除 Python hardcoded regex catalog 依賴，改由 code pattern TOML catalog 載入。
8. 移除舊的 `src/systograph/core/providers/code_patterns.py`，避免留下第二份 hardcoded regex source。
9. 將 phase plan 從 `docs/work/Timmy/schedule/plan/unfinish` 移到 `docs/work/Timmy/schedule/plan/finish`。

## 測試方式

RED 階段先跑新增測試，確認失敗在尚未存在的 `RuleCatalogLoader`：

```bash
.venv/bin/python -m pytest tests/unit/core/test_rule_catalog_loader.py tests/unit/core/test_dependency_manifest_provider.py::test_collect_uses_injected_dependency_rule_catalog tests/unit/core/test_docker_compose_provider.py::test_collect_uses_injected_docker_image_rule_catalog tests/unit/core/test_code_pattern_provider.py::test_collect_uses_injected_code_pattern_rule_catalog
```

GREEN 後跑 provider regression：

```bash
.venv/bin/python -m pytest tests/unit/core/test_rule_catalog_loader.py tests/unit/core/test_dependency_manifest_provider.py tests/unit/core/test_docker_compose_provider.py tests/unit/core/test_code_pattern_provider.py tests/integration/test_phase9_docker_compose_provider_behaviors.py tests/integration/test_phase10_dependency_manifest_provider_behaviors.py tests/integration/test_phase11_code_pattern_provider_behaviors.py
```

Full verification：

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 遇到的問題與解法

### 1. Sandbox 無法建立 pytest 暫存檔

第一次跑 pytest 時，sandbox 找不到可用 temporary directory。這是執行環境限制，不是程式 regression。改用 escalated pytest 執行後，取得真正 RED：`RuleCatalogLoader` 尚不存在。

### 2. Dependency `rule_id` 相容性

原本 Python / Node dependency rules 會共用既有 `rule_id`，例如 `langchain` 與 `@langchain/` 都必須輸出 `dependency_rag_framework_langchain`。如果全域禁止 duplicate `rule_id`，會破壞既有 package_json behavior。

解法：

- dependency catalog 以 package key 防止 duplicate package 覆蓋。
- Docker image 與 code pattern catalog 仍禁止 duplicate `rule_id`。
- 保留既有 dependency provider rule_id 輸出不變。

### 3. Ruff 行長

`RuleCatalogLoader` 初版有三個行長超過 79 字元。縮行後 `ruff check .` 通過。

## 測試結果

```text
.venv/bin/python -m pytest
163 passed in 2.28s

.venv/bin/ruff check .
All checks passed!

.venv/bin/mypy
Success: no issues found in 49 source files
```

## 驗收對照

- Provider 預設可從 package-bundled TOML rule catalogs 載入 rules：已完成。
- 測試中可注入 custom TOML catalog：已完成。
- `DependencyManifestProvider` 不再硬編碼 package mapping dict：已完成。
- `DockerComposeProvider` 不再用 hardcoded image if/else 判斷 Qdrant/Ollama/pgvector：已完成。
- `CodePatternProvider` 不再把主要 regex rules 全部硬編碼在 provider 檔案：已完成。
- Rule catalog malformed 時會明確失敗，不會靜默 fallback：已完成。
- Duplicate package/image/pattern 會明確失敗，不會靜默覆蓋：已完成。
- Regex rule 無法 compile 時會明確失敗：已完成。
- 原本 Task 9 / 10 / 11 provider behavior tests 全部通過：已完成。
- Full verification 通過：已完成。
