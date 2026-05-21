# Viewer 與 Future Trace 行為決策脈絡

本文件保留 viewer 行為與 query trace 原始討論脈絡。Viewer 可作為 Epic 1 後續工作；query trace 則延後為 explicit opt-in workflow。

## Viewer 載入 invalid map

原始問題：map JSON 不存在或格式無效時，viewer 應如何處理？

決策：

- Viewer 可以啟動，但必須顯示 error state。
- 不顯示空白 graph。
- 不顯示半完成 graph。

保留原因：

Invalid map 通常是 schema 或 artifact 問題。Viewer 應清楚指出錯誤，而不是讓使用者誤以為 graph 沒有內容。

## Viewer filter 行為

原始問題：filter 應隱藏不符合項目，還是只高亮符合項目？

決策：

- 保留完整 graph。
- 只高亮 matching items。
- 預設不隱藏 unmatched items。

保留原因：

System Map 是結構理解工具。若 filter 直接隱藏 nodes，使用者可能誤以為某些 components 不存在。

## Viewer 不重新掃描 project

決策：

- Viewer 只讀 `ai_system_map.json`。
- Viewer 不讀 project folder。
- Viewer 不推論 JSON 中不存在的 component。

保留原因：

這可以避免 viewer 變成第二套 scanner，導致 schema contract 被 UI 行為反向定義。

## Future query trace 行為

原本討論過：

- 使用者在 GUI 輸入測試問題。
- 系統呼叫 detected RAG endpoint。
- 收集 trace steps 並映射回 map。
- Error / timeout step 保留為 partial replay。
- Missing endpoint 時不送出 query。

目前決策：

- 以上不屬於 Epic 1 MVP。
- 若未來實作，必須是 explicit opt-in。
- Missing endpoint 時仍不得送出 query。
- Error / timeout 不應讓已收集的 replay 消失。
