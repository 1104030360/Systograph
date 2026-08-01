# Task 8: Implement Config Parse Provider

## 目標
實作 `ConfigParseProvider`，從 `.env`、YAML、JSON、TOML-like config 中產生 masked config facts。解析失敗必須變成 evidence / parse issue，而不是讓整體 scan crash。

## 為什麼要先做這個
config 是 RAG 系統中偵測 LLM provider、endpoint、secret-like keys、feature toggles 的高信號來源。它也最容易洩漏 secret，所以必須在 provider 初期完成並接上 masking。

## 前置需求
- Task 5 已完成 `SecretMaskingService`。
- Task 7 已完成 `FileInventory`。
- Task 12 尚未完成時，可先回傳 provider-local result，之後再接入 aggregation。

## 實作範圍
- 支援 `.env`、`.env.example`。
- 支援 `.json`。
- 支援 `.yaml` / `.yml`，YAML parser 採已決策選項 A：PyYAML + `safe_load`。
- 支援 `.toml` / `pyproject.toml` config sections。
- malformed config 產生 `ParseIssue` 與 `parse_error` evidence。
- 所有 value 經過 masking。

## 不包含範圍
- 不判斷 component slot。
- 不解析 Docker Compose，留給 Task 9。
- 不做完整 secret scanner。
- 不修復 malformed config。

## 建議實作步驟
1. 建立 `src/systograph/core/providers/config_parse_provider.py`。
2. 定義 provider input：`FileInventory` + project root。
3. 實作 `.env` parser，只記錄 key 與 masked value。
4. 使用 Python stdlib `json` parse JSON。
5. 使用 `tomllib` parse TOML。
6. 使用 PyYAML `safe_load` parse YAML；若未安裝則在 dependencies 加入 `PyYAML>=6,<7`。
7. parse failure 回傳 structured issue，不 raise 到整體 scan。
8. 測試 malformed YAML/JSON、secret masking、empty config。

## 預期輸出
- `src/systograph/core/providers/config_parse_provider.py`
- `tests/unit/core/test_config_parse_provider.py`

## 驗收標準
- `.env` 中 `OPENAI_API_KEY` 只輸出 masked value。
- malformed config 產生 parse issue 與 evidence。
- provider 不因單一壞檔中止。
- output evidence 包含 file、path、kind、masked value、rule_id。

## 可能風險與注意事項
- YAML parser 可能支援複雜型別，第一版只需要 safe load。
- 不使用 `yaml.load` 或任何 unsafe loader。
- parse error message 不應包含原始 secret value。
- `.env.example` 可記錄 key，但通常沒有真實 secret。
- JSON/YAML/TOML parse 過程中 raw value 可能短暫存在於記憶體，第一版重點不是「完全不進 memory」，而是「不可進入最終 facts、evidence、logs、reports、test snapshots」。
- TOML 解析使用 `tomllib`，並沿用 `FileInventory` 已經做好的唯讀與檔案大小邊界，不讓 provider 自己擴張掃描範圍。

## 可參考的開源專案與設計模式

### 1. Graceful Degradation: 壞檔不能拖垮整體掃描
- 可參考：scanner 類專案常見的 per-file error isolation 思維，例如 Checkov 類型的掃描流程。
- 套用方式：每個 config file 都要獨立 parse。遇到 `json.JSONDecodeError`、`tomllib.TOMLDecodeError`、`yaml.YAMLError` 或自家 `.env` parse error 時，不 raise 到整體 scan，而是轉成 structured `ParseIssue` 與 `parse_error` evidence，然後繼續掃描下一個檔案。
- 本 repo 對應：這不是額外加分項，而是本 Task 8 的硬需求，直接呼應 malformed config 測試目標。

### 2. Shared Secret Masking Path: 先遮蔽，再輸出
- 可參考：Trivy、gitleaks、detect-secrets 這類安全工具的共同精神是，scanner 可以找到敏感訊號，但不應把 raw secret 明文散落到輸出物。
- 套用方式：provider parse 出 key/value 後，不可直接把 raw value 放進 facts 或 evidence。必須先走既有 `SecretMaskingService`，再輸出 masked value。
- 本 repo 對應：沿用 Task 5 已完成的 shared masking path，不在 `ConfigParseProvider` 內重做一套 provider-local masking 規則。

### 3. Safe Parsing: 用標準且安全的 parser
- 可參考：Dynaconf / Python config tooling 常見做法是依格式使用對應 parser，避免自造輪子或使用 unsafe loader。
- 套用方式：
  - `.env`：自行做輕量 parser，聚焦 key/value 與 masking，不追求完整 shell 相容。
  - `.json`：使用 Python stdlib `json`。
  - `.toml`：使用 Python stdlib `tomllib`。
  - `.yaml`：只使用 PyYAML `safe_load()`，禁止 `yaml.load()`。
- 本 repo 對應：ConfigParseProvider 是 deterministic translator，不是通用設定執行器；第一版只需要安全、穩定、可測。

### 4. Input Boundary: Provider 不自己找檔
- 可參考：scanner pipeline / inventory-first 設計，包含你先前在 GitDiagram 與 Epic 1 研究中採用的邊界控制思維。
- 套用方式：`ConfigParseProvider` 直接接收 `FileInventory`，只處理 inventory 裡已經被判定為 eligible 的 config files。不要自己從 project root 遞迴搜尋，也不要重新碰 `.venv`、`node_modules`、gitignored paths。
- 本 repo 對應：Task 7 已經定義 `FileInventory` 是 downstream providers 的 deterministic input，Task 8 應延續這個邊界。

## 設計結論
`ConfigParseProvider` 可以視為一個 deterministic config translator：
- 它參考 scanner 類工具的容錯與 evidence 思維。
- 它遵守 Task 7 的 `FileInventory` 邊界。
- 它沿用 Task 5 的 `SecretMaskingService` shared masking path。
- 它負責安全讀取、優雅報錯、輸出 masked config facts。
- 它不負責 component 判斷、不做完整 secret scanner、也不修復壞掉的設定檔。

## 新手提示
Config provider 就像讀設定檔的翻譯器。它只把設定轉成 facts，不決定這些 facts 代表哪個 RAG 元件。

## 視覺化說明
```text
┌──────────────────────────┐
│ FileInventory             │
│ selected config files     │
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ ConfigParseProvider       │
│ env / json / yaml / toml  │
└──────┬────────┬──────────┘
       │        │
       ↓        ↓
┌──────────────┐ ┌──────────────┐
│ Config facts │ │ Parse issues │
└──────┬───────┘ └──────┬───────┘
       └────────┬───────┘
                ↓
┌──────────────────────────┐
│ Masked evidence           │
└──────────────────────────┘
```
