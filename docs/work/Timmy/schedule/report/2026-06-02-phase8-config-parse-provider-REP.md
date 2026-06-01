# 2026-06-02 Phase8 Config Parse Provider Report

## 實作摘要

本階段依照
`docs/work/Timmy/schedule/plan/unfinish/08-implement-config-parse-provider.md`
完成 `ConfigParseProvider`，讓 scanner 可以從 `FileInventory` 中讀取
`.env`、`.env.example`、JSON、YAML、TOML config，產生 masked config
facts，並在遇到 malformed config 時回傳 `ParseIssue` 與 `parse_error`
evidence，而不是中止整體掃描。

本次新增與修改：

- `src/kai_mind/core/providers/config_parse_provider.py`
- `src/kai_mind/core/models/scan.py`
- `tests/unit/core/test_config_parse_provider.py`
- `tests/integration/test_phase8_config_parse_provider_behaviors.py`
- `pyproject.toml`
- `uv.lock`

核心成果：

- 建立 `ConfigParseProvider.collect(inventory)`。
- 建立 `ScanFact`、`ParseIssue`、`ProviderScanResult` 最小 scanner models。
- `.env`、JSON、YAML、TOML scalar values 都會轉成 structured facts。
- 所有 string values 在輸出前都走 `SecretMaskingService`。
- malformed JSON / YAML / TOML 會產生 `ParseIssue` 與 `parse_error`
  evidence。
- `.env` 單行格式錯誤會記 issue，但仍保留同檔其他合法 key/value。
- 排除 `docker-compose.yml` / `compose.yml` 這類 YAML 檔，避免混入 Task 9
  範圍。
- 增加 runtime dependency：`PyYAML>=6,<7`。
- 同步更新 `uv.lock`，讓 lockfile 與 dependency metadata 一致。
- Review 後補強 structured `{key, value}` config masking，避免 `value`
  leaf 因 key name 遺失而洩漏 raw secret。

## 實作邏輯

這次維持資料結構先行，避免 provider 直接回傳鬆散 dict。

1. 先在 `scan.py` 補最小 scanner-local models：
   `ScanFact`、`ParseIssue`、`ProviderScanResult`。
2. `ConfigParseProvider` 只接受 `FileInventory`，不自己遞迴掃目錄。
3. 每個檔案獨立 parse：
   `.env` 使用輕量 parser，JSON 用 `json`，TOML 用 `tomllib`，YAML 用
   `yaml.safe_load()`。
4. structured config 解析後做 scalar flatten，path 使用 dot notation；
   list index 用 `[i]`。
5. 每個 scalar 都轉成：
   `ScanFact(kind="config_value", file, path, value, rule_id)` +
   對應 `Evidence`。
6. structured config 先整棵走 `SecretMaskingService.mask_json_like(...)`，
   再 flatten 成 facts / evidence；`.env` scalar 則用
   `SecretMaskingService.mask_value(...)`。
7. parse 失敗不 raise 到整體 scan，而是記成：
   `ParseIssue(provider="config", scan_stage="config_parse", ...)` +
   `Evidence(kind="parse_error", rule_id="config_parse_error", ...)`。

設計取捨：

- YAML parser 採 `yaml.safe_load()`。本次也用 Context7 查了 PyYAML 文件，
  確認 untrusted input 應使用 `safe_load()` / `SafeLoader`，不使用
  `unsafe_load()`。
- `PyYAML` 沒有內建 type stubs，因此 import 採 scoped
  `# type: ignore[import-untyped]`，避免把整個模組型別檢查關掉。
- 目前只 flatten scalar leaves，不做 component / endpoint / risk hint 推導；
  這些是後續 services / providers 的責任。

## 實作步驟

### 1. 先補 TODO

新增：

- `docs/work/Timmy/schedule/todo/2026-06-02-phase8-config-parse-provider-TODO.md`

內容包含：

- 階段拆分
- 實作邏輯
- TDD/BDD 步驟
- 驗收清單

### 2. 先寫 failing tests

新增 unit tests：

- `tests/unit/core/test_config_parse_provider.py`

覆蓋行為：

- `.env` secret value 會被遮罩。
- non-config YAML file name 例如 `docker-compose.yml` 不應由本 provider 處理。
- JSON / YAML / TOML 會 flatten 成 structured facts。
- malformed JSON 會產生 parse issue，但同一批次其他合法檔案仍持續被 parse。
- `.env` 壞行會記 issue，且 issue message 不可洩漏 raw secret。
- empty config file 會產生空結果。
- JSON / YAML 中 `{key: "PASSWORD", value: "..."}` 這類 structured secret
  entry 會依 sibling key 遮罩 value。

新增 BDD-style integration tests：

- `tests/integration/test_phase8_config_parse_provider_behaviors.py`

覆蓋情境：

- `openai_external_provider_rag` 會產生 masked `.env.example` facts 與
  `config.yaml` facts。
- `basic_qdrant_ollama_rag` 只會讀 `.env.example`，不會把
  `docker-compose.yml` 當成 Phase 8 config input。

### 3. 實作 provider 與最小 models

修改：

- `src/kai_mind/core/models/scan.py`

新增：

- `ScanFact`
- `ParseIssue`
- `ProviderScanResult`

新增：

- `src/kai_mind/core/providers/config_parse_provider.py`

主要行為：

- 依 inventory 篩選 `.env*`、`.json`、`.toml`、`.yaml`、`.yml`。
- 明確排除 compose file names。
- `.env` 支援 `export KEY=...` 與 quoted values 的基本去殼。
- structured config 透過 recursive flatten 轉成 scalar facts。
- 產出 deterministic evidence id。
- parse error 統一使用 `config_parse_error` rule id。

### 4. 驗證

Targeted verification：

```bash
.venv/bin/python -m pytest tests/unit/core/test_config_parse_provider.py tests/integration/test_phase8_config_parse_provider_behaviors.py
.venv/bin/ruff check src/kai_mind/core/models/scan.py src/kai_mind/core/providers/config_parse_provider.py tests/unit/core/test_config_parse_provider.py tests/integration/test_phase8_config_parse_provider_behaviors.py
.venv/bin/mypy src/kai_mind/core/models/scan.py src/kai_mind/core/providers/config_parse_provider.py tests/unit/core/test_config_parse_provider.py tests/integration/test_phase8_config_parse_provider_behaviors.py
```

Full verification：

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

Dependency sync：

```bash
uv lock
```

## 遇到的問題與解法

### 1. Read-only sandbox 讓 pytest / ruff 無法使用 temp/cache

第一次跑 targeted pytest 與 ruff 時，分別遇到：

- `No usable temporary directory found`
- `Failed to create temporary file`

這是 sandbox temp/cache 權限問題，不是程式碼錯誤。

解法：

- 改用可寫 temp/cache 環境重跑 `.venv` 下的 pytest / ruff / mypy。

### 2. 設計文件提到 `ScanFact[] / ParseIssue[]`，但 repo 尚未有正式模型

如果直接讓 provider 回傳 dict，後面 phase 很快就會變成一堆 ad hoc keys。

解法：

- 先在 `src/kai_mind/core/models/scan.py` 補最小模型，
  只放 Phase 8 真的需要的欄位，不預先發明過多抽象。

### 3. `PyYAML` 是 runtime dependency，但型別檢查沒有 stubs

`mypy` 會對 `import yaml` 報 `import-untyped`。

解法：

- 將 `PyYAML>=6,<7` 正式加入 `pyproject.toml` runtime dependencies。
- 對 `import yaml` 採 scoped `# type: ignore[import-untyped]`，
  把忽略限制在單一第三方 import，不擴大到整個檔案。

### 4. `ruff` 對 import order 與 line length 很嚴

第一輪 targeted ruff 抓出多個 line length 與 import sorting 問題。

解法：

- 手動收斂長行與型別別名。
- 剩餘 import sorting 交給 `ruff --fix` 處理。

### 5. Review 發現 structured `{key, value}` secret 會漏遮罩

Review 時用小型 repro 驗證：

```text
{"environment": [{"key": "PASSWORD", "value": "correct horse battery staple"}]}
```

原本 flatten 後只把 leaf key `value` 傳給 `mask_value(...)`，導致
`PASSWORD` 這個 sibling key 語意遺失，raw secret 會進入 facts / evidence。

解法：

- 先新增 regression test，確認 JSON / YAML 的 `{key, value}` secret entry
  會被遮罩。
- `ConfigParseProvider` 在 structured parse 成功後，先呼叫
  `SecretMaskingService.mask_json_like(...)`，再 flatten masked tree。
- 這沿用 Task 5 既有 shared masking path，不在 provider 內新增第二套規則。

## 測試方式

### RED

- 先新增 tests，再執行 targeted pytest。
- 初次 RED 結果為 `ModuleNotFoundError`，證明測試確實先於 production
  code 建立。

### GREEN

- 補最小 models 與 provider。
- 讓 targeted pytest 轉綠。

### REFACTOR / VERIFY

- 跑 targeted ruff / mypy。
- 修正型別與格式問題後，再跑 full pytest / full ruff / full mypy。

## 測試結果

- 初次 targeted pytest RED：2 errors
  - `ModuleNotFoundError: No module named 'kai_mind.core.providers.config_parse_provider'`
- Targeted pytest GREEN：`9 passed`
- Review regression targeted pytest：`11 passed`
- Targeted ruff：`All checks passed`
- Targeted mypy：`Success: no issues found in 4 source files`
- Full pytest：`113 passed`
- Full ruff：`All checks passed`
- Full mypy：`Success: no issues found in 37 source files`

沒有發現與本次改動無關的額外失敗。

## Plan 驗收確認

- `.env` 中 `OPENAI_API_KEY` 只輸出 masked value：已完成，unit +
  integration tests 覆蓋。
- malformed config 產生 parse issue 與 evidence：已完成，unit tests 覆蓋。
- provider 不因單一壞檔中止：已完成，unit test 覆蓋。
- output evidence 包含 `file`、`path`、`kind`、`masked value`、`rule_id`：
  已完成，unit tests 覆蓋。
- `.env.example` 可記錄 key presence，但不洩漏 raw value：已完成，
  integration test 覆蓋。
- JSON / YAML / TOML config 可產生 structured facts：已完成，unit tests
  覆蓋。
- provider 不重新決定 scan boundary，只處理 `FileInventory` 內檔案：
  已完成，unit + integration tests 覆蓋。
- 不解析 Docker Compose：已完成，unit + integration tests 覆蓋。
- 不使用 `yaml.load()` 或 unsafe loader：已完成，實作採
  `yaml.safe_load()`。
- 所有相關測試、`ruff`、`mypy` 都通過：已完成。

## 後續注意

- 後續 Task 9 的 Docker Compose parsing 應重用這次建立的
  `ParseIssue` / `parse_error` pattern。
- 後續 Task 10 可直接重用 TOML / JSON parser 與 flatten patterns，
  但依賴 manifest 規則仍應獨立定義，不要把 config rule ids 混進去。
