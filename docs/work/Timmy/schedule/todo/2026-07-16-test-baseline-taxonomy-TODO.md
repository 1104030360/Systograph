# Test Baseline and Taxonomy TODO

## 目標

先用可重現的資料回答「測試亂在哪裡」，建立全量測試、collection、執行時間、
coverage 與測試分層基線，不在沒有證據前大搬移檔案。

## 實作邏輯

- 現有 `tests/contracts`、`tests/unit/core`、`tests/integration`、`tests/e2e`、
  `tests/web` 已表達不同責任，先驗證分類是否真能獨立執行。
- 以 KAI-Mind 的 release-readiness 風險決定測試優先序；不把行數 coverage 當完成定義。
- 參考 R2R 的分層與 pytest 官方 fixture 階層，但不複製過度 mock 或舊測試模式。

## 步驟

- [x] 記錄 Python、pytest、uv 與 git baseline。
- [x] 執行 collection 與完整 pytest，記錄 test count、duration、warning、skip/failure。
- [x] 盤點各測試目錄、共用 fixture、marker 與真實整合邊界。
- [x] 產生 production coverage 報告，找出高風險未覆蓋區域。
- [x] 寫入本階段 Report，明確列出保留、整理與不做的項目。
