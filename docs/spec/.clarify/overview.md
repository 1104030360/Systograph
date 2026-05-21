# Discovery Overview

## 1. 釐清項目統計

- 資料模型相關：0 項
- 功能模型相關：0 項
- 總計：0 項

## 2. 優先級分佈

- High：0 項
- Medium：0 項
- Low：0 項

## 3. 建議釐清順序

### 第四階段：細節與優化

- 目前沒有 Low 優先級項目。

## 4. 釐清策略說明

- 平衡原則：前 5 題先處理 schema contract，接著處理 map / viewer / trace 的核心交互失敗行為，再回到跨平台與 GUI 邊界。
- 依賴關係：目前剩餘項目沒有必須先處理的資料模型前置依賴。
- 組合釐清：目前剩餘項目可獨立處理。

## 5. 覆蓋度摘要

| 分類 | 狀態 | 說明 |
|------|------|------|
| A1. 實體完整性 | Clear | Endpoint 已明確建模 |
| A2. 屬性定義 | Clear | 核心屬性都有型別與 note，secret masking 邊界已定義 |
| A3. 屬性值邊界條件 | Clear | status 值、event ordering 與 secret display 邊界已定義 |
| A4. 跨屬性不變條件 | Clear | 目前規格沒有明確計算型跨屬性公式需求 |
| A5. 關係與唯一性 | Clear | RiskHint 已明確關聯至 Evidence，並包含 target、rule 與 rationale |
| A6. 生命週期與狀態 | Clear | slot status、trace replay 事件順序與 trace 錯誤狀態已定義 |
| B1. 功能識別 | Clear | 建立 map、檢視 map、重播 query trace 三個交互點已識別 |
| B2. 規則完整性 | Clear | 核心成功路徑、解析錯誤、viewer 前置條件、trace MVP scope 與 trace endpoint missing 行為已定義 |
| B3. 例子覆蓋度 | Clear | 目前所有 Rule 都有 Example |
| B4. 邊界條件覆蓋 | Clear | output overwrite、filter behavior、trace error / timeout 已定義 |
| B5. 錯誤與異常處理 | Clear | project path 錯誤、parse error、invalid map JSON、endpoint missing、trace error 已定義 |
| C1. 詞彙表 | Partial | 核心術語大致一致，但尚未建立獨立 glossary；目前不建立釐清項目，因不阻礙實作或驗證策略 |
| C2. 術語衝突 | Clear | 未發現會阻礙測試的同名異義或同義混用 |
| D1. 待決事項 | Clear | Feature files 內未留下 #TODO |
| D2. 模糊描述 | Clear | GUI filter、trace MVP 與 trace error 邊界已明確定義 |
