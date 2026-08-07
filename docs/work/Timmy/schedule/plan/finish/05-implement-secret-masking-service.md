# Task 5: Implement Secret Masking Service

## 目標
建立唯一的 `SecretMaskingService`，確保 JSON、Markdown、logs、GUI detail、query trace、mapping proposal 都不輸出完整 secret。這個服務要在 providers 大量產生 evidence 前先完成。

## 為什麼要先做這個
設計文件與 AGENTS.md 都把 secret exposure 列為高優先風險。若每個 provider 自己遮罩，容易漏掉 `.env`、endpoint、trace output 或 snapshot 中的 secret。

## 前置需求
- Task 1 已完成 package scaffold。
- Task 2 已定義 evidence/value 欄位。
- Task 4 已有 fake secret fixture。

## 實作範圍
- 建立 `SecretMaskingService`。
- 支援 known secret key detection：`API_KEY`、`TOKEN`、`SECRET`、`PASSWORD`、`BEARER`、`AUTH`。
- 支援 short value 全遮罩、long value prefix/suffix + middle mask。
- 支援掃描任意 string、dict/list JSON-like data。
- 支援 evidence 常見 `{key, value}` shape：當 sibling `key` 是 secret-like key 時，`value` 也必須遮罩。
- 參考 Trivy / gitleaks 的 rules registry 設計，建立 internal `SecretPattern` registry。
- 支援常見 token-like pattern 遮罩：
  - Authorization Bearer token
  - OpenAI-style `sk-...`
  - GitHub token prefix，例如 `ghp_...`
  - GitLab PAT prefix，例如 `glpat-...`
  - Slack token，例如 `xoxb-...`
  - Slack webhook URL
  - AWS access key id，例如 `AKIA...`
  - private key block body
- 加入 snapshot-safe 測試。

## 不包含範圍
- 不做完整 secret scanner。
- 不判定 secret 是否有效。
- 不呼叫外部服務。
- 不處理企業級 DLP。
- 不掃 filesystem。
- 不掃 git history。
- 不做 entropy detection。
- 不做 allowlist / enable-disable 外部設定。
- 不呼叫 Trivy / gitleaks；它們只作為設計參考，不是 runtime dependency。

## 建議實作步驟
1. 建立 `src/systograph/core/services/secret_masking_service.py`。
2. 定義 `mask_value(value: str, key: str | None = None) -> str`。
3. 定義 `mask_text(text: str) -> str`，用保守 token-like pattern 遮罩。
4. 定義 `mask_json_like(value)`，遞迴處理 dict/list/string。
5. 定義 internal `SecretPattern` registry，集中管理 token-like regex，避免 pattern 散落在多個 hard-coded branch。
6. `mask_text()` 先處理 key-value，再遍歷 `SecretPattern` registry，且只遮 named `value` group。
7. 寫測試：短 secret 全遮罩、長 secret 保留少量 prefix/suffix、普通值不過度遮罩。
8. 寫測試：`.env` fake OpenAI key 不得完整出現在 output。
9. 寫測試：GitHub / GitLab / AWS / Slack / private key block 常見 pattern 不完整出現在 output。
10. 寫測試：`http://localhost:6333`、model name、route name 不被誤遮。
11. 寫 BDD-style integration test：Markdown/report-like payload、evidence detail、query trace 共用同一個 masking service。

## 預期輸出
- `src/systograph/core/services/secret_masking_service.py`
- `tests/unit/core/test_secret_masking_service.py`
- `tests/integration/test_phase5_secret_masking_behaviors.py`
- `docs/work/Timmy/schedule/todo/2026-05-31-phase5-secret-masking-service-TODO.md`
- `docs/work/Timmy/schedule/report/2026-05-31/2026-05-31-phase5-secret-masking-service-REP.md`

## 驗收標準
- full fake secret 不會出現在 masked output。
- key name 是 `OPENAI_API_KEY` 時即使 value 看起來普通也會遮罩。
- `http://localhost:6333` 不應被錯誤遮罩。
- 遮罩後仍能讓使用者知道 key 存在。
- GitHub / GitLab / AWS / Slack / OpenAI-style / Bearer / private key block 等常見 pattern 不完整出現在 output。
- JSON-like nested string 內的 token-like value 也會被同一套 registry 遮罩。
- report-like、Markdown-like、query trace-like payload 都走同一條 masking path。
- 不新增 runtime dependency。
- `.venv/bin/pytest`、`.venv/bin/ruff check .`、`.venv/bin/mypy` 必須通過。

## 可能風險與注意事項
- 遮罩策略要保守，寧可多遮一點，不要漏 secret。
- 不要在失敗 assert message 中印出 full secret。
- 參考依據：Trivy secret scanning docs 強調 secret-like findings 應結構化且避免洩漏；OpenTelemetry GenAI docs 提醒 input/output 可能敏感，不應預設完整 capture。
- Trivy / gitleaks 的 entropy、allowlist、repo scanning、git history scanning 都屬於 scanner 能力；Phase5 只建立 output masking foundation。
- local endpoint、model name、route name 是 release-readiness evidence，不能因為規則太寬而被誤遮。

## 新手提示
Secret masking 不是要判斷密碼對不對，而是確保報告、log、測試快照裡看不到完整密碼。

## 視覺化說明
```text
┌──────────────┐
│ Raw value    │
└──────┬───────┘
       ↓
┌──────────────────────────┐
│ SecretMaskingService      │
│ one masking path for all  │
└──────┬───────┬───────┬───┘
       │       │       │
       ↓       ↓       ↓
┌──────────┐ ┌──────────┐ ┌────────────┐
│ Evidence │ │ Markdown │ │ GUI detail │
└──────────┘ └──────────┘ └─────┬──────┘
                                ↓
                         ┌────────────┐
                         │ Query trace │
                         └────────────┘
```
