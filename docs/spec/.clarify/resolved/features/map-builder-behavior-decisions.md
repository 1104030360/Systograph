# Map Builder 行為決策脈絡

本文件整理原本分散在 `resolved/features/*` 的 map builder 行為釐清結果。

## Project folder 不存在或不可讀

原始問題：使用者提供的 project folder 不存在或不可讀時，是否仍輸出 partial map？

決策：

- 這是 fatal precondition failure。
- 不輸出正常 `ai_system_map.json`。
- 應輸出 `map-error.md`，並以 non-zero exit code 結束。

保留原因：

Project root 不可讀時沒有可靠 scan basis。輸出 partial map 會誤導使用者以為 scanner 已經看過 project。

## Config / Docker Compose 解析失敗

原始問題：單一 config 或 docker-compose 解析失敗時，是否中止整個 scan？

決策：

- 不應中止整個 scan。
- 應輸出 partial map。
- Parse error 應成為 evidence。
- 相關 risk hint 應標示 uncertainty。

保留原因：

真實 project 常有不完整、環境相依或格式不標準的 config。Epic 1 應盡量回報可觀察事實，而不是因單一檔案失敗就完全沒有產出。

## Output directory 已存在

原始問題：`outputs/` 已存在時是否覆寫舊 artifacts？

決策：

- 不覆寫既有 artifacts。
- 若 output directory 已有 map artifacts，建立 timestamped run directory。

保留原因：

Scanner output 是 review artifact。覆寫舊結果會讓前後比較與 PR artifact 保存變困難。

## Secret-safe output

原始問題：secret masking 應在哪裡處理？

決策：

- 在 serialization 前處理。
- JSON、Markdown、logs、snapshots、UI 應使用同一 masking policy。

保留原因：

若各 output layer 自行 masking，容易出現某個輸出漏遮罩。
