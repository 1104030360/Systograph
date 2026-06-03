# 2026-06-03 Phase 12a Provider Rule Catalogs TODO

## 目標

將 provider 內會持續成長的 deterministic detection rules 從 Python 硬編碼搬到 package-bundled TOML catalogs，讓後續增加 dependency package、Docker image、code pattern 規則時，不需要改 provider 掃描流程。

## 實作邏輯

1. 先用 TDD/BDD 補測試，鎖定 catalog loader validation 與三個 provider 的 custom catalog injection 行為。
2. 建立共用 `RuleCatalogLoader`，集中處理 TOML 讀取、欄位驗證、duplicate 檢查、regex compile 檢查。
3. 建立三份 package-bundled TOML catalogs：
   - `dependency_manifest_rules.toml`
   - `docker_image_rules.toml`
   - `code_pattern_rules.toml`
4. 重構 provider，讓 provider 只負責套用已載入的 rule catalog，不再保存會成長的 mapping / regex rule 清單。
5. 保留既有 facts、evidence、rule_id、ordering 與 parse behavior，不改 `ai-system-map/v1` contract。

## 步驟

1. 建立 TODO 文件，明確記錄本階段拆解。
2. 新增 `tests/unit/core/test_rule_catalog_loader.py`：
   - valid catalog loads
   - malformed TOML rejected
   - missing required field rejected
   - duplicate package/image/pattern rejected
   - duplicate rule_id rejected
   - invalid ecosystem/type rejected
   - regex compile failure rejected
3. 補 provider regression tests：
   - dependency provider 可注入 custom dependency catalog
   - Docker provider 可注入 custom image catalog
   - code pattern provider 可注入 custom pattern catalog
4. 實作 `RuleCatalogLoader` 與 rule models。
5. 建立 TOML catalogs 並搬移既有 rules。
6. 重構三個 provider 讀取 loader。
7. 跑相關測試，再跑 full verification。
8. 建立 Report，逐一對照 Phase 12a 驗收標準。

## 驗證命令

```bash
.venv/bin/python -m pytest tests/unit/core/test_rule_catalog_loader.py
.venv/bin/python -m pytest tests/unit/core/test_dependency_manifest_provider.py tests/unit/core/test_docker_compose_provider.py tests/unit/core/test_code_pattern_provider.py
.venv/bin/python -m pytest tests/integration/test_phase9_docker_compose_provider_behaviors.py tests/integration/test_phase10_dependency_manifest_provider_behaviors.py tests/integration/test_phase11_code_pattern_provider_behaviors.py
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```
