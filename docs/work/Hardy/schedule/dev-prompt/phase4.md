# Phase4 Dev Prompt: Replay, Follow Focus, and Edge Readability

請改善 query replay 與 graph readability。

## 任務

- Replay controls 支援 play / pause / previous / next。
- 依 `sequence_index` 排序 trace events。
- 目前 replay step 對應 node / edge highlight。
- 新增 Follow focus toggle。
- 開啟 Follow 時置中目前 node。
- Edge label 改成簡短順序標記。
- Edge routing 要避免多分支重疊。

## 驗收

- 播放 replay 不會讓 graph 閃動。
- Follow on 時目前 node 會置中。
- Follow off 時不自動移動畫面。
- 多分支 edge 不完全疊在一起。
