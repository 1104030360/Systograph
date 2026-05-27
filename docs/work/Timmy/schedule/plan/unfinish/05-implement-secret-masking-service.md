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
- 加入 snapshot-safe 測試。

## 不包含範圍
- 不做完整 secret scanner。
- 不判定 secret 是否有效。
- 不呼叫外部服務。
- 不處理企業級 DLP。

## 建議實作步驟
1. 建立 `src/kai_mind/core/services/secret_masking_service.py`。
2. 定義 `mask_value(value: str, key: str | None = None) -> str`。
3. 定義 `mask_text(text: str) -> str`，用保守 token-like pattern 遮罩。
4. 定義 `mask_json_like(value)`，遞迴處理 dict/list/string。
5. 寫測試：短 secret 全遮罩、長 secret 保留少量 prefix/suffix、普通值不過度遮罩。
6. 寫測試：`.env` fake OpenAI key 不得完整出現在 output。

## 預期輸出
- `src/kai_mind/core/services/secret_masking_service.py`
- `tests/core/test_secret_masking_service.py`

## 驗收標準
- full fake secret 不會出現在 masked output。
- key name 是 `OPENAI_API_KEY` 時即使 value 看起來普通也會遮罩。
- `http://localhost:6333` 不應被錯誤遮罩。
- 遮罩後仍能讓使用者知道 key 存在。

## 可能風險與注意事項
- 遮罩策略要保守，寧可多遮一點，不要漏 secret。
- 不要在失敗 assert message 中印出 full secret。
- 參考依據：Trivy secret scanning docs 強調 secret-like findings 應結構化且避免洩漏；OpenTelemetry GenAI docs 提醒 input/output 可能敏感，不應預設完整 capture。

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
