# Phase8 Config Parse Provider TODO

## 目標

實作 `ConfigParseProvider`，從 `FileInventory` 中挑出 config files，解析
`.env`、JSON、YAML、TOML，產生 masked config facts 與 parse issues，
且單一壞檔不能讓整體 scan 中止。

## 實作邏輯

- `ConfigParseProvider` 只做低階 config facts / evidence / issues，不做
  component slot 判斷。
- Provider 不自己遞迴掃目錄，只接收 `FileInventory` 作為 deterministic
  input boundary。
- 每個檔案各自 parse，錯誤隔離在單檔內；malformed config 轉成
  structured `ParseIssue` 與 `parse_error` evidence。
- 所有輸出的 value 都要經過既有 `SecretMaskingService`，不可把 raw secret
  放進 facts、evidence、logs、reports 或 test snapshots。
- path 一律沿用 project-relative POSIX path，不引入 absolute path。
- parser 選型保持簡單：`.env` 使用輕量 parser，JSON 用 stdlib `json`，
  TOML 用 stdlib `tomllib`，YAML 用 `yaml.safe_load()`。
- Provider 保持 read-only，不修改被掃描 project。

## 階段

### 階段 1：定義資料結構與 RED 測試

- [x] 釐清 provider output 應包含哪些欄位：facts、evidence、parse issues。
- [x] 先寫 unit tests，覆蓋 `.env`、JSON、YAML、TOML、malformed config、
      empty config、masking、single-file failure isolation。
- [x] 補 BDD-style integration test，使用既有 fixture 驗證真實 sample project
      的 config signals 與 parse error 行為。
- [x] 先執行 targeted tests，確認是因為功能尚未實作而失敗，不是測試寫壞。

### 階段 2：最小實作讓測試轉綠

- [x] 建立 `src/kai_mind/core/providers/config_parse_provider.py`。
- [x] 規劃 provider-local result models；若現有 models 不足，再補最小支援型別。
- [x] 先做 `.env` parse + masking。
- [x] 再做 JSON / TOML / YAML parse。
- [x] 實作 malformed file -> `ParseIssue` + `parse_error` evidence。
- [x] 確保 provider 遇到單一壞檔仍會繼續處理下一個檔案。

### 階段 3：收斂 contract 與驗證

- [x] 檢查 output paths 是否全部為 project-relative POSIX path。
- [x] 檢查 evidence / facts 中沒有 raw secret 洩漏。
- [x] 檢查 provider 沒有自行掃描 inventory 外的檔案。
- [x] 跑 targeted pytest / ruff / mypy。
- [x] 跑 full pytest / ruff / mypy。
- [x] 寫 Phase8 report，逐條核對 plan 驗收標準。

## 步驟

1. 先讀設計文件與既有 provider patterns，避免重做另一套資料流。
2. 寫 failing tests，明確描述行為，不先寫 production code。
3. 用最小資料結構讓測試能夠表達 config facts / parse issues。
4. 逐格式實作 parser，保持單檔單責任，避免多層巢狀分支。
5. 將所有 value 在輸出前送進 `SecretMaskingService`。
6. 對 malformed 檔案輸出 partial result，而不是 raise 到整體 scan。
7. 跑完整驗證，修掉與這次改動相關的回歸問題。
8. 完成後寫 report，記錄實作邏輯、步驟、測試方式、問題與解法、測試結果。

## 驗收清單

- [x] `.env` 中 `OPENAI_API_KEY` 只輸出 masked value。
- [x] `.env.example` 可輸出 key presence，但不洩漏 raw value。
- [x] JSON / YAML / TOML config 都能產生 structured config facts。
- [x] malformed JSON / YAML / TOML 會產生 parse issue 與 `parse_error`
      evidence。
- [x] provider 不因單一壞檔中止。
- [x] output evidence 包含 `file`、`path`、`kind`、`masked value`、
      `rule_id`。
- [x] evidence file path 永遠不是 absolute path，且使用 POSIX `/`。
- [x] Provider 不修改被掃描 repo。
- [x] Provider 不重新決定 scan boundary，只處理 `FileInventory` 內檔案。
- [x] 不使用 `yaml.load()` 或其他 unsafe loader。
- [x] 所有相關測試、`ruff`、`mypy` 都通過。
