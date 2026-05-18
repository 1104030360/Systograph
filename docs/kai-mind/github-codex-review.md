# GitHub Codex Code Review 設定

這份文件記錄 KAI-Mind 應如何在 GitHub pull requests 中使用 Codex。

## 建議路線

優先使用官方 Codex GitHub code review。等團隊需要更細的控制時，再考慮自訂 GitHub Action。

## 設定 Checklist

1. 替這個 repository 啟用 Codex Cloud。
2. 進入 Codex settings。
3. 對這個 repository 開啟 Code review。
4. 如果希望每個 PR 都自動 review，開啟 Automatic reviews。
5. 在 repo 根目錄使用 `AGENTS.md` 補上專案 review guidance。
6. 保留 human review。Codex 是額外 reviewer，不是替代 reviewer。

## 手動觸發 Review

在 pull request comment 中輸入：

```text
@codex review
```

也可以指定 review 方向：

```text
@codex review for security regressions, missing tests, and risky behavior changes.
@codex review for scanner safety and accidental secret exposure.
@codex review for CI gate behavior and JSON schema compatibility.
```

## Automatic Reviews

當 Codex settings 中開啟 automatic reviews 後，Codex 可以在 PR 被建立或標記 ready for review 時自動 review。這適合在團隊 PR flow 穩定後啟用。

## Repository Guidance

根目錄的 `AGENTS.md` 應告訴 Codex 這個專案重視什麼：

- Scanner behavior 預設必須 read-only。
- 不顯示 secret values。
- 標記 network exposure 與 cloud fallback 風險。
- 檢查 JSON schema compatibility。
- 檢查 scanner behavior 是否缺少 tests。

## 可選：自訂 GitHub Action

如果團隊之後想要更客製化的 workflow，可以使用 `openai/codex-action`：

- 在 `pull_request` 時觸發。
- Checkout PR merge commit。
- 用 review prompt 執行 Codex。
- 將 Codex output 貼成 PR comment。

這種方式控制力更高，但也需要管理 API keys、workflow permissions、sandboxing 與成本。

## 目前建議

MVP 階段：

- 等 Codex Cloud 啟用後，先使用官方 Codex PR review。
- 保持 `AGENTS.md` 短且聚焦。
- 一開始先用 `@codex review` 手動請 Codex review。
- 等 PR 數量上來後，再開啟 automatic reviews。
