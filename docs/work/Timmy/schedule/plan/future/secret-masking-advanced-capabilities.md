# Future: Secret Masking Advanced Capabilities

## 來源
Task 5 (Implement Secret Masking Service) 在「不包含範圍」和「可能風險與注意事項」中明確列出多項未來可擴充的能力：

> - 不做 entropy detection。
> - 不做 allowlist / enable-disable 外部設定。
> - 不處理企業級 DLP。
> - 不掃 git history。
> - Trivy / gitleaks 的 entropy、allowlist、repo scanning、git history scanning 都屬於 scanner 能力；Phase5 只建立 output masking foundation。

## 目的
將 `SecretMaskingService` 從 output masking foundation 擴充為更完整的 secret detection / masking 系統。

## 觸發條件
- 使用者回報 false negative（漏遮 secret）或 false positive（過度遮罩正常值）太多。
- 需要對 git history 中的 leaked secret 產生 risk hint。
- 需要讓使用者自訂 allowlist（例如 test fixtures 中的 fake key 不需遮罩）。
- 企業客戶需要 DLP-grade masking compliance。

## Future 1: Entropy-based Detection
- 對高 entropy 的 string value 加入額外遮罩判斷。
- 可參考 detect-secrets 的 entropy plugin 設計。
- 風險：entropy threshold 太低會 false positive 過多。

## Future 2: Allowlist / Enable-Disable 外部設定
- 讓使用者透過設定檔（例如 `.kai-mind/masking.toml`）定義：
  - 排除遮罩的 key pattern（例如 test fixtures 的 `sk-test-example`）。
  - 額外需要遮罩的 key pattern。
  - 開關特定 pattern rule。
- 必須有 schema validation，避免設定檔格式錯誤導致遮罩失效。

## Future 3: Git History Secret Scanning
- 掃描 git history 中是否曾經 commit 過 secret-like value。
- 只產生 risk hint，不修改 git history。
- 需考慮 performance（大型 repo 的 git log 很大）。
- 可參考 gitleaks 的 scanning 策略。

## Future 4: 企業級 DLP 整合
- 與外部 DLP 系統對接。
- 不在 Epic 1 範圍內。

## 與既有任務關係
- Task 5：已建立 `SecretMaskingService` 與 `SecretPattern` registry。
- Task 23：hardening 階段可一併評估 masking coverage gap。
- Task 24：final review 可檢查 masking 是否有漏洞。

## 不做事項
- 不取代既有 `SecretMaskingService`，只擴充能力。
- 不做完整 secret scanner 產品。
- 不做 secret rotation 或 remediation。
