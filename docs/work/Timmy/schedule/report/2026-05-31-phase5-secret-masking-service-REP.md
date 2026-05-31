# 2026-05-31 Phase5 Secret Masking Service Report

## 實作摘要

本階段依照 `05-implement-secret-masking-service.md` 建立
`SecretMaskingService`，提供 JSON-like data、Markdown/log-like text、
evidence detail 與 query trace 後續共用的 secret masking path。

本次重點不是建立完整 secret scanner，而是先提供 release-readiness
scanner 需要的安全輸出基礎：

- known secret key detection
- short value full mask
- long value prefix/suffix + middle mask
- text key-value masking
- internal SecretPattern registry
- Authorization Bearer masking
- common token-like masking for GitHub, GitLab, AWS, Slack, OpenAI-style keys
- private key block body masking
- JSON-like recursive masking
- evidence `{key, value}` shape masking
- localhost endpoint 不過度遮罩

## 實作邏輯

依照 TDD + BDD 方式執行：

1. 先新增 `tests/unit/core/test_secret_masking_service.py`。
2. 確認測試因缺少 `SecretMaskingService` 進入 RED。
3. 新增最小 implementation，讓 value/text/json-like masking contract
   通過。
4. 補上 `tests/integration/test_phase5_secret_masking_behaviors.py`，
   模擬 report、Markdown 與 query trace 共用同一個 masking service。
5. BDD 測試抓到 `{key, value}` evidence shape 尚未遮罩，補上 sibling
   key masking rule。
6. 參考 Trivy / gitleaks 的規則化設計，加入 internal pattern registry，
   但不加入 scanner-only 能力。
7. 執行完整測試、lint、type check。

核心設計決策：

- `SecretMaskingService` 是唯一遮罩入口，provider 不應各自實作。
- key detection 使用保守 marker：`API_KEY`、`TOKEN`、`SECRET`、
  `PASSWORD`、`BEARER`、`AUTH`。
- 一般 endpoint，例如 local service URL，保持原樣，避免失去
  release-readiness evidence。
- `{ "key": "...", "value": "..." }` 這類 evidence shape 會用 sibling
  `key` 判斷 `value` 是否要遮罩。
- token-like pattern 以 internal registry 管理，避免新增 GitHub、GitLab、
  AWS、Slack 等 pattern 時散落成多個特殊分支。
- Trivy / gitleaks 僅作為規則 registry 設計參考；本階段不做 filesystem
  scanning、git history scanning、entropy detection、allowlist config、
  secret validity check 或外部 API 驗證。
- 測試與 report 不輸出完整 secret-like value。

## 實際介面與資料流

本階段保留單一 public service API，後續 provider / report writer / GUI
detail / query trace 都應呼叫同一個 service，而不是自行遮罩：

- `mask_value(value: str, key: str | None = None) -> str`
- `mask_text(text: str) -> str`
- `mask_json_like(value)`

資料流：

```text
raw string / evidence / JSON-like payload
↓
SecretMaskingService
↓
masked report / log / GUI detail / query trace
```

`mask_text()` 的順序：

1. 先處理 key-value text，因為 key name 是最可靠的 masking signal。
2. 再遍歷 internal `SecretPattern` registry。
3. 每個 pattern 只遮 named `value` group，避免把整段 evidence text
   吃掉。

目前 internal registry 支援：

| Pattern | 用途 |
|---|---|
| `authorization-bearer` | HTTP Authorization Bearer token |
| `openai-key` | OpenAI-style `sk-...` token |
| `github-token` | GitHub token prefix |
| `gitlab-token` | GitLab PAT prefix |
| `slack-token` | Slack bot/app/user token prefix |
| `slack-webhook` | Slack incoming webhook URL |
| `aws-access-key-id` | AWS access key id |
| `private-key-block` | private key block body |

不加入 external config 是刻意決策：目前還沒有 provider pipeline / report
writer / CLI config contract，先把 internal masking foundation 做穩，避免
過早設計 config surface。

## 實作步驟

### 1. 建立 TODO

新增：

- `docs/work/Timmy/schedule/todo/2026-05-31-phase5-secret-masking-service-TODO.md`

內容包含：

- 實作邏輯
- TDD / BDD 階段拆分
- 安全注意事項
- 驗證計畫

### 2. 建立 unit contract tests

新增：

- `tests/unit/core/test_secret_masking_service.py`

測試覆蓋：

- short secret value full mask
- long secret value prefix/suffix + middle mask
- secret key masks ordinary-looking value
- non-secret localhost endpoint 不被遮罩
- env-like text 保留 key name 但不保留完整 secret-like value
- Authorization Bearer text masking
- GitHub / GitLab / AWS / Slack / private key block pattern masking
- non-secret localhost endpoint、model name、route name 不被誤遮
- JSON-like dict/list/string recursive masking

### 3. 建立 SecretMaskingService

新增：

- `src/kai_mind/core/services/secret_masking_service.py`

提供：

- `mask_value(value: str, key: str | None = None) -> str`
- `mask_text(text: str) -> str`
- `mask_json_like(value)`
- internal `SecretPattern` registry

### 4. 建立 BDD-style integration test

新增：

- `tests/integration/test_phase5_secret_masking_behaviors.py`

測試情境：

- Markdown/report-like payload
- evidence detail `{key, value}`
- query trace Bearer token
- common token-like values
- private key block body
- local endpoint evidence

## 測試方式

執行：

```bash
.venv/bin/pytest tests/unit/core/test_secret_masking_service.py
.venv/bin/pytest tests/unit/core/test_secret_masking_service.py tests/integration/test_phase5_secret_masking_behaviors.py
.venv/bin/ruff check .
.venv/bin/mypy
.venv/bin/pytest
```

## 測試結果

```text
targeted phase5 tests: 11 passed
ruff: All checks passed
mypy: Success, no issues found in 24 source files
pytest: 80 passed
```

最後一次完整驗證：

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

結果：

```text
pytest: 80 passed
ruff: All checks passed
mypy: Success, no issues found in 24 source files
```

## 遇到的問題與解法

### 問題 1：測試 expectation 與 long secret policy 不一致

現象：

- 初版 JSON-like test 對一個較長 fake secret-like value 預期 full mask。
- 但 unit contract 已定義 long value 走 prefix/suffix + middle mask。

解法：

- 維持同一個 masking policy，不針對單一 fake value 加特殊分支。
- 調整 test expectation，確保完整 value 不出現在 output。

### 問題 2：evidence `{key, value}` shape 沒有用 sibling key 遮罩

現象：

- BDD-style integration test 顯示 `value` 欄位本身不是 secret key，
  但 sibling `key` 指向 secret-like key 時仍應遮罩。

解法：

- 在 JSON-like mapping 處理中加入 sibling key rule。
- 當 mapping 包含 `key` 與 `value`，且 `key` 是 secret-like key 時，
  對 `value` 使用該 key 進行遮罩。

### 問題 3：ruff formatting

現象：

- 新增 integration test 後有 import ordering 與 line length 問題。

解法：

- 執行 ruff fix 並手動拆行。

### 問題 4：hard-coded token regex 不利擴充

現象：

- 初版只支援少量 token-like pattern。
- GitHub、GitLab、AWS、Slack webhook 與 private key block 等常見輸出
  需要更一致的 masking path。

解法：

- 參考 Trivy / gitleaks 的 rules registry 設計。
- 新增 internal `SecretPattern` registry。
- `mask_text()` 先處理 key-value，再遍歷 registry 並只遮 named
  `value` group。

### 問題 5：read-only sandbox 無可用 temp directory

現象：

- sandbox 內一般 pytest capture 需要 temp file，會在啟動時失敗。
- 使用 `pytest -s` 後，Phase5 targeted tests 可執行並通過。
- 完整 pytest 仍有既有 `tmp_path` 測試因無可用 temp directory 失敗。

解法：

- 將 Codex sandbox 調整為可寫環境後，重新執行完整驗證。
- `.venv/bin/pytest`、`.venv/bin/ruff check .`、`.venv/bin/mypy`
  均通過。

## Task 5 複查

| 項目 | 結果 |
|---|---:|
| 建立 `SecretMaskingService` | 完成 |
| 支援 known secret key detection | 完成 |
| 支援 short value full mask | 完成 |
| 支援 long value prefix/suffix + middle mask | 完成 |
| 支援掃描任意 string | 完成 |
| 支援 dict/list JSON-like data | 完成 |
| 支援 internal token pattern registry | 完成 |
| 支援 GitHub / GitLab / AWS / Slack token-like masking | 完成 |
| 支援 private key block body masking | 完成 |
| 不加入 scanner-only entropy / allowlist / validity check | 完成 |
| 加入 snapshot-safe 測試 | 完成 |
| full fake secret 不會出現在 masked output | 完成 |
| `OPENAI_API_KEY` value 看起來普通也會遮罩 | 完成 |
| `http://localhost:6333` 不被錯誤遮罩 | 完成 |
| 遮罩後仍能讓使用者知道 key 存在 | 完成 |

## 最終結果

Phase5 範圍已完成。`SecretMaskingService` 可作為後續 providers、
reports、GUI detail、query trace 與 mapping proposal 的共用遮罩入口。
完整測試、lint、type check 均通過。
