# Phase2 規格釐清總覽

## 1. 釐清項目統計

- 資料模型相關：0 項
- 功能模型相關：0 項
- 總計：0 項

本次掃描輸入：

- `docs/spec/erm.dbml`：31 個 Tables
- `docs/spec/features/*.feature`：10 個 Features、104 條 Rules、111 個 Examples
- `docs/spec/draft/epic1-phase2.md`
- 現行 `docs/MODEL-CONTRACT.md`、`docs/API-GUIDE.md` 與相關 web/core contract

舊 `docs/spec/.clarify/resolved/` 在目前工作樹已刪除，內容屬舊 RAG contract。本次只以歷史檔名防止重複提問，不恢復或沿用 legacy product surface。

## 2. 優先級分佈

- High：0 項
- Medium：0 項
- Low：0 項

## 3. 建議釐清順序

### 第一階段：核心資料模型

此階段的 High 資料模型項目已全部釐清。

原因：這些問題會改變 Build／Artifact identity、readiness/static schemas、project identity、foreign keys 與 durable decision lifecycle。

### 第二階段：核心功能規則

此階段的 High 功能項目已全部釐清。

原因：release gate、latest build、人工決策 replay 與 restart 可用性的核心決策皆已固定。

### 第三階段：邊界條件與跨模型關聯

此階段的 Medium 項目已全部釐清。

原因：deterministic serialization、查詢與排序、UI error handling、auditability、跨 build navigation 與術語一致性皆已固定。

### 第四階段：細節與優化

目前沒有 Low 優先級項目。未建立只影響文字偏好、內部 class 命名或不改變測試策略的問題。

## 4. 釐清策略說明

### 平衡原則

- 第一階段先固定資料 identity、status 與 publish boundary。
- 第二階段處理使用者可觀察的核心流程。
- 第三階段在資料模型與功能模型間交替，避免先完成一側後又因另一側答案重做。

### 依賴關係

目前沒有會阻擋下一題的未決依賴。

### 組合釐清

目前沒有需要組合釐清的未決群組。

## 5. 覆蓋度摘要

| 分類 | 狀態 | Discovery 結果 |
|---|---|---|
| A1 實體完整性 | Clear | 核心實體、Environment lifecycle 與 derived identity 邊界皆已定義 |
| A2 屬性定義 | Clear | 所有欄位有型別與 note；readiness category/severity vocabulary 已固定 |
| A3 屬性值邊界條件 | Clear | Coverage/depth bounds、跨平台 project path normalization、digest contract 與 order/rank/sequence 皆已定義 |
| A4 跨屬性不變條件 | Clear | Mapping Completeness、build parent、generated_from 與 atomic publish set 規則皆已明確 |
| A5 關係與唯一性 | Clear | PK/FK、unresolved static refs、EvidenceTableRow cardinality 與 candidate 跨 build identity 皆已建立 |
| A6 生命週期與狀態 | Clear | Build reason、共用五態、activation、readiness finding status 與 reject/skip persistence 皆已定義 |
| B1 功能識別 | Clear | 10 個使用者／系統交互點皆有獨立 Feature |
| B2 規則完整性 | Clear | 10 個 Feature 都有 Rules，且 release gate、latest、rescan、Apply retry 與 Trace lifetime 皆已定義 |
| B3 例子覆蓋度 | Clear | 103 條 Rules 全部至少有一個 Example，沒有未標記缺例情況 |
| B4 邊界條件覆蓋 | Clear | 主要 happy/failure paths、trace lifetime、audit exposure 與 corruption blast radius 皆已覆蓋 |
| B5 錯誤與異常處理 | Clear | 主要 409/422、fail-closed、strict sidecar error 與 retryable classification 皆已定義 |
| C1 詞彙表 | Partial | 尚無獨立 canonical glossary；readiness category/severity vocabulary 已在 ERM 固定 |
| C2 術語衝突 | Clear | Active v2 與 legacy 已分離；activation 欄位名稱已統一 |
| D1 待決事項 | Clear | 無 `#TODO`，目前沒有會改變實作或測試策略的未決事項 |
| D2 模糊描述 | Clear | 未發現會阻礙驗收的「健全／直覺／適當」等未量化形容詞 |

## 6. 下一步

`docs/spec/prompts/3.clarify.md` 已完成；所有釐清題皆已更新 DBML／Gherkin 並歸檔 resolved records。
