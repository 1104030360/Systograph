# 2026-05-31 Phase5 Secret Masking Service TODO

## 實作邏輯

本階段建立唯一的 `SecretMaskingService`，讓 providers、reports、logs、
GUI detail、query trace 與 mapping proposal 後續都能走同一條遮罩路徑。

核心原則：

- 不做完整 secret scanner。
- 不判斷 secret 是否有效。
- 不呼叫外部服務。
- 保留 key 存在的資訊，但不輸出完整 secret value。
- 對 key-based secret 保守遮罩，對一般 URL 例如 `http://localhost:6333`
  不過度遮罩。
- 參考 Trivy / gitleaks 的 rules registry 設計，但不把本階段擴大成
  scanner。

## 階段拆分

### 1. Red：定義 contract tests

- 新增 `tests/unit/core/test_secret_masking_service.py`。
- 覆蓋 short secret 全遮罩。
- 覆蓋 long secret prefix/suffix + middle mask。
- 覆蓋 `OPENAI_API_KEY` 即使 value 普通也遮罩。
- 覆蓋 localhost endpoint 不被遮罩。
- 覆蓋 `.env` fake OpenAI key 不完整出現在 output。
- 覆蓋 GitHub、GitLab、AWS、Slack、private key block 等常見 token-like
  pattern。
- 覆蓋 JSON-like dict/list/string 遞迴遮罩。

### 2. Green：建立最小 service

- 新增 `src/systograph/core/services/secret_masking_service.py`。
- 實作 `mask_value(value: str, key: str | None = None) -> str`。
- 實作 `mask_text(text: str) -> str`。
- 實作 `mask_json_like(value)`。
- 建立 internal `SecretPattern` registry，避免 token pattern 散落在多個
  hard-coded branch。

### 3. Refactor：穩定 API 與型別

- 使用簡單資料流，避免 provider-specific 分支。
- 維持 strict mypy 可通過。
- 確保 assert failure 不印出完整 secret。
- 不加入 entropy detection、allowlist config、secret validity check、
  filesystem scanning 或 git history scanning。

### 4. 驗證與報告

- 執行 unit test。
- 執行完整 pytest、ruff、mypy；若 read-only sandbox 無 temp directory，
  使用 no-cache / no-capture 變體並記錄限制。
- 新增 Phase5 report，記錄實作方式、測試結果與遇到的問題。

## 安全注意事項

- 測試中的 fake secret 不能用真實 secret pattern。
- 測試失敗訊息不可包含完整 secret。
- Markdown / JSON / log-like text 都要經過同一個 masking service。
