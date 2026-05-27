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
1. 建立 `src/kai_mind/core/providers/config_parse_provider.py`。
2. 定義 provider input：`FileInventory` + project root。
3. 實作 `.env` parser，只記錄 key 與 masked value。
4. 使用 Python stdlib `json` parse JSON。
5. 使用 `tomllib` parse TOML。
6. 使用 PyYAML `safe_load` parse YAML；若未安裝則在 dependencies 加入 `PyYAML>=6,<7`。
7. parse failure 回傳 structured issue，不 raise 到整體 scan。
8. 測試 malformed YAML/JSON、secret masking、empty config。

## 預期輸出
- `src/kai_mind/core/providers/config_parse_provider.py`
- `tests/core/test_config_parse_provider.py`

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
