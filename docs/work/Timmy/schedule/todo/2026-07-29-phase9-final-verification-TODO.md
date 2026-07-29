# 2026-07-29 階段E：最終全分支 review、驗收逐項確認、報告與提交 TODO

## 目標

phase9 約束 5：全部做完後逐一確認 13.7/13.8 文件提出的想法全部實現；
全套品質閘門綠；主 agent 最終 review 所有 subagent 產出；寫報告；提交。

## 實作邏輯

- 最終 review 兩層：主 agent（本 session）親自讀全分支 diff＋派一個最終
  code reviewer subagent 做 whole-branch review，交叉比對。
- 驗收逐項核對：13.7 驗收 5 條、13.8 驗收 6 條，逐條在報告中附證據
  （grep 輸出、測試名、指令結果）。
- 品質閘門：`uv run ruff check src tests`、`uv run ruff format --check src
  tests`、`uv run mypy src tests`、`uv run pytest` 全綠。
- 提交紀律：只 stage 本次 phase9 工作觸及的檔案；使用者工作樹裡既有的
  未提交文件搬移（Meeting-Sync 刪除、plan finish/ 搬移、arch-graph 修改等）
  不動也不提交。

## 步驟

- [ ] 最終 whole-branch review（review package + 最終 reviewer subagent）。
- [ ] Review findings 修正（一波 fix + 一次 scoped re-review）。
- [ ] 13.7 驗收條件逐項打勾（含 grep 零命中、4 格不變、護欄測試紅燈驗證）。
- [ ] 13.8 驗收條件逐項打勾（含假陽性測試紅燈驗證、alias 單條、快照測試）。
- [ ] 品質閘門四連跑全綠。
- [ ] 各階段 REP 報告補齊（A/B/C/D/E）。
- [ ] Commit（分支 feat/phase2-plan13.7-13.8，只含 phase9 工作檔案）。

## 驗收

- 13.7/13.8 全部驗收條件附證據通過。
- 全部 REP 檔案齊備、內容含實作邏輯/步驟/測試方式/問題與解法/測試結果。
